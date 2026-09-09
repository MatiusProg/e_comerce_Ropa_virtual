"""CU-11 · Gestionar imágenes de producto.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-11-gestionar-imagenes-de-producto.md).

Las pruebas que más importan son las que cubren lo que ni la base ni el formato
del archivo garantizan:

- **Un PNG opaco no sirve para el vestidor virtual.** Es el caso realista: se
  guarda como PNG una foto con fondo blanco y el archivo es un PNG válido en
  modo RGBA, solo que con el alfa entero en 255. Si se aceptara, el prototipo de
  realidad aumentada del día 4 superpondría un rectángulo blanco sobre el torso
  y el defecto aparecería recién ahí.
- **El formato se decide abriendo el archivo**, no leyendo su extensión ni el
  `content-type`, que los pone quien sube.
- **Al borrar la principal, otra toma su lugar.** Un producto con fotos pero sin
  principal desaparece del listado del catálogo por un descuido de mantenimiento.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
IMAGENES = "/api/v1/catalogo/imagenes"


@pytest.fixture(autouse=True)
def volumen_temporal(tmp_path, monkeypatch):
    """El volumen de imágenes, dentro de la carpeta temporal de la prueba.

    Sin esto, MEDIA_ROOT apunta a `/app/media` —la ruta del contenedor de
    Railway— y la suite escribiría archivos de prueba fuera del proyecto.
    """
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(tmp_path / "media"))
    return tmp_path / "media"


# --- Generadores de archivos ---------------------------------------------

def _png(modo: str = "RGBA", color=(200, 30, 60, 0), tamano=(24, 24)) -> bytes:
    buffer = BytesIO()
    Image.new(modo, tamano, color).save(buffer, format="PNG")
    return buffer.getvalue()


def _png_transparente() -> bytes:
    """Un PNG con alfa real: la prenda recortada del vestidor virtual."""
    return _png("RGBA", (200, 30, 60, 0))


def _png_opaco_en_rgba() -> bytes:
    """La trampa: es PNG, es RGBA, pero el alfa está entero en 255."""
    return _png("RGBA", (255, 255, 255, 255))


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (24, 24), (10, 20, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


def _gif() -> bytes:
    buffer = BytesIO()
    Image.new("P", (24, 24)).save(buffer, format="GIF")
    return buffer.getvalue()


# --- Ayudantes -----------------------------------------------------------

def _producto_con_variante(api: TestClient, admin: dict[str, str]) -> tuple[int, int]:
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Camisas", "orden": 0, "activa": True}
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
            "codigo": "CAM-001",
            "nombre": "Camisa Oxford",
            "categoria_id": categoria,
            "precio_base": "250.00",
            "activo": True,
        },
    ).json()
    variante = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes",
        headers=admin,
        json={"talla_id": talla, "color_id": color},
    ).json()
    return producto["id"], variante["id"]


def _subir(
    api: TestClient,
    admin: dict[str, str],
    producto_id: int,
    contenido: bytes,
    *,
    nombre: str = "foto.png",
    tipo: str = "image/png",
    variante_id: int | None = None,
):
    params = {"variante_id": variante_id} if variante_id is not None else None
    return api.post(
        f"{PRODUCTOS}/{producto_id}/imagenes",
        headers=admin,
        files={"archivo": (nombre, contenido, tipo)},
        params=params,
    )


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_ve_la_galeria(api: TestClient) -> None:
    assert api.get(f"{PRODUCTOS}/1/imagenes").status_code == 401


def test_un_cliente_no_gestiona_imagenes(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.get(f"{PRODUCTOS}/1/imagenes", headers=cabeceras_cliente).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_subir_una_imagen_la_guarda_y_la_deja_como_principal(
    api: TestClient, cabeceras_admin: dict[str, str], volumen_temporal
) -> None:
    """La primera imagen queda principal sola: un producto con fotos pero sin
    principal no se puede dibujar en el listado del catálogo."""
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)

    r = _subir(api, cabeceras_admin, producto_id, _png_transparente())
    assert r.status_code == 201, r.text
    imagen = r.json()
    assert imagen["es_principal"] is True
    assert imagen["es_transparente"] is False
    assert imagen["url"].startswith(settings.MEDIA_URL)
    # El archivo esta de verdad en el volumen, no solo la fila.
    assert (volumen_temporal / imagen["ruta"]).is_file()


def test_el_nombre_del_archivo_no_viene_de_quien_sube(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Un nombre elegido por quien sube puede traer '..' o separadores, y dos
    personas subiendo «frente.png» se pisarían."""
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    r = _subir(
        api, cabeceras_admin, producto_id, _png_transparente(), nombre="../../evil.png"
    )
    assert r.status_code == 201, r.text
    ruta = r.json()["ruta"]
    assert ".." not in ruta
    assert ruta.startswith(f"productos/{producto_id}/")


def test_la_segunda_imagen_no_desplaza_a_la_principal(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    primera = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()
    segunda = _subir(api, cabeceras_admin, producto_id, _jpeg(), nombre="b.jpg",
                     tipo="image/jpeg").json()

    assert primera["es_principal"] is True
    assert segunda["es_principal"] is False
    galeria = api.get(f"{PRODUCTOS}/{producto_id}/imagenes", headers=cabeceras_admin).json()
    assert sum(1 for i in galeria if i["es_principal"]) == 1


def test_se_aceptan_png_jpeg_y_webp(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    buffer = BytesIO()
    Image.new("RGB", (24, 24), (1, 2, 3)).save(buffer, format="WEBP")

    for contenido, nombre in ((_png_transparente(), "a.png"), (_jpeg(), "b.jpg"),
                              (buffer.getvalue(), "c.webp")):
        r = _subir(api, cabeceras_admin, producto_id, contenido, nombre=nombre)
        assert r.status_code == 201, r.text


# --- Excepciones del archivo ---------------------------------------------

def test_excepcion_e1_un_archivo_que_no_es_imagen(
    api: TestClient, cabeceras_admin: dict[str, str], volumen_temporal
) -> None:
    """El nombre y el content-type dicen PNG; el contenido, no."""
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    r = _subir(api, cabeceras_admin, producto_id, b"MZ\x90\x00 esto es un ejecutable")
    assert r.status_code == 422, r.text
    # Y no quedo nada escrito en el volumen: el archivo se valida ANTES de
    # tocar el disco, asi que un rechazo no deja basura que limpiar.
    carpeta = volumen_temporal / "productos"
    assert not carpeta.exists() or not list(carpeta.rglob("*.*"))


def test_excepcion_e1_un_formato_no_admitido(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    r = _subir(api, cabeceras_admin, producto_id, _gif(), nombre="animado.gif")
    assert r.status_code == 422, r.text


def test_excepcion_e2_un_archivo_demasiado_grande(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    from app.modules.catalogo import imagenes_almacen

    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    enorme = b"\x89PNG\r\n\x1a\n" + b"0" * (imagenes_almacen.TAMANO_MAXIMO + 1)
    r = _subir(api, cabeceras_admin, producto_id, enorme)
    assert r.status_code == 422, r.text
    assert "MB" in r.json()["detail"]


def test_un_archivo_vacio_no_entra(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    assert _subir(api, cabeceras_admin, producto_id, b"").status_code == 422


# --- 3a Asociar a una variante -------------------------------------------

def test_3a_asociar_la_imagen_a_una_variante(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, variante_id = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()

    r = api.patch(
        f"{IMAGENES}/{imagen['id']}", headers=cabeceras_admin, json={"variante_id": variante_id}
    )
    assert r.status_code == 200, r.text
    assert r.json()["variante_id"] == variante_id
    assert r.json()["variante_sku"]
    assert r.json()["variante_etiqueta"] == "M · Negro"


def test_no_se_asocia_a_la_variante_de_otro_producto(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Las dos claves foráneas existen, así que la base lo aceptaría: dejaría la
    foto de una camisa colgando de un pantalón."""
    producto_a, _ = _producto_con_variante(api, cabeceras_admin)
    categoria = api.get(CATEGORIAS, headers=cabeceras_admin).json()[0]["id"]
    otro = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "PAN-002",
            "nombre": "Pantalón",
            "categoria_id": categoria,
            "precio_base": "300.00",
        },
    ).json()
    talla = api.get(TALLAS, headers=cabeceras_admin).json()[0]["id"]
    color = api.get(COLORES, headers=cabeceras_admin).json()[0]["id"]
    variante_ajena = api.post(
        f"{PRODUCTOS}/{otro['id']}/variantes",
        headers=cabeceras_admin,
        json={"talla_id": talla, "color_id": color},
    ).json()

    imagen = _subir(api, cabeceras_admin, producto_a, _png_transparente()).json()
    r = api.patch(
        f"{IMAGENES}/{imagen['id']}",
        headers=cabeceras_admin,
        json={"variante_id": variante_ajena["id"]},
    )
    assert r.status_code == 422, r.text


# --- 3b La imagen principal ----------------------------------------------

def test_3b_marcar_otra_principal_desmarca_la_anterior(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    primera = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()
    segunda = _subir(api, cabeceras_admin, producto_id, _jpeg(), nombre="b.jpg").json()

    r = api.patch(
        f"{IMAGENES}/{segunda['id']}/principal",
        headers=cabeceras_admin,
        json={"es_principal": True},
    )
    assert r.status_code == 200, r.text
    galeria = {i["id"]: i["es_principal"] for i in r.json()}
    assert galeria[segunda["id"]] is True
    assert galeria[primera["id"]] is False


# --- 3c El PNG del vestidor virtual (supuesto S5) ------------------------

def test_3c_un_png_opaco_no_sirve_para_el_vestidor(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """La prueba que más importa del caso de uso.

    El archivo es un PNG válido y está en modo RGBA: pasa cualquier control de
    formato. Pero su alfa está entero en 255, así que en el vestidor virtual
    superpondría un rectángulo blanco sobre el torso.
    """
    producto_id, variante_id = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(
        api, cabeceras_admin, producto_id, _png_opaco_en_rgba(), variante_id=variante_id
    ).json()

    r = api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=cabeceras_admin,
        json={"es_transparente": True},
    )
    assert r.status_code == 422, r.text
    assert "transparente" in r.json()["detail"].lower()


def test_3c_un_png_con_alfa_real_si_se_marca(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, variante_id = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(
        api, cabeceras_admin, producto_id, _png_transparente(), variante_id=variante_id
    ).json()

    r = api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=cabeceras_admin,
        json={"es_transparente": True},
    )
    assert r.status_code == 200, r.text
    marcadas = [i for i in r.json() if i["es_transparente"]]
    assert [i["id"] for i in marcadas] == [imagen["id"]]


def test_3c_el_png_del_vestidor_necesita_una_variante(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El vestidor superpone la prenda de UNA variante, no del producto."""
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()

    r = api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=cabeceras_admin,
        json={"es_transparente": True},
    )
    assert r.status_code == 422, r.text


def test_3c_solo_un_png_transparente_por_variante(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Es el índice parcial uq_imagen_transparente_variante, visto desde afuera."""
    producto_id, variante_id = _producto_con_variante(api, cabeceras_admin)
    primera = _subir(
        api, cabeceras_admin, producto_id, _png_transparente(), variante_id=variante_id
    ).json()
    segunda = _subir(
        api,
        cabeceras_admin,
        producto_id,
        _png("RGBA", (10, 200, 10, 0)),
        nombre="b.png",
        variante_id=variante_id,
    ).json()

    api.patch(
        f"{IMAGENES}/{primera['id']}/transparente",
        headers=cabeceras_admin,
        json={"es_transparente": True},
    )
    r = api.patch(
        f"{IMAGENES}/{segunda['id']}/transparente",
        headers=cabeceras_admin,
        json={"es_transparente": True},
    )
    assert r.status_code == 200, r.text
    marcadas = [i["id"] for i in r.json() if i["es_transparente"]]
    assert marcadas == [segunda["id"]]


def test_desasociar_una_imagen_marcada_para_el_vestidor_no_se_permite(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Un PNG transparente «del producto» es una figura que no existe."""
    producto_id, variante_id = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(
        api, cabeceras_admin, producto_id, _png_transparente(), variante_id=variante_id
    ).json()
    api.patch(
        f"{IMAGENES}/{imagen['id']}/transparente",
        headers=cabeceras_admin,
        json={"es_transparente": True},
    )

    r = api.patch(
        f"{IMAGENES}/{imagen['id']}", headers=cabeceras_admin, json={"variante_id": None}
    )
    assert r.status_code == 422, r.text


# --- 3d Reordenar --------------------------------------------------------

def test_3d_reordenar_la_galeria(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    a = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()
    b = _subir(api, cabeceras_admin, producto_id, _jpeg(), nombre="b.jpg").json()
    c = _subir(api, cabeceras_admin, producto_id, _jpeg(), nombre="c.jpg").json()

    r = api.put(
        f"{PRODUCTOS}/{producto_id}/imagenes/orden",
        headers=cabeceras_admin,
        json={"imagenes": [c["id"], b["id"], a["id"]]},
    )
    assert r.status_code == 200, r.text
    ordenes = {i["id"]: i["orden"] for i in r.json()}
    assert ordenes[c["id"]] < ordenes[b["id"]] < ordenes[a["id"]]


def test_3d_no_se_reordena_con_imagenes_de_otro_producto(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()
    r = api.put(
        f"{PRODUCTOS}/{producto_id}/imagenes/orden",
        headers=cabeceras_admin,
        json={"imagenes": [imagen["id"], 999999]},
    )
    assert r.status_code == 422, r.text


# --- 3e Eliminar ---------------------------------------------------------

def test_3e_eliminar_borra_la_fila_y_el_archivo(
    api: TestClient, cabeceras_admin: dict[str, str], volumen_temporal
) -> None:
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()
    archivo = volumen_temporal / imagen["ruta"]
    assert archivo.is_file()

    assert api.delete(f"{IMAGENES}/{imagen['id']}", headers=cabeceras_admin).status_code == 204
    assert not archivo.exists()
    assert api.get(f"{PRODUCTOS}/{producto_id}/imagenes", headers=cabeceras_admin).json() == []


def test_3e_al_borrar_la_principal_otra_toma_su_lugar(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Dejar al producto sin principal lo sacaría del listado del catálogo."""
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    primera = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()
    _subir(api, cabeceras_admin, producto_id, _jpeg(), nombre="b.jpg")

    api.delete(f"{IMAGENES}/{primera['id']}", headers=cabeceras_admin)
    galeria = api.get(f"{PRODUCTOS}/{producto_id}/imagenes", headers=cabeceras_admin).json()
    assert len(galeria) == 1
    assert galeria[0]["es_principal"] is True


def test_eliminar_el_producto_arrastra_sus_imagenes(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El ON DELETE CASCADE de imagen_producto."""
    producto_id, _ = _producto_con_variante(api, cabeceras_admin)
    imagen = _subir(api, cabeceras_admin, producto_id, _png_transparente()).json()

    assert api.delete(f"{PRODUCTOS}/{producto_id}", headers=cabeceras_admin).status_code == 204
    r = api.patch(f"{IMAGENES}/{imagen['id']}", headers=cabeceras_admin, json={"orden": 1})
    assert r.status_code == 404
