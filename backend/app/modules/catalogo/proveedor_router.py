"""
P3 - Catalogo / CU-38  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-38 Registrar productos del proveedor  (RF37)

UN ROUTER APARTE, NO ENDPOINTS DENTRO DEL DE CU-10
--------------------------------------------------
El router de CU-10 declara `requiere_roles("ADMINISTRADOR")` una sola vez, a
nivel de router, y eso es lo que lo hace seguro: nadie puede olvidarse la
guarda en un endpoint. Meter aqui adentro rutas que exigen otro rol obligaria a
bajar esa dependencia al endpoint, y entonces la del Administrador dependeria
de que nadie se la olvide nunca mas. Dos roles, dos routers --- el mismo patron
que ya usa CU-07 con `router` y `router_proveedor`.

El prefijo es `/catalogo/mis-productos`, con «mis» y sin identificador de
proveedor en ninguna ruta: el ambito sale del token. Una ruta con la forma
`/catalogo/proveedores/{id}/productos` invitaria a cambiar el numero.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.catalogo import proveedor_service as service
from app.modules.catalogo.proveedor_schemas import (
    ListasDelFormularioOut,
    MiProductoCrearIn,
    MiProductoEditarIn,
)
from app.modules.catalogo.schemas import (
    CambioEstadoIn,
    GenerarVariantesIn,
    GenerarVariantesOut,
    PaginaProductos,
    ProductoOut,
)
from app.modules.catalogo.service import ErrorDeProductos

router = APIRouter(
    prefix="/catalogo/mis-productos",
    tags=["Catálogo · Proveedor"],
    dependencies=[Depends(requiere_roles("PROVEEDOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no tiene rol Proveedor."},
    },
)

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.


def _traducir_ambito(error: service.ErrorDelProveedor) -> HTTPException:
    """Los errores propios de CU-38: quien es el proveedor y que es suyo."""
    if isinstance(error, service.ProductoAjeno):
        # 404 y NO 403. Un 403 confirmaria que ese identificador corresponde a
        # un producto real de otro proveedor, y recorrer los numeros seria un
        # censo del catalogo de la competencia. Por eso «no es tuyo» y «no
        # existe» se responden igual.
        return HTTPException(404, "El producto indicado no existe.")
    if isinstance(error, service.SinFichaDeProveedor):
        # No es culpa de quien opera: le dieron el rol sin vincularle la ficha.
        return HTTPException(
            404,
            "Su usuario no tiene una ficha de proveedor asociada. "
            "Contacte al administrador.",
        )
    if isinstance(error, service.ProveedorDesactivado):
        return HTTPException(
            403,
            "Su cuenta de proveedor está desactivada. Contacte al administrador.",
        )
    return HTTPException(400, "No se pudo completar la operación.")


def _traducir_catalogo(error: ErrorDeProductos) -> HTTPException:
    """Los errores de CU-10, que es quien valida de verdad.

    Se traducen aqui otra vez, y no se reusa el `_traducir` de CU-10, porque
    aquel nombra situaciones que este caso de uso no tiene --- borrar un
    producto con dependencias, por ejemplo --- y porque el texto se le muestra
    al Proveedor, que no es el Administrador y no conoce el catalogo entero.
    """
    from app.modules.catalogo import service as catalogo

    if isinstance(error, catalogo.CodigoDuplicado):
        # Excepcion E1. El UNIQUE es de toda la tabla, asi que el codigo puede
        # estar tomado por un producto que este proveedor no ve. El mensaje no
        # dice de quien es: eso volveria a abrir el censo que el 404 cierra.
        return HTTPException(409, "Ya existe un producto con ese código.")
    if isinstance(error, catalogo.ProductoInexistente):
        return HTTPException(404, "El producto indicado no existe.")
    if isinstance(error, catalogo.MaestroInexistente):
        return HTTPException(422, "La categoría, temporada o colección no existe.")
    if isinstance(error, catalogo.ColeccionAjenaALaTemporada):
        # Excepcion E2.
        return HTTPException(
            422, "La colección elegida no pertenece a la temporada indicada."
        )
    if isinstance(error, catalogo.SkuDemasiadoLargo):
        return HTTPException(
            422,
            "El código del producto es demasiado largo para generar los SKU. "
            "Use uno más corto.",
        )
    return HTTPException(400, "No se pudo completar la operación.")


# --- Listas para el formulario -------------------------------------------

@router.get(
    "/listas",
    response_model=ListasDelFormularioOut,
    summary="CU-38 Maestros para el formulario de alta",
)
def listas_del_formulario(db: DbSession) -> ListasDelFormularioOut:
    """Categorías, tallas, colores, temporadas y colecciones activas.

    Existe porque los routers de CU-08 y de temporadas exigen rol
    Administrador a nivel de router y, además de leer, permiten crear y borrar:
    aflojar esa guarda para llenar un selector le daría al Proveedor permiso
    para crear categorías. Esta es su vista, de sólo lectura.
    """
    return service.listas_del_formulario(db)


# --- Flujo principal -----------------------------------------------------

@router.get("", response_model=PaginaProductos, summary="CU-38 Mis productos")
def listar_mis_productos(
    usuario: Usuario,
    db: DbSession,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
    busqueda: Annotated[str | None, Query(max_length=120)] = None,
    categoria_id: Annotated[int | None, Query()] = None,
    temporada_id: Annotated[int | None, Query()] = None,
    coleccion_id: Annotated[int | None, Query()] = None,
    activo: Annotated[bool | None, Query()] = None,
) -> PaginaProductos:
    """Paso 2: lo que abastece este proveedor, y nada más.

    NO acepta un parámetro `proveedor_id`. El ámbito sale del token: si fuera
    un filtro más de la cadena de consulta, bastaría con cambiarlo para leer el
    catálogo de otro.
    """
    try:
        return service.listar_mis_productos(
            db,
            usuario.id,
            pagina=pagina,
            tamano=tamano,
            busqueda=busqueda,
            categoria_id=categoria_id,
            temporada_id=temporada_id,
            coleccion_id=coleccion_id,
            activo=activo,
        )
    except service.ErrorDelProveedor as error:
        raise _traducir_ambito(error)


@router.post(
    "",
    response_model=ProductoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-38 Registrar un producto que abastezco",
    responses={
        409: {"description": "Ya existe un producto con ese código (E1)."},
        422: {"description": "Maestro inexistente, o colección ajena a la temporada (E2)."},
    },
)
def registrar_mi_producto(
    datos: MiProductoCrearIn, usuario: Usuario, db: DbSession
) -> ProductoOut:
    """Registra una prenda a nombre de este proveedor.

    **Nace inactiva.** Registrar no es publicar: el RF37 le da al Proveedor la
    capacidad de informar lo que abastece, no la de poner prendas en la vitrina
    que ve el cliente. Activarla es del Administrador, por CU-10.

    El cuerpo no lleva `proveedor_id` ni `activo`: no están en el esquema.
    """
    try:
        return service.registrar_mi_producto(db, usuario.id, datos)
    except service.ErrorDelProveedor as error:
        raise _traducir_ambito(error)
    except ErrorDeProductos as error:
        raise _traducir_catalogo(error)


@router.get(
    "/{producto_id}",
    response_model=ProductoOut,
    summary="CU-38 Detalle de un producto propio",
    responses={404: {"description": "No existe, o no es de este proveedor."}},
)
def obtener_mi_producto(
    producto_id: int, usuario: Usuario, db: DbSession
) -> ProductoOut:
    """El producto con sus variantes, si es de quien pregunta."""
    try:
        return service.obtener_mi_producto(db, usuario.id, producto_id)
    except service.ErrorDelProveedor as error:
        raise _traducir_ambito(error)
    except ErrorDeProductos as error:
        raise _traducir_catalogo(error)


@router.patch(
    "/{producto_id}",
    response_model=ProductoOut,
    summary="CU-38 Corregir un producto propio (3a)",
    responses={404: {"description": "No existe, o no es de este proveedor."}},
)
def editar_mi_producto(
    producto_id: int,
    datos: MiProductoEditarIn,
    usuario: Usuario,
    db: DbSession,
) -> ProductoOut:
    """Actualiza sólo los campos enviados.

    Mandar `temporada_id` o `coleccion_id` en `null` saca el producto de esa
    temporada o colección, que es distinto de no mandarlas.
    """
    try:
        return service.editar_mi_producto(db, usuario.id, producto_id, datos)
    except service.ErrorDelProveedor as error:
        raise _traducir_ambito(error)
    except ErrorDeProductos as error:
        raise _traducir_catalogo(error)


@router.patch(
    "/{producto_id}/estado",
    response_model=ProductoOut,
    summary="CU-38 Retirar un producto propio (3b)",
    responses={
        403: {"description": "Publicar es del Administrador: sólo se puede retirar."},
        404: {"description": "No existe, o no es de este proveedor."},
    },
)
def retirar_mi_producto(
    producto_id: int,
    datos: CambioEstadoIn,
    usuario: Usuario,
    db: DbSession,
) -> ProductoOut:
    """Retira una prenda que este proveedor ya no abastece.

    **Sólo acepta `activo: false`.** La asimetría es la misma regla por la que
    el alta nace inactiva: publicar en la vitrina es del Administrador. Se
    responde 403 y no 422 porque el dato está bien escrito — lo que falta es el
    permiso.

    Retirar no borra: el producto sigue en el inventario y en las ventas
    históricas, y sus variantes quedan desactivadas con él.
    """
    if datos.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Publicar un producto es del administrador. Desde aquí sólo "
                "puede retirar los que ya no abastece."
            ),
        )
    try:
        return service.cambiar_estado_de_mi_producto(db, usuario.id, producto_id, False)
    except service.ErrorDelProveedor as error:
        raise _traducir_ambito(error)
    except ErrorDeProductos as error:
        raise _traducir_catalogo(error)


@router.post(
    "/{producto_id}/variantes",
    response_model=GenerarVariantesOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-38 Declarar en qué tallas y colores lo abastezco",
    responses={
        404: {"description": "No existe, o no es de este proveedor."},
        422: {"description": "Talla o color inexistente, o el código no deja armar el SKU."},
    },
)
def generar_variantes(
    producto_id: int,
    datos: GenerarVariantesIn,
    usuario: Usuario,
    db: DbSession,
) -> GenerarVariantesOut:
    """Genera las combinaciones talla × color de una prenda propia.

    Es la mitad que vuelve útil al registro: sin variantes no hay SKU, y sin
    SKU no hay existencia, ni reserva, ni venta (decisión D1). Las
    combinaciones que ya existen se omiten en vez de fallar, así que repetir la
    llamada es seguro.
    """
    try:
        return service.generar_variantes_de_mi_producto(db, usuario.id, producto_id, datos)
    except service.ErrorDelProveedor as error:
        raise _traducir_ambito(error)
    except ErrorDeProductos as error:
        raise _traducir_catalogo(error)
