"""0035 - Tareas automáticas: la marca de la última vuelta.

gunicorn corre 2 workers y cada uno tiene su bucle de tareas. El advisory
lock evita que corran a la vez, pero no que el segundo repita la vuelta un
segundo después de que el primero suelta el bloqueo. `tarea_automatica`
guarda cuándo empezó la última; el que llega tarde la ve y se la saltea.

Es de la plataforma: sin `empresa_id` ni RLS. Los permisos para `violet_app`
salen de los DEFAULT PRIVILEGES de la 0022.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0035_tareas_ultima_vuelta"
down_revision: str | None = "0034_cu32_cerrada_por_regla"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tarea_automatica",
        sa.Column("clave", sa.String(40), primary_key=True),
        sa.Column("ultima_vuelta", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tarea_automatica")
