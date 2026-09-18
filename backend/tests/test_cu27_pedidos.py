"""CU-27 · Realizar pedido y pagar en línea.

Realiza los **RF15, RF16 y RF19**. Es el eslabón que cierra el criterio del
Ciclo 3 —catálogo → carrito → pago → inventario descontado— y el primero que
escribe en `venta`, `detalle_venta` y `pago`.

Lo que más importa cubrir
-------------------------
Las cuatro decisiones del caso de uso, que son las que se pierden cuando
alguien toque esto en seis días:

- **El pedido APARTA stock.** Confirmar mueve unidades de `disponible` a
  `reservada`, como CU-22. Sin eso, dos clientes pagan la última unidad y a uno
  hay que devolverle la plata.
- **Un pedido se despacha desde UNA sucursal.** `detalle_venta` no tiene
  sucursal. Si ninguna puede con todo, el pedido no se hace aunque entre todas
  sobre stock — y la pantalla lo dice ANTES de confirmar.
- **El precio se congela acá, y si cambió se avisa.** El carrito lee precios en
  vivo; entre mirar y confirmar la tienda pudo cambiarlos. El cliente manda el
  total que vio y el servidor se planta con un 409.
- **El carrito NO se vacía acá.** Lo vacía CU-28 al confirmarse el pago. Lo que
  impide apartar cinco veces es la regla de un solo pedido pendiente.

Y la que ordena todo lo demás:

- **D5: el estado lo determina el webhook, no la redirección.** El pedido nace
  en `PENDIENTE_PAGO` y ninguna ruta de este caso de uso lo mueve a `PAGADA`.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

CARRITO = "/api/v1/tienda/carrito"
ITEMS = f"{CARRITO}/items"
PEDIDOS = "/api/v1/tienda/pedidos"
OPCIONES = f"{PEDIDOS}/opciones"
EXPIRAR = "/api/v1/pedidos/expirar-vencidos"

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
VARIANTES = "/api/v1/catalogo/variantes"
CIUDADES = "/api/v1/organizacion/ciudades"
SUCURSALES = "/api/v1/organizacion/sucursales"
INGRESOS = "/api/v1/inventario/ingresos"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EXISTENCIAS = "/api/v1/inventario/existencias"
DIRECCIONES = "/api/v1/perfil/direcciones"


# --- Armado del escenario -------------------------------------------------

def _proveedor(api: TestClient, admin: dict[str, str]) -> int:
    r = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Textiles del Sur SRL",
            "identificacion_tributaria": "1023456789",
            "activo": True,
        },
    )
    if r.status_code == 409:
        return api.get(PROVEEDORES, headers=admin).json()[0]["id"]
    assert r.status_code == 201, r.text
    return r.json()["id"]


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


def _ingresar(
    api: TestClient, admin: dict[str, str], *, sucursal_id: int, lineas: list[tuple[int, int]]
) -> None:
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": _proveedor(api, admin),
            "referencia": "REM-CU27",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


@pytest.fixture
def catalogo(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Dos variantes de dos productos distintos, con precios conocidos."""
    categoria = api.post(
        CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0, "activa": True}
    ).json()["id"]
    talla = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "M", "orden": 2, "activa": True},
    ).json()["id"]
    color = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    ).json()["id"]

    def _producto(codigo: str, nombre: str, precio: str) -> int:
        r = api.post(
            PRODUCTOS,
            headers=cabeceras_admin,
            json={
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": categoria,
                "precio_base": precio,
                "activo": True,
            },
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    def _variante(producto_id: int, precio: str) -> int:
        r = api.post(
            f"{PRODUCTOS}/{producto_id}/variantes",
            headers=cabeceras_admin,
            json={"talla_id": talla, "color_id": color, "precio": precio, "activa": True},
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    uno = _producto("BLU-001", "Blusa de seda", "250.00")
    dos = _producto("BLU-002", "Blusa de lino", "180.00")
    return {
        "producto_uno": uno,
        "producto_dos": dos,
        "v_uno": _variante(uno, "250.00"),
        "v_dos": _variante(dos, "180.00"),
    }


@pytest.fixture
def tienda(api: TestClient, cabeceras_admin: dict[str, str], catalogo: dict) -> dict:
    """Una sucursal con stock de las dos variantes."""
    sucursal = _sucursal(api, cabeceras_admin, "Centro")
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        lineas=[(catalogo["v_uno"], 10), (catalogo["v_dos"], 4)],
    )
    return {**catalogo, "sucursal": sucursal}


@pytest.fixture
def direccion(api: TestClient, cabeceras_cliente: dict[str, str]) -> int:
    ciudad_id = api.get(CIUDADES, headers=cabeceras_cliente).json()[0]["id"]
    r = api.post(
        DIRECCIONES,
        headers=cabeceras_cliente,
        json={
            "ciudad_id": ciudad_id,
            "alias": "Casa",
            "direccion": "Calle Falsa 123",
            "referencia": "Portón verde",
            "predeterminada": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    return api.get("/api/v1/perfil", headers=cabeceras_cliente).json()["direcciones"][0]["id"]


def _agregar(api: TestClient, cab: dict[str, str], variante_id: int, cantidad: int = 1):
    return api.post(ITEMS, headers=cab, json={"variante_id": variante_id, "cantidad": cantidad})


def _disponible(api: TestClient, admin: dict[str, str], variante_id: int, sucursal_id: int) -> int:
    filas = api.get(
        EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}
    ).json()["items"]
    for fila in filas:
        if fila["variante_id"] == variante_id:
            return fila["cantidad_disponible"]
    return 0


def _reservada(api: TestClient, admin: dict[str, str], variante_id: int, sucursal_id: int) -> int:
    filas = api.get(
        EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}
    ).json()["items"]
    for fila in filas:
        if fila["variante_id"] == variante_id:
            return fila["cantidad_reservada"]
    return 0


def _pedir(
    api: TestClient,
    cab: dict[str, str],
    *,
    total: str,
    sucursal_id: int | None = None,
    direccion_id: int | None = None,
):
    cuerpo: dict = {
        "modalidad_entrega": "RETIRO" if sucursal_id else "ENVIO",
        "total_esperado": total,
    }
    if sucursal_id:
        cuerpo["sucursal_id"] = sucursal_id
    if direccion_id:
        cuerpo["direccion_id"] = direccion_id
    return api.post(PEDIDOS, headers=cab, json=cuerpo)


# --- Autorizacion ---------------------------------------------------------

def test_sin_token_no_se_ve_ni_se_crea_un_pedido(api: TestClient) -> None:
    assert api.get(OPCIONES).status_code == 401
    assert api.post(PEDIDOS, json={}).status_code == 401


def test_el_administrador_no_puede_pedir_por_la_tienda(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El rol se declara a nivel de router: quien no es Cliente no entra.

    No es una formalidad: el pedido se resuelve desde el token, y un usuario
    sin ficha de cliente no tiene carrito de quién ser.
    """
    assert api.get(OPCIONES, headers=cabeceras_admin).status_code == 403


# --- Paso 1: las opciones -------------------------------------------------

def test_con_el_carrito_vacio_no_se_puede_pedir_y_la_pantalla_dice_por_que(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Un carrito vacío no es un 404: es un `se_puede_pedir: false` con motivo.

    La pantalla de confirmación tiene que poder pintarse igual, con el botón
    deshabilitado y el motivo a la vista.
    """
    respuesta = api.get(OPCIONES, headers=cabeceras_cliente)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["se_puede_pedir"] is False
    assert "vacío" in cuerpo["motivo"]
    assert cuerpo["lineas"] == []


def test_las_opciones_marcan_que_sucursal_abastece_y_que_le_falta(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """Decisión 2: el cliente se entera ANTES de confirmar.

    Una lista de sucursales sin la marca dejaría elegir una que no puede, y el
    error aparecería recién al confirmar. Y cuando no puede, se nombra la
    prenda que falta: decir «no disponible» obliga a adivinar cuál.
    """
    otra = _sucursal(api, cabeceras_admin, "Norte")
    # La otra sucursal recibe SOLO una de las dos variantes.
    _ingresar(api, cabeceras_admin, sucursal_id=otra, lineas=[(tienda["v_uno"], 5)])

    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    _agregar(api, cabeceras_cliente, tienda["v_dos"], 1)

    cuerpo = api.get(OPCIONES, headers=cabeceras_cliente).json()
    assert cuerpo["se_puede_pedir"] is True

    por_id = {s["id"]: s for s in cuerpo["sucursales"]}
    assert por_id[tienda["sucursal"]]["abastece_todo"] is True
    assert por_id[otra]["abastece_todo"] is False
    assert "Blusa de lino" in " ".join(por_id[otra]["faltantes"])


def test_si_ninguna_sucursal_puede_con_todo_el_pedido_no_se_puede_hacer(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    catalogo: dict,
) -> None:
    """Decisión 2, el caso incómodo: entre todas sobra stock y aun así no se puede.

    Es la limitación consciente de que un pedido se despacha desde una sola
    sucursal. Importa que esté probada para que nadie la «arregle» sin darse
    cuenta de que partir un pedido es otro caso de uso.
    """
    una = _sucursal(api, cabeceras_admin, "Sur")
    otra = _sucursal(api, cabeceras_admin, "Este")
    _ingresar(api, cabeceras_admin, sucursal_id=una, lineas=[(catalogo["v_uno"], 5)])
    _ingresar(api, cabeceras_admin, sucursal_id=otra, lineas=[(catalogo["v_dos"], 5)])

    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    _agregar(api, cabeceras_cliente, catalogo["v_dos"], 1)

    cuerpo = api.get(OPCIONES, headers=cabeceras_cliente).json()
    assert cuerpo["se_puede_pedir"] is False
    assert "Ninguna" in cuerpo["motivo"]
    assert all(not s["abastece_todo"] for s in cuerpo["sucursales"])

    # Y confirmar tampoco cuela.
    r = _pedir(api, cabeceras_cliente, total="430.00", sucursal_id=una)
    assert r.status_code == 409, r.text


# --- Paso 2: el flujo principal -------------------------------------------

def test_el_cliente_confirma_su_pedido_y_recibe_adonde_pagar(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """Flujo principal, retiro en sucursal."""
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 2)   # 2 x 250
    _agregar(api, cabeceras_cliente, tienda["v_dos"], 1)   # 1 x 180

    respuesta = _pedir(
        api, cabeceras_cliente, total="680.00", sucursal_id=tienda["sucursal"]
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()

    pedido = cuerpo["pedido"]
    assert pedido["estado"] == "PENDIENTE_PAGO"
    assert pedido["canal"] == "DIGITAL"
    assert pedido["modalidad_entrega"] == "RETIRO"
    assert pedido["codigo"].startswith("VB-")
    assert Decimal(pedido["total"]) == Decimal("680.00")
    assert Decimal(pedido["subtotal"]) == Decimal("680.00")
    assert pedido["direccion_envio"] is None
    assert pedido["estado_pago"] == "INICIADO"
    assert pedido["pagar_antes_de"] is not None
    assert len(pedido["lineas"]) == 2

    assert cuerpo["url_pago"]
    # Con el proveedor por defecto el pago es simulado, y la respuesta lo dice
    # para que la pantalla lo avise en vez de hacerlo pasar por real.
    assert cuerpo["pago_real"] is False


def test_el_pedido_aparta_stock_pero_no_lo_descuenta(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """Decisión 1, y es la prueba central de este caso de uso.

    Las unidades pasan de `disponible` a `reservada`. NO salen del inventario:
    eso lo hace CU-28 cuando el pago se confirma, con LIBERACION + VENTA.
    """
    antes_disp = _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"])
    antes_res = _reservada(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"])

    _agregar(api, cabeceras_cliente, tienda["v_uno"], 3)
    assert _pedir(
        api, cabeceras_cliente, total="750.00", sucursal_id=tienda["sucursal"]
    ).status_code == 201

    assert _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == antes_disp - 3
    assert _reservada(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == antes_res + 3


def test_no_se_puede_pedir_mas_de_lo_que_hay(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """La validación de verdad es de acá, no del carrito.

    CU-26 deja agregar algo agotado a propósito —el carrito es una intención—.
    Quien se planta es este caso de uso.
    """
    _agregar(api, cabeceras_cliente, tienda["v_dos"], 5)   # hay 4
    respuesta = _pedir(
        api, cabeceras_cliente, total="900.00", sucursal_id=tienda["sucursal"]
    )
    assert respuesta.status_code == 409, respuesta.text


def test_el_envio_exige_direccion_y_el_retiro_exige_sucursal(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, direccion: int
) -> None:
    """Regla de forma, no de negocio: se rechaza con 422 y un mensaje legible.

    El CHECK `direccion_si_envio` de la base dice lo mismo; validarlo acá
    convierte un error de PostgreSQL en algo que la pantalla puede mostrar.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)

    # ENVIO con sucursal en vez de dirección.
    r = api.post(
        PEDIDOS,
        headers=cabeceras_cliente,
        json={
            "modalidad_entrega": "ENVIO",
            "sucursal_id": tienda["sucursal"],
            "total_esperado": "250.00",
        },
    )
    assert r.status_code == 422, r.text

    # RETIRO con dirección.
    r = api.post(
        PEDIDOS,
        headers=cabeceras_cliente,
        json={
            "modalidad_entrega": "RETIRO",
            "sucursal_id": tienda["sucursal"],
            "direccion_id": direccion,
            "total_esperado": "250.00",
        },
    )
    assert r.status_code == 422, r.text


def test_el_envio_elige_la_sucursal_solo_y_guarda_la_direccion(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, direccion: int
) -> None:
    """En un envío el cliente no elige sucursal: la elige el sistema.

    Pedirle que la elija sería pedirle que sepa desde dónde se despacha, que no
    es asunto suyo.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    respuesta = _pedir(api, cabeceras_cliente, total="250.00", direccion_id=direccion)
    assert respuesta.status_code == 201, respuesta.text

    pedido = respuesta.json()["pedido"]
    assert pedido["modalidad_entrega"] == "ENVIO"
    assert pedido["sucursal_id"] == tienda["sucursal"]
    assert "Calle Falsa 123" in pedido["direccion_envio"]


def test_una_direccion_ajena_no_sirve_y_se_ve_igual_que_una_inexistente(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """El `cliente_id` va en el WHERE, no en una comprobación posterior.

    Así probar números no dice qué direcciones tiene otra persona.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    respuesta = _pedir(api, cabeceras_cliente, total="250.00", direccion_id=999999)
    assert respuesta.status_code == 404, respuesta.text


# --- Decision 3: el precio que cambio -------------------------------------

def test_si_el_precio_cambio_entre_mirar_y_confirmar_no_se_cobra(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """Decisión 3, y el corolario que quedó anotado al elegir dónde congelar.

    El carrito lee precios en vivo. Si el sistema cobrara el precio nuevo sin
    decir nada, el cliente se enteraría leyendo el comprobante.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)

    # La tienda sube el precio mientras el cliente decide.
    r = api.patch(
        f"{VARIANTES}/{tienda['v_uno']}",
        headers=cabeceras_admin,
        json={"precio": "300.00"},
    )
    assert r.status_code == 200, r.text

    respuesta = _pedir(
        api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"]
    )
    assert respuesta.status_code == 409, respuesta.text

    detalle = respuesta.json()["detail"]
    assert Decimal(detalle["total_esperado"]) == Decimal("250.00")
    assert Decimal(detalle["total_actual"]) == Decimal("300.00")
    # Devuelve el carrito entero para que el cliente vea QUÉ cambió.
    assert detalle["lineas"]


def test_el_pedido_congela_el_precio_y_no_lo_sigue_leyendo(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """La otra mitad de la decisión: una vez confirmado, el precio no se mueve.

    Si la ficha del pedido leyera `variante_producto.precio`, el historial de
    CU-29 y el ticket promedio de CU-36 cambiarían solos cada vez que la tienda
    toca un precio.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    codigo = _pedir(
        api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]

    api.patch(
        f"{VARIANTES}/{tienda['v_uno']}",
        headers=cabeceras_admin,
        json={"precio": "999.00"},
    )

    pedido = api.get(f"{PEDIDOS}/{codigo}", headers=cabeceras_cliente).json()
    assert Decimal(pedido["total"]) == Decimal("250.00")
    assert Decimal(pedido["lineas"][0]["precio_unitario"]) == Decimal("250.00")


# --- Decision 4: un solo pedido pendiente ---------------------------------

def test_no_se_pueden_tener_dos_pedidos_esperando_pago(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """Decisión 4: es lo que impide apartar stock cinco veces.

    El caso real es el cliente que abre la pasarela, vuelve atrás y confirma de
    nuevo. Sin esta regla, cada intento inmoviliza mercadería.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    primero = _pedir(api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"])
    assert primero.status_code == 201, primero.text

    segundo = _pedir(api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"])
    assert segundo.status_code == 409, segundo.text
    # El código del pendiente va en el mensaje para que la pantalla pueda
    # ofrecer ir a pagarlo o cancelarlo.
    assert primero.json()["pedido"]["codigo"] in segundo.json()["detail"]


def test_el_carrito_sigue_entero_despues_de_confirmar(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """Decisión 4: lo vacía CU-28, no esto.

    Si se vaciara acá, un pago que falla dejaría al cliente sin carrito y
    teniendo que rearmarlo prenda por prenda.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 2)
    assert _pedir(
        api, cabeceras_cliente, total="500.00", sucursal_id=tienda["sucursal"]
    ).status_code == 201

    carrito = api.get(CARRITO, headers=cabeceras_cliente).json()
    assert carrito["unidades"] == 2


# --- D5: el estado lo determina el webhook --------------------------------

def test_ninguna_ruta_de_este_caso_de_uso_deja_el_pedido_pagado(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """D5, y es la prueba que protege la plata.

    La URL de retorno de la pasarela la puede escribir cualquiera en la barra
    de direcciones. Si visitarla alcanzara para marcar una venta como pagada,
    se llevarían la mercadería gratis.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    codigo = _pedir(
        api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]

    # Consultar la ficha cuantas veces se quiera no la mueve de estado.
    for _ in range(3):
        pedido = api.get(f"{PEDIDOS}/{codigo}", headers=cabeceras_cliente).json()
        assert pedido["estado"] == "PENDIENTE_PAGO"
        assert pedido["estado_pago"] == "INICIADO"


# --- Consultar y cancelar --------------------------------------------------

def test_un_pedido_ajeno_se_ve_igual_que_uno_inexistente(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    codigo = _pedir(
        api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]

    otra = api.post(
        "/api/v1/auth/registro",
        json={
            "correo": "otra.cu27@violetboutique.bo",
            "contrasena": "Otra12345",
            "nombres": "Otra",
            "apellidos": "Cliente",
            "telefono": None,
        },
    )
    assert otra.status_code in (200, 201), otra.text
    token = api.post(
        "/api/v1/auth/login",
        json={"correo": "otra.cu27@violetboutique.bo", "contrasena": "Otra12345"},
    ).json()["access_token"]
    ajenas = {"Authorization": f"Bearer {token}"}

    assert api.get(f"{PEDIDOS}/{codigo}", headers=ajenas).status_code == 404
    assert api.get(f"{PEDIDOS}/NO-EXISTE", headers=cabeceras_cliente).status_code == 404


def test_cancelar_devuelve_el_stock_apartado(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """Cancelar antes de pagar tiene que devolver lo que el pedido apartó.

    Si no lo devolviera, cada arrepentimiento se llevaría unidades del
    inventario para siempre.
    """
    antes = _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"])

    _agregar(api, cabeceras_cliente, tienda["v_uno"], 2)
    codigo = _pedir(
        api, cabeceras_cliente, total="500.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]
    assert _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == antes - 2

    respuesta = api.post(f"{PEDIDOS}/{codigo}/cancelar", headers=cabeceras_cliente)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "CANCELADA"

    assert _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == antes
    assert _reservada(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == 0


def test_cancelar_dos_veces_no_devuelve_el_stock_dos_veces(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """El bloqueo de `obtener_venta_entidad` existe justamente para esto.

    Sin él, dos cancelaciones simultáneas leen las dos PENDIENTE_PAGO, las dos
    pasan la comprobación y el inventario termina con MÁS unidades de las que
    hay. Esta prueba cubre la versión secuencial; la de concurrencia sería otra.
    """
    antes = _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"])
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 2)
    codigo = _pedir(
        api, cabeceras_cliente, total="500.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]

    assert api.post(f"{PEDIDOS}/{codigo}/cancelar", headers=cabeceras_cliente).status_code == 200
    segunda = api.post(f"{PEDIDOS}/{codigo}/cancelar", headers=cabeceras_cliente)
    assert segunda.status_code == 409, segunda.text

    assert _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == antes


def test_cancelado_el_pedido_se_puede_hacer_otro(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> None:
    """La regla es «uno PENDIENTE», no «uno por cliente»."""
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    codigo = _pedir(
        api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]
    api.post(f"{PEDIDOS}/{codigo}/cancelar", headers=cabeceras_cliente)

    otro = _pedir(api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"])
    assert otro.status_code == 201, otro.text


# --- La barrida de vencidos ------------------------------------------------

def test_la_barrida_es_de_la_operacion_no_del_cliente(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.post(EXPIRAR, headers=cabeceras_cliente).status_code == 403
    assert api.post(EXPIRAR).status_code == 401


def test_la_barrida_no_toca_un_pedido_que_todavia_esta_a_tiempo(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
) -> None:
    """Un pedido recién hecho no vence: la vigencia son 30 minutos.

    Es la prueba que evita el defecto más caro posible en esta barrida —
    cancelar pedidos vivos — y la que fija que el corte se mide desde
    `creado_en`.
    """
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 1)
    codigo = _pedir(
        api, cabeceras_cliente, total="250.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]

    respuesta = api.post(EXPIRAR, headers=cabeceras_admin)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["cancelados"] == 0

    assert (
        api.get(f"{PEDIDOS}/{codigo}", headers=cabeceras_cliente).json()["estado"]
        == "PENDIENTE_PAGO"
    )


def test_la_barrida_cancela_el_pedido_vencido_y_devuelve_su_stock(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
    db,
) -> None:
    """Sin esto, apartar stock al confirmar sería un defecto.

    Cada cliente que abre la pasarela y cierra la pestaña se llevaría unidades
    del inventario para siempre. Se retrofecha el pedido en vez de esperar
    media hora.
    """
    from datetime import datetime, timedelta, timezone

    from app.modules.ventas.models import Venta

    antes = _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"])
    _agregar(api, cabeceras_cliente, tienda["v_uno"], 2)
    codigo = _pedir(
        api, cabeceras_cliente, total="500.00", sucursal_id=tienda["sucursal"]
    ).json()["pedido"]["codigo"]

    venta = db.query(Venta).filter(Venta.codigo == codigo).one()
    venta.creado_en = datetime.now(timezone.utc) - timedelta(hours=2)
    db.commit()

    respuesta = api.post(EXPIRAR, headers=cabeceras_admin)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["cancelados"] == 1
    assert respuesta.json()["unidades_devueltas"] == 2

    assert (
        api.get(f"{PEDIDOS}/{codigo}", headers=cabeceras_cliente).json()["estado"]
        == "CANCELADA"
    )
    assert _disponible(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == antes
    assert _reservada(api, cabeceras_admin, tienda["v_uno"], tienda["sucursal"]) == 0


# --- El candado que faltaba (defecto encontrado el 17/09) ------------------


def test_confirmar_toma_un_candado_sobre_el_cliente(
    api: TestClient, cabeceras_cliente: dict[str, str], fabrica_sesiones
) -> None:
    """La regla de «un solo pedido pendiente» necesita bloquear al CLIENTE.

    EL DEFECTO QUE ESTA PRUEBA IMPIDE QUE VUELVA
    ---------------------------------------------
    `pedido_pendiente_de` toma `SELECT ... FOR UPDATE` sobre la venta
    pendiente. Protege bien cuando la venta existe, y **no protege nada cuando
    no existe**: una consulta que no devuelve filas no bloquea nada. Dos POST
    simultáneos leían los dos «no hay pendiente», pasaban los dos y creaban dos
    pedidos, cada uno apartando stock.

    Se reprodujo el 17/09 disparando dos peticiones a la vez contra el servidor
    levantado: los dos devolvieron 201. Con `bloquear_cliente`, uno devuelve
    409.

    Acá no se simula la carrera —pytest corre en un hilo— sino que se comprueba
    lo que la hace imposible: que el candado sea **exclusivo** y esté sobre una
    fila que **existe siempre**. Con `lock_timeout`, la segunda sesión falla en
    vez de colgar la prueba.
    """
    from sqlalchemy import select, text

    from app.modules.seguridad.models import Cliente, Usuario
    from app.modules.ventas import repository

    from .conftest import CORREO_CLIENTE

    sesion_a = fabrica_sesiones()
    sesion_b = fabrica_sesiones()
    try:
        cliente_id = sesion_a.scalar(
            select(Cliente.id)
            .join(Usuario, Usuario.id == Cliente.usuario_id)
            .where(Usuario.correo == CORREO_CLIENTE)
        )
        assert cliente_id is not None, "el cliente de las pruebas tiene que existir"

        # La primera sesión se queda con el candado, sin cerrar la transacción.
        repository.bloquear_cliente(sesion_a, cliente_id)

        # La segunda no puede tomarlo. Sin `lock_timeout` esperaría para
        # siempre, que es justamente lo que prueba que el candado sirve.
        sesion_b.execute(text("SET LOCAL lock_timeout = '400ms'"))
        with pytest.raises(Exception) as fallo:
            repository.bloquear_cliente(sesion_b, cliente_id)
        assert "lock" in str(fallo.value).lower() or "timeout" in str(fallo.value).lower()
    finally:
        sesion_a.rollback()
        sesion_b.rollback()
        sesion_a.close()
        sesion_b.close()


def test_el_candado_es_por_cliente_y_no_frena_a_los_demas(
    api: TestClient, cabeceras_cliente: dict[str, str], fabrica_sesiones
) -> None:
    """Dos clientes distintos confirman a la vez sin estorbarse.

    Importa tanto como lo anterior: un candado global —sobre una tabla, o uno
    solo para toda la tienda— serializaría TODAS las compras del negocio detrás
    de la más lenta, y en la demostración eso se ve como una tienda trabada.
    """
    from sqlalchemy import select, text

    from app.modules.seguridad.models import Cliente
    from app.modules.ventas import repository

    # Un segundo cliente de verdad, por la API de CU-01. No se saltea la prueba
    # si no existe: una prueba saltada no protege nada, y esta cubre que el
    # candado no sea global.
    otra = api.post(
        "/api/v1/auth/registro",
        json={
            "correo": "segunda.cu27@violetboutique.bo",
            "contrasena": "Segunda12345",
            "nombres": "Segunda",
            "apellidos": "Clienta",
            "telefono": None,
        },
    )
    assert otra.status_code in (200, 201, 409), otra.text

    sesion_a = fabrica_sesiones()
    sesion_b = fabrica_sesiones()
    try:
        ids = list(sesion_a.scalars(select(Cliente.id).order_by(Cliente.id).limit(2)))
        assert len(ids) == 2, (
            "hacen falta dos clientes; los crea la fixture de arriba"
        )

        repository.bloquear_cliente(sesion_a, ids[0])

        # El segundo cliente pasa sin esperar.
        sesion_b.execute(text("SET LOCAL lock_timeout = '400ms'"))
        repository.bloquear_cliente(sesion_b, ids[1])
    finally:
        sesion_a.rollback()
        sesion_b.rollback()
        sesion_a.close()
        sesion_b.close()


# --- De qué sucursal sale un envío ----------------------------------------


def test_el_envio_sale_de_una_sucursal_de_la_ciudad_del_cliente(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    catalogo: dict,
) -> None:
    """Decisión 2, la mitad que no se ve hasta que alguien mira un envío.

    Las sucursales se listan por ciudad y nombre. Tomar «la primera que pueda»
    hacía que un cliente de Santa Cruz recibiera su pedido desde Cochabamba
    —que va antes alfabéticamente— si esa sucursal podía abastecerlo. El
    pedido salía bien, el inventario cuadraba, y nadie lo habría notado hasta
    ver la mercadería cruzando el país.
    """
    ciudades = api.get(CIUDADES, headers=cabeceras_admin).json()
    assert len(ciudades) >= 2, "hacen falta dos ciudades para esta comprobación"
    lejana, cercana = ciudades[0], ciudades[1]

    def _sucursal_en(ciudad_id: int, nombre: str) -> int:
        r = api.post(
            SUCURSALES,
            headers=cabeceras_admin,
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

    # Las dos pueden abastecer el pedido entero: lo único que las diferencia es
    # la ciudad. Así la prueba falla solo si se elige por el motivo equivocado.
    suc_lejana = _sucursal_en(lejana["id"], "Aaa Lejana")
    suc_cercana = _sucursal_en(cercana["id"], "Zzz Cercana")
    for suc in (suc_lejana, suc_cercana):
        _ingresar(api, cabeceras_admin, sucursal_id=suc, lineas=[(catalogo["v_uno"], 5)])

    # La dirección del cliente está en la ciudad de la sucursal «Zzz», que por
    # nombre y por ciudad iría ÚLTIMA en la lista.
    r = api.post(
        DIRECCIONES,
        headers=cabeceras_cliente,
        json={
            "ciudad_id": cercana["id"],
            "alias": "Casa",
            "direccion": "Calle Falsa 123",
            "referencia": None,
            "predeterminada": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    direccion_id = api.get("/api/v1/perfil", headers=cabeceras_cliente).json()[
        "direcciones"
    ][0]["id"]

    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    respuesta = _pedir(api, cabeceras_cliente, total="250.00", direccion_id=direccion_id)
    assert respuesta.status_code == 201, respuesta.text

    pedido = respuesta.json()["pedido"]
    assert pedido["sucursal_id"] == suc_cercana, (
        f"el envío salió de la sucursal {pedido['sucursal_id']} "
        f"({pedido['sucursal_nombre']}) en vez de la de la ciudad del cliente"
    )


def test_si_su_ciudad_no_puede_el_envio_sale_de_otra(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    catalogo: dict,
) -> None:
    """Preferir la ciudad del cliente NO puede volverse un impedimento.

    Si la sucursal de su ciudad no tiene la prenda, mandarla de lejos es mejor
    que no vender. Sin esta prueba, «preferir» y «exigir» se confunden fácil.
    """
    ciudades = api.get(CIUDADES, headers=cabeceras_admin).json()
    lejana, cercana = ciudades[0], ciudades[1]

    r = api.post(
        SUCURSALES,
        headers=cabeceras_admin,
        json={
            "ciudad_id": lejana["id"],
            "nombre": "Única con stock",
            "direccion": "Avenida Lejana 100",
            "telefono": None,
            "horario_apertura": "09:00:00",
            "horario_cierre": "20:00:00",
            "capacidad_vestidores": 4,
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    suc_lejana = r.json()["id"]
    _ingresar(api, cabeceras_admin, sucursal_id=suc_lejana, lineas=[(catalogo["v_uno"], 5)])

    r = api.post(
        DIRECCIONES,
        headers=cabeceras_cliente,
        json={
            "ciudad_id": cercana["id"],
            "alias": "Casa",
            "direccion": "Calle Falsa 123",
            "referencia": None,
            "predeterminada": True,
        },
    )
    assert r.status_code in (200, 201), r.text
    direccion_id = api.get("/api/v1/perfil", headers=cabeceras_cliente).json()[
        "direcciones"
    ][0]["id"]

    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    respuesta = _pedir(api, cabeceras_cliente, total="250.00", direccion_id=direccion_id)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["pedido"]["sucursal_id"] == suc_lejana
