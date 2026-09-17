"""
P8 - Pagos  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Iniciar el pago electronico contra la pasarela
  CU-28 Confirmar pago del pedido (webhook firmado e idempotente)

POR QUE ESTAS DOS TABLAS NACEN EN LA 0006 Y NO EN UNA PROPIA
------------------------------------------------------------
Los identificadores reservados en la seccion 4 de
docs/entregas/ciclo-2/04-respuesta-de-karen.md solo nombran `ventas` y
`promociones`: P8 no tiene numero propio. Y una venta digital sin su fila de
pago esta a medias, asi que las dos tablas viajan con las de P7.

D5: EL ESTADO DEL PAGO LO DETERMINA LA PASARELA, NO NOSOTROS
------------------------------------------------------------
`Pago.estado` no se cambia desde la pantalla ni desde el servicio de ventas:
lo mueve CU-28 al procesar un evento firmado. Es la decision D5 de
docs/04-analisis-arquitectura.md, y `TransaccionPasarela` es la tabla que la
hace cumplible: guarda lo que la pasarela dijo, antes de que nadie lo crea.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# PASARELA es el pago digital de CU-27/CU-28; los otros dos son del punto de
# venta de CU-31 y no pasan por ninguna integracion.
METODOS_PAGO = ("PASARELA", "EFECTIVO", "TARJETA_POS")

# INICIADO -> APROBADO | RECHAZADO, y REEMBOLSADO despues de una devolucion
# (CU-32). Un pago EFECTIVO nace APROBADO: no hay nada que esperar.
ESTADOS_PAGO = ("INICIADO", "APROBADO", "RECHAZADO", "REEMBOLSADO")


class Pago(Base):
    """El cobro de una venta. Uno por venta.

    `monto` es una copia congelada, igual que `DetalleVenta.precio_unitario`:
    es lo que se cobro, no lo que la venta valdria hoy. Si despues se corrige
    la venta, el pago sigue diciendo lo que paso por la caja o por la pasarela.

    No lleva `sucursal_id` ni `turno_caja_id`: esos ya estan en la venta, y
    duplicarlos abriria la puerta a que un pago diga una caja y su venta otra.
    """

    __tablename__ = "pago"
    __table_args__ = (
        CheckConstraint("metodo IN ('" + "', '".join(METODOS_PAGO) + "')", name="metodo"),
        CheckConstraint(
            "estado IN ('" + "', '".join(ESTADOS_PAGO) + "')", name="estado"
        ),
        CheckConstraint("monto >= 0", name="monto_no_negativo"),
        # Solo el pago por pasarela tiene sesion externa. Un pago en efectivo
        # con referencia externa seria un dato que nadie escribio.
        CheckConstraint(
            "metodo = 'PASARELA' OR referencia_externa IS NULL",
            name="referencia_solo_pasarela",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    #: UNICO: un pago por venta. Un cobro en dos partes seria otro caso de uso
    #: y otra tabla; hoy el enunciado no lo pide.
    venta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("venta.id"), unique=True
    )
    metodo: Mapped[str] = mapped_column(String(12))
    estado: Mapped[str] = mapped_column(String(12), index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    #: El id de la sesion de la pasarela. UNICO para que dos ventas no puedan
    #: quedar colgadas de la misma sesion de pago, que es como un reintento mal
    #: hecho cobraria dos veces lo mismo.
    referencia_externa: Mapped[str | None] = mapped_column(String(100), unique=True)

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    transacciones: Mapped[list["TransaccionPasarela"]] = relationship(
        back_populates="pago"
    )


class TransaccionPasarela(Base):
    """Todo lo que la pasarela dijo, se haya aplicado o no. INMUTABLE.

    ACA ESTA TODA LA IDEMPOTENCIA, Y ES UNA SOLA RESTRICCION
    --------------------------------------------------------
    El UNIQUE sobre `evento_id` es lo que hace que una notificacion repetida NO
    descuente el inventario dos veces: el INSERT falla, el servicio lo trata
    como "ya visto" y no vuelve a tocar la venta.

    Sin esa restriccion la idempotencia habria que resolverla con logica -leer
    si existe, y si no insertar-, y esa logica se equivoca justamente cuando
    dos webhooks llegan a la vez, que es cuando importa. Es RNF09.

    `pago_id` ES NULLABLE A PROPOSITO
    ---------------------------------
    Un evento puede llegar sin que sepamos aun a que pago corresponde, o con
    firma invalida. Esos tambien se guardan: son exactamente los que uno quiere
    mirar cuando algo sale mal. Rechazarlos en la base los borraria de la
    historia.

    `firma_valida` se guarda en vez de filtrarse por la misma razon: un intento
    con firma mala es el registro de que alguien lo intento.
    """

    __tablename__ = "transaccion_pasarela"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pago_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pago.id"), index=True
    )
    #: El id del evento que manda la pasarela. UNICO: ver el docstring.
    evento_id: Mapped[str] = mapped_column(String(100), unique=True)
    tipo_evento: Mapped[str] = mapped_column(String(50))
    firma_valida: Mapped[bool] = mapped_column(Boolean)
    #: El JSON crudo, tal cual llego. Text y no JSONB: no se consulta por
    #: adentro, se guarda para poder releerlo tal como la pasarela lo mando.
    carga_util: Mapped[str] = mapped_column(Text)
    recibido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    pago: Mapped["Pago | None"] = relationship(back_populates="transacciones")
