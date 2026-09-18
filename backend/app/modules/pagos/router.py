"""
P8 - Pagos  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Iniciar el pago electronico contra la pasarela  (lo llama P7)
  CU-28 Confirmar pago del pedido (webhook firmado e idempotente)

EL WEBHOOK NO LLEVA TOKEN, Y NO ES UN OLVIDO
---------------------------------------------
Quien llama a este endpoint es la pasarela, que no tiene cuenta en el sistema y
no puede iniciar sesion. **Lo que lo protege es la firma**, que se verifica
antes de leer una sola clave del cuerpo.

Poner un token seria peor que inutil: obligaria a guardar una credencial
compartida en el panel de Stripe y no probaria nada sobre el contenido del
mensaje --- un token robado deja publicar cualquier cosa, mientras que la firma
cubre el cuerpo exacto que viajo ---.

Por eso este router **no declara `dependencies`**, a diferencia de todos los
demas del proyecto. Es la unica excepcion y esta es su justificacion.

EL CUERPO SE LEE EN CRUDO
-------------------------
`await request.body()` y no un modelo de Pydantic. La firma se calcula sobre
los bytes exactos que la pasarela mando; si FastAPI interpreta el JSON y
alguien lo vuelve a serializar, cambian los espacios y el orden de las claves y
la verificacion falla aunque el mensaje sea legitimo. Es el error mas comun de
esta integracion.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import settings
from app.core.dependencies import DbSession
from app.integrations import pasarela_pago
from app.modules.pagos import service
from app.modules.pagos.schemas import RespuestaWebhookOut, SimularPagoIn

_log = logging.getLogger("violetboutique.pago")

router = APIRouter(prefix="/pagos", tags=["Pagos"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.


@router.post(
    "/webhook",
    response_model=RespuestaWebhookOut,
    summary="CU-28 Confirmar el pago (lo llama la pasarela, no una persona)",
    responses={
        400: {"description": "La firma no se pudo verificar, o el cuerpo no se entiende."},
    },
)
async def recibir_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
    firma_simulada: Annotated[str | None, Header(alias="X-Firma-Simulada")] = None,
) -> RespuestaWebhookOut:
    """Aplica una notificación de la pasarela. **Es el único camino a PAGADA.**

    Es la decisión **D5**: el estado del pago lo determina la pasarela y nadie
    más. Ni la pantalla de retorno, ni un endpoint del cliente, ni el
    Administrador pueden mover una venta a pagada por otro lado.

    **Casi todo responde 200, y es deliberado.** Un código de error le dice a la
    pasarela «volvé a intentar», y eso sólo sirve cuando el problema es nuestro
    y es pasajero. Un evento repetido, uno de un tipo que no interesa o uno de
    una sesión desconocida no mejoran reintentando: se registran y se cierra el
    asunto. Stripe reenvía hasta tres días si no recibe un 2xx.

    La firma inválida es la excepción: 400, porque ahí sí hay algo que avisar y
    no es un reintento lo que lo arregla. Queda registrada igual, con
    `firma_valida = false` y sin pago asociado — son justamente las filas que
    uno quiere mirar cuando algo huele mal.

    Las dos cabeceras: `Stripe-Signature` es la de Stripe y `X-Firma-Simulada`
    la del proveedor de pruebas. Se aceptan las dos y se le pasa al proveedor la
    que haya venido; el router no sabe cuál corresponde a cuál, y no tiene por
    qué saberlo.
    """
    cuerpo = await request.body()
    firma = stripe_signature or firma_simulada

    try:
        resultado = service.confirmar_pago(db, cuerpo=cuerpo, firma=firma)
    except service.FirmaNoVerificada as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    except service.EventoIlegible as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    return RespuestaWebhookOut(resultado=resultado)


@router.post(
    "/simulacion",
    response_model=RespuestaWebhookOut,
    summary="CU-28 Disparar a mano la notificación del proveedor simulado",
    responses={
        404: {"description": "El proveedor configurado no es el simulado."},
    },
)
def simular_notificacion(
    datos: SimularPagoIn, db: DbSession
) -> RespuestaWebhookOut:
    """Fabrica la notificación que el proveedor simulado no puede mandar solo.

    **Existe porque el simulado no tiene servidor que llame de vuelta.** Con
    Stripe, quien golpea `/webhook` es Stripe; acá no hay nadie, así que este
    endpoint arma el mismo cuerpo, lo firma con el mismo secreto y lo entrega
    por el mismo camino. **No hay un segundo camino a PAGADA**: esto termina
    llamando a `confirmar_pago` igual que el webhook de verdad.

    Es lo que permite demostrar el flujo completo sin claves de Stripe, y lo que
    lo mantiene honesto: si esta ruta aplicara el pago por su cuenta, la
    demostración estaría mostrando un flujo distinto del real.

    **Devuelve 404 cuando el proveedor no es el simulado.** No 403: si el
    sistema está corriendo contra una pasarela de verdad, esta ruta no existe.
    """
    if pasarela_pago.cobra_de_verdad():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No existe esa ruta con la pasarela configurada.",
        )

    cuerpo, firma = service.fabricar_notificacion_simulada(
        sesion=datos.sesion, pedido=datos.pedido, aprobado=datos.aprobado
    )
    _log.info(
        "Simulando notificacion %s para la sesion %s",
        "aprobada" if datos.aprobado else "rechazada",
        datos.sesion,
    )

    try:
        resultado = service.confirmar_pago(db, cuerpo=cuerpo, firma=firma)
    except service.FirmaNoVerificada as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error
    except service.EventoIlegible as error:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(error)) from error

    return RespuestaWebhookOut(resultado=resultado)


@router.get(
    "/configuracion",
    summary="CU-28 Cómo está configurado el cobro (sin secretos)",
)
def configuracion() -> dict:
    """Qué proveedor está activo y si cobra de verdad.

    **No devuelve ninguna clave.** Sirve para saber, desde afuera y sin entrar
    al panel de Railway, si el despliegue quedó con la pasarela que se creía —
    que es justo el error que deja aceptando pedidos que nadie cobra.
    """
    return {
        "proveedor": settings.PAGO_PROVEEDOR,
        "cobra_de_verdad": pasarela_pago.cobra_de_verdad(),
        "moneda": settings.PAGO_MONEDA,
        "webhook_verificable": bool(settings.PAGO_WEBHOOK_SECRET.strip()),
    }
