"""CU-03 Gestionar suscripciones (2do parcial). Lo opera el administrador de la plataforma.

Cubre la ficha del 2.7: ver la suscripción y su historial (pasos 1 y 2),
asignar o cambiar el plan con su vencimiento y su pago simulado (pasos 3 y 4),
que cerrar la anterior y abrir la nueva deje una sola vigente (paso 5, RN-02),
renovar desde el vencimiento (3a), suspender y reactivar con el modo solo
consulta (3b, RN-03), el aviso al bajar de plan sin borrar nada (5a, RN-04) y
el proceso diario que marca las vencidas (E1).
"""

from datetime import timedelta

import pytest
from sqlalchemy import func, null, select, update

from app.core import tiempo
from app.core.security import hash_password
from app.modules.plataforma.models import PagoSimulado, Plan, Suscripcion
from app.modules.seguridad.models import Rol, Usuario

from .conftest import EMPRESA_PRUEBAS

EMPRESA = f"/api/v1/plataforma/empresas/{EMPRESA_PRUEBAS}/suscripciones"
VENCIMIENTO = "/api/v1/plataforma/suscripciones/vencimiento"
SUCURSALES = "/api/v1/organizacion/sucursales"
CORREO_PLATAFORMA = "plataforma@violetboutique.bo"
CLAVE = "Plataforma123"
BASICO, PROFESIONAL, EMPRESARIAL = 1, 2, 3


@pytest.fixture
def plataforma(api, db) -> dict[str, str]:
    rol = db.scalar(select(Rol).where(Rol.nombre == "ADMIN_PLATAFORMA"))
    db.add(Usuario(correo=CORREO_PLATAFORMA, hash_contrasena=hash_password(CLAVE),
                   nombres="Admin", apellidos="Plataforma", rol_id=rol.id, empresa_id=null()))
    db.commit()
    r = api.post("/api/v1/auth/login",
                 json={"empresa": None, "correo": CORREO_PLATAFORMA, "contrasena": CLAVE})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _sucursal(api, admin, nombre: str):
    return api.post(SUCURSALES, headers=admin, json={
        "ciudad_id": 1, "nombre": nombre, "direccion": f"Avenida {nombre} 100",
        "horario_apertura": "09:00:00", "horario_cierre": "20:00:00",
        "capacidad_vestidores": 4})


def _vencer(db, dias: int) -> None:
    """Corre las fechas de la suscripción actual para que haya vencido hace `dias`."""
    hoy = tiempo.hoy()
    db.execute(
        update(Suscripcion)
        .where(Suscripcion.estado.in_(("VIGENTE", "SUSPENDIDA")))
        .values(inicio=hoy - timedelta(days=dias + 30), vencimiento=hoy - timedelta(days=dias))
    )
    db.commit()


# --------------------------------------------------------------------------
#  Acceso
# --------------------------------------------------------------------------
def test_solo_la_plataforma_gestiona_las_suscripciones(api, cabeceras_admin):
    assert api.get(EMPRESA, headers=cabeceras_admin).status_code == 403
    r = api.post(EMPRESA, headers=cabeceras_admin, json={"plan_id": BASICO})
    assert r.status_code == 403
    assert api.post(VENCIMIENTO, headers=cabeceras_admin).status_code == 403


# --------------------------------------------------------------------------
#  Flujo principal
# --------------------------------------------------------------------------
def test_la_ficha_muestra_la_actual_y_el_historial(api, plataforma):
    r = api.get(EMPRESA, headers=plataforma)

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["empresa"] == "Violet Boutique"
    assert cuerpo["actual"]["plan_codigo"] == "EMPRESARIAL"
    assert cuerpo["actual"]["estado"] == "VIGENTE"
    assert len(cuerpo["historial"]) == 1


def test_cambiar_el_plan_cierra_la_anterior_y_registra_el_pago(api, db, plataforma):
    r = api.post(EMPRESA, headers=plataforma, json={"plan_id": PROFESIONAL})

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    hoy = tiempo.hoy()
    # Paso 4: el vencimiento sale de la duración del plan.
    assert cuerpo["actual"]["plan_codigo"] == "PROFESIONAL"
    assert cuerpo["actual"]["inicio"] == hoy.isoformat()
    assert cuerpo["actual"]["vencimiento"] == (hoy + timedelta(days=30)).isoformat()
    # El pago simulado: el precio mensual por la duración, con comprobante.
    assert cuerpo["pago"]["concepto"] == "CAMBIO"
    assert cuerpo["pago"]["monto"] == 750.0
    assert cuerpo["pago"]["comprobante"].startswith("SIM-")
    assert cuerpo["excedidas"] == []
    # Paso 5: queda el historial y una sola vigente (RN-02).
    assert [s["estado"] for s in cuerpo["historial"]] == ["VIGENTE", "REEMPLAZADA"]
    actuales = db.scalar(select(func.count()).select_from(Suscripcion)
                         .where(Suscripcion.estado.in_(("VIGENTE", "SUSPENDIDA"))))
    assert actuales == 1


def test_el_cambio_rige_en_la_siguiente_verificacion(api, plataforma, cabeceras_admin):
    """Con el Básico (2 sucursales) la empresa ya no crea la tercera."""
    for nombre in ("Norte", "Sur"):
        assert _sucursal(api, cabeceras_admin, nombre).status_code == 201
    api.post(EMPRESA, headers=plataforma, json={"plan_id": BASICO})

    r = _sucursal(api, cabeceras_admin, "Este")

    assert r.status_code == 403
    assert r.json()["codigo"] == "plan_limit"


def test_la_fecha_de_inicio_se_puede_indicar_pero_no_en_el_pasado(api, plataforma):
    manana = tiempo.hoy() + timedelta(days=1)
    r = api.post(EMPRESA, headers=plataforma,
                 json={"plan_id": BASICO, "inicio": manana.isoformat()})
    assert r.status_code == 200, r.text
    assert r.json()["actual"]["inicio"] == manana.isoformat()

    ayer = tiempo.hoy() - timedelta(days=1)
    r = api.post(EMPRESA, headers=plataforma, json={"plan_id": BASICO, "inicio": ayer.isoformat()})
    assert r.status_code == 422


def test_no_se_asigna_un_plan_inexistente_ni_uno_que_ya_no_se_ofrece(api, db, plataforma):
    assert api.post(EMPRESA, headers=plataforma, json={"plan_id": 99}).status_code == 404
    db.execute(update(Plan).where(Plan.id == BASICO).values(activo=False))
    db.commit()
    assert api.post(EMPRESA, headers=plataforma, json={"plan_id": BASICO}).status_code == 422


def test_a_una_empresa_de_baja_no_se_le_cambia_el_plan(api, plataforma):
    api.post(f"/api/v1/plataforma/empresas/{EMPRESA_PRUEBAS}/baja", headers=plataforma)
    r = api.post(EMPRESA, headers=plataforma, json={"plan_id": BASICO})
    assert r.status_code == 409


def test_el_alta_de_una_empresa_deja_su_pago(api, db, plataforma):
    r = api.post("/api/v1/plataforma/empresas", headers=plataforma, json={
        "nombre": "Moda Andina", "slug": "moda-andina", "plan_codigo": "BASICO",
        "sucursal": {"ciudad_id": 1, "direccion": "Calle 1"},
        "administrador": {"correo": "admin@modaandina.bo", "nombres": "Ana", "apellidos": "Rojas"}})
    assert r.status_code == 201, r.text

    ficha = api.get(f"/api/v1/plataforma/empresas/{r.json()['id']}/suscripciones",
                    headers=plataforma).json()
    assert [(p["concepto"], p["monto"]) for p in ficha["pagos"]] == [("ALTA", 300.0)]


# --------------------------------------------------------------------------
#  5a Bajar de plan
# --------------------------------------------------------------------------
def test_bajar_de_plan_avisa_lo_que_pasa_el_limite_y_no_borra_nada(api, plataforma, cabeceras_admin):
    for nombre in ("Norte", "Sur", "Este"):
        assert _sucursal(api, cabeceras_admin, nombre).status_code == 201

    r = api.post(EMPRESA, headers=plataforma, json={"plan_id": BASICO})

    assert r.status_code == 200, r.text
    assert r.json()["excedidas"] == [
        {"empresa": "Violet Boutique", "recurso": "sucursales activas", "uso": 3, "limite": 2}
    ]
    activas = [s for s in api.get(SUCURSALES, headers=cabeceras_admin).json() if s["activa"]]
    assert len(activas) == 3


# --------------------------------------------------------------------------
#  3a Renovar
# --------------------------------------------------------------------------
def test_renovar_extiende_desde_el_vencimiento_actual(api, db, plataforma):
    antes = db.scalar(select(Suscripcion.vencimiento))

    r = api.post(f"{EMPRESA}/renovar", headers=plataforma)

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["actual"]["vencimiento"] == (antes + timedelta(days=30)).isoformat()
    assert cuerpo["pago"]["concepto"] == "RENOVACION"
    assert cuerpo["pago"]["monto"] == 1500.0
    assert len(cuerpo["historial"]) == 1


def test_renovar_una_vencida_la_vuelve_vigente_desde_hoy(api, db, plataforma):
    _vencer(db, dias=5)
    api.post(VENCIMIENTO, headers=plataforma)

    r = api.post(f"{EMPRESA}/renovar", headers=plataforma)

    assert r.status_code == 200, r.text
    assert r.json()["actual"]["estado"] == "VIGENTE"
    assert r.json()["actual"]["vencimiento"] == (tiempo.hoy() + timedelta(days=30)).isoformat()


# --------------------------------------------------------------------------
#  3b Suspender o reactivar
# --------------------------------------------------------------------------
def test_suspendida_la_empresa_solo_consulta_y_al_reactivar_vuelve(api, plataforma, cabeceras_admin):
    r = api.post(f"{EMPRESA}/suspender", headers=plataforma)
    assert r.status_code == 200, r.text
    assert r.json()["actual"]["estado"] == "SUSPENDIDA"

    # RN-03: consultar sí, crear no.
    assert api.get(SUCURSALES, headers=cabeceras_admin).status_code == 200
    r = _sucursal(api, cabeceras_admin, "Norte")
    assert r.status_code == 403
    assert r.json()["codigo"] == "sin_suscripcion"

    assert api.post(f"{EMPRESA}/suspender", headers=plataforma).status_code == 409
    r = api.post(f"{EMPRESA}/reactivar", headers=plataforma)
    assert r.json()["actual"]["estado"] == "VIGENTE"
    assert _sucursal(api, cabeceras_admin, "Norte").status_code == 201
    assert api.post(f"{EMPRESA}/reactivar", headers=plataforma).status_code == 409


def test_la_que_vencio_suspendida_no_se_reactiva_se_renueva(api, db, plataforma):
    api.post(f"{EMPRESA}/suspender", headers=plataforma)
    _vencer(db, dias=1)

    r = api.post(f"{EMPRESA}/reactivar", headers=plataforma)

    assert r.status_code == 409
    assert "renuévela" in r.json()["detail"]


# --------------------------------------------------------------------------
#  E1 El proceso diario
# --------------------------------------------------------------------------
def test_el_proceso_diario_marca_las_vencidas_una_sola_vez(api, db, plataforma):
    _vencer(db, dias=1)
    # Antes del proceso ya se ve vencida: no se espera a que corra.
    assert api.get(EMPRESA, headers=plataforma).json()["actual"]["estado"] == "VENCIDA"

    r = api.post(VENCIMIENTO, headers=plataforma)
    assert r.status_code == 200, r.text
    assert r.json() == {"vencidas": 1, "empresas": ["Violet Boutique"]}
    assert db.scalar(select(Suscripcion.estado)) == "VENCIDA"

    assert api.post(VENCIMIENTO, headers=plataforma).json()["vencidas"] == 0
    # La lista de empresas la sigue mostrando, vencida.
    fila = api.get(f"/api/v1/plataforma/empresas/{EMPRESA_PRUEBAS}", headers=plataforma).json()
    assert fila["suscripcion"]["estado"] == "VENCIDA"


def test_sin_suscripcion_no_hay_nada_que_renovar(api, db, plataforma):
    db.execute(PagoSimulado.__table__.delete())
    db.execute(Suscripcion.__table__.delete())
    db.commit()
    assert api.post(f"{EMPRESA}/renovar", headers=plataforma).status_code == 409
    assert api.post(f"{EMPRESA}/suspender", headers=plataforma).status_code == 409
    # Asignar un plan a una empresa sin suscripción es un alta.
    r = api.post(EMPRESA, headers=plataforma, json={"plan_id": BASICO})
    assert r.json()["pago"]["concepto"] == "ALTA"
