"""CU-24 · Atender reserva en sucursal.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-24-atender-reserva-en-sucursal.md).

Es el caso de uso que **cierra el ciclo de vida de la reserva** y el que estrena
la convención de los dos movimientos que quedó fijada al escribir CU-22.

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **El invariante sobrevive a una venta desde reserva.** `LIBERACION +n` y
  `VENTA −n` tienen que dejar el disponible donde estaba y la reservada en cero.
  Si se escribiera solo la `VENTA`, el saldo quedaría negativo; si solo la
  `LIBERACION`, la tienda seguiría creyendo que tiene una prenda que se fue
  caminando.
- **Cerrar a medias no se puede.** Si falta el resultado de una prenda, sus
  unidades quedarían apartadas en una reserva ya `ATENDIDA` — y nadie las
  libera, porque CU-25 solo expira las vivas.
- **El ámbito del Encargado**, que se resuelve leyendo la fila y no confiando en
  el identificador de la URL.
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.reservas.models import Reserva

RESERVAS = "/api/v1/reservas"
PANEL = "/api/v1/sucursal/reservas"
EXISTENCIAS = "/api/v1/inventario/existencias"
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

BOLIVIA = timezone(timedelta(hours=-4))


def _manana(hora: int) -> datetime:
    dia = datetime.now(BOLIVIA) + timedelta(days=1)
    return dia.replace(hour=hora, minute=0, second=0, microsecond=0)


def _preparacion(reserva_id: int) -> str:
    return f"{PANEL}/{reserva_id}/preparacion"


def _atencion(reserva_id: int) -> str:
    return f"{PANEL}/{reserva_id}/atencion"


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
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
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
            "razon_social": "Textiles del Sur SRL",
            "identificacion_tributaria": "1023456789",
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
            "referencia": "REM-SEED",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


def _saldo(api: TestClient, admin: dict[str, str], *, sucursal_id: int) -> dict[int, dict]:
    filas = api.get(EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}).json()
    return {f["variante_id"]: f for f in filas}


def _resultados(reserva: dict, *valores: str) -> dict:
    """Arma el cuerpo del cierre a partir de las líneas de la reserva."""
    return {
        "resultados": [
            {"detalle_id": linea["id"], "resultado": valor}
            for linea, valor in zip(reserva["lineas"], valores)
        ]
    }


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
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


@pytest.fixture
def reserva(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
) -> dict:
    """Una reserva de dos prendas: 3 unidades de una y 2 de la otra."""
    _ingresar(
        api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variantes[0], 10), (variantes[1], 5)]
    )
    respuesta = api.post(
        RESERVAS,
        headers=cabeceras_cliente,
        json={
            "sucursal_id": sucursal,
            "franja_inicio": _manana(15).isoformat(),
            "franja_fin": _manana(16).isoformat(),
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 3},
                {"variante_id": variantes[1], "cantidad": 2},
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Autorizacion y ambito ----------------------------------------------

def test_sin_token_no_se_entra_al_panel(api: TestClient) -> None:
    assert api.get(PANEL).status_code == 401


def test_un_cliente_no_entra_al_panel_de_la_sucursal(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Son dos colecciones distintas: «mis reservas» y «las de mi sucursal»."""
    assert api.get(PANEL, headers=cabeceras_cliente).status_code == 403


def test_el_encargado_ve_las_reservas_de_su_sucursal(
    api: TestClient,
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    reserva: dict,
) -> None:
    """Paso 2, y que el listado traiga a quién hay que atender."""
    pagina = api.get(PANEL, headers=cabeceras_encargado).json()
    assert pagina["total"] == 1
    fila = pagina["items"][0]
    assert fila["sucursal_id"] == sucursal
    assert fila["estado"] == "PENDIENTE"
    assert fila["prendas"] == 2 and fila["unidades"] == 5
    # El Encargado necesita saber a quién está atendiendo.
    assert fila["cliente"] == "Ana Quiroga"


def test_el_encargado_no_atiende_una_reserva_de_otra_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    variantes: list[int],
) -> None:
    """El ámbito se resuelve leyendo la fila.

    El identificador de la URL no dice a qué sucursal pertenece: sin ese paso, a
    un Encargado le bastaría probar números para cerrar reservas de otro local.
    """
    ajena = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingresar(api, cabeceras_admin, sucursal_id=ajena, lineas=[(variantes[0], 5)])
    de_la_ajena = api.post(
        RESERVAS,
        headers=cabeceras_cliente,
        json={
            "sucursal_id": ajena,
            "franja_inicio": _manana(15).isoformat(),
            "franja_fin": _manana(16).isoformat(),
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    ).json()

    respuesta = api.patch(_preparacion(de_la_ajena["id"]), headers=cabeceras_encargado)
    assert respuesta.status_code == 403

    # Y no la ve en su panel.
    assert api.get(PANEL, headers=cabeceras_encargado).json()["total"] == 0
    # El Administrador sí ve las dos: su ámbito es toda la red.
    assert api.get(PANEL, headers=cabeceras_admin).json()["total"] == 1


# --- Preparacion ---------------------------------------------------------

def test_preparar_no_mueve_stock(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Es la única transición de la reserva que no toca el inventario.

    Las unidades ya estaban apartadas desde CU-22 y siguen estándolo: lo único
    que cambia es que alguien las fue a buscar a la percha.
    """
    antes = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    movimientos_antes = api.get(MOVIMIENTOS, headers=cabeceras_admin).json()["total"]

    respuesta = api.patch(_preparacion(reserva["id"]), headers=cabeceras_encargado)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "PREPARADA"

    despues = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert despues[variantes[0]]["cantidad_disponible"] == antes[variantes[0]]["cantidad_disponible"]
    assert despues[variantes[0]]["cantidad_reservada"] == antes[variantes[0]]["cantidad_reservada"]
    assert api.get(MOVIMIENTOS, headers=cabeceras_admin).json()["total"] == movimientos_antes


def test_no_se_prepara_dos_veces(
    api: TestClient, cabeceras_encargado: dict[str, str], reserva: dict
) -> None:
    api.patch(_preparacion(reserva["id"]), headers=cabeceras_encargado)
    segunda = api.patch(_preparacion(reserva["id"]), headers=cabeceras_encargado)
    assert segunda.status_code == 409
    assert "ya estaba preparada" in segunda.json()["detail"]


def test_el_cliente_todavia_puede_cancelar_una_preparada(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    reserva: dict,
) -> None:
    """PREPARADA sigue siendo un estado vivo: el RF29 deja cancelar hasta que se
    atienda, y que el Encargado ya haya juntado las prendas no cambia eso."""
    api.patch(_preparacion(reserva["id"]), headers=cabeceras_encargado)

    cancelada = api.patch(
        f"{RESERVAS}/{reserva['id']}/cancelacion", headers=cabeceras_cliente, json={}
    )
    assert cancelada.status_code == 200, cancelada.text
    assert cancelada.json()["estado"] == "CANCELADA"


# --- Atencion: el nucleo del caso de uso ---------------------------------

def test_lo_que_no_se_lleva_vuelve_al_disponible(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Resultado NO_LLEVA: es el mismo movimiento que una cancelación."""
    respuesta = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "NO_LLEVA", "NO_LLEVA"),
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["estado"] == "ATENDIDA"
    assert all(linea["resultado_prueba"] == "NO_LLEVA" for linea in cuerpo["lineas"])

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 10
    assert saldo[variantes[0]]["cantidad_reservada"] == 0
    assert saldo[variantes[1]]["cantidad_disponible"] == 5

    # Solo LIBERACION, ninguna VENTA: no se vendió nada.
    assert api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "VENTA"}
    ).json()["total"] == 0


def test_lo_que_se_lleva_sale_del_inventario(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """**La prueba que justifica la convención de los dos movimientos.**

    Resultado LLEVA: una `LIBERACION` de +n y una `VENTA` de −n. El neto sobre
    el disponible es cero y la prenda sale de la tienda.

    Si se escribiera solo la `VENTA`, el saldo quedaría negativo —esas unidades
    ya habían salido del disponible al crearse la reserva—. Si solo la
    `LIBERACION`, la tienda seguiría creyendo que tiene una prenda que se fue
    caminando.
    """
    respuesta = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "LLEVA", "LLEVA"),
    )
    assert respuesta.status_code == 200, respuesta.text

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    # 10 − 3 vendidas. La reservada vuelve a cero.
    assert saldo[variantes[0]]["cantidad_disponible"] == 7
    assert saldo[variantes[0]]["cantidad_reservada"] == 0
    assert saldo[variantes[0]]["cantidad_fisica"] == 7, "las prendas se fueron"
    assert saldo[variantes[1]]["cantidad_disponible"] == 3

    ventas = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "VENTA"}
    ).json()
    assert ventas["total"] == 2
    assert sorted(m["cantidad"] for m in ventas["items"]) == [-3, -2]
    assert all("se la lleva" in m["motivo"] for m in ventas["items"])


def test_una_reserva_puede_cerrarse_con_resultados_mezclados(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """El caso normal: se lleva una prenda y la otra no le quedó."""
    respuesta = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "LLEVA", "NO_LLEVA"),
    )
    assert respuesta.status_code == 200, respuesta.text

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 7   # se llevó 3
    assert saldo[variantes[1]]["cantidad_disponible"] == 5   # devolvió las 2
    assert all(fila["cantidad_reservada"] == 0 for fila in saldo.values())


def test_el_invariante_sobrevive_a_la_venta_desde_reserva(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """**D4** comprobado sobre el ciclo completo.

    INGRESO +10, RESERVA −3, LIBERACION +3, VENTA −3. La suma tiene que dar
    exactamente el disponible, y la reservada tiene que cerrar en cero.
    """
    api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "LLEVA", "NO_LLEVA"),
    )

    historial = api.get(
        MOVIMIENTOS,
        headers=cabeceras_admin,
        params={"variante_id": variantes[0], "tamano": 100},
    ).json()
    assert historial["total"] == 4
    assert sorted(m["tipo"] for m in historial["items"]) == [
        "INGRESO",
        "LIBERACION",
        "RESERVA",
        "VENTA",
    ]

    suma = sum(m["cantidad"] for m in historial["items"])
    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)[variantes[0]]
    assert suma == saldo["cantidad_disponible"] == 7

    reservas_ = [m["cantidad"] for m in historial["items"] if m["tipo"] == "RESERVA"]
    liberaciones = [m["cantidad"] for m in historial["items"] if m["tipo"] == "LIBERACION"]
    assert saldo["cantidad_reservada"] == -sum(reservas_) - sum(liberaciones) == 0


def test_se_puede_atender_una_pendiente_sin_prepararla(
    api: TestClient, cabeceras_encargado: dict[str, str], reserva: dict
) -> None:
    """PREPARADA es un paso útil, no un trámite obligatorio.

    En una tienda chica el Encargado junta las prendas y atiende al cliente en
    el mismo acto; obligarlo a pulsar «preparada» antes solo agregaría un clic.
    """
    respuesta = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "NO_LLEVA", "NO_LLEVA"),
    )
    assert respuesta.status_code == 200, respuesta.text


def test_la_observacion_del_cierre_se_guarda(
    api: TestClient, cabeceras_encargado: dict[str, str], reserva: dict
) -> None:
    cuerpo = _resultados(reserva, "NO_LLEVA", "NO_LLEVA")
    cuerpo["observacion"] = "La clienta pidió otra talla, se la encargamos"
    respuesta = api.patch(_atencion(reserva["id"]), headers=cabeceras_encargado, json=cuerpo)
    assert respuesta.json()["observacion"] == "La clienta pidió otra talla, se la encargamos"


# --- Excepcion E11: cerrar a medias no se puede --------------------------

def test_no_se_cierra_sin_el_resultado_de_todas_las_prendas(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    reserva: dict,
) -> None:
    """Excepción E11, y el motivo por el que importa.

    Si faltara una prenda, sus unidades quedarían apartadas en una reserva ya
    `ATENDIDA` — y no las libera nadie, porque CU-25 solo expira las vivas.
    """
    primera = reserva["lineas"][0]
    respuesta = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json={"resultados": [{"detalle_id": primera["id"], "resultado": "LLEVA"}]},
    )
    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"]
    assert detalle["detalles"] == [reserva["lineas"][1]["id"]]

    # Y no tocó nada: la reserva sigue viva con su stock apartado.
    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert sum(f["cantidad_reservada"] for f in saldo.values()) == 5
    assert api.get(
        f"{PANEL}/{reserva['id']}", headers=cabeceras_encargado
    ).json()["estado"] == "PENDIENTE"


def test_no_se_admiten_prendas_de_otra_reserva(
    api: TestClient, cabeceras_encargado: dict[str, str], reserva: dict
) -> None:
    """La otra mitad de E11, y se distingue de la primera: olvidarse de una
    prenda y mandar una ajena no se arreglan igual."""
    cuerpo = _resultados(reserva, "LLEVA", "LLEVA")
    cuerpo["resultados"].append({"detalle_id": 999_999, "resultado": "LLEVA"})
    respuesta = api.patch(_atencion(reserva["id"]), headers=cabeceras_encargado, json=cuerpo)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["detalles"] == [999_999]


def test_un_resultado_invalido_no_se_acepta(
    api: TestClient, cabeceras_encargado: dict[str, str], reserva: dict
) -> None:
    """Lo impide además el CHECK `ck_reserva_detalle_resultado`, pero un CHECK
    violado llega como un 500 de PostgreSQL."""
    cuerpo = _resultados(reserva, "TAL_VEZ", "LLEVA")
    respuesta = api.patch(_atencion(reserva["id"]), headers=cabeceras_encargado, json=cuerpo)
    assert respuesta.status_code == 422


# --- Estados finales -----------------------------------------------------

def test_no_se_atiende_una_reserva_cancelada(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    reserva: dict,
) -> None:
    api.patch(f"{RESERVAS}/{reserva['id']}/cancelacion", headers=cabeceras_cliente, json={})

    respuesta = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "LLEVA", "LLEVA"),
    )
    assert respuesta.status_code == 409
    assert "canceló" in respuesta.json()["detail"]


def test_no_se_atiende_dos_veces(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Sin esto, la segunda liberación devolvería unidades que ya no estaban
    apartadas: el mismo problema que la doble cancelación de CU-23."""
    primera = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "NO_LLEVA", "NO_LLEVA"),
    )
    assert primera.status_code == 200

    segunda = api.patch(
        _atencion(reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(reserva, "NO_LLEVA", "NO_LLEVA"),
    )
    assert segunda.status_code == 409

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 10, "se liberó dos veces"


def test_atender_libera_el_probador(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Una reserva atendida ya no ocupa vestidor: el control de capacidad de
    CU-22 solo cuenta las vivas."""
    db_reserva = reserva
    api.patch(
        _atencion(db_reserva["id"]),
        headers=cabeceras_encargado,
        json=_resultados(db_reserva, "NO_LLEVA", "NO_LLEVA"),
    )

    # La misma franja vuelve a estar libre.
    otra = api.post(
        RESERVAS,
        headers=cabeceras_cliente,
        json={
            "sucursal_id": sucursal,
            "franja_inicio": _manana(15).isoformat(),
            "franja_fin": _manana(16).isoformat(),
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert otra.status_code == 201, otra.text
