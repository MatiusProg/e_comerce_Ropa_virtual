"""
P11 - Reportes / CU-37  |  capa: repositorio (consultas, sin logica ni commit)

Las seis consultas que pide el RF36. Cada una devuelve filas planas, listas
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
from app.modules.ventas.models import DetalleVenta, Venta

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


# --- 1. Ventas --------------------------------------------------------------


def ventas(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
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
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 2. Inventario ----------------------------------------------------------


def inventario(db: Session, *, sucursal_id: int | None) -> list[tuple]:
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
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 3. Movimientos ---------------------------------------------------------


def movimientos(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
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
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 4. Reservas ------------------------------------------------------------


def reservas(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
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
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 5. Rendimiento por temporada y coleccion -------------------------------


def rendimiento(
    db: Session, *, desde: datetime, hasta: datetime, sucursal_id: int | None
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
    return [tuple(f) for f in db.execute(consulta).all()]


# --- 6. Compras por proveedor -----------------------------------------------


def compras(
    db: Session, *, desde: datetime, hasta: datetime, sucursal_id: int | None
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
    return [tuple(f) for f in db.execute(consulta).all()]


def nombre_de_sucursal(db: Session, sucursal_id: int) -> str | None:
    return db.scalar(select(Sucursal.nombre).where(Sucursal.id == sucursal_id))
