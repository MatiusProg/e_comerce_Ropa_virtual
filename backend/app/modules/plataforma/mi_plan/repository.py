"""
P12 - Plataforma SaaS / CU-04  |  capa: repositorio (acceso a datos)

2do parcial. Caso de uso: CU-04 Consultar plan y consumo.

Las tablas del tenant (`suscripcion`, `sucursal`, `empleado`) ya vienen
filtradas por el RLS con la empresa del usuario: acá no se nombra la empresa.
`empresa` y `plan` son de la plataforma y no tienen RLS, así que la empresa se
busca por su id.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Empleado, Sucursal
from app.modules.plataforma.models import Empresa, Plan, Suscripcion


def obtener_empresa(db: Session, empresa_id: int) -> Empresa | None:
    return db.get(Empresa, empresa_id)


def obtener_suscripcion_actual(db: Session) -> Suscripcion | None:
    """La vigente o suspendida; si no hay, la última que tuvo.

    Hay como máximo una vigente o suspendida (RN-02, índice único parcial). Si
    no hay ninguna, se muestra la más reciente para que el administrador vea
    que venció y desde cuándo.
    """
    actual = db.scalar(
        select(Suscripcion).where(Suscripcion.estado.in_(("VIGENTE", "SUSPENDIDA")))
    )
    if actual is not None:
        return actual
    return db.scalar(
        select(Suscripcion)
        .order_by(Suscripcion.vencimiento.desc(), Suscripcion.id.desc())
        .limit(1)
    )


def contar_sucursales_activas(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(Sucursal).where(Sucursal.activa.is_(True))
    )


def contar_empleados_activos(db: Session) -> int:
    """Activo es sin fecha de baja: el mismo criterio del listado de empleados."""
    return db.scalar(
        select(func.count()).select_from(Empleado).where(Empleado.fecha_baja.is_(None))
    )


def listar_planes_activos(db: Session) -> list[Plan]:
    return list(db.scalars(select(Plan).where(Plan.activo.is_(True)).order_by(Plan.precio_mensual)))
