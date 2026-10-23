"""2do parcial, CU-08 Gestionar usuarios de la empresa.

`usuario` es tabla de identidad y NO tiene RLS: el aislamiento de este caso de
uso lo pone el código. Estas pruebas son las que lo sostienen --- si alguien
quita el filtro por empresa, el administrador de una empresa vería y tocaría
las cuentas de otra.
"""

from datetime import time

import pytest
from sqlalchemy import select, update

from app.core.security import hash_password
from app.core.tenencia import CLAVE_EMPRESA
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.plataforma.models import ClienteEmpresa, Empresa
from app.modules.seguridad.models import Cliente, Rol, Usuario
from tests.conftest import CORREO_CLIENTE, _iniciar_sesion

URL = "/api/v1/usuarios"
CLAVE = "Clave12345"


@pytest.fixture
def empresa_b(db) -> int:
    existente = db.scalar(select(Empresa).where(Empresa.slug == "tienda-b"))
    if existente is not None:
        return existente.id
    empresa = Empresa(nombre="Tienda B", slug="tienda-b")
    db.add(empresa)
    db.commit()
    return empresa.id


@pytest.fixture
def sesion_b(fabrica_sesiones, empresa_b):
    sesion = fabrica_sesiones()
    sesion.info[CLAVE_EMPRESA] = empresa_b
    yield sesion
    sesion.close()


def _usuario(sesion, correo: str, rol: str, empresa_id: int | None) -> Usuario:
    rol_id = sesion.scalar(select(Rol.id).where(Rol.nombre == rol))
    usuario = Usuario(correo=correo, hash_contrasena=hash_password(CLAVE),
                      nombres="Nombre", apellidos="Apellido", rol_id=rol_id)
    sesion.add(usuario)
    sesion.commit()
    if empresa_id is None:
        # Un None en el objeto no llega al INSERT: la base pone el DEFAULT de la
        # empresa del contexto. Igual que `agregar_cliente`, se borra después.
        sesion.execute(update(Usuario).where(Usuario.id == usuario.id).values(empresa_id=None))
        sesion.commit()
    elif empresa_id != usuario.empresa_id:
        raise AssertionError("la sesión tiene que ser de la empresa del usuario")
    return usuario


def _sucursal(sesion, nombre: str) -> int:
    ciudad = sesion.scalar(select(Ciudad.id).where(Ciudad.nombre == "Santa Cruz"))
    sucursal = Sucursal(ciudad_id=ciudad, nombre=nombre, direccion="Calle 1",
                        horario_apertura=time(9), horario_cierre=time(20))
    sesion.add(sucursal)
    sesion.commit()
    return sucursal.id


def _correos(api, cabeceras) -> set[str]:
    respuesta = api.get(URL, headers=cabeceras, params={"tamano": 100})
    assert respuesta.status_code == 200, respuesta.text
    return {u["correo"] for u in respuesta.json()["items"]}


# --- Paso 2: solo los usuarios de su empresa --------------------------------

def test_lista_solo_el_personal_de_su_empresa(api, cabeceras_admin, db, sesion_b, empresa_b):
    _usuario(db, "propio@a.bo", "PROVEEDOR", 1)
    _usuario(sesion_b, "ajeno@b.bo", "PROVEEDOR", empresa_b)

    correos = _correos(api, cabeceras_admin)

    assert "propio@a.bo" in correos
    assert "ajeno@b.bo" not in correos


def test_lista_los_clientes_que_compran_en_la_empresa(
    api, cabeceras_admin, token_cliente, db, sesion_b, empresa_b
):
    """El cliente registrado en la tienda A aparece en A y no en B (RN-13)."""
    assert CORREO_CLIENTE in _correos(api, cabeceras_admin)

    admin_b = _usuario(sesion_b, "admin@b.bo", "ADMINISTRADOR", empresa_b)
    cabeceras_b = {"Authorization": f"Bearer {_iniciar_sesion(api, admin_b.correo, CLAVE)}"}

    assert CORREO_CLIENTE not in _correos(api, cabeceras_b)


def test_el_total_cuenta_solo_su_empresa(api, cabeceras_admin, db, sesion_b, empresa_b):
    for i in range(3):
        _usuario(sesion_b, f"b{i}@b.bo", "PROVEEDOR", empresa_b)

    cuerpo = api.get(URL, headers=cabeceras_admin).json()

    assert cuerpo["total"] == len(cuerpo["items"]) == 1  # solo el administrador


# --- Otra empresa: no existe -------------------------------------------------

@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("get", "", None),
    ("patch", "", {"nombres": "Hackeado"}),
    ("patch", "/estado", {"activo": False}),
    ("delete", "", None),
])
def test_usuario_de_otra_empresa_es_404(api, cabeceras_admin, sesion_b, empresa_b,
                                        metodo, ruta, cuerpo):
    ajeno = _usuario(sesion_b, "ajeno@b.bo", "PROVEEDOR", empresa_b)

    kwargs = {"headers": cabeceras_admin}
    if cuerpo is not None:
        kwargs["json"] = cuerpo
    respuesta = getattr(api, metodo)(f"{URL}/{ajeno.id}{ruta}", **kwargs)

    assert respuesta.status_code == 404, respuesta.text
    sesion_b.refresh(ajeno)
    assert ajeno.nombres == "Nombre"
    assert ajeno.activo is True


# --- El cliente se ve, pero su cuenta es de la plataforma --------------------

@pytest.mark.parametrize("metodo,ruta,cuerpo", [
    ("patch", "", {"nombres": "Otro"}),
    ("patch", "/estado", {"activo": False}),
    ("delete", "", None),
])
def test_la_cuenta_del_cliente_no_se_modifica(api, cabeceras_admin, token_cliente, db,
                                              metodo, ruta, cuerpo):
    cliente = db.scalar(select(Usuario).where(Usuario.correo == CORREO_CLIENTE))
    kwargs = {"headers": cabeceras_admin}
    if cuerpo is not None:
        kwargs["json"] = cuerpo

    respuesta = getattr(api, metodo)(f"{URL}/{cliente.id}{ruta}", **kwargs)

    assert respuesta.status_code == 409, respuesta.text
    assert "cliente" in respuesta.json()["detail"]
    db.refresh(cliente)
    assert cliente.activo is True


def test_el_cliente_de_la_empresa_se_puede_ver(api, cabeceras_admin, token_cliente, db):
    cliente = db.scalar(select(Usuario).where(Usuario.correo == CORREO_CLIENTE))

    respuesta = api.get(f"{URL}/{cliente.id}", headers=cabeceras_admin)

    assert respuesta.status_code == 200
    assert respuesta.json()["rol"] == "CLIENTE"


# --- Alta: con la empresa del token ------------------------------------------

def test_crea_con_la_empresa_del_administrador(api, cabeceras_admin, db):
    respuesta = api.post(URL, headers=cabeceras_admin, json={
        "correo": "nuevo@a.bo", "contrasena": CLAVE, "nombres": "Nuevo",
        "apellidos": "Proveedor", "rol": "PROVEEDOR",
    })

    assert respuesta.status_code == 201, respuesta.text
    creado = db.scalar(select(Usuario).where(Usuario.correo == "nuevo@a.bo"))
    assert creado.empresa_id == 1


def test_crea_encargado_en_una_sucursal_propia(api, cabeceras_admin, db):
    sucursal = _sucursal(db, "Centro")

    respuesta = api.post(URL, headers=cabeceras_admin, json={
        "correo": "encargado@a.bo", "contrasena": CLAVE, "nombres": "En",
        "apellidos": "Cargado", "rol": "ENCARGADO", "sucursal_id": sucursal,
        "documento": "1234567",
    })

    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["sucursal_id"] == sucursal


def test_no_asigna_una_sucursal_de_otra_empresa(api, cabeceras_admin, db, sesion_b):
    """Paso 5: la sucursal tiene que ser de la misma empresa. El RLS no la deja ver."""
    ajena = _sucursal(sesion_b, "Sucursal B")

    respuesta = api.post(URL, headers=cabeceras_admin, json={
        "correo": "encargado@a.bo", "contrasena": CLAVE, "nombres": "En",
        "apellidos": "Cargado", "rol": "ENCARGADO", "sucursal_id": ajena,
        "documento": "1234567",
    })

    assert respuesta.status_code == 422, respuesta.text
    assert db.scalar(select(Usuario).where(Usuario.correo == "encargado@a.bo")) is None


def test_no_crea_clientes_desde_el_panel(api, cabeceras_admin, db):
    respuesta = api.post(URL, headers=cabeceras_admin, json={
        "correo": "cliente.panel@a.bo", "contrasena": CLAVE, "nombres": "Cli",
        "apellidos": "Ente", "rol": "CLIENTE",
    })

    assert respuesta.status_code == 422, respuesta.text


def test_no_cambia_a_rol_cliente(api, cabeceras_admin, db):
    propio = _usuario(db, "propio@a.bo", "PROVEEDOR", 1)

    respuesta = api.patch(f"{URL}/{propio.id}", headers=cabeceras_admin, json={"rol": "CLIENTE"})

    assert respuesta.status_code == 422, respuesta.text


def test_los_roles_asignables_no_incluyen_cliente(api, cabeceras_admin):
    roles = {r["nombre"] for r in api.get("/api/v1/auth/roles", headers=cabeceras_admin).json()}

    assert "CLIENTE" not in roles
    assert {"ADMINISTRADOR", "ENCARGADO", "CAJERO", "PROVEEDOR"} <= roles


# --- 3a: editar y desactivar el propio personal ------------------------------

def test_edita_y_desactiva_su_personal(api, cabeceras_admin, db):
    propio = _usuario(db, "propio@a.bo", "PROVEEDOR", 1)

    editado = api.patch(f"{URL}/{propio.id}", headers=cabeceras_admin, json={"nombres": "Nuevo"})
    estado = api.patch(f"{URL}/{propio.id}/estado", headers=cabeceras_admin,
                       json={"activo": False})

    assert editado.status_code == 200 and editado.json()["nombres"] == "Nuevo"
    assert estado.status_code == 200 and estado.json()["activo"] is False
    # Un usuario desactivado no puede iniciar sesión.
    login = api.post("/api/v1/auth/login", json={"correo": "propio@a.bo", "contrasena": CLAVE})
    assert login.status_code in (401, 403)


def test_usuario_sin_empresa_no_gestiona(api, db):
    """El administrador de la plataforma no tiene empresa: no hay usuarios que gestionar."""
    _usuario(db, "plataforma@violet.bo", "ADMINISTRADOR", None)
    token = _iniciar_sesion(api, "plataforma@violet.bo", CLAVE)

    respuesta = api.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 403
