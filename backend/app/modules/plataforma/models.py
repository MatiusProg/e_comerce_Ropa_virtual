"""
P12 - Plataforma SaaS  |  capa: modelo (SQLAlchemy)

2do parcial. Las tablas por encima de las empresas: la empresa (el tenant), los
planes, la suscripción de cada empresa, la asociación del cliente con cada
empresa donde compra y el consumo mensual de los cupos (CU-05).

`empresa` y `plan` NO tienen RLS: son de la plataforma, y el login necesita
encontrar la empresa por su slug antes de saber de qué empresa es la petición.
`suscripcion`, `cliente_empresa` y `consumo_cupo` sí: cada empresa ve solo las
suyas.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base, DeEmpresa


class Empresa(Auditoria, Base):
    """Una empresa que contrata la plataforma: el tenant.

    Una sucursal no es un tenant: pertenece a una empresa, y una empresa tiene
    una o más sucursales (RN-01). El slug identifica a la empresa en el login y
    en la dirección de su tienda; es único y no se cambia después del alta
    (RN-14).
    """

    __tablename__ = "empresa"
    __table_args__ = (
        CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_formato"),
        CheckConstraint("estado IN ('ACTIVA', 'BAJA')", name="estado"),
        CheckConstraint("color_principal ~ '^#[0-9a-f]{6}$'", name="color_principal"),
        CheckConstraint("color_secundario ~ '^#[0-9a-f]{6}$'", name="color_secundario"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    razon_social: Mapped[str | None] = mapped_column(String(160))
    nit: Mapped[str | None] = mapped_column(String(30))
    slug: Mapped[str] = mapped_column(String(40), unique=True)
    correo_contacto: Mapped[str | None] = mapped_column(String(120))
    estado: Mapped[str] = mapped_column(String(10), server_default=text("'ACTIVA'"))
    # CU-12 (0026): la marca de su tienda, si el plan incluye `marca_propia`.
    # `logo` es la ruta relativa en MEDIA_ROOT; NULL es «el de Violet».
    logo: Mapped[str | None] = mapped_column(String(255))
    color_principal: Mapped[str | None] = mapped_column(String(7))
    color_secundario: Mapped[str | None] = mapped_column(String(7))

    suscripciones: Mapped[list["Suscripcion"]] = relationship(back_populates="empresa")


class Plan(Auditoria, Base):
    """Un plan de suscripción, con sus límites y sus funciones.

    Los límites son columnas `max_*` y los cupos `cupo_*`: NULL significa
    ilimitado. Las funciones habilitadas van en `funciones` (JSON), para poder
    sumar una sin migrar la base. Todo se cambia desde el backend, sin tocar
    código (RF-04).
    """

    __tablename__ = "plan"
    __table_args__ = (
        CheckConstraint("precio_mensual >= 0", name="precio"),
        CheckConstraint("duracion_dias > 0", name="duracion"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    precio_mensual: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    duracion_dias: Mapped[int] = mapped_column(SmallInteger, server_default=text("30"))
    max_sucursales: Mapped[int | None] = mapped_column(Integer)
    max_empleados: Mapped[int | None] = mapped_column(Integer)
    cupo_reportes_ia: Mapped[int | None] = mapped_column(Integer)
    cupo_fotos_ia: Mapped[int | None] = mapped_column(Integer)
    funciones: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Suscripcion(DeEmpresa, Auditoria, Base):
    """El plan de una empresa entre dos fechas.

    Es un historial: cambiar de plan cierra la suscripción vigente y abre otra.
    Una empresa tiene como máximo una vigente a la vez (RN-02), y lo garantiza
    la base con un índice único parcial.
    """

    __tablename__ = "suscripcion"
    __table_args__ = (
        CheckConstraint("vencimiento > inicio", name="fechas"),
        CheckConstraint(
            "estado IN ('VIGENTE', 'SUSPENDIDA', 'VENCIDA', 'REEMPLAZADA')", name="estado"
        ),
        Index(
            "uq_suscripcion_vigente_por_empresa",
            "empresa_id",
            unique=True,
            postgresql_where=text("estado IN ('VIGENTE', 'SUSPENDIDA')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    plan_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("plan.id"), index=True)
    inicio: Mapped[date] = mapped_column(Date)
    vencimiento: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(12), server_default=text("'VIGENTE'"))

    empresa: Mapped[Empresa] = relationship(back_populates="suscripciones")
    plan: Mapped[Plan] = relationship()


class PagoSimulado(DeEmpresa, Base):
    """Lo que se habría cobrado por una suscripción (CU-03, paso 4).

    Se registra en el alta, en el cambio de plan y en cada renovación. No pasa
    por ninguna pasarela: deja el monto y un comprobante para el historial.
    """

    __tablename__ = "pago_simulado"
    __table_args__ = (
        CheckConstraint("concepto IN ('ALTA', 'CAMBIO', 'RENOVACION')", name="concepto"),
        CheckConstraint("monto >= 0", name="monto"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    suscripcion_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("suscripcion.id"), index=True
    )
    plan_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("plan.id"))
    concepto: Mapped[str] = mapped_column(String(12))
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    comprobante: Mapped[str] = mapped_column(String(24), unique=True)
    pagado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    plan: Mapped[Plan] = relationship()


class ClienteEmpresa(DeEmpresa, Base):
    """Un cliente que compra en una empresa (RN-13).

    El cliente tiene una sola cuenta en la plataforma y no pertenece a ninguna
    empresa; esta fila es lo que dice dónde compra. Cada empresa ve solo a sus
    clientes, y nunca lo que el cliente hizo en otra.
    """

    __tablename__ = "cliente_empresa"

    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE"), primary_key=True
    )
    # Se repite la columna del mixin para que forme parte de la clave primaria.
    empresa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("empresa.id"),
        primary_key=True,
        server_default=text("app_empresa_actual()"),
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ConsumoCupo(DeEmpresa, Base):
    """Lo que una empresa usó de un cupo mensual de su plan (CU-05, RN-11).

    Una fila por empresa, cupo y mes. Los límites (sucursales, empleados) se
    cuentan sobre sus propias tablas; los cupos no, porque lo que consumen
    (una foto con IA, un reporte con IA) no deja otra fila donde contarlo.
    `periodo` es el primer día del mes en hora de Bolivia.
    """

    __tablename__ = "consumo_cupo"
    __table_args__ = (CheckConstraint("usados >= 0", name="usados"),)

    # Se repite la columna del mixin para que forme parte de la clave primaria.
    empresa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("empresa.id"),
        primary_key=True,
        server_default=text("app_empresa_actual()"),
    )
    recurso: Mapped[str] = mapped_column(String(20), primary_key=True)
    periodo: Mapped[date] = mapped_column(Date, primary_key=True)
    usados: Mapped[int] = mapped_column(Integer, server_default=text("0"))
