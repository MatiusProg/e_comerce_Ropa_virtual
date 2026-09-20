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

SOBRE EL NUMERO: NACIO 0017 Y CHOCO CON LA DE MATEO
----------------------------------------------------
Nacio como `0017_caja_por_sucursal` colgando de la `0016`, que era el head de
`main` en ese momento. **Mateo tenia una `0017_ciclo3_bitacora` colgando de la
misma**, todavia sin mergear, y encima una `0018_ciclo3_recepcion`.

Al traer `main` el arbol quedo con **dos cabezas** y `alembic upgrade head`
empezo a fallar. Se re-encadeno aca ---quien mergea segundo es quien
re-encadena--- y pasa a ser la **0019, colgando de la 0018**. El arbol vuelve a
tener una sola cabeza.

Es la tercera vez en el Ciclo 3 que la numeracion sale mal, y las tres se
atraparon corriendo migraciones, nunca antes. **No hay nada en el repositorio
que lo impida**: la unica defensa es avisarse antes de numerar, y mirar tambien
la rama del otro, no solo `main`.

LO QUE ESTO NO RESUELVE
-----------------------
**Una sucursal creada despues de esta migracion sigue naciendo sin caja.** Esto
tapa el agujero de hoy, no el de manana: lo que falta de verdad es el alta de
cajas por API, que seria del Administrador y no entro en el alcance del ciclo.
Queda anotado en la ficha de CU-30.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019_caja_por_sucursal"
down_revision: str | None = "0018_ciclo3_recepcion"
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
