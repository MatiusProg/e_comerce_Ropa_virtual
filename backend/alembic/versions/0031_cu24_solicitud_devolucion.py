"""0031 - CU-24: el cambio o la devolución pedidos por la web.

- `venta.entregado_en`: cuándo se entregó el pedido web. Desde ahí corre la
  ventana de devolución (RF-35). Lo marca el encargado.
- `solicitud_devolucion` y `linea_solicitud_devolucion`: lo que pide el
  cliente, hasta que el encargado la atiende (CU-25). Tablas de empresa con
  RLS FORCE; el SQL de la política está COPIADO a propósito, como en la 0028.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0031_cu24_solicitud_devolucion"
down_revision: str | None = "0030_cu22_nota_de_devolucion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPRESA = sa.text("app_empresa_actual()")


def upgrade() -> None:
    op.add_column("venta", sa.Column("entregado_en", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "solicitud_devolucion",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=_EMPRESA, nullable=False),
        sa.Column("venta_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("estado", sa.String(12), server_default="PENDIENTE", nullable=False),
        sa.Column("motivo", sa.String(300), nullable=False),
        sa.Column("respuesta", sa.String(300), nullable=True),
        sa.Column("atendida_por", sa.BigInteger(), nullable=True),
        sa.Column("atendida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("devolucion_id", sa.BigInteger(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("tipo IN ('DEVOLUCION', 'CAMBIO')", name="tipo"),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'APROBADA', 'RECHAZADA', 'COMPLETADA')", name="estado"
        ),
        sa.CheckConstraint(
            "estado <> 'RECHAZADA' OR respuesta IS NOT NULL", name="rechazo_con_motivo"
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_solicitud_devolucion_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["venta_id"], ["venta.id"],
                                name="fk_solicitud_devolucion_venta_id_venta"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"],
                                name="fk_solicitud_devolucion_cliente_id_cliente"),
        sa.ForeignKeyConstraint(["sucursal_id"], ["sucursal.id"],
                                name="fk_solicitud_devolucion_sucursal_id_sucursal"),
        sa.ForeignKeyConstraint(["atendida_por"], ["usuario.id"],
                                name="fk_solicitud_devolucion_atendida_por_usuario"),
        sa.ForeignKeyConstraint(["devolucion_id"], ["devolucion.id"],
                                name="fk_solicitud_devolucion_devolucion_id_devolucion"),
        sa.PrimaryKeyConstraint("id", name="pk_solicitud_devolucion"),
        sa.UniqueConstraint("devolucion_id", name="uq_solicitud_devolucion_devolucion_id"),
    )
    for columna in ("empresa_id", "venta_id", "cliente_id", "sucursal_id", "estado", "creado_en"):
        op.create_index(
            f"ix_solicitud_devolucion_{columna}", "solicitud_devolucion", [columna]
        )

    op.create_table(
        "linea_solicitud_devolucion",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=_EMPRESA, nullable=False),
        sa.Column("solicitud_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("variante_nueva_id", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("cantidad > 0", name="cantidad"),
        sa.CheckConstraint(
            "variante_nueva_id IS NULL OR variante_nueva_id <> variante_id",
            name="cambio_por_otra",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_linea_solicitud_devolucion_empresa_id_empresa"),
        sa.ForeignKeyConstraint(
            ["solicitud_id"], ["solicitud_devolucion.id"], ondelete="CASCADE",
            name="fk_linea_solicitud_devolucion_solicitud_id_solicitud_devolucion",
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"], ["variante_producto.id"],
            name="fk_linea_solicitud_devolucion_variante_id_variante_producto",
        ),
        sa.ForeignKeyConstraint(
            ["variante_nueva_id"], ["variante_producto.id"],
            name="fk_linea_solicitud_devolucion_variante_nueva_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_linea_solicitud_devolucion"),
        sa.UniqueConstraint("solicitud_id", "variante_id",
                            name="uq_linea_solicitud_devolucion_variante"),
    )
    op.create_index("ix_linea_solicitud_devolucion_empresa_id", "linea_solicitud_devolucion",
                    ["empresa_id"])
    op.create_index("ix_linea_solicitud_devolucion_solicitud_id", "linea_solicitud_devolucion",
                    ["solicitud_id"])

    op.execute("""
ALTER TABLE solicitud_devolucion ENABLE ROW LEVEL SECURITY;
ALTER TABLE solicitud_devolucion FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON solicitud_devolucion
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON solicitud_devolucion TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE solicitud_devolucion_id_seq TO violet_app;

ALTER TABLE linea_solicitud_devolucion ENABLE ROW LEVEL SECURITY;
ALTER TABLE linea_solicitud_devolucion FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON linea_solicitud_devolucion
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON linea_solicitud_devolucion TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE linea_solicitud_devolucion_id_seq TO violet_app;
""")


def downgrade() -> None:
    op.drop_table("linea_solicitud_devolucion")
    op.drop_table("solicitud_devolucion")
    op.drop_column("venta", "entregado_en")
