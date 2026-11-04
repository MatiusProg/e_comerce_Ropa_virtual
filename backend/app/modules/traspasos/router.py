"""
P15 - Traspasos entre sucursales / CU-33, CU-34 y CU-35  |  capa: router

QUIÉN PUEDE
-----------
- Pedir, seguir y atender: ENCARGADO, sobre los traspasos de su sucursal, y
  ADMINISTRADOR, sobre todos. Quién hace cada paso lo decide el servicio.
- Los sugeridos (CU-35): solo el ADMINISTRADOR, y solo si el plan incluye la
  función `traspasos_sugeridos` (CU-05).
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.core.dependencies import (
    DbSession,
    Usuario,
    UsuarioActual,
    requiere_funcion,
    requiere_roles,
)
from app.modules.traspasos import service
from app.modules.traspasos.schemas import (
    AprobarIn,
    Estado,
    OrigenPosibleOut,
    PaginaTraspasos,
    PrendaPedibleOut,
    RechazarIn,
    SolicitarTraspasoIn,
    SugerenciasOut,
    TraspasoOut,
)

router = APIRouter(
    prefix="/traspasos",
    tags=["CU-33 a CU-35 · Traspasos entre sucursales"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR", "ENCARGADO"))],
)

Id = Annotated[int, Path(ge=1)]


def _quien(usuario: UsuarioActual) -> service.Quien:
    return service.Quien(
        usuario_id=usuario.id, rol=usuario.rol, sucursal_id=usuario.sucursal_id
    )


def _traducir(e: service.ErrorDeTraspaso) -> HTTPException:
    return HTTPException(e.codigo, detail=e.mensaje)


# --- CU-35 (va antes de /{id} para que «sugeridos» no se lea como un id) ---
@router.get(
    "/sugeridos",
    response_model=SugerenciasOut,
    summary="CU-35 Consultar traspasos sugeridos",
    dependencies=[
        Depends(requiere_roles("ADMINISTRADOR")),
        Depends(requiere_funcion("traspasos_sugeridos")),
    ],
)
def sugeridos(db: DbSession, dias: Annotated[int, Query(ge=7, le=180)] = 30):
    """Qué mover y de dónde a dónde, según las prendas más vendidas de cada
    sucursal y la existencia de cada una (RF-42). No escribe nada: ordenar
    uno es un POST a `/traspasos` con `desde_sugerencia`."""
    return service.sugeridos(db, dias=dias)


# --- Seguimiento -----------------------------------------------------------
@router.get("", response_model=PaginaTraspasos, summary="CU-34 Seguir los traspasos")
def listar(
    db: DbSession,
    usuario: Usuario,
    bandeja: Annotated[Literal["ENTRANTES", "SALIENTES"] | None, Query()] = None,
    estado: Annotated[Estado | None, Query()] = None,
    abiertos: Annotated[bool, Query()] = False,
    sucursal_id: Annotated[int | None, Query(ge=1)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """ENTRANTES: lo que la sucursal pidió o le van a mandar. SALIENTES: lo
    que le piden. `sucursal_id` solo lo usa el administrador; al encargado le
    vale siempre la suya."""
    return service.listar(
        db,
        _quien(usuario),
        bandeja=bandeja,
        estado=estado,
        abiertos=abiertos,
        sucursal_id=sucursal_id,
        pagina=pagina,
        tamano=tamano,
    )


@router.get(
    "/prendas",
    response_model=list[PrendaPedibleOut],
    summary="CU-33 Prendas que se pueden pedir",
)
def prendas(
    db: DbSession,
    usuario: Usuario,
    busqueda: Annotated[str | None, Query(max_length=80)] = None,
):
    """Las prendas que alguna otra sucursal tiene disponibles (hasta 20)."""
    return service.prendas_pedibles(db, _quien(usuario), busqueda)


@router.get(
    "/origenes",
    response_model=list[OrigenPosibleOut],
    summary="CU-33 Sucursales que tienen la prenda",
)
def origenes(
    db: DbSession, usuario: Usuario, variante_id: Annotated[int, Query(ge=1)]
):
    """A quién se le puede pedir: las otras sucursales con unidades disponibles."""
    return service.origenes_posibles(db, _quien(usuario), variante_id)


@router.get("/{traspaso_id}", response_model=TraspasoOut, summary="CU-34 Ver un traspaso")
def obtener(traspaso_id: Id, db: DbSession, usuario: Usuario):
    try:
        return service.obtener(db, _quien(usuario), traspaso_id)
    except service.ErrorDeTraspaso as e:
        raise _traducir(e) from e


# --- CU-33 -------------------------------------------------------------------
@router.post(
    "",
    response_model=TraspasoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-33 Solicitar traspaso entre sucursales",
    responses={409: {"description": "No alcanza en el origen, o ya hay uno abierto."}},
)
def solicitar(datos: SolicitarTraspasoIn, db: DbSession, usuario: Usuario):
    """El encargado pide a otra sucursal para la suya y queda SOLICITADO. El
    administrador lo ordena entre dos cualesquiera y nace APROBADO (RF-40)."""
    try:
        return service.solicitar(db, _quien(usuario), datos)
    except service.ErrorDeTraspaso as e:
        raise _traducir(e) from e


# --- CU-34 -------------------------------------------------------------------
@router.post("/{traspaso_id}/aprobar", response_model=TraspasoOut, summary="CU-34 Aprobar")
def aprobar(traspaso_id: Id, db: DbSession, usuario: Usuario, datos: AprobarIn | None = None):
    """El origen acepta; puede bajar la cantidad si no le alcanza."""
    try:
        return service.aprobar(db, _quien(usuario), traspaso_id, datos or AprobarIn())
    except service.ErrorDeTraspaso as e:
        raise _traducir(e) from e


@router.post("/{traspaso_id}/rechazar", response_model=TraspasoOut, summary="CU-34 Rechazar")
def rechazar(traspaso_id: Id, datos: RechazarIn, db: DbSession, usuario: Usuario):
    """Con motivo. El origen, mientras no se envió; el destino, mientras siga
    SOLICITADO (retira su pedido)."""
    try:
        return service.rechazar(db, _quien(usuario), traspaso_id, datos)
    except service.ErrorDeTraspaso as e:
        raise _traducir(e) from e


@router.post("/{traspaso_id}/enviar", response_model=TraspasoOut, summary="CU-34 Enviar")
def enviar(traspaso_id: Id, db: DbSession, usuario: Usuario):
    """Descuenta del origen (RN-09). Si ya no alcanza, 409 y no se escribe nada."""
    try:
        return service.enviar(db, _quien(usuario), traspaso_id)
    except service.ErrorDeTraspaso as e:
        raise _traducir(e) from e


@router.post("/{traspaso_id}/recibir", response_model=TraspasoOut, summary="CU-34 Recibir")
def recibir(traspaso_id: Id, db: DbSession, usuario: Usuario):
    """Suma al destino (RN-09) y cierra el traspaso."""
    try:
        return service.recibir(db, _quien(usuario), traspaso_id)
    except service.ErrorDeTraspaso as e:
        raise _traducir(e) from e
