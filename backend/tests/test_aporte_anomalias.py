"""
Aporte propio · Anomalías en caja y devoluciones con Isolation Forest.

Lo que más importa cubrir
- Un turno con un descuadre enorme entre turnos normales queda marcado, y la
  explicación nombra el arqueo (sale de los datos, no de un modelo de lenguaje).
- Con pocos turnos no entrena: avisa cuántos faltan, sin romperse.
- Lo revisado se marca y sobrevive a un reentrenamiento.
- Solo el administrador, solo con `analitica_ml`, y una empresa no ve el
  análisis de otra (RLS).
"""
from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

import numpy as np
from sqlalchemy import func, select

from app.core import tiempo
from app.core.tenencia import CLAVE_EMPRESA
from app.modules.analitica import anomalias
from app.modules.analitica.models import ModeloAnalitica
from app.modules.seguridad.models import Usuario
from app.modules.ventas.models import Caja, TurnoCaja
from tests.test_multitenant import _ciudad, _sucursal, empresa_b  # noqa: F401 - fixture

API = "/api/v1/analitica/anomalias"


def _turnos(db, cantidad: int, *, descuadre_raro: bool = True) -> int:
    """`cantidad` turnos cerrados normales y, si se pide, uno con Bs 500 de faltante.

    Devuelve el id del turno raro (o 0).
    """
    sucursal = _sucursal("Centro", _ciudad(db))
    db.add(sucursal)
    db.flush()
    caja = Caja(sucursal_id=sucursal.id, nombre="Caja 1")
    db.add(caja)
    db.flush()
    cajero = db.scalar(select(Usuario.id).limit(1))
    azar = random.Random(7)
    inicio = tiempo.ahora() - timedelta(days=cantidad + 2)
    for i in range(cantidad):
        abierto = inicio + timedelta(days=i)
        esperado = Decimal("1000.00") + Decimal(azar.randint(0, 300))
        db.add(TurnoCaja(
            caja_id=caja.id, usuario_id=cajero, abierto_en=abierto,
            cerrado_en=abierto + timedelta(hours=8, minutes=azar.randint(-20, 20)),
            monto_apertura=Decimal("500.00"), monto_esperado=esperado,
            monto_cierre=esperado + Decimal(azar.randint(-5, 5)),
        ))
    raro = 0
    if descuadre_raro:
        abierto = tiempo.ahora() - timedelta(days=1)
        turno = TurnoCaja(
            caja_id=caja.id, usuario_id=cajero, abierto_en=abierto,
            cerrado_en=abierto + timedelta(hours=8), monto_apertura=Decimal("500.00"),
            monto_esperado=Decimal("1200.00"), monto_cierre=Decimal("700.00"),
        )
        db.add(turno)
        db.flush()
        raro = turno.id
    db.commit()
    return raro


# =====================================================================
#  El modelo, sin base
# =====================================================================

def test_el_bosque_aisla_la_fila_rara_y_explica_por_que() -> None:
    azar = np.random.default_rng(3)
    normales = np.column_stack([
        azar.uniform(0, 5, 40),        # diferencia de arqueo
        azar.integers(0, 2, 40),       # devoluciones
        azar.uniform(0, 100, 40),      # monto devuelto
        azar.uniform(0, 0.05, 40),     # descuento
        azar.uniform(0.4, 0.6, 40),    # efectivo
        azar.integers(20, 30, 40),     # ventas
        azar.uniform(7.5, 8.5, 40),    # duración
    ])
    rara = np.array([[3, 9, 2500, 0.02, 0.5, 25, 8]])  # 9 devoluciones por Bs 2.500
    d = anomalias.detectar(np.vstack([normales, rara]), anomalias.VARIABLES_TURNO, 2026)
    assert d.marcadas[-1] is True
    assert d.puntajes[-1] == max(d.puntajes)
    assert 0 < d.puntajes[-1] <= 1
    assert "devuel" in d.explicaciones[-1].lower()
    assert sum(d.marcadas) <= round(len(d.marcadas) * anomalias.CONTAMINACION) + 1


def test_la_explicacion_compara_con_lo_habitual() -> None:
    matriz = np.array([[10.0, 1.0]] * 20 + [[80.0, 1.0]])
    variables = anomalias.VARIABLES_TURNO[:2]
    texto = anomalias.explicar(matriz[-1], matriz, variables)
    assert texto.startswith("Diferencia de arqueo 8× la habitual")
    assert "Bs 80,00 contra Bs 10,00" in texto


# =====================================================================
#  Por la API
# =====================================================================

def test_antes_de_buscar_no_hay_nada(api, cabeceras_admin) -> None:
    r = api.get(API, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert r.json() == {"entrenado": False, "entrenamiento": None, "turnos": None,
                        "devoluciones": None}


def test_con_pocos_turnos_avisa_cuantos_faltan(api, db, cabeceras_admin) -> None:
    _turnos(db, 5, descuadre_raro=False)
    r = api.post(API, headers=cabeceras_admin)
    assert r.status_code == 409
    assert f"al menos {anomalias.MIN_TURNOS} turnos" in r.json()["detail"]
    assert "hay 5" in r.json()["detail"]
    assert db.scalar(select(func.count(ModeloAnalitica.id))) == 0


def test_el_descuadre_enorme_queda_marcado_con_su_motivo(api, db, cabeceras_admin) -> None:
    raro = _turnos(db, 30)
    r = api.post(API, headers=cabeceras_admin, json={"semilla": 4})
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["entrenado"] is True
    turnos = cuerpo["turnos"]
    assert turnos["muestras"] == 31
    primero = turnos["marcadas"][0]
    assert primero["id"] == raro
    assert "arqueo" in primero["explicacion"].lower()
    assert "Bs -500.00" in primero["detalle"]
    assert primero["cajero"] == "Root Pruebas" and primero["sucursal"] == "Centro"
    # Sin devoluciones no se analizan, pero se dice por qué.
    devs = cuerpo["devoluciones"]
    assert devs["suficientes"] is False and "al menos" in devs["mensaje"]
    m = cuerpo["entrenamiento"]["metricas"]
    assert m["contaminacion"] == anomalias.CONTAMINACION
    assert m["muestras_turnos"] == 31 and m["marcados_turnos"] >= 1
    assert cuerpo["entrenamiento"]["parametros"]["algoritmo"] == "IsolationForest"
    assert cuerpo["entrenamiento"]["filas_sinteticas"] == 0
    assert api.get(API, headers=cabeceras_admin).json() == cuerpo


def test_revisar_una_anomalia_y_que_no_se_pierda(api, db, cabeceras_admin) -> None:
    raro = _turnos(db, 30)
    api.post(API, headers=cabeceras_admin)
    r = api.post(f"{API}/turnos/{raro}/revisada", headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    marcada = next(i for i in r.json()["turnos"]["marcadas"] if i["id"] == raro)
    assert marcada["revision"]["por"] == "Root Pruebas"

    # Se reentrena y la revisión sigue.
    cuerpo = api.post(API, headers=cabeceras_admin).json()
    marcada = next(i for i in cuerpo["turnos"]["marcadas"] if i["id"] == raro)
    assert marcada["revision"] is not None

    assert api.post(f"{API}/turnos/999999/revisada", headers=cabeceras_admin).status_code == 404
    assert api.post(f"{API}/otra/{raro}/revisada", headers=cabeceras_admin).status_code == 422


def test_el_historial_las_incluye_sin_tocar_los_otros_modelos(api, db, cabeceras_admin) -> None:
    _turnos(db, 25)
    api.post(API, headers=cabeceras_admin)
    historial = api.get("/api/v1/analitica/entrenamientos", headers=cabeceras_admin).json()
    assert [h["tipo"] for h in historial] == ["ANOMALIAS"]
    # El dashboard de CU-30 sigue sin entrenar: son modelos independientes.
    assert api.get("/api/v1/analitica/resumen", headers=cabeceras_admin).json()["entrenado"] is False


# =====================================================================
#  Quién puede, y el plan
# =====================================================================

def test_sin_la_funcion_del_plan_se_rechaza(api, db, cabeceras_admin) -> None:
    from app.modules.plataforma.models import Plan

    plan = db.get(Plan, 3)
    antes = dict(plan.funciones)
    plan.funciones = {**antes, "analitica_ml": False}
    db.commit()
    try:
        r = api.post(API, headers=cabeceras_admin)
        assert r.status_code == 403
        assert r.json()["codigo"] == "plan_limit"
        assert api.get(API, headers=cabeceras_admin).status_code == 403
    finally:
        plan = db.get(Plan, 3)
        plan.funciones = antes
        db.commit()


def test_el_cliente_no_entra(api, cabeceras_cliente) -> None:
    assert api.post(API, headers=cabeceras_cliente).status_code == 403
    assert api.get(API, headers=cabeceras_cliente).status_code == 403


def test_una_empresa_no_ve_las_anomalias_de_otra(
    api, db, cabeceras_admin, fabrica_sesiones, empresa_b
) -> None:
    _turnos(db, 25)
    assert api.post(API, headers=cabeceras_admin).status_code == 201
    otra = fabrica_sesiones()
    otra.info[CLAVE_EMPRESA] = empresa_b
    try:
        assert otra.scalar(select(func.count(ModeloAnalitica.id))) == 0
        assert otra.scalar(select(func.count(TurnoCaja.id))) == 0
    finally:
        otra.close()
