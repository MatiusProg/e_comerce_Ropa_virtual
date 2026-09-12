"""CU-23 · Consultar y cancelar reserva.

Cubre el flujo principal, los flujos alternativos y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-23-consultar-y-cancelar-reserva.md).

La mitad de «consultar» la comparte con CU-22 y está probada allí —`GET
/reservas` y `GET /reservas/{id}`—. Lo que se prueba acá es **cancelar**, que es
lo que realiza el RF29 y lo que toca stock.

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **La doble cancelación.** Es el riesgo R5 visto del otro lado: allí era vender
  de más, acá es *inventar mercadería*. Dos peticiones simultáneas leerían la
  reserva en PENDIENTE, las dos pasarían la comprobación de estado y las dos
  liberarían el stock. Tiene prueba de concurrencia con dos conexiones reales.
- **Cancelar devuelve exactamente lo que se apartó**, ni una unidad más ni una
  menos, y deja el `LIBERACION` que lo explica.
- **Una reserva cancelada libera su probador**, porque el control de capacidad
  de CU-22 solo cuenta las vivas.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.inventario.models import Existencia
from app.modules.reservas.models import Reserva

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

BOLIVIA = timezone(timedelta(hours=-4))


def _manana(hora: int, minuto: int = 0) -> datetime:
    dia = datetime.now(BOLIVIA) + timedelta(days=1)
    return dia.replace(hour=hora, minute=minuto, second=0, microsecond=0)


def _cancelacion(reserva_id: int) -> str:
    return f"{RESERVAS}/{reserva_id}/cancelacion"


# --- Ayudantes -----------------------------------------------------------

def _crear_sucursal(
    api: TestClient, admin: dict[str, str], *, nombre: str, vestidores: int = 4
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
            "capacidad_vestidores": vestidores,
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_variantes(api: TestClient, admin: dict[str, str], cuantas: int = 2) -> list[int]:
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
    for indice, codigo in enumerate(("S", "M", "L")[:cuantas]):
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


def _reservar(
    api: TestClient,
    cabeceras: dict[str, str],
    *,
    sucursal_id: int,
    lineas: list[tuple[int, int]],
    inicio: datetime | None = None,
    fin: datetime | None = None,
):
    return api.post(
        RESERVAS,
        headers=cabeceras,
        json={
            "sucursal_id": sucursal_id,
            "franja_inicio": (inicio or _manana(15)).isoformat(),
            "franja_fin": (fin or _manana(16)).isoformat(),
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )


def _saldo(api: TestClient, admin: dict[str, str], *, sucursal_id: int) -> dict[int, dict]:
    filas = api.get(EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}).json()
    return {f["variante_id"]: f for f in filas}


# --- Fixtures ------------------------------------------------------------

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict[str, str]) -> list[int]:
    return _crear_variantes(api, cabeceras_admin)


@pytest.fixture
def reserva(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
) -> dict:
    """Una reserva viva de dos prendas: 3 unidades de una y 2 de la otra."""
    _ingresar(
        api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variantes[0], 10), (variantes[1], 5)]
    )
    respuesta = _reservar(
        api,
        cabeceras_cliente,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 3), (variantes[1], 2)],
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_cancela(api: TestClient) -> None:
    assert api.patch(_cancelacion(1), json={}).status_code == 401


def test_un_administrador_no_cancela_reservas_de_clientes(
    api: TestClient, cabeceras_admin: dict[str, str], reserva: dict
) -> None:
    """CU-23 es del Cliente. Cerrar una reserva desde la sucursal es CU-24, y es
    otra cosa: allí la reserva se atiende, no se cancela."""
    respuesta = api.patch(_cancelacion(reserva["id"]), headers=cabeceras_admin, json={})
    assert respuesta.status_code == 403


def test_no_se_cancela_una_reserva_ajena_y_el_error_no_confirma_que_existe(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Un 403 confirmaría que esa reserva existe, y eso ya es información sobre
    otro cliente. Por eso el mismo 404 que si no existiera."""
    respuesta = api.patch(_cancelacion(999_999), headers=cabeceras_cliente, json={})
    assert respuesta.status_code == 404


# --- Flujo principal -----------------------------------------------------

def test_cancelar_devuelve_el_stock_apartado(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Flujo principal, y el **RF29**.

    Sin cancelación el stock queda retenido hasta que la franja venza y CU-25 la
    expire: un día entero de mercadería inmovilizada porque alguien cambió de
    planes.
    """
    antes = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert antes[variantes[0]]["cantidad_disponible"] == 7
    assert antes[variantes[0]]["cantidad_reservada"] == 3

    respuesta = api.patch(
        _cancelacion(reserva["id"]),
        headers=cabeceras_cliente,
        json={"motivo": "Me surgió un viaje"},
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["estado"] == "CANCELADA"
    assert cuerpo["observacion"] == "Me surgió un viaje"
    # Las prendas se conservan: la reserva cancelada es historia, no se borra.
    assert len(cuerpo["lineas"]) == 2

    despues = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    for variante_id in variantes:
        fila = despues[variante_id]
        assert fila["cantidad_reservada"] == 0
    # Exactamente lo que se apartó, ni una unidad más.
    assert despues[variantes[0]]["cantidad_disponible"] == 10
    assert despues[variantes[1]]["cantidad_disponible"] == 5
    # Y el físico nunca se movió: la prenda estuvo en la percha todo el tiempo.
    assert despues[variantes[0]]["cantidad_fisica"] == 10


def test_cancelar_deja_una_liberacion_por_prenda(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    reserva: dict,
) -> None:
    """La regla de P4 sigue valiendo: ninguna cantidad vuelve sin movimiento."""
    api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})

    liberaciones = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "LIBERACION"}
    ).json()
    assert liberaciones["total"] == 2
    # Positivas: vuelven al disponible. Es lo que sostiene el invariante D4.
    assert sorted(m["cantidad"] for m in liberaciones["items"]) == [2, 3]
    assert all(
        f"Cancelacion de la reserva #{reserva['id']}" in m["motivo"]
        for m in liberaciones["items"]
    )


def test_el_invariante_se_sostiene_despues_de_cancelar(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """El ciclo completo ingreso → reserva → cancelación, con D4 comprobado.

    Es lo que confirma que los signos de RESERVA (−n) y LIBERACION (+n) son
    coherentes entre sí: si uno de los dos estuviera al revés, el saldo y la
    suma del historial se separarían acá.
    """
    api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})

    historial = api.get(
        MOVIMIENTOS,
        headers=cabeceras_admin,
        params={"variante_id": variantes[0], "tamano": 100},
    ).json()
    # INGRESO +10, RESERVA −3, LIBERACION +3.
    assert historial["total"] == 3
    suma = sum(m["cantidad"] for m in historial["items"])

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)[variantes[0]]
    assert suma == saldo["cantidad_disponible"] == 10

    reservas_ = [m["cantidad"] for m in historial["items"] if m["tipo"] == "RESERVA"]
    liberaciones = [m["cantidad"] for m in historial["items"] if m["tipo"] == "LIBERACION"]
    assert saldo["cantidad_reservada"] == -sum(reservas_) - sum(liberaciones) == 0


def test_el_motivo_es_opcional(
    api: TestClient, cabeceras_cliente: dict[str, str], reserva: dict
) -> None:
    """Cancelar no es un trámite: exigir una justificación para no ir a probarse
    ropa solo consigue que la gente escriba «asdf»."""
    respuesta = api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["observacion"] == "Cancelada por el cliente"


def test_la_reserva_cancelada_sigue_en_mis_reservas(
    api: TestClient, cabeceras_cliente: dict[str, str], reserva: dict
) -> None:
    """Cancelar no borra: la reserva es historia del cliente y de la sucursal, y
    los movimientos de LIBERACION apuntan a ella."""
    api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})

    todas = api.get(RESERVAS, headers=cabeceras_cliente).json()
    assert todas["total"] == 1
    assert todas["items"][0]["estado"] == "CANCELADA"

    vivas = api.get(RESERVAS, headers=cabeceras_cliente, params={"vivas": True}).json()
    assert vivas["total"] == 0

    cerradas = api.get(RESERVAS, headers=cabeceras_cliente, params={"vivas": False}).json()
    assert cerradas["total"] == 1


def test_cancelar_libera_el_probador(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    variantes: list[int],
) -> None:
    """El control de capacidad de CU-22 solo cuenta las reservas vivas.

    Sin esto, una sucursal de un probador se bloquearía para siempre en cuanto
    alguien reservara y se arrepintiera.
    """
    chica = _crear_sucursal(api, cabeceras_admin, nombre="Kiosco", vestidores=1)
    _ingresar(api, cabeceras_admin, sucursal_id=chica, lineas=[(variantes[0], 10)])

    primera = _reservar(
        api, cabeceras_cliente, sucursal_id=chica, lineas=[(variantes[0], 1)]
    ).json()

    # El probador está tomado.
    assert _reservar(
        api, cabeceras_cliente, sucursal_id=chica, lineas=[(variantes[0], 1)]
    ).status_code == 409

    api.patch(_cancelacion(primera["id"]), headers=cabeceras_cliente, json={})

    # Y ahora se puede.
    tercera = _reservar(
        api, cabeceras_cliente, sucursal_id=chica, lineas=[(variantes[0], 1)]
    )
    assert tercera.status_code == 201, tercera.text


# --- Excepcion E10: estados que no se cancelan ---------------------------

def test_no_se_cancela_dos_veces(
    api: TestClient, cabeceras_cliente: dict[str, str], reserva: dict
) -> None:
    """Excepción E10, y el mensaje distingue por qué."""
    primera = api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})
    assert primera.status_code == 200

    segunda = api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})
    assert segunda.status_code == 409
    assert "ya estaba cancelada" in segunda.json()["detail"]


def test_no_se_cancela_una_reserva_ya_atendida(
    api: TestClient, cabeceras_cliente: dict[str, str], db, reserva: dict
) -> None:
    """El RF29 dice «mientras no haya sido atendida», y ese es el límite.

    CU-24 todavía no existe, así que el estado se fuerza sobre la fila; lo que
    importa probar es que CU-23 lo respeta.
    """
    fila = db.scalar(select(Reserva).where(Reserva.id == reserva["id"]))
    fila.estado = "ATENDIDA"
    db.commit()

    respuesta = api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})
    assert respuesta.status_code == 409
    assert "ya fue atendida" in respuesta.json()["detail"]


def test_una_reserva_preparada_todavia_se_puede_cancelar(
    api: TestClient, cabeceras_cliente: dict[str, str], db, reserva: dict
) -> None:
    """PREPARADA sigue viva: el Encargado ya juntó las prendas, pero el cliente
    aún no llegó y el RF29 le deja cancelar hasta que se atienda."""
    fila = db.scalar(select(Reserva).where(Reserva.id == reserva["id"]))
    fila.estado = "PREPARADA"
    db.commit()

    respuesta = api.patch(_cancelacion(reserva["id"]), headers=cabeceras_cliente, json={})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "CANCELADA"


# --- Concurrencia: la doble cancelacion ----------------------------------

def test_dos_cancelaciones_simultaneas_no_inventan_mercaderia(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    fabrica_sesiones,
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """El riesgo R5 visto del otro lado.

    Allí era vender de más; acá es **inventar mercadería**. Si el cliente pulsa
    «cancelar» dos veces —o lo hace desde la web y el teléfono a la vez—, las
    dos peticiones leerían la reserva en PENDIENTE, las dos pasarían la
    comprobación de estado y las dos liberarían el stock: el saldo terminaría
    con 13 unidades de una prenda de la que solo hay 10.

    Con el `FOR UPDATE` sobre la reserva, la segunda espera, vuelve a leer
    —ahora CANCELADA— y se rechaza sola.
    """
    from app.modules.reservas import service as reservas_service
    from app.modules.reservas.schemas import CancelarReservaIn

    # El usuario de la reserva: el cliente de las pruebas es el segundo usuario.
    from app.modules.seguridad.models import Cliente

    cliente = db.scalar(select(Cliente).where(Cliente.id == reserva["cliente_id"]))
    usuario_id = cliente.usuario_id

    def cancelar() -> str:
        sesion = fabrica_sesiones()
        try:
            reservas_service.cancelar_reserva(
                sesion,
                reserva["id"],
                CancelarReservaIn(motivo=None),
                usuario_id=usuario_id,
            )
            return "ok"
        except reservas_service.ReservaNoCancelable:
            sesion.rollback()
            return "ya-cancelada"
        finally:
            sesion.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = sorted(f.result() for f in [pool.submit(cancelar), pool.submit(cancelar)])

    assert resultados == ["ok", "ya-cancelada"], (
        f"el stock se liberó dos veces: {resultados}"
    )

    existencia = db.scalar(
        select(Existencia).where(
            Existencia.variante_id == variantes[0], Existencia.sucursal_id == sucursal
        )
    )
    db.refresh(existencia)
    assert existencia.cantidad_disponible == 10, "se inventaron unidades"
    assert existencia.cantidad_reservada == 0

    # Y una sola LIBERACION por prenda, no dos.
    liberaciones = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "LIBERACION"}
    ).json()
    assert liberaciones["total"] == 2
