"""Ciclo 2 - catalogo: productos, variantes, imagenes y categorias preferidas.

Crea las cuatro tablas de las que Karen es duena en el Ciclo 2, tal como se
fijaron en la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md:

  producto           CU-10   la prenda como concepto
  variante_producto  CU-10   producto x talla x color; es el SKU y la unidad
                             de negocio (decision D1)
  imagen_producto    CU-11   fotos del producto y de sus variantes
  cliente_categoria  CU-04   categorias preferidas, diferidas del Ciclo 1
                             (seccion 6.11.3 de las decisiones tecnicas)

Escrita A MANO, no con --autogenerate. Es la regla de la seccion 4 del acuerdo
del ciclo: autogenerar mientras el otro tiene sus modelos a medio escribir
produce migraciones que borran tablas ajenas.

La cadena queda 0001_ciclo1 -> 0002_ciclo2_catalogo -> 0003_ciclo2_inv_res. El
identificador de la 0003 se acordo de antemano para que Mateo escriba la suya en
paralelo sin esperar a que esta se integre.

Ojo con los CHECK y los indices: los nombres se escriben explicitos y coinciden
con los que produce la convencion de app/db/base.py, para que un
--autogenerate posterior no vea diferencias donde no las hay. En los CHECK va
solo el sufijo, no el nombre completo.

Revision ID: 0002_ciclo2_catalogo
Revises: 0001_ciclo1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_ciclo2_catalogo"
down_revision: str | None = "0001_ciclo1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ================= P3 - Catalogo (productos) =========================
    op.create_table(
        "producto",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("codigo", sa.String(30), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.String(500), nullable=True),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=True),
        sa.Column("temporada_id", sa.Integer(), nullable=True),
        sa.Column("coleccion_id", sa.Integer(), nullable=True),
        sa.Column("precio_base", sa.Numeric(10, 2), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["categoria.id"], name="fk_producto_categoria_id_categoria"
        ),
        sa.ForeignKeyConstraint(
            ["proveedor_id"], ["proveedor.id"], name="fk_producto_proveedor_id_proveedor"
        ),
        sa.ForeignKeyConstraint(
            ["temporada_id"], ["temporada.id"], name="fk_producto_temporada_id_temporada"
        ),
        sa.ForeignKeyConstraint(
            ["coleccion_id"], ["coleccion.id"], name="fk_producto_coleccion_id_coleccion"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_producto"),
        sa.UniqueConstraint("codigo", name="uq_producto_codigo"),
    )
    op.create_index("ix_producto_categoria_id", "producto", ["categoria_id"])
    op.create_index("ix_producto_proveedor_id", "producto", ["proveedor_id"])
    op.create_index("ix_producto_temporada_id", "producto", ["temporada_id"])
    op.create_index("ix_producto_coleccion_id", "producto", ["coleccion_id"])

    op.create_table(
        "variante_producto",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("talla_id", sa.Integer(), nullable=False),
        sa.Column("color_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(40), nullable=False),
        sa.Column("precio", sa.Numeric(10, 2), nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["producto.id"],
            name="fk_variante_producto_producto_id_producto",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["talla_id"], ["talla.id"], name="fk_variante_producto_talla_id_talla"
        ),
        sa.ForeignKeyConstraint(
            ["color_id"], ["color.id"], name="fk_variante_producto_color_id_color"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_variante_producto"),
        sa.UniqueConstraint("sku", name="uq_variante_producto_sku"),
        # Una combinacion talla x color no se repite dentro del mismo producto:
        # es lo que vuelve segura la generacion automatica de variantes del
        # paso 6 de CU-10, porque reintentar no duplica.
        sa.UniqueConstraint(
            "producto_id", "talla_id", "color_id", name="uq_variante_producto_talla_color"
        ),
    )
    op.create_index("ix_variante_producto_producto_id", "variante_producto", ["producto_id"])
    op.create_index("ix_variante_producto_talla_id", "variante_producto", ["talla_id"])
    op.create_index("ix_variante_producto_color_id", "variante_producto", ["color_id"])

    op.create_table(
        "imagen_producto",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=True),
        sa.Column("ruta", sa.String(255), nullable=False),
        sa.Column("es_principal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("es_transparente", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("orden", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["producto.id"],
            name="fk_imagen_producto_producto_id_producto",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_imagen_producto_variante_id_variante_producto",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_imagen_producto"),
    )
    op.create_index("ix_imagen_producto_producto_id", "imagen_producto", ["producto_id"])
    op.create_index("ix_imagen_producto_variante_id", "imagen_producto", ["variante_id"])
    # Una sola imagen principal por producto: es la que muestra el listado del
    # catalogo (CU-17) y no puede haber dos candidatas.
    op.create_index(
        "uq_imagen_principal_producto",
        "imagen_producto",
        ["producto_id"],
        unique=True,
        postgresql_where=sa.text("es_principal"),
    )
    # Un solo PNG transparente por variante. Es el activo del que depende el
    # vestidor virtual (seccion 6.5, supuesto S5). Los dos indices parciales
    # copian el patron que el Ciclo 1 usa en uq_direccion_predeterminada.
    op.create_index(
        "uq_imagen_transparente_variante",
        "imagen_producto",
        ["variante_id"],
        unique=True,
        postgresql_where=sa.text("es_transparente"),
    )

    # ================= P1 - Seguridad (perfil del cliente) ===============
    # Cierra el diferimiento de la seccion 6.11.3: las categorias preferidas
    # esperaban a que el CU-08 creara categorias que elegir.
    op.create_table(
        "cliente_categoria",
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name="fk_cliente_categoria_cliente_id_cliente",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"],
            ["categoria.id"],
            name="fk_cliente_categoria_categoria_id_categoria",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("cliente_id", "categoria_id", name="pk_cliente_categoria"),
    )


def downgrade() -> None:
    # En orden inverso al alta: primero lo que referencia, despues lo
    # referenciado. Los indices caen con su tabla.
    op.drop_table("cliente_categoria")
    op.drop_table("imagen_producto")
    op.drop_table("variante_producto")
    op.drop_table("producto")
