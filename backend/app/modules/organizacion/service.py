"""
P2 - Organizacion  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

# TODO: implementar las reglas de negocio de este paquete.
