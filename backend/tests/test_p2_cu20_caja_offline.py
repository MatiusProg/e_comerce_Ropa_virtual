"""CU-20 · Abrir y cerrar caja con ventas offline.

Lo que más importa cubrir
-------------------------
- **Una venta offline confirmada entra al arqueo como cualquier otra**, y el
  turno la muestra aparte.
- **Una rechazada que se cobró en efectivo sigue en el cajón.** No dejó venta,
  pero el billete está: el esperado lo suma hasta que el encargado se lo
  devuelve al cliente en efectivo. Sin eso el turno cerraría con sobrante.
- **Devolverla por QR no saca el billete del cajón.**
"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from tests.test_cu31_venta_presencial import PRECIO
from tests.test_p2_cu17_sincronizacion import (  # noqa: F401  (fixtures)
    OPERACIONES,
    _sincronizar,
    _venta,
    cajero,
    encargado,
    sucursal,
    variantes,
)

MIO = "/api/v1/caja/turnos/mio"
APERTURA = Decimal("100.00")


def _turno(api: TestClient, cajero: dict) -> dict:
    r = api.get(MIO, headers=cajero["cab"])
    assert r.status_code == 200, r.text
    return r.json()


def test_la_venta_offline_confirmada_entra_al_arqueo_y_se_ve_aparte(
    api: TestClient, cajero: dict, variantes: list[int]
) -> None:
    [r] = _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0], 2)).json()[
        "resultados"
    ]
    assert r["estado"] == "CONFIRMADA"

    turno = _turno(api, cajero)
    assert turno["ventas_offline"] == 1
    assert Decimal(turno["ventas_offline_total"]) == PRECIO * 2
    assert Decimal(turno["efectivo_cobrado"]) == PRECIO * 2
    assert Decimal(turno["por_devolver"]) == 0
    assert Decimal(turno["monto_esperado"]) == APERTURA + PRECIO * 2


def test_la_rechazada_cobrada_en_efectivo_sigue_en_el_cajon(
    api: TestClient, cajero: dict, variantes: list[int]
) -> None:
    # Solo hay 2 de la segunda: pedir 5 se rechaza, pero se cobró igual.
    [r] = _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[1], 5)).json()[
        "resultados"
    ]
    assert r["estado"] == "RECHAZADA"

    turno = _turno(api, cajero)
    assert turno["ventas_offline"] == 0
    assert Decimal(turno["efectivo_cobrado"]) == 0
    assert turno["por_devolver_cantidad"] == 1
    assert Decimal(turno["por_devolver"]) == PRECIO * 5
    assert Decimal(turno["monto_esperado"]) == APERTURA + PRECIO * 5


def test_devuelta_en_efectivo_sale_del_cajon(
    api: TestClient, cajero: dict, encargado: dict, variantes: list[int]
) -> None:
    op = _venta(cajero["turno_id"], variantes[1], 5)
    _sincronizar(api, cajero["cab"], op)
    r = api.post(f"{OPERACIONES}/{op['uuid']}/devolucion", headers=encargado,
                 json={"metodo": "EFECTIVO"})
    assert r.status_code == 200, r.text

    turno = _turno(api, cajero)
    assert Decimal(turno["por_devolver"]) == 0
    assert Decimal(turno["monto_esperado"]) == APERTURA


def test_devuelta_por_qr_el_billete_se_queda(
    api: TestClient, cajero: dict, encargado: dict, variantes: list[int]
) -> None:
    op = _venta(cajero["turno_id"], variantes[1], 5)
    _sincronizar(api, cajero["cab"], op)
    r = api.post(f"{OPERACIONES}/{op['uuid']}/devolucion", headers=encargado,
                 json={"metodo": "QR", "referencia": "BNB-77"})
    assert r.status_code == 200, r.text

    assert Decimal(_turno(api, cajero)["por_devolver"]) == PRECIO * 5


def test_al_cerrar_el_esperado_incluye_lo_por_devolver(
    api: TestClient, cajero: dict, variantes: list[int]
) -> None:
    _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[1], 5))
    contado = APERTURA + PRECIO * 5
    r = api.post(f"/api/v1/caja/turnos/{cajero['turno_id']}/cierre", headers=cajero["cab"],
                 json={"monto_cierre": str(contado)})
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["diferencia"]) == 0
