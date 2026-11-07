"""
3ra presentación · CU-29 Entrenar los modelos de analítica y CU-30 Consultar
el dashboard analítico.

Lo que más importa cubrir
- Los datos sintéticos son reproducibles: la misma semilla, los mismos datos.
- El supervisado (demanda) valida con corte temporal y le gana a la línea
  base ingenua; el no supervisado (K-means) elige k por silueta y nombra los
  grupos.
- Los datos REALES de la empresa entran al entrenamiento.
- Solo el administrador, solo con la función `analitica_ml` del plan, y una
  empresa no ve los modelos de otra (RLS).
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest
from sqlalchemy import func, select, update

from app.core import tiempo
from app.core.tenencia import CLAVE_EMPRESA
from app.modules.analitica import modelos, sinteticos
from app.modules.analitica.models import CONSERVAR, ModeloAnalitica
from tests.test_cu28_webhook import pedido, tienda  # noqa: F401 - fixtures
from tests.test_multitenant import empresa_b  # noqa: F401 - fixture

API = "/api/v1/analitica"
ENTRENAR = f"{API}/entrenamientos"
RESUMEN = f"{API}/resumen"


def _lunes(n: int = sinteticos.SEMANAS) -> list[date]:
    return [date(2024, 11, 4) + timedelta(weeks=i) for i in range(n)]


def _semanas_iso(lunes: list[date]) -> np.ndarray:
    return np.array([d.isocalendar()[1] for d in lunes])


# =====================================================================
#  Los modelos, sin base
# =====================================================================

def test_los_datos_sinteticos_son_reproducibles() -> None:
    productos = sinteticos.productos_de_relleno(8)
    semanas = _semanas_iso(_lunes())
    a = sinteticos.demanda_semanal(productos, semanas, 7)
    b = sinteticos.demanda_semanal(productos, semanas, 7)
    c = sinteticos.demanda_semanal(productos, semanas, 8)
    assert a.shape == (8, sinteticos.SEMANAS)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)
    assert (a >= 0).all()
    assert np.array_equal(sinteticos.clientes_rfm(semilla=3), sinteticos.clientes_rfm(semilla=3))


def test_la_demanda_valida_con_corte_temporal_y_le_gana_a_la_linea_base() -> None:
    productos = sinteticos.productos_de_relleno(30)
    lunes = _lunes()
    sint = sinteticos.demanda_semanal(productos, _semanas_iso(lunes), 2026)
    e = modelos.entrenar_demanda(productos, sint, np.zeros_like(sint), lunes, 2026)

    m = e.metricas
    assert m["semanas_de_prueba"] == modelos.SEMANAS_DE_PRUEBA
    assert m["filas_prueba"] == 30 * modelos.SEMANAS_DE_PRUEBA
    assert 0 < m["mae"] <= m["rmse"]
    assert 0 < m["r2"] <= 1
    assert m["mae"] < m["mae_linea_base"]  # si no le gana, no sirve
    assert len(e.resultado["predicciones"]) == 30
    assert all(f["prevista"] >= 0 for f in e.resultado["predicciones"])
    assert e.resultado["semana_prevista"] == (lunes[-1] + timedelta(days=7)).isoformat()
    assert len(e.resultado["serie_validacion"]) == modelos.SEMANAS_DE_PRUEBA
    assert e.filas_reales == 0 and e.filas_sinteticas == e.filas


def test_los_segmentos_eligen_k_por_silueta_y_tienen_nombre() -> None:
    e = modelos.entrenar_segmentos(sinteticos.clientes_rfm(), np.empty((0, 3)), 2026)
    k = e.metricas["k"]
    assert k in modelos.K_CANDIDATOS
    mejor = max(e.metricas["siluetas"], key=lambda s: s["silueta"])
    assert mejor["k"] == k and e.metricas["silueta"] > 0.3
    nombres = {s["nombre"] for s in e.resultado["segmentos"]}
    assert {"Dormidos (en riesgo)", "Fieles de alto gasto"} <= nombres
    assert sum(s["clientes"] for s in e.resultado["segmentos"]) == e.filas

    # El modelo guardado clasifica sin reentrenar.
    fiel, dormido = modelos.clasificar(e.modelo, np.array([[5, 14, 5000], [380, 1, 150]]))
    assert fiel == "Fieles de alto gasto"
    assert dormido == "Dormidos (en riesgo)"


# =====================================================================
#  CU-29 y CU-30 por la API
# =====================================================================

def test_antes_de_entrenar_el_dashboard_esta_vacio(api, cabeceras_admin) -> None:
    r = api.get(RESUMEN, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert r.json() == {"entrenado": False, "demanda": None, "segmentos": None,
                        "predicciones": None, "grupos": []}
    assert api.get(f"{API}/clientes", headers=cabeceras_admin).status_code == 409
    assert api.get(f"{API}/reporte.pdf", headers=cabeceras_admin).status_code == 409


def test_el_admin_entrena_y_ve_el_dashboard(api, db, cabeceras_admin) -> None:
    r = api.post(ENTRENAR, headers=cabeceras_admin, json={"semilla": 11})
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["entrenado"] is True
    # Sin productos cargados, entrena con el catálogo sintético de relleno.
    assert cuerpo["demanda"]["parametros"]["productos"] == 20
    assert cuerpo["demanda"]["metricas"]["r2"] > 0
    assert cuerpo["segmentos"]["metricas"]["k"] >= 2
    assert cuerpo["predicciones"]["predicciones"]
    assert cuerpo["grupos"]
    assert db.scalar(select(func.count(ModeloAnalitica.id))) == 2

    assert api.get(RESUMEN, headers=cabeceras_admin).json() == cuerpo
    historial = api.get(ENTRENAR, headers=cabeceras_admin).json()
    assert {h["tipo"] for h in historial} == {"DEMANDA", "SEGMENTOS"}
    assert all(h["entrenado_por"] == "Root Pruebas" for h in historial)

    pdf = api.get(f"{API}/reporte.pdf", headers=cabeceras_admin)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    xlsx = api.get(f"{API}/reporte.xlsx", headers=cabeceras_admin)
    assert xlsx.status_code == 200 and xlsx.content[:2] == b"PK"


def test_la_misma_semilla_da_las_mismas_metricas(api, cabeceras_admin) -> None:
    a = api.post(ENTRENAR, headers=cabeceras_admin, json={"semilla": 5}).json()
    b = api.post(ENTRENAR, headers=cabeceras_admin, json={"semilla": 5}).json()
    assert a["demanda"]["metricas"] == b["demanda"]["metricas"]
    assert a["segmentos"]["metricas"] == b["segmentos"]["metricas"]


def test_se_conservan_solo_los_ultimos(api, db, cabeceras_admin) -> None:
    for _ in range(CONSERVAR + 1):
        assert api.post(ENTRENAR, headers=cabeceras_admin).status_code == 201
    por_tipo = dict(db.execute(
        select(ModeloAnalitica.tipo, func.count()).group_by(ModeloAnalitica.tipo)
    ).all())
    assert por_tipo == {"DEMANDA": CONSERVAR, "SEGMENTOS": CONSERVAR}


def test_las_ventas_reales_entran_al_entrenamiento(api, db, cabeceras_admin, pedido) -> None:
    from app.modules.ventas.models import Venta

    # El pedido se cobró la semana pasada: cae dentro de la ventana de
    # entrenamiento, que son semanas completas.
    db.execute(update(Venta).where(Venta.codigo == pedido["codigo"]).values(
        estado="PAGADA", creado_en=tiempo.ahora() - timedelta(days=8)))
    db.commit()

    cuerpo = api.post(ENTRENAR, headers=cabeceras_admin).json()
    assert cuerpo["demanda"]["parametros"]["productos"] == 1
    assert cuerpo["demanda"]["filas_reales"] >= 1
    blusa = cuerpo["predicciones"]["predicciones"][0]
    assert blusa["producto"] == "Blusa de seda" and blusa["reales_ultimas_4"] >= 2
    assert cuerpo["segmentos"]["filas_reales"] == 1

    clientes = api.get(f"{API}/clientes", headers=cabeceras_admin).json()
    assert len(clientes) == 1
    assert clientes[0]["compras"] == 1 and clientes[0]["monto"] == 500.0
    assert clientes[0]["segmento"]


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
        r = api.post(ENTRENAR, headers=cabeceras_admin)
        assert r.status_code == 403
        assert r.json()["codigo"] == "plan_limit"
        assert api.get(RESUMEN, headers=cabeceras_admin).status_code == 403
    finally:
        plan = db.get(Plan, 3)
        plan.funciones = antes
        db.commit()


def test_el_cliente_no_entra(api, cabeceras_cliente) -> None:
    assert api.post(ENTRENAR, headers=cabeceras_cliente).status_code == 403
    assert api.get(RESUMEN, headers=cabeceras_cliente).status_code == 403


def test_una_empresa_no_ve_los_modelos_de_otra(
    api, cabeceras_admin, fabrica_sesiones, empresa_b
) -> None:
    assert api.post(ENTRENAR, headers=cabeceras_admin).status_code == 201
    otra = fabrica_sesiones()
    otra.info[CLAVE_EMPRESA] = empresa_b
    try:
        assert otra.scalar(select(func.count(ModeloAnalitica.id))) == 0
    finally:
        otra.close()
    propia = fabrica_sesiones()
    try:
        assert propia.scalar(select(func.count(ModeloAnalitica.id))) == 2
    finally:
        propia.close()


@pytest.mark.parametrize("tabla", ["modelo_analitica"])
def test_los_modelos_no_viajan_en_la_copia_ni_en_la_exportacion(tabla) -> None:
    from app.modules.datos.tablas import FUERA_DE_LA_COPIA, FUERA_DE_LA_EXPORTACION

    assert tabla in FUERA_DE_LA_COPIA
    assert tabla in FUERA_DE_LA_EXPORTACION
