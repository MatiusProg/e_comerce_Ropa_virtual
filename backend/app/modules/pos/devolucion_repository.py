"""
P7 - Punto de Venta / CU-32  |  capa: repositorio (consultas, sin logica ni commit)
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.ventas.models import (
    DetalleDevolucion,
    DetalleVenta,
    Devolucion,
    Venta,
)


def venta_devolvible(db: Session, *, codigo: str, sucursal_id: int) -> Venta | None:
    """La venta que se puede devolver, si es de esta sucursal.

    Se acota a PAGADA y ENTREGADA: una venta `PENDIENTE_PAGO` no se cobro y una
    `CANCELADA` ya se deshizo. Devolver cualquiera de las dos seria sacar
    mercaderia y plata contra una venta que no ocurrio.

    El `sucursal_id` va en el WHERE: una venta de otra sucursal no existe para
    este cajero --- convencion 1 ---.
    """
    return db.scalar(
        select(Venta).where(
            Venta.codigo == codigo,
            Venta.sucursal_id == sucursal_id,
            Venta.estado.in_(("PAGADA", "ENTREGADA")),
        )
    )


def lineas_vendidas(db: Session, venta_id: int) -> list[Row]:
    """Que se vendio, con la prenda resuelta y el precio CONGELADO.

    Lee `detalle_venta.precio_unitario` y no `variante_producto.precio`: se
    reintegra lo que el cliente pago, no lo que la prenda cuesta hoy. Si la
    tienda subio el precio en el medio, devolverle el nuevo seria regalarle la
    diferencia; si lo bajo, seria quedarsela.
    """
    return list(
        db.execute(
            select(
                DetalleVenta.variante_id,
                DetalleVenta.cantidad,
                DetalleVenta.precio_unitario,
                DetalleVenta.descuento_unitario,
                VarianteProducto.sku,
                Producto.nombre.label("producto"),
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
            )
            .join(VarianteProducto, VarianteProducto.id == DetalleVenta.variante_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(DetalleVenta.venta_id == venta_id)
            .order_by(DetalleVenta.id)
        ).all()
    )


def ya_devuelto(db: Session, venta_id: int) -> dict[int, int]:
    """Cuantas unidades de cada variante ya volvieron de esta venta.

    Es lo que impide devolver dos veces la misma prenda. No hay restriccion en
    la base que lo prohiba ---y no deberia haberla: dos devoluciones parciales
    de la misma venta son legitimas---, asi que la cuenta se hace aca y el
    servicio la compara contra lo vendido.
    """
    filas = db.execute(
        select(
            DetalleDevolucion.variante_id,
            func.coalesce(func.sum(DetalleDevolucion.cantidad), 0),
        )
        .join(Devolucion, Devolucion.id == DetalleDevolucion.devolucion_id)
        .where(Devolucion.venta_id == venta_id)
        .group_by(DetalleDevolucion.variante_id)
    ).all()
    return {int(v): int(n) for v, n in filas}


def bloquear_venta(db: Session, venta_id: int) -> Venta | None:
    """Serializa las devoluciones de UNA venta. **Sin commit.**

    Sin esto, dos devoluciones simultaneas de la misma venta leen las dos el
    mismo «ya devuelto», las dos concluyen que queda una unidad y las dos la
    devuelven: la tienda reingresa dos prendas que nunca salieron y paga dos
    veces. No hay CHECK que lo atrape, porque la regla cruza dos tablas.
    """
    return db.scalar(select(Venta).where(Venta.id == venta_id).with_for_update())


def agregar_devolucion(
    db: Session,
    *,
    venta_id: int,
    turno_caja_id: int,
    motivo: str,
    monto: Decimal,
) -> Devolucion:
    """Crea la cabecera. **Sin commit.**"""
    devolucion = Devolucion(
        venta_id=venta_id,
        turno_caja_id=turno_caja_id,
        motivo=motivo,
        monto=monto,
    )
    db.add(devolucion)
    db.flush()
    return devolucion


def agregar_detalle(
    db: Session, *, devolucion_id: int, variante_id: int, cantidad: int
) -> DetalleDevolucion:
    """Una linea de la devolucion. **Sin commit.**"""
    detalle = DetalleDevolucion(
        devolucion_id=devolucion_id, variante_id=variante_id, cantidad=cantidad
    )
    db.add(detalle)
    return detalle
