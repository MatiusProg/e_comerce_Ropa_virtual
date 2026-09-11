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

    POR QUE NO HAY TABLA `ingreso` (CU-13)
    --------------------------------------
    Un ingreso de mercaderia es una cabecera -proveedor, sucursal, remito- con
    varias lineas, y la primera intencion es modelarlo con dos tablas. No se
    hizo: la seccion 3 del documento de organizacion congelo el ciclo en ocho
    tablas nuevas y una cabecera de ingreso seria la novena, con dos duenios
    discutiendo el mismo esquema a mitad de ciclo.

    En su lugar el ingreso **se reconstruye** desde estas filas. Las lineas de
    un mismo ingreso comparten `proveedor_id`, `referencia`, `usuario_id` y
    `creado_en`, y ese ultimo dato las agrupa sin ambiguedad aunque no se haya
    cargado un remito: `now()` en PostgreSQL devuelve el instante de la
    **transaccion**, no el de cada fila, y las lineas de un ingreso se escriben
    en una sola transaccion. Dos ingresos distintos son dos transacciones y
    llevan dos marcas de tiempo distintas.

    El precio de la decision es que no se puede anular «el ingreso» de un tiro,
    solo corregirlo con un `AJUSTE` -que es como se corrige cualquier otra cosa
    en esta tabla, por D4-. Si en el Ciclo 3 la recepcion de mercaderia crece
    -estados, recepcion parcial, costo por linea-, ahi si merece su propia
    cabecera; hoy no la necesita.
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
    #: Por que se movio. En CU-15 es obligatorio -es la trazabilidad que pide
    #: el RF28-; en CU-13 lo compone el servicio con el nombre del proveedor.
    motivo: Mapped[str | None] = mapped_column(String(200))

    # Solo lo llena CU-13: quien mando la mercaderia. Nulo en todos los demas
    # tipos, porque un ajuste por conteo o una reserva no vienen de nadie.
    #
    # Es el unico lugar donde queda registrada la procedencia de una prenda, y
    # sin el la relacion "producto <- proveedor" que exige el RF06 se quedaria
    # solo en `producto.proveedor_id`, que es de quien PROVEE el modelo y no de
    # quien mando ESTE lote. No son lo mismo: un mismo producto puede llegar de
    # dos proveedores distintos.
    proveedor_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("proveedor.id"), index=True
    )
    #: Numero de remito, guia o factura del ingreso. Es del papel que llego con
    #: la mercaderia, asi que no se valida su forma ni se exige unico: dos
    #: proveedores pueden numerar igual.
    referencia: Mapped[str | None] = mapped_column(String(40))

    # Queda nulo cuando el movimiento lo genera el sistema y no una persona:
    # la expiracion de reservas de CU-25 es una tarea programada, sin usuario.
    usuario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id"), index=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    existencia: Mapped["Existencia"] = relationship(back_populates="movimientos")
