"""
P8 - Pagos  |  capa: servicio (reglas de negocio)

Ciclo de desarrollo: 3
Caso de uso: CU-27, la parte de iniciar el cobro. CU-28 confirma.

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

LA COSTURA C-PAGO: QUE LE PIDE P7 A P8
---------------------------------------
P7 (Ventas) llama a `iniciar_cobro()` y recibe la URL a la que mandar al
cliente. No conoce Stripe, ni el nombre del proveedor, ni la forma de una
sesion de pago. Al reves tampoco: este modulo recibe lo que hay que cobrar y
no sabe que es un carrito ni una modalidad de entrega.

**Sin commit.** La sesion de pago se abre dentro de la transaccion que abrio
P7, y quien la cierra es P7. Ver la nota de `iniciar_cobro`.
"""
import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import pasarela_pago
from app.integrations.pasarela_pago import (
    ErrorDePasarela,
    LineaDePago,
    SolicitudDePago,
)
from app.modules.pagos import repository

_log = logging.getLogger("violetboutique.pago")

#: El metodo de la compra digital. Los otros dos ---EFECTIVO y TARJETA_POS---
#: son del punto de venta de CU-31 y no pasan por ninguna integracion.
METODO_PASARELA = "PASARELA"

#: Estado inicial. Lo mueve CU-28, y solo CU-28 (decision D5).
ESTADO_INICIADO = "INICIADO"


class ErrorDePago(Exception):
    """Base de los errores previstos de P8."""


class PasarelaNoDisponible(ErrorDePago):
    """La pasarela no contesto, o contesto algo que no se entiende.

    El router la traduce a 502. Importa que NO sea un 500: no es un defecto del
    sistema sino un servicio de terceros caido, y el cliente puede reintentar.
    """


def iniciar_cobro(
    db: Session,
    *,
    venta_id: int,
    referencia: str,
    total: Decimal,
    lineas: list[LineaDePago],
    correo_cliente: str | None,
) -> tuple[str, str]:
    """Abre la sesion de pago y deja la fila de `pago`. **Sin commit.**

    Devuelve `(url_redireccion, id_externo)`.

    EL ORDEN IMPORTA, Y ES ESTE A PROPOSITO
    ----------------------------------------
    Primero se le pide la sesion a la pasarela, DESPUES se escribe la fila.

    Al reves ---escribir el pago y luego llamar a la pasarela--- dejaria un
    `pago` en INICIADO sin sesion asociada cada vez que la pasarela falle, y
    esas filas huerfanas son las que despues nadie sabe si cobrar o no.

    Hacerlo en este orden tiene su propio riesgo y hay que decirlo: si la
    pasarela crea la sesion y la escritura posterior falla, queda una sesion
    abierta en Stripe que el sistema no conoce. Es el mal menor, y es
    recuperable: esa sesion expira sola, y si alguien llegara a pagarla, CU-28
    recibe el evento, no encuentra el pago y lo guarda igual en
    `transaccion_pasarela` con `pago_id` nulo --- que es exactamente para lo
    que esa columna admite nulos.

    NO HACE COMMIT
    --------------
    La venta, sus lineas, el apartado de stock y este pago tienen que ser una
    sola transaccion: si el pago se escribiera aparte, un corte entre las dos
    dejaria una venta sin forma de cobrarse o un cobro sin venta. Quien hace
    commit es CU-27, cuando ya escribio todo.
    """
    solicitud = SolicitudDePago(
        referencia=referencia,
        lineas=lineas,
        moneda=settings.PAGO_MONEDA,
        url_exito=settings.PAGO_URL_EXITO,
        url_cancelado=settings.PAGO_URL_CANCELADO,
        correo_cliente=correo_cliente,
        # Vuelven intactos en el webhook. Es como CU-28 encuentra la venta sin
        # tener que deducirla del monto, que no es unico.
        metadatos={"venta_id": str(venta_id), "codigo": referencia},
    )

    try:
        sesion = pasarela_pago.crear_sesion(solicitud)
    except ErrorDePasarela as e:
        _log.warning("No se pudo abrir la sesion de pago de %s: %s", referencia, e)
        raise PasarelaNoDisponible(str(e)) from e

    repository.agregar_pago(
        db,
        venta_id=venta_id,
        metodo=METODO_PASARELA,
        estado=ESTADO_INICIADO,
        monto=total,
        referencia_externa=sesion.id_externo,
    )
    return sesion.url_redireccion, sesion.id_externo


def cobra_de_verdad() -> bool:
    """Si el proveedor configurado mueve dinero real.

    P7 se lo pasa a la pantalla para que avise cuando el pago es simulado.
    """
    return pasarela_pago.cobra_de_verdad()
