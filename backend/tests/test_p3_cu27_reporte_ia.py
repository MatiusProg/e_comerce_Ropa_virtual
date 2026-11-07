"""CU-27 · Generar reporte con IA por texto o voz (2do parcial, P3).

El usuario pide un reporte en lenguaje natural; el modelo lo traduce a una
ESPECIFICACIÓN (medida, agrupación, filtros, período) que el backend valida
contra una lista blanca y ejecuta. Ninguna prueba llama al modelo de verdad:
se sustituye `interpretar_consulta`, y se prueba también el intérprete por
reglas, que es el respaldo cuando el modelo no está.

Lo que más importa:
- que los números salgan de la base (datos reales, no preparados);
- que lo que devuelve el modelo NO llegue a la consulta sin validar;
- que el encargado solo vea su sucursal y que otra empresa no se vea nunca;
- que lo ambiguo se devuelva como no entendido, con motivo;
- que se pueda exportar a PDF y Excel.
"""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.core import tiempo
from app.integrations import interprete
from app.integrations.interprete import InterpreteNoConfigurado
from app.modules.reportes import interprete_reglas
from tests.test_cu36_tablero import (
    _crear_sucursal,
    _crear_variantes,
    _ingresar,
    _vender,
)

CONSULTA = "/api/v1/reportes/ia/consulta"
EXPORTAR = "/api/v1/reportes/ia/exportar"
EMPLEADOS = "/api/v1/organizacion/empleados"


def _modelo(monkeypatch, respuesta=None, error: Exception | None = None) -> list:
    """Sustituye al modelo. Devuelve la lista de frases con que lo llamaron."""
    llamadas: list = []

    def falso(texto, vocabulario, hoy):
        llamadas.append((texto, vocabulario))
        if error is not None:
            raise error
        return respuesta

    monkeypatch.setattr(interprete, "interpretar_consulta", falso)
    return llamadas


@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict[str, str]) -> list[int]:
    return _crear_variantes(api, cabeceras_admin)


@pytest.fixture
def tienda(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variantes: list[int]):
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variantes[0], 40), (variantes[1], 3)])
    return {"variante": variantes[0], "sucursal": sucursal}


# --- Datos reales -----------------------------------------------------------------


def test_ventas_por_sucursal_salen_de_la_BASE(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch
) -> None:
    _vender(api, cabeceras_cliente, tienda, cantidad=2)
    _vender(api, cabeceras_cliente, tienda, cantidad=1)
    _modelo(monkeypatch, {"entendido": True, "medida": "ventas_monto",
                          "agrupar": ["sucursal"], "resumen": "Ventas por sucursal"})

    r = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "ventas por sucursal"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["entendido"] is True
    assert cuerpo["interprete"] == "ia"
    assert cuerpo["encabezados"] == ["Sucursal", "Monto vendido (Bs)"]
    assert cuerpo["filas"] == [["Centro", 960.0]]
    assert cuerpo["grafico"]["tipo"] == "barras"
    assert cuerpo["grafico"]["etiquetas"] == ["Centro"]
    assert "Centro" in cuerpo["narrativa"]


def test_un_pedido_SIN_pagar_no_cuenta(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch
) -> None:
    _vender(api, cabeceras_cliente, tienda, cantidad=2, pagar=False)
    _modelo(monkeypatch, {"entendido": True, "medida": "unidades_vendidas", "agrupar": ["producto"]})
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "x" * 3}).json()
    assert cuerpo["filas"] == []
    assert "No hay datos" in cuerpo["narrativa"]


def test_ventas_por_semana_dan_un_grafico_de_LINEAS(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch
) -> None:
    _vender(api, cabeceras_cliente, tienda, cantidad=1)
    _modelo(monkeypatch, {"entendido": True, "medida": "ventas_monto", "agrupar": ["semana"]})
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "por semana"}).json()
    assert cuerpo["grafico"]["tipo"] == "lineas"
    assert len(cuerpo["filas"]) == 1
    assert cuerpo["filas"][0][0].startswith("Sem. del")


def test_dos_dimensiones_hacen_SERIES(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch
) -> None:
    _vender(api, cabeceras_cliente, tienda, cantidad=1)
    _modelo(monkeypatch, {"entendido": True, "medida": "ventas_monto",
                          "agrupar": ["mes", "sucursal"], "grafico": "lineas"})
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "comparar"}).json()
    assert [s["nombre"] for s in cuerpo["grafico"]["series"]] == ["Centro"]
    assert cuerpo["grafico"]["series"][0]["datos"] == [320.0]


def test_menor_existencia_ordena_ASCENDENTE_y_respeta_el_limite(
    api, cabeceras_admin, tienda, monkeypatch
) -> None:
    _modelo(monkeypatch, {"entendido": True, "medida": "existencias", "agrupar": ["talla"],
                          "orden": "asc", "limite": 1})
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "menor stock"}).json()
    assert cuerpo["filas"] == [["M", 3]]
    assert cuerpo["subtitulos"][0].startswith("Situación al")


# --- Lo que devuelve el modelo NO se confía ------------------------------------------


@pytest.mark.parametrize(
    "crudo, texto_del_motivo",
    [
        ({"entendido": True, "medida": "sueldos"}, "No sé calcular"),
        ({"entendido": True, "medida": "ventas_monto", "agrupar": ["empleado"]}, "no se puede agrupar"),
        ({"entendido": True, "medida": "ventas_monto", "agrupar": ["dia", "mes"]}, "una sola escala"),
        ({"entendido": True, "medida": "ventas_monto", "agrupar": ["sucursal", "producto", "talla"]},
         "dos criterios"),
        ({"entendido": True, "medida": "ventas_monto", "filtros": {"sucursal": [999999]}}, "No encontré"),
    ],
)
def test_una_especificacion_invalida_se_RECHAZA_con_motivo(
    api, cabeceras_admin, monkeypatch, crudo, texto_del_motivo
) -> None:
    _modelo(monkeypatch, crudo)
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "algo"}).json()
    assert cuerpo["entendido"] is False
    assert texto_del_motivo in cuerpo["motivo"]
    assert cuerpo["ejemplos"]


def test_un_SQL_en_un_campo_no_llega_a_la_base(api, cabeceras_admin, monkeypatch) -> None:
    _modelo(monkeypatch, {"entendido": True, "medida": "ventas_monto; DROP TABLE venta"})
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "x" * 3}).json()
    assert cuerpo["entendido"] is False


def test_lo_AMBIGUO_vuelve_con_el_motivo_del_modelo(api, cabeceras_admin, monkeypatch) -> None:
    _modelo(monkeypatch, {"entendido": False, "motivo": "¿De qué sucursal?"})
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "las ventas de ahí"}).json()
    assert cuerpo == {**cuerpo, "entendido": False, "motivo": "¿De qué sucursal?"}


def test_no_entender_NO_gasta_el_cupo(api, cabeceras_admin, db, monkeypatch) -> None:
    from app.modules.plataforma import verificador

    gastado = []
    monkeypatch.setattr(verificador, "consumir_cupo", lambda *a: gastado.append(a))
    _modelo(monkeypatch, None)
    api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "hola qué tal"})
    assert gastado == []


# --- Ámbito ----------------------------------------------------------------------------


def test_el_ENCARGADO_solo_ve_su_sucursal(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch
) -> None:
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingresar(api, cabeceras_admin, sucursal_id=otra, lineas=[(tienda["variante"], 10)])
    _vender(api, cabeceras_cliente, {"variante": tienda["variante"], "sucursal": otra}, cantidad=1)
    _vender(api, cabeceras_cliente, tienda, cantidad=2)

    alta = api.post(EMPLEADOS, headers=cabeceras_admin, json={
        "nombres": "Ana", "apellidos": "Rojas", "correo": "enc.ia@violetboutique.bo",
        "contrasena": "Encargada12", "documento": "7788991", "telefono": "70000001",
        "cargo": "ENCARGADO", "sucursal_id": otra,
        "fecha_ingreso": date.today().isoformat(),
    })
    assert alta.status_code == 201, alta.text
    token = api.post("/api/v1/auth/login", json={"correo": "enc.ia@violetboutique.bo",
                                                  "contrasena": "Encargada12"}).json()["access_token"]
    # Aunque el modelo pida la otra sucursal, se impone la suya.
    _modelo(monkeypatch, {"entendido": True, "medida": "ventas_monto", "agrupar": ["sucursal"],
                          "filtros": {"sucursal": [tienda["sucursal"]]}})
    cuerpo = api.post(CONSULTA, headers={"Authorization": f"Bearer {token}"},
                      json={"texto": "ventas"}).json()
    assert cuerpo["filas"] == [["Norte", 320.0]]


def test_un_cliente_no_pide_reportes(api, cabeceras_cliente) -> None:
    assert api.post(CONSULTA, headers=cabeceras_cliente, json={"texto": "ventas"}).status_code == 403


# --- Respaldo sin IA y exportación -------------------------------------------------------


def test_sin_modelo_entra_el_interprete_por_REGLAS(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch
) -> None:
    _vender(api, cabeceras_cliente, tienda, cantidad=2)
    _modelo(monkeypatch, error=InterpreteNoConfigurado("sin clave"))
    cuerpo = api.post(CONSULTA, headers=cabeceras_admin,
                      json={"texto": "Mostrame las ventas de este mes agrupadas por sucursal"}).json()
    assert cuerpo["entendido"] is True
    assert cuerpo["interprete"] == "reglas"
    assert cuerpo["filas"] == [["Centro", 640.0]]


@pytest.mark.parametrize("formato, firma", [("pdf", b"%PDF"), ("xlsx", b"PK")])
def test_se_EXPORTA_lo_que_se_armo(
    api, cabeceras_admin, cabeceras_cliente, tienda, monkeypatch, formato, firma
) -> None:
    _vender(api, cabeceras_cliente, tienda, cantidad=1)
    _modelo(monkeypatch, {"entendido": True, "medida": "unidades_vendidas", "agrupar": ["producto"]})
    espec = api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "más vendidos"}).json()[
        "especificacion"
    ]
    r = api.post(f"{EXPORTAR}.{formato}", headers=cabeceras_admin, json=espec)
    assert r.status_code == 200, r.text
    assert r.content.startswith(firma)


# --- El intérprete por reglas, sin base -------------------------------------------------

VOCAB = {
    "medidas": {
        "ventas_monto": {"etiqueta": "Monto vendido (Bs)", "dimensiones": [
            "sucursal", "categoria", "producto", "dia", "semana", "mes", "canal"],
            "filtros": ["sucursal", "categoria", "producto", "canal"], "usa_periodo": True},
        "unidades_vendidas": {"etiqueta": "Unidades vendidas", "dimensiones": [
            "sucursal", "categoria", "producto", "dia", "semana", "mes"],
            "filtros": ["sucursal", "categoria", "producto"], "usa_periodo": True},
        "existencias": {"etiqueta": "Existencias disponibles", "dimensiones": [
            "sucursal", "categoria", "producto", "talla"],
            "filtros": ["sucursal", "categoria", "producto", "bajo_minimo"], "usa_periodo": False},
        "devoluciones_monto": {"etiqueta": "Valor devuelto (Bs)", "dimensiones": [
            "sucursal", "producto", "tipo", "mes"], "filtros": ["sucursal", "tipo"],
            "usa_periodo": True},
    },
    "valores": {"sucursal": {"1": "Centro", "2": "Norte"}, "categoria": {"5": "Blusas"}},
}
HOY = date(2026, 11, 7)


@pytest.mark.parametrize(
    "frase, esperado",
    [
        ("Mostrame las ventas de septiembre agrupadas por sucursal",
         {"medida": "ventas_monto", "agrupar": ["sucursal"], "desde": "2026-09-01", "hasta": "2026-09-30"}),
        ("¿Cuáles fueron los diez productos más vendidos este mes?",
         {"medida": "unidades_vendidas", "agrupar": ["producto"], "limite": 10, "desde": "2026-11-01"}),
        ("Generá un gráfico de ventas por semana",
         {"medida": "ventas_monto", "agrupar": ["semana"], "grafico": "lineas"}),
        ("Compará las ventas de las sucursales durante los últimos tres meses",
         {"medida": "ventas_monto", "agrupar": ["mes", "sucursal"], "desde": "2026-09-01"}),
        ("Mostrame los productos con menor existencia",
         {"medida": "existencias", "agrupar": ["producto"], "orden": "asc"}),
        ("¿Qué categorías generaron mayores ingresos durante este mes?",
         {"medida": "ventas_monto", "agrupar": ["categoria"]}),
        ("ventas de la sucursal Norte por día",
         {"agrupar": ["dia"], "filtros": {"sucursal": ["2"]}}),
    ],
)
def test_las_frases_del_ENUNCIADO_por_reglas(frase, esperado) -> None:
    crudo = interprete_reglas.interpretar(frase, VOCAB, HOY)
    assert crudo is not None
    for clave, valor in esperado.items():
        assert crudo[clave] == valor, (clave, crudo)


def test_reglas_no_inventan_lo_que_no_entienden() -> None:
    assert interprete_reglas.interpretar("contame un chiste", VOCAB, HOY) is None
