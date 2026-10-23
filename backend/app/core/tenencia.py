"""Multitenant (2do parcial, desafío VI): de qué empresa es cada consulta.

CÓMO SE AÍSLA UNA EMPRESA DE OTRA
---------------------------------
Cada tabla con datos de una empresa lleva `empresa_id` y **Row Level Security
con FORCE** (RNF02). La política deja ver y escribir solo las filas cuya
empresa es la del contexto de la transacción:

    empresa_id = app_empresa_actual() OR app_es_plataforma()

`app_empresa_actual()` lee `app.empresa_id`, que se fija con
`set_config(..., true)` --- el `true` lo hace local a la transacción, como un
`SET LOCAL` --- al empezar cada transacción de la sesión de SQLAlchemy (ver
`_al_empezar_transaccion`). **Sin contexto, la consulta devuelve cero filas**:
el sistema falla cerrado. Ocultar la opción en la interfaz no alcanza; la
restricción vive en la base, que es lo que pide el enunciado.

POR QUÉ CASI NO HAY QUE TOCAR LOS 18 MÓDULOS
--------------------------------------------
`empresa_id` tiene `DEFAULT app_empresa_actual()`. El código que ya existía
inserta filas sin nombrar la empresa, y la base le pone la del contexto; el
`WITH CHECK` de la política impide escribir con la empresa de otro.

EL ROL QUE NO SE SALTA LA POLÍTICA
----------------------------------
En Supabase el usuario `postgres` tiene BYPASSRLS: con él, ninguna política
corre, ni siquiera con FORCE. La migración `0022` crea el rol `violet_app`
(NOLOGIN, NOBYPASSRLS) y la aplicación lo asume con `SET ROLE` al conectarse
cuando `APP_DB_ROLE` está definido. Las migraciones siguen corriendo como
dueño de las tablas. Así no cambia ninguna contraseña de Railway.

DE DÓNDE SALE LA EMPRESA
------------------------
1. El usuario autenticado del personal: su `usuario.empresa_id`, leído de la
   base en `get_usuario_actual` (ver `fijar_empresa`).
2. Si no hay usuario, o es un cliente (que no pertenece a ninguna empresa:
   RN-13), la tienda que se está mirando: el encabezado `X-Empresa` con el id.
3. Si no viene, la empresa por omisión (`EMPRESA_POR_DEFECTO_ID`, la 1, que es
   la Violet Boutique del 1er parcial). El CU-06 cambia esto por el slug.

El **modo plataforma** ve todas las empresas. Es para el administrador de la
plataforma y para lo que corre sin persona: el webhook de la pasarela y las
tareas de expiración, que procesan a todas las empresas.
"""

from __future__ import annotations

from contextvars import ContextVar

from sqlalchemy import event, text
from sqlalchemy.orm import Session

# --------------------------------------------------------------------------
#  Contexto de la petición
# --------------------------------------------------------------------------
#: La empresa de la tienda que pide la petición (encabezado o la de omisión).
#: Lo fija el middleware; lo reemplaza `fijar_empresa` cuando hay usuario.
empresa_de_la_peticion: ContextVar[int | None] = ContextVar(
    "empresa_de_la_peticion", default=None
)

CLAVE_EMPRESA = "empresa_id"
CLAVE_PLATAFORMA = "plataforma"

#: El rol que opera la plataforma, por encima de las empresas (CU-01 a CU-03).
#: No pertenece a ninguna empresa y trabaja en modo plataforma.
ROL_PLATAFORMA = "ADMIN_PLATAFORMA"
#: Una empresa dada de baja: ninguno de sus usuarios puede entrar (CU-01, 3b).
EMPRESA_DE_BAJA = "BAJA"


def fijar_contexto_de_usuario(sesion: Session, *, rol: str, empresa_id: int | None) -> None:
    """El contexto que corresponde a un usuario ya identificado.

    El administrador de la plataforma ve todas las empresas; el personal, la
    suya; el cliente (sin empresa) sigue en la de la tienda que está mirando.
    """
    if rol == ROL_PLATAFORMA:
        modo_plataforma(sesion)
    elif empresa_id is not None:
        fijar_empresa(sesion, empresa_id)


def _aplicar(sesion: Session, conexion) -> None:
    empresa = sesion.info.get(CLAVE_EMPRESA)
    if empresa is None and not sesion.info.get(CLAVE_PLATAFORMA):
        empresa = empresa_de_la_peticion.get()
    conexion.execute(
        text(
            "SELECT set_config('app.empresa_id', :empresa, true), "
            "set_config('app.es_plataforma', :plataforma, true)"
        ),
        {
            "empresa": "" if empresa is None else str(int(empresa)),
            "plataforma": "on" if sesion.info.get(CLAVE_PLATAFORMA) else "",
        },
    )


@event.listens_for(Session, "after_begin")
def _al_empezar_transaccion(sesion: Session, transaccion, conexion) -> None:
    """Cada transacción arranca con el contexto de la sesión.

    Se escucha en la clase `Session`, no en una fábrica, para que valga igual
    para la sesión de la aplicación, la de las pruebas y la de los sembrados.
    """
    _aplicar(sesion, conexion)


def fijar_empresa(sesion: Session, empresa_id: int | None) -> None:
    """Fija la empresa de la sesión, también en la transacción ya abierta.

    Hace falta lo segundo porque la sesión de la petición ya consultó algo
    (la sesión y el usuario del token, que son tablas de identidad sin RLS)
    antes de saber de qué empresa es: la transacción ya empezó, y sin esto
    regiría el contexto anterior hasta el próximo commit.
    """
    sesion.info[CLAVE_EMPRESA] = empresa_id
    sesion.info.pop(CLAVE_PLATAFORMA, None)
    if sesion.in_transaction():
        _aplicar(sesion, sesion.connection())


def modo_plataforma(sesion: Session) -> None:
    """La sesión ve todas las empresas. Solo para la plataforma y el sistema."""
    sesion.info[CLAVE_PLATAFORMA] = True
    sesion.info.pop(CLAVE_EMPRESA, None)
    if sesion.in_transaction():
        _aplicar(sesion, sesion.connection())


# --------------------------------------------------------------------------
#  Lo que se crea en la base (lo usan la migración 0022 y `create_all`)
# --------------------------------------------------------------------------
ROL_APP = "violet_app"

#: Tablas con datos de una empresa: `empresa_id` + RLS con FORCE. La prueba
#: guardiana de aislamiento falla si una tabla con `empresa_id` no está acá.
TABLAS_DE_EMPRESA = (
    # plataforma
    "suscripcion",
    "cliente_empresa",
    # organización
    "sucursal",
    "empleado",
    "proveedor",
    # catálogo (por empresa: decisión de Luis del 23/10)
    "categoria",
    "talla",
    "color",
    "temporada",
    "coleccion",
    "producto",
    "variante_producto",
    "imagen_producto",
    "promocion",
    "medida_talla",
    # inventario
    "existencia",
    "movimiento_inventario",
    "abastecimiento",
    # reservas
    "reserva",
    "reserva_detalle",
    # ventas, caja y pagos
    "carrito",
    "carrito_detalle",
    "venta",
    "detalle_venta",
    "comprobante",
    "devolucion",
    "detalle_devolucion",
    "caja",
    "turno_caja",
    "pago",
    "transaccion_pasarela",
    # cliente dentro de una empresa
    "favorito",
    "recomendacion",
    # avisos y bitácora
    "notificacion",
    "bitacora",
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

#: El rol se crea si no existe y se le concede a quien migra, para que la
#: aplicación pueda hacer `SET ROLE`. En Supabase `postgres` tiene CREATEROLE
#: y, desde PostgreSQL 16, quien crea un rol recibe su ADMIN OPTION.
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


def politica_sql(tabla: str) -> str:
    """RLS con FORCE: sin FORCE, el dueño de la tabla se saltaría la política."""
    return f"""
ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS aislamiento_empresa ON {tabla};
CREATE POLICY aislamiento_empresa ON {tabla}
    USING (empresa_id = app_empresa_actual() OR app_es_plataforma())
    WITH CHECK (empresa_id = app_empresa_actual() OR app_es_plataforma());
"""


def quitar_politica_sql(tabla: str) -> str:
    return f"""
DROP POLICY IF EXISTS aislamiento_empresa ON {tabla};
ALTER TABLE {tabla} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {tabla} DISABLE ROW LEVEL SECURITY;
"""


def preparar_metadata(metadata) -> None:
    """Hace que `create_all` deje la base igual que la migración 0022.

    Las pruebas arman el esquema con `create_all`, no con Alembic. Sin esto,
    la base de pruebas no tendría las funciones (y fallaría el DEFAULT de
    `empresa_id`) ni las políticas, y las pruebas de aislamiento no probarían
    nada.
    """

    @event.listens_for(metadata, "before_create")
    def _funciones(target, conexion, **_):
        conexion.exec_driver_sql(FUNCIONES_SQL)

    @event.listens_for(metadata, "after_create")
    def _politicas(target, conexion, **_):
        conexion.exec_driver_sql(ROL_SQL)
        for tabla in TABLAS_DE_EMPRESA:
            conexion.exec_driver_sql(politica_sql(tabla))
        conexion.exec_driver_sql(PERMISOS_SQL)


# --------------------------------------------------------------------------
#  Middleware: la empresa de la tienda
# --------------------------------------------------------------------------
class EmpresaDeLaTiendaMiddleware:
    """Fija la empresa de la tienda para toda la petición (ASGI puro).

    Lee el encabezado `X-Empresa` (el id de la empresa); si no viene o no es
    un número, usa `EMPRESA_POR_DEFECTO_ID`. Es lo que ve el visitante anónimo
    y el cliente. Si la petición trae un usuario del personal,
    `get_usuario_actual` lo reemplaza por la empresa del usuario.

    ASGI puro y no `BaseHTTPMiddleware`: la variable de contexto tiene que
    quedar fijada antes de que corran los demás middlewares y la ruta, y
    restaurarse al terminar, sin depender de cómo Starlette arma sus tareas.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        from app.core.config import settings

        empresa = settings.EMPRESA_POR_DEFECTO_ID
        for nombre, valor in scope.get("headers") or ():
            if nombre == b"x-empresa":
                try:
                    empresa = int(valor.decode("latin-1"))
                except ValueError:
                    pass
                break
        marca = empresa_de_la_peticion.set(empresa)
        try:
            await self.app(scope, receive, send)
        finally:
            empresa_de_la_peticion.reset(marca)
