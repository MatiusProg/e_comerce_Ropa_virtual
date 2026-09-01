"""
P3 - Catalogo  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1 (maestros) / 2 (productos) / 3 (promociones)

Casos de uso que realiza este paquete:
  CU-08 Gestionar categorias, tallas y colores      [ciclo 1]
  CU-09 Gestionar temporadas y colecciones          [ciclo 1]
  CU-10 Gestionar productos y variantes             [ciclo 2]
  CU-11 Gestionar imagenes de producto              [ciclo 2]
  CU-12 Gestionar promociones                       [ciclo 3]
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.

# TODO: implementar las consultas de este paquete.
