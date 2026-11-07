"""Aporte propio · «Avísame cuando llegue mi talla».

El cliente pide el aviso de una talla y color sin unidades; cuando el
inventario la repone ---por cualquier camino--- le llega una notificación una
sola vez. El personal ve cuántos clientes esperan cada talla.
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.core.tenencia import CLAVE_EMPRESA
from app.modules.avisos_talla.models import AvisoTalla
from app.modules.inventario import service as inventario
from app.modules.notificaciones.models import Notificacion
from tests.test_cu36_tablero import _crear_sucursal, _crear_variantes, _ingresar
from tests.test_multitenant import empresa_b  # noqa: F401  (fixture)

AVISOS = "/api/v1/tienda/avisos-talla"
DEMANDA = "/api/v1/inventario/avisos-talla"


def _tienda(api, admin) -> dict:
    sucursal = _crear_sucursal(api, admin, nombre="Centro")
    s, m = _crear_variantes(api, admin)
    return {"sucursal": sucursal, "s": s, "m": m}


def _avisos_de_stock(db) -> int:
    return db.scalar(
        select(func.count()).select_from(Notificacion).where(Notificacion.tipo == "STOCK_DISPONIBLE")
    )


def test_el_cliente_pide_el_aviso_de_una_talla_agotada(api, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)

    r = api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "ESPERANDO"
    assert cuerpo["talla"] == "S"
    assert cuerpo["producto"] == "Blusa de seda"
    assert api.get(f"{AVISOS}/variantes", headers=cabeceras_cliente).json() == [t["s"]]


def test_pedirlo_dos_veces_deja_uno_solo(api, db, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)

    primero = api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})
    segundo = api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    assert segundo.status_code == 201
    assert segundo.json()["id"] == primero.json()["id"]
    assert len(api.get(AVISOS, headers=cabeceras_cliente).json()) == 1


def test_no_se_pide_aviso_de_lo_que_ya_tiene_unidades(api, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)
    _ingresar(api, cabeceras_admin, sucursal_id=t["sucursal"], lineas=[(t["s"], 2)])

    r = api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    assert r.status_code == 409


def test_variante_inexistente_da_404(api, cabeceras_admin, cabeceras_cliente):
    _tienda(api, cabeceras_admin)
    r = api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": 999999})
    assert r.status_code == 404


def test_un_ingreso_avisa_una_sola_vez(api, db, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)
    api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    _ingresar(api, cabeceras_admin, sucursal_id=t["sucursal"], lineas=[(t["s"], 3)])

    db.expire_all()
    assert _avisos_de_stock(db) == 1
    nota = db.scalar(select(Notificacion).where(Notificacion.tipo == "STOCK_DISPONIBLE"))
    assert "Blusa de seda" in nota.titulo
    assert nota.enlace.startswith("/tienda/producto/")
    aviso = api.get(AVISOS, headers=cabeceras_cliente).json()[0]
    assert aviso["estado"] == "AVISADO"
    assert aviso["notificado_en"] is not None

    # Un segundo ingreso ya no es noticia: la talla no estaba agotada.
    _ingresar(api, cabeceras_admin, sucursal_id=t["sucursal"], lineas=[(t["s"], 2)])
    db.expire_all()
    assert _avisos_de_stock(db) == 1


def test_reponer_otra_talla_no_avisa(api, db, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)
    api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    _ingresar(api, cabeceras_admin, sucursal_id=t["sucursal"], lineas=[(t["m"], 3)])

    db.expire_all()
    assert _avisos_de_stock(db) == 0
    assert api.get(AVISOS, headers=cabeceras_cliente).json()[0]["estado"] == "ESPERANDO"


def test_una_devolucion_que_reingresa_la_prenda_tambien_avisa(
    api, db, cabeceras_admin, cabeceras_cliente
):
    t = _tienda(api, cabeceras_admin)
    api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    # El mismo servicio que usan la caja (CU-22) y la devolución web (CU-25).
    inventario.reingresar_por_devolucion(
        db, variante_id=t["s"], sucursal_id=t["sucursal"], cantidad=1, usuario_id=None,
        motivo="Devolución de prueba",
    )
    db.commit()

    assert _avisos_de_stock(db) == 1
    assert db.scalar(select(AvisoTalla.notificado_en)) is not None


def test_si_el_movimiento_se_deshace_el_aviso_tambien(api, db, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)
    api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    inventario.reingresar_por_devolucion(
        db, variante_id=t["s"], sucursal_id=t["sucursal"], cantidad=1, usuario_id=None,
    )
    db.rollback()

    assert _avisos_de_stock(db) == 0
    assert db.scalar(select(AvisoTalla.notificado_en)) is None


def test_el_cliente_cancela_su_aviso(api, db, cabeceras_admin, cabeceras_cliente):
    t = _tienda(api, cabeceras_admin)
    aviso = api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]}).json()

    r = api.delete(f"{AVISOS}/{aviso['id']}", headers=cabeceras_cliente)

    assert r.status_code == 204
    assert api.get(AVISOS, headers=cabeceras_cliente).json() == []
    assert api.delete(f"{AVISOS}/{aviso['id']}", headers=cabeceras_cliente).status_code == 404
    # Cancelado, reponer ya no le avisa a nadie.
    _ingresar(api, cabeceras_admin, sucursal_id=t["sucursal"], lineas=[(t["s"], 1)])
    db.expire_all()
    assert _avisos_de_stock(db) == 0


def test_el_personal_no_pide_avisos_y_el_cliente_no_ve_la_demanda(
    api, cabeceras_admin, cabeceras_cliente
):
    t = _tienda(api, cabeceras_admin)

    assert (
        api.post(AVISOS, headers=cabeceras_admin, json={"variante_id": t["s"]}).status_code == 403
    )
    assert api.get(DEMANDA, headers=cabeceras_cliente).status_code == 403


def test_el_personal_ve_cuantos_clientes_esperan_cada_talla(
    api, cabeceras_admin, cabeceras_cliente
):
    t = _tienda(api, cabeceras_admin)
    api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    r = api.get(DEMANDA, headers=cabeceras_admin)

    assert r.status_code == 200, r.text
    filas = r.json()
    assert len(filas) == 1
    assert filas[0]["variante_id"] == t["s"]
    assert filas[0]["clientes"] == 1
    assert filas[0]["talla"] == "S"

    # Cuando la talla vuelve, deja de figurar como demanda que espera.
    _ingresar(api, cabeceras_admin, sucursal_id=t["sucursal"], lineas=[(t["s"], 1)])
    assert api.get(DEMANDA, headers=cabeceras_admin).json() == []


def test_otra_empresa_no_ve_los_avisos(
    api, db, fabrica_sesiones, cabeceras_admin, cabeceras_cliente, empresa_b  # noqa: F811
):
    t = _tienda(api, cabeceras_admin)
    api.post(AVISOS, headers=cabeceras_cliente, json={"variante_id": t["s"]})

    ajena = fabrica_sesiones()
    ajena.info[CLAVE_EMPRESA] = empresa_b
    try:
        assert ajena.scalar(select(func.count()).select_from(AvisoTalla)) == 0
    finally:
        ajena.close()
    assert db.scalar(select(func.count()).select_from(AvisoTalla)) == 1
