"""CU-26, CU-39 y CU-40 · Avisos por correo, exportación y copias de seguridad.

Lo que más importa cubrir
-------------------------
- **CU-26 (RF-49).** Las devoluciones web avisan: al encargado cuando entra la
  solicitud y al cliente cuando se resuelve. Sin la función `correo` del plan,
  el aviso queda en la campanita pero no sale por correo.
- **CU-39 (RF-48).** El Excel trae una hoja por tabla con las filas de la
  empresa, nunca el hash de la contraseña; sin la función del plan, 403.
- **CU-40.** La copia manual se descarga firmada y no queda guardada (RNF17);
  el plan dice cada cuánto (RN-18). Restaurar reemplaza todo en una sola
  transacción (RN-19); una copia alterada o de otra empresa se rechaza sin
  tocar nada. La automática se guarda cifrada, es idempotente y conserva las
  últimas que dice el plan.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select

from tests.test_cu28_webhook import _saldos, pedido, tienda  # noqa: F401 - fixtures
from tests.test_p2_cu24_devolucion_web import (  # noqa: F401 - fixtures
    SOLICITUDES_SUCURSAL,
    _solicitar,
    encargado,
    entregado,
    pagado,
)

EXCEL = "/api/v1/exportacion/datos.xlsx"
CSV = "/api/v1/exportacion/datos.zip"
RESPALDOS = "/api/v1/respaldos"
MANUAL = f"{RESPALDOS}/manual"
RESTAURAR = f"{RESPALDOS}/restaurar"
AUTOMATICA = "/api/v1/mantenimiento/respaldos"
CATEGORIAS = "/api/v1/catalogo/categorias"


def _con_plan(db, **cambios):
    """Cambia las funciones del plan de la empresa de prueba y las devuelve."""
    from app.modules.plataforma.models import Plan

    plan = db.get(Plan, 3)
    antes = dict(plan.funciones)
    plan.funciones = {**antes, **cambios}
    db.commit()
    return antes


def _reponer_plan(db, antes):
    from app.modules.plataforma.models import Plan

    plan = db.get(Plan, 3)
    plan.funciones = antes
    db.commit()


def _avisos(db, tipo="DEVOLUCION"):
    from app.modules.notificaciones.models import Notificacion

    db.expire_all()
    return list(db.scalars(select(Notificacion).where(Notificacion.tipo == tipo)
                           .order_by(Notificacion.id)))


# =====================================================================
# CU-26 · Notificar eventos por correo según el plan
# =====================================================================

def test_la_devolucion_web_avisa_al_encargado_y_despues_al_cliente(
    api, cabeceras_cliente, encargado, entregado, tienda, db
) -> None:
    r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
    assert r.status_code == 201, r.text
    avisos = _avisos(db)
    assert len(avisos) == 1
    assert entregado["codigo"] in avisos[0].titulo
    assert avisos[0].correo_estado == "PENDIENTE"

    aprobada = api.post(f"{SOLICITUDES_SUCURSAL}/{r.json()['id']}/aprobar", headers=encargado,
                        json={"respuesta": "Tráigala sin uso"})
    assert aprobada.status_code == 200, aprobada.text
    avisos = _avisos(db)
    assert len(avisos) == 2
    assert avisos[1].titulo.startswith("Aprobamos su devolución")
    assert avisos[1].destinatario_id != avisos[0].destinatario_id


def test_sin_la_funcion_correo_el_aviso_no_sale_por_correo(
    api, cabeceras_cliente, encargado, entregado, tienda, db
) -> None:
    antes = _con_plan(db, correo=False)
    try:
        r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
        assert r.status_code == 201, r.text
        aviso = _avisos(db)[0]
        assert aviso.correo_estado == "OMITIDO"
        assert "plan" in (aviso.correo_error or "")
    finally:
        _reponer_plan(db, antes)


# =====================================================================
# CU-39 · Exportar los datos de la empresa
# =====================================================================

def test_el_excel_trae_una_hoja_por_tabla_y_sin_contrasenas(api, cabeceras_admin) -> None:
    api.post(CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0,
                                                       "activa": True})
    r = api.get(EXCEL, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert "attachment" in r.headers["content-disposition"]
    libro = load_workbook(io.BytesIO(r.content), read_only=True)
    assert {"resumen", "personal", "categoria", "producto"} <= set(libro.sheetnames)
    categorias = list(libro["categoria"].values)
    assert any("Blusas" in (str(v) for v in fila) for fila in categorias[1:])
    encabezado_personal = list(libro["personal"].values)[0]
    assert "hash_contrasena" not in encabezado_personal


def test_el_zip_trae_un_csv_por_tabla(api, cabeceras_admin) -> None:
    r = api.get(CSV, headers=cabeceras_admin)
    assert r.status_code == 200
    nombres = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "personal.csv" in nombres and "categoria.csv" in nombres


def test_exportar_es_funcion_del_plan(api, cabeceras_admin, db) -> None:
    antes = _con_plan(db, exportar_datos=False)
    try:
        r = api.get(EXCEL, headers=cabeceras_admin)
        assert r.status_code == 403
        assert r.json()["codigo"] == "plan_limit"
    finally:
        _reponer_plan(db, antes)


# =====================================================================
# CU-40 · Copias de seguridad
# =====================================================================

def _copia(api, admin) -> bytes:
    r = api.post(MANUAL, headers=admin)
    assert r.status_code == 200, r.text
    assert r.headers["content-disposition"].endswith('.json"')
    return r.content


def _subir(api, admin, contenido: bytes, nombre="copia.json"):
    return api.post(RESTAURAR, headers=admin,
                    files={"archivo": (nombre, contenido, "application/json")})


def _categorias(api, admin) -> list[str]:
    """Todas las categorías: el listado es un árbol y se aplana."""
    def aplanar(nodos):
        for n in nodos:
            yield n["nombre"]
            yield from aplanar(n.get("subcategorias") or [])
    return sorted(aplanar(api.get(CATEGORIAS, headers=admin).json()))


def test_la_copia_manual_se_descarga_y_no_se_guarda(api, cabeceras_admin, db) -> None:
    from app.modules.datos.models import Respaldo

    copia = json.loads(_copia(api, cabeceras_admin))
    assert copia["formato"] == "violet-boutique/respaldo"
    assert copia["empresa_id"] == 1
    assert len(copia["firma"]) == 64

    db.expire_all()
    fila = db.scalar(select(Respaldo))
    assert fila.tipo == "MANUAL" and fila.contenido is None

    historial = api.get(RESPALDOS, headers=cabeceras_admin).json()
    assert historial["copias"][0]["descargable"] is False


def test_el_plan_limita_cada_cuanto_la_manual(api, cabeceras_admin, db) -> None:
    antes = _con_plan(db, respaldo_intervalo_horas=24)
    try:
        _copia(api, cabeceras_admin)
        otra = api.post(MANUAL, headers=cabeceras_admin)
        assert otra.status_code == 403
        assert "una por día" in otra.json()["detail"]
        assert api.get(RESPALDOS, headers=cabeceras_admin).json()["proxima_manual"] is not None
    finally:
        _reponer_plan(db, antes)


def test_restaurar_reemplaza_todo_y_queda_registrado(api, cabeceras_admin, db) -> None:
    api.post(CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0,
                                                       "activa": True})
    madre = api.post(CATEGORIAS, headers=cabeceras_admin, json={
        "nombre": "Ropa superior", "orden": 1, "activa": True}).json()["id"]
    api.post(CATEGORIAS, headers=cabeceras_admin, json={
        "nombre": "Camisas", "orden": 2, "activa": True, "categoria_padre_id": madre})
    copia = _copia(api, cabeceras_admin)

    # Después de la copia: se agrega una y se borra todo rastro de otra.
    api.post(CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Abrigos", "orden": 3,
                                                       "activa": True})
    assert "Abrigos" in _categorias(api, cabeceras_admin)

    r = _subir(api, cabeceras_admin, copia)
    assert r.status_code == 200, r.text
    assert r.json()["filas"]["categoria"] == 3
    # No se mezcla: lo de después de la copia ya no está.
    assert _categorias(api, cabeceras_admin) == ["Blusas", "Camisas", "Ropa superior"]

    historial = api.get(RESPALDOS, headers=cabeceras_admin).json()
    assert historial["restauraciones"][0]["archivo"] == "copia.json"
    assert historial["restauraciones"][0]["restaurado_por"]


def test_una_copia_alterada_no_se_restaura_y_no_toca_nada(api, cabeceras_admin) -> None:
    api.post(CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0,
                                                       "activa": True})
    copia = json.loads(_copia(api, cabeceras_admin))
    copia["tablas"]["categoria"][0]["nombre"] = "Trucha"
    r = _subir(api, cabeceras_admin, json.dumps(copia).encode())
    assert r.status_code == 422
    assert "alterada" in r.json()["detail"]
    assert _categorias(api, cabeceras_admin) == ["Blusas"]


def test_una_copia_de_otra_empresa_no_se_restaura(api, cabeceras_admin) -> None:
    from app.modules.datos import respaldos

    copia = json.loads(_copia(api, cabeceras_admin))
    copia.pop("firma")
    copia["empresa_id"] = 999
    copia["firma"] = respaldos._firmar({k: v for k, v in copia.items() if k != "firma"})
    r = _subir(api, cabeceras_admin, json.dumps(copia).encode())
    assert r.status_code == 422
    assert "otra empresa" in r.json()["detail"]


def test_un_archivo_cualquiera_no_es_una_copia(api, cabeceras_admin) -> None:
    assert _subir(api, cabeceras_admin, b"hola").status_code == 422


def test_la_automatica_se_guarda_cifrada_y_es_idempotente(api, cabeceras_admin, db) -> None:
    from app.modules.datos.models import Respaldo

    primera = api.post(AUTOMATICA, headers=cabeceras_admin).json()
    assert primera["creada"] is True
    segunda = api.post(AUTOMATICA, headers=cabeceras_admin).json()
    assert segunda["creada"] is False

    db.expire_all()
    fila = db.scalar(select(Respaldo).where(Respaldo.tipo == "AUTOMATICA"))
    assert fila.contenido is not None
    assert b"violet-boutique" not in fila.contenido  # cifrada

    bajada = api.get(f"{RESPALDOS}/{fila.id}/descarga", headers=cabeceras_admin)
    assert bajada.status_code == 200
    assert json.loads(bajada.content)["formato"] == "violet-boutique/respaldo"

    # Y se restaura desde ella sin subir nada.
    r = api.post(f"{RESPALDOS}/{fila.id}/restaurar", headers=cabeceras_admin)
    assert r.status_code == 200, r.text


def test_la_automatica_conserva_solo_las_que_dice_el_plan(api, cabeceras_admin, db) -> None:
    from app.modules.datos.models import Respaldo

    antes = _con_plan(db, respaldo_retencion=2)
    try:
        for _ in range(3):
            assert api.post(AUTOMATICA, headers=cabeceras_admin).json()["creada"] is True
            # Se envejece la última para que la próxima ya toque.
            db.expire_all()
            ultima = db.scalar(select(Respaldo).order_by(Respaldo.id.desc()))
            ultima.creado_en = ultima.creado_en - timedelta(days=30)
            db.commit()
        db.expire_all()
        assert db.scalar(select(func.count(Respaldo.id))) == 2
    finally:
        _reponer_plan(db, antes)


def test_solo_el_admin_gestiona_copias(api, encargado) -> None:
    assert api.post(MANUAL, headers=encargado).status_code == 403
    assert api.get(EXCEL, headers=encargado).status_code == 403


def test_restaura_una_empresa_con_ventas_y_devoluciones(
    api, cabeceras_admin, cabeceras_cliente, encargado, entregado, tienda, db
) -> None:
    """Con datos de verdad: productos, existencias, una venta web pagada y
    entregada, su pago y una solicitud de devolución. Todo vuelve igual."""
    r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
    assert r.status_code == 201, r.text
    copia = _copia(api, cabeceras_admin)
    filas = {k: len(v) for k, v in json.loads(copia)["tablas"].items()}
    assert filas["venta"] >= 1 and filas["solicitud_devolucion"] == 1

    # Se rechaza la solicitud después de la copia...
    api.post(f"{SOLICITUDES_SUCURSAL}/{r.json()['id']}/rechazar", headers=encargado,
             json={"respuesta": "Ya tiene uso visible"})
    restaurada = _subir(api, cabeceras_admin, copia)
    assert restaurada.status_code == 200, restaurada.text
    assert restaurada.json()["filas"] == filas

    # ...y la restauración la deja como estaba en la copia: pendiente.
    pendientes = api.get(SOLICITUDES_SUCURSAL, headers=encargado).json()
    assert [s["estado"] for s in pendientes] == ["PENDIENTE"]


# =====================================================================
# Tanda B de la auditoría: lo que no sale y lo que sale escapado
# =====================================================================

@pytest.mark.parametrize("texto, esperado", [
    ("=HYPERLINK(\"http://x\")", "'=HYPERLINK(\"http://x\")"),
    ("+591 70000000", "'+591 70000000"),
    ("-2+3", "'-2+3"),
    ("@SUM(A1)", "'@SUM(A1)"),
    ("\t=1", "'\t=1"),
    ("Blusa", "Blusa"),
    ("", ""),
    (-5, -5),
    (None, None),
])
def test_un_texto_que_parece_formula_sale_escapado(texto, esperado) -> None:
    from app.modules.datos import tablas

    assert tablas.sin_formula(texto) == esperado


def test_la_exportacion_escapa_formulas_y_omite_secretos(api, cabeceras_admin) -> None:
    api.post(CATEGORIAS, headers=cabeceras_admin, json={"nombre": "=1+1", "orden": 0,
                                                       "activa": True})
    libro = load_workbook(io.BytesIO(api.get(EXCEL, headers=cabeceras_admin).content))
    assert "suscripcion_push" not in libro.sheetnames
    assert "carga_util" not in [c.value for c in libro["transaccion_pasarela"][1]]
    celdas = [c.value for fila in libro["categoria"].iter_rows() for c in fila]
    assert "'=1+1" in celdas
    assert not any(isinstance(c.value, str) and c.value.startswith("=")
                   for fila in libro["categoria"].iter_rows() for c in fila)

    zf = zipfile.ZipFile(io.BytesIO(api.get(CSV, headers=cabeceras_admin).content))
    assert "suscripcion_push.csv" not in zf.namelist()
    assert "carga_util" not in zf.read("transaccion_pasarela.csv").decode("utf-8-sig")
    assert "'=1+1" in zf.read("categoria.csv").decode("utf-8-sig")


def test_las_copias_usan_su_propia_clave_y_las_viejas_se_siguen_leyendo(
    api, cabeceras_admin, monkeypatch
) -> None:
    from app.core.config import settings
    from app.modules.datos import respaldos

    api.post(CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0,
                                                       "activa": True})
    vieja = _copia(api, cabeceras_admin)  # firmada con la del token

    monkeypatch.setattr(settings, "RESPALDO_SECRET", "clave-propia-de-las-copias-1234567890")
    # La manual tiene un tope por semana: la «nueva» es la misma, firmada ahora.
    cuerpo = json.loads(vieja)
    cuerpo.pop("firma")
    nueva = json.dumps({**cuerpo, "firma": respaldos._firmar(cuerpo)}).encode()
    assert json.loads(nueva)["firma"] != json.loads(vieja)["firma"]
    assert _subir(api, cabeceras_admin, vieja).status_code == 200
    assert _subir(api, cabeceras_admin, nueva).status_code == 200

    # Quien solo tiene la clave del token ya no puede fabricar una copia válida.
    monkeypatch.setattr(settings, "RESPALDO_SECRET", "")
    r = _subir(api, cabeceras_admin, nueva)
    assert r.status_code == 422 and "alterada" in r.json()["detail"]
