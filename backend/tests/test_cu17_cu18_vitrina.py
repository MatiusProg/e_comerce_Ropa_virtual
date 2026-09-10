"""CU-17 · Consultar catálogo · y CU-18 · Consultar ficha de producto.

La vitrina pública. Lo que estas pruebas cubren, y que ni la base ni el router
garantizan por sí solos:

- **Es pública de verdad.** Sin token devuelve 200. Es el flujo principal de
  CU-17: en la app móvil la pantalla de catálogo se abre antes de que exista
  sesión, y el RF07 no pone precondición de autenticación.
- **Solo se ofrece lo comprable.** Producto inactivo, o sin ninguna variante
  activa, no aparece en el listado ni tiene ficha. Un producto sin variantes
  activas no tiene precio, ni SKU, ni existencia: mostrarlo es prometer algo que
  no se puede cumplir.
- **La ficha desactivada responde 404, no 403.** Distinguirlos convertiría la
  ficha en un detector de productos ocultos: bastaría recorrer identificadores
  para saber cuáles existen desactivados.
- **Filtrar por categoría alcanza a las subcategorías.** Los productos se cargan
  en las hojas del árbol («Mujer > Blusas»), así que filtrar por la raíz sin
  recorrer los descendientes devolvería cero.
- **El paginador cuenta lo mismo que lista.** Los filtros del conteo y los del
  listado son la misma función a propósito; si se separaran, el defecto solo
  aparecería paginando hasta el final.
- **Las tallas salen en el orden del maestro y no en el alfabético.** Sin
  `Talla.orden`, XL aparece antes que S, y la ficha es donde se nota.
- **La costura C5.** Cada variante viaja con el PNG transparente de su vestidor,
  y ese PNG no se cuela entre las fotos de la galería.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
TEMPORADAS = "/api/v1/catalogo/temporadas"
PRODUCTOS = "/api/v1/catalogo/productos"
IMAGENES = "/api/v1/catalogo/imagenes"

VITRINA = "/api/v1/tienda/productos"
FILTROS = "/api/v1/tienda/filtros"


@pytest.fixture(autouse=True)
def volumen_temporal(tmp_path, monkeypatch):
    """El volumen de imágenes, dentro de la carpeta temporal de la prueba.

    Igual que en CU-11: sin esto, MEDIA_ROOT apunta a `/app/media`, que es la
    ruta del contenedor de Railway.
    """
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    return tmp_path / "media"


# --- Ayudantes -----------------------------------------------------------

def _categoria(api, admin, nombre: str, padre: int | None = None) -> int:
    cuerpo = {"nombre": nombre, "orden": 0, "activa": True}
    if padre is not None:
        cuerpo["categoria_padre_id"] = padre
    r = api.post(CATEGORIAS, headers=admin, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _talla(api, admin, codigo: str, orden: int) -> int:
    r = api.post(
        TALLAS,
        headers=admin,
        json={"tipo_prenda": "Superior", "codigo": codigo, "orden": orden, "activa": True},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _color(api, admin, nombre: str, hexa: str) -> int:
    r = api.post(
        COLORES, headers=admin, json={"nombre": nombre, "hexadecimal": hexa, "activo": True}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _producto(api, admin, *, codigo: str, categoria_id: int, nombre: str = "Camisa Oxford",
              precio: str = "250.00", **extra) -> dict:
    cuerpo = {
        "codigo": codigo,
        "nombre": nombre,
        "categoria_id": categoria_id,
        "precio_base": precio,
        "activo": True,
    }
    cuerpo.update(extra)
    r = api.post(PRODUCTOS, headers=admin, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _variante(api, admin, producto_id: int, talla_id: int, color_id: int,
              precio: str | None = None) -> dict:
    cuerpo = {"talla_id": talla_id, "color_id": color_id}
    if precio is not None:
        cuerpo["precio"] = precio
    r = api.post(f"{PRODUCTOS}/{producto_id}/variantes", headers=admin, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _png(alfa: int = 0) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", (24, 24), (200, 30, 60, alfa)).save(buffer, format="PNG")
    return buffer.getvalue()


def _subir(api, admin, producto_id: int, contenido: bytes, variante_id: int | None = None) -> dict:
    params = {"variante_id": variante_id} if variante_id is not None else None
    r = api.post(
        f"{PRODUCTOS}/{producto_id}/imagenes",
        headers=admin,
        files={"archivo": ("foto.png", contenido, "image/png")},
        params=params,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def vitrina(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Un catálogo mínimo pero realista, cargado por la API de CU-10 y CU-11.

    Dos categorías anidadas, tres tallas con orden explícito, dos colores y tres
    productos: uno completo, uno inactivo y uno sin variantes activas. Los dos
    últimos son los que no tienen que aparecer.
    """
    admin = cabeceras_admin
    raiz = _categoria(api, admin, "Mujer")
    hoja = _categoria(api, admin, "Blusas", padre=raiz)
    otra = _categoria(api, admin, "Pantalones")

    talla_s = _talla(api, admin, "S", 1)
    talla_m = _talla(api, admin, "M", 2)
    talla_xl = _talla(api, admin, "XL", 4)
    negro = _color(api, admin, "Negro", "#101010")
    rojo = _color(api, admin, "Rojo", "#D02020")

    # El producto completo: tres variantes de precio distinto, en la hoja del
    # árbol de categorías.
    blusa = _producto(api, admin, codigo="BLU-001", categoria_id=hoja,
                      nombre="Blusa de seda", precio="300.00")
    v_xl = _variante(api, admin, blusa["id"], talla_xl, negro, "360.00")
    v_s = _variante(api, admin, blusa["id"], talla_s, negro, "300.00")
    v_m = _variante(api, admin, blusa["id"], talla_m, rojo, "330.00")

    # Otro producto, en otra categoría y más barato: sirve para el orden por
    # precio y para que el filtro por categoría tenga algo que dejar fuera.
    pantalon = _producto(api, admin, codigo="PAN-001", categoria_id=otra,
                         nombre="Pantalón recto", precio="180.00")
    _variante(api, admin, pantalon["id"], talla_m, negro, "180.00")

    # Producto desactivado: no se ofrece.
    oculto = _producto(api, admin, codigo="OCU-001", categoria_id=hoja, nombre="Prenda oculta")
    _variante(api, admin, oculto["id"], talla_s, rojo)
    r = api.patch(f"{PRODUCTOS}/{oculto['id']}/estado", headers=admin, json={"activo": False})
    assert r.status_code == 200, r.text

    # Producto activo pero sin ninguna variante activa: tampoco se ofrece.
    sin_stock = _producto(api, admin, codigo="SIN-001", categoria_id=hoja, nombre="Sin variantes")

    return {
        "admin": admin,
        "categoria_raiz": raiz,
        "categoria_hoja": hoja,
        "categoria_otra": otra,
        "talla_s": talla_s,
        "talla_m": talla_m,
        "talla_xl": talla_xl,
        "negro": negro,
        "rojo": rojo,
        "blusa": blusa["id"],
        "pantalon": pantalon["id"],
        "oculto": oculto["id"],
        "sin_variantes": sin_stock["id"],
        "variante_s": v_s["id"],
        "variante_m": v_m["id"],
        "variante_xl": v_xl["id"],
    }


# --- La vitrina es pública -----------------------------------------------

def test_el_catalogo_se_consulta_sin_token(api: TestClient, vitrina) -> None:
    """Flujo principal de CU-17: no hay precondición de sesión.

    En la app móvil la pantalla de catálogo se abre antes de que exista token.
    """
    r = api.get(VITRINA)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 2


def test_la_ficha_se_consulta_sin_token(api: TestClient, vitrina) -> None:
    assert api.get(f"{VITRINA}/{vitrina['blusa']}").status_code == 200


def test_los_filtros_se_consultan_sin_token(api: TestClient, vitrina) -> None:
    assert api.get(FILTROS).status_code == 200


def test_la_vitrina_no_expone_el_proveedor_ni_el_precio_base(
    api: TestClient, vitrina
) -> None:
    """La cara pública no es la de CU-10.

    Reutilizar el esquema del Administrador filtraría al cliente quién abastece
    cada prenda y a qué precio entró.
    """
    fila = api.get(VITRINA).json()["items"][0]
    assert "proveedor_id" not in fila
    assert "precio_base" not in fila
    assert "activo" not in fila


# --- Solo se ofrece lo comprable -----------------------------------------

def test_el_producto_desactivado_no_aparece(api: TestClient, vitrina) -> None:
    codigos = {p["codigo"] for p in api.get(VITRINA).json()["items"]}
    assert "OCU-001" not in codigos


def test_el_producto_sin_variantes_activas_no_aparece(api: TestClient, vitrina) -> None:
    """Sin variantes activas no hay precio, ni SKU, ni existencia que ofrecer."""
    codigos = {p["codigo"] for p in api.get(VITRINA).json()["items"]}
    assert "SIN-001" not in codigos


def test_la_ficha_de_un_producto_desactivado_da_404(api: TestClient, vitrina) -> None:
    """404 y no 403: distinguirlos volvería la ficha un detector de ocultos."""
    assert api.get(f"{VITRINA}/{vitrina['oculto']}").status_code == 404


def test_la_ficha_sin_variantes_activas_da_404(api: TestClient, vitrina) -> None:
    assert api.get(f"{VITRINA}/{vitrina['sin_variantes']}").status_code == 404


def test_la_ficha_inexistente_da_404(api: TestClient, vitrina) -> None:
    assert api.get(f"{VITRINA}/999999").status_code == 404


def test_una_variante_desactivada_desaparece_de_la_ficha(
    api: TestClient, vitrina
) -> None:
    r = api.patch(
        f"/api/v1/catalogo/variantes/{vitrina['variante_xl']}",
        headers=vitrina["admin"],
        json={"activa": False},
    )
    assert r.status_code == 200, r.text

    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    assert vitrina["variante_xl"] not in [v["id"] for v in ficha["variantes"]]
    # Y el rango de precios se recalcula: 360 era el máximo y ya no se ofrece.
    assert ficha["precio_hasta"] == "330.00"


# --- Búsqueda y filtros (paso 2 de CU-17) --------------------------------

def test_busqueda_por_nombre(api: TestClient, vitrina) -> None:
    items = api.get(VITRINA, params={"busqueda": "seda"}).json()["items"]
    assert [p["codigo"] for p in items] == ["BLU-001"]


def test_busqueda_por_codigo(api: TestClient, vitrina) -> None:
    items = api.get(VITRINA, params={"busqueda": "pan-"}).json()["items"]
    assert [p["codigo"] for p in items] == ["PAN-001"]


def test_filtrar_por_categoria_alcanza_a_las_subcategorias(
    api: TestClient, vitrina
) -> None:
    """El caso que sin el CTE recursivo devolvería cero.

    La blusa está en «Mujer > Blusas»; el filtro se pide sobre «Mujer».
    """
    items = api.get(VITRINA, params={"categoria_id": vitrina["categoria_raiz"]}).json()["items"]
    assert [p["codigo"] for p in items] == ["BLU-001"]


def test_filtrar_por_la_hoja_devuelve_lo_mismo(api: TestClient, vitrina) -> None:
    items = api.get(VITRINA, params={"categoria_id": vitrina["categoria_hoja"]}).json()["items"]
    assert [p["codigo"] for p in items] == ["BLU-001"]


def test_filtrar_por_talla(api: TestClient, vitrina) -> None:
    """Solo la blusa tiene talla S; el pantalón es M."""
    items = api.get(VITRINA, params={"talla_id": vitrina["talla_s"]}).json()["items"]
    assert [p["codigo"] for p in items] == ["BLU-001"]


def test_filtrar_por_color(api: TestClient, vitrina) -> None:
    items = api.get(VITRINA, params={"color_id": vitrina["rojo"]}).json()["items"]
    assert [p["codigo"] for p in items] == ["BLU-001"]


def test_filtrar_por_precio(api: TestClient, vitrina) -> None:
    """El pantalón vale 180 y la blusa arranca en 300."""
    items = api.get(VITRINA, params={"precio_max": "200"}).json()["items"]
    assert [p["codigo"] for p in items] == ["PAN-001"]


def test_un_producto_con_varias_variantes_del_color_aparece_una_sola_vez(
    api: TestClient, vitrina
) -> None:
    """El motivo por el que los filtros usan EXISTS y no JOIN.

    La blusa tiene dos variantes negras. Con JOIN, la fila del producto se
    duplicaría y el LIMIT cortaría por la mitad de un producto.
    """
    pagina = api.get(VITRINA, params={"color_id": vitrina["negro"]}).json()
    codigos = [p["codigo"] for p in pagina["items"]]
    assert len(codigos) == len(set(codigos))
    assert pagina["total"] == len(codigos)


# --- Orden y paginación --------------------------------------------------

def test_orden_por_precio_ascendente(api: TestClient, vitrina) -> None:
    items = api.get(VITRINA, params={"orden": "precio_asc"}).json()["items"]
    assert [p["codigo"] for p in items] == ["PAN-001", "BLU-001"]


def test_orden_por_precio_descendente(api: TestClient, vitrina) -> None:
    items = api.get(VITRINA, params={"orden": "precio_desc"}).json()["items"]
    assert [p["codigo"] for p in items] == ["BLU-001", "PAN-001"]


def test_un_orden_inventado_da_422(api: TestClient, vitrina) -> None:
    """El `Literal` del router: un 422 que nombra las opciones, no un KeyError."""
    assert api.get(VITRINA, params={"orden": "por_simpatia"}).status_code == 422


def test_el_total_coincide_con_lo_que_se_lista(api: TestClient, vitrina) -> None:
    """El conteo y el listado filtran con la misma función, a propósito."""
    primera = api.get(VITRINA, params={"tamano": 1, "pagina": 1}).json()
    segunda = api.get(VITRINA, params={"tamano": 1, "pagina": 2}).json()

    assert primera["total"] == segunda["total"] == 2
    assert len(primera["items"]) == len(segunda["items"]) == 1
    # Ningún producto en las dos páginas: es lo que garantiza el desempate por id.
    assert primera["items"][0]["id"] != segunda["items"][0]["id"]


def test_el_tamano_de_pagina_tiene_tope(api: TestClient, vitrina) -> None:
    """Sin tope, `tamano=100000` traería el catálogo entero con todo dentro."""
    assert api.get(VITRINA, params={"tamano": 100000}).status_code == 422


# --- La tarjeta del listado ----------------------------------------------

def test_la_tarjeta_trae_el_rango_de_precios_y_los_colores(
    api: TestClient, vitrina
) -> None:
    items = api.get(VITRINA, params={"busqueda": "seda"}).json()["items"]
    tarjeta = items[0]
    assert tarjeta["precio_desde"] == "300.00"
    assert tarjeta["precio_hasta"] == "360.00"
    assert {c["nombre"] for c in tarjeta["colores"]} == {"Negro", "Rojo"}
    assert tarjeta["categoria_nombre"] == "Blusas"


def test_sin_fotos_la_tarjeta_no_trae_imagen(api: TestClient, vitrina) -> None:
    """Nula, no vacía: la interfaz dibuja su marcador."""
    tarjeta = api.get(VITRINA, params={"busqueda": "seda"}).json()["items"][0]
    assert tarjeta["imagen_url"] is None


def test_la_tarjeta_trae_la_imagen_principal(api: TestClient, vitrina) -> None:
    _subir(api, vitrina["admin"], vitrina["blusa"], _png(alfa=255))
    tarjeta = api.get(VITRINA, params={"busqueda": "seda"}).json()["items"][0]
    assert tarjeta["imagen_url"] is not None
    assert tarjeta["imagen_url"].startswith(settings.MEDIA_URL)


def test_el_png_del_vestidor_no_se_usa_como_foto_de_catalogo(
    api: TestClient, vitrina
) -> None:
    """Es un recorte con fondo transparente: en la vitrina se vería suelto."""
    imagen = _subir(
        api, vitrina["admin"], vitrina["blusa"], _png(alfa=0), variante_id=vitrina["variante_s"]
    )
    r = api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=vitrina["admin"],
        json={"es_transparente": True},
    )
    assert r.status_code == 200, r.text

    tarjeta = api.get(VITRINA, params={"busqueda": "seda"}).json()["items"][0]
    assert tarjeta["imagen_url"] is None
    assert tarjeta["tiene_vestidor"] is True


# --- La ficha (CU-18) ----------------------------------------------------

def test_la_ficha_trae_variantes_tallas_y_colores(api: TestClient, vitrina) -> None:
    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    assert ficha["nombre"] == "Blusa de seda"
    assert len(ficha["variantes"]) == 3
    assert [t["codigo"] for t in ficha["tallas"]] == ["S", "M", "XL"]
    assert {c["nombre"] for c in ficha["colores"]} == {"Negro", "Rojo"}


def test_las_tallas_salen_en_el_orden_del_maestro(api: TestClient, vitrina) -> None:
    """Sin `Talla.orden`, el alfabético pondría M, S, XL --- y XL antes que S."""
    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    assert [v["talla_codigo"] for v in ficha["variantes"]] == ["S", "M", "XL"]


def test_cada_variante_trae_su_precio_y_su_color(api: TestClient, vitrina) -> None:
    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    primera = ficha["variantes"][0]
    assert primera["precio"] == "300.00"
    assert primera["color_hexadecimal"] == "#101010"
    assert primera["sku"]


# --- Costura C5 · la ficha entrega el activo del vestidor virtual --------

def test_la_variante_trae_el_png_del_vestidor(api: TestClient, vitrina) -> None:
    """La mitad de la costura C5.

    La pantalla de realidad aumentada recibe el activo al navegar y no vuelve a
    consultar la API ni conoce la tabla de imágenes.
    """
    imagen = _subir(
        api, vitrina["admin"], vitrina["blusa"], _png(alfa=0), variante_id=vitrina["variante_m"]
    )
    api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=vitrina["admin"],
        json={"es_transparente": True},
    )

    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    assert ficha["tiene_vestidor"] is True

    por_id = {v["id"]: v for v in ficha["variantes"]}
    assert por_id[vitrina["variante_m"]]["imagen_vestidor_url"] is not None
    # Las otras dos no tienen PNG propio: el botón se habilita por variante.
    assert por_id[vitrina["variante_s"]]["imagen_vestidor_url"] is None


def test_sin_png_transparente_la_ficha_no_ofrece_vestidor(
    api: TestClient, vitrina
) -> None:
    """Si el prototipo de RA no encuentra imagen es un dato que falta, no un
    error de código: la ficha lo dice de antemano (supuesto S5)."""
    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    assert ficha["tiene_vestidor"] is False
    assert all(v["imagen_vestidor_url"] is None for v in ficha["variantes"])


def test_el_png_del_vestidor_no_entra_en_la_galeria(api: TestClient, vitrina) -> None:
    """Viaja dentro de su variante, no suelto entre las fotos del producto."""
    _subir(api, vitrina["admin"], vitrina["blusa"], _png(alfa=255))
    imagen = _subir(
        api, vitrina["admin"], vitrina["blusa"], _png(alfa=0), variante_id=vitrina["variante_m"]
    )
    api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=vitrina["admin"],
        json={"es_transparente": True},
    )

    ficha = api.get(f"{VITRINA}/{vitrina['blusa']}").json()
    assert [i["id"] for i in ficha["imagenes"]] == [
        i["id"] for i in ficha["imagenes"] if i["id"] != imagen["id"]
    ]
    assert len(ficha["imagenes"]) == 1


# --- Opciones de filtrado ------------------------------------------------

def test_los_filtros_solo_ofrecen_lo_que_el_catalogo_tiene(
    api: TestClient, vitrina
) -> None:
    """Una talla que ningún producto usa es una opción que vacía la vitrina al
    elegirla, y el cliente no tiene forma de saber por qué."""
    _talla(api, vitrina["admin"], "XXL", 5)
    _color(api, vitrina["admin"], "Turquesa", "#30D0C0")

    filtros = api.get(FILTROS).json()
    assert "XXL" not in [t["codigo"] for t in filtros["tallas"]]
    assert "Turquesa" not in [c["nombre"] for c in filtros["colores"]]
    assert {t["codigo"] for t in filtros["tallas"]} == {"S", "M", "XL"}


def test_los_filtros_traen_los_extremos_de_precio(api: TestClient, vitrina) -> None:
    filtros = api.get(FILTROS).json()
    assert filtros["precio_min"] == "180.00"
    assert filtros["precio_max"] == "360.00"


def test_los_filtros_traen_la_jerarquia_de_categorias(api: TestClient, vitrina) -> None:
    """Con `categoria_padre_id`, para que el panel dibuje el árbol."""
    filtros = api.get(FILTROS).json()
    hoja = next(c for c in filtros["categorias"] if c["nombre"] == "Blusas")
    assert hoja["categoria_padre_id"] == vitrina["categoria_raiz"]
