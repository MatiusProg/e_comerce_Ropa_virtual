"""0022 - 2do parcial: la base multitenant (desafío VI, base del CU-01).

QUÉ HACE
--------
1. Crea la plataforma: `empresa`, `plan`, `suscripcion` y `cliente_empresa`.
2. Da de alta la empresa 1, **Violet Boutique** (slug `violet-boutique`), los
   tres planes (Básico, Profesional y Empresarial) y le asigna el Empresarial.
3. Agrega `empresa_id` a las 35 tablas con datos de una empresa y les pone la
   empresa 1: **todo lo que había del 1er parcial pasa a ser de Violet
   Boutique**, y producción sigue funcionando igual.
4. Activa Row Level Security **con FORCE** en esas tablas.
5. Crea el rol `violet_app` (sin BYPASSRLS) que la aplicación asume con
   `SET ROLE` cuando `APP_DB_ROLE` está definido.

El porqué de cada pieza está en `app/core/tenencia.py`. El SQL de las
funciones, las políticas y la lista de tablas está COPIADO acá a propósito: una
migración describe la base de un momento, y si importara la lista de la
aplicación, sumar una tabla mañana cambiaría lo que hace esta migración.

`empresa_id` TIENE DEFAULT `app_empresa_actual()`
-------------------------------------------------
Es lo que permite que el código que ya inserta filas no tenga que nombrar la
empresa. Acá también sirve para rellenar: la migración fija `app.empresa_id`
en 1 antes de agregar las columnas, y PostgreSQL evalúa el DEFAULT en cada
fila existente al agregar la columna.

LOS ÚNICOS PASAN A SER POR EMPRESA
----------------------------------
Dos empresas pueden tener el mismo código de producto, el mismo SKU o una
sucursal con el mismo nombre en la misma ciudad. Los nombres de las
restricciones no cambian, porque los servicios las reconocen por el nombre.

`usuario.correo` sigue siendo único en toda la plataforma: el login todavía
busca por correo solo. Lo relaja el CU-06, cuando el login lleve el slug.

Sin `empresa_id`: `rol`, `permiso`, `ciudad` (compartidas, decisión de Luis) y
las tablas de identidad (`cliente`, `direccion_cliente`, `medida_cliente`,
`sesion_token`, `token_recuperacion`), que el login necesita antes de saber la
empresa. `usuario` lleva `empresa_id` nullable y sin RLS: NULL para el cliente
(RN-13) y para el administrador de la plataforma.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022_multitenant_base"
down_revision: str | None = "0021_ciclo3_notificaciones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROL_APP = "violet_app"
DEFAULT_EMPRESA = sa.text("app_empresa_actual()")

#: Las que ya existían. `suscripcion` y `cliente_empresa` nacen acá con la columna.
TABLAS_EXISTENTES = (
    "sucursal", "empleado", "proveedor",
    "categoria", "talla", "color", "temporada", "coleccion", "producto",
    "variante_producto", "imagen_producto", "promocion", "medida_talla",
    "existencia", "movimiento_inventario", "abastecimiento",
    "reserva", "reserva_detalle",
    "carrito", "carrito_detalle", "venta", "detalle_venta", "comprobante",
    "devolucion", "detalle_devolucion", "caja", "turno_caja", "pago",
    "transaccion_pasarela",
    "favorito", "recomendacion",
    "notificacion", "bitacora",
)
#: Lo que hace la plataforma no es de ninguna empresa: en estas puede quedar NULL.
NULLABLES = ("bitacora", "transaccion_pasarela")
TABLAS_CON_RLS = ("suscripcion", "cliente_empresa") + TABLAS_EXISTENTES

#: (tabla, nombre, columnas antes, columnas ahora)
UNICOS = (
    ("categoria", "uq_categoria_padre_nombre", ["categoria_padre_id", "nombre"],
     ["empresa_id", "categoria_padre_id", "nombre"]),
    ("talla", "uq_talla_tipo_codigo", ["tipo_prenda", "codigo"],
     ["empresa_id", "tipo_prenda", "codigo"]),
    ("color", "uq_color_nombre", ["nombre"], ["empresa_id", "nombre"]),
    ("temporada", "uq_temporada_nombre", ["nombre"], ["empresa_id", "nombre"]),
    ("producto", "uq_producto_codigo", ["codigo"], ["empresa_id", "codigo"]),
    ("variante_producto", "uq_variante_producto_sku", ["sku"], ["empresa_id", "sku"]),
    ("sucursal", "uq_sucursal_ciudad_nombre", ["ciudad_id", "nombre"],
     ["empresa_id", "ciudad_id", "nombre"]),
    ("empleado", "uq_empleado_documento", ["documento"], ["empresa_id", "documento"]),
    ("proveedor", "uq_proveedor_identificacion_tributaria", ["identificacion_tributaria"],
     ["empresa_id", "identificacion_tributaria"]),
    ("carrito", "uq_carrito_cliente_id", ["cliente_id"], ["empresa_id", "cliente_id"]),
    ("recomendacion", "uq_recomendacion_cliente_id", ["cliente_id"],
     ["empresa_id", "cliente_id"]),
)

FUNCIONES_SQL = """
CREATE OR REPLACE FUNCTION app_empresa_actual() RETURNS bigint
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.empresa_id', true), '')::bigint
$$;

CREATE OR REPLACE FUNCTION app_es_plataforma() RETURNS boolean
LANGUAGE sql STABLE AS $$
    SELECT coalesce(current_setting('app.es_plataforma', true), '') = 'on'
$$;
"""

ROL_SQL = f"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROL_APP}') THEN
        CREATE ROLE {ROL_APP} NOLOGIN NOBYPASSRLS;
    END IF;
    BEGIN
        EXECUTE 'GRANT {ROL_APP} TO ' || quote_ident(current_user);
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE USING MESSAGE = 'No se pudo conceder {ROL_APP}: ' || SQLERRM;
    END;
END $$;
"""

PERMISOS_SQL = f"""
GRANT USAGE ON SCHEMA public TO {ROL_APP};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROL_APP};
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {ROL_APP};
GRANT EXECUTE ON FUNCTION app_empresa_actual(), app_es_plataforma() TO {ROL_APP};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROL_APP};
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {ROL_APP};
"""

FUNCIONES_BASICO = (
    '{"reportes_ia": false, "correo": false, "ia_cliente": false, "marca_propia": false, '
    '"traspasos_sugeridos": false, "foto_ia": false, "analitica_ml": false, '
    '"exportar_datos": false, "bitacora_dias": 30, "respaldo_intervalo_horas": 168, '
    '"respaldo_retencion": 4}'
)
FUNCIONES_PROFESIONAL = (
    '{"reportes_ia": true, "correo": true, "ia_cliente": true, "marca_propia": true, '
    '"traspasos_sugeridos": true, "foto_ia": true, "analitica_ml": false, '
    '"exportar_datos": false, "bitacora_dias": 180, "respaldo_intervalo_horas": 24, '
    '"respaldo_retencion": 7}'
)
FUNCIONES_EMPRESARIAL = (
    '{"reportes_ia": true, "correo": true, "ia_cliente": true, "marca_propia": true, '
    '"traspasos_sugeridos": true, "foto_ia": true, "analitica_ml": true, '
    '"exportar_datos": true, "bitacora_dias": null, "respaldo_intervalo_horas": null, '
    '"respaldo_retencion": 30}'
)


def _politica(tabla: str) -> str:
    return f"""
ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS aislamiento_empresa ON {tabla};
CREATE POLICY aislamiento_empresa ON {tabla}
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
"""


def _auditoria() -> list[sa.Column]:
    return [
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
    ]


def upgrade() -> None:
    op.execute(FUNCIONES_SQL)
    op.execute(ROL_SQL)

    # --- 1. La plataforma -------------------------------------------------
    op.create_table(
        "empresa",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("razon_social", sa.String(160)),
        sa.Column("nit", sa.String(30)),
        sa.Column("slug", sa.String(40), nullable=False),
        sa.Column("correo_contacto", sa.String(120)),
        sa.Column("estado", sa.String(10), server_default=sa.text("'ACTIVA'"), nullable=False),
        *_auditoria(),
        sa.CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name="slug_formato"),
        sa.CheckConstraint("estado IN ('ACTIVA', 'BAJA')", name="estado"),
        sa.PrimaryKeyConstraint("id", name="pk_empresa"),
        sa.UniqueConstraint("slug", name="uq_empresa_slug"),
    )
    op.create_table(
        "plan",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(40), nullable=False),
        sa.Column("precio_mensual", sa.Numeric(10, 2), nullable=False),
        sa.Column("duracion_dias", sa.SmallInteger(), server_default=sa.text("30"), nullable=False),
        sa.Column("max_sucursales", sa.Integer()),
        sa.Column("max_empleados", sa.Integer()),
        sa.Column("cupo_reportes_ia", sa.Integer()),
        sa.Column("cupo_fotos_ia", sa.Integer()),
        sa.Column("funciones", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"),
                  nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_auditoria(),
        sa.CheckConstraint("precio_mensual >= 0", name="precio"),
        sa.CheckConstraint("duracion_dias > 0", name="duracion"),
        sa.PrimaryKeyConstraint("id", name="pk_plan"),
        sa.UniqueConstraint("codigo", name="uq_plan_codigo"),
        sa.UniqueConstraint("nombre", name="uq_plan_nombre"),
    )
    op.create_table(
        "suscripcion",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("plan_id", sa.SmallInteger(), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("vencimiento", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(12), server_default=sa.text("'VIGENTE'"), nullable=False),
        sa.Column("empresa_id", sa.BigInteger(), server_default=DEFAULT_EMPRESA, nullable=False),
        *_auditoria(),
        sa.CheckConstraint("vencimiento > inicio", name="fechas"),
        sa.CheckConstraint(
            "estado IN ('VIGENTE', 'SUSPENDIDA', 'VENCIDA', 'REEMPLAZADA')", name="estado"
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plan.id"], name="fk_suscripcion_plan_id_plan"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_suscripcion_empresa_id_empresa"),
        sa.PrimaryKeyConstraint("id", name="pk_suscripcion"),
    )
    op.create_index("ix_suscripcion_plan_id", "suscripcion", ["plan_id"])
    op.create_index("ix_suscripcion_empresa_id", "suscripcion", ["empresa_id"])
    op.create_index(
        "uq_suscripcion_vigente_por_empresa", "suscripcion", ["empresa_id"], unique=True,
        postgresql_where=sa.text("estado IN ('VIGENTE', 'SUSPENDIDA')"),
    )
    op.create_table(
        "cliente_empresa",
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("empresa_id", sa.BigInteger(), server_default=DEFAULT_EMPRESA, nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["cliente.id"], ondelete="CASCADE",
                                name="fk_cliente_empresa_cliente_id_cliente"),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresa.id"],
                                name="fk_cliente_empresa_empresa_id_empresa"),
        sa.PrimaryKeyConstraint("cliente_id", "empresa_id", name="pk_cliente_empresa"),
    )

    # --- 2. La empresa 1 y los planes --------------------------------------
    op.execute(
        "INSERT INTO empresa (id, nombre, slug, estado) "
        "VALUES (1, 'Violet Boutique', 'violet-boutique', 'ACTIVA')"
    )
    op.execute("SELECT setval(pg_get_serial_sequence('empresa', 'id'), 1)")
    op.execute(
        "INSERT INTO plan (id, codigo, nombre, precio_mensual, duracion_dias, max_sucursales, "
        "max_empleados, cupo_reportes_ia, cupo_fotos_ia, funciones) VALUES "
        f"(1, 'BASICO', 'Básico', 300, 30, 2, 10, 0, 0, '{FUNCIONES_BASICO}'), "
        f"(2, 'PROFESIONAL', 'Profesional', 750, 30, 10, 60, 300, 10, '{FUNCIONES_PROFESIONAL}'), "
        f"(3, 'EMPRESARIAL', 'Empresarial', 1500, 30, NULL, NULL, NULL, 100, "
        f"'{FUNCIONES_EMPRESARIAL}')"
    )
    op.execute("SELECT setval(pg_get_serial_sequence('plan', 'id'), 3)")
    # Un año para la empresa del 1er parcial: no puede vencer en plena defensa.
    op.execute(
        "INSERT INTO suscripcion (empresa_id, plan_id, inicio, vencimiento, estado) "
        "VALUES (1, 3, current_date, current_date + 365, 'VIGENTE')"
    )

    # --- 3. empresa_id en las tablas existentes ----------------------------
    # Con el contexto en la empresa 1, el DEFAULT rellena las filas existentes
    # al agregar la columna (set_config local: dura lo que la transacción).
    op.execute("SELECT set_config('app.empresa_id', '1', true)")
    for tabla in TABLAS_EXISTENTES:
        op.add_column(
            tabla,
            sa.Column("empresa_id", sa.BigInteger(), server_default=DEFAULT_EMPRESA,
                      nullable=True),
        )
        op.execute(f"UPDATE {tabla} SET empresa_id = 1 WHERE empresa_id IS NULL")
        if tabla not in NULLABLES:
            op.alter_column(tabla, "empresa_id", nullable=False)
        op.create_foreign_key(f"fk_{tabla}_empresa_id_empresa", tabla, "empresa",
                              ["empresa_id"], ["id"])
        op.create_index(f"ix_{tabla}_empresa_id", tabla, ["empresa_id"])

    # usuario: el personal es de la empresa 1; el cliente no tiene empresa.
    op.add_column(
        "usuario",
        sa.Column("empresa_id", sa.BigInteger(), server_default=DEFAULT_EMPRESA, nullable=True),
    )
    op.execute(
        "UPDATE usuario SET empresa_id = CASE WHEN rol_id = "
        "(SELECT id FROM rol WHERE nombre = 'CLIENTE') THEN NULL ELSE 1 END"
    )
    op.create_foreign_key("fk_usuario_empresa_id_empresa", "usuario", "empresa",
                          ["empresa_id"], ["id"])
    op.create_index("ix_usuario_empresa_id", "usuario", ["empresa_id"])
    op.execute("INSERT INTO cliente_empresa (cliente_id, empresa_id) SELECT id, 1 FROM cliente")

    # --- 4. Los únicos, por empresa -----------------------------------------
    for tabla, nombre, _antes, ahora in UNICOS:
        op.drop_constraint(nombre, tabla, type_="unique")
        op.create_unique_constraint(nombre, tabla, ahora)

    # --- 5. RLS y permisos --------------------------------------------------
    for tabla in TABLAS_CON_RLS:
        op.execute(_politica(tabla))
    op.execute(PERMISOS_SQL)


def downgrade() -> None:
    for tabla in TABLAS_CON_RLS:
        op.execute(
            f"DROP POLICY IF EXISTS aislamiento_empresa ON {tabla}; "
            f"ALTER TABLE {tabla} NO FORCE ROW LEVEL SECURITY; "
            f"ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY;"
        )
    # Al volver los únicos globales, dos empresas con el mismo código chocarían:
    # el downgrade solo es seguro mientras exista una sola empresa.
    for tabla, nombre, antes, _ahora in UNICOS:
        op.drop_constraint(nombre, tabla, type_="unique")
        op.create_unique_constraint(nombre, tabla, antes)

    op.drop_index("ix_usuario_empresa_id", table_name="usuario")
    op.drop_constraint("fk_usuario_empresa_id_empresa", "usuario", type_="foreignkey")
    op.drop_column("usuario", "empresa_id")
    for tabla in reversed(TABLAS_EXISTENTES):
        op.drop_index(f"ix_{tabla}_empresa_id", table_name=tabla)
        op.drop_constraint(f"fk_{tabla}_empresa_id_empresa", tabla, type_="foreignkey")
        op.drop_column(tabla, "empresa_id")

    op.drop_table("cliente_empresa")
    op.drop_index("uq_suscripcion_vigente_por_empresa", table_name="suscripcion")
    op.drop_index("ix_suscripcion_empresa_id", table_name="suscripcion")
    op.drop_index("ix_suscripcion_plan_id", table_name="suscripcion")
    op.drop_table("suscripcion")
    op.drop_table("plan")
    op.drop_table("empresa")
    op.execute("DROP FUNCTION IF EXISTS app_es_plataforma(); DROP FUNCTION IF EXISTS app_empresa_actual();")
    # El rol `violet_app` queda: es de todo el servidor, y otra base podría usarlo.
