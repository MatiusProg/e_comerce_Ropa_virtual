"""
P12 - Plataforma SaaS  |  CU-05 Verificar límites y funciones del plan

Es la clase control `VerificadorPlan` del 3.2. Antes de una operación
controlada comprueba, en este orden, lo que dice la ficha del CU-05:

  2. que la empresa tenga una suscripción vigente      (2a: sin_suscripcion)
  3. que su plan incluya la función                    (3a: plan_limit)
  4. que lo usado no llegue al límite o al cupo        (4a: plan_limit)

El control vive en el backend (RF-09): ocultar el botón en la interfaz no
alcanza. Los casos de uso que lo incluyen no lo llaman a mano: declaran la
dependencia de FastAPI (`requiere_funcion`, `requiere_limite`, `requiere_cupo`,
en app/core/dependencies.py) y el rechazo sale solo.

Todo trabaja sobre la empresa de la sesión, que ya fijó el RLS: la del personal
o, para el cliente, la de la tienda que está mirando (una foto con IA del
probador se descuenta del cupo de la tienda, no del cliente).

Al bajar de plan no se borra nada (RN-04): lo que ya existe se conserva, y
solo se impide crear por encima del nuevo límite. Por eso se compara `uso >=
limite` y no `>`: con 3 sucursales y un límite de 2, no se crea la cuarta,
pero las tres siguen funcionando.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.organizacion.models import Empleado, Sucursal
from app.modules.plataforma.models import ConsumoCupo, Plan, Suscripcion

SUSCRIPCION_VIGENTE = "VIGENTE"

#: Código del error que la interfaz reconoce para ofrecer ver los planes.
CODIGO_PLAN = "plan_limit"
CODIGO_SIN_SUSCRIPCION = "sin_suscripcion"

#: Nombre legible de cada función, para el mensaje del 3a.
FUNCIONES = {
    "reportes_ia": "los reportes con IA",
    "correo": "los avisos por correo",
    "ia_cliente": "las recomendaciones y el asistente con IA",
    "marca_propia": "la tienda con la marca de la empresa",
    "traspasos_sugeridos": "los traspasos sugeridos",
    "foto_ia": "la foto realista con IA",
    "analitica_ml": "la analítica con ML",
    "exportar_datos": "la exportación completa de los datos",
}


def _contar_sucursales(db: Session) -> int:
    return db.scalar(select(func.count(Sucursal.id)).where(Sucursal.activa.is_(True))) or 0


def _contar_empleados(db: Session) -> int:
    return db.scalar(select(func.count(Empleado.id)).where(Empleado.fecha_baja.is_(None))) or 0


@dataclass(frozen=True)
class Limite:
    columna: str
    contar: Callable[[Session], int]
    nombre: str


#: Los límites del plan: la columna `max_*` y cómo se cuenta lo que ya hay.
LIMITES = {
    "sucursales": Limite("max_sucursales", _contar_sucursales, "sucursales activas"),
    "empleados": Limite("max_empleados", _contar_empleados, "empleados activos"),
}

#: Los cupos mensuales: la columna `cupo_*` y su nombre. Se cuentan en
#: `consumo_cupo`.
CUPOS = {
    "reportes_ia": ("cupo_reportes_ia", "reportes con IA"),
    "fotos_ia": ("cupo_fotos_ia", "fotos con IA"),
}


# --------------------------------------------------------------------------
#  Errores
# --------------------------------------------------------------------------
class RechazoDelPlan(Exception):
    """El plan no permite la operación. Se responde 403 sin cambiar nada."""

    codigo = CODIGO_PLAN

    def __init__(self, mensaje: str, *, limite: int | None = None, uso: int | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.limite = limite
        self.uso = uso

    def cuerpo(self) -> dict:
        cuerpo: dict = {"detail": self.mensaje, "codigo": self.codigo}
        if self.limite is not None:
            cuerpo["limite"] = self.limite
            cuerpo["uso"] = self.uso
        return cuerpo


class SinSuscripcionVigente(RechazoDelPlan):
    """2a: la suscripción venció o está suspendida; la empresa solo consulta (RN-03)."""

    codigo = CODIGO_SIN_SUSCRIPCION

    def __init__(self):
        super().__init__(
            "La suscripción de la empresa no está vigente: solo se puede consultar. "
            "Contacte a la plataforma para renovarla."
        )


# --------------------------------------------------------------------------
#  Verificaciones
# --------------------------------------------------------------------------
def suscripcion_vigente(db: Session) -> Suscripcion | None:
    """Paso 2: la suscripción vigente de la empresa de la sesión.

    Vigente es estado VIGENTE y sin pasar el vencimiento. El vencimiento se mira
    por fecha y no se espera a que alguien marque la fila como VENCIDA: si no,
    una suscripción vencida seguiría sirviendo hasta que corriera ese proceso.
    """
    return db.scalar(
        select(Suscripcion).where(
            Suscripcion.estado == SUSCRIPCION_VIGENTE,
            Suscripcion.vencimiento >= tiempo.hoy(),
        )
    )


def plan_vigente(db: Session) -> Plan:
    """El plan de la suscripción vigente, o `SinSuscripcionVigente` (2a)."""
    suscripcion = suscripcion_vigente(db)
    if suscripcion is None:
        raise SinSuscripcionVigente()
    return suscripcion.plan


def verificar_funcion(db: Session, funcion: str) -> None:
    """Paso 3: que el plan incluya la función (3a)."""
    plan = plan_vigente(db)
    if not plan.funciones.get(funcion):
        nombre = FUNCIONES.get(funcion, funcion)
        raise RechazoDelPlan(
            f"El plan {plan.nombre} no incluye {nombre}. Consulte los planes para cambiarlo."
        )


def verificar_limite(db: Session, recurso: str) -> None:
    """Paso 4 para un límite: que lo que hay no llegue al máximo del plan (4a)."""
    limite = LIMITES[recurso]
    plan = plan_vigente(db)
    maximo = getattr(plan, limite.columna)
    if maximo is None:  # ilimitado
        return
    uso = limite.contar(db)
    if uso >= maximo:
        raise RechazoDelPlan(
            f"El plan {plan.nombre} permite hasta {maximo} {limite.nombre} y ya tiene {uso}.",
            limite=maximo,
            uso=uso,
        )


def _periodo():
    return tiempo.hoy().replace(day=1)


def uso_del_mes(db: Session, cupo: str) -> int:
    """Lo que la empresa de la sesión lleva usado del cupo este mes."""
    return (
        db.scalar(
            select(ConsumoCupo.usados).where(
                ConsumoCupo.recurso == cupo, ConsumoCupo.periodo == _periodo()
            )
        )
        or 0
    )


def verificar_cupo(db: Session, cupo: str) -> None:
    """Paso 4 para un cupo mensual: que quede al menos uno (4a, RN-11)."""
    columna, nombre = CUPOS[cupo]
    plan = plan_vigente(db)
    maximo = getattr(plan, columna)
    if maximo is None:  # ilimitado
        return
    uso = uso_del_mes(db, cupo)
    if uso >= maximo:
        raise RechazoDelPlan(
            f"La empresa ya usó sus {maximo} {nombre} del mes que incluye el plan {plan.nombre}.",
            limite=maximo,
            uso=uso,
        )


def consumir_cupo(db: Session, cupo: str) -> int:
    """Descuenta uno del cupo del mes y devuelve lo usado. No hace commit.

    Se llama DESPUÉS de que la operación salió bien: una foto que falló no
    debería gastar el cupo. Vuelve a verificar y suma en una sola sentencia,
    con la condición en el `ON CONFLICT`, para que dos pedidos simultáneos no
    pasen los dos con el último lugar.
    """
    verificar_cupo(db, cupo)
    columna, _ = CUPOS[cupo]
    maximo = getattr(plan_vigente(db), columna)
    sentencia = insert(ConsumoCupo).values(recurso=cupo, periodo=_periodo(), usados=1)
    sentencia = sentencia.on_conflict_do_update(
        index_elements=[ConsumoCupo.empresa_id, ConsumoCupo.recurso, ConsumoCupo.periodo],
        set_={"usados": ConsumoCupo.usados + 1},
        where=None if maximo is None else ConsumoCupo.usados < maximo,
    ).returning(ConsumoCupo.usados)
    usados = db.scalar(sentencia)
    if usados is None:  # otro pedido se llevó el último lugar
        verificar_cupo(db, cupo)  # rechaza con el límite y el uso
        raise RechazoDelPlan("El cupo del mes se agotó.")
    return usados
