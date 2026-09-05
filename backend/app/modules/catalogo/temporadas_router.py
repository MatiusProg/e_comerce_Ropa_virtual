"""
P3 - Catalogo  |  CU-09 Gestionar temporadas y colecciones  |  capa: router

Ciclo de desarrollo: 1

Archivos propios para no chocar con el CU-08; el motivo esta en
`temporadas_schemas.py`. Se monta en `app/main.py` en vez de colgarse del
router de catalogo, porque ese archivo si lo toca el CU-08.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, requiere_roles
from app.modules.catalogo import temporadas_service as service
from app.modules.catalogo.temporadas_schemas import (
    CambioEstadoColeccionIn,
    CambioEstadoTemporadaIn,
    ColeccionCrearIn,
    ColeccionEditarIn,
    ColeccionOut,
    TemporadaCrearIn,
    TemporadaEditarIn,
    TemporadaOut,
)

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.
#
# Todo el caso de uso exige rol Administrador, y la dependencia se declara UNA
# sola vez a nivel de router: endpoint por endpoint, olvidarla en uno solo
# abriria un agujero sin que nada avise.
router = APIRouter(
    prefix="/catalogo",
    tags=["Catalogo · Temporadas"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)

#: Codigo que la interfaz reconoce para saber que el 409 se puede reintentar
#: confirmando, en vez de ser un rechazo definitivo (excepcion E2).
SOLAPAMIENTO = "SOLAPAMIENTO"


def _traducir(error: service.ErrorDeTemporadas) -> HTTPException:
    """Convierte los errores de negocio de CU-09 en respuestas HTTP."""
    if isinstance(error, service.TemporadaInexistente):
        return HTTPException(404, "La temporada indicada no existe.")
    if isinstance(error, service.ColeccionInexistente):
        return HTTPException(404, "La colección indicada no existe.")
    if isinstance(error, service.TemporadaDuplicada):
        return HTTPException(409, "Ya existe una temporada con ese nombre.")
    if isinstance(error, service.NombreDeColeccionDuplicado):
        return HTTPException(
            409, "Ya existe una colección con ese nombre en la misma temporada."
        )
    if isinstance(error, service.SolapamientoDeTemporadas):
        # Excepcion E2. NO es un rechazo: el mensaje lleva el prefijo que la
        # interfaz reconoce para ofrecer confirmar y reenviar con
        # `confirmar_solapamiento`. Sin ese prefijo habria que adivinar de que
        # 409 se trata comparando textos.
        return HTTPException(
            409,
            f"{SOLAPAMIENTO}: el rango se superpone con {error}. "
            "Confirme si desea guardarla de todos modos.",
        )
    if isinstance(error, service.TemporadaConColecciones):
        # Excepcion E3.
        return HTTPException(
            409,
            "La temporada tiene colecciones asociadas y no puede eliminarse. "
            "Puede cerrarla en su lugar.",
        )
    if isinstance(error, service.RangoInvalido):
        # Excepcion E1.
        return HTTPException(
            422, "La fecha de fin debe ser posterior a la de inicio."
        )
    return HTTPException(400, "No se pudo completar la operación.")


# --- Temporadas ----------------------------------------------------------


@router.get(
    "/temporadas", response_model=list[TemporadaOut], summary="CU-09 Listar temporadas"
)
def listar_temporadas(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=60)] = None,
    activa: Annotated[bool | None, Query()] = None,
) -> list[TemporadaOut]:
    """Temporadas con su vigencia, estado y recuento de colecciones (paso 2)."""
    return service.listar_temporadas(db, busqueda=busqueda, activa=activa)


@router.post(
    "/temporadas",
    response_model=TemporadaOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-09 Registrar temporada",
    responses={
        409: {"description": "Nombre repetido, o solapamiento a confirmar (E2)."},
        422: {"description": "Fechas incoherentes (excepción E1)."},
    },
)
def crear_temporada(datos: TemporadaCrearIn, db: DbSession) -> TemporadaOut:
    """Registra una temporada.

    Si el rango se superpone con otra abierta responde 409 pidiendo
    confirmación; reenviar con `confirmar_solapamiento: true` la guarda igual.
    """
    try:
        return service.crear_temporada(db, datos)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.get(
    "/temporadas/{temporada_id}",
    response_model=TemporadaOut,
    summary="CU-09 Ver una temporada",
)
def obtener_temporada(temporada_id: int, db: DbSession) -> TemporadaOut:
    try:
        return service.obtener_temporada(db, temporada_id)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.patch(
    "/temporadas/{temporada_id}",
    response_model=TemporadaOut,
    summary="CU-09 Editar temporada",
)
def editar_temporada(
    temporada_id: int, datos: TemporadaEditarIn, db: DbSession
) -> TemporadaOut:
    """Modifica una temporada (flujo alternativo 3a)."""
    try:
        return service.editar_temporada(db, temporada_id, datos)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.patch(
    "/temporadas/{temporada_id}/estado",
    response_model=TemporadaOut,
    summary="CU-09 Cerrar o reabrir una temporada",
)
def cambiar_estado_temporada(
    temporada_id: int, datos: CambioEstadoTemporadaIn, db: DbSession
) -> TemporadaOut:
    """Flujo alternativo 3b.

    Cerrarla no borra nada: sus productos siguen siendo consultables, solo
    dejan de considerarse de temporada vigente.
    """
    try:
        return service.cambiar_estado_temporada(
            db, temporada_id, datos.activa, confirmado=datos.confirmar_solapamiento
        )
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.delete(
    "/temporadas/{temporada_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-09 Eliminar temporada",
    responses={409: {"description": "Tiene colecciones asociadas (excepción E3)."}},
)
def eliminar_temporada(temporada_id: int, db: DbSession) -> None:
    """Elimina la temporada, solo si no tiene colecciones (excepción E3)."""
    try:
        service.eliminar_temporada(db, temporada_id)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


# --- Colecciones (flujo alternativo 1a) ----------------------------------


@router.get(
    "/colecciones",
    response_model=list[ColeccionOut],
    summary="CU-09 Listar colecciones",
)
def listar_colecciones(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=60)] = None,
    temporada_id: Annotated[int | None, Query()] = None,
    activa: Annotated[bool | None, Query()] = None,
) -> list[ColeccionOut]:
    return service.listar_colecciones(
        db, busqueda=busqueda, temporada_id=temporada_id, activa=activa
    )


@router.post(
    "/colecciones",
    response_model=ColeccionOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-09 Registrar colección",
    responses={409: {"description": "El nombre ya existe en esa temporada."}},
)
def crear_coleccion(datos: ColeccionCrearIn, db: DbSession) -> ColeccionOut:
    """Flujo alternativo 1a."""
    try:
        return service.crear_coleccion(db, datos)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.get(
    "/colecciones/{coleccion_id}",
    response_model=ColeccionOut,
    summary="CU-09 Ver una colección",
)
def obtener_coleccion(coleccion_id: int, db: DbSession) -> ColeccionOut:
    try:
        return service.obtener_coleccion(db, coleccion_id)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.patch(
    "/colecciones/{coleccion_id}",
    response_model=ColeccionOut,
    summary="CU-09 Editar colección",
)
def editar_coleccion(
    coleccion_id: int, datos: ColeccionEditarIn, db: DbSession
) -> ColeccionOut:
    """Flujo alternativo 3a."""
    try:
        return service.editar_coleccion(db, coleccion_id, datos)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)


@router.patch(
    "/colecciones/{coleccion_id}/estado",
    response_model=ColeccionOut,
    summary="CU-09 Dar de baja o reactivar una colección",
)
def cambiar_estado_coleccion(
    coleccion_id: int, datos: CambioEstadoColeccionIn, db: DbSession
) -> ColeccionOut:
    """La colección no se elimina: se conserva por trazabilidad."""
    try:
        return service.cambiar_estado_coleccion(db, coleccion_id, datos.activa)
    except service.ErrorDeTemporadas as error:
        raise _traducir(error)
