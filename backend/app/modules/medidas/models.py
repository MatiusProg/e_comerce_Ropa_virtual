"""CU-21 · Medidas del cuerpo del cliente y de la prenda por talla.

Las dos tablas de la migracion `0011_ciclo3_medidas`. Ahi esta el porque de
cada decision; aca solo la declaracion.

LO QUE HAY QUE TENER CLARO AL LEER ESTO
----------------------------------------
`MedidaCliente` es un CUERPO. `MedidaTalla` es una PRENDA, con la holgura ya
adentro. Se confunden facil porque las dos tienen `busto_cm`, y confundirlas
hace que el vestidor dibuje una prenda del tamano exacto del cuerpo --- sin
aire por ningun lado, que es como se veria una prenda dos tallas mas chica.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Auditoria, Base


class MedidaCliente(Auditoria, Base):
    """Las medidas del cuerpo de un cliente. Una fila por cliente, sin historial."""

    __tablename__ = "medida_cliente"
    __table_args__ = (
        UniqueConstraint("cliente_id", name="uq_medida_cliente_cliente_id"),
        # Los mismos rangos que la migracion. Repetirlos aca no es redundancia
        # inutil: es lo que hace que `alembic check` avise si alguien afloja uno
        # de los dos lados y se separan.
        CheckConstraint("busto_cm BETWEEN 50 AND 200", name="busto"),
        CheckConstraint("cintura_cm BETWEEN 40 AND 200", name="cintura"),
        CheckConstraint("cadera_cm BETWEEN 50 AND 200", name="cadera"),
        CheckConstraint(
            "altura_cm IS NULL OR altura_cm BETWEEN 100 AND 230", name="altura"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE"), unique=True
    )
    busto_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    cintura_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    cadera_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    altura_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))

    # SIN `relationship` a Cliente a proposito. Declararla obliga a que la clase
    # Cliente este registrada en el mismo mapeador antes de que este modulo se
    # importe, y como `alembic/env.py` importa los modulos en orden, la
    # resolucion del nombre falla con un KeyError que no dice nada util. Nada de
    # lo que hace CU-21 navega de una medida a su cliente: se consulta siempre
    # al reves, por `cliente_id`.


class MedidaTalla(Auditoria, Base):
    """Cuanto mide LA PRENDA de un producto en una talla, con holgura incluida."""

    __tablename__ = "medida_talla"
    __table_args__ = (
        UniqueConstraint(
            "producto_id", "talla_id", name="uq_medida_talla_producto_talla"
        ),
        CheckConstraint("busto_cm BETWEEN 30 AND 250", name="busto"),
        CheckConstraint("cintura_cm BETWEEN 30 AND 250", name="cintura"),
        CheckConstraint("cadera_cm BETWEEN 30 AND 250", name="cadera"),
        CheckConstraint("largo_cm BETWEEN 20 AND 200", name="largo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("producto.id", ondelete="CASCADE")
    )
    talla_id: Mapped[int] = mapped_column(ForeignKey("talla.id"))
    busto_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    cintura_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    cadera_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    largo_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
