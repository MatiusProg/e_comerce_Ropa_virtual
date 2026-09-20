"""CU-30 · Abrir y cerrar caja.

Es la **puerta de CU-31**: la base exige `turno_caja_id` en toda venta
presencial (`ck_venta_turno_segun_canal`), así que sin un turno abierto no se
puede cobrar en el mostrador. Por eso este caso de uso va antes.

Lo que más importa cubrir
-------------------------
Abrir un turno es escribir una fila; lo que este módulo aporta es el **arqueo**,
y ahí es donde se puede equivocar en silencio:

- **Tarjeta y QR no entran al cajón.** Sumarlos al esperado haría que todo
  turno con un pago con tarjeta apareciera descuadrado — y un arqueo que
  siempre descuadra enseña a ignorarlo, que es peor que no tenerlo.
- **Una venta cancelada no se cobró**, aunque quede colgada del turno.
- **El descuadre NO se rechaza.** Es justamente lo que hay que registrar. Una
  validación que exija que cuadre impide anotar el problema.
- **Una caja, un turno abierto.** Dos turnos a la vez hacen que el arqueo no
  cierre nunca: no se sabría a cuál imputar lo cobrado.
- **Cierra quien abrió.** El arqueo le atribuye un descuadre a una persona;
  que otro lo cierre significa anotarle el faltante a quien no estuvo ahí.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

CAJAS = "/api/v1/caja/cajas"
TURNOS = "/api/v1/caja/turnos"
MIO = "/api/v1/caja/turnos/mio"
EMPLEADOS = "/api/v1/organizacion/empleados"
SUCURSALES = "/api/v1/organizacion/sucursales"


@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    r = api.post(
        SUCURSALES,
        headers=cabeceras_admin,
        json={
            "ciudad_id": 1,
            "nombre": "Centro",
            "direccion": "Avenida Centro 100",
            "telefono": None,
            "horario_apertura": "09:00",
            "horario_cierre": "20:00",
            "capacidad_vestidores": 2,
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _cajero(
    api: TestClient, admin: dict[str, str], sucursal_id: int, sufijo: str = ""
) -> dict[str, str]:
    correo = f"cajero{sufijo}@violetboutique.bo"
    clave = "Cajero1234"
    r = api.post(
        EMPLEADOS,
        headers=admin,
        json={
            "nombres": "Ana",
            "apellidos": f"Caja{sufijo or '1'}",
            "correo": correo,
            "contrasena": clave,
            "documento": f"900000{sufijo or '1'}",
            "telefono": "70000001",
            "cargo": "CAJERO",
            "sucursal_id": sucursal_id,
            "fecha_ingreso": (date.today() - timedelta(days=10)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    entrada = api.post("/api/v1/auth/login", json={"correo": correo, "contrasena": clave})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


@pytest.fixture
def cajero(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int) -> dict:
    return _cajero(api, cabeceras_admin, sucursal)


@pytest.fixture
def caja(db, sucursal: int) -> int:
    """Una caja en la sucursal.

    Se crea en la base y no por la API porque **el alta de cajas no tiene
    endpoint**: CU-30 es abrir y cerrar turnos, no administrar el catálogo de
    cajas. Eso es del administrador y todavía no está construido; la prueba lo
    deja explícito en vez de esconderlo.
    """
    from app.modules.ventas.models import Caja

    fila = Caja(sucursal_id=sucursal, nombre="Caja 1", activa=True)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila.id


def _abrir(api: TestClient, cab: dict, caja_id: int, monto: str = "100.00"):
    return api.post(
        TURNOS, headers=cab, json={"caja_id": caja_id, "monto_apertura": monto}
    )


def _venta(
    db,
    *,
    turno_id: int,
    sucursal_id: int,
    metodo: str,
    total: str,
    estado: str = "PAGADA",
    codigo: str,
) -> None:
    """Una venta presencial colgada del turno, escrita directo en la base.

    CU-31 no existe todavía: no hay endpoint que registre una venta presencial.
    Escribirla a mano es lo único que permite probar el arqueo hoy, y es
    deliberado — cuando CU-31 exista, estas pruebas siguen valiendo porque
    verifican la CUENTA, no el camino por el que entró la venta.
    """
    from app.modules.ventas.models import Venta

    db.add(
        Venta(
            codigo=codigo,
            canal="PRESENCIAL",
            estado=estado,
            sucursal_id=sucursal_id,
            turno_caja_id=turno_id,
            metodo_pago=metodo,
            subtotal=Decimal(total),
            descuento=Decimal("0"),
            total=Decimal(total),
        )
    )
    db.commit()


# --- Abrir ------------------------------------------------------------------


def test_al_empezar_el_dia_no_hay_turno_y_eso_no_es_un_error(
    api: TestClient, cajero: dict, caja: int
) -> None:
    r = api.get(MIO, headers=cajero)
    assert r.status_code == 200
    assert r.json() is None


def test_el_cajero_abre_su_turno(api: TestClient, cajero: dict, caja: int) -> None:
    r = _abrir(api, cajero, caja, "250.50")
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert Decimal(cuerpo["monto_apertura"]) == Decimal("250.50")
    # Sin ventas todavía: el esperado es lo que se puso al abrir.
    assert Decimal(cuerpo["monto_esperado"]) == Decimal("250.50")
    assert cuerpo["cerrado_en"] is None
    assert cuerpo["caja_nombre"] == "Caja 1"

    assert api.get(MIO, headers=cajero).json()["id"] == cuerpo["id"]


def test_se_puede_abrir_con_cero(api: TestClient, cajero: dict, caja: int) -> None:
    """Una caja que arranca vacía es normal, no un error de carga."""
    assert _abrir(api, cajero, caja, "0").status_code == 201


def test_un_monto_negativo_lo_rechaza_el_esquema(
    api: TestClient, cajero: dict, caja: int
) -> None:
    assert _abrir(api, cajero, caja, "-5").status_code == 422


def test_UNA_CAJA_UN_TURNO_ABIERTO(
    api: TestClient, cabeceras_admin: dict, cajero: dict, caja: int, sucursal: int
) -> None:
    """Dos turnos a la vez hacen que el arqueo no cierre nunca.

    Y el mensaje tiene que EXPLICAR, no reventar: el índice único parcial ya
    impide el dato malo, pero sin el bloqueo el segundo cajero vería un error
    de integridad en vez de «esa caja ya está abierta».
    """
    assert _abrir(api, cajero, caja).status_code == 201

    otro = _cajero(api, cabeceras_admin, sucursal, sufijo="2")
    r = _abrir(api, otro, caja)
    assert r.status_code == 409
    assert "ya tiene un turno abierto" in r.json()["detail"].lower()


def test_UNA_PERSONA_UN_TURNO(
    api: TestClient, cajero: dict, caja: int, db, sucursal: int
) -> None:
    from app.modules.ventas.models import Caja

    otra = Caja(sucursal_id=sucursal, nombre="Caja 2", activa=True)
    db.add(otra)
    db.commit()
    db.refresh(otra)

    assert _abrir(api, cajero, caja).status_code == 201
    r = _abrir(api, cajero, otra.id)
    assert r.status_code == 409
    assert "ya tiene un turno abierto" in r.json()["detail"].lower()


def test_la_caja_ocupada_se_informa_pero_no_desaparece(
    api: TestClient, cajero: dict, caja: int
) -> None:
    """El cajero necesita saber que existe y está tomada, no que no está."""
    antes = api.get(CAJAS, headers=cajero).json()
    assert antes[0]["ocupada"] is False

    _abrir(api, cajero, caja)

    despues = api.get(CAJAS, headers=cajero).json()
    assert len(despues) == 1
    assert despues[0]["ocupada"] is True


# --- El arqueo --------------------------------------------------------------


def test_SOLO_EL_EFECTIVO_SUMA_AL_ESPERADO(
    api: TestClient, cajero: dict, caja: int, db, sucursal: int
) -> None:
    """Es la regla central del módulo.

    Tarjeta y QR no entran al cajón. Si sumaran, todo turno con un pago con
    tarjeta aparecería descuadrado.
    """
    turno = _abrir(api, cajero, caja, "100.00").json()["id"]

    _venta(db, turno_id=turno, sucursal_id=sucursal, metodo="EFECTIVO",
           total="200.00", codigo="VB-CAJA-1")
    _venta(db, turno_id=turno, sucursal_id=sucursal, metodo="TARJETA",
           total="500.00", codigo="VB-CAJA-2")
    _venta(db, turno_id=turno, sucursal_id=sucursal, metodo="QR",
           total="300.00", codigo="VB-CAJA-3")

    cuerpo = api.get(MIO, headers=cajero).json()
    assert Decimal(cuerpo["efectivo_cobrado"]) == Decimal("200.00")
    assert Decimal(cuerpo["monto_esperado"]) == Decimal("300.00")  # 100 + 200

    # El desglose sí muestra los tres: el cierre se tiene que poder revisar.
    metodos = {l["metodo"]: Decimal(l["total"]) for l in cuerpo["por_metodo"]}
    assert metodos == {
        "EFECTIVO": Decimal("200.00"),
        "TARJETA": Decimal("500.00"),
        "QR": Decimal("300.00"),
    }


def test_una_venta_CANCELADA_no_suma(
    api: TestClient, cajero: dict, caja: int, db, sucursal: int
) -> None:
    turno = _abrir(api, cajero, caja, "100.00").json()["id"]
    _venta(db, turno_id=turno, sucursal_id=sucursal, metodo="EFECTIVO",
           total="400.00", estado="CANCELADA", codigo="VB-CAJA-4")

    cuerpo = api.get(MIO, headers=cajero).json()
    assert Decimal(cuerpo["efectivo_cobrado"]) == Decimal("0")
    assert Decimal(cuerpo["monto_esperado"]) == Decimal("100.00")


# --- Cerrar -----------------------------------------------------------------


def test_cerrar_guarda_LOS_DOS_numeros_y_la_diferencia(
    api: TestClient, cajero: dict, caja: int, db, sucursal: int
) -> None:
    """Un descuadre sin los dos números no se puede auditar."""
    turno = _abrir(api, cajero, caja, "100.00").json()["id"]
    _venta(db, turno_id=turno, sucursal_id=sucursal, metodo="EFECTIVO",
           total="250.00", codigo="VB-CAJA-5")

    r = api.post(f"{TURNOS}/{turno}/cierre", headers=cajero,
                 json={"monto_cierre": "340.00"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert Decimal(cuerpo["monto_esperado"]) == Decimal("350.00")
    assert Decimal(cuerpo["monto_cierre"]) == Decimal("340.00")
    assert Decimal(cuerpo["diferencia"]) == Decimal("-10.00")
    assert cuerpo["cerrado_en"] is not None


def test_un_DESCUADRE_no_se_rechaza(
    api: TestClient, cajero: dict, caja: int
) -> None:
    """Es justamente lo que hay que registrar.

    Una validación que exija que cuadre impide anotar el problema, y entonces
    el faltante se resuelve fuera del sistema —o no se resuelve—.
    """
    turno = _abrir(api, cajero, caja, "100.00").json()["id"]
    r = api.post(f"{TURNOS}/{turno}/cierre", headers=cajero,
                 json={"monto_cierre": "0"})
    assert r.status_code == 200
    assert Decimal(r.json()["diferencia"]) == Decimal("-100.00")


def test_sobrante_tambien_se_registra(
    api: TestClient, cajero: dict, caja: int
) -> None:
    turno = _abrir(api, cajero, caja, "100.00").json()["id"]
    r = api.post(f"{TURNOS}/{turno}/cierre", headers=cajero,
                 json={"monto_cierre": "130.00"})
    assert Decimal(r.json()["diferencia"]) == Decimal("30.00")


def test_CIERRA_QUIEN_ABRIO(
    api: TestClient, cabeceras_admin: dict, cajero: dict, caja: int, sucursal: int
) -> None:
    """El arqueo le atribuye un descuadre a una persona.

    Que otro cajero pueda cerrar el turno ajeno significa anotarle el faltante
    a quien no estuvo en la caja.
    """
    turno = _abrir(api, cajero, caja).json()["id"]
    otro = _cajero(api, cabeceras_admin, sucursal, sufijo="3")

    r = api.post(f"{TURNOS}/{turno}/cierre", headers=otro,
                 json={"monto_cierre": "100.00"})
    assert r.status_code == 403


def test_no_se_cierra_dos_veces(api: TestClient, cajero: dict, caja: int) -> None:
    turno = _abrir(api, cajero, caja).json()["id"]
    api.post(f"{TURNOS}/{turno}/cierre", headers=cajero, json={"monto_cierre": "100"})
    r = api.post(f"{TURNOS}/{turno}/cierre", headers=cajero, json={"monto_cierre": "100"})
    assert r.status_code == 409


def test_despues_de_cerrar_la_caja_queda_libre(
    api: TestClient, cajero: dict, caja: int
) -> None:
    turno = _abrir(api, cajero, caja).json()["id"]
    api.post(f"{TURNOS}/{turno}/cierre", headers=cajero, json={"monto_cierre": "100"})

    assert api.get(MIO, headers=cajero).json() is None
    assert api.get(CAJAS, headers=cajero).json()[0]["ocupada"] is False
    assert _abrir(api, cajero, caja).status_code == 201


# --- Quién puede ------------------------------------------------------------


def test_un_cliente_no_abre_caja(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.get(CAJAS, headers=cabeceras_cliente).status_code == 403


def test_el_administrador_tampoco(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """No está en una sucursal: un turno que nadie abrió no tiene arqueo."""
    assert api.get(CAJAS, headers=cabeceras_admin).status_code == 403


def test_sin_token_no_hay_caja(api: TestClient) -> None:
    assert api.get(CAJAS).status_code == 401
