"""
P9 - Vestidor Virtual  |  capa: repositorio (consultas, sin reglas ni commit)
2do parcial, 3ra presentacion: CU-36, CU-37 y CU-38.

Todo pasa por RLS: las tablas de este modulo y las de catalogo que se cruzan
son de empresa, asi que una consulta nunca ve la prenda de otra tienda aunque
alguien adivine un id.
"""

from __future__ import annotations

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import (
    Color,
    ImagenProducto,
    Producto,
    Talla,
    VarianteProducto,
)
from app.modules.medidas.models import MedidaTalla
from app.modules.vestidor_virtual.models import PuntoPrenda, SesionVestidorVirtual


def producto(db: Session, producto_id: int) -> Producto | None:
    return db.get(Producto, producto_id)


def productos_con_vestidor(db: Session) -> list[Row]:
    """Los productos que tienen al menos una imagen de vestidor (PNG + variante)."""
    return list(
        db.execute(
            select(Producto.id, Producto.nombre, Producto.activo)
            .join(ImagenProducto, ImagenProducto.producto_id == Producto.id)
            .where(
                ImagenProducto.es_transparente.is_(True),
                ImagenProducto.variante_id.is_not(None),
            )
            .group_by(Producto.id, Producto.nombre, Producto.activo)
            .order_by(Producto.nombre)
        ).all()
    )


def imagenes_de_vestidor(
    db: Session, producto_id: int, *, solo_activas: bool = False
) -> list[Row]:
    """Las imagenes de vestidor de un producto, con su variante y sus puntos (si los hay)."""
    consulta = (
        select(
            ImagenProducto.id.label("imagen_id"),
            ImagenProducto.ruta,
            VarianteProducto.id.label("variante_id"),
            Talla.id.label("talla_id"),
            Talla.codigo.label("talla"),
            Color.id.label("color_id"),
            Color.nombre.label("color"),
            PuntoPrenda,
        )
        .join(VarianteProducto, VarianteProducto.id == ImagenProducto.variante_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .outerjoin(PuntoPrenda, PuntoPrenda.imagen_id == ImagenProducto.id)
        .where(
            ImagenProducto.producto_id == producto_id,
            ImagenProducto.es_transparente.is_(True),
        )
        .order_by(Talla.orden, Color.nombre, ImagenProducto.orden, ImagenProducto.id)
    )
    if solo_activas:
        consulta = consulta.where(VarianteProducto.activa.is_(True))
    return list(db.execute(consulta).all())


def imagen(db: Session, imagen_id: int) -> ImagenProducto | None:
    return db.get(ImagenProducto, imagen_id)


def puntos_de(db: Session, imagen_id: int) -> PuntoPrenda | None:
    return db.scalar(select(PuntoPrenda).where(PuntoPrenda.imagen_id == imagen_id))


def tallas_del_producto(db: Session, producto_id: int) -> list[Row]:
    """Las tallas en las que se vende el producto, con su medida de prenda si existe."""
    return list(
        db.execute(
            select(Talla.id, Talla.codigo, Talla.orden, MedidaTalla)
            .join(VarianteProducto, VarianteProducto.talla_id == Talla.id)
            .outerjoin(
                MedidaTalla,
                (MedidaTalla.talla_id == Talla.id)
                & (MedidaTalla.producto_id == producto_id),
            )
            .where(VarianteProducto.producto_id == producto_id)
            .distinct()
            .order_by(Talla.orden)
        ).all()
    )


def medida_talla(db: Session, producto_id: int, talla_id: int) -> MedidaTalla | None:
    return db.scalar(
        select(MedidaTalla).where(
            MedidaTalla.producto_id == producto_id, MedidaTalla.talla_id == talla_id
        )
    )


def variante_preparada(db: Session, variante_id: int) -> Row | None:
    """La variante con su producto y talla, si tiene imagen de vestidor CON puntos.

    Es la condicion para que una prueba tenga sentido: sin puntos no hay escala,
    y sin escala lo que se dibuja no respeta la talla.
    """
    return db.execute(
        select(
            VarianteProducto.id,
            VarianteProducto.producto_id,
            Producto.nombre.label("producto"),
            Talla.id.label("talla_id"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(ImagenProducto, ImagenProducto.variante_id == VarianteProducto.id)
        .join(PuntoPrenda, PuntoPrenda.imagen_id == ImagenProducto.id)
        .where(
            VarianteProducto.id == variante_id,
            VarianteProducto.activa.is_(True),
            Producto.activo.is_(True),
            ImagenProducto.es_transparente.is_(True),
        )
        .limit(1)
    ).first()


def sesion(db: Session, sesion_id: int) -> SesionVestidorVirtual | None:
    return db.get(SesionVestidorVirtual, sesion_id)


def sesiones_de(db: Session, cliente_id: int, limite: int = 20) -> list[Row]:
    return list(
        db.execute(
            select(
                SesionVestidorVirtual,
                Producto.id.label("producto_id"),
                Producto.nombre.label("producto"),
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
            )
            .join(VarianteProducto, VarianteProducto.id == SesionVestidorVirtual.variante_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(SesionVestidorVirtual.cliente_id == cliente_id)
            .order_by(SesionVestidorVirtual.creado_en.desc(), SesionVestidorVirtual.id.desc())
            .limit(limite)
        ).all()
    )


def una_sesion_con_detalle(db: Session, sesion_id: int) -> Row | None:
    return db.execute(
        select(
            SesionVestidorVirtual,
            Producto.id.label("producto_id"),
            Producto.nombre.label("producto"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
        )
        .join(VarianteProducto, VarianteProducto.id == SesionVestidorVirtual.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(SesionVestidorVirtual.id == sesion_id)
    ).first()
