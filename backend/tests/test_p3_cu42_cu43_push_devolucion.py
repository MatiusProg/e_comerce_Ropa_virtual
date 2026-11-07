"""CU-42 Enviar avisos push de las operaciones sin conexión
CU-43 Devolver automáticamente el pago de una operación rechazada

Lo que más importa cubrir
-------------------------
- **CU-43, por el mismo medio:** un QR rechazado se reintegra solo (nace
  devuelto, sin responsable, con su referencia) y ya no aparece para CU-19;
  el efectivo queda para entregar en la sucursal y le avisa al encargado.
- **El cliente opcional de la venta offline** recibe sus avisos; uno ajeno se
  ignora sin rechazar una venta ya cobrada.
- **CU-42:** el cajero recibe UN resumen por lote (no uno por operación) y un
  reintento no lo repite; el push sale a sus dispositivos y un dispositivo que
  ya no existe se borra.
- **Los dispositivos:** alta idempotente, pasa de dueño, baja, y Web Push exige
  sus claves.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.integrations.push.simulado import ENVIADOS
from app.modules.notificaciones.models import Notificacion, SuscripcionPush
from app.modules.offline.models import OperacionOffline
from app.modules.ventas.models import Venta
from tests.test_cu31_venta_presencial import (
    PRECIO,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _crear_variantes,
    _empleado,
    _ingresar,
    _manana,
)

PAQUETE = "/api/v1/offline/paquete"
SINCRONIZAR = "/api/v1/offline/sincronizar"
OPERACIONES = "/api/v1/offline/operaciones"
NOTIFICACIONES = "/api/v1/notificaciones"
DISPOSITIVOS = "/api/v1/notificaciones/push/dispositivos"
DESPACHO_PUSH = "/api/v1/mantenimiento/notificaciones/despacho-push"


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture(autouse=True)
def _sin_push_previo():
    ENVIADOS.clear()
    yield
    ENVIADOS.clear()


@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict, sucursal: int) -> list[int]:
    ids = _crear_variantes(api, cabeceras_admin)
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(ids[0], 10), (ids[1], 2)])
    return ids


@pytest.fixture
def cajero(api: TestClient, cabeceras_admin: dict, sucursal: int, db) -> dict:
    cab = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="4")
    turno_id = _abrir_turno(api, cab, _caja(db, sucursal))
    return {"cab": cab, "turno_id": turno_id}


@pytest.fixture
def encargado(api: TestClient, cabeceras_admin: dict, sucursal: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=sucursal, sufijo="4")


@pytest.fixture
def cliente_id(api: TestClient, cabeceras_cliente: dict, cajero: dict) -> int:
    """El cliente tal como lo ve el cajero en el paquete de CU-13."""
    paquete = api.get(PAQUETE, headers=cajero["cab"]).json()
    [cliente] = [c for c in paquete["clientes"] if c["documento"] == "9876543"]
    return cliente["id"]


def _venta(turno_id: int, variante_id: int, cantidad: int = 1, *, cliente_id=None, **pago) -> dict:
    total = PRECIO * cantidad
    op = {
        "uuid": str(uuid.uuid4()),
        "tipo": "VENTA",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "turno_caja_id": turno_id,
        "lineas": [
            {"variante_id": variante_id, "cantidad": cantidad, "precio_unitario": str(PRECIO)}
        ],
        "pago": {"metodo": "EFECTIVO", "monto": str(total), **pago},
    }
    if cliente_id is not None:
        op["cliente_id"] = cliente_id
    return op


def _qr(turno_id: int, variante_id: int, cantidad: int = 1, **kw) -> dict:
    return _venta(
        turno_id, variante_id, cantidad, metodo="QR", referencia="BNB-555", **kw
    )


def _sincronizar(api: TestClient, cab: dict, *operaciones: dict) -> list[dict]:
    r = api.post(
        SINCRONIZAR, headers=cab, json={"dispositivo": "pruebas", "operaciones": list(operaciones)}
    )
    assert r.status_code == 200, r.text
    return r.json()["resultados"]


def _avisos(api: TestClient, cab: dict) -> list[dict]:
    r = api.get(NOTIFICACIONES, headers=cab)
    assert r.status_code == 200, r.text
    return r.json()["items"]


def _registrar(api: TestClient, cab: dict, direccion: str, canal: str = "FCM", **extra):
    return api.post(
        DISPOSITIVOS, headers=cab, json={"canal": canal, "direccion": direccion, **extra}
    )


# =====================================================================
# CU-43: la devolución automática
# =====================================================================

def test_qr_rechazado_se_reintegra_solo_y_no_queda_para_cu19(
    api: TestClient, cajero: dict, encargado: dict, variantes: list[int], db
) -> None:
    op = _qr(cajero["turno_id"], variantes[1], cantidad=5)  # hay 2: se rechaza
    [r] = _sincronizar(api, cajero["cab"], op)

    assert r["estado"] == "RECHAZADA"
    assert r["devolucion_automatica"] is True
    assert r["devuelta"] is True
    assert r["requiere_devolucion"] is False
    assert r["referencia_devolucion"].startswith("REINT-QR-")

    fila = db.scalar(select(OperacionOffline).where(OperacionOffline.uuid == uuid.UUID(op["uuid"])))
    assert fila.devuelto_por is None
    assert fila.metodo_devolucion == "QR"
    assert "BNB-555" in fila.observacion_devolucion

    # CU-19 ya no la lista ni la deja registrar de nuevo.
    assert api.get(OPERACIONES, headers=encargado, params={"por_devolver": True}).json() == []
    otra = api.post(
        f"{OPERACIONES}/{op['uuid']}/devolucion",
        headers=encargado,
        json={"metodo": "QR", "referencia": "BNB-1"},
    )
    assert otra.status_code == 409
    assert "reintegró" in otra.json()["detail"]


def test_efectivo_rechazado_queda_para_la_sucursal_y_avisa_al_encargado(
    api: TestClient, cajero: dict, encargado: dict, variantes: list[int]
) -> None:
    op = _venta(cajero["turno_id"], variantes[1], cantidad=5)
    [r] = _sincronizar(api, cajero["cab"], op)
    assert r["requiere_devolucion"] is True
    assert r["devolucion_automatica"] is False

    pendientes = api.get(OPERACIONES, headers=encargado, params={"por_devolver": True}).json()
    assert [p["uuid"] for p in pendientes] == [op["uuid"]]

    [aviso] = [a for a in _avisos(api, encargado) if a["tipo"] == "DEVOLUCION_PAGO"]
    assert "efectivo" in aviso["titulo"]
    assert str(PRECIO * 5) in aviso["titulo"]
    assert aviso["enlace"] == "/sucursal/sin-conexion"


def test_la_venta_offline_con_cliente_queda_a_su_nombre_y_le_avisa(
    api: TestClient, cajero: dict, cabeceras_cliente: dict, cliente_id: int,
    variantes: list[int], db,
) -> None:
    [r] = _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0], cliente_id=cliente_id))
    assert r["estado"] == "CONFIRMADA"
    venta = db.scalar(select(Venta).where(Venta.codigo == r["venta_codigo"]))
    assert venta.cliente_id == cliente_id

    [aviso] = _avisos(api, cabeceras_cliente)
    assert aviso["tipo"] == "OPERACION_OFFLINE"
    assert r["venta_codigo"] in aviso["titulo"]
    assert aviso["enlace"] == "/mi-cuenta/compras"


def test_al_cliente_le_avisan_que_se_le_reintegro_el_qr(
    api: TestClient, cajero: dict, cabeceras_cliente: dict, cliente_id: int, variantes: list[int]
) -> None:
    [r] = _sincronizar(
        api, cajero["cab"], _qr(cajero["turno_id"], variantes[1], 5, cliente_id=cliente_id)
    )
    avisos = {a["tipo"]: a for a in _avisos(api, cabeceras_cliente)}
    assert set(avisos) == {"OPERACION_OFFLINE", "DEVOLUCION_PAGO"}
    assert "No pudimos confirmar" in avisos["OPERACION_OFFLINE"]["titulo"]
    assert "por QR" in avisos["DEVOLUCION_PAGO"]["titulo"]
    assert r["referencia_devolucion"] in avisos["DEVOLUCION_PAGO"]["cuerpo"]


def test_al_cliente_le_avisan_donde_retirar_el_efectivo(
    api: TestClient, cajero: dict, cabeceras_cliente: dict, cliente_id: int, variantes: list[int]
) -> None:
    _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[1], 5, cliente_id=cliente_id))
    [devolucion] = [a for a in _avisos(api, cabeceras_cliente) if a["tipo"] == "DEVOLUCION_PAGO"]
    assert "Centro" in devolucion["titulo"]


def test_un_cliente_ajeno_se_ignora_sin_rechazar_la_venta(
    api: TestClient, cajero: dict, variantes: list[int], db
) -> None:
    [r] = _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0], cliente_id=999999))
    assert r["estado"] == "CONFIRMADA"
    venta = db.scalar(select(Venta).where(Venta.codigo == r["venta_codigo"]))
    assert venta.cliente_id is None


def test_la_reserva_del_cliente_rechazada_le_avisa_sin_dinero_que_devolver(
    api: TestClient, cabeceras_cliente: dict, variantes: list[int], sucursal: int
) -> None:
    op = {
        "uuid": str(uuid.uuid4()),
        "tipo": "RESERVA",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "sucursal_id": sucursal,
        "franja_inicio": _manana(6).isoformat(),  # fuera de horario
        "franja_fin": _manana(7).isoformat(),
        "lineas": [{"variante_id": variantes[0], "cantidad": 1, "precio_unitario": str(PRECIO)}],
    }
    [r] = _sincronizar(api, cabeceras_cliente, op)
    # Una reserva no se cobra (auditoría del 05/11): no hay nada que reintegrar.
    assert r["devolucion_automatica"] is False
    tipos = sorted(a["tipo"] for a in _avisos(api, cabeceras_cliente))
    # Solo el aviso de la reserva; al cliente no le llega resumen.
    assert tipos == ["OPERACION_OFFLINE"]


# =====================================================================
# CU-42: el resumen del lote y el push
# =====================================================================

def test_el_cajero_recibe_un_solo_resumen_por_lote(
    api: TestClient, cajero: dict, variantes: list[int]
) -> None:
    ops = [
        _venta(cajero["turno_id"], variantes[0]),
        _venta(cajero["turno_id"], variantes[0]),
        _qr(cajero["turno_id"], variantes[1], 5),
    ]
    _sincronizar(api, cajero["cab"], *ops)
    [resumen] = _avisos(api, cajero["cab"])
    assert resumen["tipo"] == "OPERACION_OFFLINE"
    assert "1 rechazada(s), 2 confirmada(s)" in resumen["titulo"]
    assert "reintegró por QR" in resumen["cuerpo"]
    assert resumen["enlace"] == "/caja/pendientes"

    # El reintento del mismo lote no vuelve a avisar.
    _sincronizar(api, cajero["cab"], *ops)
    assert len(_avisos(api, cajero["cab"])) == 1


def test_el_push_sale_al_dispositivo_del_cajero(
    api: TestClient, cajero: dict, variantes: list[int], db
) -> None:
    assert _registrar(api, cajero["cab"], "token-fcm-del-cajero-0001").status_code == 201
    _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0]))

    [(destino, aviso)] = ENVIADOS
    assert destino.canal == "FCM"
    assert destino.direccion == "token-fcm-del-cajero-0001"
    assert "confirmada" in aviso.titulo
    assert aviso.enlace == "/caja/pendientes"
    assert aviso.datos["tipo"] == "OPERACION_OFFLINE"

    [n] = db.scalars(select(Notificacion)).all()
    assert n.push_estado == "ENVIADO"
    assert n.push_enviado_en is not None


def test_sin_dispositivos_el_push_se_omite(
    api: TestClient, cajero: dict, variantes: list[int], db
) -> None:
    _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0]))
    assert ENVIADOS == []
    [n] = db.scalars(select(Notificacion)).all()
    assert n.push_estado == "OMITIDO"


def test_un_dispositivo_que_ya_no_existe_se_borra(
    api: TestClient, cajero: dict, variantes: list[int], db
) -> None:
    _registrar(api, cajero["cab"], "invalida-app-desinstalada")
    _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0]))

    [n] = db.scalars(select(Notificacion)).all()
    assert n.push_estado == "FALLIDO"
    assert "ya no está registrado" in n.push_error
    db.expire_all()
    assert db.scalars(select(SuscripcionPush)).all() == []


def test_el_push_llega_a_todos_los_dispositivos_del_cliente(
    api: TestClient, cajero: dict, cabeceras_cliente: dict, cliente_id: int, variantes: list[int]
) -> None:
    _registrar(api, cabeceras_cliente, "token-fcm-telefono-ana")
    _registrar(
        api, cabeceras_cliente, "https://fcm.googleapis.com/fcm/send/navegador-ana",
        canal="WEBPUSH", clave_p256dh="BExampleKey", clave_auth="authsecreto",
    )
    _sincronizar(api, cajero["cab"], _venta(cajero["turno_id"], variantes[0], cliente_id=cliente_id))
    al_cliente = [d.canal for d, a in ENVIADOS if "Su compra" in a.titulo]
    assert sorted(al_cliente) == ["FCM", "WEBPUSH"]


def test_el_despacho_de_mantenimiento_toma_los_pendientes(
    api: TestClient, cabeceras_admin: dict, cajero: dict, db
) -> None:
    from app.modules.notificaciones import service as notificaciones
    from app.modules.seguridad.models import Usuario

    _registrar(api, cajero["cab"], "token-fcm-del-cajero-0002")
    usuario = db.scalar(select(Usuario).where(Usuario.correo == "cajero4@violetboutique.bo"))
    notificaciones.notificar(
        db, destinatario=usuario, tipo="STOCK_BAJO", titulo="Prueba", cuerpo="Aviso de prueba"
    )
    db.commit()

    r = api.post(DESPACHO_PUSH, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert r.json() == {"intentadas": 1, "enviadas": 1, "fallidas": 0}
    assert api.post(DESPACHO_PUSH, headers=cabeceras_admin).json()["intentadas"] == 0
    assert len(ENVIADOS) == 1


# =====================================================================
# CU-42: los dispositivos
# =====================================================================

def test_el_alta_es_idempotente_y_la_baja_lo_quita(
    api: TestClient, cabeceras_cliente: dict
) -> None:
    assert _registrar(api, cabeceras_cliente, "token-fcm-repetido-01").status_code == 201
    assert _registrar(api, cabeceras_cliente, "token-fcm-repetido-01").status_code == 201
    assert len(api.get(DISPOSITIVOS, headers=cabeceras_cliente).json()) == 1

    r = api.post(f"{DISPOSITIVOS}/baja", headers=cabeceras_cliente,
                 json={"direccion": "token-fcm-repetido-01"})
    assert r.status_code == 204
    assert api.get(DISPOSITIVOS, headers=cabeceras_cliente).json() == []
    # Dos veces no es un error.
    assert api.post(f"{DISPOSITIVOS}/baja", headers=cabeceras_cliente,
                    json={"direccion": "token-fcm-repetido-01"}).status_code == 204


def test_el_dispositivo_pasa_a_quien_inicio_sesion_ahora(
    api: TestClient, cajero: dict, encargado: dict
) -> None:
    _registrar(api, cajero["cab"], "telefono-de-la-caja-01")
    _registrar(api, encargado, "telefono-de-la-caja-01")
    assert api.get(DISPOSITIVOS, headers=cajero["cab"]).json() == []
    assert len(api.get(DISPOSITIVOS, headers=encargado).json()) == 1


def test_webpush_exige_claves_y_https(api: TestClient, cabeceras_cliente: dict) -> None:
    sin_claves = _registrar(api, cabeceras_cliente, "https://push.example/abc", canal="WEBPUSH")
    assert sin_claves.status_code == 422
    sin_https = _registrar(
        api, cabeceras_cliente, "http://push.example/abc", canal="WEBPUSH",
        clave_p256dh="x" * 20, clave_auth="y" * 10,
    )
    assert sin_https.status_code == 422


def test_la_configuracion_dice_si_hay_web_push(api: TestClient, cabeceras_cliente: dict) -> None:
    r = api.get(f"{NOTIFICACIONES}/push/configuracion", headers=cabeceras_cliente)
    assert r.status_code == 200
    assert r.json()["simulado"] is True


def test_sin_sesion_no_se_registra_un_dispositivo(api: TestClient) -> None:
    assert api.post(DISPOSITIVOS, json={"canal": "FCM", "direccion": "x" * 20}).status_code == 401


# --- Tanda B de la auditoría: seguridad de los dispositivos -----------------

_CLAVES = {"clave_p256dh": "p" * 40, "clave_auth": "a" * 16}


def test_webpush_solo_acepta_servicios_de_push_conocidos(
    api: TestClient, cabeceras_cliente: dict
) -> None:
    # El servidor le hace un POST al endpoint: una URL interna sería SSRF.
    for url in ("https://169.254.169.254/latest/meta-data",
                "https://fcm.googleapis.com.evil.example/x",
                "https://localhost:8000/api/v1/x"):
        r = _registrar(api, cabeceras_cliente, url, canal="WEBPUSH", **_CLAVES)
        assert r.status_code == 422, url
    for url in ("https://fcm.googleapis.com/fcm/send/abc",
                "https://updates.push.services.mozilla.com/wpush/v2/abc",
                "https://wns2-bl2p.notify.windows.com/w/?token=abc",
                "https://web.push.apple.com/abc"):
        assert _registrar(api, cabeceras_cliente, url, canal="WEBPUSH",
                          **_CLAVES).status_code == 201, url


def test_un_navegador_ajeno_no_se_reasigna_sin_sus_claves(
    api: TestClient, cajero: dict, encargado: dict
) -> None:
    url = "https://fcm.googleapis.com/fcm/send/navegador-de-la-caja"
    assert _registrar(api, cajero["cab"], url, canal="WEBPUSH", **_CLAVES).status_code == 201

    # Con saber el endpoint no alcanza: sin las mismas claves, 409.
    otras = {"clave_p256dh": "q" * 40, "clave_auth": "b" * 16}
    r = _registrar(api, encargado, url, canal="WEBPUSH", **otras)
    assert r.status_code == 409, r.text
    assert len(api.get(DISPOSITIVOS, headers=cajero["cab"]).json()) == 1
    assert api.get(DISPOSITIVOS, headers=encargado).json() == []

    # El mismo navegador (mismas claves) sí pasa a quien inició sesión ahora.
    assert _registrar(api, encargado, url, canal="WEBPUSH", **_CLAVES).status_code == 201
    assert api.get(DISPOSITIVOS, headers=cajero["cab"]).json() == []
    assert len(api.get(DISPOSITIVOS, headers=encargado).json()) == 1
