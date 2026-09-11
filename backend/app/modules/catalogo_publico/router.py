"""
P5 - Catalogo Publico / CU-17 y CU-18  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2
Casos de uso:
  CU-17 Consultar catalogo
  CU-18 Consultar ficha de producto
  CU-19 Consultar disponibilidad por sucursal

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Path, Query

from app.core.dependencies import DbSession
from app.modules.catalogo_publico import service
from app.modules.catalogo_publico.schemas import (
    DisponibilidadOut,
    FichaProductoOut,
    FiltrosOut,
    PaginaVitrina,
)

# Este router NO lleva `dependencies=[Depends(requiere_roles(...))]`, y es la
# diferencia de fondo con el router de CU-10.
#
# La vitrina es PUBLICA: el RF07 dice que el cliente consulta el catalogo desde
# web y movil, y en la app movil la pantalla de catalogo se abre antes de que
# exista un token --- el flujo principal de CU-17 no tiene precondicion de
# sesion. Exigir rol aqui obligaria a registrarse para mirar una prenda, que es
# exactamente lo contrario de lo que el caso de uso pide.
#
# Lo que se ofrece esta acotado por la regla del servicio --- solo producto activo
# con variantes activas --- y los esquemas de este paquete no exponen proveedor,
# precio base ni estado: ver la cabecera de schemas.py.
router = APIRouter(prefix="/tienda", tags=["Catálogo público"])


def _traducir(error: service.ErrorDeVitrina) -> HTTPException:
    """Convierte los errores de negocio de la vitrina en respuestas HTTP."""
    if isinstance(error, service.ProductoNoDisponible):
        # Excepcion E1 de CU-18. Deliberadamente 404 y no 403: ver la docstring
        # de ProductoNoDisponible.
        return HTTPException(404, "La prenda que busca ya no está disponible.")
    if isinstance(error, service.VarianteNoDisponible):
        # Excepcion E1 de CU-19, con el mismo criterio.
        return HTTPException(
            404, "Esa combinación de talla y color ya no está disponible."
        )
    return HTTPException(400, "No se pudo completar la consulta.")


@router.get(
    "/filtros",
    response_model=FiltrosOut,
    summary="CU-17 Opciones de filtrado de la vitrina",
)
def obtener_filtros(db: DbSession) -> FiltrosOut:
    """Paso 2: categorías, tallas, colores, temporadas, colecciones y precios.

    Va antes que `/productos/{producto_id}` en el archivo a propósito. FastAPI
    resuelve las rutas en el orden en que se declaran, y si el detalle se
    declarara primero, `/tienda/filtros` entraría por él y fallaría con un 422
    al intentar leer «filtros» como un entero.
    """
    return service.obtener_filtros(db)


@router.get(
    "/productos",
    response_model=PaginaVitrina,
    summary="CU-17 Consultar catálogo",
)
def listar_productos(
    db: DbSession,
    busqueda: Annotated[
        str | None, Query(max_length=120, description="Nombre, descripción o código")
    ] = None,
    categoria_id: Annotated[
        int | None, Query(description="Incluye las subcategorías que cuelgan de ella")
    ] = None,
    talla_id: Annotated[int | None, Query()] = None,
    color_id: Annotated[int | None, Query()] = None,
    temporada_id: Annotated[int | None, Query()] = None,
    coleccion_id: Annotated[int | None, Query()] = None,
    precio_min: Annotated[Decimal | None, Query(ge=0)] = None,
    precio_max: Annotated[Decimal | None, Query(ge=0)] = None,
    orden: Annotated[
        Literal["novedades", "precio_asc", "precio_desc", "nombre"], Query()
    ] = "novedades",
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=48)] = 12,
) -> PaginaVitrina:
    """Paso 2: la vitrina, con búsqueda, filtros, orden y paginación (RF07).

    El tope de 48 por página es más bajo que el de 100 del router de
    Administrador, y a propósito: cada tarjeta arrastra su rango de precios, su
    imagen y sus colores, y esta consulta la sirve una app móvil sobre datos
    móviles. Sin tope, `tamano=100000` traería el catálogo entero con todo eso
    dentro.

    `orden` se declara como `Literal` para que un valor inventado devuelva un
    422 que nombra las opciones válidas, en vez de un `KeyError` del servicio.

    **Falta el filtro por sucursal** que el caso de uso también enuncia: depende
    de `existencia` y llega con la costura C1, junto con CU-19.
    """
    return service.listar_productos(
        db,
        pagina=pagina,
        tamano=tamano,
        orden=orden,
        busqueda=busqueda,
        categoria_id=categoria_id,
        talla_id=talla_id,
        color_id=color_id,
        temporada_id=temporada_id,
        coleccion_id=coleccion_id,
        precio_min=precio_min,
        precio_max=precio_max,
    )


@router.get(
    "/productos/{producto_id}",
    response_model=FichaProductoOut,
    summary="CU-18 Consultar ficha de producto",
    responses={404: {"description": "La prenda no existe o ya no se ofrece."}},
)
def obtener_ficha(
    db: DbSession,
    producto_id: Annotated[int, Path(ge=1)],
) -> FichaProductoOut:
    """Paso 3: la ficha con su galería, sus variantes, sus tallas y sus colores.

    Cada variante viaja con `imagen_vestidor_url`, el PNG de fondo transparente
    que necesita el vestidor virtual. Es la costura **C5**: la pantalla de
    realidad aumentada recibe el activo al navegar y no vuelve a consultar la
    API ni conoce la tabla de imágenes.
    """
    try:
        return service.obtener_ficha(db, producto_id)
    except service.ErrorDeVitrina as error:
        raise _traducir(error) from error


@router.get(
    "/variantes/{variante_id}/disponibilidad",
    response_model=DisponibilidadOut,
    summary="CU-19 Consultar disponibilidad por sucursal",
    responses={404: {"description": "La variante no existe o ya no se ofrece."}},
)
def disponibilidad_de_variante(
    db: DbSession,
    variante_id: Annotated[int, Path(ge=1)],
) -> DisponibilidadOut:
    """Paso 2: en qué sucursales hay stock de la talla y el color elegidos (RF08).

    Cuelga de la **variante** y no del producto porque la existencia es por
    variante: preguntar «dónde hay esta blusa» no tiene respuesta útil si no se
    dice en qué talla y en qué color.

    Es público, como el resto de P5. Lo que se informa es lo **disponible**, no
    lo reservado: al cliente le sirve saber cuánto puede llevarse, y publicar lo
    apartado dejaría deducir el movimiento comercial de cada tienda.
    """
    try:
        return service.disponibilidad_de_variante(db, variante_id)
    except service.ErrorDeVitrina as error:
        raise _traducir(error) from error
