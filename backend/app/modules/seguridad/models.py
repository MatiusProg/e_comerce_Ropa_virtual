"""
P1 - Seguridad y Usuarios  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
  CU-41 Recuperar contrasena  (ciclo 3)

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
    Integer,
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


# Las categorias preferidas del cliente son el mismo caso: relacion muchos a
# muchos sin atributos propios, asi que tabla intermedia y no clase.
#
# Se difirieron en el Ciclo 1 --- seccion 6.11.3 de docs/06-decisiones-tecnicas
# --- porque las categorias las crea el CU-08 y entonces no existia ninguna que
# elegir: el selector del perfil habria quedado permanentemente vacio. Ahora
# existen. La forma esta fijada en la seccion 6.4 de
# docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md.
cliente_categoria = Table(
    "cliente_categoria",
    Base.metadata,
    Column(
        "cliente_id",
        BigInteger,
        ForeignKey("cliente.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "categoria_id",
        Integer,
        ForeignKey("categoria.id", ondelete="CASCADE"),
        primary_key=True,
    ),
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

    # passive_deletes deja que el ON DELETE CASCADE de la base haga el trabajo.
    # Sin el, al borrar un usuario el ORM intenta primero poner en NULL la clave
    # foranea de cliente y de sesion_token, que son NOT NULL, y el borrado falla
    # con una violacion de integridad. Lo necesita CU-03, que elimina cuentas.
    cliente: Mapped["Cliente | None"] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    sesiones: Mapped[list["SesionToken"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )
    tokens_recuperacion: Mapped[list["TokenRecuperacion"]] = relationship(
        back_populates="usuario", cascade="all, delete-orphan", passive_deletes=True
    )


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
        back_populates="cliente", cascade="all, delete-orphan", passive_deletes=True
    )
    # Sin cascade: borrar un cliente borra sus filas de cliente_categoria por el
    # ON DELETE CASCADE de la tabla puente, pero NUNCA la categoria en si.
    categorias_preferidas: Mapped[list["Categoria"]] = relationship(
        "Categoria", secondary=cliente_categoria, lazy="selectin"
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


class TokenRecuperacion(Base):
    """Enlace de un solo uso para recuperar el acceso a una cuenta (CU-41).

    Realiza el RF39. Aparece en el Ciclo 3: el Ciclo 1 dejo que cualquiera se
    autorregistrara (RF01) y no dejo ninguna forma de volver a entrar tras
    olvidar la contrasena, salvo pedirselo al Administrador.

    NO GUARDA EL TOKEN
    ------------------
    Guarda su SHA-256, igual que `usuario` guarda el hash de la contrasena y
    por el mismo motivo: mientras vive, este token ES la credencial de la
    cuenta --- quien lo tenga puede cambiar la contrasena sin saber la
    anterior. Si se guardara en claro, una lectura de esta tabla entregaria el
    acceso a todas las cuentas con un enlace pendiente.

    SHA-256 y no bcrypt, que es lo que usan las contrasenas: el token son 32
    bytes aleatorios, no una palabra que alguien pueda adivinar, asi que no
    hace falta encarecer el calculo para frenar un ataque por diccionario. Y
    tiene que poder buscarse por igualdad, que es justo lo que bcrypt --- con
    su sal por fila --- no permite.

    De un solo uso: `usado_en` se escribe al canjearlo y un token usado no
    vuelve a servir aunque no haya expirado. Sin eso, el enlace serviria tantas
    veces como alguien lo abriera, y los enlaces quedan en el historial del
    correo.

    No usa el mixin de Auditoria: como `sesion_token`, sus fechas son las de su
    propio ciclo de vida y no las de una edicion.
    """

    __tablename__ = "token_recuperacion"
    __table_args__ = (
        CheckConstraint("expira_en > solicitado_en", name="vigencia"),
        # Solo interesan los tokens sin canjear: al pedir un enlace nuevo hay
        # que invalidar los anteriores de ese usuario. El indice parcial se
        # mantiene chico aunque la tabla acumule historia.
        Index(
            "idx_recuperacion_usuario_pendiente",
            "usuario_id",
            postgresql_where=text("usado_en IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("usuario.id", ondelete="CASCADE")
    )
    #: SHA-256 del token en hexadecimal: 64 caracteres, siempre.
    hash_token: Mapped[str] = mapped_column(String(64), unique=True)
    solicitado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship(back_populates="tokens_recuperacion")
