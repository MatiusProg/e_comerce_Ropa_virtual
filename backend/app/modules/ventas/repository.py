"""
P7 - Ventas y Punto de Venta  |  capa: repositorio (consultas, sin logica de negocio)

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

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.

# TODO: implementar las consultas de este paquete.
