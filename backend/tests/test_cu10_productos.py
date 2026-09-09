"""CU-10 · Gestionar productos y variantes.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-10-gestionar-productos-y-variantes.md).

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **E2, colección ajena a la temporada.** El esquema guarda `temporada_id` y
  `coleccion_id` a la vez —la única redundancia aceptada, decisión 2 de la §6.4—
  y ninguna restricción impide que se contradigan. Solo el servicio lo hace.
- **El SKU no se trunca.** Dos colores que empiezan igual, «Verde militar» y
  «Verde menta», producirían el mismo SKU si se recortara, y un SKU repetido es
  exactamente lo que un SKU no puede ser.
- **Volver a generar variantes no duplica ni falla.** Es lo que permite agregar
  una talla y regenerar sin deseleccionar lo anterior.
"""

from fastapi.testclient import TestClient

PRODUCTOS = "/api/v1/catalogo/productos"
VARIANTES = "/api/v1/catalogo/variantes"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
TEMPORADAS = "/api/v1/catalogo/temporadas"
COLECCIONES = "/api/v1/catalogo/colecciones"


# --- Ayudantes -----------------------------------------------------------

def _categoria(api: TestClient, admin: dict[str, str], nombre: str = "Camisas") -> int:
    r = api.post(CATEGORIAS, headers=admin, json={"nombre": nombre, "orden": 0, "activa": True})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _talla(api: TestClient, admin: dict[str, str], codigo: str, orden: int = 0) -> int:
    r = api.post(
        TALLAS,
        headers=admin,
        json={"tipo_prenda": "Superior", "codigo": codigo, "orden": orden, "activa": True},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _color(api: TestClient, admin: dict[str, str], nombre: str, hexa: str = "#101010") -> int:
    r = api.post(
        COLORES, headers=admin, json={"nombre": nombre, "hexadecimal": hexa, "activo": True}
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _temporada(api: TestClient, admin: dict[str, str], nombre: str = "Verano 2026") -> int:
    r = api.post(
        TEMPORADAS,
        headers=admin,
        json={
            "nombre": nombre,
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-03-31",
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _coleccion(api: TestClient, admin: dict[str, str], temporada_id: int, nombre: str) -> int:
    r = api.post(
        COLECCIONES,
        headers=admin,
        json={"temporada_id": temporada_id, "nombre": nombre, "activa": True},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _producto(
    api: TestClient, admin: dict[str, str], *, codigo="CAM-001", categoria_id=None, **extra
) -> dict:
    cuerpo = {
        "codigo": codigo,
        "nombre": "Camisa Oxford manga larga",
        "categoria_id": categoria_id if categoria_id is not None else _categoria(api, admin),
        "precio_base": "250.00",
        "activo": True,
    }
    cuerpo.update(extra)
    r = api.post(PRODUCTOS, headers=admin, json=cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_listan_los_productos(api: TestClient) -> None:
    assert api.get(PRODUCTOS).status_code == 401


def test_un_cliente_no_entra_a_los_productos(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """CU-10 es solo del Administrador: la vitrina del cliente es CU-17."""
    assert api.get(PRODUCTOS, headers=cabeceras_cliente).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_alta_de_producto_y_detalle(api: TestClient, cabeceras_admin: dict[str, str]) -> None:
    producto = _producto(api, cabeceras_admin)
    assert producto["codigo"] == "CAM-001"
    assert producto["variantes"] == []
    assert producto["variantes_totales"] == 0

    r = api.get(f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert r.json()["categoria_nombre"] == "Camisas"


def test_el_codigo_se_guarda_en_mayusculas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin normalizar, 'cam-001' y 'CAM-001' entrarían los dos: el UNIQUE de
    PostgreSQL distingue mayúsculas."""
    producto = _producto(api, cabeceras_admin, codigo="cam-001")
    assert producto["codigo"] == "CAM-001"


def test_excepcion_e1_codigo_duplicado(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    categoria = _categoria(api, cabeceras_admin)
    _producto(api, cabeceras_admin, codigo="CAM-001", categoria_id=categoria)
    r = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "CAM-001",
            "nombre": "Otra camisa",
            "categoria_id": categoria,
            "precio_base": "100.00",
        },
    )
    assert r.status_code == 409, r.text


def test_excepcion_e1_el_codigo_se_compara_sin_distinguir_mayusculas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    categoria = _categoria(api, cabeceras_admin)
    _producto(api, cabeceras_admin, codigo="CAM-001", categoria_id=categoria)
    r = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "  cam-001 ",
            "nombre": "Otra camisa",
            "categoria_id": categoria,
            "precio_base": "100.00",
        },
    )
    assert r.status_code == 409, r.text


def test_una_categoria_inexistente_da_404(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    r = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "X-1",
            "nombre": "Sin categoría",
            "categoria_id": 999999,
            "precio_base": "10.00",
        },
    )
    assert r.status_code == 404, r.text


# --- La redundancia temporada / coleccion (decision 2 de la 6.4) ---------

def test_excepcion_e2_la_coleccion_debe_pertenecer_a_la_temporada(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """La única redundancia del esquema, y la única prueba que la sostiene.

    Ninguna restricción de la base impide que `producto.temporada_id` y la
    temporada de su colección se contradigan.
    """
    verano = _temporada(api, cabeceras_admin, "Verano 2026")
    invierno = _temporada(api, cabeceras_admin, "Invierno 2026")
    coleccion_de_verano = _coleccion(api, cabeceras_admin, verano, "Playa")

    r = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "CAM-009",
            "nombre": "Camisa",
            "categoria_id": _categoria(api, cabeceras_admin),
            "precio_base": "100.00",
            "temporada_id": invierno,
            "coleccion_id": coleccion_de_verano,
        },
    )
    assert r.status_code == 422, r.text


def test_si_solo_viene_la_coleccion_la_temporada_se_completa_sola(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Es la otra mitad de la regla: dejar la temporada nula haría inconsistente
    el reporte de rotación, que es lo que justifica conservar la redundancia."""
    verano = _temporada(api, cabeceras_admin, "Verano 2026")
    coleccion = _coleccion(api, cabeceras_admin, verano, "Playa")

    producto = _producto(api, cabeceras_admin, coleccion_id=coleccion)
    assert producto["temporada_id"] == verano
    assert producto["coleccion_id"] == coleccion


def test_editar_puede_sacar_al_producto_de_la_coleccion(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Enviar null es distinto de no enviar el campo: significa quitarlo."""
    verano = _temporada(api, cabeceras_admin)
    coleccion = _coleccion(api, cabeceras_admin, verano, "Playa")
    producto = _producto(api, cabeceras_admin, coleccion_id=coleccion)

    r = api.patch(
        f"{PRODUCTOS}/{producto['id']}",
        headers=cabeceras_admin,
        json={"coleccion_id": None},
    )
    assert r.status_code == 200, r.text
    assert r.json()["coleccion_id"] is None
    # La temporada se conserva: el producto sigue siendo de verano aunque ya no
    # pertenezca a ninguna coleccion.
    assert r.json()["temporada_id"] == verano


def test_renombrar_sin_enviar_la_coleccion_no_la_quita(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    verano = _temporada(api, cabeceras_admin)
    coleccion = _coleccion(api, cabeceras_admin, verano, "Playa")
    producto = _producto(api, cabeceras_admin, coleccion_id=coleccion)

    r = api.patch(
        f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin, json={"nombre": "Otro nombre"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["coleccion_id"] == coleccion


# --- Paso 7: generacion de variantes -------------------------------------

def test_paso_7_genera_el_producto_cartesiano(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    tallas = [_talla(api, cabeceras_admin, "S", 1), _talla(api, cabeceras_admin, "M", 2)]
    colores = [
        _color(api, cabeceras_admin, "Negro"),
        _color(api, cabeceras_admin, "Blanco", "#FFFFFF"),
    ]

    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={"tallas": tallas, "colores": colores},
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert cuerpo["creadas"] == 4
    assert cuerpo["omitidas"] == 0
    assert {v["sku"] for v in cuerpo["variantes"]} == {
        "CAM-001-S-NEGRO",
        "CAM-001-S-BLANCO",
        "CAM-001-M-NEGRO",
        "CAM-001-M-BLANCO",
    }


def test_la_variante_hereda_el_precio_base_del_producto(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "S")],
            "colores": [_color(api, cabeceras_admin, "Negro")],
        },
    )
    assert r.json()["variantes"][0]["precio"] == "250.00"


def test_volver_a_generar_omite_lo_que_ya_existe_y_no_falla(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Agregar una talla y regenerar no obliga a deseleccionar lo anterior."""
    producto = _producto(api, cabeceras_admin)
    s = _talla(api, cabeceras_admin, "S", 1)
    negro = _color(api, cabeceras_admin, "Negro")

    api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={"tallas": [s], "colores": [negro]},
    )
    m = _talla(api, cabeceras_admin, "M", 2)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={"tallas": [s, m], "colores": [negro]},
    )
    assert r.status_code == 201, r.text
    assert r.json()["creadas"] == 1
    assert r.json()["omitidas"] == 1


def test_el_sku_no_se_trunca_y_dos_colores_parecidos_no_colisionan(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """«Verde militar» y «Verde menta» comparten los primeros seis caracteres."""
    producto = _producto(api, cabeceras_admin)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "S")],
            "colores": [
                _color(api, cabeceras_admin, "Verde militar", "#4B5320"),
                _color(api, cabeceras_admin, "Verde menta", "#98FF98"),
            ],
        },
    )
    assert r.status_code == 201, r.text
    skus = {v["sku"] for v in r.json()["variantes"]}
    assert len(skus) == 2, skus


def test_el_sku_pierde_las_tildes(api: TestClient, cabeceras_admin: dict[str, str]) -> None:
    """Un SKU viaja a etiquetas y lectores donde una eñe no siempre sobrevive."""
    producto = _producto(api, cabeceras_admin)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "S")],
            "colores": [_color(api, cabeceras_admin, "Marrón añejo", "#804000")],
        },
    )
    assert r.json()["variantes"][0]["sku"] == "CAM-001-S-MARRONANEJO"


def test_un_codigo_muy_largo_avisa_en_vez_de_truncar(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin, codigo="C" * 30)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "XXL")],
            "colores": [_color(api, cabeceras_admin, "Verde militar", "#4B5320")],
        },
    )
    assert r.status_code == 422, r.text


def test_las_variantes_salen_en_el_orden_de_las_tallas(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin el orden de la talla, XL aparecería antes que S por alfabético."""
    producto = _producto(api, cabeceras_admin)
    xl = _talla(api, cabeceras_admin, "XL", 4)
    s = _talla(api, cabeceras_admin, "S", 1)
    negro = _color(api, cabeceras_admin, "Negro")

    api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={"tallas": [xl, s], "colores": [negro]},
    )
    detalle = api.get(f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin).json()
    assert [v["talla_codigo"] for v in detalle["variantes"]] == ["S", "XL"]


# --- Flujos alternativos de variante -------------------------------------

def test_7a_alta_suelta_de_una_variante(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes",
        headers=cabeceras_admin,
        json={
            "talla_id": _talla(api, cabeceras_admin, "S"),
            "color_id": _color(api, cabeceras_admin, "Negro"),
            "precio": "300.00",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["precio"] == "300.00"


def test_7a_la_misma_combinacion_dos_veces_no_entra(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    cuerpo = {
        "talla_id": _talla(api, cabeceras_admin, "S"),
        "color_id": _color(api, cabeceras_admin, "Negro"),
    }
    api.post(f"{PRODUCTOS}/{producto['id']}/variantes", headers=cabeceras_admin, json=cuerpo)
    r = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes", headers=cabeceras_admin, json=cuerpo
    )
    assert r.status_code == 409, r.text


def test_7b_editar_el_precio_de_una_variante(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    variante = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes",
        headers=cabeceras_admin,
        json={
            "talla_id": _talla(api, cabeceras_admin, "S"),
            "color_id": _color(api, cabeceras_admin, "Negro"),
        },
    ).json()

    r = api.patch(
        f"{VARIANTES}/{variante['id']}", headers=cabeceras_admin, json={"precio": "999.99"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["precio"] == "999.99"


def test_cambiar_el_precio_base_no_repropaga_a_las_variantes(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Decisión 1 de la §6.4: si repropagara, cambiaría el precio de variantes
    ya vendidas."""
    producto = _producto(api, cabeceras_admin)
    api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "S")],
            "colores": [_color(api, cabeceras_admin, "Negro")],
        },
    )
    api.patch(
        f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin, json={"precio_base": "500.00"}
    )
    detalle = api.get(f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin).json()
    assert detalle["precio_base"] == "500.00"
    assert detalle["variantes"][0]["precio"] == "250.00"


# --- 3b Desactivar -------------------------------------------------------

def test_3b_desactivar_el_producto_arrastra_sus_variantes(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Una variante activa colgando de un producto retirado aparecería en el
    inventario y en las reservas de algo que ya no se ofrece."""
    producto = _producto(api, cabeceras_admin)
    api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "S")],
            "colores": [_color(api, cabeceras_admin, "Negro")],
        },
    )
    r = api.patch(
        f"{PRODUCTOS}/{producto['id']}/estado", headers=cabeceras_admin, json={"activo": False}
    )
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is False
    assert all(not v["activa"] for v in r.json()["variantes"])
    assert r.json()["variantes_activas"] == 0


# --- Listado, filtros y paginacion ---------------------------------------

def test_el_listado_filtra_por_busqueda_de_codigo_y_nombre(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    categoria = _categoria(api, cabeceras_admin)
    _producto(api, cabeceras_admin, codigo="CAM-001", categoria_id=categoria)
    _producto(
        api, cabeceras_admin, codigo="PAN-002", categoria_id=categoria, nombre="Pantalón chino"
    )

    r = api.get(PRODUCTOS, headers=cabeceras_admin, params={"busqueda": "PAN"})
    assert r.status_code == 200, r.text
    assert [p["codigo"] for p in r.json()["items"]] == ["PAN-002"]


def test_el_listado_trae_el_conteo_de_variantes(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={
            "tallas": [_talla(api, cabeceras_admin, "S"), _talla(api, cabeceras_admin, "M", 2)],
            "colores": [_color(api, cabeceras_admin, "Negro")],
        },
    )
    fila = api.get(PRODUCTOS, headers=cabeceras_admin).json()["items"][0]
    assert fila["variantes_totales"] == 2
    assert fila["variantes_activas"] == 2


def test_la_paginacion_cuenta_el_total_con_los_mismos_filtros(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Si el conteo filtrara distinto que el listado, el paginador ofrecería
    páginas vacías."""
    categoria = _categoria(api, cabeceras_admin)
    for i in range(3):
        _producto(api, cabeceras_admin, codigo=f"CAM-00{i}", categoria_id=categoria)
    _producto(api, cabeceras_admin, codigo="PAN-100", categoria_id=categoria)

    r = api.get(
        PRODUCTOS, headers=cabeceras_admin, params={"busqueda": "CAM", "tamano": 2, "pagina": 1}
    )
    cuerpo = r.json()
    assert cuerpo["total"] == 3
    assert len(cuerpo["items"]) == 2

    segunda = api.get(
        PRODUCTOS, headers=cabeceras_admin, params={"busqueda": "CAM", "tamano": 2, "pagina": 2}
    ).json()
    assert len(segunda["items"]) == 1


def test_el_tamano_de_pagina_tiene_tope(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Sin tope, `tamano=100000` traería el catálogo entero."""
    r = api.get(PRODUCTOS, headers=cabeceras_admin, params={"tamano": 100000})
    assert r.status_code == 422


# --- Eliminacion ---------------------------------------------------------

def test_un_producto_sin_dependencias_se_elimina(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    producto = _producto(api, cabeceras_admin)
    assert api.delete(f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin).status_code == 204
    assert api.get(f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin).status_code == 404


def test_eliminar_el_producto_arrastra_sus_variantes(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """El ON DELETE CASCADE de variante_producto. Lo que no arrastra son las
    tablas de Mateo, que no tienen cascada y protegen el borrado."""
    producto = _producto(api, cabeceras_admin)
    variante = api.post(
        f"{PRODUCTOS}/{producto['id']}/variantes",
        headers=cabeceras_admin,
        json={
            "talla_id": _talla(api, cabeceras_admin, "S"),
            "color_id": _color(api, cabeceras_admin, "Negro"),
        },
    ).json()

    api.delete(f"{PRODUCTOS}/{producto['id']}", headers=cabeceras_admin)
    assert api.patch(
        f"{VARIANTES}/{variante['id']}", headers=cabeceras_admin, json={"precio": "10.00"}
    ).status_code == 404
