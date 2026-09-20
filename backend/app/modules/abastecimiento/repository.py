"""
P4 - Inventario / CU-39  |  capa: repositorio (consultas, sin logica ni commit)
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Abastecimiento
from app.modules.organizacion.models import Proveedor


def proveedor_de_usuario(db: Session, usuario_id: int) -> Proveedor | None:
    return db.scalar(select(Proveedor).where(Proveedor.usuario_id == usuario_id))


def variante_de(db: Session, variante_id: int):
    """La variante con su prenda, si existe y se puede abastecer."""
    return db.execute(
        select(
            VarianteProducto.id,
            VarianteProducto.sku,
            Producto.id,
            Producto.nombre,
            Producto.proveedor_id,
            Talla.codigo,
            Color.nombre,
            VarianteProducto.activa,
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(VarianteProducto.id == variante_id)
    ).one_or_none()


def vigente(db: Session, proveedor_id: int, variante_id: int) -> Abastecimiento | None:
    return db.scalar(
        select(Abastecimiento).where(
            Abastecimiento.proveedor_id == proveedor_id,
            Abastecimiento.variante_id == variante_id,
            Abastecimiento.estado == "ANUNCIADO",
        )
    )


def por_id(db: Session, anuncio_id: int) -> Abastecimiento | None:
    return db.get(Abastecimiento, anuncio_id)


def mios(db: Session, proveedor_id: int, *, incluir_cancelados: bool) -> list[tuple]:
    consulta = (
        select(
            Abastecimiento.id,
            Abastecimiento.variante_id,
            VarianteProducto.sku,
            Producto.nombre,
            Talla.codigo,
            Color.nombre,
            Abastecimiento.cantidad,
            Abastecimiento.dias_plazo,
            Abastecimiento.observacion,
            Abastecimiento.estado,
            Abastecimiento.creado_en,
        )
        .join(VarianteProducto, VarianteProducto.id == Abastecimiento.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(Abastecimiento.proveedor_id == proveedor_id)
        .order_by(Abastecimiento.creado_en.desc())
    )
    if not incluir_cancelados:
        consulta = consulta.where(Abastecimiento.estado == "ANUNCIADO")
    return [tuple(f) for f in db.execute(consulta).all()]


def variantes_del_proveedor(db: Session, proveedor_id: int) -> list[tuple]:
    """Las variantes que este proveedor puede anunciar.

    SOLO LAS DE SUS PROPIOS PRODUCTOS. Un proveedor no puede prometer una
    prenda de otro: el anuncio alimenta el inventario consolidado, y un
    «proxima a ingresar» respaldado por quien no la abastece es peor que no
    tener el dato.
    """
    return [
        tuple(f)
        for f in db.execute(
            select(
                VarianteProducto.id,
                VarianteProducto.sku,
                Producto.nombre,
                Talla.codigo,
                Color.nombre,
            )
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(
                Producto.proveedor_id == proveedor_id,
                VarianteProducto.activa.is_(True),
                Producto.activo.is_(True),
            )
            .order_by(Producto.nombre, Talla.codigo, Color.nombre)
        ).all()
    ]


def crear(
    db: Session,
    *,
    proveedor_id: int,
    variante_id: int,
    cantidad: int,
    dias_plazo: int,
    observacion: str | None,
) -> Abastecimiento:
    """**Sin commit.**"""
    fila = Abastecimiento(
        proveedor_id=proveedor_id,
        variante_id=variante_id,
        cantidad=cantidad,
        dias_plazo=dias_plazo,
        observacion=observacion,
        estado="ANUNCIADO",
    )
    db.add(fila)
    db.flush()
    return fila


# --- Lo que consume el inventario consolidado (CU-16) -----------------------


def anunciado_por_variante(db: Session, variante_ids: list[int]) -> dict[int, tuple[int, int]]:
    """Cuanto hay anunciado y en cuantos dias, por variante.

    EN BLOQUE Y NO UNA CONSULTA POR FILA. El consolidado muestra paginas de
    decenas de variantes; preguntar una por una serian decenas de viajes para
    pintar una columna.

    Devuelve `{variante_id: (cantidad_total, dias_minimos)}`.

    **Se suma entre proveedores y se toma el plazo MENOR.** Si dos proveedores
    anuncian la misma variante, van a llegar las dos cantidades; y lo que le
    importa a quien mira el inventario es cuando llega la primera.
    """
    if not variante_ids:
        return {}
    filas = db.execute(
        select(
            Abastecimiento.variante_id,
            func.sum(Abastecimiento.cantidad),
            func.min(Abastecimiento.dias_plazo),
        )
        .where(
            Abastecimiento.variante_id.in_(variante_ids),
            Abastecimiento.estado == "ANUNCIADO",
        )
        .group_by(Abastecimiento.variante_id)
    ).all()
    return {f[0]: (int(f[1] or 0), int(f[2] or 0)) for f in filas}
