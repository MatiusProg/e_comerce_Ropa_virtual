"""Ciclo 3 - el cambio de prenda, como segundo flujo de CU-32.

QUE SE AGREGA Y POR QUE NO ES UNA TABLA NUEVA
----------------------------------------------
Un cambio es una devolucion que ademas vende: la prenda vieja vuelve al
inventario y otra sale. Lo que vuelve ya lo sabe expresar `devolucion` con sus
`detalle_devolucion`; lo que sale ya lo sabe expresar `venta` con sus
`detalle_venta`. Una tabla nueva tendria que volver a modelar una de las dos y
quedaria con la mitad de las reglas duplicadas --- el precio congelado, el
descuento de CU-12, el comprobante ---.

Asi que el cambio es **una fila de `devolucion` que apunta a una `venta`**.

LO QUE OBLIGA A DISTINGUIR `monto` DE `diferencia`
---------------------------------------------------
`devolucion.monto` significa, desde CU-30, **lo que sale del cajon**, y el
arqueo lo resta. En un cambio no sale nada por la prenda devuelta: su valor se
**acredita** contra la prenda nueva. Lo unico que se mueve en el cajon es la
diferencia entre las dos.

Por eso:

| columna | en una DEVOLUCION | en un CAMBIO |
|---|---|---|
| `monto` | el reintegro, si se pago en efectivo | siempre 0 |
| `diferencia` | siempre 0 | total nuevo - valor devuelto, CON SIGNO |

`diferencia` es la unica columna con signo de todo P7, y lo es a proposito:
positiva el cliente paga, negativa la tienda devuelve. Partirla en dos columnas
no negativas obligaria a un CHECK que impida que las dos tengan valor a la vez,
y a que cada consulta se acuerde de restar una y sumar la otra.

`CAMBIO` ENTRA COMO METODO DE PAGO DE LA VENTA, Y NO ES UN PARCHE
------------------------------------------------------------------
La venta nueva vale lo que vale la prenda que sale --- Bs 250 ---, no lo que
entro al cajon --- Bs 50 ---. `caja.repository.efectivo_cobrado` suma las
ventas cuyo `metodo_pago` es EFECTIVO, asi que marcarla como efectivo dejaria
el turno con un sobrante de 200 que nadie puede contar.

Se podria excluirla con un `NOT EXISTS` contra esta tabla en cada consulta del
arqueo. Se prefirio **darle su propio metodo**: el filtro que ya existia la
deja fuera sin condicion nueva, ninguna consulta futura puede olvidarse de
excluirla, y el desglose del cierre la muestra en su propia linea en vez de
esconderla --- la mercaderia si se movio, y el cajero lo sabe ---.

`CAMBIO` no es una forma de cobrar: no se puede elegir en la pantalla de venta
y no vale para `metodo_diferencia`. Por eso el modelo tiene dos tuplas,
`METODOS_PAGO` y `METODOS_VENTA`, y solo la segunda lo incluye.

La `UNIQUE` sobre `venta_cambio_id` queda igual: impide que dos devoluciones
reclamen la misma venta como suya.

EL PLAZO NO ES UNA COLUMNA
---------------------------
Ni la devolucion ni el cambio guardan «hasta cuando se podia»: se comparan
`venta.creado_en` contra `DEVOLUCION_PLAZO_DIAS` en el servicio. Guardarlo
seria congelar en cada fila una politica comercial que la tienda va a querer
cambiar, y ademas no se puede reconstruir hacia atras --- las devoluciones que
ya estan escritas se registraron sin plazo ninguno ---.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_ciclo3_cambio_prenda"
down_revision: str | None = "0019_caja_por_sucursal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- La venta del cambio necesita su propio metodo -------------------
    #
    # PostgreSQL no sabe ampliar un CHECK: se borra y se vuelve a crear con el
    # valor nuevo adentro. El orden importa --- primero el viejo, despues el
    # nuevo --- porque los dos se llaman igual.
    op.drop_constraint("metodo_pago", "venta", type_="check")
    op.create_check_constraint(
        "metodo_pago",
        "venta",
        "metodo_pago IS NULL"
        " OR metodo_pago IN ('EFECTIVO', 'TARJETA', 'QR', 'CAMBIO')",
    )

    # `server_default` en las tres columnas nuevas y no solo `nullable=False`:
    # la tabla puede tener devoluciones escritas y sin valor por defecto el
    # ALTER falla. Son ademas los valores correctos para lo ya escrito: todo lo
    # que existe hoy es una devolucion pura, sin venta y sin diferencia.
    op.add_column(
        "devolucion",
        sa.Column(
            "tipo", sa.String(length=12), nullable=False, server_default="DEVOLUCION"
        ),
    )
    op.add_column(
        "devolucion",
        sa.Column("venta_cambio_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "devolucion",
        sa.Column(
            "diferencia",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "devolucion",
        sa.Column("metodo_diferencia", sa.String(length=20), nullable=True),
    )

    op.create_foreign_key(
        "fk_devolucion_venta_cambio_id_venta",
        "devolucion",
        "venta",
        ["venta_cambio_id"],
        ["id"],
    )
    # Una venta es la contraparte de UN cambio. Sin esto, dos devoluciones
    # podrian apuntar a la misma venta nueva, y el historial no sabria cual de
    # las dos la explica.
    op.create_unique_constraint(
        "uq_devolucion_venta_cambio_id", "devolucion", ["venta_cambio_id"]
    )

    op.create_check_constraint(
        "tipo",
        "devolucion",
        "tipo IN ('DEVOLUCION', 'CAMBIO')",
    )
    # Un cambio sin venta nueva no es un cambio, y una devolucion con venta
    # nueva es un cambio mal etiquetado. La equivalencia impide las dos.
    op.create_check_constraint(
        "cambio_tiene_venta",
        "devolucion",
        "(tipo = 'CAMBIO') = (venta_cambio_id IS NOT NULL)",
    )
    # En un cambio la plata de la prenda vieja NO sale del cajon: se acredita.
    # Si `monto` pudiera valer algo, el arqueo restaria dos veces --- una por
    # `monto` y otra por la `diferencia` ---.
    op.create_check_constraint(
        "cambio_no_saca_del_cajon",
        "devolucion",
        "tipo = 'DEVOLUCION' OR monto = 0",
    )
    op.create_check_constraint(
        "devolucion_sin_diferencia",
        "devolucion",
        "tipo = 'CAMBIO' OR (diferencia = 0 AND metodo_diferencia IS NULL)",
    )
    # Una diferencia que se movio sin decir como se salda no se puede arquear;
    # un metodo sin diferencia que saldar es ruido que confunde el cierre.
    op.create_check_constraint(
        "metodo_si_hay_diferencia",
        "devolucion",
        "(diferencia <> 0) = (metodo_diferencia IS NOT NULL)",
    )
    op.create_check_constraint(
        "metodo_diferencia",
        "devolucion",
        "metodo_diferencia IS NULL"
        " OR metodo_diferencia IN ('EFECTIVO', 'TARJETA', 'QR')",
    )


def downgrade() -> None:
    op.drop_constraint("metodo_diferencia", "devolucion", type_="check")
    op.drop_constraint(
        "metodo_si_hay_diferencia", "devolucion", type_="check"
    )
    op.drop_constraint(
        "devolucion_sin_diferencia", "devolucion", type_="check"
    )
    op.drop_constraint(
        "cambio_no_saca_del_cajon", "devolucion", type_="check"
    )
    op.drop_constraint("cambio_tiene_venta", "devolucion", type_="check")
    op.drop_constraint("tipo", "devolucion", type_="check")
    op.drop_constraint("uq_devolucion_venta_cambio_id", "devolucion", type_="unique")
    op.drop_constraint(
        "fk_devolucion_venta_cambio_id_venta", "devolucion", type_="foreignkey"
    )
    op.drop_column("devolucion", "metodo_diferencia")
    op.drop_column("devolucion", "diferencia")
    op.drop_column("devolucion", "venta_cambio_id")
    op.drop_column("devolucion", "tipo")

    # Las ventas de cambio ya no existen ---acaban de perder la devolucion que
    # las explicaba--- pero sus filas siguen ahi con `metodo_pago = 'CAMBIO'`.
    # Sin esto, volver a crear el CHECK estrecho falla contra los datos, que es
    # la forma correcta de fallar: avisa en vez de borrar ventas en silencio.
    op.drop_constraint("metodo_pago", "venta", type_="check")
    op.create_check_constraint(
        "metodo_pago",
        "venta",
        "metodo_pago IS NULL OR metodo_pago IN ('EFECTIVO', 'TARJETA', 'QR')",
    )
