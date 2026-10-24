"""0025 - CU-06 Iniciar sesión en una empresa: el correo, único por empresa.

Hasta la 0024, `usuario.correo` era único en toda la plataforma, y el login
encontraba al usuario solo por el correo. Con el CU-06 el login indica la
empresa por su slug (RN-12), así que el correo pasa a ser único:

- por empresa, para el personal (`empresa_id` NOT NULL): la misma persona puede
  trabajar en dos empresas con el mismo correo;
- en la plataforma, para las cuentas sin empresa: el cliente, que tiene una
  sola cuenta (RN-13), y el administrador de la plataforma.

Son dos índices únicos parciales, porque un UNIQUE (empresa_id, correo) común
no compara los NULL entre sí y dejaría repetir clientes. Los correos ya se
guardan en minúsculas (los esquemas los normalizan), así que alcanza con la
columna tal cual.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025_cu06_correo_por_empresa"
down_revision: str | None = "0024_cu05_consumo_cupo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_usuario_empresa_correo", "usuario", ["empresa_id", "correo"], unique=True,
        postgresql_where=sa.text("empresa_id IS NOT NULL"),
    )
    op.create_index(
        "uq_usuario_correo_sin_empresa", "usuario", ["correo"], unique=True,
        postgresql_where=sa.text("empresa_id IS NULL"),
    )
    op.drop_constraint("uq_usuario_correo", "usuario", type_="unique")


def downgrade() -> None:
    # Falla si ya hay un correo repetido entre empresas: es lo que corresponde,
    # volver atrás no puede decidir cuál de las dos cuentas borrar.
    op.create_unique_constraint("uq_usuario_correo", "usuario", ["correo"])
    op.drop_index("uq_usuario_correo_sin_empresa", table_name="usuario")
    op.drop_index("uq_usuario_empresa_correo", table_name="usuario")
