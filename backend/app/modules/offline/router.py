"""
P14 - Offline y sincronización / CU-13 a CU-19  |  capa: router

QUIÉN PUEDE
-----------
- El paquete del mostrador y la venta offline: CAJERO y ENCARGADO, los mismos
  que cobran en línea (CU-31).
- El paquete para reservar y la reserva offline: también el CLIENTE (CU-15).
- Atender las rechazadas y devolver el dinero: ENCARGADO, de su sucursal, y
  el ADMINISTRADOR, de todas (CU-19, solo web).
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.offline import service
from app.modules.offline.schemas import (
    DevolucionIn,
    LoteIn,
    LoteOut,
    OperacionOut,
    PaqueteDeClienteOut,
    PaqueteDeMostradorOut,
)

router = APIRouter(prefix="/offline", tags=["CU-13 a CU-19 · Offline y sincronización"])

Estado = Literal["CONFIRMADA", "RECHAZADA"]


@router.get(
    "/paquete",
    response_model=PaqueteDeMostradorOut,
    summary="CU-13 Preparar el dispositivo (mostrador)",
    dependencies=[Depends(requiere_roles("CAJERO", "ENCARGADO"))],
)
def paquete_de_mostrador(db: DbSession, usuario: Usuario):
    """Prendas con precio y saldo de la sucursal, el turno abierto y los
    clientes mínimos, para vender sin conexión."""
    try:
        return service.paquete_de_mostrador(db, usuario.id)
    except service.ErrorOffline as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.get(
    "/paquete-cliente",
    response_model=PaqueteDeClienteOut,
    summary="CU-13 Preparar el dispositivo (cliente)",
    dependencies=[Depends(requiere_roles("CLIENTE"))],
)
def paquete_de_cliente(db: DbSession):
    """Sucursales y prendas con su saldo por sucursal, para reservar sin
    conexión (CU-15)."""
    return service.paquete_de_cliente(db)


@router.post(
    "/sincronizar",
    response_model=LoteOut,
    summary="CU-17 Sincronizar operaciones pendientes",
    dependencies=[Depends(requiere_roles("CAJERO", "ENCARGADO", "CLIENTE"))],
)
def sincronizar(lote: LoteIn, db: DbSession, usuario: Usuario):
    """Confirma o rechaza cada operación del lote. Es idempotente por UUID:
    reenviar una operación devuelve lo que se decidió la primera vez."""
    if usuario.rol == "CLIENTE" and any(o.tipo == "VENTA" for o in lote.operaciones):
        raise HTTPException(403, "Un cliente no registra ventas de mostrador.")
    try:
        return service.sincronizar(
            db,
            usuario_id=usuario.id,
            rol=usuario.rol,
            sucursal_del_usuario=usuario.sucursal_id,
            lote=lote,
        )
    except service.ErrorOffline as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.get(
    "/operaciones/mias",
    response_model=list[OperacionOut],
    summary="CU-18 Consultar operaciones ya sincronizadas",
    dependencies=[Depends(requiere_roles("CAJERO", "ENCARGADO", "CLIENTE"))],
)
def operaciones_mias(
    db: DbSession, usuario: Usuario, estado: Annotated[Estado | None, Query()] = None
):
    return service.operaciones_mias(db, usuario.id, estado=estado)


@router.get(
    "/operaciones",
    response_model=list[OperacionOut],
    summary="CU-19 Operaciones offline de la sucursal",
    dependencies=[Depends(requiere_roles("ENCARGADO", "ADMINISTRADOR"))],
)
def operaciones_de_sucursal(
    db: DbSession,
    usuario: Usuario,
    estado: Annotated[Estado | None, Query()] = None,
    por_devolver: bool = False,
):
    return service.operaciones_de_sucursal(
        db, _ambito(usuario), estado=estado, por_devolver=por_devolver
    )


@router.post(
    "/operaciones/{uuid}/devolucion",
    response_model=OperacionOut,
    summary="CU-19 Registrar la devolución del dinero",
    dependencies=[Depends(requiere_roles("ENCARGADO", "ADMINISTRADOR"))],
)
def registrar_devolucion(uuid: UUID, datos: DevolucionIn, db: DbSession, usuario: Usuario):
    try:
        return service.registrar_devolucion(
            db, uuid, datos, usuario_id=usuario.id, sucursal_id=_ambito(usuario)
        )
    except service.ErrorOffline as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


def _ambito(usuario) -> int | None:
    """El encargado ve su sucursal; el administrador, todas."""
    if usuario.rol == "ADMINISTRADOR":
        return None
    if usuario.sucursal_id is None:
        raise HTTPException(403, "Su cuenta no está asignada a ninguna sucursal.")
    return usuario.sucursal_id
