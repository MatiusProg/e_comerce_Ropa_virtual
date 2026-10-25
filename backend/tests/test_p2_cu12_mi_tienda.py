"""2do parcial, CU-12 Personalizar la tienda de la empresa.

El administrador sube el logo y elige dos colores; la tienda en línea los
aplica. Solo si el plan incluye `marca_propia` (1a, CU-05). El logo se valida
abriéndolo, como las imágenes de producto (4a).
"""

from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import update

from app.core.config import settings
from app.core.tenencia import CLAVE_EMPRESA
from app.db.session import get_db
from app.main import app
from app.modules.plataforma.models import Empresa, Suscripcion

URL = "/api/v1/plataforma/mi-tienda"
MARCA = "/api/v1/tienda/marca"
COLORES = {"color_principal": "#1A2B3C", "color_secundario": "#ffcc00"}


@pytest.fixture(autouse=True)
def media(tmp_path, monkeypatch) -> Path:
    """Igual que en el CU-11: los archivos van a una carpeta temporal."""
    raiz = tmp_path / "media"
    monkeypatch.setattr(settings, "MEDIA_ROOT", str(raiz))
    return raiz


def _png(color=(200, 50, 120)) -> bytes:
    salida = BytesIO()
    Image.new("RGB", (64, 64), color).save(salida, format="PNG")
    return salida.getvalue()


def _subir(api, cabeceras, contenido: bytes, nombre="logo.png"):
    return api.post(f"{URL}/logo", headers=cabeceras,
                    files={"archivo": (nombre, contenido, "image/png")})


def _pasar_al_basico(db) -> None:
    """El plan Básico no incluye la marca propia."""
    db.execute(update(Suscripcion).values(plan_id=1))
    db.commit()


# --- Flujo principal ---------------------------------------------------------

def test_la_pantalla_muestra_la_marca_y_si_el_plan_la_incluye(api, cabeceras_admin):
    respuesta = api.get(URL, headers=cabeceras_admin)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["incluida"] is True  # el Empresarial de las pruebas la incluye
    assert cuerpo["slug"] == "violet-boutique"
    assert cuerpo["logo_url"] is None and cuerpo["color_principal"] is None


def test_guarda_los_colores_y_la_tienda_los_aplica(api, cabeceras_admin):
    respuesta = api.put(f"{URL}/colores", headers=cabeceras_admin, json=COLORES)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["color_principal"] == "#1a2b3c"  # en minúsculas
    marca = api.get(MARCA).json()  # pública, sin token
    assert marca["color_principal"] == "#1a2b3c"
    assert marca["color_secundario"] == "#ffcc00"


def test_vuelve_a_los_colores_de_violet(api, cabeceras_admin):
    api.put(f"{URL}/colores", headers=cabeceras_admin, json=COLORES)

    respuesta = api.put(f"{URL}/colores", headers=cabeceras_admin, json={})

    assert respuesta.json()["color_principal"] is None
    assert api.get(MARCA).json()["color_principal"] is None


@pytest.mark.parametrize("color", ["rojo", "#12345", "#gggggg", "123456"])
def test_un_color_mal_escrito_no_se_guarda(api, cabeceras_admin, color):
    respuesta = api.put(f"{URL}/colores", headers=cabeceras_admin,
                        json={"color_principal": color})

    assert respuesta.status_code == 422


def test_sube_el_logo_y_la_tienda_lo_muestra(api, cabeceras_admin, media):
    respuesta = _subir(api, cabeceras_admin, _png())

    assert respuesta.status_code == 200, respuesta.text
    url = respuesta.json()["logo_url"]
    assert url.startswith("/media/empresas/1/logo-") and url.endswith(".png")
    assert (media / url.removeprefix("/media/")).is_file()
    assert api.get(MARCA).json()["logo_url"] == url


def test_un_logo_nuevo_reemplaza_y_borra_el_anterior(api, cabeceras_admin, media):
    viejo = _subir(api, cabeceras_admin, _png()).json()["logo_url"]

    nuevo = _subir(api, cabeceras_admin, _png((10, 10, 10))).json()["logo_url"]

    assert nuevo != viejo
    assert not (media / viejo.removeprefix("/media/")).exists()
    assert (media / nuevo.removeprefix("/media/")).is_file()


def test_quitar_el_logo(api, cabeceras_admin, media):
    url = _subir(api, cabeceras_admin, _png()).json()["logo_url"]

    respuesta = api.delete(f"{URL}/logo", headers=cabeceras_admin)

    assert respuesta.status_code == 200
    assert respuesta.json()["logo_url"] is None
    assert not (media / url.removeprefix("/media/")).exists()


# --- 4a: imagen inválida -----------------------------------------------------

@pytest.mark.parametrize("contenido,nombre", [
    (b"esto no es una imagen", "logo.png"),
    (b"", "vacio.png"),
    (b"GIF89a" + b"\x00" * 20, "logo.gif"),
])
def test_un_archivo_que_no_es_imagen_se_rechaza(api, cabeceras_admin, contenido, nombre):
    anterior = _subir(api, cabeceras_admin, _png()).json()["logo_url"]

    respuesta = _subir(api, cabeceras_admin, contenido, nombre)

    assert respuesta.status_code == 422
    assert "imagen" in respuesta.json()["detail"]
    assert api.get(URL, headers=cabeceras_admin).json()["logo_url"] == anterior


# --- 1a: el plan no incluye la función --------------------------------------

def test_sin_la_funcion_se_ve_pero_no_se_guarda(api, cabeceras_admin, db):
    _pasar_al_basico(db)

    pantalla = api.get(URL, headers=cabeceras_admin)
    colores = api.put(f"{URL}/colores", headers=cabeceras_admin, json=COLORES)
    logo = _subir(api, cabeceras_admin, _png())

    assert pantalla.status_code == 200 and pantalla.json()["incluida"] is False
    for respuesta in (colores, logo):
        assert respuesta.status_code == 403
        assert respuesta.json()["codigo"] == "plan_limit"


def test_al_bajar_de_plan_la_tienda_vuelve_a_violet_sin_borrar_la_marca(
    api, cabeceras_admin, db
):
    """RN-04: no se borra nada; se deja de aplicar."""
    api.put(f"{URL}/colores", headers=cabeceras_admin, json=COLORES)
    _pasar_al_basico(db)

    assert api.get(MARCA).json()["color_principal"] is None
    assert api.get(URL, headers=cabeceras_admin).json()["color_principal"] == "#1a2b3c"


# --- Quién puede ------------------------------------------------------------

def test_el_cliente_no_entra_a_mi_tienda(api, cabeceras_cliente):
    assert api.get(URL, headers=cabeceras_cliente).status_code == 403


def test_la_tienda_de_otra_empresa_no_ve_la_marca_ajena(api, cabeceras_admin, db,
                                                        fabrica_sesiones):
    """La marca pública es la de la tienda que se mira (`X-Empresa`)."""
    api.put(f"{URL}/colores", headers=cabeceras_admin, json=COLORES)
    otra = Empresa(nombre="Tienda B", slug="tienda-b")
    db.add(otra)
    db.commit()

    # Como en el CU-07: la empresa la pone el middleware y no la fábrica.
    def _sin_empresa_fija():
        sesion = fabrica_sesiones()
        sesion.info.pop(CLAVE_EMPRESA, None)
        try:
            yield sesion
        finally:
            sesion.close()

    app.dependency_overrides[get_db] = _sin_empresa_fija
    marca = api.get(MARCA, headers={"X-Empresa": str(otra.id)}).json()

    assert marca["empresa"] == "Tienda B"
    assert marca["color_principal"] is None
