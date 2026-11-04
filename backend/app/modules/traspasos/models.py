"""
P15 - Traspasos entre sucursales / CU-33, CU-34 y CU-35  |  capa: modelo

3ra presentación del 2do parcial. Una sola tabla: el pedido de mercadería de
una sucursal a otra, con su seguimiento (RF-39 a RF-42).

POR QUÉ UNA TABLA Y NO SOLO LOS MOVIMIENTOS
-------------------------------------------
La transferencia del 1er parcial (CU-15) era instantánea: dos filas de
`movimiento_inventario` en la misma transacción. Un traspaso no: se pide, se
aprueba, se despacha y días después se recibe. Entre el envío y la recepción
las unidades ya salieron del origen y todavía no entraron al destino (RN-09),
y eso no se puede leer en los movimientos sin una fila que diga «está en
camino».

Los movimientos se siguen escribiendo igual, de tipo TRANSFERENCIA, con el
mismo invariante de siempre (el saldo es la suma de los movimientos). El
traspaso apunta a ellos —la salida al enviar, la entrada al recibir— y no al
revés, para no tocar `movimiento_inventario`, que es del inventario.

TIPO
----
  PEDIDO     el encargado del destino lo pide (CU-33); el origen lo aprueba
  ORDEN      el administrador lo ordena sin pedido previo (RF-40): nace APROBADO
  SUGERIDO   una ORDEN que salió de los traspasos sugeridos (CU-35)

ESTADOS (RF-41)
---------------
  SOLICITADO -> APROBADO -> ENVIADO -> RECIBIDO
       \\            \\
        RECHAZADO    RECHAZADO

Un traspaso ENVIADO ya no se rechaza: la mercadería está en el camión. Si
llega de menos, se corrige con un ajuste del inventario (CU-21).
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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Auditoria, Base, DeEmpresa

TIPOS_TRASPASO = ("PEDIDO", "ORDEN", "SUGERIDO")
ESTADOS_TRASPASO = ("SOLICITADO", "APROBADO", "ENVIADO", "RECIBIDO", "RECHAZADO")

#: Los estados en los que el traspaso todavía no terminó.
ESTADOS_ABIERTOS = ("SOLICITADO", "APROBADO", "ENVIADO")


def _en(valores: tuple[str, ...]) -> str:
    return "('" + "', '".join(valores) + "')"


class Traspaso(DeEmpresa, Auditoria, Base):
    __tablename__ = "traspaso"
    __table_args__ = (
        CheckConstraint(f"tipo IN {_en(TIPOS_TRASPASO)}", name="tipo"),
        CheckConstraint(f"estado IN {_en(ESTADOS_TRASPASO)}", name="estado"),
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint(
            "sucursal_origen_id <> sucursal_destino_id", name="origen_distinto_destino"
        ),
        # El motivo del rechazo existe si y solo si se rechazó.
        CheckConstraint(
            "(estado = 'RECHAZADO') = (motivo_rechazo IS NOT NULL)",
            name="motivo_rechazo_segun_estado",
        ),
        # La salida existe desde que se envía, y la entrada desde que se recibe.
        CheckConstraint(
            "(estado IN ('ENVIADO', 'RECIBIDO')) = (movimiento_salida_id IS NOT NULL)",
            name="salida_segun_estado",
        ),
        CheckConstraint(
            "(estado = 'RECIBIDO') = (movimiento_entrada_id IS NOT NULL)",
            name="entrada_segun_estado",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(12), index=True)

    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id"), index=True
    )
    sucursal_origen_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    sucursal_destino_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    #: Lo pedido. Al aprobar, el origen puede bajarla si no le alcanza; se
    #: guarda lo pedido aparte para que el seguimiento muestre los dos.
    cantidad: Mapped[int] = mapped_column(Integer)
    cantidad_solicitada: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str | None] = mapped_column(String(200))

    solicitado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    aprobado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enviado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recibido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    recibido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rechazado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    rechazado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_rechazo: Mapped[str | None] = mapped_column(String(200))

    movimiento_salida_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("movimiento_inventario.id")
    )
    movimiento_entrada_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("movimiento_inventario.id")
    )
