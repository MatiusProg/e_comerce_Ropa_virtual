"""CU-13 · Registrar ingreso de mercadería.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-13-registrar-ingreso-de-mercaderia.md).

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **La transacción es todo o nada (E9).** Un remito de tres líneas con la
  tercera inválida no puede dejar las dos primeras cargadas. Ninguna
  restricción de PostgreSQL lo impide: lo sostiene que el servicio haga un solo
  `commit` al final.
- **El saldo es la suma de sus movimientos (D4).** Es la afirmación sobre la que
  se apoya todo el paquete, y acá se comprueba literalmente: se registran tres
  ingresos y se verifica que el disponible coincida con la suma del historial.
- **El ámbito del Encargado.** Su sucursal viaja en el token, no en el cuerpo;
  mandar otra en el JSON tiene que dar 403 y no cargar nada.
- **El ingreso se reconstruye desde sus movimientos.** No hay tabla `ingreso`:
  el historial agrupa por instante de transacción, y esa agrupación tiene que
  separar dos ingresos distintos y unir las líneas de uno solo.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

INGRESOS = "/api/v1/inventario/ingresos"
EXISTENCIAS = "/api/v1/inventario/existencias"
MOVIMIENTOS = "/api/v1/inventario/movimientos"

SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EMPLEADOS = "/api/v1/organizacion/empleados"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
VARIANTES = "/api/v1/catalogo/variantes"


# --- Ayudantes -----------------------------------------------------------

def _crear_sucursal(
    api: TestClient, admin: dict[str, str], *, nombre: str, activa: bool = True
) -> int:
    ciudad_id = api.get(CIUDADES, headers=admin).json()[0]["id"]
    r = api.post(
        SUCURSALES,
        headers=admin,
        json={
            "ciudad_id": ciudad_id,
            "nombre": nombre,
            "direccion": f"Avenida {nombre} 100",
            "telefono": None,
            "horario_apertura": "09:00:00",
            "horario_cierre": "20:00:00",
            "capacidad_vestidores": 4,
            "activa": activa,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_proveedor(
    api: TestClient,
    admin: dict[str, str],
    *,
    razon_social: str = "Textiles del Sur SRL",
    nit: str = "1023456789",
    activo: bool = True,
) -> int:
    r = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": razon_social,
            "identificacion_tributaria": nit,
            "activo": activo,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_variantes(
    api: TestClient, admin: dict[str, str], *, codigo: str = "CAM-001", cuantas: int = 2
) -> list[dict]:
    """Un producto con `cuantas` variantes, que es lo que se puede recibir."""
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": f"Cat {codigo}", "orden": 0, "activa": True}
    )
    assert categoria.status_code == 201, categoria.text

    producto = api.post(
        PRODUCTOS,
        headers=admin,
        json={
            "codigo": codigo,
            "nombre": "Camisa Oxford manga larga",
            "categoria_id": categoria.json()["id"],
            "precio_base": "250.00",
            "activo": True,
        },
    )
    assert producto.status_code == 201, producto.text

    tallas = []
    for indice in range(cuantas):
        t = api.post(
            TALLAS,
            headers=admin,
            json={
                "tipo_prenda": "Superior",
                "codigo": f"T{indice}{codigo[-1]}",
                "orden": indice,
                "activa": True,
            },
        )
        assert t.status_code == 201, t.text
        tallas.append(t.json()["id"])

    color = api.post(
        COLORES,
        headers=admin,
        json={"nombre": f"Negro {codigo}", "hexadecimal": "#101010", "activo": True},
    )
    assert color.status_code == 201, color.text

    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=admin,
        json={"tallas": tallas, "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text
    return generadas.json()["variantes"]


def _ingreso(
    api: TestClient,
    cabeceras: dict[str, str],
    *,
    sucursal_id: int,
    proveedor_id: int,
    lineas: list[dict],
    referencia: str | None = "REM-0001",
    observacion: str | None = None,
):
    return api.post(
        INGRESOS,
        headers=cabeceras,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": referencia,
            "observacion": observacion,
            "lineas": lineas,
        },
    )


# --- Fixtures ------------------------------------------------------------

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def proveedor(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_proveedor(api, cabeceras_admin)


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict[str, str]) -> list[dict]:
    return _crear_variantes(api, cabeceras_admin)


@pytest.fixture
def cabeceras_encargado(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int):
    """Un Encargado de `sucursal`, con su token ya resuelto.

    Se crea por CU-06 y no a mano: el vínculo cargo → rol → ámbito de sucursal
    es justo lo que esta prueba necesita que sea real.
    """
    correo = "encargado.centro@violetboutique.bo"
    clave = "Encargado12"
    alta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "nombres": "Luz",
            "apellidos": "Vargas",
            "correo": correo,
            "contrasena": clave,
            "documento": "5544332",
            "telefono": "70000000",
            "cargo": "ENCARGADO",
            "sucursal_id": sucursal,
            "fecha_ingreso": (date.today() - timedelta(days=30)).isoformat(),
        },
    )
    assert alta.status_code == 201, alta.text

    entrada = api.post(
        "/api/v1/auth/login", json={"correo": correo, "contrasena": clave}
    )
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_registra_un_ingreso(api: TestClient) -> None:
    assert api.post(INGRESOS, json={}).status_code == 401


def test_un_cliente_no_entra_al_inventario(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El inventario es de Administrador y Encargado; el Cliente ve la vitrina."""
    assert api.get(INGRESOS, headers=cabeceras_cliente).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_el_ingreso_sube_el_saldo_y_deja_el_movimiento(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """Pasos 4 a 7. El saldo sube y queda la fila que lo explica."""
    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[
            {"variante_id": variantes[0]["id"], "cantidad": 10},
            {"variante_id": variantes[1]["id"], "cantidad": 4},
        ],
        observacion="Llegó completo",
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["unidades"] == 14
    assert len(cuerpo["lineas"]) == 2
    assert cuerpo["referencia"] == "REM-0001"
    # La prenda se nombra, no se numera: el depósito no lee identificadores.
    assert cuerpo["lineas"][0]["sku"] == variantes[0]["sku"]
    assert cuerpo["lineas"][0]["producto"] == "Camisa Oxford manga larga"
    assert cuerpo["lineas"][0]["disponible_resultante"] == 10

    saldos = api.get(
        EXISTENCIAS, headers=cabeceras_admin, params={"sucursal_id": sucursal}
    )
    assert saldos.status_code == 200, saldos.text
    por_variante = {s["variante_id"]: s for s in saldos.json()}
    assert por_variante[variantes[0]["id"]]["cantidad_disponible"] == 10
    assert por_variante[variantes[1]["id"]]["cantidad_disponible"] == 4
    # Un ingreso no reserva nada.
    assert por_variante[variantes[0]["id"]]["cantidad_reservada"] == 0

    movimientos = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "INGRESO"}
    ).json()
    assert movimientos["total"] == 2
    primero = movimientos["items"][0]
    assert primero["tipo"] == "INGRESO"
    assert primero["proveedor"] == "Textiles del Sur SRL"
    assert primero["usuario"] == "Root Pruebas"
    assert "Llegó completo" in primero["motivo"]


def test_un_segundo_ingreso_suma_sobre_el_saldo_anterior(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """La existencia se crea una sola vez; el segundo ingreso la actualiza.

    Sin el UNIQUE (variante, sucursal) esto crearía dos saldos paralelos de la
    misma prenda y la vitrina mostraría cualquiera de los dos.
    """
    for cantidad in (10, 5, 3):
        respuesta = _ingreso(
            api,
            cabeceras_admin,
            sucursal_id=sucursal,
            proveedor_id=proveedor,
            lineas=[{"variante_id": variantes[0]["id"], "cantidad": cantidad}],
        )
        assert respuesta.status_code == 201, respuesta.text

    saldos = api.get(
        EXISTENCIAS,
        headers=cabeceras_admin,
        params={"sucursal_id": sucursal, "solo_con_saldo": True},
    ).json()
    assert len(saldos) == 1
    assert saldos[0]["cantidad_disponible"] == 18


def test_el_saldo_es_la_suma_de_sus_movimientos(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """La decisión D4, comprobada literalmente.

    Es la afirmación sobre la que se apoya todo P4: la existencia está
    desnormalizada por rendimiento, y esta prueba es lo que garantiza que la
    desnormalización no se despegue del historial.
    """
    for cantidad in (7, 11, 2):
        _ingreso(
            api,
            cabeceras_admin,
            sucursal_id=sucursal,
            proveedor_id=proveedor,
            lineas=[{"variante_id": variantes[0]["id"], "cantidad": cantidad}],
        )

    historial = api.get(
        MOVIMIENTOS,
        headers=cabeceras_admin,
        params={"variante_id": variantes[0]["id"], "tamano": 100},
    ).json()
    suma = sum(m["cantidad"] for m in historial["items"])

    saldo = api.get(
        EXISTENCIAS, headers=cabeceras_admin, params={"sucursal_id": sucursal}
    ).json()
    disponible = next(
        s["cantidad_disponible"]
        for s in saldo
        if s["variante_id"] == variantes[0]["id"]
    )
    assert suma == disponible == 20


# --- Historial (paso 2) --------------------------------------------------

def test_las_lineas_de_un_ingreso_se_agrupan_en_una_sola_fila(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """No hay tabla `ingreso`: el historial lo reconstruye desde sus líneas.

    Dos ingresos son dos transacciones y llevan dos marcas de tiempo distintas,
    así que tienen que quedar en dos filas —y las dos líneas del primero, en una
    sola—.
    """
    _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[
            {"variante_id": variantes[0]["id"], "cantidad": 6},
            {"variante_id": variantes[1]["id"], "cantidad": 4},
        ],
        referencia="REM-0001",
    )
    _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 1}],
        referencia="REM-0002",
    )

    historial = api.get(INGRESOS, headers=cabeceras_admin).json()
    assert historial["total"] == 2

    # El más reciente primero.
    reciente, anterior = historial["items"]
    assert reciente["referencia"] == "REM-0002"
    assert reciente["lineas"] == 1 and reciente["unidades"] == 1
    assert anterior["referencia"] == "REM-0001"
    assert anterior["lineas"] == 2 and anterior["unidades"] == 10
    assert anterior["proveedor"] == "Textiles del Sur SRL"

    detalle = api.get(
        f"{INGRESOS}/detalle",
        headers=cabeceras_admin,
        params={
            "registrado_en": anterior["registrado_en"],
            "sucursal_id": sucursal,
            "referencia": "REM-0001",
        },
    )
    assert detalle.status_code == 200, detalle.text
    assert {linea["cantidad"] for linea in detalle.json()} == {6, 4}


# --- Ambito de sucursal --------------------------------------------------

def test_el_encargado_registra_el_ingreso_de_su_sucursal(
    api: TestClient,
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """CU-13 es del Administrador y del Encargado: es quien recibe las cajas."""
    respuesta = _ingreso(
        api,
        cabeceras_encargado,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 3}],
    )
    assert respuesta.status_code == 201, respuesta.text


def test_el_encargado_no_carga_mercaderia_en_otra_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    proveedor: int,
    variantes: list[dict],
) -> None:
    """El ámbito viaja en el token, no en el cuerpo de la petición.

    Sin esta comprobación, el Encargado tendría rol suficiente y podría cargar
    stock en un local que no es el suyo con solo cambiar un número del JSON.
    """
    ajena = _crear_sucursal(api, cabeceras_admin, nombre="Norte")

    respuesta = _ingreso(
        api,
        cabeceras_encargado,
        sucursal_id=ajena,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 3}],
    )
    assert respuesta.status_code == 403

    # Y no cargó nada: el rechazo es antes de tocar la base.
    saldos = api.get(
        EXISTENCIAS, headers=cabeceras_admin, params={"sucursal_id": ajena}
    ).json()
    assert saldos == []


def test_el_encargado_solo_ve_los_ingresos_de_su_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """Aunque pida explícitamente otra, ve la suya: no se le devuelve un 403 en
    una lectura, se le acota el alcance."""
    ajena = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=ajena,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 9}],
    )
    _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 2}],
    )

    propios = api.get(INGRESOS, headers=cabeceras_encargado).json()
    assert propios["total"] == 1
    assert propios["items"][0]["sucursal_id"] == sucursal

    # El Administrador sí ve los dos.
    todos = api.get(INGRESOS, headers=cabeceras_admin).json()
    assert todos["total"] == 2


# --- Excepciones ---------------------------------------------------------

def test_excepcion_e1_una_prenda_inexistente_frena_el_ingreso(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[
            {"variante_id": variantes[0]["id"], "cantidad": 5},
            {"variante_id": 999_999, "cantidad": 1},
        ],
    )
    assert respuesta.status_code == 422
    # La interfaz necesita saber CUÁL línea señalar.
    assert respuesta.json()["detail"]["variantes"] == [999_999]


def test_excepcion_e9_si_una_linea_falla_no_queda_cargada_ninguna(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """El remito es una transacción: todo o nada.

    Es lo que evita que el depósito tenga que averiguar por dónde iba un
    ingreso que se cortó a la mitad.
    """
    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[
            {"variante_id": variantes[0]["id"], "cantidad": 5},
            {"variante_id": variantes[1]["id"], "cantidad": 5},
            {"variante_id": 999_999, "cantidad": 1},
        ],
    )
    assert respuesta.status_code == 422

    saldos = api.get(
        EXISTENCIAS, headers=cabeceras_admin, params={"sucursal_id": sucursal}
    ).json()
    assert saldos == [], "quedaron líneas del ingreso que falló"


def test_excepcion_e1_una_prenda_desactivada_no_se_recibe(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """Flujo 7c de CU-10: la variante existe pero dejó de ofrecerse."""
    baja = api.patch(
        f"{VARIANTES}/{variantes[0]['id']}", headers=cabeceras_admin, json={"activa": False}
    )
    assert baja.status_code == 200, baja.text

    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 5}],
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["variantes"] == [variantes[0]["id"]]


def test_excepcion_e2_no_entra_mercaderia_a_una_sucursal_dada_de_baja(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    proveedor: int,
    variantes: list[dict],
) -> None:
    cerrada = _crear_sucursal(api, cabeceras_admin, nombre="Cerrada", activa=False)
    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=cerrada,
        proveedor_id=proveedor,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 5}],
    )
    assert respuesta.status_code == 422
    assert "baja" in respuesta.json()["detail"]


def test_excepcion_e3_un_proveedor_dado_de_baja_no_envia_mercaderia(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    variantes: list[dict],
) -> None:
    inactivo = _crear_proveedor(
        api,
        cabeceras_admin,
        razon_social="Confecciones Cerradas SA",
        nit="9988776655",
        activo=False,
    )
    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=inactivo,
        lineas=[{"variante_id": variantes[0]["id"], "cantidad": 5}],
    )
    assert respuesta.status_code == 422


def test_excepcion_e4_la_misma_prenda_no_puede_venir_en_dos_lineas(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    """Se rechaza en vez de sumar: dos líneas iguales casi siempre son la misma
    caja contada dos veces, y sumarlas guardaría el error como si fuera dato."""
    respuesta = _ingreso(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=proveedor,
        lineas=[
            {"variante_id": variantes[0]["id"], "cantidad": 5},
            {"variante_id": variantes[0]["id"], "cantidad": 3},
        ],
    )
    assert respuesta.status_code == 422


def test_un_ingreso_sin_lineas_no_es_un_ingreso(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, proveedor: int
) -> None:
    respuesta = _ingreso(
        api, cabeceras_admin, sucursal_id=sucursal, proveedor_id=proveedor, lineas=[]
    )
    assert respuesta.status_code == 422


def test_no_se_reciben_cantidades_de_cero_o_negativas(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    proveedor: int,
    variantes: list[dict],
) -> None:
    for cantidad in (0, -3):
        respuesta = _ingreso(
            api,
            cabeceras_admin,
            sucursal_id=sucursal,
            proveedor_id=proveedor,
            lineas=[{"variante_id": variantes[0]["id"], "cantidad": cantidad}],
        )
        assert respuesta.status_code == 422, f"cantidad {cantidad} fue aceptada"
