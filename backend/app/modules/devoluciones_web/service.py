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
