"""
P17 - Roles y permisos por empresa / CU-41  |  capa: router

Solo el ADMINISTRADOR de la empresa, y uno SIN rol propio: el permiso
`roles.gestionar` no se delega (ver `app/core/permisos.py`), así que la guarda
de `get_usuario_actual` ya corta a quien tenga uno.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.roles import service
from app.modules.roles.schemas import (
    AsignacionIn,
    EstadoIn,
    PermisoOut,
    PersonaOut,
    RolEditarIn,
    RolIn,
    RolOut,
)

router = APIRouter(
    prefix="/roles",
    tags=["CU-41 · Roles y permisos de la empresa"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)

Id = Annotated[int, Path(ge=1)]


def _traducir(e: service.ErrorDeRoles) -> HTTPException:
    return HTTPException(e.codigo, detail=e.mensaje)


@router.get("/permisos", response_model=list[PermisoOut], summary="CU-41 Catálogo de permisos")
def permisos(db: DbSession):
    """Los permisos que se pueden poner en un rol propio, con cuáles incluye el
    plan de la empresa (RN-22)."""
    return service.catalogo_de_permisos(db)


@router.get("/personal", response_model=list[PersonaOut], summary="CU-41 El personal y su rol")
def personal(db: DbSession, usuario: Usuario):
    return service.personal(db, usuario.empresa_id)


@router.put("/asignacion", response_model=PersonaOut, summary="CU-41 Asignar un rol propio")
def asignar(datos: AsignacionIn, db: DbSession, usuario: Usuario):
    """Con `rol_empresa_id` nulo le quita el rol propio: vuelve a tener todo lo
    de su rol base. Vale desde la próxima petición de esa persona."""
    try:
        return service.asignar(db, usuario.empresa_id, usuario.id, datos)
    except service.ErrorDeRoles as e:
        raise _traducir(e) from e


@router.get("", response_model=list[RolOut], summary="CU-41 Roles de la empresa")
def listar(db: DbSession):
    return service.listar(db)


@router.post("", response_model=RolOut, status_code=201, summary="CU-41 Crear un rol")
def crear(datos: RolIn, db: DbSession):
    try:
        return service.crear(db, datos)
    except service.ErrorDeRoles as e:
        raise _traducir(e) from e


@router.patch("/{rol_id}", response_model=RolOut, summary="CU-41 Editar un rol")
def editar(rol_id: Id, datos: RolEditarIn, db: DbSession):
    try:
        return service.editar(db, rol_id, datos)
    except service.ErrorDeRoles as e:
        raise _traducir(e) from e


@router.patch("/{rol_id}/estado", response_model=RolOut, summary="CU-41 Activar o desactivar")
def estado(rol_id: Id, datos: EstadoIn, db: DbSession):
    try:
        return service.cambiar_estado(db, rol_id, datos.activo)
    except service.ErrorDeRoles as e:
        raise _traducir(e) from e
