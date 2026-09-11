"""CU-19 · Consultar disponibilidad por sucursal.

Es el primer caso de uso que **cruza la costura C1**: P5 no consulta
`existencia` —que es tabla de P4— sino que importa
`inventario.service.disponibilidad_por_sucursal`. Estas pruebas recorren el
camino entero, desde que el Administrador registra un ingreso con el CU-13 de
Mateo hasta que el cliente anónimo ve en qué tienda hay la prenda.

Lo que más importa cubrir:

- **Que la costura devuelva lo mismo que el inventario.** Si las dos mitades se
  desincronizan, el cliente viaja a una sucursal donde no hay nada. Se compara
  contra el endpoint de existencias del propio paquete de Mateo.
- **Que la disponibilidad no sea una puerta trasera.** Una variante retirada del
  catálogo no puede seguir informando dónde hay stock de ella: sería contar por
  un endpoint lo que los otros dos ocultan.
- **Que no se publique lo reservado.** `existencia` lleva las dos cantidades; acá
  solo puede salir la disponible.
- **Que las sucursales en cero no aparezcan.** Para el inventario un saldo en
  cero es un dato legítimo; para la vitrina es ruido.
"""

import pytest
from fastapi.testclient import TestClient

CIUDADES = "/api/v1/organizacion/ciudades"
SUCURSALES = "/api/v1/organizacion/sucursales"
PROVEEDORES = "/api/v1/organizacion/proveedores"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
VARIANTES = "/api/v1/catalogo/variantes"
INGRESOS = "/api/v1/inventario/ingresos"
EXISTENCIAS = "/api/v1/inventario/existencias"

TIENDA = "/api/v1/tienda"


def _disponibilidad(variante_id: int) -> str:
    return f"{TIENDA}/variantes/{variante_id}/disponibilidad"


# --- Ayudantes -----------------------------------------------------------

def _sucursal(api: TestClient, admin: dict[str, str], nombre: str, indice_ciudad: int = 0) -> int:
    ciudades = api.get(CIUDADES, headers=admin).json()
    r = api.post(
        SUCURSALES,
        headers=admin,
        json={
            "ciudad_id": ciudades[indice_ciudad]["id"],
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
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _producto_con_variantes(api: TestClient, admin: dict[str, str]) -> dict:
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
    negro = api.post(
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
            "precio_base": "300.00",
            "activo": True,
        },
    )
    assert producto.status_code == 201, producto.text
    producto_id = producto.json()["id"]

    variantes = {}
    for etiqueta, talla in (("s", talla_s), ("m", talla_m)):
        r = api.post(
            f"{PRODUCTOS}/{producto_id}/variantes",
            headers=admin,
            json={"talla_id": talla, "color_id": negro},
        )
        assert r.status_code == 201, r.text
        variantes[etiqueta] = r.json()["id"]

    return {"producto_id": producto_id, **variantes}


def _ingresar(
    api: TestClient,
    admin: dict[str, str],
    *,
    sucursal_id: int,
    proveedor_id: int,
    variante_id: int,
    cantidad: int,
) -> None:
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": "REM-001",
            "lineas": [{"variante_id": variante_id, "cantidad": cantidad}],
        },
    )
    assert r.status_code == 201, r.text


@pytest.fixture
def red(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Dos sucursales en ciudades distintas, con stock repartido.

    La talla S está en las dos tiendas con cantidades distintas; la M, en
    ninguna. Es lo que permite comprobar a la vez el flujo principal y el
    alternativo de «sin stock».
    """
    admin = cabeceras_admin
    centro = _sucursal(api, admin, "Centro", indice_ciudad=0)
    norte = _sucursal(api, admin, "Norte", indice_ciudad=1)
    proveedor = _proveedor(api, admin)
    prendas = _producto_con_variantes(api, admin)

    _ingresar(
        api, admin, sucursal_id=centro, proveedor_id=proveedor,
        variante_id=prendas["s"], cantidad=7,
    )
    _ingresar(
        api, admin, sucursal_id=norte, proveedor_id=proveedor,
        variante_id=prendas["s"], cantidad=3,
    )

    return {"admin": admin, "centro": centro, "norte": norte, **prendas}


# --- Flujo principal -----------------------------------------------------

def test_la_disponibilidad_se_consulta_sin_token(api: TestClient, red) -> None:
    """Es público, como el resto de P5: se consulta antes de tener sesión."""
    assert api.get(_disponibilidad(red["s"])).status_code == 200


def test_lista_las_sucursales_con_su_ciudad_y_su_cantidad(
    api: TestClient, red
) -> None:
    cuerpo = api.get(_disponibilidad(red["s"])).json()

    assert cuerpo["variante_id"] == red["s"]
    assert cuerpo["talla_codigo"] == "S"
    assert cuerpo["color_nombre"] == "Negro"
    assert cuerpo["total_disponible"] == 10

    por_sucursal = {s["sucursal_nombre"]: s for s in cuerpo["sucursales"]}
    assert por_sucursal["Centro"]["cantidad_disponible"] == 7
    assert por_sucursal["Norte"]["cantidad_disponible"] == 3
    # La ciudad viaja resuelta: el cliente elige por ciudad antes que por
    # nombre de tienda, y sin esto la interfaz tendría que cruzarla.
    assert por_sucursal["Centro"]["ciudad_nombre"]
    assert por_sucursal["Norte"]["ciudad_nombre"] != por_sucursal["Centro"]["ciudad_nombre"]


def test_el_total_es_la_suma_de_las_sucursales(api: TestClient, red) -> None:
    cuerpo = api.get(_disponibilidad(red["s"])).json()
    assert cuerpo["total_disponible"] == sum(
        s["cantidad_disponible"] for s in cuerpo["sucursales"]
    )


def test_la_costura_devuelve_lo_mismo_que_el_inventario(
    api: TestClient, red
) -> None:
    """El cruce de la costura C1, comprobado contra la fuente.

    Si las dos mitades se desincronizaran, el cliente viajaría a una sucursal
    donde no hay nada. Se compara la vitrina contra el endpoint de existencias
    del propio paquete de Mateo, que lee la misma tabla por otro camino.
    """
    vitrina = api.get(_disponibilidad(red["s"])).json()
    inventario = api.get(EXISTENCIAS, headers=red["admin"]).json()

    esperado = {
        fila["sucursal_id"]: fila["cantidad_disponible"]
        for fila in inventario
        if fila["variante_id"] == red["s"] and fila["cantidad_disponible"] > 0
    }
    obtenido = {
        fila["sucursal_id"]: fila["cantidad_disponible"]
        for fila in vitrina["sucursales"]
    }
    assert obtenido == esperado


# --- Flujos alternativos -------------------------------------------------

def test_sin_stock_responde_la_variante_con_la_lista_vacia(
    api: TestClient, red
) -> None:
    """La talla M no entró a ninguna tienda.

    No es un 404: la prenda existe y se ofrece, lo que no hay es stock. La
    pantalla necesita poder decir «no disponible por ahora» sin que parezca que
    la prenda desapareció.
    """
    cuerpo = api.get(_disponibilidad(red["m"])).json()
    assert cuerpo["total_disponible"] == 0
    assert cuerpo["sucursales"] == []
    assert cuerpo["talla_codigo"] == "M"


def test_la_sucursal_en_cero_no_aparece(api: TestClient, red) -> None:
    """Para el inventario un saldo en cero es un dato legítimo —es lo que hace
    falta para reponer—; para la vitrina es ruido."""
    # La Norte tiene 3 de la talla S y nada de la M; pese a existir la
    # existencia de S, no debe listarse para la M.
    cuerpo = api.get(_disponibilidad(red["m"])).json()
    assert all(s["cantidad_disponible"] > 0 for s in cuerpo["sucursales"])


def test_no_se_publica_lo_reservado(api: TestClient, red) -> None:
    """`existencia` lleva disponible y reservada; acá solo puede salir la
    primera. Publicar lo apartado dejaría deducir el movimiento de cada tienda."""
    sucursal = api.get(_disponibilidad(red["s"])).json()["sucursales"][0]
    assert "cantidad_reservada" not in sucursal
    assert "cantidad_fisica" not in sucursal
    assert set(sucursal) == {
        "sucursal_id",
        "sucursal_nombre",
        "ciudad_nombre",
        "cantidad_disponible",
    }


# --- Excepciones ---------------------------------------------------------

def test_la_variante_inexistente_da_404(api: TestClient, red) -> None:
    assert api.get(_disponibilidad(999999)).status_code == 404


def test_la_variante_desactivada_da_404(api: TestClient, red) -> None:
    """La disponibilidad no puede ser una puerta trasera.

    Sin esta comprobación, una variante retirada del catálogo seguiría
    informando en qué sucursales hay stock de ella: se contaría por un endpoint
    lo que CU-17 y CU-18 ocultan.
    """
    r = api.patch(
        f"{VARIANTES}/{red['s']}", headers=red["admin"], json={"activa": False}
    )
    assert r.status_code == 200, r.text
    assert api.get(_disponibilidad(red["s"])).status_code == 404


def test_el_producto_desactivado_tapa_su_disponibilidad(
    api: TestClient, red
) -> None:
    r = api.patch(
        f"{PRODUCTOS}/{red['producto_id']}/estado",
        headers=red["admin"],
        json={"activo": False},
    )
    assert r.status_code == 200, r.text
    assert api.get(_disponibilidad(red["s"])).status_code == 404


def test_identificador_invalido_da_422(api: TestClient, red) -> None:
    assert api.get(_disponibilidad(0)).status_code == 422
