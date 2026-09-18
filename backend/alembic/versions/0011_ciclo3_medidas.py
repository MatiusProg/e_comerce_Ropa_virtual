"""Ciclo 3 - medidas del cliente y tabla de tallas, para el vestidor (CU-21).

QUE PROBLEMA RESUELVE
---------------------
Hasta hoy el vestidor escala la prenda para que CALCE el cuerpo, siempre. La
consecuencia es que **la XS y la XXL se ven identicas en pantalla**: el cliente
elige talla sin que la pantalla le diga nada, que es justo lo que un probador
tendria que resolver.

Con las medidas del cliente y las de la prenda, la razon entre las dos decide
como se dibuja: una prenda mas chica que el cuerpo sale ajustada y corta, una
mas grande sale holgada. Y de paso se puede recomendar la talla.

DOS TABLAS, Y POR QUE SEPARADAS
--------------------------------
`medida_cliente` guarda el CUERPO de una persona; `medida_talla`, la PRENDA.
Son cosas distintas y se confunden facil al leer una tabla de tallas: los
centimetros que publica una marca a veces son del cuerpo al que le queda bien
la prenda y a veces de la prenda estirada sobre la mesa. Aca `medida_talla` es
siempre **la prenda**, ya con su holgura adentro, porque es lo que gobierna el
dibujo.

POR QUE LA TABLA DE TALLAS CUELGA DEL PRODUCTO Y NO SOLO DE LA TALLA
---------------------------------------------------------------------
Porque una M de blusa no mide lo mismo que una M de casaca, y sobre todo
porque **asi funciona el mercado real**: SHEIN, que es de donde vienen la
mayoria de las prendas que se consiguen hoy, no publica una tabla unica ---
cada proveedor sube la suya por producto, y dos «L» de la misma tienda pueden
medir distinto. Una tabla global por talla seria mas comoda y mentirosa.

`UNIQUE (producto_id, talla_id)`: un producto tiene una sola fila por talla.

`medida_cliente` lleva `UNIQUE (cliente_id)`: un cuerpo, un juego de medidas.
No se guarda historial. Si alguna vez interesa ver como cambiaron, va a ser
una tabla de historial aparte y no filas repetidas aca, que obligarian a todas
las consultas a preguntarse cual es la vigente.

LOS CHECK NO SON DECORACION
----------------------------
Un busto de 8 cm o de 400 no es un cliente raro: es un formulario que mando
pulgadas, o metros, o un campo vacio que llego como cero. Sin el CHECK, ese
dato entra y el vestidor dibuja una prenda absurda sobre el cuerpo sin que
nada avise. Los rangos son anchos a proposito --- no es validacion de negocio,
es un filtro de disparates.

**En los CHECK va solo el sufijo** ('busto', no 'ck_medida_cliente_busto'): la
convencion de `app/db/base.py` antepone 'ck_<tabla>_' sola, y pasar el nombre
completo lo DUPLICA. Ya paso en la 0003 y costo la 0004 para arreglarlo.

SOBRE EL NUMERO
---------------
Al 18/09/2026 la cabeza era `0010_ciclo3_sin_calzado` y esta cuelga de ahi. El
`0007` sigue reservado para las promociones de Mateo (CU-12). Karen esta en
CU-28: quedo avisada de que el `0011` lo toma Mateo, asi que si le hace falta
una migracion va a la `0012`. Dos revisiones colgando de la misma dejarian el
arbol con dos cabezas y `alembic upgrade head` deja de saber que hacer.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_ciclo3_medidas"
down_revision: str | None = "0010_ciclo3_sin_calzado"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medida_cliente",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        # Numeric y no Float: son centimetros con un decimal, y el redondeo
        # binario de un float se ve en la pantalla del cliente como 87.99999.
        sa.Column("busto_cm", sa.Numeric(5, 1), nullable=False),
        sa.Column("cintura_cm", sa.Numeric(5, 1), nullable=False),
        sa.Column("cadera_cm", sa.Numeric(5, 1), nullable=False),
        # La altura es opcional: no hace falta para elegir talla de blusa, pero
        # si para el largo de un pantalon o un vestido.
        sa.Column("altura_cm", sa.Numeric(5, 1), nullable=True),
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
        sa.CheckConstraint("busto_cm BETWEEN 50 AND 200", name="busto"),
        sa.CheckConstraint("cintura_cm BETWEEN 40 AND 200", name="cintura"),
        sa.CheckConstraint("cadera_cm BETWEEN 50 AND 200", name="cadera"),
        sa.CheckConstraint(
            "altura_cm IS NULL OR altura_cm BETWEEN 100 AND 230", name="altura"
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name="fk_medida_cliente_cliente_id_cliente",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_medida_cliente"),
        sa.UniqueConstraint("cliente_id", name="uq_medida_cliente_cliente_id"),
    )

    op.create_table(
        "medida_talla",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("producto_id", sa.BigInteger(), nullable=False),
        sa.Column("talla_id", sa.Integer(), nullable=False),
        # Medidas DE LA PRENDA, con su holgura ya adentro.
        sa.Column("busto_cm", sa.Numeric(5, 1), nullable=False),
        sa.Column("cintura_cm", sa.Numeric(5, 1), nullable=False),
        sa.Column("cadera_cm", sa.Numeric(5, 1), nullable=False),
        # De hombro a ruedo. Es lo que hace que una XS se vea CORTA y no solo
        # angosta --- sin esto, el largo lo seguiria mandando el torso de la
        # persona y todas las tallas caerian a la misma altura.
        sa.Column("largo_cm", sa.Numeric(5, 1), nullable=False),
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
        sa.CheckConstraint("busto_cm BETWEEN 30 AND 250", name="busto"),
        sa.CheckConstraint("cintura_cm BETWEEN 30 AND 250", name="cintura"),
        sa.CheckConstraint("cadera_cm BETWEEN 30 AND 250", name="cadera"),
        sa.CheckConstraint("largo_cm BETWEEN 20 AND 200", name="largo"),
        sa.ForeignKeyConstraint(
            ["producto_id"],
            ["producto.id"],
            name="fk_medida_talla_producto_id_producto",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["talla_id"],
            ["talla.id"],
            name="fk_medida_talla_talla_id_talla",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_medida_talla"),
        sa.UniqueConstraint(
            "producto_id", "talla_id", name="uq_medida_talla_producto_talla"
        ),
    )
    # La ficha pide todas las tallas de UN producto de una vez, para poder
    # comparar entre si y recomendar. El UNIQUE de arriba ya sirve de indice
    # para ese acceso porque `producto_id` va primero.


def downgrade() -> None:
    op.drop_table("medida_talla")
    op.drop_table("medida_cliente")
