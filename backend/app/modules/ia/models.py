"""
P10 - Inteligencia Artificial  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-33 Recibir recomendaciones de prendas
  CU-34 Conversar con el asistente virtual
  CU-35 Generar reporte por comando de voz
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Recomendacion
#   - ConversacionAsistente
#   - SolicitudReporteIA
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
