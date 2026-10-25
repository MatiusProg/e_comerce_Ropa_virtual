"""Las ciudades son compartidas: solo las gestiona la plataforma (2do parcial).

Si las editara el administrador de cada empresa, renombrar una ciudad se la
cambiaría a todas las demás. Las empresas solo las eligen al dar de alta una
sucursal o una dirección.
"""

import pytest
from sqlalchemy import null, select

from app.core.security import hash_password
from app.modules.seguridad.models import Rol, Usuario

CIUDADES = "/api/v1/organizacion/ciudades"
CORREO_PLATAFORMA = "plataforma@violetboutique.bo"
CLAVE = "Plataforma123"


@pytest.fixture
def cabeceras_plataforma(api, db) -> dict[str, str]:
    rol = db.scalar(select(Rol).where(Rol.nombre == "ADMIN_PLATAFORMA"))
    db.add(
        Usuario(
            correo=CORREO_PLATAFORMA,
            hash_contrasena=hash_password(CLAVE),
            nombres="Admin",
            apellidos="Plataforma",
            rol_id=rol.id,
            empresa_id=null(),
        )
    )
    db.commit()
    respuesta = api.post(
        "/api/v1/auth/login",
        json={"empresa": None, "correo": CORREO_PLATAFORMA, "contrasena": CLAVE},
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_la_plataforma_gestiona_las_ciudades(api, cabeceras_plataforma):
    alta = api.post(CIUDADES, headers=cabeceras_plataforma,
                    json={"nombre": "Cochabamba", "departamento": "Cochabamba"})
    assert alta.status_code == 201, alta.text
    ciudad = f"{CIUDADES}/{alta.json()['id']}"

    editada = api.patch(ciudad, headers=cabeceras_plataforma, json={"nombre": "Quillacollo"})
    assert editada.status_code == 200, editada.text
    assert editada.json()["nombre"] == "Quillacollo"

    assert api.delete(ciudad, headers=cabeceras_plataforma).status_code == 204


def test_el_administrador_de_una_empresa_solo_las_consulta(api, cabeceras_admin):
    assert api.get(CIUDADES, headers=cabeceras_admin).status_code == 200

    alta = api.post(CIUDADES, headers=cabeceras_admin,
                    json={"nombre": "Cochabamba", "departamento": "Cochabamba"})
    assert alta.status_code == 403
    ciudad_id = api.get(CIUDADES, headers=cabeceras_admin).json()[0]["id"]
    assert api.patch(f"{CIUDADES}/{ciudad_id}", headers=cabeceras_admin,
                     json={"nombre": "Otra"}).status_code == 403
    assert api.delete(f"{CIUDADES}/{ciudad_id}", headers=cabeceras_admin).status_code == 403
