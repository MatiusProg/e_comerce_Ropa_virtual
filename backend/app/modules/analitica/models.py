"""
P19 - Analítica con ML / CU-29 y CU-30  |  capa: modelo

`modelo_analitica`: cada entrenamiento de un modelo de la empresa.

- DEMANDA: el supervisado. Predice las unidades que venderá cada producto la
  semana que viene.
- SEGMENTOS: el no supervisado. Agrupa a los clientes por recencia,
  frecuencia y monto (RFM).
- ANOMALIAS (aporte propio, 0043): Isolation Forest sobre los turnos de caja
  y las devoluciones. Su `resultado` guarda lo marcado y si ya se revisó.

Por cada entrenamiento se guardan los parámetros, las métricas de la
validación, el tamaño del conjunto de datos (cuántas filas reales y cuántas
sintéticas), el resultado listo para el dashboard (CU-30) y el modelo
serializado. El modelo va EN LA BASE y no en disco: el disco de Railway no
sobrevive a un despliegue.

Se conservan los últimos `CONSERVAR` de cada tipo.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DeEmpresa

TIPOS_MODELO = ("DEMANDA", "SEGMENTOS", "ANOMALIAS")

#: Cuántos entrenamientos de cada tipo se conservan.
CONSERVAR = 5


class ModeloAnalitica(DeEmpresa, Base):
    __tablename__ = "modelo_analitica"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('" + "', '".join(TIPOS_MODELO) + "')", name="tipo_valido"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12), index=True)
    #: Qué algoritmo y con qué hiperparámetros, la semilla y las variables.
    parametros: Mapped[dict] = mapped_column(JSONB)
    #: MAE, RMSE y R² del supervisado; silueta e inercia del no supervisado.
    metricas: Mapped[dict] = mapped_column(JSONB)
    #: Lo que muestra el dashboard: predicciones, segmentos y series.
    resultado: Mapped[dict] = mapped_column(JSONB)
    filas_entrenamiento: Mapped[int] = mapped_column(Integer)
    #: Las filas que salieron de datos reales de la empresa.
    filas_reales: Mapped[int] = mapped_column(Integer)
    #: Las que completó el generador de datos sintéticos.
    filas_sinteticas: Mapped[int] = mapped_column(Integer)
    duracion_ms: Mapped[int] = mapped_column(Integer)
    #: El modelo entrenado (joblib). Solo lo lee este mismo módulo.
    modelo: Mapped[bytes] = mapped_column(LargeBinary)
    #: Nulo si quien lo entrenó ya no existe.
    entrenado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="SET NULL")
    )
    entrenado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
