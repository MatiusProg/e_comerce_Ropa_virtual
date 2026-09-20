"""
P3 - Catalogo / CU-12  |  capa: repositorio (consultas, sin logica ni commit)
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import (
    Categoria,
    Producto,
    Temporada,
    VarianteProducto,
)
from app.modules.catalogo.promociones_models import Promocion


def descuentos_de_variantes(
    db: Session, *, variante_ids: list[int], hoy: date
) -> list[Row]:
    """El descuento vigente de cada variante pedida, si tiene alguno.

    UNA SOLA CONSULTA PARA LOS TRES ALCANCES
    -----------------------------------------
    Los tres se resuelven contra la misma fila de `variante_producto` unida a su
    producto: el alcance PRODUCTO compara con `producto.id`, el CATEGORIA con
    `producto.categoria_id` y el TEMPORADA con `producto.temporada_id`. Pedirlos
    en tres consultas y cruzarlos en Python daria lo mismo y costaria tres
    viajes por cada pagina de la vitrina.

    Devuelve **una fila por promocion que alcanza a cada variante**, no una por
    variante: cuando dos promociones se cruzan ---una del producto y otra de su
    categoria--- salen las dos, y quien decide cual gana es el servicio. Esa
    decision es una regla de negocio y no tiene por que estar escondida en un
    `ORDER BY`.
    """
    if not variante_ids:
        return []

    return list(
        db.execute(
            select(
                VarianteProducto.id.label("variante_id"),
                Promocion.id.label("promocion_id"),
                Promocion.nombre,
                Promocion.alcance,
                Promocion.porcentaje,
            )
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(
                Promocion,
                or_(
                    Promocion.producto_id == Producto.id,
                    Promocion.categoria_id == Producto.categoria_id,
                    Promocion.temporada_id == Producto.temporada_id,
                ),
            )
            .where(
                VarianteProducto.id.in_(variante_ids),
                Promocion.activa.is_(True),
                Promocion.desde <= hoy,
                or_(Promocion.hasta.is_(None), Promocion.hasta >= hoy),
            )
        ).all()
    )


def descuentos_de_productos(
    db: Session, *, producto_ids: list[int], hoy: date
) -> list[Row]:
    """Igual, pero por producto: es lo que necesita la vitrina.

    La grilla del catalogo muestra productos, no variantes, y todas las
    variantes de un producto comparten el mismo descuento ---porque los tres
    alcances son del producto o de algo que lo contiene---. Pedirlo por
    variante ahi seria traer diez filas para responder una.
    """
    if not producto_ids:
        return []

    return list(
        db.execute(
            select(
                Producto.id.label("producto_id"),
                Promocion.id.label("promocion_id"),
                Promocion.nombre,
                Promocion.alcance,
                Promocion.porcentaje,
            )
            .join(
                Promocion,
                or_(
                    Promocion.producto_id == Producto.id,
                    Promocion.categoria_id == Producto.categoria_id,
                    Promocion.temporada_id == Producto.temporada_id,
                ),
            )
            .where(
                Producto.id.in_(producto_ids),
                Promocion.activa.is_(True),
                Promocion.desde <= hoy,
                or_(Promocion.hasta.is_(None), Promocion.hasta >= hoy),
            )
        ).all()
    )


# =====================================================================
# El CRUD del Administrador
# =====================================================================

def _seleccion() -> Select:
    """La promocion con el nombre de su objetivo ya resuelto.

    Se resuelve aca y no en la pantalla porque «la categoria 4» no le dice nada
    a nadie: la lista tiene que poder leerse de corrido.
    """
    return (
        select(
            Promocion,
            Producto.nombre.label("producto_nombre"),
            Categoria.nombre.label("categoria_nombre"),
            Temporada.nombre.label("temporada_nombre"),
        )
        .outerjoin(Producto, Producto.id == Promocion.producto_id)
        .outerjoin(Categoria, Categoria.id == Promocion.categoria_id)
        .outerjoin(Temporada, Temporada.id == Promocion.temporada_id)
    )


def listar(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    alcance: str | None,
    solo_vigentes: bool,
    hoy: date,
) -> tuple[int, list[Row]]:
    filtros = []
    if alcance:
        filtros.append(Promocion.alcance == alcance)
    if solo_vigentes:
        filtros += [
            Promocion.activa.is_(True),
            Promocion.desde <= hoy,
            or_(Promocion.hasta.is_(None), Promocion.hasta >= hoy),
        ]

    total = db.scalar(
        select(func.count()).select_from(Promocion).where(*filtros)
    )
    filas = db.execute(
        _seleccion()
        .where(*filtros)
        # Las que empiezan despues van primero: lo que esta por venir es lo que
        # el Administrador acaba de cargar y quiere ver.
        .order_by(Promocion.desde.desc(), Promocion.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()
    return int(total or 0), filas


def obtener(db: Session, promocion_id: int) -> Row | None:
    return db.execute(_seleccion().where(Promocion.id == promocion_id)).first()


def entidad(db: Session, promocion_id: int) -> Promocion | None:
    return db.get(Promocion, promocion_id)


def existe_nombre(db: Session, nombre: str, *, excepto_id: int | None = None) -> bool:
    consulta = select(Promocion.id).where(func.lower(Promocion.nombre) == nombre.lower())
    if excepto_id is not None:
        consulta = consulta.where(Promocion.id != excepto_id)
    return db.scalar(consulta) is not None


def producto_existe(db: Session, producto_id: int) -> bool:
    return db.scalar(select(Producto.id).where(Producto.id == producto_id)) is not None


def categoria_existe(db: Session, categoria_id: int) -> bool:
    return (
        db.scalar(select(Categoria.id).where(Categoria.id == categoria_id)) is not None
    )


def temporada_existe(db: Session, temporada_id: int) -> bool:
    return (
        db.scalar(select(Temporada.id).where(Temporada.id == temporada_id)) is not None
    )


def agregar(db: Session, promocion: Promocion) -> Promocion:
    """**Sin commit.**"""
    db.add(promocion)
    db.flush()
    return promocion
