"""0042 - Aporte propio: «Avísame cuando llegue mi talla».

- `aviso_talla`: el cliente pide que le avisen cuando una variante (talla y
  color) sin unidades vuelva a tener. Una fila por pedido; queda pendiente
  hasta que el stock vuelve (`notificado_en`) o el cliente la cancela (se
  borra). Un mismo cliente tiene a lo sumo UN aviso pendiente por variante
  (índice único parcial), y eso es lo que vuelve idempotente el alta.
- `notificacion.tipo`: se suma `STOCK_DISPONIBLE`.

Tabla de empresa con RLS y FORCE; el SQL de la política está COPIADO a
propósito, como en la 0036 a la 0041.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0042_aviso_talla"
down_revision: str | None = "0041_cu36_probador"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIPOS_ANTES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO', "
    "'DEVOLUCION', 'OPERACION_OFFLINE', 'DEVOLUCION_PAGO')"
)
TIPOS_DESPUES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO', "
    "'DEVOLUCION', 'OPERACION_OFFLINE', 'DEVOLUCION_PAGO', 'STOCK_DISPONIBLE')"
)


def _rls(tabla: str) -> None:
    op.execute(f"""
ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON {tabla}
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON {tabla} TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE {tabla}_id_seq TO violet_app;
""")


def upgrade() -> None:
    op.create_table(
        "aviso_talla",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("notificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notificacion_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_aviso_talla_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="CASCADE",
                                name="fk_aviso_talla_cliente_id_cliente"),
        sa.ForeignKeyConstraint(["variante_id"], ["variante_producto.id"], ondelete="CASCADE",
                                name="fk_aviso_talla_variante_id_variante_producto"),
        sa.ForeignKeyConstraint(["notificacion_id"], ["notificacion.id"], ondelete="SET NULL",
                                name="fk_aviso_talla_notificacion_id_notificacion"),
        sa.PrimaryKeyConstraint("id", name="pk_aviso_talla"),
    )
    for columna in ("empresa_id", "cliente_id"):
        op.create_index(f"ix_aviso_talla_{columna}", "aviso_talla", [columna])
    # Lo que busca el gancho del inventario: los pendientes de una variante.
    op.create_index(
        "ix_aviso_talla_pendientes", "aviso_talla", ["variante_id"],
        postgresql_where=sa.text("notificado_en IS NULL"),
    )
    op.create_index(
        "uq_aviso_talla_pendiente", "aviso_talla", ["cliente_id", "variante_id"], unique=True,
        postgresql_where=sa.text("notificado_en IS NULL"),
    )
    _rls("aviso_talla")

    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint("tipo_valido", "notificacion", f"tipo IN {TIPOS_DESPUES}")


def downgrade() -> None:
    op.drop_table("aviso_talla")
    op.execute("DELETE FROM notificacion WHERE tipo = 'STOCK_DISPONIBLE'")
    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint("tipo_valido", "notificacion", f"tipo IN {TIPOS_ANTES}")
