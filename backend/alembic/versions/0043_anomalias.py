"""0043 - Aporte propio: anomalías en caja y devoluciones (Isolation Forest).

No hace falta una tabla nueva: el entrenamiento es una fila más de
`modelo_analitica`, de tipo ANOMALIAS. Solo se amplía el CHECK del tipo.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0043_anomalias"
down_revision: str | None = "0042_aviso_talla"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CHECK = "ck_modelo_analitica_tipo_valido"


def upgrade() -> None:
    op.execute(f"ALTER TABLE modelo_analitica DROP CONSTRAINT {_CHECK}")
    op.execute(
        f"ALTER TABLE modelo_analitica ADD CONSTRAINT {_CHECK} "
        "CHECK (tipo IN ('DEMANDA', 'SEGMENTOS', 'ANOMALIAS'))"
    )


def downgrade() -> None:
    # FORCE RLS alcanza también al dueño: se entra en modo plataforma para borrar.
    op.execute("SET LOCAL app.es_plataforma = 'on'")
    op.execute("DELETE FROM modelo_analitica WHERE tipo = 'ANOMALIAS'")
    op.execute(f"ALTER TABLE modelo_analitica DROP CONSTRAINT {_CHECK}")
    op.execute(
        f"ALTER TABLE modelo_analitica ADD CONSTRAINT {_CHECK} "
        "CHECK (tipo IN ('DEMANDA', 'SEGMENTOS'))"
    )
