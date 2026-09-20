"""
P7 - Punto de Venta / CU-31  |  capa: router

Registrar venta presencial.

QUIEN PUEDE
-----------
CAJERO y ENCARGADO, los mismos que CU-30 y por el mismo motivo: el encargado
atiende el mostrador en sucursales chicas ---que es el caso de esta tienda--- y
dejarlo afuera obligaria a tener un usuario Cajero de mentira para poder cobrar.

El ADMINISTRADOR no: no esta en una sucursal ni tiene turno abierto, y toda
venta presencial cuelga de un turno.

NINGUN ENDPOINT RECIBE `sucursal_id`
-------------------------------------
Todos lo sacan del turno abierto de quien pide. Es la convencion 2 del ciclo:
un dato de ambito **no se acepta y se comprueba, no se acepta**. Por eso la
firma de cada funcion lleva `usuario` y nunca una sucursal en la URL.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.pos import service
from app.modules.pos.schemas import (
    PaginaDePrendas,
    ReservaPorCobrarOut,
    VentaPresencialIn,
    VentaPresencialOut,
)

router = APIRouter(
    prefix="/pos",
    tags=["CU-31 · Registrar venta presencial"],
    dependencies=[Depends(requiere_roles("CAJERO", "ENCARGADO"))],
)


@router.get("/prendas", response_model=PaginaDePrendas)
def prendas_del_mostrador(
    db: DbSession,
    usuario: Usuario,
    busqueda: Annotated[str | None, Query(max_length=80)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
):
    """Lo que hay para vender en la sucursal de quien cobra.

    Solo con saldo: una prenda agotada no se puede vender, y ofrecerla llevaria
    al cajero a armar un ticket que va a fallar con el cliente delante.
    """
    try:
        total, items = service.buscar_prendas(
            db, usuario.id, busqueda=busqueda, pagina=pagina, tamano=tamano
        )
    except service.ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e
    return PaginaDePrendas(total=total, pagina=pagina, tamano=tamano, items=items)


@router.get("/reservas", response_model=list[ReservaPorCobrarOut])
def reservas_por_cobrar(db: DbSession, usuario: Usuario):
    """Las reservas que el Encargado ya atendió y que nadie cobró todavía.

    Es el puente de la decisión D2: la reserva atendida (CU-24) y la venta
    presencial son el mismo acto comercial visto desde dos lados, y esta lista
    es lo que evita que el cajero tenga que volver a cargar a mano lo que el
    cliente ya se probó y se llevó.
    """
    try:
        return service.reservas_por_cobrar(db, usuario.id)
    except service.ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.get("/reservas/{reserva_id}", response_model=ReservaPorCobrarOut)
def ver_reserva(
    reserva_id: Annotated[int, Path(ge=1)], db: DbSession, usuario: Usuario
):
    """El detalle de una reserva por cobrar, con los precios de hoy."""
    try:
        return service.ver_reserva(db, usuario.id, reserva_id)
    except service.ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.post("/ventas", response_model=VentaPresencialOut, status_code=201)
def registrar_venta(datos: VentaPresencialIn, db: DbSession, usuario: Usuario):
    """Cobra en el mostrador y emite el comprobante.

    La venta nace **PAGADA**: el dinero se recibe en el acto y no hay pasarela
    que confirme nada.
    """
    try:
        return service.registrar_venta(db, usuario.id, datos)
    except service.ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.get("/ventas/{codigo}", response_model=VentaPresencialOut)
def ver_venta(
    codigo: Annotated[str, Path(min_length=3, max_length=20)],
    db: DbSession,
    usuario: Usuario,
):
    """Relee una venta del mostrador, para reimprimir el ticket."""
    try:
        return service.ver_venta(db, usuario.id, codigo)
    except service.ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.get(
    "/ventas/{codigo}/comprobante",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def comprobante(
    codigo: Annotated[str, Path(min_length=3, max_length=20)],
    db: DbSession,
    usuario: Usuario,
):
    """El comprobante en PDF, para imprimirlo o mandarlo.

    `inline` y no `attachment`: en el mostrador lo que se quiere es que se abra
    y se imprima, no que se baje a una carpeta de descargas.
    """
    try:
        nombre, cuerpo = service.comprobante_en_pdf(db, usuario.id, codigo)
    except service.ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e
    return Response(
        content=cuerpo,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{nombre}"'},
    )
