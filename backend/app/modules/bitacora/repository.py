"""
P12 - Bitacora / CU-42  |  capa: repositorio

Regla: aqui solo van consultas. Ninguna regla de negocio, ningun commit ---
el commit de la escritura lo hace el servicio, que es quien sabe que un
fallo de bitacora no puede tumbar la peticion.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.bitacora.models import AsientoBitacora
from app.modules.seguridad.models import Usuario


def agregar(db: Session, **campos: Any) -> AsientoBitacora:
    """Inserta un asiento. **Sin commit.**"""
    asiento = AsientoBitacora(**campos)
    db.add(asiento)
    db.flush()
    return asiento


def _filtrar(consulta, *, desde, hasta, usuario_id, accion, entidad, exito, busqueda):
    if desde is not None:
        consulta = consulta.where(AsientoBitacora.ocurrido_en >= desde)
    if hasta is not None:
        consulta = consulta.where(AsientoBitacora.ocurrido_en < hasta)
    if usuario_id is not None:
        consulta = consulta.where(AsientoBitacora.usuario_id == usuario_id)
    if accion:
        consulta = consulta.where(AsientoBitacora.accion == accion)
    if entidad:
        consulta = consulta.where(AsientoBitacora.entidad == entidad)
    if exito is not None:
        consulta = consulta.where(AsientoBitacora.exito.is_(exito))
    if busqueda:
        # Busca en el actor y en la ruta, que es por donde se busca de
        # verdad: «que hizo fulano» y «quien toco los precios».
        patron = f"%{busqueda.strip()}%"
        consulta = consulta.where(
            or_(
                AsientoBitacora.actor.ilike(patron),
                AsientoBitacora.ruta.ilike(patron),
            )
        )
    return consulta


def contar(db: Session, **filtros: Any) -> int:
    consulta = _filtrar(
        select(func.count()).select_from(AsientoBitacora), **filtros
    )
    return db.scalar(consulta) or 0


def listar(
    db: Session, *, limite: int, desplazamiento: int, **filtros: Any
) -> list[tuple]:
    """Los asientos con el nombre de quien los hizo, si todavia existe.

    `isouter` a proposito: el usuario puede haber sido borrado y el asiento
    tiene que seguir apareciendo. Para eso mismo se guarda `actor`, que es lo
    que se muestra cuando la cuenta ya no esta.
    """
    consulta = _filtrar(
        select(
            AsientoBitacora,
            func.concat(Usuario.nombres, " ", Usuario.apellidos),
        ).join(Usuario, Usuario.id == AsientoBitacora.usuario_id, isouter=True),
        **filtros,
    )
    consulta = (
        consulta.order_by(AsientoBitacora.ocurrido_en.desc(), AsientoBitacora.id.desc())
        .limit(limite)
        .offset(desplazamiento)
    )
    return [tuple(f) for f in db.execute(consulta).all()]


def acciones(db: Session) -> list[str]:
    return list(
        db.scalars(
            select(AsientoBitacora.accion).distinct().order_by(AsientoBitacora.accion)
        ).all()
    )


def entidades(db: Session) -> list[str]:
    return list(
        db.scalars(
            select(AsientoBitacora.entidad)
            .where(AsientoBitacora.entidad.is_not(None))
            .distinct()
            .order_by(AsientoBitacora.entidad)
        ).all()
    )


def ultimo(db: Session) -> AsientoBitacora | None:
    """El asiento mas reciente. Lo usan las pruebas."""
    return db.scalar(
        select(AsientoBitacora).order_by(AsientoBitacora.id.desc()).limit(1)
    )
