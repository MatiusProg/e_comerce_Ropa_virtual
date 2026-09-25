"""
P11 - Reportes / CU-37  |  capa: repositorio (consultas, sin logica ni commit)

Las seis consultas que pide el RF36, mas la de devoluciones y cambios
(24/09/2026), que el RF36 no pedia y sin la cual el dinero devuelto no
aparecia en ningun lado. Cada una devuelve filas planas, listas
para el exportador: nada de objetos con relaciones, porque el exportador no
sabe navegarlas y cargarlas perezosamente aca seria una consulta por fila.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import (
    Coleccion,
    Color,
    Producto,
    Talla,
    Temporada,
    VarianteProducto,
)
from app.modules.inventario.models import Existencia, MovimientoInventario
from app.modules.organizacion.models import Proveedor, Sucursal
from app.modules.reservas.models import Reserva
from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import (
    Caja,
    DetalleDevolucion,
    DetalleVenta,
    Devolucion,
    TurnoCaja,
    Venta,
)

#: Los estados que cuentan como venta consumada. Una PENDIENTE_PAGO todavia no
#: vendio nada y una CANCELADA no vendio nunca: meterlas infla los reportes y
#: los vuelve incomparables con el tablero de CU-36, que usa el mismo criterio.
VENDIDAS = ("PAGADA", "ENTREGADA")


def _subtotal_de_linea():
    """Lo que aporto una linea de venta.

    `detalle_venta` guarda cantidad, precio unitario y descuento unitario, y
    NO el subtotal: es dato derivado y guardarlo permitiria que contradijera a
    los tres de los que sale.
    """
    return DetalleVenta.cantidad * (
        DetalleVenta.precio_unitario - DetalleVenta.descuento_unitario
    )


def _acotar_sucursal(consulta: Select, columna, sucursal_id: int | None) -> Select:
    return consulta if sucursal_id is None else consulta.where(columna == sucursal_id)


def _si(consulta: Select, columna, valor) -> Select:
    """Aplica el filtro solo si vino. Sin valor, el reporte no se acota.

    Es lo que permite que cada reporte declare sus filtros y que la pantalla
    mande solo los que el usuario eligio: un `None` significa «todos», no
    «ninguno».
    """
    return consulta if valor in (None, "") else consulta.where(columna == valor)


# --- 1. Ventas --------------------------------------------------------------


def ventas(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    canal: str | None = None,
    estado: str | None = None,
    metodo_pago: str | None = None,
) -> list[tuple]:
    consulta = (
        select(
            Venta.codigo,
            Venta.creado_en,
            Sucursal.nombre,
            Venta.canal,
            Venta.estado,
            func.coalesce(Venta.metodo_pago, "—"),
            Venta.total,
        )
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        .where(
            Venta.creado_en >= desde,
            Venta.creado_en < hasta,
            Venta.estado.in_(VENDIDAS),
        )
        .order_by(Venta.creado_en.desc())
    )
    consulta = _acotar_sucursal(consulta, Venta.sucursal_id, sucursal_id)
    consulta = _si(consulta, Venta.canal, canal)
    consulta = _si(consulta, Venta.metodo_pago, metodo_pago)
    # El estado ACOTA dentro de las consumadas, no las reemplaza: pedir
    # «canceladas» en un reporte de ventas no puede devolver ventas que no
    # existieron. El filtro elige entre PAGADA y ENTREGADA.
    consulta = _si(consulta, Venta.estado, estado)
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 2. Inventario ----------------------------------------------------------


def inventario(
    db: Session, *, sucursal_id: int | None, bajo_minimo: str | None = None
) -> list[tuple]:
    """Saldos por variante y sucursal.

    Sin periodo: un inventario es una FOTO de ahora, no un acumulado. Pedirle
    fechas seria prometer un saldo historico que la tabla no guarda --- los
    saldos se mantienen desnormalizados y solo tienen el valor actual.
    """
    consulta = (
        select(
            Sucursal.nombre,
            Producto.codigo,
            Producto.nombre,
            Talla.codigo,
            Color.nombre,
            Existencia.cantidad_disponible,
            Existencia.cantidad_reservada,
            Existencia.stock_minimo,
        )
        .join(VarianteProducto, VarianteProducto.id == Existencia.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .order_by(Sucursal.nombre, Producto.nombre, Talla.codigo)
    )
    consulta = _acotar_sucursal(consulta, Existencia.sucursal_id, sucursal_id)
    if bajo_minimo == "si":
        # Lo que hay que reponer. Es la consulta que de verdad se imprime: un
        # inventario completo de 2.355 filas no se lee, se archiva.
        consulta = consulta.where(
            Existencia.cantidad_disponible <= Existencia.stock_minimo
        )
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 3. Movimientos ---------------------------------------------------------


def movimientos(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    tipo: str | None = None,
) -> list[tuple]:
    consulta = (
        select(
            MovimientoInventario.creado_en,
            Sucursal.nombre,
            MovimientoInventario.tipo,
            Producto.nombre,
            Talla.codigo,
            Color.nombre,
            MovimientoInventario.cantidad,
            func.coalesce(Usuario.correo, "—"),
        )
        .join(Existencia, Existencia.id == MovimientoInventario.existencia_id)
        .join(VarianteProducto, VarianteProducto.id == Existencia.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .join(Usuario, Usuario.id == MovimientoInventario.usuario_id, isouter=True)
        .where(
            MovimientoInventario.creado_en >= desde,
            MovimientoInventario.creado_en < hasta,
        )
        .order_by(MovimientoInventario.creado_en.desc())
    )
    consulta = _acotar_sucursal(consulta, Existencia.sucursal_id, sucursal_id)
    consulta = _si(consulta, MovimientoInventario.tipo, tipo)
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 4. Reservas ------------------------------------------------------------


def reservas(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    estado: str | None = None,
) -> list[tuple]:
    # `Reserva` NO tiene columna `codigo` ---se identifica por id--- y
    # `cliente_id` apunta a `cliente`, no a `usuario`: el correo esta un salto
    # mas alla. Las dos cosas se comprobaron contra el modelo y no se
    # supusieron.
    consulta = (
        select(
            Reserva.id,
            Reserva.franja_inicio,
            Sucursal.nombre,
            Reserva.estado,
            func.coalesce(Usuario.correo, "—"),
        )
        .join(Sucursal, Sucursal.id == Reserva.sucursal_id)
        .join(Cliente, Cliente.id == Reserva.cliente_id, isouter=True)
        .join(Usuario, Usuario.id == Cliente.usuario_id, isouter=True)
        .where(Reserva.franja_inicio >= desde, Reserva.franja_inicio < hasta)
        .order_by(Reserva.franja_inicio.desc())
    )
    consulta = _acotar_sucursal(consulta, Reserva.sucursal_id, sucursal_id)
    consulta = _si(consulta, Reserva.estado, estado)
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 5. Rendimiento por temporada y coleccion -------------------------------


def rendimiento(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    temporada_id: int | None = None,
) -> list[tuple]:
    """Cuanto se vendio de cada temporada y coleccion.

    Es el unico reporte AGREGADO de los seis: los demas listan hechos. Aca la
    pregunta es «que temporada funciono», y una lista de ventas sueltas no la
    contesta.
    """
    consulta = (
        select(
            func.coalesce(Temporada.nombre, "Sin temporada"),
            func.coalesce(Coleccion.nombre, "Sin colección"),
            func.count(func.distinct(Venta.id)),
            func.sum(DetalleVenta.cantidad),
            # `DetalleVenta` no guarda el subtotal de la linea: se calcula con
            # el precio y el descuento unitarios, que son lo que si tiene.
            func.sum(_subtotal_de_linea()),
        )
        .select_from(DetalleVenta)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .join(VarianteProducto, VarianteProducto.id == DetalleVenta.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Temporada, Temporada.id == Producto.temporada_id, isouter=True)
        .join(Coleccion, Coleccion.id == Producto.coleccion_id, isouter=True)
        .where(
            Venta.creado_en >= desde,
            Venta.creado_en < hasta,
            Venta.estado.in_(VENDIDAS),
        )
        .group_by(Temporada.nombre, Coleccion.nombre)
        .order_by(func.sum(_subtotal_de_linea()).desc())
    )
    consulta = _acotar_sucursal(consulta, Venta.sucursal_id, sucursal_id)
    consulta = _si(consulta, Producto.temporada_id, temporada_id)
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 6. Compras por proveedor -----------------------------------------------


def compras(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    proveedor_id: int | None = None,
) -> list[tuple]:
    """Lo que entro por ingreso de mercaderia, por proveedor.

    «Compras» del lado de la tienda es el INGRESO de CU-13: no hay una tabla
    de ordenes de compra, y el movimiento de ingreso es el hecho que la
    registra.
    """
    consulta = (
        select(
            func.coalesce(Proveedor.razon_social, "Sin proveedor"),
            Sucursal.nombre,
            func.count(func.distinct(MovimientoInventario.id)),
            func.sum(MovimientoInventario.cantidad),
        )
        .select_from(MovimientoInventario)
        .join(Existencia, Existencia.id == MovimientoInventario.existencia_id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .join(
            Proveedor,
            Proveedor.id == MovimientoInventario.proveedor_id,
            isouter=True,
        )
        .where(
            MovimientoInventario.creado_en >= desde,
            MovimientoInventario.creado_en < hasta,
            MovimientoInventario.tipo == "INGRESO",
        )
        .group_by(Proveedor.razon_social, Sucursal.nombre)
        .order_by(func.sum(MovimientoInventario.cantidad).desc())
    )
    consulta = _acotar_sucursal(consulta, Existencia.sucursal_id, sucursal_id)
    consulta = _si(consulta, MovimientoInventario.proveedor_id, proveedor_id)
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 7. Devoluciones y cambios ----------------------------------------------


def devoluciones(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    tipo: str | None = None,
) -> list[tuple]:
    """Lo que volvio al local, EN DINERO, prenda por prenda.

    POR QUE ESTE REPORTE TIENE QUE EXISTIR
    ---------------------------------------
    Hasta el 24/09/2026 el dinero devuelto no aparecia en NINGUN reporte ni en
    el tablero. Lo unico rastreable era la mercaderia, en el reporte de
    movimientos filtrado por `DEVOLUCION`, y en unidades: nadie podia decir
    cuanto valia lo que volvio, ni que prenda vuelve mas, ni en que caja.

    UNA FILA POR LINEA DEVUELTA, Y NO POR DEVOLUCION
    -------------------------------------------------
    Es lo que permite las dos lecturas que hacen falta: **por producto** ---que
    prenda se devuelve mas, que es donde se ve una talla mal rotulada o una
    falla de confeccion--- y **por cajero**, que es quien la recibio.

    Agrupar por devolucion daria el flujo de caja y perderia las dos.

    EL VALOR SALE DEL PRECIO CONGELADO DE LA VENTA, NO DEL DE HOY
    --------------------------------------------------------------
    Por eso el `join` con `detalle_venta` por (venta, variante): lo que volvio
    vale lo que el cliente pago por ello. Si se leyera
    `variante_producto.precio`, una prenda que cambio de precio despues
    reescribiria hacia atras cuanto se devolvio el mes pasado.

    **Este valor no esta guardado en ninguna columna, y es a proposito.**
    `devolucion.monto` es otra cosa ---lo que sale del CAJON, cero con tarjeta,
    con QR y en todo cambio---. Guardar el valor seria un dato derivado que
    puede contradecir a los tres de los que sale.

    LA SUCURSAL SALE DEL TURNO, NO DE LA VENTA
    --------------------------------------------
    Una devolucion se recibe donde se recibe. Que la venta original sea de otra
    sucursal no cambia donde volvio la prenda ni de que inventario forma parte
    ahora.
    """
    valor = DetalleDevolucion.cantidad * (
        DetalleVenta.precio_unitario - DetalleVenta.descuento_unitario
    )
    consulta = (
        select(
            Devolucion.creado_en,
            Sucursal.nombre,
            Devolucion.tipo,
            Venta.codigo,
            func.coalesce(Usuario.correo, "—"),
            Producto.nombre,
            Talla.codigo,
            Color.nombre,
            DetalleDevolucion.cantidad,
            valor.label("valor"),
        )
        .join(DetalleDevolucion, DetalleDevolucion.devolucion_id == Devolucion.id)
        .join(Venta, Venta.id == Devolucion.venta_id)
        # El precio CONGELADO de esa prenda en esa venta. Es un join por DOS
        # columnas: la misma variante en otra venta se pago otro precio.
        .join(
            DetalleVenta,
            (DetalleVenta.venta_id == Devolucion.venta_id)
            & (DetalleVenta.variante_id == DetalleDevolucion.variante_id),
        )
        .join(VarianteProducto, VarianteProducto.id == DetalleDevolucion.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(TurnoCaja, TurnoCaja.id == Devolucion.turno_caja_id)
        .join(Caja, Caja.id == TurnoCaja.caja_id)
        .join(Sucursal, Sucursal.id == Caja.sucursal_id)
        .join(Usuario, Usuario.id == TurnoCaja.usuario_id, isouter=True)
        .where(
            Devolucion.creado_en >= desde,
            Devolucion.creado_en < hasta,
        )
        .order_by(Devolucion.creado_en.desc())
    )
    consulta = _acotar_sucursal(consulta, Caja.sucursal_id, sucursal_id)
    consulta = _si(consulta, Devolucion.tipo, tipo)
    return [tuple(f) for f in db.execute(consulta).all()]


def opciones_de_sucursal(db: Session) -> list[tuple[str, str]]:
    return [
        (str(f[0]), f[1])
        for f in db.execute(
            select(Sucursal.id, Sucursal.nombre)
            .where(Sucursal.activa.is_(True))
            .order_by(Sucursal.nombre)
        ).all()
    ]


def opciones_de_proveedor(db: Session) -> list[tuple[str, str]]:
    return [
        (str(f[0]), f[1])
        for f in db.execute(
            select(Proveedor.id, Proveedor.razon_social)
            .where(Proveedor.activo.is_(True))
            .order_by(Proveedor.razon_social)
        ).all()
    ]


def opciones_de_temporada(db: Session) -> list[tuple[str, str]]:
    from app.modules.catalogo.models import Temporada as T

    return [
        (str(f[0]), f[1])
        for f in db.execute(
            select(T.id, T.nombre).order_by(T.fecha_inicio.desc())
        ).all()
    ]


def nombre_de_sucursal(db: Session, sucursal_id: int) -> str | None:
    return db.scalar(select(Sucursal.nombre).where(Sucursal.id == sucursal_id))
