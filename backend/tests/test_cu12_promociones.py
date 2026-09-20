"""CU-12 · Gestionar promociones (RF35).

Definir descuentos con vigencia sobre un producto, una categoría o una
temporada — **y que efectivamente descuenten**. Lo segundo no está en el
enunciado del caso de uso, pero una promoción que no rebaja nada no es una
función: es una tabla.

Lo que más importa cubrir
-------------------------
- **Cuando dos promociones se cruzan, gana la mayor.** Es la regla del módulo y
  la que más fácil se rompe sin darse cuenta: sumarlas regalaría la prenda, y
  que ganara siempre la más específica haría que un 10 % del producto tapara el
  20 % que la vitrina anuncia para toda la categoría.
- **No se acumulan nunca.** Se aplica una sola.
- **La vigencia se respeta por los dos lados.** Una que empieza mañana no
  descuenta hoy; una que venció ayer, tampoco. Y `activa` no es lo mismo que
  `vigente`.
- **El precio y el descuento se congelan juntos al vender.** Si mañana la
  promoción se apaga, el pedido tiene que seguir explicando por qué se cobró lo
  que se cobró.
- **El total del servidor y el de la pantalla tienen que coincidir.** CU-27 y
  CU-31 rechazan con 409 si `total_esperado` no da; si el descuento no viajara
  hasta la pantalla, *ninguna* prenda en promoción se podría vender.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

PROMOCIONES = "/api/v1/catalogo/promociones"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
TEMPORADAS = "/api/v1/catalogo/temporadas"

HOY = date.today()
AYER = HOY - timedelta(days=1)
MANANA = HOY + timedelta(days=1)


# =====================================================================
# Montaje
# =====================================================================

@pytest.fixture
def catalogo(api: TestClient, cabeceras_admin: dict) -> dict:
    """Un producto de Bs 250 en la categoría «Camisas» y la temporada «Verano».

    Devuelve los identificadores de todo, porque las promociones se definen
    sobre cada uno de los tres niveles.
    """
    categoria = api.post(
        CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Camisas", "orden": 0, "activa": True}
    )
    assert categoria.status_code == 201, categoria.text

    temporada = api.post(
        TEMPORADAS,
        headers=cabeceras_admin,
        json={
            "nombre": "Verano 2026",
            "descripcion": None,
            "fecha_inicio": AYER.isoformat(),
            "fecha_fin": (HOY + timedelta(days=90)).isoformat(),
            "activa": True,
        },
    )
    assert temporada.status_code == 201, temporada.text

    producto = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "CAM-001",
            "nombre": "Camisa Oxford manga larga",
            "categoria_id": categoria.json()["id"],
            "temporada_id": temporada.json()["id"],
            "precio_base": "250.00",
            "activo": True,
        },
    )
    assert producto.status_code == 201, producto.text

    talla = api.post(
        TALLAS,
        headers=cabeceras_admin,
        json={"tipo_prenda": "Superior", "codigo": "M", "orden": 0, "activa": True},
    )
    color = api.post(
        COLORES,
        headers=cabeceras_admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    )
    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=cabeceras_admin,
        json={"tallas": [talla.json()["id"]], "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text

    return {
        "categoria_id": categoria.json()["id"],
        "temporada_id": temporada.json()["id"],
        "producto_id": producto.json()["id"],
        "variante_id": generadas.json()["variantes"][0]["id"],
    }


def _crear(
    api: TestClient,
    admin: dict,
    *,
    nombre: str,
    alcance: str,
    objetivo_id: int,
    porcentaje: str,
    desde: date = AYER,
    hasta: date | None = None,
    activa: bool = True,
):
    return api.post(
        PROMOCIONES,
        headers=admin,
        json={
            "nombre": nombre,
            "alcance": alcance,
            "objetivo_id": objetivo_id,
            "porcentaje": porcentaje,
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat() if hasta else None,
            "activa": activa,
        },
    )


def _descuento_de(db, variante_id: int, precio: str) -> dict | None:
    """El descuento que gana para esa variante, pasando por el servicio real."""
    from app.modules.catalogo import promociones_service as service

    salida = service.descuentos_por_variante(db, {variante_id: Decimal(precio)})
    d = salida.get(variante_id)
    if d is None:
        return None
    return {
        "nombre": d.nombre,
        "porcentaje": str(d.porcentaje),
        "monto_unitario": str(d.monto_unitario),
        "precio_final": str(d.precio_final),
    }


# =====================================================================
# Autorización
# =====================================================================

def test_sin_token_no_se_gestionan_promociones(api: TestClient) -> None:
    assert api.get(PROMOCIONES).status_code == 401
    assert api.post(PROMOCIONES, json={}).status_code == 401


def test_un_cliente_no_define_descuentos(api: TestClient, cabeceras_cliente: dict) -> None:
    """Un descuento cambia lo que la tienda cobra en todas sus sucursales."""
    assert api.get(PROMOCIONES, headers=cabeceras_cliente).status_code == 403


# =====================================================================
# El alta
# =====================================================================

def test_se_crea_una_promocion_sobre_una_categoria(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    r = _crear(
        api,
        cabeceras_admin,
        nombre="Camisas al 20",
        alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"],
        porcentaje="20.00",
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()

    assert cuerpo["alcance"] == "CATEGORIA"
    assert cuerpo["objetivo_id"] == catalogo["categoria_id"]
    # El objetivo llega NOMBRADO: «la categoría 4» no le dice nada a nadie.
    assert cuerpo["objetivo_nombre"] == "Camisas"
    assert cuerpo["porcentaje"] == "20.00"
    assert cuerpo["vigente"] is True


def test_una_promocion_que_empieza_manana_esta_activa_pero_no_vigente(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    """Sin distinguirlas, el Administrador cree que algo está roto."""
    r = _crear(
        api,
        cabeceras_admin,
        nombre="La que viene",
        alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"],
        porcentaje="30.00",
        desde=MANANA,
    )
    assert r.status_code == 201, r.text
    assert r.json()["activa"] is True
    assert r.json()["vigente"] is False


def test_no_se_puede_apuntar_a_algo_que_no_existe(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    r = _crear(
        api,
        cabeceras_admin,
        nombre="Al vacío",
        alcance="CATEGORIA",
        objetivo_id=987654,
        porcentaje="10.00",
    )
    assert r.status_code == 404
    assert "categoría" in r.json()["detail"].lower()


def test_el_nombre_no_se_repite(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    kwargs = dict(
        nombre="Liquidación", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="10.00",
    )
    assert _crear(api, cabeceras_admin, **kwargs).status_code == 201
    repetida = _crear(api, cabeceras_admin, **kwargs)
    assert repetida.status_code == 409


def test_el_porcentaje_esta_acotado(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    """Cero no es una promoción y más de cien es regalar y poner plata encima."""
    for malo in ("0.00", "-5.00", "101.00"):
        r = _crear(
            api,
            cabeceras_admin,
            nombre=f"Mala {malo}",
            alcance="CATEGORIA",
            objetivo_id=catalogo["categoria_id"],
            porcentaje=malo,
        )
        assert r.status_code == 422, f"aceptó {malo}"


def test_la_vigencia_tiene_que_ser_coherente(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    r = _crear(
        api,
        cabeceras_admin,
        nombre="Al revés",
        alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"],
        porcentaje="10.00",
        desde=HOY,
        hasta=AYER,
    )
    assert r.status_code == 422


# =====================================================================
# LA REGLA: cuál gana
# =====================================================================

def test_una_sola_promocion_descuenta_lo_que_dice(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    _crear(
        api, cabeceras_admin, nombre="Camisas al 20", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="20.00",
    )
    d = _descuento_de(db, catalogo["variante_id"], "250.00")
    assert d["monto_unitario"] == "50.00"
    assert d["precio_final"] == "200.00"
    # Viaja el NOMBRE y no solo el porcentaje: quien ve «−20 %» sin saber de
    # qué se pregunta si es un error.
    assert d["nombre"] == "Camisas al 20"


def test_cuando_dos_se_cruzan_gana_la_mayor_y_no_se_suman(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    """LA PRUEBA QUE SOSTIENE LA REGLA DEL MÓDULO.

    Si se sumaran, dos promociones pensadas por separado terminarían regalando
    la prenda sin que nadie lo haya decidido: 10 % + 20 % = 30 %.

    Si ganara siempre la más específica, el cliente vería el 10 % del producto
    mientras la vitrina anuncia 20 % para toda la categoría — y una tienda que
    anuncia un descuento y después cobra otro tiene un problema peor que el de
    tener dos promociones cruzadas.
    """
    _crear(
        api, cabeceras_admin, nombre="Esta camisa al 10", alcance="PRODUCTO",
        objetivo_id=catalogo["producto_id"], porcentaje="10.00",
    )
    _crear(
        api, cabeceras_admin, nombre="Camisas al 20", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="20.00",
    )

    d = _descuento_de(db, catalogo["variante_id"], "250.00")
    assert d["porcentaje"] == "20.00", "no ganó la mayor"
    assert d["monto_unitario"] == "50.00", "se acumularon"
    assert d["nombre"] == "Camisas al 20"


def test_a_igual_porcentaje_gana_la_mas_especifica(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    """Es la que alguien puso mirando esa prenda concreta."""
    _crear(
        api, cabeceras_admin, nombre="Verano al 15", alcance="TEMPORADA",
        objetivo_id=catalogo["temporada_id"], porcentaje="15.00",
    )
    _crear(
        api, cabeceras_admin, nombre="Esta camisa al 15", alcance="PRODUCTO",
        objetivo_id=catalogo["producto_id"], porcentaje="15.00",
    )

    d = _descuento_de(db, catalogo["variante_id"], "250.00")
    assert d["nombre"] == "Esta camisa al 15"


def test_las_tres_clases_de_alcance_alcanzan(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    """Producto, categoría y temporada llegan las tres a la misma variante."""
    for alcance, clave, pct in (
        ("PRODUCTO", "producto_id", "5.00"),
        ("CATEGORIA", "categoria_id", "6.00"),
        ("TEMPORADA", "temporada_id", "7.00"),
    ):
        # De a una: se crea, se comprueba y se apaga.
        r = _crear(
            api, cabeceras_admin, nombre=f"Sola {alcance}", alcance=alcance,
            objetivo_id=catalogo[clave], porcentaje=pct,
        )
        assert r.status_code == 201, r.text
        d = _descuento_de(db, catalogo["variante_id"], "100.00")
        assert d["porcentaje"] == pct, f"{alcance} no alcanzó"
        api.patch(
            f"{PROMOCIONES}/{r.json()['id']}/estado",
            headers=cabeceras_admin,
            json={"activa": False},
        )


# =====================================================================
# La vigencia
# =====================================================================

def test_una_promocion_que_empieza_manana_no_descuenta_hoy(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    _crear(
        api, cabeceras_admin, nombre="La que viene", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="50.00", desde=MANANA,
    )
    assert _descuento_de(db, catalogo["variante_id"], "250.00") is None


def test_una_promocion_vencida_no_descuenta(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    _crear(
        api, cabeceras_admin, nombre="La que fue", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="50.00",
        desde=HOY - timedelta(days=10), hasta=AYER,
    )
    assert _descuento_de(db, catalogo["variante_id"], "250.00") is None


def test_una_promocion_apagada_no_descuenta(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    r = _crear(
        api, cabeceras_admin, nombre="Apagable", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="40.00",
    )
    assert _descuento_de(db, catalogo["variante_id"], "250.00") is not None

    apagada = api.patch(
        f"{PROMOCIONES}/{r.json()['id']}/estado",
        headers=cabeceras_admin,
        json={"activa": False},
    )
    assert apagada.status_code == 200, apagada.text
    assert apagada.json()["vigente"] is False
    assert _descuento_de(db, catalogo["variante_id"], "250.00") is None


def test_sin_fecha_de_fin_sigue_vigente(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    """«Hasta agotar stock» no tiene una fecha que nadie pueda saber de antemano."""
    _crear(
        api, cabeceras_admin, nombre="Sin fin", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="25.00", hasta=None,
    )
    d = _descuento_de(db, catalogo["variante_id"], "200.00")
    assert d["monto_unitario"] == "50.00"


# =====================================================================
# La edición
# =====================================================================

def test_se_edita_el_porcentaje_y_la_vigencia(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    creada = _crear(
        api, cabeceras_admin, nombre="Editable", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="10.00",
    ).json()

    r = api.patch(
        f"{PROMOCIONES}/{creada['id']}",
        headers=cabeceras_admin,
        json={"porcentaje": "35.00", "hasta": MANANA.isoformat()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["porcentaje"] == "35.00"
    assert r.json()["hasta"] == MANANA.isoformat()


def test_quitar_la_fecha_de_fin_hay_que_pedirlo(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    """En una edición parcial «no vino» y «vino en nulo» son lo mismo."""
    creada = _crear(
        api, cabeceras_admin, nombre="Con fin", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="10.00", hasta=MANANA,
    ).json()

    # Mandar `hasta: null` no la borra: se lee como «no la toques».
    sin_efecto = api.patch(
        f"{PROMOCIONES}/{creada['id']}", headers=cabeceras_admin, json={"hasta": None}
    )
    assert sin_efecto.json()["hasta"] == MANANA.isoformat()

    borrada = api.patch(
        f"{PROMOCIONES}/{creada['id']}",
        headers=cabeceras_admin,
        json={"quitar_hasta": True},
    )
    assert borrada.json()["hasta"] is None


def test_el_alcance_no_se_edita(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    """Cambiarle el alcance a una promoción viva es otra promoción.

    La que estaba corriendo alcanzaba otras prendas, y los pedidos ya cobrados
    con ella quedarían explicados por una regla que ya no dice lo mismo.
    """
    creada = _crear(
        api, cabeceras_admin, nombre="Fija", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="10.00",
    ).json()

    api.patch(
        f"{PROMOCIONES}/{creada['id']}",
        headers=cabeceras_admin,
        json={"alcance": "PRODUCTO", "objetivo_id": catalogo["producto_id"]},
    )
    despues = api.get(f"{PROMOCIONES}/{creada['id']}", headers=cabeceras_admin).json()
    assert despues["alcance"] == "CATEGORIA"
    assert despues["objetivo_id"] == catalogo["categoria_id"]


def test_editar_una_que_no_existe_da_404(
    api: TestClient, cabeceras_admin: dict
) -> None:
    r = api.patch(
        f"{PROMOCIONES}/987654", headers=cabeceras_admin, json={"porcentaje": "5.00"}
    )
    assert r.status_code == 404


# =====================================================================
# La lista
# =====================================================================

def test_la_lista_filtra_por_alcance_y_por_vigencia(
    api: TestClient, cabeceras_admin: dict, catalogo: dict
) -> None:
    _crear(
        api, cabeceras_admin, nombre="Cat vigente", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="10.00",
    )
    _crear(
        api, cabeceras_admin, nombre="Prod futura", alcance="PRODUCTO",
        objetivo_id=catalogo["producto_id"], porcentaje="10.00", desde=MANANA,
    )

    todas = api.get(PROMOCIONES, headers=cabeceras_admin).json()
    assert todas["total"] == 2

    solo_cat = api.get(
        PROMOCIONES, headers=cabeceras_admin, params={"alcance": "CATEGORIA"}
    ).json()
    assert solo_cat["total"] == 1

    vigentes = api.get(
        PROMOCIONES, headers=cabeceras_admin, params={"solo_vigentes": True}
    ).json()
    assert [p["nombre"] for p in vigentes["items"]] == ["Cat vigente"]


# =====================================================================
# El redondeo, que termina en un recibo que alguien lee
# =====================================================================

def test_el_descuento_se_redondea_a_centavos(
    api: TestClient, db, cabeceras_admin: dict, catalogo: dict
) -> None:
    """12,5 % de Bs 249,90 son Bs 31,2375. El recibo no tiene cuatro decimales."""
    _crear(
        api, cabeceras_admin, nombre="Doce y medio", alcance="CATEGORIA",
        objetivo_id=catalogo["categoria_id"], porcentaje="12.50",
    )
    d = _descuento_de(db, catalogo["variante_id"], "249.90")
    assert d["monto_unitario"] == "31.24"
    assert d["precio_final"] == "218.66"
    # Y las dos mitades tienen que seguir sumando el precio de lista.
    assert Decimal(d["monto_unitario"]) + Decimal(d["precio_final"]) == Decimal("249.90")


def test_una_prenda_sin_promocion_no_trae_descuento(
    api: TestClient, db, catalogo: dict
) -> None:
    """No aparece en el diccionario: «no hay» y «hay uno de cero» no se confunden."""
    assert _descuento_de(db, catalogo["variante_id"], "250.00") is None
