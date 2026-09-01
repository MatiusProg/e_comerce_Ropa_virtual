"""
P11 - Reportes y Tablero  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-36 Consultar tablero de indicadores
  CU-37 Generar reportes de gestion (PDF / Excel)
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

# TODO: implementar las reglas de negocio de este paquete.
