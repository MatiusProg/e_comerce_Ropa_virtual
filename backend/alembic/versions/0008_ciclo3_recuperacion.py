"""Ciclo 3 - CU-41: recuperar contrasena.

Agrega la tabla `token_recuperacion`, que sostiene el enlace de un solo uso del
RF39. Es la unica tabla propia que estrena CU-41.

SOBRE EL NUMERO Y DE QUIEN CUELGA  ---  LEER ANTES DE ESCRIBIR LA 0006
----------------------------------------------------------------------
Los identificadores se reservaron ANTES de escribir nada, en la seccion 4 de
docs/entregas/ciclo-2/04-respuesta-de-karen.md: `0006_ciclo3_ventas` y
`0007_ciclo3_promociones` son de Mateo, y de ahi en adelante de Karen.

Pero reservar el NOMBRE no ordena la CADENA. Alembic no mira el numero del
archivo: mira `down_revision`. Dos revisiones que cuelguen de la misma dejan el
arbol con dos cabezas y `alembic upgrade head` falla pidiendo cual.

Al 15/09/2026 la 0006 y la 0007 no estan escritas y la cabeza sigue siendo
`0005_ciclo3_favoritos`. Esta cuelga de ahi, que es lo unico que puede hacer:
apuntar a una revision inexistente rompe el comando entero, no solo esta
migracion.

CONSECUENCIA PARA MATEO: la cabeza ya no es la 0005 sino esta. Su
`0006_ciclo3_ventas` tiene que declarar

    down_revision = "0008_ciclo3_recuperacion"

La cadena queda 0005 -> 0008 -> 0006 -> 0007, que se lee raro y es correcta: el
numero del archivo es un nombre, no un orden. El orden es la cadena.

POR QUE UNA TABLA Y NO UNA COLUMNA EN `usuario`
-----------------------------------------------
Dos columnas en `usuario` --- el hash del token y su vencimiento --- alcanzarian
para el flujo principal y fallarian en lo demas: no habria historia de quien
pidio recuperar ni cuando, no se podria caducar un enlace sin escribir sobre la
fila del usuario, y cada peticion ensuciaria una tabla que se lee en CADA
autenticacion. Una tabla aparte, como `sesion_token`, que es el mismo problema:
credenciales de vida corta con su propio ciclo de vida.

EL TOKEN NO SE GUARDA
---------------------
Se guarda su SHA-256. Mientras vive, el token ES la credencial de la cuenta, y
una lectura de esta tabla en claro entregaria el acceso a todas las cuentas con
un enlace pendiente. El razonamiento completo esta en el modelo.

Escrita A MANO, no con --autogenerate, como todas las del proyecto.

Revision ID: 0008_ciclo3_recuperacion
Revises: 0005_ciclo3_favoritos
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_ciclo3_recuperacion"
down_revision: str | None = "0005_ciclo3_favoritos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "token_recuperacion",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        # SHA-256 en hexadecimal: 64 caracteres, siempre. UNIQUE porque dos
        # filas con el mismo hash significarian que el mismo enlace sirve para
        # dos cuentas; con 32 bytes aleatorios no va a pasar, y si pasara es
        # mejor que falle el alta a que el canje elija una fila al azar.
        sa.Column("hash_token", sa.String(length=64), nullable=False),
        sa.Column(
            "solicitado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        # ON DELETE CASCADE: un enlace de recuperacion no tiene ningun sentido
        # sin la cuenta que recupera, y no hay nada que conservar de el. Ademas
        # CU-03 elimina cuentas, y sin el cascade ese borrado fallaria.
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["usuario.id"],
            name="fk_token_recuperacion_usuario_id_usuario",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_token_recuperacion"),
        sa.UniqueConstraint("hash_token", name="uq_token_recuperacion_hash_token"),
        # El nombre va PELADO: la convencion de app/db/base.py lo expande a
        # ck_token_recuperacion_vigencia. Escribirlo ya expandido lo expande
        # otra vez y queda ck_token_recuperacion_ck_token_recuperacion_vigencia,
        # que no es el que declara el modelo --- y `alembic check` lo marca como
        # una restriccion borrada y otra agregada. Es el mismo estilo que usa la
        # 0001 para `sesion_token`.
        sa.CheckConstraint("expira_en > solicitado_en", name="vigencia"),
    )

    # Parcial: al pedir un enlace nuevo hay que invalidar los pendientes de ese
    # usuario, y esa es la unica consulta que filtra por usuario_id. Los
    # canjeados no se consultan nunca, solo se conservan, asi que quedan fuera
    # del indice y este no crece con la historia.
    op.create_index(
        "idx_recuperacion_usuario_pendiente",
        "token_recuperacion",
        ["usuario_id"],
        postgresql_where=sa.text("usado_en IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_recuperacion_usuario_pendiente", table_name="token_recuperacion"
    )
    op.drop_table("token_recuperacion")
