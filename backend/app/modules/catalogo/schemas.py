"""
P3 - Catalogo  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 1 (maestros) / 2 (productos) / 3 (promociones)

Casos de uso que realiza este paquete:
  CU-08 Gestionar categorias, tallas y colores      [ciclo 1]
  CU-09 Gestionar temporadas y colecciones          [ciclo 1]
  CU-10 Gestionar productos y variantes             [ciclo 2]
  CU-11 Gestionar imagenes de producto              [ciclo 2]
  CU-12 Gestionar promociones                       [ciclo 3]
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
