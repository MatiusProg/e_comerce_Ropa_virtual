"""
P7 - Ventas / CU-29  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-29 Consultar historial de compras  (RF15, RF16)

EL PREFIJO ES /tienda/compras Y NO /tienda/pedidos
---------------------------------------------------
Aunque por debajo sean la misma tabla. Un «pedido» es el flujo de comprar ---
elegir, confirmar, pagar --- y vive mientras eso ocurre; una «compra» es lo que
quedo despues. Para el cliente son dos momentos distintos y los busca en lugares
distintos.

Ademas evita un enredo practico: `/tienda/pedidos` ya es de CU-27, y dos routers
con el mismo prefijo repartidos en dos archivos hacen que buscar donde esta un
endpoint sea adivinar.

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.seguridad import service as seguridad
from app.modules.ventas import historial_service as service
from app.modules.ventas import service as ventas_service
from app.modules.ventas.historial_schemas import PaginaCompras

router = APIRouter(
    prefix="/tienda/compras",
    tags=["Ventas · Compras"],
    # El rol se declara UNA vez a nivel de router: olvidarlo en un solo
    # endpoint abriria un agujero sin que nada avise.
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, seguridad.PerfilInexistente):
        return HTTPException(403, "Esta cuenta no tiene ficha de cliente.")
    if isinstance(error, ventas_service.PedidoInexistente):
        # 404 y nunca 403: un 403 confirmaria que ese codigo corresponde a una
        # compra real, y recorrer codigos se volveria un censo de compras.
        return HTTPException(404, "No encontramos esa compra.")
    if isinstance(error, service.SinComprobante):
        return HTTPException(
            409,
            "Esta compra todavía no se pagó, así que no tiene comprobante.",
        )
    raise error


@router.get(
    "",
    response_model=PaginaCompras,
    summary="CU-29 Mis compras",
)
def listar_compras(
    db: DbSession,
    usuario: Usuario,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=50)] = 10,
) -> PaginaCompras:
    """El historial del cliente, de la más nueva a la más vieja.

    **Van todas las compras**, incluidas las canceladas y las que esperan pago.
    Un historial que sólo mostrara lo pagado dejaría al cliente sin forma de
    encontrar el pedido que acaba de hacer —que es justo el que va a buscar— ni
    de entender por qué un cobro que recuerda no aparece. El estado se muestra;
    la fila no se esconde.
    """
    try:
        return service.listar_compras(db, usuario.id, pagina=pagina, tamano=tamano)
    except Exception as error:
        raise _traducir(error) from error


@router.get(
    "/{codigo}/comprobante",
    summary="CU-29 Descargar el comprobante de una compra",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "El recibo en PDF.",
        },
        404: {"description": "No existe esa compra, o es de otro cliente."},
        409: {"description": "La compra todavía no se pagó."},
    },
)
def descargar_comprobante(codigo: str, db: DbSession, usuario: Usuario) -> Response:
    """El recibo de una compra pagada, en PDF.

    **Se emite una vez y se reimprime siempre.** La primera descarga crea el
    comprobante con su número y su fecha; todas las siguientes devuelven ese
    mismo. Un comprobante que cambiara de número cada vez que se lo mira no
    serviría como comprobante de nada.

    Devuelve **409 y no 404** cuando la compra existe pero todavía espera el
    pago: el cliente tiene que poder distinguir «no encontramos esa compra» de
    «esa compra todavía no se pagó», porque lo que hace después es distinto.
    """
    try:
        nombre, cuerpo = service.comprobante_en_pdf(db, usuario.id, codigo)
    except Exception as error:
        raise _traducir(error) from error

    return Response(
        content=cuerpo,
        media_type="application/pdf",
        headers={
            # `attachment` y no `inline`: el enunciado pide **descargar** el
            # comprobante. Con `inline` el navegador lo abre en una pestaña y
            # guardarlo pasa a ser un paso mas que el cliente tiene que
            # descubrir solo.
            "Content-Disposition": f'attachment; filename="{nombre}"',
        },
        status_code=status.HTTP_200_OK,
    )
