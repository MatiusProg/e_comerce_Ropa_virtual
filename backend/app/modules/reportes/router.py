"""
P11 - Reportes y Tablero  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-36 Consultar tablero de indicadores
  CU-37 Generar reportes de gestion (PDF / Excel)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/reportes", tags=["Reportes"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.

# TODO: declarar los endpoints de este paquete.
