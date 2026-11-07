"""CU-41 · Gestionar roles y permisos de la empresa (RF-64, RN-22).

Lo que más importa cubrir
-------------------------
- **Un rol propio solo acota:** el cajero con un rol propio deja de poder
  hacer lo que su rol no conserva, en la petición siguiente y sin volver a
  iniciar sesión. Sin rol propio, todo sigue como siempre.
- **Nunca da más que su rol base:** no se le pone un permiso de otro rol, y a
  una persona solo se le asigna un rol de su mismo rol base.
- **RN-22:** un permiso que es función del plan no entra si el plan no la
  incluye. Y los roles de una empresa no los ve otra (RLS).
- **No se delega gestionar roles ni usuarios.**
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import permisos as catalogo
from tests.test_cu31_venta_presencial import (
    PRENDAS,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _empleado,
)

ROLES = "/api/v1/roles"
PERMISOS = f"{ROLES}/permisos"
PERSONAL = f"{ROLES}/personal"
ASIGNACION = f"{ROLES}/asignacion"


@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def cajero(api, cabeceras_admin, db, sucursal) -> dict:
    cab = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="61")
    _abrir_turno(api, cab, _caja(db, sucursal))
    return cab


@pytest.fixture
def encargado(api, cabeceras_admin, sucursal) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=sucursal, sufijo="62")


def _persona(api, admin, correo_inicio: str) -> dict:
    return next(p for p in api.get(PERSONAL, headers=admin).json()
                if p["correo"].startswith(correo_inicio))


def _rol(api, admin, *, nombre="Vendedor", base="CAJERO", permisos=("ventas.registrar",
                                                                    "caja.operar")):
    return api.post(ROLES, headers=admin, json={
        "nombre": nombre, "descripcion": "Solo vende", "rol_base": base,
        "permisos": list(permisos)})


def _asignar(api, admin, usuario_id: int, rol_id: int | None):
    return api.put(ASIGNACION, headers=admin,
                   json={"usuario_id": usuario_id, "rol_empresa_id": rol_id})


# =====================================================================
# El catálogo
# =====================================================================

def test_toda_ruta_del_catalogo_resuelve_a_su_permiso() -> None:
    for permiso in catalogo.CATALOGO:
        for ruta in permiso.rutas:
            assert catalogo.permiso_de_ruta(f"/api/v1{ruta}/x") == permiso.codigo
    # El más específico gana.
    assert catalogo.permiso_de_ruta("/api/v1/pos/devoluciones/1") == "devoluciones.registrar"
    assert catalogo.permiso_de_ruta("/api/v1/traspasos/sugeridos") == "traspasos.sugeridos"
    assert catalogo.permiso_de_ruta("/api/v1/reportes/ventas.pdf") == "reportes.ver"
    assert catalogo.permiso_de_ruta("/api/v1/algo-nuevo") is None


def test_el_catalogo_no_ofrece_lo_que_no_se_delega(api, cabeceras_admin) -> None:
    codigos = {p["codigo"] for p in api.get(PERMISOS, headers=cabeceras_admin).json()}
    assert "ventas.registrar" in codigos
    assert "roles.gestionar" not in codigos
    assert "usuarios.gestionar" not in codigos


# =====================================================================
# Crear y validar
# =====================================================================

def test_el_admin_crea_un_rol_propio(api, cabeceras_admin) -> None:
    r = _rol(api, cabeceras_admin)
    assert r.status_code == 201, r.text
    assert r.json()["permisos"] == ["caja.operar", "ventas.registrar"]
    assert r.json()["personas"] == 0
    assert [x["nombre"] for x in api.get(ROLES, headers=cabeceras_admin).json()] == ["Vendedor"]


def test_no_se_repite_el_nombre(api, cabeceras_admin) -> None:
    _rol(api, cabeceras_admin)
    assert _rol(api, cabeceras_admin, nombre="vendedor").status_code == 409


def test_no_da_mas_que_su_rol_base(api, cabeceras_admin) -> None:
    r = _rol(api, cabeceras_admin, permisos=("ventas.registrar", "inventario.gestionar"))
    assert r.status_code == 422
    assert "rol base" in r.json()["detail"]


def test_no_se_delega_gestionar_roles(api, cabeceras_admin) -> None:
    r = _rol(api, cabeceras_admin, nombre="Jefe", base="ADMINISTRADOR",
             permisos=("roles.gestionar",))
    assert r.status_code == 422


def test_un_permiso_fuera_del_plan_no_entra(api, cabeceras_admin, db) -> None:
    from app.modules.plataforma.models import Plan

    plan = db.get(Plan, 3)
    antes = dict(plan.funciones)
    plan.funciones = {**antes, "reportes_ia": False}
    db.commit()
    try:
        catalogo_ = {p["codigo"]: p for p in api.get(PERMISOS, headers=cabeceras_admin).json()}
        assert catalogo_["reportes_ia.usar"]["incluido_en_plan"] is False
        r = _rol(api, cabeceras_admin, nombre="Analista", base="ENCARGADO",
                 permisos=("reportes.ver", "reportes_ia.usar"))
        assert r.status_code == 403
    finally:
        plan = db.get(Plan, 3)
        plan.funciones = antes
        db.commit()


def test_un_encargado_no_gestiona_roles(api, encargado) -> None:
    assert api.get(ROLES, headers=encargado).status_code == 403


# =====================================================================
# Asignar y hacer cumplir
# =====================================================================

def test_el_rol_propio_acota_al_cajero_en_la_siguiente_peticion(
    api, cabeceras_admin, cajero
) -> None:
    # Sin rol propio, el cajero hace todo lo de su rol.
    assert api.get(PRENDAS, headers=cajero).status_code == 200
    assert api.get("/api/v1/offline/operaciones/mias", headers=cajero).status_code == 200

    rol = _rol(api, cabeceras_admin).json()["id"]
    persona = _persona(api, cabeceras_admin, "cajero61")
    r = _asignar(api, cabeceras_admin, persona["usuario_id"], rol)
    assert r.status_code == 200 and r.json()["rol_empresa"] == "Vendedor"

    # Mismo token: vende, pero ya no trabaja sin conexión.
    assert api.get(PRENDAS, headers=cajero).status_code == 200
    negado = api.get("/api/v1/offline/operaciones/mias", headers=cajero)
    assert negado.status_code == 403
    assert "Vendedor" in negado.json()["detail"]
    # Lo libre sigue libre: sus avisos.
    assert api.get("/api/v1/notificaciones", headers=cajero).status_code == 200

    # Se le quita el rol propio y vuelve a tener todo.
    _asignar(api, cabeceras_admin, persona["usuario_id"], None)
    assert api.get("/api/v1/offline/operaciones/mias", headers=cajero).status_code == 200


def test_quitar_un_permiso_vale_al_instante(api, cabeceras_admin, cajero) -> None:
    rol = _rol(api, cabeceras_admin).json()["id"]
    _asignar(api, cabeceras_admin, _persona(api, cabeceras_admin, "cajero61")["usuario_id"], rol)
    assert api.get(PRENDAS, headers=cajero).status_code == 200

    api.patch(f"{ROLES}/{rol}", headers=cabeceras_admin, json={"permisos": ["caja.operar"]})
    assert api.get(PRENDAS, headers=cajero).status_code == 403


def test_el_login_trae_los_permisos(api, cabeceras_admin, cajero) -> None:
    rol = _rol(api, cabeceras_admin).json()["id"]
    _asignar(api, cabeceras_admin, _persona(api, cabeceras_admin, "cajero61")["usuario_id"], rol)
    entrada = api.post("/api/v1/auth/login",
                       json={"correo": "cajero61@violetboutique.bo", "contrasena": "Mostrador12"})
    usuario = entrada.json()["usuario"]
    assert usuario["rol"] == "CAJERO"
    assert usuario["rol_empresa"] == "Vendedor"
    assert usuario["permisos"] == ["caja.operar", "ventas.registrar"]


def test_solo_se_asigna_un_rol_del_mismo_rol_base(
    api, cabeceras_admin, cajero, encargado
) -> None:
    rol = _rol(api, cabeceras_admin).json()["id"]
    r = _asignar(api, cabeceras_admin, _persona(api, cabeceras_admin, "encargado62")["usuario_id"],
                 rol)
    assert r.status_code == 422


def test_el_admin_no_se_asigna_un_rol_a_si_mismo(api, cabeceras_admin) -> None:
    rol = _rol(api, cabeceras_admin, nombre="Analista", base="ADMINISTRADOR",
               permisos=("tablero.ver",)).json()["id"]
    yo = next(p for p in api.get(PERSONAL, headers=cabeceras_admin).json()
              if p["rol_base"] == "ADMINISTRADOR")
    assert _asignar(api, cabeceras_admin, yo["usuario_id"], rol).status_code == 409


def test_un_rol_con_personas_no_se_apaga(api, cabeceras_admin, cajero) -> None:
    rol = _rol(api, cabeceras_admin).json()["id"]
    _asignar(api, cabeceras_admin, _persona(api, cabeceras_admin, "cajero61")["usuario_id"], rol)
    r = api.patch(f"{ROLES}/{rol}/estado", headers=cabeceras_admin, json={"activo": False})
    assert r.status_code == 409


def test_un_analista_admin_solo_entra_a_lo_suyo(api, cabeceras_admin, db) -> None:
    """Un rol propio de base ADMINISTRADOR: ve el tablero y nada más."""
    from tests.test_cu31_venta_presencial import EMPLEADOS  # noqa: F401

    rol = _rol(api, cabeceras_admin, nombre="Analista", base="ADMINISTRADOR",
               permisos=("tablero.ver", "reportes.ver")).json()["id"]
    alta = api.post("/api/v1/usuarios", headers=cabeceras_admin, json={
        "correo": "analista@violetboutique.bo", "contrasena": "Analista123",
        "nombres": "Ana", "apellidos": "Lista", "rol": "ADMINISTRADOR"})
    assert alta.status_code == 201, alta.text
    _asignar(api, cabeceras_admin, alta.json()["id"], rol)
    entrada = api.post("/api/v1/auth/login",
                       json={"correo": "analista@violetboutique.bo", "contrasena": "Analista123"})
    cab = {"Authorization": f"Bearer {entrada.json()['access_token']}"}

    assert api.get("/api/v1/reportes/tablero", headers=cab).status_code == 200
    # Tanda C: la lista de sucursales es una consulta de apoyo (el filtro del
    # reporte la necesita); crear una sucursal sigue cerrado.
    assert api.get("/api/v1/organizacion/sucursales", headers=cab).status_code == 200
    assert api.post("/api/v1/organizacion/sucursales", headers=cab,
                    json={"nombre": "X"}).status_code == 403
    assert api.get("/api/v1/organizacion/empleados", headers=cab).status_code == 403
    assert api.get(ROLES, headers=cab).status_code == 403


# --- Tanda B de la auditoría ------------------------------------------------

def test_un_rol_propio_que_no_se_encuentra_cierra_en_vez_de_abrir() -> None:
    """Antes, si el rol propio no aparecía, la persona quedaba con todo su
    rol base. Ahora es 403, salvo las rutas libres (su sesión, sus avisos)."""
    from types import SimpleNamespace

    from fastapi import HTTPException

    from app.core.dependencies import _aplicar_rol_propio

    db = SimpleNamespace(get=lambda *_: None)
    usuario = SimpleNamespace(rol_empresa=None, permisos=None)

    def peticion(ruta):
        return SimpleNamespace(url=SimpleNamespace(path=ruta), method="GET")

    with pytest.raises(HTTPException) as e:
        _aplicar_rol_propio(peticion("/api/v1/catalogo/prendas"), db, usuario, 999)
    assert e.value.status_code == 403
    _aplicar_rol_propio(peticion("/api/v1/notificaciones"), db, usuario, 999)


def test_cambiar_de_rol_base_le_quita_el_rol_propio() -> None:
    from app.modules.seguridad.models import Usuario

    u = Usuario(rol_id=3, rol_empresa_id=7)
    u.asignar_rol(3)  # mismo rol: lo conserva
    assert u.rol_empresa_id == 7
    u.asignar_rol(2)  # otro rol: el «Vendedor» de un cajero no vale para él
    assert (u.rol_id, u.rol_empresa_id) == (2, None)


def test_el_cajero_ascendido_pierde_su_rol_propio(
    api, cabeceras_admin, cajero, sucursal
) -> None:
    rol = _rol(api, cabeceras_admin).json()["id"]
    persona = _persona(api, cabeceras_admin, "cajero61")
    assert _asignar(api, cabeceras_admin, persona["usuario_id"], rol).status_code == 200

    lista = api.get("/api/v1/organizacion/empleados", headers=cabeceras_admin).json()
    emp = next(e for e in lista if e["correo"].startswith("cajero61"))
    r = api.patch(f"/api/v1/organizacion/empleados/{emp['id']}", headers=cabeceras_admin,
                  json={"cargo": "ENCARGADO"})
    assert r.status_code == 200, r.text
    assert _persona(api, cabeceras_admin, "cajero61")["rol_empresa_id"] is None


def test_un_rol_parcial_puede_llenar_sus_desplegables_pero_no_escribir(
    api, cabeceras_admin, db
) -> None:
    """Un analista (ADMIN con solo reportes) abre la pantalla de reportes y
    el selector de sucursales ya no falla con 403; pero no puede crear una."""
    from app.core import permisos

    assert permisos.es_consulta_de_apoyo("GET", "/api/v1/organizacion/sucursales")
    assert permisos.es_consulta_de_apoyo("GET", "/api/v1/catalogo/productos/5")
    assert not permisos.es_consulta_de_apoyo("POST", "/api/v1/organizacion/sucursales")
    assert not permisos.es_consulta_de_apoyo("GET", "/api/v1/organizacion/empleados")
    assert not permisos.es_consulta_de_apoyo("GET", "/api/v1/catalogo/promociones")
