"""CU-25 · Atender solicitud de devolución (2do parcial).

Lo que más importa cubrir
-------------------------
- **Aprobar o rechazar, y el rechazo dice por qué (RF-36).** Rechazada, las
  unidades vuelven a poder pedirse.
- **Recibir una devolución aprobada** reingresa la prenda, reembolsa por la
  pasarela (mismo medio) y deja la nota ABIERTA, de origen WEB, sin turno y
  sin tocar ningún cajón.
- **La nota se cierra solo con la conformidad del cliente (RN-20).** Si no
  está conforme, queda abierta con su observación.
- **El cambio aprobado se retira en caja (CU-22)**, aunque la ventana haya
  vencido, y la solicitud queda completada con esa nota.
- **Si la pasarela falla, no queda nada escrito.**
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core import tiempo
from tests.test_cu28_webhook import _saldos, pedido, tienda  # noqa: F401 - fixtures
from tests.test_cu31_venta_presencial import _abrir_turno, _caja, _empleado
from tests.test_p2_cu24_devolucion_web import (  # noqa: F401 - fixtures
    DEVOLUCIONES_WEB,
    SOLICITUDES_SUCURSAL,
    _solicitar,
    encargado,
    entregado,
    otra_talla,
    pagado,
)

NOTAS = "/api/v1/pos/notas-devolucion"


def _accion(api, cab, solicitud_id: int, accion: str, respuesta: str | None = None):
    cuerpo = {} if accion == "recibir" else {"respuesta": respuesta}
    return api.post(f"{SOLICITUDES_SUCURSAL}/{solicitud_id}/{accion}", headers=cab, json=cuerpo)


@pytest.fixture
def devolucion_pedida(api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict) -> int:
    r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# =====================================================================
# Aprobar y rechazar
# =====================================================================

def test_el_rechazo_exige_motivo_y_libera_las_unidades(
    api: TestClient, cabeceras_cliente: dict, encargado: dict, entregado: dict, tienda: dict,
    devolucion_pedida: int,
) -> None:
    assert _accion(api, encargado, devolucion_pedida, "rechazar", "").status_code == 422
    r = _accion(api, encargado, devolucion_pedida, "rechazar", "La prenda tiene uso visible")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECHAZADA"
    assert r.json()["respuesta"] == "La prenda tiene uso visible"
    # Ya no se puede volver a atender.
    assert _accion(api, encargado, devolucion_pedida, "aprobar").status_code == 409
    # Y la unidad vuelve a estar disponible para pedirse.
    ficha = api.get(f"{DEVOLUCIONES_WEB}/pedidos/{entregado['codigo']}", headers=cabeceras_cliente).json()
    assert ficha["lineas"][0]["devolvibles"] == 2


def test_el_encargado_de_otra_sucursal_no_la_atiende(
    api: TestClient, cabeceras_admin: dict, devolucion_pedida: int
) -> None:
    from tests.test_cu31_venta_presencial import _crear_sucursal

    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    ajeno = _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=otra, sufijo="26")
    assert _accion(api, ajeno, devolucion_pedida, "aprobar").status_code == 404


# =====================================================================
# Recibir: nota ABIERTA, reingreso y reembolso
# =====================================================================

def test_recibir_reingresa_reembolsa_y_deja_la_nota_abierta(
    api: TestClient, cabeceras_admin: dict, cabeceras_cliente: dict, encargado: dict,
    entregado: dict, tienda: dict, devolucion_pedida: int,
) -> None:
    antes = _saldos(api, cabeceras_admin, tienda["variante"], tienda["sucursal"])
    # No se recibe lo que no se aprobó.
    assert _accion(api, encargado, devolucion_pedida, "recibir").status_code == 409
    assert _accion(api, encargado, devolucion_pedida, "aprobar", "Traela a la tienda").status_code == 200

    r = _accion(api, encargado, devolucion_pedida, "recibir")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["estado"] == "COMPLETADA"
    assert s["nota_estado"] == "ABIERTA" and s["conforme"] is None
    assert s["numero_nota"].startswith("ND-")
    assert s["reembolso_monto"] == "250.00"
    assert s["reembolso_referencia"].startswith("re_sim_")

    despues = _saldos(api, cabeceras_admin, tienda["variante"], tienda["sucursal"])
    assert despues[0] == antes[0] + 1

    nota = api.get(f"{NOTAS}/{s['devolucion_id']}", headers=encargado).json()
    assert nota["origen"] == "WEB" and nota["caja"] == "Devolución web"
    assert nota["monto_reintegrado"] == "0.00"  # no sale de ningún cajón
    assert nota["cajero"]  # quien la recibió
    # El cliente ve su nota.
    assert api.get(f"{DEVOLUCIONES_WEB}/{devolucion_pedida}/nota", headers=cabeceras_cliente).status_code == 200


def test_sin_conformidad_la_nota_no_se_cierra(
    api: TestClient, cabeceras_cliente: dict, encargado: dict, devolucion_pedida: int
) -> None:
    _accion(api, encargado, devolucion_pedida, "aprobar")
    _accion(api, encargado, devolucion_pedida, "recibir")
    url = f"{DEVOLUCIONES_WEB}/{devolucion_pedida}/conformidad"

    r = api.post(url, headers=cabeceras_cliente, json={"conforme": False, "observacion": "Falta el reembolso"})
    assert r.status_code == 200
    assert r.json()["nota_estado"] == "ABIERTA" and r.json()["conforme"] is False

    r = api.post(url, headers=cabeceras_cliente, json={"conforme": True, "observacion": "Ya me llegó"})
    assert r.json()["nota_estado"] == "CERRADA" and r.json()["conforme"] is True
    # Cerrada, no se vuelve a tocar.
    assert api.post(url, headers=cabeceras_cliente, json={"conforme": False}).status_code == 409


def test_si_la_pasarela_falla_no_queda_nada(
    api: TestClient, cabeceras_admin: dict, encargado: dict, tienda: dict, devolucion_pedida: int,
    monkeypatch,
) -> None:
    from app.integrations import pasarela_pago
    from app.integrations.pasarela_pago.base import ErrorDePasarela

    def _falla(*_a, **_k):
        raise ErrorDePasarela("tarjeta vencida")

    _accion(api, encargado, devolucion_pedida, "aprobar")
    antes = _saldos(api, cabeceras_admin, tienda["variante"], tienda["sucursal"])
    monkeypatch.setattr(pasarela_pago, "reembolsar", _falla)
    r = _accion(api, encargado, devolucion_pedida, "recibir")
    assert r.status_code == 502
    assert "no se registró nada" in r.json()["detail"]
    assert _saldos(api, cabeceras_admin, tienda["variante"], tienda["sucursal"]) == antes
    lista = api.get(SOLICITUDES_SUCURSAL, headers=encargado).json()
    assert lista[0]["estado"] == "APROBADA" and lista[0]["devolucion_id"] is None


def test_un_cambio_no_se_recibe_aca(
    api: TestClient, cabeceras_cliente: dict, encargado: dict, entregado: dict, tienda: dict,
    otra_talla: int,
) -> None:
    s = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1,
                   tipo="CAMBIO", nueva=otra_talla).json()
    _accion(api, encargado, s["id"], "aprobar")
    r = _accion(api, encargado, s["id"], "recibir")
    assert r.status_code == 409 and "caja" in r.json()["detail"]


# =====================================================================
# El cambio aprobado se retira en caja (CU-22)
# =====================================================================

def test_el_cambio_aprobado_se_hace_en_caja_aunque_venza_la_ventana(
    api: TestClient, cabeceras_admin: dict, cabeceras_cliente: dict, encargado: dict,
    entregado: dict, tienda: dict, otra_talla: int, db,
) -> None:
    from app.modules.ventas.models import Venta

    s = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1,
                   tipo="CAMBIO", nueva=otra_talla).json()
    _accion(api, encargado, s["id"], "aprobar", "Pasá por la tienda")

    # El cliente tarda: la compra y la entrega quedan fuera de la ventana.
    fila = db.query(Venta).filter(Venta.codigo == entregado["codigo"]).one()
    fila.creado_en = tiempo.ahora() - timedelta(days=10)
    fila.entregado_en = tiempo.ahora() - timedelta(days=9)
    db.commit()

    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=tienda["sucursal"], sufijo="25")
    _abrir_turno(api, cajero, _caja(db, tienda["sucursal"]))
    r = api.post(
        "/api/v1/pos/devoluciones/cambios",
        headers=cajero,
        json={
            "venta_codigo": entregado["codigo"],
            "motivo": "Cambio pedido por la web",
            "devueltas": [{"variante_id": tienda["variante"], "cantidad": 1}],
            "llevadas": [{"variante_id": otra_talla, "cantidad": 1}],
            "metodo_diferencia": "EFECTIVO",
            "conformidad": {"conforme": True},
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["diferencia"] == "30.00"

    mia = api.get(DEVOLUCIONES_WEB, headers=cabeceras_cliente).json()[0]
    assert mia["estado"] == "COMPLETADA" and mia["devolucion_id"] == r.json()["id"]
    assert mia["nota_estado"] == "CERRADA"  # en caja el cliente estuvo presente


def test_sin_cambio_aprobado_la_caja_sigue_exigiendo_la_ventana(
    api: TestClient, cabeceras_admin: dict, entregado: dict, tienda: dict, otra_talla: int, db,
) -> None:
    from app.modules.ventas.models import Venta

    fila = db.query(Venta).filter(Venta.codigo == entregado["codigo"]).one()
    fila.creado_en = tiempo.ahora() - timedelta(days=10)
    db.commit()
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=tienda["sucursal"], sufijo="27")
    _abrir_turno(api, cajero, _caja(db, tienda["sucursal"]))
    r = api.post(
        "/api/v1/pos/devoluciones/cambios",
        headers=cajero,
        json={
            "venta_codigo": entregado["codigo"],
            "motivo": "Sin solicitud",
            "devueltas": [{"variante_id": tienda["variante"], "cantidad": 1}],
            "llevadas": [{"variante_id": otra_talla, "cantidad": 1}],
            "metodo_diferencia": "EFECTIVO",
            "conformidad": {"conforme": True},
        },
    )
    assert r.status_code == 409 and "plazo" in r.json()["detail"]
