"""Configuracion compartida de las pruebas (flujo de Pruebas del PUDS).

REGLA DE SEGURIDAD DE ESTE ARCHIVO
----------------------------------
Las pruebas NUNCA deben tocar la base de produccion. El `.env` del proyecto
apunta a Supabase, asi que aqui se exige una variable aparte, TEST_DATABASE_URL,
y se la impone sobre DATABASE_URL antes de importar la aplicacion. Si esa
variable no esta definida, las pruebas que necesitan base se SALTAN: es
preferible no probar a probar contra los datos reales.

    # PowerShell
    # El PostgreSQL local escucha en el 5433: el 5432 es el de Docker.
    $env:TEST_DATABASE_URL = "postgresql+psycopg://usuario:clave@localhost:5433/violetboutique_test"
    .venv\\Scripts\\python.exe -m pytest

La base indicada se crea y se destruye entera en cada corrida, asi que tiene
que ser una base dedicada a pruebas y vacia.
"""

import os
from datetime import date, timedelta
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

URL_PRUEBAS = os.environ.get("TEST_DATABASE_URL")

# Antes de importar la aplicacion: si hay base de pruebas, es la unica que la
# aplicacion va a conocer. pydantic-settings da prioridad a las variables de
# entorno por encima del .env, de modo que esto desactiva la URL de Supabase.
if URL_PRUEBAS:
    os.environ["DATABASE_URL"] = URL_PRUEBAS

# LA PASARELA DE PAGO DE LAS PRUEBAS ES SIEMPRE LA SIMULADA
# ----------------------------------------------------------
# Se impone aqui por el mismo motivo que la base: para que la suite NO dependa
# de lo que diga el `.env`. Sin esto, poner PAGO_PROVEEDOR=stripe para
# desarrollar en local haria que las pruebas de CU-27 y CU-28 **salgan a
# internet a hablar con Stripe de verdad**: abririan sesiones de cobro con la
# clave que este configurada, tardarian lo que tarde la red, y fallarian sin
# conexion --- ademas de que la ruta de simulacion responde 404 cuando la
# pasarela cobra en serio, que es justamente lo que esas pruebas usan.
#
# Una suite que llama a un servicio de terceros no prueba el sistema: prueba el
# servicio de terceros y la conexion a internet.
os.environ["PAGO_PROVEEDOR"] = "simulada"

# Y con secreto, para que la firma del webhook se VERIFIQUE en las pruebas en
# vez de saltearse. El proveedor simulado no comprueba nada cuando esta vacio
# (y avisa por el log), asi que sin esto la parte mas delicada de CU-28 ---que
# un cuerpo sin firma valida no puede mover nada--- quedaria sin probar.
os.environ["PAGO_WEBHOOK_SECRET"] = "secreto-de-pruebas-no-es-de-nadie"

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# Importar los modelos puebla Base.metadata. Sin esto, create_all no crearia
# ninguna tabla: el metadata solo conoce las clases que fueron importadas.
from app.modules.catalogo import models as modelos_catalogo  # noqa: E402,F401
from app.modules.catalogo_publico import models as modelos_cat_pub  # noqa: E402,F401
from app.modules.inventario import models as modelos_inventario  # noqa: E402,F401
from app.modules.reservas import models as modelos_reservas  # noqa: E402,F401
from app.modules.organizacion import models as modelos_organizacion  # noqa: E402,F401
from app.modules.plataforma import models as modelos_plataforma  # noqa: E402,F401
from app.modules.seguridad import models as modelos_seguridad  # noqa: E402,F401
from app.modules.ventas import carrito_models as modelos_carrito  # noqa: E402,F401

#: Tablas que se vacian entre una prueba y la siguiente. El resto (roles,
#: ciudades) son datos de referencia y se siembran una sola vez.
#:
#: `sucursal` entra aca porque CU-06 crea una por prueba y el UNIQUE
#: (ciudad_id, nombre) haria fallar a la segunda. `empleado` cascadearia con
#: usuario, pero se nombra igual: depender de un CASCADE para la limpieza
#: hace que la prueba dependa de un detalle del esquema.
#:
#: El ORDEN importa: se vacian en esta secuencia, asi que cada tabla va antes
#: que aquellas a las que apunta. Las del Ciclo 2 se intercalaron por eso y no
#: al final --- producto referencia a proveedor, categoria, temporada y
#: coleccion, y variante_producto a talla y color.
TABLAS_VOLATILES = (
    # CU-42: la bitacora va PRIMERA. Apunta a `usuario` con ON DELETE SET
    # NULL, asi que truncar usuario sin vaciarla antes dejaria asientos
    # huerfanos de una prueba en la siguiente --- y varias cuentan cuantos
    # asientos hay.
    "bitacora",
    # CU-40: apunta a `usuario` con ON DELETE CASCADE, asi que el CASCADE la
    # limpiaria por rebote. Se nombra igual, por el mismo motivo que
    # `empleado`: depender de un detalle del esquema para la limpieza hace que
    # las pruebas que CUENTAN avisos dependan de el sin decirlo.
    "notificacion",
    # CU-39: cuelga de proveedor y de variante, que estan mas abajo.
    "abastecimiento",
    # P4 va primero: el movimiento apunta a la existencia, al usuario y al
    # proveedor, y la existencia a la variante y a la sucursal. Todas ellas
    # estan mas abajo en esta misma tupla.
    # P6 antes que P4: el detalle apunta a la reserva y a la variante, y la
    # reserva al cliente y a la sucursal.
    # P7: el detalle apunta al carrito y a la variante; el carrito al cliente.
    "carrito_detalle",
    "carrito",
    "reserva_detalle",
    "reserva",
    "movimiento_inventario",
    "existencia",
    # `favorito` apunta a `cliente` y a `producto`, las dos mas abajo.
    "favorito",
    "cliente_categoria",
    "direccion_cliente",
    "sesion_token",
    # `token_recuperacion` apunta a `usuario`, que va mas abajo. Mismo caso que
    # `sesion_token`, al que acompana.
    "token_recuperacion",
    "cliente",
    "empleado",
    "imagen_producto",
    # CU-12: apunta a producto, categoria y temporada, las tres mas abajo. El
    # CASCADE la limpiaria igual por rebote, pero listarla es lo que hace que
    # `RESTART IDENTITY` tambien la alcance --- y que no dependa de que alguien
    # recuerde por que funciona.
    "promocion",
    "variante_producto",
    "producto",
    "proveedor",
    "sucursal",
    "usuario",
    "categoria",
    "talla",
    "color",
    "coleccion",
    "temporada",
    # 2do parcial: las empresas que crea una prueba (CU-01) no pueden quedar
    # para la siguiente. Va al final porque todas las tablas del tenant la
    # referencian; el CASCADE las alcanza igual. La empresa 1 se vuelve a
    # sembrar en `_sembrar_referencias`, y RESTART IDENTITY le devuelve el id.
    "consumo_cupo",
    "suscripcion",
    "empresa",
    # CU-05: una prueba puede cambiar los límites de un plan; se vuelven a
    # sembrar los de la 0022 en `_sembrar_referencias`.
    "plan",
)

def _migracion_0022():
    """El módulo de la migración 0022, de donde salen las funciones de los planes."""
    import importlib.util
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0022_multitenant_base.py"
    spec = importlib.util.spec_from_file_location("migracion_0022", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


_M0022 = _migracion_0022()

#: Los tres planes de la migracion 0022: las pruebas arman el esquema con
#: `create_all`, que no siembra datos. Las funciones se leen de la migración
#: y no se copian: la copia se había quedado sin las claves del CU-40.
PLANES = (
    dict(id=1, codigo="BASICO", nombre="Básico", precio_mensual=Decimal("300"),
         max_sucursales=2, max_empleados=10, cupo_reportes_ia=0, cupo_fotos_ia=0,
         funciones=json.loads(_M0022.FUNCIONES_BASICO)),
    dict(id=2, codigo="PROFESIONAL", nombre="Profesional", precio_mensual=Decimal("750"),
         max_sucursales=10, max_empleados=60, cupo_reportes_ia=300, cupo_fotos_ia=10,
         funciones=json.loads(_M0022.FUNCIONES_PROFESIONAL)),
    dict(id=3, codigo="EMPRESARIAL", nombre="Empresarial", precio_mensual=Decimal("1500"),
         max_sucursales=None, max_empleados=None, cupo_reportes_ia=None, cupo_fotos_ia=100,
         funciones=json.loads(_M0022.FUNCIONES_EMPRESARIAL)),
)

#: Credenciales del cliente de prueba. La contrasena cumple la regla del
#: RNF01: ocho caracteres, con letra y digito.
CORREO_CLIENTE = "ana.cliente@violetboutique.bo"
CLAVE_CLIENTE = "Secreta123"
CORREO_ADMIN = "admin.pruebas@violetboutique.bo"
CLAVE_ADMIN = "Admin12345"


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP sin base de datos. Sirve para /health y poco mas."""
    return TestClient(app)


@pytest.fixture(scope="session")
def motor():
    """Motor contra la base de pruebas, con el esquema recien creado."""
    if not URL_PRUEBAS:
        pytest.skip(
            "Defina TEST_DATABASE_URL para ejecutar las pruebas con base de datos."
        )

    from sqlalchemy import create_engine

    motor = create_engine(URL_PRUEBAS)

    # Se parte siempre de cero: una corrida anterior interrumpida podria haber
    # dejado tablas a medias, y una prueba que depende de basura previa no
    # prueba nada.
    Base.metadata.drop_all(motor)
    Base.metadata.create_all(motor)

    yield motor

    Base.metadata.drop_all(motor)
    motor.dispose()


#: 2do parcial: la empresa de las pruebas que no hablan de multitenant. Es la
#: misma que la migracion 0022 le da a los datos del 1er parcial.
EMPRESA_PRUEBAS = 1
SLUG_PRUEBAS = "violet-boutique"


class _ClienteDePruebas(TestClient):
    """CU-06: el login indica la empresa por su slug (RN-12).

    Las pruebas anteriores al 2do parcial inician sesión sin slug; en vez de
    tocar cada una, este cliente le agrega el de la empresa de las pruebas al
    login que no trae la clave `empresa`. Las pruebas del CU-06 (y las de la
    plataforma, que entra sin slug) la mandan explícita, aunque sea `None`.
    """

    def post(self, url, *args, **kwargs):
        cuerpo = kwargs.get("json")
        if str(url).endswith("/auth/login") and isinstance(cuerpo, dict) and "empresa" not in cuerpo:
            kwargs["json"] = {"empresa": SLUG_PRUEBAS, **cuerpo}
        return super().post(url, *args, **kwargs)


@pytest.fixture(scope="session")
def motor_app(motor):
    """Motor con el que trabaja la aplicacion: asume el rol SIN BYPASSRLS.

    El usuario de la base local es superusuario y se saltaria todas las
    politicas. Con este motor, TODA la bateria corre con el RLS de verdad: si
    algun camino del codigo olvida fijar la empresa, su prueba ve cero filas y
    falla, en vez de pasar por casualidad. El esquema y el TRUNCATE siguen
    usando `motor`, que es el dueno de las tablas.
    """
    from sqlalchemy import create_engine

    from app.core.tenencia import ROL_APP
    from app.db.session import asumir_rol_de_la_aplicacion

    motor_app = create_engine(URL_PRUEBAS)
    asumir_rol_de_la_aplicacion(motor_app, ROL_APP)
    yield motor_app
    motor_app.dispose()


@pytest.fixture(scope="session")
def fabrica_sesiones(motor_app):
    from sqlalchemy.orm import sessionmaker

    from app.core.tenencia import CLAVE_EMPRESA

    return sessionmaker(
        bind=motor_app,
        autoflush=False,
        expire_on_commit=False,
        info={CLAVE_EMPRESA: EMPRESA_PRUEBAS},
    )


@pytest.fixture
def db(motor, fabrica_sesiones):
    """Base limpia para una prueba, con los datos de referencia sembrados.

    Se vacian las tablas volatiles en vez de envolver todo en una transaccion
    que se deshace: el servicio hace commit de verdad -- forma parte de lo que
    se quiere probar -- y anidar transacciones alrededor de eso vuelve fragil
    la prueba por motivos que no tienen que ver con el caso de uso.
    """
    from sqlalchemy import text

    with motor.begin() as conexion:
        conexion.execute(
            text(f"TRUNCATE {', '.join(TABLAS_VOLATILES)} RESTART IDENTITY CASCADE")
        )

    sesion = fabrica_sesiones()
    _sembrar_referencias(sesion)
    try:
        yield sesion
    finally:
        sesion.close()


def _sembrar_referencias(sesion) -> None:
    """Siembra la empresa de las pruebas, los roles y las ciudades. Es idempotente."""
    from sqlalchemy import select, text

    from app.modules.organizacion.models import Ciudad
    from app.modules.plataforma.models import Empresa, Plan, Suscripcion
    from app.modules.seguridad.models import Rol

    for datos in PLANES:
        if sesion.get(Plan, datos["id"]) is None:
            sesion.add(Plan(**datos))
    sesion.flush()
    # Los planes van con id fijo: la secuencia no se entera y el primer plan
    # creado por la API (CU-02) chocaría con el 1. La migración hace lo mismo.
    sesion.execute(text("SELECT setval(pg_get_serial_sequence('plan', 'id'), (SELECT max(id) FROM plan))"))
    if sesion.get(Empresa, EMPRESA_PRUEBAS) is None:
        empresa = Empresa(nombre="Violet Boutique", slug="violet-boutique")
        sesion.add(empresa)
        sesion.flush()
        # La primera fila de una tabla recien creada: la secuencia da el 1.
        assert empresa.id == EMPRESA_PRUEBAS, empresa.id
        # CU-05: sin suscripcion vigente la empresa solo consulta. Igual que
        # la 0022: el Empresarial, que no limita nada.
        sesion.add(
            Suscripcion(
                plan_id=3,
                inicio=date.today() - timedelta(days=1),
                vencimiento=date.today() + timedelta(days=365),
            )
        )

    roles = {
        "ADMINISTRADOR": "Administra todo el sistema.",
        "CLIENTE": "Compra y reserva prendas.",
        "ENCARGADO": "Responsable de una sucursal.",
        "CAJERO": "Atiende el punto de venta.",
        "PROVEEDOR": "Abastece productos.",
        "ADMIN_PLATAFORMA": "Administra la plataforma SaaS.",
    }
    for nombre, descripcion in roles.items():
        if sesion.scalar(select(Rol).where(Rol.nombre == nombre)) is None:
            sesion.add(Rol(nombre=nombre, descripcion=descripcion))

    ciudades = [("Santa Cruz", "Santa Cruz"), ("La Paz", "La Paz")]
    for nombre, departamento in ciudades:
        if sesion.scalar(select(Ciudad).where(Ciudad.nombre == nombre)) is None:
            sesion.add(Ciudad(nombre=nombre, departamento=departamento))

    sesion.commit()


@pytest.fixture
def api(db, fabrica_sesiones):
    """Cliente HTTP apuntando a la base de pruebas.

    Sustituye la dependencia get_db para que la aplicacion use esta base y no
    la del .env, incluso si alguien olvidara exportar TEST_DATABASE_URL.
    """

    def _get_db_de_prueba():
        sesion = fabrica_sesiones()
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = _get_db_de_prueba
    with _ClienteDePruebas(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _iniciar_sesion(
    api: TestClient, correo: str, contrasena: str, empresa: str | None = SLUG_PRUEBAS
) -> str:
    """CU-06: `empresa` es el slug; `None` para el administrador de la plataforma."""
    respuesta = api.post(
        "/api/v1/auth/login",
        json={"empresa": empresa, "correo": correo, "contrasena": contrasena},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


@pytest.fixture
def token_cliente(api: TestClient) -> str:
    """Registra un cliente por CU-01 y devuelve su token de CU-02."""
    respuesta = api.post(
        "/api/v1/auth/registro",
        json={
            "nombres": "Ana",
            "apellidos": "Quiroga",
            "documento": "9876543",
            "telefono": "70011223",
            "correo": CORREO_CLIENTE,
            "contrasena": CLAVE_CLIENTE,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return _iniciar_sesion(api, CORREO_CLIENTE, CLAVE_CLIENTE)


@pytest.fixture
def cabeceras_cliente(token_cliente: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_cliente}"}


@pytest.fixture
def cabeceras_admin(api: TestClient, db) -> dict[str, str]:
    """Un administrador, creado directamente en la base.

    No se puede crear por la API: dar de alta un administrador exige ya estar
    autenticado como administrador (CU-03).
    """
    from sqlalchemy import select

    from app.modules.seguridad.models import Rol, Usuario

    rol = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    db.add(
        Usuario(
            correo=CORREO_ADMIN,
            hash_contrasena=hash_password(CLAVE_ADMIN),
            nombres="Root",
            apellidos="Pruebas",
            rol_id=rol.id,
        )
    )
    db.commit()
    return {"Authorization": f"Bearer {_iniciar_sesion(api, CORREO_ADMIN, CLAVE_ADMIN)}"}
