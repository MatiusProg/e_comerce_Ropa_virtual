"""CU-13 a CU-19 · Trabajar sin conexión y sincronizar.

Lo que más importa cubrir
-------------------------
- **Idempotencia (RNF05).** La misma operación enviada dos veces no vende dos
  veces: la segunda devuelve lo que se decidió la primera.
- **Gana el que llega primero al servidor (RN-06).** Si el stock ya no
  alcanza, la venta offline se rechaza con el motivo, no deja nada a medias,
  y si se cobró queda para devolver (CU-19).
- **Una rechazada no deshace a las confirmadas del mismo lote.**
- **El ámbito no se acepta del cuerpo:** el turno tiene que ser de quien vende.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from tests.test_cu31_venta_presencial import (
    PRECIO,
    VENTAS,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _crear_variantes,
    _disponible,
    _empleado,
    _ingresar,
    _manana,
)

PAQUETE = "/api/v1/offline/paquete"
PAQUETE_CLIENTE = "/api/v1/offline/paquete-cliente"
SINCRONIZAR = "/api/v1/offline/sincronizar"
MIAS = "/api/v1/offline/operaciones/mias"
OPERACIONES = "/api/v1/offline/operaciones"


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict, sucursal: int) -> list[int]:
    ids = _crear_variantes(api, cabeceras_admin)
    # 10 de la primera y 2 de la segunda.
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(ids[0], 10), (ids[1], 2)])
    return ids


@pytest.fixture
def cajero(api: TestClient, cabeceras_admin: dict, sucursal: int, db) -> dict:
    cab = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="7")
    turno_id = _abrir_turno(api, cab, _caja(db, sucursal))
    return {"cab": cab, "turno_id": turno_id}


@pytest.fixture
def encargado(api: TestClient, cabeceras_admin: dict, sucursal: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=sucursal, sufijo="7")


def _venta(turno_id: int, variante_id: int, cantidad: int = 1, **pago) -> dict:
    total = PRECIO * cantidad
    return {
        "uuid": str(uuid.uuid4()),
        "tipo": "VENTA",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "turno_caja_id": turno_id,
        "lineas": [
            {"variante_id": variante_id, "cantidad": cantidad, "precio_unitario": str(PRECIO)}
        ],
        "pago": {"metodo": "EFECTIVO", "monto": str(total), **pago},
    }


def _sincronizar(api: TestClient, cab: dict, *operaciones: dict):
    return api.post(
        SINCRONIZAR, headers=cab, json={"dispositivo": "pruebas", "operaciones": list(operaciones)}
    )


# =====================================================================
# CU-13 Preparar el dispositivo
# =====================================================================

def test_sin_turno_no_se_prepara_el_mostrador(
    api: TestClient, cabeceras_admin: dict, sucursal: int
) -> None:
    cab = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="8")
    r = api.get(PAQUETE, headers=cab)
    assert r.status_code == 409
    assert "turno" in r.json()["detail"]


def test_el_paquete_trae_prendas_turno_y_vigencia(
    api: TestClient, cajero: dict, variantes: list[int], sucursal: int
) -> None:
    r = api.get(PAQUETE, headers=cajero["cab"])
    assert r.status_code == 200, r.text
    paquete = r.json()
    assert paquete["turno_caja_id"] == cajero["turno_id"]
    assert paquete["sucursal"]["id"] == sucursal
    assert {p["variante_id"]: p["disponible"] for p in paquete["prendas"]} == {
        variantes[0]: 10,
        variantes[1]: 2,
    }
    assert paquete["vigente_hasta"] > paquete["generado_en"]


def test_el_cliente_descarga_sucursales_y_saldos(
    api: TestClient, cabeceras_cliente: dict, variantes: list[int], sucursal: int
) -> None:
    r = api.get(PAQUETE_CLIENTE, headers=cabeceras_cliente)
    assert r.status_code == 200, r.text
    paquete = r.json()
    assert [s["id"] for s in paquete["sucursales"]] == [sucursal]
    prenda = next(p for p in paquete["prendas"] if p["variante_id"] == variantes[0])
    assert prenda["sucursales"] == [{"sucursal_id": sucursal, "disponible": 10}]


# =====================================================================
# CU-14 + CU-16 + CU-17: la venta offline
# =====================================================================

def test_venta_offline_confirmada_descuenta_y_queda_en_el_turno(
    api: TestClient, cajero: dict, variantes: list[int], sucursal: int, cabeceras_admin: dict
) -> None:
    op = _venta(cajero["turno_id"], variantes[0], cantidad=3)
    r = _sincronizar(api, cajero["cab"], op)
    assert r.status_code == 200, r.text
    [resultado] = r.json()["resultados"]
    assert resultado["estado"] == "CONFIRMADA"
    assert resultado["venta_codigo"].startswith("VP-")
    assert resultado["repetida"] is False
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 7

    venta = api.get(f"{VENTAS}/{resultado['venta_codigo']}", headers=cajero["cab"]).json()
    assert venta["estado"] == "PAGADA"
    assert venta["metodo_pago"] == "EFECTIVO"


def test_la_misma_operacion_dos_veces_no_vende_dos_veces(
    api: TestClient, cajero: dict, variantes: list[int], sucursal: int, cabeceras_admin: dict
) -> None:
    op = _venta(cajero["turno_id"], variantes[0], cantidad=2)
    primera = _sincronizar(api, cajero["cab"], op).json()["resultados"][0]
    segunda = _sincronizar(api, cajero["cab"], op).json()["resultados"][0]

    assert segunda["repetida"] is True
    assert segunda["venta_codigo"] == primera["venta_codigo"]
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 8

    [registrada] = api.get(MIAS, headers=cajero["cab"]).json()
    assert registrada["intentos"] == 2


def test_si_otra_venta_llego_primero_la_offline_se_rechaza_para_devolver(
    api: TestClient, cajero: dict, variantes: list[int], sucursal: int, cabeceras_admin: dict
) -> None:
    # En línea se venden 2 de las 2 que había.
    en_linea = api.post(
        VENTAS,
        headers=cajero["cab"],
        json={"metodo_pago": "EFECTIVO", "lineas": [{"variante_id": variantes[1], "cantidad": 2}]},
    )
    assert en_linea.status_code == 201, en_linea.text

    op = _venta(cajero["turno_id"], variantes[1], cantidad=1)
    [resultado] = _sincronizar(api, cajero["cab"], op).json()["resultados"]
    assert resultado["estado"] == "RECHAZADA"
    assert "llegó primero" in resultado["motivo"]
    assert resultado["venta_codigo"] is None
    assert resultado["requiere_devolucion"] is True
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1]) == 0


def test_una_rechazada_no_deshace_las_confirmadas_del_lote(
    api: TestClient, cajero: dict, variantes: list[int], sucursal: int, cabeceras_admin: dict
) -> None:
    buena = _venta(cajero["turno_id"], variantes[0], cantidad=1)
    sin_stock = _venta(cajero["turno_id"], variantes[1], cantidad=5)
    otra_buena = _venta(cajero["turno_id"], variantes[0], cantidad=1)
    cuerpo = _sincronizar(api, cajero["cab"], buena, sin_stock, otra_buena).json()
    assert [r["estado"] for r in cuerpo["resultados"]] == ["CONFIRMADA", "RECHAZADA", "CONFIRMADA"]
    assert (cuerpo["confirmadas"], cuerpo["rechazadas"]) == (2, 1)
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 8
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1]) == 2


def test_un_turno_ajeno_se_rechaza(
    api: TestClient, cajero: dict, variantes: list[int], cabeceras_admin: dict, sucursal: int
) -> None:
    otro = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="9")
    op = _venta(cajero["turno_id"], variantes[0])
    [resultado] = _sincronizar(api, otro, op).json()["resultados"]
    assert resultado["estado"] == "RECHAZADA"
    assert "turno" in resultado["motivo"]


def test_qr_sin_referencia_no_se_acepta(api: TestClient, cajero: dict, variantes: list[int]) -> None:
    op = _venta(cajero["turno_id"], variantes[0], metodo="QR")
    assert _sincronizar(api, cajero["cab"], op).status_code == 422


def test_un_cliente_no_sincroniza_ventas(
    api: TestClient, cabeceras_cliente: dict, cajero: dict, variantes: list[int]
) -> None:
    op = _venta(cajero["turno_id"], variantes[0])
    assert _sincronizar(api, cabeceras_cliente, op).status_code == 403


# =====================================================================
# CU-15: la reserva offline
# =====================================================================

def test_reserva_offline_del_cliente_aparta_el_stock(
    api: TestClient, cabeceras_cliente: dict, variantes: list[int], sucursal: int,
    cabeceras_admin: dict,
) -> None:
    op = {
        "uuid": str(uuid.uuid4()),
        "tipo": "RESERVA",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "sucursal_id": sucursal,
        "franja_inicio": _manana(15).isoformat(),
        "franja_fin": _manana(16).isoformat(),
        "lineas": [{"variante_id": variantes[0], "cantidad": 2, "precio_unitario": str(PRECIO)}],
    }
    [resultado] = _sincronizar(api, cabeceras_cliente, op).json()["resultados"]
    assert resultado["estado"] == "CONFIRMADA", resultado
    assert resultado["reserva_id"] is not None
    assert resultado["requiere_devolucion"] is False
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 8


def test_reserva_offline_fuera_de_horario_se_rechaza_con_el_motivo(
    api: TestClient, cabeceras_cliente: dict, variantes: list[int], sucursal: int
) -> None:
    op = {
        "uuid": str(uuid.uuid4()),
        "tipo": "RESERVA",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "sucursal_id": sucursal,
        "franja_inicio": _manana(6).isoformat(),
        "franja_fin": _manana(7).isoformat(),
        "lineas": [{"variante_id": variantes[0], "cantidad": 1, "precio_unitario": str(PRECIO)}],
        "pago": {"metodo": "QR", "monto": "50.00", "referencia": "BNB-123"},
    }
    [resultado] = _sincronizar(api, cabeceras_cliente, op).json()["resultados"]
    assert resultado["estado"] == "RECHAZADA"
    assert "atiende" in resultado["motivo"]
    assert resultado["requiere_devolucion"] is True


# =====================================================================
# CU-19: atender las rechazadas y devolver el dinero
# =====================================================================

def test_el_encargado_registra_la_devolucion_una_sola_vez(
    api: TestClient, cajero: dict, encargado: dict, variantes: list[int]
) -> None:
    op = _venta(cajero["turno_id"], variantes[1], cantidad=5)
    _sincronizar(api, cajero["cab"], op)

    pendientes = api.get(OPERACIONES, headers=encargado, params={"por_devolver": True}).json()
    assert [p["uuid"] for p in pendientes] == [op["uuid"]]

    url = f"{OPERACIONES}/{op['uuid']}/devolucion"
    r = api.post(url, headers=encargado, json={"metodo": "EFECTIVO", "observacion": "Se le devolvió"})
    assert r.status_code == 200, r.text
    assert r.json()["devuelta"] is True
    assert r.json()["requiere_devolucion"] is False

    assert api.post(url, headers=encargado, json={"metodo": "EFECTIVO"}).status_code == 409
    assert api.get(OPERACIONES, headers=encargado, params={"por_devolver": True}).json() == []


def test_una_confirmada_no_se_devuelve(
    api: TestClient, cajero: dict, encargado: dict, variantes: list[int]
) -> None:
    op = _venta(cajero["turno_id"], variantes[0])
    _sincronizar(api, cajero["cab"], op)
    r = api.post(f"{OPERACIONES}/{op['uuid']}/devolucion", headers=encargado, json={"metodo": "EFECTIVO"})
    assert r.status_code == 409


def test_el_cajero_no_atiende_devoluciones(api: TestClient, cajero: dict) -> None:
    assert api.get(OPERACIONES, headers=cajero["cab"]).status_code == 403
