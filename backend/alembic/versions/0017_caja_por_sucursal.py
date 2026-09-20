"""Ciclo 3 - una caja en cada sucursal que no tenga ninguna (CU-30, CU-31, CU-32).

POR QUE ESTO ES UNA MIGRACION Y NO EL SEMBRADO
-----------------------------------------------
Ya estaba en `seed_catalogo._cajas`, y ahi seguia sirviendo para una base
nueva. El problema es **cuando corre**: el `Dockerfile` del despliegue ejecuta
`alembic upgrade head` y nada mas. El sembrado lo corre una persona, a mano, y
produccion se habia sembrado ANTES de que CU-30 existiera.

Resultado, comprobado el 20/09/2026 contra la base de produccion: las **seis**
sucursales tenian cero cajas. CU-30, CU-31 y CU-32 estaban construidos,
desplegados, probados... y eran **imposibles de usar**. El cajero entraba a
`/caja`, veia la lista vacia y no habia ningun error que lo explicara ---
parecia que la pantalla no cargaba.

El propio docstring de `seed_catalogo._cajas` advertia exactamente eso. La
advertencia estaba escrita y aun asi paso, porque quedaba en manos de que
alguien se acordara de correr el sembrado. Una migracion no se olvida: va con
el despliegue.

POR QUE ES IDEMPOTENTE Y NO BORRA NADA
---------------------------------------
El `WHERE NOT EXISTS` deja fuera a toda sucursal que ya tenga una caja, sea la
que creo el sembrado o una que alguien agrego despues. Correr esto sobre una
base que ya esta bien no cambia una sola fila.

El `downgrade` **no borra las cajas**. Podria parecer lo simetrico, pero seria
destruir datos de operacion: para cuando alguien baje esta migracion, esas
cajas ya tienen turnos y ventas colgando, y el borrado se los llevaria por
delante o fallaria contra la clave foranea. Una migracion que crea filas de
arranque no tiene inversa razonable, y es mas honesto decirlo que fingirla.

!! ATENCION AL NUMERO: HAY UNA 0017 DE MATEO SIN MERGEAR !!
------------------------------------------------------------
Esta cuelga de la `0016_ciclo3_promociones`, que es el head de `main` hoy.
**Mateo tiene una `0017_ciclo3_bitacora` que cuelga de la misma**, todavia en
su rama, y encima una `0018_ciclo3_recepcion`. Las corrio contra la base de
pruebas, que es compartida, y por eso aparecio el choque.

Cuando las dos ramas esten en `main`, el arbol va a tener **dos cabezas** y
`alembic upgrade head` va a fallar diciendo «multiple heads». **Quien mergee
segundo tiene que re-encadenar**: cambiar el `down_revision` de su migracion
para que cuelgue de la del otro, o crear una revision de merge.

No se colgo de la 0018 de Mateo directamente porque esa revision **no existe en
esta rama**: `alembic upgrade head` fallaria aca y no se podria correr la
suite. Es el precio de que las dos ramas escriban migraciones a la vez, y la
unica salida buena es avisarse antes de numerar --- que es la leccion que ya
costo tres veces en este ciclo.

LO QUE ESTO NO RESUELVE
-----------------------
**Una sucursal creada despues de esta migracion sigue naciendo sin caja.** Esto
tapa el agujero de hoy, no el de manana: lo que falta de verdad es el alta de
cajas por API, que seria del Administrador y no entro en el alcance del ciclo.
Queda anotado en la ficha de CU-30.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017_caja_por_sucursal"
down_revision: str | None = "0016_ciclo3_promociones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO caja (sucursal_id, nombre, activa)
        SELECT s.id, 'Caja 1', true
        FROM sucursal s
        WHERE NOT EXISTS (
            SELECT 1 FROM caja c WHERE c.sucursal_id = s.id
        )
        """
    )


def downgrade() -> None:
    """A proposito no hace nada. Ver el encabezado."""
