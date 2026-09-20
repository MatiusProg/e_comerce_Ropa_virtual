"""
P7 - Ventas y Punto de Venta / CU-26  |  capa: servicio (reglas y transacciones)

Ciclo de desarrollo: 3
Caso de uso: CU-26 Gestionar carrito de compras  (RF14)

DOS REGLAS QUE DEFINEN EL CASO DE USO, Y CONVIENE NO PERDERLAS
--------------------------------------------------------------
**1. El carrito no guarda precios.** Se calculan al leer, contra
`variante_producto`. Un carrito es una intencion, no un contrato: el precio se
fija al generar el pedido (CU-27). Guardar una foto dejaria al carrito cotizando
un valor que la tienda ya no sostiene, y el cliente lo descubriria al pagar.

**2. El carrito no inmoviliza inventario.** Agregar no descuenta ni aparta
nada. Eso lo hace una RESERVA (CU-22), que si aparta unidades porque el cliente
va a ir a buscarlas. Un carrito que apartara stock dejaria inventario congelado
por cada cliente que abandona la compra --- que son casi todos. Aqui la
disponibilidad se INFORMA; validarla en serio es de CU-27, contra el bloqueo de
la existencia, que es donde importa y donde ya esta resuelto el riesgo R5.

SOBRE LAS PROMOCIONES --- CERRADO EL 20/09
-------------------------------------------
La descripcion del caso de uso dice «ver el total con las promociones
aplicadas». Eso quedo pendiente hasta que existiera **CU-12**, y ya existe: la
tabla la estrena la `0016_ciclo3_promociones`.

El punto donde se aplican es `_armar_carrito`, tal como estaba anunciado, y es
**el unico lugar**: el total del carrito sale de ahi y de ningun otro lado.

El precio de lista y el descuento viajan por separado en cada linea, no un solo
numero ya rebajado: el cliente tiene que ver de cuanto era y cuanto paga, que
es lo que vuelve creible la oferta.
"""
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalogo import imagenes_almacen as almacen
from app.modules.catalogo import promociones_service as promociones
from app.modules.catalogo_publico import service as catalogo_publico
from app.modules.ventas import carrito_repository as repository
from app.modules.ventas.carrito_schemas import (
    AgregarAlCarritoIn,
    CambiarCantidadIn,
    CANTIDAD_MAXIMA,
    CarritoOut,
    LineaCarritoOut,
)

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.


# --- Errores de negocio --------------------------------------------------

class ErrorDelCarrito(Exception):
    """Base de los errores previstos de CU-26."""


class PrendaNoOfrecible(ErrorDelCarrito):
    """Excepcion E1: la variante no existe, o dejo de ofrecerse.

    Los tres casos --- inexistente, variante desactivada, producto desactivado
    --- son UNA sola excepcion, con el mismo criterio que CU-18: la vitrina no
    confirma que algo existe si no se puede comprar.
    """


class PrendaFueraDelCarrito(ErrorDelCarrito):
    """Se quiso cambiar o quitar algo que no esta en el carrito."""


class CantidadFueraDeRango(ErrorDelCarrito):
    """Sumar dejaria la linea por encima del tope por prenda.

    Es distinto de mandar una cantidad invalida --- eso lo rechaza el esquema
    con un 422 ---: aqui la peticion es valida y el resultado no.
    """


# --- El cliente del token ------------------------------------------------

def _cliente(db: Session, usuario_id: int) -> int:
    """El cliente del token, por la misma costura con P1 que usa CU-20.

    Si la cuenta no tiene ficha de cliente --- un Administrador, por ejemplo ---
    P1 levanta su excepcion y el router la traduce. P7 no necesita saber como se
    resuelve, y reusar la costura evita una segunda forma de responder lo mismo.
    """
    return catalogo_publico._cliente(db, usuario_id)


def _carrito_de(db: Session, cliente_id: int, *, crear: bool):
    """El carrito del cliente. Lo crea solo si hace falta escribir en el.

    Leer un carrito que no existe NO lo crea: si lo creara, cada visita a la
    pantalla dejaria una fila, y la mayoria de los clientes nunca agrega nada.
    """
    carrito = repository.obtener_carrito(db, cliente_id)
    if carrito is None and crear:
        carrito = repository.agregar_carrito(db, cliente_id)
    return carrito


# --- Armado de la respuesta ----------------------------------------------

def _armar_carrito(db: Session, carrito_id: int | None) -> CarritoOut:
    """El carrito completo, con precios, promociones y disponibilidad al dia.

    Es el unico lugar donde se calcula el total, y desde CU-12 tambien donde se
    aplican las promociones --- que es lo que este docstring venia anunciando
    desde el Ciclo 3 temprano ---.

    EL DESCUENTO SE LEE EN VIVO, COMO EL PRECIO
    --------------------------------------------
    `carrito_detalle` no guarda ni precio ni descuento. Si guardara el descuento,
    una promocion vencida se honraria indefinidamente y una que arranca hoy no
    alcanzaria lo que el cliente agrego ayer. El carrito es una intencion; lo
    que se congela es la venta (CU-27, CU-31).
    """
    if carrito_id is None:
        # Un carrito vacio no es un error ni un 404: es el estado normal de
        # quien todavia no agrego nada, y la pantalla tiene que poder pintarlo.
        return CarritoOut(lineas=[], items=0, unidades=0, total=Decimal("0.00"), no_disponibles=0)

    filas = repository.lineas_resueltas(db, carrito_id)
    stock = repository.stock_de_variantes(db, [f.variante_id for f in filas])
    imagenes = repository.imagen_principal(db, [f.producto_id for f in filas])

    # CU-12. Una sola consulta para todo el carrito, no una por linea.
    descuentos = promociones.descuentos_por_variante(
        db, {f.variante_id: f.precio for f in filas}
    )

    lineas: list[LineaCarritoOut] = []
    total = Decimal("0.00")
    no_disponibles = 0

    for fila in filas:
        disponible = bool(fila.ofrecible)
        descuento = descuentos.get(fila.variante_id)
        unitario = descuento.precio_final if descuento else fila.precio
        subtotal = (unitario * fila.cantidad) if disponible else Decimal("0.00")

        if disponible:
            total += subtotal
        else:
            no_disponibles += 1

        ruta = imagenes.get(fila.producto_id)
        lineas.append(
            LineaCarritoOut(
                variante_id=fila.variante_id,
                producto_id=fila.producto_id,
                sku=fila.sku,
                producto_nombre=fila.producto_nombre,
                talla_codigo=fila.talla_codigo,
                color_nombre=fila.color_nombre,
                color_hexadecimal=fila.color_hexadecimal,
                imagen_url=almacen.url_de(ruta) if ruta else None,
                cantidad=fila.cantidad,
                # El precio de lista y el descuento van por separado: el
                # cliente tiene que ver de cuanto era y cuanto paga.
                precio_unitario=fila.precio,
                descuento=promociones.a_contrato(descuento),
                subtotal=subtotal,
                disponible=disponible,
                stock_total=stock.get(fila.variante_id, 0),
            )
        )

    return CarritoOut(
        lineas=lineas,
        items=len(lineas),
        # Las unidades cuentan TODAS las lineas, disponibles o no: es lo que el
        # cliente metio en el carrito, y la burbuja del icono no puede cambiar
        # sola porque la tienda desactivo una prenda.
        unidades=sum(linea.cantidad for linea in lineas),
        total=total,
        no_disponibles=no_disponibles,
    )


# --- Flujo principal -----------------------------------------------------

def ver_carrito(db: Session, usuario_id: int) -> CarritoOut:
    """Paso 2: el carrito con sus precios y su disponibilidad al dia."""
    cliente_id = _cliente(db, usuario_id)
    carrito = _carrito_de(db, cliente_id, crear=False)
    return _armar_carrito(db, carrito.id if carrito else None)


def agregar(db: Session, usuario_id: int, datos: AgregarAlCarritoIn) -> CarritoOut:
    """Paso 3: agregar una prenda. SUMA a lo que ya hubiera de esa variante.

    Es lo que espera quien pulsa «Agregar» dos veces desde la ficha: la segunda
    vez no reemplaza la primera.

    No se comprueba el stock antes de agregar, y es deliberado: el carrito no
    aparta nada, asi que impedir agregar algo agotado solo le quitaria al
    cliente la posibilidad de dejarlo anotado mientras la tienda repone. La
    linea viaja con `stock_total` para que la pantalla lo diga.
    """
    cliente_id = _cliente(db, usuario_id)

    # Excepcion E1, antes de crear nada: agregar algo que no se ofrece no debe
    # dejar un carrito vacio de rastro.
    if repository.obtener_variante_ofrecible(db, datos.variante_id) is None:
        raise PrendaNoOfrecible(str(datos.variante_id))

    carrito = _carrito_de(db, cliente_id, crear=True)
    linea = repository.obtener_linea(db, carrito.id, datos.variante_id)

    try:
        if linea is None:
            repository.agregar_linea(
                db,
                carrito_id=carrito.id,
                variante_id=datos.variante_id,
                cantidad=datos.cantidad,
            )
        else:
            nueva = linea.cantidad + datos.cantidad
            if nueva > CANTIDAD_MAXIMA:
                # No se recorta en silencio al tope: el cliente pidio algo que
                # no se le puede dar y tiene que enterarse. Recortar dejaria una
                # cantidad distinta de la que pidio sin decirselo.
                db.rollback()
                raise CantidadFueraDeRango(str(nueva))
            linea.cantidad = nueva
        db.commit()
    except IntegrityError:
        # Dos peticiones simultaneas con la misma variante: el UNIQUE de
        # (carrito_id, variante_id) frena a la segunda. Se rehace la lectura y
        # se suma sobre la linea que gano.
        db.rollback()
        linea = repository.obtener_linea(db, carrito.id, datos.variante_id)
        if linea is None:
            raise
        linea.cantidad = min(linea.cantidad + datos.cantidad, CANTIDAD_MAXIMA)
        db.commit()
    except ErrorDelCarrito:
        raise
    except Exception:
        db.rollback()
        raise

    return _armar_carrito(db, carrito.id)


def cambiar_cantidad(
    db: Session, usuario_id: int, variante_id: int, datos: CambiarCantidadIn
) -> CarritoOut:
    """Flujo alternativo 3a: FIJA la cantidad de una linea, no la suma.

    Es la operacion del selector de cantidad del carrito. Va por otro verbo que
    `agregar` a proposito: un mismo endpoint que a veces suma y a veces fija
    seria imposible de usar sin mirar el codigo.

    Se permite fijar la cantidad de una prenda que dejo de ofrecerse: la linea
    sigue ahi y el cliente puede querer acomodarla antes de sacarla. No suma al
    total igual.
    """
    cliente_id = _cliente(db, usuario_id)
    carrito = _carrito_de(db, cliente_id, crear=False)
    linea = (
        repository.obtener_linea(db, carrito.id, variante_id) if carrito else None
    )
    if linea is None:
        raise PrendaFueraDelCarrito(str(variante_id))

    try:
        linea.cantidad = datos.cantidad
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _armar_carrito(db, carrito.id)


def quitar(db: Session, usuario_id: int, variante_id: int) -> CarritoOut:
    """Flujo alternativo 3b: sacar una prenda del carrito.

    Quitar algo que no esta NO es un error silencioso: se levanta la excepcion.
    A diferencia de desmarcar un favorito ---que es un corazon que se toca dos
    veces sin querer--- aqui el boton esta junto a una linea concreta, y que no
    exista significa que la pantalla esta desactualizada. Decirlo hace que se
    recargue.
    """
    cliente_id = _cliente(db, usuario_id)
    carrito = _carrito_de(db, cliente_id, crear=False)
    linea = (
        repository.obtener_linea(db, carrito.id, variante_id) if carrito else None
    )
    if linea is None:
        raise PrendaFueraDelCarrito(str(variante_id))

    try:
        repository.eliminar_linea(db, linea)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _armar_carrito(db, carrito.id)


def vaciar(db: Session, usuario_id: int) -> CarritoOut:
    """Flujo alternativo 3c: vaciar el carrito entero.

    Es idempotente: vaciar un carrito que ya estaba vacio no falla. Aqui SI,
    al reves que `quitar`, porque la operacion no habla de una linea concreta
    --- pedir «que quede vacio» sobre algo ya vacio es una peticion cumplida.
    """
    cliente_id = _cliente(db, usuario_id)
    carrito = _carrito_de(db, cliente_id, crear=False)
    if carrito is None:
        return _armar_carrito(db, None)

    try:
        repository.vaciar(db, carrito.id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _armar_carrito(db, carrito.id)
