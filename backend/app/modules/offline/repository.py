"""
P14 - Offline y sincronización / CU-13 a CU-19  |  capa: repositorio

Ninguna consulta filtra por empresa: lo hace la RLS de cada tabla.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Row, and_, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Categoria, Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia, MovimientoInventario
from app.modules.offline.models import OperacionOffline
from app.modules.organizacion.models import Proveedor, Sucursal
from app.modules.plataforma.models import ClienteEmpresa
from app.modules.seguridad.models import Cliente, Usuario

#: Tope de lo que se descarga. Una boutique tiene cientos de variantes, no
#: decenas de miles; el tope está para que un catálogo raro no llene el
#: almacenamiento del teléfono.
MAXIMO_PRENDAS = 2_000
MAXIMO_CLIENTES = 1_000


def operacion_por_uuid(
    db: Session, uuid: UUID, *, bloquear: bool = False
) -> OperacionOffline | None:
    consulta = select(OperacionOffline).where(OperacionOffline.uuid == uuid)
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def sucursal(db: Session, sucursal_id: int) -> Sucursal | None:
    return db.get(Sucursal, sucursal_id)


def sucursales_activas(db: Session) -> list[Sucursal]:
    return list(
        db.scalars(
            select(Sucursal).where(Sucursal.activa.is_(True)).order_by(Sucursal.nombre)
        )
    )


def _prendas() -> select:
    return (
        select(
            VarianteProducto.id.label("variante_id"),
            VarianteProducto.sku,
            Producto.id.label("producto_id"),
            Producto.nombre.label("producto"),
            Categoria.nombre.label("categoria"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
            VarianteProducto.precio,
            Existencia.sucursal_id,
            Existencia.cantidad_disponible.label("disponible"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(Existencia, Existencia.variante_id == VarianteProducto.id)
        .where(
            VarianteProducto.activa.is_(True),
            Producto.activo.is_(True),
            Existencia.cantidad_disponible > 0,
        )
        .order_by(Producto.nombre, Talla.codigo, Color.nombre)
    )


def prendas_de_sucursal(db: Session, sucursal_id: int) -> list[Row]:
    """Lo vendible en una sucursal. Solo con saldo, como el mostrador (CU-31)."""
    return list(
        db.execute(
            _prendas().where(Existencia.sucursal_id == sucursal_id).limit(MAXIMO_PRENDAS)
        )
    )


def prendas_en_sucursales_activas(db: Session) -> list[Row]:
    """Una fila por prenda y sucursal activa con saldo (para reservar)."""
    return list(
        db.execute(
            _prendas()
            .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
            .where(Sucursal.activa.is_(True))
            .limit(MAXIMO_PRENDAS * 4)
        )
    )


def clientes_de_la_empresa(db: Session) -> list[Row]:
    """Los clientes que ya compraron o reservaron en esta empresa (RN-13)."""
    return list(
        db.execute(
            select(
                Cliente.id,
                Usuario.nombres,
                Usuario.apellidos,
                Cliente.documento,
            )
            .join(ClienteEmpresa, ClienteEmpresa.cliente_id == Cliente.id)
            .join(Usuario, Usuario.id == Cliente.usuario_id)
            .where(Usuario.activo.is_(True))
            .order_by(Usuario.apellidos, Usuario.nombres)
            .limit(MAXIMO_CLIENTES)
        )
    )


def cliente_de_la_empresa(db: Session, cliente_id: int) -> bool:
    return (
        db.scalar(
            select(ClienteEmpresa.cliente_id).where(
                ClienteEmpresa.cliente_id == cliente_id
            )
        )
        is not None
    )


def operaciones(
    db: Session,
    *,
    sucursal_id: int | None = None,
    usuario_id: int | None = None,
    estado: str | None = None,
    por_devolver: bool = False,
    limite: int = 200,
) -> list[tuple[OperacionOffline, Usuario]]:
    consulta = select(OperacionOffline, Usuario).join(
        Usuario, Usuario.id == OperacionOffline.usuario_id
    )
    if sucursal_id is not None:
        consulta = consulta.where(OperacionOffline.sucursal_id == sucursal_id)
    if usuario_id is not None:
        consulta = consulta.where(OperacionOffline.usuario_id == usuario_id)
    if estado is not None:
        consulta = consulta.where(OperacionOffline.estado == estado)
    if por_devolver:
        consulta = consulta.where(
            OperacionOffline.estado == "RECHAZADA",
            OperacionOffline.monto_cobrado.is_not(None),
            OperacionOffline.devuelto_en.is_(None),
        )
    consulta = consulta.order_by(OperacionOffline.recibida_en.desc()).limit(limite)
    return [(fila[0], fila[1]) for fila in db.execute(consulta)]


# =====================================================================
# CU-21 Inventario sin conexión
# =====================================================================

def prendas_para_inventario(db: Session, sucursal_id: int) -> list[Row]:
    """Todas las prendas activas, con su saldo en la sucursal (cero si no hay)."""
    return list(
        db.execute(
            select(
                VarianteProducto.id.label("variante_id"),
                VarianteProducto.sku,
                Producto.nombre.label("producto"),
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
                func.coalesce(Existencia.cantidad_disponible, 0).label("disponible"),
                func.coalesce(Existencia.cantidad_reservada, 0).label("reservada"),
                func.coalesce(Existencia.stock_minimo, 0).label("stock_minimo"),
            )
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .outerjoin(
                Existencia,
                and_(
                    Existencia.variante_id == VarianteProducto.id,
                    Existencia.sucursal_id == sucursal_id,
                ),
            )
            .where(VarianteProducto.activa.is_(True), Producto.activo.is_(True))
            .order_by(Producto.nombre, Talla.codigo, Color.nombre)
            .limit(MAXIMO_PRENDAS)
        )
    )


def proveedores_activos(db: Session) -> list[Proveedor]:
    return list(
        db.scalars(
            select(Proveedor).where(Proveedor.activo.is_(True)).order_by(Proveedor.razon_social)
        )
    )


def unidades_de_operacion(db: Session, operacion_id: int) -> int:
    """Lo que movió una operación offline de inventario, con signo."""
    return int(
        db.scalar(
            select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0)).where(
                MovimientoInventario.operacion_offline_id == operacion_id
            )
        )
        or 0
    )


#: Los movimientos que pasan unidades entre el disponible y lo reservado: no
#: cambian lo que hay en la percha.
_NO_CAMBIAN_LO_FISICO = ("RESERVA", "LIBERACION")


def fisico_al_momento(
    db: Session, *, variante_id: int, sucursal_id: int, momento: datetime
) -> int:
    """CU-21 sin conexión: cuántas unidades había en la percha en `momento`.

    Es lo físico de hoy (disponible + reservada) menos lo que se movió después.
    Un movimiento que vino de una operación sin conexión cuenta en la hora en
    que pasó en el teléfono, no en la de la sincronización: una venta offline
    hecha antes del conteo y subida después ya no estaba en la percha cuando
    se contó.
    """
    existencia = db.scalar(
        select(Existencia).where(
            Existencia.variante_id == variante_id, Existencia.sucursal_id == sucursal_id
        )
    )
    if existencia is None:
        return 0
    cuando = func.coalesce(OperacionOffline.creada_en_cliente, MovimientoInventario.creado_en)
    posteriores = db.scalar(
        select(func.coalesce(func.sum(MovimientoInventario.cantidad), 0))
        .select_from(MovimientoInventario)
        .outerjoin(
            OperacionOffline, OperacionOffline.id == MovimientoInventario.operacion_offline_id
        )
        .where(
            MovimientoInventario.existencia_id == existencia.id,
            MovimientoInventario.tipo.not_in(_NO_CAMBIAN_LO_FISICO),
            cuando > momento,
        )
    )
    return existencia.cantidad_disponible + existencia.cantidad_reservada - int(posteriores)
