"""
P10 - Inteligencia Artificial  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-33 Recibir recomendaciones de prendas
  CU-34 Conversar con el asistente virtual      [sin empezar]
  CU-35 Generar reporte por comando de voz      [sin empezar]

Solo esta declarada `Recomendacion`. `ConversacionAsistente` y
`SolicitudReporteIA` siguen sin escribirse **a proposito**: CU-34 y CU-35 son
los que el plan deja caer primero si falta tiempo, y una tabla vacia en
produccion es peor que ninguna --- promete algo que no existe.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Auditoria, Base


class Recomendacion(Base, Auditoria):
    """La recomendacion VIGENTE de un cliente. Ver la migracion 0013.

    Una fila por cliente, sin historial: lo que interesa es la que esta en uso.
    """

    __tablename__ = "recomendacion"
    __table_args__ = (
        UniqueConstraint("cliente_id", name="uq_recomendacion_cliente_id"),
        CheckConstraint(
            "jsonb_typeof(sugerencias) = 'array'", name="sugerencias_es_lista"
        ),
        CheckConstraint("length(motor) > 0", name="motor"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE"), unique=True
    )
    generada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

    #: Con que se produjo: el nombre del proveedor, o `popularidad` cuando el
    #: modelo no estaba disponible. Sirve para saber, mirando produccion, si
    #: todo el mundo esta recibiendo el resultado degradado --- que se ve igual
    #: de bien y no avisa de nada.
    motor: Mapped[str] = mapped_column(String(30))

    #: `[{"producto_id": 12, "motivo": "..."}]`.
    sugerencias: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
