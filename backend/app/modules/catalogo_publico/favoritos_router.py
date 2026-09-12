"""
P5 - Catalogo Publico / CU-20  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-20 Gestionar favoritos

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.

**Este es el unico router de P5 que exige sesion**, y por eso esta en un archivo
aparte. CU-17, CU-18 y CU-19 son publicos --- el catalogo se mira sin cuenta ---
pero un favorito es de alguien: sin sesion no hay de quien.

Se incluye dentro del router de la vitrina en vez de montarse en `main.py`, con
el mismo patron que CU-11 usa dentro del router de catalogo: `main.py` es el
archivo que todos los casos de uso tocan, y no agregar nada ahi vuelve el
conflicto imposible en vez de improbable.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.catalogo_publico import service
from app.modules.catalogo_publico.schemas import PaginaFavoritos

router = APIRouter(
    prefix="/favoritos",
    tags=["Catálogo público · Favoritos"],
    # El rol se declara UNA vez a nivel de router y no endpoint por endpoint:
    # olvidarlo en uno solo abriria un agujero sin que nada avise. Es el criterio
    # de CU-03, CU-05, CU-08 y CU-10.
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)


@router.get(
    "",
    response_model=PaginaFavoritos,
    summary="CU-20 Mis prendas favoritas",
)
def listar_favoritos(
    db: DbSession,
    usuario: Usuario,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=48)] = 12,
) -> PaginaFavoritos:
    """Paso 2: la lista del cliente, lo último marcado primero (RF31).

    Las tarjetas son las mismas que las de la vitrina. Solo se listan las
    prendas que **siguen siendo ofrecibles**: la fila del favorito no se borra
    cuando el producto se desactiva —es historial de preferencia y lo usa el
    recomendador del CU-33— pero mostrarla sería ofrecer algo que no se puede
    comprar.
    """
    return service.listar_favoritos(db, usuario.id, pagina=pagina, tamano=tamano)


@router.get(
    "/ids",
    response_model=list[int],
    summary="CU-20 Identificadores de mis favoritos",
)
def ids_de_favoritos(db: DbSession, usuario: Usuario) -> list[int]:
    """Los identificadores marcados, para pintar los corazones de la vitrina.

    Existe como endpoint propio porque **la vitrina es pública**: agregarle un
    campo `es_favorito` a la tarjeta obligaría a que CU-17 supiera quién está
    mirando, y hoy no lo sabe ni tiene por qué. La pantalla pide esta lista una
    vez al entrar, si hay sesión de Cliente, y marca las tarjetas del lado del
    navegador.

    Va declarado **antes** que `/{producto_id}`: FastAPI resuelve las rutas en
    orden y, al revés, «ids» entraría por el detalle y fallaría al leerse como
    un entero.
    """
    return service.ids_de_favoritos(db, usuario.id)


@router.put(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-20 Marcar una prenda como favorita",
    responses={404: {"description": "La prenda no existe o ya no se ofrece."}},
)
def marcar_favorito(
    db: DbSession,
    usuario: Usuario,
    producto_id: Annotated[int, Path(ge=1)],
) -> Response:
    """Paso 3: marca la prenda.

    Es `PUT` y no `POST` porque **es idempotente**: marcar dos veces deja lo
    mismo y responde igual. El corazón de una interfaz se puede tocar dos veces
    sin querer, y fallar por eso convertiría un doble toque en un error.
    """
    try:
        service.marcar_favorito(db, usuario.id, producto_id)
    except service.ErrorDeVitrina as error:
        raise _traducir(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{producto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-20 Quitar una prenda de mis favoritas",
)
def desmarcar_favorito(
    db: DbSession,
    usuario: Usuario,
    producto_id: Annotated[int, Path(ge=1)],
) -> Response:
    """Paso 4: la quita de la lista.

    También es idempotente, y **a propósito no exige que la prenda siga siendo
    ofrecible**: si se desactivó después de marcarla, el cliente tiene que poder
    sacarla igual. Exigirlo dejaría favoritos imposibles de borrar.
    """
    try:
        service.desmarcar_favorito(db, usuario.id, producto_id)
    except service.ErrorDeVitrina as error:
        raise _traducir(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _traducir(error: service.ErrorDeVitrina) -> HTTPException:
    if isinstance(error, service.ProductoNoDisponible):
        return HTTPException(404, "La prenda que busca ya no está disponible.")
    return HTTPException(400, "No se pudo completar la operación.")
