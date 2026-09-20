"""
P4 - Inventario / CU-39  |  capa: router

Realiza el **RF38**. Es del PROVEEDOR: nadie mas anuncia lo que va a traer.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.abastecimiento import service
from app.modules.abastecimiento.schemas import (
    AnunciarIn,
    AnuncioOut,
    VarianteAnunciableOut,
)

router = APIRouter(
    prefix="/proveedor/abastecimiento",
    tags=["CU-39 · Informar abastecimiento"],
    dependencies=[Depends(requiere_roles("PROVEEDOR"))],
)


def _traducir(e: service.ErrorDeAbastecimiento) -> HTTPException:
    return HTTPException(e.codigo, detail=e.mensaje)


@router.get("/variantes", response_model=list[VarianteAnunciableOut])
def variantes_que_puedo_anunciar(db: DbSession, usuario: Usuario):
    """Las combinaciones de MIS productos, para elegir en el formulario."""
    try:
        return service.mis_variantes(db, usuario.id)
    except service.ErrorDeAbastecimiento as e:
        raise _traducir(e) from e


@router.get("", response_model=list[AnuncioOut])
def mis_avisos(
    db: DbSession,
    usuario: Usuario,
    incluir_cancelados: Annotated[bool, Query()] = False,
):
    """Lo que informé. Por omisión solo lo vigente."""
    try:
        return service.mis_anuncios(
            db, usuario.id, incluir_cancelados=incluir_cancelados
        )
    except service.ErrorDeAbastecimiento as e:
        raise _traducir(e) from e


@router.post("", response_model=AnuncioOut, status_code=status.HTTP_201_CREATED)
def informar(datos: AnunciarIn, db: DbSession, usuario: Usuario):
    """Informa que puedo abastecer una prenda, cuánto y en cuántos días.

    Es lo único que produce el estado «próxima a ingresar» del inventario
    consolidado (CU-16).
    """
    try:
        return service.anunciar(
            db,
            usuario.id,
            variante_id=datos.variante_id,
            cantidad=datos.cantidad,
            dias_plazo=datos.dias_plazo,
            observacion=datos.observacion,
        )
    except service.ErrorDeAbastecimiento as e:
        raise _traducir(e) from e


@router.delete("/{anuncio_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar(
    anuncio_id: Annotated[int, Path(ge=1)], db: DbSession, usuario: Usuario
):
    """Retira el aviso. La prenda deja de figurar como próxima a ingresar.

    Se marca CANCELADO y no se borra: el compromiso existió, y el inventario
    que lo mostró durante una semana tiene que poder explicarse después.
    """
    try:
        service.cancelar(db, usuario.id, anuncio_id)
    except service.ErrorDeAbastecimiento as e:
        raise _traducir(e) from e
