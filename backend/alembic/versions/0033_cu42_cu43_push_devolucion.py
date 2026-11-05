"""0033 - CU-42 avisos push y CU-43 devolución automática del pago.

- `suscripcion_push`: los dispositivos (app con FCM, web con Web Push) que
  aceptan avisos de una persona. Tabla de empresa con RLS FORCE; el SQL de la
  política está COPIADO a propósito, como en la 0028.
- `notificacion`: el estado del push (como el del correo) y los dos tipos
  nuevos, OPERACION_OFFLINE y DEVOLUCION_PAGO.
- `operacion_offline`: el cliente de la operación (opcional en la venta) y si
  la devolución la hizo el sistema solo.

Va AL FINAL, después de la 0039 de Karen, aunque el número sea menor: el
acuerdo de la P3 reservó de la 0029 a la 0035 para nosotros, pero ella mergeó
de la 0036 a la 0039 antes. A Alembic le importa la cadena, no el número.

Primero colgaba de la 0037, igual que la 0038 de Karen, y `main` quedó con
DOS cabezas: el `alembic upgrade head` del Dockerfile falla así. Se movió al
final ---y no la 0038 detrás de esta--- porque la 0038 y la 0039 ya pueden
estar aplicadas en producción y en la base de Karen; esta, todavía no.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033_cu42_cu43_push"
down_revision: str | None = "0039_cu40_respaldos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EMPRESA = sa.text("app_empresa_actual()")

# Lo que dejó la 0039 (CU-26 sumó DEVOLUCION).
TIPOS_ANTES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO', "
    "'DEVOLUCION')"
)
TIPOS_DESPUES = (
    "('RESERVA_EN_SUCURSAL', 'RESERVA_PREPARADA', 'PEDIDO_PAGADO', 'STOCK_BAJO', 'TRASPASO', "
    "'DEVOLUCION', 'OPERACION_OFFLINE', 'DEVOLUCION_PAGO')"
)


def upgrade() -> None:
    # --- notificacion ------------------------------------------------------
    op.add_column(
        "notificacion",
        sa.Column("push_estado", sa.String(20), server_default="OMITIDO", nullable=False),
    )
    op.add_column("notificacion", sa.Column("push_enviado_en", sa.DateTime(timezone=True)))
    op.add_column("notificacion", sa.Column("push_error", sa.String(300)))
    op.create_check_constraint(
        "push_estado_valido",
        "notificacion",
        "push_estado IN ('OMITIDO', 'PENDIENTE', 'ENVIADO', 'FALLIDO')",
    )
    op.create_check_constraint(
        "push_enviado_tiene_fecha",
        "notificacion",
        "(push_estado = 'ENVIADO') = (push_enviado_en IS NOT NULL)",
    )
    op.create_index(
        "ix_notificacion_push_pendientes",
        "notificacion",
        ["creada_en"],
        postgresql_where=sa.text("push_estado = 'PENDIENTE'"),
    )
    # op.f(): el nombre ya es el definitivo (ver la 0018).
    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint("tipo_valido", "notificacion", f"tipo IN {TIPOS_DESPUES}")

    # --- suscripcion_push --------------------------------------------------
    op.create_table(
        "suscripcion_push",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.BigInteger(), server_default=_EMPRESA, nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("canal", sa.String(10), nullable=False),
        sa.Column("direccion", sa.Text(), nullable=False),
        sa.Column("clave_p256dh", sa.String(200)),
        sa.Column("clave_auth", sa.String(100)),
        sa.Column("dispositivo", sa.String(120)),
        sa.Column("creada_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("usada_en", sa.DateTime(timezone=True)),
        sa.CheckConstraint("canal IN ('FCM', 'WEBPUSH')", name="canal"),
        sa.CheckConstraint(
            "canal <> 'WEBPUSH' OR (clave_p256dh IS NOT NULL AND clave_auth IS NOT NULL)",
            name="webpush_con_claves",
        ),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_suscripcion_push_empresa_id_empresa"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE",
                                name="fk_suscripcion_push_usuario_id_usuario"),
        sa.PrimaryKeyConstraint("id", name="pk_suscripcion_push"),
        sa.UniqueConstraint("empresa_id", "direccion", name="uq_suscripcion_push_direccion"),
    )
    op.create_index("ix_suscripcion_push_empresa_id", "suscripcion_push", ["empresa_id"])
    op.create_index("ix_suscripcion_push_usuario_id", "suscripcion_push", ["usuario_id"])
    op.execute("""
ALTER TABLE suscripcion_push ENABLE ROW LEVEL SECURITY;
ALTER TABLE suscripcion_push FORCE ROW LEVEL SECURITY;
CREATE POLICY aislamiento_empresa ON suscripcion_push
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
GRANT SELECT, INSERT, UPDATE, DELETE ON suscripcion_push TO violet_app;
GRANT USAGE, SELECT, UPDATE ON SEQUENCE suscripcion_push_id_seq TO violet_app;
""")

    # --- operacion_offline -------------------------------------------------
    op.add_column("operacion_offline", sa.Column("cliente_id", sa.BigInteger()))
    op.create_foreign_key(
        "fk_operacion_offline_cliente_id_cliente", "operacion_offline", "cliente",
        ["cliente_id"], ["id"],
    )
    op.create_index("ix_operacion_offline_cliente_id", "operacion_offline", ["cliente_id"])
    op.add_column(
        "operacion_offline",
        sa.Column("devolucion_automatica", sa.Boolean(), server_default="false",
                  nullable=False),
    )
    op.create_check_constraint(
        "devolucion_con_responsable",
        "operacion_offline",
        "devuelto_en IS NULL OR devolucion_automatica OR devuelto_por IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_operacion_offline_devolucion_con_responsable"),
                       "operacion_offline", type_="check")
    op.drop_column("operacion_offline", "devolucion_automatica")
    op.drop_index("ix_operacion_offline_cliente_id", table_name="operacion_offline")
    op.drop_constraint("fk_operacion_offline_cliente_id_cliente", "operacion_offline",
                       type_="foreignkey")
    op.drop_column("operacion_offline", "cliente_id")

    op.drop_table("suscripcion_push")

    op.execute("DELETE FROM notificacion WHERE tipo IN ('OPERACION_OFFLINE', 'DEVOLUCION_PAGO')")
    op.drop_constraint(op.f("ck_notificacion_tipo_valido"), "notificacion", type_="check")
    op.create_check_constraint("tipo_valido", "notificacion", f"tipo IN {TIPOS_ANTES}")
    op.drop_index("ix_notificacion_push_pendientes", table_name="notificacion")
    op.drop_constraint(op.f("ck_notificacion_push_enviado_tiene_fecha"), "notificacion",
                       type_="check")
    op.drop_constraint(op.f("ck_notificacion_push_estado_valido"), "notificacion",
                       type_="check")
    op.drop_column("notificacion", "push_error")
    op.drop_column("notificacion", "push_enviado_en")
    op.drop_column("notificacion", "push_estado")
