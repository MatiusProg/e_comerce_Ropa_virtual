"""0041 - CU-36, CU-37 y CU-38: el probador con la talla real.

- `punto_prenda`: los puntos de referencia de cada imagen de vestidor (hombro
  izquierdo, hombro derecho y ruedo, en coordenadas relativas). Junto con los
  centimetros de `medida_talla` dicen cuantos pixeles de la imagen son un
  centimetro de tela (CU-36).
- `sesion_probador`: la `SesionVestidorVirtual` que la arquitectura declaraba
  desde el Ciclo 3. Registra cada prueba (CU-37) y la foto realista si se pidio
  (CU-38).

Tablas de empresa con RLS y FORCE; el SQL de la politica esta COPIADO a
proposito, como en la 0036 a la 0039.

Encadena tras la 0034 (la cabeza al 07/11). Si el ML (0040) se mergea antes,
se ajusta este `down_revision`.
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0041_cu36_probador"
down_revision: str | None = "0034_cu32_cerrada_por_regla"
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


def _coordenada(nombre: str) -> sa.Column:
    return sa.Column(nombre, sa.Numeric(5, 4), nullable=False)


def upgrade() -> None:
    op.create_table(
        "punto_prenda",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("imagen_id", sa.BigInteger(), nullable=False),
        _coordenada("hombro_izq_x"),
        _coordenada("hombro_izq_y"),
        _coordenada("hombro_der_x"),
        _coordenada("hombro_der_y"),
        _coordenada("ruedo_x"),
        _coordenada("ruedo_y"),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint(
            "hombro_izq_x BETWEEN 0 AND 1 AND hombro_izq_y BETWEEN 0 AND 1 AND "
            "hombro_der_x BETWEEN 0 AND 1 AND hombro_der_y BETWEEN 0 AND 1 AND "
            "ruedo_x BETWEEN 0 AND 1 AND ruedo_y BETWEEN 0 AND 1",
            name="dentro_de_la_imagen",
        ),
        sa.CheckConstraint("hombro_izq_x < hombro_der_x", name="hombros_en_orden"),
        sa.CheckConstraint("ruedo_y > hombro_izq_y AND ruedo_y > hombro_der_y",
                           name="ruedo_debajo"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_punto_prenda_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["imagen_id"], ["imagen_producto.id"], ondelete="CASCADE",
                                name="fk_punto_prenda_imagen_id_imagen_producto"),
        sa.PrimaryKeyConstraint("id", name="pk_punto_prenda"),
        sa.UniqueConstraint("imagen_id", name="uq_punto_prenda_imagen_id"),
    )
    op.create_index("ix_punto_prenda_empresa_id", "punto_prenda", ["empresa_id"])
    _rls("punto_prenda")

    op.create_table(
        "sesion_probador",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=sa.text("app_empresa_actual()"),
                  nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("metodo", sa.String(10), nullable=False),
        sa.Column("ajuste", sa.String(15), nullable=True),
        sa.Column("talla_recomendada", sa.String(10), nullable=True),
        sa.Column("foto_ruta", sa.String(255), nullable=True),
        sa.Column("foto_generada_por", sa.String(60), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("metodo IN ('POSE', 'MANUAL')", name="metodo_valido"),
        sa.CheckConstraint("(foto_ruta IS NULL) = (foto_generada_por IS NULL)",
                           name="foto_completa"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_sesion_probador_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="CASCADE",
                                name="fk_sesion_probador_cliente_id_cliente"),
        sa.ForeignKeyConstraint(["variante_id"], ["variante_producto.id"], ondelete="CASCADE",
                                name="fk_sesion_probador_variante_id_variante_producto"),
        sa.PrimaryKeyConstraint("id", name="pk_sesion_probador"),
    )
    for columna in ("empresa_id", "cliente_id", "creado_en"):
        op.create_index(f"ix_sesion_probador_{columna}", "sesion_probador", [columna])
    _rls("sesion_probador")


def downgrade() -> None:
    op.drop_table("sesion_probador")
    op.drop_table("punto_prenda")
