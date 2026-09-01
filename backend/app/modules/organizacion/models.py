"""
P2 - Organizacion  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Ciudad
#   - Sucursal
#   - Empleado
#   - Proveedor
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
