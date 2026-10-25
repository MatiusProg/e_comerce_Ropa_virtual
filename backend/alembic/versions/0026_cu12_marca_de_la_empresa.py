"""0026 - CU-12 Personalizar la tienda de la empresa: el logo y los colores.

La empresa con la función `marca_propia` en su plan muestra su tienda con su
logo y sus dos colores en lugar de los de Violet. Van en `empresa` porque son
uno por empresa, y `empresa` no tiene RLS (es la tabla del tenant): el código
la acota por el id de la empresa de la sesión.

`logo` guarda la ruta relativa dentro de MEDIA_ROOT, igual que las imágenes de
producto (CU-11). Los colores son hexadecimales `#rrggbb`; NULL es «el de
Violet».
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_cu12_marca_de_la_empresa"
down_revision: str | None = "0025_cu06_correo_por_empresa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HEX = "^#[0-9a-f]{6}$"


def upgrade() -> None:
    op.add_column("empresa", sa.Column("logo", sa.String(255), nullable=True))
    op.add_column("empresa", sa.Column("color_principal", sa.String(7), nullable=True))
    op.add_column("empresa", sa.Column("color_secundario", sa.String(7), nullable=True))
    op.create_check_constraint(
        op.f("ck_empresa_color_principal"), "empresa", f"color_principal ~ '{_HEX}'"
    )
    op.create_check_constraint(
        op.f("ck_empresa_color_secundario"), "empresa", f"color_secundario ~ '{_HEX}'"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_empresa_color_secundario"), "empresa", type_="check")
    op.drop_constraint(op.f("ck_empresa_color_principal"), "empresa", type_="check")
    op.drop_column("empresa", "color_secundario")
    op.drop_column("empresa", "color_principal")
    op.drop_column("empresa", "logo")
