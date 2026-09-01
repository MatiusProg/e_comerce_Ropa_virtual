"""
P1 - Seguridad y Usuarios  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Usuario
#   - Rol
#   - Permiso
#   - Cliente
#   - SesionToken
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
