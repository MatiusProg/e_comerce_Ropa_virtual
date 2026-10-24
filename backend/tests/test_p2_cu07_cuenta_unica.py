"""2do parcial, CU-07 Registrar cliente con cuenta única.

El cliente tiene UNA cuenta en la plataforma (RN-13). Si ya se registró en la
tienda A y quiere comprar en la B, no se le crea otra: inicia sesión con la
suya y queda asociado también a B (flujo alternativo 4b).
"""

import pytest
from sqlalchemy import func, select

from app.core.security import hash_password
from app.core.tenencia import CLAVE_EMPRESA, modo_plataforma
from app.db.session import get_db
from app.main import app
from app.modules.plataforma.models import ClienteEmpresa, Empresa
from app.modules.seguridad.models import Cliente, Rol, Usuario
from tests.conftest import CLAVE_ADMIN, CLAVE_CLIENTE, CORREO_ADMIN, CORREO_CLIENTE

REGISTRO = "/api/v1/auth/registro"
ASOCIAR = "/api/v1/auth/registro/asociar"
DATOS = {"nombres": "Ana", "apellidos": "Quiroga", "correo": CORREO_CLIENTE,
         "contrasena": CLAVE_CLIENTE}


@pytest.fixture
def api(api, fabrica_sesiones):
    """El `api` de siempre, pero la empresa la pone la tienda, como en producción.

    La fábrica de las pruebas fija la empresa 1 en toda sesión, y así el
    encabezado `X-Empresa` no llegaría nunca al RLS. Acá la sesión sale sin
    empresa y la toma de `EmpresaDeLaTiendaMiddleware` (o del usuario, si es
    del personal).
    """

    def _sin_empresa_fija():
        sesion = fabrica_sesiones()
        sesion.info.pop(CLAVE_EMPRESA, None)
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = _sin_empresa_fija
    return api


@pytest.fixture
def tienda_b(db) -> dict[str, str]:
    """Las cabeceras de una petición hecha desde la tienda de la empresa B."""
    empresa = Empresa(nombre="Tienda B", slug="tienda-b")
    db.add(empresa)
    db.commit()
    return {"X-Empresa": str(empresa.id)}


@pytest.fixture
def plataforma(fabrica_sesiones):
    """`cliente_empresa` tiene RLS: para verla entera, una sesión de plataforma."""
    sesion = fabrica_sesiones()
    modo_plataforma(sesion)
    yield sesion
    sesion.close()


def _empresas(plataforma, correo: str) -> set[int]:
    empresas = set(plataforma.scalars(
        select(ClienteEmpresa.empresa_id)
        .join(Cliente, Cliente.id == ClienteEmpresa.cliente_id)
        .join(Usuario, Usuario.id == Cliente.usuario_id)
        .where(Usuario.correo == correo)
    ))
    plataforma.rollback()
    return empresas


# --- Flujo principal ---------------------------------------------------------

def test_cuenta_nueva_queda_en_la_tienda_donde_se_registra(api, db, tienda_b, plataforma):
    respuesta = api.post(REGISTRO, json=DATOS, headers=tienda_b)

    assert respuesta.status_code == 201, respuesta.text
    usuario = db.scalar(select(Usuario).where(Usuario.correo == CORREO_CLIENTE))
    assert usuario.empresa_id is None  # el cliente no es de ninguna empresa
    assert _empresas(plataforma, CORREO_CLIENTE) == {int(tienda_b["X-Empresa"])}


# --- 4b: el correo ya tiene cuenta de cliente --------------------------------

def test_registrarse_otra_vez_ofrece_usar_la_cuenta(api, token_cliente, tienda_b):
    respuesta = api.post(REGISTRO, json=DATOS, headers=tienda_b)

    assert respuesta.status_code == 409
    assert "cuenta de cliente" in respuesta.json()["detail"]


def test_asociar_usa_la_misma_cuenta_en_la_otra_tienda(api, db, token_cliente, tienda_b, plataforma):
    respuesta = api.post(ASOCIAR, headers=tienda_b,
                         json={"correo": CORREO_CLIENTE, "contrasena": CLAVE_CLIENTE})

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["access_token"]
    assert respuesta.json()["usuario"]["rol"] == "CLIENTE"
    # Una sola cuenta, ahora en las dos empresas.
    assert db.scalar(select(func.count()).select_from(Usuario)
                     .where(Usuario.correo == CORREO_CLIENTE)) == 1
    assert _empresas(plataforma, CORREO_CLIENTE) == {1, int(tienda_b["X-Empresa"])}


def test_asociar_dos_veces_no_duplica(api, db, token_cliente, tienda_b, plataforma):
    credenciales = {"correo": CORREO_CLIENTE, "contrasena": CLAVE_CLIENTE}
    api.post(ASOCIAR, headers=tienda_b, json=credenciales)

    respuesta = api.post(ASOCIAR, headers=tienda_b, json=credenciales)

    assert respuesta.status_code == 200, respuesta.text
    assert _empresas(plataforma, CORREO_CLIENTE) == {1, int(tienda_b["X-Empresa"])}


def test_asociar_con_la_contrasena_equivocada_no_asocia(api, db, token_cliente, tienda_b, plataforma):
    respuesta = api.post(ASOCIAR, headers=tienda_b,
                         json={"correo": CORREO_CLIENTE, "contrasena": "Otra12345"})

    assert respuesta.status_code == 401
    assert _empresas(plataforma, CORREO_CLIENTE) == {1}


def test_asociar_una_cuenta_del_personal_no_se_permite(api, db, cabeceras_admin, tienda_b):
    respuesta = api.post(ASOCIAR, headers=tienda_b,
                         json={"correo": CORREO_ADMIN, "contrasena": CLAVE_ADMIN})

    assert respuesta.status_code == 409
    assert "personal" in respuesta.json()["detail"]


def test_asociar_una_cuenta_desactivada_no_asocia(api, db, token_cliente, tienda_b, plataforma):
    usuario = db.scalar(select(Usuario).where(Usuario.correo == CORREO_CLIENTE))
    usuario.activo = False
    db.commit()

    respuesta = api.post(ASOCIAR, headers=tienda_b,
                         json={"correo": CORREO_CLIENTE, "contrasena": CLAVE_CLIENTE})

    assert respuesta.status_code == 403
    assert _empresas(plataforma, CORREO_CLIENTE) == {1}


def test_el_correo_del_personal_sigue_siendo_duplicado(api, db, tienda_b):
    """El 4b es solo para clientes: el correo de un empleado no se ofrece."""
    rol = db.scalar(select(Rol.id).where(Rol.nombre == "CAJERO"))
    db.add(Usuario(correo="cajero@a.bo", hash_contrasena=hash_password("Clave12345"),
                   nombres="Ca", apellidos="Jero", rol_id=rol))
    db.commit()

    respuesta = api.post(REGISTRO, headers=tienda_b, json={**DATOS, "correo": "cajero@a.bo"})

    assert respuesta.status_code == 409
    assert "cuenta de cliente" not in respuesta.json()["detail"]
