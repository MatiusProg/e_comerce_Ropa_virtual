"""CU-25 · Expirar reservas vencidas.

Cubre el flujo y las condiciones de la ficha
(docs/entregas/ciclo-2/cu-25-expirar-reservas-vencidas.md).

Es el único caso de uso del sistema cuyo actor es **A6, el Sistema**: no lo
inicia una persona. Realiza el **RF30**: sin él, cada reserva no atendida
inmoviliza inventario de forma indefinida.

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **La tolerancia se respeta.** Una reserva cuya franja terminó hace un rato
  **no** expira todavía: `RESERVA_VIGENCIA_HORAS` existe para el cliente que
  llega tarde, y expirarla antes le quitaría la prenda mientras va en camino.
- **Es idempotente.** Correrla dos veces no libera el stock dos veces — que
  sería inventar mercadería, el mismo problema que la doble cancelación.
- **No toca las que no le tocan**: ni las canceladas, ni las atendidas, ni las
  que siguen en su franja.
- **Los movimientos quedan sin usuario**, que es para lo que esa columna admite
  nulo.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.modules.reservas.models import Reserva

RESERVAS = "/api/v1/reservas"
PANEL = "/api/v1/sucursal/reservas"
EXPIRACION = "/api/v1/mantenimiento/reservas/expiracion"
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


def _envejecer(db, reserva_id: int, *, horas: float) -> None:
    """Mueve la franja de una reserva al pasado.

    Es la única forma de probar una expiración sin esperar un día real: se crea
    la reserva por la puerta normal —CU-22, con todas sus validaciones— y recién
    después se le corre el reloj. Escribir la fila a mano en lugar de reservar
    de verdad haría que esta prueba no se enterara si CU-22 dejara de apartar
    stock.
    """
    fila = db.scalar(select(Reserva).where(Reserva.id == reserva_id))
    ahora = datetime.now(timezone.utc)
    fila.franja_fin = ahora - timedelta(hours=horas)
    fila.franja_inicio = fila.franja_fin - timedelta(hours=1)
    db.commit()


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


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_dispara_la_expiracion(api: TestClient) -> None:
    assert api.post(EXPIRACION).status_code == 401


def test_solo_el_administrador_dispara_la_expiracion(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """Es mantenimiento del sistema, no una operación sobre una reserva."""
    assert api.post(EXPIRACION, headers=cabeceras_cliente).status_code == 403


# --- La tolerancia -------------------------------------------------------

def test_una_reserva_vigente_no_expira(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, reserva: dict
) -> None:
    """La franja es de mañana: no hay nada que expirar."""
    respuesta = api.post(EXPIRACION, headers=cabeceras_admin)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["encontradas"] == 0
    assert cuerpo["expiradas"] == 0
    assert cuerpo["unidades_liberadas"] == 0

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert sum(f["cantidad_reservada"] for f in saldo.values()) == 5


def test_una_reserva_recien_vencida_todavia_no_expira(
    api: TestClient, cabeceras_admin: dict[str, str], db, sucursal: int, reserva: dict
) -> None:
    """**La prueba de la tolerancia.**

    La franja terminó hace una hora, pero `RESERVA_VIGENCIA_HORAS` no se cumplió
    todavía. Expirarla ahora le quitaría la prenda al cliente que llega tarde y
    va en camino — que es exactamente para lo que esa tolerancia existe.
    """
    assert settings.RESERVA_VIGENCIA_HORAS > 1, "esta prueba supone tolerancia > 1h"
    _envejecer(db, reserva["id"], horas=1)

    cuerpo = api.post(EXPIRACION, headers=cabeceras_admin).json()
    assert cuerpo["expiradas"] == 0

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert sum(f["cantidad_reservada"] for f in saldo.values()) == 5


def test_pasada_la_tolerancia_la_reserva_expira_y_devuelve_el_stock(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Flujo principal, y el **RF30**."""
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)

    respuesta = api.post(EXPIRACION, headers=cabeceras_admin)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["encontradas"] == 1
    assert cuerpo["expiradas"] == 1
    assert cuerpo["unidades_liberadas"] == 5
    assert cuerpo["reservas"] == [reserva["id"]]
    # El corte viaja para que la pantalla pueda explicar por qué una reserva de
    # ayer todavía no expiró.
    assert cuerpo["corte"]

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 10
    assert saldo[variantes[1]]["cantidad_disponible"] == 5
    assert all(f["cantidad_reservada"] == 0 for f in saldo.values())

    fila = db.scalar(select(Reserva).where(Reserva.id == reserva["id"]))
    db.refresh(fila)
    assert fila.estado == "EXPIRADA"
    assert "venció" in fila.observacion


def test_los_movimientos_de_expiracion_no_tienen_usuario(
    api: TestClient, cabeceras_admin: dict[str, str], db, reserva: dict
) -> None:
    """El actor es A6, el Sistema: no hay persona detrás.

    Es exactamente para lo que `movimiento_inventario.usuario_id` admite nulo,
    según la nota del modelo.
    """
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)
    api.post(EXPIRACION, headers=cabeceras_admin)

    liberaciones = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "LIBERACION"}
    ).json()
    assert liberaciones["total"] == 2
    for movimiento in liberaciones["items"]:
        assert movimiento["usuario_id"] is None
        assert movimiento["usuario"] is None
        assert "expirada sin atencion" in movimiento["motivo"]


# --- Idempotencia --------------------------------------------------------

def test_correrla_dos_veces_no_libera_el_stock_dos_veces(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Es el mismo problema que la doble cancelación: inventar mercadería.

    Una tarea programada se dispara sola y se puede solapar consigo misma, así
    que ser idempotente no es un lujo.
    """
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)

    primera = api.post(EXPIRACION, headers=cabeceras_admin).json()
    segunda = api.post(EXPIRACION, headers=cabeceras_admin).json()

    assert primera["expiradas"] == 1
    assert segunda["expiradas"] == 0
    assert segunda["unidades_liberadas"] == 0

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 10, "se liberó dos veces"


# --- Lo que NO tiene que tocar -------------------------------------------

def test_no_expira_una_reserva_ya_cancelada(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """Ya liberó su stock al cancelarse: volver a liberarlo lo duplicaría."""
    api.patch(f"{RESERVAS}/{reserva['id']}/cancelacion", headers=cabeceras_cliente, json={})
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)

    cuerpo = api.post(EXPIRACION, headers=cabeceras_admin).json()
    assert cuerpo["expiradas"] == 0

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 10


def test_no_expira_una_reserva_ya_atendida(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """El cliente vino y se llevó las prendas: expirarla las devolvería al
    inventario, y no están."""
    api.patch(
        f"{PANEL}/{reserva['id']}/atencion",
        headers=cabeceras_admin,
        json={
            "resultados": [
                {"detalle_id": linea["id"], "resultado": "LLEVA"}
                for linea in reserva["lineas"]
            ]
        },
    )
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)

    cuerpo = api.post(EXPIRACION, headers=cabeceras_admin).json()
    assert cuerpo["expiradas"] == 0

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo[variantes[0]]["cantidad_disponible"] == 7, "se inventaron prendas"


def test_una_preparada_tambien_expira(
    api: TestClient, cabeceras_admin: dict[str, str], db, sucursal: int, reserva: dict
) -> None:
    """PREPARADA sigue reteniendo stock: que el Encargado haya juntado las
    prendas no significa que el cliente haya venido."""
    api.patch(f"{PANEL}/{reserva['id']}/preparacion", headers=cabeceras_admin)
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)

    cuerpo = api.post(EXPIRACION, headers=cabeceras_admin).json()
    assert cuerpo["expiradas"] == 1

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert all(f["cantidad_reservada"] == 0 for f in saldo.values())


def test_una_expirada_libera_el_probador(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """El control de capacidad de CU-22 solo cuenta las vivas."""
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)
    api.post(EXPIRACION, headers=cabeceras_admin)

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


def test_el_invariante_se_sostiene_despues_de_expirar(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    db,
    sucursal: int,
    variantes: list[int],
    reserva: dict,
) -> None:
    """**D4** sobre el ciclo INGRESO → RESERVA → LIBERACION por expiración."""
    _envejecer(db, reserva["id"], horas=settings.RESERVA_VIGENCIA_HORAS + 1)
    api.post(EXPIRACION, headers=cabeceras_admin)

    historial = api.get(
        MOVIMIENTOS,
        headers=cabeceras_admin,
        params={"variante_id": variantes[0], "tamano": 100},
    ).json()
    suma = sum(m["cantidad"] for m in historial["items"])

    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)[variantes[0]]
    assert suma == saldo["cantidad_disponible"] == 10
    assert saldo["cantidad_reservada"] == 0
