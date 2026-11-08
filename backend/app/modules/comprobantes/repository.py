"""
P16 - Mis comprobantes / CU-46  |  capa: repositorio (consultas, sin reglas)

Las dos consultas de «mis comprobantes»: las compras (con su recibo, si ya se
emitió) y las notas de devolución. **Las dos filtran por `cliente_id` en el
WHERE**, y por debajo el RLS las deja ver solo las filas de la empresa de la
sesión: un cliente nunca ve lo de otro, ni lo suyo en otra tienda.

Regla: aquí solo van consultas. Ningún commit.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Sucursal
from app.modules.plataforma.models import ClienteEmpresa
from app.modules.ventas.models import (
    Comprobante,
    DetalleDevolucion,
    DetalleVenta,
    Devolucion,
    Venta,
)


def es_cliente_de_la_tienda(db: Session, cliente_id: int) -> bool:
    """Si el cliente está asociado a la empresa de la sesión (`cliente_empresa`).

    `cliente_empresa` está bajo RLS: la fila solo se ve si es de esta empresa.
    """
    return (
        db.scalar(
            select(func.count())
            .select_from(ClienteEmpresa)
            .where(ClienteEmpresa.cliente_id == cliente_id)
        )
        or 0
    ) > 0


def _filtrar_fechas(consulta: Select, columna, desde: datetime | None, hasta: datetime | None):
    if desde is not None:
        consulta = consulta.where(columna >= desde)
    if hasta is not None:
        # Límite abierto: `hasta` es la medianoche boliviana del día siguiente.
        consulta = consulta.where(columna < hasta)
    return consulta


def _seleccion_compras(cliente_id: int) -> Select:
    return (
        select(
            Venta.id,
            Venta.empresa_id,
            Venta.codigo,
            Venta.estado,
            Venta.canal,
            Venta.modalidad_entrega,
            Venta.total,
            Venta.creado_en,
            Sucursal.nombre.label("sucursal"),
            Comprobante.numero.label("comprobante_numero"),
            Comprobante.emitido_en.label("comprobante_emitido_en"),
        )
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        # LEFT JOIN: la compra que espera pago no tiene comprobante y tiene que
        # aparecer igual.
        .outerjoin(Comprobante, Comprobante.venta_id == Venta.id)
        .where(Venta.cliente_id == cliente_id)
    )


def compras(
    db: Session,
    *,
    cliente_id: int,
    desde: datetime | None,
    hasta: datetime | None,
    estado: str | None,
    limite: int,
) -> tuple[list[Row], int]:
    """Las compras del cliente, de la más nueva a la más vieja, y cuántas hay."""
    consulta = _filtrar_fechas(_seleccion_compras(cliente_id), Venta.creado_en, desde, hasta)
    if estado is not None:
        consulta = consulta.where(Venta.estado == estado)
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = db.execute(
        consulta.order_by(Venta.creado_en.desc(), Venta.id.desc()).limit(limite)
    ).all()
    return list(filas), total


def _valor_devuelto():
    """Lo que valían las prendas devueltas, al precio que se pagaron."""
    return (
        select(
            func.coalesce(
                func.sum(
                    DetalleDevolucion.cantidad
                    * (DetalleVenta.precio_unitario - DetalleVenta.descuento_unitario)
                ),
                0,
            )
        )
        .select_from(DetalleDevolucion)
        .join(
            DetalleVenta,
            (DetalleVenta.venta_id == Devolucion.venta_id)
            & (DetalleVenta.variante_id == DetalleDevolucion.variante_id),
        )
        .where(DetalleDevolucion.devolucion_id == Devolucion.id)
        .correlate(Devolucion)
        .scalar_subquery()
    )


def devoluciones(
    db: Session,
    *,
    cliente_id: int,
    desde: datetime | None,
    hasta: datetime | None,
    estado: str | None,
    limite: int,
) -> tuple[list[Row], int]:
    """Las notas de devolución (y de cambio) de las compras del cliente."""
    consulta = (
        select(
            Devolucion.id,
            Devolucion.empresa_id,
            Devolucion.tipo,
            Devolucion.estado,
            Devolucion.origen,
            Devolucion.creado_en,
            Venta.codigo.label("venta_codigo"),
            Sucursal.nombre.label("sucursal"),
            _valor_devuelto().label("valor_devuelto"),
        )
        .join(Venta, Venta.id == Devolucion.venta_id)
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        .where(Venta.cliente_id == cliente_id)
    )
    consulta = _filtrar_fechas(consulta, Devolucion.creado_en, desde, hasta)
    if estado is not None:
        consulta = consulta.where(Devolucion.estado == estado)
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = db.execute(
        consulta.order_by(Devolucion.creado_en.desc(), Devolucion.id.desc()).limit(limite)
    ).all()
    return list(filas), total


# --------------------------------------------------------------------------
#  La verificación pública (sin cliente: la identifica el token)
# --------------------------------------------------------------------------
def venta_para_verificar(db: Session, venta_id: int) -> Row | None:
    return db.execute(
        select(
            Venta.id,
            Venta.codigo,
            Venta.estado,
            Venta.total,
            Venta.creado_en,
            Comprobante.numero.label("comprobante_numero"),
            Comprobante.emitido_en.label("comprobante_emitido_en"),
        )
        .outerjoin(Comprobante, Comprobante.venta_id == Venta.id)
        .where(Venta.id == venta_id)
    ).first()


def devolucion_para_verificar(db: Session, devolucion_id: int) -> Row | None:
    return db.execute(
        select(
            Devolucion.id,
            Devolucion.tipo,
            Devolucion.estado,
            Devolucion.creado_en,
            Venta.codigo.label("venta_codigo"),
            _valor_devuelto().label("valor_devuelto"),
        )
        .join(Venta, Venta.id == Devolucion.venta_id)
        .where(Devolucion.id == devolucion_id)
    ).first()
