"""CU-06 · Gestionar empleados.

Cubre el flujo principal, los tres flujos alternativos y las tres excepciones de
la ficha del caso de uso (docs/entregas/ciclo-1/cap-1-captura-requisitos.md).

Las pruebas que importan son las del vínculo con P1: el cargo decide el rol de
la cuenta, y tanto el rol como la sucursal viajan DENTRO del token. Reasignar o
dar de baja sin revocar las sesiones dejaría al empleado operando con el ámbito
anterior hasta que su token venza.

Los fixtures propios de este caso de uso viven acá y no en conftest.py: el CU-07
se desarrolla en paralelo y así no compartimos archivo.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

EMPLEADOS = "/api/v1/organizacion/empleados"
SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"

HOY = date.today()
INGRESO = (HOY - timedelta(days=30)).isoformat()


def _crear_sucursal(
    api: TestClient, admin: dict[str, str], *, nombre: str, activa: bool = True
) -> int:
    ciudades = api.get(CIUDADES, headers=admin)
    assert ciudades.status_code == 200, ciudades.text
    ciudad_id = ciudades.json()[0]["id"]

    respuesta = api.post(
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
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    """Una sucursal activa. Es precondición del caso de uso."""
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


def _alta(
    api: TestClient,
    admin: dict[str, str],
    *,
    sucursal_id: int,
    documento: str = "5551234",
    cargo: str = "ENCARGADO",
    correo: str = "encargado.centro@fashionstore.bo",
) -> dict:
    respuesta = api.post(
        EMPLEADOS,
        headers=admin,
        json={
            "documento": documento,
            "telefono": "70099887",
            "cargo": cargo,
            "sucursal_id": sucursal_id,
            "fecha_ingreso": INGRESO,
            "nombres": "Rosa",
            "apellidos": "Mendoza",
            "correo": correo,
            "contrasena": "Trabajo123",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _token(api: TestClient, correo: str, contrasena: str) -> str:
    respuesta = api.post(
        "/api/v1/auth/login", json={"correo": correo, "contrasena": contrasena}
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_listan_empleados(api: TestClient) -> None:
    assert api.get(EMPLEADOS).status_code == 401


def test_un_cliente_no_entra_a_la_gestion_de_empleados(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    """El actor de CU-06 es el Administrador."""
    assert api.get(EMPLEADOS, headers=cabeceras_cliente).status_code == 403


# --- Flujo principal, pasos 4 a 7 ----------------------------------------

def test_registrar_un_empleado_crea_su_cuenta_con_el_rol_del_cargo(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """Paso 7: la cuenta y la ficha se crean juntas, y el cargo fija el rol."""
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)

    assert empleado["cargo"] == "ENCARGADO"
    assert empleado["sucursal"] == "Centro"
    assert empleado["documento"] == "5551234"
    assert empleado["activo"] is True
    assert empleado["usuario_activo"] is True

    # La cuenta existe y entra con el rol del cargo.
    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "encargado.centro@fashionstore.bo", "contrasena": "Trabajo123"},
    )
    assert entrada.status_code == 200
    assert entrada.json()["usuario"]["rol"] == "ENCARGADO"
    # Y su ámbito de sucursal viaja resuelto: es lo que da sentido al caso de uso.
    assert entrada.json()["usuario"]["sucursal_id"] == sucursal


def test_excepcion_e1_documento_ya_registrado(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    _alta(api, cabeceras_admin, sucursal_id=sucursal)

    respuesta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "5551234",
            "telefono": None,
            "cargo": "CAJERO",
            "sucursal_id": sucursal,
            "fecha_ingreso": INGRESO,
            "nombres": "Otro",
            "apellidos": "Distinto",
            "correo": "otro.distinto@fashionstore.bo",
            "contrasena": "Trabajo123",
        },
    )
    assert respuesta.status_code == 409


def test_excepcion_e2_no_se_asigna_personal_a_una_sucursal_dada_de_baja(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    inactiva = _crear_sucursal(api, cabeceras_admin, nombre="Cerrada", activa=False)

    respuesta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "7778888",
            "telefono": None,
            "cargo": "CAJERO",
            "sucursal_id": inactiva,
            "fecha_ingreso": INGRESO,
            "nombres": "Nadie",
            "apellidos": "Aqui",
            "correo": "nadie.aqui@fashionstore.bo",
            "contrasena": "Trabajo123",
        },
    )
    assert respuesta.status_code == 422
    assert "baja" in respuesta.json()["detail"].lower()


def test_excepcion_e3_si_falla_el_alta_no_queda_la_cuenta_a_medias(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """El documento repetido corta el alta DESPUÉS de validar la sucursal.

    Lo que se verifica es que la cuenta no quede creada por su cuenta: si la
    transacción no fuera única, el correo quedaría tomado y el segundo intento
    con datos corregidos fallaría por un motivo que el administrador no puede
    entender.
    """
    _alta(api, cabeceras_admin, sucursal_id=sucursal)

    api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "5551234",  # repetido: el alta se cae
            "telefono": None,
            "cargo": "CAJERO",
            "sucursal_id": sucursal,
            "fecha_ingreso": INGRESO,
            "nombres": "Nuevo",
            "apellidos": "Cajero",
            "correo": "nuevo.cajero@fashionstore.bo",
            "contrasena": "Trabajo123",
        },
    )

    # El correo del intento fallido tiene que seguir libre.
    respuesta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "9990000",
            "telefono": None,
            "cargo": "CAJERO",
            "sucursal_id": sucursal,
            "fecha_ingreso": INGRESO,
            "nombres": "Nuevo",
            "apellidos": "Cajero",
            "correo": "nuevo.cajero@fashionstore.bo",
            "contrasena": "Trabajo123",
        },
    )
    assert respuesta.status_code == 201, respuesta.text


# --- Flujo alternativo 3c: vincular a un usuario existente ---------------

def test_flujo_3c_vincular_una_cuenta_existente(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, db
) -> None:
    """El rol de la cuenta pasa a ser el del cargo."""
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.modules.seguridad.models import Rol, Usuario

    rol_cajero = db.scalar(select(Rol).where(Rol.nombre == "CAJERO"))
    db.add(
        Usuario(
            correo="suelto@fashionstore.bo",
            hash_contrasena=hash_password("Trabajo123"),
            nombres="Cuenta",
            apellidos="Suelta",
            rol_id=rol_cajero.id,
        )
    )
    db.commit()

    vinculables = api.get(f"{EMPLEADOS}/usuarios-vinculables", headers=cabeceras_admin)
    assert vinculables.status_code == 200
    candidato = next(
        u for u in vinculables.json() if u["correo"] == "suelto@fashionstore.bo"
    )

    respuesta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "1112223",
            "telefono": None,
            "cargo": "ENCARGADO",
            "sucursal_id": sucursal,
            "fecha_ingreso": INGRESO,
            "usuario_id": candidato["id"],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["correo"] == "suelto@fashionstore.bo"

    # El cargo mandó sobre el rol que tenía la cuenta.
    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "suelto@fashionstore.bo", "contrasena": "Trabajo123"},
    )
    assert entrada.json()["usuario"]["rol"] == "ENCARGADO"
    assert entrada.json()["usuario"]["sucursal_id"] == sucursal


def test_los_clientes_no_aparecen_como_vinculables(
    api: TestClient, cabeceras_admin: dict[str, str], cabeceras_cliente: dict[str, str]
) -> None:
    """Un empleado no puede ser la misma cuenta con la que alguien compra."""
    respuesta = api.get(f"{EMPLEADOS}/usuarios-vinculables", headers=cabeceras_admin)
    correos = [u["correo"] for u in respuesta.json()]
    assert "ana.cliente@fashionstore.bo" not in correos


def test_una_cuenta_que_ya_es_empleado_deja_de_ser_vinculable(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)

    respuesta = api.get(f"{EMPLEADOS}/usuarios-vinculables", headers=cabeceras_admin)
    assert empleado["usuario_id"] not in [u["id"] for u in respuesta.json()]


def test_no_se_admiten_los_dos_caminos_del_alta_a_la_vez(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """O se indica una cuenta existente o los datos de una nueva, no ambas."""
    respuesta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "4445556",
            "telefono": None,
            "cargo": "CAJERO",
            "sucursal_id": sucursal,
            "fecha_ingreso": INGRESO,
            "usuario_id": 1,
            "correo": "ambiguo@fashionstore.bo",
            "nombres": "Ambi",
            "apellidos": "Guo",
            "contrasena": "Trabajo123",
        },
    )
    assert respuesta.status_code == 422


# --- Flujo alternativo 3a: editar y reasignar ----------------------------

def test_reasignar_de_sucursal_revoca_el_token_del_empleado(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """El `sucursal_id` viaja DENTRO del token.

    Sin revocar, el empleado reasignado seguiría operando sobre su sucursal
    anterior hasta que el token venza — ocho horas después. Es un agujero de
    ámbito, no una demora cosmética.
    """
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)
    suyo = {
        "Authorization": f"Bearer {_token(api, 'encargado.centro@fashionstore.bo', 'Trabajo123')}"
    }
    # El token sirve antes de la reasignación.
    assert api.get("/api/v1/auth/yo", headers=suyo).status_code == 200

    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}",
        headers=cabeceras_admin,
        json={"sucursal_id": otra},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["sucursal"] == "Norte"

    # Y deja de servir inmediatamente después.
    assert api.get("/api/v1/auth/yo", headers=suyo).status_code == 401

    # Al volver a entrar, el ámbito nuevo ya viaja en el token.
    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "encargado.centro@fashionstore.bo", "contrasena": "Trabajo123"},
    )
    assert entrada.json()["usuario"]["sucursal_id"] == otra


def test_cambiar_el_cargo_cambia_el_rol_de_la_cuenta(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}", headers=cabeceras_admin, json={"cargo": "CAJERO"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["cargo"] == "CAJERO"

    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "encargado.centro@fashionstore.bo", "contrasena": "Trabajo123"},
    )
    assert entrada.json()["usuario"]["rol"] == "CAJERO"


def test_editar_datos_sin_tocar_el_ambito_no_revoca_la_sesion(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """Corregir un teléfono no tiene por qué echar al empleado del sistema."""
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)
    suyo = {
        "Authorization": f"Bearer {_token(api, 'encargado.centro@fashionstore.bo', 'Trabajo123')}"
    }

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}",
        headers=cabeceras_admin,
        json={"telefono": "71234567"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["telefono"] == "71234567"
    assert api.get("/api/v1/auth/yo", headers=suyo).status_code == 200


def test_no_se_puede_reasignar_a_una_sucursal_dada_de_baja(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)
    inactiva = _crear_sucursal(api, cabeceras_admin, nombre="Cerrada", activa=False)

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}",
        headers=cabeceras_admin,
        json={"sucursal_id": inactiva},
    )
    assert respuesta.status_code == 422


def test_editar_sin_cambiar_el_documento_no_choca_consigo_mismo(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """Sin excluir al propio empleado, guardar diría que su documento ya existe."""
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}",
        headers=cabeceras_admin,
        json={"documento": "5551234", "telefono": "70000000"},
    )
    assert respuesta.status_code == 200


# --- Flujo alternativo 3b: dar de baja -----------------------------------

def test_dar_de_baja_desactiva_la_cuenta_y_corta_el_acceso(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)
    suyo = {
        "Authorization": f"Bearer {_token(api, 'encargado.centro@fashionstore.bo', 'Trabajo123')}"
    }

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}/baja", headers=cabeceras_admin, json={}
    )
    assert respuesta.status_code == 200

    cuerpo = respuesta.json()
    assert cuerpo["activo"] is False
    assert cuerpo["usuario_activo"] is False
    assert cuerpo["fecha_baja"] == HOY.isoformat()

    # El token vigente deja de servir...
    assert api.get("/api/v1/auth/yo", headers=suyo).status_code == 401
    # ...y tampoco puede volver a entrar.
    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "encargado.centro@fashionstore.bo", "contrasena": "Trabajo123"},
    )
    assert entrada.status_code == 403


def test_no_se_da_de_baja_dos_veces(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)
    api.patch(f"{EMPLEADOS}/{empleado['id']}/baja", headers=cabeceras_admin, json={})

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}/baja", headers=cabeceras_admin, json={}
    )
    assert respuesta.status_code == 409


def test_la_baja_no_puede_ser_anterior_al_ingreso(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    """Lo exige el CHECK ck_empleado_fechas; se rechaza antes de llegar ahí."""
    empleado = _alta(api, cabeceras_admin, sucursal_id=sucursal)

    respuesta = api.patch(
        f"{EMPLEADOS}/{empleado['id']}/baja",
        headers=cabeceras_admin,
        json={"fecha_baja": (HOY - timedelta(days=365)).isoformat()},
    )
    assert respuesta.status_code == 422


# --- Paso 2: listado y filtros -------------------------------------------

def test_el_listado_filtra_por_sucursal_cargo_y_estado(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _alta(api, cabeceras_admin, sucursal_id=sucursal)
    cajero = _alta(
        api,
        cabeceras_admin,
        sucursal_id=otra,
        documento="2223334",
        cargo="CAJERO",
        correo="cajero.norte@fashionstore.bo",
    )

    por_sucursal = api.get(
        EMPLEADOS, headers=cabeceras_admin, params={"sucursal_id": otra}
    )
    assert [e["id"] for e in por_sucursal.json()] == [cajero["id"]]

    por_cargo = api.get(EMPLEADOS, headers=cabeceras_admin, params={"cargo": "CAJERO"})
    assert [e["id"] for e in por_cargo.json()] == [cajero["id"]]

    api.patch(f"{EMPLEADOS}/{cajero['id']}/baja", headers=cabeceras_admin, json={})
    activos = api.get(EMPLEADOS, headers=cabeceras_admin, params={"activo": True})
    assert cajero["id"] not in [e["id"] for e in activos.json()]

    dados_de_baja = api.get(
        EMPLEADOS, headers=cabeceras_admin, params={"activo": False}
    )
    assert [e["id"] for e in dados_de_baja.json()] == [cajero["id"]]


def test_los_cargos_asignables_son_los_dos_del_check(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    respuesta = api.get(f"{EMPLEADOS}/cargos", headers=cabeceras_admin)
    assert respuesta.status_code == 200
    assert respuesta.json() == ["ENCARGADO", "CAJERO"]


def test_un_cargo_inventado_se_rechaza(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int
) -> None:
    respuesta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "documento": "6667778",
            "telefono": None,
            "cargo": "GERENTE",
            "sucursal_id": sucursal,
            "fecha_ingreso": INGRESO,
            "nombres": "Falso",
            "apellidos": "Cargo",
            "correo": "falso.cargo@fashionstore.bo",
            "contrasena": "Trabajo123",
        },
    )
    assert respuesta.status_code == 422
