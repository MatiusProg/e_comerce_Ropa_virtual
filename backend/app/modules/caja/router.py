"""
P7 - Ventas y POS / CU-30  |  capa: router

Abrir y cerrar caja. Es la puerta de CU-31: la base exige `turno_caja_id` en
toda venta presencial, asi que sin turno abierto no se puede cobrar.

QUIEN PUEDE
-----------
CAJERO y ENCARGADO. El encargado atiende el mostrador en sucursales chicas
---que es el caso de esta tienda--- y dejarlo afuera obligaria a tener un
usuario Cajero de mentira para poder cobrar.

El ADMINISTRADOR no: no esta en una sucursal, y un turno que nadie abrio
fisicamente no tiene arqueo posible.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.caja import service
from app.modules.caja.schemas import (
    AbrirTurnoIn,
    CajaOut,
    CerrarTurnoIn,
    TurnoOut,
)

router = APIRouter(
    prefix="/caja",
    tags=["CU-30 · Abrir y cerrar caja"],
    dependencies=[Depends(requiere_roles("CAJERO", "ENCARGADO"))],
)


def _salida(estado: service.EstadoDelTurno) -> TurnoOut:
    turno = estado.turno
    return TurnoOut(
        id=turno.id,
        caja_id=turno.caja_id,
        caja_nombre=estado.caja_nombre,
        sucursal_nombre=estado.sucursal_nombre,
        abierto_en=turno.abierto_en,
        cerrado_en=turno.cerrado_en,
        monto_apertura=turno.monto_apertura,
        efectivo_cobrado=estado.efectivo,
        devoluciones=estado.devoluciones,
        cambios=estado.cambios,
        monto_esperado=estado.esperado,
        monto_cierre=turno.monto_cierre,
        diferencia=estado.diferencia,
        por_metodo=[
            {"metodo": l.metodo, "ventas": l.ventas, "total": l.total}
            for l in estado.por_metodo
        ],
    )


def _sucursal_del_usuario(usuario) -> int:
    if usuario.sucursal_id is None:
        # Pasa con un Cajero mal dado de alta. Es 409 y no 500: el dato falta
        # y hay quien puede arreglarlo, pero no es culpa de la peticion.
        raise HTTPException(
            409,
            detail=(
                "Su usuario no está asignado a ninguna sucursal. "
                "Pídale al administrador que lo asigne."
            ),
        )
    return usuario.sucursal_id


@router.get("/cajas", response_model=list[CajaOut])
def cajas_de_mi_sucursal(db: DbSession, usuario: Usuario):
    """Las cajas activas de la sucursal del usuario, con cuál está ocupada."""
    sucursal_id = _sucursal_del_usuario(usuario)
    return [
        CajaOut(id=caja.id, nombre=caja.nombre, ocupada=ocupada)
        for caja, ocupada in service.cajas_disponibles(db, sucursal_id)
    ]


@router.get("/turnos/mio", response_model=TurnoOut | None)
def mi_turno_abierto(db: DbSession, usuario: Usuario):
    """El turno que tengo abierto, o `null`.

    Devuelve `null` y no 404 porque **no tener turno abierto es el estado
    normal** al empezar el dia. Con 404 la pantalla trataria lo corriente por
    el camino de los fallos.
    """
    estado = service.mi_turno(db, usuario.id)
    return _salida(estado) if estado else None


@router.post("/turnos", response_model=TurnoOut, status_code=201)
def abrir_turno(datos: AbrirTurnoIn, db: DbSession, usuario: Usuario):
    """Abre el turno en una caja libre."""
    try:
        return _salida(
            service.abrir(
                db,
                caja_id=datos.caja_id,
                usuario_id=usuario.id,
                monto_apertura=datos.monto_apertura,
            )
        )
    except service.ErrorDeCaja as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e


@router.post("/turnos/{turno_id}/cierre", response_model=TurnoOut)
def cerrar_turno(
    turno_id: Annotated[int, Path(ge=1)],
    datos: CerrarTurnoIn,
    db: DbSession,
    usuario: Usuario,
):
    """Cierra el turno con el arqueo.

    Devuelve los tres numeros: lo que el sistema esperaba, lo que la persona
    conto, y la diferencia. **Nunca rechaza un conteo por no cuadrar**: el
    descuadre es justamente lo que hay que registrar.
    """
    try:
        return _salida(
            service.cerrar(
                db,
                turno_id=turno_id,
                usuario_id=usuario.id,
                monto_cierre=datos.monto_cierre,
            )
        )
    except service.ErrorDeCaja as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e
