"""
P1 - Seguridad y Usuarios  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente

El esquema es el disenado en docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md
seccion 3.3. Si algo cambia aqui, hay que cambiarlo alli: el documento y el
codigo describen la misma base.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Table,
    Column,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base

# La relacion Rol - Permiso es muchos a muchos y no lleva atributos propios,
# asi que se resuelve con una tabla intermedia y no con una clase.
rol_permiso = Table(
    "rol_permiso",
    Base.metadata,
    Column("rol_id", SmallInteger, ForeignKey("rol.id", ondelete="CASCADE"), primary_key=True),
    Column("permiso_id", SmallInteger, ForeignKey("permiso.id", ondelete="CASCADE"), primary_key=True),
)


class Rol(Base):
    """Define el conjunto de permisos de un tipo de usuario."""

    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(150))

    permisos: Mapped[list["Permiso"]] = relationship(
        secondary=rol_permiso, back_populates="roles"
    )
    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")


class Permiso(Base):
    """Accion concreta que un rol puede ejecutar."""

    __tablename__ = "permiso"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(150))

    roles: Mapped[list[Rol]] = relationship(
        secondary=rol_permiso, back_populates="permisos"
    )


class Usuario(Auditoria, Base):
    """Cualquier persona que accede al sistema, con su credencial y su rol.

    La contrasena nunca se almacena: se guarda su hash (RNF01).
    """

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    correo: Mapped[str] = mapped_column(String(120), unique=True)
    hash_contrasena: Mapped[str] = mapped_column(String(255))
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    rol_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("rol.id"), index=True)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    rol: Mapped[Rol] = relationship(back_populates="usuarios")
    cliente: Mapped["Cliente | None"] = relationship(back_populates="usuario")
    sesiones: Mapped[list["SesionToken"]] = relationship(back_populates="usuario")


class Cliente(Auditoria, Base):
    """Datos comerciales de un usuario con rol Cliente.

    Las tallas habituales alimentan al recomendador del Ciclo 3 (CU-33).
    """

    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="CASCADE"), unique=True
    )
    documento: Mapped[str | None] = mapped_column(String(20), unique=True)
    telefono: Mapped[str | None] = mapped_column(String(20))
    talla_superior: Mapped[str | None] = mapped_column(String(10))
    talla_inferior: Mapped[str | None] = mapped_column(String(10))
    talla_calzado: Mapped[str | None] = mapped_column(String(10))

    usuario: Mapped[Usuario] = relationship(back_populates="cliente")
    direcciones: Mapped[list["DireccionCliente"]] = relationship(
        back_populates="cliente", cascade="all, delete-orphan"
    )


class DireccionCliente(Auditoria, Base):
    """Direccion de entrega de un cliente (CU-04).

    Aparece en el flujo de Diseno, no en el de Analisis: CU-04 admite varias
    direcciones por cliente, y una relacion uno a muchos no cabe como atributo.

    La clave foranea a ciudad cruza al paquete P2. Se declara por nombre de
    tabla para no importar el modulo y crear una dependencia circular.
    """

    __tablename__ = "direccion_cliente"
    __table_args__ = (
        # Un cliente puede tener varias direcciones, pero a lo sumo una
        # predeterminada. El indice parcial lo garantiza en la base, no solo
        # en el servicio.
        Index(
            "uq_direccion_predeterminada",
            "cliente_id",
            unique=True,
            postgresql_where=text("predeterminada"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE")
    )
    ciudad_id: Mapped[int] = mapped_column(ForeignKey("ciudad.id"))
    alias: Mapped[str] = mapped_column(String(40))
    direccion: Mapped[str] = mapped_column(String(200))
    referencia: Mapped[str | None] = mapped_column(String(200))
    predeterminada: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))

    cliente: Mapped[Cliente] = relationship(back_populates="direcciones")


class SesionToken(Base):
    """Registro de una sesion emitida, para poder revocarla (CU-02).

    Sin esta tabla, desactivar un usuario no tendria efecto inmediato: su token
    ya emitido seguiria siendo valido hasta vencer. Su ciclo de vida es el
    diagrama de estado de la seccion 3.2.

    No usa el mixin de Auditoria: sus fechas son las del propio ciclo de vida.
    """

    __tablename__ = "sesion_token"
    __table_args__ = (
        CheckConstraint("expira_en > emitido_en", name="vigencia"),
        # Solo interesan las sesiones no revocadas; el indice parcial se
        # mantiene pequeno aunque la tabla crezca.
        Index(
            "idx_sesion_usuario_activa",
            "usuario_id",
            postgresql_where=text("revocado_en IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="CASCADE")
    )
    jti: Mapped[UUID] = mapped_column(Uuid, unique=True)
    emitido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship(back_populates="sesiones")
