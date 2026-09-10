"""
P3 - Catalogo / CU-11  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2
Caso de uso: CU-11 Gestionar imagenes de producto

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.

Este router NO se monta en main.py: lo incluye el router de catalogo, que ya
estaba montado desde el Ciclo 1. main.py es uno de los cinco archivos
compartidos del ciclo (seccion 5 del acuerdo), y sus lineas 29-31 y 107-109 son
justamente las que descomenta Mateo; no agregar nada ahi vuelve el conflicto
imposible en vez de improbable.
"""
from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.core.dependencies import DbSession
from app.modules.catalogo import imagenes_service as service
from app.modules.catalogo.imagenes_schemas import (
    ImagenEditarIn,
    ImagenOut,
    MarcarPrincipalIn,
    MarcarTransparenteIn,
    ReordenarIn,
)

# Sin `dependencies` propias: este router se incluye dentro del de catalogo, que
# ya exige rol Administrador a nivel de router. Declararlo otra vez aqui haria
# que la exigencia se evaluara dos veces por peticion.
router = APIRouter(tags=["Catalogo · Imágenes"])


def _traducir(error: service.ErrorDeImagenes) -> HTTPException:
    """Convierte los errores de negocio de CU-11 en respuestas HTTP."""
    if isinstance(error, service.ProductoInexistente):
        return HTTPException(404, "El producto indicado no existe.")
    if isinstance(error, service.ImagenInexistente):
        return HTTPException(404, "La imagen indicada no existe.")
    if isinstance(error, service.VarianteAjena):
        return HTTPException(
            422, "Esa variante pertenece a otro producto."
        )
    if isinstance(error, service.ArchivoInvalido):
        # Excepciones E1 y E2. El motivo lo redacta el servicio porque depende
        # de que fallo: formato, tamaño o dimensiones.
        return HTTPException(422, error.motivo)
    if isinstance(error, service.TransparenteSinVariante):
        return HTTPException(
            422,
            "La imagen del vestidor virtual pertenece a una variante concreta: "
            "asóciela a una talla y color antes de marcarla.",
        )
    if isinstance(error, service.SinTransparencia):
        return HTTPException(
            422,
            "Esa imagen no tiene fondo transparente. El vestidor virtual "
            "superpondría el fondo sobre el cuerpo; use un PNG recortado.",
        )
    if isinstance(error, service.ImagenAjena):
        return HTTPException(422, "Alguna de las imágenes no es de este producto.")
    return HTTPException(400, "No se pudo completar la operación.")


@router.get(
    "/productos/{producto_id}/imagenes",
    response_model=list[ImagenOut],
    summary="CU-11 Galería de un producto",
)
def listar(producto_id: int, db: DbSession) -> list[ImagenOut]:
    """Paso 2: las imágenes del producto, con la principal primero."""
    try:
        return service.listar(db, producto_id)
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error


@router.post(
    "/productos/{producto_id}/imagenes",
    response_model=ImagenOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-11 Subir una imagen",
)
async def subir(
    producto_id: int,
    db: DbSession,
    archivo: UploadFile = File(..., description="PNG, JPEG o WEBP"),
    variante_id: int | None = None,
) -> ImagenOut:
    """Pasos 3 y 4.

    El archivo se lee entero en memoria antes de tocar el disco: el tope de 5 MB
    del servicio lo hace seguro, y permite validar que sea realmente una imagen
    **antes** de escribir nada en el volumen.
    """
    contenido = await archivo.read()
    try:
        return service.subir(
            db, producto_id, contenido=contenido, variante_id=variante_id
        )
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error


@router.patch(
    "/imagenes/{imagen_id}",
    response_model=ImagenOut,
    summary="CU-11 Asociar a una variante o cambiar el orden (3a, 3d)",
)
def editar(imagen_id: int, datos: ImagenEditarIn, db: DbSession) -> ImagenOut:
    try:
        return service.editar(db, imagen_id, datos)
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error


@router.patch(
    "/imagenes/{imagen_id}/principal",
    response_model=list[ImagenOut],
    summary="CU-11 Marcar la imagen principal (3b)",
)
def marcar_principal(
    imagen_id: int, datos: MarcarPrincipalIn, db: DbSession
) -> list[ImagenOut]:
    """Devuelve la galería entera: marcar una desmarca la anterior."""
    try:
        return service.marcar_principal(db, imagen_id, datos)
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error


@router.patch(
    "/imagenes/{imagen_id}/transparente",
    response_model=list[ImagenOut],
    summary="CU-11 Marcar el PNG del vestidor virtual (3c)",
)
def marcar_transparente(
    imagen_id: int, datos: MarcarTransparenteIn, db: DbSession
) -> list[ImagenOut]:
    """Verifica que el archivo tenga transparencia real antes de aceptarlo."""
    try:
        return service.marcar_transparente(db, imagen_id, datos)
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error


@router.put(
    "/productos/{producto_id}/imagenes/orden",
    response_model=list[ImagenOut],
    summary="CU-11 Reordenar la galería (3d)",
)
def reordenar(producto_id: int, datos: ReordenarIn, db: DbSession) -> list[ImagenOut]:
    """El orden completo de una sola vez, no de a un movimiento por petición."""
    try:
        return service.reordenar(db, producto_id, datos)
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error


@router.delete(
    "/imagenes/{imagen_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-11 Eliminar una imagen (3e)",
)
def eliminar(imagen_id: int, db: DbSession) -> Response:
    try:
        service.eliminar(db, imagen_id)
    except service.ErrorDeImagenes as error:
        raise _traducir(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
