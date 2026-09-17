"""CU-36 · Consultar tablero de indicadores.

Es el primer caso de uso de P11, y P11 es el unico paquete del sistema que solo
lee. Eso cambia que es lo que hay que probar: no hay invariante de saldo que
sostener ni transaccion que pueda quedar a medias. Lo que puede salir mal en un
tablero es **decir un numero equivocado con total aplomo**, y esas son las
pruebas que valen:

- **El borde del periodo.** «Hasta el 15» tiene que incluir el 15 entero. Es el
  error que no se nota nunca ---el tablero se ve bien--- hasta que alguien
  consulta un solo dia y lo ve vacio.
- **Sin datos no es cero por ciento.** Una tasa sin denominador viaja en nulo.
  Devolver 0.0 pintaria el tablero en rojo el dia que se estrena el sistema, que
  es exactamente el dia de la defensa.
- **Que entra y que no entra en cada cuenta.** Una reserva cancelada no es una
  prenda que interese, y una reserva abierta no es una que fracaso. Las dos
  cosas se prueban porque las dos son decisiones, no consecuencias del esquema.
- **El bloque de ventas viaja aunque no haya ventas.** Es el contrato que le
  permite a la pantalla no cambiar cuando aterrice la `0006`.

Lo que NO se prueba aca es la regla de stock critico: es de P4, la prueba de
CU-16 ya la cubre, y el tablero la consume por la costura justamente para no
tener una segunda definicion que mantener. Lo que si se comprueba es que el
tablero la pida y no la reimplemente ---la prueba mueve el umbral por la API de
CU-16 y espera que el tablero lo note---.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.modules.reportes.tablero_service import ESTADOS_ABIERTOS, ESTADOS_CERRADOS
from app.modules.reservas.models import ESTADOS_RESERVA

TABLERO = "/api/v1/reportes/tablero"
RESERVAS = "/api/v1/reservas"
PANEL = "/api/v1/sucursal/reservas"
INGRESOS = "/api/v1/inventario/ingresos"
EXISTENCIAS = "/api/v1/inventario/existencias"

SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EMPLEADOS = "/api/v1/organizacion/empleados"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"

BOLIVIA = timezone(timedelta(hours=-4))


def _manana(hora: int) -> datetime:
    dia = datetime.now(BOLIVIA) + timedelta(days=1)
    return dia.replace(hour=hora, minute=0, second=0, microsecond=0)


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


def _crear_variantes(api: TestClient, admin: dict[str, str]) -> list[int]:
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Blusas", "orden": 0, "activa": True}
    )
    producto = api.post(
        PRODUCTOS,
        headers=admin,
        json={
            "codigo": "BLU-001",
            "nombre": "Blusa de seda",
            "categoria_id": categoria.json()["id"],
            "precio_base": "320.00",
            "activo": True,
        },
    )
    tallas = []
    for indice, codigo in enumerate(("S", "M")):
        t = api.post(
            TALLAS,
            headers=admin,
            json={"tipo_prenda": "Superior", "codigo": codigo, "orden": indice, "activa": True},
        )
        tallas.append(t.json()["id"])
    color = api.post(
        COLORES,
        headers=admin,
        json={"nombre": "Marfil", "hexadecimal": "#F5F0E6", "activo": True},
    )
    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=admin,
        json={"tallas": tallas, "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text
    return [v["id"] for v in generadas.json()["variantes"]]


def _ingresar(
    api: TestClient, admin: dict[str, str], *, sucursal_id: int, lineas: list[tuple[int, int]]
) -> None:
    proveedor = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Sedas Andinas SRL",
            "identificacion_tributaria": "1098765432",
            "activo": True,
        },
    )
    proveedor_id = (
        api.get(PROVEEDORES, headers=admin).json()[0]["id"]
        if proveedor.status_code == 409
        else proveedor.json()["id"]
    )
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": "REM-CU36",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


def _reservar(
    api: TestClient, cliente: dict[str, str], *, sucursal_id: int, lineas: list[tuple[int, int]]
) -> dict:
    r = api.post(
        RESERVAS,
        headers=cliente,
        json={
            "sucursal_id": sucursal_id,
            "franja_inicio": _manana(15).isoformat(),
            "franja_fin": _manana(16).isoformat(),
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def _tablero(api: TestClient, admin: dict[str, str], **params) -> dict:
    r = api.get(TABLERO, headers=admin, params=params)
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
def stock(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variantes: list[int]):
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 20), (variantes[1], 12)],
    )


@pytest.fixture
def cabeceras_encargado(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int):
    correo = "encargada.centro@violetboutique.bo"
    clave = "Encargada12"
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
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


# =====================================================================
# Autorizacion
# =====================================================================

def test_sin_token_no_hay_tablero(api: TestClient) -> None:
    assert api.get(TABLERO).status_code == 401


def test_el_cliente_no_ve_el_tablero(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.get(TABLERO, headers=cabeceras_cliente).status_code == 403


def test_el_encargado_tampoco(
    api: TestClient, cabeceras_encargado: dict[str, str]
) -> None:
    """Aunque exista el filtro por sucursal.

    Su ambito es su local y lo que necesita ya lo tiene en CU-16 y CU-24. Ver
    la nota del router: darselo seria un router aparte con el `sucursal_id`
    tomado del token, no de la URL.
    """
    assert api.get(TABLERO, headers=cabeceras_encargado).status_code == 403


# =====================================================================
# Sin datos
# =====================================================================

def test_tablero_vacio_no_inventa_ceros_donde_no_hay_dato(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Las cuentas van en cero; las TASAS van en nulo.

    Es la distincion que sostiene toda la pantalla: cero reservas atendidas de
    cero cerradas no es «cero por ciento de conversion».
    """
    cuerpo = _tablero(api, cabeceras_admin)

    assert cuerpo["reservas"]["total"] == 0
    assert cuerpo["reservas"]["abiertas"] == 0
    assert cuerpo["conversion"]["cerradas"] == 0
    assert cuerpo["conversion"]["tasa_atencion"] is None
    assert cuerpo["conversion"]["tasa_prueba"] is None
    assert cuerpo["mas_reservadas"] == []


def test_el_periodo_por_omision_son_treinta_dias_que_terminan_hoy(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    cuerpo = _tablero(api, cabeceras_admin)
    hoy = datetime.now(timezone.utc).date()

    assert cuerpo["periodo"]["hasta"] == hoy.isoformat()
    assert cuerpo["periodo"]["desde"] == (hoy - timedelta(days=29)).isoformat()
    assert cuerpo["periodo"]["sucursal_id"] is None
    assert cuerpo["periodo"]["sucursal"] is None


# =====================================================================
# Reservas y conversion
# =====================================================================

def test_cuenta_las_reservas_por_estado(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 2)])
    segunda = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[1], 1)]
    )
    cancelada = api.patch(
        f"{RESERVAS}/{segunda['id']}/cancelacion",
        headers=cabeceras_cliente,
        json={"observacion": "Ya no puedo ir"},
    )
    assert cancelada.status_code == 200, cancelada.text

    reservas = _tablero(api, cabeceras_admin)["reservas"]

    assert reservas["pendientes"] == 1
    assert reservas["canceladas"] == 1
    assert reservas["preparadas"] == 0
    assert reservas["atendidas"] == 0
    assert reservas["expiradas"] == 0
    assert reservas["total"] == 2
    assert reservas["abiertas"] == 1


def test_una_reserva_preparada_sigue_estando_abierta(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """`abiertas` no es `pendientes`, y por eso se devuelven las dos.

    Una reserva PREPARADA ya tiene las prendas juntas y sigue esperando a que
    el cliente aparezca. Contar solo las PENDIENTE le diria al Administrador
    que no queda nada por atender justo cuando el Encargado termino de trabajar.
    """
    reserva = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 2)]
    )
    r = api.patch(f"{PANEL}/{reserva['id']}/preparacion", headers=cabeceras_encargado)
    assert r.status_code == 200, r.text

    reservas = _tablero(api, cabeceras_admin)["reservas"]

    assert reservas["pendientes"] == 0
    assert reservas["preparadas"] == 1
    assert reservas["abiertas"] == 1


def test_las_dos_tasas_de_conversion(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Una reserva atendida con una prenda llevada y otra no, mas una cancelada.

    Con eso los dos denominadores son distintos y la prueba distingue de verdad:
    la tasa de atencion es 1 de 2 cerradas, y la de prueba es 1 de 2 lineas.
    """
    atendida = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 2), (variantes[1], 1)],
    )
    api.patch(f"{PANEL}/{atendida['id']}/preparacion", headers=cabeceras_encargado)
    cierre = api.patch(
        f"{PANEL}/{atendida['id']}/atencion",
        headers=cabeceras_encargado,
        json={
            "resultados": [
                {"detalle_id": atendida["lineas"][0]["id"], "resultado": "LLEVA"},
                {"detalle_id": atendida["lineas"][1]["id"], "resultado": "NO_LLEVA"},
            ]
        },
    )
    assert cierre.status_code == 200, cierre.text

    otra = _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[1], 1)])
    api.patch(
        f"{RESERVAS}/{otra['id']}/cancelacion",
        headers=cabeceras_cliente,
        json={"observacion": "Me arrepenti"},
    )

    conversion = _tablero(api, cabeceras_admin)["conversion"]

    assert conversion["cerradas"] == 2
    assert conversion["atendidas"] == 1
    assert conversion["tasa_atencion"] == 50.0

    assert conversion["lineas_probadas"] == 2
    assert conversion["lineas_llevadas"] == 1
    assert conversion["tasa_prueba"] == 50.0


def test_una_reserva_abierta_no_hunde_la_tasa(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Todavia no fracaso: solo no termino.

    Sin esto, consultar un dia con reservas para la tarde mostraria la
    conversion desplomandose sola a medida que entran reservas nuevas.
    """
    atendida = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)]
    )
    api.patch(f"{PANEL}/{atendida['id']}/preparacion", headers=cabeceras_encargado)
    api.patch(
        f"{PANEL}/{atendida['id']}/atencion",
        headers=cabeceras_encargado,
        json={
            "resultados": [
                {"detalle_id": atendida["lineas"][0]["id"], "resultado": "LLEVA"}
            ]
        },
    )
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[1], 1)])

    conversion = _tablero(api, cabeceras_admin)["conversion"]

    assert conversion["cerradas"] == 1
    assert conversion["tasa_atencion"] == 100.0


def test_los_estados_abiertos_y_cerrados_cubren_todos_los_de_p6() -> None:
    """Si P6 agrega un estado, esta cuenta queda vieja en silencio.

    Es la unica prueba del archivo que no toca la base: comprueba una relacion
    entre dos constantes. Vale igual, porque el sintoma de que se rompa seria un
    porcentaje levemente equivocado, que nadie mira dos veces.
    """
    assert set(ESTADOS_ABIERTOS) | set(ESTADOS_CERRADOS) == set(ESTADOS_RESERVA)
    assert not set(ESTADOS_ABIERTOS) & set(ESTADOS_CERRADOS)


# =====================================================================
# Ranking de prendas
# =====================================================================

def test_el_ranking_ordena_por_unidades_y_cuenta_reservas_distintas(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 3)])
    _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 2), (variantes[1], 1)],
    )

    ranking = _tablero(api, cabeceras_admin)["mas_reservadas"]

    assert [f["variante_id"] for f in ranking] == [variantes[0], variantes[1]]
    assert ranking[0]["unidades"] == 5
    assert ranking[0]["reservas"] == 2
    assert ranking[1]["unidades"] == 1
    assert ranking[1]["reservas"] == 1
    assert ranking[0]["sku"]
    assert ranking[0]["producto"] == "Blusa de seda"


def test_una_reserva_cancelada_no_entra_en_el_ranking(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Un ranking que las contara seria un ranking de arrepentimientos."""
    viva = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)]
    )
    assert viva["id"]
    anulada = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[1], 9)]
    )
    api.patch(
        f"{RESERVAS}/{anulada['id']}/cancelacion",
        headers=cabeceras_cliente,
        json={"observacion": "No voy"},
    )

    ranking = _tablero(api, cabeceras_admin)["mas_reservadas"]

    assert [f["variante_id"] for f in ranking] == [variantes[0]]


# =====================================================================
# El borde del periodo
# =====================================================================

def test_hasta_incluye_el_dia_entero(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Consultar «hoy a hoy» tiene que ver la reserva que se acaba de hacer.

    Es el error clasico de un rango de fechas: comparar `<=` contra el ultimo
    dia a las 00:00:00 deja afuera todo lo que pase despues de la medianoche,
    o sea todo. No se nota mirando un mes; se nota mirando un dia.
    """
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)])
    hoy = datetime.now(timezone.utc).date().isoformat()

    cuerpo = _tablero(api, cabeceras_admin, desde=hoy, hasta=hoy)

    assert cuerpo["reservas"]["total"] == 1
    assert cuerpo["periodo"]["desde"] == hoy
    assert cuerpo["periodo"]["hasta"] == hoy


def test_un_periodo_viejo_no_ve_lo_de_hoy(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """La otra mitad de la prueba anterior: el filtro filtra de verdad."""
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)])
    viejo = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()

    cuerpo = _tablero(api, cabeceras_admin, desde=viejo, hasta=viejo)

    assert cuerpo["reservas"]["total"] == 0


def test_un_rango_invertido_se_ordena_en_vez_de_rechazarse(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)])
    hoy = datetime.now(timezone.utc).date()
    ayer = hoy - timedelta(days=1)

    cuerpo = _tablero(
        api, cabeceras_admin, desde=hoy.isoformat(), hasta=ayer.isoformat()
    )

    assert cuerpo["periodo"]["desde"] == ayer.isoformat()
    assert cuerpo["periodo"]["hasta"] == hoy.isoformat()
    assert cuerpo["reservas"]["total"] == 1


# =====================================================================
# Filtro por sucursal
# =====================================================================

def test_el_filtro_por_sucursal_separa_las_reservas(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)])

    propio = _tablero(api, cabeceras_admin, sucursal_id=sucursal)
    ajeno = _tablero(api, cabeceras_admin, sucursal_id=otra)

    assert propio["reservas"]["total"] == 1
    assert propio["periodo"]["sucursal"] == "Centro"
    assert ajeno["reservas"]["total"] == 0
    assert ajeno["periodo"]["sucursal"] == "Norte"


def test_una_sucursal_inexistente_devuelve_ceros_y_no_un_404(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """De solo lectura y sin nada que proteger.

    Un 404 obligaria a la pantalla a distinguir «no existe» de «no tuvo
    movimiento», que se ven igual y se atienden igual.
    """
    cuerpo = _tablero(api, cabeceras_admin, sucursal_id=999_999)

    assert cuerpo["reservas"]["total"] == 0
    assert cuerpo["periodo"]["sucursal_id"] == 999_999
    assert cuerpo["periodo"]["sucursal"] is None


# =====================================================================
# Inventario
# =====================================================================

def test_los_saldos_no_dependen_del_periodo(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Un saldo es una foto, no un acumulado: `existencia` no tiene fecha.

    Consultar un periodo de hace tres meses tiene que devolver el stock de
    ahora, no cero. Es contraintuitivo leerlo en la pantalla y por eso el
    contrato lo dice ---ver `SaludInventarioOut`--- y la prueba lo fija.
    """
    viejo = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()

    cuerpo = _tablero(api, cabeceras_admin, desde=viejo, hasta=viejo)

    assert cuerpo["inventario"]["total_disponible"] == 32
    assert cuerpo["reservas"]["total"] == 0


def test_lo_reservado_sale_del_disponible_y_los_dos_se_informan(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 5)])

    inventario = _tablero(api, cabeceras_admin)["inventario"]

    assert inventario["total_disponible"] == 27
    assert inventario["total_reservado"] == 5


def test_el_tablero_pide_la_alerta_a_p4_en_vez_de_definirla(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Se mueve el umbral por la API de CU-16 y el tablero tiene que notarlo.

    Si el tablero tuviera su propia definicion de «stock critico», esta prueba
    pasaria igual el dia que las dos definiciones se separen ---y ese es
    justamente el dia en que CU-16 y el tablero empezarian a contradecirse
    sobre la misma prenda---. Lo que se fija aca no es el numero: es que haya un
    solo lugar donde la regla vive.
    """
    antes = _tablero(api, cabeceras_admin)["inventario"]
    assert antes["en_alerta"] == 0

    filas = api.get(
        EXISTENCIAS, headers=cabeceras_admin, params={"sucursal_id": sucursal, "tamano": 50}
    ).json()["items"]
    fila = next(f for f in filas if f["variante_id"] == variantes[0])

    ajuste = api.patch(
        f"{EXISTENCIAS}/{fila['existencia_id']}/stock-minimo",
        headers=cabeceras_encargado,
        json={"stock_minimo": 25},
    )
    assert ajuste.status_code == 200, ajuste.text

    despues = _tablero(api, cabeceras_admin)
    assert despues["inventario"]["en_alerta"] == 1
    assert [a["variante_id"] for a in despues["alertas"]] == [variantes[0]]
    assert despues["alertas"][0]["stock_minimo"] == 25
    assert despues["alertas"][0]["sucursal"] == "Centro"


# =====================================================================
# Ventas: el bloque que todavia no tiene tablas
# =====================================================================

def test_el_bloque_de_ventas_viaja_aunque_no_exista_la_tabla(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Es lo que permite que la pantalla no cambie cuando aterrice la `0006`.

    Un bloque que apareciera de la nada obligaria a tocar la interfaz dos veces:
    una para dibujar el aviso y otra para dibujar las tarjetas.
    """
    ventas = _tablero(api, cabeceras_admin)["ventas"]

    assert ventas["disponible"] is False
    assert ventas["motivo"]
    assert ventas["monto_periodo"] is None
    assert ventas["ticket_promedio"] is None
    assert ventas["mas_vendidas"] == []
