"""
P2 - Organizacion / CU-06  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1
Caso de uso: CU-06 Gestionar empleados

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, requiere_roles
from app.modules.organizacion.empleados import service
from app.modules.organizacion.empleados.schemas import (
    CARGOS,
    BajaEmpleadoIn,
    EmpleadoCrearIn,
    EmpleadoEditarIn,
    EmpleadoOut,
    UsuarioVinculableOut,
)

# Todo el caso de uso exige rol Administrador, y la dependencia se declara UNA
# sola vez a nivel de router: endpoint por endpoint, olvidarla en uno solo
# abriria un agujero sin que nada avise. Es el mismo criterio del CU-03 y del
# CU-05.
router = APIRouter(
    prefix="/organizacion/empleados",
    tags=["Organizacion · Empleados"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


def _traducir(error: service.ErrorDeEmpleados) -> HTTPException:
    """Convierte los errores de negocio de CU-06 en respuestas HTTP."""
    if isinstance(error, service.EmpleadoInexistente):
        return HTTPException(404, "El empleado indicado no existe.")
    if isinstance(error, service.DocumentoYaRegistrado):
        # Excepcion E1. El caso de uso devuelve el control al paso 5, así que
        # la interfaz usa este 409 para señalar el campo sin cerrar el diálogo.
        return HTTPException(409, "Ya existe un empleado con ese documento.")
    if isinstance(error, service.CorreoYaRegistrado):
        return HTTPException(409, "Ya existe una cuenta con ese correo electrónico.")
    if isinstance(error, service.SucursalInexistente):
        return HTTPException(422, "La sucursal indicada no existe.")
    if isinstance(error, service.SucursalInactiva):
        # Excepcion E2.
        return HTTPException(
            422,
            "La sucursal está dada de baja. Reactívela antes de asignarle personal.",
        )
    if isinstance(error, service.UsuarioNoVinculable):
        return HTTPException(
            422,
            "Esa cuenta ya no se puede vincular: fue desactivada o ya tiene un "
            "empleado asociado.",
        )
    if isinstance(error, service.EmpleadoYaDadoDeBaja):
        return HTTPException(409, "El empleado ya está dado de baja.")
    if isinstance(error, service.FechaDeBajaInvalida):
        return HTTPException(
            422, "La fecha de baja no puede ser anterior a la de ingreso."
        )
    if isinstance(error, service.RolInexistente):
        return HTTPException(
            500, "Falta en la base el rol correspondiente al cargo. Revise el seed."
        )
    return HTTPException(400, "No se pudo completar la operación.")


@router.get("", response_model=list[EmpleadoOut], summary="CU-06 Listar empleados")
def listar_empleados(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=120)] = None,
    sucursal_id: Annotated[int | None, Query()] = None,
    cargo: Annotated[str | None, Query(pattern="^(ENCARGADO|CAJERO)$")] = None,
    activo: Annotated[bool | None, Query()] = None,
) -> list[EmpleadoOut]:
    """Paso 2: empleados con su cargo, sucursal y estado, con filtros.

    `activo` distingue a quien sigue en actividad de quien tiene fecha de baja.
    No es lo mismo que el estado de la cuenta, que viaja aparte.
    """
    return service.listar_empleados(
        db, busqueda=busqueda, sucursal_id=sucursal_id, cargo=cargo, activo=activo
    )


@router.get(
    "/cargos",
    response_model=list[str],
    summary="CU-06 Cargos asignables",
)
def listar_cargos() -> list[str]:
    """Los dos cargos que admite la tabla, para el selector del formulario.

    Es una constante, no una consulta: el CHECK ck_empleado_cargo los fija en
    la base. Se expone igual para que la interfaz no los repita por su cuenta y
    se desincronice el día que se agregue uno.
    """
    return list(CARGOS)


@router.get(
    "/usuarios-vinculables",
    response_model=list[UsuarioVinculableOut],
    summary="CU-06 Cuentas sin empleado (flujo 3c)",
)
def listar_usuarios_vinculables(db: DbSession) -> list[UsuarioVinculableOut]:
    """Cuentas existentes que todavía no tienen ficha de empleado."""
    return service.listar_usuarios_vinculables(db)


@router.post(
    "",
    response_model=EmpleadoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-06 Registrar empleado",
    responses={
        409: {"description": "Documento o correo ya registrados (excepción E1)."},
        422: {"description": "Sucursal inexistente o dada de baja (excepción E2)."},
    },
)
def crear_empleado(datos: EmpleadoCrearIn, db: DbSession) -> EmpleadoOut:
    """Pasos 4 a 7, y flujo alternativo 3c si llega `usuario_id`.

    La cuenta y la ficha se crean en una sola transacción: si falla cualquiera
    de las dos no queda ninguna (excepción E3).
    """
    try:
        return service.crear_empleado(db, datos)
    except service.ErrorDeEmpleados as error:
        raise _traducir(error)


@router.get(
    "/{empleado_id}", response_model=EmpleadoOut, summary="CU-06 Ver un empleado"
)
def obtener_empleado(empleado_id: int, db: DbSession) -> EmpleadoOut:
    try:
        return service.obtener_empleado(db, empleado_id)
    except service.ErrorDeEmpleados as error:
        raise _traducir(error)


@router.patch(
    "/{empleado_id}", response_model=EmpleadoOut, summary="CU-06 Editar o reasignar"
)
def editar_empleado(
    empleado_id: int, datos: EmpleadoEditarIn, db: DbSession
) -> EmpleadoOut:
    """Flujo alternativo 3a.

    Cambiar el cargo o la sucursal actualiza también el usuario vinculado y
    revoca sus sesiones: el rol y el ámbito viajan dentro del token.
    """
    try:
        return service.editar_empleado(db, empleado_id, datos)
    except service.ErrorDeEmpleados as error:
        raise _traducir(error)


@router.patch(
    "/{empleado_id}/baja",
    response_model=EmpleadoOut,
    summary="CU-06 Dar de baja",
    responses={409: {"description": "El empleado ya está dado de baja."}},
)
def dar_de_baja(empleado_id: int, datos: BajaEmpleadoIn, db: DbSession) -> EmpleadoOut:
    """Flujo alternativo 3b: registra la baja, desactiva la cuenta y revoca
    sus tokens vigentes."""
    try:
        return service.dar_de_baja(db, empleado_id, datos)
    except service.ErrorDeEmpleados as error:
        raise _traducir(error)
