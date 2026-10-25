"""CU-02 Gestionar planes (2do parcial). Lo opera el administrador de la plataforma.

Cubre la ficha del 2.6: listar con cuántas empresas usan cada plan (paso 2),
crear y editar (pasos 3 a 5), el nombre único y los límites inválidos (4a),
desactivar sin quitarle el plan a nadie (3a), que bajar un límite no borre nada
y avise a quién afecta (5a, RN-04), y que el cambio rija en la siguiente
verificación sin tocar el código (postcondición).
"""

import pytest
from sqlalchemy import null, select

from app.core.security import hash_password
from app.modules.plataforma.models import Plan
from app.modules.seguridad.models import Rol, Usuario

PLANES = "/api/v1/plataforma/planes"
SUCURSALES = "/api/v1/organizacion/sucursales"
CORREO_PLATAFORMA = "plataforma@violetboutique.bo"
CLAVE = "Plataforma123"


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


def _plan(**cambios) -> dict:
    datos = {
        "nombre": "Pyme Plus",
        "precio_mensual": 450,
        "duracion_dias": 30,
        "max_sucursales": 3,
        "max_empleados": 20,
        "cupo_reportes_ia": 50,
        "cupo_fotos_ia": None,
        "bitacora_dias": 90,
        "funciones": ["reportes_ia", "correo"],
    }
    return datos | cambios


def _sucursal(api, admin, nombre: str):
    return api.post(SUCURSALES, headers=admin, json={
        "ciudad_id": 1, "nombre": nombre, "direccion": f"Avenida {nombre} 100",
        "horario_apertura": "09:00:00", "horario_cierre": "20:00:00",
        "capacidad_vestidores": 4})


# --------------------------------------------------------------------------
#  Acceso
# --------------------------------------------------------------------------
def test_solo_la_plataforma_gestiona_los_planes(api, cabeceras_admin):
    assert api.get(PLANES, headers=cabeceras_admin).status_code == 403
    assert api.post(PLANES, headers=cabeceras_admin, json=_plan()).status_code == 403


# --------------------------------------------------------------------------
#  Flujo principal
# --------------------------------------------------------------------------
def test_la_lista_muestra_cada_plan_con_sus_empresas(api, plataforma):
    planes = {p["codigo"]: p for p in api.get(PLANES, headers=plataforma).json()}

    assert list(planes) == ["BASICO", "PROFESIONAL", "EMPRESARIAL"]  # por precio
    # La empresa de las pruebas está en el Empresarial (conftest).
    assert planes["EMPRESARIAL"]["empresas"] == 1
    assert planes["BASICO"]["empresas"] == 0
    assert planes["BASICO"]["max_sucursales"] == 2
    assert planes["EMPRESARIAL"]["max_sucursales"] is None  # vacío es ilimitado
    assert "reportes_ia" in planes["PROFESIONAL"]["funciones"]
    assert "reportes_ia" not in planes["BASICO"]["funciones"]
    # Un ajuste como bitacora_dias no es una función.
    assert "bitacora_dias" not in planes["BASICO"]["funciones"]
    assert planes["BASICO"]["bitacora_dias"] == 30


def test_crear_un_plan(api, plataforma):
    r = api.post(PLANES, headers=plataforma, json=_plan())

    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["codigo"] == "PYME_PLUS"  # sale del nombre
    assert plan["precio_mensual"] == 450
    assert plan["funciones"] == ["reportes_ia", "correo"]
    assert plan["activo"] is True
    assert plan["empresas"] == 0
    assert plan["excedidas"] == []
    assert "PYME_PLUS" in [p["codigo"] for p in api.get(PLANES, headers=plataforma).json()]


def test_editar_conserva_el_codigo_y_los_ajustes_que_no_son_funciones(api, db, plataforma):
    basico = db.scalar(select(Plan).where(Plan.codigo == "BASICO"))
    basico.funciones = basico.funciones | {"respaldo_retencion": 3}
    db.commit()

    r = api.put(f"{PLANES}/{basico.id}", headers=plataforma,
                json=_plan(nombre="Básico", precio_mensual=320, max_sucursales=2,
                           cupo_reportes_ia=0, funciones=["correo"]))

    assert r.status_code == 200, r.text
    assert r.json()["codigo"] == "BASICO"
    db.expire_all()
    guardado = db.get(Plan, basico.id)
    assert guardado.funciones["correo"] is True
    assert guardado.funciones["reportes_ia"] is False
    assert guardado.funciones["respaldo_retencion"] == 3
    assert guardado.funciones["bitacora_dias"] == 90


def test_las_funciones_tienen_el_nombre_de_mi_plan(api, plataforma):
    funciones = {f["clave"]: f["nombre"] for f in
                 api.get(f"{PLANES}/funciones", headers=plataforma).json()}
    assert funciones["reportes_ia"] == "Reportes generativos con IA"
    assert "bitacora_dias" not in funciones


# --------------------------------------------------------------------------
#  4a: datos inválidos
# --------------------------------------------------------------------------
def test_el_nombre_es_unico_sin_importar_mayusculas(api, plataforma):
    r = api.post(PLANES, headers=plataforma, json=_plan(nombre="profesional"))
    assert r.status_code == 409


@pytest.mark.parametrize(
    "cambio",
    [{"max_sucursales": 0}, {"max_empleados": -1}, {"precio_mensual": -5},
     {"duracion_dias": 0}, {"funciones": ["volar"]}, {"nombre": "  "}],
    ids=["sucursales-0", "empleados-negativo", "precio-negativo", "duracion-0",
         "funcion-desconocida", "nombre-vacio"],
)
def test_los_limites_invalidos_se_rechazan(api, plataforma, cambio):
    assert api.post(PLANES, headers=plataforma, json=_plan(**cambio)).status_code == 422


# --------------------------------------------------------------------------
#  3a: desactivar
# --------------------------------------------------------------------------
def test_desactivar_deja_de_ofrecerlo_pero_quien_lo_tiene_lo_conserva(api, db, plataforma,
                                                                       cabeceras_admin):
    empresarial = db.scalar(select(Plan.id).where(Plan.codigo == "EMPRESARIAL"))

    r = api.post(f"{PLANES}/{empresarial}/desactivar", headers=plataforma)

    assert r.status_code == 200, r.text
    assert r.json()["activo"] is False
    # El selector del alta (sin incluir_inactivos) ya no lo ofrece...
    ofrecidos = [p["codigo"] for p in api.get(PLANES, headers=plataforma).json()]
    assert "EMPRESARIAL" not in ofrecidos
    todos = api.get(PLANES, headers=plataforma, params={"incluir_inactivos": True}).json()
    assert "EMPRESARIAL" in [p["codigo"] for p in todos]
    # ...pero la empresa que lo tiene sigue operando con él.
    assert _sucursal(api, cabeceras_admin, "Centro").status_code == 201

    assert api.post(f"{PLANES}/{empresarial}/activar", headers=plataforma).json()["activo"]


def test_un_plan_inexistente_da_404(api, plataforma):
    assert api.put(f"{PLANES}/999", headers=plataforma, json=_plan()).status_code == 404


# --------------------------------------------------------------------------
#  5a y postcondición: bajar un límite
# --------------------------------------------------------------------------
def test_bajar_un_limite_avisa_a_quien_afecta_y_no_borra_nada(api, db, plataforma,
                                                              cabeceras_admin):
    for nombre in ("A", "B", "C"):
        assert _sucursal(api, cabeceras_admin, nombre).status_code == 201
    empresarial = db.scalar(select(Plan.id).where(Plan.codigo == "EMPRESARIAL"))

    r = api.put(f"{PLANES}/{empresarial}", headers=plataforma,
                json=_plan(nombre="Empresarial", max_sucursales=2, max_empleados=None))

    assert r.status_code == 200, r.text
    assert r.json()["excedidas"] == [
        {"empresa": "Violet Boutique", "recurso": "sucursales activas", "uso": 3, "limite": 2}
    ]
    # No se borró nada...
    assert len(api.get(SUCURSALES, headers=cabeceras_admin).json()) == 3
    # ...y el nuevo límite rige desde la siguiente operación, sin tocar el código.
    cuarta = _sucursal(api, cabeceras_admin, "D")
    assert cuarta.status_code == 403
    assert cuarta.json()["codigo"] == "plan_limit"
