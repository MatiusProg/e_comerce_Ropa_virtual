"""
P2 - Organizacion  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, requiere_roles
from app.modules.organizacion import service
from app.modules.organizacion.schemas import (
    CambioEstadoSucursalIn,
    CiudadCrearIn,
    CiudadEditarIn,
    CiudadOut,
    SucursalCrearIn,
    SucursalEditarIn,
    SucursalOut,
)

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.
#
# TODO el paquete exige rol Administrador, y la dependencia se declara UNA sola
# vez a nivel de router: endpoint por endpoint, olvidarla en uno solo abriria un
# agujero sin que nada avise.
router = APIRouter(
    prefix="/organizacion",
    tags=["Organizacion"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


def _traducir(error: service.ErrorDeOrganizacion) -> HTTPException:
    """Convierte los errores de negocio de CU-05 en respuestas HTTP."""
    if isinstance(error, service.CiudadInexistente):
        return HTTPException(404, "La ciudad indicada no existe.")
    if isinstance(error, service.SucursalInexistente):
        return HTTPException(404, "La sucursal indicada no existe.")
    if isinstance(error, service.CiudadDuplicada):
        return HTTPException(409, "Ya existe una ciudad con ese nombre.")
    if isinstance(error, service.NombreDeSucursalDuplicado):
        # Excepcion E1. La interfaz usa este mensaje para señalar el campo.
        return HTTPException(
            409, "Ya existe una sucursal con ese nombre en la misma ciudad."
        )
    if isinstance(error, service.CiudadConSucursalesActivas):
        # Excepcion E2.
        return HTTPException(
            409,
            "La ciudad tiene sucursales activas. Dé de baja sus sucursales "
            "antes de eliminarla.",
        )
    if isinstance(error, service.CiudadConHistorial):
        return HTTPException(
            409,
            "La ciudad tiene sucursales registradas que se conservan por "
            "trazabilidad y no puede eliminarse.",
        )
    if isinstance(error, service.HorarioInvalido):
        return HTTPException(
            422, "El horario de cierre debe ser posterior al de apertura."
        )
    return HTTPException(400, "No se pudo completar la operación.")


# --- CU-05 Ciudades (flujo alternativo 3a) -------------------------------


@router.get("/ciudades", response_model=list[CiudadOut], summary="CU-05 Listar ciudades")
def listar_ciudades(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=60)] = None,
) -> list[CiudadOut]:
    """Ciudades con el recuento de sus sucursales, totales y activas."""
    return service.listar_ciudades(db, busqueda=busqueda)


@router.post(
    "/ciudades",
    response_model=CiudadOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-05 Registrar ciudad",
    responses={409: {"description": "Ya existe una ciudad con ese nombre."}},
)
def crear_ciudad(datos: CiudadCrearIn, db: DbSession) -> CiudadOut:
    try:
        return service.crear_ciudad(db, datos)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


@router.get(
    "/ciudades/{ciudad_id}", response_model=CiudadOut, summary="CU-05 Ver una ciudad"
)
def obtener_ciudad(ciudad_id: int, db: DbSession) -> CiudadOut:
    try:
        return service.obtener_ciudad(db, ciudad_id)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


@router.patch(
    "/ciudades/{ciudad_id}", response_model=CiudadOut, summary="CU-05 Editar ciudad"
)
def editar_ciudad(ciudad_id: int, datos: CiudadEditarIn, db: DbSession) -> CiudadOut:
    try:
        return service.editar_ciudad(db, ciudad_id, datos)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


@router.delete(
    "/ciudades/{ciudad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-05 Eliminar ciudad",
    responses={409: {"description": "La ciudad tiene sucursales (excepción E2)."}},
)
def eliminar_ciudad(ciudad_id: int, db: DbSession) -> None:
    """Elimina la ciudad, solo si no le queda ninguna sucursal.

    `ciudad` no tiene indicador de estado: darla de baja es eliminarla.
    """
    try:
        service.eliminar_ciudad(db, ciudad_id)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


# --- CU-05 Sucursales ----------------------------------------------------


@router.get(
    "/sucursales",
    response_model=list[SucursalOut],
    summary="CU-05 Listar sucursales",
)
def listar_sucursales(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=80)] = None,
    ciudad_id: Annotated[int | None, Query()] = None,
    activa: Annotated[bool | None, Query()] = None,
) -> list[SucursalOut]:
    """Sucursales con su ciudad, dirección, horario, capacidad y estado.

    Es el paso 2 del flujo principal y, con `activa=true`, tambien el selector
    del formulario de CU-03. Es el mismo endpoint que ya existia: se extendio
    en vez de declarar otro con la misma ruta, porque FastAPI se queda con la
    primera registrada y la segunda moriria sin ningun error visible (ver 6.11.2
    de las decisiones tecnicas).
    """
    return service.listar_sucursales(
        db, busqueda=busqueda, ciudad_id=ciudad_id, activa=activa
    )


@router.post(
    "/sucursales",
    response_model=SucursalOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-05 Registrar sucursal",
    responses={
        409: {"description": "El nombre ya existe en esa ciudad (excepción E1)."},
        422: {"description": "Horario u capacidad inválidos (excepción E3)."},
    },
)
def crear_sucursal(datos: SucursalCrearIn, db: DbSession) -> SucursalOut:
    try:
        return service.crear_sucursal(db, datos)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


@router.get(
    "/sucursales/{sucursal_id}",
    response_model=SucursalOut,
    summary="CU-05 Ver una sucursal",
)
def obtener_sucursal(sucursal_id: int, db: DbSession) -> SucursalOut:
    try:
        return service.obtener_sucursal(db, sucursal_id)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


@router.patch(
    "/sucursales/{sucursal_id}",
    response_model=SucursalOut,
    summary="CU-05 Editar sucursal",
)
def editar_sucursal(
    sucursal_id: int, datos: SucursalEditarIn, db: DbSession
) -> SucursalOut:
    """Modifica los datos de una sucursal (flujo alternativo 3b)."""
    try:
        return service.editar_sucursal(db, sucursal_id, datos)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


@router.patch(
    "/sucursales/{sucursal_id}/estado",
    response_model=SucursalOut,
    summary="CU-05 Dar de alta o de baja una sucursal",
)
def cambiar_estado_sucursal(
    sucursal_id: int, datos: CambioEstadoSucursalIn, db: DbSession
) -> SucursalOut:
    """Flujo alternativo 3c.

    La baja no borra la fila: la sucursal deja de ofrecerse para reservas y
    compras, y se conserva para la trazabilidad histórica.
    """
    try:
        return service.cambiar_estado_sucursal(db, sucursal_id, datos.activa)
    except service.ErrorDeOrganizacion as error:
        raise _traducir(error)


# TODO CU-06 y CU-07: declarar el resto de los endpoints.
