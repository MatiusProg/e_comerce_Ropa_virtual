"""
P12 - Plataforma SaaS  |  capa: servicio (la clase control GestorSuscripciones)

CU-03 Gestionar suscripciones. Lo opera el administrador de la plataforma, en
modo plataforma: ve las suscripciones de todas las empresas.

  1.3  obtener la empresa
  1.4  su historial de suscripciones y de pagos                (pasos 1 y 2)
  1.7  el plan elegido
  1.8  registrar el pago simulado                              (paso 4)
  1.9  cerrar la suscripción vigente                           (paso 5)
  1.10 crear la nueva con su vencimiento
  2.x  renovar: extender el vencimiento                        (3a)
  3.x  suspender o reactivar                                   (3b)
  4.x  avisar lo que pasa el límite del plan nuevo             (5a)
  5.x  marcar las vencidas, el proceso diario                  (E1)

UNA SOLA VIGENTE (paso 5, RN-02)
--------------------------------
Cerrar la anterior y abrir la nueva van en la misma transacción. La base lo
garantiza además con el índice único parcial sobre VIGENTE y SUSPENDIDA: si
dos cambios simultáneos llegaran a abrir dos, el segundo commit falla y no
queda nada a medias.

BAJAR DE PLAN NO BORRA NADA (5a, RN-04)
---------------------------------------
Se cambia igual, y se devuelve lo que la empresa ya tiene por encima de los
límites del plan nuevo. El verificador del CU-05 le impide crear más.

EL VENCIMIENTO NO ESPERA AL PROCESO DIARIO (E1)
-----------------------------------------------
El verificador ya trata como no vigente a la suscripción cuya fecha pasó. El
proceso diario solo deja el estado de la fila al día, para el historial y para
la lista de empresas; es idempotente.
"""

import secrets
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.tenencia import EMPRESA_DE_BAJA
from app.modules.plataforma.models import Empresa, PagoSimulado, Plan, Suscripcion
from app.modules.plataforma.planes import excedidas_en
from app.modules.plataforma.schemas import (
    AsignarPlanIn,
    PagoSimuladoOut,
    SuscripcionGuardadaOut,
    SuscripcionesOut,
    SuscripcionOut,
    VencimientoOut,
)

VIGENTE, SUSPENDIDA, VENCIDA, REEMPLAZADA = "VIGENTE", "SUSPENDIDA", "VENCIDA", "REEMPLAZADA"
#: Las que la empresa tiene «ahora»: como máximo una (RN-02).
ESTADOS_ACTUALES = (VIGENTE, SUSPENDIDA)
#: El precio del plan es mensual; el pago cubre la duración del plan.
DIAS_POR_MES = 30


class ErrorDeSuscripcion(Exception):
    """Error de negocio del CU-03."""


class EmpresaInexistente(ErrorDeSuscripcion):
    pass


class EmpresaDeBaja(ErrorDeSuscripcion):
    pass


class PlanInexistente(ErrorDeSuscripcion):
    pass


class PlanNoOfrecido(ErrorDeSuscripcion):
    """El plan está desactivado (CU-02, 3a): no se asigna a nadie nuevo."""


class InicioEnElPasado(ErrorDeSuscripcion):
    pass


class SinSuscripcion(ErrorDeSuscripcion):
    """No hay suscripción que renovar, suspender o reactivar."""


class EstadoSinCambio(ErrorDeSuscripcion):
    """3b: ya está en el estado pedido."""


class VencioSuspendida(ErrorDeSuscripcion):
    """3b: venció mientras estaba suspendida; hay que renovarla."""


class CambioSimultaneo(ErrorDeSuscripcion):
    """Otro cambio dejó una suscripción vigente entre la lectura y el commit."""


# --------------------------------------------------------------------------
#  Lectura (pasos 1 y 2)
# --------------------------------------------------------------------------
def _empresa(db: Session, empresa_id: int) -> Empresa:
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise EmpresaInexistente(str(empresa_id))
    return empresa


def _actual(db: Session, empresa_id: int) -> Suscripcion | None:
    return db.scalar(
        select(Suscripcion).where(
            Suscripcion.empresa_id == empresa_id, Suscripcion.estado.in_(ESTADOS_ACTUALES)
        )
    )


def estado_efectivo(suscripcion: Suscripcion, hoy: date) -> str:
    """VIGENTE con la fecha pasada es VENCIDA, aunque E1 todavía no la marcó."""
    if suscripcion.estado in ESTADOS_ACTUALES and suscripcion.vencimiento < hoy:
        return VENCIDA
    return suscripcion.estado


def _suscripcion_out(s: Suscripcion, hoy: date) -> SuscripcionOut:
    return SuscripcionOut(
        id=s.id,
        plan_id=s.plan_id,
        plan_codigo=s.plan.codigo,
        plan_nombre=s.plan.nombre,
        inicio=s.inicio,
        vencimiento=s.vencimiento,
        estado=estado_efectivo(s, hoy),
        dias_restantes=(s.vencimiento - hoy).days,
    )


def _pago_out(p: PagoSimulado) -> PagoSimuladoOut:
    return PagoSimuladoOut(
        id=p.id,
        suscripcion_id=p.suscripcion_id,
        concepto=p.concepto,
        plan_nombre=p.plan.nombre,
        monto=float(p.monto),
        comprobante=p.comprobante,
        pagado_en=p.pagado_en,
    )


def obtener(db: Session, empresa_id: int) -> SuscripcionesOut:
    """Paso 2: la suscripción actual, el historial y los pagos de la empresa."""
    empresa = _empresa(db, empresa_id)
    hoy = tiempo.hoy()
    historial = list(
        db.scalars(
            select(Suscripcion)
            .where(Suscripcion.empresa_id == empresa_id)
            .order_by(Suscripcion.id.desc())
        )
    )
    pagos = db.scalars(
        select(PagoSimulado)
        .where(PagoSimulado.empresa_id == empresa_id)
        .order_by(PagoSimulado.pagado_en.desc(), PagoSimulado.id.desc())
    )
    actual = next((s for s in historial if s.estado in ESTADOS_ACTUALES), None)
    if actual is None and historial:
        actual = historial[0]
    return SuscripcionesOut(
        empresa_id=empresa.id,
        empresa=empresa.nombre,
        actual=_suscripcion_out(actual, hoy) if actual else None,
        historial=[_suscripcion_out(s, hoy) for s in historial],
        pagos=[_pago_out(p) for p in pagos],
    )


# --------------------------------------------------------------------------
#  El pago simulado (paso 4)
# --------------------------------------------------------------------------
def monto_de(plan: Plan) -> Decimal:
    """El precio mensual por la duración del plan, en meses de 30 días."""
    monto = plan.precio_mensual * plan.duracion_dias / DIAS_POR_MES
    return Decimal(monto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def registrar_pago(
    db: Session, suscripcion: Suscripcion, plan: Plan, concepto: str
) -> PagoSimulado:
    """Deja el pago de la suscripción. No hace commit.

    Lo usa también el alta del CU-01, que ya tiene fijada la empresa nueva.
    """
    pago = PagoSimulado(
        empresa_id=suscripcion.empresa_id,
        suscripcion_id=suscripcion.id,
        plan_id=plan.id,
        concepto=concepto,
        monto=monto_de(plan),
        comprobante=f"SIM-{tiempo.hoy():%Y%m%d}-{secrets.token_hex(3).upper()}",
    )
    db.add(pago)
    return pago


def _guardado(
    db: Session, empresa: Empresa, pago: PagoSimulado | None, excedidas=()
) -> SuscripcionGuardadaOut:
    estado = obtener(db, empresa.id)
    return SuscripcionGuardadaOut(
        **estado.model_dump(),
        pago=_pago_out(pago) if pago else None,
        excedidas=list(excedidas),
    )


def _confirmar(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if "uq_suscripcion_vigente_por_empresa" in str(error.orig):
            raise CambioSimultaneo() from error
        raise


# --------------------------------------------------------------------------
#  Asignar o cambiar el plan (flujo principal, pasos 3 a 6)
# --------------------------------------------------------------------------
def asignar_plan(db: Session, empresa_id: int, datos: AsignarPlanIn) -> SuscripcionGuardadaOut:
    """**Hace commit.** Cierra la actual y abre la nueva, con su pago."""
    empresa = _empresa(db, empresa_id)
    if empresa.estado == EMPRESA_DE_BAJA:
        raise EmpresaDeBaja(empresa.slug)
    plan = db.get(Plan, datos.plan_id)
    if plan is None:
        raise PlanInexistente(str(datos.plan_id))
    if not plan.activo:
        raise PlanNoOfrecido(plan.codigo)
    hoy = tiempo.hoy()
    inicio = datos.inicio or hoy
    if inicio < hoy:
        raise InicioEnElPasado(inicio.isoformat())

    # Paso 5: la anterior se cierra antes de abrir la nueva, en la misma
    # transacción; el flush ordena las sentencias para el índice único.
    anterior = _actual(db, empresa.id)
    if anterior is not None:
        anterior.estado = REEMPLAZADA
        db.flush()
    nueva = Suscripcion(
        empresa_id=empresa.id,
        plan_id=plan.id,
        inicio=inicio,
        vencimiento=inicio + timedelta(days=plan.duracion_dias),
        estado=VIGENTE,
    )
    db.add(nueva)
    db.flush()
    pago = registrar_pago(db, nueva, plan, "ALTA" if anterior is None else "CAMBIO")
    _confirmar(db)

    # 5a: lo que ya pasa los límites del plan nuevo. No se toca nada.
    excedidas = excedidas_en(db, plan, {empresa.id: empresa.nombre})
    return _guardado(db, empresa, pago, excedidas)


# --------------------------------------------------------------------------
#  3a Renovar
# --------------------------------------------------------------------------
def renovar(db: Session, empresa_id: int) -> SuscripcionGuardadaOut:
    """**Hace commit.** Extiende el vencimiento por la duración del plan.

    Desde el vencimiento actual, para no regalar ni quitar días. Si ya pasó,
    desde hoy: renovar una vencida no puede dejarla vencida. Una VENCIDA vuelve
    a VIGENTE; una SUSPENDIDA sigue suspendida (reactivarla es el 3b).
    """
    empresa = _empresa(db, empresa_id)
    if empresa.estado == EMPRESA_DE_BAJA:
        raise EmpresaDeBaja(empresa.slug)
    suscripcion = _actual(db, empresa.id) or db.scalar(
        select(Suscripcion)
        .where(Suscripcion.empresa_id == empresa.id, Suscripcion.estado == VENCIDA)
        .order_by(Suscripcion.id.desc())
        .limit(1)
    )
    if suscripcion is None:
        raise SinSuscripcion(empresa.slug)

    hoy = tiempo.hoy()
    plan = suscripcion.plan
    suscripcion.vencimiento = max(suscripcion.vencimiento, hoy) + timedelta(
        days=plan.duracion_dias
    )
    if suscripcion.estado == VENCIDA:
        suscripcion.estado = VIGENTE
    pago = registrar_pago(db, suscripcion, plan, "RENOVACION")
    _confirmar(db)
    return _guardado(db, empresa, pago)


# --------------------------------------------------------------------------
#  3b Suspender o reactivar
# --------------------------------------------------------------------------
def cambiar_estado(db: Session, empresa_id: int, *, suspender: bool) -> SuscripcionGuardadaOut:
    """**Hace commit.** Suspendida, la empresa solo consulta (RN-03)."""
    empresa = _empresa(db, empresa_id)
    suscripcion = _actual(db, empresa.id)
    if suscripcion is None:
        raise SinSuscripcion(empresa.slug)
    if suspender:
        if suscripcion.estado == SUSPENDIDA:
            raise EstadoSinCambio(SUSPENDIDA)
        suscripcion.estado = SUSPENDIDA
    else:
        if suscripcion.estado == VIGENTE:
            raise EstadoSinCambio(VIGENTE)
        if suscripcion.vencimiento < tiempo.hoy():
            raise VencioSuspendida(suscripcion.vencimiento.isoformat())
        suscripcion.estado = VIGENTE
    db.commit()
    return _guardado(db, empresa, None)


# --------------------------------------------------------------------------
#  E1 El proceso diario
# --------------------------------------------------------------------------
def marcar_vencidas(db: Session) -> VencimientoOut:
    """**Hace commit.** VIGENTE o SUSPENDIDA con la fecha pasada → VENCIDA.

    Idempotente: correrlo dos veces el mismo día no marca nada la segunda.
    """
    empresas = list(
        db.scalars(
            update(Suscripcion)
            .where(
                Suscripcion.estado.in_(ESTADOS_ACTUALES),
                Suscripcion.vencimiento < tiempo.hoy(),
            )
            .values(estado=VENCIDA)
            .returning(Suscripcion.empresa_id)
        )
    )
    nombres = sorted(
        db.scalars(select(Empresa.nombre).where(Empresa.id.in_(empresas))) if empresas else []
    )
    db.commit()
    return VencimientoOut(vencidas=len(empresas), empresas=nombres)
