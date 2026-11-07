"""CU-33 a CU-35 · Traspasos entre sucursales.

Lo que más importa cubrir
-------------------------
- **RN-09.** El traspaso descuenta del origen al ENVIARSE y suma al destino al
  RECIBIRSE, nunca antes; si al enviar ya no alcanza, no se escribe nada.
- **El ámbito no se acepta del cuerpo.** El encargado pide para SU sucursal, no
  aprueba lo que pidió y no ve los traspasos de otras.
- **El administrador ordena sin pedido (RF-40):** el traspaso nace APROBADO.
- **Los sugeridos (RF-42)** mueven de donde sobra a donde se vende y falta, y
  descuentan lo que ya está en camino. Exigen la función del plan.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.test_cu31_venta_presencial import (
    VENTAS,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _crear_variantes,
    _disponible,
    _empleado,
    _ingresar,
)

TRASPASOS = "/api/v1/traspasos"
SUGERIDOS = f"{TRASPASOS}/sugeridos"


# =====================================================================
# Fixtures: Centro tiene la mercadería, Norte la pide
# =====================================================================

@pytest.fixture
def centro(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def norte(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Norte")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict, centro: int) -> list[int]:
    ids = _crear_variantes(api, cabeceras_admin)
    _ingresar(api, cabeceras_admin, sucursal_id=centro, lineas=[(ids[0], 10), (ids[1], 3)])
    return ids


@pytest.fixture
def enc_centro(api: TestClient, cabeceras_admin: dict, centro: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=centro, sufijo="31")


@pytest.fixture
def enc_norte(api: TestClient, cabeceras_admin: dict, norte: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=norte, sufijo="32")


def _pedir(api, cab, *, variante: int, origen: int, cantidad: int = 4, **extra):
    return api.post(
        TRASPASOS,
        headers=cab,
        json={"variante_id": variante, "sucursal_origen_id": origen, "cantidad": cantidad,
              "motivo": "Se agotó en vitrina", **extra},
    )


def _saldo(api, admin, sucursal: int, variante: int) -> int:
    try:
        return _disponible(api, admin, sucursal_id=sucursal, variante_id=variante)
    except AssertionError:
        return 0


# =====================================================================
# CU-33 Solicitar traspaso
# =====================================================================

def test_el_encargado_pide_para_su_sucursal_y_avisa_al_origen(
    api, cabeceras_admin, enc_centro, enc_norte, centro, norte, variantes, db
) -> None:
    r = _pedir(api, enc_norte, variante=variantes[0], origen=centro)
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["tipo"] == "PEDIDO"
    assert t["estado"] == "SOLICITADO"
    assert t["destino"]["id"] == norte
    assert t["origen"]["nombre"] == "Centro"
    assert t["acciones"] == ["RECHAZAR"]  # el que pidió solo puede retirarlo

    # Pedir no mueve nada.
    assert _saldo(api, cabeceras_admin, centro, variantes[0]) == 10

    from app.modules.notificaciones.models import Notificacion

    avisos = db.scalars(select(Notificacion).where(Notificacion.tipo == "TRASPASO")).all()
    assert len(avisos) == 1
    assert "Norte le pide 4" in avisos[0].titulo


def test_el_encargado_no_elige_otro_destino(api, enc_norte, centro, variantes) -> None:
    otra = _pedir(api, enc_norte, variante=variantes[0], origen=centro,
                  sucursal_destino_id=centro)
    assert otra.status_code in (403, 422)


def test_no_se_pide_mas_de_lo_que_tiene_el_origen(api, enc_norte, centro, variantes) -> None:
    r = _pedir(api, enc_norte, variante=variantes[1], origen=centro, cantidad=5)
    assert r.status_code == 409
    assert "3 unidades" in r.json()["detail"]


def test_no_se_duplica_un_pedido_abierto(api, enc_norte, centro, variantes) -> None:
    assert _pedir(api, enc_norte, variante=variantes[0], origen=centro).status_code == 201
    r = _pedir(api, enc_norte, variante=variantes[0], origen=centro)
    assert r.status_code == 409
    assert "Ya hay un traspaso" in r.json()["detail"]


def test_el_admin_ordena_sin_pedido_y_nace_aprobado(
    api, cabeceras_admin, centro, norte, variantes
) -> None:
    r = _pedir(api, cabeceras_admin, variante=variantes[0], origen=centro,
               sucursal_destino_id=norte)
    assert r.status_code == 201, r.text
    assert r.json()["tipo"] == "ORDEN"
    assert r.json()["estado"] == "APROBADO"
    assert set(r.json()["acciones"]) == {"ENVIAR", "RECHAZAR"}

    sin_destino = _pedir(api, cabeceras_admin, variante=variantes[0], origen=norte)
    assert sin_destino.status_code == 422


def test_las_sucursales_que_tienen_la_prenda(api, enc_norte, centro, variantes) -> None:
    r = api.get(f"{TRASPASOS}/origenes", headers=enc_norte,
                params={"variante_id": variantes[0]})
    assert r.status_code == 200
    assert r.json() == [{"sucursal_id": centro, "sucursal": "Centro", "disponible": 10}]


def test_el_buscador_trae_lo_que_tienen_las_otras(api, enc_norte, enc_centro, variantes) -> None:
    r = api.get(f"{TRASPASOS}/prendas", headers=enc_norte, params={"busqueda": "oxford"})
    assert r.status_code == 200
    assert {p["variante_id"]: p["disponible"] for p in r.json()} == {
        variantes[0]: 10, variantes[1]: 3}
    # Centro no se pide a sí mismo: lo que tiene no cuenta.
    assert api.get(f"{TRASPASOS}/prendas", headers=enc_centro).json() == []


def test_un_cajero_no_pide_traspasos(api, cabeceras_admin, norte, centro, variantes) -> None:
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=norte, sufijo="33")
    assert _pedir(api, cajero, variante=variantes[0], origen=centro).status_code == 403


# =====================================================================
# CU-34 Atender traspaso: el circuito completo y RN-09
# =====================================================================

def test_circuito_completo_mueve_el_inventario_en_cada_punta(
    api, cabeceras_admin, enc_centro, enc_norte, centro, norte, variantes
) -> None:
    t = _pedir(api, enc_norte, variante=variantes[0], origen=centro, cantidad=4).json()

    # El que pidió no se aprueba a sí mismo.
    assert api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=enc_norte).status_code == 403

    # Centro aprueba solo 3 de los 4.
    r = api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=enc_centro, json={"cantidad": 3})
    assert r.status_code == 200, r.text
    assert (r.json()["estado"], r.json()["cantidad"], r.json()["cantidad_solicitada"]) == (
        "APROBADO", 3, 4)
    assert _saldo(api, cabeceras_admin, centro, variantes[0]) == 10  # aprobar no aparta

    r = api.post(f"{TRASPASOS}/{t['id']}/enviar", headers=enc_centro)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "ENVIADO"
    assert _saldo(api, cabeceras_admin, centro, variantes[0]) == 7
    assert _saldo(api, cabeceras_admin, norte, variantes[0]) == 0  # en camino

    # Enviar dos veces no descuenta dos veces.
    assert api.post(f"{TRASPASOS}/{t['id']}/enviar", headers=enc_centro).status_code == 409
    # Recibir es del destino.
    assert api.post(f"{TRASPASOS}/{t['id']}/recibir", headers=enc_centro).status_code == 403

    r = api.post(f"{TRASPASOS}/{t['id']}/recibir", headers=enc_norte)
    assert r.status_code == 200, r.text
    fin = r.json()
    assert fin["estado"] == "RECIBIDO"
    assert fin["acciones"] == []
    assert fin["aprobado_en"] and fin["enviado_en"] and fin["recibido_en"]
    assert _saldo(api, cabeceras_admin, norte, variantes[0]) == 3

    # Los dos movimientos quedan en el kardex con la referencia del traspaso.
    movs = api.get("/api/v1/inventario/movimientos", headers=cabeceras_admin,
                   params={"tipo": "TRANSFERENCIA", "tamano": 50}).json()["items"]
    assert sorted(m["cantidad"] for m in movs) == [-3, 3]


def test_si_al_enviar_ya_no_alcanza_no_se_escribe_nada(
    api, cabeceras_admin, enc_centro, enc_norte, centro, norte, variantes, db
) -> None:
    t = _pedir(api, enc_norte, variante=variantes[1], origen=centro, cantidad=3).json()
    api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=enc_centro)

    # Entre aprobar y despachar, Centro vendió dos.
    cajero = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=centro, sufijo="34")
    _abrir_turno(api, cajero, _caja(db, centro))
    venta = api.post(VENTAS, headers=cajero, json={
        "metodo_pago": "EFECTIVO", "monto_recibido": "1000.00",
        "lineas": [{"variante_id": variantes[1], "cantidad": 2}]})
    assert venta.status_code == 201, venta.text

    r = api.post(f"{TRASPASOS}/{t['id']}/enviar", headers=enc_centro)
    assert r.status_code == 409
    assert "RN-09" in r.json()["detail"]
    assert _saldo(api, cabeceras_admin, centro, variantes[1]) == 1
    assert api.get(f"{TRASPASOS}/{t['id']}", headers=enc_centro).json()["estado"] == "APROBADO"


def test_rechazar_exige_motivo_y_lo_deja_cerrado(
    api, enc_centro, enc_norte, centro, variantes
) -> None:
    t = _pedir(api, enc_norte, variante=variantes[0], origen=centro).json()
    assert api.post(f"{TRASPASOS}/{t['id']}/rechazar", headers=enc_centro,
                    json={"motivo": ""}).status_code == 422
    r = api.post(f"{TRASPASOS}/{t['id']}/rechazar", headers=enc_centro,
                 json={"motivo": "Lo necesitamos para la vitrina"})
    assert r.status_code == 200
    assert r.json()["estado"] == "RECHAZADO"
    assert r.json()["motivo_rechazo"] == "Lo necesitamos para la vitrina"
    assert api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=enc_centro).status_code == 409


def test_el_destino_retira_su_pedido_solo_antes_de_aprobarse(
    api, enc_centro, enc_norte, centro, variantes
) -> None:
    t = _pedir(api, enc_norte, variante=variantes[0], origen=centro).json()
    api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=enc_centro)
    r = api.post(f"{TRASPASOS}/{t['id']}/rechazar", headers=enc_norte,
                 json={"motivo": "Ya no hace falta"})
    assert r.status_code == 403


def test_un_encargado_ajeno_no_ve_el_traspaso(
    api, cabeceras_admin, enc_norte, centro, variantes
) -> None:
    t = _pedir(api, enc_norte, variante=variantes[0], origen=centro).json()
    sur = _crear_sucursal(api, cabeceras_admin, nombre="Sur")
    ajeno = _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=sur, sufijo="35")
    assert api.get(f"{TRASPASOS}/{t['id']}", headers=ajeno).status_code == 404
    assert api.get(TRASPASOS, headers=ajeno).json()["total"] == 0
    assert api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=ajeno).status_code == 404


def test_las_bandejas_del_encargado(api, enc_centro, enc_norte, centro, variantes) -> None:
    _pedir(api, enc_norte, variante=variantes[0], origen=centro)
    assert api.get(TRASPASOS, headers=enc_centro,
                   params={"bandeja": "SALIENTES"}).json()["total"] == 1
    assert api.get(TRASPASOS, headers=enc_centro,
                   params={"bandeja": "ENTRANTES"}).json()["total"] == 0
    assert api.get(TRASPASOS, headers=enc_norte,
                   params={"bandeja": "ENTRANTES"}).json()["total"] == 1


# =====================================================================
# CU-35 Consultar traspasos sugeridos
# =====================================================================

def _vender_en(api, admin, db, sucursal: int, variante: int, cantidad: int, sufijo: str):
    cajero = _empleado(api, admin, cargo="CAJERO", sucursal_id=sucursal, sufijo=sufijo)
    _abrir_turno(api, cajero, _caja(db, sucursal))
    r = api.post(VENTAS, headers=cajero, json={
        "metodo_pago": "EFECTIVO", "monto_recibido": "5000.00",
        "lineas": [{"variante_id": variante, "cantidad": cantidad}]})
    assert r.status_code == 201, r.text


def test_sugiere_llevar_de_donde_sobra_a_donde_se_vende(
    api, cabeceras_admin, centro, norte, variantes, db
) -> None:
    # Norte tenía 6 y vendió 5: le queda 1. Centro tiene 10 y no vendió nada.
    _ingresar(api, cabeceras_admin, sucursal_id=norte, lineas=[(variantes[0], 6)])
    _vender_en(api, cabeceras_admin, db, norte, variantes[0], 5, "36")

    r = api.get(SUGERIDOS, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    [s] = [i for i in r.json()["items"] if i["variante_id"] == variantes[0]]
    assert s["origen"]["sucursal_id"] == centro
    assert s["destino"]["sucursal_id"] == norte
    assert s["destino"]["vendidas"] == 5
    # Para cubrir otros 5 le faltan 4.
    assert s["cantidad_sugerida"] == 4

    # Ordenarlo desde la sugerencia, y la sugerencia desaparece.
    o = _pedir(api, cabeceras_admin, variante=variantes[0], origen=centro,
               sucursal_destino_id=norte, cantidad=4, desde_sugerencia=True)
    assert o.status_code == 201, o.text
    assert o.json()["tipo"] == "SUGERIDO"
    otra = api.get(SUGERIDOS, headers=cabeceras_admin).json()["items"]
    assert not [i for i in otra if i["variante_id"] == variantes[0]]


def test_sin_ventas_no_hay_sugerencias(api, cabeceras_admin, variantes) -> None:
    assert api.get(SUGERIDOS, headers=cabeceras_admin).json()["items"] == []


def test_los_sugeridos_son_del_admin_y_de_su_plan(
    api, cabeceras_admin, enc_norte, db, variantes
) -> None:
    assert api.get(SUGERIDOS, headers=enc_norte).status_code == 403

    from app.modules.plataforma.models import Plan

    plan = db.get(Plan, 3)
    plan.funciones = {**plan.funciones, "traspasos_sugeridos": False}
    db.commit()
    r = api.get(SUGERIDOS, headers=cabeceras_admin)
    assert r.status_code == 403
    assert r.json()["codigo"] == "plan_limit" or "plan" in r.text


# =====================================================================
# Tanda C de la auditoría
# =====================================================================

def test_con_el_destino_dado_de_baja_el_origen_lo_recibe_de_vuelta(
    api, cabeceras_admin, enc_centro, enc_norte, centro, norte, variantes
) -> None:
    t = _pedir(api, enc_norte, variante=variantes[0], origen=centro, cantidad=4).json()
    api.post(f"{TRASPASOS}/{t['id']}/aprobar", headers=enc_centro)
    assert api.post(f"{TRASPASOS}/{t['id']}/enviar", headers=enc_centro).status_code == 200
    assert _saldo(api, cabeceras_admin, centro, variantes[0]) == 6

    # Mientras el destino está activo, devolver no corresponde.
    assert api.post(f"{TRASPASOS}/{t['id']}/devolver", headers=enc_centro).status_code == 409

    r = api.patch(f"/api/v1/organizacion/sucursales/{norte}/estado", headers=cabeceras_admin,
                  json={"activa": False})
    assert r.status_code == 200, r.text

    # Ya no se puede recibir allá, y el origen ve el botón para recuperarla.
    r = api.post(f"{TRASPASOS}/{t['id']}/recibir", headers=cabeceras_admin)
    assert r.status_code == 422, r.text
    detalle = api.get(f"{TRASPASOS}/{t['id']}", headers=enc_centro).json()
    assert detalle["acciones"] == ["DEVOLVER"]

    r = api.post(f"{TRASPASOS}/{t['id']}/devolver", headers=enc_centro)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RECIBIDO"
    assert _saldo(api, cabeceras_admin, centro, variantes[0]) == 10
    assert _saldo(api, cabeceras_admin, norte, variantes[0]) == 0


def test_crear_el_saldo_dos_veces_no_choca(db, norte, variantes) -> None:
    """Lo que pasa en dos recepciones simultáneas: la segunda creación del
    saldo de la misma prenda no revienta con la UNIQUE, toma la misma fila."""
    from app.core.tenencia import fijar_empresa
    from app.modules.inventario import repository as inventario_repo

    fijar_empresa(db, 1)
    a = inventario_repo.agregar_existencia(db, variante_id=variantes[0], sucursal_id=norte)
    b = inventario_repo.agregar_existencia(db, variante_id=variantes[0], sucursal_id=norte)
    assert a is not None and a.id == b.id
    db.rollback()
