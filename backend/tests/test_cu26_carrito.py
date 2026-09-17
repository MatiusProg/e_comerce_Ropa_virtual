"""CU-26 · Gestionar carrito de compras.

Realiza el **RF14**. Es la entrada al criterio de cierre del Ciclo 3 —catálogo →
carrito → pago → inventario descontado— y las **dos primeras tablas propias de
P7**: el paquete existía como esqueleto con su `models.py` vacío a propósito.

Lo que más importa cubrir
-------------------------
Casi todo lo de acá sale de dos decisiones, y las pruebas existen para que no se
pierdan cuando alguien toque esto en seis días:

- **El carrito no guarda precios.** Se calculan al leer. Si la tienda cambia el
  precio, el carrito muestra el nuevo — porque es una intención, no un
  contrato, y el precio se fija recién al generar el pedido (CU-27).
- **El carrito no inmoviliza inventario.** Agregar no descuenta ni aparta nada:
  eso lo hace una reserva (CU-22). Se puede agregar algo agotado.
- **Agregar SUMA; cambiar cantidad FIJA.** Dos verbos distintos porque son dos
  operaciones distintas, y confundirlas es el defecto clásico del carrito.
- **Una prenda que deja de ofrecerse no desaparece de la lista**: se marca y
  deja de sumar. Si desapareciera, el cliente vería bajar el total sin entender
  por qué.
- **El carrito es de cada quien.** Dos clientes no comparten nada.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from .conftest import CLAVE_CLIENTE, CORREO_CLIENTE

CARRITO = "/api/v1/tienda/carrito"
ITEMS = f"{CARRITO}/items"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
VARIANTES = "/api/v1/catalogo/variantes"

CORREO_OTRA = "otra.cliente@violetboutique.bo"
CLAVE_OTRA = "Otra12345"


@pytest.fixture
def catalogo(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Un producto con dos variantes activas, y otro producto aparte."""
    categoria = api.post(
        CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0, "activa": True}
    ).json()["id"]
    talla = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "M", "orden": 2, "activa": True},
    ).json()["id"]
    otra_talla = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "L", "orden": 3, "activa": True},
    ).json()["id"]
    color = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    ).json()["id"]

    def _producto(codigo: str, nombre: str, precio: str) -> dict:
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
        return r.json()

    uno = _producto("BLU-001", "Blusa de seda", "250.00")
    dos = _producto("BLU-002", "Blusa de lino", "180.00")

    def _variante(producto_id: int, talla_id: int, precio: str) -> int:
        r = api.post(
            f"{PRODUCTOS}/{producto_id}/variantes",
            headers=cabeceras_admin,
            json={"talla_id": talla_id, "color_id": color, "precio": precio, "activa": True},
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    return {
        "producto_uno": uno["id"],
        "producto_dos": dos["id"],
        "v_uno": _variante(uno["id"], talla, "250.00"),
        "v_uno_l": _variante(uno["id"], otra_talla, "270.00"),
        "v_dos": _variante(dos["id"], talla, "180.00"),
    }


def _agregar(api: TestClient, cab: dict[str, str], variante_id: int, cantidad: int = 1):
    return api.post(ITEMS, headers=cab, json={"variante_id": variante_id, "cantidad": cantidad})


# --- Flujo principal -----------------------------------------------------

def test_el_carrito_de_quien_nunca_agrego_nada_esta_vacio_y_no_es_un_error(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Un carrito vacío es el estado normal, no un 404.

    La pantalla tiene que poder pintarse antes de que el cliente agregue nada.
    """
    respuesta = api.get(CARRITO, headers=cabeceras_cliente)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "lineas": [],
        "items": 0,
        "unidades": 0,
        "total": "0.00",
        "no_disponibles": 0,
    }


def test_el_cliente_arma_su_carrito_y_ve_el_total(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """Flujo principal: agregar dos prendas distintas y ver el total."""
    assert _agregar(api, cabeceras_cliente, catalogo["v_uno"], 2).status_code == 201
    ultimo = _agregar(api, cabeceras_cliente, catalogo["v_dos"], 1)
    assert ultimo.status_code == 201, ultimo.text

    carrito = ultimo.json()
    assert carrito["items"] == 2
    assert carrito["unidades"] == 3
    # 250,00 x 2 + 180,00 x 1
    assert Decimal(carrito["total"]) == Decimal("680.00")
    assert carrito["no_disponibles"] == 0

    # Lo último agregado va primero: es lo que el cliente acaba de tocar.
    assert carrito["lineas"][0]["variante_id"] == catalogo["v_dos"]

    linea = carrito["lineas"][1]
    assert linea["cantidad"] == 2
    assert Decimal(linea["subtotal"]) == Decimal("500.00")
    assert linea["producto_nombre"] == "Blusa de seda"
    assert linea["talla_codigo"] == "M"
    assert linea["color_nombre"] == "Negro"
    assert linea["disponible"] is True


def test_agregar_la_misma_prenda_dos_veces_SUMA(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """Es lo que espera quien pulsa «Agregar» dos veces desde la ficha.

    La segunda vez no reemplaza la primera, y tampoco crea una segunda línea:
    el carrito mostraría la misma prenda dos veces y el cliente no sabría cuál
    editar.
    """
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 2)
    carrito = _agregar(api, cabeceras_cliente, catalogo["v_uno"], 3).json()

    assert carrito["items"] == 1
    assert carrito["lineas"][0]["cantidad"] == 5


def test_cambiar_la_cantidad_FIJA_en_vez_de_sumar(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """Es el selector del carrito, y por eso va por otro verbo que agregar."""
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 5)

    carrito = api.patch(
        f"{ITEMS}/{catalogo['v_uno']}", headers=cabeceras_cliente, json={"cantidad": 2}
    )
    assert carrito.status_code == 200, carrito.text
    assert carrito.json()["lineas"][0]["cantidad"] == 2
    assert Decimal(carrito.json()["total"]) == Decimal("500.00")


def test_quitar_una_prenda_y_vaciar_el_carrito(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    _agregar(api, cabeceras_cliente, catalogo["v_dos"], 1)

    quitado = api.delete(f"{ITEMS}/{catalogo['v_uno']}", headers=cabeceras_cliente)
    assert quitado.status_code == 200, quitado.text
    assert quitado.json()["items"] == 1

    vaciado = api.delete(CARRITO, headers=cabeceras_cliente)
    assert vaciado.status_code == 200
    assert vaciado.json()["items"] == 0
    assert Decimal(vaciado.json()["total"]) == Decimal("0.00")


def test_vaciar_un_carrito_ya_vacio_no_falla(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Pedir «que quede vacío» sobre algo ya vacío es una petición cumplida.

    Es la diferencia con quitar una línea, que sí falla: aquélla habla de algo
    concreto que tendría que estar ahí.
    """
    assert api.delete(CARRITO, headers=cabeceras_cliente).status_code == 200
    assert api.delete(CARRITO, headers=cabeceras_cliente).status_code == 200


def test_quitar_algo_que_no_esta_en_el_carrito_si_falla(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """Un corazón se toca dos veces sin querer; este botón no.

    Que no exista la línea significa que la pantalla está vieja, y decirlo hace
    que se recargue.
    """
    assert api.delete(f"{ITEMS}/{catalogo['v_uno']}", headers=cabeceras_cliente).status_code == 404
    assert (
        api.patch(
            f"{ITEMS}/{catalogo['v_uno']}", headers=cabeceras_cliente, json={"cantidad": 2}
        ).status_code
        == 404
    )


# --- El carrito no guarda precios ----------------------------------------

def test_el_precio_del_carrito_es_el_VIGENTE_no_el_de_cuando_se_agrego(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    catalogo: dict,
) -> None:
    """Es la decisión de fondo del caso de uso.

    Un carrito es una intención, no un contrato: el precio se fija al generar el
    pedido (CU-27). Guardar una foto dejaría al carrito cotizando un valor que
    la tienda ya no sostiene, y el cliente lo descubriría al pagar.
    """
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 2)
    assert Decimal(api.get(CARRITO, headers=cabeceras_cliente).json()["total"]) == Decimal("500.00")

    cambio = api.patch(
        f"{VARIANTES}/{catalogo['v_uno']}", headers=cabeceras_admin, json={"precio": "300.00"}
    )
    assert cambio.status_code == 200, cambio.text

    carrito = api.get(CARRITO, headers=cabeceras_cliente).json()
    assert Decimal(carrito["lineas"][0]["precio_unitario"]) == Decimal("300.00")
    assert Decimal(carrito["total"]) == Decimal("600.00")


# --- El carrito no inmoviliza inventario ---------------------------------

def test_se_puede_agregar_una_prenda_sin_stock(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """El carrito no aparta nada: impedirlo sólo le quitaría al cliente la
    posibilidad de dejarlo anotado mientras la tienda repone.

    La línea viaja con `stock_total` para que la pantalla lo diga. Acá no hay
    ninguna existencia cargada, así que es cero.
    """
    respuesta = _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["lineas"][0]["stock_total"] == 0
    assert respuesta.json()["lineas"][0]["disponible"] is True


# --- Prendas que dejan de ofrecerse --------------------------------------

def test_una_prenda_desactivada_sigue_en_la_lista_pero_no_suma(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    catalogo: dict,
) -> None:
    """Si desapareciera, el cliente vería bajar el total sin entender por qué.

    Se queda marcada para que pueda sacarla él, o preguntar.
    """
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 2)
    _agregar(api, cabeceras_cliente, catalogo["v_dos"], 1)

    baja = api.patch(
        f"{PRODUCTOS}/{catalogo['producto_uno']}/estado",
        headers=cabeceras_admin,
        json={"activo": False},
    )
    assert baja.status_code == 200, baja.text

    carrito = api.get(CARRITO, headers=cabeceras_cliente).json()
    assert carrito["items"] == 2
    assert carrito["no_disponibles"] == 1
    # Sólo suma la que sigue ofreciéndose.
    assert Decimal(carrito["total"]) == Decimal("180.00")

    caida = next(l for l in carrito["lineas"] if l["variante_id"] == catalogo["v_uno"])
    assert caida["disponible"] is False
    assert Decimal(caida["subtotal"]) == Decimal("0.00")
    # Las unidades SÍ la cuentan: es lo que el cliente metió, y la burbuja del
    # ícono no puede cambiar sola porque la tienda desactivó una prenda.
    assert carrito["unidades"] == 3


def test_una_prenda_desactivada_se_puede_quitar_igual(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    catalogo: dict,
) -> None:
    """Exigir que siga ofreciéndose dejaría líneas imposibles de borrar."""
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    api.patch(
        f"{PRODUCTOS}/{catalogo['producto_uno']}/estado",
        headers=cabeceras_admin,
        json={"activo": False},
    )

    quitado = api.delete(f"{ITEMS}/{catalogo['v_uno']}", headers=cabeceras_cliente)
    assert quitado.status_code == 200, quitado.text
    assert quitado.json()["items"] == 0


def test_no_se_puede_agregar_una_prenda_que_ya_no_se_ofrece(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    catalogo: dict,
) -> None:
    """Excepción E1. Un solo mensaje para «no existe» y «no se ofrece»."""
    api.patch(
        f"{PRODUCTOS}/{catalogo['producto_uno']}/estado",
        headers=cabeceras_admin,
        json={"activo": False},
    )

    assert _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1).status_code == 404
    assert _agregar(api, cabeceras_cliente, 999_999, 1).status_code == 404


def test_agregar_algo_que_no_se_ofrece_no_crea_el_carrito(
    api: TestClient, db, cabeceras_cliente: dict[str, str]
) -> None:
    """La comprobación va ANTES de crear el carrito.

    Si fuera al revés, quien prueba con un identificador inventado dejaría una
    fila de carrito vacía por cada intento. Se mira la tabla, no la respuesta:
    un carrito vacío y un carrito inexistente se ven igual desde afuera, y la
    diferencia es justamente lo que esta prueba comprueba.
    """
    from sqlalchemy import func, select

    from app.modules.ventas.carrito_models import Carrito

    assert _agregar(api, cabeceras_cliente, 999_999, 1).status_code == 404

    assert db.scalar(select(func.count()).select_from(Carrito)) == 0


# --- El tope por prenda --------------------------------------------------

def test_no_se_puede_pasar_del_tope_por_prenda(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """409 y no 422: el número que mandó es válido; el resultado de sumarlo, no.

    Y NO se recorta en silencio al tope: el cliente pidió algo que no se le
    puede dar y tiene que enterarse.
    """
    from app.modules.ventas.carrito_schemas import CANTIDAD_MAXIMA

    assert _agregar(api, cabeceras_cliente, catalogo["v_uno"], CANTIDAD_MAXIMA).status_code == 201

    choque = _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    assert choque.status_code == 409
    assert str(CANTIDAD_MAXIMA) in choque.json()["detail"]

    # Y la cantidad quedó donde estaba, no recortada ni aumentada.
    assert api.get(CARRITO, headers=cabeceras_cliente).json()["lineas"][0]["cantidad"] == CANTIDAD_MAXIMA


def test_una_cantidad_invalida_la_rechaza_el_esquema(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """Cero o negativo es 422: no llega a ser una operación del caso de uso."""
    assert _agregar(api, cabeceras_cliente, catalogo["v_uno"], 0).status_code == 422
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 1)
    assert (
        api.patch(
            f"{ITEMS}/{catalogo['v_uno']}", headers=cabeceras_cliente, json={"cantidad": 0}
        ).status_code
        == 422
    )


# --- El carrito es de cada quien -----------------------------------------

def test_dos_clientes_no_comparten_carrito(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo: dict
) -> None:
    """No hay identificador de carrito en ninguna ruta: sale del token."""
    _agregar(api, cabeceras_cliente, catalogo["v_uno"], 2)

    alta = api.post(
        "/api/v1/auth/registro",
        json={
            "nombres": "Otra",
            "apellidos": "Clienta",
            "documento": "1234567",
            "correo": CORREO_OTRA,
            "contrasena": CLAVE_OTRA,
        },
    )
    assert alta.status_code == 201, alta.text
    token = api.post(
        "/api/v1/auth/login", json={"correo": CORREO_OTRA, "contrasena": CLAVE_OTRA}
    ).json()["access_token"]
    otra = {"Authorization": f"Bearer {token}"}

    assert api.get(CARRITO, headers=otra).json()["items"] == 0

    _agregar(api, otra, catalogo["v_dos"], 1)
    assert [l["variante_id"] for l in api.get(CARRITO, headers=otra).json()["lineas"]] == [
        catalogo["v_dos"]
    ]
    assert [l["variante_id"] for l in api.get(CARRITO, headers=cabeceras_cliente).json()["lineas"]] == [
        catalogo["v_uno"]
    ]


def test_un_administrador_no_tiene_carrito(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """La guarda es de rol CLIENTE, declarada a nivel de router.

    Un carrito es de alguien que compra; el Administrador no lo es.
    """
    assert api.get(CARRITO, headers=cabeceras_admin).status_code == 403


def test_sin_token_no_hay_carrito(api: TestClient) -> None:
    """A diferencia de la vitrina, esto NO es público: un carrito es de alguien."""
    assert api.get(CARRITO).status_code == 401
    assert api.post(ITEMS, json={"variante_id": 1, "cantidad": 1}).status_code == 401
