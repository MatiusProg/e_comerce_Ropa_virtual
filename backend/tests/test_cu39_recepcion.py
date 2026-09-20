"""CU-38 + CU-39 · El aviso de abastecimiento se CIERRA cuando la prenda llega.

EL HUECO, EN UNA FRASE
-----------------------
Una vez que una prenda aparecía como «próxima a ingresar» **no había forma de
recibirla**. Lo único que existía era el ingreso directo de CU-13, que no sabe
nada del anuncio. Así que la mercadería llegaba, entraba al saldo, y el
consolidado la seguía prometiendo como en camino: **la contaba dos veces**.

La migración 0015 lo había dejado anotado como pendiente, diciendo que atarlo
al ingreso exigía decidir qué pasa si llega la mitad. Esas reglas ahora están
definidas y son lo que este archivo prueba.

Lo que más importa cubrir
-------------------------
- **Que deje de prometerse lo que ya llegó.** Es el defecto que se veía.
- **Que una entrega parcial no cierre el aviso**, porque lo que falta sigue
  estando en camino.
- **Que no se pueda cerrar el aviso de otro proveedor ni el de otra prenda.**
- **Que el ingreso sin aviso siga funcionando igual**: CU-13 existe desde el
  Ciclo 1 y cubre la compra que nadie anunció.
- **Que el proveedor se entere** de que su lote entró.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

INGRESOS = "/api/v1/inventario/ingresos"
AVISOS = f"{INGRESOS}/avisos"
CONSOLIDADO = "/api/v1/inventario/consolidado"
PROVEEDOR = "/api/v1/proveedor/abastecimiento"
PROVEEDORES = "/api/v1/organizacion/proveedores"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
SUCURSALES = "/api/v1/organizacion/sucursales"

CLAVE = "Proveedor123"


@pytest.fixture
def escenario(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Un proveedor con acceso, dos variantes suyas y una sucursal."""
    alta = api.post(
        PROVEEDORES,
        headers=cabeceras_admin,
        json={
            "razon_social": "Textiles del Oriente S.R.L.",
            "identificacion_tributaria": "1023456789",
            "activo": True,
        },
    )
    assert alta.status_code == 201, alta.text
    proveedor = alta.json()["id"]

    acceso = api.post(
        f"{PROVEEDORES}/{proveedor}/acceso",
        headers=cabeceras_admin,
        json={
            "correo": "proveedor.recepcion@violetboutique.bo",
            "contrasena": CLAVE,
            "nombres": "Persona",
            "apellidos": "Del Proveedor",
        },
    )
    assert acceso.status_code in (200, 201), acceso.text

    entrada = api.post(
        "/api/v1/auth/login",
        json={"correo": "proveedor.recepcion@violetboutique.bo", "contrasena": CLAVE},
    )
    cab_prov = {"Authorization": f"Bearer {entrada.json()['access_token']}"}

    categoria = api.post(
        CATEGORIAS,
        headers=cabeceras_admin,
        json={"nombre": "Abrigos", "orden": 0, "activa": True},
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

    sucursal = api.post(
        SUCURSALES,
        headers=cabeceras_admin,
        json={
            "ciudad_id": 1,
            "nombre": "Violet Centro",
            "direccion": "Avenida Centro 100",
            "telefono": None,
            "horario_apertura": "09:00",
            "horario_cierre": "20:00",
            "capacidad_vestidores": 2,
            "activa": True,
        },
    ).json()["id"]

    def _variante(codigo: str, nombre: str) -> int:
        producto = api.post(
            PRODUCTOS,
            headers=cabeceras_admin,
            json={
                "codigo": codigo,
                "nombre": nombre,
                "categoria_id": categoria,
                "proveedor_id": proveedor,
                "precio_base": "300.00",
                "activo": True,
            },
        )
        assert producto.status_code == 201, producto.text
        return api.post(
            f"{PRODUCTOS}/{producto.json()['id']}/variantes",
            headers=cabeceras_admin,
            json={
                "talla_id": talla,
                "color_id": color,
                "precio": "300.00",
                "activa": True,
            },
        ).json()["id"]

    return {
        "proveedor_id": proveedor,
        "cab_prov": cab_prov,
        "sucursal": sucursal,
        "variante_a": _variante("ABR-A", "Abrigo largo"),
        "variante_b": _variante("ABR-B", "Abrigo corto"),
    }


def _anunciar(api: TestClient, esc: dict, variante: int, cantidad: int, dias: int = 7) -> int:
    r = api.post(
        PROVEEDOR,
        headers=esc["cab_prov"],
        json={"variante_id": variante, "cantidad": cantidad, "dias_plazo": dias},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _ingresar(
    api: TestClient, cab: dict, esc: dict, lineas: list[dict], **extra
) -> dict:
    return api.post(
        INGRESOS,
        headers=cab,
        json={
            "sucursal_id": esc["sucursal"],
            "proveedor_id": extra.get("proveedor_id", esc["proveedor_id"]),
            "referencia": "REM-001",
            "lineas": lineas,
        },
    ).json()


# --- Los avisos se pueden ver desde donde se recibe -------------------------


def test_LO_ANUNCIADO_APARECE_COMO_AVISO_DE_INGRESO(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Es la mitad que faltaba: sin esta lista, quien recibe el camión tiene
    que buscar la variante a mano y el aviso nunca se cierra."""
    _anunciar(api, escenario, escenario["variante_a"], 45)

    r = api.get(AVISOS, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    aviso = r.json()[0]
    assert aviso["variante_id"] == escenario["variante_a"]
    assert aviso["cantidad_anunciada"] == 45
    assert aviso["cantidad_pendiente"] == 45
    assert aviso["proveedor"] == "Textiles del Oriente S.R.L."


def test_los_avisos_vienen_por_plazo_no_por_fecha_de_anuncio(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Lo que le sirve a quien recibe es «esto tendría que estar llegando»."""
    _anunciar(api, escenario, escenario["variante_a"], 10, dias=30)
    _anunciar(api, escenario, escenario["variante_b"], 10, dias=2)

    plazos = [a["dias_plazo"] for a in api.get(AVISOS, headers=cabeceras_admin).json()]
    assert plazos == sorted(plazos)


# --- El aviso se cierra -----------------------------------------------------


def test_RECIBIR_LO_ANUNCIADO_DEJA_DE_PROMETERLO(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """El defecto que se veía en la pantalla.

    Antes: la mercadería llegaba, entraba al saldo, y el consolidado seguía
    diciendo «+45 en camino» sobre unidades que ya estaban contadas.
    """
    aviso = _anunciar(api, escenario, escenario["variante_a"], 45)

    ingreso = _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 45, "abastecimiento_id": aviso}],
    )
    assert ingreso["lineas"][0]["pendiente_del_aviso"] == 0

    # Ya no está en camino...
    assert api.get(AVISOS, headers=cabeceras_admin).json() == []

    # ...y el consolidado no lo promete más.
    fila = next(
        f
        for f in api.get(
            CONSOLIDADO,
            headers=cabeceras_admin,
            params={"sucursal_id": escenario["sucursal"]},
        ).json()["listado"]["items"]
        if f["variante_id"] == escenario["variante_a"]
    )
    assert fila["total_disponible"] == 45
    assert fila["cantidad_anunciada"] == 0
    assert fila["estado"] == "disponible"


def test_UNA_ENTREGA_PARCIAL_NO_CIERRA_EL_AVISO(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Lo que falta sigue estando en camino.

    Cerrarlo haría desaparecer de la pantalla mercadería que el proveedor
    todavía debe; dejarlo abierto por el total la contaría dos veces.
    """
    aviso = _anunciar(api, escenario, escenario["variante_a"], 45)

    ingreso = _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 30, "abastecimiento_id": aviso}],
    )
    assert ingreso["lineas"][0]["pendiente_del_aviso"] == 15

    pendiente = api.get(AVISOS, headers=cabeceras_admin).json()[0]
    assert pendiente["cantidad_recibida"] == 30
    assert pendiente["cantidad_pendiente"] == 15


def test_el_resto_se_puede_recibir_despues_y_ahi_si_cierra(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Una entrega puede venir en tres camiones: es un acumulado."""
    aviso = _anunciar(api, escenario, escenario["variante_a"], 45)

    for cuantas in (20, 15, 10):
        _ingresar(
            api,
            cabeceras_admin,
            escenario,
            [
                {
                    "variante_id": escenario["variante_a"],
                    "cantidad": cuantas,
                    "abastecimiento_id": aviso,
                }
            ],
        )

    assert api.get(AVISOS, headers=cabeceras_admin).json() == []


def test_si_llega_DE_MAS_entra_todo_y_el_aviso_se_cierra(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """El sobrante es un dato del remito, no un error.

    La mercadería ya está físicamente en la tienda; rechazar el ingreso
    dejaría el depósito con cajas que el sistema dice que no existen.
    """
    aviso = _anunciar(api, escenario, escenario["variante_a"], 10)

    ingreso = _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 14, "abastecimiento_id": aviso}],
    )
    assert ingreso["lineas"][0]["cantidad"] == 14
    assert ingreso["lineas"][0]["pendiente_del_aviso"] == 0
    assert api.get(AVISOS, headers=cabeceras_admin).json() == []


# --- Lo que no se puede hacer -----------------------------------------------


def test_NO_SE_PUEDE_CERRAR_EL_AVISO_DE_OTRA_PRENDA(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Sin esta comprobación, recibir una blusa cerraría el aviso de un
    pantalón y las dos cuentas quedarían mal a la vez."""
    aviso_de_a = _anunciar(api, escenario, escenario["variante_a"], 10)

    r = api.post(
        INGRESOS,
        headers=cabeceras_admin,
        json={
            "sucursal_id": escenario["sucursal"],
            "proveedor_id": escenario["proveedor_id"],
            "lineas": [
                {
                    "variante_id": escenario["variante_b"],
                    "cantidad": 5,
                    "abastecimiento_id": aviso_de_a,
                }
            ],
        },
    )
    assert r.status_code == 422, r.text
    assert "otra prenda" in r.json()["detail"]


def test_no_se_puede_cerrar_el_aviso_de_OTRO_PROVEEDOR(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Llegaría la mercadería de uno y el sistema descontaría la deuda del
    otro."""
    aviso = _anunciar(api, escenario, escenario["variante_a"], 10)

    otro = api.post(
        PROVEEDORES,
        headers=cabeceras_admin,
        json={
            "razon_social": "Denim Bolivia S.R.L.",
            "identificacion_tributaria": "9988776655",
            "activo": True,
        },
    ).json()["id"]

    r = api.post(
        INGRESOS,
        headers=cabeceras_admin,
        json={
            "sucursal_id": escenario["sucursal"],
            "proveedor_id": otro,
            "lineas": [
                {
                    "variante_id": escenario["variante_a"],
                    "cantidad": 10,
                    "abastecimiento_id": aviso,
                }
            ],
        },
    )
    assert r.status_code == 422, r.text
    assert "otro proveedor" in r.json()["detail"]


def test_un_aviso_ya_recibido_no_se_puede_recibir_de_nuevo(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    aviso = _anunciar(api, escenario, escenario["variante_a"], 10)
    _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 10, "abastecimiento_id": aviso}],
    )

    r = api.post(
        INGRESOS,
        headers=cabeceras_admin,
        json={
            "sucursal_id": escenario["sucursal"],
            "proveedor_id": escenario["proveedor_id"],
            "lineas": [
                {
                    "variante_id": escenario["variante_a"],
                    "cantidad": 10,
                    "abastecimiento_id": aviso,
                }
            ],
        },
    )
    assert r.status_code in (404, 409), r.text


def test_UN_AVISO_INVALIDO_NO_DEJA_MEDIO_REMITO_CARGADO(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Excepción E9: el ingreso es una transacción.

    Los avisos se resuelven ANTES de tocar ningún saldo justamente para esto:
    si la segunda línea es inválida, la primera no puede haber entrado.
    """
    r = api.post(
        INGRESOS,
        headers=cabeceras_admin,
        json={
            "sucursal_id": escenario["sucursal"],
            "proveedor_id": escenario["proveedor_id"],
            "lineas": [
                {"variante_id": escenario["variante_a"], "cantidad": 5},
                {
                    "variante_id": escenario["variante_b"],
                    "cantidad": 5,
                    "abastecimiento_id": 99999,
                },
            ],
        },
    )
    assert r.status_code == 404, r.text

    consolidado = api.get(
        CONSOLIDADO,
        headers=cabeceras_admin,
        params={"sucursal_id": escenario["sucursal"]},
    ).json()["listado"]["items"]
    assert all(f["total_disponible"] == 0 for f in consolidado), consolidado


# --- Lo que NO cambia -------------------------------------------------------


def test_EL_INGRESO_SIN_AVISO_SIGUE_FUNCIONANDO_IGUAL(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """CU-13 existe desde el Ciclo 1 y cubre la compra que nadie anunció.

    Exigir el aviso lo rompería, y obligaría a inventar un anuncio para cada
    caja que entra por la puerta.
    """
    ingreso = _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 7}],
    )
    assert ingreso["lineas"][0]["disponible_resultante"] == 7
    assert ingreso["lineas"][0]["abastecimiento_id"] is None


# --- El proveedor se entera -------------------------------------------------


def test_EL_PROVEEDOR_VE_QUE_SU_LOTE_ENTRO(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """Antes anunciaba y no se enteraba de nada: el aviso quedaba
    «ANUNCIADO» para siempre aunque la mercadería hubiera llegado hace
    semanas."""
    aviso = _anunciar(api, escenario, escenario["variante_a"], 45)
    _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 45, "abastecimiento_id": aviso}],
    )

    mios = api.get(PROVEEDOR, headers=escenario["cab_prov"]).json()
    entregado = next(a for a in mios if a["id"] == aviso)
    assert entregado["estado"] == "RECIBIDO"
    assert entregado["cantidad_recibida"] == 45
    assert entregado["cantidad_pendiente"] == 0
    assert entregado["recibido_en"] is not None


def test_el_proveedor_ve_cuanto_falta_de_una_entrega_parcial(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """«Ingresaron 30 de 45», sin tener que llamar por teléfono."""
    aviso = _anunciar(api, escenario, escenario["variante_a"], 45)
    _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 30, "abastecimiento_id": aviso}],
    )

    mio = next(
        a for a in api.get(PROVEEDOR, headers=escenario["cab_prov"]).json()
        if a["id"] == aviso
    )
    assert mio["estado"] == "ANUNCIADO"
    assert mio["cantidad_recibida"] == 30
    assert mio["cantidad_pendiente"] == 15


def test_un_aviso_recibido_no_bloquea_anunciar_el_lote_siguiente(
    api: TestClient, cabeceras_admin: dict[str, str], escenario: dict
) -> None:
    """El índice único parcial es sobre ANUNCIADO justamente para esto."""
    aviso = _anunciar(api, escenario, escenario["variante_a"], 10)
    _ingresar(
        api,
        cabeceras_admin,
        escenario,
        [{"variante_id": escenario["variante_a"], "cantidad": 10, "abastecimiento_id": aviso}],
    )

    segundo = _anunciar(api, escenario, escenario["variante_a"], 20)
    assert segundo != aviso
