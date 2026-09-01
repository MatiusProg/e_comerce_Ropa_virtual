"""
P3 - Catalogo  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1 (maestros) / 2 (productos) / 3 (promociones)

Casos de uso que realiza este paquete:
  CU-08 Gestionar categorias, tallas y colores      [ciclo 1]
  CU-09 Gestionar temporadas y colecciones          [ciclo 1]
  CU-10 Gestionar productos y variantes             [ciclo 2]
  CU-11 Gestionar imagenes de producto              [ciclo 2]
  CU-12 Gestionar promociones                       [ciclo 3]
"""
from fastapi import APIRouter

router = APIRouter(prefix="/catalogo", tags=["Catalogo"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.

# TODO: declarar los endpoints de este paquete.
