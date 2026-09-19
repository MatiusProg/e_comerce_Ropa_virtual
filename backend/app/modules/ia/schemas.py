"""
P10 - Inteligencia Artificial / CU-33  |  capa: contratos
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PrendaSugeridaOut(BaseModel):
    producto_id: int
    nombre: str
    categoria: str
    precio_desde: Decimal | None = None
    imagen_url: str | None = None

    #: Una linea que explica por que se sugiere. **Vacia cuando el modelo no
    #: estuvo disponible** y la lista salio por popularidad: la pantalla
    #: entonces no dibuja la etiqueta, en vez de mostrar un texto inventado.
    motivo: str = ""


class RecomendacionesOut(BaseModel):
    prendas: list[PrendaSugeridaOut]

    #: `gemini` cuando las ordeno el modelo, `popularidad` cuando no.
    #:
    #: Viaja hasta la pantalla a proposito: **una sugerencia hecha por un
    #: modelo tiene que poder decir que lo es.** Presentarla sin distinguir
    #: seria atribuirle a la tienda un criterio que no eligio.
    motor: str

    generada_en: datetime
