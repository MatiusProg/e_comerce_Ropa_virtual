"""
P11 - Reportes y Tablero / CU-36  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-36 Consultar tablero de indicadores

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSession, requiere_roles
from app.modules.reportes import tablero_service as service
from app.modules.reportes.tablero_schemas import TableroOut

# Solo Administrador, igual que CU-14 y por la misma razon de fondo: el valor
# del tablero es comparar --- una sucursal contra otra, esta semana contra la
# anterior ---, y esa lectura es de quien decide sobre la red entera.
#
# El Encargado NO entra, aunque el filtro por sucursal exista. Su ambito esta
# acotado a su local (seccion 6.11 de las decisiones tecnicas) y darle el
# tablero seria, o bien mostrarle numeros de tiendas que no maneja, o bien
# devolverle un tablero de una sola sucursal --- que son las alertas de stock
# que ya tiene en CU-16 y las reservas que ya tiene en CU-24 ---. Si mas
# adelante se decide darselo, es un router aparte con el `sucursal_id` tomado
# del token y no aceptado por la URL, que es la convencion 2 del ciclo.
router = APIRouter(
    prefix="/reportes",
    tags=["Reportes"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


@router.get(
    "/tablero",
    response_model=TableroOut,
    summary="CU-36 Consultar tablero de indicadores",
)
def consultar_tablero(
    db: DbSession,
    desde: Annotated[
        date | None,
        Query(description="Primer día del período. Por omisión, 30 días atrás."),
    ] = None,
    hasta: Annotated[
        date | None,
        Query(description="Último día, incluido. Por omisión, hoy."),
    ] = None,
    sucursal_id: Annotated[
        int | None,
        Query(description="Acota a una sucursal. Sin esto, la red entera."),
    ] = None,
) -> TableroOut:
    """Los KPIs del negocio en tiempo real (RF24).

    **Un solo endpoint devuelve el tablero entero.** Ver la docstring de
    `TableroOut`: las tarjetas salen del mismo filtrado y la pantalla las
    muestra juntas.

    **El bloque `inventario` ignora `desde` y `hasta`, a proposito.** Un saldo es
    una foto del instante y no un acumulado; `existencia` no tiene fecha contra
    la que filtrar. La pantalla lo rotula como «ahora» y no como parte del
    periodo --- ver `SaludInventarioOut`.

    **El bloque `ventas` viaja con `disponible: false`** hasta que exista la
    migración `0006_ciclo3_ventas`, que es de Mateo. Se declara igual para que
    la pantalla no cambie cuando aterrice; la razón larga está en la cabecera de
    `tablero_schemas.py`.

    Un `sucursal_id` que no existe devuelve ceros, no un 404: es de solo lectura
    y «no existe» se ve igual que «no tuvo movimiento».
    """
    return service.consultar(db, desde=desde, hasta=hasta, sucursal_id=sucursal_id)
