"""CU-16 · Gestionar disponibilidad de la sucursal.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-16-gestionar-disponibilidad-de-la-sucursal.md).

CU-16 es el caso de uso del **Encargado** sobre su propio local: consultar sus
existencias, corregirlas por conteo físico y saber qué tiene que reponer. La
mitad del ajuste la comparte con CU-15 —es el mismo endpoint— y lo que las
separa es el ámbito, que viaja en el token.

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **El ámbito, en las dos direcciones.** Que el Encargado pueda ajustar lo suyo
  y que no pueda tocar lo ajeno son dos afirmaciones distintas, y las dos tienen
  que ser ciertas. La segunda además tiene que fallar **antes** de escribir.
- **La alerta se compara contra el disponible, no contra el físico.** Lo
  reservado ya tiene dueño y no sirve para atender al próximo cliente que entre,
  que es justo lo que la alerta quiere evitar.
- **Umbral cero es «sin alerta».** Si no, cada existencia creada por un ingreso
  empezaría a avisar sola con un número que nadie eligió.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.inventario.models import Existencia

ALERTAS = "/api/v1/inventario/alertas"
EXISTENCIAS = "/api/v1/inventario/existencias"
AJUSTE = "/api/v1/inventario/movimientos/ajuste"
INGRESOS = "/api/v1/inventario/ingresos"
MOVIMIENTOS = "/api/v1/inventario/movimientos"

SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EMPLEADOS = "/api/v1/organizacion/empleados"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"


def _minimo(existencia_id: int) -> str:
    return f"{EXISTENCIAS}/{existencia_id}/stock-minimo"


# --- Ayudantes -----------------------------------------------------------

def _crear_sucursal(api: TestClient, admin: dict[str, str], *, nombre: str) -> int:
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
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_variantes(api: TestClient, admin: dict[str, str], cuantas: int = 3) -> list[int]:
    """Un producto con `cuantas` variantes, una por talla."""
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Camisas", "orden": 0, "activa": True}
    )
    producto = api.post(
        PRODUCTOS,
        headers=admin,
        json={
            "codigo": "CAM-001",
            "nombre": "Camisa Oxford manga larga",
            "categoria_id": categoria.json()["id"],
            "precio_base": "250.00",
            "activo": True,
        },
    )
    tallas = []
    for indice, codigo in enumerate(("S", "M", "L", "XL", "XXL")[:cuantas]):
        t = api.post(
            TALLAS,
            headers=admin,
            json={"tipo_prenda": "Superior", "codigo": codigo, "orden": indice, "activa": True},
        )
        assert t.status_code == 201, t.text
        tallas.append(t.json()["id"])

    color = api.post(
        COLORES,
        headers=admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    )
    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=admin,
        json={"tallas": tallas, "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text
    return [v["id"] for v in generadas.json()["variantes"]]


def _proveedor(api: TestClient, admin: dict[str, str]) -> int:
    """El proveedor de las pruebas. Idempotente a proposito.

    Varias pruebas hacen dos ingresos y llamarian dos veces a este ayudante; el
    UNIQUE sobre la identificacion tributaria haria fallar al segundo. Se
    reutiliza el que ya existe en vez de inventar un NIT distinto por llamada,
    que escondria el dia que de verdad se quiera probar el duplicado.
    """
    r = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Textiles del Sur SRL",
            "identificacion_tributaria": "1023456789",
            "activo": True,
        },
    )
    if r.status_code == 409:
        return api.get(PROVEEDORES, headers=admin).json()[0]["id"]
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _ingresar(
    api: TestClient,
    admin: dict[str, str],
    *,
    sucursal_id: int,
    proveedor_id: int,
    lineas: list[tuple[int, int]],
) -> None:
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": "REM-SEED",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


def _existencias(api: TestClient, cabeceras: dict[str, str], **params) -> list[dict]:
    r = api.get(EXISTENCIAS, headers=cabeceras, params=params)
    assert r.status_code == 200, r.text
    return r.json()


# --- Fixtures ------------------------------------------------------------

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict[str, str]) -> list[int]:
    return _crear_variantes(api, cabeceras_admin)


@pytest.fixture
def cabeceras_encargado(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int):
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
    entrada = api.post("/api/v1/auth/login", json={"correo": correo, "contrasena": clave})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


@pytest.fixture
def con_stock(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variantes: list[int]
) -> list[dict]:
    """Tres prendas en la sucursal, con 10, 4 y 1 unidades."""
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=_proveedor(api, cabeceras_admin),
        lineas=[(variantes[0], 10), (variantes[1], 4), (variantes[2], 1)],
    )
    return _existencias(api, cabeceras_admin, sucursal_id=sucursal)


# --- Autorizacion y ambito ----------------------------------------------

def test_sin_token_no_se_consultan_las_alertas(api: TestClient) -> None:
    assert api.get(ALERTAS).status_code == 401


def test_un_cliente_no_entra_a_la_disponibilidad(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.get(ALERTAS, headers=cabeceras_cliente).status_code == 403


def test_el_encargado_ajusta_su_propia_sucursal(
    api: TestClient,
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: list[dict],
) -> None:
    """Flujo principal de CU-16.

    Es la mitad del ajuste que el 10/09 quedó fuera por leer solo la fila de
    CU-15: el Encargado sí corrige el saldo de su local.
    """
    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_encargado,
        json={
            "variante_id": variantes[0],
            "sucursal_id": sucursal,
            "cantidad_contada": 8,
            "motivo": "Conteo físico del lunes",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["diferencia"] == -2
    assert respuesta.json()["existencia"]["cantidad_disponible"] == 8

    # Y queda a su nombre en el historial: es la trazabilidad del RF28.
    fila = api.get(
        MOVIMIENTOS, headers=cabeceras_encargado, params={"tipo": "AJUSTE"}
    ).json()["items"][0]
    assert fila["usuario"] == "Luz Vargas"


def test_el_encargado_no_ajusta_la_sucursal_ajena(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    variantes: list[int],
) -> None:
    """Y el rechazo es antes de escribir, no después.

    El ámbito viaja en el token; cambiar el número del JSON no alcanza.
    """
    ajena = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=ajena,
        proveedor_id=_proveedor(api, cabeceras_admin),
        lineas=[(variantes[0], 10)],
    )

    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_encargado,
        json={
            "variante_id": variantes[0],
            "sucursal_id": ajena,
            "cantidad_contada": 999,
            "motivo": "Conteo físico del lunes",
        },
    )
    assert respuesta.status_code == 403

    saldo = _existencias(api, cabeceras_admin, sucursal_id=ajena)
    assert saldo[0]["cantidad_disponible"] == 10, "el ajuste rechazado igual escribió"


def test_el_encargado_no_toca_el_umbral_de_otra_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    variantes: list[int],
) -> None:
    """Sin resolver de qué sucursal es la existencia, bastaría probar números.

    Es la razón por la que el router busca la existencia antes de comprobar el
    ámbito: el identificador de la URL no dice a qué local pertenece.
    """
    ajena = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=ajena,
        proveedor_id=_proveedor(api, cabeceras_admin),
        lineas=[(variantes[0], 10)],
    )
    existencia = _existencias(api, cabeceras_admin, sucursal_id=ajena)[0]

    respuesta = api.patch(
        _minimo(existencia["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": 50},
    )
    assert respuesta.status_code == 403

    sigue = _existencias(api, cabeceras_admin, sucursal_id=ajena)[0]
    assert sigue["stock_minimo"] == 0


# --- Umbral de reposicion ------------------------------------------------

def test_una_existencia_nace_sin_umbral_y_sin_alerta(
    api: TestClient, cabeceras_admin: dict[str, str], con_stock: list[dict]
) -> None:
    """Cero significa «sin alerta», y es el valor por defecto a propósito.

    Si no lo fuera, cada existencia creada por un ingreso empezaría a avisar
    sola con un número que nadie eligió.
    """
    assert all(e["stock_minimo"] == 0 for e in con_stock)
    assert all(e["bajo_minimo"] is False for e in con_stock)
    assert api.get(ALERTAS, headers=cabeceras_admin).json() == []


def test_fijar_el_umbral_enciende_la_alerta(
    api: TestClient,
    cabeceras_encargado: dict[str, str],
    con_stock: list[dict],
) -> None:
    """Paso 4: el Encargado dice cuándo esa prenda tiene que avisar."""
    # La que tiene 4 unidades, con umbral 6: queda en alerta.
    cuatro = next(e for e in con_stock if e["cantidad_disponible"] == 4)

    respuesta = api.patch(
        _minimo(cuatro["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": 6},
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["stock_minimo"] == 6
    assert respuesta.json()["bajo_minimo"] is True

    alertas = api.get(ALERTAS, headers=cabeceras_encargado).json()
    assert len(alertas) == 1
    assert alertas[0]["existencia_id"] == cuatro["existencia_id"]


def test_el_umbral_no_genera_movimiento(
    api: TestClient,
    cabeceras_encargado: dict[str, str],
    con_stock: list[dict],
) -> None:
    """Es la única escritura del paquete que no deja movimiento, y está bien.

    Lo que no se toca sin movimiento es una *cantidad de mercadería*; el umbral
    no lo es. Si generara uno, el historial se llenaría de filas que no cambian
    ningún saldo y `cantidad <> 0` las rechazaría de todos modos.
    """
    antes = api.get(MOVIMIENTOS, headers=cabeceras_encargado).json()["total"]

    api.patch(
        _minimo(con_stock[0]["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": 99},
    )

    despues = api.get(MOVIMIENTOS, headers=cabeceras_encargado).json()["total"]
    assert despues == antes
    # Y el saldo no se movió.
    assert _existencias(api, cabeceras_encargado)[0]["cantidad_disponible"] == \
        con_stock[0]["cantidad_disponible"]


def test_el_umbral_en_cero_apaga_la_alerta(
    api: TestClient, cabeceras_encargado: dict[str, str], con_stock: list[dict]
) -> None:
    """Flujo alternativo: la prenda deja de vigilarse."""
    existencia = con_stock[0]["existencia_id"]
    api.patch(_minimo(existencia), headers=cabeceras_encargado, json={"stock_minimo": 99})
    assert len(api.get(ALERTAS, headers=cabeceras_encargado).json()) == 1

    api.patch(_minimo(existencia), headers=cabeceras_encargado, json={"stock_minimo": 0})
    assert api.get(ALERTAS, headers=cabeceras_encargado).json() == []


def test_un_umbral_negativo_no_se_acepta(
    api: TestClient, cabeceras_encargado: dict[str, str], con_stock: list[dict]
) -> None:
    respuesta = api.patch(
        _minimo(con_stock[0]["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": -1},
    )
    assert respuesta.status_code == 422


def test_el_umbral_de_una_existencia_inexistente_da_404(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    respuesta = api.patch(
        _minimo(999_999), headers=cabeceras_admin, json={"stock_minimo": 5}
    )
    assert respuesta.status_code == 404


# --- La regla de la alerta ----------------------------------------------

def test_estar_justo_en_el_minimo_ya_es_alerta(
    api: TestClient, cabeceras_encargado: dict[str, str], con_stock: list[dict]
) -> None:
    """Se compara con `<=` y no con `<`: ese es el sentido de «mínimo»."""
    cuatro = next(e for e in con_stock if e["cantidad_disponible"] == 4)
    respuesta = api.patch(
        _minimo(cuatro["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": 4},
    )
    assert respuesta.json()["bajo_minimo"] is True


def test_la_alerta_mira_el_disponible_y_no_el_fisico(
    api: TestClient,
    cabeceras_encargado: dict[str, str],
    db,
    con_stock: list[dict],
) -> None:
    """La prueba más importante de este caso de uso.

    Con 10 unidades de las que 8 están reservadas, quedan 2 para vender. El
    físico sigue diciendo 10, pero esas 8 ya tienen dueño y no sirven para
    atender al próximo cliente que entre — que es exactamente lo que la alerta
    quiere evitar. Con umbral 5, tiene que avisar.
    """
    diez = next(e for e in con_stock if e["cantidad_disponible"] == 10)

    # CU-22 todavía no existe, así que las reservas se simulan sobre la fila.
    existencia = db.scalar(
        select(Existencia).where(Existencia.id == diez["existencia_id"])
    )
    existencia.cantidad_disponible = 2
    existencia.cantidad_reservada = 8
    db.commit()

    respuesta = api.patch(
        _minimo(diez["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": 5},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["cantidad_fisica"] == 10, "el físico no cambió"
    assert cuerpo["bajo_minimo"] is True, "10 físicas taparon un disponible de 2"


def test_las_alertas_salen_de_la_mas_urgente_a_la_menos(
    api: TestClient, cabeceras_encargado: dict[str, str], con_stock: list[dict]
) -> None:
    """Quien abre esto a primera hora necesita ver arriba lo que pide hoy.

    Se ordena por la distancia al umbral y no por la cantidad: una prenda en
    cero con mínimo diez urge más que una en nueve con el mismo mínimo, aunque
    las dos estén en alerta.
    """
    por_cantidad = {e["cantidad_disponible"]: e["existencia_id"] for e in con_stock}
    # Las tres en alerta, con distancias -9, -1 y 0 respecto de su umbral.
    for cantidad, umbral in ((1, 10), (4, 5), (10, 10)):
        api.patch(
            _minimo(por_cantidad[cantidad]),
            headers=cabeceras_encargado,
            json={"stock_minimo": umbral},
        )

    alertas = api.get(ALERTAS, headers=cabeceras_encargado).json()
    assert len(alertas) == 3
    distancias = [a["cantidad_disponible"] - a["stock_minimo"] for a in alertas]
    assert distancias == sorted(distancias), f"sin ordenar por urgencia: {distancias}"
    assert distancias[0] == -9


def test_el_encargado_solo_ve_las_alertas_de_su_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: list[dict],
) -> None:
    """Aunque pida explícitamente otra: en una lectura se acota, no se rechaza."""
    ajena = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=ajena,
        proveedor_id=_proveedor(api, cabeceras_admin),
        lineas=[(variantes[0], 2)],
    )
    de_la_ajena = _existencias(api, cabeceras_admin, sucursal_id=ajena)[0]

    api.patch(
        _minimo(de_la_ajena["existencia_id"]),
        headers=cabeceras_admin,
        json={"stock_minimo": 20},
    )
    api.patch(
        _minimo(con_stock[0]["existencia_id"]),
        headers=cabeceras_encargado,
        json={"stock_minimo": 20},
    )

    propias = api.get(ALERTAS, headers=cabeceras_encargado).json()
    assert len(propias) == 1
    assert propias[0]["sucursal_id"] == sucursal

    # El Administrador ve las dos: su ámbito es toda la red.
    assert len(api.get(ALERTAS, headers=cabeceras_admin).json()) == 2


def test_reponer_por_un_ingreso_apaga_la_alerta(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: list[dict],
) -> None:
    """El ciclo completo: avisa, se repone, deja de avisar.

    Es lo que confirma que la alerta se calcula contra el saldo actual y no se
    guarda como un estado que alguien tenga que acordarse de apagar.
    """
    uno = next(e for e in con_stock if e["cantidad_disponible"] == 1)
    api.patch(
        _minimo(uno["existencia_id"]), headers=cabeceras_encargado, json={"stock_minimo": 5}
    )
    assert len(api.get(ALERTAS, headers=cabeceras_encargado).json()) == 1

    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        proveedor_id=_proveedor(api, cabeceras_admin),
        lineas=[(uno["variante_id"], 20)],
    )

    assert api.get(ALERTAS, headers=cabeceras_encargado).json() == []
