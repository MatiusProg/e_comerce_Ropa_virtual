"""CU-05 Verificar límites y funciones del plan (2do parcial).

Cubre la ficha del 2.6: la operación que cumple el plan (flujo principal), la
empresa sin suscripción vigente que solo consulta (2a, RN-03), la función que
el plan no incluye (3a), el límite y el cupo alcanzados (4a, RN-11), y que
bajar de plan no borre nada (RN-04).

La empresa de las pruebas arranca con el Empresarial (conftest), que no limita
nada; cada prueba la pasa al plan que necesita.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.tenencia import fijar_empresa
from app.integrations import interprete
from app.integrations.interprete.base import Pedido
from app.modules.plataforma import verificador
from app.modules.plataforma.models import ConsumoCupo, Empresa, Plan, Suscripcion

SUCURSALES = "/api/v1/organizacion/sucursales"
EMPLEADOS = "/api/v1/organizacion/empleados"
VOZ = "/api/v1/reportes/voz"


def _pasar_a(db, codigo: str, **cambios) -> None:
    """Pasa la empresa de las pruebas al plan `codigo`, con límites retocados."""
    plan = db.scalar(select(Plan).where(Plan.codigo == codigo))
    for campo, valor in cambios.items():
        setattr(plan, campo, valor)
    db.execute(update(Suscripcion).values(plan_id=plan.id))
    db.commit()


def _sucursal(api: TestClient, admin, nombre: str):
    return api.post(
        SUCURSALES,
        headers=admin,
        json={
            "ciudad_id": 1,
            "nombre": nombre,
            "direccion": f"Avenida {nombre} 100",
            "horario_apertura": "09:00:00",
            "horario_cierre": "20:00:00",
            "capacidad_vestidores": 4,
        },
    )


def _empleado(api: TestClient, admin, sucursal_id: int, n: int):
    return api.post(
        EMPLEADOS,
        headers=admin,
        json={
            "documento": f"555000{n}",
            "cargo": "CAJERO",
            "sucursal_id": sucursal_id,
            "fecha_ingreso": (date.today() - timedelta(days=10)).isoformat(),
            "nombres": "Rosa",
            "apellidos": f"Mendoza {n}",
            "correo": f"cajero{n}@violetboutique.bo",
            "contrasena": "Trabajo123",
        },
    )


# --------------------------------------------------------------------------
#  Flujo principal y 4a: límites
# --------------------------------------------------------------------------
def test_dentro_del_limite_la_operacion_sigue(api, db, cabeceras_admin):
    _pasar_a(db, "BASICO")  # hasta 2 sucursales
    assert _sucursal(api, cabeceras_admin, "Centro").status_code == 201
    assert _sucursal(api, cabeceras_admin, "Norte").status_code == 201


def test_la_sucursal_que_pasa_el_limite_se_rechaza_con_plan_limit(api, db, cabeceras_admin):
    _pasar_a(db, "BASICO")
    _sucursal(api, cabeceras_admin, "Centro")
    _sucursal(api, cabeceras_admin, "Norte")

    r = _sucursal(api, cabeceras_admin, "Sur")

    assert r.status_code == 403
    cuerpo = r.json()
    assert cuerpo["codigo"] == "plan_limit"
    assert (cuerpo["limite"], cuerpo["uso"]) == (2, 2)
    # `detail` sigue siendo un mensaje: es lo que ya muestran los servicios de la web.
    assert "Básico" in cuerpo["detail"]
    nombres = [s["nombre"] for s in api.get(SUCURSALES, headers=cabeceras_admin).json()]
    assert "Sur" not in nombres


def test_una_sucursal_que_nace_desactivada_no_consume_el_limite(api, db, cabeceras_admin):
    _pasar_a(db, "BASICO")
    _sucursal(api, cabeceras_admin, "Centro")
    _sucursal(api, cabeceras_admin, "Norte")

    r = api.post(SUCURSALES, headers=cabeceras_admin, json={
        "ciudad_id": 1, "nombre": "Sur", "direccion": "Avenida Sur 100",
        "horario_apertura": "09:00:00", "horario_cierre": "20:00:00",
        "capacidad_vestidores": 4, "activa": False})

    assert r.status_code == 201, r.text


def test_bajar_de_plan_no_borra_nada_solo_impide_crear_mas(api, db, cabeceras_admin):
    """RN-04: con 3 sucursales y un plan de 2, las 3 siguen; la cuarta no entra."""
    ids = [_sucursal(api, cabeceras_admin, n).json()["id"] for n in ("A", "B", "C")]
    _pasar_a(db, "BASICO")

    assert len(api.get(SUCURSALES, headers=cabeceras_admin).json()) == 3
    assert _sucursal(api, cabeceras_admin, "D").status_code == 403

    # Dar de baja nunca se impide...
    baja = api.patch(f"{SUCURSALES}/{ids[0]}/estado", headers=cabeceras_admin,
                     json={"activa": False})
    assert baja.status_code == 200, baja.text
    # ...pero reactivarla suma una activa, igual que el alta: con 2 de 2, no.
    alta = api.patch(f"{SUCURSALES}/{ids[0]}/estado", headers=cabeceras_admin,
                     json={"activa": True})
    assert alta.status_code == 403
    assert alta.json()["codigo"] == "plan_limit"


def test_el_limite_de_empleados_cuenta_solo_los_activos(api, db, cabeceras_admin):
    _pasar_a(db, "BASICO", max_empleados=1)
    sucursal_id = _sucursal(api, cabeceras_admin, "Centro").json()["id"]

    primero = _empleado(api, cabeceras_admin, sucursal_id, 1)
    assert primero.status_code == 201, primero.text
    segundo = _empleado(api, cabeceras_admin, sucursal_id, 2)
    assert segundo.status_code == 403
    assert (segundo.json()["limite"], segundo.json()["uso"]) == (1, 1)

    # Dado de baja, deja de contar y libera el lugar.
    api.patch(f"{EMPLEADOS}/{primero.json()['id']}/baja", headers=cabeceras_admin, json={})
    assert _empleado(api, cabeceras_admin, sucursal_id, 3).status_code == 201


def test_un_limite_vacio_es_ilimitado(api, db, cabeceras_admin):
    _pasar_a(db, "EMPRESARIAL")
    for nombre in ("A", "B", "C", "D"):
        assert _sucursal(api, cabeceras_admin, nombre).status_code == 201


# --------------------------------------------------------------------------
#  2a: sin suscripción vigente, solo consulta
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    "cambio",
    [
        {"estado": "SUSPENDIDA"},
        # Vencida por fecha aunque nadie la haya marcado VENCIDA todavía.
        {"inicio": date.today() - timedelta(days=60),
         "vencimiento": date.today() - timedelta(days=1)},
    ],
    ids=["suspendida", "vencida-por-fecha"],
)
def test_sin_suscripcion_vigente_la_empresa_solo_consulta(api, db, cabeceras_admin, cambio):
    db.execute(update(Suscripcion).values(**cambio))
    db.commit()

    r = _sucursal(api, cabeceras_admin, "Centro")
    assert r.status_code == 403
    assert r.json()["codigo"] == "sin_suscripcion"
    # Consultar sí.
    assert api.get(SUCURSALES, headers=cabeceras_admin).status_code == 200
    # Y cerrar sesión también: no es escribir datos de la empresa.
    assert api.post("/api/v1/auth/logout", headers=cabeceras_admin).status_code in (200, 204)


# --------------------------------------------------------------------------
#  3a y 4a: funciones y cupos (el pedido de reporte por voz usa la IA)
# --------------------------------------------------------------------------
@pytest.fixture
def interprete_falso(monkeypatch):
    pedido = Pedido(tipo="ventas", formato="pdf", desde=None, hasta=None, filtros={},
                    resumen="Ventas, en PDF")
    monkeypatch.setattr(interprete, "interpretar", lambda t, r, h: pedido)


def test_la_funcion_que_el_plan_no_incluye_se_rechaza(api, db, cabeceras_admin, interprete_falso):
    _pasar_a(db, "BASICO")
    r = api.post(VOZ, headers=cabeceras_admin, json={"texto": "ventas en pdf"})
    assert r.status_code == 403
    assert r.json()["codigo"] == "plan_limit"
    assert "reportes con IA" in r.json()["detail"]


def test_el_cupo_del_mes_se_descuenta_y_al_agotarse_se_rechaza(
    api, db, cabeceras_admin, interprete_falso
):
    _pasar_a(db, "PROFESIONAL", cupo_reportes_ia=2)

    for _ in range(2):
        r = api.post(VOZ, headers=cabeceras_admin, json={"texto": "ventas en pdf"})
        assert r.status_code == 200, r.text
    agotado = api.post(VOZ, headers=cabeceras_admin, json={"texto": "ventas en pdf"})

    assert agotado.status_code == 403
    assert (agotado.json()["limite"], agotado.json()["uso"]) == (2, 2)
    assert verificador.uso_del_mes(db, "reportes_ia") == 2


def test_consumir_cupo_no_pasa_del_maximo(db):
    _pasar_a(db, "PROFESIONAL", cupo_fotos_ia=1)
    assert verificador.consumir_cupo(db, "fotos_ia") == 1
    db.commit()
    with pytest.raises(verificador.RechazoDelPlan):
        verificador.consumir_cupo(db, "fotos_ia")


def test_el_cupo_de_una_empresa_no_lo_ve_otra(db):
    _pasar_a(db, "PROFESIONAL")
    verificador.consumir_cupo(db, "fotos_ia")
    db.commit()

    otra = Empresa(nombre="Moda Andina", slug="moda-andina")
    db.add(otra)
    db.commit()
    fijar_empresa(db, otra.id)
    try:
        assert verificador.uso_del_mes(db, "fotos_ia") == 0
        assert db.scalar(select(ConsumoCupo)) is None
        # Y sin suscripción propia, la otra empresa no tiene plan.
        with pytest.raises(verificador.SinSuscripcionVigente):
            verificador.plan_vigente(db)
    finally:
        fijar_empresa(db, 1)
