"""2do parcial, desafío VI: el aislamiento entre empresas (RNF02, RNF11).

Estas pruebas corren con el rol `violet_app`, que NO se salta el RLS (ver el
fixture `motor_app` del conftest): lo que prueban es la política de la base, no
un filtro del código.

La primera es la guardiana: si mañana alguien agrega una tabla con
`empresa_id` y se olvida de su política, falla acá y no en producción.
"""

from datetime import date, time, timedelta

import psycopg
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.tenencia import CLAVE_EMPRESA, TABLAS_DE_EMPRESA, fijar_empresa, modo_plataforma
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.plataforma.models import ClienteEmpresa, Empresa, Suscripcion
from app.modules.seguridad.models import Cliente, Rol, Usuario

EMPRESA_A = 1  # la de las pruebas (conftest.EMPRESA_PRUEBAS)


@pytest.fixture
def empresa_b(db) -> int:
    """Una segunda empresa. `empresa` no tiene RLS: es de la plataforma."""
    existente = db.scalar(select(Empresa).where(Empresa.slug == "tienda-b"))
    if existente is not None:
        return existente.id
    empresa = Empresa(nombre="Tienda B", slug="tienda-b")
    db.add(empresa)
    db.flush()
    # CU-05: sin suscripción vigente, la empresa solo consulta.
    db.add(
        Suscripcion(
            empresa_id=empresa.id,
            plan_id=3,
            inicio=date.today() - timedelta(days=1),
            vencimiento=date.today() + timedelta(days=30),
        )
    )
    modo_plataforma(db)  # el WITH CHECK no deja escribir otra empresa
    db.commit()
    fijar_empresa(db, EMPRESA_A)
    return empresa.id


def _sucursal(nombre: str, ciudad_id: int, **extra) -> Sucursal:
    return Sucursal(
        ciudad_id=ciudad_id,
        nombre=nombre,
        direccion="Av. Siempre Viva 123",
        horario_apertura=time(9),
        horario_cierre=time(20),
        **extra,
    )


def _sesion_de(fabrica_sesiones, empresa_id: int | None) -> Session:
    sesion = fabrica_sesiones()
    sesion.info[CLAVE_EMPRESA] = empresa_id
    return sesion


def _ciudad(db) -> int:
    return db.scalar(select(Ciudad.id).where(Ciudad.nombre == "Santa Cruz"))


# --------------------------------------------------------------------------
#  La guardiana
# --------------------------------------------------------------------------
def test_toda_tabla_con_empresa_tiene_rls_con_force(motor):
    """Cada tabla con `empresa_id` tiene su política, y no se olvida ninguna.

    `usuario` es la única excepción: es de identidad, y el login la consulta
    antes de saber de qué empresa es la petición (ver app/core/tenencia.py).
    """
    with motor.connect() as conexion:
        con_columna = set(
            conexion.execute(
                text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND column_name = 'empresa_id'"
                )
            ).scalars()
        )
        estado = dict(
            conexion.execute(
                text(
                    "SELECT relname, relrowsecurity AND relforcerowsecurity FROM pg_class "
                    "WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace"
                )
            ).all()
        )
        con_politica = set(
            conexion.execute(
                text(
                    "SELECT tablename FROM pg_policies "
                    "WHERE policyname = 'aislamiento_empresa'"
                )
            ).scalars()
        )

    esperadas = con_columna - {"usuario"}
    assert esperadas == set(TABLAS_DE_EMPRESA), (
        "Tabla con empresa_id fuera de TABLAS_DE_EMPRESA, o al revés: "
        f"{esperadas ^ set(TABLAS_DE_EMPRESA)}"
    )
    sin_force = sorted(t for t in esperadas if not estado.get(t))
    assert not sin_force, f"Sin RLS con FORCE: {sin_force}"
    assert esperadas <= con_politica, f"Sin política: {sorted(esperadas - con_politica)}"


def test_el_rol_de_la_aplicacion_no_se_salta_el_rls(motor):
    with motor.connect() as conexion:
        bypass = conexion.execute(
            text("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'violet_app'")
        ).scalar_one()
    assert bypass is False


# --------------------------------------------------------------------------
#  La política
# --------------------------------------------------------------------------
def test_sin_contexto_no_se_ve_ninguna_fila(db, fabrica_sesiones):
    """Falla cerrado: sin empresa en la transacción, cero filas."""
    db.add(_sucursal("Centro", _ciudad(db)))
    db.commit()
    assert db.scalar(select(func.count()).select_from(Sucursal)) == 1

    with _sesion_de(fabrica_sesiones, None) as sesion:
        assert sesion.scalar(select(func.count()).select_from(Sucursal)) == 0


def test_cada_empresa_ve_solo_lo_suyo(db, fabrica_sesiones, empresa_b):
    ciudad = _ciudad(db)
    db.add(_sucursal("Centro", ciudad))
    db.commit()

    with _sesion_de(fabrica_sesiones, empresa_b) as sesion:
        assert sesion.scalar(select(func.count()).select_from(Sucursal)) == 0
        # El mismo nombre en la misma ciudad: el único es por empresa.
        sesion.add(_sucursal("Centro", ciudad))
        sesion.commit()
        nombres = sesion.scalars(select(Sucursal.empresa_id)).all()
        assert nombres == [empresa_b]

    assert db.scalars(select(Sucursal.empresa_id)).all() == [EMPRESA_A]


def test_el_default_pone_la_empresa_del_contexto(db, fabrica_sesiones, empresa_b):
    with _sesion_de(fabrica_sesiones, empresa_b) as sesion:
        sucursal = _sucursal("Norte", _ciudad(db))
        sesion.add(sucursal)
        sesion.commit()
        assert sucursal.empresa_id == empresa_b


def test_no_se_puede_escribir_con_la_empresa_de_otro(db, fabrica_sesiones, empresa_b):
    """El WITH CHECK de la política: la empresa A no escribe filas de la B."""
    with _sesion_de(fabrica_sesiones, EMPRESA_A) as sesion:
        sesion.add(_sucursal("Intrusa", _ciudad(db), empresa_id=empresa_b))
        with pytest.raises(DBAPIError) as error:
            sesion.commit()
        sesion.rollback()
    # Por el tipo y no por el texto: el mensaje sale en el idioma del servidor.
    assert isinstance(error.value.orig, psycopg.errors.InsufficientPrivilege)


def test_no_se_puede_modificar_lo_de_otra_empresa(db, fabrica_sesiones, empresa_b):
    db.add(_sucursal("Centro", _ciudad(db)))
    db.commit()

    with _sesion_de(fabrica_sesiones, empresa_b) as sesion:
        cambiadas = sesion.execute(text("UPDATE sucursal SET nombre = 'Hackeada'")).rowcount
        borradas = sesion.execute(text("DELETE FROM sucursal")).rowcount
        sesion.commit()
    assert (cambiadas, borradas) == (0, 0)
    assert db.scalars(select(Sucursal.nombre)).all() == ["Centro"]


def test_el_modo_plataforma_ve_todas_las_empresas(db, fabrica_sesiones, empresa_b):
    ciudad = _ciudad(db)
    db.add(_sucursal("Centro", ciudad))
    db.commit()
    with _sesion_de(fabrica_sesiones, empresa_b) as sesion:
        sesion.add(_sucursal("Centro", ciudad))
        sesion.commit()

    with fabrica_sesiones() as sesion:
        modo_plataforma(sesion)
        assert sesion.scalar(select(func.count()).select_from(Sucursal)) == 2


def test_fijar_empresa_cambia_la_transaccion_ya_abierta(db, fabrica_sesiones, empresa_b):
    """Es el caso de la petición: ya consultó el token antes de saber la empresa."""
    db.add(_sucursal("Centro", _ciudad(db)))
    db.commit()
    with _sesion_de(fabrica_sesiones, EMPRESA_A) as sesion:
        assert sesion.scalar(select(func.count()).select_from(Sucursal)) == 1
        fijar_empresa(sesion, empresa_b)
        assert sesion.scalar(select(func.count()).select_from(Sucursal)) == 0


# --------------------------------------------------------------------------
#  Por la API
# --------------------------------------------------------------------------
def _admin_de(db, empresa_id: int, correo: str) -> None:
    rol = db.scalar(select(Rol).where(Rol.nombre == "ADMINISTRADOR"))
    db.add(
        Usuario(
            correo=correo,
            hash_contrasena=hash_password("Admin12345"),
            nombres="Admin",
            apellidos="Empresa",
            rol_id=rol.id,
            empresa_id=empresa_id,
        )
    )
    db.commit()


def _token(api, correo: str, empresa: str = "violet-boutique") -> dict[str, str]:
    respuesta = api.post(
        "/api/v1/auth/login",
        json={"empresa": empresa, "correo": correo, "contrasena": "Admin12345"},
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_el_administrador_de_cada_empresa_ve_solo_sus_sucursales(api, db, empresa_b):
    _admin_de(db, EMPRESA_A, "admin.a@violetboutique.bo")
    _admin_de(db, empresa_b, "admin.b@tiendab.bo")
    ciudad = _ciudad(db)
    a, b = _token(api, "admin.a@violetboutique.bo"), _token(api, "admin.b@tiendab.bo", "tienda-b")
    alta = {
        "ciudad_id": ciudad,
        "nombre": "Centro",
        "direccion": "Calle 1",
        "horario_apertura": "09:00:00",
        "horario_cierre": "20:00:00",
    }

    assert api.post("/api/v1/organizacion/sucursales", json=alta, headers=a).status_code == 201
    # El mismo nombre en la misma ciudad no choca: es otra empresa.
    respuesta = api.post("/api/v1/organizacion/sucursales", json=alta, headers=b)
    assert respuesta.status_code == 201, respuesta.text
    id_de_b = respuesta.json()["id"]

    def _ids(cabeceras):
        respuesta = api.get("/api/v1/organizacion/sucursales", headers=cabeceras)
        assert respuesta.status_code == 200, respuesta.text
        cuerpo = respuesta.json()
        filas = cuerpo["items"] if isinstance(cuerpo, dict) else cuerpo
        return {fila["id"] for fila in filas}

    assert id_de_b not in _ids(a)
    assert _ids(b) == {id_de_b}
    # Ni pidiéndola por id: para la empresa A, la sucursal de B no existe.
    assert api.get(f"/api/v1/organizacion/sucursales/{id_de_b}", headers=a).status_code == 404


def test_el_cliente_queda_sin_empresa_y_asociado_a_la_tienda(api, db, token_cliente):
    """RN-13: una sola cuenta en la plataforma; dónde compra lo dice cliente_empresa."""
    usuario = db.scalar(select(Usuario).where(Usuario.correo == "ana.cliente@violetboutique.bo"))
    assert usuario.empresa_id is None
    cliente = db.scalar(select(Cliente).where(Cliente.usuario_id == usuario.id))
    asociaciones = db.scalars(
        select(ClienteEmpresa.empresa_id).where(ClienteEmpresa.cliente_id == cliente.id)
    ).all()
    assert asociaciones == [EMPRESA_A]
