"""
P8 - Pagos  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Iniciar el pago electronico contra la pasarela
  CU-28 Confirmar pago del pedido (webhook firmado e idempotente)
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Pago
#   - TransaccionPasarela
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
