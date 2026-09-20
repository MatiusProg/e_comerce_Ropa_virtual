"""Ciclo 3 - la bitacora del sistema (CU-42).

QUE HUECO CIERRA, Y POR QUE NO LO CERRABA EL RNF10
---------------------------------------------------
El RNF10 exige trazabilidad, pero **solo de existencias**: cada modificacion
de inventario queda como un `movimiento_inventario` inmutable. Eso cubre la
mercaderia y nada mas.

No hay ningun registro de quien inicio sesion, quien cambio un precio, quien
desactivo un producto, quien dio de baja a un empleado ni quien abrio una
caja. En un sistema con cinco roles y operaciones sobre dinero eso es un
agujero: cuando algo aparece cambiado, no hay como saber quien lo cambio.

Esta tabla lo cierra, y con ella el **RNF14** que se agrego al documento de
requisitos.

INMUTABLE, COMO EL MOVIMIENTO DE INVENTARIO
--------------------------------------------
Misma decision **D4**: no hay `actualizado_en` y la API no expone ni un
`POST`, ni un `PATCH`, ni un `DELETE` sobre esta tabla. Una bitacora que se
puede corregir no prueba nada --- justamente quien tendria motivo para
alterarla es quien tiene el rol para leerla.

POR QUE `usuario_id` ES NULO Y ADEMAS SE COPIA EL CORREO
---------------------------------------------------------
Nulo porque **un intento de sesion con un correo que no existe es lo mas
interesante que puede registrar una bitacora**, y exigir un usuario dejaria
fuera justo ese caso.

Y el correo se copia en `actor` aunque ya este en `usuario`, a proposito: la
clave foranea es `ON DELETE SET NULL` ---borrar una cuenta no puede borrar
el rastro de lo que hizo--- y sin la copia el asiento quedaria anonimo. Lo
mismo con `rol`: los roles se reasignan, y la bitacora tiene que decir con
cual se actuo ENTONCES.

POR QUE NO SE GUARDAN LAS LECTURAS
-----------------------------------
Solo POST, PUT, PATCH y DELETE. Anotar cada `GET` serian miles de filas por
dia ---cada pantalla del catalogo son varias--- y volveria inutilizable la
pantalla que existe para buscar en ellas.

SOBRE EL NUMERO
---------------
Cuelga de la `0016_ciclo3_promociones`, que es de Karen y ya esta aplicada
en produccion. Al 20/09 es la cabeza; **si Karen toma la 0017 antes, esta
pasa a 0018** --- el `Dockerfile` corre `alembic upgrade head` en cada
despliegue y dos cabezas tumban el servidor, como paso con la 0016.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_ciclo3_bitacora"
down_revision: str | None = "0016_ciclo3_promociones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bitacora",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "ocurrido_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        # 160: el correo mas largo que acepta `usuario.correo`.
        sa.Column("actor", sa.String(length=160), nullable=True),
        sa.Column("rol", sa.String(length=40), nullable=True),
        sa.Column("accion", sa.String(length=40), nullable=False),
        sa.Column("entidad", sa.String(length=60), nullable=True),
        # Texto y no entero: hay recursos identificados por codigo y otros
        # por clave compuesta, y un entero obligaria a dejarlo nulo ahi.
        sa.Column("entidad_id", sa.String(length=60), nullable=True),
        sa.Column("metodo", sa.String(length=10), nullable=False),
        sa.Column("ruta", sa.String(length=300), nullable=False),
        sa.Column("estado_http", sa.Integer(), nullable=False),
        sa.Column("exito", sa.Boolean(), nullable=False),
        sa.Column("ip", sa.String(length=60), nullable=True),
        sa.Column("agente", sa.String(length=200), nullable=True),
        sa.Column(
            "detalle",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name=op.f("fk_bitacora_usuario_id_usuario"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bitacora")),
    )
    op.create_index(
        op.f("ix_bitacora_accion"), "bitacora", ["accion"], unique=False
    )
    op.create_index(
        op.f("ix_bitacora_entidad"), "bitacora", ["entidad"], unique=False
    )
    op.create_index(
        op.f("ix_bitacora_ocurrido_en"), "bitacora", ["ocurrido_en"], unique=False
    )
    op.create_index(
        op.f("ix_bitacora_usuario_id"), "bitacora", ["usuario_id"], unique=False
    )
    # Compuesto: el uso real es «que hizo fulano ultimamente». Sin el, hay
    # que leer todas las filas de esa persona antes de ordenarlas por fecha.
    op.create_index(
        "ix_bitacora_usuario_fecha",
        "bitacora",
        ["usuario_id", "ocurrido_en"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bitacora_usuario_fecha", table_name="bitacora")
    op.drop_index(op.f("ix_bitacora_usuario_id"), table_name="bitacora")
    op.drop_index(op.f("ix_bitacora_ocurrido_en"), table_name="bitacora")
    op.drop_index(op.f("ix_bitacora_entidad"), table_name="bitacora")
    op.drop_index(op.f("ix_bitacora_accion"), table_name="bitacora")
    op.drop_table("bitacora")
