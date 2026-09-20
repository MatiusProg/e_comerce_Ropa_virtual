"""Ciclo 3 - como se cobro una venta presencial, para que el arqueo signifique algo (CU-30).

POR QUE ESTO ES DE CU-30 Y NO DE CU-31
---------------------------------------
Parece dato de la venta ---y lo es--- pero lo que lo vuelve necesario es el
ARQUEO. `TurnoCaja.monto_esperado` esta definido como «apertura mas lo cobrado
en efectivo menos las devoluciones». Sin saber si cada venta se cobro en
efectivo o con tarjeta, esa cuenta no se puede hacer: o se suma todo ---y el
turno aparece descuadrado por cada pago con tarjeta--- o no se suma nada ---y
el esperado es siempre el monto de apertura, con lo cual el arqueo no compara
nada---.

Las dos salidas son peores que no tener la funcion, porque un arqueo que
siempre descuadra ensena a ignorarlo.

NULO EN LAS VENTAS DIGITALES, Y OBLIGATORIO EN LAS PRESENCIALES
----------------------------------------------------------------
Mismo patron que `turno_segun_canal` y `modalidad_segun_canal`, que ya estan
en la tabla. Una venta digital se cobra por la pasarela: el metodo lo sabe
Stripe y guardarlo aca seria copiar un dato del que no somos duenos. Una
presencial se cobra en el mostrador, y ahi el metodo es nuestro o no existe.

Las filas que YA ESTAN son todas digitales ---la venta presencial no se puede
registrar todavia, justamente porque falta CU-31--- asi que el CHECK entra sin
tener que rellenar nada. Se comprobo antes de escribir esto.

**En los CHECK va solo el sufijo.** La convencion de `app/db/base.py` antepone
`ck_<tabla>_` sola; pasar el nombre completo lo duplica.

SOBRE EL NUMERO
---------------
Cuelga de la `0013_ciclo3_recomendaciones`. Karen quedo avisada de que la 0014
la toma Mateo; la suya es la 0015 y cuelga de esta. Karen no escribio ninguna
migracion en CU-28, CU-29 ni CU-36, asi que el arbol sigue con una sola cabeza.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_ciclo3_metodo_pago"
down_revision: str | None = "0013_ciclo3_recomendaciones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Como se puede cobrar en el mostrador.
#:
#: `QR` esta porque en Bolivia el pago con codigo QR bancario es corriente y
#: **no es efectivo**: no entra al cajon y no puede sumar al arqueo. Meterlo
#: dentro de EFECTIVO seria descuadrar el turno por cada uno.
METODOS = ("EFECTIVO", "TARJETA", "QR")


def upgrade() -> None:
    op.add_column("venta", sa.Column("metodo_pago", sa.String(20), nullable=True))
    op.create_check_constraint(
        "metodo_pago",
        "venta",
        "metodo_pago IS NULL OR metodo_pago IN ('"
        + "', '".join(METODOS)
        + "')",
    )
    op.create_check_constraint(
        "metodo_segun_canal",
        "venta",
        "(canal = 'PRESENCIAL' AND metodo_pago IS NOT NULL)"
        " OR (canal = 'DIGITAL' AND metodo_pago IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_venta_metodo_segun_canal", "venta", type_="check")
    op.drop_constraint("ck_venta_metodo_pago", "venta", type_="check")
    op.drop_column("venta", "metodo_pago")
