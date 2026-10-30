"""0028 - CU-13 a CU-19: la operación hecha sin conexión.

Una fila por venta o reserva que llegó de un dispositivo offline, con lo que
decidió el servidor (CONFIRMADA o RECHAZADA), el cobro offline (CU-16) y, si
se rechazó después de cobrar, la devolución del dinero (CU-19).

El UUID lo crea el dispositivo y es UNIQUE: es la idempotencia de la
sincronización (RNF05). Tabla de empresa: `empresa_id` con el DEFAULT del
contexto y RLS con FORCE. El SQL de la política está COPIADO a propósito, como
en la 0027.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0028_cu17_operacion_offline"
down_revision: str | None = "0027_cu03_pago_simulado"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operacion_offline",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("dispositivo", sa.String(80), nullable=True),
        sa.Column("creada_en_cliente", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recibida_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("intentos", sa.SmallInteger(), server_default="1", nullable=False),
        sa.Column("metodo_pago", sa.String(10), nullable=True),
        sa.Column("monto_cobrado", sa.Numeric(12, 2), nullable=True),
        sa.Column("referencia_pago", sa.String(60), nullable=True),
        sa.Column("carga", postgresql.JSONB(), nullable=False),
        sa.Column("venta_id", sa.BigInteger(), nullable=True),
        sa.Column("reserva_id", sa.BigInteger(), nullable=True),
        sa.Column("motivo_rechazo", sa.String(300), nullable=True),
        sa.Column("devuelto_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("devuelto_por", sa.BigInteger(), nullable=True),
        sa.Column("metodo_devolucion", sa.String(10), nullable=True),
        sa.Column("referencia_devolucion", sa.String(60), nullable=True),
        sa.Column("observacion_devolucion", sa.String(300), nullable=True),
        sa.CheckConstraint("tipo IN ('VENTA', 'RESERVA')", name="tipo"),
        sa.CheckConstraint("estado IN ('CONFIRMADA', 'RECHAZADA')", name="estado"),
        sa.CheckConstraint("metodo_pago IS NULL OR metodo_pago IN ('EFECTIVO', 'QR')",
                           name="metodo_pago"),
        sa.CheckConstraint("(metodo_pago IS NULL) = (monto_cobrado IS NULL)",
                           name="pago_completo"),
        sa.CheckConstraint("monto_cobrado IS NULL OR monto_cobrado > 0", name="monto"),
        sa.CheckConstraint(
            "(estado = 'CONFIRMADA' AND (venta_id IS NOT NULL OR reserva_id IS NOT NULL)"
            " AND motivo_rechazo IS NULL)"
            " OR (estado = 'RECHAZADA' AND venta_id IS NULL AND reserva_id IS NULL"
            " AND motivo_rechazo IS NOT NULL)",
            name="resultado_segun_estado",
        ),
        sa.CheckConstraint(
            "devuelto_en IS NULL OR (estado = 'RECHAZADA' AND monto_cobrado IS NOT NULL)",
            name="devolucion_solo_si_rechazada",
        ),
        sa.CheckConstraint("intentos >= 1", name="intentos"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_operacion_offline_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"],
                                name="fk_operacion_offline_sucursal_id_sucursal"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"],
                                name="fk_operacion_offline_usuario_id_usuario"),
        sa.ForeignKeyConstraint(["venta_id"], ["venta.id"],
                                name="fk_operacion_offline_venta_id_venta"),
        sa.ForeignKeyConstraint(["reserva_id"], ["reserva.id"],
                                name="fk_operacion_offline_reserva_id_reserva"),
        sa.ForeignKeyConstraint(["devuelto_por"], ["usuario.id"],
                                name="fk_operacion_offline_devuelto_por_usuario"),
        sa.PrimaryKeyConstraint("id", name="pk_operacion_offline"),
        sa.UniqueConstraint("uuid", name="uq_operacion_offline_uuid"),
        sa.UniqueConstraint("venta_id", name="uq_operacion_offline_venta_id"),
        sa.UniqueConstraint("reserva_id", name="uq_operacion_offline_reserva_id"),
    )
    op.create_index("ix_operacion_offline_empresa_id", "operacion_offline", ["empresa_id"])
    op.create_index("ix_operacion_offline_estado", "operacion_offline", ["estado"])
    op.create_index("ix_operacion_offline_sucursal_id", "operacion_offline", ["sucursal_id"])
    op.execute("""
ALTER TABLE operacion_offline ENABLE ROW LEVEL SECURITY;
ALTER TABLE operacion_offline FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON operacion_offline
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON operacion_offline TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE operacion_offline_id_seq TO violet_app;
""")


def downgrade() -> None:
    op.drop_index("ix_operacion_offline_sucursal_id", table_name="operacion_offline")
    op.drop_index("ix_operacion_offline_estado", table_name="operacion_offline")
    op.drop_index("ix_operacion_offline_empresa_id", table_name="operacion_offline")
    op.drop_table("operacion_offline")
