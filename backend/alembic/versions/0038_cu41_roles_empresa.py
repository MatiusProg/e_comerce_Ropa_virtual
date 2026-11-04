"""0038 - CU-41: roles y permisos propios de cada empresa.

- `rol_empresa`: el rol propio, que parte de un rol base del personal.
- `rol_empresa_permiso`: los códigos del catálogo de permisos que conserva
  (el catálogo vive en `app/core/permisos.py`).
- `usuario.rol_empresa_id`: el rol propio de cada persona; nulo = todo lo de
  su rol base, como hasta ahora.

Las dos tablas nuevas son de empresa: `empresa_id` con el DEFAULT del contexto
y RLS con FORCE (RN-22: otra empresa no ve ni usa los roles). SQL de la
política COPIADO a propósito, como en la 0036 y la 0037.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0038_cu41_roles_empresa"
down_revision: str | None = "0037_cu31_ofertas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _rls(tabla: str) -> None:
    op.execute(f"""
ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON {tabla}
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE {tabla}_id_seq TO violet_app;
""")


def upgrade() -> None:
    op.create_table(
        "rol_empresa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("nombre", sa.String(40), nullable=False),
        sa.Column("descripcion", sa.String(150), nullable=True),
        sa.Column("rol_base", sa.String(15), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("rol_base IN ('ADMINISTRADOR', 'ENCARGADO', 'CAJERO')",
                           name="rol_base_valido"),
        sa.UniqueConstraint("empresa_id", "nombre", name="uq_rol_empresa_nombre"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_rol_empresa_empresa_id_empresa"),
        sa.PrimaryKeyConstraint("id", name="pk_rol_empresa"),
    )
    op.create_index("ix_rol_empresa_empresa_id", "rol_empresa", ["empresa_id"])
    _rls("rol_empresa")

    op.create_table(
        "rol_empresa_permiso",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("rol_empresa_id", sa.Integer(), nullable=False),
        sa.Column("permiso", sa.String(60), nullable=False),
        sa.UniqueConstraint("rol_empresa_id", "permiso", name="uq_rol_empresa_permiso"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_rol_empresa_permiso_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["rol_empresa_id"], ["rol_empresa.id"], ondelete="CASCADE",
                                name="fk_rol_empresa_permiso_rol_empresa_id_rol_empresa"),
        sa.PrimaryKeyConstraint("id", name="pk_rol_empresa_permiso"),
    )
    op.create_index("ix_rol_empresa_permiso_empresa_id", "rol_empresa_permiso", ["empresa_id"])
    op.create_index("ix_rol_empresa_permiso_rol_empresa_id", "rol_empresa_permiso",
                    ["rol_empresa_id"])
    _rls("rol_empresa_permiso")

    op.add_column("usuario", sa.Column("rol_empresa_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_usuario_rol_empresa_id_rol_empresa", "usuario", "rol_empresa",
                          ["rol_empresa_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_usuario_rol_empresa_id", "usuario", ["rol_empresa_id"])


def downgrade() -> None:
    op.drop_index("ix_usuario_rol_empresa_id", table_name="usuario")
    op.drop_constraint("fk_usuario_rol_empresa_id_rol_empresa", "usuario", type_="foreignkey")
    op.drop_column("usuario", "rol_empresa_id")
    op.drop_index("ix_rol_empresa_permiso_rol_empresa_id", table_name="rol_empresa_permiso")
    op.drop_index("ix_rol_empresa_permiso_empresa_id", table_name="rol_empresa_permiso")
    op.drop_table("rol_empresa_permiso")
    op.drop_index("ix_rol_empresa_empresa_id", table_name="rol_empresa")
    op.drop_table("rol_empresa")
