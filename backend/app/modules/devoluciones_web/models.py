"""
P15 - Devoluciones por la web / CU-24 y CU-25  |  capa: modelo

2do parcial. El cliente pide por la web el cambio o la devolución de prendas de
un pedido ENTREGADO, dentro de la ventana de la empresa (CU-23); el encargado
de la sucursal la atiende (CU-25).

POR QUÉ UNA SOLICITUD Y NO UNA DEVOLUCIÓN DIRECTA
-------------------------------------------------
En caja (CU-22) la prenda está sobre el mostrador y el cliente presente: el
trámite se hace y se cierra en el acto. Por la web, lo que existe al principio
es un PEDIDO del cliente: la prenda todavía no volvió y nadie la revisó. La
`devolucion` (la nota) recién nace cuando el encargado recibe la prenda; hasta
entonces lo que hay es esta solicitud, con su estado.

    PENDIENTE  -> APROBADA -> COMPLETADA   (CU-25: recibió la prenda)
    PENDIENTE  -> RECHAZADA                (CU-25, con el motivo)
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, DeEmpresa

TIPOS_SOLICITUD = ("DEVOLUCION", "CAMBIO")
ESTADOS_SOLICITUD = ("PENDIENTE", "APROBADA", "RECHAZADA", "COMPLETADA")
#: Las que todavía reservan unidades del pedido: no se pueden pedir dos veces.
ESTADOS_ABIERTOS = ("PENDIENTE", "APROBADA")


class SolicitudDevolucion(DeEmpresa, Base):
    """Un pedido de cambio o devolución hecho por el cliente desde la web."""

    __tablename__ = "solicitud_devolucion"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('" + "', '".join(TIPOS_SOLICITUD) + "')", name="tipo"
        ),
        CheckConstraint(
            "estado IN ('" + "', '".join(ESTADOS_SOLICITUD) + "')", name="estado"
        ),
        # RF-36: el rechazo dice por qué.
        CheckConstraint(
            "estado <> 'RECHAZADA' OR respuesta IS NOT NULL", name="rechazo_con_motivo"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("venta.id"), index=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id"), index=True
    )
    #: La del pedido: es la que la atiende (CU-25).
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(12))
    estado: Mapped[str] = mapped_column(String(12), server_default="PENDIENTE", index=True)
    motivo: Mapped[str] = mapped_column(String(300))

    # --- CU-25 -------------------------------------------------------------
    respuesta: Mapped[str | None] = mapped_column(String(300))
    atendida_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    atendida_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: La nota de devolución que la cerró (CU-25).
    devolucion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("devolucion.id"), unique=True
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    lineas: Mapped[list["LineaSolicitudDevolucion"]] = relationship(
        back_populates="solicitud", cascade="all, delete-orphan", passive_deletes=True
    )


class LineaSolicitudDevolucion(DeEmpresa, Base):
    """Una prenda que vuelve y, en un cambio, la que el cliente quiere a cambio."""

    __tablename__ = "linea_solicitud_devolucion"
    __table_args__ = (
        UniqueConstraint(
            "solicitud_id", "variante_id", name="uq_linea_solicitud_devolucion_variante"
        ),
        CheckConstraint("cantidad > 0", name="cantidad"),
        CheckConstraint(
            "variante_nueva_id IS NULL OR variante_nueva_id <> variante_id",
            name="cambio_por_otra",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    solicitud_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("solicitud_devolucion.id", ondelete="CASCADE"), index=True
    )
    variante_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("variante_producto.id"))
    cantidad: Mapped[int] = mapped_column(Integer)
    #: Solo en un CAMBIO: la misma prenda en otra talla o color.
    variante_nueva_id: Mapped[int | None] = mapped_column(
        # Nombre explícito: el de la convención pasa de los 63 caracteres.
        BigInteger,
        ForeignKey("variante_producto.id", name="fk_linea_solicitud_devolucion_variante_nueva_id"),
    )

    solicitud: Mapped[SolicitudDevolucion] = relationship(back_populates="lineas")
