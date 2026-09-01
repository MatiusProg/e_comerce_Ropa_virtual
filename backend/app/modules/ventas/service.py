"""
P7 - Ventas y Punto de Venta  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-26 Gestionar carrito de compras
  CU-27 Realizar pedido (la parte de pago vive en el modulo pagos)
  CU-29 Consultar historial de compras
  CU-30 Abrir y cerrar caja
  CU-31 Registrar venta presencial
  CU-32 Registrar devolucion
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

# TODO: implementar las reglas de negocio de este paquete.
