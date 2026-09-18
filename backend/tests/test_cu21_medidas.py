"""CU-21 · Medidas del cliente y ajuste de la prenda por talla.

Completa el **RF13**: el vestidor deja de escalar la prenda para que calce
siempre y pasa a dibujar cada talla del tamaño que de verdad tiene.

Lo que más importa cubrir
-------------------------
Esto se escribió el 18/09/2026 a dos días de la entrega, así que las pruebas
están donde el sistema se rompe de forma silenciosa:

- **Que degrade en vez de fallar.** Sin medidas cargadas, o sin tabla de
  tallas, el ajuste tiene que responder 200 diciendo que no hay — nunca un
  error. El vestidor es una cámara que funciona sin servidor: que un extra
  opcional impida probarse una prenda sería cambiar una mejora por una
  regresión.
- **Que la talla recomendada sea la que menos se aparta**, y no «la primera que
  entra». A un cuerpo chico le entran casi todas las tallas; recomendar la
  primera de la lista acierta por casualidad y falla en cuanto el cuerpo cae
  entre dos.
- **Que los factores devuelvan 1.0 en la talla que corresponde.** Es lo que
  garantiza que el vestidor calibrado a mano el 18/09 se siga viendo igual para
  quien tiene su talla: la funcionalidad nueva no puede mover lo que ya estaba
  bien.
- **Que las medidas sean de cada quien.** Las de una clienta no se ven ni se
  pisan desde otra cuenta.
- **Que un disparate no entre.** Un busto de 900 cm es un formulario que mandó
  milímetros, y sin el rechazo el vestidor dibuja una prenda absurda sin que
  nada avise.
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from .conftest import CLAVE_CLIENTE, CORREO_CLIENTE

MEDIDAS = "/api/v1/clientes/me/medidas"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"

CORREO_OTRA = "otra.medidas@violetboutique.bo"
CLAVE_OTRA = "Secreta123"

#: Un cuerpo de talla M según el tallaje sembrado: busto 92.
CUERPO_M = {"busto_cm": 92, "cintura_cm": 72.5, "cadera_cm": 101}


def _ajuste(api: TestClient, cab: dict, producto_id: int):
    r = api.get(f"/api/v1/tienda/productos/{producto_id}/ajuste", headers=cab)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def prenda(api: TestClient, cabeceras_admin: dict[str, str], db) -> dict:
    """Una blusa con las cinco tallas y su tabla de medidas sembrada.

    La tabla se siembra con el MISMO código que usa el sistema de verdad
    (`seed_medidas.sembrar`) y no a mano: una prueba que arma su propia tabla
    verifica la aritmética contra números inventados por ella misma, y deja de
    notar el día que el sembrado cambie.
    """
    from app.db import seed_medidas

    categoria = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Blusas", "orden": 0, "activa": True},
    ).json()["id"]
    color = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    ).json()["id"]

    tallas = {}
    for orden, codigo in enumerate(["XS", "S", "M", "L", "XL"]):
        tallas[codigo] = api.post(
            TALLAS,
            headers=cabeceras_admin,
            json={
                "tipo_prenda": "Superior",
                "codigo": codigo,
                "orden": orden,
                "activa": True,
            },
        ).json()["id"]

    producto = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "BLU-021",
            "nombre": "Blusa de gasa",
            "categoria_id": categoria,
            "precio_base": "300.00",
            "activo": True,
        },
    ).json()["id"]

    for talla_id in tallas.values():
        api.post(
            f"{PRODUCTOS}/{producto}/variantes",
            headers=cabeceras_admin,
            json={
                "talla_id": talla_id,
                "color_id": color,
                "precio": "300.00",
                "activa": True,
            },
        )

    # Un producto SIN tabla: una prenda que NO es de torso.
    #
    # Lo que decide es el TIPO DE TALLA, no la categoría. Se probó al revés
    # ---una cartera con talla M--- y era dato imposible: en la base real las
    # carteras y los cinturones son talla Única, y los pantalones usan la serie
    # numérica. Con talla M la prueba pasaba por el motivo equivocado.
    talla_unica = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "Unica", "codigo": "U", "orden": 9, "activa": True},
    ).json()["id"]
    otra_categoria = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Carteras", "orden": 1, "activa": True},
    ).json()["id"]
    sin_tabla = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "CAR-001",
            "nombre": "Cartera de mano",
            "categoria_id": otra_categoria,
            "precio_base": "150.00",
            "activo": True,
        },
    ).json()["id"]
    api.post(
        f"{PRODUCTOS}/{sin_tabla}/variantes",
        headers=cabeceras_admin,
        json={
            "talla_id": talla_unica,
            "color_id": color,
            "precio": "150.00",
            "activa": True,
        },
    )

    escritas = seed_medidas.sembrar(db)
    db.commit()
    assert escritas == 5, "la blusa tiene que quedar con sus cinco tallas"

    return {"producto": producto, "sin_tabla": sin_tabla, "tallas": tallas}


# --- Degradar en vez de fallar ---------------------------------------------


def test_quien_nunca_cargo_medidas_recibe_null_y_no_un_404(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """No tenerlas cargadas es el estado normal de una cuenta nueva.

    Con 404 la pantalla trataria un caso corriente por el camino de los fallos.
    """
    r = api.get(MEDIDAS, headers=cabeceras_cliente)
    assert r.status_code == 200
    assert r.json() is None


def test_sin_medidas_el_ajuste_responde_que_no_hay_en_vez_de_fallar(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    assert cuerpo["hay_medidas"] is False
    # La tabla SI existe: el que falta es el cuerpo.
    assert cuerpo["hay_tabla"] is True
    assert cuerpo["tallas"] == []
    assert cuerpo["talla_recomendada"] is None


def test_un_producto_sin_tabla_de_tallas_tampoco_falla(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """Carteras, cinturones y pantalones no tienen tabla, y no son un error.

    No la tienen porque no son prendas de TORSO --- su talla no es de la serie
    XS..XXXL ---, no porque su categoria sea desconocida. Una categoria de
    torso que no encaje en ninguna regla igual recibe tabla, con una holgura
    generica: mas vale una respuesta aproximada que dejar el vestidor mudo.
    """
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["sin_tabla"])
    assert cuerpo["hay_tabla"] is False
    assert cuerpo["tallas"] == []


def test_un_producto_que_no_existe_no_revienta(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    cuerpo = _ajuste(api, cabeceras_cliente, 999_999)
    assert cuerpo["hay_tabla"] is False


# --- Guardar las medidas ----------------------------------------------------


def test_el_cliente_carga_sus_medidas_y_las_vuelve_a_ver(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    r = api.put(MEDIDAS, headers=cabeceras_cliente, json={**CUERPO_M, "altura_cm": 165})
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["busto_cm"]) == Decimal("92.0")

    r = api.get(MEDIDAS, headers=cabeceras_cliente)
    assert Decimal(r.json()["cintura_cm"]) == Decimal("72.5")
    assert Decimal(r.json()["altura_cm"]) == Decimal("165.0")


def test_volver_a_guardar_REEMPLAZA_y_no_crea_otra_fila(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Un cuerpo, un juego de medidas. Sin historial.

    Si se acumularan filas, toda consulta tendria que preguntarse cual es la
    vigente y la respuesta dependeria del orden.
    """
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    api.put(
        MEDIDAS,
        headers=cabeceras_cliente,
        json={"busto_cm": 104, "cintura_cm": 85, "cadera_cm": 115},
    )
    r = api.get(MEDIDAS, headers=cabeceras_cliente)
    assert Decimal(r.json()["busto_cm"]) == Decimal("104.0")
    # La altura que no se volvio a mandar se borra: el PUT reemplaza entero.
    assert r.json()["altura_cm"] is None


def test_la_altura_es_opcional(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    r = api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    assert r.status_code == 200
    assert r.json()["altura_cm"] is None


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("busto_cm", 900),  # milimetros, o un cero de mas
        ("busto_cm", 10),
        ("cintura_cm", 0),
        ("cadera_cm", 400),
        ("altura_cm", 15),
    ],
)
def test_un_disparate_no_entra(
    api: TestClient, cabeceras_cliente: dict[str, str], campo: str, valor: int
) -> None:
    """Sin esto, el vestidor dibuja una prenda absurda y nada avisa."""
    r = api.put(MEDIDAS, headers=cabeceras_cliente, json={**CUERPO_M, campo: valor})
    assert r.status_code == 422


def test_faltando_una_medida_obligatoria_rechaza(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    r = api.put(MEDIDAS, headers=cabeceras_cliente, json={"busto_cm": 92})
    assert r.status_code == 422


# --- La recomendación -------------------------------------------------------


def test_a_un_cuerpo_talla_M_se_le_recomienda_la_M(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    assert cuerpo["talla_recomendada"] == "M"
    assert cuerpo["talla_recomendada_id"] == prenda["tallas"]["M"]


def test_la_recomendada_NO_es_la_primera_que_entra(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """A un cuerpo chico le entran casi todas, y la mas chica no es la mejor.

    Con un busto de 82 ---talla XS--- la S (95 cm de prenda) tambien «entra».
    Lo que decide es cual se aparta menos de la holgura de diseno, no cual
    aparece primero en la lista.
    """
    api.put(
        MEDIDAS,
        headers=cabeceras_cliente,
        json={"busto_cm": 82, "cintura_cm": 62.5, "cadera_cm": 89},
    )
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    assert cuerpo["talla_recomendada"] == "XS"


def test_un_cuerpo_mas_grande_sube_de_talla(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    api.put(
        MEDIDAS,
        headers=cabeceras_cliente,
        json={"busto_cm": 102, "cintura_cm": 82.5, "cadera_cm": 113},
    )
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    assert cuerpo["talla_recomendada"] == "XL"


# --- Cómo se dibuja cada talla ---------------------------------------------


def test_la_talla_que_corresponde_se_dibuja_EXACTAMENTE_como_antes(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """Factor 1.0 en la recomendada.

    Es lo que garantiza que el vestidor calibrado a mano el 18/09 se siga
    viendo igual para quien tiene su talla. Una funcionalidad nueva no puede
    mover lo que ya estaba bien.
    """
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    recomendada = next(
        t for t in cuerpo["tallas"] if t["codigo"] == cuerpo["talla_recomendada"]
    )
    assert recomendada["factor_ancho"] == pytest.approx(1.0, abs=0.001)
    assert recomendada["factor_largo"] == pytest.approx(1.0, abs=0.001)


def test_la_XS_y_la_XL_YA_NO_se_dibujan_iguales(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    """El defecto que todo esto existe para arreglar.

    Hasta el 18/09 la prenda se escalaba para calzar el cuerpo siempre, asi que
    todas las tallas se veian identicas en pantalla y el cliente elegia a
    ciegas dentro de un probador.
    """
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    por_codigo = {t["codigo"]: t for t in cuerpo["tallas"]}

    assert por_codigo["XS"]["factor_ancho"] < 1.0
    assert por_codigo["XL"]["factor_ancho"] > 1.0
    # Y tambien mas corta, no solo mas angosta.
    assert por_codigo["XS"]["factor_largo"] < por_codigo["XL"]["factor_largo"]


def test_los_factores_crecen_con_la_talla(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    anchos = [t["factor_ancho"] for t in cuerpo["tallas"]]
    assert anchos == sorted(anchos), "las tallas vienen de la mas chica a la mas grande"


def test_una_prenda_mas_chica_que_el_cuerpo_se_marca_como_que_no_entra(
    api: TestClient, cabeceras_cliente: dict[str, str], prenda: dict
) -> None:
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)
    cuerpo = _ajuste(api, cabeceras_cliente, prenda["producto"])
    por_codigo = {t["codigo"]: t for t in cuerpo["tallas"]}
    # La XS de esta blusa mide 90 cm y el cuerpo 92: literalmente no cierra.
    assert por_codigo["XS"]["ajuste"] == "NO_ENTRA"
    assert por_codigo["M"]["ajuste"] == "A_TU_MEDIDA"


# --- De cada quien ----------------------------------------------------------


def test_las_medidas_son_de_cada_quien(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    api.put(MEDIDAS, headers=cabeceras_cliente, json=CUERPO_M)

    api.post(
        "/api/v1/auth/registro",
        json={
            "correo": CORREO_OTRA,
            "contrasena": CLAVE_OTRA,
            "nombres": "Otra",
            "apellidos": "Clienta",
        },
    )
    token = api.post(
        "/api/v1/auth/login",
        json={"correo": CORREO_OTRA, "contrasena": CLAVE_OTRA},
    ).json()["access_token"]
    cab_otra = {"Authorization": f"Bearer {token}"}

    assert api.get(MEDIDAS, headers=cab_otra).json() is None

    api.put(
        MEDIDAS,
        headers=cab_otra,
        json={"busto_cm": 104, "cintura_cm": 85, "cadera_cm": 115},
    )
    # Las de la primera no se movieron.
    r = api.get(MEDIDAS, headers=cabeceras_cliente)
    assert Decimal(r.json()["busto_cm"]) == Decimal("92.0")


def test_un_administrador_no_carga_medidas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Tiene usuario pero no ficha de cliente: no hay a quien atribuirselas."""
    assert api.get(MEDIDAS, headers=cabeceras_admin).status_code == 403


def test_sin_token_no_se_ven_medidas(api: TestClient) -> None:
    assert api.get(MEDIDAS).status_code == 401
