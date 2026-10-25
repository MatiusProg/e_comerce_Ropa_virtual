"""
P12 - Plataforma SaaS  |  capa: esquemas (Pydantic)

CU-01 Gestionar empresas y CU-02 Gestionar planes.
"""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.modules.plataforma.verificador import FUNCIONES

#: El slug va en el login y en la dirección de la tienda: minúsculas, números y
#: guiones simples. Es la misma regla que el CHECK de la tabla `empresa`.
PATRON_SLUG = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class SucursalPrincipalIn(BaseModel):
    """La primera sucursal de la empresa: sin ella, la empresa no puede vender."""

    ciudad_id: int
    nombre: str = Field(default="Casa matriz", min_length=1, max_length=80)
    direccion: str = Field(min_length=1, max_length=200)


class AdministradorEmpresaIn(BaseModel):
    """El administrador de la empresa. La contraseña la genera el sistema."""

    correo: EmailStr
    nombres: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=80)


class EmpresaCrearIn(BaseModel):
    """Paso 3 del flujo principal del CU-01."""

    nombre: str = Field(min_length=1, max_length=120)
    razon_social: str | None = Field(default=None, max_length=160)
    nit: str | None = Field(default=None, max_length=30)
    slug: str = Field(min_length=2, max_length=40, pattern=PATRON_SLUG)
    correo_contacto: EmailStr | None = None
    plan_codigo: str = Field(min_length=1, max_length=20)
    sucursal: SucursalPrincipalIn
    administrador: AdministradorEmpresaIn

    @field_validator("slug", mode="before")
    @classmethod
    def _slug_en_minusculas(cls, valor):
        return valor.strip().lower() if isinstance(valor, str) else valor


class EmpresaEditarIn(BaseModel):
    """Flujo alternativo 3a. El slug no está: no se cambia después del alta (RN-14)."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    razon_social: str | None = Field(default=None, max_length=160)
    nit: str | None = Field(default=None, max_length=30)
    correo_contacto: EmailStr | None = None


class SuscripcionResumenOut(BaseModel):
    plan_codigo: str
    plan_nombre: str
    inicio: date
    vencimiento: date
    estado: str


class EmpresaOut(BaseModel):
    """Una fila de la lista de empresas (paso 2 del flujo principal)."""

    id: int
    nombre: str
    razon_social: str | None
    nit: str | None
    slug: str
    correo_contacto: str | None
    estado: str
    creado_en: datetime
    suscripcion: SuscripcionResumenOut | None
    sucursales: int
    usuarios: int


class EmpresaCreadaOut(EmpresaOut):
    """El alta. La contraseña temporal se devuelve UNA vez, para el caso en que
    el correo no llegue: después no hay forma de verla."""

    administrador_correo: str
    contrasena_temporal: str
    correo_enviado: bool


class PlanOut(BaseModel):
    """Un plan con todo lo que define (CU-02, paso 2).

    El selector del alta de empresas (CU-01) usa solo los primeros campos.
    """

    id: int
    codigo: str
    nombre: str
    precio_mensual: float
    duracion_dias: int
    max_sucursales: int | None
    max_empleados: int | None
    cupo_reportes_ia: int | None
    cupo_fotos_ia: int | None
    funciones: list[str]
    #: Cuántos días de bitácora ve la empresa; None es todo el historial.
    bitacora_dias: int | None
    activo: bool
    #: Empresas con una suscripción vigente o suspendida en este plan.
    empresas: int


class PlanIn(BaseModel):
    """Paso 3 del CU-02. Los límites vacíos son ilimitados (paso 4).

    El código no se pide: sale del nombre en el alta y no cambia después,
    porque lo usan el alta de empresas y la página de planes.
    """

    nombre: str = Field(min_length=1, max_length=40)
    precio_mensual: float = Field(ge=0, le=99_999_999)
    duracion_dias: int = Field(ge=1, le=366)
    max_sucursales: int | None = Field(default=None, ge=1)
    max_empleados: int | None = Field(default=None, ge=1)
    # Un cupo en 0 es «no incluye»: el Básico viene así de la migración.
    cupo_reportes_ia: int | None = Field(default=None, ge=0)
    cupo_fotos_ia: int | None = Field(default=None, ge=0)
    bitacora_dias: int | None = Field(default=None, ge=1)
    funciones: list[str] = Field(default_factory=list)

    @field_validator("nombre", mode="before")
    @classmethod
    def _sin_espacios(cls, valor):
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("funciones")
    @classmethod
    def _funciones_conocidas(cls, valor: list[str]) -> list[str]:
        desconocidas = sorted(set(valor) - FUNCIONES.keys())
        if desconocidas:
            raise ValueError(f"Funciones desconocidas: {', '.join(desconocidas)}.")
        return sorted(set(valor))


class EmpresaExcedidaOut(BaseModel):
    """Alternativo 5a: una empresa que ya tiene más de lo que el plan permite."""

    empresa: str
    recurso: str
    uso: int
    limite: int


class PlanGuardadoOut(PlanOut):
    """El plan guardado, con las empresas que quedaron por encima de un límite.

    No se les borra nada: solo no pueden crear más (RN-04).
    """

    excedidas: list[EmpresaExcedidaOut] = []


class FuncionOut(BaseModel):
    """Una función que el plan puede incluir, para las casillas del formulario."""

    clave: str
    nombre: str


# --- CU-03 Suscripciones ------------------------------------------------------


class SuscripcionOut(BaseModel):
    """Una suscripción del historial de la empresa."""

    id: int
    plan_id: int
    plan_codigo: str
    plan_nombre: str
    inicio: date
    vencimiento: date
    #: VIGENTE, SUSPENDIDA, VENCIDA o REEMPLAZADA. Una VIGENTE cuya fecha ya
    #: pasó sale como VENCIDA aunque el proceso diario (E1) no la haya marcado.
    estado: str
    dias_restantes: int


class PagoSimuladoOut(BaseModel):
    id: int
    suscripcion_id: int
    concepto: str
    plan_nombre: str
    monto: float
    comprobante: str
    pagado_en: datetime


class SuscripcionesOut(BaseModel):
    """Paso 2: la suscripción actual y el historial de la empresa."""

    empresa_id: int
    empresa: str
    #: La VIGENTE o SUSPENDIDA; si no hay, la última (vencida o reemplazada).
    actual: SuscripcionOut | None
    historial: list[SuscripcionOut]
    pagos: list[PagoSimuladoOut]


class AsignarPlanIn(BaseModel):
    """Paso 3: el plan y la fecha de inicio (hoy si no se indica)."""

    plan_id: int
    inicio: date | None = None


class SuscripcionGuardadaOut(SuscripcionesOut):
    """El estado actualizado, el pago registrado y el aviso del 5a.

    `excedidas` lista lo que la empresa ya tiene por encima de los límites del
    plan nuevo: no se borra nada, solo no puede crear más (RN-04).
    """

    pago: PagoSimuladoOut | None = None
    excedidas: list[EmpresaExcedidaOut] = []


class VencimientoOut(BaseModel):
    """E1: lo que hizo el proceso diario."""

    vencidas: int
    empresas: list[str]
