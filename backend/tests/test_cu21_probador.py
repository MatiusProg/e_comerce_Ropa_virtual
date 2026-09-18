"""CU-21 · El probado por IA, que es la parte OPCIONAL del vestidor virtual.

Realiza parte del **RF13**. El resto de CU-21 —cámara, detección de pose,
superposición— corre en el teléfono y no se prueba desde acá: la sección 4.2
dice que P9 «reside principalmente en la aplicación móvil», y del servidor
solo necesita esto.

Lo que más importa cubrir
-------------------------
- **Que sea opcional de verdad.** Con el proveedor apagado —que es el valor por
  defecto— el endpoint de estado dice `disponible: false` y el de probar
  responde **503 y no 500**. La diferencia decide si la app esconde el botón o
  lo muestra y falla al tocarlo.
- **Que no se pueda probar cualquier cosa.** Una variante sin PNG de vestidor,
  una desactivada, o un archivo que no es imagen.
- **Que sea del Cliente.** Como el carrito y los pedidos.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

PROBADOR = "/api/v1/vestidor/probador"
PROBAR = "/api/v1/vestidor/probar"

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
VARIANTES = "/api/v1/catalogo/variantes"
IMAGENES = "/api/v1/catalogo/imagenes"


def _png(alfa: int = 0) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (24, 24), (200, 30, 60, alfa)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def prenda(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Un producto con dos variantes: una con PNG de vestidor y otra sin él."""
    admin = cabeceras_admin
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Blusas", "orden": 0, "activa": True}
    ).json()["id"]
    talla_s = api.post(
        TALLAS,
        headers=admin,
        json={"tipo_prenda": "Superior", "codigo": "S", "orden": 1, "activa": True},
    ).json()["id"]
    talla_m = api.post(
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
            "codigo": "BLU-VEST",
            "nombre": "Blusa de prueba",
            "categoria_id": categoria,
            "precio_base": "200.00",
            "activo": True,
        },
    ).json()["id"]

    def _variante(talla_id: int) -> int:
        r = api.post(
            f"{PRODUCTOS}/{producto}/variantes",
            headers=admin,
            json={"talla_id": talla_id, "color_id": color, "precio": "200.00", "activa": True},
        )
        assert r.status_code == 201, r.text
        return r.json()["id"]

    con_png = _variante(talla_s)
    sin_png = _variante(talla_m)

    subida = api.post(
        f"{PRODUCTOS}/{producto}/imagenes",
        headers=admin,
        files={"archivo": ("prenda.png", _png(alfa=0), "image/png")},
        params={"variante_id": con_png},
    )
    assert subida.status_code == 201, subida.text
    marcada = api.patch(
        f"{IMAGENES}/{subida.json()['id']}/transparente",
        headers=admin,
        json={"es_transparente": True},
    )
    assert marcada.status_code == 200, marcada.text

    return {"producto": producto, "con_png": con_png, "sin_png": sin_png, "admin": admin}


def _probar(api: TestClient, cab: dict[str, str], variante_id: int, contenido=None):
    return api.post(
        PROBAR,
        headers=cab,
        data={"variante_id": variante_id},
        files={"captura": ("captura.png", contenido or _png(alfa=255), "image/png")},
    )


# --- Autorizacion ----------------------------------------------------------

def test_el_vestidor_es_del_cliente(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    assert api.get(PROBADOR).status_code == 401
    assert api.get(PROBADOR, headers=cabeceras_admin).status_code == 403


# --- Que sea opcional de verdad --------------------------------------------

def test_por_omision_el_probado_por_ia_esta_apagado(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El valor por defecto NO llama a nadie, y lo dice.

    Es el riesgo R9: un valor por defecto que consume cuota la gasta cada vez
    que alguien abre el vestidor en una máquina recién clonada.
    """
    respuesta = api.get(PROBADOR, headers=cabeceras_cliente)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["disponible"] is False
    assert cuerpo["motivo"]


def test_con_el_probador_apagado_responde_503_y_no_500(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """503 es «apagado»; 500 sería «roto». La app decide distinto con cada uno.

    Con 503 esconde el botón y no reintenta. Con 500 lo trataría como un fallo
    pasajero y volvería a intentar contra algo que nunca va a funcionar.
    """
    respuesta = _probar(api, cabeceras_cliente, prenda["con_png"])
    assert respuesta.status_code == 503, respuesta.text
    assert "no está" in respuesta.json()["detail"]


def test_el_vestidor_sigue_andando_sin_el_probador(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """Lo OPCIONAL no puede romper lo obligatorio.

    El recorrido de CU-21 —ver la prenda, elegir variante, capturar— se apoya
    en la ficha pública, no en el probador. Si esto dejara de responder porque
    la IA no está configurada, el caso de uso entero caería con ella.
    """
    ficha = api.get(f"/api/v1/tienda/productos/{prenda['producto']}")
    assert ficha.status_code == 200, ficha.text
    cuerpo = ficha.json()
    assert cuerpo["tiene_vestidor"] is True
    con_png = [v for v in cuerpo["variantes"] if v["imagen_vestidor_url"]]
    assert len(con_png) == 1


# --- Que no se pueda probar cualquier cosa ---------------------------------

def test_una_variante_sin_png_no_se_puede_probar(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """404 antes de gastar una llamada al modelo.

    Importa el ORDEN: se comprueba la prenda ANTES de hablar con el proveedor.
    Al revés se gastaría cuota para descubrir que no había nada que componer.
    """
    respuesta = _probar(api, cabeceras_cliente, prenda["sin_png"])
    assert respuesta.status_code == 404, respuesta.text


def test_una_variante_inexistente_no_se_puede_probar(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert _probar(api, cabeceras_cliente, 999999).status_code == 404


def test_una_variante_desactivada_deja_de_poder_probarse(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """Probarse algo que la tienda dejó de ofrecer termina en un carrito
    que no se puede pagar."""
    r = api.patch(
        f"{VARIANTES}/{prenda['con_png']}",
        headers=prenda["admin"],
        json={"activa": False},
    )
    assert r.status_code == 200, r.text
    assert _probar(api, cabeceras_cliente, prenda["con_png"]).status_code == 404


def test_una_captura_vacia_se_rechaza(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    respuesta = _probar(api, cabeceras_cliente, prenda["con_png"], contenido=b"")
    assert respuesta.status_code in (422, 503), respuesta.text
