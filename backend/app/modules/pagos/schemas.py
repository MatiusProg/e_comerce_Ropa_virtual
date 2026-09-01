"""
P8 - Pagos  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Iniciar el pago electronico contra la pasarela
  CU-28 Confirmar pago del pedido (webhook firmado e idempotente)
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
