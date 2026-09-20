"""
P3 - Catalogo / CU-12  |  capa: router

Gestionar promociones (RF35).

QUIEN PUEDE
-----------
Solo el ADMINISTRADOR. Un descuento cambia lo que la tienda cobra en todas sus
sucursales a la vez: no es una decision de mostrador.

Se declara UNA sola vez a nivel de router y no endpoint por endpoint; olvidarla
en uno solo abriria un agujero sin que nada avise. Es el criterio de CU-03,
CU-05, CU-08 y CU-09.

SE MONTA EN `main.py` Y NO CUELGA DEL ROUTER DE CATALOGO
---------------------------------------------------------
Mismo motivo que `temporadas_router`: `catalogo/router.py` lo tocan CU-10 y
CU-11, y colgarse de ahi seria editar un archivo compartido para no ganar nada.

NO HAY BORRADO
--------------
Una promocion se apaga, no se borra: las ventas ya cobradas con ella la nombran
en su historial, y volver a encenderla la temporada que viene es lo normal.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.dependencies import DbSession, requiere_roles
from app.modules.catalogo import promociones_service as service
from app.modules.catalogo.promociones_schemas import (
    Alcance,
    CambioEstadoIn,
    PaginaPromociones,
    PromocionCrearIn,
    PromocionEditarIn,
    PromocionOut,
)

router = APIRouter(
    prefix="/catalogo/promociones",
    tags=["Catálogo · Promociones"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


def _traducir(error: service.ErrorDePromociones) -> HTTPException:
    if isinstance(error, service.PromocionInexistente):
        return HTTPException(404, "La promoción indicada no existe.")
    if isinstance(error, service.NombreDuplicado):
        return HTTPException(
            409, f"Ya hay una promoción llamada «{error.nombre}»."
        )
    if isinstance(error, service.ObjetivoInexistente):
        nombre = {
            "PRODUCTO": "El producto",
            "CATEGORIA": "La categoría",
            "TEMPORADA": "La temporada",
        }[error.alcance]
        return HTTPException(404, f"{nombre} que eligió no existe.")
    if isinstance(error, service.VigenciaInvalida):
        return HTTPException(
            422, "La fecha de fin no puede ser anterior a la de inicio."
        )
    return HTTPException(400, "No se pudo completar la operación.")  # pragma: no cover


@router.get("", response_model=PaginaPromociones)
def listar_promociones(
    db: DbSession,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
    alcance: Alcance | None = None,
    solo_vigentes: bool = False,
):
    """Las promociones cargadas, con cuáles están descontando hoy.

    `vigente` no es lo mismo que `activa`: una promoción activa que empieza el
    mes que viene no está descontando nada, y sin distinguirlas el
    Administrador cree que algo está roto.
    """
    total, items = service.listar(
        db,
        pagina=pagina,
        tamano=tamano,
        alcance=alcance,
        solo_vigentes=solo_vigentes,
    )
    return PaginaPromociones(total=total, pagina=pagina, tamano=tamano, items=items)


@router.post("", response_model=PromocionOut, status_code=201)
def crear_promocion(datos: PromocionCrearIn, db: DbSession):
    """Define un descuento con vigencia sobre un producto, una categoría o una
    temporada."""
    try:
        return service.crear(db, datos)
    except service.ErrorDePromociones as e:
        raise _traducir(e) from e


@router.get("/{promocion_id}", response_model=PromocionOut)
def obtener_promocion(promocion_id: Annotated[int, Path(ge=1)], db: DbSession):
    try:
        return service.obtener(db, promocion_id)
    except service.ErrorDePromociones as e:
        raise _traducir(e) from e


@router.patch("/{promocion_id}", response_model=PromocionOut)
def editar_promocion(
    promocion_id: Annotated[int, Path(ge=1)],
    datos: PromocionEditarIn,
    db: DbSession,
):
    """Cambia el nombre, el porcentaje o la vigencia.

    **El alcance y el objetivo no se editan.** Cambiarle el alcance a una
    promoción viva es otra promoción: la que estaba corriendo alcanzaba otras
    prendas, y los pedidos ya cobrados con ella quedarían explicados por una
    regla que ya no dice lo mismo. Para eso se apaga esta y se crea otra.
    """
    try:
        return service.editar(db, promocion_id, datos)
    except service.ErrorDePromociones as e:
        raise _traducir(e) from e


@router.patch("/{promocion_id}/estado", response_model=PromocionOut)
def cambiar_estado(
    promocion_id: Annotated[int, Path(ge=1)],
    datos: CambioEstadoIn,
    db: DbSession,
):
    """Enciende o apaga la promoción. No hay borrado: ver la cabecera."""
    try:
        return service.cambiar_estado(db, promocion_id, datos)
    except service.ErrorDePromociones as e:
        raise _traducir(e) from e
