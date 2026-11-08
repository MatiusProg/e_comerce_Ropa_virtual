"""CU-36, CU-37 y CU-38 · El probador con la talla real (3ra presentación).

Lo que más importa cubrir
-------------------------
- CU-36: los puntos y las medidas que se aceptan son los que dan una escala
  con sentido. Un doble clic, un ruedo arriba de los hombros o una L más chica
  que la M se rechazan con un mensaje que dice qué corregir.
- CU-37: la sugerencia de talla y el registro de la prueba los calcula el
  SERVIDOR, y una prenda sin calibrar no se puede probar.
- CU-38: la foto respeta el plan (función y cupo), el cupo se descuenta solo
  si la foto salió, y por omisión sale la vista SIMULADA, que no cuesta nada.
- Todo queda dentro de la empresa: otra tienda no ve la prenda ni las pruebas.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, update

from app.core.config import settings
from app.integrations import probador_ia
from app.integrations.probador_ia import (
    ErrorDelProbador,
    ResultadoDeProbado,
    SolicitudDeProbado,
)
from app.integrations.probador_ia.no_disponible import ProbadorNoDisponible
from app.integrations.probador_ia.simulado import ProbadorSimulado
from app.modules.plataforma import verificador
from app.modules.plataforma.models import Plan, Suscripcion

from tests.test_multitenant import empresa_b  # noqa: F401  (fixture)

API = "/api/v1"
ADMIN = f"{API}/catalogo/probador"
VESTIDOR = f"{API}/vestidor"
PRODUCTOS = f"{API}/catalogo/productos"

PUNTOS_OK = {
    "hombro_izq": {"x": 0.25, "y": 0.15},
    "hombro_der": {"x": 0.75, "y": 0.16},
    "ruedo": {"x": 0.5, "y": 0.9},
}


def _png(color=(200, 30, 60, 0), tam=(40, 60)) -> bytes:
    buffer = BytesIO()
    Image.new("RGBA", tam, color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def blusa(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Una blusa en S, M y L, con PNG de vestidor en la S y en la M."""
    admin = cabeceras_admin
    categoria = api.post(f"{API}/catalogo/categorias", headers=admin,
                         json={"nombre": "Blusas", "orden": 0, "activa": True}).json()["id"]
    tallas = {}
    for orden, codigo in enumerate(("S", "M", "L"), start=1):
        r = api.post(f"{API}/catalogo/tallas", headers=admin,
                     json={"tipo_prenda": "Superior", "codigo": codigo, "orden": orden,
                           "activa": True})
        assert r.status_code == 201, r.text
        tallas[codigo] = r.json()["id"]
    color = api.post(f"{API}/catalogo/colores", headers=admin,
                     json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True}).json()["id"]
    producto = api.post(PRODUCTOS, headers=admin, json={
        "codigo": "BLU-PROB", "nombre": "Blusa probador", "categoria_id": categoria,
        "precio_base": "200.00", "activo": True}).json()["id"]

    variantes, imagenes = {}, {}
    for codigo, talla_id in tallas.items():
        r = api.post(f"{PRODUCTOS}/{producto}/variantes", headers=admin,
                     json={"talla_id": talla_id, "color_id": color, "precio": "200.00",
                           "activa": True})
        assert r.status_code == 201, r.text
        variantes[codigo] = r.json()["id"]
    for codigo in ("S", "M"):
        subida = api.post(f"{PRODUCTOS}/{producto}/imagenes", headers=admin,
                          files={"archivo": ("p.png", _png(), "image/png")},
                          params={"variante_id": variantes[codigo]})
        assert subida.status_code == 201, subida.text
        imagenes[codigo] = subida.json()["id"]
        r = api.patch(f"{API}/catalogo/imagenes/{imagenes[codigo]}/transparente",
                      headers=admin, json={"es_transparente": True})
        assert r.status_code == 200, r.text
    return {"producto": producto, "tallas": tallas, "variantes": variantes,
            "imagenes": imagenes, "admin": admin}


def _medidas(blusa, **cambios) -> dict:
    base = {"S": 95, "M": 100, "L": 105}
    base.update(cambios)
    return {"tallas": [
        {"talla_id": blusa["tallas"][c], "busto_cm": b, "cintura_cm": b - 20,
         "cadera_cm": b + 5, "largo_cm": 60 + i * 2}
        for i, (c, b) in enumerate(base.items())
    ]}


@pytest.fixture
def blusa_lista(api, blusa) -> dict:
    r = api.put(f"{ADMIN}/imagenes/{blusa['imagenes']['S']}/puntos", headers=blusa["admin"],
                json=PUNTOS_OK)
    assert r.status_code == 200, r.text
    r = api.put(f"{ADMIN}/imagenes/{blusa['imagenes']['M']}/puntos", headers=blusa["admin"],
                json=PUNTOS_OK)
    assert r.status_code == 200, r.text
    r = api.put(f"{ADMIN}/productos/{blusa['producto']}/medidas", headers=blusa["admin"],
                json=_medidas(blusa))
    assert r.status_code == 200, r.text
    assert r.json()["lista"] is True
    return blusa


def _cargar_medidas_cliente(api, cab, busto=92):
    r = api.put(f"{API}/clientes/me/medidas", headers=cab,
                json={"busto_cm": busto, "cintura_cm": 72, "cadera_cm": 100, "altura_cm": 165})
    assert r.status_code == 200, r.text


def _pasar_a(db, codigo: str, **cambios) -> None:
    plan = db.scalar(select(Plan).where(Plan.codigo == codigo))
    for campo, valor in cambios.items():
        setattr(plan, campo, valor)
    db.execute(update(Suscripcion).values(plan_id=plan.id))
    db.commit()


# --- CU-36 · Preparar la prenda ---------------------------------------------

def test_la_preparacion_es_del_administrador(api, blusa, cabeceras_cliente):
    url = f"{ADMIN}/productos/{blusa['producto']}"
    assert api.get(url).status_code == 401
    assert api.get(url, headers=cabeceras_cliente).status_code == 403


def test_al_principio_dice_que_falta(api, blusa):
    r = api.get(f"{ADMIN}/productos/{blusa['producto']}", headers=blusa["admin"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["lista"] is False
    assert len(cuerpo["imagenes"]) == 2
    assert [t["codigo"] for t in cuerpo["tallas"]] == ["S", "M", "L"]
    assert any("hombros" in f for f in cuerpo["faltan"])
    assert any("S, M, L" in f for f in cuerpo["faltan"])


@pytest.mark.parametrize("puntos, palabra", [
    ({**PUNTOS_OK, "hombro_izq": {"x": 0.8, "y": 0.15}}, "izquierda"),
    ({**PUNTOS_OK, "hombro_der": {"x": 0.3, "y": 0.15}}, "juntos"),
    ({**PUNTOS_OK, "hombro_der": {"x": 0.75, "y": 0.45}}, "más alto"),
    ({**PUNTOS_OK, "ruedo": {"x": 0.5, "y": 0.2}}, "ruedo"),
])
def test_puntos_sin_sentido_se_rechazan(api, blusa, puntos, palabra):
    r = api.put(f"{ADMIN}/imagenes/{blusa['imagenes']['S']}/puntos", headers=blusa["admin"],
                json=puntos)
    assert r.status_code == 422, r.text
    assert palabra in r.json()["detail"]


def test_un_punto_fuera_de_la_imagen_se_rechaza(api, blusa):
    puntos = {**PUNTOS_OK, "ruedo": {"x": 0.5, "y": 1.3}}
    r = api.put(f"{ADMIN}/imagenes/{blusa['imagenes']['S']}/puntos", headers=blusa["admin"],
                json=puntos)
    assert r.status_code == 422


def test_los_puntos_se_corrigen_sin_duplicar(api, blusa):
    url = f"{ADMIN}/imagenes/{blusa['imagenes']['S']}/puntos"
    assert api.put(url, headers=blusa["admin"], json=PUNTOS_OK).status_code == 200
    otros = {**PUNTOS_OK, "ruedo": {"x": 0.5, "y": 0.7}}
    assert api.put(url, headers=blusa["admin"], json=otros).status_code == 200
    cuerpo = api.get(f"{ADMIN}/productos/{blusa['producto']}", headers=blusa["admin"]).json()
    s = next(i for i in cuerpo["imagenes"] if i["imagen_id"] == blusa["imagenes"]["S"])
    assert s["puntos"]["ruedo"]["y"] == pytest.approx(0.7)


def test_una_imagen_con_fondo_no_se_calibra(api, blusa):
    subida = api.post(f"{PRODUCTOS}/{blusa['producto']}/imagenes", headers=blusa["admin"],
                      files={"archivo": ("f.png", _png((10, 10, 10, 255)), "image/png")})
    assert subida.status_code == 201, subida.text
    r = api.put(f"{ADMIN}/imagenes/{subida.json()['id']}/puntos", headers=blusa["admin"],
                json=PUNTOS_OK)
    assert r.status_code == 422
    assert "vestidor" in r.json()["detail"]


def test_una_talla_mas_grande_no_puede_medir_menos(api, blusa):
    r = api.put(f"{ADMIN}/productos/{blusa['producto']}/medidas", headers=blusa["admin"],
                json=_medidas(blusa, L=98))
    assert r.status_code == 422, r.text
    assert "L" in r.json()["detail"] and "M" in r.json()["detail"]


def test_medidas_fuera_de_rango_o_de_otra_talla_se_rechazan(api, blusa, cabeceras_admin):
    datos = _medidas(blusa)
    datos["tallas"][0]["largo_cm"] = 5
    assert api.put(f"{ADMIN}/productos/{blusa['producto']}/medidas", headers=blusa["admin"],
                   json=datos).status_code == 422
    ajena = api.post(f"{API}/catalogo/tallas", headers=cabeceras_admin,
                     json={"tipo_prenda": "Superior", "codigo": "XL", "orden": 9,
                           "activa": True}).json()["id"]
    datos = {"tallas": [{"talla_id": ajena, "busto_cm": 110, "cintura_cm": 90,
                         "cadera_cm": 115, "largo_cm": 66}]}
    r = api.put(f"{ADMIN}/productos/{blusa['producto']}/medidas", headers=blusa["admin"],
                json=datos)
    assert r.status_code == 422
    assert "no se vende" in r.json()["detail"]


def test_la_lista_de_productos_muestra_el_avance(api, blusa_lista):
    filas = api.get(f"{ADMIN}/productos", headers=blusa_lista["admin"]).json()
    fila = next(f for f in filas if f["producto_id"] == blusa_lista["producto"])
    assert fila["imagenes"] == 2 and fila["imagenes_calibradas"] == 2
    assert fila["tallas"] == 3 and fila["tallas_medidas"] == 3
    assert fila["lista"] is True


# --- CU-37 · Probarse la prenda ----------------------------------------------

def test_la_prueba_trae_las_prendas_calibradas_y_la_sugerencia(api, blusa_lista,
                                                               cabeceras_cliente):
    _cargar_medidas_cliente(api, cabeceras_cliente, busto=92)
    r = api.get(f"{VESTIDOR}/productos/{blusa_lista['producto']}/prueba",
                headers=cabeceras_cliente)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    # La L no tiene foto propia: usa la calibrada de su mismo color, porque la
    # forma es la misma y lo que cambia son los centímetros (fix del 08/11).
    assert [p["talla"] for p in cuerpo["prendas"]] == ["S", "M", "L"]
    por_talla_img = {p["talla"]: p["imagen_url"] for p in cuerpo["prendas"]}
    assert por_talla_img["L"] in (por_talla_img["S"], por_talla_img["M"])
    assert cuerpo["medidas"]["busto_cm"] == "92.0"
    assert cuerpo["ajuste"]["hay_medidas"] is True
    # Cuerpo de 92 de busto = talla M del tallaje; la holgura de diseño de
    # esta blusa es 100 - 92 = 8 en todas las tallas.
    assert cuerpo["ajuste"]["talla_recomendada"] == "M"
    por_talla = {t["codigo"]: t for t in cuerpo["ajuste"]["tallas"]}
    assert por_talla["M"]["ajuste"] == "A_TU_MEDIDA"
    assert por_talla["S"]["factor_ancho"] < 1 < por_talla["L"]["factor_ancho"]
    # Por omisión la foto se ofrece: el proveedor simulado no cuesta nada.
    assert cuerpo["foto_ia"]["disponible"] is True


def test_sin_medidas_la_prueba_igual_responde(api, blusa_lista, cabeceras_cliente):
    cuerpo = api.get(f"{VESTIDOR}/productos/{blusa_lista['producto']}/prueba",
                     headers=cabeceras_cliente).json()
    assert cuerpo["medidas"] is None
    assert cuerpo["ajuste"]["hay_medidas"] is False
    assert cuerpo["prendas"]


def test_registrar_una_prueba_calcula_el_ajuste_en_el_servidor(api, blusa_lista,
                                                               cabeceras_cliente):
    _cargar_medidas_cliente(api, cabeceras_cliente, busto=92)
    r = api.post(f"{VESTIDOR}/sesiones", headers=cabeceras_cliente,
                 json={"variante_id": blusa_lista["variantes"]["S"], "metodo": "POSE"})
    assert r.status_code == 201, r.text
    sesion = r.json()
    assert sesion["talla"] == "S"
    assert sesion["ajuste"] in ("AJUSTADA", "NO_ENTRA")
    assert sesion["talla_recomendada"] == "M"
    assert sesion["foto_url"] is None
    mias = api.get(f"{VESTIDOR}/sesiones", headers=cabeceras_cliente).json()
    assert [s["id"] for s in mias] == [sesion["id"]]


def test_una_prenda_sin_calibrar_no_se_prueba(api, blusa_lista, cabeceras_cliente):
    # La L no tiene imagen propia, pero su color sí: se prueba con esa (08/11).
    r = api.post(f"{VESTIDOR}/sesiones", headers=cabeceras_cliente,
                 json={"variante_id": blusa_lista["variantes"]["L"], "metodo": "MANUAL"})
    assert r.status_code == 201, r.text
    # Un color sin ninguna imagen calibrada no se puede probar.
    admin = blusa_lista["admin"]
    blanco = api.post(f"{API}/catalogo/colores", headers=admin,
                      json={"nombre": "Blanco", "hexadecimal": "#FAFAFA", "activo": True}).json()["id"]
    r = api.post(f"{PRODUCTOS}/{blusa_lista['producto']}/variantes", headers=admin,
                 json={"talla_id": blusa_lista["tallas"]["M"], "color_id": blanco,
                       "precio": "200.00", "activa": True})
    assert r.status_code == 201, r.text
    r = api.post(f"{VESTIDOR}/sesiones", headers=cabeceras_cliente,
                 json={"variante_id": r.json()["id"], "metodo": "MANUAL"})
    assert r.status_code == 404
    r = api.post(f"{VESTIDOR}/sesiones", headers=cabeceras_cliente,
                 json={"variante_id": blusa_lista["variantes"]["S"], "metodo": "OTRO"})
    assert r.status_code == 422


# --- CU-38 · La foto realista ------------------------------------------------

def _sesion(api, blusa, cab) -> int:
    r = api.post(f"{VESTIDOR}/sesiones", headers=cab,
                 json={"variante_id": blusa["variantes"]["M"], "metodo": "MANUAL"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _foto(api, cab, sesion_id, contenido=None):
    return api.post(f"{VESTIDOR}/sesiones/{sesion_id}/foto", headers=cab,
                    files={"composicion": ("c.png", contenido or _png((90, 60, 120, 255),
                                                                     (120, 160)), "image/png")})


def _usadas(db) -> int:
    return verificador.uso_del_mes(db, "fotos_ia")


def test_la_foto_simulada_se_guarda_y_descuenta_el_cupo(api, db, blusa_lista,
                                                        cabeceras_cliente):
    sesion_id = _sesion(api, blusa_lista, cabeceras_cliente)
    antes = _usadas(db)
    r = _foto(api, cabeceras_cliente, sesion_id)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["foto_generada_por"] == "simulado"
    assert cuerpo["foto_url"].startswith(settings.MEDIA_URL)
    db.expire_all()
    assert _usadas(db) == antes + 1
    archivo = Path(settings.MEDIA_ROOT) / cuerpo["foto_url"][len(settings.MEDIA_URL):].lstrip("/")
    assert archivo.exists()
    # Una segunda foto de la misma prueba no gasta otra.
    assert _foto(api, cabeceras_cliente, sesion_id).status_code == 409
    db.expire_all()
    assert _usadas(db) == antes + 1
    # Borrar la prueba borra la foto.
    assert api.delete(f"{VESTIDOR}/sesiones/{sesion_id}",
                      headers=cabeceras_cliente).status_code == 204
    assert not archivo.exists()


def test_el_plan_sin_foto_ia_la_rechaza(api, db, blusa_lista, cabeceras_cliente):
    sesion_id = _sesion(api, blusa_lista, cabeceras_cliente)
    _pasar_a(db, "BASICO")
    r = _foto(api, cabeceras_cliente, sesion_id)
    assert r.status_code == 403
    assert r.json()["codigo"] == "plan_limit"
    prueba = api.get(f"{VESTIDOR}/productos/{blusa_lista['producto']}/prueba",
                     headers=cabeceras_cliente).json()
    assert prueba["foto_ia"]["disponible"] is False
    assert "plan" in prueba["foto_ia"]["motivo"]


def test_con_el_cupo_agotado_no_hay_foto(api, db, blusa_lista, cabeceras_cliente):
    sesion_id = _sesion(api, blusa_lista, cabeceras_cliente)
    _pasar_a(db, "PROFESIONAL", cupo_fotos_ia=1)
    otra = _sesion(api, blusa_lista, cabeceras_cliente)
    assert _foto(api, cabeceras_cliente, otra).status_code == 200
    r = _foto(api, cabeceras_cliente, sesion_id)
    assert r.status_code == 403
    assert "fotos con IA" in r.json()["detail"]


def test_una_foto_que_falla_no_gasta_el_cupo(api, db, blusa_lista, cabeceras_cliente,
                                             monkeypatch):
    monkeypatch.setattr(probador_ia, "obtener_proveedor", lambda: ProbadorNoDisponible())
    sesion_id = _sesion(api, blusa_lista, cabeceras_cliente)
    antes = _usadas(db)
    assert _foto(api, cabeceras_cliente, sesion_id).status_code == 503
    db.expire_all()
    assert _usadas(db) == antes


def test_la_foto_de_otro_cliente_no_se_toca(api, blusa_lista, cabeceras_cliente, cabeceras_admin):
    sesion_id = _sesion(api, blusa_lista, cabeceras_cliente)
    # El administrador no es cliente: ni siquiera entra al vestidor.
    assert _foto(api, cabeceras_admin, sesion_id).status_code == 403
    assert api.delete(f"{VESTIDOR}/sesiones/999999",
                      headers=cabeceras_cliente).status_code == 404


def test_una_composicion_que_no_es_imagen_se_rechaza(api, blusa_lista, cabeceras_cliente):
    sesion_id = _sesion(api, blusa_lista, cabeceras_cliente)
    r = api.post(f"{VESTIDOR}/sesiones/{sesion_id}/foto", headers=cabeceras_cliente,
                 files={"composicion": ("c.txt", b"hola", "text/plain")})
    assert r.status_code == 422


# --- El proveedor ----------------------------------------------------------------

def test_el_simulado_devuelve_un_png_marcado():
    resultado = ProbadorSimulado().probar(
        SolicitudDeProbado(foto=_png((90, 60, 120, 255), (300, 400)), prenda=b"", descripcion="x")
    )
    assert resultado.generada_por == "simulado"
    imagen = Image.open(BytesIO(resultado.imagen))
    assert imagen.format == "PNG" and imagen.size == (300, 400)
    # La franja de la marca oscurece el borde de abajo.
    assert imagen.convert("RGB").getpixel((5, 395)) != imagen.convert("RGB").getpixel((5, 5))


def test_el_simulado_rechaza_lo_que_no_es_imagen():
    with pytest.raises(ErrorDelProbador):
        ProbadorSimulado().probar(SolicitudDeProbado(foto=b"no", prenda=b"", descripcion=""))


def test_si_el_proveedor_real_falla_sale_la_simulada(monkeypatch):
    class Roto:
        nombre = "gemini"
        disponible = True

        def probar(self, solicitud) -> ResultadoDeProbado:
            raise ErrorDelProbador("429")

    monkeypatch.setattr(probador_ia, "obtener_proveedor", lambda: Roto())
    resultado = probador_ia.probar(
        SolicitudDeProbado(foto=_png((1, 2, 3, 255)), prenda=b"", descripcion="")
    )
    assert resultado.generada_por == "simulado (falló gemini)"


# --- Aislamiento entre empresas --------------------------------------------------

def test_otra_tienda_no_ve_la_prenda_ni_las_pruebas(api, blusa_lista, cabeceras_cliente,
                                                     fabrica_sesiones, empresa_b):  # noqa: F811
    """El token del cliente fija su tienda (CU-06), así que se mira con RLS directo:
    una sesión de la empresa B no ve los puntos ni las pruebas de la A."""
    from app.core.tenencia import CLAVE_EMPRESA
    from app.modules.vestidor_virtual.models import PuntoPrenda, SesionVestidorVirtual

    _sesion(api, blusa_lista, cabeceras_cliente)
    for empresa, esperadas in ((1, (2, 1)), (empresa_b, (0, 0))):
        sesion = fabrica_sesiones()
        sesion.info[CLAVE_EMPRESA] = empresa
        try:
            puntos = len(sesion.scalars(select(PuntoPrenda)).all())
            pruebas = len(sesion.scalars(select(SesionVestidorVirtual)).all())
        finally:
            sesion.close()
        assert (puntos, pruebas) == esperadas, empresa


def test_la_foto_de_una_talla_sin_imagen_propia_usa_la_de_su_color(api, blusa_lista, cabeceras_cliente):
    # La L no tiene PNG propio: se prueba con el de su color (08/11) y la foto tiene que salir igual.
    r = api.post(f"{VESTIDOR}/sesiones", headers=cabeceras_cliente,
                 json={"variante_id": blusa_lista["variantes"]["L"], "metodo": "POSE"})
    assert r.status_code == 201, r.text
    r = api.post(f"{VESTIDOR}/sesiones/{r.json()['id']}/foto", headers=cabeceras_cliente,
                 files={"composicion": ("c.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["foto_url"]
    assert r.json()["talla"] == "L"


def test_la_lista_del_probador_trae_lo_calibrado(api, blusa_lista, cabeceras_cliente):
    r = api.get(f"{VESTIDOR}/productos-listos", headers=cabeceras_cliente)
    assert r.status_code == 200, r.text
    assert [p["producto_id"] for p in r.json()] == [blusa_lista["producto"]]
    assert r.json()[0]["imagen_url"]
