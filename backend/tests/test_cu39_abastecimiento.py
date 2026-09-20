"""CU-39 · Informar disponibilidad y plazo de abastecimiento.

Realiza el **RF38** y cierra el **agujero H1** del análisis de alcance:
`EstadoExistencia.PROXIMA_A_INGRESAR` estaba declarado desde el Ciclo 2 y
**ninguna fila lo devolvía**, porque CU-13 registra la mercadería *cuando ya
llegó* y nada anunciaba lo que estaba por llegar.

Lo que más importa cubrir
-------------------------
- **Que el estado nuevo aparezca de verdad.** Es la razón de ser del caso de
  uso: sin eso son cuatro endpoints que escriben en una tabla que nadie lee.
- **Que «próxima a ingresar» no tape lo que sí hay.** Una variante con 5
  disponibles y 20 anunciadas está DISPONIBLE — se puede vender hoy.
- **Que un proveedor solo anuncie lo suyo.** Un «próxima a ingresar»
  respaldado por quien no abastece esa prenda promete algo que nadie se
  comprometió a traer.
- **Que cada uno cancele el suyo.** Si no, un proveedor borra el compromiso de
  otro y el inventario pierde información sin que su dueño se entere.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

ABASTECIMIENTO = "/api/v1/proveedor/abastecimiento"
VARIANTES = f"{ABASTECIMIENTO}/variantes"
CONSOLIDADO = "/api/v1/inventario/consolidado"
PROVEEDORES = "/api/v1/organizacion/proveedores"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
SUCURSALES = "/api/v1/organizacion/sucursales"
INGRESOS = "/api/v1/inventario/ingresos"


def _proveedor_con_usuario(
    api: TestClient, admin: dict, db, sufijo: str
) -> tuple[int, dict]:
    """Un proveedor con su usuario, para poder entrar como él."""
    from sqlalchemy import select

    from app.core.security import hash_password
    from app.modules.organizacion.models import Proveedor
    from app.modules.seguridad.models import Rol, Usuario

    correo = f"proveedor{sufijo}@violetboutique.bo"
    clave = "Proveedor12"
    rol = db.scalar(select(Rol).where(Rol.nombre == "PROVEEDOR"))
    usuario = Usuario(
        correo=correo,
        hash_contrasena=hash_password(clave),
        nombres="Textiles",
        apellidos=f"Sur{sufijo}",
        rol_id=rol.id,
        activo=True,
    )
    db.add(usuario)
    db.flush()
    proveedor = Proveedor(
        usuario_id=usuario.id,
        razon_social=f"Textiles del Sur {sufijo}",
        identificacion_tributaria=f"10234567{sufijo}",
        activo=True,
    )
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)

    entrada = api.post(
        "/api/v1/auth/login", json={"correo": correo, "contrasena": clave}
    )
    assert entrada.status_code == 200, entrada.text
    return proveedor.id, {
        "Authorization": f"Bearer {entrada.json()['access_token']}"
    }


@pytest.fixture
def escenario(api: TestClient, cabeceras_admin: dict[str, str], db) -> dict:
    """Un proveedor con una prenda propia agotada, y otro proveedor ajeno."""
    categoria = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Blusas", "orden": 0, "activa": True},
    ).json()["id"]
    talla = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "M", "orden": 2, "activa": True},
    ).json()["id"]
    color = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    ).json()["id"]

    proveedor_id, cabeceras = _proveedor_con_usuario(api, cabeceras_admin, db, "1")
    ajeno_id, cabeceras_ajeno = _proveedor_con_usuario(api, cabeceras_admin, db, "2")

    def _producto(codigo: str, nombre: str, de_quien: int) -> tuple[int, int]:
        pid = api.post(
            PRODUCTOS,
            headers=cabeceras_admin,
            json={
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": categoria,
                "proveedor_id": de_quien,
                "precio_base": "250.00",
                "activo": True,
            },
        ).json()["id"]
        vid = api.post(
            f"{PRODUCTOS}/{pid}/variantes",
            headers=cabeceras_admin,
            json={
                "talla_id": talla,
                "color_id": color,
                "precio": "250.00",
                "activa": True,
            },
        ).json()["id"]
        return pid, vid

    _, mia = _producto("BLU-M", "Blusa mía", proveedor_id)
    _, ajena = _producto("BLU-A", "Blusa ajena", ajeno_id)

    return {
        "proveedor_id": proveedor_id,
        "cabeceras": cabeceras,
        "cabeceras_ajeno": cabeceras_ajeno,
        "variante_mia": mia,
        "variante_ajena": ajena,
    }


@pytest.fixture
def sucursal_vacia(api: TestClient, cabeceras_admin: dict, escenario: dict, db) -> int:
    """Una sucursal con la prenda AGOTADA: existencia en cero.

    Es el estado del que parte el caso de uso: la prenda se vendió toda y el
    proveedor anuncia que vuelve.
    """
    from app.modules.inventario.models import Existencia

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
    sucursal_id = r.json()["id"]
    db.add(
        Existencia(
            variante_id=escenario["variante_mia"],
            sucursal_id=sucursal_id,
            cantidad_disponible=0,
            cantidad_reservada=0,
        )
    )
    db.commit()
    return sucursal_id


def _anunciar(api: TestClient, cab: dict, variante_id: int, cantidad: int = 10, dias: int = 7):
    return api.post(
        ABASTECIMIENTO,
        headers=cab,
        json={"variante_id": variante_id, "cantidad": cantidad, "dias_plazo": dias},
    )


# --- Lo que el caso de uso existe para producir ----------------------------


def test_UNA_PRENDA_AGOTADA_Y_ANUNCIADA_SALE_COMO_PROXIMA_A_INGRESAR(
    api: TestClient, cabeceras_admin: dict, escenario: dict, db, sucursal_vacia: int
) -> None:
    """La razón de ser de CU-39, y la prueba de que el RF38 quedó cerrado.

    Sin esto son cuatro endpoints que escriben en una tabla que nadie lee.

    LIMITE CONOCIDO, Y POR ESO LA FIXTURE CREA LA EXISTENCIA EN CERO
    -----------------------------------------------------------------
    El consolidado se arma sobre las filas de `existencia`, y una variante que
    NUNCA tuvo stock en ninguna sucursal no tiene fila --- así que no aparece
    en el listado y no puede mostrarse como próxima a ingresar.

    Cubre el caso que importa: «se agotó y vuelve». El otro ---anunciar algo
    que la tienda nunca tuvo--- exigiría que el consolidado saliera también de
    `abastecimiento`, y eso es cambiar de dónde salen sus filas. Queda anotado
    en el documento de entrega en vez de resolverse a medias.
    """
    variante = escenario["variante_mia"]

    antes = api.get(CONSOLIDADO, headers=cabeceras_admin).json()["listado"]["items"]
    fila = next(i for i in antes if i["variante_id"] == variante)
    assert fila["estado"] == "agotada"
    assert fila["cantidad_anunciada"] == 0

    assert _anunciar(api, escenario["cabeceras"], variante, 20, 5).status_code == 201

    despues = api.get(CONSOLIDADO, headers=cabeceras_admin).json()["listado"]["items"]
    fila = next(i for i in despues if i["variante_id"] == variante)
    assert fila["estado"] == "proxima_a_ingresar"
    assert fila["cantidad_anunciada"] == 20
    assert fila["dias_para_ingresar"] == 5


def test_al_cancelar_vuelve_a_figurar_como_agotada(
    api: TestClient, cabeceras_admin: dict, escenario: dict, sucursal_vacia: int
) -> None:
    variante = escenario["variante_mia"]
    anuncio = _anunciar(api, escenario["cabeceras"], variante).json()["id"]
    api.delete(f"{ABASTECIMIENTO}/{anuncio}", headers=escenario["cabeceras"])

    items = api.get(CONSOLIDADO, headers=cabeceras_admin).json()["listado"]["items"]
    fila = next(i for i in items if i["variante_id"] == variante)
    assert fila["estado"] == "agotada"
    assert fila["cantidad_anunciada"] == 0


def test_lo_anunciado_NO_TAPA_lo_que_si_hay(
    api: TestClient, cabeceras_admin: dict, escenario: dict, db
) -> None:
    """Una variante con stock y con anuncio sigue DISPONIBLE.

    Decir «próxima a ingresar» haría creer que hoy no se puede vender.
    """
    from app.modules.inventario.consolidado_service import _estado
    from app.modules.inventario.consolidado_schemas import EstadoExistencia

    assert _estado(5, 0, 20) is EstadoExistencia.DISPONIBLE
    assert _estado(0, 3, 20) is EstadoExistencia.RESERVADA
    assert _estado(0, 0, 20) is EstadoExistencia.PROXIMA_A_INGRESAR
    assert _estado(0, 0, 0) is EstadoExistencia.AGOTADA


def test_al_cancelar_deja_de_figurar(
    api: TestClient, cabeceras_admin: dict, escenario: dict
) -> None:
    r = _anunciar(api, escenario["cabeceras"], escenario["variante_mia"])
    anuncio = r.json()["id"]

    assert api.delete(
        f"{ABASTECIMIENTO}/{anuncio}", headers=escenario["cabeceras"]
    ).status_code == 204

    vigentes = api.get(ABASTECIMIENTO, headers=escenario["cabeceras"]).json()
    assert vigentes == []
    # Pero la fila sigue existiendo: el compromiso existió y el inventario que
    # lo mostró una semana tiene que poder explicarse después.
    todos = api.get(
        ABASTECIMIENTO,
        headers=escenario["cabeceras"],
        params={"incluir_cancelados": True},
    ).json()
    assert len(todos) == 1
    assert todos[0]["estado"] == "CANCELADO"


# --- De quién es cada cosa --------------------------------------------------


def test_un_proveedor_NO_anuncia_prendas_ajenas(
    api: TestClient, escenario: dict
) -> None:
    """Prometería algo que nadie se comprometió a traer."""
    r = _anunciar(api, escenario["cabeceras"], escenario["variante_ajena"])
    assert r.status_code == 403
    assert "sus propios productos" in r.json()["detail"].lower()


def test_solo_ve_sus_propias_variantes_para_elegir(
    api: TestClient, escenario: dict
) -> None:
    lista = api.get(VARIANTES, headers=escenario["cabeceras"]).json()
    ids = {v["variante_id"] for v in lista}
    assert escenario["variante_mia"] in ids
    assert escenario["variante_ajena"] not in ids


def test_cada_proveedor_cancela_EL_SUYO(
    api: TestClient, escenario: dict
) -> None:
    """Si no, borra el compromiso de otro sin que su dueño se entere."""
    anuncio = _anunciar(api, escenario["cabeceras"], escenario["variante_mia"]).json()["id"]
    r = api.delete(f"{ABASTECIMIENTO}/{anuncio}", headers=escenario["cabeceras_ajeno"])
    assert r.status_code == 403


# --- Un anuncio vigente por proveedor y variante ---------------------------


def test_no_se_anuncia_dos_veces_la_misma_prenda(
    api: TestClient, escenario: dict
) -> None:
    """El índice único parcial ya lo impide; el mensaje dice qué hacer."""
    assert _anunciar(api, escenario["cabeceras"], escenario["variante_mia"]).status_code == 201
    r = _anunciar(api, escenario["cabeceras"], escenario["variante_mia"])
    assert r.status_code == 409
    assert "cancélelo" in r.json()["detail"].lower()


def test_despues_de_cancelar_SI_se_puede_volver_a_anunciar(
    api: TestClient, escenario: dict
) -> None:
    """Es la razón de que el índice único sea PARCIAL."""
    anuncio = _anunciar(api, escenario["cabeceras"], escenario["variante_mia"]).json()["id"]
    api.delete(f"{ABASTECIMIENTO}/{anuncio}", headers=escenario["cabeceras"])
    assert _anunciar(api, escenario["cabeceras"], escenario["variante_mia"]).status_code == 201


# --- Lo que no entra --------------------------------------------------------


@pytest.mark.parametrize(
    "campo,valor",
    [("cantidad", 0), ("cantidad", -5), ("dias_plazo", -1), ("dias_plazo", 400)],
)
def test_un_disparate_lo_rechaza_el_esquema(
    api: TestClient, escenario: dict, campo: str, valor: int
) -> None:
    cuerpo = {
        "variante_id": escenario["variante_mia"],
        "cantidad": 10,
        "dias_plazo": 7,
        campo: valor,
    }
    assert api.post(ABASTECIMIENTO, headers=escenario["cabeceras"], json=cuerpo).status_code == 422


def test_cero_dias_SI_es_valido(api: TestClient, escenario: dict) -> None:
    """«Lo tengo ahora» es una respuesta legítima."""
    assert _anunciar(api, escenario["cabeceras"], escenario["variante_mia"], dias=0).status_code == 201


def test_una_prenda_que_no_existe(api: TestClient, escenario: dict) -> None:
    assert _anunciar(api, escenario["cabeceras"], 999_999).status_code == 404


# --- Quién puede ------------------------------------------------------------


def test_un_cliente_no_informa_abastecimiento(
    api: TestClient, cabeceras_cliente: dict[str, str]
) -> None:
    assert api.get(ABASTECIMIENTO, headers=cabeceras_cliente).status_code == 403


def test_el_administrador_tampoco(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """Es el proveedor quien se compromete, no la tienda por él."""
    assert api.get(ABASTECIMIENTO, headers=cabeceras_admin).status_code == 403


def test_sin_token(api: TestClient) -> None:
    assert api.get(ABASTECIMIENTO).status_code == 401
