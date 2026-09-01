"""
P8 - Pagos  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Iniciar el pago electronico contra la pasarela
  CU-28 Confirmar pago del pedido (webhook firmado e idempotente)
"""
from fastapi import APIRouter

router = APIRouter(prefix="/pagos", tags=["Pagos"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.

# TODO: declarar los endpoints de este paquete.
