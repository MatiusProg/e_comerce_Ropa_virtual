"""Ciclo 3 - el anuncio se CIERRA cuando la mercaderia llega (CU-38 + CU-39).

EL HUECO QUE CIERRA
--------------------
La 0015 dejo esto anotado como pendiente, con estas palabras:

    NO SE CIERRA SOLO AL LLEGAR LA MERCADERIA. Cuando el ingreso de CU-13
    registra lo que llego, el anuncio sigue ANUNCIADO hasta que alguien lo
    cancela. Es deliberado y esta anotado como pendiente: atarlo al ingreso
    exige decidir que pasa si llega la mitad, o si llega de otro proveedor, y
    esas son reglas de negocio que nadie definio.

Al 20/09 esas reglas ya estan definidas, y el hueco se nota al usarlo: una
vez que una prenda aparece como «proxima a ingresar» **no hay forma de
recibirla**. Lo unico que hay es el ingreso directo de CU-13, que no sabe
nada del anuncio; asi que despues de que la mercaderia llega, el consolidado
sigue diciendo «+45 en camino» **sobre unidades que ya estan en el saldo**.
Las cuenta dos veces.

LAS REGLAS QUE FALTABAN
------------------------
1. **Llega la cantidad completa** -> el anuncio pasa a `RECIBIDO` y deja de
   sumar al «proximo a ingresar».
2. **Llega menos** -> el anuncio sigue `ANUNCIADO` **por el resto**. No se
   cierra: lo que falta sigue estando en camino, y cerrarlo haria desaparecer
   de la pantalla mercaderia que el proveedor todavia debe.
3. **Llega mas de lo anunciado** -> entra todo al inventario y el anuncio se
   cierra. El sobrante es un dato del remito, no un error que valga la pena
   rechazar: la mercaderia ya esta fisicamente en la tienda.
4. **Un ingreso sin anuncio** sigue funcionando igual que siempre. Atar el
   ingreso al anuncio de forma obligatoria romperia CU-13, que existe desde
   el Ciclo 1 y cubre la compra que nadie anuncio.

POR QUE `cantidad_recibida` Y NO SOLO EL ESTADO
------------------------------------------------
Porque sin ella una entrega parcial no se puede representar: o el anuncio
esta abierto por el total ---y el consolidado promete de mas--- o esta
cerrado ---y promete de menos---. Con el acumulado, lo que sigue en camino es
`cantidad - cantidad_recibida`, que es exactamente lo que falta.

Es un acumulado y no un reemplazo: una entrega puede venir en tres camiones.

POR QUE EL INDICE UNICO PARCIAL NO CAMBIA
-------------------------------------------
Sigue siendo sobre `estado = 'ANUNCIADO'`. Un anuncio RECIBIDO ya no bloquea
uno nuevo del mismo proveedor para la misma variante, que es justo lo que se
quiere: el proveedor vuelve a anunciar el lote siguiente.

SOBRE EL NUMERO
---------------
Cuelga de la `0017_ciclo3_bitacora`, de la misma tanda. Si Karen toma la 0018
antes, esta pasa a 0019: el `Dockerfile` corre `alembic upgrade head` en cada
despliegue y dos cabezas tumban el servidor.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

#: Corto a proposito: `alembic_version.version_num` es `varchar(32)` y
#: «0018_ciclo3_recepcion_de_anuncios» son 33 caracteres. La migracion
#: aplica el DDL y revienta al anotar la version, dejando la base migrada y
#: a Alembic creyendo que no lo esta.
revision: str = "0018_ciclo3_recepcion"
down_revision: str | None = "0017_ciclo3_bitacora"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `server_default="0"` y NOT NULL: las filas que ya existen no recibieron
    # nada todavia, y dejar la columna nula obligaria a un `coalesce` en cada
    # consulta del consolidado --- que es la que tiene que ser rapida.
    op.add_column(
        "abastecimiento",
        sa.Column(
            "cantidad_recibida",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # Cuando se completo. Nulo mientras siga en camino.
    op.add_column(
        "abastecimiento",
        sa.Column("recibido_en", sa.DateTime(timezone=True), nullable=True),
    )

    # El estado admite uno mas. Se recrea la restriccion porque PostgreSQL no
    # deja alterarla en el lugar.
    # `op.f(...)` marca el nombre como YA definitivo. Sin el, la convencion
    # `ck_%(table_name)s_%(constraint_name)s` de `db/base.py` le antepone la
    # tabla otra vez y busca `ck_abastecimiento_ck_abastecimiento_estado`.
    op.drop_constraint(
        op.f("ck_abastecimiento_estado"), "abastecimiento", type_="check"
    )
    op.create_check_constraint(
        "estado",
        "abastecimiento",
        "estado IN ('ANUNCIADO', 'CANCELADO', 'RECIBIDO')",
    )
    op.create_check_constraint(
        "recibida_no_negativa", "abastecimiento", "cantidad_recibida >= 0"
    )


def downgrade() -> None:
    # Los RECIBIDO vuelven a CANCELADO y no a ANUNCIADO: un anuncio recibido
    # ya no esta en camino, y devolverlo a ANUNCIADO haria que el consolidado
    # prometa otra vez mercaderia que ya esta en el saldo --- el defecto que
    # esta migracion vino a arreglar, reintroducido por la bajada.
    op.execute("UPDATE abastecimiento SET estado = 'CANCELADO' WHERE estado = 'RECIBIDO'")

    op.drop_constraint(
        "ck_abastecimiento_recibida_no_negativa", "abastecimiento", type_="check"
    )
    # `op.f(...)` marca el nombre como YA definitivo. Sin el, la convencion
    # `ck_%(table_name)s_%(constraint_name)s` de `db/base.py` le antepone la
    # tabla otra vez y busca `ck_abastecimiento_ck_abastecimiento_estado`.
    op.drop_constraint(
        op.f("ck_abastecimiento_estado"), "abastecimiento", type_="check"
    )
    op.create_check_constraint(
        "estado", "abastecimiento", "estado IN ('ANUNCIADO', 'CANCELADO')"
    )
    op.drop_column("abastecimiento", "recibido_en")
    op.drop_column("abastecimiento", "cantidad_recibida")
