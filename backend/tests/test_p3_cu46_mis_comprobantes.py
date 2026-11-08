"""CU-46 · Consultar mis comprobantes por voz (el «reporte transaccional»).

Lo que más importa cubrir
-------------------------
- **Aislamiento.** Un cliente no ve los comprobantes de otro cliente, ni los
  suyos de otra tienda (RLS + `cliente_empresa`).
- **Las reglas de interpretación**: cantidad, mes o rango, y tipo (compras,
  devoluciones, todo). Sin IA: no gasta el cupo de la tienda.
- **El pedido no entendido** responde «no entendí» con ejemplos y sin datos.
- **El QR y la verificación pública**: el token firmado no se puede fabricar,
  y la página no expone datos personales.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.tenencia import fijar_empresa
from app.modules.comprobantes import interprete, verificacion
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import Devolucion, Venta
from tests.conftest import CLAVE_CLIENTE, CORREO_CLIENTE, EMPRESA_PRUEBAS
from tests.test_multitenant import empresa_b  # noqa: F401 - fixture de pytest

CONSULTA = "/api/v1/tienda/mis-comprobantes/consulta"
PUBLICO = "/api/v1/publico/comprobantes"
HOY = date(2026, 11, 8)


# =====================================================================
# Armado: filas directas en la base, con la empresa de cada una
# =====================================================================

def _en_empresa(db, empresa_id: int):
    fijar_empresa(db, empresa_id)


def _sucursal(db, empresa_id: int, nombre: str = "Centro") -> int:
    _en_empresa(db, empresa_id)
    ciudad = db.scalar(select(Ciudad.id).where(Ciudad.nombre == "Santa Cruz"))
    sucursal = Sucursal(
        ciudad_id=ciudad, nombre=nombre, direccion="Av. Monseñor Rivero 100",
        horario_apertura=time(9), horario_cierre=time(20),
    )
    db.add(sucursal)
    db.commit()
    _en_empresa(db, EMPRESA_PRUEBAS)
    return sucursal.id


_secuencia = iter(range(1, 10_000))


def _venta(
    db, *, empresa_id: int, cliente_id: int, sucursal_id: int, total: str = "250.00",
    estado: str = "PAGADA", creado_en: datetime | None = None,
) -> Venta:
    _en_empresa(db, empresa_id)
    venta = Venta(
        codigo=f"VB-T{empresa_id}-{next(_secuencia):05d}",
        canal="DIGITAL",
        estado=estado,
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        modalidad_entrega="RETIRO",
        subtotal=Decimal(total),
        descuento=Decimal("0"),
        total=Decimal(total),
        creado_en=creado_en or datetime.now(timezone.utc),
    )
    db.add(venta)
    db.commit()
    _en_empresa(db, EMPRESA_PRUEBAS)
    return venta


def _devolucion(db, *, venta: Venta, usuario_id: int, empresa_id: int = EMPRESA_PRUEBAS) -> Devolucion:
    _en_empresa(db, empresa_id)
    devolucion = Devolucion(
        venta_id=venta.id, origen="WEB", recibida_por=usuario_id, tipo="DEVOLUCION",
        motivo="No me quedó", monto=Decimal("0"), estado="ABIERTA",
    )
    db.add(devolucion)
    db.commit()
    _en_empresa(db, EMPRESA_PRUEBAS)
    return devolucion


def _cliente(db, correo: str = CORREO_CLIENTE) -> tuple[int, int]:
    usuario = db.scalar(select(Usuario).where(Usuario.correo == correo))
    cliente = db.scalar(select(Cliente).where(Cliente.usuario_id == usuario.id))
    return cliente.id, usuario.id


def _otro_cliente(api: TestClient) -> dict[str, str]:
    r = api.post(
        "/api/v1/auth/registro",
        json={
            "nombres": "Bruno", "apellidos": "Suárez", "documento": "5554443",
            "telefono": "70099887", "correo": "bruno@correo.bo", "contrasena": "Secreta123",
        },
    )
    assert r.status_code == 201, r.text
    return _login(api, "bruno@correo.bo", "Secreta123")


def _login(api: TestClient, correo: str, clave: str, empresa: str = "violet-boutique") -> dict:
    r = api.post("/api/v1/auth/login", json={"empresa": empresa, "correo": correo, "contrasena": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _consultar(api: TestClient, cabeceras: dict, texto: str) -> dict:
    r = api.post(CONSULTA, headers=cabeceras, json={"texto": texto})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def sucursal(db) -> int:
    return _sucursal(db, EMPRESA_PRUEBAS)


# =====================================================================
# Autorización
# =====================================================================

def test_sin_token_no_hay_consulta(api: TestClient) -> None:
    assert api.post(CONSULTA, json={"texto": "mis compras"}).status_code == 401


def test_el_administrador_no_consulta_comprobantes_de_cliente(
    api: TestClient, cabeceras_admin: dict
) -> None:
    assert api.post(CONSULTA, headers=cabeceras_admin, json={"texto": "mis compras"}).status_code == 403


def test_el_texto_se_valida(api: TestClient, cabeceras_cliente: dict) -> None:
    assert api.post(CONSULTA, headers=cabeceras_cliente, json={"texto": "x"}).status_code == 422
    assert api.post(CONSULTA, headers=cabeceras_cliente, json={"texto": "a" * 301}).status_code == 422


# =====================================================================
# Aislamiento
# =====================================================================

def test_un_cliente_no_ve_los_comprobantes_de_otro(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    otro = _otro_cliente(api)
    ana, _ = _cliente(db)
    bruno, _ = _cliente(db, "bruno@correo.bo")
    propia = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal)
    ajena = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=bruno, sucursal_id=sucursal)

    de_ana = {c["referencia"] for c in _consultar(api, cabeceras_cliente, "todos mis comprobantes")["items"]}
    de_bruno = {c["referencia"] for c in _consultar(api, otro, "todos mis comprobantes")["items"]}

    assert de_ana == {propia.codigo}
    assert de_bruno == {ajena.codigo}


def test_un_cliente_no_ve_lo_suyo_de_otra_tienda(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int, empresa_b: int  # noqa: F811
) -> None:
    ana, usuario = _cliente(db)
    # Ana entra también a la tienda B: queda asociada a las dos (RN-13).
    en_b = _login(api, CORREO_CLIENTE, CLAVE_CLIENTE, "tienda-b")
    sucursal_b = _sucursal(db, empresa_b, "Centro B")
    venta_a = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal)
    venta_b = _venta(db, empresa_id=empresa_b, cliente_id=ana, sucursal_id=sucursal_b)
    _devolucion(db, venta=venta_b, usuario_id=usuario, empresa_id=empresa_b)

    en_a = _consultar(api, cabeceras_cliente, "todos mis comprobantes")
    en_tienda_b = _consultar(api, en_b, "todos mis comprobantes")

    assert {c["referencia"] for c in en_a["items"]} == {venta_a.codigo}
    assert {c["referencia"] for c in en_tienda_b["items"]} == {venta_b.codigo}
    assert {c["tipo"] for c in en_tienda_b["items"]} == {"COMPRA", "DEVOLUCION"}


# =====================================================================
# La consulta
# =====================================================================

def test_las_ultimas_n_compras_de_la_mas_nueva_a_la_mas_vieja(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, _ = _cliente(db)
    ventas = [
        _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
               creado_en=datetime(2026, 10, d, 15, tzinfo=timezone.utc))
        for d in (1, 5, 9, 12)
    ]

    cuerpo = _consultar(api, cabeceras_cliente, "mis últimas 3 compras")

    assert cuerpo["entendido"] is True
    assert cuerpo["interprete"] == "reglas"
    assert cuerpo["criterio"]["cantidad"] == 3
    assert [c["referencia"] for c in cuerpo["items"]] == [v.codigo for v in ventas[::-1][:3]]
    assert cuerpo["encontrados"] == 4
    primera = cuerpo["items"][0]
    assert primera["documento"] == "RECIBO"
    assert primera["codigo"] == f"R-{ventas[-1].id:08d}"
    assert primera["total"] == "250.00"
    # Hora de Bolivia: las 15:00 UTC son las 11:00 en Santa Cruz.
    assert primera["fecha"].endswith("-04:00")
    assert primera["fecha_texto"] == "12/10/2026 11:00"
    assert primera["descargable"] is True
    assert primera["url_verificacion"].endswith(f"/verificar/{primera['token']}")


def test_los_recibos_de_un_mes(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, _ = _cliente(db)
    _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
           creado_en=datetime(2025, 9, 30, 12, tzinfo=timezone.utc))
    de_octubre = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
                        creado_en=datetime(2025, 10, 15, 12, tzinfo=timezone.utc))
    # El 1/11 a las 02:00 UTC todavía es 31 de octubre en Bolivia.
    tarde = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
                   creado_en=datetime(2025, 11, 1, 2, tzinfo=timezone.utc))

    cuerpo = _consultar(api, cabeceras_cliente, "mis recibos de octubre de 2025")

    assert cuerpo["criterio"]["desde"] == "2025-10-01"
    assert cuerpo["criterio"]["hasta"] == "2025-10-31"
    assert {c["referencia"] for c in cuerpo["items"]} == {de_octubre.codigo, tarde.codigo}


def test_las_devoluciones_son_notas_nd(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, usuario = _cliente(db)
    venta = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
                   estado="ENTREGADA")
    nota = _devolucion(db, venta=venta, usuario_id=usuario)

    cuerpo = _consultar(api, cabeceras_cliente, "mis devoluciones")

    assert [c["codigo"] for c in cuerpo["items"]] == [f"ND-{nota.id:06d}"]
    item = cuerpo["items"][0]
    assert item["tipo"] == "DEVOLUCION"
    assert item["documento"] == "NOTA_DEVOLUCION"
    assert item["estado"] == "ABIERTA"
    assert item["referencia"] == venta.codigo
    assert item["token"]


def test_la_compra_sin_pagar_aparece_pero_sin_comprobante(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, _ = _cliente(db)
    venta = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
                   estado="PENDIENTE_PAGO")

    item = _consultar(api, cabeceras_cliente, "mis compras")["items"][0]

    assert item["codigo"] == venta.codigo
    assert item["documento"] is None
    assert item["token"] is None
    assert item["descargable"] is False


def test_el_limite_es_cincuenta(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    cuerpo = _consultar(api, cabeceras_cliente, "mis últimas 500 compras")

    assert cuerpo["criterio"]["cantidad"] == interprete.MAXIMO == 50
    assert any("50" in a for a in cuerpo["avisos"])


def test_el_pedido_no_entendido_no_inventa_datos(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, _ = _cliente(db)
    _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal)

    cuerpo = _consultar(api, cabeceras_cliente, "hola, qué tal el clima")

    assert cuerpo["entendido"] is False
    assert cuerpo["items"] == []
    assert cuerpo["criterio"] is None
    assert cuerpo["motivo"]
    assert "Mis últimas 3 compras" in cuerpo["ejemplos"]


def test_la_consulta_queda_en_la_bitacora(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    from app.modules.bitacora.models import AsientoBitacora

    _consultar(api, cabeceras_cliente, "mis compras")

    db.expire_all()
    rutas = db.scalars(select(AsientoBitacora.ruta)).all()
    assert any(r and r.endswith("/tienda/mis-comprobantes/consulta") for r in rutas)


# =====================================================================
# Las reglas (unitarias, con un «hoy» fijo)
# =====================================================================

@pytest.mark.parametrize(
    ("texto", "tipo", "cantidad", "desde", "hasta"),
    [
        ("mis últimas 3 compras", "COMPRAS", 3, None, None),
        ("Mis tres últimas compras", "COMPRAS", 3, None, None),
        ("mi última compra", "COMPRAS", 1, None, None),
        ("mis recibos de octubre", "COMPRAS", None, date(2026, 10, 1), date(2026, 10, 31)),
        ("mis facturas de diciembre", "COMPRAS", None, date(2025, 12, 1), date(2025, 12, 31)),
        ("mis devoluciones", "DEVOLUCIONES", None, None, None),
        ("mis notas de devolución del mes pasado", "DEVOLUCIONES", None, date(2026, 10, 1), date(2026, 10, 31)),
        ("todos mis comprobantes", "TODO", None, None, None),
        ("mis compras y devoluciones de este año", "TODO", None, date(2026, 1, 1), HOY),
        ("mis compras de los últimos 3 meses", "COMPRAS", None, date(2026, 9, 1), HOY),
        ("mis compras del 01/10/2026 al 15/10/2026", "COMPRAS", None, date(2026, 10, 1), date(2026, 10, 15)),
        ("mis recibos del 1 al 15 de octubre", "COMPRAS", None, date(2026, 10, 1), date(2026, 10, 15)),
        ("mis compras desde el 5/10", "COMPRAS", None, date(2026, 10, 5), None),
        ("las últimas 5", "TODO", 5, None, None),
    ],
)
def test_reglas_de_interpretacion(texto, tipo, cantidad, desde, hasta) -> None:
    criterio = interprete.interpretar(texto, HOY)

    assert criterio is not None
    assert (criterio.tipo, criterio.cantidad, criterio.desde, criterio.hasta) == (
        tipo, cantidad, desde, hasta
    )


def test_reglas_del_estado() -> None:
    assert interprete.interpretar("mis compras pagadas", HOY).estado == "PAGADA"
    assert interprete.interpretar("mis compras pendientes", HOY).estado == "PENDIENTE_PAGO"
    assert interprete.interpretar("mis devoluciones abiertas", HOY).estado == "ABIERTA"


@pytest.mark.parametrize("texto", ["hola", "quiero un vestido rojo", "¿abren el domingo?", "   "])
def test_lo_que_no_es_un_pedido_de_comprobantes_no_se_entiende(texto) -> None:
    assert interprete.interpretar(texto, HOY) is None


def test_el_resumen_dice_lo_que_entendio() -> None:
    assert interprete.resumir(interprete.interpretar("mis últimas 3 compras", HOY)) == (
        "Tus últimas 3 compras"
    )
    assert interprete.resumir(interprete.interpretar("mis recibos de octubre", HOY)) == (
        "Tus compras del 01/10/2026 al 31/10/2026"
    )


# =====================================================================
# QR y verificación pública
# =====================================================================

def test_la_verificacion_publica_no_expone_datos_personales(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, _ = _cliente(db)
    venta = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal,
                   total="480.50")
    token = _consultar(api, cabeceras_cliente, "mis compras")["items"][0]["token"]

    r = api.get(f"{PUBLICO}/{token}")  # sin sesión

    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["codigo"] == f"R-{venta.id:08d}"
    assert cuerpo["referencia"] == venta.codigo
    assert cuerpo["total"] == "480.50"
    assert cuerpo["estado"] == "PAGADA"
    assert cuerpo["tienda"] == "Violet Boutique"
    texto = r.text.lower()
    for dato_personal in ("ana", "quiroga", "9876543", "70011223", "@"):
        assert dato_personal not in texto


def test_la_verificacion_de_una_nota_de_devolucion(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, usuario = _cliente(db)
    venta = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal)
    nota = _devolucion(db, venta=venta, usuario_id=usuario)

    token = verificacion.firmar(verificacion.NOTA, EMPRESA_PRUEBAS, nota.id)
    cuerpo = api.get(f"{PUBLICO}/{token}").json()

    assert cuerpo["documento"] == "NOTA_DEVOLUCION"
    assert cuerpo["codigo"] == f"ND-{nota.id:06d}"


def test_un_token_alterado_o_inventado_no_sirve(
    api: TestClient, db, cabeceras_cliente: dict, sucursal: int
) -> None:
    ana, _ = _cliente(db)
    venta = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=ana, sucursal_id=sucursal)
    token = verificacion.firmar(verificacion.RECIBO, EMPRESA_PRUEBAS, venta.id)
    cuerpo, firma = token.split(".")

    # Otro número con la misma firma: la firma ya no corresponde.
    otro = f"V{EMPRESA_PRUEBAS}-{venta.id + 1}.{firma}"
    assert api.get(f"{PUBLICO}/{otro}").status_code == 404
    # Sin firma, o con basura.
    assert api.get(f"{PUBLICO}/{cuerpo}").status_code == 404
    assert api.get(f"{PUBLICO}/hola").status_code == 404
    assert api.get(f"{PUBLICO}/{otro}/qr.svg").status_code == 404
    # El bueno, sí.
    assert api.get(f"{PUBLICO}/{token}").status_code == 200


def test_el_token_de_otra_empresa_no_encuentra_la_venta(
    api: TestClient, db, sucursal: int, empresa_b: int  # noqa: F811
) -> None:
    """La empresa del token fija el RLS: una venta de A con un token de B no existe."""
    venta = _venta(db, empresa_id=EMPRESA_PRUEBAS, cliente_id=None, sucursal_id=sucursal)
    token = verificacion.firmar(verificacion.RECIBO, empresa_b, venta.id)

    assert api.get(f"{PUBLICO}/{token}").status_code == 404


def test_el_qr_lleva_a_la_pagina_de_verificacion(api: TestClient) -> None:
    token = verificacion.firmar(verificacion.RECIBO, EMPRESA_PRUEBAS, 42)

    svg = api.get(f"{PUBLICO}/{token}/qr.svg")
    matriz = api.get(f"{PUBLICO}/{token}/qr").json()

    assert svg.status_code == 200
    assert svg.headers["content-type"].startswith("image/svg+xml")
    assert svg.text.startswith("<svg") and "<path" in svg.text
    assert matriz["texto"].endswith(f"/verificar/{token}")
    n = len(matriz["modulos"])
    assert n >= 21 and all(len(fila) == n for fila in matriz["modulos"])
    # El token es estable: el QR del PDF y el de la pantalla son el mismo.
    assert verificacion.firmar(verificacion.RECIBO, EMPRESA_PRUEBAS, 42) == token
