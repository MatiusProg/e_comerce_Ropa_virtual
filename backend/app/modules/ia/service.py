"""
P10 - Inteligencia Artificial  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-33 Recibir recomendaciones de prendas
  CU-34 Conversar con el asistente virtual
  CU-35 Generar reporte por comando de voz
"""
from sqlalchemy.orm import Session  # noqa: F401

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

# TODO: implementar las reglas de negocio de este paquete.
