"""Ciclo 3 - CU-26: carrito de compras.

Agrega `carrito` y `carrito_detalle`, las dos primeras tablas propias de P7.
El paquete existia como esqueleto desde el arranque del Ciclo 3 y su
`models.py` estaba vacio a proposito.

SOBRE EL NUMERO Y DE QUIEN CUELGA  ---  LEER ANTES DE ESCRIBIR LA 0006
----------------------------------------------------------------------
Es la segunda vez que hace falta decirlo, asi que conviene que quede claro de
una vez: **Alembic no mira el numero del archivo, mira `down_revision`**. El
numero es un nombre reservado; el orden lo fija la cadena.

Al 15/09/2026 la cabeza era `0008_ciclo3_recuperacion` y esta cuelga de ahi.

CONSECUENCIA PARA MATEO: la cabeza ya no es la 0008 sino ESTA. Su
`0006_ciclo3_ventas` tiene que declarar

    down_revision = "0009_ciclo3_carrito"

y no `0008_ciclo3_recuperacion`, que es lo que decia el aviso del PR #31. La
cadena queda `0005 -> 0008 -> 0009 -> 0006 -> 0007`. Se lee raro y es correcta.
Dos revisiones colgando de la misma dejarian el arbol con dos cabezas y
`alembic upgrade head` fallaria pidiendo cual.

POR QUE ESTAS DOS TABLAS Y NO LAS DE VENTAS
-------------------------------------------
`pedido`, `venta`, `caja` y sus detalles siguen reservados para la
`0006_ciclo3_ventas` de Mateo. El carrito es separable: existe antes del pedido
y sobrevive a que el cliente no compre. Estrenar solo lo que CU-26 necesita
respeta la reserva --- no se escribe su archivo ni se le adelantan sus tablas.

EL CARRITO NO GUARDA PRECIOS
----------------------------
No hay columna de precio en `carrito_detalle`, y es deliberado. Un carrito es
una INTENCION, no un contrato: el precio se fija cuando se genera el pedido
(CU-27), no cuando se agrega la prenda. Guardar una foto del precio dejaria al
carrito cotizando un valor que la tienda ya no sostiene, y el cliente lo
descubriria al pagar. El total se calcula al leer, contra `variante_producto`.

Es la misma familia de razonamiento que `favorito`, que tampoco guarda nada del
producto: lo que se guarda es la eleccion, no sus atributos.

EL CARRITO NO INMOVILIZA INVENTARIO
-----------------------------------
Agregar al carrito no descuenta ni aparta stock. Eso es lo que hace una RESERVA
(CU-22), que es un caso de uso distinto y ya existe: la reserva aparta unidades
desde que se crea hasta que su franja vence, justamente porque el cliente va a
ir a buscarlas. Un carrito que apartara stock dejaria inventario congelado por
cada cliente que abandona la compra --- que son casi todos.

La disponibilidad se COMPRUEBA al leer el carrito, para avisar, y se VALIDA en
serio al generar el pedido (CU-27).

Escrita A MANO, no con --autogenerate, como todas las del proyecto.

Revision ID: 0009_ciclo3_carrito
Revises: 0008_ciclo3_recuperacion
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_ciclo3_carrito"
down_revision: str | None = "0008_ciclo3_recuperacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "carrito",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # UNIQUE: un cliente, un carrito. No hay carritos guardados ni listas
        # multiples --- eso seria otro caso de uso --- y el UNIQUE es lo que
        # vuelve imposible que dos peticiones simultaneas del mismo cliente
        # creen dos carritos y una mitad de las prendas quede en cada uno.
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name="fk_carrito_cliente_id_cliente",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_carrito"),
        sa.UniqueConstraint("cliente_id", name="uq_carrito_cliente_id"),
    )

    op.create_table(
        "carrito_detalle",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("carrito_id", sa.BigInteger(), nullable=False),
        sa.Column("variante_id", sa.BigInteger(), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
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
        # El carrito se borra entero con su cliente y sus lineas con el.
        sa.ForeignKeyConstraint(
            ["carrito_id"],
            ["carrito.id"],
            name="fk_carrito_detalle_carrito_id_carrito",
            ondelete="CASCADE",
        ),
        # A la variante NO se le pone CASCADE: no se borra una variante que
        # esta en algun carrito, se desactiva. Si se borrara, la linea
        # desapareceria sin que el cliente entienda por que le falta algo.
        sa.ForeignKeyConstraint(
            ["variante_id"],
            ["variante_producto.id"],
            name="fk_carrito_detalle_variante_id_variante_producto",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_carrito_detalle"),
        # Una variante aparece UNA vez por carrito: agregarla de nuevo suma
        # cantidad, no crea otra linea. Sin esto el carrito mostraria la misma
        # prenda dos veces y el cliente no sabria cual editar.
        sa.UniqueConstraint(
            "carrito_id", "variante_id", name="uq_carrito_detalle_carrito_id"
        ),
        # La cantidad cero no es una linea: es una linea borrada. El nombre va
        # pelado porque la convencion de app/db/base.py lo expande.
        sa.CheckConstraint("cantidad > 0", name="cantidad_positiva"),
    )

    # El carrito se lee entero cada vez que se abre la pantalla, siempre
    # filtrando por carrito_id. El UNIQUE de arriba ya lo indexa por la
    # izquierda, asi que no hace falta otro indice.


def downgrade() -> None:
    op.drop_table("carrito_detalle")
    op.drop_table("carrito")
