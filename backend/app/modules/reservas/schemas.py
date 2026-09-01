"""
P6 - Reservas  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
