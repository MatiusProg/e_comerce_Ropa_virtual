"""0039 - CU-40 copias de seguridad y CU-26 el aviso de devoluciones.

- `respaldo`: el registro de cada copia; la automática guarda su contenido
  cifrado, la manual no (RNF17).
- `restauracion`: el historial de restauraciones (RF-63, RN-19).
- `notificacion.tipo` suma DEVOLUCION (CU-26: las devoluciones por la web).

Tablas de empresa con RLS y FORCE; el SQL de la política está COPIADO a
propósito, como en la 0036 a la 0038.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0039_cu40_respaldos"
down_revision: str | None = "0038_cu41_roles_empresa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIPOS_ANTES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO')"
)
TIPOS_DESPUES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO', "
    "'DEVOLUCION')"
)


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
        "respaldo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("archivo", sa.String(120), nullable=False),
        sa.Column("tamano_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("filas", postgresql.JSONB(), nullable=False),
        sa.Column("contenido", sa.LargeBinary(), nullable=True),
        sa.Column("creado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("tipo IN ('MANUAL', 'AUTOMATICA')", name="tipo_valido"),
        sa.CheckConstraint("(tipo = 'AUTOMATICA') = (contenido IS NOT NULL)",
                           name="contenido_segun_tipo"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_respaldo_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["creado_por"], ["usuario.id"], ondelete="SET NULL",
                                name="fk_respaldo_creado_por_usuario"),
        sa.PrimaryKeyConstraint("id", name="pk_respaldo"),
    )
    for columna in ("empresa_id", "tipo", "creado_en"):
        op.create_index(f"ix_respaldo_{columna}", "respaldo", [columna])
    _rls("respaldo")

    op.create_table(
        "restauracion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("origen", sa.String(10), nullable=False),
        sa.Column("archivo", sa.String(120), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("datos_del", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filas", postgresql.JSONB(), nullable=False),
        sa.Column("respaldo_id", sa.Integer(), nullable=True),
        sa.Column("restaurado_por", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("origen IN ('ARCHIVO', 'COPIA')", name="origen_valido"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_restauracion_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["respaldo_id"], ["respaldo.id"], ondelete="SET NULL",
                                name="fk_restauracion_respaldo_id_respaldo"),
        sa.ForeignKeyConstraint(["restaurado_por"], ["usuario.id"], ondelete="SET NULL",
                                name="fk_restauracion_restaurado_por_usuario"),
        sa.PrimaryKeyConstraint("id", name="pk_restauracion"),
    )
    op.create_index("ix_restauracion_empresa_id", "restauracion", ["empresa_id"])
    _rls("restauracion")

    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint("tipo_valido", "notificacion", f"tipo IN {TIPOS_DESPUES}")


def downgrade() -> None:
    op.execute("DELETE FROM notificacion WHERE tipo = 'DEVOLUCION'")
    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint("tipo_valido", "notificacion", f"tipo IN {TIPOS_ANTES}")
    op.drop_index("ix_restauracion_empresa_id", table_name="restauracion")
    op.drop_table("restauracion")
    for columna in ("creado_en", "tipo", "empresa_id"):
        op.drop_index(f"ix_respaldo_{columna}", table_name="respaldo")
    op.drop_table("respaldo")
