"""
P9 - Vestidor Virtual (RA)  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-21 Utilizar vestidor virtual (la RA corre en el dispositivo;
         el backend sirve los activos y registra la sesion)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/vestidor", tags=["Vestidor virtual"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.

# TODO: declarar los endpoints de este paquete.
