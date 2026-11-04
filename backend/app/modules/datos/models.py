"""
P18 - Datos de la empresa / CU-39 y CU-40  |  capa: modelo

`respaldo`: cada copia de seguridad generada (RF-60, RF-61). La MANUAL se
descarga y NO queda en el servidor: de ella solo se guarda el registro (RNF17).
La AUTOMATICA guarda su contenido CIFRADO, para poder bajarla o restaurarla
después; se conservan solo las últimas que el plan indica.

`restauracion`: cada vez que se reemplazaron los datos de la empresa desde una
copia (RF-62), con quién, cuándo y de qué archivo (RF-63, RN-19).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, DeEmpresa


class Respaldo(DeEmpresa, Base):
    __tablename__ = "respaldo"
    __table_args__ = (
        CheckConstraint("tipo IN ('MANUAL', 'AUTOMATICA')", name="tipo_valido"),
        # RNF17: la manual no se guarda; la automática, siempre.
        CheckConstraint(
            "(tipo = 'AUTOMATICA') = (contenido IS NOT NULL)", name="contenido_segun_tipo"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10), index=True)
    archivo: Mapped[str] = mapped_column(String(120))
    tamano_bytes: Mapped[int] = mapped_column(Integer)
    #: SHA-256 del archivo tal como se entregó: para reconocerlo después.
    sha256: Mapped[str] = mapped_column(String(64))
    #: Filas por tabla, para el historial (RF-63).
    filas: Mapped[dict] = mapped_column(JSONB)
    #: Solo la automática: el JSON cifrado (Fernet).
    contenido: Mapped[bytes | None] = mapped_column(LargeBinary)
    #: Nulo en la automática: la generó el sistema.
    creado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="SET NULL")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Restauracion(DeEmpresa, Base):
    __tablename__ = "restauracion"
    __table_args__ = (
        CheckConstraint("origen IN ('ARCHIVO', 'COPIA')", name="origen_valido"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    #: ARCHIVO: lo subió el administrador. COPIA: una automática guardada.
    origen: Mapped[str] = mapped_column(String(10))
    archivo: Mapped[str] = mapped_column(String(120))
    sha256: Mapped[str] = mapped_column(String(64))
    #: De cuándo eran los datos que se repusieron.
    datos_del: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    filas: Mapped[dict] = mapped_column(JSONB)
    respaldo_id: Mapped[int | None] = mapped_column(
        ForeignKey("respaldo.id", ondelete="SET NULL")
    )
    restaurado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="SET NULL")
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


__all__ = ["Respaldo", "Restauracion"]
