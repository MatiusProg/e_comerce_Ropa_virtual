"""
P12 - Plataforma SaaS  |  capa: servicio

CU-02 Gestionar planes. Lo opera el administrador de la plataforma.

LOS CAMBIOS RIGEN DESDE LA SIGUIENTE VERIFICACIÓN (paso 5)
-----------------------------------------------------------
El verificador del CU-05 lee el plan de la base en cada operación, así que no
hay nada que propagar: guardar el plan alcanza para que valga en todas sus
empresas. Por eso el plan se puede cambiar sin tocar el código.

BAJAR UN LÍMITE NO BORRA NADA (alternativo 5a, RN-04)
------------------------------------------------------
Si una empresa ya tiene más de lo que el nuevo límite permite, conserva todo
y solo deja de poder crear más. Al guardar se devuelve la lista de esas
empresas para que el administrador sepa a quién afecta.

DESACTIVAR NO QUITA EL PLAN A NADIE (alternativo 3a)
-----------------------------------------------------
Un plan inactivo deja de ofrecerse en las altas y en la página de planes, pero
las empresas que lo tienen lo conservan hasta su vencimiento.
"""

import re
import unicodedata
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Empleado, Sucursal
from app.modules.plataforma.mi_plan.service import ETIQUETAS_FUNCIONES
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.plataforma.schemas import (
    EmpresaExcedidaOut,
    FuncionOut,
    PlanGuardadoOut,
    PlanIn,
    PlanOut,
)
from app.modules.plataforma.verificador import FUNCIONES

#: Las suscripciones que cuentan como «empresas que usan el plan»: una
#: suspendida sigue siendo de ese plan, y vuelve a él al reactivarse.
ESTADOS_CON_PLAN = ("VIGENTE", "SUSPENDIDA")


class ErrorDePlanes(Exception):
    """Error de negocio del CU-02."""


class PlanInexistente(ErrorDePlanes):
    pass


class NombreDePlanRepetido(ErrorDePlanes):
    pass


# --------------------------------------------------------------------------
#  Lectura
# --------------------------------------------------------------------------
def _empresas_por_plan(db: Session) -> dict[int, int]:
    return dict(
        db.execute(
            select(Suscripcion.plan_id, func.count(func.distinct(Suscripcion.empresa_id)))
            .where(Suscripcion.estado.in_(ESTADOS_CON_PLAN))
            .group_by(Suscripcion.plan_id)
        ).all()
    )


def _salida(plan: Plan, empresas: int) -> PlanOut:
    return PlanOut(
        id=plan.id,
        codigo=plan.codigo,
        nombre=plan.nombre,
        precio_mensual=float(plan.precio_mensual),
        duracion_dias=plan.duracion_dias,
        max_sucursales=plan.max_sucursales,
        max_empleados=plan.max_empleados,
        cupo_reportes_ia=plan.cupo_reportes_ia,
        cupo_fotos_ia=plan.cupo_fotos_ia,
        funciones=[clave for clave in FUNCIONES if (plan.funciones or {}).get(clave) is True],
        bitacora_dias=(plan.funciones or {}).get("bitacora_dias"),
        activo=plan.activo,
        empresas=empresas,
    )


def listar_planes(db: Session, *, incluir_inactivos: bool = False) -> list[PlanOut]:
    """Paso 2. Sin `incluir_inactivos`, solo los que se ofrecen (alta de empresas)."""
    consulta = select(Plan).order_by(Plan.precio_mensual, Plan.id)
    if not incluir_inactivos:
        consulta = consulta.where(Plan.activo.is_(True))
    empresas = _empresas_por_plan(db)
    return [_salida(p, empresas.get(p.id, 0)) for p in db.scalars(consulta)]


def listar_funciones() -> list[FuncionOut]:
    """Las funciones que un plan puede incluir, con un nombre para la casilla."""
    # Los mismos nombres que ve la empresa en «Mi plan» (CU-04).
    return [
        FuncionOut(clave=clave, nombre=ETIQUETAS_FUNCIONES.get(clave, clave)) for clave in FUNCIONES
    ]


def _obtener(db: Session, plan_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise PlanInexistente(str(plan_id))
    return plan


def obtener_plan(db: Session, plan_id: int) -> PlanOut:
    plan = _obtener(db, plan_id)
    return _salida(plan, _empresas_por_plan(db).get(plan.id, 0))


# --------------------------------------------------------------------------
#  Escritura
# --------------------------------------------------------------------------
def _codigo_desde(nombre: str) -> str:
    """«Pyme Plus» → «PYME_PLUS». Mayúsculas sin tildes, como BASICO."""
    ascii_ = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]+", "_", ascii_.upper()).strip("_")[:20] or "PLAN"


def _codigo_libre(db: Session, base: str) -> str:
    codigo, n = base, 2
    while db.scalar(select(Plan.id).where(Plan.codigo == codigo)) is not None:
        sufijo = f"_{n}"
        codigo, n = base[: 20 - len(sufijo)] + sufijo, n + 1
    return codigo


def _validar_nombre(db: Session, nombre: str, *, salvo: int | None = None) -> None:
    """Paso 4: el nombre es único, sin importar mayúsculas."""
    consulta = select(Plan.id).where(func.lower(Plan.nombre) == nombre.lower())
    if salvo is not None:
        consulta = consulta.where(Plan.id != salvo)
    if db.scalar(consulta) is not None:
        raise NombreDePlanRepetido(nombre)


def _aplicar(plan: Plan, datos: PlanIn) -> None:
    plan.nombre = datos.nombre
    plan.precio_mensual = Decimal(str(datos.precio_mensual)).quantize(Decimal("0.01"))
    plan.duracion_dias = datos.duracion_dias
    plan.max_sucursales = datos.max_sucursales
    plan.max_empleados = datos.max_empleados
    plan.cupo_reportes_ia = datos.cupo_reportes_ia
    plan.cupo_fotos_ia = datos.cupo_fotos_ia
    # `funciones` guarda también ajustes que no son funciones (como
    # `bitacora_dias`): se conservan, y cada función queda en true o false.
    ajustes = {k: v for k, v in (plan.funciones or {}).items() if k not in FUNCIONES}
    plan.funciones = (
        ajustes
        | {clave: clave in datos.funciones for clave in FUNCIONES}
        | {"bitacora_dias": datos.bitacora_dias}
    )


def _excedidas(db: Session, plan: Plan) -> list[EmpresaExcedidaOut]:
    """Alternativo 5a: las empresas del plan que ya pasan algún límite.

    Se cuenta igual que el verificador del CU-05: sucursales activas y
    empleados sin fecha de baja. La plataforma ve todas las empresas, así que
    se agrupa por empresa en una consulta por recurso.
    """
    empresas = dict(
        db.execute(
            select(Empresa.id, Empresa.nombre)
            .join(Suscripcion, Suscripcion.empresa_id == Empresa.id)
            .where(Suscripcion.plan_id == plan.id, Suscripcion.estado.in_(ESTADOS_CON_PLAN))
        ).all()
    )
    if not empresas:
        return []

    recursos = (
        ("sucursales activas", plan.max_sucursales, Sucursal.empresa_id, Sucursal.activa.is_(True)),
        ("empleados activos", plan.max_empleados, Empleado.empresa_id, Empleado.fecha_baja.is_(None)),
    )
    excedidas: list[EmpresaExcedidaOut] = []
    for nombre, limite, columna, condicion in recursos:
        if limite is None:
            continue
        filas = db.execute(
            select(columna, func.count())
            .where(columna.in_(empresas), condicion)
            .group_by(columna)
            .having(func.count() > limite)
        ).all()
        excedidas += [
            EmpresaExcedidaOut(empresa=empresas[empresa_id], recurso=nombre, uso=uso, limite=limite)
            for empresa_id, uso in filas
        ]
    return sorted(excedidas, key=lambda e: (e.empresa, e.recurso))


def _guardado(db: Session, plan: Plan) -> PlanGuardadoOut:
    salida = _salida(plan, _empresas_por_plan(db).get(plan.id, 0))
    return PlanGuardadoOut(**salida.model_dump(), excedidas=_excedidas(db, plan))


def crear_plan(db: Session, datos: PlanIn) -> PlanGuardadoOut:
    _validar_nombre(db, datos.nombre)
    plan = Plan(codigo=_codigo_libre(db, _codigo_desde(datos.nombre)))
    _aplicar(plan, datos)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _guardado(db, plan)


def editar_plan(db: Session, plan_id: int, datos: PlanIn) -> PlanGuardadoOut:
    plan = _obtener(db, plan_id)
    _validar_nombre(db, datos.nombre, salvo=plan.id)
    _aplicar(plan, datos)
    db.commit()
    db.refresh(plan)
    return _guardado(db, plan)


def cambiar_estado(db: Session, plan_id: int, *, activo: bool) -> PlanOut:
    """Alternativo 3a. Desactivar no toca las suscripciones que ya lo usan."""
    plan = _obtener(db, plan_id)
    plan.activo = activo
    db.commit()
    db.refresh(plan)
    return _salida(plan, _empresas_por_plan(db).get(plan.id, 0))
