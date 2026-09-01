"""
P10 - Inteligencia Artificial  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-33 Recibir recomendaciones de prendas
  CU-34 Conversar con el asistente virtual
  CU-35 Generar reporte por comando de voz
"""
from fastapi import APIRouter

router = APIRouter(prefix="/ia", tags=["Inteligencia artificial"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.

# TODO: declarar los endpoints de este paquete.
