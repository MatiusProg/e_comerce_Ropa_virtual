"""
P19 - Analítica con ML / CU-29 y CU-30  |  capa: repositorio

Los datos REALES de la empresa que alimentan a los modelos, y la persistencia
de los entrenamientos. Todo pasa por la sesión de la petición: el RLS deja
fuera las filas de otra empresa sin un `WHERE empresa_id` que olvidarse.

Una venta cuenta si se cobró: PAGADA o ENTREGADA. Las pendientes de pago y
las canceladas no son demanda.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Row, case, delete, func, select
from sqlalchemy.orm import Session

from app.modules.analitica.models import CONSERVAR, ModeloAnalitica
from app.modules.catalogo.models import Categoria, Producto, VarianteProducto
from app.modules.organizacion.models import Sucursal
from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import (
    Caja,
    DetalleDevolucion,
    DetalleVenta,
    Devolucion,
    TurnoCaja,
    Venta,
)

ESTADOS_COBRADOS = ("PAGADA", "ENTREGADA")

#: Tope de productos por entrenamiento: que entrene en segundos.
MAX_PRODUCTOS = 300

#: La semana empieza el lunes, en hora boliviana (ver app/core/tiempo.py).
_SEMANA = func.date_trunc("week", func.timezone("America/La_Paz", Venta.creado_en))


def productos_activos(db: Session) -> list[Row]:
    """id, nombre, categoría, precio y si tiene temporada, de los activos."""
    return list(db.execute(
        select(
            Producto.id,
            Producto.nombre,
            Categoria.nombre.label("categoria"),
            Producto.precio_base,
            Producto.temporada_id,
        )
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .where(Producto.activo.is_(True))
        .order_by(Producto.id)
        .limit(MAX_PRODUCTOS)
    ).all())


def ventas_semanales(db: Session, desde: datetime) -> list[Row]:
    """Unidades vendidas por producto y semana, desde `desde`."""
    semana = _SEMANA.label("semana")
    return list(db.execute(
        select(
            VarianteProducto.producto_id,
            semana,
            func.sum(DetalleVenta.cantidad).label("unidades"),
        )
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .join(VarianteProducto, VarianteProducto.id == DetalleVenta.variante_id)
        .where(Venta.estado.in_(ESTADOS_COBRADOS), Venta.creado_en >= desde)
        .group_by(VarianteProducto.producto_id, semana)
    ).all())


def rfm_de_clientes(db: Session) -> list[Row]:
    """Por cliente: su última compra, cuántas compras y cuánto gastó."""
    return list(db.execute(
        select(
            Venta.cliente_id,
            Usuario.nombres,
            Usuario.apellidos,
            func.max(Venta.creado_en).label("ultima"),
            func.count(Venta.id).label("compras"),
            func.sum(Venta.total).label("monto"),
        )
        .join(Cliente, Cliente.id == Venta.cliente_id)
        .join(Usuario, Usuario.id == Cliente.usuario_id)
        .where(Venta.estado.in_(ESTADOS_COBRADOS), Venta.cliente_id.is_not(None))
        .group_by(Venta.cliente_id, Usuario.nombres, Usuario.apellidos)
    ).all())


# --- Aporte propio: anomalías en caja y devoluciones ---------------------------

#: Tope de filas por entrenamiento de anomalías.
MAX_FILAS_ANOMALIAS = 5000


def turnos_cerrados(db: Session, desde: datetime) -> list[Row]:
    """Cada turno cerrado con su arqueo, lo vendido y lo devuelto en él."""
    ventas = (
        select(
            Venta.turno_caja_id.label("turno_id"),
            func.count(Venta.id).label("ventas"),
            func.sum(Venta.subtotal).label("subtotal"),
            func.sum(Venta.descuento).label("descuento"),
            func.sum(Venta.total).label("total"),
            func.sum(case((Venta.metodo_pago == "EFECTIVO", Venta.total), else_=0)).label(
                "efectivo"
            ),
        )
        .where(Venta.turno_caja_id.is_not(None), Venta.estado != "CANCELADA")
        .group_by(Venta.turno_caja_id)
        .subquery()
    )
    devueltas = (
        select(
            Devolucion.turno_caja_id.label("turno_id"),
            func.count(Devolucion.id).label("devoluciones"),
            func.sum(Devolucion.monto).label("monto_devuelto"),
        )
        .where(Devolucion.turno_caja_id.is_not(None))
        .group_by(Devolucion.turno_caja_id)
        .subquery()
    )
    return list(db.execute(
        select(
            TurnoCaja.id,
            TurnoCaja.abierto_en,
            TurnoCaja.cerrado_en,
            TurnoCaja.monto_cierre,
            TurnoCaja.monto_esperado,
            Caja.nombre.label("caja"),
            Sucursal.nombre.label("sucursal"),
            (Usuario.nombres + " " + Usuario.apellidos).label("cajero"),
            func.coalesce(ventas.c.ventas, 0).label("ventas"),
            func.coalesce(ventas.c.subtotal, 0).label("subtotal"),
            func.coalesce(ventas.c.descuento, 0).label("descuento"),
            func.coalesce(ventas.c.total, 0).label("total"),
            func.coalesce(ventas.c.efectivo, 0).label("efectivo"),
            func.coalesce(devueltas.c.devoluciones, 0).label("devoluciones"),
            func.coalesce(devueltas.c.monto_devuelto, 0).label("monto_devuelto"),
        )
        .join(Caja, Caja.id == TurnoCaja.caja_id)
        .join(Sucursal, Sucursal.id == Caja.sucursal_id)
        .join(Usuario, Usuario.id == TurnoCaja.usuario_id)
        .outerjoin(ventas, ventas.c.turno_id == TurnoCaja.id)
        .outerjoin(devueltas, devueltas.c.turno_id == TurnoCaja.id)
        .where(TurnoCaja.cerrado_en.is_not(None), TurnoCaja.abierto_en >= desde)
        .order_by(TurnoCaja.abierto_en.desc())
        .limit(MAX_FILAS_ANOMALIAS)
    ).all())


def devoluciones_recientes(db: Session, desde: datetime) -> list[Row]:
    """Cada devolución o cambio con lo que valía, su venta y quién la atendió."""
    valor = (
        select(
            DetalleDevolucion.devolucion_id,
            func.sum(
                DetalleDevolucion.cantidad
                * (DetalleVenta.precio_unitario - DetalleVenta.descuento_unitario)
            ).label("valor"),
        )
        .join(Devolucion, Devolucion.id == DetalleDevolucion.devolucion_id)
        .join(DetalleVenta, (DetalleVenta.venta_id == Devolucion.venta_id)
              & (DetalleVenta.variante_id == DetalleDevolucion.variante_id))
        .group_by(DetalleDevolucion.devolucion_id)
        .subquery()
    )
    quien = func.coalesce(TurnoCaja.usuario_id, Devolucion.recibida_por)
    return list(db.execute(
        select(
            Devolucion.id,
            Devolucion.creado_en,
            Devolucion.tipo,
            Devolucion.monto,
            Venta.creado_en.label("venta_en"),
            Venta.entregado_en,
            Venta.metodo_pago,
            quien.label("usuario_id"),
            (Usuario.nombres + " " + Usuario.apellidos).label("cajero"),
            Sucursal.nombre.label("sucursal"),
            func.coalesce(valor.c.valor, Devolucion.monto).label("valor"),
        )
        .join(Venta, Venta.id == Devolucion.venta_id)
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        .outerjoin(TurnoCaja, TurnoCaja.id == Devolucion.turno_caja_id)
        .outerjoin(Usuario, Usuario.id == quien)
        .outerjoin(valor, valor.c.devolucion_id == Devolucion.id)
        .where(Devolucion.creado_en >= desde)
        .order_by(Devolucion.creado_en.desc())
        .limit(MAX_FILAS_ANOMALIAS)
    ).all())


def ventas_por_cajero(db: Session, desde: datetime) -> dict[int, int]:
    """Cuántas ventas cobró cada cajero desde `desde` (para su tasa de devolución)."""
    return dict(db.execute(
        select(TurnoCaja.usuario_id, func.count(Venta.id))
        .join(TurnoCaja, TurnoCaja.id == Venta.turno_caja_id)
        .where(Venta.creado_en >= desde, Venta.estado != "CANCELADA")
        .group_by(TurnoCaja.usuario_id)
    ).all())


# --- Los entrenamientos ---------------------------------------------------------

def guardar(db: Session, modelo: ModeloAnalitica) -> ModeloAnalitica:
    """Agrega el entrenamiento y borra los viejos de su tipo (sin commit)."""
    db.add(modelo)
    db.flush()
    viejos = select(ModeloAnalitica.id).where(
        ModeloAnalitica.tipo == modelo.tipo
    ).order_by(ModeloAnalitica.entrenado_en.desc(), ModeloAnalitica.id.desc()).offset(CONSERVAR)
    db.execute(delete(ModeloAnalitica).where(ModeloAnalitica.id.in_(viejos)))
    return modelo


def ultimo(db: Session, tipo: str) -> ModeloAnalitica | None:
    return db.scalar(
        select(ModeloAnalitica)
        .where(ModeloAnalitica.tipo == tipo)
        .order_by(ModeloAnalitica.entrenado_en.desc(), ModeloAnalitica.id.desc())
        .limit(1)
    )


def historial(db: Session) -> list[Row]:
    """Los entrenamientos conservados, sin el modelo serializado."""
    return list(db.execute(
        select(
            ModeloAnalitica.id,
            ModeloAnalitica.tipo,
            ModeloAnalitica.entrenado_en,
            ModeloAnalitica.metricas,
            ModeloAnalitica.filas_entrenamiento,
            ModeloAnalitica.filas_reales,
            ModeloAnalitica.filas_sinteticas,
            ModeloAnalitica.duracion_ms,
            (Usuario.nombres + " " + Usuario.apellidos).label("entrenado_por"),
        )
        .outerjoin(Usuario, Usuario.id == ModeloAnalitica.entrenado_por)
        .order_by(ModeloAnalitica.entrenado_en.desc(), ModeloAnalitica.id.desc())
    ).all())
