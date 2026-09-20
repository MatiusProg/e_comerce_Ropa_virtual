"""Ciclo 3 - lo que el proveedor anuncia que va a traer (CU-39).

CIERRA EL AGUJERO H1, Y CON EL EL RF38
---------------------------------------
El enunciado pide que el inventario consolidado distinga cinco estados, entre
ellos «proxima a ingresar». `EstadoExistencia.PROXIMA_A_INGRESAR` esta
declarado desde el Ciclo 2 y **ninguna fila lo devuelve**, porque nada en el
sistema anuncia lo que esta por llegar: CU-13 registra la mercaderia *cuando
ya llego*.

Esta tabla es lo que faltaba. El proveedor declara que puede abastecer una
variante, cuanto y en cuantos dias; el consolidado lee eso y recien entonces
ese estado existe.

POR QUE CUELGA DE LA VARIANTE Y NO DEL PRODUCTO
------------------------------------------------
Porque el consolidado es por VARIANTE (decision D1): «hay 3 de la blusa» no
significa nada si no se dice de que talla y color. Un anuncio a nivel producto
obligaria a repartirlo entre variantes al mostrarlo, y ese reparto seria
inventado.

UN ANUNCIO VIGENTE POR PROVEEDOR Y VARIANTE
--------------------------------------------
Indice unico PARCIAL sobre los que estan en ANUNCIADO. Parcial y no UNIQUE
normal por lo mismo que en `turno_caja`: los cancelados son muchos y
legitimos, y prohibirlos impediria volver a anunciar algo que se cancelo.

Dos anuncios vigentes del mismo proveedor para la misma variante no es un dato
util sino una duda: el consolidado tendria que decidir si suma o si toma el
ultimo, y cualquiera de las dos sorprende a alguien. Si el proveedor quiere
cambiar la cantidad, edita el suyo.

NO SE CIERRA SOLO AL LLEGAR LA MERCADERIA
------------------------------------------
Cuando el ingreso de CU-13 registra lo que llego, el anuncio sigue ANUNCIADO
hasta que alguien lo cancela. Es deliberado y esta anotado como pendiente:
atarlo al ingreso exige decidir que pasa si llega la mitad, o si llega de otro
proveedor, y esas son reglas de negocio que nadie definio. Adivinarlas seria
peor que dejar el cierre a mano.

SOBRE EL NUMERO
---------------
Cuelga de la `0014_ciclo3_metodo_pago`. **Karen tenia anotada la 0015**, pero
al 20/09 no escribio ninguna migracion en CU-28, CU-29, CU-30-UI, CU-31 ni
CU-32, y se verifico su rama antes de tomar este numero. **La suya pasa a ser
la 0016 y cuelga de esta.**
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_ciclo3_abastecimiento"
down_revision: str | None = "0014_ciclo3_metodo_pago"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: En que puede estar un anuncio.
ESTADOS = ("ANUNCIADO", "CANCELADO")


def upgrade() -> None:
    op.create_table(
        "abastecimiento",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("proveedor_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        # En DIAS y no una fecha: el proveedor piensa en «te lo tengo en una
        # semana», no en «el 27 de septiembre». Guardar la fecha obligaria a
        # recalcularla cada vez que el anuncio se edita, y a decidir que pasa
        # con una fecha que ya paso --- que con dias no se plantea.
        sa.Column("dias_plazo", sa.Integer(), nullable=False),
        sa.Column("observacion", sa.String(200), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False, server_default="ANUNCIADO"),
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
        sa.CheckConstraint("cantidad > 0", name="cantidad_positiva"),
        # 0 dias es valido: «lo tengo ahora». 365 es el tope de lo creible;
        # un plazo de tres anos es un dato mal cargado, no una promesa.
        sa.CheckConstraint("dias_plazo BETWEEN 0 AND 365", name="plazo_razonable"),
        sa.CheckConstraint(
            "estado IN ('" + "', '".join(ESTADOS) + "')", name="estado"
        ),
        sa.ForeignKeyConstraint(
            ["proveedor_id"],
            ["proveedor.id"],
            name="fk_abastecimiento_proveedor_id_proveedor",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_abastecimiento_variante_id_variante_producto",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_abastecimiento"),
    )

    # El proveedor lista LOS SUYOS, incluidos los cancelados. El indice
    # parcial de abajo no sirve para eso ---solo cubre los ANUNCIADO---, asi
    # que hace falta este aparte. Lo detecto `alembic check`: el modelo lo
    # declaraba con `index=True` y la migracion no lo creaba, que es la misma
    # desviacion que ya costo una migracion de arreglo en el Ciclo 2.
    op.create_index(
        "ix_abastecimiento_proveedor_id", "abastecimiento", ["proveedor_id"]
    )

    # Un anuncio VIGENTE por proveedor y variante. Parcial: los cancelados se
    # pueden repetir, y tienen que poder repetirse.
    op.create_index(
        "ix_abastecimiento_vigente",
        "abastecimiento",
        ["proveedor_id", "variante_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'ANUNCIADO'"),
    )

    # El consolidado pregunta «que variantes tienen algo anunciado» para TODA
    # una pagina de resultados. Sin este indice, esa consulta recorre la tabla
    # entera en cada carga del inventario.
    op.create_index(
        "ix_abastecimiento_variante_estado",
        "abastecimiento",
        ["variante_id", "estado"],
    )


def downgrade() -> None:
    op.drop_index("ix_abastecimiento_variante_estado", table_name="abastecimiento")
    op.drop_index("ix_abastecimiento_proveedor_id", table_name="abastecimiento")
    op.drop_index("ix_abastecimiento_vigente", table_name="abastecimiento")
    op.drop_table("abastecimiento")
