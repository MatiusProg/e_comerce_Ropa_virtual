"""0040 - CU-29 y CU-30: los modelos de la analítica con ML.

Una fila por entrenamiento: el modelo de demanda (supervisado) o el de
segmentos de clientes (no supervisado), con sus parámetros, sus métricas, el
resultado para el dashboard y el modelo serializado.

Tabla de empresa: `empresa_id` con el DEFAULT del contexto y RLS con FORCE. El
SQL de la política está COPIADO a propósito, como en la 0036.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0040_cu29_analitica"
down_revision: str | None = "0035_tareas_ultima_vuelta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "modelo_analitica",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("parametros", postgresql.JSONB(), nullable=False),
        sa.Column("metricas", postgresql.JSONB(), nullable=False),
        sa.Column("resultado", postgresql.JSONB(), nullable=False),
        sa.Column("filas_entrenamiento", sa.Integer(), nullable=False),
        sa.Column("filas_reales", sa.Integer(), nullable=False),
        sa.Column("filas_sinteticas", sa.Integer(), nullable=False),
        sa.Column("duracion_ms", sa.Integer(), nullable=False),
        sa.Column("modelo", sa.LargeBinary(), nullable=False),
        sa.Column("entrenado_por", sa.BigInteger(), nullable=True),
        sa.Column("entrenado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("tipo IN ('DEMANDA', 'SEGMENTOS')", name="tipo_valido"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_modelo_analitica_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["entrenado_por"], ["usuario.id"], ondelete="SET NULL",
                                name="fk_modelo_analitica_entrenado_por_usuario"),
        sa.PrimaryKeyConstraint("id", name="pk_modelo_analitica"),
    )
    for columna in ("empresa_id", "tipo", "entrenado_en"):
        op.create_index(f"ix_modelo_analitica_{columna}", "modelo_analitica", [columna])
    op.execute("""
ALTER TABLE modelo_analitica ENABLE ROW LEVEL SECURITY;
ALTER TABLE modelo_analitica FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON modelo_analitica
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON modelo_analitica TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE modelo_analitica_id_seq TO violet_app;
""")


def downgrade() -> None:
    op.drop_table("modelo_analitica")
