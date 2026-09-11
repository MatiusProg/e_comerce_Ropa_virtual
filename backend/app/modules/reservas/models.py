"""
P6 - Reservas  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Duenio de las tablas `reserva` y `reserva_detalle` durante el Ciclo 2. Los
nombres y tipos son los acordados en la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md.

Igual que en P4, la clave foranea a `variante_producto` se declara por nombre y
sin `relationship()`: esa tabla es de Karen (costura C2).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base

#: Estados de una reserva. Es el objeto con ciclo de vida rico del Ciclo 2, y
#: el que sostiene el diagrama de estado del documento —la seccion 5.3 del plan
#: dice que en el Ciclo 1 no habia ninguno que lo justificara—.
#:
#: Las transiciones validas son:
#:
#:     PENDIENTE --> PREPARADA --> ATENDIDA      (CU-22, CU-24)
#:     PENDIENTE --> CANCELADA                   (CU-23, la cancela el cliente)
#:     PREPARADA --> CANCELADA                   (CU-23)
#:     PENDIENTE --> EXPIRADA                    (CU-25, vencio la franja)
#:     PREPARADA --> EXPIRADA                    (CU-25)
#:
#: ATENDIDA, CANCELADA y EXPIRADA son finales. Solo las tres primeras
#: transiciones las dispara una persona; las dos ultimas, la tarea programada.
#:
#: Salir de PENDIENTE o PREPARADA hacia CANCELADA o EXPIRADA devuelve el stock
#: de `cantidad_reservada` a `cantidad_disponible` y deja un movimiento de tipo
#: LIBERACION. Llegar a ATENDIDA lo descuenta de la reservada sin devolverlo.
ESTADOS_RESERVA = ("PENDIENTE", "PREPARADA", "ATENDIDA", "CANCELADA", "EXPIRADA")

#: Resultado de probarse una prenda, que el Encargado registra en CU-24. Queda
#: nulo mientras la reserva no se atienda.
RESULTADOS_PRUEBA = ("LLEVA", "NO_LLEVA")


class Reserva(Auditoria, Base):
    """Apartado de prendas para probarselas en una sucursal.

    La franja horaria es lo que la hace expirar: CU-25 busca las que siguen en
    PENDIENTE o PREPARADA con `franja_fin` ya pasada y les devuelve el stock.
    Por eso `franja_fin` va indexada junto con el estado.

    Las dos fechas son `timestamptz`. Sin zona horaria, una reserva creada a las
    23:00 en Bolivia y comparada contra un `now()` en UTC expiraria cuatro horas
    antes de lo que dice la pantalla.
    """

    __tablename__ = "reserva"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('" + "', '".join(ESTADOS_RESERVA) + "')", name="estado"
        ),
        CheckConstraint("franja_fin > franja_inicio", name="franja"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id"), index=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    franja_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    franja_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    estado: Mapped[str] = mapped_column(String(10), index=True)

    #: Lo escribe CU-23 cuando la cancela el cliente y CU-24 cuando el
    #: Encargado la cierra. Nulo mientras la reserva sigue viva.
    observacion: Mapped[str | None] = mapped_column(String(200))

    detalles: Mapped[list["DetalleReserva"]] = relationship(
        back_populates="reserva", cascade="all, delete-orphan"
    )


class DetalleReserva(Auditoria, Base):
    """Una variante y su cantidad dentro de una reserva.

    La clase se llama `DetalleReserva` porque asi la nombra el modelo de
    analisis (P6 en docs/04-analisis-arquitectura.md) y asi aparece en los
    diagramas; la **tabla** se llama `reserva_detalle` porque asi quedo fijada
    en la seccion 6.4 del documento de organizacion. Se respetan las dos.
    """

    __tablename__ = "reserva_detalle"
    __table_args__ = (
        # La misma variante no se repite dentro de una reserva: si el cliente
        # quiere dos unidades, sube la cantidad.
        UniqueConstraint("reserva_id", "variante_id", name="uq_reserva_detalle_reserva_variante"),
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint(
            "resultado_prueba IS NULL OR resultado_prueba IN ('"
            + "', '".join(RESULTADOS_PRUEBA)
            + "')",
            name="resultado",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    reserva_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reserva.id", ondelete="CASCADE"), index=True
    )
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id"), index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    resultado_prueba: Mapped[str | None] = mapped_column(String(10))

    reserva: Mapped["Reserva"] = relationship(back_populates="detalles")
