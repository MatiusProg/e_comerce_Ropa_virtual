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

from sqlalchemy import Row, delete, func, select
from sqlalchemy.orm import Session

from app.modules.analitica.models import CONSERVAR, ModeloAnalitica
from app.modules.catalogo.models import Categoria, Producto, VarianteProducto
from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import DetalleVenta, Venta

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
