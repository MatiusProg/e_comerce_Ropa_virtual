"""CU-32 · Registrar devolución.

La prenda vuelve al inventario de la sucursal y, **si se había pagado en
efectivo**, la plata sale del cajón.

Lo que más importa cubrir
-------------------------
- **El arqueo tiene que seguir cerrando.** `devolucion.monto` es lo que sale
  del cajón, no lo que vale la prenda: CU-30 lo resta del esperado del turno.
  Si una devolución de una venta con tarjeta sumara ahí, el turno cerraría con
  un faltante de plata que nunca entró —y un arqueo que siempre descuadra
  enseña a ignorarlo—.
- **La prenda vuelve al inventario igual, se haya pagado como se haya pagado.**
  Lo que volvió al local está en el local; eso no depende del medio de pago.
- **No se puede devolver dos veces lo mismo.** No hay restricción en la base
  que lo impida —dos devoluciones parciales de una venta son legítimas—, así
  que la cuenta la hace el servicio contra lo ya devuelto.
- **La venta no se edita.** Una devolución es un hecho nuevo, no una
  corrección: si se editara la venta, el reporte de rotación y el ticket
  promedio de CU-36 cambiarían solos, hacia atrás.

Los ayudantes se importan de las pruebas de CU-31 en vez de copiarse: son el
mismo montaje —sucursal, cajero, caja, turno, stock— y dos copias que empiezan
a divergir harían que una de las dos dejara de probar lo que dice probar.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.test_cu31_venta_presencial import (  # noqa: F401 - fixtures de pytest
    PRECIO,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _disponible,
    _empleado,
    cajero,
    mostrador,
    stock,
    sucursal,
    variantes,
)

DEVOLUCIONES = "/api/v1/pos/devoluciones"
VENTAS = "/api/v1/pos/ventas"
CAJA_MIO = "/api/v1/caja/turnos/mio"


def _vender(
    api: TestClient, cab: dict, variante_id: int, cantidad: int, metodo: str = "EFECTIVO"
) -> str:
    r = api.post(
        VENTAS,
        headers=cab,
        json={
            "metodo_pago": metodo,
            "lineas": [{"variante_id": variante_id, "cantidad": cantidad}],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["codigo"]


def _devolver(
    api: TestClient,
    cab: dict,
    codigo: str,
    variante_id: int,
    cantidad: int,
    motivo: str = "No le quedó bien",
):
    return api.post(
        DEVOLUCIONES,
        headers=cab,
        json={
            "venta_codigo": codigo,
            "motivo": motivo,
            "lineas": [{"variante_id": variante_id, "cantidad": cantidad}],
        },
    )


# =====================================================================
# Autorización y ámbito
# =====================================================================

def test_sin_token_no_se_devuelve_nada(api: TestClient) -> None:
    assert api.get(f"{DEVOLUCIONES}/ventas/VP-1").status_code == 401
    assert api.post(DEVOLUCIONES, json={}).status_code == 401


def test_un_cliente_no_registra_devoluciones(
    api: TestClient, cabeceras_cliente: dict
) -> None:
    assert api.get(f"{DEVOLUCIONES}/ventas/VP-1", headers=cabeceras_cliente).status_code == 403


def test_sin_turno_abierto_no_se_devuelve(
    api: TestClient, cajero: dict, stock
) -> None:
    """La devolución sale de un cajón y cuelga de un turno, igual que la venta."""
    r = api.get(f"{DEVOLUCIONES}/ventas/VP-20260920-AAAA", headers=cajero)
    assert r.status_code == 409


# =====================================================================
# Qué se puede devolver
# =====================================================================

def test_la_venta_llega_con_lo_que_queda_por_devolver(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 3)

    r = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab)
    assert r.status_code == 200, r.text
    venta = r.json()

    assert venta["metodo_pago"] == "EFECTIVO"
    assert venta["sale_del_cajon"] is True
    linea = venta["lineas"][0]
    assert linea["vendidas"] == 3
    assert linea["devueltas"] == 0
    assert linea["devolvibles"] == 3
    assert linea["precio_unitario"] == str(PRECIO)


def test_lo_ya_devuelto_deja_de_ofrecerse(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Ofrecer unidades que ya volvieron llevaría a reingresarlas dos veces."""
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 3)
    assert _devolver(api, cab, codigo, variantes[0], 1).status_code == 201

    linea = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab).json()["lineas"][0]
    assert linea["devueltas"] == 1
    assert linea["devolvibles"] == 2


def test_una_venta_de_otra_sucursal_no_se_devuelve_aca(
    api: TestClient,
    db,
    mostrador: dict,
    cabeceras_admin: dict,
    variantes: list[int],
    stock,
) -> None:
    codigo = _vender(api, mostrador["cabeceras"], variantes[0], 1)

    norte = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    otro = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=norte, sufijo="2")
    _abrir_turno(api, otro, _caja(db, norte, "Caja N1"))

    assert api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=otro).status_code == 404
    assert _devolver(api, otro, codigo, variantes[0], 1).status_code == 404


def test_una_venta_inexistente_da_404(api: TestClient, mostrador: dict) -> None:
    r = api.get(f"{DEVOLUCIONES}/ventas/VP-20260920-ZZZZ", headers=mostrador["cabeceras"])
    assert r.status_code == 404


# =====================================================================
# Registrar la devolución
# =====================================================================

def test_la_prenda_vuelve_al_inventario(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    cab = mostrador["cabeceras"]
    antes = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])

    codigo = _vender(api, cab, variantes[0], 3)
    vendido = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
    assert vendido == antes - 3

    r = _devolver(api, cab, codigo, variantes[0], 2)
    assert r.status_code == 201, r.text

    despues = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
    assert despues == vendido + 2


def test_la_devolucion_deja_su_movimiento(
    api: TestClient, db, mostrador: dict, variantes: list[int], stock
) -> None:
    """D4: ninguna cantidad se mueve sin un movimiento que la explique."""
    from app.modules.inventario.models import MovimientoInventario

    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2)
    _devolver(api, cab, codigo, variantes[0], 2)

    movimientos = (
        db.query(MovimientoInventario)
        .filter(MovimientoInventario.tipo == "DEVOLUCION")
        .all()
    )
    assert len(movimientos) == 1
    assert movimientos[0].cantidad == 2
    assert codigo in (movimientos[0].motivo or "")


def test_la_venta_no_se_edita(
    api: TestClient, db, mostrador: dict, variantes: list[int], stock
) -> None:
    """Una devolución es un hecho nuevo, no una corrección de la venta."""
    from app.modules.ventas.models import Venta

    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2)
    _devolver(api, cab, codigo, variantes[0], 2)

    venta = db.query(Venta).filter(Venta.codigo == codigo).one()
    db.refresh(venta)
    assert venta.estado == "PAGADA"
    assert str(venta.total) == str(PRECIO * 2)


# =====================================================================
# El arqueo de CU-30, que es donde esto se puede romper en silencio
# =====================================================================

def test_devolver_un_cobro_en_efectivo_baja_el_esperado(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2)  # 500,00 al cajón

    antes = api.get(CAJA_MIO, headers=cab).json()
    assert antes["monto_esperado"] == "600.00"  # apertura 100 + 500

    r = _devolver(api, cab, codigo, variantes[0], 1)  # salen 250,00
    assert r.status_code == 201, r.text
    assert r.json()["sale_del_cajon"] is True
    assert r.json()["monto"] == "250.00"

    despues = api.get(CAJA_MIO, headers=cab).json()
    assert despues["devoluciones"] == "250.00"
    assert despues["monto_esperado"] == "350.00"


def test_devolver_un_cobro_con_tarjeta_no_toca_el_cajon(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """LA PRUEBA QUE SOSTIENE EL ARQUEO.

    Esa plata **nunca entró al cajón**, así que tampoco puede salir de él. Si
    `monto` no fuera cero, el turno cerraría con un faltante de 250 Bs que
    nadie puede explicar —y el cajero se llevaría la culpa—.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2, metodo="TARJETA")

    antes = api.get(CAJA_MIO, headers=cab).json()
    assert antes["monto_esperado"] == "100.00"  # solo la apertura

    r = _devolver(api, cab, codigo, variantes[0], 1)
    assert r.status_code == 201, r.text
    cuerpo = r.json()

    assert cuerpo["sale_del_cajon"] is False
    assert cuerpo["monto"] == "0.00"
    # Pero el valor de lo devuelto sí se informa: el cliente tiene que saber
    # cuánto le vuelve por su tarjeta.
    assert cuerpo["valor_devuelto"] == "250.00"

    despues = api.get(CAJA_MIO, headers=cab).json()
    assert despues["monto_esperado"] == "100.00"

    # Y la prenda volvió al inventario igual.
    assert _disponible(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]
    ) == 9


# =====================================================================
# Lo que hay que rechazar
# =====================================================================

def test_no_se_devuelve_mas_de_lo_vendido(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2)

    r = _devolver(api, cab, codigo, variantes[0], 3)
    assert r.status_code == 409
    assert "quedan 2" in r.json()["detail"]


def test_no_se_devuelve_dos_veces_la_misma_prenda(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2)
    assert _devolver(api, cab, codigo, variantes[0], 2).status_code == 201

    saldo = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])

    segunda = _devolver(api, cab, codigo, variantes[0], 1)
    assert segunda.status_code == 409
    assert "ya se devolvió entera" in segunda.json()["detail"]

    # Y no reingresó nada de más.
    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
        == saldo
    )


def test_una_prenda_que_no_estaba_en_la_venta_se_rechaza(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    r = _devolver(api, cab, codigo, variantes[1], 1)
    assert r.status_code == 422


def test_el_motivo_es_obligatorio(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Una devolución sin motivo es mercadería y plata que nadie puede auditar."""
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    sin_motivo = api.post(
        DEVOLUCIONES,
        headers=cab,
        json={
            "venta_codigo": codigo,
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert sin_motivo.status_code == 422

    vacio = _devolver(api, cab, codigo, variantes[0], 1, motivo="")
    assert vacio.status_code == 422


def test_la_misma_prenda_dos_veces_en_la_misma_devolucion_se_rechaza(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 3)

    r = api.post(
        DEVOLUCIONES,
        headers=cab,
        json={
            "venta_codigo": codigo,
            "motivo": "Dos líneas iguales",
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 1},
                {"variante_id": variantes[0], "cantidad": 1},
            ],
        },
    )
    assert r.status_code == 422


def test_sin_lineas_no_hay_devolucion(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    codigo = _vender(api, mostrador["cabeceras"], variantes[0], 1)
    r = api.post(
        DEVOLUCIONES,
        headers=mostrador["cabeceras"],
        json={"venta_codigo": codigo, "motivo": "Sin nada", "lineas": []},
    )
    assert r.status_code == 422


# =====================================================================
# Devoluciones parciales, que son el caso corriente
# =====================================================================

def test_dos_devoluciones_parciales_de_la_misma_venta(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Son legítimas: el cliente vuelve dos veces. Lo que no se puede es pasarse."""
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 4)

    assert _devolver(api, cab, codigo, variantes[0], 1).status_code == 201
    assert _devolver(api, cab, codigo, variantes[0], 2).status_code == 201
    # Queda 1. Pedir 2 se pasa.
    assert _devolver(api, cab, codigo, variantes[0], 2).status_code == 409
    assert _devolver(api, cab, codigo, variantes[0], 1).status_code == 201

    linea = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab).json()["lineas"][0]
    assert linea["devueltas"] == 4
    assert linea["devolvibles"] == 0

    # 10 iniciales − 4 vendidas + 4 devueltas
    assert _disponible(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]
    ) == 10


def test_el_arqueo_suma_todas_las_devoluciones_del_turno(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 4)  # 1000,00 al cajón

    _devolver(api, cab, codigo, variantes[0], 1)
    _devolver(api, cab, codigo, variantes[0], 1)

    turno = api.get(CAJA_MIO, headers=cab).json()
    assert turno["devoluciones"] == "500.00"
    # apertura 100 + 1000 cobrados − 500 devueltos
    assert turno["monto_esperado"] == "600.00"
