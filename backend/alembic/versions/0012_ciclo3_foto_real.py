"""Ciclo 3 - distinguir la FOTO de una prenda del dibujo que la reemplaza (CU-21).

QUE PROBLEMA RESUELVE
---------------------
El vestidor muestra dos cosas que no son lo mismo y hasta hoy la base no podia
diferenciarlas:

  - **la foto real** de la prenda, recortada con fondo transparente;
  - **la silueta que dibuja el sembrado**, un relleno de color con hombros
    rectos que existe para que el supuesto S5 ---«hay un PNG con alfa»--- se
    cumpla para todas las variantes.

Las dos viven en `imagen_producto` con `es_transparente` en verdadero, asi que
son indistinguibles para cualquier consulta. La consecuencia se ve al abrir el
probador: **la primera prenda que ofrece es un dibujo**, porque el orden sale
del id y no de si la imagen vale la pena mirarse.

POR QUE LA COLUMNA DICE «GENERADA» Y NO «REAL»
-----------------------------------------------
Porque el valor por omision tiene que ser el caso bueno. Una imagen que sube un
administrador por CU-11 **es una foto**: si la columna dijera `es_foto_real`
con omision en falso, cada carga nueva nacetria marcada como dibujo y habria
que acordarse de corregirla. Al reves, lo unico que hay que marcar es lo que
genera el propio sembrado, que lo hace solo.

SE MARCA TODO LO QUE YA ESTA
-----------------------------
El `UPDATE` de abajo marca como generadas **todas** las imagenes de vestidor
existentes. Es correcto al 18/09/2026: en produccion las 59 que hay salieron
del sembrado, y no hay ninguna foto real cargada todavia. La primera foto que
se suba despues de esta migracion queda bien sin tocar nada.

Si alguna vez se corriera esta migracion sobre una base que YA tuviera fotos
reales, habria que desmarcarlas a mano. Se prefiere ese riesgo, que es visible
---una foto real se ve---, antes que dejar las 59 siluetas mezcladas con las
fotos, que es invisible.

SOBRE EL NUMERO
---------------
Cuelga de la `0011_ciclo3_medidas`, que es de esta misma sesion. Karen esta en
CU-28 y quedo avisada: Mateo toma la 0011 y la 0012, asi que si le hace falta
una migracion va a la 0013. Dos revisiones colgando de la misma dejarian el
arbol con dos cabezas y `alembic upgrade head` deja de saber que hacer.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_ciclo3_foto_real"
down_revision: str | None = "0011_ciclo3_medidas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "imagen_producto",
        sa.Column(
            "es_silueta_generada",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    # Todo lo que hay hoy salio del sembrado. Ver el encabezado.
    op.execute(
        "UPDATE imagen_producto SET es_silueta_generada = true"
        " WHERE es_transparente"
    )


def downgrade() -> None:
    op.drop_column("imagen_producto", "es_silueta_generada")
