"""
P12 - Plataforma SaaS  |  capa: router (FastAPI)

CU-01 Gestionar empresas y CU-02 Gestionar planes. Todo el router exige
ADMIN_PLATAFORMA, declarado una sola vez: endpoint por endpoint, olvidarlo en
uno abriría un agujero.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, requiere_roles
from app.core.tenencia import ROL_PLATAFORMA
from app.modules.plataforma import planes, service
from app.modules.plataforma.schemas import (
    EmpresaCrearIn,
    EmpresaCreadaOut,
    EmpresaEditarIn,
    EmpresaOut,
    FuncionOut,
    PlanGuardadoOut,
    PlanIn,
    PlanOut,
)

router = APIRouter(
    prefix="/plataforma",
    tags=["Plataforma · Empresas"],
    dependencies=[Depends(requiere_roles(ROL_PLATAFORMA))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es administrador de la plataforma."},
    },
)


def _traducir(error: service.ErrorDePlataforma) -> HTTPException:
    if isinstance(error, service.EmpresaInexistente):
        return HTTPException(status.HTTP_404_NOT_FOUND, "La empresa indicada no existe.")
    if isinstance(error, service.SlugRepetido):
        return HTTPException(status.HTTP_409_CONFLICT, "Ese slug ya lo usa otra empresa.")
    if isinstance(error, service.CorreoYaRegistrado):
        return HTTPException(
            status.HTTP_409_CONFLICT, "El correo del administrador ya tiene una cuenta."
        )
    if isinstance(error, service.PlanInexistente):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El plan indicado no existe.")
    if isinstance(error, service.CiudadInexistente):
        return HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "La ciudad de la sucursal no existe."
        )
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(error))


@router.get("/empresas", response_model=list[EmpresaOut], summary="CU-01 Listar empresas")
def listar_empresas(
    db: DbSession, busqueda: Annotated[str | None, Query(max_length=60)] = None
) -> list[EmpresaOut]:
    return service.listar_empresas(db, busqueda=busqueda)


# --- CU-02 Planes ----------------------------------------------------------


def _traducir_plan(error: planes.ErrorDePlanes) -> HTTPException:
    if isinstance(error, planes.PlanInexistente):
        return HTTPException(status.HTTP_404_NOT_FOUND, "El plan indicado no existe.")
    if isinstance(error, planes.NombreDePlanRepetido):
        return HTTPException(status.HTTP_409_CONFLICT, "Ya existe un plan con ese nombre.")
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(error))


@router.get("/planes", response_model=list[PlanOut], summary="CU-02 Listar planes")
def listar_planes(
    db: DbSession, incluir_inactivos: Annotated[bool, Query()] = False
) -> list[PlanOut]:
    """Sin `incluir_inactivos`, solo los que se ofrecen: es el selector del alta (CU-01)."""
    return planes.listar_planes(db, incluir_inactivos=incluir_inactivos)


@router.get(
    "/planes/funciones",
    response_model=list[FuncionOut],
    summary="CU-02 Funciones que un plan puede incluir",
)
def listar_funciones() -> list[FuncionOut]:
    return planes.listar_funciones()


@router.post(
    "/planes",
    response_model=PlanGuardadoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-02 Crear un plan",
    responses={409: {"description": "Ya existe un plan con ese nombre."}},
)
def crear_plan(datos: PlanIn, db: DbSession) -> PlanGuardadoOut:
    try:
        return planes.crear_plan(db, datos)
    except planes.ErrorDePlanes as error:
        raise _traducir_plan(error) from error


@router.get("/planes/{plan_id}", response_model=PlanOut, summary="CU-02 Ver un plan")
def obtener_plan(plan_id: int, db: DbSession) -> PlanOut:
    try:
        return planes.obtener_plan(db, plan_id)
    except planes.ErrorDePlanes as error:
        raise _traducir_plan(error) from error


@router.put(
    "/planes/{plan_id}",
    response_model=PlanGuardadoOut,
    summary="CU-02 Editar un plan (devuelve las empresas que quedan por encima de un límite)",
    responses={409: {"description": "Ya existe un plan con ese nombre."}},
)
def editar_plan(plan_id: int, datos: PlanIn, db: DbSession) -> PlanGuardadoOut:
    try:
        return planes.editar_plan(db, plan_id, datos)
    except planes.ErrorDePlanes as error:
        raise _traducir_plan(error) from error


@router.post(
    "/planes/{plan_id}/desactivar",
    response_model=PlanOut,
    summary="CU-02 Dejar de ofrecer un plan (quien lo tiene lo conserva)",
)
def desactivar_plan(plan_id: int, db: DbSession) -> PlanOut:
    try:
        return planes.cambiar_estado(db, plan_id, activo=False)
    except planes.ErrorDePlanes as error:
        raise _traducir_plan(error) from error


@router.post("/planes/{plan_id}/activar", response_model=PlanOut, summary="CU-02 Volver a ofrecer un plan")
def activar_plan(plan_id: int, db: DbSession) -> PlanOut:
    try:
        return planes.cambiar_estado(db, plan_id, activo=True)
    except planes.ErrorDePlanes as error:
        raise _traducir_plan(error) from error


# --- CU-01 Empresas --------------------------------------------------------


@router.post(
    "/empresas",
    response_model=EmpresaCreadaOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-01 Registrar una empresa con su suscripción, sucursal y administrador",
)
def crear_empresa(datos: EmpresaCrearIn, db: DbSession) -> EmpresaCreadaOut:
    try:
        return service.crear_empresa(db, datos)
    except service.ErrorDePlataforma as error:
        raise _traducir(error) from error


@router.get("/empresas/{empresa_id}", response_model=EmpresaOut, summary="CU-01 Ver una empresa")
def obtener_empresa(empresa_id: int, db: DbSession) -> EmpresaOut:
    try:
        return service.obtener_empresa(db, empresa_id)
    except service.ErrorDePlataforma as error:
        raise _traducir(error) from error


@router.patch(
    "/empresas/{empresa_id}", response_model=EmpresaOut, summary="CU-01 Editar una empresa"
)
def editar_empresa(empresa_id: int, datos: EmpresaEditarIn, db: DbSession) -> EmpresaOut:
    try:
        return service.editar_empresa(db, empresa_id, datos)
    except service.ErrorDePlataforma as error:
        raise _traducir(error) from error


@router.post(
    "/empresas/{empresa_id}/baja",
    response_model=EmpresaOut,
    summary="CU-01 Dar de baja una empresa (no borra nada; corta el acceso)",
)
def dar_de_baja(empresa_id: int, db: DbSession) -> EmpresaOut:
    try:
        return service.cambiar_estado(db, empresa_id, activa=False)
    except service.ErrorDePlataforma as error:
        raise _traducir(error) from error


@router.post(
    "/empresas/{empresa_id}/reactivar",
    response_model=EmpresaOut,
    summary="CU-01 Reactivar una empresa dada de baja",
)
def reactivar(empresa_id: int, db: DbSession) -> EmpresaOut:
    try:
        return service.cambiar_estado(db, empresa_id, activa=True)
    except service.ErrorDePlataforma as error:
        raise _traducir(error) from error
