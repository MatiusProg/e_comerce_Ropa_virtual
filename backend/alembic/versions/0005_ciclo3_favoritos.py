"""Ciclo 3 - CU-20: favoritos del cliente.

Agrega la tabla `favorito`, que es la PRIMERA tabla propia del paquete P5. Los
tres casos de uso del Ciclo 2 --- CU-17, CU-18 y CU-19 --- solo leian tablas de
P3 y P4, y por eso `catalogo_publico/models.py` estuvo vacio a proposito hasta
ahora.

SOBRE EL NUMERO
---------------
El identificador se reservo ANTES de escribir nada, en la seccion 4 de
docs/entregas/ciclo-2/04-respuesta-de-karen.md, que es donde Mateo pidio que se
acordaran despues de que su 0004 apareciera fuera del acuerdo original. Cuelga
de `0004_stock_minimo`, que es la cabeza actual.

Quedan reservadas ademas la `0006_ciclo3_ventas` y la `0007_ciclo3_promociones`,
las dos de Mateo. Dos revisiones con el mismo `down_revision` dejarian el arbol
con dos cabezas y `alembic upgrade head` fallaria pidiendo cual.

POR QUE UNA TABLA Y NO UNA COLUMNA
----------------------------------
Un cliente marca muchas prendas y una prenda la marcan muchos clientes: es una
relacion muchos a muchos y no cabe como atributo. Es el mismo razonamiento por
el que el Ciclo 1 creo `direccion_cliente` y el Ciclo 2 `cliente_categoria`.

Escrita A MANO, no con --autogenerate, como todas las del proyecto.

Revision ID: 0005_ciclo3_favoritos
Revises: 0004_stock_minimo
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_ciclo3_favoritos"
down_revision: str | None = "0004_stock_minimo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "favorito",
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Los dos con ON DELETE CASCADE: un favorito no tiene sentido sin su
        # cliente ni sin su producto, y no hay nada que conservar de el. Es
        # distinto de una venta, que sobrevive a la baja del producto porque es
        # un hecho historico.
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name="fk_favorito_cliente_id_cliente",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["producto.id"],
            name="fk_favorito_producto_id_producto",
            ondelete="CASCADE",
        ),
        # Clave primaria compuesta: un cliente marca una prenda una vez. Es lo
        # que vuelve idempotente al alta --- marcar dos veces no duplica --- sin
        # que el servicio tenga que comprobar antes de insertar.
        sa.PrimaryKeyConstraint("cliente_id", "producto_id", name="pk_favorito"),
    )

    # El listado del cliente siempre filtra por cliente y ordena por fecha
    # descendente. La clave primaria ya indexa `cliente_id` por la izquierda,
    # pero no sirve para el orden; con este indice la consulta no ordena en
    # memoria.
    op.create_index(
        "ix_favorito_cliente_creado", "favorito", ["cliente_id", "creado_en"]
    )


def downgrade() -> None:
    op.drop_index("ix_favorito_cliente_creado", table_name="favorito")
    op.drop_table("favorito")
