"""
P4 - Inventario  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal

Duenio de las tablas `existencia` y `movimiento_inventario` durante el Ciclo 2
(seccion 3 de docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md). Los
nombres y tipos son los acordados en la seccion 6.4 de ese mismo documento.

NOTA SOBRE LAS CLAVES FORANEAS A `variante_producto`
----------------------------------------------------
`variante_producto` es de Karen y nace en la migracion 0002. Aqui se la
referencia **por nombre de tabla y nunca con `relationship()`**: importar sus
clases acoplaria los dos modulos y obligaria a que las dos migraciones entren
en orden para poder siquiera importar este archivo. La resolucion de una clave
foranea declarada por cadena es perezosa, asi que este modulo se importa aunque
la tabla todavia no exista. Es la costura C2 del documento del ciclo.
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
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base

#: Tipos de movimiento que registra CU-15, tomados de la descripcion de P4 en
#: docs/04-analisis-arquitectura.md.
#:
#: Se guardan como texto con un CHECK y no como un ENUM nativo de PostgreSQL a
#: proposito: agregarle un valor a un ENUM nativo obliga a un ALTER TYPE que no
#: se puede revertir en el `downgrade`, y las migraciones de este ciclo se
#: escriben a mano (seccion 4 del documento de organizacion). Un CHECK se
#: cambia y se deshace con una linea.
TIPOS_MOVIMIENTO = (
    "INGRESO",  # llega mercaderia del proveedor (CU-13)
    "RESERVA",  # se aparta stock para una reserva (CU-22)
    "LIBERACION",  # la reserva se cancela o expira (CU-23, CU-25)
    "VENTA",  # sale por venta presencial o pedido (Ciclo 3)
    "DEVOLUCION",  # vuelve una prenda vendida (Ciclo 3)
    "TRANSFERENCIA",  # se mueve entre sucursales (CU-15)
    "AJUSTE",  # correccion por conteo fisico (CU-15)
)


class Existencia(Auditoria, Base):
    """Saldo de una variante en una sucursal.

    Conceptualmente es el saldo de sus movimientos (D4 en
    docs/04-analisis-arquitectura.md): se mantiene desnormalizada porque el
    catalogo publico consulta disponibilidad en cada busqueda y sumar los
    movimientos en cada consulta no escala.

    Las dos cantidades van separadas porque significan cosas distintas: lo
    reservado sigue siendo de la tienda pero ya no se puede vender a otro. Una
    reserva mueve unidades de `cantidad_disponible` a `cantidad_reservada`; al
    atenderla se descuentan de la reservada, y al cancelarla o expirarla
    vuelven a la disponible.

    Es la fila sobre la que CU-22 toma el bloqueo `SELECT ... FOR UPDATE` para
    evitar la sobreventa (riesgo R5).
    """

    __tablename__ = "existencia"
    __table_args__ = (
        # Una sola fila por variante y sucursal: sin esto, dos ingresos
        # simultaneos crearian dos saldos paralelos de la misma prenda.
        UniqueConstraint("variante_id", "sucursal_id", name="uq_existencia_variante_sucursal"),
        CheckConstraint("cantidad_disponible >= 0", name="disponible_no_negativa"),
        CheckConstraint("cantidad_reservada >= 0", name="reservada_no_negativa"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id"), index=True
    )
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    cantidad_disponible: Mapped[int] = mapped_column(
        Integer, server_default=text("0")
    )
    cantidad_reservada: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    movimientos: Mapped[list["MovimientoInventario"]] = relationship(
        back_populates="existencia"
    )


class MovimientoInventario(Base):
    """Registro trazable de cada cambio de una existencia.

    **No usa el mixin `Auditoria`**: un movimiento es inmutable por diseno (D4),
    asi que tiene `creado_en` y no tiene `actualizado_en`. Corregir un
    movimiento equivocado se hace con otro movimiento de tipo `AJUSTE`, no
    editando el anterior; es lo que hace que el historial sirva de auditoria.

    **La cantidad lleva signo**: positiva si entra, negativa si sale. No se
    deduce del tipo porque hay dos tipos que van en las dos direcciones —un
    `AJUSTE` por conteo fisico puede sumar o restar, y una `TRANSFERENCIA` es
    salida en una sucursal y entrada en otra—. Con el signo en la cantidad, la
    afirmacion de D4 se vuelve literal y verificable: el saldo de una
    existencia es la **suma** de sus movimientos, y una prueba puede
    comprobarlo.

    Una **transferencia entre sucursales** son dos filas, no una: una negativa
    en la existencia de origen y una positiva en la de destino, las dos de tipo
    `TRANSFERENCIA` y unidas por el texto del motivo. Asi cada fila sigue
    perteneciendo a una sola existencia y el saldo de cada sucursal se
    reconstruye mirando solo sus propios movimientos.
    """

    __tablename__ = "movimiento_inventario"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('" + "', '".join(TIPOS_MOVIMIENTO) + "')", name="tipo"
        ),
        # Un movimiento de cero unidades no es un movimiento. El signo si
        # importa y por eso no se exige que sea positiva.
        CheckConstraint("cantidad <> 0", name="cantidad_no_nula"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    existencia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("existencia.id"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(15))
    #: Con signo: positiva entra, negativa sale.
    cantidad: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str | None] = mapped_column(String(200))

    # Queda nulo cuando el movimiento lo genera el sistema y no una persona:
    # la expiracion de reservas de CU-25 es una tarea programada, sin usuario.
    usuario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id"), index=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    existencia: Mapped["Existencia"] = relationship(back_populates="movimientos")
