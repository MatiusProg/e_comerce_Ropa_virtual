"""
P12 - Bitacora / CU-42  |  capa: ruta

SOLO EL ADMINISTRADOR
----------------------
Y es una decision, no una omision. La bitacora dice a que hora entra cada
empleado, desde que direccion y que toca: en manos de un Encargado eso es
vigilancia de sus companeros, no auditoria. El Encargado ya tiene el reporte
de movimientos de SU sucursal, que es lo que necesita para su trabajo.

NO HAY FORMA DE ESCRIBIR, EDITAR NI BORRAR
-------------------------------------------
Este router solo tiene `GET`. Los asientos los pone el middleware; no existe
un `POST /bitacora` porque un asiento que se puede inventar a mano no prueba
nada, ni un `DELETE` porque justo quien tendria motivo para borrar es quien
tiene este rol.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import DbSession, requiere_roles
from app.modules.bitacora import service
from app.modules.bitacora.schemas import (
    AsientoOut,
    OpcionesBitacoraOut,
    PaginaBitacoraOut,
)

router = APIRouter(
    prefix="/bitacora",
    tags=["CU-42 · Consultar bitácora del sistema"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


@router.get(
    "",
    response_model=PaginaBitacoraOut,
    summary="CU-42 Consultar la bitácora",
)
def consultar(
    db: DbSession,
    desde: Annotated[date | None, Query(description="Desde este día, inclusive.")] = None,
    hasta: Annotated[date | None, Query(description="Hasta este día, inclusive.")] = None,
    usuario_id: Annotated[int | None, Query()] = None,
    rol: Annotated[
        str | None,
        Query(description="Un rol, o «EMPLEADOS» para los tres internos."),
    ] = None,
    accion: Annotated[str | None, Query()] = None,
    entidad: Annotated[str | None, Query()] = None,
    exito: Annotated[bool | None, Query(description="Solo las que salieron bien, o solo las que no.")] = None,
    busqueda: Annotated[str | None, Query(description="Busca en el correo y en la ruta.")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=service.TAMANO_MAXIMO)] = 50,
) -> PaginaBitacoraOut:
    """Los asientos, del más reciente al más viejo.

    Se pagina siempre: la bitácora de una tienda en marcha son miles de
    filas al mes y devolverlas enteras tumbaría la pantalla que existe para
    leerlas.
    """
    try:
        resultado = service.listar(
            db,
            desde=desde,
            hasta=hasta,
            usuario_id=usuario_id,
            rol=rol,
            accion=accion,
            entidad=entidad,
            exito=exito,
            busqueda=busqueda,
            pagina=pagina,
            tamano=tamano,
        )
    except service.ErrorDeBitacora as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e

    return PaginaBitacoraOut(
        total=resultado.total,
        pagina=resultado.pagina,
        tamano=resultado.tamano,
        items=[
            AsientoOut(
                id=a.id,
                ocurrido_en=service.en_bolivia(a.ocurrido_en),
                usuario_id=a.usuario_id,
                actor=a.actor,
                nombre=nombre,
                rol=a.rol,
                accion=a.accion,
                entidad=a.entidad,
                entidad_id=a.entidad_id,
                metodo=a.metodo,
                ruta=a.ruta,
                estado_http=a.estado_http,
                exito=a.exito,
                ip=a.ip,
                agente=a.agente,
                detalle=a.detalle,
            )
            for a, nombre in resultado.items
        ],
    )


@router.get(
    "/opciones",
    response_model=OpcionesBitacoraOut,
    summary="CU-42 Las acciones y entidades que hay registradas",
)
def opciones(db: DbSession) -> OpcionesBitacoraOut:
    """Para armar los filtros con lo que realmente hay.

    Con una lista escrita en el código, el filtro ofrecería acciones que no
    dan ningún resultado y escondería las que sí.
    """
    return OpcionesBitacoraOut(**service.opciones(db))
