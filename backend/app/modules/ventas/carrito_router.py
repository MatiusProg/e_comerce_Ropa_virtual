"""
P7 - Ventas y Punto de Venta / CU-26  |  capa: router (HTTP y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-26 Gestionar carrito de compras  (RF14)

EL PREFIJO ES /tienda/carrito Y EL PAQUETE ES P7
------------------------------------------------
La ruta vive bajo `/tienda` porque es donde el cliente la usa --- viene de la
vitrina y va al pago --- pero el codigo es de P7, no de P5. Por eso se monta en
`main.py` en vez de colgarse del router de la vitrina, como si hace CU-20: los
favoritos SON de P5, y colgar un router de P7 dentro de uno de P5 crearia una
dependencia al reves de la que declara la arquitectura.

NINGUNA RUTA LLEVA IDENTIFICADOR DE CARRITO
-------------------------------------------
El carrito se resuelve desde el token, igual que la ficha del Proveedor en
CU-38 y el perfil en CU-04. Una ruta con la forma `/carritos/{id}` invitaria a
cambiar el numero, y no hay ningun motivo para que un cliente nombre el carrito
de otro.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.seguridad import service as seguridad
from app.modules.ventas import carrito_service as service
from app.modules.ventas.carrito_schemas import (
    AgregarAlCarritoIn,
    CambiarCantidadIn,
    CANTIDAD_MAXIMA,
    CarritoOut,
)

router = APIRouter(
    prefix="/tienda/carrito",
    tags=["Ventas · Carrito"],
    # El rol se declara UNA vez a nivel de router y no endpoint por endpoint:
    # olvidarlo en uno solo abriria un agujero sin que nada avise.
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)

# Regla: el router valida la entrada, resuelve la autorizacion y delega en el
# servicio. Ninguna regla de negocio vive aqui.


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, service.PrendaNoOfrecible):
        # Excepcion E1. Un solo mensaje para «no existe» y «ya no se ofrece»,
        # con el mismo criterio que CU-18: la vitrina no confirma que algo
        # existe si no se puede comprar.
        return HTTPException(404, "La prenda que busca ya no está disponible.")
    if isinstance(error, service.PrendaFueraDelCarrito):
        return HTTPException(404, "Esa prenda no está en su carrito.")
    if isinstance(error, service.CantidadFueraDeRango):
        # 409 y no 422: lo que mandó es un número válido. Lo que no se puede es
        # el resultado de sumarlo a lo que ya había.
        return HTTPException(
            409,
            f"No puede llevar más de {CANTIDAD_MAXIMA} unidades de la misma prenda.",
        )
    if isinstance(error, seguridad.PerfilInexistente):
        # La cuenta tiene rol Cliente pero no ficha de cliente. No deberia pasar
        # --- CU-01 crea las dos juntas --- pero si pasara, el carrito no tiene
        # de quien ser.
        return HTTPException(403, "Su cuenta no tiene una ficha de cliente asociada.")
    return HTTPException(400, "No se pudo completar la operación.")


@router.get("", response_model=CarritoOut, summary="CU-26 Mi carrito")
def ver_carrito(db: DbSession, usuario: Usuario) -> CarritoOut:
    """Paso 2: el carrito con sus precios y su disponibilidad al día.

    **Un carrito vacío no es un 404**: es un carrito con cero líneas. La
    pantalla tiene que poder pintarse antes de que el cliente agregue nada, sin
    tratar el caso normal como un error.

    Leer el carrito no lo crea en la base: la mayoría de quienes abren esta
    pantalla nunca agregan nada, y crear una fila por visita sería escribir por
    mirar.
    """
    try:
        return service.ver_carrito(db, usuario.id)
    except (service.ErrorDelCarrito, seguridad.PerfilInexistente) as error:
        raise _traducir(error) from error


@router.post(
    "/items",
    response_model=CarritoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-26 Agregar una prenda al carrito",
    responses={
        404: {"description": "La prenda no existe o ya no se ofrece (E1)."},
        409: {"description": "Superaría el tope de unidades por prenda."},
    },
)
def agregar(datos: AgregarAlCarritoIn, db: DbSession, usuario: Usuario) -> CarritoOut:
    """Paso 3: agrega una prenda. **Suma** a lo que ya hubiera de esa variante.

    Es lo que espera quien pulsa «Agregar» dos veces desde la ficha del
    producto: la segunda vez no reemplaza la primera. Para *fijar* una cantidad
    está `PATCH /items/{variante_id}`.

    Devuelve el carrito entero y no sólo la línea: la pantalla necesita el total
    y la burbuja del ícono, y pedirlos aparte serían dos viajes por cada
    «Agregar».

    **Se puede agregar algo agotado.** El carrito no aparta inventario —eso es
    una reserva, CU-22—, así que impedirlo sólo le quitaría al cliente la
    posibilidad de dejarlo anotado mientras la tienda repone. La línea viaja
    con `stock_total` para que la pantalla lo diga.
    """
    try:
        return service.agregar(db, usuario.id, datos)
    except (service.ErrorDelCarrito, seguridad.PerfilInexistente) as error:
        raise _traducir(error) from error


@router.patch(
    "/items/{variante_id}",
    response_model=CarritoOut,
    summary="CU-26 Cambiar la cantidad de una prenda (3a)",
    responses={404: {"description": "Esa prenda no está en el carrito."}},
)
def cambiar_cantidad(
    variante_id: Annotated[int, Path(ge=1)],
    datos: CambiarCantidadIn,
    db: DbSession,
    usuario: Usuario,
) -> CarritoOut:
    """**Fija** la cantidad de una línea; no la suma.

    Es la operación del selector de cantidad del carrito, y va por otro verbo
    que `POST /items` a propósito: un mismo endpoint que a veces suma y a veces
    fija sería imposible de usar sin mirar el código.

    Para dejar la cantidad en cero está `DELETE`: el esquema exige al menos 1,
    porque una línea con cero unidades no es una línea, es una línea borrada.
    """
    try:
        return service.cambiar_cantidad(db, usuario.id, variante_id, datos)
    except (service.ErrorDelCarrito, seguridad.PerfilInexistente) as error:
        raise _traducir(error) from error


@router.delete(
    "/items/{variante_id}",
    response_model=CarritoOut,
    summary="CU-26 Quitar una prenda del carrito (3b)",
    responses={404: {"description": "Esa prenda no está en el carrito."}},
)
def quitar(
    variante_id: Annotated[int, Path(ge=1)], db: DbSession, usuario: Usuario
) -> CarritoOut:
    """Saca una prenda del carrito.

    **No exige que la prenda siga ofreciéndose**: si se desactivó después de
    agregarla, el cliente tiene que poder sacarla igual. Exigirlo dejaría
    líneas imposibles de borrar — es la misma decisión que tomó CU-20 al
    desmarcar un favorito.

    A diferencia de aquél, esto **sí falla** si la prenda no está en el
    carrito. Un corazón se toca dos veces sin querer; este botón está junto a
    una línea concreta, y que no exista significa que la pantalla está vieja.
    Decirlo hace que se recargue.
    """
    try:
        return service.quitar(db, usuario.id, variante_id)
    except (service.ErrorDelCarrito, seguridad.PerfilInexistente) as error:
        raise _traducir(error) from error


@router.delete("", response_model=CarritoOut, summary="CU-26 Vaciar el carrito (3c)")
def vaciar(db: DbSession, usuario: Usuario) -> CarritoOut:
    """Deja el carrito sin líneas.

    **Es idempotente**, al revés que quitar una línea: pedir «que quede vacío»
    sobre algo ya vacío es una petición cumplida, no un error.
    """
    try:
        return service.vaciar(db, usuario.id)
    except (service.ErrorDelCarrito, seguridad.PerfilInexistente) as error:
        raise _traducir(error) from error
