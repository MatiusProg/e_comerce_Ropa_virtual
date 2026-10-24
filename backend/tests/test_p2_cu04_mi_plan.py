"""2do parcial, CU-04 Consultar plan y consumo.

El administrador de la empresa ve su plan, el estado de la suscripción, cuánto
usó de cada límite y las funciones incluidas. Corre con el RLS de verdad (rol
`violet_app`): el uso que se cuenta es solo el de su empresa.
"""

from datetime import date, time, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.security import hash_password
from app.core.tenencia import CLAVE_EMPRESA
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.plataforma.models import Empresa, Plan, Suscripcion
from app.modules.seguridad.models import Rol, Usuario

URL = "/api/v1/plataforma/mi-plan"

FUNCIONES_PROFESIONAL = {
    "reportes_ia": True,
    "correo": True,
    "marca_propia": True,
    "analitica_ml": False,
    "bitacora_dias": 180,
    "respaldo_intervalo_horas": 24,
    "respaldo_retencion": 7,
}


@pytest.fixture
def planes(motor, db) -> dict[str, int]:
    """Los planes Básico y Profesional, y ninguna suscripción.

    `plan` y `suscripcion` no están entre las tablas que el conftest vacía: se
    vacían acá para que cada prueba arranque sin suscripciones de la anterior.
    """
    with motor.begin() as conexion:
        conexion.execute(text("TRUNCATE suscripcion, plan RESTART IDENTITY CASCADE"))
    basico = Plan(
        codigo="BASICO", nombre="Básico", precio_mensual=300, duracion_dias=30,
        max_sucursales=2, max_empleados=10, cupo_reportes_ia=0, cupo_fotos_ia=0,
        funciones={"reportes_ia": False, "marca_propia": False, "bitacora_dias": 30},
    )
    profesional = Plan(
        codigo="PROFESIONAL", nombre="Profesional", precio_mensual=750, duracion_dias=30,
        max_sucursales=10, max_empleados=60, cupo_reportes_ia=300, cupo_fotos_ia=10,
        funciones=FUNCIONES_PROFESIONAL,
    )
    db.add_all([basico, profesional])
    db.commit()
    return {"BASICO": basico.id, "PROFESIONAL": profesional.id}


def _suscribir(db: Session, plan_id: int, *, estado="VIGENTE", inicio=None, dias=30) -> None:
    inicio = inicio or tiempo.hoy()
    db.add(Suscripcion(plan_id=plan_id, inicio=inicio,
                       vencimiento=inicio + timedelta(days=dias), estado=estado))
    db.commit()


def _sucursal(db: Session, nombre: str, activa: bool = True) -> None:
    ciudad = db.scalar(select(Ciudad.id).where(Ciudad.nombre == "Santa Cruz"))
    db.add(Sucursal(ciudad_id=ciudad, nombre=nombre, direccion="Av. Busch 100",
                    horario_apertura=time(9), horario_cierre=time(20), activa=activa))
    db.commit()


def _limite(cuerpo: dict, codigo: str) -> dict:
    return next(x for x in cuerpo["limites"] + cuerpo["cupos"] if x["codigo"] == codigo)


def test_muestra_plan_suscripcion_y_uso(api, cabeceras_admin, db, planes):
    _suscribir(db, planes["PROFESIONAL"], dias=30)
    _sucursal(db, "Centro")
    _sucursal(db, "Norte")
    _sucursal(db, "Cerrada", activa=False)

    respuesta = api.get(URL, headers=cabeceras_admin)

    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["slug"] == "violet-boutique"
    assert cuerpo["plan"]["codigo"] == "PROFESIONAL"
    assert cuerpo["suscripcion"]["estado"] == "VIGENTE"
    assert cuerpo["suscripcion"]["dias_restantes"] == 30
    assert cuerpo["suscripcion"]["solo_consulta"] is False
    # Paso 3: la desactivada no cuenta para el límite (CU-09, 3b).
    assert _limite(cuerpo, "sucursales") == {
        "codigo": "sucursales", "etiqueta": "Sucursales activas",
        "usado": 2, "limite": 10, "alcanzado": False,
    }
    assert _limite(cuerpo, "empleados")["usado"] == 0
    # Los cupos de IA todavía no se miden: None, no un 0 que mentiría.
    assert _limite(cuerpo, "reportes_ia") == {
        "codigo": "reportes_ia", "etiqueta": "Reportes con IA del mes",
        "usado": None, "limite": 300, "alcanzado": False,
    }


def test_funciones_incluidas_y_no_incluidas(api, cabeceras_admin, db, planes):
    _suscribir(db, planes["PROFESIONAL"])

    funciones = {
        f["codigo"]: f for f in api.get(URL, headers=cabeceras_admin).json()["plan"]["funciones"]
    }

    assert funciones["marca_propia"]["incluida"] is True
    assert funciones["marca_propia"]["etiqueta"].startswith("Tienda en línea")
    assert funciones["analitica_ml"]["incluida"] is False
    assert funciones["bitacora_dias"]["detalle"] == "180 días"
    assert funciones["respaldo_intervalo_horas"]["detalle"] == "Una por día"
    assert funciones["respaldo_retencion"]["detalle"] == "Las últimas 7"


def test_limite_alcanzado(api, cabeceras_admin, db, planes):
    _suscribir(db, planes["BASICO"])
    _sucursal(db, "Centro")
    _sucursal(db, "Norte")

    sucursales = _limite(api.get(URL, headers=cabeceras_admin).json(), "sucursales")

    assert (sucursales["usado"], sucursales["limite"], sucursales["alcanzado"]) == (2, 2, True)


def test_ilimitado_es_null(api, cabeceras_admin, db, planes):
    plan = db.get(Plan, planes["PROFESIONAL"])
    plan.max_sucursales = None
    db.commit()
    _suscribir(db, plan.id)

    sucursales = _limite(api.get(URL, headers=cabeceras_admin).json(), "sucursales")

    assert sucursales["limite"] is None
    assert sucursales["alcanzado"] is False


def test_compara_con_los_otros_planes(api, cabeceras_admin, db, planes):
    _suscribir(db, planes["BASICO"])

    otros = api.get(URL, headers=cabeceras_admin).json()["otros_planes"]

    assert [p["codigo"] for p in otros] == ["PROFESIONAL"]


def test_suspendida_es_solo_consulta(api, cabeceras_admin, db, planes):
    """Flujo 2a."""
    _suscribir(db, planes["BASICO"], estado="SUSPENDIDA")

    suscripcion = api.get(URL, headers=cabeceras_admin).json()["suscripcion"]

    assert suscripcion["estado"] == "SUSPENDIDA"
    assert suscripcion["solo_consulta"] is True


def test_vigente_con_fecha_pasada_se_muestra_vencida(api, cabeceras_admin, db, planes):
    """El proceso diario (CU-03, E1) todavía no la marcó: igual es solo consulta."""
    _suscribir(db, planes["BASICO"], inicio=tiempo.hoy() - timedelta(days=40), dias=30)

    suscripcion = api.get(URL, headers=cabeceras_admin).json()["suscripcion"]

    assert suscripcion["estado"] == "VENCIDA"
    assert suscripcion["dias_restantes"] == -10
    assert suscripcion["solo_consulta"] is True


def test_vencida_muestra_la_ultima(api, cabeceras_admin, db, planes):
    _suscribir(db, planes["BASICO"], estado="VENCIDA",
               inicio=tiempo.hoy() - timedelta(days=60), dias=30)

    cuerpo = api.get(URL, headers=cabeceras_admin).json()

    assert cuerpo["suscripcion"]["estado"] == "VENCIDA"
    assert cuerpo["suscripcion"]["solo_consulta"] is True
    assert cuerpo["plan"]["codigo"] == "BASICO"


def test_sin_suscripcion(api, cabeceras_admin, db, planes):
    cuerpo = api.get(URL, headers=cabeceras_admin).json()

    assert cuerpo["suscripcion"] is None
    assert cuerpo["plan"] is None
    assert len(cuerpo["otros_planes"]) == 2


def test_solo_cuenta_lo_de_su_empresa(api, cabeceras_admin, db, planes, fabrica_sesiones):
    """Las sucursales y la suscripción de otra empresa no se ven ni se cuentan."""
    _suscribir(db, planes["BASICO"])
    _sucursal(db, "Centro")

    otra = db.scalar(select(Empresa).where(Empresa.slug == "tienda-b"))
    if otra is None:
        otra = Empresa(nombre="Tienda B", slug="tienda-b")
        db.add(otra)
        db.commit()
    sesion_b = fabrica_sesiones()
    sesion_b.info[CLAVE_EMPRESA] = otra.id
    try:
        ciudad = sesion_b.scalar(select(Ciudad.id).where(Ciudad.nombre == "Santa Cruz"))
        for nombre in ("B1", "B2", "B3"):
            sesion_b.add(Sucursal(ciudad_id=ciudad, nombre=nombre, direccion="Calle 1",
                                  horario_apertura=time(9), horario_cierre=time(20)))
        sesion_b.add(Suscripcion(plan_id=planes["PROFESIONAL"], inicio=date.today(),
                                 vencimiento=date.today() + timedelta(days=30)))
        sesion_b.commit()
    finally:
        sesion_b.close()

    cuerpo = api.get(URL, headers=cabeceras_admin).json()

    assert cuerpo["plan"]["codigo"] == "BASICO"
    assert _limite(cuerpo, "sucursales")["usado"] == 1


def test_solo_el_administrador(api, cabeceras_cliente, planes):
    assert api.get(URL, headers=cabeceras_cliente).status_code == 403


def test_sin_token(api):
    assert api.get(URL).status_code == 401


def test_usuario_sin_empresa(api, db, planes):
    """El administrador de la plataforma no tiene empresa: no hay «mi plan»."""
    from tests.conftest import _iniciar_sesion

    # CU-06 (RN-12): sin empresa solo existe la cuenta de la plataforma.
    rol = db.scalar(select(Rol).where(Rol.nombre == "ADMIN_PLATAFORMA"))
    usuario = Usuario(correo="plataforma@violet.bo", hash_contrasena=hash_password("Clave12345"),
                      nombres="Plata", apellidos="Forma", rol_id=rol.id)
    db.add(usuario)
    db.commit()
    db.execute(text("UPDATE usuario SET empresa_id = NULL WHERE id = :id"), {"id": usuario.id})
    db.commit()
    token = _iniciar_sesion(api, "plataforma@violet.bo", "Clave12345", None)

    respuesta = api.get(URL, headers={"Authorization": f"Bearer {token}"})

    assert respuesta.status_code == 403
