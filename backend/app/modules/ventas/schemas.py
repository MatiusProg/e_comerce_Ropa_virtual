"""
P7 - Ventas y Punto de Venta  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-26 Gestionar carrito de compras
  CU-27 Realizar pedido (la parte de pago vive en el modulo pagos)
  CU-29 Consultar historial de compras
  CU-30 Abrir y cerrar caja
  CU-31 Registrar venta presencial
  CU-32 Registrar devolucion
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
