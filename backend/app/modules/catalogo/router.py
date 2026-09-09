"""
P3 - Catalogo / CU-10  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2
Caso de uso: CU-10 Gestionar productos y variantes

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.dependencies import DbSession, requiere_roles
from app.modules.catalogo import service
from app.modules.catalogo.imagenes_router import router as imagenes_router
from app.modules.catalogo.schemas import (
    CambioEstadoIn,
    GenerarVariantesIn,
    GenerarVariantesOut,
    PaginaProductos,
    ProductoCrearIn,
    ProductoEditarIn,
    ProductoOut,
    VarianteCrearIn,
    VarianteEditarIn,
    VarianteOut,
)

# Todo el caso de uso exige rol Administrador, y la dependencia se declara UNA
# sola vez a nivel de router: endpoint por endpoint, olvidarla en uno solo
# abriria un agujero sin que nada avise. Es el criterio de CU-03, CU-05, CU-06 y
# CU-08.
#
# La vitrina del cliente NO se sirve desde aqui: CU-17, CU-18 y CU-19 viven en
# el paquete P5 (catalogo_publico), con su propio router y sin exigencia de rol.
router = APIRouter(
    prefix="/catalogo",
    tags=["Catalogo · Productos"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


# CU-11 cuelga de este mismo router y hereda su exigencia de rol. Se incluye
# aqui y no en main.py para no tocar un archivo compartido: ver la cabecera de
# imagenes_router.py.
router.include_router(imagenes_router)


def _traducir(error: service.ErrorDeProductos) -> HTTPException:
    """Convierte los errores de negocio de CU-10 en respuestas HTTP."""
    if isinstance(error, service.ProductoInexistente):
        return HTTPException(404, "El producto indicado no existe.")
    if isinstance(error, service.VarianteInexistente):
        return HTTPException(404, "La variante indicada no existe.")
    if isinstance(error, service.MaestroInexistente):
        return HTTPException(
            404,
            "Alguno de los datos elegidos ya no existe: categoría, proveedor, "
            "temporada, colección, talla o color.",
        )
    if isinstance(error, service.CodigoDuplicado):
        # Excepcion E1. El caso de uso pide señalar el campo, así que la
        # interfaz usa este 409 sin cerrar el diálogo.
        return HTTPException(
            409, "Ya existe un producto con ese código, o una variante con ese SKU."
        )
    if isinstance(error, service.ColeccionAjenaALaTemporada):
        # Excepcion E2.
        return HTTPException(
            422,
            "La colección elegida pertenece a otra temporada. Corrija la "
            "temporada o elija una colección de la temporada indicada.",
        )
    if isinstance(error, service.SkuDemasiadoLargo):
        return HTTPException(
            422,
            "El código del producto es demasiado largo para generar los SKU de "
            "sus variantes. Use un código más corto.",
        )
    if isinstance(error, service.TieneDependencias):
        # Excepcion E3: la interfaz usa este mensaje para ofrecer desactivar.
        return HTTPException(
            409,
            "El producto ya tiene existencias o reservas asociadas y no puede "
            "eliminarse. Puede desactivarlo en su lugar.",
        )
    return HTTPException(400, "No se pudo completar la operación.")


# --- Productos (flujo principal) -----------------------------------------

@router.get(
    "/productos",
    response_model=PaginaProductos,
    summary="CU-10 Listado de productos",
)
def listar_productos(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=120, description="Nombre o código")] = None,
    categoria_id: Annotated[int | None, Query()] = None,
    temporada_id: Annotated[int | None, Query()] = None,
    coleccion_id: Annotated[int | None, Query()] = None,
    proveedor_id: Annotated[int | None, Query()] = None,
    activo: Annotated[bool | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaProductos:
    """Paso 2: los productos con sus filtros y su paginación.

    El tope de 100 por página no es decorativo: sin él, una petición con
    `tamano=100000` traería el catálogo entero y con él todas sus variantes.
    """
    return service.listar_productos(
        db,
        pagina=pagina,
        tamano=tamano,
        busqueda=busqueda,
        categoria_id=categoria_id,
        temporada_id=temporada_id,
        coleccion_id=coleccion_id,
        proveedor_id=proveedor_id,
        activo=activo,
    )


@router.post(
    "/productos",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-10 Registrar producto",
)
def crear_producto(datos: ProductoCrearIn, db: DbSession) -> ProductoOut:
    """Pasos 4 a 6: alta del producto, todavía sin variantes."""
    try:
        return service.crear_producto(db, datos)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.get(
    "/productos/{producto_id}",
    response_model=ProductoOut,
    summary="CU-10 Detalle de un producto con sus variantes",
)
def obtener_producto(producto_id: int, db: DbSession) -> ProductoOut:
    try:
        return service.obtener_producto(db, producto_id)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.patch(
    "/productos/{producto_id}",
    response_model=ProductoOut,
    summary="CU-10 Editar producto (3a)",
)
def editar_producto(
    producto_id: int, datos: ProductoEditarIn, db: DbSession
) -> ProductoOut:
    try:
        return service.editar_producto(db, producto_id, datos)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.patch(
    "/productos/{producto_id}/estado",
    response_model=ProductoOut,
    summary="CU-10 Activar o desactivar un producto (3b)",
)
def cambiar_estado_producto(
    producto_id: int, datos: CambioEstadoIn, db: DbSession
) -> ProductoOut:
    """Desactivar arrastra las variantes: ver el servicio."""
    try:
        return service.cambiar_estado_producto(db, producto_id, datos)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.delete(
    "/productos/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-10 Eliminar producto",
)
def eliminar_producto(producto_id: int, db: DbSession) -> Response:
    """Excepción E3 si ya tiene existencias o reservas."""
    try:
        service.eliminar_producto(db, producto_id)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Variantes (paso 7 y sus alternativos) -------------------------------

@router.post(
    "/productos/{producto_id}/variantes/generar",
    response_model=GenerarVariantesOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-10 Generar variantes talla × color",
)
def generar_variantes(
    producto_id: int, datos: GenerarVariantesIn, db: DbSession
) -> GenerarVariantesOut:
    """Paso 7: la generación masiva.

    Devuelve cuántas creó y cuántas omitió por existir ya, para que la interfaz
    lo pueda decir en vez de dejar al Administrador comparando la tabla.
    """
    try:
        return service.generar_variantes(db, producto_id, datos)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.post(
    "/productos/{producto_id}/variantes",
    response_model=VarianteOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-10 Agregar una variante suelta (7a)",
)
def crear_variante(
    producto_id: int, datos: VarianteCrearIn, db: DbSession
) -> VarianteOut:
    try:
        return service.crear_variante(db, producto_id, datos)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.patch(
    "/variantes/{variante_id}",
    response_model=VarianteOut,
    summary="CU-10 Editar precio o estado de una variante (7b, 7c)",
)
def editar_variante(
    variante_id: int, datos: VarianteEditarIn, db: DbSession
) -> VarianteOut:
    try:
        return service.editar_variante(db, variante_id, datos)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error


@router.delete(
    "/variantes/{variante_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-10 Eliminar una variante",
)
def eliminar_variante(variante_id: int, db: DbSession) -> Response:
    try:
        service.eliminar_variante(db, variante_id)
    except service.ErrorDeProductos as error:
        raise _traducir(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
