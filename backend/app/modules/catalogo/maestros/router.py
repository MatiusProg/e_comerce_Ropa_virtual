"""
P3 - Catalogo / CU-08  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1
Caso de uso: CU-08 Gestionar categorias, tallas y colores

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, requiere_roles
from app.modules.catalogo.maestros import service
from app.modules.catalogo.maestros.schemas import (
    CambioEstadoIn,
    CategoriaCrearIn,
    CategoriaEditarIn,
    CategoriaOut,
    ColorCrearIn,
    ColorEditarIn,
    ColorOut,
    TallaCrearIn,
    TallaEditarIn,
    TallaOut,
)

# Todo el caso de uso exige rol Administrador, y la dependencia se declara UNA
# sola vez a nivel de router: endpoint por endpoint, olvidarla en uno solo
# abriria un agujero sin que nada avise. Es el criterio de CU-03, CU-05 y CU-06.
router = APIRouter(
    prefix="/catalogo",
    tags=["Catalogo · Maestros"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


def _traducir(error: service.ErrorDeMaestros) -> HTTPException:
    """Convierte los errores de negocio de CU-08 en respuestas HTTP."""
    if isinstance(error, service.CategoriaInexistente):
        return HTTPException(404, "La categoría indicada no existe.")
    if isinstance(error, service.TallaInexistente):
        return HTTPException(404, "La talla indicada no existe.")
    if isinstance(error, service.ColorInexistente):
        return HTTPException(404, "El color indicado no existe.")
    if isinstance(error, service.NombreDuplicado):
        # Excepcion E1. El caso de uso pide señalar el campo, así que la
        # interfaz usa este 409 sin cerrar el diálogo.
        return HTTPException(409, "Ya existe un elemento con ese nombre o código.")
    if isinstance(error, service.CicloEnLaJerarquia):
        # Excepcion E2.
        return HTTPException(
            422,
            "No se puede colgar una categoría de una de sus propias "
            "subcategorías: la rama quedaría fuera del árbol.",
        )
    if isinstance(error, service.TieneDependencias):
        # Excepcion E3: la interfaz usa este mensaje para ofrecer desactivar.
        return HTTPException(
            409,
            "El elemento tiene dependencias y no puede eliminarse. "
            "Puede desactivarlo en su lugar.",
        )
    return HTTPException(400, "No se pudo completar la operación.")


# --- Categorias (flujo principal) ----------------------------------------

@router.get(
    "/categorias",
    response_model=list[CategoriaOut],
    summary="CU-08 Árbol de categorías",
)
def listar_categorias(db: DbSession) -> list[CategoriaOut]:
    """Paso 2: las categorías en forma de árbol, con su orden y estado.

    La jerarquía se arma en el servidor y no en la interfaz, para que la web y
    la app móvil reciban las dos la misma estructura ya resuelta.
    """
    return service.listar_categorias(db)


@router.post(
    "/categorias",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-08 Registrar categoría",
    responses={409: {"description": "Nombre repetido entre hermanas (excepción E1)."}},
)
def crear_categoria(datos: CategoriaCrearIn, db: DbSession) -> CategoriaOut:
    """Pasos 4 a 7."""
    try:
        return service.crear_categoria(db, datos)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.patch(
    "/categorias/{categoria_id}",
    response_model=CategoriaOut,
    summary="CU-08 Editar categoría",
    responses={422: {"description": "El padre elegido formaría un ciclo (E2)."}},
)
def editar_categoria(
    categoria_id: int, datos: CategoriaEditarIn, db: DbSession
) -> CategoriaOut:
    """Flujo alternativo 3a, incluida la reubicación en el árbol."""
    try:
        return service.editar_categoria(db, categoria_id, datos)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.patch(
    "/categorias/{categoria_id}/estado",
    response_model=CategoriaOut,
    summary="CU-08 Activar o desactivar categoría",
)
def cambiar_estado_categoria(
    categoria_id: int, datos: CambioEstadoIn, db: DbSession
) -> CategoriaOut:
    """Flujo alternativo 3b. No cascadea a las subcategorías."""
    try:
        return service.cambiar_estado_categoria(db, categoria_id, datos.activo)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.delete(
    "/categorias/{categoria_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-08 Eliminar categoría",
    responses={409: {"description": "Tiene subcategorías o productos (excepción E3)."}},
)
def eliminar_categoria(categoria_id: int, db: DbSession) -> None:
    try:
        service.eliminar_categoria(db, categoria_id)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


# --- Tallas (flujo alternativo 1a) ---------------------------------------

@router.get("/tallas", response_model=list[TallaOut], summary="CU-08 Listar tallas")
def listar_tallas(
    db: DbSession,
    tipo_prenda: Annotated[str | None, Query(max_length=30)] = None,
    activa: Annotated[bool | None, Query()] = None,
) -> list[TallaOut]:
    """Tallas en el orden en que se muestran en la ficha de producto."""
    return service.listar_tallas(
        db, tipo_prenda=tipo_prenda.strip().upper() if tipo_prenda else None, activa=activa
    )


@router.get(
    "/tallas/tipos",
    response_model=list[str],
    summary="CU-08 Tipos de prenda ya usados",
)
def listar_tipos_de_prenda(db: DbSession) -> list[str]:
    """Para que el formulario los ofrezca en vez de que se reescriban.

    Sin esto, la misma familia termina partida en «SUPERIOR» y «PARTE
    SUPERIOR», y las tallas dejan de agruparse.
    """
    return service.listar_tipos_de_prenda(db)


@router.post(
    "/tallas",
    response_model=TallaOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-08 Registrar talla",
)
def crear_talla(datos: TallaCrearIn, db: DbSession) -> TallaOut:
    try:
        return service.crear_talla(db, datos)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.patch(
    "/tallas/{talla_id}", response_model=TallaOut, summary="CU-08 Editar talla"
)
def editar_talla(talla_id: int, datos: TallaEditarIn, db: DbSession) -> TallaOut:
    try:
        return service.editar_talla(db, talla_id, datos)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.patch(
    "/tallas/{talla_id}/estado",
    response_model=TallaOut,
    summary="CU-08 Activar o desactivar talla",
)
def cambiar_estado_talla(
    talla_id: int, datos: CambioEstadoIn, db: DbSession
) -> TallaOut:
    try:
        return service.cambiar_estado_talla(db, talla_id, datos.activo)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.delete(
    "/tallas/{talla_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-08 Eliminar talla",
)
def eliminar_talla(talla_id: int, db: DbSession) -> None:
    try:
        service.eliminar_talla(db, talla_id)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


# --- Colores (flujo alternativo 1b) --------------------------------------

@router.get("/colores", response_model=list[ColorOut], summary="CU-08 Listar colores")
def listar_colores(
    db: DbSession, activo: Annotated[bool | None, Query()] = None
) -> list[ColorOut]:
    return service.listar_colores(db, activo=activo)


@router.post(
    "/colores",
    response_model=ColorOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-08 Registrar color",
)
def crear_color(datos: ColorCrearIn, db: DbSession) -> ColorOut:
    try:
        return service.crear_color(db, datos)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.patch(
    "/colores/{color_id}", response_model=ColorOut, summary="CU-08 Editar color"
)
def editar_color(color_id: int, datos: ColorEditarIn, db: DbSession) -> ColorOut:
    try:
        return service.editar_color(db, color_id, datos)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.patch(
    "/colores/{color_id}/estado",
    response_model=ColorOut,
    summary="CU-08 Activar o desactivar color",
)
def cambiar_estado_color(
    color_id: int, datos: CambioEstadoIn, db: DbSession
) -> ColorOut:
    try:
        return service.cambiar_estado_color(db, color_id, datos.activo)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)


@router.delete(
    "/colores/{color_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-08 Eliminar color",
)
def eliminar_color(color_id: int, db: DbSession) -> None:
    try:
        service.eliminar_color(db, color_id)
    except service.ErrorDeMaestros as error:
        raise _traducir(error)
