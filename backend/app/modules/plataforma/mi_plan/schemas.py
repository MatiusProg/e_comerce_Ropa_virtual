"""
P12 - Plataforma SaaS / CU-04  |  capa: esquemas de salida (Pydantic)

2do parcial. Caso de uso: CU-04 Consultar plan y consumo.

Todo es de salida: el caso de uso no modifica ningún dato.
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FuncionOut(BaseModel):
    """Una función del plan, con su nombre para la pantalla (paso 3)."""

    codigo: str
    etiqueta: str
    incluida: bool
    #: Para las funciones que no son sí o no (los días de bitácora, la
    #: frecuencia de las copias): el valor en palabras. None si no aplica.
    detalle: str | None = None


class LimiteOut(BaseModel):
    """Un límite o un cupo con lo que la empresa ya usó, por ejemplo 2 de 10.

    `limite` None significa ilimitado. `usado` None significa que ese consumo
    todavía no se mide: los cupos de IA se cuentan desde los casos de uso que
    los gastan (CU-27 y CU-38), que aún no existen.
    """

    codigo: str
    etiqueta: str
    usado: int | None
    limite: int | None
    #: True cuando ya no se puede crear más (usado >= limite).
    alcanzado: bool


class PlanOut(BaseModel):
    """Un plan con sus límites y funciones, para mostrarlo y compararlo."""

    id: int
    codigo: str
    nombre: str
    precio_mensual: Decimal
    duracion_dias: int
    max_sucursales: int | None
    max_empleados: int | None
    cupo_reportes_ia: int | None
    cupo_fotos_ia: int | None
    funciones: list[FuncionOut]


class SuscripcionOut(BaseModel):
    """El estado de la suscripción y sus fechas (paso 2)."""

    estado: str
    inicio: date
    vencimiento: date
    #: Negativo si ya venció.
    dias_restantes: int
    #: Flujo 2a: vencida o suspendida, la empresa solo consulta (RN-03).
    solo_consulta: bool


class MiPlanOut(BaseModel):
    """Lo que muestra la pantalla «Mi plan»."""

    empresa: str
    slug: str
    #: None si la empresa nunca tuvo una suscripción.
    suscripcion: SuscripcionOut | None
    plan: PlanOut | None
    limites: list[LimiteOut]
    cupos: list[LimiteOut]
    #: Paso 4: los planes activos, para comparar.
    otros_planes: list[PlanOut]
