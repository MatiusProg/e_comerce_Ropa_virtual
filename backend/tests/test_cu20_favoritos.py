"""CU-20 · Gestionar favoritos.

El primer caso de uso del Ciclo 3, y el que estrena la **primera tabla propia de
P5**: durante el Ciclo 2 el paquete solo leía tablas de P3 y P4.

Se adelanta al Ciclo 3 por lo que desbloquea, no por su prioridad —que es Baja—:
el **RF31** dice que los favoritos «alimentan el historial de preferencias que
necesita el recomendador del RF25». Con CU-04 preferencias ya entregado, esto
completa la preferencia declarada que consume CU-33.

Lo que más importa cubrir:

- **Que marcar sea idempotente.** El corazón de una interfaz se toca dos veces
  sin querer; la clave primaria compuesta lo rechazaría con un error de base.
- **Que desmarcar no exija que la prenda siga ofreciéndose.** Si se desactivó
  después de marcarla, el cliente tiene que poder sacarla igual — si no, quedan
  favoritos imposibles de borrar.
- **Que la lista oculte lo que ya no se ofrece, sin borrar la fila.** Es
  historial de preferencia y lo usa CU-33; mostrarlo sería ofrecer algo que no
  se puede comprar.
- **Que los favoritos sean de cada quien.** Dos clientes no comparten lista.
"""

import pytest
from fastapi.testclient import TestClient

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
VARIANTES = "/api/v1/catalogo/variantes"

FAVORITOS = "/api/v1/tienda/favoritos"
IDS = f"{FAVORITOS}/ids"


def _catalogo(api: TestClient, admin: dict[str, str]) -> dict:
    """Tres productos ofrecibles, cada uno con una variante activa."""
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

    productos = {}
    for etiqueta, codigo, nombre in (
        ("uno", "BLU-001", "Blusa de seda"),
        ("dos", "BLU-002", "Blusa de lino"),
        ("tres", "BLU-003", "Blusa estampada"),
    ):
        r = api.post(
            PRODUCTOS,
            headers=admin,
            json={
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": categoria,
                "precio_base": "300.00",
                "activo": True,
            },
        )
        assert r.status_code == 201, r.text
        producto_id = r.json()["id"]
        v = api.post(
            f"{PRODUCTOS}/{producto_id}/variantes",
            headers=admin,
            json={"talla_id": talla, "color_id": color},
        )
        assert v.status_code == 201, v.text
        productos[etiqueta] = producto_id
        productos[f"variante_{etiqueta}"] = v.json()["id"]

    return productos


@pytest.fixture
def catalogo(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    return {"admin": cabeceras_admin, **_catalogo(api, cabeceras_admin)}


# --- Autorización --------------------------------------------------------

def test_sin_token_no_hay_favoritos(api: TestClient) -> None:
    """A diferencia del resto de P5, esto no es público: un favorito es de
    alguien, y sin sesión no hay de quién."""
    assert api.get(FAVORITOS).status_code == 401
    assert api.put(f"{FAVORITOS}/1").status_code == 401


def test_un_administrador_no_tiene_favoritos(
    api: TestClient, cabeceras_admin: dict[str, str], catalogo
) -> None:
    assert api.get(FAVORITOS, headers=cabeceras_admin).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_la_lista_arranca_vacia(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    cuerpo = api.get(FAVORITOS, headers=cabeceras_cliente).json()
    assert cuerpo["total"] == 0
    assert cuerpo["items"] == []


def test_marcar_y_ver_la_prenda_en_la_lista(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    r = api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    assert r.status_code == 204, r.text

    cuerpo = api.get(FAVORITOS, headers=cabeceras_cliente).json()
    assert cuerpo["total"] == 1
    assert cuerpo["items"][0]["id"] == catalogo["uno"]


def test_la_tarjeta_es_la_misma_que_la_de_la_vitrina(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    """La pantalla de favoritos muestra lo mismo que el catálogo: si los
    esquemas difirieran, la misma prenda se vería distinta en cada lugar."""
    api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)

    favorito = api.get(FAVORITOS, headers=cabeceras_cliente).json()["items"][0]
    vitrina = next(
        p
        for p in api.get("/api/v1/tienda/productos").json()["items"]
        if p["id"] == catalogo["uno"]
    )
    assert favorito == vitrina


def test_desmarcar_la_saca_de_la_lista(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    r = api.delete(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    assert r.status_code == 204, r.text
    assert api.get(FAVORITOS, headers=cabeceras_cliente).json()["total"] == 0


def test_lo_ultimo_marcado_va_primero(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    for etiqueta in ("uno", "dos", "tres"):
        api.put(f"{FAVORITOS}/{catalogo[etiqueta]}", headers=cabeceras_cliente)

    ids = [p["id"] for p in api.get(FAVORITOS, headers=cabeceras_cliente).json()["items"]]
    assert ids[0] == catalogo["tres"]


# --- Idempotencia --------------------------------------------------------

def test_marcar_dos_veces_no_duplica_ni_falla(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    """La clave primaria compuesta lo rechazaría con un error de base; un doble
    toque del corazón no puede ser un error."""
    assert api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente).status_code == 204
    assert api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente).status_code == 204
    assert api.get(FAVORITOS, headers=cabeceras_cliente).json()["total"] == 1


def test_desmarcar_lo_que_no_estaba_no_falla(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    r = api.delete(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    assert r.status_code == 204


# --- Los ids, para pintar los corazones ---------------------------------

def test_los_ids_devuelven_solo_los_marcados(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    api.put(f"{FAVORITOS}/{catalogo['tres']}", headers=cabeceras_cliente)

    ids = api.get(IDS, headers=cabeceras_cliente).json()
    assert sorted(ids) == sorted([catalogo["uno"], catalogo["tres"]])


def test_la_ruta_ids_no_la_toma_el_detalle(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    """`/ids` se declara antes que `/{producto_id}`: al revés, FastAPI leería
    «ids» como un entero y devolvería 422."""
    assert api.get(IDS, headers=cabeceras_cliente).status_code == 200


# --- Solo se marca lo ofrecible -----------------------------------------

def test_no_se_puede_marcar_una_prenda_inexistente(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    assert api.put(f"{FAVORITOS}/999999", headers=cabeceras_cliente).status_code == 404


def test_no_se_puede_marcar_una_prenda_desactivada(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    """Sin esto, el favorito sería una forma de guardar referencias a productos
    que el catálogo oculta."""
    api.patch(
        f"{PRODUCTOS}/{catalogo['uno']}/estado",
        headers=catalogo["admin"],
        json={"activo": False},
    )
    assert api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente).status_code == 404


def test_no_se_puede_marcar_una_prenda_sin_variantes_activas(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    api.patch(
        f"{VARIANTES}/{catalogo['variante_uno']}",
        headers=catalogo["admin"],
        json={"activa": False},
    )
    assert api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente).status_code == 404


# --- La prenda que deja de ofrecerse después de marcada -----------------

def test_la_prenda_desactivada_desaparece_de_la_lista_pero_no_de_la_tabla(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    """La fila no se borra —es historial de preferencia y lo usa CU-33 (RF31)—
    pero no se muestra: sería ofrecer algo que no se puede comprar."""
    api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    api.patch(
        f"{PRODUCTOS}/{catalogo['uno']}/estado",
        headers=catalogo["admin"],
        json={"activo": False},
    )

    assert api.get(FAVORITOS, headers=cabeceras_cliente).json()["total"] == 0
    # Pero la fila sigue ahí: los ids la devuelven.
    assert catalogo["uno"] in api.get(IDS, headers=cabeceras_cliente).json()


def test_se_puede_desmarcar_una_prenda_que_dejo_de_ofrecerse(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    """Exigir que sea ofrecible para desmarcar dejaría favoritos imposibles de
    borrar."""
    api.put(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    api.patch(
        f"{PRODUCTOS}/{catalogo['uno']}/estado",
        headers=catalogo["admin"],
        json={"activo": False},
    )

    r = api.delete(f"{FAVORITOS}/{catalogo['uno']}", headers=cabeceras_cliente)
    assert r.status_code == 204
    assert api.get(IDS, headers=cabeceras_cliente).json() == []


# --- Paginación ----------------------------------------------------------

def test_el_total_no_depende_de_la_pagina(
    api: TestClient, cabeceras_cliente: dict[str, str], catalogo
) -> None:
    for etiqueta in ("uno", "dos", "tres"):
        api.put(f"{FAVORITOS}/{catalogo[etiqueta]}", headers=cabeceras_cliente)

    primera = api.get(FAVORITOS, headers=cabeceras_cliente, params={"tamano": 2}).json()
    segunda = api.get(
        FAVORITOS, headers=cabeceras_cliente, params={"tamano": 2, "pagina": 2}
    ).json()

    assert primera["total"] == segunda["total"] == 3
    assert len(primera["items"]) == 2
    assert len(segunda["items"]) == 1
    vistos = [p["id"] for p in primera["items"] + segunda["items"]]
    assert len(set(vistos)) == 3
