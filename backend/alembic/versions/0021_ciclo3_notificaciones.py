"""0021 - CU-40 Notificar eventos a los usuarios (P13). Realiza el RF11.

UNA SOLA TABLA
--------------
`notificacion` guarda el aviso y, en las mismas columnas, el resultado de
haberlo mandado por correo. Las tres clases que el 2.3 de CU-40 dibuja no son
tres tablas: `GestorNotificaciones` es el servicio y `CanalDeAviso` es la
costura `app/integrations/correo`, que existe desde CU-41 y no se persiste
---los canales no se dan de alta desde la aplicacion, se eligen con la variable
CORREO_PROVEEDOR---.

Una segunda tabla de envios tendria exactamente una fila por notificacion
mientras haya un solo canal ademas del de la aplicacion. Cuando entre un
segundo ---SMS, push del movil--- ahi si corresponde separarla.

POR QUE ESTA TABLA NO EXISTIA HASTA HOY
----------------------------------------
Hasta el 28/09 CU-40 estaba sin construir, y los diagramas lo dibujaban vacio a
proposito: `Notificacion` sin columnas y sus clases sin operaciones, porque
inventarle metodos habria hecho que el modelo mintiera justo donde habia que
defender que faltaba. Con esta migracion deja de faltar.

LA `ondelete` ES CASCADE, AL REVES QUE LA BITACORA
----------------------------------------------------
En `bitacora` el usuario se pone en NULL al borrarse la cuenta, porque un
asiento sin actor sigue siendo un registro historico. Un aviso no: es PARA
alguien. Sin destinatario no queda historia, queda una fila que nadie puede
leer y que nadie va a borrar.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_ciclo3_notificaciones"
down_revision: str | None = "0020_ciclo3_cambio_prenda"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notificacion",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("destinatario_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        # Relativo: el dominio cambia entre local y Railway, y un enlace
        # guardado con el de desarrollo no sirve en produccion. El correo lo
        # completa con WEB_BASE_URL al momento de enviar.
        sa.Column("enlace", sa.String(length=300), nullable=True),
        # `entidad` + `entidad_id` y no tres claves foraneas: apuntan a
        # `reserva`, `venta` o `existencia` segun el tipo, y una FK por cada una
        # dejaria dos columnas nulas siempre.
        sa.Column("entidad", sa.String(length=60), nullable=True),
        sa.Column("entidad_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("leida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "correo_estado",
            sa.String(length=20),
            server_default="PENDIENTE",
            nullable=False,
        ),
        sa.Column("correo_enviado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correo_error", sa.String(length=300), nullable=True),
        # Los nombres de las restricciones van PELADOS: la convencion de
        # app/db/base.py los expande a ck_notificacion_<nombre>. Escribirlos ya
        # expandidos los expande otra vez y `alembic check` marca una
        # restriccion borrada y otra agregada.
        sa.CheckConstraint(
            "tipo IN ('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', "
            "'PEDIDO_PAGADO', 'STOCK_BAJO')",
            name="tipo_valido",
        ),
        sa.CheckConstraint(
            "correo_estado IN ('OMITIDO', 'PENDIENTE', 'ENVIADO', 'FALLIDO')",
            name="correo_estado_valido",
        ),
        # Un correo ENVIADO tiene fecha y ninguno de los otros tres la tiene.
        # Sin esto una fila puede decir PENDIENTE y traer fecha, y el
        # despachador no sabria a cual creerle.
        sa.CheckConstraint(
            "(correo_estado = 'ENVIADO') = (correo_enviado_en IS NOT NULL)",
            name="enviado_tiene_fecha",
        ),
        sa.ForeignKeyConstraint(
            ["destinatario_id"], ["usuario.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # La consulta real es «los mios, del mas nuevo al mas viejo». Sin el indice
    # compuesto hay que leer todas las filas de la persona antes de ordenarlas.
    op.create_index(
        "ix_notificacion_destinatario_creada",
        "notificacion",
        ["destinatario_id", "creada_en"],
    )

    # Parcial a proposito: el despachador solo busca las pendientes, que son
    # pocas entre muchas. Indexar las miles ya enviadas no le sirve a nadie.
    op.create_index(
        "ix_notificacion_pendientes",
        "notificacion",
        ["creada_en"],
        postgresql_where=sa.text("correo_estado = 'PENDIENTE'"),
    )


def downgrade() -> None:
    op.drop_index("ix_notificacion_pendientes", table_name="notificacion")
    op.drop_index("ix_notificacion_destinatario_creada", table_name="notificacion")
    op.drop_table("notificacion")
