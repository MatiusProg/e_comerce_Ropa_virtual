"""CU-21 · Acceso a datos de medidas. Sin reglas de negocio y sin commit."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Talla
from app.modules.medidas.models import MedidaCliente, MedidaTalla
from app.modules.seguridad.models import Cliente


def cliente_de_usuario(db: Session, usuario_id: int) -> Cliente | None:
    return db.scalar(select(Cliente).where(Cliente.usuario_id == usuario_id))


def medidas_de(db: Session, cliente_id: int) -> MedidaCliente | None:
    return db.scalar(
        select(MedidaCliente).where(MedidaCliente.cliente_id == cliente_id)
    )


def guardar_medidas(
    db: Session,
    cliente_id: int,
    busto_cm: Decimal,
    cintura_cm: Decimal,
    cadera_cm: Decimal,
    altura_cm: Decimal | None,
) -> MedidaCliente:
    """Crea o actualiza las medidas del cliente. **Sin commit.**

    Es un `upsert` hecho a mano y no un `INSERT ... ON CONFLICT` porque la
    pantalla necesita la fila de vuelta para mostrarla, y el camino de
    actualizar es el habitual: casi nadie carga sus medidas una sola vez.
    """
    fila = medidas_de(db, cliente_id)
    if fila is None:
        fila = MedidaCliente(cliente_id=cliente_id)
        db.add(fila)
    fila.busto_cm = busto_cm
    fila.cintura_cm = cintura_cm
    fila.cadera_cm = cadera_cm
    fila.altura_cm = altura_cm
    db.flush()
    return fila


def tabla_de_producto(db: Session, producto_id: int) -> list[tuple]:
    """Las medidas de todas las tallas de un producto, de la mas chica a la mas grande.

    El orden sale de `talla.orden` y no del codigo: ordenar por texto pone la
    XL antes que la S, que es el mismo defecto que ya esta documentado en el
    modelo de `Talla`.
    """
    return list(
        db.execute(
            select(
                MedidaTalla.talla_id,
                Talla.codigo,
                MedidaTalla.busto_cm,
                MedidaTalla.cintura_cm,
                MedidaTalla.cadera_cm,
                MedidaTalla.largo_cm,
            )
            .join(Talla, Talla.id == MedidaTalla.talla_id)
            .where(MedidaTalla.producto_id == producto_id)
            .order_by(Talla.orden)
        ).all()
    )
