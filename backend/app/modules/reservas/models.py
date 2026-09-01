"""
P6 - Reservas  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Reserva
#   - DetalleReserva
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
