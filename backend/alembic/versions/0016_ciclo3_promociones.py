"""Ciclo 3 - promociones con vigencia sobre producto, categoria o temporada (CU-12, RF35).

LAS COLUMNAS QUE LA RECIBEN YA EXISTEN
---------------------------------------
`detalle_venta.descuento_unitario` y `venta.descuento` estan desde la
`0006_ciclo3_ventas`, en cero, con el CHECK `total = subtotal - descuento` ya
atado. Se pusieron entonces a proposito: agregarlas ahora obligaria a decidir
que descuento tenian las ventas ya hechas, y la respuesta correcta ---ninguno---
se pierde si la columna no estaba. Esta migracion no toca ninguna de las dos.

UN SOLO OBJETIVO, GARANTIZADO POR LA BASE
------------------------------------------
Tres claves foraneas nulables y un CHECK que exige exactamente una, coherente
con el `alcance` declarado. La alternativa ---una columna `objetivo_id`
generica con el alcance de discriminador--- es mas corta y **no puede tener
clave foranea**: nada impediria apuntar a una categoria borrada, y esa
promocion no se aplicaria nunca sin que nadie entendiera por que.

POR QUE `desde` Y `hasta` SON `date` Y NO `timestamptz`
--------------------------------------------------------
El resto del esquema usa `timestamptz` donde el dato ES un instante: la franja
de una reserva, el cierre de un turno. Una promocion no es un instante: quien
la carga piensa «del 1 al 15 de octubre». Guardar una marca de tiempo obligaria
a inventar una hora de corte que el Administrador nunca eligio.

La contracara es que hay que preguntar que dia es **en Bolivia** y no en el
servidor. Railway corre en UTC y ahi el dia cambia a las 20:00 hora boliviana:
una promocion que termina «el 30» dejaria de aplicar con la tienda abierta.
Lo resuelve `promociones_service._hoy()`.

SOBRE EL NUMERO, QUE CASI SALE MAL
-----------------------------------
La `0014` dejo anotado que «la de Karen es la 0015», asi que esta nacio siendo
la 0015 y colgando de la 0014. **Estaba mal**: entre medio Mateo escribio la
`0015_ciclo3_abastecimiento` para CU-39, que ya estaba en `main`. Dos 0015
hermanas dejan el arbol con dos cabezas y `alembic upgrade head` falla sin
decir cual es el problema.

Lo atrapo el propio `alembic upgrade` contra la base de pruebas, que estaba
sellada en la 0015 de Mateo y no encontraba esa revision en la rama. Esta pasa
a ser la **0016 y cuelga de la suya**; el arbol vuelve a tener una sola cabeza.

La leccion, que ya costo dos veces en este ciclo: **antes de numerar una
migracion hay que traer `main`**, no alcanza con mirar el head de la rama
propia.

**Los docs decian `0007_ciclo3_promociones`.** Ese numero se reservo temprano y
la cadena le paso por encima: un archivo `0007` que corre despues de la 0015
seria una trampa para el que lea la carpeta. Se corrigen las dos referencias.

**En los CHECK va solo el sufijo**: la convencion de `app/db/base.py` antepone
`ck_<tabla>_` sola, y pasar el nombre completo lo duplica. La 0014 lo deja
avisado y esta migracion lo hizo mal igual: quedaron cuatro
`ck_promocion_ck_promocion_...` hasta que `alembic check` los mostro.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_ciclo3_promociones"
down_revision: str | None = "0015_ciclo3_abastecimiento"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Los tres alcances del RF35.
ALCANCES = ("PRODUCTO", "CATEGORIA", "TEMPORADA")


def upgrade() -> None:
    op.create_table(
        "promocion",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("alcance", sa.String(10), nullable=False),
        # `producto.id` es BIGINT y los otros dos INTEGER. No es capricho: la
        # tabla de productos crece con el catalogo y las de categorias y
        # temporadas son maestros de unas decenas de filas. Poner Integer aca
        # lo atrapo `alembic check`.
        sa.Column(
            "producto_id",
            sa.BigInteger(),
            sa.ForeignKey("producto.id"),
            nullable=True,
        ),
        sa.Column(
            "categoria_id",
            sa.Integer(),
            sa.ForeignKey("categoria.id"),
            nullable=True,
        ),
        sa.Column(
            "temporada_id",
            sa.Integer(),
            sa.ForeignKey("temporada.id"),
            nullable=True,
        ),
        sa.Column("porcentaje", sa.Numeric(5, 2), nullable=False),
        sa.Column("desde", sa.Date(), nullable=False),
        sa.Column("hasta", sa.Date(), nullable=True),
        sa.Column(
            "activa", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "alcance IN ('" + "', '".join(ALCANCES) + "')",
            name="alcance",
        ),
        # El cero no es una promocion, es no tener ninguna. El 100 si: regalar
        # una prenda en liquidacion es una decision real.
        sa.CheckConstraint(
            "porcentaje > 0 AND porcentaje <= 100",
            name="porcentaje_acotado",
        ),
        sa.CheckConstraint(
            "hasta IS NULL OR hasta >= desde",
            name="vigencia_coherente",
        ),
        sa.CheckConstraint(
            "(alcance = 'PRODUCTO'  AND producto_id  IS NOT NULL"
            " AND categoria_id IS NULL AND temporada_id IS NULL)"
            " OR (alcance = 'CATEGORIA' AND categoria_id IS NOT NULL"
            " AND producto_id IS NULL AND temporada_id IS NULL)"
            " OR (alcance = 'TEMPORADA' AND temporada_id IS NOT NULL"
            " AND producto_id IS NULL AND categoria_id IS NULL)",
            name="un_objetivo_segun_alcance",
        ),
    )

    op.create_index("ix_promocion_alcance", "promocion", ["alcance"])
    op.create_index("ix_promocion_producto_id", "promocion", ["producto_id"])
    op.create_index("ix_promocion_categoria_id", "promocion", ["categoria_id"])
    op.create_index("ix_promocion_temporada_id", "promocion", ["temporada_id"])

    # La consulta que corre en CADA pagina de la vitrina, en cada carrito y en
    # cada cobro es «las promociones activas vigentes hoy». Sin este indice
    # recorre la tabla entera cada vez.
    op.create_index(
        "ix_promocion_vigencia", "promocion", ["activa", "desde", "hasta"]
    )


def downgrade() -> None:
    op.drop_index("ix_promocion_vigencia", table_name="promocion")
    op.drop_index("ix_promocion_temporada_id", table_name="promocion")
    op.drop_index("ix_promocion_categoria_id", table_name="promocion")
    op.drop_index("ix_promocion_producto_id", table_name="promocion")
    op.drop_index("ix_promocion_alcance", table_name="promocion")
    op.drop_table("promocion")
