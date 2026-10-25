"""0027 - CU-03 Gestionar suscripciones: el pago simulado.

Cada alta, cambio de plan o renovación de una suscripción deja un pago
simulado (paso 4 del CU-03): el monto que se habría cobrado y un comprobante.
No pasa por ninguna pasarela; existe para que el historial muestre qué se
cobró, cuándo y por qué.

Es una tabla de empresa: `empresa_id` con el DEFAULT del contexto y RLS con
FORCE, igual que `suscripcion`. El SQL de la política está COPIADO a
propósito: una migración no puede depender de código que después cambia.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_cu03_pago_simulado"
down_revision: str | None = "0026_cu12_marca_de_la_empresa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pago_simulado",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("suscripcion_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.SmallInteger(), nullable=False),
        sa.Column("concepto", sa.String(12), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("comprobante", sa.String(24), nullable=False),
        sa.Column("pagado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("concepto IN ('ALTA', 'CAMBIO', 'RENOVACION')", name="concepto"),
        sa.CheckConstraint("monto >= 0", name="monto"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_pago_simulado_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["suscripcion_id"], ["suscripcion.id"],
                                name="fk_pago_simulado_suscripcion_id_suscripcion"),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"], name="fk_pago_simulado_plan_id_plan"),
        sa.PrimaryKeyConstraint("id", name="pk_pago_simulado"),
        sa.UniqueConstraint("comprobante", name="uq_pago_simulado_comprobante"),
    )
    op.create_index("ix_pago_simulado_empresa_id", "pago_simulado", ["empresa_id"])
    op.create_index("ix_pago_simulado_suscripcion_id", "pago_simulado", ["suscripcion_id"])
    op.execute("""
ALTER TABLE pago_simulado ENABLE ROW LEVEL SECURITY;
ALTER TABLE pago_simulado FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON pago_simulado
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON pago_simulado TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE pago_simulado_id_seq TO violet_app;
""")


def downgrade() -> None:
    op.drop_index("ix_pago_simulado_suscripcion_id", table_name="pago_simulado")
    op.drop_index("ix_pago_simulado_empresa_id", table_name="pago_simulado")
    op.drop_table("pago_simulado")
