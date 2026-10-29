"""
P14 - Offline y sincronización / CU-13 a CU-19  |  capa: repositorio

Ninguna consulta filtra por empresa: lo hace la RLS de cada tabla.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia
from app.modules.offline.models import OperacionOffline
from app.modules.organizacion.models import Sucursal
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
            Producto.nombre.label("producto"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
            VarianteProducto.precio,
            Existencia.sucursal_id,
            Existencia.cantidad_disponible.label("disponible"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
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
