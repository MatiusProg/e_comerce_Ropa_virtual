"""
P15 - Devoluciones por la web / CU-24  |  capa: repositorio

Ninguna consulta filtra por empresa: lo hace la RLS de cada tabla.
"""

from __future__ import annotations

from sqlalchemy import Row, and_, func, select
from sqlalchemy.orm import Session, aliased

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.devoluciones_web.models import (
    ESTADOS_ABIERTOS,
    LineaSolicitudDevolucion,
    SolicitudDevolucion,
)
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Sucursal
from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import DetalleVenta, Venta


def venta_digital(db: Session, codigo: str, *, bloquear: bool = False) -> Venta | None:
    consulta = select(Venta).where(Venta.codigo == codigo, Venta.canal == "DIGITAL")
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def nombre_de_sucursal(db: Session, sucursal_id: int) -> str:
    return db.scalar(select(Sucursal.nombre).where(Sucursal.id == sucursal_id)) or ""


def pedidos_digitales(
    db: Session, *, sucursal_id: int | None, estado: str | None, codigo: str | None = None
) -> list[Row]:
    unidades = (
        select(func.coalesce(func.sum(DetalleVenta.cantidad), 0))
        .where(DetalleVenta.venta_id == Venta.id)
        .scalar_subquery()
    )
    consulta = (
        select(
            Venta.codigo,
            Venta.estado,
            Venta.modalidad_entrega,
            (Usuario.nombres + " " + Usuario.apellidos).label("cliente"),
            Venta.total,
            unidades.label("unidades"),
            Venta.creado_en,
            Venta.entregado_en,
        )
        .outerjoin(Cliente, Cliente.id == Venta.cliente_id)
        .outerjoin(Usuario, Usuario.id == Cliente.usuario_id)
        .where(Venta.canal == "DIGITAL", Venta.estado.in_(("PAGADA", "ENTREGADA")))
        .order_by(Venta.creado_en.desc())
        .limit(200)
    )
    if sucursal_id is not None:
        consulta = consulta.where(Venta.sucursal_id == sucursal_id)
    if estado is not None:
        consulta = consulta.where(Venta.estado == estado)
    if codigo is not None:
        consulta = consulta.where(Venta.codigo == codigo)
    return list(db.execute(consulta).all())


def pedido_en_solicitudes_abiertas(db: Session, venta_id: int) -> dict[int, int]:
    filas = db.execute(
        select(LineaSolicitudDevolucion.variante_id, func.sum(LineaSolicitudDevolucion.cantidad))
        .join(SolicitudDevolucion, SolicitudDevolucion.id == LineaSolicitudDevolucion.solicitud_id)
        .where(
            SolicitudDevolucion.venta_id == venta_id,
            SolicitudDevolucion.estado.in_(ESTADOS_ABIERTOS),
        )
        .group_by(LineaSolicitudDevolucion.variante_id)
    ).all()
    return {int(v): int(n) for v, n in filas}


def opciones_de_cambio(db: Session, *, variante_id: int, sucursal_id: int) -> list[Row]:
    """La misma prenda en otra talla o color, activa y con saldo en la sucursal."""
    original = aliased(VarianteProducto)
    return list(
        db.execute(
            select(
                VarianteProducto.id.label("variante_id"),
                VarianteProducto.sku,
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
                VarianteProducto.precio,
                Existencia.cantidad_disponible.label("disponible"),
            )
            .join(original, original.producto_id == VarianteProducto.producto_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .join(
                Existencia,
                and_(
                    Existencia.variante_id == VarianteProducto.id,
                    Existencia.sucursal_id == sucursal_id,
                ),
            )
            .where(
                original.id == variante_id,
                VarianteProducto.id != variante_id,
                VarianteProducto.activa.is_(True),
                Producto.activo.is_(True),
                Existencia.cantidad_disponible > 0,
            )
            .order_by(Talla.codigo, Color.nombre)
        ).all()
    )


def cabecera_de_solicitud(db: Session, solicitud_id: int) -> Row:
    return db.execute(
        select(
            SolicitudDevolucion.id,
            SolicitudDevolucion.venta_id,
            Venta.codigo.label("venta_codigo"),
            Sucursal.nombre.label("sucursal"),
            (Usuario.nombres + " " + Usuario.apellidos).label("cliente"),
            SolicitudDevolucion.tipo,
            SolicitudDevolucion.estado,
            SolicitudDevolucion.motivo,
            SolicitudDevolucion.respuesta,
            SolicitudDevolucion.creado_en,
            SolicitudDevolucion.atendida_en,
        )
        .join(Venta, Venta.id == SolicitudDevolucion.venta_id)
        .join(Sucursal, Sucursal.id == SolicitudDevolucion.sucursal_id)
        .join(Cliente, Cliente.id == SolicitudDevolucion.cliente_id)
        .join(Usuario, Usuario.id == Cliente.usuario_id)
        .where(SolicitudDevolucion.id == solicitud_id)
    ).one()


def lineas_de_solicitud(db: Session, solicitud_id: int) -> list[Row]:
    nueva = aliased(VarianteProducto)
    talla = aliased(Talla)
    color = aliased(Color)
    return list(
        db.execute(
            select(
                LineaSolicitudDevolucion.variante_id,
                LineaSolicitudDevolucion.cantidad,
                LineaSolicitudDevolucion.variante_nueva_id,
                talla.codigo.label("talla_nueva"),
                color.nombre.label("color_nueva"),
                nueva.precio.label("precio_nuevo"),
            )
            .outerjoin(nueva, nueva.id == LineaSolicitudDevolucion.variante_nueva_id)
            .outerjoin(talla, talla.id == nueva.talla_id)
            .outerjoin(color, color.id == nueva.color_id)
            .where(LineaSolicitudDevolucion.solicitud_id == solicitud_id)
            .order_by(LineaSolicitudDevolucion.id)
        ).all()
    )


def ids_de_solicitudes(
    db: Session,
    *,
    cliente_id: int | None = None,
    sucursal_id: int | None = None,
    estado: str | None = None,
) -> list[int]:
    consulta = select(SolicitudDevolucion.id).order_by(SolicitudDevolucion.creado_en.desc()).limit(200)
    if cliente_id is not None:
        consulta = consulta.where(SolicitudDevolucion.cliente_id == cliente_id)
    if sucursal_id is not None:
        consulta = consulta.where(SolicitudDevolucion.sucursal_id == sucursal_id)
    if estado is not None:
        consulta = consulta.where(SolicitudDevolucion.estado == estado)
    return list(db.scalars(consulta))
