"""
P5 - Catalogo Publico y Disponibilidad  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2 (catalogo) / 3 (favoritos)

Casos de uso que realiza este paquete:
  CU-17 Consultar catalogo                          [ciclo 2]
  CU-18 Consultar ficha de producto                 [ciclo 2]
  CU-19 Consultar disponibilidad por sucursal       [ciclo 2]
  CU-20 Gestionar favoritos                         [ciclo 3]
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
