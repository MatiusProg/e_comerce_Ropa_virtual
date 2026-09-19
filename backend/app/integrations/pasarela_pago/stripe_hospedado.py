"""Stripe Checkout: la sesion de pago la hospeda Stripe, no nosotros.

Se elige con PAGO_PROVEEDOR=stripe y PAGO_API_KEY=sk_test_...

POR QUE CHECKOUT HOSPEDADO Y NO UN FORMULARIO PROPIO
-----------------------------------------------------
Con Checkout, **el sistema nunca ve un numero de tarjeta**: el cliente los
escribe en una pagina de Stripe. Es lo que dice la seccion 6.7, y no es solo
comodidad --- un formulario propio nos metaria en el alcance de PCI-DSS, que es
un problema que un proyecto academico no puede resolver ni deberia simular.

EL MONTO VA EN LA UNIDAD MINIMA DE LA MONEDA
---------------------------------------------
Stripe cobra en centavos, no en bolivianos: 150.50 se manda como 15050. Es el
error clasico de esta integracion --- mandar 150.5 cobra un centavo y medio, y
mandar 150 cobra un boliviano y medio ---, asi que la conversion esta en una
funcion sola y con su prueba.

Se usa `Decimal` y se cuantiza antes de pasar a entero. Con `float` el precio
150.55 se guarda como 150.54999999999998 y truncar da 15054 en vez de 15055:
un centavo de diferencia por linea que no cuadra con `venta.total`, y un
descuadre de centavos en una pasarela es de los defectos mas caros de encontrar.

LA MONEDA
---------
Stripe no admite el boliviano (BOB) como moneda de cobro en la mayoria de las
cuentas de prueba, asi que `PAGO_MONEDA` existe y por defecto es 'usd'. Es una
limitacion del sandbox, no del diseno: la venta se guarda en su moneda y lo
unico que se traduce es lo que se le manda a la pasarela. Queda anotado como
deuda --- ver la ficha de CU-27 ---.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings
from app.integrations.pasarela_pago.base import (
    ErrorDePasarela,
    EventoDePago,
    FirmaInvalida,
    SesionDePago,
    SolicitudDePago,
)

_log = logging.getLogger("violetboutique.pago")

#: Los eventos de Stripe que hablan del resultado del cobro de una sesion.
#: Cualquier otro se registra y no mueve nada --- una cuenta emite decenas ---.
TIPO_COMPLETADA = "checkout.session.completed"
TIPO_EXPIRADA = "checkout.session.expired"
TIPOS_DE_COBRO = (TIPO_COMPLETADA, TIPO_EXPIRADA)


def a_unidad_minima(monto: Decimal) -> int:
    """Convierte 150.50 en 15050. Ver la nota de la cabecera.

    Cuantiza a dos decimales ANTES de multiplicar, con redondeo comercial. Si
    llegara un monto con mas decimales de los que la moneda admite, truncar
    despues de multiplicar perderia un centavo.
    """
    return int((Decimal(monto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) * 100)


class ProveedorStripe:
    """Crea una Checkout Session y devuelve su URL."""

    nombre = "stripe"
    cobra_de_verdad = True

    def __init__(self) -> None:
        if not settings.PAGO_API_KEY:
            raise ValueError(
                "PAGO_PROVEEDOR=stripe exige PAGO_API_KEY. Con la clave vacia, "
                "Stripe rechaza toda peticion y el cliente veria un error al "
                "confirmar el pedido."
            )
        # Se importa aca y no arriba para que el modulo se pueda leer ---y el
        # resto de la costura se pueda usar--- sin tener el SDK instalado.
        import stripe

        self._stripe = stripe
        self._cliente = stripe.StripeClient(settings.PAGO_API_KEY)

    def crear_sesion(self, solicitud: SolicitudDePago) -> SesionDePago:
        lineas = [
            {
                "price_data": {
                    "currency": solicitud.moneda.lower(),
                    "product_data": {"name": linea.descripcion},
                    "unit_amount": a_unidad_minima(linea.precio_unitario),
                },
                "quantity": linea.cantidad,
            }
            for linea in solicitud.lineas
        ]

        try:
            sesion = self._cliente.v1.checkout.sessions.create(
                params={
                    "mode": "payment",
                    "line_items": lineas,
                    # `pedido` va ADEMAS de la sesion: la pantalla de
                    # retorno lo necesita para saber que consultar, y con solo
                    # la sesion tendria que guardarselo aparte. El simulado ya
                    # lo mandaba; esto los deja iguales.
                    "success_url": solicitud.url_exito
                    + "?sesion={CHECKOUT_SESSION_ID}&pedido="
                    + solicitud.referencia,
                    "cancel_url": solicitud.url_cancelado
                    + "?pedido="
                    + solicitud.referencia,
                    "customer_email": solicitud.correo_cliente,
                    # Vuelven intactos en el webhook: es como CU-28 sabe a que
                    # venta corresponde el evento sin adivinarlo por el monto.
                    "metadata": solicitud.metadatos,
                },
                # LA CLAVE DE IDEMPOTENCIA VA EN `options`, NO EN `params`.
                #
                # No es un detalle de estilo: `params` es el cuerpo de la
                # peticion y Stripe **rechaza los parametros que no conoce**.
                # Puesta ahi adentro, TODA la llamada fallaba con
                # «Received unknown parameter: idempotency_key», el proveedor lo
                # traducia a ErrorDePasarela y el cliente veia «perdida de
                # comunicacion con la pasarela» --- un mensaje honesto y
                # enganoso a la vez: Stripe contestaba perfecto, lo que estaba
                # mal era lo que le mandabamos.
                #
                # Lo que hace, bien puesta: si esta peticion se reintenta
                # ---por un corte de red al responder--- Stripe devuelve la
                # MISMA sesion en vez de abrir una segunda. Sin eso, un
                # reintento dejaria dos sesiones cobrables para un mismo pedido.
                # Comprobado contra Stripe: dos llamadas con la misma clave
                # devuelven el mismo `cs_test_...`.
                options={"idempotency_key": "pedido-" + solicitud.referencia},
            )
        except Exception as e:  # el SDK levanta su propia jerarquia
            _log.exception("Stripe rechazo la sesion del pedido %s", solicitud.referencia)
            raise ErrorDePasarela(str(e)) from e

        if not sesion.url:
            raise ErrorDePasarela("Stripe devolvio una sesion sin URL de pago.")

        return SesionDePago(id_externo=sesion.id, url_redireccion=sesion.url)


    # --- CU-28: la notificacion ------------------------------------------

    def interpretar_webhook(self, cuerpo: bytes, firma: str | None) -> EventoDePago:
        """Verifica la firma de Stripe y traduce el evento.

        `construct_event` hace las dos cosas: comprueba el HMAC contra
        `PAGO_WEBHOOK_SECRET` --- el `whsec_...` que da el panel al registrar
        el endpoint, que **no es** la clave de API --- y devuelve el evento ya
        interpretado. Si la firma no cuadra levanta, y eso se traduce a
        `FirmaInvalida`.

        **El cuerpo tiene que llegar en bytes y sin tocar.** Stripe firma los
        bytes exactos que mando; volver a serializar el JSON cambia espacios y
        orden de claves y la verificacion falla aunque el mensaje sea legitimo.
        Es el error mas comun de esta integracion y por eso el router lee
        `await request.body()` en vez de recibir un modelo de Pydantic.

        La marca de tiempo de la firma tiene tolerancia de cinco minutos, que
        es la de Stripe: una notificacion vieja reenviada por un tercero no
        sirve para nada.
        """
        secreto = settings.PAGO_WEBHOOK_SECRET.strip()
        if not secreto:
            # Sin secreto no hay nada que verificar, y aceptar sin verificar
            # seria dejar que cualquiera de por pagado un pedido.
            raise FirmaInvalida(
                "PAGO_WEBHOOK_SECRET no esta configurado: no se puede verificar."
            )
        if not firma:
            raise FirmaInvalida("La peticion no trae la cabecera Stripe-Signature.")

        import stripe

        try:
            evento = stripe.Webhook.construct_event(cuerpo, firma, secreto)
        except ValueError as error:
            raise ErrorDePasarela(f"El cuerpo no es JSON valido: {error}") from error
        except Exception as error:  # SignatureVerificationError y parientes
            raise FirmaInvalida(str(error)) from error

        # A DICCIONARIO, DE UNA VEZ Y EN UN SOLO LUGAR.
        #
        # `construct_event` devuelve un `stripe.Event`, que **no es un dict**:
        # en el SDK 15.x `StripeObject` niega `.get()` a proposito y levanta
        # «'get' is a dict method, but a Event is not a dict». Tratarlo como
        # diccionario reventaba con AttributeError, el router respondia 500 y
        # Stripe reintentaba durante dias contra un endpoint que nunca iba a
        # aceptarlo --- con el pedido pagado y la venta en PENDIENTE_PAGO.
        #
        # Se convierte una sola vez y el resto de la funcion trabaja con datos
        # planos: asi no queda ningun acceso que dependa de la forma del SDK, y
        # una version futura que cambie esa forma rompe aqui y no en cinco
        # lugares distintos.
        datos = evento.to_dict()

        tipo = str(datos.get("type") or "")
        objeto = (datos.get("data") or {}).get("object") or {}
        metadatos = objeto.get("metadata") or {}

        # `checkout.session.completed` es el que interesa: la sesion se cerro
        # con el pago hecho. `expired` es su contraparte --- el cliente nunca
        # pago y Stripe cerro la sesion ---. El resto se registra y no mueve
        # nada: una cuenta de Stripe emite decenas de tipos distintos.
        aprobado = tipo == TIPO_COMPLETADA and objeto.get("payment_status") == "paid"

        return EventoDePago(
            id_evento=str(datos.get("id") or ""),
            tipo=tipo,
            id_sesion=(str(objeto["id"]) if objeto.get("id") else None),
            referencia=(str(metadatos["codigo"]) if metadatos.get("codigo") else None),
            aprobado=aprobado,
            es_de_cobro=tipo in TIPOS_DE_COBRO,
            carga_util=cuerpo.decode("utf-8", errors="replace"),
        )
