"""Clase base declarativa de SQLAlchemy.

La convencion de nombres de restricciones e indices se fija aqui para que
Alembic genere migraciones deterministas: sin esto, los nombres los inventa
PostgreSQL y las migraciones de bajada (downgrade) fallan.
"""

from datetime import datetime

from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


class Auditoria:
    """Mixin de fechas. Se aplica a las entidades que se editan.

    Nota: las entidades de MovimientoInventario NO usan este mixin, porque un
    movimiento es inmutable por diseno (D4 en docs/04-analisis-arquitectura.md).
    """

    creado_en: Mapped[datetime] = mapped_column(server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
