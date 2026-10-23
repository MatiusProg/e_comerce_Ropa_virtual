"""
P12 - Plataforma SaaS  |  capa: router (FastAPI)

CU-01 Gestionar empresas. Todo el router exige ADMIN_PLATAFORMA, declarado una
sola vez: endpoint por endpoint, olvidarlo en uno abriría un agujero.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, requiere_roles
from app.core.tenencia import ROL_PLATAFORMA
from app.modules.plataforma import service
from app.modules.plataforma.schemas import (
    EmpresaCrearIn,
    EmpresaCreadaOut,
    EmpresaEditarIn,
    EmpresaOut,
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


@router.get("/planes", response_model=list[PlanOut], summary="CU-01 Planes para el alta")
def listar_planes(db: DbSession) -> list[PlanOut]:
    return service.listar_planes(db)


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
