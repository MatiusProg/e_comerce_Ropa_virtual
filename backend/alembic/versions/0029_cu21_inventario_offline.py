"""0029 - CU-21: el inventario de la sucursal, también sin conexión.

- `operacion_offline` acepta dos tipos más: INGRESO y AJUSTE. Confirmados no
  tienen venta ni reserva: lo que dejan son movimientos de inventario.
- `movimiento_inventario.operacion_offline_id`: el movimiento sabe de qué
  operación offline salió. El kardex lo muestra como «sin conexión».
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0029_cu21_inventario_offline"
down_revision: str | None = "0028_cu17_operacion_offline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RESULTADO_NUEVO = (
    "(estado = 'CONFIRMADA' AND (venta_id IS NOT NULL OR reserva_id IS NOT NULL"
    " OR tipo IN ('INGRESO', 'AJUSTE'))"
    " AND motivo_rechazo IS NULL)"
    " OR (estado = 'RECHAZADA' AND venta_id IS NULL AND reserva_id IS NULL"
    " AND motivo_rechazo IS NOT NULL)"
)
_RESULTADO_VIEJO = (
    "(estado = 'CONFIRMADA' AND (venta_id IS NOT NULL OR reserva_id IS NOT NULL)"
    " AND motivo_rechazo IS NULL)"
    " OR (estado = 'RECHAZADA' AND venta_id IS NULL AND reserva_id IS NULL"
    " AND motivo_rechazo IS NOT NULL)"
)


def upgrade() -> None:
    # La convención antepone la tabla: a `name=` va solo el sufijo.
    op.drop_constraint("tipo", "operacion_offline", type_="check")
    op.create_check_constraint(
        "tipo", "operacion_offline", "tipo IN ('VENTA', 'RESERVA', 'INGRESO', 'AJUSTE')"
    )
    op.drop_constraint("resultado_segun_estado", "operacion_offline", type_="check")
    op.create_check_constraint("resultado_segun_estado", "operacion_offline", _RESULTADO_NUEVO)

    op.add_column(
        "movimiento_inventario",
        sa.Column("operacion_offline_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_movimiento_inventario_operacion_offline_id_operacion_offline",
        "movimiento_inventario",
        "operacion_offline",
        ["operacion_offline_id"],
        ["id"],
    )
    op.create_index(
        "ix_movimiento_inventario_operacion_offline_id",
        "movimiento_inventario",
        ["operacion_offline_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_movimiento_inventario_operacion_offline_id", table_name="movimiento_inventario")
    op.drop_constraint(
        "fk_movimiento_inventario_operacion_offline_id_operacion_offline",
        "movimiento_inventario",
        type_="foreignkey",
    )
    op.drop_column("movimiento_inventario", "operacion_offline_id")
    op.execute("DELETE FROM operacion_offline WHERE tipo IN ('INGRESO', 'AJUSTE')")
    op.drop_constraint("resultado_segun_estado", "operacion_offline", type_="check")
    op.create_check_constraint("resultado_segun_estado", "operacion_offline", _RESULTADO_VIEJO)
    op.drop_constraint("tipo", "operacion_offline", type_="check")
    op.create_check_constraint("tipo", "operacion_offline", "tipo IN ('VENTA', 'RESERVA')")
