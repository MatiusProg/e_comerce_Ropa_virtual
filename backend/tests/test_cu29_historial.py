"""CU-29 · Consultar historial de compras.

Realiza parte del **RF15** y **RF16**. Es el caso de uso que cierra el flujo del
cliente: hasta ahora alguien compraba y **no tenía dónde ver lo que compró** —
sólo llegaba a su pedido si conservaba el código de la URL.

Lo que más importa cubrir
-------------------------
- **Van todas las compras, no sólo las pagadas.** Un historial que escondiera
  las canceladas y las que esperan pago dejaría al cliente sin forma de
  encontrar el pedido que acaba de hacer, que es justo el que va a buscar.
- **Una compra ajena no existe.** 404 y nunca 403: un 403 confirmaría que ese
  código corresponde a una compra real.
- **El comprobante se emite UNA vez y se reimprime siempre.** Si cada descarga
  generara un número nuevo, no serviría como comprobante de nada. Es lo que
  garantiza el `UNIQUE` sobre `comprobante.venta_id`.
- **Sin pagar no hay comprobante**, y se distingue de «no existe»: 409 y no
  404, porque lo que el cliente hace después es distinto.
"""

import pytest
from fastapi.testclient import TestClient

COMPRAS = "/api/v1/tienda/compras"
CARRITO = "/api/v1/tienda/carrito"
PEDIDOS = "/api/v1/tienda/pedidos"
SIMULACION = "/api/v1/pagos/simulacion"

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
CIUDADES = "/api/v1/organizacion/ciudades"
SUCURSALES = "/api/v1/organizacion/sucursales"
INGRESOS = "/api/v1/inventario/ingresos"
PROVEEDORES = "/api/v1/organizacion/proveedores"

PRECIO = 250


# --- Armado del escenario -------------------------------------------------

def _sucursal(api: TestClient, admin: dict[str, str], nombre: str) -> int:
    ciudad_id = api.get(CIUDADES, headers=admin).json()[0]["id"]
    r = api.post(
        SUCURSALES,
        headers=admin,
        json={
            "ciudad_id": ciudad_id,
            "nombre": nombre,
            "direccion": f"Avenida {nombre} 100",
            "telefono": None,
            "horario_apertura": "09:00:00",
            "horario_cierre": "20:00:00",
            "capacidad_vestidores": 4,
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _ingresar(api: TestClient, admin: dict[str, str], *, sucursal_id: int, lineas) -> None:
    creado = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Sedas Andinas SRL",
            "identificacion_tributaria": "1098765432",
            "activo": True,
        },
    )
    proveedor_id = (
        api.get(PROVEEDORES, headers=admin).json()[0]["id"]
        if creado.status_code == 409
        else creado.json()["id"]
    )
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": "REM-CU29",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


@pytest.fixture
def tienda(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Una sucursal con stock de una variante de precio conocido."""
    admin = cabeceras_admin
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Blusas", "orden": 0, "activa": True}
    ).json()["id"]
    talla = api.post(
        TALLAS,
        headers=admin,
        json={"tipo_prenda": "Superior", "codigo": "M", "orden": 2, "activa": True},
    ).json()["id"]
    color = api.post(
        COLORES,
        headers=admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    ).json()["id"]
    producto = api.post(
        PRODUCTOS,
        headers=admin,
        json={
            "codigo": "BLU-001",
            "nombre": "Blusa de seda",
            "categoria_id": categoria,
            "precio_base": f"{PRECIO}.00",
            "activo": True,
        },
    ).json()["id"]
    variante = api.post(
        f"{PRODUCTOS}/{producto}/variantes",
        headers=admin,
        json={"talla_id": talla, "color_id": color, "precio": f"{PRECIO}.00", "activa": True},
    ).json()["id"]

    sucursal = _sucursal(api, admin, "Centro")
    _ingresar(api, admin, sucursal_id=sucursal, lineas=[(variante, 40)])
    return {"variante": variante, "sucursal": sucursal}


def _comprar(
    api: TestClient, cliente: dict[str, str], tienda: dict, *, cantidad: int = 1, pagar: bool = True
) -> str:
    """Una compra por el flujo real. Devuelve el código del pedido."""
    api.post(
        f"{CARRITO}/items",
        headers=cliente,
        json={"variante_id": tienda["variante"], "cantidad": cantidad},
    )
    r = api.post(
        PEDIDOS,
        headers=cliente,
        json={
            "modalidad_entrega": "RETIRO",
            "sucursal_id": tienda["sucursal"],
            "total_esperado": f"{PRECIO * cantidad}.00",
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    if pagar:
        sesion = cuerpo["url_pago"].split("sesion=")[1].split("&")[0]
        confirmado = api.post(
            SIMULACION,
            json={"sesion": sesion, "pedido": cuerpo["pedido"]["codigo"], "aprobado": True},
        )
        assert confirmado.json()["resultado"] == "aplicado", confirmado.text
    return cuerpo["pedido"]["codigo"]


def _cancelar(api: TestClient, cliente: dict[str, str], codigo: str) -> None:
    r = api.post(f"{PEDIDOS}/{codigo}/cancelar", headers=cliente)
    assert r.status_code == 200, r.text


# =====================================================================
# Autorizacion
# =====================================================================

def test_sin_token_no_hay_historial(api: TestClient) -> None:
    assert api.get(COMPRAS).status_code == 401


def test_el_administrador_no_tiene_historial_de_compras(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Es del Cliente, como el carrito y los pedidos."""
    assert api.get(COMPRAS, headers=cabeceras_admin).status_code == 403


# =====================================================================
# El listado
# =====================================================================

def test_sin_compras_el_historial_esta_vacio_y_no_falla(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    cuerpo = api.get(COMPRAS, headers=cabeceras_cliente).json()

    assert cuerpo["total"] == 0
    assert cuerpo["items"] == []


def test_una_compra_aparece_con_su_detalle(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    codigo = _comprar(api, cabeceras_cliente, tienda, cantidad=2)

    cuerpo = api.get(COMPRAS, headers=cabeceras_cliente).json()

    assert cuerpo["total"] == 1
    compra = cuerpo["items"][0]
    assert compra["codigo"] == codigo
    assert compra["estado"] == "PAGADA"
    assert compra["total"] == f"{PRECIO * 2}.00"
    assert len(compra["lineas"]) == 1
    assert compra["lineas"][0]["cantidad"] == 2


def test_el_historial_trae_TODAS_las_compras_y_no_solo_las_pagadas(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """**La decisión de este caso de uso.**

    Un historial que escondiera las canceladas dejaría al cliente sin forma de
    entender por qué un pedido que recuerda no aparece. El estado se muestra; la
    fila no se esconde.
    """
    pagada = _comprar(api, cabeceras_cliente, tienda)
    cancelada = _comprar(api, cabeceras_cliente, tienda, pagar=False)
    _cancelar(api, cabeceras_cliente, cancelada)

    items = api.get(COMPRAS, headers=cabeceras_cliente).json()["items"]
    por_codigo = {c["codigo"]: c["estado"] for c in items}

    assert por_codigo[pagada] == "PAGADA"
    assert por_codigo[cancelada] == "CANCELADA"


def test_la_mas_nueva_va_primero(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    primera = _comprar(api, cabeceras_cliente, tienda)
    segunda = _comprar(api, cabeceras_cliente, tienda)

    items = api.get(COMPRAS, headers=cabeceras_cliente).json()["items"]

    assert [c["codigo"] for c in items] == [segunda, primera]


def test_el_historial_pagina(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """Un historial sólo crece: sin paginar, una cuenta vieja traería cientos de
    pedidos con sus líneas en cada carga."""
    for _ in range(3):
        _comprar(api, cabeceras_cliente, tienda)

    primera = api.get(COMPRAS, headers=cabeceras_cliente, params={"tamano": 2}).json()
    segunda = api.get(
        COMPRAS, headers=cabeceras_cliente, params={"tamano": 2, "pagina": 2}
    ).json()

    assert primera["total"] == 3
    assert len(primera["items"]) == 2
    assert len(segunda["items"]) == 1
    # Sin solaparse: el orden es estable.
    codigos = {c["codigo"] for c in primera["items"]} | {c["codigo"] for c in segunda["items"]}
    assert len(codigos) == 3


# =====================================================================
# El comprobante
# =====================================================================

def test_el_comprobante_de_una_compra_pagada_es_un_pdf(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    codigo = _comprar(api, cabeceras_cliente, tienda, cantidad=2)

    r = api.get(f"{COMPRAS}/{codigo}/comprobante", headers=cabeceras_cliente)

    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"], (
        "el enunciado pide DESCARGAR el comprobante, no abrirlo en una pestaña"
    )
    assert r.content.startswith(b"%PDF"), "no es un PDF de verdad"


def test_reimprimir_NO_es_reemitir(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """**La prueba que justifica el UNIQUE sobre `comprobante.venta_id`.**

    Un comprobante que cambiara de número cada vez que se lo mira no serviría
    como comprobante de nada. La segunda descarga tiene que traer el mismo.
    """
    codigo = _comprar(api, cabeceras_cliente, tienda)

    primera = api.get(f"{COMPRAS}/{codigo}/comprobante", headers=cabeceras_cliente)
    segunda = api.get(f"{COMPRAS}/{codigo}/comprobante", headers=cabeceras_cliente)

    assert primera.headers["content-disposition"] == segunda.headers["content-disposition"]


def test_una_compra_sin_pagar_no_tiene_comprobante(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """409 y no 404: la compra existe, lo que falta es el pago.

    El cliente tiene que poder distinguir «no encontramos esa compra» de «esa
    compra todavía no se pagó», porque lo que hace después es distinto.
    """
    codigo = _comprar(api, cabeceras_cliente, tienda, pagar=False)

    r = api.get(f"{COMPRAS}/{codigo}/comprobante", headers=cabeceras_cliente)

    assert r.status_code == 409


def test_una_compra_cancelada_tampoco(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """Un recibo de algo que no se cobró sería un papel que miente."""
    codigo = _comprar(api, cabeceras_cliente, tienda, pagar=False)
    _cancelar(api, cabeceras_cliente, codigo)

    assert api.get(f"{COMPRAS}/{codigo}/comprobante", headers=cabeceras_cliente).status_code == 409


def test_una_compra_que_no_existe_da_404(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    r = api.get(f"{COMPRAS}/VB-99999999-XXXX/comprobante", headers=cabeceras_cliente)

    assert r.status_code == 404


def test_el_comprobante_se_emite_al_pagar_y_no_al_descargar(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, db
) -> None:
    """Un recibo se emite cuando el dinero entra, no cuando alguien lo pide.

    Se comprueba en la base y no por la API: la descarga tambien lo emitiria
    ---para cubrir las ventas viejas--- asi que pedirlo por HTTP no distinguiria
    los dos caminos.
    """
    from sqlalchemy import select

    from app.modules.ventas.models import Comprobante, Venta

    codigo = _comprar(api, cabeceras_cliente, tienda)

    venta = db.scalar(select(Venta).where(Venta.codigo == codigo))
    comprobante = db.scalar(select(Comprobante).where(Comprobante.venta_id == venta.id))

    assert comprobante is not None, "el webhook tenía que haberlo emitido"
    assert comprobante.tipo == "RECIBO"
    assert comprobante.numero == f"R-{venta.id:08d}"
