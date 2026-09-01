"""
P7 - Ventas y Punto de Venta  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-26 Gestionar carrito de compras
  CU-27 Realizar pedido (la parte de pago vive en el modulo pagos)
  CU-29 Consultar historial de compras
  CU-30 Abrir y cerrar caja
  CU-31 Registrar venta presencial
  CU-32 Registrar devolucion
"""
from app.db.base import Base  # noqa: F401

# Clases de entidad de este paquete (ver docs/04-analisis-arquitectura.md):
#   - Carrito
#   - ItemCarrito
#   - Venta
#   - DetalleVenta
#   - Comprobante
#   - Caja
#   - TurnoCaja
#   - Devolucion
# TODO: declarar los modelos SQLAlchemy y generar la migracion con Alembic.
