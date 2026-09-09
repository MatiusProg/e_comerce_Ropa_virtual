"""Ciclo 2 - inventario y reservas: existencia, movimiento, reserva y detalle.

Crea las cuatro tablas de los paquetes P4 y P6, con los nombres y tipos fijados
en la seccion 6.4 de docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md.

Escrita a mano, no con `--autogenerate`: autogenerar con los modelos del otro a
medio escribir produce migraciones que borran tablas ajenas (seccion 4 del
documento de organizacion).

DEPENDE DE LA 0002, QUE ES DE KAREN
-----------------------------------
`existencia.variante_id` y `reserva_detalle.variante_id` apuntan a
`variante_producto`, que nace en `0002_ciclo2_catalogo`. Por eso `down_revision`
la nombra: `alembic upgrade head` va a fallar hasta que esa migracion este en la
rama, y eso es correcto, no un error. Los identificadores se acordaron el primer
dia justamente para poder escribir las dos en paralelo (seccion 4).

Los nombres de restricciones e indices se escriben explicitos y coinciden con la
convencion de app/db/base.py. En los CHECK se pasa **solo el sufijo** ('estado',
no 'ck_reserva_estado'): la convencion antepone el resto, y pasar el nombre
completo lo duplica. Mismo criterio que la 0001.

Revision ID: 0003_ciclo2_inv_res
Revises: 0002_ciclo2_catalogo
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ciclo2_inv_res"
down_revision: str | None = "0002_ciclo2_catalogo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ================= P4 - Inventario ===================================
    op.create_table(
        "existencia",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column(
            "cantidad_disponible",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "cantidad_reservada",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_existencia"),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_existencia_variante_id_variante_producto",
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_id"],
            ["sucursal.id"],
            name="fk_existencia_sucursal_id_sucursal",
        ),
        # Un unico saldo por variante y sucursal. Es lo que permite que CU-22
        # bloquee "la" fila con SELECT ... FOR UPDATE (riesgo R5): si pudiera
        # haber dos, el bloqueo no serviria de nada.
        sa.UniqueConstraint(
            "variante_id", "sucursal_id", name="uq_existencia_variante_sucursal"
        ),
        sa.CheckConstraint(
            "cantidad_disponible >= 0", name="ck_existencia_disponible_no_negativa"
        ),
        sa.CheckConstraint(
            "cantidad_reservada >= 0", name="ck_existencia_reservada_no_negativa"
        ),
    )
    op.create_index(
        "ix_existencia_variante_id", "existencia", ["variante_id"], unique=False
    )
    op.create_index(
        "ix_existencia_sucursal_id", "existencia", ["sucursal_id"], unique=False
    )

    op.create_table(
        "movimiento_inventario",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("existencia_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=15), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_movimiento_inventario"),
        sa.ForeignKeyConstraint(
            ["existencia_id"],
            ["existencia.id"],
            name="fk_movimiento_inventario_existencia_id_existencia",
        ),
        # Sin ON DELETE: un usuario no se borra, se desactiva (CU-03), y el
        # historial tiene que seguir diciendo quien movio el stock.
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_movimiento_inventario_usuario_id_usuario",
        ),
        sa.CheckConstraint(
            "tipo IN ('INGRESO', 'RESERVA', 'LIBERACION', 'VENTA', "
            "'DEVOLUCION', 'TRANSFERENCIA', 'AJUSTE')",
            name="ck_movimiento_inventario_tipo",
        ),
        # La cantidad lleva signo -positiva entra, negativa sale-, de modo que
        # el saldo de una existencia es la suma de sus movimientos. Cero no es
        # un movimiento.
        sa.CheckConstraint(
            "cantidad <> 0", name="ck_movimiento_inventario_cantidad_no_nula"
        ),
    )
    op.create_index(
        "ix_movimiento_inventario_existencia_id",
        "movimiento_inventario",
        ["existencia_id"],
        unique=False,
    )
    op.create_index(
        "ix_movimiento_inventario_usuario_id",
        "movimiento_inventario",
        ["usuario_id"],
        unique=False,
    )

    # ================= P6 - Reservas ======================================
    op.create_table(
        "reserva",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("sucursal_id", sa.Integer(), nullable=False),
        sa.Column("franja_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("franja_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=10), nullable=False),
        sa.Column("observacion", sa.String(length=200), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reserva"),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["cliente.id"], name="fk_reserva_cliente_id_cliente"
        ),
        sa.ForeignKeyConstraint(
            ["sucursal_id"], ["sucursal.id"], name="fk_reserva_sucursal_id_sucursal"
        ),
        sa.CheckConstraint(
            "estado IN ('PENDIENTE', 'PREPARADA', 'ATENDIDA', "
            "'CANCELADA', 'EXPIRADA')",
            name="ck_reserva_estado",
        ),
        sa.CheckConstraint("franja_fin > franja_inicio", name="ck_reserva_franja"),
    )
    op.create_index("ix_reserva_cliente_id", "reserva", ["cliente_id"], unique=False)
    op.create_index("ix_reserva_sucursal_id", "reserva", ["sucursal_id"], unique=False)
    op.create_index("ix_reserva_estado", "reserva", ["estado"], unique=False)
    # CU-25 barre por franja vencida y estado vivo; el indice compuesto es el
    # que hace que esa tarea no recorra la tabla entera cada vez que corre.
    op.create_index(
        "ix_reserva_franja_fin_estado",
        "reserva",
        ["franja_fin", "estado"],
        unique=False,
    )

    op.create_table(
        "reserva_detalle",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("reserva_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("resultado_prueba", sa.String(length=10), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reserva_detalle"),
        sa.ForeignKeyConstraint(
            ["reserva_id"],
            ["reserva.id"],
            name="fk_reserva_detalle_reserva_id_reserva",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_reserva_detalle_variante_id_variante_producto",
        ),
        sa.UniqueConstraint(
            "reserva_id", "variante_id", name="uq_reserva_detalle_reserva_variante"
        ),
        sa.CheckConstraint("cantidad > 0", name="ck_reserva_detalle_cantidad_positiva"),
        sa.CheckConstraint(
            "resultado_prueba IS NULL OR resultado_prueba IN ('LLEVA', 'NO_LLEVA')",
            name="ck_reserva_detalle_resultado",
        ),
    )
    op.create_index(
        "ix_reserva_detalle_reserva_id", "reserva_detalle", ["reserva_id"], unique=False
    )
    op.create_index(
        "ix_reserva_detalle_variante_id",
        "reserva_detalle",
        ["variante_id"],
        unique=False,
    )


def downgrade() -> None:
    # En orden inverso al alta: primero lo que apunta, despues lo apuntado.
    op.drop_table("reserva_detalle")
    op.drop_table("reserva")
    op.drop_table("movimiento_inventario")
    op.drop_table("existencia")
