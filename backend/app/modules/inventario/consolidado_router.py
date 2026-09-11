"""
P4 - Inventario / CU-14  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2
Caso de uso: CU-14 Consultar inventario consolidado

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.dependencies import DbSession, requiere_roles
from app.modules.inventario import consolidado_service as service
from app.modules.inventario.consolidado_schemas import (
    EstadoExistencia,
    PaginaInventarioConsolidado,
    ResumenInventarioOut,
)


class InventarioConsolidadoOut(BaseModel):
    """El listado y su resumen, en una sola respuesta.

    Van juntos y no en dos endpoints porque la pantalla los muestra siempre a la
    vez y se calculan del mismo filtrado: separarlos serian dos consultas que
    recorren lo mismo, y abriria la posibilidad de que la cabecera y la tabla
    muestren filtros distintos si una de las dos llega tarde.
    """

    listado: PaginaInventarioConsolidado
    resumen: ResumenInventarioOut


# Solo Administrador, y ahi esta la diferencia con el `operacion_router` de
# CU-13 y CU-15, que tambien admite al Encargado.
#
# CU-14 es la vista de **toda la red**: su valor es comparar una sucursal contra
# otra --- es lo que permite ver el desbalance de stock entre tiendas ---. Un
# Encargado tiene el ambito acotado a la suya (§6.11 de las decisiones tecnicas),
# asi que darle acceso seria, o bien mostrarle la red entera, o bien devolverle
# una vista de red con una sola sucursal, que es el listado que ya tiene en su
# propia pantalla. Su caso de uso es el CU-16.
router = APIRouter(
    prefix="/inventario",
    tags=["Inventario"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


@router.get(
    "/consolidado",
    response_model=InventarioConsolidadoOut,
    summary="CU-14 Consultar inventario consolidado",
)
def consultar_consolidado(
    db: DbSession,
    busqueda: Annotated[
        str | None, Query(max_length=120, description="SKU, prenda o color")
    ] = None,
    sucursal_id: Annotated[int | None, Query()] = None,
    producto_id: Annotated[int | None, Query()] = None,
    estado: Annotated[EstadoExistencia | None, Query()] = None,
    orden: Annotated[str, Query(pattern="^(prenda|disponible_asc|disponible_desc|sucursales)$")] = "prenda",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> InventarioConsolidadoOut:
    """Paso 2: las existencias de toda la red, agrupadas por variante (RF21).

    Devuelve una fila **por variante**, con su reparto entre sucursales adentro.
    Es lo que distingue esta pantalla de la pestaña de existencias de CU-13 y
    CU-15: aquella responde «sobre qué fila opero», y ésta, «cómo está repartida
    la prenda en la red».

    `estado` admite `proxima_a_ingresar` en el contrato, pero hoy **ninguna fila
    lo devuelve**: no hay caso de uso que anuncie mercadería en camino. Ver la
    docstring de `EstadoExistencia`.
    """
    listado, resumen = service.consultar(
        db,
        pagina=pagina,
        tamano=tamano,
        orden=orden,
        busqueda=busqueda,
        sucursal_id=sucursal_id,
        producto_id=producto_id,
        estado=estado,
    )
    return InventarioConsolidadoOut(listado=listado, resumen=resumen)
