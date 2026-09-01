"""
P6 - Reservas  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.

# TODO: implementar las consultas de este paquete.
