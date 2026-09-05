"""CU-08 · Gestionar categorías, tallas y colores.

Cubre el flujo principal, los cuatro flujos alternativos y las tres excepciones
de la ficha (docs/entregas/ciclo-1/cap-1-captura-requisitos.md).

Las dos pruebas que más importan son las que cubren lo que la base **no**
garantiza por sí sola:

- **E2, ciclos en la jerarquía.** El `CHECK ck_categoria_no_autopadre` solo
  impide que una categoría sea su propia madre. Un ciclo A→B→A pasa por debajo
  y dejaría esa rama fuera del árbol para siempre.
- **E1 entre categorías raíz.** `uq_categoria_padre_nombre` no compara dos
  filas con `categoria_padre_id` nulo: en PostgreSQL dos NULL no son iguales.
  Sin validarlo en el servicio, entrarían dos «Ropa» de primer nivel.
"""

from fastapi.testclient import TestClient

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"


def _crear_categoria(
    api: TestClient,
    admin: dict[str, str],
    *,
    nombre: str,
    padre: int | None = None,
    orden: int = 0,
) -> dict:
    respuesta = api.post(
        CATEGORIAS,
        headers=admin,
        json={
            "nombre": nombre,
            "categoria_padre_id": padre,
            "orden": orden,
            "activa": True,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _arbol(api: TestClient, admin: dict[str, str]) -> list[dict]:
    respuesta = api.get(CATEGORIAS, headers=admin)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_listan_las_categorias(api: TestClient) -> None:
    assert api.get(CATEGORIAS).status_code == 401


def test_un_cliente_no_entra_a_los_maestros(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El actor de CU-08 es el Administrador."""
    assert api.get(CATEGORIAS, headers=cabeceras_cliente).status_code == 403
    assert api.get(TALLAS, headers=cabeceras_cliente).status_code == 403
    assert api.get(COLORES, headers=cabeceras_cliente).status_code == 403


# --- Categorias: flujo principal -----------------------------------------

def test_el_arbol_llega_con_la_jerarquia_armada(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Paso 2: la jerarquía se resuelve en el servidor, no en la interfaz."""
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])
    _crear_categoria(api, cabeceras_admin, nombre="Vestidos", padre=dama["id"])
    _crear_categoria(api, cabeceras_admin, nombre="Calzado")

    arbol = _arbol(api, cabeceras_admin)

    raices = {c["nombre"] for c in arbol}
    assert raices == {"Ropa", "Calzado"}

    nodo_ropa = next(c for c in arbol if c["nombre"] == "Ropa")
    assert [c["nombre"] for c in nodo_ropa["subcategorias"]] == ["Dama"]
    assert [c["nombre"] for c in nodo_ropa["subcategorias"][0]["subcategorias"]] == [
        "Vestidos"
    ]


def test_el_arbol_respeta_el_orden_de_presentacion(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin orden explícito, la taxonomía sale alfabética y no como el negocio
    la piensa."""
    _crear_categoria(api, cabeceras_admin, nombre="Zapatos", orden=1)
    _crear_categoria(api, cabeceras_admin, nombre="Abrigos", orden=2)

    assert [c["nombre"] for c in _arbol(api, cabeceras_admin)] == ["Zapatos", "Abrigos"]


# --- Categorias: excepcion E1 --------------------------------------------

def test_excepcion_e1_dos_hermanas_no_pueden_llamarse_igual(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Dama", "categoria_padre_id": ropa["id"], "orden": 0, "activa": True},
    )
    assert respuesta.status_code == 409


def test_excepcion_e1_tambien_entre_categorias_raiz(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El agujero que la restricción de la base NO tapa.

    `uq_categoria_padre_nombre` no compara dos filas con `categoria_padre_id`
    nulo, porque en PostgreSQL dos NULL no son iguales. Sin la validación del
    servicio entrarían dos «Ropa» de primer nivel, y el administrador tendría
    dos ramas idénticas sin forma de distinguirlas.
    """
    _crear_categoria(api, cabeceras_admin, nombre="Ropa")

    respuesta = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Ropa", "categoria_padre_id": None, "orden": 0, "activa": True},
    )
    assert respuesta.status_code == 409


def test_el_nombre_se_compara_sin_distinguir_mayusculas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    _crear_categoria(api, cabeceras_admin, nombre="Ropa")

    respuesta = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "ROPA", "categoria_padre_id": None, "orden": 0, "activa": True},
    )
    assert respuesta.status_code == 409


def test_dos_hermanas_de_padres_distintos_si_pueden_llamarse_igual(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """«Dama» bajo Ropa y «Dama» bajo Calzado son categorías distintas."""
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    calzado = _crear_categoria(api, cabeceras_admin, nombre="Calzado")

    _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])
    _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=calzado["id"])


# --- Categorias: excepcion E2, ciclos ------------------------------------

def test_excepcion_e2_una_categoria_no_puede_colgar_de_si_misma(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")

    respuesta = api.patch(
        f"{CATEGORIAS}/{ropa['id']}",
        headers=cabeceras_admin,
        json={"categoria_padre_id": ropa["id"]},
    )
    assert respuesta.status_code == 422


def test_excepcion_e2_ciclo_de_dos_niveles(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """A→B→A. El CHECK de la base no lo ve; la consulta recursiva sí.

    Si pasara, la rama quedaría colgada de sí misma y ninguna consulta normal
    volvería a encontrarla: desaparecería del árbol para siempre.
    """
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.patch(
        f"{CATEGORIAS}/{ropa['id']}",
        headers=cabeceras_admin,
        json={"categoria_padre_id": dama["id"]},
    )
    assert respuesta.status_code == 422
    assert "rama" in respuesta.json()["detail"].lower()


def test_excepcion_e2_ciclo_de_tres_niveles(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """A→B→C→A. Es el que obliga a que la consulta sea recursiva de verdad:
    mirar solo los hijos directos no lo detecta."""
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])
    vestidos = _crear_categoria(api, cabeceras_admin, nombre="Vestidos", padre=dama["id"])

    respuesta = api.patch(
        f"{CATEGORIAS}/{ropa['id']}",
        headers=cabeceras_admin,
        json={"categoria_padre_id": vestidos["id"]},
    )
    assert respuesta.status_code == 422


def test_mover_una_rama_a_otro_padre_valido_si_funciona(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """La validación de ciclos no debe bloquear una reubicación legítima."""
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    calzado = _crear_categoria(api, cabeceras_admin, nombre="Calzado")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.patch(
        f"{CATEGORIAS}/{dama['id']}",
        headers=cabeceras_admin,
        json={"categoria_padre_id": calzado["id"]},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["categoria_padre_id"] == calzado["id"]


def test_una_subcategoria_puede_volverse_raiz(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Enviar el padre en null significa sacarla al primer nivel.

    Es distinto de no enviarlo, que la deja donde está.
    """
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.patch(
        f"{CATEGORIAS}/{dama['id']}",
        headers=cabeceras_admin,
        json={"categoria_padre_id": None},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["categoria_padre_id"] is None

    assert {c["nombre"] for c in _arbol(api, cabeceras_admin)} == {"Ropa", "Dama"}


def test_renombrar_sin_enviar_el_padre_no_la_mueve(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.patch(
        f"{CATEGORIAS}/{dama['id']}", headers=cabeceras_admin, json={"nombre": "Mujer"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Mujer"
    assert respuesta.json()["categoria_padre_id"] == ropa["id"]


# --- Categorias: flujo 3b y excepcion E3 ---------------------------------

def test_desactivar_una_categoria_no_arrastra_a_sus_hijas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El caso de uso no lo pide, y hacerlo dejaría al administrador sin
    entender por qué desaparecieron ramas enteras."""
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.patch(
        f"{CATEGORIAS}/{ropa['id']}/estado", headers=cabeceras_admin, json={"activo": False}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["activa"] is False

    nodo_ropa = next(c for c in _arbol(api, cabeceras_admin) if c["id"] == ropa["id"])
    hija = next(c for c in nodo_ropa["subcategorias"] if c["id"] == dama["id"])
    assert hija["activa"] is True


def test_excepcion_e3_no_se_elimina_una_categoria_con_subcategorias(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    respuesta = api.delete(f"{CATEGORIAS}/{ropa['id']}", headers=cabeceras_admin)
    assert respuesta.status_code == 409
    # El mensaje tiene que ofrecer la salida que pide el caso de uso.
    assert "desactivar" in respuesta.json()["detail"].lower()


def test_una_categoria_hoja_si_se_elimina(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    ropa = _crear_categoria(api, cabeceras_admin, nombre="Ropa")
    dama = _crear_categoria(api, cabeceras_admin, nombre="Dama", padre=ropa["id"])

    assert api.delete(f"{CATEGORIAS}/{dama['id']}", headers=cabeceras_admin).status_code == 204
    assert _arbol(api, cabeceras_admin)[0]["subcategorias"] == []


# --- Tallas (flujo alternativo 1a) ---------------------------------------

def test_las_tallas_salen_en_su_orden_y_no_alfabeticas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin el orden, XL aparece antes que S."""
    for codigo, orden in [("XL", 4), ("S", 1), ("M", 2), ("L", 3)]:
        respuesta = api.post(
            TALLAS,
            headers=cabeceras_admin,
            json={"tipo_prenda": "SUPERIOR", "codigo": codigo, "orden": orden, "activa": True},
        )
        assert respuesta.status_code == 201, respuesta.text

    listado = api.get(TALLAS, headers=cabeceras_admin).json()
    assert [t["codigo"] for t in listado] == ["S", "M", "L", "XL"]


def test_el_tipo_de_prenda_se_normaliza(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin normalizar, «Superior» y «superior» serían dos grupos distintos y la
    restricción dejaría pasar «M» repetida en cada uno."""
    api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": " superior ", "codigo": "m", "orden": 1, "activa": True},
    )

    listado = api.get(TALLAS, headers=cabeceras_admin).json()
    assert listado[0]["tipo_prenda"] == "SUPERIOR"
    assert listado[0]["codigo"] == "M"


def test_excepcion_e1_talla_repetida_en_el_mismo_tipo(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    cuerpo = {"tipo_prenda": "SUPERIOR", "codigo": "M", "orden": 1, "activa": True}
    assert api.post(TALLAS, headers=cabeceras_admin, json=cuerpo).status_code == 201
    assert api.post(TALLAS, headers=cabeceras_admin, json=cuerpo).status_code == 409


def test_el_mismo_codigo_en_otro_tipo_de_prenda_si_entra(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """«M» de parte superior y «M» de calzado son tallas distintas."""
    for tipo in ("SUPERIOR", "CALZADO"):
        respuesta = api.post(
            TALLAS,
            headers=cabeceras_admin,
            json={"tipo_prenda": tipo, "codigo": "M", "orden": 1, "activa": True},
        )
        assert respuesta.status_code == 201, respuesta.text


def test_los_tipos_de_prenda_se_ofrecen_para_no_reescribirlos(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "SUPERIOR", "codigo": "M", "orden": 1, "activa": True},
    )
    api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "CALZADO", "codigo": "38", "orden": 1, "activa": True},
    )

    respuesta = api.get(f"{TALLAS}/tipos", headers=cabeceras_admin)
    assert respuesta.status_code == 200
    assert respuesta.json() == ["CALZADO", "SUPERIOR"]


def test_desactivar_una_talla_la_saca_del_listado_filtrado(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Flujo 3b: deja de ofrecerse para variantes nuevas, pero sigue existiendo."""
    creada = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "SUPERIOR", "codigo": "M", "orden": 1, "activa": True},
    ).json()

    api.patch(
        f"{TALLAS}/{creada['id']}/estado", headers=cabeceras_admin, json={"activo": False}
    )

    activas = api.get(TALLAS, headers=cabeceras_admin, params={"activa": True}).json()
    assert creada["id"] not in [t["id"] for t in activas]
    # Pero sigue estando: no se borró.
    todas = api.get(TALLAS, headers=cabeceras_admin).json()
    assert creada["id"] in [t["id"] for t in todas]


# --- Colores (flujo alternativo 1b) --------------------------------------

def test_el_color_exige_el_formato_hexadecimal(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El CHECK ck_color_hex lo exige en la base; acá se rechaza antes, para
    devolver un 422 que nombra el campo."""
    for invalido in ("rojo", "#GGG", "#12345", "FF0000"):
        respuesta = api.post(
            COLORES,
            headers=cabeceras_admin,
            json={"nombre": "Prueba", "hexadecimal": invalido, "activo": True},
        )
        assert respuesta.status_code == 422, invalido


def test_el_hexadecimal_se_guarda_en_mayusculas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Un solo formato: si no, dos filas describirían el mismo color con
    '#ff0000' y '#FF0000'."""
    respuesta = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Rojo", "hexadecimal": "#ff0000", "activo": True},
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["hexadecimal"] == "#FF0000"


def test_excepcion_e1_color_con_nombre_repetido(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Rojo", "hexadecimal": "#FF0000", "activo": True},
    )

    # Distinto tono, mismo nombre y con otra capitalización: sigue siendo el
    # mismo color para quien lo elige de una lista.
    respuesta = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "rojo", "hexadecimal": "#CC0000", "activo": True},
    )
    assert respuesta.status_code == 409


def test_editar_un_color_sin_cambiarle_el_nombre_no_choca_consigo_mismo(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    color = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Rojo", "hexadecimal": "#FF0000", "activo": True},
    ).json()

    respuesta = api.patch(
        f"{COLORES}/{color['id']}",
        headers=cabeceras_admin,
        json={"nombre": "Rojo", "hexadecimal": "#CC0000"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["hexadecimal"] == "#CC0000"


def test_los_nombres_de_restriccion_existen_en_la_base(db) -> None:
    """Los nombres que el servicio busca en el IntegrityError tienen que existir.

    Cuando dos administradores dan de alta el mismo nombre a la vez, la
    verificación previa del servicio no alcanza: la restricción de la base es
    la que decide, y el bloque `except IntegrityError` traduce esa violación a
    un 409 buscando el nombre de la restricción dentro del mensaje.

    Un nombre mal escrito no lo detecta nadie —el bloque simplemente no entra y
    lo que debería ser un 409 sale como un 500—, y solo se descubre en una
    carrera real, que es justo cuando menos se quiere descubrir. De hecho pasó:
    el nombre de categoría estaba escrito como `uq_categoria_categoria_padre_id`
    y la restricción se llama `uq_categoria_padre_nombre`.
    """
    from sqlalchemy import text

    from app.modules.catalogo.maestros.service import UQ_CATEGORIA, UQ_COLOR, UQ_TALLA

    existentes = set(
        db.scalars(text("SELECT conname FROM pg_constraint WHERE contype = 'u'"))
    )

    faltantes = {UQ_CATEGORIA, UQ_TALLA, UQ_COLOR} - existentes
    assert not faltantes, (
        "El servicio busca restricciones que no existen en la base: "
        f"{sorted(faltantes)}"
    )
