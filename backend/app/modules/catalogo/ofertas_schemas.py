"""
P16 - Ofertas / CU-31 y CU-32  |  capa: esquemas (contrato)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# =====================================================================
#  CU-31 · Precios mayoristas
# =====================================================================

class EscalonMayoristaOut(BaseModel):
    """Lo que la vitrina y la caja muestran: «desde 6 u., Bs 70 c/u»."""

    model_config = ConfigDict(from_attributes=True)

    cantidad_minima: int
    precio_unitario: Decimal


class MayoristaCrearIn(BaseModel):
    producto_id: int = Field(ge=1)
    cantidad_minima: int = Field(ge=2, le=10000)
    precio_unitario: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class MayoristaEditarIn(BaseModel):
    cantidad_minima: int | None = Field(default=None, ge=2, le=10000)
    precio_unitario: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)


class EstadoIn(BaseModel):
    activo: bool


class MayoristaOut(BaseModel):
    id: int
    producto_id: int
    producto: str
    #: El precio de lista del producto, para que la pantalla muestre el ahorro.
    precio_base: Decimal
    cantidad_minima: int
    precio_unitario: Decimal
    activo: bool


class PaginaMayoristas(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[MayoristaOut]


# =====================================================================
#  CU-32 · Fuera de temporada
# =====================================================================

class ReglaIn(BaseModel):
    activa: bool
    dias_desde_fin: int = Field(ge=0, le=730)
    existencia_minima: int = Field(ge=1, le=100000)
    porcentaje: Decimal = Field(gt=0, le=90, max_digits=5, decimal_places=2)


class ReglaOut(BaseModel):
    activa: bool
    dias_desde_fin: int
    existencia_minima: int
    porcentaje: Decimal
    #: Que la regla nunca se guardo y estos son los valores por omision.
    por_omision: bool = False


class CandidataOut(BaseModel):
    """Un producto que cumple el factor de RF-57, y lo que pasa con el."""

    producto_id: int
    producto: str
    temporada: str
    fin_de_temporada: date
    dias_desde_fin: int
    disponible: int
    #: NUEVA: se le crearia la oferta. VIGENTE: ya la tiene encendida.
    #: APAGADA: el Administrador la apago y no se vuelve a crear (RN-16).
    situacion: str
    promocion_id: int | None = None


class AplicacionOut(BaseModel):
    """El resumen de una corrida de CU-32. Correrla dos veces no duplica nada."""

    hoy: date
    regla_activa: bool
    creadas: int
    cerradas: int
    ya_vigentes: int
    apagadas_por_admin: int
    candidatas: list[CandidataOut]
