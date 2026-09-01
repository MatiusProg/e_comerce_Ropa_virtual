"""
P5 - Catalogo Publico y Disponibilidad  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 2 (catalogo) / 3 (favoritos)

Casos de uso que realiza este paquete:
  CU-17 Consultar catalogo                          [ciclo 2]
  CU-18 Consultar ficha de producto                 [ciclo 2]
  CU-19 Consultar disponibilidad por sucursal       [ciclo 2]
  CU-20 Gestionar favoritos                         [ciclo 3]
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Favorito
#   - EventoNavegacion
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
