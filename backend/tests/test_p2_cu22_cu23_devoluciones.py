"""CU-22 · Registrar cambio o devolución en caja, y CU-23 · Configurar la
ventana de devolución (2do parcial).

Lo que el 2do parcial suma al CU-32 del 1er parcial:
- **La nota de devolución (RF-37):** lo que volvió y lo que salió con su talla
  y su precio, la diferencia, el motivo y la conformidad del cliente.
- **Sin conformidad no se registra (RN-20).** En caja el cliente está en el
  mostrador: la nota nace CERRADA y conforme.
- **La ventana es de cada empresa, en horas (RF-35, RN-08)**, y fuera de ella
  se rechaza.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient

from app.core import tiempo
from tests.test_cu31_venta_presencial import (  # noqa: F401 - fixtures de pytest
    _crear_sucursal,
    _empleado,
    cajero,
    mostrador,
    stock,
    sucursal,
    variantes,
)
from tests.test_cu32_cambios import _cambiar
from tests.test_cu32_devoluciones import DEVOLUCIONES, _devolver, _vender

NOTAS = "/api/v1/pos/notas-devolucion"
VENTANA = "/api/v1/plataforma/mi-tienda/devoluciones"


def _envejecer_horas(db, codigo: str, horas: int) -> None:
    from app.modules.ventas.models import Venta

    fila = db.query(Venta).filter(Venta.codigo == codigo).one()
    fila.creado_en = tiempo.ahora() - timedelta(hours=horas)
    db.commit()


# =====================================================================
# CU-22: la conformidad
# =====================================================================

def test_sin_conformidad_no_se_devuelve(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    cuerpo = {
        "venta_codigo": codigo,
        "motivo": "No le quedó",
        "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
    }
    assert api.post(DEVOLUCIONES, headers=cab, json=cuerpo).status_code == 422
    cuerpo["conformidad"] = {"conforme": False}
    assert api.post(DEVOLUCIONES, headers=cab, json=cuerpo).status_code == 422


def test_la_devolucion_deja_su_nota_cerrada_y_conforme(
    api: TestClient, cabeceras_admin: dict, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 2)
    r = api.post(
        DEVOLUCIONES,
        headers=cab,
        json={
            "venta_codigo": codigo,
            "motivo": "Tenía una mancha",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            "conformidad": {"conforme": True, "observacion": "Prefiere el dinero"},
        },
    )
    assert r.status_code == 201, r.text
    devolucion = r.json()
    assert devolucion["numero_nota"] == f"ND-{devolucion['id']:06d}"

    nota = api.get(f"{NOTAS}/{devolucion['id']}", headers=cab).json()
    assert nota["numero"] == devolucion["numero_nota"]
    assert nota["tipo"] == "DEVOLUCION" and nota["estado"] == "CERRADA"
    assert nota["conforme"] is True
    assert nota["observacion_cliente"] == "Prefiere el dinero"
    assert nota["venta_codigo"] == codigo
    assert nota["horas_desde_la_venta"] == 0
    [linea] = nota["devueltas"]
    assert linea["talla"] and linea["cantidad"] == 1
    assert nota["valor_devuelto"] == linea["subtotal"]
    assert nota["llevadas"] == [] and nota["venta_nueva_codigo"] is None
    assert nota["caja"] and nota["cajero"] and nota["sucursal"]

    # El administrador también la ve.
    assert api.get(f"{NOTAS}/{devolucion['id']}", headers=cabeceras_admin).status_code == 200


def test_la_nota_del_cambio_trae_las_dos_tallas_y_la_diferencia(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 201, r.text
    cambio = r.json()

    nota = api.get(f"{NOTAS}/{cambio['id']}", headers=cab).json()
    assert nota["tipo"] == "CAMBIO"
    assert nota["venta_nueva_codigo"] == cambio["venta_nueva_codigo"]
    assert nota["devueltas"][0]["variante_id"] == variantes[0]
    assert nota["llevadas"][0]["variante_id"] == variantes[1]
    assert nota["devueltas"][0]["talla"] != nota["llevadas"][0]["talla"]
    assert nota["diferencia"] == cambio["diferencia"]
    assert nota["a_favor_de"] == cambio["a_favor_de"]
    assert nota["conforme"] is True


def test_el_cambio_tambien_exige_conformidad(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    r = api.post(
        f"{DEVOLUCIONES}/cambios",
        headers=cab,
        json={
            "venta_codigo": codigo,
            "motivo": "Le quedó grande",
            "devueltas": [{"variante_id": variantes[0], "cantidad": 1}],
            "llevadas": [{"variante_id": variantes[1], "cantidad": 1}],
        },
    )
    assert r.status_code == 422


def test_la_nota_de_otra_sucursal_no_existe_para_el_cajero(
    api: TestClient, cabeceras_admin: dict, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    devolucion = _devolver(api, cab, codigo, variantes[0], 1).json()

    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    ajeno = _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=otra, sufijo="22")
    assert api.get(f"{NOTAS}/{devolucion['id']}", headers=ajeno).status_code == 404


def test_un_cliente_no_ve_notas(api: TestClient, cabeceras_cliente: dict) -> None:
    assert api.get(f"{NOTAS}/1", headers=cabeceras_cliente).status_code == 403


# =====================================================================
# CU-23: la ventana de la empresa
# =====================================================================

def test_la_ventana_empieza_en_48_horas(api: TestClient, cabeceras_admin: dict) -> None:
    r = api.get(VENTANA, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert r.json() == {"horas": 48}


def test_el_administrador_cambia_la_ventana_y_rige_al_devolver(
    api: TestClient, cabeceras_admin: dict, mostrador: dict, variantes: list[int], stock, db
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _envejecer_horas(db, codigo, 30)

    # Con 48 horas, una venta de hace 30 se puede devolver...
    buscada = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab).json()
    assert buscada["plazo_horas"] == 48 and buscada["dentro_de_plazo"] is True

    # ...con 24, ya no (RN-08).
    r = api.put(VENTANA, headers=cabeceras_admin, json={"horas": 24})
    assert r.status_code == 200 and r.json() == {"horas": 24}
    buscada = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab).json()
    assert buscada["plazo_horas"] == 24 and buscada["dentro_de_plazo"] is False

    r = _devolver(api, cab, codigo, variantes[0], 1)
    assert r.status_code == 409
    assert "1 día" in r.json()["detail"]


def test_la_ventana_en_horas_sueltas_se_dice_en_horas(
    api: TestClient, cabeceras_admin: dict, mostrador: dict, variantes: list[int], stock, db
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _envejecer_horas(db, codigo, 13)
    api.put(VENTANA, headers=cabeceras_admin, json={"horas": 12})
    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 409
    assert "12 horas" in r.json()["detail"]


def test_la_ventana_tiene_limites(api: TestClient, cabeceras_admin: dict) -> None:
    assert api.put(VENTANA, headers=cabeceras_admin, json={"horas": 0}).status_code == 422
    assert api.put(VENTANA, headers=cabeceras_admin, json={"horas": 721}).status_code == 422


def test_el_cajero_no_configura_la_ventana(api: TestClient, mostrador: dict) -> None:
    assert api.put(VENTANA, headers=mostrador["cabeceras"], json={"horas": 72}).status_code == 403
