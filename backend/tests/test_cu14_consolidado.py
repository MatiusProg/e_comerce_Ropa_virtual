"""CU-14 · Consultar inventario consolidado.

La vista de red del Administrador. Es de Karen por la §4.1 de la
contrapropuesta —el único caso de uso de inventario que no escribe ninguna
tabla— y se apoya en la costura C1, igual que CU-19.

Lo que más importa cubrir:

- **Que agrupe por variante y no por (variante, sucursal).** Es lo que distingue
  esta pantalla de la pestaña de existencias de CU-13/CU-15: una prenda repartida
  en tres tiendas tiene que ocupar una fila con el reparto adentro, no tres.
- **Que «agotada» gane sobre «reservada».** Una variante con 0 disponibles y 3
  apartadas está agotada para quien quiera comprarla hoy; decir «reservada» haría
  creer que hay algo que ofrecer.
- **Que filtrar por sucursal filtre antes de agrupar.** Preguntar «qué hay en la
  Centro» tiene que devolver los saldos de la Centro, no las variantes que están
  en la Centro con su reparto en toda la red.
- **Que el resumen sume lo filtrado y no la página.** Un resumen que solo suma
  las veinte filas visibles no es un resumen.
- **Que sea solo del Administrador.** El Encargado tiene su ámbito acotado a su
  sucursal y su caso de uso es CU-16.
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
INGRESOS = "/api/v1/inventario/ingresos"

CONSOLIDADO = "/api/v1/inventario/consolidado"


# --- Ayudantes -----------------------------------------------------------

def _sucursal(api: TestClient, admin: dict[str, str], nombre: str, ciudad: int = 0) -> int:
    ciudades = api.get(CIUDADES, headers=admin).json()
    r = api.post(
        SUCURSALES,
        headers=admin,
        json={
            "ciudad_id": ciudades[ciudad]["id"],
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


def _variantes(api: TestClient, admin: dict[str, str]) -> dict:
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
    ).json()

    variantes = {}
    for etiqueta, talla in (("s", talla_s), ("m", talla_m)):
        r = api.post(
            f"{PRODUCTOS}/{producto['id']}/variantes",
            headers=admin,
            json={"talla_id": talla, "color_id": negro},
        )
        assert r.status_code == 201, r.text
        variantes[etiqueta] = r.json()["id"]

    return {"producto_id": producto["id"], **variantes}


def _ingresar(api, admin, *, sucursal_id, proveedor_id, variante_id, cantidad) -> None:
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
    """La talla S repartida en dos tiendas; la M, solo en una.

    Es lo mínimo para poder comprobar a la vez la agrupación, el reparto y el
    filtro por sucursal.
    """
    admin = cabeceras_admin
    centro = _sucursal(api, admin, "Centro", ciudad=0)
    norte = _sucursal(api, admin, "Norte", ciudad=1)
    proveedor = _proveedor(api, admin)
    prendas = _variantes(api, admin)

    _ingresar(api, admin, sucursal_id=centro, proveedor_id=proveedor,
              variante_id=prendas["s"], cantidad=7)
    _ingresar(api, admin, sucursal_id=norte, proveedor_id=proveedor,
              variante_id=prendas["s"], cantidad=3)
    _ingresar(api, admin, sucursal_id=centro, proveedor_id=proveedor,
              variante_id=prendas["m"], cantidad=5)

    return {"admin": admin, "centro": centro, "norte": norte, **prendas}


# --- Autorización --------------------------------------------------------

def test_sin_token_no_se_consulta(api: TestClient) -> None:
    assert api.get(CONSOLIDADO).status_code == 401


def test_un_cliente_no_entra(api: TestClient, cabeceras_cliente: dict[str, str]) -> None:
    assert api.get(CONSOLIDADO, headers=cabeceras_cliente).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_agrupa_por_variante_con_su_reparto(api: TestClient, red) -> None:
    """Una prenda repartida en dos tiendas ocupa UNA fila, no dos.

    Es la diferencia de fondo con la pestaña de existencias de CU-13 y CU-15.
    """
    cuerpo = api.get(CONSOLIDADO, headers=red["admin"]).json()
    items = cuerpo["listado"]["items"]

    assert cuerpo["listado"]["total"] == 2  # dos variantes, no tres filas

    talla_s = next(i for i in items if i["variante_id"] == red["s"])
    assert talla_s["total_disponible"] == 10
    assert talla_s["sucursales_con_saldo"] == 2
    assert {s["sucursal"] for s in talla_s["sucursales"]} == {"Centro", "Norte"}
    assert sum(s["cantidad_disponible"] for s in talla_s["sucursales"]) == 10


def test_el_total_fisico_es_disponible_mas_reservado(api: TestClient, red) -> None:
    item = api.get(CONSOLIDADO, headers=red["admin"]).json()["listado"]["items"][0]
    assert item["total_fisico"] == item["total_disponible"] + item["total_reservado"]


def test_la_prenda_viaja_nombrada_y_no_con_el_identificador(
    api: TestClient, red
) -> None:
    """«Variante 412» no le dice nada a quien mira el inventario."""
    item = api.get(CONSOLIDADO, headers=red["admin"]).json()["listado"]["items"][0]
    assert item["producto"] == "Blusa de seda"
    assert item["talla"] in {"S", "M"}
    assert item["color"] == "Negro"
    assert item["sku"]


# --- Estado --------------------------------------------------------------

def test_con_saldo_la_variante_esta_disponible(api: TestClient, red) -> None:
    items = api.get(CONSOLIDADO, headers=red["admin"]).json()["listado"]["items"]
    assert all(i["estado"] == "disponible" for i in items)


def test_la_variante_sin_existencia_no_aparece(api: TestClient, red) -> None:
    """Sin ingreso no hay fila en `existencia`, así que no hay nada que listar.

    Es una consecuencia del modelo y conviene dejarla escrita: el consolidado
    muestra lo que alguna vez entró, no el catálogo entero.
    """
    cuerpo = api.get(CONSOLIDADO, headers=red["admin"]).json()
    assert cuerpo["listado"]["total"] == 2


def test_el_estado_proximo_a_ingresar_no_lo_produce_nadie(
    api: TestClient, red
) -> None:
    """El agujero H1 del análisis de alcance, comprobado.

    El enunciado pide distinguir la mercadería «próxima a ingresar», y CU-14 lo
    promete, pero **ningún caso de uso la anuncia**: CU-13 registra lo que ya
    llegó. El filtro existe en el contrato y hoy no devuelve nada. Lo cerraría
    el CU-39 propuesto el 10/09.
    """
    cuerpo = api.get(
        CONSOLIDADO, headers=red["admin"], params={"estado": "proxima_a_ingresar"}
    ).json()
    assert cuerpo["listado"]["total"] == 0
    assert cuerpo["resumen"]["variantes"] == 0


# --- Filtros -------------------------------------------------------------

def test_filtrar_por_sucursal_filtra_antes_de_agrupar(api: TestClient, red) -> None:
    """«Qué hay en la Norte» devuelve los saldos de la Norte.

    No las variantes que están en la Norte con su reparto en toda la red: eso
    sería una vista de red disfrazada de vista de tienda.
    """
    cuerpo = api.get(
        CONSOLIDADO, headers=red["admin"], params={"sucursal_id": red["norte"]}
    ).json()
    items = cuerpo["listado"]["items"]

    assert len(items) == 1  # solo la talla S llegó a la Norte
    assert items[0]["total_disponible"] == 3
    assert [s["sucursal"] for s in items[0]["sucursales"]] == ["Norte"]


def test_buscar_por_sku(api: TestClient, red) -> None:
    sku = api.get(CONSOLIDADO, headers=red["admin"]).json()["listado"]["items"][0]["sku"]
    cuerpo = api.get(CONSOLIDADO, headers=red["admin"], params={"busqueda": sku}).json()
    assert cuerpo["listado"]["total"] == 1


def test_buscar_por_nombre_de_prenda(api: TestClient, red) -> None:
    cuerpo = api.get(
        CONSOLIDADO, headers=red["admin"], params={"busqueda": "seda"}
    ).json()
    assert cuerpo["listado"]["total"] == 2


def test_ordenar_por_disponible(api: TestClient, red) -> None:
    ascendente = api.get(
        CONSOLIDADO, headers=red["admin"], params={"orden": "disponible_asc"}
    ).json()["listado"]["items"]
    descendente = api.get(
        CONSOLIDADO, headers=red["admin"], params={"orden": "disponible_desc"}
    ).json()["listado"]["items"]

    assert ascendente[0]["total_disponible"] == 5
    assert descendente[0]["total_disponible"] == 10


def test_un_orden_inventado_da_422(api: TestClient, red) -> None:
    assert (
        api.get(CONSOLIDADO, headers=red["admin"], params={"orden": "por_color"}).status_code
        == 422
    )


# --- Resumen y paginación ------------------------------------------------

def test_el_resumen_suma_lo_filtrado_y_no_la_pagina(api: TestClient, red) -> None:
    """Con una fila por página, el resumen tiene que seguir sumando las dos."""
    cuerpo = api.get(
        CONSOLIDADO, headers=red["admin"], params={"tamano": 1, "pagina": 1}
    ).json()

    assert len(cuerpo["listado"]["items"]) == 1
    assert cuerpo["listado"]["total"] == 2
    assert cuerpo["resumen"]["variantes"] == 2
    assert cuerpo["resumen"]["total_disponible"] == 15


def test_el_resumen_respeta_el_filtro(api: TestClient, red) -> None:
    cuerpo = api.get(
        CONSOLIDADO, headers=red["admin"], params={"sucursal_id": red["norte"]}
    ).json()
    assert cuerpo["resumen"]["variantes"] == 1
    assert cuerpo["resumen"]["total_disponible"] == 3


def test_paginar_no_repite_ni_pierde_filas(api: TestClient, red) -> None:
    primera = api.get(
        CONSOLIDADO, headers=red["admin"], params={"tamano": 1, "pagina": 1}
    ).json()["listado"]["items"]
    segunda = api.get(
        CONSOLIDADO, headers=red["admin"], params={"tamano": 1, "pagina": 2}
    ).json()["listado"]["items"]

    assert primera[0]["variante_id"] != segunda[0]["variante_id"]
