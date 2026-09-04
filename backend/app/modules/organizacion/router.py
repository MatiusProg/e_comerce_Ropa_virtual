"""
P2 - Organizacion  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import DbSession, requiere_roles
from app.modules.organizacion import service
from app.modules.organizacion.schemas import CiudadBreveOut, SucursalBreveOut

router = APIRouter(prefix="/organizacion", tags=["Organizacion"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.


@router.get(
    "/sucursales",
    response_model=list[SucursalBreveOut],
    summary="Sucursales activas (selector)",
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es valido."},
        403: {"description": "El usuario no es Administrador."},
    },
)
def listar_sucursales_activas(db: DbSession) -> list[SucursalBreveOut]:
    """Sucursales activas, para poblar el selector del formulario de CU-03.

    Es solo lectura y devuelve el minimo indispensable. El alta, la edicion y
    la baja de sucursales son CU-05 y no viven aca todavia.
    """
    return service.listar_sucursales_activas(db)


@router.get(
    "/ciudades",
    response_model=list[CiudadBreveOut],
    summary="Ciudades (selector)",
    dependencies=[Depends(requiere_roles("CLIENTE", "ADMINISTRADOR"))],
    responses={401: {"description": "Falta el token o ya no es valido."}},
)
def listar_ciudades(db: DbSession) -> list[CiudadBreveOut]:
    """Ciudades registradas, para poblar el selector de direcciones de CU-04.

    Mismo criterio que el endpoint de sucursales: es solo lectura y devuelve el
    minimo indispensable. El alta, la edicion y la baja de ciudades son CU-05.
    Ver la seccion 6.11.2 de docs/06-decisiones-tecnicas.md.
    """
    return service.listar_ciudades(db)


# TODO CU-05, CU-06 y CU-07: declarar el resto de los endpoints.
