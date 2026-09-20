"""CU-33 · Recibir recomendaciones de prendas.

Realiza el **RF25** — «el sistema deberá proporcionar al menos una
funcionalidad basada en inteligencia artificial» —, que hasta el 18/09/2026
era el único requisito funcional del proyecto sin nada construido.

NINGUNA PRUEBA LLAMA AL MODELO DE VERDAD
-----------------------------------------
Se sustituye el proveedor. Una prueba que sale a internet tarda quince
segundos, gasta cuota, y **falla cuando Google devuelve 503** — que pasa: se
midió el 18/09 y es justamente lo que el paso 3 existe para absorber. Una
prueba que falla por algo que el sistema maneja bien no prueba nada, enseña a
ignorar el rojo.

Lo que más importa cubrir
-------------------------
- **Que degrade en vez de fallar.** Sin proveedor, sin clave o con el servicio
  caído, el cliente recibe prendas igual. Es el punto 3 de la decisión técnica
  y la razón de que el riesgo R9 —quedarse sin crédito— no pueda dejar una
  pantalla vacía en la defensa.
- **Que el filtro determinista se respete.** El modelo ORDENA; no elige. Una
  prenda agotada, o inactiva, no puede aparecer aunque el modelo la nombre.
- **Que no se confíe en lo que devuelve el modelo.** Un identificador que no
  estaba en las candidatas se descarta: mostrarlo sería ofrecerle al cliente
  algo que la tienda no tiene.
- **Que se guarde.** Sin caché, entrar y salir de la pantalla son llamadas al
  modelo, y eso es el riesgo R9 otra vez.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.integrations import recomendador
from app.integrations.recomendador import (
    Candidata,
    ErrorDelRecomendador,
    PerfilDelCliente,
    Sugerencia,
)

RECOMENDACIONES = "/api/v1/tienda/recomendaciones"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
SUCURSALES = "/api/v1/organizacion/sucursales"
INGRESOS = "/api/v1/inventario/ingresos"
PROVEEDORES = "/api/v1/organizacion/proveedores"


class _ProveedorFalso:
    """Un recomendador que devuelve lo que la prueba le diga."""

    nombre = "falso"
    disponible = True

    def __init__(self, respuesta=None, error: Exception | None = None):
        self.respuesta = respuesta
        self.error = error
        self.llamadas = 0
        self.ultimo_perfil: PerfilDelCliente | None = None
        self.ultimas_candidatas: list[Candidata] = []

    def ordenar(self, perfil, candidatas, cuantas):
        self.llamadas += 1
        self.ultimo_perfil = perfil
        self.ultimas_candidatas = list(candidatas)
        if self.error is not None:
            raise self.error
        if self.respuesta is not None:
            return self.respuesta
        # Por omisión: las primeras, con un motivo reconocible.
        return [
            Sugerencia(producto_id=c.producto_id, motivo=f"porque sí {c.producto_id}")
            for c in candidatas[:cuantas]
        ]


@pytest.fixture
def proveedor(monkeypatch):
    """Sustituye el proveedor. Devuelve el falso para poder interrogarlo."""
    falso = _ProveedorFalso()
    monkeypatch.setattr(recomendador, "obtener_proveedor", lambda: falso)
    monkeypatch.setattr(
        recomendador, "ordenar", lambda p, c, n: falso.ordenar(p, c, n)
    )
    monkeypatch.setattr(recomendador, "nombre_del_proveedor", lambda: falso.nombre)
    return falso


@pytest.fixture
def tienda(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Tres prendas de torso: dos con stock y una agotada."""
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
    r = api.post(
        SUCURSALES,
        headers=cabeceras_admin,
        json={
            "ciudad_id": 1,
            "nombre": "Central",
            "direccion": "Avenida Central 100",
            "telefono": None,
            "horario_apertura": "09:00",
            "horario_cierre": "20:00",
            "capacidad_vestidores": 2,
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    sucursal = r.json()["id"]

    r = api.post(
        PROVEEDORES,
        headers=cabeceras_admin,
        json={
            "razon_social": "Textiles del Sur SRL",
            "identificacion_tributaria": "1023456789",
            "activo": True,
        },
    )
    proveedor_id = (
        api.get(PROVEEDORES, headers=cabeceras_admin).json()[0]["id"]
        if r.status_code == 409
        else r.json()["id"]
    )

    def _producto(codigo: str, nombre: str) -> tuple[int, int]:
        pid = api.post(
            PRODUCTOS,
            headers=cabeceras_admin,
            json={
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": categoria,
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

    con_stock_a, v_a = _producto("BLU-A", "Blusa con stock A")
    con_stock_b, v_b = _producto("BLU-B", "Blusa con stock B")
    agotada, _ = _producto("BLU-C", "Blusa agotada")

    r = api.post(
        INGRESOS,
        headers=cabeceras_admin,
        json={
            "sucursal_id": sucursal,
            "proveedor_id": proveedor_id,
            "referencia": "REM-CU33",
            "lineas": [
                {"variante_id": v_a, "cantidad": 5},
                {"variante_id": v_b, "cantidad": 5},
            ],
        },
    )
    assert r.status_code == 201, r.text

    return {
        "con_stock": [con_stock_a, con_stock_b],
        "agotada": agotada,
        "categoria": categoria,
        "variantes": {con_stock_a: v_a, con_stock_b: v_b},
    }


def _pedir(api: TestClient, cab: dict, forzar: bool = False) -> dict:
    r = api.get(
        f"{RECOMENDACIONES}{'?forzar=true' if forzar else ''}", headers=cab
    )
    assert r.status_code == 200, r.text
    return r.json()


# --- El filtro determinista -----------------------------------------------


def test_una_prenda_AGOTADA_no_se_recomienda(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor
) -> None:
    """Es la garantía del paso 1, y la razón de que el enfoque sea híbrido.

    Al modelo ni siquiera se le ofrece: no puede recomendar lo que no ve.
    """
    _pedir(api, cabeceras_cliente)
    ofrecidas = {c.producto_id for c in proveedor.ultimas_candidatas}
    assert tienda["agotada"] not in ofrecidas
    assert set(tienda["con_stock"]) <= ofrecidas


def test_al_modelo_no_se_le_manda_quien_es_la_clienta(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor
) -> None:
    """El perfil que sale hacia un tercero no lleva datos personales.

    El modelo no los necesita para ordenar ropa. La prueba mira los campos que
    existen: si alguien agrega el correo al perfil, esto falla.
    """
    _pedir(api, cabeceras_cliente)
    campos = vars(proveedor.ultimo_perfil).keys()
    assert "correo" not in campos
    assert "nombres" not in campos
    assert "documento" not in campos


# --- No se confía en lo que devuelve el modelo -----------------------------


def test_un_producto_que_el_modelo_INVENTA_se_descarta(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, monkeypatch
) -> None:
    """Mostrarlo sería ofrecer algo que la tienda no tiene."""
    falso = _ProveedorFalso(
        respuesta=[
            Sugerencia(producto_id=999_999, motivo="no existe"),
            Sugerencia(producto_id=tienda["con_stock"][0], motivo="esta sí"),
        ]
    )
    monkeypatch.setattr(recomendador, "ordenar", lambda p, c, n: falso.ordenar(p, c, n))
    monkeypatch.setattr(recomendador, "nombre_del_proveedor", lambda: falso.nombre)

    cuerpo = _pedir(api, cabeceras_cliente)
    ids = {p["producto_id"] for p in cuerpo["prendas"]}
    assert 999_999 not in ids
    assert tienda["con_stock"][0] in ids


# --- Degradar en vez de fallar ---------------------------------------------


def test_sin_proveedor_de_IA_igual_hay_recomendaciones(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, monkeypatch
) -> None:
    """El punto 3 de la decisión técnica.

    Es lo que evita que el riesgo R9 ---quedarse sin crédito antes de la
    defensa--- deje la pantalla vacía.
    """
    def _explota(perfil, candidatas, cuantas):
        raise ErrorDelRecomendador("no hay clave")

    monkeypatch.setattr(recomendador, "ordenar", _explota)

    cuerpo = _pedir(api, cabeceras_cliente)
    assert cuerpo["motor"] == "popularidad"
    assert len(cuerpo["prendas"]) > 0
    # Sin motivos: no se inventa una razón que nadie eligió.
    assert all(p["motivo"] == "" for p in cuerpo["prendas"])


def test_el_motor_viaja_hasta_la_pantalla(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor
) -> None:
    """Una sugerencia hecha por un modelo tiene que poder decir que lo es."""
    cuerpo = _pedir(api, cabeceras_cliente)
    assert cuerpo["motor"] == "falso"
    assert all(p["motivo"] for p in cuerpo["prendas"])


def test_una_tienda_sin_stock_devuelve_lista_vacia_y_no_un_error(
    api: TestClient, cabeceras_cliente: dict[str, str], proveedor
) -> None:
    """Catálogo vacío no es un fallo. La pantalla ya sabe dibujar nada."""
    cuerpo = _pedir(api, cabeceras_cliente)
    assert cuerpo["prendas"] == []
    assert proveedor.llamadas == 0, "no se llama al modelo si no hay qué ordenar"


# --- La caché ---------------------------------------------------------------


def test_la_segunda_visita_NO_vuelve_a_llamar_al_modelo(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor
) -> None:
    """Sin esto, entrar y salir de la pantalla son llamadas al modelo."""
    _pedir(api, cabeceras_cliente)
    _pedir(api, cabeceras_cliente)
    _pedir(api, cabeceras_cliente)
    assert proveedor.llamadas == 1


def test_forzar_vuelve_a_generar(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor
) -> None:
    """Es para la demostración: sin esto habría que esperar doce horas."""
    _pedir(api, cabeceras_cliente)
    _pedir(api, cabeceras_cliente, forzar=True)
    assert proveedor.llamadas == 2


def test_la_recomendacion_se_puede_invalidar(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor, db
) -> None:
    """La llama quien cambia el perfil o registra una compra."""
    from app.modules.ia import repository as ia_repository
    from app.modules.ia import service as ia_service
    from app.modules.seguridad.models import Cliente
    from sqlalchemy import select

    _pedir(api, cabeceras_cliente)
    cliente = db.scalar(select(Cliente))
    assert ia_repository.guardada(db, cliente.id) is not None

    ia_service.invalidar(db, cliente.id)
    db.commit()
    assert ia_repository.guardada(db, cliente.id) is None

    _pedir(api, cabeceras_cliente)
    assert proveedor.llamadas == 2


# --- Quién puede pedirlas ---------------------------------------------------


def test_un_administrador_no_recibe_recomendaciones(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """No tiene perfil de compra: no hay nada que recomendarle."""
    assert api.get(RECOMENDACIONES, headers=cabeceras_admin).status_code == 403


def test_sin_token_no_hay_recomendaciones(api: TestClient) -> None:
    assert api.get(RECOMENDACIONES).status_code == 401


# --- La guardada sigue al catalogo -----------------------------------------
#
# La recomendacion vive doce horas y el catalogo se mueve mientras tanto. Los
# datos del producto ya se leian de nuevo en cada lectura ---por eso un cambio
# de precio se ve enseguida---, pero solo se comprobaba `activo`. Una prenda
# cuya ultima variante se dio de baja, o cuya ultima unidad se vendio, seguia
# apareciendo recomendada y sin precio hasta que venciera.


def test_una_prenda_QUE_DEJO_DE_SER_OFRECIBLE_desaparece_de_la_guardada(
    api: TestClient,
    cabeceras_cliente: dict[str, str],
    cabeceras_admin: dict[str, str],
    tienda: dict,
    proveedor,
) -> None:
    """Recomendar lo que ya no se puede comprar es prometer de mas.

    Da igual por que dejo de estar: borrada, desactivada, sin variante activa
    o agotada. Para quien mira la pantalla las cuatro son la misma cosa.
    """
    primera = _pedir(api, cabeceras_cliente)
    recomendados = {p["producto_id"] for p in primera["prendas"]}
    assert set(tienda["con_stock"]) <= recomendados

    caida = tienda["con_stock"][0]
    baja = api.patch(
        f"/api/v1/catalogo/variantes/{tienda['variantes'][caida]}",
        headers=cabeceras_admin,
        json={"activa": False},
    )
    assert baja.status_code == 200, baja.text

    segunda = _pedir(api, cabeceras_cliente)
    quedan = {p["producto_id"] for p in segunda["prendas"]}
    assert caida not in quedan
    assert tienda["con_stock"][1] in quedan


def test_ninguna_prenda_recomendada_se_muestra_SIN_PRECIO(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict, proveedor
) -> None:
    """Es la señal de que se colo una prenda sin variante ofrecible.

    Una tarjeta con nombre y foto pero sin precio se lee como un error de la
    aplicacion, y es exactamente lo que salia cuando la guardada envejecia.
    """
    for prenda in _pedir(api, cabeceras_cliente)["prendas"]:
        assert prenda["precio_desde"], prenda
