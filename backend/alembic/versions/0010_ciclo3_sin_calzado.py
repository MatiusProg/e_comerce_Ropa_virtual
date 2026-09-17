"""Ciclo 3 - la tienda no vende zapatos: fuera `cliente.talla_calzado`.

Quita la columna que la `0001` le puso a `cliente` y que nunca apunto a nada.

POR QUE SE BORRA
----------------
**El negocio es ropa, no calzado.** No hay un solo tipo `CALZADO` en la tabla
`talla` ni un solo producto de calzado en el catalogo, ni sembrado ni en
produccion. La columna existe desde el Ciclo 1 por inercia del modelo inicial.

La consecuencia, hasta hoy, es que **el perfil del cliente pedia una talla de
calzado para una tienda sin zapatos**: un selector con numeros del 35 al 44 que
no se cruzan con nada y que no sirven para recomendar, filtrar ni vender.

Aclarado el 13/09: el negocio es principalmente ropa femenina. Puede haber una
categoria de varon a futuro; calzado no esta en el alcance.

SE PIERDEN DATOS, Y ES A PROPOSITO
-----------------------------------
En produccion hay **501 clientes con un valor escrito** en esta columna. Son
numeros que el formulario les hizo elegir y que el sistema nunca uso para nada.
Al quitar la columna se van.

Por eso el `downgrade` **no los devuelve**: vuelve a crear la columna, vacia.
Recuperar los valores exigiria haberlos copiado antes a otro lado, y copiar un
dato que se decidio no usar es quedarse con el problema con un nombre distinto.
Si alguna vez la tienda vende zapatos, la talla de calzado va a ser una fila de
`talla` con tipo CALZADO ---como las demas--- y no una columna suelta en
`cliente`.

SOBRE EL NUMERO Y DE QUIEN CUELGA  ---  LEER ANTES DE ESCRIBIR LA 0007
----------------------------------------------------------------------
Es la tercera vez que la cabeza se mueve en este ciclo, asi que otra vez:
**Alembic no mira el numero del archivo, mira `down_revision`.**

Cuando esta columna se anoto para borrar, la migracion iba a ser la `0009`. Ya
no: la `0009` la tomo el carrito (CU-26). El `0007` sigue reservado para las
promociones de Mateo (CU-12), asi que a esta le toca el `0010`.

Al 17/09/2026 la cabeza era `0006_ciclo3_ventas` y esta cuelga de ahi.

CONSECUENCIA PARA MATEO: la cabeza ya no es la 0006 sino ESTA. Su
`0007_ciclo3_promociones` tiene que declarar

    down_revision = "0010_ciclo3_sin_calzado"

La cadena queda `0005 -> 0008 -> 0009 -> 0006 -> 0010 -> 0007`. Se lee raro y es
correcta. Dos revisiones colgando de la misma dejarian el arbol con dos cabezas
y `alembic upgrade head` fallaria pidiendo cual.

NO ES ADITIVA: HAY QUE TOCAR OCHO PUNTAS
-----------------------------------------
Medido el 17/09, ademas de esta migracion:

  1. el modelo `Cliente`                          (seguridad/models.py)
  2. los dos esquemas de CU-04                    (seguridad/schemas.py)
  3. el servicio de perfil                        (seguridad/service.py)
  4. el sembrado                                  (db/seed_operacion.py)
  5. la prueba de CU-04                           (tests/test_cu04_perfil.py)
  6. el modelo y el formulario de la web          (frontend-web)
  7. los tres scripts de EA que generan los diagramas de datos y de clases
  8. el movil --- QUEDA PENDIENTE, ver la ficha; es de Mateo y lo esta tocando

La punta 8 no rompe nada mientras tanto: Pydantic ignora los campos que sobran,
asi que un movil que siga mandando `talla_calzado` recibe un 200 y el campo se
descarta. Lo unico que se ve es una fila vacia en su pantalla de perfil.

Escrita A MANO, no con --autogenerate, como todas las del proyecto.

Revision ID: 0010_ciclo3_sin_calzado
Revises: 0006_ciclo3_ventas
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_ciclo3_sin_calzado"
down_revision: str | None = "0006_ciclo3_ventas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("cliente", "talla_calzado")


def downgrade() -> None:
    """Devuelve la columna, VACIA. Ver la nota de cabecera.

    Nullable, como nacio en la `0001`: los 501 valores que habia no se
    recuperan, y una columna NOT NULL sin valores no se podria crear.
    """
    op.add_column(
        "cliente",
        sa.Column("talla_calzado", sa.String(10), nullable=True),
    )
