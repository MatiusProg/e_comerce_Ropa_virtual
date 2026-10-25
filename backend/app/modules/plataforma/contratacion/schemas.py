"""
P12 - Plataforma SaaS / CU-11  |  capa: esquemas (Pydantic)

Lo que ve y manda la empresa interesada, sin sesión. No se expone nada interno:
ni los ids de los planes, ni cuántas empresas tiene cada uno.
"""

import re
from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.modules.plataforma.schemas import AdministradorEmpresaIn, EmpresaCrearIn
from app.modules.seguridad.schemas import CONTRASENA_LONGITUD_MINIMA

_TIENE_LETRA = re.compile(r"[A-Za-z]")
_TIENE_DIGITO = re.compile(r"\d")


class FuncionPublicaOut(BaseModel):
    clave: str
    nombre: str
    incluida: bool


class PlanPublicoOut(BaseModel):
    """Paso 2: un plan que se ofrece, con su precio y lo que incluye."""

    codigo: str
    nombre: str
    precio_mensual: float
    duracion_dias: int
    #: `None` es ilimitado.
    max_sucursales: int | None
    max_empleados: int | None
    cupo_reportes_ia: int | None
    cupo_fotos_ia: int | None
    bitacora_dias: int | None
    funciones: list[FuncionPublicaOut]


class CiudadPublicaOut(BaseModel):
    id: int
    nombre: str
    departamento: str


class SlugOut(BaseModel):
    """Paso 5 y alternativo 5a: si el slug está libre y, si no, cuáles sí."""

    slug: str
    disponible: bool
    sugerencias: list[str]


class AdministradorContratoIn(AdministradorEmpresaIn):
    """El administrador elige su contraseña: es él quien contrata."""

    contrasena: str = Field(min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128)

    @field_validator("contrasena")
    @classmethod
    def _contrasena_fuerte(cls, valor: str) -> str:
        if not _TIENE_LETRA.search(valor) or not _TIENE_DIGITO.search(valor):
            raise ValueError("La contraseña debe incluir al menos una letra y un número.")
        return valor


class PagoSimuladoIn(BaseModel):
    """Paso 6: el pago por QR simulado.

    El código de operación es el que mostraría la app del banco al pagar. Como
    las tarjetas de prueba de una pasarela, `000000` simula un pago rechazado
    (alternativo 6a).
    """

    metodo: str = Field(default="QR", pattern="^QR$")
    codigo_operacion: str = Field(pattern=r"^\d{6}$")


class ContratarIn(EmpresaCrearIn):
    """Pasos 3 y 4: el plan, la empresa, su sucursal, su administrador y el pago."""

    administrador: AdministradorContratoIn
    pago: PagoSimuladoIn


class ComprobanteOut(BaseModel):
    comprobante: str
    metodo: str
    monto: float
    pagado_en: datetime


class ContratacionOut(BaseModel):
    """Pasos 6 a 8: el comprobante y con qué datos iniciar sesión."""

    empresa: str
    slug: str
    plan: str
    vencimiento: date
    administrador_correo: str
    correo_enviado: bool
    pago: ComprobanteOut
