"""Aporte propio · «Avísame cuando llegue mi talla»  |  capa: router.

QUIÉN PUEDE
-----------
- Pedir, ver y cancelar sus avisos: el CLIENTE.
- Ver cuántos clientes esperan cada talla: ENCARGADO y ADMINISTRADOR. La ruta
  cuelga de `/inventario`, así que la cubre el permiso `inventario.gestionar`
  de los roles propios (CU-41) sin anotar nada nuevo.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.avisos_talla import service
from app.modules.avisos_talla.schemas import AvisoIn, AvisoOut, DemandaOut
from app.modules.seguridad.service import PerfilInexistente

cliente_router = APIRouter(
    prefix="/tienda/avisos-talla",
    tags=["Aporte propio · Avísame cuando llegue mi talla (cliente)"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
)
personal_router = APIRouter(
    prefix="/inventario/avisos-talla",
    tags=["Aporte propio · Avísame cuando llegue mi talla (personal)"],
    dependencies=[Depends(requiere_roles("ENCARGADO", "ADMINISTRADOR"))],
)


def _http(e: Exception) -> HTTPException:
    if isinstance(e, PerfilInexistente):
        return HTTPException(status.HTTP_403_FORBIDDEN, "Su cuenta no es de cliente.")
    if isinstance(e, service.ErrorAvisoTalla):
        return HTTPException(e.codigo, e.mensaje)
    raise e


@cliente_router.get("", response_model=list[AvisoOut], summary="Mis avisos de talla")
def mis_avisos(db: DbSession, usuario: Usuario):
    try:
        return service.mis_avisos(db, usuario.id)
    except PerfilInexistente as e:
        raise _http(e) from e


@cliente_router.get(
    "/variantes", response_model=list[int], summary="Variantes que estoy esperando"
)
def variantes_esperadas(db: DbSession, usuario: Usuario):
    try:
        return service.variantes_esperadas(db, usuario.id)
    except PerfilInexistente as e:
        raise _http(e) from e


@cliente_router.post(
    "",
    response_model=AvisoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Avísenme cuando llegue esta talla y color",
    responses={
        404: {"description": "La variante no existe o ya no se ofrece."},
        409: {"description": "La variante ya tiene unidades."},
    },
)
def suscribir(datos: AvisoIn, db: DbSession, usuario: Usuario):
    try:
        return service.suscribir(db, usuario.id, datos.variante_id)
    except (PerfilInexistente, service.ErrorAvisoTalla) as e:
        raise _http(e) from e


@cliente_router.delete(
    "/{aviso_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cancelar un aviso"
)
def cancelar(db: DbSession, usuario: Usuario, aviso_id: Annotated[int, Path(ge=1)]):
    try:
        service.cancelar(db, usuario.id, aviso_id)
    except (PerfilInexistente, service.ErrorAvisoTalla) as e:
        raise _http(e) from e
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@personal_router.get(
    "",
    response_model=list[DemandaOut],
    summary="Tallas agotadas que hay clientes esperando",
)
def demanda(db: DbSession):
    return service.demanda(db)
