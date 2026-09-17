"""
P7 - Ventas y Punto de Venta / CU-26  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3
Caso de uso: CU-26 Gestionar carrito de compras

ARCHIVOS PROPIOS DENTRO DEL PAQUETE
-----------------------------------
`carrito_*.py`, y no `models.py` / `service.py` / `router.py`, que quedan para
los casos de uso de Mateo --- CU-27, CU-29 a CU-32 ---. Es el mismo patron que
ya usan `imagenes_*` y `temporadas_*` dentro de `catalogo/`, y `consolidado_*`
dentro de `inventario/`: dos personas trabajan sobre el mismo paquete sin
tocar los mismos archivos.

Son las DOS PRIMERAS TABLAS PROPIAS DE P7. El paquete existia como esqueleto
desde el arranque del Ciclo 3 con su `models.py` vacio a proposito.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Carrito(Base):
    """El carrito abierto de un cliente. Hay uno solo, y puede no existir.

    NO GUARDA PRECIOS NI TOTALES. Un carrito es una intencion, no un contrato:
    el precio se fija cuando se genera el pedido (CU-27). Guardar una foto del
    precio dejaria al carrito cotizando un valor que la tienda ya no sostiene, y
    el cliente lo descubriria al pagar. El total se calcula al leer, contra
    `variante_producto`.

    NO INMOVILIZA INVENTARIO. Eso lo hace una RESERVA (CU-22), que aparta
    unidades desde que se crea porque el cliente va a ir a buscarlas. Un carrito
    que apartara stock dejaria inventario congelado por cada cliente que
    abandona la compra --- que son casi todos.

    No usa el mixin de Auditoria aunque tenga las dos fechas: `actualizado_en`
    no describe una edicion de la fila sino la ultima vez que el cliente toco su
    carrito, que es lo que permitiria abandonar los viejos mas adelante.
    """

    __tablename__ = "carrito"
    __table_args__ = (
        # Un cliente, un carrito. Es lo que vuelve imposible que dos peticiones
        # simultaneas creen dos carritos y la compra quede partida en dos.
        UniqueConstraint("cliente_id", name="uq_carrito_cliente_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lineas: Mapped[list["CarritoDetalle"]] = relationship(
        back_populates="carrito",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class CarritoDetalle(Base):
    """Una prenda concreta en el carrito, con cuántas unidades.

    Apunta a la VARIANTE y no al producto, como todo lo que es una unidad de
    negocio: es la decision D1. Un carrito con «una blusa» sin talla ni color no
    se puede convertir en pedido.

    Es la diferencia con `favorito`, que apunta al producto porque es una
    intencion anterior a elegir talla y color.
    """

    __tablename__ = "carrito_detalle"
    __table_args__ = (
        # Una variante aparece UNA vez por carrito: agregarla de nuevo suma
        # cantidad. Sin esto el carrito mostraria la misma prenda dos veces y el
        # cliente no sabria cual editar.
        UniqueConstraint("carrito_id", "variante_id", name="uq_carrito_detalle_carrito_id"),
        # Cantidad cero no es una linea: es una linea borrada.
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    carrito_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("carrito.id", ondelete="CASCADE")
    )
    # Sin CASCADE a proposito: una variante que esta en algun carrito no se
    # borra, se desactiva. Si se borrara, la linea desapareceria sin que el
    # cliente entienda por que le falta algo.
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id")
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    carrito: Mapped[Carrito] = relationship(back_populates="lineas")
