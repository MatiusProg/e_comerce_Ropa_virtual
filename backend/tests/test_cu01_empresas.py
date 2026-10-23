"""CU-01 Gestionar empresas (2do parcial). Lo opera el administrador de la plataforma.

Cubre la ficha del 2.6: el alta transaccional (pasos 4 a 6), la edición sin
slug (3a), la baja que corta el acceso (3b), el slug repetido (4a), y que una
empresa nueva quede aislada de las demás desde el primer minuto.
"""

from decimal import Decimal

import pytest
from sqlalchemy import null, select

from app.core.security import hash_password
from app.core.tenencia import CLAVE_EMPRESA, modo_plataforma
from app.modules.bitacora.models import AsientoBitacora
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.seguridad.models import Rol, Usuario

API = "/api/v1"
CORREO_PLATAFORMA = "plataforma@violetboutique.bo"
CLAVE = "Plataforma123"


@pytest.fixture
def planes(db):
    """Los tres planes de la migración 0022 (las pruebas arman el esquema con create_all)."""
    for id_, codigo, nombre, precio in (
        (1, "BASICO", "Básico", "300"),
        (2, "PROFESIONAL", "Profesional", "750"),
        (3, "EMPRESARIAL", "Empresarial", "1500"),
    ):
        if db.get(Plan, id_) is None:
            db.add(Plan(id=id_, codigo=codigo, nombre=nombre, precio_mensual=Decimal(precio)))
    db.commit()


@pytest.fixture
def cabeceras_plataforma(api, db, planes) -> dict[str, str]:
    rol = db.scalar(select(Rol).where(Rol.nombre == "ADMIN_PLATAFORMA"))
    if db.scalar(select(Usuario).where(Usuario.correo == CORREO_PLATAFORMA)) is None:
        db.add(
            Usuario(
                correo=CORREO_PLATAFORMA,
                hash_contrasena=hash_password(CLAVE),
                nombres="Admin",
                apellidos="Plataforma",
                rol_id=rol.id,
                # null() y no None: con None, SQLAlchemy omite la columna y
                # el DEFAULT le pone la empresa del contexto.
                empresa_id=null(),
            )
        )
        db.commit()
    return _token(api, CORREO_PLATAFORMA, CLAVE)


def _token(api, correo: str, clave: str) -> dict[str, str]:
    respuesta = api.post(f"{API}/auth/login", json={"correo": correo, "contrasena": clave})
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def _alta(slug: str = "moda-andina", correo: str = "admin@modaandina.bo", plan: str = "BASICO"):
    return {
        "nombre": "Moda Andina",
        "razon_social": "Moda Andina S.R.L.",
        "nit": "1029384756",
        "slug": slug,
        "plan_codigo": plan,
        "sucursal": {"ciudad_id": 1, "direccion": "Av. Busch 123"},
        "administrador": {"correo": correo, "nombres": "Rosa", "apellidos": "Mamani"},
    }


# --------------------------------------------------------------------------
#  Acceso
# --------------------------------------------------------------------------
def test_la_cuenta_de_plataforma_no_tiene_empresa(db, cabeceras_plataforma):
    usuario = db.scalar(select(Usuario).where(Usuario.correo == CORREO_PLATAFORMA))
    assert usuario.empresa_id is None


def test_solo_la_plataforma_gestiona_empresas(api, cabeceras_admin):
    assert api.get(f"{API}/plataforma/empresas", headers=cabeceras_admin).status_code == 403
    assert api.get(f"{API}/plataforma/empresas").status_code == 401


# --------------------------------------------------------------------------
#  Flujo principal
# --------------------------------------------------------------------------
def test_alta_crea_todo_en_una_transaccion(api, db, cabeceras_plataforma, fabrica_sesiones):
    respuesta = api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["slug"] == "moda-andina"
    assert cuerpo["estado"] == "ACTIVA"
    assert cuerpo["suscripcion"]["plan_codigo"] == "BASICO"
    assert cuerpo["suscripcion"]["estado"] == "VIGENTE"
    assert (cuerpo["sucursales"], cuerpo["usuarios"]) == (1, 1)
    assert cuerpo["correo_enviado"] is True

    # El administrador entra con la contraseña temporal y ve SOLO su empresa.
    cabeceras = _token(api, "admin@modaandina.bo", cuerpo["contrasena_temporal"])
    sucursales = api.get(f"{API}/organizacion/sucursales", headers=cabeceras).json()
    filas = sucursales["items"] if isinstance(sucursales, dict) else sucursales
    assert [f["nombre"] for f in filas] == ["Casa matriz"]

    # La caja nace con la sucursal: la empresa puede vender desde el primer día.
    with fabrica_sesiones() as sesion:
        sesion.info[CLAVE_EMPRESA] = cuerpo["id"]
        from app.modules.ventas.models import Caja

        assert len(sesion.scalars(select(Caja)).all()) == 1


def test_slug_repetido_no_crea_nada(api, db, cabeceras_plataforma):
    assert api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma).status_code == 201
    respuesta = api.post(
        f"{API}/plataforma/empresas",
        json=_alta(correo="otro@modaandina.bo"),
        headers=cabeceras_plataforma,
    )
    assert respuesta.status_code == 409
    assert db.scalar(select(Usuario).where(Usuario.correo == "otro@modaandina.bo")) is None


def test_correo_ya_registrado(api, cabeceras_plataforma):
    respuesta = api.post(
        f"{API}/plataforma/empresas",
        json=_alta(slug="otra", correo=CORREO_PLATAFORMA),
        headers=cabeceras_plataforma,
    )
    assert respuesta.status_code == 409


def test_slug_invalido_y_plan_inexistente(api, cabeceras_plataforma):
    malo = api.post(f"{API}/plataforma/empresas", json=_alta(slug="Con Espacios"),
                    headers=cabeceras_plataforma)
    assert malo.status_code == 422
    sin_plan = api.post(f"{API}/plataforma/empresas", json=_alta(plan="PLATINO"),
                        headers=cabeceras_plataforma)
    assert sin_plan.status_code == 422


def test_listar_muestra_todas_con_su_plan(api, cabeceras_plataforma):
    api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma)
    filas = api.get(f"{API}/plataforma/empresas", headers=cabeceras_plataforma).json()
    assert {f["slug"] for f in filas} >= {"violet-boutique", "moda-andina"}


# --------------------------------------------------------------------------
#  Alternativos
# --------------------------------------------------------------------------
def test_editar_no_cambia_el_slug(api, cabeceras_plataforma):
    id_ = api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma).json()["id"]
    respuesta = api.patch(
        f"{API}/plataforma/empresas/{id_}",
        json={"nombre": "Moda Andina Bolivia", "slug": "cambiado"},
        headers=cabeceras_plataforma,
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Moda Andina Bolivia"
    assert respuesta.json()["slug"] == "moda-andina"


def test_la_baja_corta_el_acceso_y_la_reactivacion_lo_devuelve(api, cabeceras_plataforma):
    alta = api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma).json()
    clave = alta["contrasena_temporal"]
    cabeceras = _token(api, "admin@modaandina.bo", clave)

    assert api.post(f"{API}/plataforma/empresas/{alta['id']}/baja",
                    headers=cabeceras_plataforma).json()["estado"] == "BAJA"
    # El token que ya tenía deja de servir, y no puede volver a entrar.
    assert api.get(f"{API}/organizacion/sucursales", headers=cabeceras).status_code in (401, 403)
    login = api.post(f"{API}/auth/login", json={"correo": "admin@modaandina.bo", "contrasena": clave})
    assert login.status_code == 403

    api.post(f"{API}/plataforma/empresas/{alta['id']}/reactivar", headers=cabeceras_plataforma)
    _token(api, "admin@modaandina.bo", clave)


def test_lo_de_la_plataforma_no_queda_en_la_bitacora_de_ninguna_empresa(
    api, db, cabeceras_plataforma, fabrica_sesiones
):
    # La bitácora registra lo que cambia algo, no las consultas.
    api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma)
    with fabrica_sesiones() as sesion:
        modo_plataforma(sesion)
        asiento = sesion.scalars(
            select(AsientoBitacora)
            .where(AsientoBitacora.ruta.like("%/plataforma/empresas%"))
            .order_by(AsientoBitacora.id.desc())
        ).first()
    assert asiento is not None
    assert asiento.empresa_id is None


# --------------------------------------------------------------------------
#  Los usuarios (CU-03) también quedan acotados a la empresa
# --------------------------------------------------------------------------
def test_el_admin_de_una_empresa_no_ve_usuarios_de_otra(api, db, cabeceras_plataforma, cabeceras_admin):
    alta = api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma).json()
    cabeceras_b = _token(api, "admin@modaandina.bo", alta["contrasena_temporal"])

    correos_b = {u["correo"] for u in api.get(f"{API}/usuarios", headers=cabeceras_b).json()["items"]}
    assert correos_b == {"admin@modaandina.bo"}

    # Ni por id: el administrador de la empresa 1 no existe para la B.
    id_admin_a = db.scalar(select(Usuario.id).where(Usuario.correo == "admin.pruebas@violetboutique.bo"))
    assert api.get(f"{API}/usuarios/{id_admin_a}", headers=cabeceras_b).status_code == 404
    assert api.patch(f"{API}/usuarios/{id_admin_a}", json={"nombres": "X"},
                     headers=cabeceras_b).status_code == 404


def test_una_empresa_no_puede_crear_administradores_de_plataforma(api, cabeceras_admin):
    respuesta = api.post(
        f"{API}/usuarios",
        json={
            "nombres": "Falso",
            "apellidos": "Admin",
            "correo": "falso@violetboutique.bo",
            "contrasena": "Secreta123",
            "rol": "ADMIN_PLATAFORMA",
        },
        headers=cabeceras_admin,
    )
    assert respuesta.status_code in (400, 404, 422), respuesta.text


def test_el_personal_de_otra_empresa_recibe_su_sucursal_en_el_login(api, db, cabeceras_plataforma):
    """La sucursal sale de `empleado`, que tiene RLS: el login fija la empresa antes."""
    alta = api.post(f"{API}/plataforma/empresas", json=_alta(), headers=cabeceras_plataforma).json()
    cabeceras_b = _token(api, "admin@modaandina.bo", alta["contrasena_temporal"])
    sucursales = api.get(f"{API}/organizacion/sucursales", headers=cabeceras_b).json()
    sucursal_id = (sucursales["items"] if isinstance(sucursales, dict) else sucursales)[0]["id"]

    creado = api.post(
        f"{API}/usuarios",
        json={
            "nombres": "Carla",
            "apellidos": "Cajera",
            "correo": "cajera@modaandina.bo",
            "contrasena": "Secreta123",
            "rol": "CAJERO",
            "sucursal_id": sucursal_id,
            "documento": "5551234",
        },
        headers=cabeceras_b,
    )
    assert creado.status_code == 201, creado.text
    login = api.post(f"{API}/auth/login", json={"correo": "cajera@modaandina.bo", "contrasena": "Secreta123"})
    assert login.status_code == 200
    assert login.json()["usuario"]["sucursal_id"] == sucursal_id
