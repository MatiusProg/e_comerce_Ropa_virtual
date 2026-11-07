"""CU-31 y CU-32 · Ofertas, precios mayoristas y fuera de temporada.

Lo que más importa cubrir
-------------------------
- **RN-15.** Se cobra UN precio, el más bajo entre el de lista, el mayorista
  (si se llega a la cantidad) y la oferta vigente. No se suman nunca.
- **La cantidad mínima es por producto:** tallas y colores mezclados suman.
- **El mayorista llega a la caja, al carrito y a la vitrina** (RF-56).
- **RN-16.** La oferta automática se crea solo si se cumplen los días desde el
  fin de la temporada Y la existencia sobrante; el admin la apaga y no vuelve.
- **Aplicar es idempotente:** dos corridas no crean dos ofertas.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_cu26_carrito import CARRITO, _agregar
from tests.test_cu31_venta_presencial import (
    PRENDAS,
    VENTAS,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _crear_variantes,
    _empleado,
    _ingresar,
)

OFERTAS = "/api/v1/ofertas"
MAYORISTAS = f"{OFERTAS}/mayoristas"
REGLA = f"{OFERTAS}/fuera-de-temporada/regla"
CANDIDATAS = f"{OFERTAS}/fuera-de-temporada/candidatas"
APLICAR = f"{OFERTAS}/fuera-de-temporada/aplicar"
PROMOCIONES = "/api/v1/catalogo/promociones"
TEMPORADAS = "/api/v1/catalogo/temporadas"
FICHA = "/api/v1/tienda/productos"

HOY = date.today()


# =====================================================================
# Fixtures: una camisa de Bs 250 en S y M, con 20 de cada una
# =====================================================================

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict, sucursal: int) -> list[int]:
    ids = _crear_variantes(api, cabeceras_admin)
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(ids[0], 20), (ids[1], 20)])
    return ids


@pytest.fixture
def producto(db, variantes) -> int:
    from app.modules.catalogo.models import VarianteProducto

    return db.scalar(
        select(VarianteProducto.producto_id).where(VarianteProducto.id == variantes[0])
    )


@pytest.fixture
def cajero(api, cabeceras_admin, db, sucursal) -> dict:
    cab = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="51")
    _abrir_turno(api, cab, _caja(db, sucursal))
    return cab


def _mayorista(api, admin, producto: int, desde: int = 6, precio: str = "200.00"):
    return api.post(MAYORISTAS, headers=admin,
                    json={"producto_id": producto, "cantidad_minima": desde,
                          "precio_unitario": precio})


def _vender(api, cajero, lineas: list[tuple[int, int]]):
    r = api.post(VENTAS, headers=cajero, json={
        "metodo_pago": "EFECTIVO", "monto_recibido": "9000.00",
        "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas]})
    assert r.status_code == 201, r.text
    return r.json()


def _promocion(api, admin, producto: int, porcentaje: str):
    r = api.post(PROMOCIONES, headers=admin, json={
        "nombre": f"Promo {porcentaje}", "alcance": "PRODUCTO", "objetivo_id": producto,
        "porcentaje": porcentaje, "desde": (HOY - timedelta(days=1)).isoformat(),
        "hasta": None, "activa": True})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# =====================================================================
# CU-31 · Gestionar precios mayoristas
# =====================================================================

def test_el_admin_define_un_precio_mayorista(api, cabeceras_admin, producto) -> None:
    r = _mayorista(api, cabeceras_admin, producto)
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["cantidad_minima"] == 6
    assert Decimal(cuerpo["precio_unitario"]) == Decimal("200.00")
    assert cuerpo["producto"] == "Camisa Oxford manga larga"

    lista = api.get(MAYORISTAS, headers=cabeceras_admin).json()
    assert lista["total"] == 1


def test_no_se_repite_el_escalon_de_un_producto(api, cabeceras_admin, producto) -> None:
    assert _mayorista(api, cabeceras_admin, producto).status_code == 201
    assert _mayorista(api, cabeceras_admin, producto, precio="190.00").status_code == 409


def test_el_mayorista_tiene_que_ser_mas_barato(api, cabeceras_admin, producto) -> None:
    r = _mayorista(api, cabeceras_admin, producto, precio="250.00")
    assert r.status_code == 422
    assert "menor" in r.json()["detail"]


def test_un_cajero_no_gestiona_ofertas(api, cajero, producto) -> None:
    assert _mayorista(api, cajero, producto).status_code == 403
    assert api.post(APLICAR, headers=cajero).status_code == 403


# =====================================================================
# CU-31 · El mayorista al cobrar (RF-56, RN-15)
# =====================================================================

def test_la_caja_muestra_los_escalones(api, cabeceras_admin, cajero, producto, variantes) -> None:
    _mayorista(api, cabeceras_admin, producto)
    prendas = api.get(PRENDAS, headers=cajero).json()["items"]
    fila = next(p for p in prendas if p["variante_id"] == variantes[0])
    assert fila["producto_id"] == producto
    assert fila["mayoristas"] == [{"cantidad_minima": 6, "precio_unitario": "200.00"}]


def test_tallas_mezcladas_suman_para_el_mayorista(
    api, cabeceras_admin, cajero, producto, variantes
) -> None:
    _mayorista(api, cabeceras_admin, producto)
    # 3 S + 3 M = 6 camisas: llegan al escalón.
    venta = _vender(api, cajero, [(variantes[0], 3), (variantes[1], 3)])
    assert Decimal(venta["subtotal"]) == Decimal("1500.00")
    assert Decimal(venta["total"]) == Decimal("1200.00")


def test_sin_llegar_a_la_cantidad_se_cobra_el_de_lista(
    api, cabeceras_admin, cajero, producto, variantes
) -> None:
    _mayorista(api, cabeceras_admin, producto)
    venta = _vender(api, cajero, [(variantes[0], 3), (variantes[1], 2)])
    assert Decimal(venta["total"]) == Decimal("1250.00")


def test_se_aplica_el_escalon_mas_alto_alcanzado(
    api, cabeceras_admin, cajero, producto, variantes
) -> None:
    _mayorista(api, cabeceras_admin, producto, desde=6, precio="200.00")
    _mayorista(api, cabeceras_admin, producto, desde=10, precio="180.00")
    venta = _vender(api, cajero, [(variantes[0], 10)])
    assert Decimal(venta["total"]) == Decimal("1800.00")


def test_gana_la_oferta_si_deja_menos_que_el_mayorista(
    api, cabeceras_admin, cajero, producto, variantes
) -> None:
    _mayorista(api, cabeceras_admin, producto)        # 200
    _promocion(api, cabeceras_admin, producto, "30.00")  # 175
    venta = _vender(api, cajero, [(variantes[0], 6)])
    assert Decimal(venta["total"]) == Decimal("1050.00")


def test_gana_el_mayorista_si_deja_menos_que_la_oferta_y_no_se_suman(
    api, cabeceras_admin, cajero, producto, variantes
) -> None:
    _mayorista(api, cabeceras_admin, producto)        # 200
    _promocion(api, cabeceras_admin, producto, "10.00")  # 225
    venta = _vender(api, cajero, [(variantes[0], 6)])
    # 6 x 200; sumarlos daría 6 x 175 = 1050.
    assert Decimal(venta["total"]) == Decimal("1200.00")


def test_un_mayorista_apagado_no_se_aplica(
    api, cabeceras_admin, cajero, producto, variantes
) -> None:
    escalon = _mayorista(api, cabeceras_admin, producto).json()["id"]
    r = api.patch(f"{MAYORISTAS}/{escalon}/estado", headers=cabeceras_admin,
                  json={"activo": False})
    assert r.status_code == 200 and r.json()["activo"] is False
    venta = _vender(api, cajero, [(variantes[0], 6)])
    assert Decimal(venta["total"]) == Decimal("1500.00")


def test_el_carrito_aplica_el_mayorista(
    api, cabeceras_admin, cabeceras_cliente, producto, variantes
) -> None:
    _mayorista(api, cabeceras_admin, producto)
    _agregar(api, cabeceras_cliente, variantes[0], 4)
    _agregar(api, cabeceras_cliente, variantes[1], 2)
    carrito = api.get(CARRITO, headers=cabeceras_cliente).json()
    assert Decimal(carrito["total"]) == Decimal("1200.00")
    linea = carrito["lineas"][0]
    assert linea["descuento"]["tipo"] == "MAYORISTA"
    assert linea["descuento"]["promocion_id"] is None


def test_la_ficha_publica_muestra_los_escalones(
    api, cabeceras_admin, cabeceras_cliente, producto
) -> None:
    _mayorista(api, cabeceras_admin, producto)
    ficha = api.get(f"{FICHA}/{producto}", headers=cabeceras_cliente)
    assert ficha.status_code == 200, ficha.text
    assert ficha.json()["mayoristas"] == [{"cantidad_minima": 6, "precio_unitario": "200.00"}]


# =====================================================================
# CU-32 · Aplicar ofertas de fuera de temporada (RF-57, RN-16)
# =====================================================================

def _temporada_terminada(api, admin, db, producto: int, *, hace_dias: int) -> int:
    from app.modules.catalogo.models import Producto

    fin = HOY - timedelta(days=hace_dias)
    r = api.post(TEMPORADAS, headers=admin, json={
        "nombre": f"Invierno {hace_dias}", "descripcion": None,
        "fecha_inicio": (fin - timedelta(days=90)).isoformat(),
        "fecha_fin": fin.isoformat(), "activa": True})
    assert r.status_code == 201, r.text
    db.get(Producto, producto).temporada_id = r.json()["id"]
    db.commit()
    return r.json()["id"]


def _regla(api, admin, *, activa=True, dias=30, existencia=10, porcentaje="30.00"):
    r = api.put(REGLA, headers=admin, json={
        "activa": activa, "dias_desde_fin": dias, "existencia_minima": existencia,
        "porcentaje": porcentaje})
    assert r.status_code == 200, r.text
    return r.json()


def test_la_regla_arranca_apagada(api, cabeceras_admin) -> None:
    regla = api.get(REGLA, headers=cabeceras_admin).json()
    assert regla["activa"] is False
    assert regla["por_omision"] is True


def test_crea_la_oferta_cuando_se_cumple_el_factor(
    api, cabeceras_admin, cajero, db, producto, variantes
) -> None:
    # Terminó hace 40 días y quedan 40 camisas: cumple 30 días y 10 sobrantes.
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)

    candidatas = api.get(CANDIDATAS, headers=cabeceras_admin).json()
    assert [(c["producto_id"], c["situacion"]) for c in candidatas] == [(producto, "NUEVA")]

    hecho = api.post(APLICAR, headers=cabeceras_admin).json()
    assert hecho["creadas"] == 1

    promos = api.get(PROMOCIONES, headers=cabeceras_admin).json()["items"]
    assert [(p["origen"], p["vigente"], p["objetivo_id"]) for p in promos] == [
        ("AUTOMATICA", True, producto)
    ]
    # Y descuenta en la caja sin que nadie haga nada más.
    venta = _vender(api, cajero, [(variantes[0], 1)])
    assert Decimal(venta["total"]) == Decimal("175.00")


def test_aplicar_dos_veces_no_duplica(api, cabeceras_admin, db, producto, variantes) -> None:
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)
    api.post(APLICAR, headers=cabeceras_admin)
    segunda = api.post(APLICAR, headers=cabeceras_admin).json()
    assert segunda["creadas"] == 0
    assert segunda["ya_vigentes"] == 1
    assert api.get(PROMOCIONES, headers=cabeceras_admin).json()["total"] == 1


def test_la_que_apago_el_admin_no_se_vuelve_a_crear(
    api, cabeceras_admin, db, producto, variantes
) -> None:
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)
    api.post(APLICAR, headers=cabeceras_admin)
    promo = api.get(PROMOCIONES, headers=cabeceras_admin).json()["items"][0]["id"]
    api.patch(f"{PROMOCIONES}/{promo}/estado", headers=cabeceras_admin, json={"activa": False})

    otra = api.post(APLICAR, headers=cabeceras_admin).json()
    assert otra["creadas"] == 0
    assert otra["apagadas_por_admin"] == 1
    assert api.get(PROMOCIONES, headers=cabeceras_admin).json()["total"] == 1


def test_con_la_regla_apagada_no_crea_nada(api, cabeceras_admin, db, producto, variantes) -> None:
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin, activa=False)
    assert api.post(APLICAR, headers=cabeceras_admin).json()["creadas"] == 0


def test_no_califica_si_falta_tiempo_o_no_sobra(api, cabeceras_admin, db, producto, variantes) -> None:
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=10)
    _regla(api, cabeceras_admin, dias=30)
    assert api.get(CANDIDATAS, headers=cabeceras_admin).json() == []

    # Ya pasaron los días, pero se piden 50 sobrantes y hay 40.
    _regla(api, cabeceras_admin, dias=5, existencia=50)
    assert api.get(CANDIDATAS, headers=cabeceras_admin).json() == []

    _regla(api, cabeceras_admin, dias=5, existencia=40)
    assert len(api.get(CANDIDATAS, headers=cabeceras_admin).json()) == 1


def test_se_cierra_cuando_deja_de_sobrar(api, cabeceras_admin, db, producto, variantes) -> None:
    from app.modules.catalogo.promociones_models import Promocion

    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)
    api.post(APLICAR, headers=cabeceras_admin)
    # La oferta tiene unos días encima.
    promo = db.scalar(select(Promocion).where(Promocion.origen == "AUTOMATICA"))
    promo.desde = HOY - timedelta(days=5)
    db.commit()

    # Se subió la vara: 40 ya no es sobrante.
    _regla(api, cabeceras_admin, existencia=100)
    hecho = api.post(APLICAR, headers=cabeceras_admin).json()
    assert hecho["cerradas"] == 1

    fila = api.get(PROMOCIONES, headers=cabeceras_admin).json()["items"][0]
    assert fila["vigente"] is False
    assert fila["hasta"] == (HOY - timedelta(days=1)).isoformat()


# --- Tanda C de la auditoría ------------------------------------------------

def _automatica(db):
    from app.modules.catalogo.promociones_models import Promocion

    db.expire_all()
    return db.scalar(select(Promocion).where(Promocion.origen == "AUTOMATICA"))


def test_apagar_la_regla_cierra_sus_ofertas_en_el_acto(
    api, cabeceras_admin, db, producto, variantes
) -> None:
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)
    api.post(APLICAR, headers=cabeceras_admin)
    promo = _automatica(db)
    promo.desde = HOY - timedelta(days=5)
    db.commit()

    # Sin esperar a la próxima aplicación.
    _regla(api, cabeceras_admin, activa=False)
    fila = api.get(PROMOCIONES, headers=cabeceras_admin).json()["items"][0]
    assert fila["vigente"] is False
    assert fila["hasta"] == (HOY - timedelta(days=1)).isoformat()
    assert _automatica(db).cerrada_por_regla is True


def test_la_que_cerro_el_admin_no_se_reabre_y_la_de_la_regla_si(
    api, cabeceras_admin, db, producto, variantes
) -> None:
    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)
    api.post(APLICAR, headers=cabeceras_admin)
    promo = _automatica(db)
    promo.desde = HOY - timedelta(days=5)
    db.commit()

    # La cierra la regla (se sube la vara) y vuelve a calificar: se reabre.
    _regla(api, cabeceras_admin, existencia=100)
    assert api.post(APLICAR, headers=cabeceras_admin).json()["cerradas"] == 1
    _regla(api, cabeceras_admin, existencia=10)
    assert api.post(APLICAR, headers=cabeceras_admin).json()["creadas"] == 1
    assert _automatica(db).hasta is None

    # Ahora la cierra el admin con fecha de fin: queda cerrada.
    promo = _automatica(db)
    promo.desde = HOY - timedelta(days=5)
    db.commit()
    r = api.patch(f"{PROMOCIONES}/{promo.id}", headers=cabeceras_admin,
                  json={"hasta": (HOY - timedelta(days=1)).isoformat()})
    assert r.status_code == 200, r.text
    otra = api.post(APLICAR, headers=cabeceras_admin).json()
    assert otra["creadas"] == 0
    assert otra["apagadas_por_admin"] == 1
    assert _automatica(db).hasta == HOY - timedelta(days=1)


def test_el_stock_de_una_sucursal_dada_de_baja_no_es_sobrante(
    api, cabeceras_admin, db, producto, variantes
) -> None:
    from app.modules.organizacion.models import Sucursal

    _temporada_terminada(api, cabeceras_admin, db, producto, hace_dias=40)
    _regla(api, cabeceras_admin)
    assert len(api.get(CANDIDATAS, headers=cabeceras_admin).json()) == 1

    for s in db.scalars(select(Sucursal)):
        s.activa = False
    db.commit()
    assert api.get(CANDIDATAS, headers=cabeceras_admin).json() == []
