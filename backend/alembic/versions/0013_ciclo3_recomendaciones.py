"""Ciclo 3 - la recomendacion vigente de cada cliente (CU-33).

QUE GUARDA, Y POR QUE HACE FALTA GUARDARLO
-------------------------------------------
CU-33 es hibrido: un filtro determinista en SQL elige las candidatas y un
modelo las ordena. El primer paso es barato; el segundo **tarda segundos,
depende de un tercero y tiene cuota**.

Sin guardar nada, cada vez que el cliente abre la pantalla de inicio se llama
al modelo. En una demostracion eso es entrar y salir cinco veces y agotar el
plan gratuito delante del tribunal --- que es exactamente el riesgo R9 del
plan. Con la recomendacion guardada, se llama una vez cada varias horas.

UNA FILA POR CLIENTE, NO UN HISTORIAL
--------------------------------------
`UNIQUE (cliente_id)`: lo que interesa es la recomendacion VIGENTE. Guardar
todas las que se generaron obligaria a cada consulta a preguntarse cual es la
buena, y la respuesta dependeria del orden. Si alguna vez se quiere analizar
como evolucionaron, eso es una tabla de historial aparte y con otro proposito.

POR QUE LAS SUGERENCIAS VAN EN JSON Y NO EN UNA TABLA HIJA
-----------------------------------------------------------
Porque **no son datos del negocio, son un resultado**. Nadie va a consultar
«que clientes tienen la prenda 12 recomendada», ni a unir esta tabla con
ventas. Se escribe entera y se lee entera. Una tabla hija con seis filas por
cliente daria integridad referencial que no aporta ---si la prenda se
descataloga, la recomendacion se regenera igual--- a cambio de un JOIN en cada
lectura.

Lo que SI se guarda aparte es `motor`: con que se genero. Sirve para saber, al
mirar produccion, si el modelo esta funcionando o si todo el mundo esta
recibiendo el resultado degradado por popularidad --- que se ve igual de bien
y no avisa de nada.

SOBRE EL NUMERO
---------------
Cuelga de la `0012_ciclo3_foto_real`. Karen quedo avisada de que Mateo toma la
0011, la 0012 y esta 0013; la suya pasa a ser la 0014 y cuelga de esta. No
sirve dejarle un hueco: dos revisiones colgando de la 0012 dejan el arbol con
dos cabezas igual, y `alembic upgrade head` deja de saber que hacer --- que en
esta aplicacion tira la API abajo, porque el arranque del contenedor la corre.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_ciclo3_recomendaciones"
down_revision: str | None = "0012_ciclo3_foto_real"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recomendacion",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "generada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Con que se produjo: el modelo, o el orden por popularidad cuando el
        # modelo no estaba disponible.
        sa.Column("motor", sa.String(30), nullable=False),
        # JSONB y no JSON: ocupa menos y se puede indexar si alguna vez hace
        # falta. La forma es [{"producto_id": 12, "motivo": "..."}].
        sa.Column(
            "sugerencias",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
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
        # Que sea una lista, no un objeto ni un numero suelto. Sin esto, un
        # error del proveedor que devuelva `{}` se guarda y la pantalla recibe
        # algo que no sabe recorrer.
        sa.CheckConstraint(
            "jsonb_typeof(sugerencias) = 'array'", name="sugerencias_es_lista"
        ),
        sa.CheckConstraint("length(motor) > 0", name="motor"),
        sa.ForeignKeyConstraint(
            ["cliente_id"],
            ["cliente.id"],
            name="fk_recomendacion_cliente_id_cliente",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recomendacion"),
        sa.UniqueConstraint("cliente_id", name="uq_recomendacion_cliente_id"),
    )


def downgrade() -> None:
    op.drop_table("recomendacion")
