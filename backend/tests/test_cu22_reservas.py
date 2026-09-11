"""CU-22 · Crear reserva de prendas.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-22-crear-reserva-de-prendas.md).

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **La prueba de concurrencia del riesgo R5.** El plan la exige con nombre y
  apellido —§5.6, R5: «prueba explícita de concurrencia en el Ciclo 2»—: dos
  clientes reservando la última unidad al mismo tiempo, y solo uno se la lleva.
  Es la única prueba del proyecto que abre dos conexiones de verdad.
- **La transacción es todo o nada.** Una reserva de tres prendas donde la
  tercera no tiene stock no puede dejar las dos primeras apartadas: eso sería
  stock inmovilizado sin reserva que lo explique, y no lo liberaría nadie
  —CU-25 expira reservas, y eso no sería una—.
- **Reservar no destruye stock, lo traslada** (D3). El físico no cambia; lo que
  cambia es de qué bolsillo es cada unidad.
- **La capacidad de probadores.** `sucursal.capacidad_vestidores` existe desde
  el Ciclo 1 y ningún caso de uso la leía.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.inventario.models import Existencia, MovimientoInventario

RESERVAS = "/api/v1/reservas"
EXISTENCIAS = "/api/v1/inventario/existencias"
INGRESOS = "/api/v1/inventario/ingresos"
MOVIMIENTOS = "/api/v1/inventario/movimientos"

SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"
PROVEEDORES = "/api/v1/organizacion/proveedores"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"

#: Zona de Bolivia. Se usa una zona REAL y no UTC a propósito: el horario de la
#: sucursal es una hora de pared («abre a las 09:00»), y si las pruebas
#: trabajaran en UTC no detectarían que el servidor compara mal las dos cosas.
BOLIVIA = timezone(timedelta(hours=-4))


def _manana(hora: int, minuto: int = 0) -> datetime:
    """Mañana a esa hora, en hora de Bolivia.

    Mañana y no hoy porque una franja de hoy puede haber pasado ya según a qué
    hora se corran las pruebas, y una prueba que falla según la hora del día no
    sirve para nada.
    """
    dia = datetime.now(BOLIVIA) + timedelta(days=1)
    return dia.replace(hour=hora, minute=minuto, second=0, microsecond=0)


# --- Ayudantes -----------------------------------------------------------

def _crear_sucursal(
    api: TestClient,
    admin: dict[str, str],
    *,
    nombre: str,
    vestidores: int = 4,
    activa: bool = True,
    apertura: str = "09:00:00",
    cierre: str = "20:00:00",
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
            "horario_apertura": apertura,
            "horario_cierre": cierre,
            "capacidad_vestidores": vestidores,
            "activa": activa,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_variantes(api: TestClient, admin: dict[str, str], cuantas: int = 3) -> list[int]:
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
    for indice, codigo in enumerate(("S", "M", "L", "XL")[:cuantas]):
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
    lineas: list[tuple[int, int]],
) -> None:
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": _proveedor(api, admin),
            "referencia": "REM-SEED",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


def _reservar(
    api: TestClient,
    cabeceras: dict[str, str],
    *,
    sucursal_id: int,
    lineas: list[tuple[int, int]],
    inicio: datetime | None = None,
    fin: datetime | None = None,
    observacion: str | None = None,
):
    inicio = inicio or _manana(15)
    fin = fin or _manana(16)
    return api.post(
        RESERVAS,
        headers=cabeceras,
        json={
            "sucursal_id": sucursal_id,
            "franja_inicio": inicio.isoformat(),
            "franja_fin": fin.isoformat(),
            "observacion": observacion,
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )


def _saldo(api: TestClient, admin: dict[str, str], *, sucursal_id: int) -> list[dict]:
    return api.get(EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}).json()


# --- Fixtures ------------------------------------------------------------

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict[str, str]) -> list[int]:
    return _crear_variantes(api, cabeceras_admin)


@pytest.fixture
def con_stock(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variantes: list[int]
) -> None:
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 10), (variantes[1], 5), (variantes[2], 1)],
    )


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_reserva(api: TestClient) -> None:
    assert api.post(RESERVAS, json={}).status_code == 401


def test_un_administrador_no_reserva(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """CU-22 es del Cliente. El Administrador tiene su propio inventario."""
    assert api.get(RESERVAS, headers=cabeceras_admin).status_code == 403


# --- Flujo principal -----------------------------------------------------

def test_la_reserva_aparta_el_stock_sin_destruirlo(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """Pasos 4 a 7, y la decisión **D3** comprobada.

    «Una reserva no descuenta el stock: lo traslada de disponible a reservado.»
    El total físico no se mueve — la prenda sigue en la percha, con dueño.
    """
    respuesta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 2), (variantes[1], 1)],
        observacion="Paso después del trabajo",
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["estado"] == "PENDIENTE"
    assert cuerpo["unidades"] == 3
    assert len(cuerpo["lineas"]) == 2
    assert cuerpo["sucursal"] == "Centro"
    # La prenda se nombra, no se numera.
    assert cuerpo["lineas"][0]["producto"] == "Camisa Oxford manga larga"
    assert cuerpo["lineas"][0]["sku"]
    assert cuerpo["lineas"][0]["resultado_prueba"] is None

    por_variante = {e["variante_id"]: e for e in _saldo(api, cabeceras_admin, sucursal_id=sucursal)}
    primera = por_variante[variantes[0]]
    assert primera["cantidad_disponible"] == 8
    assert primera["cantidad_reservada"] == 2
    # Lo que importa de D3: el físico no cambió.
    assert primera["cantidad_fisica"] == 10


def test_la_reserva_deja_un_movimiento_por_prenda(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """La regla de P4 sigue valiendo desde P6: ninguna cantidad cambia sin
    movimiento que la explique."""
    _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 2)]
    )

    movimientos = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "RESERVA"}
    ).json()
    assert movimientos["total"] == 1
    fila = movimientos["items"][0]
    # Negativo: sale de disponible. Es lo que sostiene el invariante D4.
    assert fila["cantidad"] == -2
    assert "Reserva #" in fila["motivo"]
    assert fila["usuario"] == "Ana Quiroga"


def test_el_saldo_sigue_siendo_la_suma_de_sus_movimientos(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """El invariante de D4, ahora con un tipo que mueve los dos bolsillos.

    Es la comprobación que justifica que RESERVA valga −n y no +n: si el signo
    estuviera al revés, el disponible y la suma del historial se separarían acá.
    """
    _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 3)]
    )

    historial = api.get(
        MOVIMIENTOS,
        headers=cabeceras_admin,
        params={"variante_id": variantes[0], "tamano": 100},
    ).json()
    suma = sum(m["cantidad"] for m in historial["items"])

    saldo = next(
        e for e in _saldo(api, cabeceras_admin, sucursal_id=sucursal)
        if e["variante_id"] == variantes[0]
    )
    assert suma == saldo["cantidad_disponible"] == 7
    # Y el segundo invariante: la reservada es lo apartado menos lo liberado.
    reservas = [m["cantidad"] for m in historial["items"] if m["tipo"] == "RESERVA"]
    liberaciones = [m["cantidad"] for m in historial["items"] if m["tipo"] == "LIBERACION"]
    assert saldo["cantidad_reservada"] == -sum(reservas) - sum(liberaciones) == 3


def test_mis_reservas_lista_solo_las_propias(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)])
    _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[1], 1)],
        inicio=_manana(17),
        fin=_manana(18),
    )

    pagina = api.get(RESERVAS, headers=cabeceras_cliente).json()
    assert pagina["total"] == 2
    assert all(r["sucursal"] == "Centro" for r in pagina["items"])
    assert pagina["items"][0]["prendas"] == 1

    vivas = api.get(RESERVAS, headers=cabeceras_cliente, params={"vivas": True}).json()
    assert vivas["total"] == 2


def test_el_detalle_de_una_reserva_ajena_da_404_y_no_403(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """Un 403 confirmaría que esa reserva existe, y eso ya es información sobre
    otro cliente."""
    propia = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)]
    ).json()

    assert api.get(f"{RESERVAS}/{propia['id']}", headers=cabeceras_cliente).status_code == 200
    assert api.get(f"{RESERVAS}/999999", headers=cabeceras_cliente).status_code == 404


# --- La transaccion ------------------------------------------------------

def test_si_una_prenda_no_tiene_stock_no_se_aparta_ninguna(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """Excepción E9, y la razón por la que importa más que en un ingreso.

    Stock apartado sin una reserva que lo explique no lo libera nadie: CU-25
    expira reservas, y eso no sería una.
    """
    respuesta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        # La tercera tiene UNA unidad sembrada y se piden cinco. Cinco y no
        # noventa y nueve: el esquema topa en diez por linea, y con un numero
        # fuera de rango la peticion moriria en la validacion de Pydantic sin
        # llegar nunca a la transaccion, que es justo lo que esta prueba mira.
        lineas=[(variantes[0], 2), (variantes[1], 1), (variantes[2], 5)],
    )
    assert respuesta.status_code == 409, respuesta.text

    for existencia in _saldo(api, cabeceras_admin, sucursal_id=sucursal):
        assert existencia["cantidad_reservada"] == 0, "quedó stock apartado"
    assert api.get(RESERVAS, headers=cabeceras_cliente).json()["total"] == 0
    assert api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "RESERVA"}
    ).json()["total"] == 0


def test_no_se_reserva_una_prenda_que_nunca_estuvo_en_esa_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    variantes: list[int],
) -> None:
    """Sin existencia no hay nada que apartar, y no se crea una en cero: eso
    inventaría una disponibilidad que no existe."""
    vacia = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    respuesta = _reservar(
        api, cabeceras_cliente, sucursal_id=vacia, lineas=[(variantes[0], 1)]
    )
    assert respuesta.status_code == 409
    assert _saldo(api, cabeceras_admin, sucursal_id=vacia) == []


# --- Riesgo R5: la prueba de concurrencia --------------------------------

def test_r5_dos_clientes_no_pueden_reservar_la_ultima_unidad(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    fabrica_sesiones,
    db,
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """**La prueba que el plan exige por su nombre** (§5.6, riesgo R5).

    Dos transacciones intentan apartar **la misma última unidad** al mismo
    tiempo, cada una con su propia conexión a PostgreSQL. Sin el
    `SELECT ... FOR UPDATE` de `apartar_para_reserva`, las dos leen «queda 1»,
    las dos pasan la comprobación y las dos reservan: eso es la sobreventa.

    Con el bloqueo, la segunda **espera** a que la primera confirme, vuelve a
    leer —ahora «quedan 0»— y falla. El resultado tiene que ser exactamente
    uno y uno: un éxito y un rechazo.

    `variantes[2]` tiene una sola unidad, sembrada por el *fixture*.
    """
    from app.modules.inventario import service as inventario

    ultima = variantes[2]

    def apartar() -> str:
        """Una transacción completa e independiente, como la de una petición."""
        sesion = fabrica_sesiones()
        try:
            inventario.apartar_para_reserva(
                sesion,
                variante_id=ultima,
                sucursal_id=sucursal,
                cantidad=1,
                usuario_id=None,
                motivo="Prueba de concurrencia R5",
            )
            sesion.commit()
            return "ok"
        except inventario.StockInsuficiente:
            sesion.rollback()
            return "sin-stock"
        finally:
            sesion.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = sorted(f.result() for f in [pool.submit(apartar), pool.submit(apartar)])

    assert resultados == ["ok", "sin-stock"], (
        f"sobreventa: los dos intentos resolvieron {resultados}"
    )

    # Y el saldo quedó consistente: una apartada, ninguna disponible, y un solo
    # movimiento. Sin el bloqueo, acá habría dos movimientos y un disponible de
    # -1 que el CHECK habría rechazado con un 500.
    existencia = db.scalar(
        select(Existencia).where(
            Existencia.variante_id == ultima, Existencia.sucursal_id == sucursal
        )
    )
    db.refresh(existencia)
    assert existencia.cantidad_disponible == 0
    assert existencia.cantidad_reservada == 1

    movimientos = db.scalars(
        select(MovimientoInventario).where(
            MovimientoInventario.existencia_id == existencia.id,
            MovimientoInventario.tipo == "RESERVA",
        )
    ).all()
    assert len(movimientos) == 1


# --- Capacidad de probadores (E6) ---------------------------------------

def test_no_se_reserva_sin_probador_libre(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    variantes: list[int],
) -> None:
    """Excepción E6.

    Es la regla que vuelve útil a `sucursal.capacidad_vestidores`, declarada en
    el Ciclo 1 y sin ningún caso de uso que la leyera. Sin esto, veinte clientes
    reservan la misma franja en una tienda con un probador.
    """
    chica = _crear_sucursal(api, cabeceras_admin, nombre="Kiosco", vestidores=1)
    _ingresar(api, cabeceras_admin, sucursal_id=chica, lineas=[(variantes[0], 10)])

    primera = _reservar(
        api, cabeceras_cliente, sucursal_id=chica, lineas=[(variantes[0], 1)]
    )
    assert primera.status_code == 201, primera.text

    # La misma franja, el único probador ya tomado.
    segunda = _reservar(
        api, cabeceras_cliente, sucursal_id=chica, lineas=[(variantes[0], 1)]
    )
    assert segunda.status_code == 409
    assert "probadores" in segunda.json()["detail"]

    # Y el stock de la que se rechazó no quedó apartado.
    saldo = _saldo(api, cabeceras_admin, sucursal_id=chica)[0]
    assert saldo["cantidad_reservada"] == 1


def test_dos_franjas_consecutivas_no_se_solapan(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    variantes: list[int],
) -> None:
    """15:00-16:00 y 16:00-17:00 son turnos encadenados, no un conflicto.

    Por eso el solapamiento se calcula con `<` estricto: con `<=` no se podrían
    encadenar turnos, que es el uso normal de un probador.
    """
    chica = _crear_sucursal(api, cabeceras_admin, nombre="Kiosco", vestidores=1)
    _ingresar(api, cabeceras_admin, sucursal_id=chica, lineas=[(variantes[0], 10)])

    primera = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=chica,
        lineas=[(variantes[0], 1)],
        inicio=_manana(15),
        fin=_manana(16),
    )
    segunda = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=chica,
        lineas=[(variantes[0], 1)],
        inicio=_manana(16),
        fin=_manana(17),
    )
    assert primera.status_code == 201, primera.text
    assert segunda.status_code == 201, segunda.text


# --- La franja -----------------------------------------------------------

def test_no_se_reserva_en_el_pasado(
    api: TestClient, cabeceras_cliente: dict[str, str], sucursal: int, variantes: list[int],
    con_stock: None,
) -> None:
    """Excepción E3."""
    ayer = datetime.now(BOLIVIA) - timedelta(days=1)
    respuesta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 1)],
        inicio=ayer.replace(hour=15, minute=0, second=0, microsecond=0),
        fin=ayer.replace(hour=16, minute=0, second=0, microsecond=0),
    )
    assert respuesta.status_code == 422
    assert "pasó" in respuesta.json()["detail"]


def test_no_se_reserva_con_demasiada_anticipacion(
    api: TestClient, cabeceras_cliente: dict[str, str], sucursal: int, variantes: list[int],
    con_stock: None,
) -> None:
    """Excepción E5. La reserva inmoviliza stock desde que se crea: reservar
    para dentro de un mes dejaría unidades apartadas un mes."""
    lejos = datetime.now(BOLIVIA) + timedelta(days=30)
    respuesta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 1)],
        inicio=lejos.replace(hour=15, minute=0, second=0, microsecond=0),
        fin=lejos.replace(hour=16, minute=0, second=0, microsecond=0),
    )
    assert respuesta.status_code == 422
    assert "anticipación" in respuesta.json()["detail"]


def test_la_franja_tiene_que_durar_algo_razonable(
    api: TestClient, cabeceras_cliente: dict[str, str], sucursal: int, variantes: list[int],
    con_stock: None,
) -> None:
    """Excepción E4, por los dos extremos."""
    corta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 1)],
        inicio=_manana(15),
        fin=_manana(15, 5),
    )
    assert corta.status_code == 422

    larga = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 1)],
        inicio=_manana(10),
        fin=_manana(19),
    )
    assert larga.status_code == 422


def test_no_se_reserva_fuera_del_horario_de_la_sucursal(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    variantes: list[int],
) -> None:
    """Excepción E8, y la que atrapa el error de zona horaria.

    La sucursal abre a las 09:00 **hora de pared**. La franja va en hora de
    Bolivia (−04:00). Si el servidor convirtiera a UTC antes de comparar, las
    15:00 locales se leerían como 19:00 y una tienda que cierra a las 18:00
    rechazaría una reserva perfectamente válida — o al revés.
    """
    temprana = _crear_sucursal(
        api, cabeceras_admin, nombre="Matutina", apertura="09:00:00", cierre="14:00:00"
    )
    _ingresar(api, cabeceras_admin, sucursal_id=temprana, lineas=[(variantes[0], 10)])

    # 10:00-11:00 locales: dentro del horario.
    dentro = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=temprana,
        lineas=[(variantes[0], 1)],
        inicio=_manana(10),
        fin=_manana(11),
    )
    assert dentro.status_code == 201, dentro.text

    # 16:00-17:00 locales: ya cerró.
    fuera = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=temprana,
        lineas=[(variantes[0], 1)],
        inicio=_manana(16),
        fin=_manana(17),
    )
    assert fuera.status_code == 422
    assert "atiende" in fuera.json()["detail"]


def test_la_franja_tiene_que_traer_zona_horaria(
    api: TestClient, cabeceras_cliente: dict[str, str], sucursal: int, variantes: list[int],
    con_stock: None,
) -> None:
    """Sin zona, el servidor tendría que suponer cuál es — y suponer mal hace
    que una reserva expire cuatro horas antes de lo que dice la pantalla."""
    respuesta = api.post(
        RESERVAS,
        headers=cabeceras_cliente,
        json={
            "sucursal_id": sucursal,
            "franja_inicio": "2099-01-01T15:00:00",
            "franja_fin": "2099-01-01T16:00:00",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 422


# --- Excepciones del catalogo y la sucursal ------------------------------

def test_no_se_reserva_una_prenda_desactivada(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    con_stock: None,
) -> None:
    """Excepción E1, segunda mitad: la prenda existe pero dejó de ofrecerse."""
    api.patch(
        f"/api/v1/catalogo/variantes/{variantes[0]}",
        headers=cabeceras_admin,
        json={"activa": False},
    )
    respuesta = _reservar(
        api, cabeceras_cliente, sucursal_id=sucursal, lineas=[(variantes[0], 1)]
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["variantes"] == [variantes[0]]


def test_no_se_reserva_en_una_sucursal_dada_de_baja(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    variantes: list[int],
) -> None:
    """Excepción E2."""
    cerrada = _crear_sucursal(api, cabeceras_admin, nombre="Cerrada", activa=False)
    respuesta = _reservar(
        api, cabeceras_cliente, sucursal_id=cerrada, lineas=[(variantes[0], 1)]
    )
    assert respuesta.status_code == 422


def test_la_misma_prenda_no_puede_ir_en_dos_lineas(
    api: TestClient, cabeceras_cliente: dict[str, str], sucursal: int, variantes: list[int],
    con_stock: None,
) -> None:
    """Excepción E7. Lo impide además `uq_reserva_detalle_reserva_variante`,
    pero un UNIQUE violado llega como un 500 de PostgreSQL."""
    respuesta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 1), (variantes[0], 2)],
    )
    assert respuesta.status_code == 422


def test_una_reserva_sin_prendas_no_es_una_reserva(
    api: TestClient, cabeceras_cliente: dict[str, str], sucursal: int
) -> None:
    respuesta = _reservar(api, cabeceras_cliente, sucursal_id=sucursal, lineas=[])
    assert respuesta.status_code == 422
