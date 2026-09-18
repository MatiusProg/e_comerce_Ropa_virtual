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
import hashlib
import hmac
import json
import logging
import secrets
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import pasarela_pago
from app.integrations.pasarela_pago import (
    ErrorDePasarela,
    FirmaInvalida,
    LineaDePago,
    SolicitudDePago,
)
from app.modules.inventario import service as inventario
from app.modules.pagos import repository
from app.modules.ventas import carrito_repository
from app.modules.ventas import repository as ventas_repository
from app.modules.ventas.models import Venta

#: El estado al que CU-28 lleva la venta. Es el unico camino a PAGADA.
ESTADO_VENTA_PAGADA = "PAGADA"

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


# =====================================================================
# CU-28 - Confirmar pago del pedido
# =====================================================================
#
# TODA LA IDEMPOTENCIA ES UNA SOLA RESTRICCION
# ---------------------------------------------
# El UNIQUE sobre `transaccion_pasarela.evento_id` es lo que hace que una
# notificacion repetida NO descuente el inventario dos veces: el INSERT falla,
# se trata como «ya visto» y no se vuelve a tocar la venta.
#
# Se escribe la transaccion ANTES de mover nada, y a proposito. Al reves ---
# mover primero y registrar despues --- dos entregas simultaneas del mismo
# evento pasarian las dos por el descuento antes de que ninguna llegue al
# INSERT. Registrar primero convierte la carrera en un choque contra la base,
# que es lo unico que sabe resolverla.
#
# Las pasarelas reintentan de verdad: Stripe reenvia hasta tres dias si no
# recibe un 2xx. Esto no es un caso de borde.
#
# POR QUE SE RESPONDE 200 A CASI TODO
# ------------------------------------
# Un codigo de error le dice a la pasarela «volve a intentar». Eso solo sirve
# cuando el problema es nuestro y es pasajero. Un evento repetido, uno de un
# tipo que no interesa, o uno de una sesion que no conocemos NO mejoran
# reintentando: se registran, se responde 200 y se acabo. Devolver error ahi
# deja a la pasarela golpeando durante dias por algo que nunca va a cambiar.
#
# La firma invalida es la excepcion y responde 400: ahi si hay algo que avisar,
# y no es un reintento lo que lo arregla.

#: Lo que el servicio decidio hacer con un evento. Viaja al router para que
#: elija el codigo HTTP, y al log para que se pueda seguir que paso.
RESULTADO_APLICADO = "aplicado"
RESULTADO_REPETIDO = "repetido"
RESULTADO_IGNORADO = "ignorado"
RESULTADO_SIN_PAGO = "sin_pago"
RESULTADO_RECHAZADO = "rechazado"

ESTADO_APROBADO = "APROBADO"
ESTADO_RECHAZADO = "RECHAZADO"


class FirmaNoVerificada(ErrorDePago):
    """La notificacion no venia firmada por quien dice. El router da 400."""


class EventoIlegible(ErrorDePago):
    """Venia firmada pero el cuerpo no se entiende. El router da 400."""


def confirmar_pago(db: Session, *, cuerpo: bytes, firma: str | None) -> str:
    """Aplica una notificacion de la pasarela. **Hace commit.**

    Es el unico camino por el que una venta llega a PAGADA: la decision D5 dice
    que el estado del pago lo determina la pasarela y nadie mas. Ni la pantalla
    de retorno ni un endpoint del cliente pueden mover esto.

    Devuelve uno de los `RESULTADO_*` para que el router elija el codigo y el
    log diga que paso. Levanta `FirmaNoVerificada` o `EventoIlegible`; todo lo
    demas se resuelve adentro y termina en un 200.
    """
    # 1. Verificar y traducir. Son la misma llamada a proposito: asi no hay
    #    forma de leer el contenido sin haber comprobado quien lo mando.
    try:
        evento = pasarela_pago.interpretar_webhook(cuerpo, firma)
    except FirmaInvalida as error:
        # La firma invalida SI se registra, con `firma_valida=False` y sin
        # pago asociado. Son justamente las filas que uno quiere mirar cuando
        # algo huele mal, y por eso `transaccion_pasarela.pago_id` es nullable.
        _registrar_firma_invalida(db, cuerpo=cuerpo)
        _log.warning("Webhook con firma invalida: %s", error)
        raise FirmaNoVerificada(str(error)) from error
    except ErrorDePasarela as error:
        _log.warning("Webhook ilegible: %s", error)
        raise EventoIlegible(str(error)) from error

    # 2. Registrar ANTES de mover nada. Ver la nota de arriba.
    pago = _pago_del_evento(db, evento)
    try:
        repository.agregar_transaccion(
            db,
            pago_id=pago.id if pago else None,
            evento_id=evento.id_evento,
            tipo_evento=evento.tipo,
            firma_valida=True,
            carga_util=evento.carga_util,
        )
    except IntegrityError:
        # El UNIQUE de `evento_id` lo atrapo: esta notificacion ya se aplico.
        db.rollback()
        _log.info("Webhook repetido, se ignora: %s", evento.id_evento)
        return RESULTADO_REPETIDO

    # 3. Los eventos que no hablan de un cobro quedan registrados y no mueven
    #    nada. Una cuenta de Stripe emite decenas de tipos distintos.
    if not evento.es_de_cobro:
        db.commit()
        return RESULTADO_IGNORADO

    if pago is None:
        # Un evento de cobro de una sesion que no conocemos. Queda guardado
        # ---es lo que se mira cuando algo no cuadra--- y no hay nada que
        # aplicar. Reintentar no lo mejora: 200.
        db.commit()
        _log.warning("Cobro sin pago conocido: sesion=%s", evento.id_sesion)
        return RESULTADO_SIN_PAGO

    if not evento.aprobado:
        pago.estado = ESTADO_RECHAZADO
        db.commit()
        _log.info("Pago rechazado por la pasarela: %s", evento.id_sesion)
        return RESULTADO_RECHAZADO

    # 4. Aprobado. Si el pago ya estaba aprobado no se vuelve a aplicar: es la
    #    segunda red, para el caso de dos eventos DISTINTOS sobre el mismo
    #    cobro --- que el UNIQUE de `evento_id` no puede atrapar ---.
    if pago.estado == ESTADO_APROBADO:
        db.commit()
        return RESULTADO_REPETIDO

    _aplicar_cobro(db, pago)
    db.commit()
    _log.info("Pago aprobado y aplicado: sesion=%s", evento.id_sesion)
    return RESULTADO_APLICADO


def _registrar_firma_invalida(db: Session, *, cuerpo: bytes) -> None:
    """Deja rastro de una notificacion que no se pudo verificar.

    El `evento_id` se deriva del cuerpo con un hash: sin firma valida no se
    puede confiar en el identificador que venga adentro --- ni siquiera se lee
    el JSON ---, y hace falta alguno porque la columna es UNIQUE. Dos intentos
    identicos quedan como una sola fila, que es lo correcto: es el mismo
    intento repetido.
    """
    huella = hashlib.sha256(cuerpo).hexdigest()[:40]
    try:
        repository.agregar_transaccion(
            db,
            pago_id=None,
            evento_id=f"sin-firma:{huella}",
            tipo_evento="firma.invalida",
            firma_valida=False,
            carga_util=cuerpo.decode("utf-8", errors="replace")[:20_000],
        )
        db.commit()
    except IntegrityError:
        # Ya estaba registrado ese mismo intento.
        db.rollback()


def _pago_del_evento(db: Session, evento) -> object | None:
    """El pago al que se refiere el evento, bloqueado para actualizarlo.

    Se busca por la sesion, que es lo que la pasarela siempre devuelve. El
    codigo de la venta queda como respaldo para el caso en que los metadatos
    lleguen y la sesion no --- y porque es lo que hace legible el registro
    cuando algo falla.

    El `FOR UPDATE` serializa dos entregas del mismo cobro que lleguen a la vez
    con identificadores de evento distintos.
    """
    if evento.id_sesion:
        pago = repository.obtener_por_referencia(db, evento.id_sesion, bloquear=True)
        if pago is not None:
            return pago

    if evento.referencia:
        venta = ventas_repository.obtener_venta_entidad(db, codigo=evento.referencia)
        if venta is not None:
            return repository.obtener_por_venta(db, venta.id, bloquear=True)

    return None


def _aplicar_cobro(db: Session, pago) -> None:
    """Marca el pago y la venta, y mueve el inventario. **Sin commit.**

    LOS DOS MOVIMIENTOS, OTRA VEZ
    ------------------------------
    CU-27 **aparto** el stock al crear el pedido, asi que estas unidades estan
    en `cantidad_reservada`, no en `cantidad_disponible`. Venderlas es
    `LIBERACION +n` seguido de `VENTA -n`: el neto sobre el disponible es cero,
    los dos movimientos son no nulos ---el CHECK rechaza los de cero--- y el
    invariante `disponible == suma(movimientos)` se sostiene.

    Es exactamente lo que hace CU-24 cuando el cliente se lleva la prenda que
    fue a probarse, y esta escrito igual a proposito: un `VENTA -n` a secas
    descontaria por segunda vez unidades que ya habian salido del disponible, y
    dejaria el saldo en negativo.
    """
    venta = db.get(Venta, pago.venta_id)
    if venta is None:
        # No deberia pasar: `pago.venta_id` es clave foranea. Si pasa, es mejor
        # dejarlo dicho que seguir de largo.
        raise EventoIlegible(f"El pago {pago.id} no tiene venta.")

    pago.estado = ESTADO_APROBADO
    venta.estado = ESTADO_VENTA_PAGADA

    for detalle in ventas_repository.detalles_de(db, venta.id):
        inventario.liberar_de_reserva(
            db,
            variante_id=detalle.variante_id,
            sucursal_id=venta.sucursal_id,
            cantidad=detalle.cantidad,
            usuario_id=None,
            motivo=f"Pago confirmado del pedido {venta.codigo}",
        )
        inventario.descontar_por_venta(
            db,
            variante_id=detalle.variante_id,
            sucursal_id=venta.sucursal_id,
            cantidad=detalle.cantidad,
            usuario_id=None,
            motivo=f"Venta {venta.codigo}",
        )

    _vaciar_carrito(db, venta.cliente_id)


def _vaciar_carrito(db: Session, cliente_id: int | None) -> None:
    """El carrito se vacia ACA, no al confirmar el pedido. **Sin commit.**

    Es la decision de CU-27 y esta escrita en su servicio: si el carrito se
    vaciara al confirmar, un pago que nunca llega dejaria al cliente sin
    carrito y sin compra --- tendria que rearmarlo entero para reintentar ---.
    Mientras el pedido espera pago, el carrito sigue ahi; lo que impide armar
    cinco pedidos es la regla de uno solo pendiente por cliente, no el vaciado.

    Se vacia solo cuando el dinero entro, que es cuando el carrito dejo de
    representar una intencion y paso a ser una compra hecha.

    `cliente_id` puede ser nulo: `venta.cliente_id` lo es en la venta
    presencial de CU-31, que no pasa por aca pero comparte la tabla.
    """
    if cliente_id is None:
        return
    carrito = carrito_repository.obtener_carrito(db, cliente_id)
    if carrito is not None:
        carrito_repository.vaciar(db, carrito.id)


def fabricar_notificacion_simulada(
    *, sesion: str, pedido: str | None, aprobado: bool
) -> tuple[bytes, str | None]:
    """El cuerpo y la firma de una notificacion del proveedor simulado.

    **Firma con el mismo secreto que despues se verifica.** Podria devolver el
    cuerpo sin firmar y que el proveedor lo acepte, pero entonces la ruta de
    simulacion estaria tomando un atajo que el webhook real no tiene, y la
    demostracion mostraria un flujo distinto del que se defiende.

    El identificador del evento se arma con azar y no con un contador: dos
    simulaciones seguidas de la misma sesion tienen que poder distinguirse
    ---una para ver la aprobacion y otra para ver que la repeticion no
    aplica--- y un contador obligaria a guardar estado en alguna parte.
    """
    from app.integrations.pasarela_pago.simulada import TIPO_APROBADO, TIPO_RECHAZADO

    cuerpo_json = json.dumps(
        {
            "id_evento": f"evsim_{secrets.token_hex(8)}",
            "tipo": TIPO_APROBADO if aprobado else TIPO_RECHAZADO,
            "sesion": sesion,
            "pedido": pedido,
        },
        separators=(",", ":"),
    )
    cuerpo = cuerpo_json.encode("utf-8")

    secreto = settings.PAGO_WEBHOOK_SECRET.strip()
    if not secreto:
        # Sin secreto el proveedor simulado no verifica nada (y avisa por el
        # log), asi que no hay firma que mandar.
        return cuerpo, None

    firma = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return cuerpo, firma
