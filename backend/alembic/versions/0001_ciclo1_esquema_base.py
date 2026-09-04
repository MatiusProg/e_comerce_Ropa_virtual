"""Ciclo 1 - esquema base: seguridad, organizacion y maestros del catalogo.

Crea las dieciseis tablas de los paquetes P1, P2 y P3 (maestros), tal como se
disenaron en docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.

Los nombres de restricciones e indices se escriben explicitos y coinciden con
los que produce la convencion de app/db/base.py. Ojo con los CHECK: la
convencion es ck_%(table_name)s_%(constraint_name)s y se aplica SOBRE el nombre
que se pasa, asi que aqui va solo el sufijo ('rango', no 'ck_temporada_rango');
si se pasa el nombre completo sale duplicado. Asi, cuando mas adelante se
use `alembic revision --autogenerate`, Alembic no ve diferencias donde no las
hay y no genera migraciones fantasma.

Revision ID: 0001_ciclo1
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_ciclo1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ================= P1 - Seguridad y Usuarios =========================
    op.create_table(
        "rol",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(30), nullable=False),
        sa.Column("descripcion", sa.String(150), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_rol"),
        sa.UniqueConstraint("nombre", name="uq_rol_nombre"),
    )
    op.create_table(
        "permiso",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("descripcion", sa.String(150), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_permiso"),
        sa.UniqueConstraint("codigo", name="uq_permiso_codigo"),
    )
    op.create_table(
        "rol_permiso",
        sa.Column("rol_id", sa.SmallInteger(), nullable=False),
        sa.Column("permiso_id", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rol_id"], ["rol.id"], name="fk_rol_permiso_rol_id_rol", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["permiso_id"],
            ["permiso.id"],
            name="fk_rol_permiso_permiso_id_permiso",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("rol_id", "permiso_id", name="pk_rol_permiso"),
    )
    op.create_table(
        "usuario",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("correo", sa.String(120), nullable=False),
        sa.Column("hash_contrasena", sa.String(255), nullable=False),
        sa.Column("nombres", sa.String(80), nullable=False),
        sa.Column("apellidos", sa.String(80), nullable=False),
        sa.Column("rol_id", sa.SmallInteger(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["rol_id"], ["rol.id"], name="fk_usuario_rol_id_rol"),
        sa.PrimaryKeyConstraint("id", name="pk_usuario"),
        sa.UniqueConstraint("correo", name="uq_usuario_correo"),
    )
    op.create_index("ix_usuario_rol_id", "usuario", ["rol_id"])

    op.create_table(
        "cliente",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("documento", sa.String(20), nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("talla_superior", sa.String(10), nullable=True),
        sa.Column("talla_inferior", sa.String(10), nullable=True),
        sa.Column("talla_calzado", sa.String(10), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_cliente_usuario_id_usuario",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cliente"),
        sa.UniqueConstraint("usuario_id", name="uq_cliente_usuario_id"),
        sa.UniqueConstraint("documento", name="uq_cliente_documento"),
    )

    op.create_table(
        "sesion_token",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("emitido_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revocado_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("expira_en > emitido_en", name="vigencia"),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_sesion_token_usuario_id_usuario",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sesion_token"),
        sa.UniqueConstraint("jti", name="uq_sesion_token_jti"),
    )
    # Solo interesan las sesiones no revocadas: el indice parcial se mantiene
    # pequeno aunque la tabla crezca.
    op.create_index(
        "idx_sesion_usuario_activa",
        "sesion_token",
        ["usuario_id"],
        postgresql_where=sa.text("revocado_en IS NULL"),
    )

    # ================= P2 - Organizacion =================================
    op.create_table(
        "ciudad",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("departamento", sa.String(60), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ciudad"),
        sa.UniqueConstraint("nombre", name="uq_ciudad_nombre"),
    )
    op.create_table(
        "sucursal",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ciudad_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("direccion", sa.String(200), nullable=False),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("horario_apertura", sa.Time(), nullable=False),
        sa.Column("horario_cierre", sa.Time(), nullable=False),
        sa.Column("capacidad_vestidores", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("horario_cierre > horario_apertura", name="horario"),
        sa.CheckConstraint("capacidad_vestidores > 0", name="capacidad"),
        sa.ForeignKeyConstraint(["ciudad_id"], ["ciudad.id"], name="fk_sucursal_ciudad_id_ciudad"),
        sa.PrimaryKeyConstraint("id", name="pk_sucursal"),
        sa.UniqueConstraint("ciudad_id", "nombre", name="uq_sucursal_ciudad_nombre"),
    )
    op.create_index("ix_sucursal_ciudad_id", "sucursal", ["ciudad_id"])

    op.create_table(
        "direccion_cliente",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("ciudad_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(40), nullable=False),
        sa.Column("direccion", sa.String(200), nullable=False),
        sa.Column("referencia", sa.String(200), nullable=True),
        sa.Column("predeterminada", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name="fk_direccion_cliente_cliente_id_cliente",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ciudad_id"], ["ciudad.id"], name="fk_direccion_cliente_ciudad_id_ciudad"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_direccion_cliente"),
    )
    # Un cliente puede tener varias direcciones, pero a lo sumo una
    # predeterminada. Lo garantiza la base, no solo el servicio.
    op.create_index(
        "uq_direccion_predeterminada",
        "direccion_cliente",
        ["cliente_id"],
        unique=True,
        postgresql_where=sa.text("predeterminada"),
    )

    op.create_table(
        "empleado",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column("documento", sa.String(20), nullable=False),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("cargo", sa.String(30), nullable=False),
        sa.Column("fecha_ingreso", sa.Date(), nullable=False),
        sa.Column("fecha_baja", sa.Date(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("cargo IN ('ENCARGADO', 'CAJERO')", name="cargo"),
        sa.CheckConstraint(
            "fecha_baja IS NULL OR fecha_baja >= fecha_ingreso", name="fechas"
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_empleado_usuario_id_usuario"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"], name="fk_empleado_sucursal_id_sucursal"),
        sa.PrimaryKeyConstraint("id", name="pk_empleado"),
        sa.UniqueConstraint("usuario_id", name="uq_empleado_usuario_id"),
        sa.UniqueConstraint("documento", name="uq_empleado_documento"),
    )
    op.create_index("ix_empleado_sucursal_id", "empleado", ["sucursal_id"])

    op.create_table(
        "proveedor",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("razon_social", sa.String(120), nullable=False),
        sa.Column("identificacion_tributaria", sa.String(30), nullable=False),
        sa.Column("contacto", sa.String(80), nullable=True),
        sa.Column("telefono", sa.String(20), nullable=True),
        sa.Column("correo", sa.String(120), nullable=True),
        sa.Column("direccion", sa.String(200), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name="fk_proveedor_usuario_id_usuario"),
        sa.PrimaryKeyConstraint("id", name="pk_proveedor"),
        sa.UniqueConstraint("usuario_id", name="uq_proveedor_usuario_id"),
        sa.UniqueConstraint(
            "identificacion_tributaria", name="uq_proveedor_identificacion_tributaria"
        ),
    )

    # ================= P3 - Catalogo (maestros) ==========================
    op.create_table(
        "categoria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("categoria_padre_id", sa.Integer(), nullable=True),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("orden", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Impide que una categoria sea su propia padre. Los ciclos mas largos
        # (A -> B -> A) los valida el servicio: excepcion E2 de CU-08.
        sa.CheckConstraint(
            "categoria_padre_id IS DISTINCT FROM id", name="no_autopadre"
        ),
        sa.ForeignKeyConstraint(
            ["categoria_padre_id"],
            ["categoria.id"],
            name="fk_categoria_categoria_padre_id_categoria",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categoria"),
        sa.UniqueConstraint("categoria_padre_id", "nombre", name="uq_categoria_padre_nombre"),
    )
    op.create_index("ix_categoria_categoria_padre_id", "categoria", ["categoria_padre_id"])

    op.create_table(
        "talla",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tipo_prenda", sa.String(30), nullable=False),
        sa.Column("codigo", sa.String(10), nullable=False),
        sa.Column("orden", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_talla"),
        sa.UniqueConstraint("tipo_prenda", "codigo", name="uq_talla_tipo_codigo"),
    )
    op.create_table(
        "color",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(40), nullable=False),
        sa.Column("hexadecimal", sa.CHAR(7), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("hexadecimal ~ '^#[0-9A-Fa-f]{6}$'", name="hex"),
        sa.PrimaryKeyConstraint("id", name="pk_color"),
        sa.UniqueConstraint("nombre", name="uq_color_nombre"),
    )
    op.create_table(
        "temporada",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("descripcion", sa.String(200), nullable=True),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("fecha_fin > fecha_inicio", name="rango"),
        sa.PrimaryKeyConstraint("id", name="pk_temporada"),
        sa.UniqueConstraint("nombre", name="uq_temporada_nombre"),
    )
    op.create_table(
        "coleccion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("temporada_id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("descripcion", sa.String(200), nullable=True),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["temporada_id"], ["temporada.id"], name="fk_coleccion_temporada_id_temporada"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_coleccion"),
        sa.UniqueConstraint("temporada_id", "nombre", name="uq_coleccion_temporada_nombre"),
    )
    op.create_index("ix_coleccion_temporada_id", "coleccion", ["temporada_id"])


def downgrade() -> None:
    # Orden inverso al de creacion: primero lo que depende, despues lo que es
    # dependido.
    op.drop_table("coleccion")
    op.drop_table("temporada")
    op.drop_table("color")
    op.drop_table("talla")
    op.drop_table("categoria")
    op.drop_table("proveedor")
    op.drop_table("empleado")
    op.drop_table("direccion_cliente")
    op.drop_table("sucursal")
    op.drop_table("ciudad")
    op.drop_table("sesion_token")
    op.drop_table("cliente")
    op.drop_table("usuario")
    op.drop_table("rol_permiso")
    op.drop_table("permiso")
    op.drop_table("rol")
