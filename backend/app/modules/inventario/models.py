"""
P4 - Inventario  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Existencia
#   - MovimientoInventario
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
