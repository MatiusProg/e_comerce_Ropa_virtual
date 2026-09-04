"""
P2 - Organizacion  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from sqlalchemy.orm import Session

from app.modules.organizacion import repository
from app.modules.organizacion.schemas import SucursalBreveOut

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.


def listar_sucursales_activas(db: Session) -> list[SucursalBreveOut]:
    """Sucursales disponibles para asignar a un empleado."""
    return [
        SucursalBreveOut(id=f.id, nombre=f.nombre, ciudad=f.ciudad)
        for f in repository.listar_sucursales_activas(db)
    ]


# TODO CU-05, CU-06 y CU-07: implementar el resto de las reglas.
