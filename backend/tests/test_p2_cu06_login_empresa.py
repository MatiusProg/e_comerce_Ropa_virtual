"""CU-06 Iniciar sesión en una empresa (2do parcial; evoluciona el CU-02).

Cubre la ficha del 2.6: el login con el slug y el token con la empresa
(flujo principal), la plataforma sin slug (1a, RN-12), la empresa inexistente
o de baja (2a), la suscripción vencida que entra en solo consulta (3a), las
credenciales incorrectas (4a) y el cierre de sesión (6a). Y lo que trae el
correo único por empresa: la misma persona en dos empresas, y la cuenta única
del cliente que entra a otra tienda (RN-13).
"""

import pytest
from sqlalchemy import null, select, update

from app.core.security import decodificar_token, hash_password
from app.core.tenencia import fijar_empresa, modo_plataforma
from app.modules.plataforma.models import ClienteEmpresa, Empresa, Suscripcion
from app.modules.seguridad.models import Cliente, Rol, Usuario
from tests.conftest import CLAVE_ADMIN, CORREO_ADMIN, CORREO_CLIENTE, CLAVE_CLIENTE

LOGIN = "/api/v1/auth/login"
CLAVE = "Secreta123"


def _login(api, correo: str, clave: str, empresa: str | None):
    return api.post(LOGIN, json={"empresa": empresa, "correo": correo, "contrasena": clave})


def _usuario(db, correo: str, rol: str, empresa_id: int | None) -> Usuario:
    usuario = Usuario(
        correo=correo,
        hash_contrasena=hash_password(CLAVE),
        nombres="Prueba",
        apellidos="Login",
        rol_id=db.scalar(select(Rol.id).where(Rol.nombre == rol)),
        # null() y no None: con None, el DEFAULT le pone la empresa del contexto.
        empresa_id=null() if empresa_id is None else empresa_id,
    )
    db.add(usuario)
    db.commit()
    return usuario


@pytest.fixture
def tienda_b(db) -> int:
    """Una segunda empresa, con su suscripción vigente."""
    empresa = Empresa(nombre="Tienda B", slug="tienda-b")
    db.add(empresa)
    db.flush()
    vigente = db.scalar(select(Suscripcion))
    db.add(Suscripcion(empresa_id=empresa.id, plan_id=3, inicio=vigente.inicio,
                       vencimiento=vigente.vencimiento))
    modo_plataforma(db)  # el WITH CHECK no deja escribir otra empresa
    db.commit()
    fijar_empresa(db, 1)
    return empresa.id


# --------------------------------------------------------------------------
#  Flujo principal
# --------------------------------------------------------------------------
def test_con_el_slug_entra_y_el_token_lleva_la_empresa(api, cabeceras_admin):
    respuesta = _login(api, CORREO_ADMIN, CLAVE_ADMIN, "violet-boutique")

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["usuario"]["empresa"] == {"id": 1, "nombre": "Violet Boutique",
                                            "slug": "violet-boutique"}
    assert cuerpo["usuario"]["solo_consulta"] is False
    assert decodificar_token(cuerpo["access_token"])["empresa_id"] == 1


def test_el_slug_no_distingue_mayusculas_ni_espacios(api, cabeceras_admin):
    assert _login(api, CORREO_ADMIN, CLAVE_ADMIN, "  Violet-Boutique ").status_code == 200


def test_yo_devuelve_la_empresa_de_la_sesion(api, cabeceras_admin):
    yo = api.get("/api/v1/auth/yo", headers=cabeceras_admin)
    assert yo.status_code == 200
    assert yo.json()["empresa"]["slug"] == "violet-boutique"


# --------------------------------------------------------------------------
#  1a: sin slug, solo la plataforma (RN-12)
# --------------------------------------------------------------------------
def test_sin_slug_entra_el_administrador_de_la_plataforma(api, db):
    _usuario(db, "plataforma@violetboutique.bo", "ADMIN_PLATAFORMA", None)

    respuesta = _login(api, "plataforma@violetboutique.bo", CLAVE, None)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["usuario"]["empresa"] is None
    assert decodificar_token(respuesta.json()["access_token"])["empresa_id"] is None


@pytest.mark.parametrize("clave", [CLAVE_ADMIN, "Equivocada1"], ids=["bien", "mal"])
def test_sin_slug_el_personal_tiene_que_indicar_la_empresa(api, cabeceras_admin, clave):
    """Con la contraseña bien o mal, la misma respuesta: no revela la cuenta."""
    respuesta = _login(api, CORREO_ADMIN, clave, None)
    assert respuesta.status_code == 422
    assert "empresa" in respuesta.json()["detail"]


def test_la_plataforma_no_entra_con_un_slug(api, db):
    _usuario(db, "plataforma@violetboutique.bo", "ADMIN_PLATAFORMA", None)
    assert _login(api, "plataforma@violetboutique.bo", CLAVE, "violet-boutique").status_code == 401


# --------------------------------------------------------------------------
#  2a y 4a
# --------------------------------------------------------------------------
def test_empresa_inexistente(api, cabeceras_admin):
    respuesta = _login(api, CORREO_ADMIN, CLAVE_ADMIN, "no-existe")
    assert respuesta.status_code == 404
    assert "Empresa no encontrada" in respuesta.json()["detail"]


def test_empresa_dada_de_baja_es_empresa_no_encontrada(api, db, tienda_b):
    _usuario(db, "admin@tiendab.bo", "ADMINISTRADOR", tienda_b)
    db.execute(update(Empresa).where(Empresa.id == tienda_b).values(estado="BAJA"))
    db.commit()
    assert _login(api, "admin@tiendab.bo", CLAVE, "tienda-b").status_code == 404


def test_credenciales_incorrectas_sin_decir_cual(api, cabeceras_admin):
    mala_clave = _login(api, CORREO_ADMIN, "Equivocada1", "violet-boutique")
    no_existe = _login(api, "nadie@violetboutique.bo", CLAVE, "violet-boutique")
    assert mala_clave.status_code == no_existe.status_code == 401
    assert mala_clave.json() == no_existe.json()


def test_el_personal_de_una_empresa_no_entra_por_otra(api, db, cabeceras_admin, tienda_b):
    assert _login(api, CORREO_ADMIN, CLAVE_ADMIN, "tienda-b").status_code == 401


# --------------------------------------------------------------------------
#  3a: suscripción vencida o suspendida
# --------------------------------------------------------------------------
def test_con_la_suscripcion_suspendida_entra_en_solo_consulta(api, db, cabeceras_admin):
    db.execute(update(Suscripcion).values(estado="SUSPENDIDA"))
    db.commit()

    respuesta = _login(api, CORREO_ADMIN, CLAVE_ADMIN, "violet-boutique")

    assert respuesta.status_code == 200
    assert respuesta.json()["usuario"]["solo_consulta"] is True


# --------------------------------------------------------------------------
#  El correo único por empresa
# --------------------------------------------------------------------------
def test_la_misma_persona_trabaja_en_dos_empresas_con_el_mismo_correo(api, db, tienda_b):
    _usuario(db, "rosa@correo.bo", "ADMINISTRADOR", 1)
    _usuario(db, "rosa@correo.bo", "CAJERO", tienda_b)

    en_a = _login(api, "rosa@correo.bo", CLAVE, "violet-boutique").json()["usuario"]
    en_b = _login(api, "rosa@correo.bo", CLAVE, "tienda-b").json()["usuario"]

    assert (en_a["rol"], en_a["empresa"]["slug"]) == ("ADMINISTRADOR", "violet-boutique")
    assert (en_b["rol"], en_b["empresa"]["slug"]) == ("CAJERO", "tienda-b")
    assert en_a["id"] != en_b["id"]


def test_dentro_de_una_empresa_el_correo_no_se_repite(api, cabeceras_admin):
    datos = {"nombres": "Otro", "apellidos": "Admin", "correo": CORREO_ADMIN,
             "contrasena": "Admin12345", "rol": "ADMINISTRADOR"}
    respuesta = api.post("/api/v1/usuarios", json=datos, headers=cabeceras_admin)
    assert respuesta.status_code == 409, respuesta.text


# --------------------------------------------------------------------------
#  El cliente: una cuenta, varias tiendas (RN-13)
# --------------------------------------------------------------------------
def test_el_cliente_entra_a_otra_tienda_con_la_misma_cuenta(api, db, token_cliente, tienda_b):
    respuesta = _login(api, CORREO_CLIENTE, CLAVE_CLIENTE, "tienda-b")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["usuario"]["empresa"]["slug"] == "tienda-b"
    assert decodificar_token(respuesta.json()["access_token"])["empresa_id"] == tienda_b
    # Y desde ahora la tienda B lo ve como su cliente.
    modo_plataforma(db)
    cliente_id = db.scalar(
        select(Cliente.id).join(Usuario).where(Usuario.correo == CORREO_CLIENTE)
    )
    empresas = set(db.scalars(
        select(ClienteEmpresa.empresa_id).where(ClienteEmpresa.cliente_id == cliente_id)
    ))
    fijar_empresa(db, 1)
    assert empresas == {1, tienda_b}


def test_el_token_del_cliente_trabaja_en_la_tienda_donde_entro(api, db, token_cliente, tienda_b):
    """Con el token de la tienda B el cliente opera, aunque el encabezado diga otra."""
    token_b = _login(api, CORREO_CLIENTE, CLAVE_CLIENTE, "tienda-b").json()["access_token"]
    cabeceras = {"Authorization": f"Bearer {token_b}", "X-Empresa": "1"}

    respuesta = api.get("/api/v1/tienda/carrito", headers=cabeceras)
    assert respuesta.status_code == 200, respuesta.text


# --------------------------------------------------------------------------
#  6a y la recuperación de contraseña
# --------------------------------------------------------------------------
def test_cerrar_sesion_invalida_el_token(api, cabeceras_admin):
    assert api.post("/api/v1/auth/logout", headers=cabeceras_admin).status_code == 204
    assert api.get("/api/v1/auth/yo", headers=cabeceras_admin).status_code == 401


def test_la_recuperacion_del_personal_se_pide_con_el_slug(api, db, cabeceras_admin, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.modules.seguridad.service.enviar", lambda m: enviados.append(m))

    api.post("/api/v1/auth/recuperacion", json={"correo": CORREO_ADMIN})
    assert enviados == []  # sin slug se busca entre las cuentas sin empresa
    api.post("/api/v1/auth/recuperacion",
             json={"empresa": "violet-boutique", "correo": CORREO_ADMIN})
    assert len(enviados) == 1


def test_el_cliente_recupera_con_o_sin_slug(api, token_cliente, monkeypatch):
    """La pantalla trae el slug recordado: el cliente no tiene que borrarlo."""
    enviados = []
    monkeypatch.setattr("app.modules.seguridad.service.enviar", lambda m: enviados.append(m))

    api.post("/api/v1/auth/recuperacion", json={"correo": CORREO_CLIENTE})
    api.post("/api/v1/auth/recuperacion",
             json={"empresa": "violet-boutique", "correo": CORREO_CLIENTE})
    assert len(enviados) == 2
