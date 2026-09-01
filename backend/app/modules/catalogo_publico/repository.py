"""
P5 - Catalogo Publico y Disponibilidad  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2 (catalogo) / 3 (favoritos)

Casos de uso que realiza este paquete:
  CU-17 Consultar catalogo                          [ciclo 2]
  CU-18 Consultar ficha de producto                 [ciclo 2]
  CU-19 Consultar disponibilidad por sucursal       [ciclo 2]
  CU-20 Gestionar favoritos                         [ciclo 3]
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.

# TODO: implementar las consultas de este paquete.
