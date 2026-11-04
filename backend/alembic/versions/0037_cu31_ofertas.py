"""0037 - CU-31 y CU-32: precios mayoristas y ofertas de fuera de temporada.

- `precio_mayorista`: escalones «desde N prendas del producto, a Bs X» (RF-56).
- `regla_fuera_de_temporada`: el factor medible de RF-57, una fila por empresa.
- `promocion.origen`: MANUAL (la de siempre, RF-58) o AUTOMATICA (la que crea
  la regla, CU-32). Las que ya existen quedan MANUAL por el DEFAULT.

Las dos tablas nuevas son de empresa: `empresa_id` con el DEFAULT del contexto
y RLS con FORCE. El SQL de la política está COPIADO a propósito, como en la
0027, la 0028 y la 0036.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0037_cu31_ofertas"
down_revision: str | None = "0036_cu33_traspaso"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def _auditoria() -> list[sa.Column]:
    return [
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "precio_mayorista",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad_minima", sa.Integer(), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(10, 2), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_auditoria(),
        sa.CheckConstraint("cantidad_minima >= 2", name="cantidad_minima_mayorista"),
        sa.CheckConstraint("precio_unitario > 0", name="precio_positivo"),
        sa.UniqueConstraint("empresa_id", "producto_id", "cantidad_minima",
                            name="uq_precio_mayorista_producto_cantidad"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_precio_mayorista_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["producto_id"], ["producto.id"],
                                name="fk_precio_mayorista_producto_id_producto"),
        sa.PrimaryKeyConstraint("id", name="pk_precio_mayorista"),
    )
    op.create_index("ix_precio_mayorista_empresa_id", "precio_mayorista", ["empresa_id"])
    op.create_index("ix_precio_mayorista_producto_id", "precio_mayorista", ["producto_id"])
    _rls("precio_mayorista")

    op.create_table(
        "regla_fuera_de_temporada",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dias_desde_fin", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("existencia_minima", sa.Integer(), server_default=sa.text("10"),
                  nullable=False),
        sa.Column("porcentaje", sa.Numeric(5, 2), server_default=sa.text("30"), nullable=False),
        *_auditoria(),
        sa.CheckConstraint("dias_desde_fin >= 0", name="dias_no_negativos"),
        sa.CheckConstraint("existencia_minima >= 1", name="existencia_positiva"),
        sa.CheckConstraint("porcentaje > 0 AND porcentaje <= 90",
                           name="porcentaje_regla_acotado"),
        sa.UniqueConstraint("empresa_id", name="uq_regla_fuera_de_temporada_empresa"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_regla_fuera_de_temporada_empresa_id_empresa"),
        sa.PrimaryKeyConstraint("id", name="pk_regla_fuera_de_temporada"),
    )
    op.create_index("ix_regla_fuera_de_temporada_empresa_id", "regla_fuera_de_temporada",
                    ["empresa_id"])
    _rls("regla_fuera_de_temporada")

    op.add_column(
        "promocion",
        sa.Column("origen", sa.String(10), server_default=sa.text("'MANUAL'"), nullable=False),
    )
    op.create_index("ix_promocion_origen", "promocion", ["origen"])
    op.create_check_constraint(
        "origen_valido", "promocion", "origen IN ('MANUAL', 'AUTOMATICA')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM promocion WHERE origen = 'AUTOMATICA'")
    op.drop_constraint(op.f("ck_promocion_origen_valido"), "promocion", type_="check")
    op.drop_index("ix_promocion_origen", table_name="promocion")
    op.drop_column("promocion", "origen")

    op.drop_index("ix_regla_fuera_de_temporada_empresa_id",
                  table_name="regla_fuera_de_temporada")
    op.drop_table("regla_fuera_de_temporada")

    op.drop_index("ix_precio_mayorista_producto_id", table_name="precio_mayorista")
    op.drop_index("ix_precio_mayorista_empresa_id", table_name="precio_mayorista")
    op.drop_table("precio_mayorista")
