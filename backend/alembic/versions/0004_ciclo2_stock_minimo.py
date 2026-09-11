"""Ciclo 2 - CU-16: umbral de reposicion por existencia, y arreglo de la 0003.

Agrega `existencia.stock_minimo`, que es lo que le da sentido a las «alertas de
stock bajo» que el CU-16 promete y que hasta ahora no tenian contra que
compararse.

Y corrige los ocho CHECK de la 0003, que quedaron con el prefijo duplicado. Ver
la nota al pie de este archivo.

POR QUE UNA 0004 Y NO UN CAMBIO EN LA 0003
------------------------------------------
La 0003 ya entro a `main` (PR #18) y se aplico. Editar una migracion aplicada
deja las bases que ya corrieron sin el cambio y sin forma de enterarse: Alembic
guarda que la revision se ejecuto, no que su contenido siga siendo el mismo. La
0003 se pudo editar el 10/09 justamente porque todavia no habia entrado a
ninguna rama compartida; hoy ya no.

SOBRE EL NUMERO
---------------
La seccion 4 del documento de organizacion solo acordo la 0002 (Karen) y la
0003 (Mateo). Esta 0004 es de Mateo y cuelga de la 0003. Si Karen necesita una
migracion propia en lo que queda del ciclo, hay que acordar su identificador
antes de escribirla: dos revisiones con `down_revision = "0003_ciclo2_inv_res"`
dejarian el arbol con dos cabezas y `upgrade head` fallaria pidiendo cual.

La columna es ADITIVA y con valor por defecto, asi que cumple la condicion de
forma de la seccion 3 de la contrapropuesta y no rompe ninguna fila existente.

Revision ID: 0004_stock_minimo
Revises: 0003_ciclo2_inv_res
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_stock_minimo"
down_revision: str | None = "0003_ciclo2_inv_res"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --- Arreglo de los CHECK de la 0003 -------------------------------------
#
# EL PROBLEMA
# -----------
# La convencion de `app/db/base.py` es `ck_%(table_name)s_%(constraint_name)s`:
# antepone sola la tabla, asi que a `name=` hay que pasarle SOLO el sufijo. La
# 0003 lo dice en su propia cabecera y despues lo hace al reves en las cuatro
# tablas, con lo que los ocho CHECK quedaron con el prefijo dos veces:
#
#     ck_existencia_ck_existencia_disponible_no_negativa
#     ck_movimiento_inventario_ck_movimiento_inventario_canti_3ab8
#                                                            ^^^^
# El ultimo encima se paso de los 63 caracteres que admite un identificador de
# PostgreSQL y el motor lo trunco con un hash.
#
# POR QUE IMPORTA, Y NO ES SOLO FEO
# ---------------------------------
# `Base.metadata.create_all()` --- que es con lo que las pruebas arman el
# esquema --- si aplica bien la convencion y genera los nombres CORTOS. Con lo
# cual la base de pruebas y la base migrada tenian nombres distintos para la
# misma restriccion. Cualquier codigo que distinga una violacion por el nombre
# de su restriccion, que es justo lo que hace el ayudante `_viola()` de varios
# servicios del Ciclo 1, pasaria en las pruebas y fallaria en produccion --- o
# al reves ---, y el sintoma seria un 500 en vez de un mensaje que se entiende.
#
# Renombrar es barato y no toca datos: un CHECK se identifica por nombre, y
# cambiarselo no lo re-valida ni bloquea la tabla mas que un instante.
RENOMBRES: tuple[tuple[str, str, str], ...] = (
    ("existencia", "ck_existencia_ck_existencia_disponible_no_negativa",
     "ck_existencia_disponible_no_negativa"),
    ("existencia", "ck_existencia_ck_existencia_reservada_no_negativa",
     "ck_existencia_reservada_no_negativa"),
    ("movimiento_inventario", "ck_movimiento_inventario_ck_movimiento_inventario_tipo",
     "ck_movimiento_inventario_tipo"),
    ("movimiento_inventario", "ck_movimiento_inventario_ck_movimiento_inventario_canti_3ab8",
     "ck_movimiento_inventario_cantidad_no_nula"),
    ("reserva", "ck_reserva_ck_reserva_estado", "ck_reserva_estado"),
    ("reserva", "ck_reserva_ck_reserva_franja", "ck_reserva_franja"),
    ("reserva_detalle", "ck_reserva_detalle_ck_reserva_detalle_cantidad_positiva",
     "ck_reserva_detalle_cantidad_positiva"),
    ("reserva_detalle", "ck_reserva_detalle_ck_reserva_detalle_resultado",
     "ck_reserva_detalle_resultado"),
)


def _renombrar(tabla: str, viejo: str, nuevo: str) -> None:
    """Renombra un CHECK solo si existe con el nombre viejo.

    Se comprueba antes en vez de renombrar a ciegas porque hay bases que nunca
    tuvieron el nombre mal: una creada con `create_all` --- las de prueba ---
    ya lo tiene corto. Un ALTER a secas fallaria ahi y dejaria la migracion sin
    poder correr contra media flota.
    """
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{viejo}'
                  AND conrelid = '{tabla}'::regclass
            ) THEN
                ALTER TABLE {tabla} RENAME CONSTRAINT "{viejo}" TO "{nuevo}";
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for tabla, viejo, nuevo in RENOMBRES:
        _renombrar(tabla, viejo, nuevo)

    op.add_column(
        "existencia",
        sa.Column(
            "stock_minimo",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    # Cero significa «sin alerta»; negativo no significa nada.
    op.create_check_constraint(
        "stock_minimo_no_negativo", "existencia", "stock_minimo >= 0"
    )


def downgrade() -> None:
    # SOLO el sufijo, igual que en `create_check_constraint`: la convencion de
    # `app/db/base.py` antepone `ck_existencia_` sola. Pasarle el nombre
    # completo produce `ck_existencia_ck_existencia_stock_minimo_no_negativo`,
    # que es exactamente el error que esta misma migracion viene a arreglar.
    op.drop_constraint("stock_minimo_no_negativo", "existencia", type_="check")
    op.drop_column("existencia", "stock_minimo")

    # Los nombres vuelven a como los dejo la 0003, con prefijo duplicado y
    # todo: un `downgrade` tiene que dejar la base como estaba, aunque como
    # estaba fuera peor. Si no se revirtiera, bajar y volver a subir daria un
    # error de «ya existe» en el renombrado de arriba.
    for tabla, viejo, nuevo in RENOMBRES:
        _renombrar(tabla, nuevo, viejo)
