"""Lo que el plan promete, se cumple (CU-05, 2do parcial).

La primera parte es la guardiana, con la idea de PLAN_RULES de
PROYECTO_MEDICOS: si alguien agrega a un plan un límite, un cupo, una función o
un ajuste sin registrar dónde se hace cumplir, falla. La segunda prueba cada
regla que antes los planes declaraban y nadie consultaba: los avisos por
correo, la IA del cliente, la foto con IA y los días de bitácora.
"""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select, update

from app.core import tiempo
from app.integrations import asistente, interprete, probador_ia, recomendador
from app.modules.bitacora.models import AsientoBitacora
from app.modules.notificaciones import service as notificaciones
from app.modules.plataforma import verificador
from app.modules.plataforma.models import Plan, Suscripcion
from app.modules.seguridad.models import Usuario

from .conftest import CORREO_ADMIN, _M0022

ESTADOS = {"aplicado", "pendiente", "no_aplica"}
#: Columnas del plan que no prometen nada: lo identifican o lo encienden.
COLUMNAS_SIN_REGLA = {"id", "codigo", "nombre", "funciones", "activo",
                      "creado_en", "creado_por", "actualizado_en", "actualizado_por"}


def _pasar_a(db, codigo: str, **cambios) -> None:
    plan = db.scalar(select(Plan).where(Plan.codigo == codigo))
    for campo, valor in cambios.items():
        setattr(plan, campo, valor)
    db.execute(update(Suscripcion).values(plan_id=plan.id))
    db.commit()


# --------------------------------------------------------------------------
#  La guardiana
# --------------------------------------------------------------------------
def _declarado() -> set[str]:
    columnas = {c.name for c in Plan.__table__.columns} - COLUMNAS_SIN_REGLA
    funciones = set()
    for nombre in ("FUNCIONES_BASICO", "FUNCIONES_PROFESIONAL", "FUNCIONES_EMPRESARIAL"):
        funciones |= json.loads(getattr(_M0022, nombre)).keys()
    return columnas | funciones | verificador.FUNCIONES.keys()


def test_todo_lo_que_declara_un_plan_tiene_donde_se_hace_cumplir():
    faltan = _declarado() - verificador.REGLAS_DEL_PLAN.keys()
    assert not faltan, (
        f"El plan declara {sorted(faltan)} y nadie lo hace cumplir. Regístrelo en "
        f"plataforma/verificador.py::REGLAS_DEL_PLAN con dónde se aplica."
    )


def test_el_registro_no_tiene_reglas_huerfanas():
    sobran = verificador.REGLAS_DEL_PLAN.keys() - _declarado()
    assert not sobran, f"REGLAS_DEL_PLAN menciona {sorted(sobran)}, que ningún plan declara."


def test_cada_regla_aplicada_apunta_a_codigo_que_existe():
    modulos = Path(__file__).resolve().parents[1] / "app" / "modules"
    for clave, (estado, donde) in verificador.REGLAS_DEL_PLAN.items():
        assert estado in ESTADOS, clave
        assert donde.strip(), clave
        if estado == "aplicado":
            ruta = donde.split(" · ")[0].strip()
            assert (modulos / ruta).exists(), f"{clave}: no existe app/modules/{ruta}"


def test_el_conftest_siembra_las_mismas_funciones_que_la_migracion(db):
    for codigo, nombre in (("BASICO", "FUNCIONES_BASICO"), ("EMPRESARIAL", "FUNCIONES_EMPRESARIAL")):
        plan = db.scalar(select(Plan).where(Plan.codigo == codigo))
        assert plan.funciones == json.loads(getattr(_M0022, nombre))


# --------------------------------------------------------------------------
#  correo: el aviso queda en la campanita, pero no sale por correo
# --------------------------------------------------------------------------
@pytest.mark.parametrize(("codigo", "estado"), [("BASICO", "OMITIDO"), ("PROFESIONAL", "PENDIENTE")])
def test_el_aviso_sale_por_correo_solo_si_el_plan_lo_incluye(db, cabeceras_admin, codigo, estado):
    _pasar_a(db, codigo)
    admin = db.scalar(select(Usuario).where(Usuario.correo == CORREO_ADMIN))

    aviso = notificaciones.notificar(db, destinatario=admin, tipo="STOCK_BAJO",
                                     titulo="Hola", cuerpo="Un aviso de prueba")
    db.commit()

    assert aviso.correo_estado == estado
    if estado == "OMITIDO":
        assert "plan" in aviso.correo_error


# --------------------------------------------------------------------------
#  ia_cliente: el asistente se rechaza; las recomendaciones van sin IA
# --------------------------------------------------------------------------
def test_sin_ia_para_el_cliente_el_asistente_no_esta(api, db, cabeceras_cliente, monkeypatch):
    monkeypatch.setattr(asistente, "esta_disponible", lambda: True)
    _pasar_a(db, "BASICO")

    assert api.get("/api/v1/asistente/disponible", headers=cabeceras_cliente).json()["disponible"] is False
    r = api.post("/api/v1/asistente", headers=cabeceras_cliente, json={"pregunta": "¿Qué me queda?"})
    assert r.status_code == 403
    assert r.json()["codigo"] == "plan_limit"


def test_sin_ia_para_el_cliente_las_recomendaciones_no_llaman_al_modelo(
    api, db, cabeceras_cliente, monkeypatch
):
    def _no_deberia(*_):
        raise AssertionError("Se llamó al modelo con un plan sin IA para el cliente.")

    monkeypatch.setattr(recomendador, "ordenar", _no_deberia)
    _pasar_a(db, "BASICO")

    r = api.get("/api/v1/tienda/recomendaciones", headers=cabeceras_cliente)

    assert r.status_code == 200, r.text
    assert r.json()["motor"] == "popularidad"


# --------------------------------------------------------------------------
#  reportes_ia: el micrófono no se ofrece
# --------------------------------------------------------------------------
def test_sin_reportes_con_ia_el_pedido_por_voz_no_se_ofrece(api, db, cabeceras_admin, monkeypatch):
    monkeypatch.setattr(interprete, "esta_disponible", lambda: True)
    disponible = "/api/v1/reportes/voz/disponible"

    assert api.get(disponible, headers=cabeceras_admin).json()["disponible"] is True
    _pasar_a(db, "BASICO")
    assert api.get(disponible, headers=cabeceras_admin).json()["disponible"] is False


# --------------------------------------------------------------------------
#  foto_ia y cupo_fotos_ia: el probado por IA del vestidor
# --------------------------------------------------------------------------
def test_sin_foto_con_ia_el_probador_no_se_ofrece_ni_se_usa(api, db, cabeceras_cliente, monkeypatch):
    monkeypatch.setattr(probador_ia, "esta_disponible", lambda: True)
    _pasar_a(db, "BASICO")

    estado = api.get("/api/v1/vestidor/probador", headers=cabeceras_cliente).json()
    assert estado["disponible"] is False
    assert "plan" in estado["motivo"]

    r = api.post("/api/v1/vestidor/probar", headers=cabeceras_cliente,
                 data={"variante_id": "1"}, files={"captura": ("c.png", b"x", "image/png")})
    assert r.status_code == 403
    assert r.json()["codigo"] == "plan_limit"


def test_con_el_cupo_de_fotos_agotado_el_probador_no_se_ofrece(api, db, cabeceras_cliente, monkeypatch):
    monkeypatch.setattr(probador_ia, "esta_disponible", lambda: True)
    _pasar_a(db, "PROFESIONAL", cupo_fotos_ia=1)
    assert api.get("/api/v1/vestidor/probador", headers=cabeceras_cliente).json()["disponible"]

    verificador.consumir_cupo(db, "fotos_ia")
    db.commit()

    estado = api.get("/api/v1/vestidor/probador", headers=cabeceras_cliente).json()
    assert estado["disponible"] is False
    assert "este mes" in estado["motivo"]
    r = api.post("/api/v1/vestidor/probar", headers=cabeceras_cliente,
                 data={"variante_id": "1"}, files={"captura": ("c.png", b"x", "image/png")})
    assert r.status_code == 403


# --------------------------------------------------------------------------
#  bitacora_dias: la consulta no va más atrás
# --------------------------------------------------------------------------
def _asiento(dias_atras: int, ruta: str) -> AsientoBitacora:
    return AsientoBitacora(ocurrido_en=tiempo.ahora() - timedelta(days=dias_atras),
                           accion="PRUEBA", metodo="POST", ruta=ruta, estado_http=200, exito=True)


def test_la_bitacora_muestra_solo_los_dias_del_plan(api, db, cabeceras_admin):
    db.add_all([_asiento(2, "/reciente"), _asiento(45, "/vieja")])
    db.commit()

    def rutas(**params):
        r = api.get("/api/v1/bitacora", headers=cabeceras_admin,
                    params={"accion": "PRUEBA", **params})
        assert r.status_code == 200, r.text
        return {a["ruta"] for a in r.json()["items"]}

    # Empresarial: todo el historial.
    assert rutas() == {"/reciente", "/vieja"}
    # Básico: 30 días, aunque se pida desde antes.
    _pasar_a(db, "BASICO")
    desde = (tiempo.hoy() - timedelta(days=60)).isoformat()
    assert rutas(desde=desde) == {"/reciente"}
