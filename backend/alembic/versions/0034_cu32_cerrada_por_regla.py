"""0034 - CU-32: quién cerró una oferta automática.

`promocion.cerrada_por_regla`: verdadero cuando la cerró la regla de fuera de
temporada (dejó de cumplir el factor o se apagó la regla). Solo esas se
reabren si el producto vuelve a calificar; la que cerró el Administrador a
mano —poniéndole fecha de fin— queda cerrada (RN-16), igual que la apagada.

Las automáticas encendidas y ya cerradas antes de esta migración se marcan
como cerradas por la regla: es lo que la regla hacía hasta ahora, y así se
conserva su comportamiento.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0034_cu32_cerrada_por_regla"
down_revision: str | None = "0033_cu42_cu43_push"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "promocion",
        sa.Column("cerrada_por_regla", sa.Boolean(), server_default=sa.text("false"),
                  nullable=False),
    )
    op.execute(
        "UPDATE promocion SET cerrada_por_regla = true "
        "WHERE origen = 'AUTOMATICA' AND activa AND hasta IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("promocion", "cerrada_por_regla")
