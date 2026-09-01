"""
P4 - Inventario  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.

# TODO: implementar las consultas de este paquete.
