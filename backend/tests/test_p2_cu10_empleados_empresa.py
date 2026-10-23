"""2do parcial, CU-10 Gestionar empleados de la empresa: el aislamiento.

`empleado` tiene RLS, pero la cuenta del empleado vive en `usuario`, que no lo
tiene. El flujo de vincular una cuenta existente (el 3c del CU-06 del 1er
parcial) preguntaba «¿tiene ficha de empleado?» y el RLS escondía las fichas
de las otras empresas: sus empleados aparecían como cuentas libres.
"""

from datetime import time

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.core.tenencia import CLAVE_EMPRESA
from app.modules.organizacion.models import Ciudad, Empleado, Sucursal
from app.modules.plataforma.models import Empresa
from app.modules.seguridad.models import Rol, Usuario

URL = "/api/v1/organizacion/empleados"
CLAVE = "Clave12345"


@pytest.fixture
def sesion_b(db, fabrica_sesiones):
    empresa = db.scalar(select(Empresa).where(Empresa.slug == "tienda-b"))
    if empresa is None:
        empresa = Empresa(nombre="Tienda B", slug="tienda-b")
        db.add(empresa)
        db.commit()
    sesion = fabrica_sesiones()
    sesion.info[CLAVE_EMPRESA] = empresa.id
    yield sesion
    sesion.close()


def _sucursal(sesion, nombre: str) -> int:
    ciudad = sesion.scalar(select(Ciudad.id).where(Ciudad.nombre == "Santa Cruz"))
    sucursal = Sucursal(ciudad_id=ciudad, nombre=nombre, direccion="Calle 1",
                        horario_apertura=time(9), horario_cierre=time(20))
    sesion.add(sucursal)
    sesion.commit()
    return sucursal.id


def _cuenta(sesion, correo: str, rol: str = "ADMINISTRADOR") -> Usuario:
    """Una cuenta en la empresa de la sesión (la toma del DEFAULT del contexto)."""
    rol_id = sesion.scalar(select(Rol.id).where(Rol.nombre == rol))
    usuario = Usuario(correo=correo, hash_contrasena=hash_password(CLAVE),
                      nombres="Nombre", apellidos="Apellido", rol_id=rol_id)
    sesion.add(usuario)
    sesion.commit()
    return usuario


def test_no_ofrece_cuentas_de_otra_empresa(api, cabeceras_admin, db, sesion_b):
    _cuenta(db, "libre@a.bo")
    _cuenta(sesion_b, "libre@b.bo")
    # Un empleado de B: el RLS esconde su ficha a la empresa A.
    empleado_b = _cuenta(sesion_b, "cajero@b.bo", "CAJERO")
    sesion_b.add(Empleado(usuario_id=empleado_b.id, sucursal_id=_sucursal(sesion_b, "B1"),
                          documento="555", cargo="CAJERO", fecha_ingreso="2026-01-01"))
    sesion_b.commit()

    respuesta = api.get(f"{URL}/usuarios-vinculables", headers=cabeceras_admin)

    assert respuesta.status_code == 200, respuesta.text
    correos = {u["correo"] for u in respuesta.json()}
    assert "libre@a.bo" in correos
    assert "libre@b.bo" not in correos
    assert "cajero@b.bo" not in correos


def test_no_vincula_una_cuenta_de_otra_empresa(api, cabeceras_admin, db, sesion_b):
    ajena = _cuenta(sesion_b, "libre@b.bo")
    sucursal = _sucursal(db, "Centro")

    respuesta = api.post(URL, headers=cabeceras_admin, json={
        "usuario_id": ajena.id, "sucursal_id": sucursal, "documento": "777",
        "cargo": "CAJERO", "fecha_ingreso": "2026-10-01",
    })

    assert respuesta.status_code == 422, respuesta.text
    sesion_b.refresh(ajena)
    rol = sesion_b.scalar(select(Rol.nombre).where(Rol.id == ajena.rol_id))
    assert rol == "ADMINISTRADOR"


def test_el_empleado_nuevo_queda_en_la_empresa_del_administrador(api, cabeceras_admin, db):
    sucursal = _sucursal(db, "Centro")

    respuesta = api.post(URL, headers=cabeceras_admin, json={
        "correo": "nuevo@a.bo", "contrasena": CLAVE, "nombres": "Nuevo",
        "apellidos": "Cajero", "sucursal_id": sucursal, "documento": "888",
        "cargo": "CAJERO", "fecha_ingreso": "2026-10-01",
    })

    assert respuesta.status_code == 201, respuesta.text
    assert db.scalar(select(Usuario.empresa_id).where(Usuario.correo == "nuevo@a.bo")) == 1


def test_no_lista_empleados_de_otra_empresa(api, cabeceras_admin, sesion_b):
    cuenta = _cuenta(sesion_b, "cajero@b.bo", "CAJERO")
    sesion_b.add(Empleado(usuario_id=cuenta.id, sucursal_id=_sucursal(sesion_b, "B1"),
                          documento="555", cargo="CAJERO", fecha_ingreso="2026-01-01"))
    sesion_b.commit()

    respuesta = api.get(URL, headers=cabeceras_admin)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == []
