"""
P15 - Devoluciones por la web / CU-24  |  capa: router

QUIÉN PUEDE
-----------
- Entregar un pedido y ver las solicitudes: ENCARGADO, de su sucursal, y el
  ADMINISTRADOR, de todas.
- Pedir el cambio o la devolución y ver las suyas: el CLIENTE.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.devoluciones_web import service
from app.modules.devoluciones_web.schemas import (
    ConformidadClienteIn,
    PedidoDeSucursalOut,
    RespuestaIn,
    PedidoDevolvibleOut,
    SolicitudIn,
    SolicitudOut,
)
from app.modules.pos.devolucion_schemas import NotaDevolucionOut

sucursal_router = APIRouter(
    prefix="/sucursal",
    tags=["CU-24 · Devoluciones por la web (sucursal)"],
    dependencies=[Depends(requiere_roles("ENCARGADO", "ADMINISTRADOR"))],
)
cliente_router = APIRouter(
    prefix="/tienda/devoluciones",
    tags=["CU-24 · Devoluciones por la web (cliente)"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
)


def _ambito(usuario) -> int | None:
    if usuario.rol == "ADMINISTRADOR":
        return None
    if usuario.sucursal_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Su cuenta no está asignada a ninguna sucursal.")
    return usuario.sucursal_id


def _http(e: service.ErrorDevolucionWeb) -> HTTPException:
    return HTTPException(e.codigo, e.mensaje)


# --- Precondición: entregar el pedido ------------------------------------

@sucursal_router.get(
    "/pedidos", response_model=list[PedidoDeSucursalOut], summary="Pedidos web de la sucursal"
)
def pedidos_de_sucursal(
    db: DbSession,
    usuario: Usuario,
    estado: Annotated[Literal["PAGADA", "ENTREGADA"] | None, Query()] = None,
):
    return service.pedidos_de_sucursal(db, sucursal_id=_ambito(usuario), estado=estado)


@sucursal_router.post(
    "/pedidos/{codigo}/entregar",
    response_model=PedidoDeSucursalOut,
    summary="Marcar un pedido web como entregado (desde acá corre la ventana)",
)
def entregar(codigo: str, db: DbSession, usuario: Usuario):
    try:
        return service.entregar(db, codigo, sucursal_id=_ambito(usuario))
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


@sucursal_router.get(
    "/solicitudes-devolucion",
    response_model=list[SolicitudOut],
    summary="CU-25 Solicitudes de cambio o devolución de la sucursal",
)
def solicitudes_de_sucursal(
    db: DbSession,
    usuario: Usuario,
    estado: Annotated[
        Literal["PENDIENTE", "APROBADA", "RECHAZADA", "COMPLETADA"] | None, Query()
    ] = None,
):
    return service.solicitudes_de_sucursal(db, sucursal_id=_ambito(usuario), estado=estado)


# --- CU-24: el cliente ---------------------------------------------------------

@cliente_router.get(
    "/pedidos/{codigo}",
    response_model=PedidoDevolvibleOut,
    summary="CU-24 Qué puedo devolver o cambiar de este pedido",
)
def pedido_devolvible(codigo: str, db: DbSession, usuario: Usuario):
    try:
        return service.pedido_devolvible(db, usuario.id, codigo)
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


@cliente_router.post(
    "", response_model=SolicitudOut, status_code=201,
    summary="CU-24 Solicitar el cambio o la devolución",
)
def solicitar(datos: SolicitudIn, db: DbSession, usuario: Usuario):
    try:
        return service.solicitar(db, usuario.id, datos)
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


@cliente_router.get("", response_model=list[SolicitudOut], summary="CU-24 Mis solicitudes")
def mis_solicitudes(db: DbSession, usuario: Usuario):
    try:
        return service.mis_solicitudes(db, usuario.id)
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


# --- CU-25: atender (encargado) ---------------------------------------------------

@sucursal_router.post(
    "/solicitudes-devolucion/{solicitud_id}/aprobar",
    response_model=SolicitudOut,
    summary="CU-25 Aprobar una solicitud de cambio o devolución",
)
def aprobar(solicitud_id: int, datos: RespuestaIn, db: DbSession, usuario: Usuario):
    try:
        return service.aprobar(
            db, solicitud_id, usuario_id=usuario.id, sucursal_id=_ambito(usuario),
            respuesta=datos.respuesta,
        )
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


@sucursal_router.post(
    "/solicitudes-devolucion/{solicitud_id}/rechazar",
    response_model=SolicitudOut,
    summary="CU-25 Rechazar una solicitud, con el motivo",
)
def rechazar(solicitud_id: int, datos: RespuestaIn, db: DbSession, usuario: Usuario):
    try:
        return service.rechazar(
            db, solicitud_id, usuario_id=usuario.id, sucursal_id=_ambito(usuario),
            respuesta=datos.respuesta,
        )
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


@sucursal_router.post(
    "/solicitudes-devolucion/{solicitud_id}/recibir",
    response_model=SolicitudOut,
    summary="CU-25 Recibir la prenda y reembolsar por la pasarela",
)
def recibir(solicitud_id: int, db: DbSession, usuario: Usuario):
    try:
        return service.recibir(db, solicitud_id, usuario_id=usuario.id, sucursal_id=_ambito(usuario))
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


# --- CU-25: el cliente da su conformidad (RN-20) ----------------------------------

@cliente_router.post(
    "/{solicitud_id}/conformidad",
    response_model=SolicitudOut,
    summary="CU-25 Dar o negar la conformidad con la devolución",
)
def conformidad(solicitud_id: int, datos: ConformidadClienteIn, db: DbSession, usuario: Usuario):
    try:
        return service.conformidad(
            db, usuario.id, solicitud_id, conforme=datos.conforme, observacion=datos.observacion
        )
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e


@cliente_router.get(
    "/{solicitud_id}/nota",
    response_model=NotaDevolucionOut,
    summary="CU-25 La nota de mi devolución",
)
def nota(solicitud_id: int, db: DbSession, usuario: Usuario):
    try:
        return service.nota_del_cliente(db, usuario.id, solicitud_id)
    except service.ErrorDevolucionWeb as e:
        raise _http(e) from e
