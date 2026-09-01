"""
P11 - Reportes y Tablero  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-36 Consultar tablero de indicadores
  CU-37 Generar reportes de gestion (PDF / Excel)
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
