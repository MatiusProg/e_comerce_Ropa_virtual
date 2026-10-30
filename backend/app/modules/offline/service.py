"""
P14 - Offline y sincronización / CU-13 a CU-19  |  capa: servicio

CU-13 Preparar el dispositivo  ->  `paquete_de_mostrador`, `paquete_de_cliente`
CU-17 Sincronizar              ->  `sincronizar`
CU-18 Consultar pendientes     ->  `operaciones_mias` (la cola local la muestra
                                    el dispositivo; acá está lo ya decidido)
CU-19 Atender rechazadas       ->  `operaciones_de_sucursal`, `registrar_devolucion`
CU-14, CU-15 y CU-16 se hacen en el dispositivo y llegan acá por CU-17.

CADA OPERACIÓN VA EN SU PROPIO SAVEPOINT, Y SE CONFIRMA SOLA
------------------------------------------------------------
Un lote trae operaciones independientes: que la tercera se quede sin stock no
puede deshacer las dos primeras, que ya se cobraron y ya se entregaron. Por
eso cada una corre dentro de `begin_nested()` y el lote hace commit después de
cada una: si el servidor se cae a mitad del lote, lo ya decidido queda, y el
dispositivo reintenta el resto sin duplicar nada (el UUID).

QUIÉN LLEGÓ PRIMERO (RN-06)
---------------------------
No hay nada que resolver a mano: el inventario se descuenta con `FOR UPDATE`
(la misma costura de P4 que usa el mostrador), así que la operación que llega
primero al servidor se lleva la unidad y la que llega después encuentra el
saldo en cero y queda RECHAZADA con el motivo. Si se cobró, se marca para
devolver (CU-19). Se decide con la llegada al servidor y no con la hora del
dispositivo, que es un reloj que nadie controla.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenencia import empresa_actual
from app.modules.caja import repository as caja_repository
from app.modules.catalogo import promociones_service as promociones
from app.modules.inventario import service as inventario
from app.modules.notificaciones import service as notificaciones
from app.modules.offline import repository
from app.modules.offline.models import OperacionOffline
from app.modules.offline.schemas import (
    ClienteOfflineOut,
    DevolucionIn,
    DisponibleEnSucursalOut,
    LoteIn,
    LoteOut,
    OperacionOfflineIn,
    OperacionOut,
    PaqueteDeClienteOut,
    PaqueteDeMostradorOut,
    PrendaOfflineOut,
    PrendaParaReservarOut,
    ResultadoOut,
    SucursalOfflineOut,
)
from app.modules.pos import repository as pos_repository
from app.modules.pos import service as pos_service
from app.modules.reservas import repository as reservas_repository
from app.modules.reservas import service as reservas_service
from app.modules.reservas.schemas import LineaReservaIn, ReservaCrearIn
from app.modules.ventas import historial_service
from app.modules.ventas.models import Venta

CERO = Decimal("0.00")

#: Los roles del personal que trabajan en un mostrador.
ROLES_DE_MOSTRADOR = ("CAJERO", "ENCARGADO")


class ErrorOffline(Exception):
    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class Rechazo(Exception):
    """La operación no se puede confirmar. No es un error del pedido: es un
    resultado, y se guarda con su motivo."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo[:300]


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _vigencia(generado: datetime) -> datetime:
    return generado + timedelta(hours=settings.OFFLINE_VIGENCIA_HORAS)


def _sucursal_out(sucursal) -> SucursalOfflineOut:
    return SucursalOfflineOut(
        id=sucursal.id,
        nombre=sucursal.nombre,
        horario_apertura=sucursal.horario_apertura.strftime("%H:%M"),
        horario_cierre=sucursal.horario_cierre.strftime("%H:%M"),
    )


# =====================================================================
# CU-13 Preparar el dispositivo para trabajar offline
# =====================================================================

def paquete_de_mostrador(db: Session, usuario_id: int) -> PaqueteDeMostradorOut:
    """Lo que el cajero descarga antes de quedarse sin red.

    Exige el turno abierto, igual que cobrar en línea: toda venta presencial
    cuelga de un turno (CHECK `ck_venta_turno_segun_canal`), y la venta
    offline también. El turno que se descarga es al que se van a imputar.
    """
    try:
        mostrador = pos_service.mostrador_de(db, usuario_id)
    except pos_service.SinTurnoAbierto as e:
        raise ErrorOffline(
            "Abra su turno de caja antes de preparar el dispositivo: las ventas "
            "sin conexión se cargan a ese turno.",
            409,
        ) from e

    filas = repository.prendas_de_sucursal(db, mostrador.sucursal_id)
    descuentos = promociones.descuentos_por_variante(
        db, {f.variante_id: f.precio for f in filas}
    )
    generado = _ahora()
    return PaqueteDeMostradorOut(
        generado_en=generado,
        vigente_hasta=_vigencia(generado),
        empresa_id=empresa_actual(db),
        usuario_id=usuario_id,
        sucursal=_sucursal_out(repository.sucursal(db, mostrador.sucursal_id)),
        turno_caja_id=mostrador.turno_id,
        caja_nombre=mostrador.caja_nombre,
        prendas=[
            PrendaOfflineOut(
                variante_id=f.variante_id,
                sku=f.sku,
                producto=f.producto,
                talla=f.talla,
                color=f.color,
                precio=f.precio,
                descuento=promociones.a_contrato(descuentos.get(f.variante_id)),
                disponible=f.disponible,
            )
            for f in filas
        ],
        clientes=[
            ClienteOfflineOut(
                id=c.id,
                nombre=f"{c.nombres} {c.apellidos}".strip(),
                documento=c.documento,
            )
            for c in repository.clientes_de_la_empresa(db)
        ],
    )


def paquete_de_cliente(db: Session) -> PaqueteDeClienteOut:
    """Lo que el cliente descarga al móvil para reservar sin conexión (CU-15)."""
    sucursales = repository.sucursales_activas(db)
    prendas: dict[int, PrendaParaReservarOut] = {}
    for f in repository.prendas_en_sucursales_activas(db):
        prenda = prendas.get(f.variante_id)
        if prenda is None:
            prenda = prendas[f.variante_id] = PrendaParaReservarOut(
                variante_id=f.variante_id,
                sku=f.sku,
                producto=f.producto,
                talla=f.talla,
                color=f.color,
                precio=f.precio,
                sucursales=[],
            )
        prenda.sucursales.append(
            DisponibleEnSucursalOut(sucursal_id=f.sucursal_id, disponible=f.disponible)
        )
    generado = _ahora()
    return PaqueteDeClienteOut(
        generado_en=generado,
        vigente_hasta=_vigencia(generado),
        empresa_id=empresa_actual(db),
        sucursales=[_sucursal_out(s) for s in sucursales],
        prendas=list(prendas.values()),
    )


# =====================================================================
# CU-17 Sincronizar operaciones pendientes
# =====================================================================

def sincronizar(
    db: Session, *, usuario_id: int, rol: str, sucursal_del_usuario: int | None, lote: LoteIn
) -> LoteOut:
    """Decide cada operación del lote. **Hace commit por operación.**"""
    resultados: list[ResultadoOut] = []
    for operacion in lote.operaciones:
        resultados.append(
            _sincronizar_una(
                db,
                operacion,
                usuario_id=usuario_id,
                rol=rol,
                sucursal_del_usuario=sucursal_del_usuario,
                dispositivo=lote.dispositivo,
            )
        )
    return LoteOut(
        resultados=resultados,
        confirmadas=sum(r.estado == "CONFIRMADA" for r in resultados),
        rechazadas=sum(r.estado == "RECHAZADA" for r in resultados),
    )


def _sincronizar_una(
    db: Session,
    op: OperacionOfflineIn,
    *,
    usuario_id: int,
    rol: str,
    sucursal_del_usuario: int | None,
    dispositivo: str | None,
) -> ResultadoOut:
    # RNF05: si ya llegó, se devuelve lo que se decidió la primera vez.
    previa = repository.operacion_por_uuid(db, op.uuid, bloquear=True)
    if previa is not None:
        if previa.usuario_id != usuario_id:
            # Un UUID ajeno no se revela: es otra persona, quizá de otra
            # sucursal. Se rechaza sin decir qué había.
            raise ErrorOffline("Esa operación no es suya.", 409)
        previa.intentos += 1
        db.commit()
        return _resultado(db, previa, repetida=True)

    fila = OperacionOffline(
        uuid=op.uuid,
        tipo=op.tipo,
        usuario_id=usuario_id,
        dispositivo=dispositivo,
        creada_en_cliente=op.creada_en,
        metodo_pago=op.pago.metodo if op.pago else None,
        monto_cobrado=op.pago.monto if op.pago else None,
        referencia_pago=(op.pago.referencia or None) if op.pago else None,
        carga=op.model_dump(mode="json"),
    )

    punto = db.begin_nested()
    try:
        if op.tipo == "VENTA":
            fila.sucursal_id, fila.venta_id = _confirmar_venta(db, op, usuario_id=usuario_id)
        else:
            fila.sucursal_id, fila.reserva_id = _confirmar_reserva(
                db,
                op,
                usuario_id=usuario_id,
                rol=rol,
                sucursal_del_usuario=sucursal_del_usuario,
            )
        fila.estado = "CONFIRMADA"
    except Rechazo as r:
        punto.rollback()
        fila.estado = "RECHAZADA"
        fila.motivo_rechazo = r.motivo
        fila.venta_id = fila.reserva_id = None
        # La sucursal de una operación rechazada también se registra: es la
        # que va a atender la devolución (CU-19).
        fila.sucursal_id = _sucursal_declarada(
            db, op, usuario_id=usuario_id, sucursal_del_usuario=sucursal_del_usuario
        )
    else:
        punto.commit()

    db.add(fila)
    try:
        db.commit()
    except IntegrityError:
        # Dos pedidos con el mismo UUID a la vez: el otro ganó el UNIQUE.
        # Lo que hizo este se deshace entero y se devuelve lo del otro.
        db.rollback()
        previa = repository.operacion_por_uuid(db, op.uuid)
        if previa is None or previa.usuario_id != usuario_id:  # pragma: no cover
            raise
        return _resultado(db, previa, repetida=True)
    db.refresh(fila)
    return _resultado(db, fila, repetida=False)


def _sucursal_declarada(
    db: Session, op: OperacionOfflineIn, *, usuario_id: int, sucursal_del_usuario: int | None
) -> int:
    """La sucursal de una operación rechazada, sin confiar en lo que llegó.

    Si no hay ninguna que se pueda comprobar, el pedido mismo está mal
    formado y se responde con error en vez de guardar una fila sin sucursal.
    """
    if op.tipo == "VENTA" and op.turno_caja_id is not None:
        turno = caja_repository.turno_por_id(db, op.turno_caja_id)
        if turno is not None and turno.usuario_id == usuario_id:
            caja = caja_repository.caja_por_id(db, turno.caja_id)
            if caja is not None:
                return caja.sucursal_id
    if sucursal_del_usuario is not None:
        return sucursal_del_usuario
    if op.sucursal_id is not None and repository.sucursal(db, op.sucursal_id) is not None:
        return op.sucursal_id
    raise ErrorOffline("La operación no dice de qué sucursal es.", 422)


def _confirmar_venta(
    db: Session, op: OperacionOfflineIn, *, usuario_id: int
) -> tuple[int, int]:
    """CU-14 confirmada en el servidor. Devuelve (sucursal, venta).

    Es la venta del mostrador (CU-31) con dos diferencias, las dos porque el
    cliente ya pagó y ya se fue con la prenda:
      - el precio es el que se cobró, no el de hoy;
      - si algo no cuadra, no se le pide al cajero que corrija: se rechaza.
    """
    turno = caja_repository.turno_por_id(db, op.turno_caja_id)
    if turno is None or turno.usuario_id != usuario_id:
        raise Rechazo("El turno de caja de la venta no es suyo.")
    caja = caja_repository.caja_por_id(db, turno.caja_id)
    # Se acepta aunque el turno ya se haya cerrado: el dinero entró a esa
    # caja mientras estaba abierta. Cómo entra al arqueo es del CU-20.
    sucursal_id = caja.sucursal_id

    prendas = pos_repository.prendas_por_id(
        db, variante_ids=[l.variante_id for l in op.lineas], sucursal_id=sucursal_id
    )
    faltantes = [l.variante_id for l in op.lineas if l.variante_id not in prendas]
    if faltantes:
        raise Rechazo("Alguna de las prendas ya no se vende en esta sucursal.")

    subtotal = sum((l.precio_unitario * l.cantidad for l in op.lineas), CERO)
    descuento = sum((l.descuento_unitario * l.cantidad for l in op.lineas), CERO)
    total = subtotal - descuento

    pago = op.pago
    if pago.metodo == "EFECTIVO" and pago.monto < total:
        raise Rechazo(f"Se cobraron Bs {pago.monto} y el total es Bs {total}.")
    if pago.metodo == "QR" and pago.monto != total:
        raise Rechazo(f"El QR fue por Bs {pago.monto} y el total es Bs {total}.")

    codigo = pos_service.generar_codigo_de_venta(db)
    venta = pos_repository.agregar_venta_presencial(
        db,
        codigo=codigo,
        cliente_id=None,
        sucursal_id=sucursal_id,
        turno_caja_id=turno.id,
        reserva_id=None,
        metodo_pago=pago.metodo,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
    )
    for linea in op.lineas:
        pos_repository.agregar_detalle(
            db,
            venta_id=venta.id,
            variante_id=linea.variante_id,
            cantidad=linea.cantidad,
            precio_unitario=linea.precio_unitario,
            descuento_unitario=linea.descuento_unitario,
        )
        try:
            inventario.descontar_por_venta(
                db,
                variante_id=linea.variante_id,
                sucursal_id=sucursal_id,
                cantidad=linea.cantidad,
                usuario_id=usuario_id,
                motivo=f"Venta {codigo} sin conexión",
            )
        except inventario.StockInsuficiente as e:
            nombre = " · ".join(
                p
                for p in (
                    prendas[linea.variante_id].producto,
                    prendas[linea.variante_id].talla,
                    prendas[linea.variante_id].color,
                )
                if p
            )
            raise Rechazo(
                f"Ya no alcanza «{nombre}»: quedan {e.disponible} y se vendieron "
                f"{linea.cantidad} sin conexión. Otra venta llegó primero."
            ) from e
    historial_service.asegurar_comprobante(db, venta)
    return sucursal_id, venta.id


def _confirmar_reserva(
    db: Session,
    op: OperacionOfflineIn,
    *,
    usuario_id: int,
    rol: str,
    sucursal_del_usuario: int | None,
) -> tuple[int, int]:
    """CU-15 confirmada en el servidor. Devuelve (sucursal, reserva).

    Pasa por las mismas reglas que la reserva en línea (CU-22): horario,
    probadores libres, anticipación y stock. Una reserva hecha sin conexión
    para una franja que ya pasó cuando se sincronizó se rechaza igual.
    """
    if rol in ROLES_DE_MOSTRADOR:
        if sucursal_del_usuario is None:
            raise Rechazo("Su cuenta no está asignada a ninguna sucursal.")
        if op.sucursal_id is not None and op.sucursal_id != sucursal_del_usuario:
            raise Rechazo("Solo puede reservar en su propia sucursal.")
        sucursal_id = sucursal_del_usuario
        if op.cliente_id is None or not repository.cliente_de_la_empresa(db, op.cliente_id):
            raise Rechazo("La reserva no tiene un cliente de esta tienda.")
        cliente_id = op.cliente_id
    else:
        cliente = reservas_repository.obtener_cliente_de_usuario(db, usuario_id)
        if cliente is None:
            raise Rechazo("Su cuenta no tiene una ficha de cliente.")
        if op.sucursal_id is None:
            raise Rechazo("La reserva no dice en qué sucursal.")
        sucursal_id = op.sucursal_id
        cliente_id = cliente.id

    datos = ReservaCrearIn(
        sucursal_id=sucursal_id,
        franja_inicio=op.franja_inicio,
        franja_fin=op.franja_fin,
        lineas=[
            LineaReservaIn(variante_id=l.variante_id, cantidad=l.cantidad)
            for l in op.lineas
        ],
    )
    try:
        reserva = reservas_service.registrar_reserva(
            db, datos, cliente_id=cliente_id, usuario_id=usuario_id
        )
    except (reservas_service.ErrorDeReservas, inventario.ErrorDeInventario) as e:
        # Los mismos mensajes que ve quien reserva en línea.
        from app.modules.reservas.router import _traducir

        raise Rechazo(str(_traducir(e).detail)) from e

    notificaciones.avisar_reserva_en_sucursal(db, reserva)
    return sucursal_id, reserva.id


def _resultado(db: Session, fila: OperacionOffline, *, repetida: bool) -> ResultadoOut:
    venta_codigo = None
    if fila.venta_id is not None:
        venta = db.get(Venta, fila.venta_id)
        venta_codigo = venta.codigo if venta else None
    return ResultadoOut(
        uuid=fila.uuid,
        tipo=fila.tipo,
        estado=fila.estado,
        motivo=fila.motivo_rechazo,
        venta_codigo=venta_codigo,
        reserva_id=fila.reserva_id,
        requiere_devolucion=_por_devolver(fila),
        devuelta=fila.devuelto_en is not None,
        repetida=repetida,
        recibida_en=fila.recibida_en,
    )


def _por_devolver(fila: OperacionOffline) -> bool:
    return (
        fila.estado == "RECHAZADA"
        and fila.monto_cobrado is not None
        and fila.devuelto_en is None
    )


# =====================================================================
# CU-18 Consultar operaciones pendientes  /  CU-19 Atender rechazadas
# =====================================================================

def _operacion_out(db: Session, fila: OperacionOffline, usuario) -> OperacionOut:
    base = _resultado(db, fila, repetida=False)
    return OperacionOut(
        **base.model_dump(),
        sucursal_id=fila.sucursal_id,
        usuario=f"{usuario.nombres} {usuario.apellidos}".strip(),
        creada_en_cliente=fila.creada_en_cliente,
        intentos=fila.intentos,
        metodo_pago=fila.metodo_pago,
        monto_cobrado=fila.monto_cobrado,
        referencia_pago=fila.referencia_pago,
        devuelto_en=fila.devuelto_en,
        metodo_devolucion=fila.metodo_devolucion,
        referencia_devolucion=fila.referencia_devolucion,
    )


def operaciones_mias(
    db: Session, usuario_id: int, *, estado: str | None
) -> list[OperacionOut]:
    """Lo que este usuario ya sincronizó, con lo que decidió el servidor."""
    return [
        _operacion_out(db, fila, usuario)
        for fila, usuario in repository.operaciones(db, usuario_id=usuario_id, estado=estado)
    ]


def operaciones_de_sucursal(
    db: Session, sucursal_id: int | None, *, estado: str | None, por_devolver: bool
) -> list[OperacionOut]:
    """Las de la sucursal del encargado; `None` = todas (el administrador)."""
    return [
        _operacion_out(db, fila, usuario)
        for fila, usuario in repository.operaciones(
            db, sucursal_id=sucursal_id, estado=estado, por_devolver=por_devolver
        )
    ]


def registrar_devolucion(
    db: Session,
    uuid,
    datos: DevolucionIn,
    *,
    usuario_id: int,
    sucursal_id: int | None,
) -> OperacionOut:
    """CU-19: el encargado le devolvió al cliente lo que pagó. **Hace commit.**

    EL ARQUEO NO SE DESCUADRA
    -------------------------
    Una venta rechazada no dejó fila en `venta`, así que el arqueo del turno
    nunca contó ese dinero, aunque el billete sí está en el cajón. Al
    devolverlo, el cajón vuelve a coincidir con el arqueo. Por eso no se
    escribe ningún movimiento de caja: escribirlo descontaría dos veces.
    """
    fila = repository.operacion_por_uuid(db, uuid, bloquear=True)
    if fila is None or (sucursal_id is not None and fila.sucursal_id != sucursal_id):
        raise ErrorOffline("No existe esa operación en su sucursal.", 404)
    if fila.estado != "RECHAZADA":
        raise ErrorOffline("La operación se confirmó: no hay nada que devolver.", 409)
    if fila.monto_cobrado is None:
        raise ErrorOffline("La operación no se había cobrado: no hay nada que devolver.", 409)
    if fila.devuelto_en is not None:
        raise ErrorOffline("Esa devolución ya se registró.", 409)

    fila.devuelto_en = _ahora()
    fila.devuelto_por = usuario_id
    fila.metodo_devolucion = datos.metodo
    fila.referencia_devolucion = (datos.referencia or "").strip() or None
    fila.observacion_devolucion = (datos.observacion or "").strip() or None
    db.commit()
    db.refresh(fila)
    from app.modules.seguridad.models import Usuario

    return _operacion_out(db, fila, db.get(Usuario, fila.usuario_id))
