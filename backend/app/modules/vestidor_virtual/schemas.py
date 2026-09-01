"""
P9 - Vestidor Virtual (RA)  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-21 Utilizar vestidor virtual (la RA corre en el dispositivo;
         el backend sirve los activos y registra la sesion)
"""
from pydantic import BaseModel, ConfigDict  # noqa: F401

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).

# TODO: definir los esquemas de este paquete.
