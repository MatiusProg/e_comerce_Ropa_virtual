"""0036 - CU-33 a CU-35: el traspaso entre sucursales.

Una fila por pedido de mercadería de una sucursal a otra, con su seguimiento
(SOLICITADO, APROBADO, ENVIADO, RECIBIDO o RECHAZADO) y los dos movimientos de
inventario que deja: la salida al enviar y la entrada al recibir (RN-09).

Además, el aviso nuevo `TRASPASO` en `notificacion`: al encargado del origen le
avisan que le pidieron mercadería, y al del destino, que ya va en camino.

Tabla de empresa: `empresa_id` con el DEFAULT del contexto y RLS con FORCE. El
SQL de la política está COPIADO a propósito, como en la 0027 y la 0028.

Acuerdo de la P3: Mateo y Luis usan de la 0029 a la 0035, Karen desde la 0036.
Al mergear se ajusta el `down_revision` a la última que haya en `main`.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036_cu33_traspaso"
down_revision: str | None = "0032_cu25_devolucion_web"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TIPOS_AVISO_ANTES = "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO')"
TIPOS_AVISO_DESPUES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO')"
)


def upgrade() -> None:
    op.create_table(
        "traspaso",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_origen_id", sa.Integer(), nullable=False),
        sa.Column("sucursal_destino_id", sa.Integer(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("cantidad_solicitada", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(200), nullable=True),
        sa.Column("solicitado_por", sa.BigInteger(), nullable=True),
        sa.Column("aprobado_por", sa.BigInteger(), nullable=True),
        sa.Column("aprobado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enviado_por", sa.BigInteger(), nullable=True),
        sa.Column("enviado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recibido_por", sa.BigInteger(), nullable=True),
        sa.Column("recibido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rechazado_por", sa.BigInteger(), nullable=True),
        sa.Column("rechazado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_rechazo", sa.String(200), nullable=True),
        sa.Column("movimiento_salida_id", sa.BigInteger(), nullable=True),
        sa.Column("movimiento_entrada_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("tipo IN ('PEDIDO', 'ORDEN', 'SUGERIDO')", name="tipo"),
        sa.CheckConstraint(
            "estado IN ('SOLICITADO', 'APROBADO', 'ENVIADO', 'RECIBIDO', 'RECHAZADO')",
            name="estado",
        ),
        sa.CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        sa.CheckConstraint("sucursal_origen_id <> sucursal_destino_id",
                           name="origen_distinto_destino"),
        sa.CheckConstraint("(estado = 'RECHAZADO') = (motivo_rechazo IS NOT NULL)",
                           name="motivo_rechazo_segun_estado"),
        sa.CheckConstraint(
            "(estado IN ('ENVIADO', 'RECIBIDO')) = (movimiento_salida_id IS NOT NULL)",
            name="salida_segun_estado",
        ),
        sa.CheckConstraint("(estado = 'RECIBIDO') = (movimiento_entrada_id IS NOT NULL)",
                           name="entrada_segun_estado"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_traspaso_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["variante_id"], ["variante_producto.id"],
                                name="fk_traspaso_variante_id_variante_producto"),
        sa.ForeignKeyConstraint(["sucursal_origen_id"], ["sucursal.id"],
                                name="fk_traspaso_sucursal_origen_id_sucursal"),
        sa.ForeignKeyConstraint(["sucursal_destino_id"], ["sucursal.id"],
                                name="fk_traspaso_sucursal_destino_id_sucursal"),
        *[
            sa.ForeignKeyConstraint([col], ["usuario.id"], name=f"fk_traspaso_{col}_usuario")
            for col in ("solicitado_por", "aprobado_por", "enviado_por", "recibido_por",
                        "rechazado_por")
        ],
        sa.ForeignKeyConstraint(["movimiento_salida_id"], ["movimiento_inventario.id"],
                                name="fk_traspaso_movimiento_salida_id_movimiento_inventario"),
        sa.ForeignKeyConstraint(["movimiento_entrada_id"], ["movimiento_inventario.id"],
                                name="fk_traspaso_movimiento_entrada_id_movimiento_inventario"),
        sa.PrimaryKeyConstraint("id", name="pk_traspaso"),
    )
    for columna in ("empresa_id", "estado", "variante_id", "sucursal_origen_id",
                    "sucursal_destino_id"):
        op.create_index(f"ix_traspaso_{columna}", "traspaso", [columna])
    op.execute("""
ALTER TABLE traspaso ENABLE ROW LEVEL SECURITY;
ALTER TABLE traspaso FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON traspaso
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON traspaso TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE traspaso_id_seq TO violet_app;
""")

    # op.f(): el nombre ya es el definitivo (ver la 0018).
    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint(
        "tipo_valido", "notificacion", f"tipo IN {TIPOS_AVISO_DESPUES}"
    )


def downgrade() -> None:
    op.execute("DELETE FROM notificacion WHERE tipo = 'TRASPASO'")
    # op.f(): el nombre ya es el definitivo (ver la 0018).
    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint(
        "tipo_valido", "notificacion", f"tipo IN {TIPOS_AVISO_ANTES}"
    )
    for columna in ("sucursal_destino_id", "sucursal_origen_id", "variante_id", "estado",
                    "empresa_id"):
        op.drop_index(f"ix_traspaso_{columna}", table_name="traspaso")
    op.drop_table("traspaso")
