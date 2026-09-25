"""
P7 - Punto de Venta / CU-32  |  capa: router

Registrar devolucion.

QUIEN PUEDE
-----------
CAJERO y ENCARGADO, los mismos que CU-30 y CU-31: la devolucion sale de un
cajon y cuelga de un turno, igual que la venta.

NINGUN ENDPOINT RECIBE `sucursal_id`
-------------------------------------
Sale del turno abierto de quien pide. Convencion 2 del ciclo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.pos import devolucion_service as service
from app.modules.pos.devolucion_schemas import (
    CambioIn,
    CambioOut,
    DevolucionIn,
    DevolucionOut,
    VentaDevolvibleOut,
)
from app.modules.pos.service import ErrorDeMostrador

router = APIRouter(
    prefix="/pos/devoluciones",
    tags=["CU-32 · Registrar devolución"],
    dependencies=[Depends(requiere_roles("CAJERO", "ENCARGADO"))],
)


@router.get("/ventas/{codigo}", response_model=VentaDevolvibleOut)
def venta_a_devolver(
    codigo: Annotated[str, Path(min_length=3, max_length=20)],
    db: DbSession,
    usuario: Usuario,
):
    """La venta y **lo que todavía queda por devolver** de ella.

    No alcanza con listar lo vendido: una venta puede haberse devuelto en
    parte, y ofrecer las unidades que ya volvieron llevaría a reingresar dos
    veces una prenda que salió una sola.
    """
    try:
        return service.buscar_venta(db, usuario.id, codigo)
    except ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.post("", response_model=DevolucionOut, status_code=201)
def registrar_devolucion(datos: DevolucionIn, db: DbSession, usuario: Usuario):
    """Recibe la prenda de vuelta y la reingresa al inventario.

    **El dinero sale del cajón solo si la venta se cobró en efectivo.** La
    respuesta lo dice con `sale_del_cajon`: reintegrar en billetes un cobro con
    tarjeta dejaría el arqueo del turno con un faltante que nadie puede
    explicar, porque esa plata nunca entró al cajón.
    """
    try:
        return service.registrar(db, usuario.id, datos)
    except ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.post("/cambios", response_model=CambioOut, status_code=201)
def registrar_cambio(datos: CambioIn, db: DbSession, usuario: Usuario):
    """Recibe una prenda y entrega otra en su lugar, en una sola operación.

    **Es un endpoint aparte y no un `POST ""` con un campo de más.** Los dos
    flujos devuelven cosas distintas —una devolución entrega un reintegro; un
    cambio entrega una venta nueva con su comprobante— y un contrato que
    sirviera para los dos tendría la mitad de los campos en nulo según el caso,
    que es justo lo que obliga a la pantalla a adivinar cuál recibió.

    **La diferencia la calcula el servidor**, con los precios y las promociones
    vigentes al confirmar. `diferencia_esperada` es una guarda opcional: si la
    pantalla traía otro número, se rechaza en vez de cobrar callado algo que el
    cliente no vio.
    """
    try:
        return service.registrar_cambio(db, usuario.id, datos)
    except ErrorDeMostrador as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e
