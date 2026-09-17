"""
P7 - Ventas y Punto de Venta  |  capa: router (HTTP y autorizacion)

Ciclo de desarrollo: 3
Caso de uso: CU-27 Realizar pedido y pagar en linea  (RF15, RF16, RF19)

EL PREFIJO ES /tienda/pedidos, POR LO MISMO QUE EL CARRITO
-----------------------------------------------------------
La ruta vive bajo `/tienda` porque es donde el cliente la usa, pero el codigo
es de P7. Se monta en `main.py` y no cuelga del router de la vitrina, con el
mismo criterio que dejo escrito CU-26.

NINGUNA RUTA LLEVA IDENTIFICADOR NUMERICO DE VENTA
---------------------------------------------------
Se direcciona por `codigo` --- `VB-20260917-A3F2` ---, que es el que el cliente
ve y puede leer por telefono. Y toda consulta va acotada al cliente del token,
asi que un codigo ajeno responde 404 igual que uno inexistente: probar codigos
no dice si existen.

LA BARRIDA DE VENCIDOS VA APARTE
---------------------------------
`/pedidos/expirar-vencidos` no es del cliente sino de la operacion, asi que
esta en otro router con otro rol. Dejarla en este, aunque fuera con su propia
guarda, la pondria detras de `requiere_roles("CLIENTE")`.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.inventario.service import StockInsuficiente
from app.modules.pagos import service as pagos
from app.modules.seguridad import service as seguridad
from app.modules.ventas import service
from app.modules.ventas.schemas import (
    CrearPedidoIn,
    CrearPedidoOut,
    ExpiracionDePedidosOut,
    OpcionesDePedidoOut,
    PedidoOut,
)

router = APIRouter(
    prefix="/tienda/pedidos",
    tags=["Ventas · Pedidos"],
    # El rol se declara UNA vez a nivel de router, igual que en CU-26:
    # olvidarlo en un endpoint abriria un agujero sin que nada avise.
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)

#: Router de operacion. Mismo patron que la expiracion de reservas de CU-25.
router_operacion = APIRouter(prefix="/pedidos", tags=["Ventas · Pedidos"])

Codigo = Annotated[str, Path(description="Código del pedido, p. ej. VB-20260917-A3F2.")]


def _traducir(error: Exception) -> HTTPException:
    if isinstance(error, service.CarritoVacio):
        return HTTPException(409, "Su carrito está vacío.")
    if isinstance(error, service.CarritoConPrendasCaidas):
        return HTTPException(
            409,
            "Hay prendas en su carrito que ya no se ofrecen. Quítelas para continuar.",
        )
    if isinstance(error, service.YaTienePedidoPendiente):
        # 409 y no 400: la petición es válida, lo que no se puede es el estado
        # en que está el cliente. El código va en el mensaje para que la
        # pantalla pueda ofrecer ir a pagarlo o cancelarlo.
        return HTTPException(
            409,
            f"Ya tiene el pedido {error.codigo} esperando pago. "
            "Termínelo o cancélelo antes de hacer otro.",
        )
    if isinstance(error, service.SucursalNoAbastece):
        return HTTPException(
            409,
            "Esa sucursal no tiene todas las prendas de su pedido: "
            + ", ".join(error.faltantes),
        )
    if isinstance(error, service.NingunaSucursalAbastece):
        return HTTPException(
            409,
            "Ninguna de nuestras sucursales tiene todas las prendas de su pedido. "
            "Puede dividirlo en dos compras.",
        )
    if isinstance(error, service.DestinoInvalido):
        return HTTPException(404, "El destino que eligió ya no está disponible.")
    if isinstance(error, service.PedidoInexistente):
        return HTTPException(404, "No encontramos ese pedido.")
    if isinstance(error, service.PedidoNoCancelable):
        return HTTPException(
            409,
            "Ese pedido ya no se puede cancelar porque está "
            f"{error.estado.lower().replace('_', ' ')}.",
        )
    if isinstance(error, StockInsuficiente):
        # Se llegó a apartar y no alcanzó: alguien se llevó la última unidad
        # entre que el cliente miró y confirmó. No es un 500 ni un 422.
        return HTTPException(
            409,
            "Alguien se llevó la última unidad de una de sus prendas mientras "
            "usted confirmaba. Revise su carrito.",
        )
    if isinstance(error, pagos.PasarelaNoDisponible):
        # 502 y no 500: no es un defecto nuestro sino un tercero caído, y el
        # cliente puede reintentar. No quedó nada escrito.
        return HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "No pudimos comunicarnos con la pasarela de pago. Intente de nuevo.",
        )
    if isinstance(error, seguridad.PerfilInexistente):
        return HTTPException(403, "Su cuenta no tiene una ficha de cliente asociada.")
    return HTTPException(400, "No se pudo completar la operación.")


@router.get(
    "/opciones",
    response_model=OpcionesDePedidoOut,
    summary="CU-27 · Paso 1: qué puedo pedir y a dónde",
)
def opciones_de_pedido(db: DbSession, usuario: Usuario) -> OpcionesDePedidoOut:
    """El carrito, las sucursales que pueden abastecerlo y mis direcciones.

    Todo junto a propósito: pedirlo en tres viajes dejaría la pantalla
    pintándose por partes y abriría una ventana en la que el total podría
    cambiar entre una consulta y la siguiente.
    """
    try:
        return service.opciones_de_pedido(db, usuario.id)
    except Exception as e:
        raise _traducir(e) from e


@router.post(
    "",
    response_model=CrearPedidoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-27 · Paso 2: confirmar el pedido e iniciar el pago",
    responses={
        409: {
            "description": (
                "El total cambió, el carrito no sirve, ya hay un pedido "
                "pendiente, o no queda stock."
            )
        },
        502: {"description": "La pasarela de pago no respondió."},
    },
)
def crear_pedido(
    datos: CrearPedidoIn, db: DbSession, usuario: Usuario
) -> CrearPedidoOut:
    """Crea el pedido, aparta el stock y devuelve la URL de la pasarela.

    El estado del pedido nace en `PENDIENTE_PAGO` y **no lo mueve esta ruta**:
    lo mueve el webhook verificado de CU-28. Es la decisión D5.
    """
    try:
        return service.crear_pedido(db, usuario.id, datos)
    except service.PrecioCambiado as e:
        # 409 con cuerpo propio: la pantalla necesita el carrito al día para
        # que el cliente vea QUÉ cambió, no solo que cambió.
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=service.conflicto_de_precio(db, usuario.id, e).model_dump(mode="json"),
        ) from e
    except Exception as e:
        raise _traducir(e) from e


@router.get(
    "/{codigo}",
    response_model=PedidoOut,
    summary="CU-27 · Paso 5: el estado de mi pedido",
)
def ver_pedido(codigo: Codigo, db: DbSession, usuario: Usuario) -> PedidoOut:
    """La ficha del pedido. Es lo que consulta la pantalla de retorno.

    Devuelve el estado que dice la BASE, no el que diga la URL por la que el
    navegador volvió de la pasarela. Ver D5: esa URL la puede escribir
    cualquiera a mano.
    """
    try:
        return service.ver_pedido(db, usuario.id, codigo)
    except Exception as e:
        raise _traducir(e) from e


@router.post(
    "/{codigo}/cancelar",
    response_model=PedidoOut,
    summary="CU-27 · Flujo alternativo: cancelar antes de pagar",
)
def cancelar_pedido(codigo: Codigo, db: DbSession, usuario: Usuario) -> PedidoOut:
    """Cancela un pedido que todavía espera pago y devuelve el stock apartado.

    Una venta ya pagada NO se cancela por acá: eso es una devolución (CU-32),
    que mueve dinero y necesita una caja.
    """
    try:
        return service.cancelar_pedido(db, usuario.id, codigo)
    except Exception as e:
        raise _traducir(e) from e


@router_operacion.post(
    "/expirar-vencidos",
    response_model=ExpiracionDePedidosOut,
    summary="CU-27 · Devolver el stock de los pedidos que nadie pagó",
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)
def expirar_pedidos_vencidos(db: DbSession) -> ExpiracionDePedidosOut:
    """Cancela los pedidos sin pagar vencidos y devuelve sus unidades.

    Misma forma que la expiración de reservas de CU-25: no hay planificador en
    el proceso, se dispara desde afuera.

    **Sin esto, apartar stock al confirmar sería un defecto**: cada cliente que
    abre la pasarela y cierra la pestaña se llevaría unidades del inventario
    para siempre.
    """
    return service.expirar_pedidos_vencidos(db)
