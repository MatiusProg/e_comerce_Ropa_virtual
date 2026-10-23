"""
P2 - Organizacion  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores

Depende de P1: empleados y proveedores se vinculan a su usuario del sistema.
El esquema es el de docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md 3.3.
"""

from datetime import date, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base, DeEmpresa


class Ciudad(Auditoria, Base):
    """Agrupa las sucursales de una misma plaza."""

    __tablename__ = "ciudad"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    departamento: Mapped[str] = mapped_column(String(60))

    sucursales: Mapped[list["Sucursal"]] = relationship(back_populates="ciudad")


class Sucursal(DeEmpresa, Auditoria, Base):
    """Tienda fisica.

    Es el eje sobre el que se particionan el inventario, las reservas y las
    ventas: agregar una sucursal es una operacion de datos, no de codigo
    (RNF04).
    """

    __tablename__ = "sucursal"
    __table_args__ = (
        UniqueConstraint("empresa_id", "ciudad_id", "nombre", name="uq_sucursal_ciudad_nombre"),
        CheckConstraint("horario_cierre > horario_apertura", name="horario"),
        CheckConstraint("capacidad_vestidores > 0", name="capacidad"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ciudad_id: Mapped[int] = mapped_column(ForeignKey("ciudad.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    direccion: Mapped[str] = mapped_column(String(200))
    telefono: Mapped[str | None] = mapped_column(String(20))
    horario_apertura: Mapped[time] = mapped_column(Time)
    horario_cierre: Mapped[time] = mapped_column(Time)
    capacidad_vestidores: Mapped[int] = mapped_column(
        SmallInteger, server_default=text("1")
    )
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    ciudad: Mapped[Ciudad] = relationship(back_populates="sucursales")
    empleados: Mapped[list["Empleado"]] = relationship(back_populates="sucursal")


class Empleado(DeEmpresa, Auditoria, Base):
    """Persona que trabaja en una sucursal, con su cargo.

    Vincula a la persona con su tienda, que es lo que permite acotar el ambito
    de datos de un Encargado o un Cajero a su propia sucursal (RF26).
    """

    __tablename__ = "empleado"
    __table_args__ = (
        CheckConstraint("cargo IN ('ENCARGADO', 'CAJERO')", name="cargo"),
        CheckConstraint(
            "fecha_baja IS NULL OR fecha_baja >= fecha_ingreso", name="fechas"
        ),
        UniqueConstraint("empresa_id", "documento", name="uq_empleado_documento"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id"), unique=True
    )
    sucursal_id: Mapped[int] = mapped_column(ForeignKey("sucursal.id"), index=True)
    documento: Mapped[str] = mapped_column(String(20))
    telefono: Mapped[str | None] = mapped_column(String(20))
    cargo: Mapped[str] = mapped_column(String(30))
    fecha_ingreso: Mapped[date] = mapped_column(Date)
    fecha_baja: Mapped[date | None] = mapped_column(Date)

    sucursal: Mapped[Sucursal] = relationship(back_populates="empleados")


class Proveedor(DeEmpresa, Auditoria, Base):
    """Empresa que abastece prendas.

    El vinculo con un usuario es opcional: solo lo tiene el proveedor al que se
    le habilita acceso para consultar sus propios productos.
    """

    __tablename__ = "proveedor"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "identificacion_tributaria",
            name="uq_proveedor_identificacion_tributaria",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("usuario.id"), unique=True
    )
    razon_social: Mapped[str] = mapped_column(String(120))
    identificacion_tributaria: Mapped[str] = mapped_column(String(30))
    contacto: Mapped[str | None] = mapped_column(String(80))
    telefono: Mapped[str | None] = mapped_column(String(20))
    correo: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
