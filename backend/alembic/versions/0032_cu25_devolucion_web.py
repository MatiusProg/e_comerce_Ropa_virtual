"""0032 - CU-25: la devolución pedida por la web, recibida por el encargado.

- `devolucion.turno_caja_id` pasa a admitir NULL: una devolución web no pasa
  por caja ni toca un cajón. `origen` dice de dónde vino (CAJA o WEB) y el
  CHECK `origen_y_turno` exige el turno en caja y quien la recibió en la web.
- `reembolso_referencia` y `reembolso_monto`: el reembolso por la pasarela.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032_cu25_devolucion_web"
down_revision: str | None = "0031_cu24_solicitud_devolucion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("devolucion", "turno_caja_id", nullable=True)
    op.add_column(
        "devolucion",
        sa.Column("origen", sa.String(6), server_default="CAJA", nullable=False),
    )
    op.add_column("devolucion", sa.Column("recibida_por", sa.BigInteger(), nullable=True))
    op.add_column(
        "devolucion", sa.Column("reembolso_referencia", sa.String(100), nullable=True)
    )
    op.add_column("devolucion", sa.Column("reembolso_monto", sa.Numeric(10, 2), nullable=True))
    op.create_foreign_key(
        "fk_devolucion_recibida_por_usuario", "devolucion", "usuario", ["recibida_por"], ["id"]
    )
    # La convención antepone la tabla: a `name=` va solo el sufijo.
    op.create_check_constraint("origen", "devolucion", "origen IN ('CAJA', 'WEB')")
    op.create_check_constraint(
        "origen_y_turno",
        "devolucion",
        "(origen = 'CAJA' AND turno_caja_id IS NOT NULL)"
        " OR (origen = 'WEB' AND turno_caja_id IS NULL AND recibida_por IS NOT NULL"
        " AND monto = 0)",
    )


def downgrade() -> None:
    op.execute("DELETE FROM detalle_devolucion WHERE devolucion_id IN "
               "(SELECT id FROM devolucion WHERE origen = 'WEB')")
    op.execute("UPDATE solicitud_devolucion SET devolucion_id = NULL WHERE devolucion_id IN "
               "(SELECT id FROM devolucion WHERE origen = 'WEB')")
    op.execute("DELETE FROM devolucion WHERE origen = 'WEB'")
    op.drop_constraint("origen_y_turno", "devolucion", type_="check")
    op.drop_constraint("origen", "devolucion", type_="check")
    op.drop_constraint("fk_devolucion_recibida_por_usuario", "devolucion", type_="foreignkey")
    op.drop_column("devolucion", "reembolso_monto")
    op.drop_column("devolucion", "reembolso_referencia")
    op.drop_column("devolucion", "recibida_por")
    op.drop_column("devolucion", "origen")
    op.alter_column("devolucion", "turno_caja_id", nullable=False)
