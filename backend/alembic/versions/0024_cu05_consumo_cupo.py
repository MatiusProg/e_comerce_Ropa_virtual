"""0024 - CU-05 Verificar límites y funciones del plan: el consumo de los cupos.

Los límites del plan (sucursales, empleados) se cuentan sobre sus propias
tablas. Los cupos mensuales (fotos y reportes con IA) no tienen dónde
contarse: lo que consumen no deja otra fila. `consumo_cupo` lleva una fila por
empresa, cupo y mes (RN-11).

Es una tabla de empresa: `empresa_id` con el DEFAULT del contexto y RLS con
FORCE, igual que las de la 0022. El SQL de la política está COPIADO a
propósito: una migración no puede depender de código que después cambia.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024_cu05_consumo_cupo"
down_revision: str | None = "0023_cu01_rol_plataforma"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consumo_cupo",
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("recurso", sa.String(20), nullable=False),
        sa.Column("periodo", sa.Date(), nullable=False),
        sa.Column("usados", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("usados >= 0", name="usados"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_consumo_cupo_empresa_id_empresa"),
        sa.PrimaryKeyConstraint("empresa_id", "recurso", "periodo", name="pk_consumo_cupo"),
    )
    op.execute("""
ALTER TABLE consumo_cupo ENABLE ROW LEVEL SECURITY;
ALTER TABLE consumo_cupo FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON consumo_cupo
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON consumo_cupo TO violet_app;
""")


def downgrade() -> None:
    op.drop_table("consumo_cupo")
