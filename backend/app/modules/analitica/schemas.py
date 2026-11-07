"""
P19 - Analítica con ML / CU-29 y CU-30  |  capa: contratos

Las métricas y los parámetros viajan como diccionarios: cada modelo tiene las
suyas (MAE y R² uno, silueta el otro) y el dashboard las muestra por nombre.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EntrenarIn(BaseModel):
    #: La misma semilla da los mismos datos sintéticos y el mismo modelo.
    semilla: int = Field(2026, ge=0, le=1_000_000)


class EntrenamientoOut(BaseModel):
    id: int
    entrenado_en: datetime
    parametros: dict
    metricas: dict
    filas_entrenamiento: int
    filas_reales: int
    filas_sinteticas: int
    duracion_ms: int


class SegmentoOut(BaseModel):
    grupo: int
    nombre: str
    accion: str
    clientes: int
    clientes_reales: int
    recencia_dias: float
    compras: float
    monto: float


class ResumenOut(BaseModel):
    entrenado: bool
    demanda: EntrenamientoOut | None
    segmentos: EntrenamientoOut | None
    #: semana_prevista, predicciones, serie_validacion, historia, importancia
    predicciones: dict | None
    grupos: list[SegmentoOut]


class HistorialOut(BaseModel):
    id: int
    tipo: str
    entrenado_en: datetime
    metricas: dict
    filas_entrenamiento: int
    filas_reales: int
    filas_sinteticas: int
    duracion_ms: int
    entrenado_por: str | None


class ClienteSegmentoOut(BaseModel):
    cliente_id: int
    cliente: str
    segmento: str
    recencia_dias: float
    compras: int
    monto: float
