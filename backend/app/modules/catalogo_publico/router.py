"""
P5 - Catalogo Publico y Disponibilidad  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2 (catalogo) / 3 (favoritos)

Casos de uso que realiza este paquete:
  CU-17 Consultar catalogo                          [ciclo 2]
  CU-18 Consultar ficha de producto                 [ciclo 2]
  CU-19 Consultar disponibilidad por sucursal       [ciclo 2]
  CU-20 Gestionar favoritos                         [ciclo 3]
"""
from fastapi import APIRouter

router = APIRouter(prefix="/tienda", tags=["Catalogo publico"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.

# TODO: declarar los endpoints de este paquete.
