"""CU-11 Contratar un plan desde la web (2do parcial). El actor no tiene sesión.

Cubre la ficha: los planes que se ofrecen con sus funciones (paso 2), que el
slug esté libre y las sugerencias cuando no (5 y 5a), el pago simulado con su
comprobante (6), que lo creado sea lo mismo que en el alta del CU-01 (7), el
inicio de sesión con el slug y la contraseña elegida (8), y que un pago
rechazado no cree nada (6a).
"""

import pytest
from sqlalchemy import func, select, update

from app.core.tenencia import modo_plataforma
from app.modules.organizacion.models import Sucursal
from app.modules.plataforma.models import Empresa, PagoSimulado, Plan, Suscripcion
from app.modules.seguridad.models import Usuario

BASE = "/api/v1/contratar"
CLAVE = "Andina2026"


def _datos(**cambios) -> dict:
    datos = {
        "nombre": "Moda Andina",
        "razon_social": "Moda Andina S.R.L.",
        "nit": "1020304050",
        "slug": "moda-andina",
        "correo_contacto": "hola@modaandina.bo",
        "plan_codigo": "PROFESIONAL",
        "sucursal": {"ciudad_id": 1, "nombre": "Casa matriz", "direccion": "Av. Busch 120"},
        "administrador": {"correo": "ana@modaandina.bo", "nombres": "Ana",
                          "apellidos": "Rojas", "contrasena": CLAVE},
        "pago": {"metodo": "QR", "codigo_operacion": "482913"},
    }
    return datos | cambios


def _empresas(db) -> int:
    return db.scalar(select(func.count()).select_from(Empresa))


# --------------------------------------------------------------------------
#  Paso 2: los planes
# --------------------------------------------------------------------------
def test_los_planes_se_ven_sin_sesion_y_solo_los_que_se_ofrecen(api, db):
    db.execute(update(Plan).where(Plan.codigo == "BASICO").values(activo=False))
    db.commit()

    r = api.get(f"{BASE}/planes")

    assert r.status_code == 200, r.text
    planes = {p["codigo"]: p for p in r.json()}
    assert set(planes) == {"PROFESIONAL", "EMPRESARIAL"}
    funciones = {f["clave"]: f["incluida"] for f in planes["PROFESIONAL"]["funciones"]}
    assert funciones["correo"] is True
    assert "id" not in planes["PROFESIONAL"] and "empresas" not in planes["PROFESIONAL"]


def test_las_ciudades_se_ven_sin_sesion(api):
    r = api.get(f"{BASE}/ciudades")
    assert r.status_code == 200
    assert {c["nombre"] for c in r.json()} >= {"Santa Cruz", "La Paz"}


# --------------------------------------------------------------------------
#  Paso 5 y 5a: el slug
# --------------------------------------------------------------------------
def test_un_slug_libre_se_acepta(api):
    assert api.get(f"{BASE}/slug", params={"valor": "Moda-Andina"}).json() == {
        "slug": "moda-andina", "disponible": True, "sugerencias": []}


def test_un_slug_ocupado_sugiere_otros_libres(api):
    r = api.get(f"{BASE}/slug", params={"valor": "violet-boutique"}).json()

    assert r["disponible"] is False
    assert len(r["sugerencias"]) == 3
    assert "violet-boutique" not in r["sugerencias"]
    assert all(s.startswith("violet-boutique-") for s in r["sugerencias"])


def test_un_slug_con_formato_invalido_no_esta_disponible(api):
    r = api.get(f"{BASE}/slug", params={"valor": "Moda Andina!"}).json()
    assert r["disponible"] is False


# --------------------------------------------------------------------------
#  Flujo principal
# --------------------------------------------------------------------------
def test_contratar_crea_todo_y_se_entra_con_el_slug(api, db):
    r = api.post(BASE, json=_datos())

    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["slug"] == "moda-andina"
    assert cuerpo["plan"] == "Profesional"
    # Paso 6: el comprobante del pago simulado.
    assert cuerpo["pago"]["comprobante"].startswith("SIM-")
    assert cuerpo["pago"]["monto"] == 750.0
    assert "contrasena" not in r.text

    # Paso 7: lo mismo que el alta del CU-01. La sesión de la prueba es de la
    # empresa 1; para ver las filas de la nueva, mira como la plataforma.
    modo_plataforma(db)
    empresa = db.scalar(select(Empresa).where(Empresa.slug == "moda-andina"))
    assert db.scalar(select(Suscripcion.estado).where(Suscripcion.empresa_id == empresa.id)) == "VIGENTE"
    assert db.scalar(select(func.count()).select_from(Sucursal)
                     .where(Sucursal.empresa_id == empresa.id)) == 1
    pago = db.scalar(select(PagoSimulado).where(PagoSimulado.empresa_id == empresa.id))
    assert (pago.concepto, pago.comprobante) == ("ALTA", cuerpo["pago"]["comprobante"])

    # Paso 8: entra con la contraseña que eligió.
    r = api.post("/api/v1/auth/login", json={
        "empresa": "moda-andina", "correo": "ana@modaandina.bo", "contrasena": CLAVE})
    assert r.status_code == 200, r.text


def test_el_correo_es_de_bienvenida_sin_contrasena(api, monkeypatch):
    enviados = []
    monkeypatch.setattr("app.modules.plataforma.service.enviar", enviados.append)

    api.post(BASE, json=_datos())

    assert len(enviados) == 1
    assert "Bienvenido" in enviados[0].asunto
    assert CLAVE not in enviados[0].cuerpo_texto
    assert "moda-andina" in enviados[0].cuerpo_texto


# --------------------------------------------------------------------------
#  Alternativos
# --------------------------------------------------------------------------
def test_5a_slug_ocupado_no_cobra_y_sugiere(api, db):
    antes = _empresas(db)

    r = api.post(BASE, json=_datos(slug="violet-boutique"))

    assert r.status_code == 409
    assert r.json()["codigo"] == "slug_ocupado"
    assert len(r.json()["sugerencias"]) == 3
    assert _empresas(db) == antes
    modo_plataforma(db)
    assert db.scalar(select(func.count()).select_from(PagoSimulado)) == 0


def test_6a_pago_rechazado_no_crea_nada(api, db):
    antes = _empresas(db)

    r = api.post(BASE, json=_datos(pago={"metodo": "QR", "codigo_operacion": "000000"}))

    assert r.status_code == 402
    assert r.json()["codigo"] == "pago_rechazado"
    assert _empresas(db) == antes
    assert db.scalar(select(func.count()).select_from(Usuario)
                     .where(Usuario.correo == "ana@modaandina.bo")) == 0


def test_un_plan_que_no_se_ofrece_no_se_contrata(api, db):
    db.execute(update(Plan).where(Plan.codigo == "BASICO").values(activo=False))
    db.commit()
    r = api.post(BASE, json=_datos(plan_codigo="BASICO"))
    assert r.status_code == 422
    assert r.json()["codigo"] == "plan_no_ofrecido"


@pytest.mark.parametrize("contrasena", ["corta1", "sinnumeros", "12345678"])
def test_la_contrasena_del_administrador_cumple_la_regla(api, contrasena):
    datos = _datos()
    datos["administrador"] = datos["administrador"] | {"contrasena": contrasena}
    assert api.post(BASE, json=datos).status_code == 422


def test_el_codigo_de_operacion_tiene_seis_digitos(api):
    r = api.post(BASE, json=_datos(pago={"metodo": "QR", "codigo_operacion": "12ab"}))
    assert r.status_code == 422
