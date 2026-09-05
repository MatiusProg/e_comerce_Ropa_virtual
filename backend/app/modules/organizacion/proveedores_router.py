"""
P2 - Organizacion  |  CU-07 Gestionar proveedores  |  capa: router

Ciclo de desarrollo: 1

Archivos propios para no chocar con el CU-06; el motivo esta en
`proveedores_schemas.py`. Se montan en `app/main.py` --- dos lineas --- en vez
de colgarse del router de organizacion, porque ese archivo si lo toca el CU-06.

Son DOS routers porque el caso de uso tiene dos actores con permisos
distintos: el Administrador, que gestiona, y el Proveedor, que solo consulta
sus propios datos. La exigencia de rol se declara una sola vez por router: si
se declarara endpoint por endpoint, olvidarla en uno solo abriria un agujero.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.organizacion import proveedores_service as service
from app.modules.organizacion.proveedores_schemas import (
    AccesoProveedorIn,
    CambioEstadoProveedorIn,
    ProveedorCrearIn,
    ProveedorEditarIn,
    ProveedorOut,
)

router = APIRouter(
    prefix="/organizacion/proveedores",
    tags=["Organizacion · Proveedores"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)

#: Router del segundo actor. Va aparte porque exige rol PROVEEDOR, no
#: ADMINISTRADOR, y porque su ruta no lleva identificador.
router_proveedor = APIRouter(
    prefix="/organizacion/mi-ficha",
    tags=["Organizacion · Proveedores"],
    dependencies=[Depends(requiere_roles("PROVEEDOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no tiene rol Proveedor."},
    },
)


def _traducir(error: service.ErrorDeProveedores) -> HTTPException:
    """Convierte los errores de negocio de CU-07 en respuestas HTTP."""
    if isinstance(error, service.ProveedorInexistente):
        return HTTPException(404, "El proveedor indicado no existe.")
    if isinstance(error, service.ProveedorSinFicha):
        return HTTPException(404, "Su usuario no tiene una ficha de proveedor asociada.")
    if isinstance(error, service.IdentificacionDuplicada):
        # Excepcion E1. La interfaz usa este mensaje para señalar el campo.
        return HTTPException(
            409, "Ya existe un proveedor con esa identificación tributaria."
        )
    if isinstance(error, service.CorreoYaRegistrado):
        return HTTPException(409, "Ya existe una cuenta con ese correo electrónico.")
    if isinstance(error, service.AccesoYaHabilitado):
        return HTTPException(409, "El proveedor ya tiene acceso habilitado.")
    if isinstance(error, service.RolProveedorInexistente):
        # No es culpa de quien opera: falta cargar el seed de roles.
        return HTTPException(
            503, "El sistema no está inicializado. Contacte al administrador."
        )
    return HTTPException(400, "No se pudo completar la operación.")


# --- El Proveedor consulta sus propios datos -----------------------------


@router_proveedor.get(
    "", response_model=ProveedorOut, summary="CU-07 Mi ficha de proveedor"
)
def mi_ficha(usuario: Usuario, db: DbSession) -> ProveedorOut:
    """Los datos del proveedor que porta el token.

    No recibe identificador: se resuelve desde el token, para que nadie pueda
    pedir la ficha de otro cambiando un número en la URL.
    """
    try:
        return service.obtener_mi_ficha(db, usuario.id)
    except service.ErrorDeProveedores as error:
        raise _traducir(error)


# --- El Administrador gestiona -------------------------------------------


@router.get("", response_model=list[ProveedorOut], summary="CU-07 Listar proveedores")
def listar_proveedores(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=120)] = None,
    activo: Annotated[bool | None, Query()] = None,
) -> list[ProveedorOut]:
    """Proveedores con razón social, identificación, contacto y estado (paso 2)."""
    return service.listar(db, busqueda=busqueda, activo=activo)


@router.post(
    "",
    response_model=ProveedorOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-07 Registrar proveedor",
    responses={
        409: {"description": "La identificación tributaria ya existe (excepción E1)."},
        422: {"description": "Correo con formato inválido (excepción E2)."},
    },
)
def crear_proveedor(datos: ProveedorCrearIn, db: DbSession) -> ProveedorOut:
    try:
        return service.crear(db, datos)
    except service.ErrorDeProveedores as error:
        raise _traducir(error)


@router.get(
    "/{proveedor_id}", response_model=ProveedorOut, summary="CU-07 Ver un proveedor"
)
def obtener_proveedor(proveedor_id: int, db: DbSession) -> ProveedorOut:
    try:
        return service.obtener(db, proveedor_id)
    except service.ErrorDeProveedores as error:
        raise _traducir(error)


@router.patch(
    "/{proveedor_id}", response_model=ProveedorOut, summary="CU-07 Editar proveedor"
)
def editar_proveedor(
    proveedor_id: int, datos: ProveedorEditarIn, db: DbSession
) -> ProveedorOut:
    """Modifica los datos del proveedor (flujo alternativo 3a)."""
    try:
        return service.editar(db, proveedor_id, datos)
    except service.ErrorDeProveedores as error:
        raise _traducir(error)


@router.patch(
    "/{proveedor_id}/estado",
    response_model=ProveedorOut,
    summary="CU-07 Dar de alta o de baja un proveedor",
)
def cambiar_estado_proveedor(
    proveedor_id: int, datos: CambioEstadoProveedorIn, db: DbSession
) -> ProveedorOut:
    """Flujo alternativo 3b.

    La baja no borra la ficha: sus productos históricos se conservan.
    """
    try:
        return service.cambiar_estado(db, proveedor_id, datos.activo)
    except service.ErrorDeProveedores as error:
        raise _traducir(error)


@router.post(
    "/{proveedor_id}/acceso",
    response_model=ProveedorOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-07 Habilitar acceso al Proveedor",
    responses={409: {"description": "El correo ya existe o ya tiene acceso."}},
)
def habilitar_acceso(
    proveedor_id: int, datos: AccesoProveedorIn, db: DbSession
) -> ProveedorOut:
    """Flujo alternativo 3c.

    Crea un usuario con rol Proveedor vinculado a la ficha, con alcance
    limitado a sus propios productos. Las dos operaciones van en una única
    transacción.
    """
    try:
        return service.habilitar_acceso(db, proveedor_id, datos)
    except service.ErrorDeProveedores as error:
        raise _traducir(error)
