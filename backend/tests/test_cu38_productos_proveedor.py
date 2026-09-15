"""CU-38 · Registrar productos del proveedor.

Realiza el **RF37**. Hasta el Ciclo 2 el Proveedor era un actor principal que
**no iniciaba ningún caso de uso**: existía como ficha que el Administrador daba
de alta (CU-07) y, con acceso habilitado, podía mirar esa ficha. Nada más. Esto
es lo que lo convierte en un actor de verdad.

El código propio de este caso de uso es casi todo **ámbito**: el CRUD ya es de
CU-10 y no se reimplementa. Por eso estas pruebas empujan sobre el ámbito, que
es lo único que puede romperse acá.

Lo que más importa cubrir
-------------------------
- **Que un proveedor no vea ni toque lo de otro**, y que el intento se responda
  `404` y no `403`: un 403 confirmaría que ese identificador es un producto real
  de la competencia, y recorrer los números sería un censo del catálogo ajeno.
- **Que `proveedor_id` no se pueda mandar.** Es el ataque obvio: pedir el alta
  a nombre de otro, o mover un producto propio al catálogo de otro.
- **Que lo registrado nazca inactivo** y que el Proveedor no pueda publicarlo.
  Registrar no es publicar: la vitrina la ve el cliente.
- **Que la baja de CU-07 corte de verdad.** Si un proveedor desactivado pudiera
  seguir cargando prendas, esa baja sería decorativa.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from .conftest import CLAVE_ADMIN, CORREO_ADMIN  # noqa: F401  (los usa el fixture)

MIS = "/api/v1/catalogo/mis-productos"
LISTAS = f"{MIS}/listas"
PROVEEDORES = "/api/v1/organizacion/proveedores"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"

CLAVE_PROVEEDOR = "Proveedor123"


# --- Escenario -----------------------------------------------------------

def _crear_proveedor_con_acceso(
    api: TestClient, admin: dict[str, str], *, razon: str, nit: str, correo: str
) -> dict:
    """Un proveedor dado de alta por CU-07 y con acceso habilitado.

    Se hace por la API y no escribiendo en la base: así estas pruebas también
    comprueban que el camino real —el que usa el Administrador— deja al
    Proveedor en condiciones de usar CU-38.
    """
    alta = api.post(
        PROVEEDORES,
        headers=admin,
        json={"razon_social": razon, "identificacion_tributaria": nit, "activo": True},
    )
    assert alta.status_code == 201, alta.text
    proveedor = alta.json()

    acceso = api.post(
        f"{PROVEEDORES}/{proveedor['id']}/acceso",
        headers=admin,
        json={
            "correo": correo,
            "contrasena": CLAVE_PROVEEDOR,
            "nombres": "Persona",
            "apellidos": "Del Proveedor",
        },
    )
    assert acceso.status_code in (200, 201), acceso.text
    return proveedor


def _entrar(api: TestClient, correo: str, clave: str = CLAVE_PROVEEDOR) -> dict[str, str]:
    r = api.post("/api/v1/auth/login", json={"correo": correo, "contrasena": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def maestros(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Una categoría, dos tallas y dos colores activos."""
    categoria = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Blusas", "orden": 0, "activa": True},
    )
    assert categoria.status_code == 201, categoria.text

    tallas = []
    for codigo, orden in (("S", 1), ("M", 2)):
        r = api.post(
            TALLAS,
            headers=cabeceras_admin,
            json={"tipo_prenda": "Superior", "codigo": codigo, "orden": orden, "activa": True},
        )
        assert r.status_code == 201, r.text
        tallas.append(r.json()["id"])

    colores = []
    for nombre, hexa in (("Negro", "#101010"), ("Malva", "#8E6DA6")):
        r = api.post(
            COLORES, headers=cabeceras_admin, json={"nombre": nombre, "hexadecimal": hexa, "activo": True}
        )
        assert r.status_code == 201, r.text
        colores.append(r.json()["id"])

    return {"categoria": categoria.json()["id"], "tallas": tallas, "colores": colores}


@pytest.fixture
def dos_proveedores(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Dos proveedores con acceso. El aislamiento se prueba con dos, no con uno."""
    uno = _crear_proveedor_con_acceso(
        api, cabeceras_admin, razon="Textiles Uno", nit="1000001", correo="uno@proveedor.bo"
    )
    dos = _crear_proveedor_con_acceso(
        api, cabeceras_admin, razon="Textiles Dos", nit="1000002", correo="dos@proveedor.bo"
    )
    return {
        "uno": {"ficha": uno, "cab": _entrar(api, "uno@proveedor.bo")},
        "dos": {"ficha": dos, "cab": _entrar(api, "dos@proveedor.bo")},
    }


def _registrar(api: TestClient, cab: dict[str, str], maestros: dict, codigo: str, **extra):
    cuerpo = {
        "codigo": codigo,
        "nombre": f"Blusa {codigo}",
        "categoria_id": maestros["categoria"],
        "precio_base": "250.00",
    }
    cuerpo.update(extra)
    return api.post(MIS, headers=cab, json=cuerpo)


# --- Flujo principal -----------------------------------------------------

def test_el_proveedor_registra_una_prenda_y_declara_sus_tallas_y_colores(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """Flujo principal completo: registrar, listar y generar variantes."""
    cab = dos_proveedores["uno"]["cab"]

    alta = _registrar(api, cab, maestros, "TXU-001")
    assert alta.status_code == 201, alta.text
    producto = alta.json()

    # Queda a su nombre, sin haberlo pedido.
    assert producto["proveedor_id"] == dos_proveedores["uno"]["ficha"]["id"]

    # Y NACE INACTIVA: registrar no es publicar.
    assert producto["activo"] is False

    # Paso 7: las tallas y colores en que la abastece.
    variantes = api.post(
        f"{MIS}/{producto['id']}/variantes",
        headers=cab,
        json={"tallas": maestros["tallas"], "colores": maestros["colores"]},
    )
    assert variantes.status_code == 201, variantes.text
    assert variantes.json()["creadas"] == 4  # 2 tallas x 2 colores

    detalle = api.get(f"{MIS}/{producto['id']}", headers=cab)
    assert detalle.status_code == 200
    assert len(detalle.json()["variantes"]) == 4

    listado = api.get(MIS, headers=cab)
    assert listado.status_code == 200
    assert [p["codigo"] for p in listado.json()["items"]] == ["TXU-001"]


def test_generar_las_mismas_variantes_dos_veces_no_duplica(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """Repetir la llamada es seguro: las que ya existen se omiten."""
    cab = dos_proveedores["uno"]["cab"]
    producto = _registrar(api, cab, maestros, "TXU-002").json()
    cuerpo = {"tallas": maestros["tallas"], "colores": maestros["colores"]}

    primera = api.post(f"{MIS}/{producto['id']}/variantes", headers=cab, json=cuerpo)
    segunda = api.post(f"{MIS}/{producto['id']}/variantes", headers=cab, json=cuerpo)

    assert primera.json()["creadas"] == 4
    assert segunda.json()["creadas"] == 0
    assert segunda.json()["omitidas"] == 4


# --- El ámbito, que es todo el caso de uso -------------------------------

def test_el_proveedor_no_puede_pedir_el_alta_a_nombre_de_otro(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """`proveedor_id` no está en el esquema: si llega, se descarta.

    Es el ataque obvio, y no se defiende comprobándolo sino no aceptándolo.
    """
    alta = _registrar(
        api,
        dos_proveedores["uno"]["cab"],
        maestros,
        "TXU-003",
        proveedor_id=dos_proveedores["dos"]["ficha"]["id"],
    )
    assert alta.status_code == 201, alta.text
    assert alta.json()["proveedor_id"] == dos_proveedores["uno"]["ficha"]["id"]


def test_el_proveedor_no_puede_publicar_su_prenda_desde_el_alta(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """Mandar `activo: true` en el alta tampoco la publica."""
    alta = _registrar(api, dos_proveedores["uno"]["cab"], maestros, "TXU-004", activo=True)
    assert alta.status_code == 201
    assert alta.json()["activo"] is False


def test_un_producto_de_otro_proveedor_no_existe(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """404 en las cuatro puertas, y NO 403.

    Un 403 confirmaría que ese identificador es un producto real de la
    competencia, y recorrer los números sería un censo del catálogo ajeno.
    """
    ajeno = _registrar(api, dos_proveedores["dos"]["cab"], maestros, "TXD-001").json()
    cab = dos_proveedores["uno"]["cab"]
    ruta = f"{MIS}/{ajeno['id']}"

    assert api.get(ruta, headers=cab).status_code == 404
    assert api.patch(ruta, headers=cab, json={"nombre": "Robada"}).status_code == 404
    assert api.patch(f"{ruta}/estado", headers=cab, json={"activo": False}).status_code == 404
    assert (
        api.post(
            f"{ruta}/variantes",
            headers=cab,
            json={"tallas": maestros["tallas"], "colores": maestros["colores"]},
        ).status_code
        == 404
    )

    # Y el de la competencia quedó intacto.
    suyo = api.get(ruta, headers=dos_proveedores["dos"]["cab"])
    assert suyo.status_code == 200
    assert suyo.json()["nombre"] == "Blusa TXD-001"


def test_el_listado_solo_muestra_lo_propio(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    dos_proveedores: dict,
    maestros: dict,
) -> None:
    """Ni lo de otro proveedor, ni lo que no tiene proveedor.

    El catálogo sembrado tiene productos con `proveedor_id` nulo: no son de
    nadie en particular, así que tampoco son suyos.
    """
    _registrar(api, dos_proveedores["uno"]["cab"], maestros, "TXU-005")
    _registrar(api, dos_proveedores["dos"]["cab"], maestros, "TXD-002")

    sin_dueno = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "SIN-001",
            "nombre": "Prenda sin proveedor",
            "categoria_id": maestros["categoria"],
            "precio_base": "100.00",
        },
    )
    assert sin_dueno.status_code == 201, sin_dueno.text

    listado = api.get(MIS, headers=dos_proveedores["uno"]["cab"]).json()
    assert [p["codigo"] for p in listado["items"]] == ["TXU-005"]
    assert listado["total"] == 1


def test_editar_no_puede_mover_el_producto_a_otro_proveedor(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """`proveedor_id` tampoco está en el esquema de edición."""
    cab = dos_proveedores["uno"]["cab"]
    producto = _registrar(api, cab, maestros, "TXU-006").json()

    editado = api.patch(
        f"{MIS}/{producto['id']}",
        headers=cab,
        json={"nombre": "Blusa corregida", "proveedor_id": dos_proveedores["dos"]["ficha"]["id"]},
    )
    assert editado.status_code == 200, editado.text
    assert editado.json()["nombre"] == "Blusa corregida"
    assert editado.json()["proveedor_id"] == dos_proveedores["uno"]["ficha"]["id"]

    # Y el otro proveedor sigue sin verlo.
    assert api.get(f"{MIS}/{producto['id']}", headers=dos_proveedores["dos"]["cab"]).status_code == 404


def test_un_administrador_no_entra_por_la_puerta_del_proveedor(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """La guarda es de rol PROVEEDOR, declarada a nivel de router.

    El Administrador tiene su propia puerta —CU-10— con alcance a todo el
    catálogo; ésta resuelve el ámbito desde el token y para él no significaría
    nada.
    """
    assert api.get(MIS, headers=cabeceras_admin).status_code == 403
    assert api.get(LISTAS, headers=cabeceras_admin).status_code == 403


def test_sin_token_no_se_entra(api: TestClient) -> None:
    assert api.get(MIS).status_code == 401


# --- Retirar, que es lo único que puede hacer con el estado --------------

def test_el_proveedor_retira_una_prenda_y_sus_variantes_se_desactivan(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """Retirar no borra: el producto sigue en el inventario y en el histórico."""
    cab = dos_proveedores["uno"]["cab"]
    producto = _registrar(api, cab, maestros, "TXU-007").json()
    api.post(
        f"{MIS}/{producto['id']}/variantes",
        headers=cab,
        json={"tallas": maestros["tallas"], "colores": maestros["colores"]},
    )

    retirado = api.patch(f"{MIS}/{producto['id']}/estado", headers=cab, json={"activo": False})
    assert retirado.status_code == 200, retirado.text
    assert retirado.json()["activo"] is False
    assert all(not v["activa"] for v in retirado.json()["variantes"])

    # Sigue existiendo y lo sigue viendo.
    assert api.get(f"{MIS}/{producto['id']}", headers=cab).status_code == 200


def test_el_proveedor_no_puede_publicar_una_prenda(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """403 y no 422: el dato está bien escrito, lo que falta es el permiso.

    Publicar en la vitrina es del Administrador, por CU-10. Es la misma regla
    por la que el alta nace inactiva.
    """
    cab = dos_proveedores["uno"]["cab"]
    producto = _registrar(api, cab, maestros, "TXU-008").json()

    respuesta = api.patch(f"{MIS}/{producto['id']}/estado", headers=cab, json={"activo": True})
    assert respuesta.status_code == 403
    assert "administrador" in respuesta.json()["detail"].lower()

    assert api.get(f"{MIS}/{producto['id']}", headers=cab).json()["activo"] is False


def test_el_administrador_si_puede_publicar_lo_que_cargo_el_proveedor(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    dos_proveedores: dict,
    maestros: dict,
) -> None:
    """La otra mitad de la regla: el circuito tiene que poder cerrarse.

    Si nadie pudiera activarlo, lo que registra el Proveedor no llegaría nunca
    a la vitrina y el caso de uso no serviría para nada.
    """
    producto = _registrar(api, dos_proveedores["uno"]["cab"], maestros, "TXU-009").json()

    publicado = api.patch(
        f"{PRODUCTOS}/{producto['id']}/estado", headers=cabeceras_admin, json={"activo": True}
    )
    assert publicado.status_code == 200, publicado.text
    assert publicado.json()["activo"] is True

    # Y el Proveedor lo ve publicado.
    assert api.get(f"{MIS}/{producto['id']}", headers=dos_proveedores["uno"]["cab"]).json()["activo"] is True


# --- Errores de CU-10, vistos desde el Proveedor -------------------------

def test_un_codigo_ya_tomado_por_otro_proveedor_da_409_sin_decir_de_quien(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """Excepción E1. El UNIQUE es de toda la tabla, no por proveedor.

    El mensaje no puede nombrar al dueño: eso reabriría el censo que el 404
    cierra.
    """
    _registrar(api, dos_proveedores["dos"]["cab"], maestros, "TXD-003")

    choque = _registrar(api, dos_proveedores["uno"]["cab"], maestros, "TXD-003")
    assert choque.status_code == 409
    detalle = choque.json()["detail"].lower()
    assert "código" in detalle
    assert "textiles dos" not in detalle


def test_una_categoria_inexistente_da_422(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    alta = _registrar(
        api, dos_proveedores["uno"]["cab"], maestros, "TXU-010", categoria_id=999_999
    )
    assert alta.status_code == 422


# --- Quién es el proveedor -----------------------------------------------

def test_un_usuario_con_rol_proveedor_pero_sin_ficha_recibe_un_mensaje_util(
    api: TestClient, db, cabeceras_admin: dict[str, str]
) -> None:
    """Pasa si le asignan el rol por CU-03 en vez de habilitar acceso por CU-07.

    No es culpa de quien opera y el mensaje lo dice: no hay nada que pueda
    hacer él desde su lado.
    """
    from app.core.security import hash_password
    from app.modules.seguridad.models import Rol, Usuario

    rol = db.scalar(select(Rol).where(Rol.nombre == "PROVEEDOR"))
    db.add(
        Usuario(
            correo="huerfano@proveedor.bo",
            hash_contrasena=hash_password(CLAVE_PROVEEDOR),
            nombres="Sin",
            apellidos="Ficha",
            rol_id=rol.id,
        )
    )
    db.commit()

    respuesta = api.get(MIS, headers=_entrar(api, "huerfano@proveedor.bo"))
    assert respuesta.status_code == 404
    assert "ficha de proveedor" in respuesta.json()["detail"].lower()


def test_un_proveedor_dado_de_baja_no_puede_seguir_cargando_prendas(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    dos_proveedores: dict,
    maestros: dict,
) -> None:
    """Si no cortara, la baja de CU-07 sería decorativa.

    403 y no 404: acá sí se le puede decir por qué, porque es su propia ficha
    y no revela nada de nadie más.
    """
    ficha = dos_proveedores["uno"]["ficha"]
    cab = dos_proveedores["uno"]["cab"]

    baja = api.patch(
        f"{PROVEEDORES}/{ficha['id']}/estado", headers=cabeceras_admin, json={"activo": False}
    )
    assert baja.status_code == 200, baja.text

    assert api.get(MIS, headers=cab).status_code == 403
    assert _registrar(api, cab, maestros, "TXU-011").status_code == 403


# --- Las listas del formulario -------------------------------------------

def test_las_listas_traen_los_maestros_activos(
    api: TestClient, dos_proveedores: dict, maestros: dict
) -> None:
    """El Proveedor no puede leer los routers de CU-08: éste es su camino."""
    listas = api.get(LISTAS, headers=dos_proveedores["uno"]["cab"])
    assert listas.status_code == 200, listas.text
    cuerpo = listas.json()

    assert [c["nombre"] for c in cuerpo["categorias"]] == ["Blusas"]
    assert sorted(t["codigo"] for t in cuerpo["tallas"]) == ["M", "S"]
    assert sorted(c["nombre"] for c in cuerpo["colores"]) == ["Malva", "Negro"]
    assert "temporadas" in cuerpo and "colecciones" in cuerpo


def test_las_listas_no_ofrecen_un_maestro_dado_de_baja(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    dos_proveedores: dict,
    maestros: dict,
) -> None:
    """Ofrecer en un alta algo dado de baja sería crear deuda a propósito."""
    baja = api.patch(
        f"{COLORES}/{maestros['colores'][0]}/estado",
        headers=cabeceras_admin,
        json={"activo": False},
    )
    assert baja.status_code == 200, baja.text

    listas = api.get(LISTAS, headers=dos_proveedores["uno"]["cab"]).json()
    assert [c["nombre"] for c in listas["colores"]] == ["Malva"]


def test_el_proveedor_sigue_sin_poder_crear_maestros(
    api: TestClient, dos_proveedores: dict
) -> None:
    """Es el motivo por el que `/listas` existe en vez de aflojar CU-08.

    La guarda de aquellos routers se declara una sola vez para todo el router:
    abrirla para leer habría abierto también el crear y el borrar.
    """
    cab = dos_proveedores["uno"]["cab"]
    assert api.post(CATEGORIAS, headers=cab, json={"nombre": "Inventada", "orden": 9}).status_code == 403
    assert api.get(CATEGORIAS, headers=cab).status_code == 403


# --- La edición parcial, que es donde se pierden datos en silencio ------
#
# El servicio del Proveedor traduce su esquema al de CU-10 con
# `model_construct`, conservando `model_fields_set`. Si esa traducción se
# rompiera, CU-10 no fallaría: leería «no enviado» donde el Proveedor mandó un
# valor, o al revés. El resultado sería un producto que pierde su temporada al
# corregirle el nombre — y ninguna prueba de las de arriba lo notaría.

TEMPORADAS = "/api/v1/catalogo/temporadas"
COLECCIONES = "/api/v1/catalogo/colecciones"


@pytest.fixture
def temporada_con_coleccion(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    temporada = api.post(
        TEMPORADAS,
        headers=cabeceras_admin,
        json={
            "nombre": "Verano 2026",
            "fecha_inicio": "2026-12-01",
            "fecha_fin": "2027-02-28",
            "activa": True,
        },
    )
    assert temporada.status_code == 201, temporada.text
    temporada_id = temporada.json()["id"]

    coleccion = api.post(
        COLECCIONES,
        headers=cabeceras_admin,
        json={"temporada_id": temporada_id, "nombre": "Playa", "activa": True},
    )
    assert coleccion.status_code == 201, coleccion.text
    return {"temporada": temporada_id, "coleccion": coleccion.json()["id"]}


def test_corregir_solo_el_nombre_no_borra_la_temporada_ni_la_coleccion(
    api: TestClient, dos_proveedores: dict, maestros: dict, temporada_con_coleccion: dict
) -> None:
    """«No enviado» tiene que seguir significando «no lo toques».

    Es la pérdida de datos silenciosa que acecha en toda edición parcial: el
    formulario manda un campo y el servidor vacía otros tres.
    """
    cab = dos_proveedores["uno"]["cab"]
    producto = _registrar(
        api,
        cab,
        maestros,
        "TXU-020",
        temporada_id=temporada_con_coleccion["temporada"],
        coleccion_id=temporada_con_coleccion["coleccion"],
    ).json()
    assert producto["temporada_id"] == temporada_con_coleccion["temporada"]

    editado = api.patch(f"{MIS}/{producto['id']}", headers=cab, json={"nombre": "Otro nombre"})
    assert editado.status_code == 200, editado.text
    assert editado.json()["nombre"] == "Otro nombre"
    assert editado.json()["temporada_id"] == temporada_con_coleccion["temporada"]
    assert editado.json()["coleccion_id"] == temporada_con_coleccion["coleccion"]


def test_mandar_la_coleccion_en_null_si_saca_el_producto_de_ella(
    api: TestClient, dos_proveedores: dict, maestros: dict, temporada_con_coleccion: dict
) -> None:
    """La otra mitad: enviar `null` es distinto de no enviar.

    Sacar un producto de una colección es una operación legítima, y la única
    forma de pedirla es mandando el campo en null.
    """
    cab = dos_proveedores["uno"]["cab"]
    producto = _registrar(
        api,
        cab,
        maestros,
        "TXU-021",
        temporada_id=temporada_con_coleccion["temporada"],
        coleccion_id=temporada_con_coleccion["coleccion"],
    ).json()

    editado = api.patch(f"{MIS}/{producto['id']}", headers=cab, json={"coleccion_id": None})
    assert editado.status_code == 200, editado.text
    assert editado.json()["coleccion_id"] is None
    # La temporada NO se va con ella: no se envió.
    assert editado.json()["temporada_id"] == temporada_con_coleccion["temporada"]


def test_una_coleccion_ajena_a_la_temporada_da_422(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    dos_proveedores: dict,
    maestros: dict,
    temporada_con_coleccion: dict,
) -> None:
    """Excepción E2, heredada de CU-10."""
    otra = api.post(
        TEMPORADAS,
        headers=cabeceras_admin,
        json={
            "nombre": "Invierno 2026",
            "fecha_inicio": "2026-06-01",
            "fecha_fin": "2026-08-31",
            "activa": True,
        },
    )
    assert otra.status_code == 201, otra.text

    alta = _registrar(
        api,
        dos_proveedores["uno"]["cab"],
        maestros,
        "TXU-022",
        temporada_id=otra.json()["id"],
        coleccion_id=temporada_con_coleccion["coleccion"],
    )
    assert alta.status_code == 422
    assert "colección" in alta.json()["detail"].lower()
