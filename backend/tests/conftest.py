"""Configuracion compartida de las pruebas (flujo de Pruebas del PUDS).

REGLA DE SEGURIDAD DE ESTE ARCHIVO
----------------------------------
Las pruebas NUNCA deben tocar la base de produccion. El `.env` del proyecto
apunta a Supabase, asi que aqui se exige una variable aparte, TEST_DATABASE_URL,
y se la impone sobre DATABASE_URL antes de importar la aplicacion. Si esa
variable no esta definida, las pruebas que necesitan base se SALTAN: es
preferible no probar a probar contra los datos reales.

    # PowerShell
    $env:TEST_DATABASE_URL = "postgresql+psycopg://usuario:clave@localhost:5432/fashionstore_test"
    .venv\\Scripts\\python.exe -m pytest

La base indicada se crea y se destruye entera en cada corrida, asi que tiene
que ser una base dedicada a pruebas y vacia.
"""

import os

import pytest
from fastapi.testclient import TestClient

URL_PRUEBAS = os.environ.get("TEST_DATABASE_URL")

# Antes de importar la aplicacion: si hay base de pruebas, es la unica que la
# aplicacion va a conocer. pydantic-settings da prioridad a las variables de
# entorno por encima del .env, de modo que esto desactiva la URL de Supabase.
if URL_PRUEBAS:
    os.environ["DATABASE_URL"] = URL_PRUEBAS

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

# Importar los modelos puebla Base.metadata. Sin esto, create_all no crearia
# ninguna tabla: el metadata solo conoce las clases que fueron importadas.
from app.modules.catalogo import models as modelos_catalogo  # noqa: E402,F401
from app.modules.organizacion import models as modelos_organizacion  # noqa: E402,F401
from app.modules.seguridad import models as modelos_seguridad  # noqa: E402,F401

#: Tablas que se vacian entre una prueba y la siguiente. El resto (roles,
#: ciudades) son datos de referencia y se siembran una sola vez.
#:
#: `sucursal` entra aca porque CU-06 crea una por prueba y el UNIQUE
#: (ciudad_id, nombre) haria fallar a la segunda. `empleado` cascadearia con
#: usuario, pero se nombra igual: depender de un CASCADE para la limpieza
#: hace que la prueba dependa de un detalle del esquema.
TABLAS_VOLATILES = (
    "direccion_cliente",
    "sesion_token",
    "cliente",
    "empleado",
    "proveedor",
    "sucursal",
    "usuario",
    "categoria",
    "talla",
    "color",
    "coleccion",
    "temporada",
)

#: Credenciales del cliente de prueba. La contrasena cumple la regla del
#: RNF01: ocho caracteres, con letra y digito.
CORREO_CLIENTE = "ana.cliente@fashionstore.bo"
CLAVE_CLIENTE = "Secreta123"
CORREO_ADMIN = "admin.pruebas@fashionstore.bo"
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


@pytest.fixture(scope="session")
def fabrica_sesiones(motor):
    from sqlalchemy.orm import sessionmaker

    return sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)


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
    """Siembra los roles y las ciudades. Es idempotente."""
    from sqlalchemy import select

    from app.modules.organizacion.models import Ciudad
    from app.modules.seguridad.models import Rol

    roles = {
        "ADMINISTRADOR": "Administra todo el sistema.",
        "CLIENTE": "Compra y reserva prendas.",
        "ENCARGADO": "Responsable de una sucursal.",
        "CAJERO": "Atiende el punto de venta.",
        "PROVEEDOR": "Abastece productos.",
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
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()


def _iniciar_sesion(api: TestClient, correo: str, contrasena: str) -> str:
    respuesta = api.post(
        "/api/v1/auth/login", json={"correo": correo, "contrasena": contrasena}
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
