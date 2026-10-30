"""
P14 - Offline y sincronización / CU-13 a CU-19  |  capa: modelo

2do parcial. Una sola tabla: la bitácora de lo que llegó de un dispositivo que
trabajó sin conexión.

POR QUÉ NO SE AGREGAN COLUMNAS A `venta` NI A `reserva`
------------------------------------------------------
Una operación offline puede terminar RECHAZADA, y entonces no hay venta ni
reserva a la que colgarle nada: el cobro existió y el registro de que existió
tiene que quedar igual (RN-06, el dinero se devuelve). Por eso la operación
es una fila propia, con su resultado, y la venta o la reserva confirmada
apunta desde acá, no al revés.

EL UUID LO CREA EL CLIENTE (RNF05, RN-07)
-----------------------------------------
Es la llave de la idempotencia: si la misma operación llega dos veces —el
teléfono perdió la respuesta y reintenta—, la segunda no vuelve a vender ni a
apartar; el servidor devuelve lo que ya decidió la primera vez.
"""

from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DeEmpresa

TIPOS_OPERACION = ("VENTA", "RESERVA")

#: Los estados del SERVIDOR. Los del cliente son más (local, enviada,
#: confirmada, rechazada, en conflicto: RF-20): `local` y `enviada` viven solo
#: en el dispositivo, porque al servidor una operación llega ya enviada y sale
#: de acá decidida.
ESTADOS_OPERACION = ("CONFIRMADA", "RECHAZADA")

#: Sin conexión solo se cobra en efectivo o con QR anotando la referencia
#: (RN-05). La tarjeta necesita la pasarela, y la pasarela necesita red.
METODOS_OFFLINE = ("EFECTIVO", "QR")


class OperacionOffline(DeEmpresa, Base):
    """Una venta o una reserva hecha sin conexión, y qué decidió el servidor."""

    __tablename__ = "operacion_offline"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('" + "', '".join(TIPOS_OPERACION) + "')", name="tipo"
        ),
        CheckConstraint(
            "estado IN ('" + "', '".join(ESTADOS_OPERACION) + "')", name="estado"
        ),
        CheckConstraint(
            "metodo_pago IS NULL OR metodo_pago IN ('"
            + "', '".join(METODOS_OFFLINE)
            + "')",
            name="metodo_pago",
        ),
        CheckConstraint(
            "(metodo_pago IS NULL) = (monto_cobrado IS NULL)", name="pago_completo"
        ),
        CheckConstraint("monto_cobrado IS NULL OR monto_cobrado > 0", name="monto"),
        # Confirmada = tiene lo que creó. Rechazada = tiene el motivo.
        CheckConstraint(
            "(estado = 'CONFIRMADA' AND (venta_id IS NOT NULL OR reserva_id IS NOT NULL)"
            " AND motivo_rechazo IS NULL)"
            " OR (estado = 'RECHAZADA' AND venta_id IS NULL AND reserva_id IS NULL"
            " AND motivo_rechazo IS NOT NULL)",
            name="resultado_segun_estado",
        ),
        # CU-19: solo se devuelve lo que se cobró de una operación rechazada.
        CheckConstraint(
            "devuelto_en IS NULL OR (estado = 'RECHAZADA' AND monto_cobrado IS NOT NULL)",
            name="devolucion_solo_si_rechazada",
        ),
        CheckConstraint("intentos >= 1", name="intentos"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid: Mapped[uuid_lib.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    tipo: Mapped[str] = mapped_column(String(10))
    estado: Mapped[str] = mapped_column(String(12), index=True)

    #: Dónde y quién (RF-19). La sucursal la deduce el servidor del turno o
    #: de la ficha del empleado; solo la reserva de un cliente la trae.
    sucursal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sucursal.id"), index=True
    )
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    dispositivo: Mapped[str | None] = mapped_column(String(80))

    #: Cuándo la hizo la persona, según el reloj del dispositivo. Se guarda
    #: aparte de `recibida_en` porque «quién llegó primero» (RN-06) se decide
    #: con la hora del SERVIDOR, que es la única en la que se puede confiar.
    creada_en_cliente: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recibida_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    #: Cuántas veces llegó. Más de una = el dispositivo reintentó (RNF10).
    intentos: Mapped[int] = mapped_column(SmallInteger, server_default="1")

    #: El cobro offline (CU-16). La referencia es el número de la operación QR
    #: que da el banco; NUNCA datos de una tarjeta (RNF10).
    metodo_pago: Mapped[str | None] = mapped_column(String(10))
    monto_cobrado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    referencia_pago: Mapped[str | None] = mapped_column(String(60))

    #: Lo que llegó, tal cual, para poder explicar después qué se pidió.
    carga: Mapped[dict] = mapped_column(JSONB)

    venta_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("venta.id"), unique=True
    )
    reserva_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("reserva.id"), unique=True
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(String(300))

    # --- CU-19: la devolución del dinero de una operación rechazada --------
    devuelto_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    devuelto_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id")
    )
    metodo_devolucion: Mapped[str | None] = mapped_column(String(10))
    referencia_devolucion: Mapped[str | None] = mapped_column(String(60))
    observacion_devolucion: Mapped[str | None] = mapped_column(String(300))
