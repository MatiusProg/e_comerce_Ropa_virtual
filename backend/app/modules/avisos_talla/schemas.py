"""Aporte propio · «Avísame cuando llegue mi talla»  |  capa: contratos."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AvisoIn(BaseModel):
    variante_id: int = Field(ge=1)


class AvisoOut(BaseModel):
    id: int
    variante_id: int
    producto_id: int | None
    producto: str
    talla: str
    color: str
    sku: str
    imagen_url: str | None = None
    #: False si la prenda se retiró del catálogo después de pedir el aviso.
    ofrecible: bool
    estado: Literal["ESPERANDO", "AVISADO"]
    creado_en: datetime
    notificado_en: datetime | None = None


class DemandaOut(BaseModel):
    """Una talla y color agotados, con cuántos clientes la esperan."""

    variante_id: int
    producto_id: int
    producto: str
    talla: str
    color: str
    sku: str
    clientes: int
    esperando_desde: datetime
