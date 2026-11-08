"""Aporte propio · «Avísame cuando llegue mi talla»  |  capa: modelo."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DeEmpresa


class AvisoTalla(DeEmpresa, Base):
    """El pedido de un cliente: «avíseme cuando vuelva esta talla y color».

    **Es de la VARIANTE y no del producto**, al revés que el favorito: lo que se
    agotó es una talla y un color concretos, y avisar «llegó la blusa» cuando
    llegó en una talla que no es la suya sería ruido.

    Nace pendiente (`notificado_en` nulo). El inventario, al reponer, la marca
    notificada en la misma transacción en la que deja el aviso, así que no se
    avisa dos veces. Cancelar la borra: no es historial que alguien consulte.
    La fila notificada sí queda, porque cuenta cuántas veces una talla tuvo
    clientes esperando.
    """

    __tablename__ = "aviso_talla"
    __table_args__ = (
        Index("ix_aviso_talla_pendientes", "variante_id",
              postgresql_where=text("notificado_en IS NULL")),
        Index("uq_aviso_talla_pendiente", "cliente_id", "variante_id", unique=True,
              postgresql_where=text("notificado_en IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id", ondelete="CASCADE")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    notificado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notificacion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("notificacion.id", ondelete="SET NULL")
    )
