"""
P15 - Devoluciones por la web / CU-24  |  capa: servicio (la clase control)

  Precondición  `pedidos_de_sucursal`, `entregar`   (el encargado entrega)
  CU-24         `pedido_devolvible`, `solicitar`, `mis_solicitudes`
  CU-25         `solicitudes_de_sucursal` (la lista; atender va en CU-25)

LA VENTANA CORRE DESDE LA ENTREGA (RF-35)
-----------------------------------------
No desde la compra: un pedido por envío puede tardar días en llegar, y el
cliente no puede devolver lo que todavía no tiene. Por eso hace falta que el
encargado marque la entrega, y `venta.entregado_en` es el reloj.

LO QUE SE PUEDE PEDIR
---------------------
Lo vendido, menos lo que ya volvió (CU-22, en caja) y menos lo que ya está
pedido en otra solicitud abierta. Sin eso, el cliente podría pedir dos veces la
devolución de la misma prenda mientras el encargado no atiende la primera.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.devoluciones_web import repository
from app.modules.devoluciones_web.models import (
    LineaSolicitudDevolucion,
    SolicitudDevolucion,
)
from app.modules.devoluciones_web.schemas import (
    LineaDevolvibleWebOut,
    LineaSolicitudOut,
    OpcionDeCambioOut,
    PedidoDeSucursalOut,
    PedidoDevolvibleOut,
    SolicitudIn,
    SolicitudOut,
)
from app.modules.pos import devolucion_repository as devoluciones
from app.modules.pos.devolucion_service import ventana_en_horas
from app.modules.reservas import repository as reservas_repository

CERO = Decimal("0.00")


class ErrorDevolucionWeb(Exception):
    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _cliente_id(db: Session, usuario_id: int) -> int:
    cliente = reservas_repository.obtener_cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise ErrorDevolucionWeb("Su cuenta no tiene una ficha de cliente.", 403)
    return cliente.id


def _aware(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


# =====================================================================
# Precondición: el encargado entrega el pedido
# =====================================================================

def pedidos_de_sucursal(
    db: Session, *, sucursal_id: int | None, estado: str | None
) -> list[PedidoDeSucursalOut]:
    return [
        PedidoDeSucursalOut(**f._mapping)
        for f in repository.pedidos_digitales(db, sucursal_id=sucursal_id, estado=estado)
    ]


def entregar(db: Session, codigo: str, *, sucursal_id: int | None) -> PedidoDeSucursalOut:
    """PAGADA -> ENTREGADA, con la hora. Desde acá corre la ventana. **Commit.**"""
    venta = repository.venta_digital(db, codigo, bloquear=True)
    if venta is None or (sucursal_id is not None and venta.sucursal_id != sucursal_id):
        raise ErrorDevolucionWeb("No hay un pedido con ese código en su sucursal.", 404)
    if venta.estado == "ENTREGADA":
        raise ErrorDevolucionWeb("Ese pedido ya se entregó.", 409)
    if venta.estado != "PAGADA":
        raise ErrorDevolucionWeb("Solo se entrega un pedido pagado.", 409)
    venta.estado = "ENTREGADA"
    venta.entregado_en = tiempo.ahora()
    db.commit()
    [fila] = repository.pedidos_digitales(db, sucursal_id=None, estado=None, codigo=codigo)
    return PedidoDeSucursalOut(**fila._mapping)


# =====================================================================
# CU-24: lo que se puede pedir, y pedirlo
# =====================================================================

def _venta_del_cliente(db: Session, codigo: str, cliente_id: int):
    venta = repository.venta_digital(db, codigo)
    if venta is None or venta.cliente_id != cliente_id:
        raise ErrorDevolucionWeb("No tiene un pedido con ese código.", 404)
    if venta.estado != "ENTREGADA" or venta.entregado_en is None:
        raise ErrorDevolucionWeb(
            "Solo se puede pedir el cambio o la devolución de un pedido ya entregado.", 409
        )
    return venta


def _plazo(db: Session, venta) -> tuple[int, datetime, bool]:
    horas = ventana_en_horas(db)
    vence = _aware(venta.entregado_en) + timedelta(hours=horas)
    return horas, vence, tiempo.ahora() <= vence


def _comprometidas(db: Session, venta_id: int) -> dict[int, int]:
    """Lo que ya volvió más lo pedido en solicitudes abiertas, por variante."""
    total = dict(devoluciones.ya_devuelto(db, venta_id))
    for variante, cantidad in repository.pedido_en_solicitudes_abiertas(db, venta_id).items():
        total[variante] = total.get(variante, 0) + cantidad
    return total


def pedido_devolvible(db: Session, usuario_id: int, codigo: str) -> PedidoDevolvibleOut:
    cliente_id = _cliente_id(db, usuario_id)
    venta = _venta_del_cliente(db, codigo, cliente_id)
    horas, vence, dentro = _plazo(db, venta)
    comprometidas = _comprometidas(db, venta.id)
    lineas = []
    for f in devoluciones.lineas_vendidas(db, venta.id):
        ya = comprometidas.get(f.variante_id, 0)
        lineas.append(
            LineaDevolvibleWebOut(
                variante_id=f.variante_id,
                sku=f.sku,
                producto=f.producto,
                talla=f.talla,
                color=f.color,
                vendidas=f.cantidad,
                comprometidas=ya,
                devolvibles=max(0, f.cantidad - ya),
                precio_pagado=f.precio_unitario - f.descuento_unitario,
                opciones_de_cambio=[
                    OpcionDeCambioOut(**o._mapping)
                    for o in repository.opciones_de_cambio(
                        db, variante_id=f.variante_id, sucursal_id=venta.sucursal_id
                    )
                ],
            )
        )
    return PedidoDevolvibleOut(
        codigo=venta.codigo,
        sucursal=repository.nombre_de_sucursal(db, venta.sucursal_id),
        entregado_en=venta.entregado_en,
        ventana_horas=horas,
        vence_en=vence,
        dentro_de_plazo=dentro,
        lineas=lineas,
    )


def solicitar(db: Session, usuario_id: int, datos: SolicitudIn) -> SolicitudOut:
    """CU-24. Valida todo antes de escribir y deja la solicitud PENDIENTE. **Commit.**"""
    cliente_id = _cliente_id(db, usuario_id)
    venta = _venta_del_cliente(db, datos.venta_codigo, cliente_id)
    # Serializa las solicitudes de este pedido: dos a la vez leerían lo mismo
    # comprometido y las dos se llevarían la última unidad.
    repository.venta_digital(db, venta.codigo, bloquear=True)

    horas, vence, dentro = _plazo(db, venta)
    if not dentro:
        # RN-08: fuera de la ventana se rechaza.
        raise ErrorDevolucionWeb(
            f"El plazo para pedir un cambio o una devolución es de {horas} horas desde "
            f"la entrega, y venció el {tiempo.en_bolivia(vence):%d/%m/%Y a las %H:%M}.",
            409,
        )

    vendidas = {f.variante_id: f for f in devoluciones.lineas_vendidas(db, venta.id)}
    comprometidas = _comprometidas(db, venta.id)
    for linea in datos.lineas:
        fila = vendidas.get(linea.variante_id)
        if fila is None:
            raise ErrorDevolucionWeb("Alguna de las prendas no está en ese pedido.", 422)
        libres = fila.cantidad - comprometidas.get(linea.variante_id, 0)
        if linea.cantidad > libres:
            raise ErrorDevolucionWeb(
                f"De «{fila.producto} {fila.talla} {fila.color}» puede pedir hasta {libres}:"
                " el resto ya volvió o ya está pedido.",
                409,
            )
        if linea.variante_nueva_id is not None:
            opciones = {
                o.variante_id
                for o in repository.opciones_de_cambio(
                    db, variante_id=linea.variante_id, sucursal_id=venta.sucursal_id
                )
            }
            if linea.variante_nueva_id not in opciones:
                raise ErrorDevolucionWeb(
                    "La prenda que eligió a cambio no es el mismo producto, o no hay en la"
                    " sucursal del pedido.",
                    422,
                )

    solicitud = SolicitudDevolucion(
        venta_id=venta.id,
        cliente_id=cliente_id,
        sucursal_id=venta.sucursal_id,
        tipo=datos.tipo,
        motivo=datos.motivo.strip(),
        lineas=[
            LineaSolicitudDevolucion(
                variante_id=l.variante_id,
                cantidad=l.cantidad,
                variante_nueva_id=l.variante_nueva_id,
            )
            for l in datos.lineas
        ],
    )
    db.add(solicitud)
    db.commit()
    return solicitud_out(db, solicitud.id)


# =====================================================================
# Consultas
# =====================================================================

def solicitud_out(db: Session, solicitud_id: int) -> SolicitudOut:
    cabecera = repository.cabecera_de_solicitud(db, solicitud_id)
    vendidas = {f.variante_id: f for f in devoluciones.lineas_vendidas(db, cabecera.venta_id)}
    lineas: list[LineaSolicitudOut] = []
    valor_devuelto = CERO
    valor_nuevo = CERO
    for l in repository.lineas_de_solicitud(db, solicitud_id):
        f = vendidas[l.variante_id]
        pagado = f.precio_unitario - f.descuento_unitario
        valor_devuelto += pagado * l.cantidad
        if l.precio_nuevo is not None:
            valor_nuevo += l.precio_nuevo * l.cantidad
        lineas.append(
            LineaSolicitudOut(
                variante_id=l.variante_id,
                sku=f.sku,
                producto=f.producto,
                talla=f.talla,
                color=f.color,
                cantidad=l.cantidad,
                precio_pagado=pagado,
                variante_nueva_id=l.variante_nueva_id,
                talla_nueva=l.talla_nueva,
                color_nueva=l.color_nueva,
                precio_nuevo=l.precio_nuevo,
            )
        )
    es_cambio = cabecera.tipo == "CAMBIO"
    return SolicitudOut(
        id=cabecera.id,
        venta_codigo=cabecera.venta_codigo,
        sucursal=cabecera.sucursal,
        cliente=cabecera.cliente,
        tipo=cabecera.tipo,
        estado=cabecera.estado,
        motivo=cabecera.motivo,
        respuesta=cabecera.respuesta,
        creado_en=cabecera.creado_en,
        atendida_en=cabecera.atendida_en,
        lineas=lineas,
        valor_devuelto=valor_devuelto,
        valor_nuevo=valor_nuevo if es_cambio else None,
        diferencia=(valor_nuevo - valor_devuelto) if es_cambio else None,
        devolucion_id=cabecera.devolucion_id,
        numero_nota=f"ND-{cabecera.devolucion_id:06d}" if cabecera.devolucion_id else None,
        nota_estado=cabecera.nota_estado,
        conforme=cabecera.conforme,
        reembolso_monto=cabecera.reembolso_monto,
        reembolso_referencia=cabecera.reembolso_referencia,
    )


def mis_solicitudes(db: Session, usuario_id: int) -> list[SolicitudOut]:
    cliente_id = _cliente_id(db, usuario_id)
    return [solicitud_out(db, i) for i in repository.ids_de_solicitudes(db, cliente_id=cliente_id)]


def solicitudes_de_sucursal(
    db: Session, *, sucursal_id: int | None, estado: str | None
) -> list[SolicitudOut]:
    return [
        solicitud_out(db, i)
        for i in repository.ids_de_solicitudes(db, sucursal_id=sucursal_id, estado=estado)
    ]


# =====================================================================
# CU-25 Atender solicitud de devolución (encargado)
# =====================================================================
#
#   aprobar / rechazar   PENDIENTE -> APROBADA | RECHAZADA (con el motivo)
#   recibir              DEVOLUCION APROBADA -> COMPLETADA: entra la prenda,
#                        se reembolsa por la pasarela y nace la nota ABIERTA
#   (caja, CU-22)        CAMBIO APROBADO -> COMPLETADA al retirarlo en caja,
#                        que salda la diferencia (`completar_con`)
#   conformidad          el cliente cierra la nota (RN-20)


def _solicitud_de_sucursal(db: Session, solicitud_id: int, sucursal_id: int | None):
    solicitud = repository.solicitud(db, solicitud_id, bloquear=True)
    if solicitud is None or (sucursal_id is not None and solicitud.sucursal_id != sucursal_id):
        raise ErrorDevolucionWeb("No existe esa solicitud en su sucursal.", 404)
    return solicitud


def aprobar(
    db: Session, solicitud_id: int, *, usuario_id: int, sucursal_id: int | None,
    respuesta: str | None,
) -> SolicitudOut:
    """RF-36. Una DEVOLUCIÓN aprobada espera la prenda; un CAMBIO, que el
    cliente lo retire en caja. **Commit.**"""
    solicitud = _solicitud_de_sucursal(db, solicitud_id, sucursal_id)
    if solicitud.estado != "PENDIENTE":
        raise ErrorDevolucionWeb("Esa solicitud ya se atendió.", 409)
    solicitud.estado = "APROBADA"
    solicitud.respuesta = (respuesta or "").strip() or None
    solicitud.atendida_por = usuario_id
    solicitud.atendida_en = tiempo.ahora()
    db.commit()
    return solicitud_out(db, solicitud.id)


def rechazar(
    db: Session, solicitud_id: int, *, usuario_id: int, sucursal_id: int | None,
    respuesta: str | None,
) -> SolicitudOut:
    """RF-36: el rechazo dice por qué. Las unidades vuelven a poder pedirse. **Commit.**"""
    motivo = (respuesta or "").strip()
    if len(motivo) < 5:
        raise ErrorDevolucionWeb("Diga por qué se rechaza (al menos 5 letras).", 422)
    solicitud = _solicitud_de_sucursal(db, solicitud_id, sucursal_id)
    if solicitud.estado != "PENDIENTE":
        raise ErrorDevolucionWeb("Esa solicitud ya se atendió.", 409)
    solicitud.estado = "RECHAZADA"
    solicitud.respuesta = motivo
    solicitud.atendida_por = usuario_id
    solicitud.atendida_en = tiempo.ahora()
    db.commit()
    return solicitud_out(db, solicitud.id)


def recibir(
    db: Session, solicitud_id: int, *, usuario_id: int, sucursal_id: int | None
) -> SolicitudOut:
    """La prenda de una DEVOLUCIÓN aprobada llegó a la sucursal. **Commit.**

    En una sola transacción: la nota (ABIERTA, origen WEB, sin turno: no toca
    ningún cajón), sus líneas, el reingreso al inventario y el reembolso por la
    pasarela, por el mismo medio con que se pagó. Si la pasarela falla, no
    queda nada escrito: ni la prenda reingresada ni una nota sin reembolso.
    """
    from app.integrations import pasarela_pago
    from app.integrations.pasarela_pago.base import ErrorDePasarela
    from app.modules.inventario import service as inventario
    from app.modules.pagos.models import Pago
    from app.modules.ventas.models import DetalleDevolucion, Devolucion

    solicitud = _solicitud_de_sucursal(db, solicitud_id, sucursal_id)
    if solicitud.tipo != "DEVOLUCION":
        raise ErrorDevolucionWeb("Un cambio se retira en caja, no se recibe acá.", 409)
    if solicitud.estado != "APROBADA":
        raise ErrorDevolucionWeb("Solo se recibe una devolución aprobada.", 409)

    venta = repository.venta_por_id(db, solicitud.venta_id, bloquear=True)
    vendidas = {f.variante_id: f for f in devoluciones.lineas_vendidas(db, venta.id)}
    ya = devoluciones.ya_devuelto(db, venta.id)
    lineas = list(solicitud.lineas)
    valor = CERO
    for l in lineas:
        fila = vendidas[l.variante_id]
        if l.cantidad > fila.cantidad - ya.get(l.variante_id, 0):
            raise ErrorDevolucionWeb(
                f"De «{fila.producto} {fila.talla}» ya volvió parte en caja: revise la solicitud.",
                409,
            )
        valor += (fila.precio_unitario - fila.descuento_unitario) * l.cantidad

    devolucion = Devolucion(
        venta_id=venta.id,
        turno_caja_id=None,
        origen="WEB",
        recibida_por=usuario_id,
        tipo="DEVOLUCION",
        motivo=f"Pedida por la web: {solicitud.motivo}"[:200],
        monto=CERO,
        estado="ABIERTA",
        conforme=None,
    )
    db.add(devolucion)
    db.flush()
    for l in lineas:
        db.add(
            DetalleDevolucion(
                devolucion_id=devolucion.id, variante_id=l.variante_id, cantidad=l.cantidad
            )
        )
        inventario.reingresar_por_devolucion(
            db,
            variante_id=l.variante_id,
            sucursal_id=venta.sucursal_id,
            cantidad=l.cantidad,
            usuario_id=usuario_id,
            motivo=f"Devolución web de {venta.codigo} (nota {devolucion.numero_nota})"[:200],
        )

    pago = db.query(Pago).filter(Pago.venta_id == venta.id).one_or_none()
    if pago is not None and pago.metodo == "PASARELA" and pago.referencia_externa:
        try:
            devolucion.reembolso_referencia = pasarela_pago.reembolsar(
                pago.referencia_externa, valor, clave=f"devolucion-web-{solicitud.id}"
            )
        except ErrorDePasarela as e:
            db.rollback()
            raise ErrorDevolucionWeb(
                f"La pasarela no pudo hacer el reembolso; no se registró nada. Detalle: {e}",
                502,
            ) from e
        devolucion.reembolso_monto = valor

    solicitud.estado = "COMPLETADA"
    solicitud.devolucion_id = devolucion.id
    db.commit()
    return solicitud_out(db, solicitud.id)


# --- Lo usa la caja (CU-22) para el cambio aprobado ---------------------------

def cambio_aprobado_de(db: Session, venta_id: int):
    """La solicitud de CAMBIO aprobada de esta venta, si la hay."""
    return repository.cambio_aprobado(db, venta_id)


def completar_con(db: Session, solicitud, devolucion_id: int) -> None:
    """El cambio se hizo en caja: la solicitud queda COMPLETADA. **Sin commit.**"""
    solicitud.estado = "COMPLETADA"
    solicitud.devolucion_id = devolucion_id


# --- El cliente cierra la nota (RN-20) -----------------------------------------

def conformidad(
    db: Session, usuario_id: int, solicitud_id: int, *, conforme: bool, observacion: str | None
) -> SolicitudOut:
    """Conforme cierra la nota. No conforme la deja ABIERTA con la observación,
    a la vista del encargado: sin conformidad, la nota no se cierra. **Commit.**"""
    from app.modules.ventas.models import Devolucion

    cliente_id = _cliente_id(db, usuario_id)
    solicitud = repository.solicitud(db, solicitud_id, bloquear=True)
    if solicitud is None or solicitud.cliente_id != cliente_id:
        raise ErrorDevolucionWeb("No tiene esa solicitud.", 404)
    if solicitud.devolucion_id is None:
        raise ErrorDevolucionWeb("Todavía no hay una nota que confirmar.", 409)
    devolucion = db.get(Devolucion, solicitud.devolucion_id)
    if devolucion.estado == "CERRADA":
        raise ErrorDevolucionWeb("La nota ya está cerrada.", 409)
    devolucion.conforme = conforme
    devolucion.observacion_cliente = (observacion or "").strip() or None
    if conforme:
        devolucion.estado = "CERRADA"
    db.commit()
    return solicitud_out(db, solicitud.id)


def nota_del_cliente(db: Session, usuario_id: int, solicitud_id: int):
    from app.modules.pos import devolucion_service

    cliente_id = _cliente_id(db, usuario_id)
    solicitud = repository.solicitud(db, solicitud_id)
    if solicitud is None or solicitud.cliente_id != cliente_id or solicitud.devolucion_id is None:
        raise ErrorDevolucionWeb("No hay una nota para esa solicitud.", 404)
    return devolucion_service.nota(db, solicitud.devolucion_id, sucursal_id=None)
