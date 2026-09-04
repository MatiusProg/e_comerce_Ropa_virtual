"""
P2 - Organizacion  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from pydantic import BaseModel, ConfigDict

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).


class SucursalBreveOut(BaseModel):
    """Sucursal reducida a lo que hace falta para elegirla en un selector.

    Es lo minimo que necesita CU-03 para asignarle sucursal a un Encargado o a
    un Cajero. El detalle completo y el CRUD son de CU-05.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad: str


class CiudadBreveOut(BaseModel):
    """Ciudad reducida a lo que hace falta para elegirla en un selector.

    Es lo minimo que necesita CU-04 para que el Cliente indique la ciudad de una
    direccion de entrega. El detalle completo y el CRUD son de CU-05.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    departamento: str


# TODO CU-05, CU-06 y CU-07: definir el resto de los esquemas.
