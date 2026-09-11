"""CU-04 · Gestionar perfil del cliente — categorías preferidas.

El bloque del caso de uso que quedó diferido del Ciclo 1: el paso 2 promete
«datos personales, tallas habituales, **preferencias** y direcciones», y las
preferencias dependían de CU-08, que entonces no creaba ninguna categoría que
elegir. Cierra la §6.11.3 de `docs/06-decisiones-tecnicas.md`.

Archivo aparte de `test_cu04_perfil.py`, que es del Ciclo 1 y cubre los datos
personales y las direcciones: así queda claro en el historial qué entró en cada
ciclo, y ninguna rama toca las líneas de la otra.

Lo que más importa cubrir:

- **Que la operación sea de reemplazo y no de acumulación.** Se manda la
  selección completa; guardar dos veces la misma lista tiene que dejar lo mismo,
  y quitar una categoría tiene que quitarla de verdad.
- **Que una categoría desactivada no se pueda elegir.** El cliente puede tener
  el árbol cargado desde antes de que el Administrador desactivara una rama.
- **Que el error nombre las que sobran.** Decir solo «hay un error» deja al
  cliente sin saber cuál desmarcar.
- **Que la tabla puente no imponga sus errores al usuario.** Mandar la misma
  categoría dos veces es algo que una interfaz puede hacer sin querer; la clave
  primaria compuesta lo rechazaría con un error de base.
"""

import pytest
from fastapi.testclient import TestClient

PERFIL = "/api/v1/perfil"
PREFERENCIAS = f"{PERFIL}/categorias"
CATEGORIAS = "/api/v1/catalogo/categorias"


@pytest.fixture
def categorias(api: TestClient, cabeceras_admin: dict[str, str]) -> dict[str, int]:
    """Tres categorías activas y una desactivada."""
    creadas = {}
    for nombre in ("Blusas", "Pantalones", "Calzado", "Descontinuada"):
        r = api.post(
            CATEGORIAS,
            headers=cabeceras_admin,
            json={"nombre": nombre, "orden": 0, "activa": True},
        )
        assert r.status_code == 201, r.text
        creadas[nombre] = r.json()["id"]

    # Desactivar va por `/estado` y con el campo `activo`; el esquema de edición
    # de CU-08 no lleva el estado a propósito.
    r = api.patch(
        f"{CATEGORIAS}/{creadas['Descontinuada']}/estado",
        headers=cabeceras_admin,
        json={"activo": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["activa"] is False
    return creadas


def _guardar(api: TestClient, cabeceras: dict[str, str], ids: list[int]):
    return api.put(PREFERENCIAS, headers=cabeceras, json={"categorias": ids})


# --- Autorización --------------------------------------------------------

def test_sin_token_no_se_guardan(api: TestClient, categorias) -> None:
    assert api.put(PREFERENCIAS, json={"categorias": []}).status_code == 401


def test_un_administrador_no_tiene_preferencias(
    api: TestClient, cabeceras_admin: dict[str, str], categorias
) -> None:
    """El perfil es del Cliente: el Administrador no tiene ficha de cliente."""
    assert _guardar(api, cabeceras_admin, []).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_el_perfil_arranca_sin_preferencias(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    perfil = api.get(PERFIL, headers=cabeceras_cliente).json()
    assert perfil["categorias_preferidas"] == []


def test_guardar_preferencias_las_devuelve_en_el_perfil(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    elegidas = [categorias["Blusas"], categorias["Calzado"]]
    respuesta = _guardar(api, cabeceras_cliente, elegidas)
    assert respuesta.status_code == 200, respuesta.text

    # La respuesta trae el perfil completo, para refrescar con una sola lectura.
    nombres = {c["nombre"] for c in respuesta.json()["categorias_preferidas"]}
    assert nombres == {"Blusas", "Calzado"}
    assert respuesta.json()["correo"]

    perfil = api.get(PERFIL, headers=cabeceras_cliente).json()
    assert {c["nombre"] for c in perfil["categorias_preferidas"]} == {"Blusas", "Calzado"}


def test_la_categoria_viaja_con_su_nombre(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    """«Categoría 7» no se puede dibujar sin volver a pedir el maestro."""
    cuerpo = _guardar(api, cabeceras_cliente, [categorias["Blusas"]]).json()
    preferida = cuerpo["categorias_preferidas"][0]
    assert preferida["id"] == categorias["Blusas"]
    assert preferida["nombre"] == "Blusas"


# --- Es reemplazo, no acumulación ---------------------------------------

def test_guardar_dos_veces_lo_mismo_no_duplica(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    """La operación es idempotente: repetirla no cambia nada."""
    elegidas = [categorias["Blusas"], categorias["Calzado"]]
    _guardar(api, cabeceras_cliente, elegidas)
    cuerpo = _guardar(api, cabeceras_cliente, elegidas).json()
    assert len(cuerpo["categorias_preferidas"]) == 2


def test_guardar_reemplaza_la_seleccion_anterior(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    _guardar(api, cabeceras_cliente, [categorias["Blusas"], categorias["Calzado"]])
    cuerpo = _guardar(api, cabeceras_cliente, [categorias["Pantalones"]]).json()
    assert [c["nombre"] for c in cuerpo["categorias_preferidas"]] == ["Pantalones"]


def test_la_lista_vacia_borra_las_preferencias(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    """Es cómo el cliente deja de recibir recomendaciones sesgadas por una
    preferencia que ya no tiene. No es un error ni un caso especial."""
    _guardar(api, cabeceras_cliente, [categorias["Blusas"]])
    cuerpo = _guardar(api, cabeceras_cliente, []).json()
    assert cuerpo["categorias_preferidas"] == []


def test_la_misma_categoria_dos_veces_se_guarda_una(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    """La clave primaria compuesta de `cliente_categoria` lo rechazaría con un
    error de base; es algo que una interfaz puede mandar sin querer."""
    cuerpo = _guardar(
        api, cabeceras_cliente, [categorias["Blusas"], categorias["Blusas"]]
    )
    assert cuerpo.status_code == 200, cuerpo.text
    assert len(cuerpo.json()["categorias_preferidas"]) == 1


# --- Excepciones ---------------------------------------------------------

def test_una_categoria_inexistente_da_422_y_la_nombra(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    respuesta = _guardar(api, cabeceras_cliente, [categorias["Blusas"], 999999])
    assert respuesta.status_code == 422
    assert "999999" in respuesta.json()["detail"]


def test_una_categoria_desactivada_no_se_puede_elegir(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    """El cliente puede tener el árbol cargado desde antes de que el
    Administrador desactivara la rama."""
    respuesta = _guardar(api, cabeceras_cliente, [categorias["Descontinuada"]])
    assert respuesta.status_code == 422
    assert str(categorias["Descontinuada"]) in respuesta.json()["detail"]


def test_nada_se_guarda_si_una_categoria_sobra(
    api: TestClient, cabeceras_cliente: dict[str, str], categorias
) -> None:
    """Todo o nada: media selección guardada sería peor que ninguna."""
    _guardar(api, cabeceras_cliente, [categorias["Pantalones"]])
    _guardar(api, cabeceras_cliente, [categorias["Blusas"], 999999])

    perfil = api.get(PERFIL, headers=cabeceras_cliente).json()
    assert [c["nombre"] for c in perfil["categorias_preferidas"]] == ["Pantalones"]


def test_hay_un_tope_de_preferencias(
    api: TestClient, cabeceras_cliente: dict[str, str], cabeceras_admin: dict[str, str]
) -> None:
    """Una preferencia que abarca todo el catálogo no es una preferencia: el
    recomendador del CU-33 la usa para acotar candidatas."""
    muchas = []
    for i in range(13):
        r = api.post(
            CATEGORIAS,
            headers=cabeceras_admin,
            json={"nombre": f"Categoria {i}", "orden": 0, "activa": True},
        )
        muchas.append(r.json()["id"])

    assert _guardar(api, cabeceras_cliente, muchas).status_code == 422
    assert _guardar(api, cabeceras_cliente, muchas[:12]).status_code == 200
