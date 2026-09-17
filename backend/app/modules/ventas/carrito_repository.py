"""
P7 - Ventas y Punto de Venta / CU-26  |  capa: repositorio (consultas)

Ciclo de desarrollo: 3
Caso de uso: CU-26 Gestionar carrito de compras

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, NINGUN commit: el control de la transaccion vive en el servicio.
"""
from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import (
    Color,
    ImagenProducto,
    Producto,
    Talla,
    VarianteProducto,
)
from app.modules.inventario.models import Existencia
from app.modules.ventas.carrito_models import Carrito, CarritoDetalle


# --- El carrito ----------------------------------------------------------

def obtener_carrito(db: Session, cliente_id: int) -> Carrito | None:
    """El carrito del cliente, o None si nunca agrego nada."""
    return db.scalar(select(Carrito).where(Carrito.cliente_id == cliente_id))


def agregar_carrito(db: Session, cliente_id: int) -> Carrito:
    """Crea el carrito. No confirma: la transaccion es del servicio."""
    carrito = Carrito(cliente_id=cliente_id)
    db.add(carrito)
    db.flush()
    return carrito


# --- Las lineas ----------------------------------------------------------

def obtener_linea(
    db: Session, carrito_id: int, variante_id: int
) -> CarritoDetalle | None:
    return db.scalar(
        select(CarritoDetalle).where(
            CarritoDetalle.carrito_id == carrito_id,
            CarritoDetalle.variante_id == variante_id,
        )
    )


def agregar_linea(
    db: Session, *, carrito_id: int, variante_id: int, cantidad: int
) -> CarritoDetalle:
    linea = CarritoDetalle(
        carrito_id=carrito_id, variante_id=variante_id, cantidad=cantidad
    )
    db.add(linea)
    db.flush()
    return linea


def eliminar_linea(db: Session, linea: CarritoDetalle) -> None:
    db.delete(linea)


def vaciar(db: Session, carrito_id: int) -> int:
    """Borra todas las lineas. Devuelve cuantas eran.

    El carrito en si NO se borra: la fila vale poco y volver a crearla en la
    proxima prenda seria una escritura mas. Un carrito sin lineas es un carrito
    vacio, que es un estado legitimo.
    """
    lineas = list(
        db.scalars(select(CarritoDetalle).where(CarritoDetalle.carrito_id == carrito_id))
    )
    for linea in lineas:
        db.delete(linea)
    return len(lineas)


# --- La lectura del carrito, que es una sola consulta --------------------

def lineas_resueltas(db: Session, carrito_id: int) -> list[Row]:
    """Las lineas con la prenda ya resuelta: nombre, talla, color y estado.

    UNA consulta para todo el carrito. La alternativa --- leer las lineas y
    pedir la ficha de cada variante --- haria una consulta por prenda, que es el
    defecto que la pantalla de inventario ya pago una vez.

    `ofrecible` sale de aqui y no del servicio porque son dos banderas de la
    base: la variante activa y su producto activo. Una prenda que dejo de
    ofrecerse despues de agregarse sigue en el carrito --- la fila no se borra
    sola --- pero no suma al total.
    """
    return list(
        db.execute(
            select(
                CarritoDetalle.id.label("linea_id"),
                CarritoDetalle.variante_id,
                CarritoDetalle.cantidad,
                VarianteProducto.sku,
                VarianteProducto.precio,
                VarianteProducto.producto_id,
                Producto.nombre.label("producto_nombre"),
                Talla.codigo.label("talla_codigo"),
                Color.nombre.label("color_nombre"),
                Color.hexadecimal.label("color_hexadecimal"),
                (VarianteProducto.activa & Producto.activo).label("ofrecible"),
            )
            .join(VarianteProducto, VarianteProducto.id == CarritoDetalle.variante_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(CarritoDetalle.carrito_id == carrito_id)
            # Lo ultimo agregado primero: es lo que el cliente acaba de tocar y
            # lo que espera ver arriba.
            .order_by(CarritoDetalle.creado_en.desc(), CarritoDetalle.id.desc())
        ).all()
    )


def stock_de_variantes(db: Session, variante_ids: list[int]) -> dict[int, int]:
    """Unidades disponibles en TODA la red, por variante.

    Es un aviso para el cliente, no una reserva: el carrito no inmoviliza nada
    --- eso es CU-22 --- y la validacion de verdad ocurre al generar el pedido.

    Se suma `cantidad_disponible` y no se toca `cantidad_reservada`: lo
    reservado sigue siendo de la tienda pero ya esta apartado para otro.
    """
    if not variante_ids:
        return {}
    filas = db.execute(
        select(Existencia.variante_id, func.sum(Existencia.cantidad_disponible))
        .where(Existencia.variante_id.in_(variante_ids))
        .group_by(Existencia.variante_id)
    ).all()
    return {variante_id: int(total or 0) for variante_id, total in filas}


def imagen_principal(db: Session, producto_ids: list[int]) -> dict[int, str]:
    """La foto de cada producto, con el mismo criterio que la vitrina.

    Se excluye la transparente: es el activo del vestidor virtual, no una foto
    de catalogo, y en una lista se veria como un recorte suelto. Es la misma
    regla que aplica CU-17.
    """
    if not producto_ids:
        return {}
    filas = db.execute(
        select(ImagenProducto.producto_id, ImagenProducto.ruta)
        .where(
            ImagenProducto.producto_id.in_(producto_ids),
            ImagenProducto.es_transparente.is_(False),
        )
        .distinct(ImagenProducto.producto_id)
        .order_by(
            ImagenProducto.producto_id,
            ImagenProducto.es_principal.desc(),
            ImagenProducto.orden,
            ImagenProducto.id,
        )
    ).all()
    return {fila[0]: fila[1] for fila in filas}


def obtener_variante_ofrecible(db: Session, variante_id: int) -> Row | None:
    """La variante, si existe y se puede comprar hoy.

    Devuelve None cuando no existe, cuando esta desactivada o cuando su producto
    lo esta. Los tres casos se responden igual hacia afuera, con el mismo
    criterio que CU-18: la vitrina no confirma que algo existe si no se ofrece.
    """
    return db.execute(
        select(VarianteProducto.id, VarianteProducto.producto_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .where(
            VarianteProducto.id == variante_id,
            VarianteProducto.activa.is_(True),
            Producto.activo.is_(True),
        )
    ).one_or_none()
