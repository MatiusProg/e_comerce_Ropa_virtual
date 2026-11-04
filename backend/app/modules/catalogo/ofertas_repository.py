"""
P16 - Ofertas / CU-31 y CU-32  |  capa: repositorio

Solo consultas; las transacciones las cierra el servicio.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Producto, Temporada, VarianteProducto
from app.modules.catalogo.ofertas_models import PrecioMayorista, ReglaFueraDeTemporada
from app.modules.catalogo.promociones_models import Promocion
from app.modules.inventario.models import Existencia


# =====================================================================
#  Precios mayoristas
# =====================================================================

def escalones_de_variantes(
    db: Session, variante_ids: list[int]
) -> list[Row]:
    """Los escalones ACTIVOS de los productos de esas variantes.

    Una fila por (variante, escalón): `variante_id`, `producto_id`,
    `cantidad_minima`, `precio_unitario`. Las variantes sin escalones no
    aparecen.
    """
    if not variante_ids:
        return []
    return list(
        db.execute(
            select(
                VarianteProducto.id.label("variante_id"),
                VarianteProducto.producto_id,
                PrecioMayorista.cantidad_minima,
                PrecioMayorista.precio_unitario,
            )
            .join(PrecioMayorista, PrecioMayorista.producto_id == VarianteProducto.producto_id)
            .where(
                VarianteProducto.id.in_(variante_ids),
                PrecioMayorista.activo.is_(True),
            )
            .order_by(VarianteProducto.id, PrecioMayorista.cantidad_minima)
        )
    )


def escalones_de_productos(db: Session, producto_ids: list[int]) -> list[PrecioMayorista]:
    """Los escalones activos de esos productos, para mostrarlos (vitrina, caja)."""
    if not producto_ids:
        return []
    return list(
        db.scalars(
            select(PrecioMayorista)
            .where(
                PrecioMayorista.producto_id.in_(producto_ids),
                PrecioMayorista.activo.is_(True),
            )
            .order_by(PrecioMayorista.producto_id, PrecioMayorista.cantidad_minima)
        )
    )


def listar_mayoristas(
    db: Session, *, busqueda: str | None, pagina: int, tamano: int
) -> tuple[int, list[Row]]:
    consulta = select(
        PrecioMayorista,
        Producto.nombre.label("producto_nombre"),
        Producto.precio_base.label("precio_base"),
    ).join(Producto, Producto.id == PrecioMayorista.producto_id)
    if busqueda:
        consulta = consulta.where(Producto.nombre.ilike(f"%{busqueda.strip()}%"))
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    filas = db.execute(
        consulta.order_by(Producto.nombre, PrecioMayorista.cantidad_minima)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()
    return total, list(filas)


def mayorista(db: Session, mayorista_id: int) -> PrecioMayorista | None:
    return db.get(PrecioMayorista, mayorista_id)


def fila_de_mayorista(db: Session, mayorista_id: int) -> Row | None:
    return db.execute(
        select(
            PrecioMayorista,
            Producto.nombre.label("producto_nombre"),
            Producto.precio_base.label("precio_base"),
        )
        .join(Producto, Producto.id == PrecioMayorista.producto_id)
        .where(PrecioMayorista.id == mayorista_id)
    ).first()


def producto(db: Session, producto_id: int) -> Producto | None:
    return db.get(Producto, producto_id)


def existe_escalon(
    db: Session, producto_id: int, cantidad_minima: int, *, excepto_id: int | None = None
) -> bool:
    consulta = select(PrecioMayorista.id).where(
        PrecioMayorista.producto_id == producto_id,
        PrecioMayorista.cantidad_minima == cantidad_minima,
    )
    if excepto_id is not None:
        consulta = consulta.where(PrecioMayorista.id != excepto_id)
    return db.scalar(consulta.limit(1)) is not None


def precio_minimo_del_producto(db: Session, producto_id: int) -> Decimal | None:
    return db.scalar(
        select(func.min(VarianteProducto.precio)).where(
            VarianteProducto.producto_id == producto_id,
            VarianteProducto.activa.is_(True),
        )
    )


# =====================================================================
#  Fuera de temporada
# =====================================================================

def regla(db: Session) -> ReglaFueraDeTemporada | None:
    """La de la empresa del contexto; el RLS deja ver una sola."""
    return db.scalar(select(ReglaFueraDeTemporada).limit(1))


def candidatas_fuera_de_temporada(
    db: Session, *, hasta_fin: date, existencia_minima: int
) -> list[Row]:
    """Los productos que cumplen el factor de RF-57.

    - su temporada terminó el `hasta_fin` o antes (hoy menos los días), y
    - la suma de lo disponible en todas las sucursales llega al mínimo.

    Trae también la promoción automática que ya tenga, si tiene alguna: el
    servicio decide con eso si la crea o la deja como está.
    """
    disponible = (
        select(
            VarianteProducto.producto_id.label("producto_id"),
            func.coalesce(func.sum(Existencia.cantidad_disponible), 0).label("disponible"),
        )
        .join(Existencia, Existencia.variante_id == VarianteProducto.id)
        .where(VarianteProducto.activa.is_(True))
        .group_by(VarianteProducto.producto_id)
        .subquery()
    )
    automatica = (
        select(
            Promocion.producto_id.label("producto_id"),
            func.max(Promocion.id).label("promocion_id"),
        )
        .where(Promocion.origen == "AUTOMATICA", Promocion.alcance == "PRODUCTO")
        .group_by(Promocion.producto_id)
        .subquery()
    )
    return list(
        db.execute(
            select(
                Producto.id.label("producto_id"),
                Producto.nombre.label("producto"),
                Temporada.id.label("temporada_id"),
                Temporada.nombre.label("temporada"),
                Temporada.fecha_fin,
                disponible.c.disponible,
                automatica.c.promocion_id,
            )
            .join(Temporada, Temporada.id == Producto.temporada_id)
            .join(disponible, disponible.c.producto_id == Producto.id)
            .outerjoin(automatica, automatica.c.producto_id == Producto.id)
            .where(
                Producto.activo.is_(True),
                Temporada.fecha_fin <= hasta_fin,
                disponible.c.disponible >= existencia_minima,
            )
            .order_by(disponible.c.disponible.desc(), Producto.nombre)
        )
    )


def automaticas_vigentes(db: Session) -> list[Promocion]:
    """Las automáticas encendidas y sin fecha de fin: las que la regla vigila."""
    return list(
        db.scalars(
            select(Promocion).where(
                Promocion.origen == "AUTOMATICA",
                Promocion.activa.is_(True),
                Promocion.hasta.is_(None),
            )
        )
    )


def promocion(db: Session, promocion_id: int) -> Promocion | None:
    return db.get(Promocion, promocion_id)


def agregar(db: Session, entidad) -> None:
    db.add(entidad)
    db.flush()
