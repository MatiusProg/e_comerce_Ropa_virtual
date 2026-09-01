"""
P3 - Catalogo  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1 (maestros) / 2 (productos) / 3 (promociones)

Casos de uso que realiza este paquete:
  CU-08 Gestionar categorias, tallas y colores      [ciclo 1]
  CU-09 Gestionar temporadas y colecciones          [ciclo 1]
  CU-10 Gestionar productos y variantes             [ciclo 2]
  CU-11 Gestionar imagenes de producto              [ciclo 2]
  CU-12 Gestionar promociones                       [ciclo 3]
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Categoria
#   - Talla
#   - Color
#   - Temporada
#   - Coleccion
#   - Producto
#   - VarianteProducto
#   - ImagenProducto
#   - Promocion
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
