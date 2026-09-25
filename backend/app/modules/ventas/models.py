"""
P7 - Ventas y Punto de Venta  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Realizar pedido (la parte de pago vive en el modulo pagos)
  CU-29 Consultar historial de compras
  CU-30 Abrir y cerrar caja
  CU-31 Registrar venta presencial
  CU-32 Registrar devolucion

CU-26 NO ESTA ACA
-----------------
`Carrito` y `CarritoDetalle` viven en `carrito_models.py`, y sus tablas nacieron
en la `0009_ciclo3_carrito`. Es el patron de archivos propios dentro del paquete
ajeno que ya usan `imagenes_*` en catalogo y `consolidado_*` en inventario.

EL PRECIO SE CONGELA ACA Y NO ANTES
-----------------------------------
`carrito_detalle` no guarda precio: lo lee en vivo contra `variante_producto`.
`DetalleVenta.precio_unitario` es el primer lugar donde el precio queda fijo, y
es el correcto: el carrito es una intencion y la venta es un compromiso. La
decision, con sus cuatro razones, esta en la seccion 3 de
docs/entregas/ciclo-3/00-esquema-de-ventas-y-pagos.md.

Corolario para CU-27: entre que el cliente mira el carrito y confirma el pedido
el precio pudo cambiar. CU-27 lo AVISA en vez de cobrar callado.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Los dos canales de D2. Una sola Venta los cubre a los dos: no hay tabla
# `pedido` aparte, porque duplicarla obligaria a copiar los detalles de una a
# otra y a descontar inventario en dos lugares.
CANALES_VENTA = ("DIGITAL", "PRESENCIAL")

# PENDIENTE_PAGO -> PAGADA -> ENTREGADA, y CANCELADA desde las dos primeras.
# La venta PRESENCIAL nace directamente en PAGADA: no pasa por la pasarela.
ESTADOS_VENTA = ("PENDIENTE_PAGO", "PAGADA", "ENTREGADA", "CANCELADA")

#: Como se puede cobrar en el mostrador (CU-30, CU-31).
#:
#: `QR` esta porque en Bolivia el pago con codigo QR bancario es corriente y
#: **no es efectivo**: no entra al cajon y no puede sumar al arqueo. Meterlo
#: dentro de EFECTIVO descuadraria el turno por cada uno.
METODOS_PAGO = ("EFECTIVO", "TARJETA", "QR")

#: Lo que `venta.metodo_pago` puede contener, que no es lo mismo (0020).
#:
#: `CAMBIO` no es una forma de cobrar y por eso NO esta en `METODOS_PAGO`: el
#: cajero no puede elegirlo, no aparece en la pantalla de venta y nunca vale
#: para `devolucion.metodo_diferencia`. Lo escribe solo CU-32 en la venta que
#: nace de un cambio de prenda.
#:
#: POR QUE ESA VENTA NECESITA UN METODO PROPIO
#: -------------------------------------------
#: La venta de un cambio vale la prenda que sale ---Bs 250---, no lo que entro
#: al cajon ---Bs 50---. Si llevara `EFECTIVO`, el arqueo de CU-30 la sumaria
#: entera y el turno cerraria con un sobrante de 200 que nadie puede contar.
#:
#: Con un metodo propio, el filtro que ya existia ---`metodo_pago = EFECTIVO`---
#: la deja fuera sin que haga falta ninguna condicion nueva, y el desglose del
#: cierre la muestra en su propia linea en vez de esconderla. Lo que si entro
#: al cajon se cuenta aparte: `devolucion.diferencia`.
METODOS_VENTA = METODOS_PAGO + ("CAMBIO",)

#: Los dos flujos de CU-32 (0020).
#:
#: `DEVOLUCION` la prenda vuelve y la plata se reintegra.
#: `CAMBIO`     la prenda vuelve, otra sale, y solo se mueve la diferencia.
#:
#: Es una columna y no dos tablas porque las dos escriben exactamente lo mismo
#: --- una cabecera, sus lineas y un reingreso al inventario --- y el cambio
#: **ademas** apunta a una venta. Ver la 0020.
TIPOS_DEVOLUCION = ("DEVOLUCION", "CAMBIO")

# Solo aplica al canal DIGITAL. En PRESENCIAL el cliente ya se lleva la prenda.
MODALIDADES_ENTREGA = ("RETIRO", "ENVIO")

TIPOS_COMPROBANTE = ("RECIBO", "FACTURA")


class Caja(Base):
    """Un punto de cobro fisico dentro de una sucursal (CU-30).

    No usa el mixin de Auditoria: es una tabla de catalogo, se da de alta una
    vez y se desactiva con `activa`. No se borra, porque los turnos viejos la
    siguen nombrando.
    """

    __tablename__ = "caja"
    __table_args__ = (
        # Dos cajas con el mismo nombre en la misma sucursal harian imposible
        # saber en cual se cobro. Entre sucursales si se repite: casi todas
        # tienen su "Caja 1".
        UniqueConstraint("sucursal_id", "nombre", name="uq_caja_sucursal_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(50))
    activa: Mapped[bool] = mapped_column(Boolean, server_default="true")

    turnos: Mapped[list["TurnoCaja"]] = relationship(back_populates="caja")


class TurnoCaja(Base):
    """Una jornada de cobro: se abre con un monto y se cierra con un arqueo.

    `monto_esperado` lo calcula el sistema al cerrar -apertura mas lo cobrado en
    efectivo menos las devoluciones-; `monto_cierre` lo cuenta la persona. La
    diferencia entre los dos ES el arqueo, y por eso se guardan los dos y no el
    resultado: un descuadre sin los dos numeros no se puede auditar.

    No usa Auditoria porque sus dos fechas no son de edicion de la fila:
    `abierto_en` y `cerrado_en` son el hecho que la tabla registra.
    """

    __tablename__ = "turno_caja"
    __table_args__ = (
        CheckConstraint(
            "cerrado_en IS NULL OR cerrado_en >= abierto_en", name="cierre_posterior"
        ),
        # Cerrar exige haber contado. Un turno cerrado sin monto es un arqueo
        # que nadie hizo.
        CheckConstraint(
            "cerrado_en IS NULL OR monto_cierre IS NOT NULL", name="cierre_con_monto"
        ),
        # UN SOLO TURNO ABIERTO POR CAJA. Es un indice unico PARCIAL y no un
        # UniqueConstraint porque el UNIQUE normal prohibiria tambien los turnos
        # ya cerrados, que son muchos y legitimos. Dos turnos abiertos a la vez
        # hacen que el arqueo no cierre nunca: no se sabria a cual imputar lo
        # cobrado.
        Index(
            "ix_turno_caja_abierto",
            "caja_id",
            unique=True,
            postgresql_where=text("cerrado_en IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    caja_id: Mapped[int] = mapped_column(Integer, ForeignKey("caja.id"), index=True)
    #: El Cajero que lo abrio.
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id"), index=True
    )
    abierto_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    monto_apertura: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    #: Lo que la persona conto al cerrar. Nulo mientras el turno sigue abierto.
    monto_cierre: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    #: Lo que el sistema dice que deberia haber. Nulo hasta cerrar.
    monto_esperado: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    caja: Mapped[Caja] = relationship(back_populates="turnos")


class Venta(Base):
    """La tabla central de P7. UN concepto para los dos canales (D2).

    No hay tabla `pedido`: CU-27 crea una Venta en PENDIENTE_PAGO y la pasarela
    la lleva a PAGADA. CU-31 crea una Venta PRESENCIAL que nace PAGADA.

    `subtotal`, `descuento` y `total` se guardan calculados y no se recalculan
    al leer, por la misma razon que `DetalleVenta.precio_unitario`: una venta
    de marzo tiene que seguir sumando lo que sumo en marzo aunque los precios y
    las promociones hayan cambiado. El CHECK garantiza que los tres sean
    coherentes entre si en la base, no solo en el servicio.
    """

    __tablename__ = "venta"
    __table_args__ = (
        CheckConstraint("canal IN ('" + "', '".join(CANALES_VENTA) + "')", name="canal"),
        CheckConstraint(
            "estado IN ('" + "', '".join(ESTADOS_VENTA) + "')", name="estado"
        ),
        CheckConstraint(
            "modalidad_entrega IS NULL OR modalidad_entrega IN ('"
            + "', '".join(MODALIDADES_ENTREGA)
            + "')",
            name="modalidad",
        ),
        CheckConstraint("total = subtotal - descuento", name="total_coherente"),
        CheckConstraint(
            "metodo_pago IS NULL OR metodo_pago IN ('"
            + "', '".join(METODOS_VENTA)
            + "')",
            name="metodo_pago",
        ),
        # Una presencial se cobra en el mostrador y ahi el metodo es nuestro;
        # una digital la cobra la pasarela y el metodo lo sabe Stripe. Sin
        # esto, el arqueo de CU-30 no puede distinguir el efectivo.
        CheckConstraint(
            "(canal = 'PRESENCIAL' AND metodo_pago IS NOT NULL)"
            " OR (canal = 'DIGITAL' AND metodo_pago IS NULL)",
            name="metodo_segun_canal",
        ),
        CheckConstraint("subtotal >= 0 AND descuento >= 0", name="montos_no_negativos"),
        # Una venta presencial se cobra en una caja abierta; una digital no
        # pasa por ninguna. Sin esto, un pedido web podria quedar colgado de un
        # turno y descuadrar el arqueo de una sucursal que no lo cobro.
        CheckConstraint(
            "(canal = 'PRESENCIAL' AND turno_caja_id IS NOT NULL)"
            " OR (canal = 'DIGITAL' AND turno_caja_id IS NULL)",
            name="turno_segun_canal",
        ),
        # La modalidad de entrega es de la venta digital; en presencial el
        # cliente ya se lleva la prenda.
        CheckConstraint(
            "(canal = 'DIGITAL' AND modalidad_entrega IS NOT NULL)"
            " OR (canal = 'PRESENCIAL' AND modalidad_entrega IS NULL)",
            name="modalidad_segun_canal",
        ),
        # Si es ENVIO hay que saber adonde, y si no lo es no hay direccion que
        # guardar. Las dos mitades en una sola restriccion.
        #
        # El IS NOT DISTINCT FROM va en la comparacion con 'ENVIO', NO entre
        # las dos mitades. En una venta PRESENCIAL `modalidad_entrega` es NULL,
        # y `NULL = 'ENVIO'` da NULL, no falso: escrito al reves, el CHECK
        # rechazaba TODA venta presencial. Lo atrapo el humo de la 0006.
        CheckConstraint(
            "(modalidad_entrega IS NOT DISTINCT FROM 'ENVIO')"
            " = (direccion_id IS NOT NULL)",
            name="direccion_si_envio",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    #: Legible para el cliente; es lo que dice el comprobante y lo que la
    #: persona lee por telefono. Unico, y NO es la clave primaria: el numero
    #: que se muestra y el que referencian las otras tablas son cosas distintas.
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    canal: Mapped[str] = mapped_column(String(12), index=True)
    estado: Mapped[str] = mapped_column(String(20), index=True)

    #: Nulo a proposito: la venta presencial puede ser anonima. Quien entra,
    #: paga y se va no tiene por que dejar sus datos.
    cliente_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cliente.id"), index=True
    )
    #: La sucursal que abastece. En PRESENCIAL, donde se vendio.
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    turno_caja_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("turno_caja.id"), index=True
    )

    #: El puente de D2: el Encargado atiende una reserva (CU-24) y esa misma
    #: reserva se cobra como venta presencial, sin transformar datos. UNICO,
    #: porque una reserva no se puede cobrar dos veces.
    reserva_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reserva.id"), unique=True
    )

    modalidad_entrega: Mapped[str | None] = mapped_column(String(10))
    direccion_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("direccion_cliente.id")
    )

    #: EFECTIVO, TARJETA o QR. Solo en las presenciales. Es lo que permite que
    #: el arqueo de CU-30 sume al esperado unicamente lo que entro al cajon.
    metodo_pago: Mapped[str | None] = mapped_column(String(20))

    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    #: Lo que aportan las promociones de CU-12. Cero mientras la 0007 no exista.
    descuento: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    #: Indexada porque TODO el tablero de CU-36 corta por fecha: ventas del dia,
    #: del mes y ticket promedio del periodo son tres consultas sobre esto.
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    detalles: Mapped[list["DetalleVenta"]] = relationship(
        back_populates="venta", cascade="all, delete-orphan", passive_deletes=True
    )
    comprobante: Mapped["Comprobante | None"] = relationship(back_populates="venta")


class DetalleVenta(Base):
    """Una variante vendida, con su precio CONGELADO.

    INMUTABLE, como MovimientoInventario (D4): una correccion es una devolucion
    (CU-32), no un UPDATE. Por eso no lleva `actualizado_en`.

    `precio_unitario` es una copia, no una lectura: si se leyera en vivo contra
    `variante_producto`, el historial de compras de CU-29 y el ticket promedio
    de CU-36 cambiarian solos cada vez que la tienda toca un precio, y un
    comprobante impreso dejaria de coincidir con el sistema.

    `descuento_unitario` esta desde ahora aunque CU-12 no exista: agregarla
    despues obligaria a reescribir las filas ya vendidas para decidir que
    descuento tenian, y la respuesta correcta -ninguno- se pierde si la columna
    no estaba.
    """

    __tablename__ = "detalle_venta"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        CheckConstraint(
            "precio_unitario >= 0 AND descuento_unitario >= 0",
            name="montos_no_negativos",
        ),
        # Regalar no es vender por menos que cero.
        CheckConstraint(
            "descuento_unitario <= precio_unitario", name="descuento_acotado"
        ),
        # Una variante aparece una vez por venta; dos unidades son cantidad 2.
        # Es la misma regla que en reserva_detalle y en carrito_detalle.
        UniqueConstraint("venta_id", "variante_id", name="uq_detalle_venta_venta_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("venta.id", ondelete="CASCADE"), index=True
    )
    #: D1: la unidad de negocio es la variante, nunca el producto.
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id"), index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    descuento_unitario: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), server_default="0"
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    venta: Mapped[Venta] = relationship(back_populates="detalles")


class Comprobante(Base):
    """El recibo o la factura de una venta. Uno por venta, y no se edita.

    `nit_ci` y `razon_social` son nulos en un RECIBO y obligatorios en una
    FACTURA, que es lo que dice el CHECK. Se copian y no se leen del cliente
    porque son los datos que dio AL FACTURAR: si el cliente cambia su NIT
    despues, la factura ya emitida no cambia.
    """

    __tablename__ = "comprobante"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('" + "', '".join(TIPOS_COMPROBANTE) + "')", name="tipo"
        ),
        CheckConstraint(
            "tipo = 'RECIBO' OR (nit_ci IS NOT NULL AND razon_social IS NOT NULL)",
            name="factura_con_datos",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    #: UNICO: una venta no tiene dos comprobantes. Reimprimir no es reemitir.
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("venta.id"), unique=True
    )
    tipo: Mapped[str] = mapped_column(String(10))
    numero: Mapped[str] = mapped_column(String(20), unique=True)
    nit_ci: Mapped[str | None] = mapped_column(String(20))
    razon_social: Mapped[str | None] = mapped_column(String(120))
    emitido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    venta: Mapped[Venta] = relationship(back_populates="comprobante")


class Devolucion(Base):
    """Una venta que vuelve, entera o en parte (CU-32).

    INMUTABLE, sin `actualizado_en`: si la devolucion estaba mal, se corrige con
    otro movimiento, no reescribiendo esta.

    Cuelga de un `turno_caja` porque el dinero sale de una caja concreta, y sin
    eso el arqueo de CU-30 no cerraria: `monto_esperado` resta justamente esto.

    LOS DOS FLUJOS VIVEN EN ESTA MISMA TABLA (0020)
    ------------------------------------------------
    Un CAMBIO es esto mismo y ademas una venta: la prenda vieja vuelve por
    `detalle_devolucion` y la nueva sale por la `venta` a la que apunta
    `venta_cambio_id`. Lo unico que lo distingue de una devolucion pura es
    **por donde se mueve la plata**, y eso son dos columnas, no dos tablas.
    """

    __tablename__ = "devolucion"
    __table_args__ = (
        CheckConstraint("monto >= 0", name="monto_no_negativo"),
        CheckConstraint(
            "tipo IN ('" + "', '".join(TIPOS_DEVOLUCION) + "')", name="tipo"
        ),
        # Un cambio sin venta nueva no es un cambio; una devolucion con venta
        # nueva es un cambio mal etiquetado.
        CheckConstraint(
            "(tipo = 'CAMBIO') = (venta_cambio_id IS NOT NULL)",
            name="cambio_tiene_venta",
        ),
        # En un cambio el valor de la prenda vieja se ACREDITA contra la nueva:
        # no sale un billete del cajon por ella. Si `monto` pudiera valer algo,
        # el arqueo lo restaria ademas de la diferencia y contaria dos veces.
        CheckConstraint(
            "tipo = 'DEVOLUCION' OR monto = 0", name="cambio_no_saca_del_cajon"
        ),
        CheckConstraint(
            "tipo = 'CAMBIO' OR (diferencia = 0 AND metodo_diferencia IS NULL)",
            name="devolucion_sin_diferencia",
        ),
        CheckConstraint(
            "(diferencia <> 0) = (metodo_diferencia IS NOT NULL)",
            name="metodo_si_hay_diferencia",
        ),
        CheckConstraint(
            "metodo_diferencia IS NULL OR metodo_diferencia IN ('"
            + "', '".join(METODOS_PAGO)
            + "')",
            name="metodo_diferencia",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("venta.id"), index=True
    )
    #: Donde se proceso. Es lo que ata la plata que sale a un arqueo.
    turno_caja_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("turno_caja.id"), index=True
    )
    #: DEVOLUCION o CAMBIO. Ver `TIPOS_DEVOLUCION`.
    tipo: Mapped[str] = mapped_column(String(12), server_default="DEVOLUCION")
    #: La venta que se llevo el cliente a cambio. Solo en los CAMBIO.
    #:
    #: UNICA a proposito: dos devoluciones que reclamaran la misma venta nueva
    #: harian que el arqueo la excluyera dos veces. El indice que trae de
    #: regalo es el que usa ese `NOT EXISTS`.
    venta_cambio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("venta.id"), unique=True
    )
    motivo: Mapped[str] = mapped_column(String(200))
    #: Lo que sale del cajon por la prenda devuelta. Cero en todo CAMBIO.
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    #: `total de lo nuevo - valor de lo devuelto`, CON SIGNO. Cero fuera de un
    #: cambio. Positiva: paga el cliente. Negativa: devuelve la tienda.
    diferencia: Mapped[Decimal] = mapped_column(Numeric(10, 2), server_default="0")
    #: Como se salda la diferencia. NULL si no hay diferencia que saldar.
    metodo_diferencia: Mapped[str | None] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    detalles: Mapped[list["DetalleDevolucion"]] = relationship(
        back_populates="devolucion", cascade="all, delete-orphan", passive_deletes=True
    )


class DetalleDevolucion(Base):
    """Que variante vuelve y cuantas unidades.

    Devolver REINGRESA al inventario con un MovimientoInventario de tipo
    DEVOLUCION, que ya existe en TIPOS_MOVIMIENTO desde la 0003. Esta tabla dice
    que volvio; el movimiento dice adonde.
    """

    __tablename__ = "detalle_devolucion"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        UniqueConstraint(
            "devolucion_id", "variante_id", name="uq_detalle_devolucion_devolucion_id"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    devolucion_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("devolucion.id", ondelete="CASCADE"), index=True
    )
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id"), index=True
    )
    cantidad: Mapped[int] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    devolucion: Mapped[Devolucion] = relationship(back_populates="detalles")
