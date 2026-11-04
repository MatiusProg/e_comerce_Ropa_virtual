"""0030 - CU-22 y CU-23: la nota de devolución y la ventana por empresa.

- `empresa.ventana_devolucion_horas` (CU-23, RF-35, RN-08): reemplaza el plazo
  fijo de dos días del 1er parcial. Empieza en 48 horas, que es lo mismo.
- `devolucion.estado`, `conforme` y `observacion_cliente` (CU-22, RF-37,
  RN-20): la conformidad del cliente. Las devoluciones ya registradas quedan
  CERRADAS con `conforme` NULL: se hicieron antes de que existiera la nota, y
  no se les inventa una conformidad que nadie tomó.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030_cu22_nota_de_devolucion"
down_revision: str | None = "0029_cu21_inventario_offline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "empresa",
        sa.Column("ventana_devolucion_horas", sa.SmallInteger(),
                  server_default=sa.text("48"), nullable=False),
    )
    # La convención antepone la tabla: a `name=` va solo el sufijo.
    op.create_check_constraint(
        "ventana_devolucion", "empresa", "ventana_devolucion_horas BETWEEN 1 AND 720"
    )

    op.add_column(
        "devolucion",
        sa.Column("estado", sa.String(10), server_default="CERRADA", nullable=False),
    )
    op.add_column("devolucion", sa.Column("conforme", sa.Boolean(), nullable=True))
    op.add_column(
        "devolucion", sa.Column("observacion_cliente", sa.String(300), nullable=True)
    )
    op.create_check_constraint("estado", "devolucion", "estado IN ('ABIERTA', 'CERRADA')")
    op.create_check_constraint(
        "cerrada_con_conformidad",
        "devolucion",
        "estado = 'ABIERTA' OR conforme IS DISTINCT FROM false",
    )


def downgrade() -> None:
    op.drop_constraint("cerrada_con_conformidad", "devolucion", type_="check")
    op.drop_constraint("estado", "devolucion", type_="check")
    op.drop_column("devolucion", "observacion_cliente")
    op.drop_column("devolucion", "conforme")
    op.drop_column("devolucion", "estado")
    op.drop_constraint("ventana_devolucion", "empresa", type_="check")
    op.drop_column("empresa", "ventana_devolucion_horas")
