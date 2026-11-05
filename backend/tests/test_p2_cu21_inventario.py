"""CU-21 · Gestionar el inventario de la sucursal (2do parcial).

Lo que CU-21 suma a los ingresos y ajustes del 1er parcial (RF-52 y RF-53):
- **Kardex**: todos los movimientos de una prenda en una sucursal con el saldo
  que dejó cada uno, y el saldo final cuadra con la existencia.
- **Ingreso y conteo sin conexión**, por la misma sincronización de CU-17.
- **El conteo offline aplica la diferencia, no lo contado** (decisión del
  03/11): las ventas que llegaron en el medio no se pisan.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from tests.test_cu31_venta_presencial import (
    PRECIO,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _crear_variantes,
    _disponible,
    _empleado,
    _ingresar,
)

KARDEX = "/api/v1/inventario/kardex"
PAQUETE_INVENTARIO = "/api/v1/offline/paquete-inventario"
SINCRONIZAR = "/api/v1/offline/sincronizar"
PROVEEDORES = "/api/v1/organizacion/proveedores"


@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict, sucursal: int) -> list[int]:
    ids = _crear_variantes(api, cabeceras_admin)
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(ids[0], 10)])
    return ids


@pytest.fixture
def encargado(api: TestClient, cabeceras_admin: dict, sucursal: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=sucursal, sufijo="21")


@pytest.fixture
def proveedor(api: TestClient, cabeceras_admin: dict, variantes: list[int]) -> int:
    # `_ingresar` ya creó uno.
    return api.get(PROVEEDORES, headers=cabeceras_admin).json()[0]["id"]


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ingreso(proveedor_id: int, *lineas: tuple[int, int]) -> dict:
    return {
        "uuid": str(uuid.uuid4()),
        "tipo": "INGRESO",
        "creada_en": _ahora(),
        "ingreso": {
            "proveedor_id": proveedor_id,
            "referencia": "REM-OFF-1",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    }


def _conteo(variante_id: int, *, visto: int, contado: int) -> dict:
    return {
        "uuid": str(uuid.uuid4()),
        "tipo": "AJUSTE",
        "creada_en": _ahora(),
        "conteo": {
            "variante_id": variante_id,
            "saldo_visto": visto,
            "cantidad_contada": contado,
            "motivo": "Conteo de fin de semana",
        },
    }


def _sincronizar(api: TestClient, cab: dict, *operaciones: dict):
    return api.post(
        SINCRONIZAR, headers=cab, json={"dispositivo": "pruebas", "operaciones": list(operaciones)}
    )


# =====================================================================
# Kardex (RF-53)
# =====================================================================

def test_el_kardex_trae_el_saldo_de_cada_movimiento(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int], sucursal: int
) -> None:
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variantes[0], 5)])
    r = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[0]})
    assert r.status_code == 200, r.text
    kardex = r.json()
    assert kardex["sucursal_id"] == sucursal
    assert kardex["disponible"] == 15
    # Del más reciente al más viejo; el primero deja el saldo actual.
    assert [(m["cantidad"], m["saldo"]) for m in kardex["items"]] == [(5, 15), (10, 10)]
    assert kardex["items"][0]["saldo"] == kardex["disponible"]
    assert kardex["items"][0]["sin_conexion"] is False
    assert kardex["items"][0]["proveedor"]


def test_el_saldo_no_se_reinicia_en_la_segunda_pagina(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int], sucursal: int
) -> None:
    for _ in range(3):
        _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variantes[0], 1)])
    r = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[0], "tamano": 2, "pagina": 2})
    kardex = r.json()
    assert kardex["total"] == 4
    assert [m["saldo"] for m in kardex["items"]] == [11, 10]


def test_el_administrador_tiene_que_decir_la_sucursal(
    api: TestClient, cabeceras_admin: dict, variantes: list[int], sucursal: int
) -> None:
    assert api.get(KARDEX, headers=cabeceras_admin, params={"variante_id": variantes[0]}).status_code == 422
    r = api.get(
        KARDEX, headers=cabeceras_admin, params={"variante_id": variantes[0], "sucursal_id": sucursal}
    )
    assert r.status_code == 200
    assert r.json()["disponible"] == 10


def test_el_encargado_no_ve_el_kardex_de_otra_sucursal(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int]
) -> None:
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    r = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[0], "sucursal_id": otra})
    assert r.status_code == 403


def test_una_prenda_sin_movimientos_da_un_kardex_vacio(
    api: TestClient, encargado: dict, variantes: list[int]
) -> None:
    r = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[1]})
    assert r.status_code == 200
    assert r.json()["items"] == [] and r.json()["disponible"] == 0


# =====================================================================
# Preparar el dispositivo para el inventario
# =====================================================================

def test_el_paquete_trae_todas_las_prendas_y_los_proveedores(
    api: TestClient, encargado: dict, variantes: list[int], proveedor: int, sucursal: int
) -> None:
    r = api.get(PAQUETE_INVENTARIO, headers=encargado)
    assert r.status_code == 200, r.text
    paquete = r.json()
    assert paquete["sucursal"]["id"] == sucursal
    saldos = {p["variante_id"]: p["disponible"] for p in paquete["prendas"]}
    # También la que todavía no tiene saldo acá.
    assert saldos[variantes[0]] == 10 and saldos[variantes[1]] == 0
    assert [p["id"] for p in paquete["proveedores"]] == [proveedor]


def test_el_cajero_no_descarga_el_paquete_de_inventario(
    api: TestClient, cabeceras_admin: dict, sucursal: int
) -> None:
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="21")
    assert api.get(PAQUETE_INVENTARIO, headers=cajero).status_code == 403


# =====================================================================
# Ingreso sin conexión
# =====================================================================

def test_el_ingreso_offline_sube_el_saldo_y_queda_marcado(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int],
    proveedor: int, sucursal: int,
) -> None:
    r = _sincronizar(api, encargado, _ingreso(proveedor, (variantes[0], 4), (variantes[1], 3)))
    assert r.status_code == 200, r.text
    resultado = r.json()["resultados"][0]
    assert resultado["estado"] == "CONFIRMADA"
    assert resultado["unidades"] == 7
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 14
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1]) == 3

    kardex = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[0]}).json()
    assert kardex["items"][0]["sin_conexion"] is True
    assert kardex["items"][0]["referencia"] == "REM-OFF-1"


def test_el_ingreso_offline_repetido_no_suma_dos_veces(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int],
    proveedor: int, sucursal: int,
) -> None:
    op = _ingreso(proveedor, (variantes[0], 4))
    _sincronizar(api, encargado, op)
    r = _sincronizar(api, encargado, op)
    assert r.json()["resultados"][0]["repetida"] is True
    assert r.json()["resultados"][0]["unidades"] == 4
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 14


def test_un_proveedor_inactivo_rechaza_el_ingreso_sin_cargar_nada(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int],
    proveedor: int, sucursal: int,
) -> None:
    r = api.patch(f"{PROVEEDORES}/{proveedor}/estado", headers=cabeceras_admin, json={"activo": False})
    assert r.status_code == 200, r.text
    resultado = _sincronizar(api, encargado, _ingreso(proveedor, (variantes[0], 4))).json()["resultados"][0]
    assert resultado["estado"] == "RECHAZADA"
    assert resultado["motivo"]
    assert resultado["unidades"] is None
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 10


def test_el_cajero_no_registra_inventario_sin_conexion(
    api: TestClient, cabeceras_admin: dict, variantes: list[int], proveedor: int, sucursal: int
) -> None:
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="22")
    resultado = _sincronizar(api, cajero, _ingreso(proveedor, (variantes[0], 4))).json()["resultados"][0]
    assert resultado["estado"] == "RECHAZADA"
    assert "encargado" in resultado["motivo"]


def test_el_cliente_no_manda_inventario(
    api: TestClient, cabeceras_cliente: dict, variantes: list[int], proveedor: int
) -> None:
    r = _sincronizar(api, cabeceras_cliente, _ingreso(proveedor, (variantes[0], 4)))
    assert r.status_code == 403


# =====================================================================
# Conteo sin conexión: se aplica la diferencia
# =====================================================================

def test_el_conteo_offline_aplica_la_diferencia_y_respeta_las_ventas_del_medio(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int], sucursal: int, db
) -> None:
    """El encargado cuenta 8 sin red cuando había 10. DESPUÉS del conteo, en
    línea, se venden 3. Al sincronizar quedan 10 - 2 - 3 = 5, no 8."""
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="23")
    turno_id = _abrir_turno(api, cajero, _caja(db, sucursal))
    conteo = _conteo(variantes[0], visto=10, contado=8)  # se cuenta primero
    venta = _sincronizar(
        api,
        cajero,
        {
            "uuid": str(uuid.uuid4()),
            "tipo": "VENTA",
            "creada_en": _ahora(),
            "turno_caja_id": turno_id,
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 3, "precio_unitario": str(PRECIO)}
            ],
            "pago": {"metodo": "EFECTIVO", "monto": str(PRECIO * 3)},
        },
    )
    assert venta.json()["resultados"][0]["estado"] == "CONFIRMADA", venta.text

    r = _sincronizar(api, encargado, conteo)
    resultado = r.json()["resultados"][0]
    assert resultado["estado"] == "CONFIRMADA", resultado
    assert resultado["unidades"] == -2
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 5

    movimiento = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[0]}).json()["items"][0]
    assert movimiento["tipo"] == "AJUSTE" and movimiento["sin_conexion"] is True
    assert "había 10" in movimiento["motivo"]


def test_el_conteo_offline_no_descuenta_dos_veces_lo_vendido_antes_de_contar(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int], sucursal: int, db
) -> None:
    """Auditoría del 05/11. El paquete dice 10. ANTES del conteo se venden 3 en
    línea, así que en la percha hay 7 y el encargado cuenta 7. El saldo del
    paquete (10) está viejo: con él se restaban 3 de nuevo y quedaban 4."""
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="29")
    turno_id = _abrir_turno(api, cajero, _caja(db, sucursal))
    venta = _sincronizar(
        api,
        cajero,
        {
            "uuid": str(uuid.uuid4()),
            "tipo": "VENTA",
            "creada_en": _ahora(),
            "turno_caja_id": turno_id,
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 3, "precio_unitario": str(PRECIO)}
            ],
            "pago": {"metodo": "EFECTIVO", "monto": str(PRECIO * 3)},
        },
    )
    assert venta.json()["resultados"][0]["estado"] == "CONFIRMADA", venta.text

    r = _sincronizar(api, encargado, _conteo(variantes[0], visto=10, contado=7))
    resultado = r.json()["resultados"][0]
    assert resultado["estado"] == "CONFIRMADA", resultado
    assert resultado["unidades"] == 0
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 7


def test_un_conteo_igual_a_lo_visto_se_confirma_sin_movimiento(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int], sucursal: int
) -> None:
    resultado = _sincronizar(api, encargado, _conteo(variantes[0], visto=10, contado=10)).json()["resultados"][0]
    assert resultado["estado"] == "CONFIRMADA"
    assert resultado["unidades"] == 0
    kardex = api.get(KARDEX, headers=encargado, params={"variante_id": variantes[0]}).json()
    assert kardex["total"] == 1


def test_el_conteo_se_mide_contra_la_percha_y_no_contra_el_saldo_del_paquete(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int], sucursal: int
) -> None:
    """Un `saldo_visto` viejo (30) no cambia nada: había 10 y se contaron 5."""
    resultado = _sincronizar(api, encargado, _conteo(variantes[0], visto=30, contado=5)).json()["resultados"][0]
    assert resultado["estado"] == "CONFIRMADA"
    assert resultado["unidades"] == -5
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 5


def test_un_conteo_rechazado_no_deshace_el_ingreso_del_mismo_lote(
    api: TestClient, cabeceras_admin: dict, encargado: dict, variantes: list[int],
    proveedor: int, sucursal: int,
) -> None:
    r = _sincronizar(
        api,
        encargado,
        _ingreso(proveedor, (variantes[0], 2)),
        # Una prenda que no existe: el conteo se rechaza.
        _conteo(999_999, visto=0, contado=1),
    )
    assert [x["estado"] for x in r.json()["resultados"]] == ["CONFIRMADA", "RECHAZADA"]
    assert _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]) == 12


def test_un_movimiento_de_inventario_no_lleva_pago() -> None:
    from pydantic import ValidationError

    from app.modules.offline.schemas import OperacionOfflineIn

    op = _conteo(1, visto=1, contado=1)
    op["pago"] = {"metodo": "EFECTIVO", "monto": "10"}
    with pytest.raises(ValidationError):
        OperacionOfflineIn.model_validate(op)
