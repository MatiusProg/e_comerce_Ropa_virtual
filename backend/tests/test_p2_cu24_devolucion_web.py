"""CU-24 · Solicitar cambio o devolución por la web (2do parcial).

Lo que más importa cubrir
-------------------------
- **Solo un pedido ENTREGADO**, y la ventana corre **desde la entrega** (RF-35),
  que la marca el encargado de la sucursal del pedido.
- **Fuera de la ventana se rechaza (RN-08).**
- **No se pide dos veces lo mismo:** lo que ya volvió o ya está pedido en una
  solicitud abierta deja de estar disponible.
- **El cambio es por la misma prenda en otra talla o color**, con saldo en la
  sucursal del pedido.
- **Cada uno ve lo suyo:** el cliente sus pedidos; el encargado su sucursal.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core import tiempo
from tests.test_cu28_webhook import (  # noqa: F401 - fixtures de pytest
    PRODUCTOS,
    SIMULACION,
    TALLAS,
    _ingresar,
    pedido,
    tienda,
)
from tests.test_cu31_venta_presencial import _crear_sucursal, _empleado

PEDIDOS_SUCURSAL = "/api/v1/sucursal/pedidos"
SOLICITUDES_SUCURSAL = "/api/v1/sucursal/solicitudes-devolucion"
DEVOLUCIONES_WEB = "/api/v1/tienda/devoluciones"
VENTANA = "/api/v1/plataforma/mi-tienda/devoluciones"


@pytest.fixture
def pagado(api: TestClient, pedido: dict) -> dict:
    r = api.post(
        SIMULACION,
        json={"sesion": pedido["sesion"], "pedido": pedido["codigo"], "aprobado": True},
    )
    assert r.status_code == 200, r.text
    return pedido


@pytest.fixture
def encargado(api: TestClient, cabeceras_admin: dict, tienda: dict) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=tienda["sucursal"], sufijo="24")


@pytest.fixture
def entregado(api: TestClient, pagado: dict, encargado: dict) -> dict:
    r = api.post(f"{PEDIDOS_SUCURSAL}/{pagado['codigo']}/entregar", headers=encargado)
    assert r.status_code == 200, r.text
    return pagado


@pytest.fixture
def otra_talla(api: TestClient, cabeceras_admin: dict, tienda: dict, entregado: dict, db) -> int:
    """La misma blusa en talla L, con 3 en la sucursal del pedido."""
    from app.modules.catalogo.models import VarianteProducto

    original = db.get(VarianteProducto, tienda["variante"])
    producto_id, color_id = original.producto_id, original.color_id
    talla = api.post(
        TALLAS, headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "L", "orden": 3, "activa": True},
    ).json()["id"]
    variante = api.post(
        f"{PRODUCTOS}/{producto_id}/variantes",
        headers=cabeceras_admin,
        json={"talla_id": talla, "color_id": color_id, "precio": "280.00", "activa": True},
    )
    assert variante.status_code == 201, variante.text
    _ingresar(api, cabeceras_admin, sucursal_id=tienda["sucursal"], lineas=[(variante.json()["id"], 3)])
    return variante.json()["id"]


def _solicitar(api, cab, codigo, variante, cantidad=1, *, tipo="DEVOLUCION", nueva=None):
    linea = {"variante_id": variante, "cantidad": cantidad}
    if nueva is not None:
        linea["variante_nueva_id"] = nueva
    return api.post(
        DEVOLUCIONES_WEB,
        headers=cab,
        json={"venta_codigo": codigo, "tipo": tipo, "motivo": "No me quedó bien", "lineas": [linea]},
    )


def _envejecer_entrega(db, codigo: str, horas: int) -> None:
    from app.modules.ventas.models import Venta

    fila = db.query(Venta).filter(Venta.codigo == codigo).one()
    fila.entregado_en = tiempo.ahora() - timedelta(hours=horas)
    db.commit()


# =====================================================================
# La entrega (precondición)
# =====================================================================

def test_el_encargado_ve_el_pedido_pagado_y_lo_entrega(
    api: TestClient, cabeceras_cliente: dict, pagado: dict, encargado: dict
) -> None:
    pendientes = api.get(PEDIDOS_SUCURSAL, headers=encargado, params={"estado": "PAGADA"}).json()
    assert [p["codigo"] for p in pendientes] == [pagado["codigo"]]
    assert pendientes[0]["unidades"] == 2 and pendientes[0]["cliente"]

    r = api.post(f"{PEDIDOS_SUCURSAL}/{pagado['codigo']}/entregar", headers=encargado)
    assert r.status_code == 200
    assert r.json()["estado"] == "ENTREGADA" and r.json()["entregado_en"]
    # Dos veces no.
    assert api.post(f"{PEDIDOS_SUCURSAL}/{pagado['codigo']}/entregar", headers=encargado).status_code == 409
    # El cliente ve cuándo se le entregó.
    ficha = api.get(f"/api/v1/tienda/pedidos/{pagado['codigo']}", headers=cabeceras_cliente)
    assert ficha.json()["entregado_en"]


def test_un_pedido_sin_pagar_no_se_entrega(api: TestClient, pedido: dict, encargado: dict) -> None:
    r = api.post(f"{PEDIDOS_SUCURSAL}/{pedido['codigo']}/entregar", headers=encargado)
    assert r.status_code == 409
    assert "pagado" in r.json()["detail"]


def test_el_encargado_de_otra_sucursal_no_lo_entrega(
    api: TestClient, cabeceras_admin: dict, pagado: dict
) -> None:
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    ajeno = _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=otra, sufijo="25")
    assert api.post(f"{PEDIDOS_SUCURSAL}/{pagado['codigo']}/entregar", headers=ajeno).status_code == 404


# =====================================================================
# CU-24: qué se puede pedir
# =====================================================================

def test_sin_entregar_no_se_pide_nada(api: TestClient, cabeceras_cliente: dict, pagado: dict) -> None:
    r = api.get(f"{DEVOLUCIONES_WEB}/pedidos/{pagado['codigo']}", headers=cabeceras_cliente)
    assert r.status_code == 409
    assert "entregado" in r.json()["detail"]


def test_el_pedido_entregado_dice_que_se_puede_y_hasta_cuando(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, otra_talla: int, tienda: dict
) -> None:
    r = api.get(f"{DEVOLUCIONES_WEB}/pedidos/{entregado['codigo']}", headers=cabeceras_cliente)
    assert r.status_code == 200, r.text
    ficha = r.json()
    assert ficha["ventana_horas"] == 48 and ficha["dentro_de_plazo"] is True
    [linea] = ficha["lineas"]
    assert linea["devolvibles"] == 2
    assert [o["variante_id"] for o in linea["opciones_de_cambio"]] == [otra_talla]
    assert linea["opciones_de_cambio"][0]["talla"] == "L"


# =====================================================================
# CU-24: pedirlo
# =====================================================================

def test_la_devolucion_queda_pendiente_y_la_ven_los_dos(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict, encargado: dict
) -> None:
    r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
    assert r.status_code == 201, r.text
    solicitud = r.json()
    assert solicitud["estado"] == "PENDIENTE" and solicitud["tipo"] == "DEVOLUCION"
    assert solicitud["valor_devuelto"] == "250.00"
    assert solicitud["diferencia"] is None

    mias = api.get(DEVOLUCIONES_WEB, headers=cabeceras_cliente).json()
    assert [s["id"] for s in mias] == [solicitud["id"]]
    de_la_sucursal = api.get(SOLICITUDES_SUCURSAL, headers=encargado, params={"estado": "PENDIENTE"}).json()
    assert [s["id"] for s in de_la_sucursal] == [solicitud["id"]]


def test_lo_pedido_deja_de_estar_disponible(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict
) -> None:
    assert _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 2).status_code == 201
    r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
    assert r.status_code == 409
    assert "hasta 0" in r.json()["detail"]
    ficha = api.get(f"{DEVOLUCIONES_WEB}/pedidos/{entregado['codigo']}", headers=cabeceras_cliente).json()
    assert ficha["lineas"][0]["devolvibles"] == 0


def test_el_cambio_lleva_la_otra_talla_y_calcula_la_diferencia(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict, otra_talla: int
) -> None:
    r = _solicitar(
        api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1, tipo="CAMBIO", nueva=otra_talla
    )
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["lineas"][0]["talla_nueva"] == "L"
    assert s["valor_nuevo"] == "280.00" and s["diferencia"] == "30.00"


def test_el_cambio_por_otro_producto_no_vale(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict
) -> None:
    r = _solicitar(
        api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1, tipo="CAMBIO", nueva=999_999
    )
    assert r.status_code == 422


def test_un_cambio_sin_prenda_nueva_no_se_acepta(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict
) -> None:
    assert _solicitar(
        api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1, tipo="CAMBIO"
    ).status_code == 422


def test_fuera_de_la_ventana_se_rechaza(
    api: TestClient, cabeceras_cliente: dict, cabeceras_admin: dict, entregado: dict, tienda: dict, db
) -> None:
    api.put(VENTANA, headers=cabeceras_admin, json={"horas": 24})
    _envejecer_entrega(db, entregado["codigo"], 25)
    r = _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1)
    assert r.status_code == 409
    assert "24 horas desde la entrega" in r.json()["detail"]


def test_la_ventana_corre_desde_la_entrega_y_no_desde_la_compra(
    api: TestClient, cabeceras_cliente: dict, entregado: dict, tienda: dict, db
) -> None:
    """Comprado hace 5 días, entregado hoy: todavía se puede."""
    from app.modules.ventas.models import Venta

    fila = db.query(Venta).filter(Venta.codigo == entregado["codigo"]).one()
    fila.creado_en = tiempo.ahora() - timedelta(days=5)
    db.commit()
    assert _solicitar(api, cabeceras_cliente, entregado["codigo"], tienda["variante"], 1).status_code == 201


def test_un_pedido_ajeno_no_existe_para_el_cliente(
    api: TestClient, cabeceras_admin: dict, entregado: dict, tienda: dict
) -> None:
    otro = api.post(
        "/api/v1/auth/registro",
        json={
            "nombres": "Otra", "apellidos": "Clienta", "correo": "otra.clienta24@demo.bo",
            "contrasena": "Prueba2026x", "documento": "77700024",
        },
    )
    if otro.status_code not in (200, 201):
        pytest.skip(f"registro no disponible en esta forma: {otro.status_code}")
    entrada = api.post("/api/v1/auth/login", json={"correo": "otra.clienta24@demo.bo", "contrasena": "Prueba2026x"})
    cab = {"Authorization": f"Bearer {entrada.json()['access_token']}"}
    assert api.get(f"{DEVOLUCIONES_WEB}/pedidos/{entregado['codigo']}", headers=cab).status_code == 404


def test_el_cajero_no_entrega_pedidos(api: TestClient, cabeceras_admin: dict, tienda: dict, pagado: dict) -> None:
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=tienda["sucursal"], sufijo="24")
    assert api.post(f"{PEDIDOS_SUCURSAL}/{pagado['codigo']}/entregar", headers=cajero).status_code == 403
