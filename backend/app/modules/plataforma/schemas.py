"""
P12 - Plataforma SaaS  |  capa: esquemas (Pydantic)

CU-01 Gestionar empresas.
"""

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

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
    """Para el selector de plan del formulario de alta."""

    codigo: str
    nombre: str
    precio_mensual: float
    duracion_dias: int
