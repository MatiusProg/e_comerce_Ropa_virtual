"""
P3 - Catalogo  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1 (maestros) / 2 (productos) / 3 (promociones)

Casos de uso que realiza este paquete:
  CU-08 Gestionar categorias, tallas y colores      [ciclo 1]
  CU-09 Gestionar temporadas y colecciones          [ciclo 1]
  CU-10 Gestionar productos y variantes             [ciclo 2]
  CU-11 Gestionar imagenes de producto              [ciclo 2]
  CU-12 Gestionar promociones                       [ciclo 3]
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

# TODO: implementar las reglas de negocio de este paquete.
