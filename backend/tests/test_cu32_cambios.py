"""CU-32 · Cambiar una prenda por otra (segundo flujo).

La prenda vieja vuelve al inventario, otra sale, y **lo único que mueve plata
es la diferencia entre las dos**.

Lo que más importa cubrir
-------------------------
- **El arqueo no puede contar la venta nueva.** Es el riesgo central del flujo.
  La venta del cambio vale la prenda que sale —Bs 250—, no lo que entró al
  cajón —Bs 50—. Si sumara entera, el turno cerraría con un sobrante de 200
  que el cajero no puede explicar ni contando bien, y un arqueo que descuadra
  solo enseña a ignorarlo. Lo garantiza `metodo_pago = 'CAMBIO'`.
- **La diferencia va con signo y se salda por donde se diga.** Positiva la pone
  el cliente, negativa la tienda. Solo toca el cajón si se salda en efectivo:
  una diferencia cobrada con tarjeta no entra al cajón, igual que no entra una
  venta con tarjeta.
- **Primero entra lo viejo y después sale lo nuevo.** Es el orden del mostrador
  y es lo único que deja cambiar una prenda fallada por **otra idéntica**
  cuando era la última: al revés, el descuento no encontraría stock de una
  prenda que el cliente tiene en la mano.
- **El plazo.** Dos días desde el cobro, contados en horas, y vale igual para
  devolver que para cambiar —si el cambio durara más, cambiar y después
  devolver sería la forma de devolver fuera de plazo—.
- **Todo o nada.** Si falta stock de lo nuevo, no puede quedar la prenda vieja
  reingresada contra un cambio que no ocurrió.

Los ayudantes se importan de CU-31 y CU-32 en vez de copiarse, por el mismo
motivo que aquellas se importan entre sí: es el mismo montaje, y dos copias que
empiezan a divergir hacen que una de las dos deje de probar lo que dice.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core import tiempo
from tests.test_cu31_venta_presencial import (  # noqa: F401 - fixtures de pytest
    PRECIO,
    _abrir_turno,
    _caja,
    _crear_sucursal,
    _disponible,
    _empleado,
    cajero,
    mostrador,
    stock,
    sucursal,
    variantes,
)
from tests.test_cu32_devoluciones import _devolver, _vender

DEVOLUCIONES = "/api/v1/pos/devoluciones"
CAMBIOS = f"{DEVOLUCIONES}/cambios"
CAJA_MIO = "/api/v1/caja/turnos/mio"


# =====================================================================
# Ayudantes
# =====================================================================

def _cambiar(
    api: TestClient,
    cab: dict,
    codigo: str,
    *,
    devuelve: tuple[int, int],
    lleva: tuple[int, int],
    metodo: str | None = None,
    esperada: str | None = None,
    motivo: str = "Le quedó grande",
):
    cuerpo: dict = {
        "venta_codigo": codigo,
        "motivo": motivo,
        "devueltas": [{"variante_id": devuelve[0], "cantidad": devuelve[1]}],
        "llevadas": [{"variante_id": lleva[0], "cantidad": lleva[1]}],
    }
    if metodo is not None:
        cuerpo["metodo_diferencia"] = metodo
    if esperada is not None:
        cuerpo["diferencia_esperada"] = esperada
    return api.post(CAMBIOS, headers=cab, json=cuerpo)


def _fijar_precio(db, variante_id: int, precio: str) -> None:
    """Le pone otro precio a una variante.

    Se toca la base y no un endpoint a propósito: lo que estas pruebas quieren
    es **una diferencia de precio entre dos prendas**, no ejercitar el alta del
    catálogo. Las dos variantes del montaje salen del mismo producto y por eso
    nacen valiendo lo mismo.
    """
    from app.modules.catalogo.models import VarianteProducto

    fila = db.get(VarianteProducto, variante_id)
    fila.precio = Decimal(precio)
    db.commit()


def _envejecer_venta(db, codigo: str, dias: int) -> None:
    """Retrasa la fecha de una venta, para probar el plazo sin esperar dos días."""
    from app.modules.ventas.models import Venta

    fila = db.query(Venta).filter(Venta.codigo == codigo).one()
    fila.creado_en = tiempo.ahora() - timedelta(days=dias)
    db.commit()


def _arqueo(api: TestClient, cab: dict) -> dict:
    r = api.get(CAJA_MIO, headers=cab)
    assert r.status_code == 200, r.text
    return r.json()


# =====================================================================
# Autorización
# =====================================================================

def test_sin_token_no_se_cambia_nada(api: TestClient) -> None:
    assert api.post(CAMBIOS, json={}).status_code == 401


def test_un_cliente_no_registra_cambios(
    api: TestClient, cabeceras_cliente: dict
) -> None:
    assert api.post(CAMBIOS, headers=cabeceras_cliente, json={}).status_code == 403


# =====================================================================
# El cambio parejo: las dos prendas valen lo mismo
# =====================================================================

def test_cambio_parejo_no_mueve_plata(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Las dos salen del mismo producto, así que valen lo mismo.

    Es el caso más común del mostrador —se lleva otra talla— y el que tiene que
    salir sin que nadie toque el cajón.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 201, r.text
    cambio = r.json()

    assert Decimal(cambio["diferencia"]) == Decimal("0.00")
    assert cambio["a_favor_de"] == "NADIE"
    assert cambio["metodo_diferencia"] is None
    assert cambio["toca_el_cajon"] is False
    # La venta nueva existe y trae su comprobante: el cliente se va con papel.
    assert cambio["venta_nueva_codigo"].startswith("VP-")
    assert cambio["venta_nueva_codigo"] != cambio["venta_codigo"]
    assert cambio["comprobante_numero"]


def test_un_cambio_parejo_con_metodo_se_rechaza(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Un método de pago contra una diferencia de cero no se guarda en silencio.

    El CHECK `ck_devolucion_metodo_si_hay_diferencia` lo rechazaría igual, pero
    como error de integridad —que para el cajero es un «error del sistema» sin
    causa—. Se atrapa antes, con el motivo.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO",
    )
    assert r.status_code == 422
    assert "no hay diferencia" in r.json()["detail"].lower()


# =====================================================================
# La diferencia, que es lo único que mueve plata
# =====================================================================

def test_la_prenda_nueva_cuesta_mas_y_la_diferencia_la_pone_el_cliente(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "300.00")

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO",
    )
    assert r.status_code == 201, r.text
    cambio = r.json()

    assert Decimal(cambio["valor_devuelto"]) == PRECIO
    assert Decimal(cambio["total_llevado"]) == Decimal("300.00")
    assert Decimal(cambio["diferencia"]) == Decimal("50.00")
    assert cambio["a_favor_de"] == "CLIENTE"
    assert cambio["toca_el_cajon"] is True


def test_la_prenda_nueva_cuesta_menos_y_la_diferencia_la_pone_la_tienda(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """La diferencia negativa es el caso que un campo sin signo no sabría decir."""
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "180.00")

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO",
    )
    assert r.status_code == 201, r.text
    cambio = r.json()

    assert Decimal(cambio["diferencia"]) == Decimal("-70.00")
    assert cambio["a_favor_de"] == "TIENDA"


def test_hay_diferencia_y_no_se_dice_como_se_salda(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "300.00")

    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 422
    assert "forma de pago" in r.json()["detail"].lower()


def test_si_la_diferencia_no_es_la_que_la_pantalla_calculo_se_frena(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """Mismo espíritu que `ConflictoDePrecio` en CU-31.

    Entre que el cajero arma el cambio y confirma, una promoción de CU-12 pudo
    empezar. Se le muestra el número nuevo en vez de cobrarle al cliente algo
    que no vio en pantalla.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "300.00")

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO", esperada="20.00",
    )
    assert r.status_code == 409
    assert "50" in r.json()["detail"]


# =====================================================================
# EL ARQUEO: lo que este flujo puede romper
# =====================================================================

def test_el_arqueo_cuenta_la_diferencia_y_no_la_venta_entera(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """El corazón del flujo.

    Apertura 100 + venta en efectivo 250 = 350 antes del cambio. El cliente
    cambia por una de 300 y pone 50 en efectivo, así que el cajón tiene 400.

    Si la venta nueva contara como efectivo, el esperado diría 700: los 350 de
    antes más 300 de una prenda que se pagó con otra prenda. Sobrarían 300 que
    nadie puso.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "300.00")

    antes = _arqueo(api, cab)
    assert Decimal(antes["monto_esperado"]) == Decimal("350.00")

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO",
    )
    assert r.status_code == 201, r.text

    despues = _arqueo(api, cab)
    assert Decimal(despues["cambios"]) == Decimal("50.00")
    assert Decimal(despues["monto_esperado"]) == Decimal("400.00")
    # La venta vieja sigue contada entera: una devolución no corrige la venta,
    # y un cambio tampoco. Lo que cambia es que ahora hay 50 más en el cajón.
    assert Decimal(despues["efectivo_cobrado"]) == PRECIO


def test_una_diferencia_a_favor_de_la_tienda_baja_el_esperado(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "180.00")

    _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO",
    )

    arqueo = _arqueo(api, cab)
    assert Decimal(arqueo["cambios"]) == Decimal("-70.00")
    assert Decimal(arqueo["monto_esperado"]) == Decimal("280.00")  # 100 + 250 - 70


def test_una_diferencia_con_tarjeta_no_toca_el_cajon(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """Mismo principio que una venta con tarjeta: esa plata no entra al cajón.

    El filtro es por cómo se salda HOY, no por cómo se pagó la venta original.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "300.00")

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="TARJETA",
    )
    assert r.status_code == 201, r.text
    assert r.json()["toca_el_cajon"] is False

    arqueo = _arqueo(api, cab)
    assert Decimal(arqueo["cambios"]) == Decimal("0.00")
    assert Decimal(arqueo["monto_esperado"]) == Decimal("350.00")


def test_la_venta_del_cambio_aparece_en_el_desglose_con_su_propio_metodo(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """No se esconde: la mercadería salió del local y el cajero la movió.

    Lo que la línea NO dice es plata que haya entrado al cajón.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))

    por_metodo = {l["metodo"]: l for l in _arqueo(api, cab)["por_metodo"]}
    assert "CAMBIO" in por_metodo
    assert por_metodo["CAMBIO"]["ventas"] == 1
    assert Decimal(por_metodo["CAMBIO"]["total"]) == PRECIO


# =====================================================================
# El inventario
# =====================================================================

def test_la_vieja_vuelve_y_la_nueva_sale(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    antes_vieja = _disponible(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]
    )
    antes_nueva = _disponible(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1]
    )

    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 201, r.text

    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
        == antes_vieja + 1
    )
    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1])
        == antes_nueva - 1
    )


def test_cambiar_una_prenda_fallada_por_otra_identica_siendo_la_ultima(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """El caso que justifica el orden: primero entra lo viejo, después sale lo nuevo.

    La segunda prenda tiene 4 unidades. Se venden las 4, así que queda 0. El
    cliente vuelve con una fallada y quiere otra igual: la única disponible es
    justamente la que trae en la mano.

    Si el sistema descontara antes de reingresar, rechazaría el cambio por
    falta de stock con la prenda sobre el mostrador.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[1], 4)
    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1])
        == 0
    )

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[1], 1), lleva=(variantes[1], 1),
        motivo="Vino con una costura abierta",
    )
    assert r.status_code == 201, r.text
    assert Decimal(r.json()["diferencia"]) == Decimal("0.00")
    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[1])
        == 0
    )


def test_sin_stock_de_la_nueva_no_queda_la_vieja_reingresada(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Todo o nada. Es lo que no puede garantizar una devolución seguida de una venta."""
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    # Se agota la segunda prenda: 4 unidades, se venden las 4.
    _vender(api, cab, variantes[1], 4)

    antes = _disponible(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]
    )

    # Con método: llevarse dos devolviendo una deja Bs 250 de diferencia, y sin
    # decir cómo se salda el servicio frena ahí —antes de mirar el stock— y la
    # prueba no llegaría a probar lo que dice.
    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 2),
        metodo="EFECTIVO",
    )
    assert r.status_code == 409, r.text

    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
        == antes
    )
    # Y la venta original sigue entera por devolver.
    quedan = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab).json()
    assert quedan["lineas"][0]["devolvibles"] == 1


# =====================================================================
# Qué se puede cambiar, y hasta cuándo
# =====================================================================

def test_no_se_puede_cambiar_una_prenda_que_no_estaba_en_esa_venta(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    r = _cambiar(api, cab, codigo, devuelve=(variantes[1], 1), lleva=(variantes[0], 1))
    assert r.status_code == 422


def test_un_cambio_gasta_el_saldo_devolvible_de_la_venta(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Cambiar y devolver salen del mismo saldo.

    Si no, cambiar una prenda y después devolverla reingresaría dos veces una
    prenda que salió una sola.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    assert _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1)
    ).status_code == 201

    r = _devolver(api, cab, codigo, variantes[0], 1)
    assert r.status_code == 409
    assert "ya se devolvió" in r.json()["detail"]


@pytest.mark.parametrize("dias", [3, 10])
def test_fuera_de_plazo_no_se_cambia(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db, dias: int
) -> None:
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _envejecer_venta(db, codigo, dias)

    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 409
    assert "plazo" in r.json()["detail"].lower()


def test_fuera_de_plazo_tampoco_se_devuelve(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """El plazo es el mismo para los dos flujos, a propósito.

    Si el cambio durara más que la devolución, cambiar por algo y devolver eso
    sería la forma de devolver fuera de plazo.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _envejecer_venta(db, codigo, 3)

    r = _devolver(api, cab, codigo, variantes[0], 1)
    assert r.status_code == 409
    assert "plazo" in r.json()["detail"].lower()


def test_dentro_del_plazo_todavia_se_cambia(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """El borde de adentro. Sin esto, un plazo roto que rechace todo pasaría.

    Un día y medio es menos que los dos del plazo por defecto.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    from app.modules.ventas.models import Venta

    fila = db.query(Venta).filter(Venta.codigo == codigo).one()
    fila.creado_en = tiempo.ahora() - timedelta(days=1, hours=12)
    db.commit()

    r = _cambiar(api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1))
    assert r.status_code == 201, r.text


def test_la_busqueda_avisa_del_plazo_antes_de_armar_nada(
    api: TestClient, mostrador: dict, variantes: list[int], stock, db
) -> None:
    """Una venta vencida se puede MIRAR, no registrar.

    El cajero necesita abrirla para explicarle al cliente por qué no se puede y
    desde cuándo. Un plazo que solo se descubre al confirmar hace perder el
    trabajo hecho y deja al cajero discutiendo sin un número que mostrar.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    fresca = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab).json()
    assert fresca["plazo_dias"] == 2
    assert fresca["dentro_de_plazo"] is True

    _envejecer_venta(db, codigo, 3)

    vencida = api.get(f"{DEVOLUCIONES}/ventas/{codigo}", headers=cab)
    assert vencida.status_code == 200, vencida.text
    assert vencida.json()["dentro_de_plazo"] is False


# =====================================================================
# EL TABLERO Y EL REPORTE: que el dinero devuelto se vea en algún lado
# =====================================================================
#
# Hasta el 24/09/2026 no se veía en ninguno de los dos. El tablero sumaba
# `venta.total` sin restar nada, y ningún reporte tocaba la tabla `devolucion`.
# El cambio de prenda lo hizo evidente: la venta original se seguía contando y
# ADEMÁS nacía una venta nueva por la prenda que sale.

TABLERO = "/api/v1/reportes/tablero"
REPORTE_DEVOLUCIONES = "/api/v1/reportes/devoluciones.xlsx"


def _ventas_del_tablero(api: TestClient, admin: dict) -> dict:
    r = api.get(TABLERO, headers=admin)
    assert r.status_code == 200, r.text
    return r.json()["ventas"]


def test_el_tablero_resta_lo_devuelto(
    api: TestClient, mostrador: dict, cabeceras_admin: dict, variantes: list[int], stock
) -> None:
    """Vender 250 y que lo devuelvan entero no deja 250 vendidos: deja 0.

    El bruto no cambia —esa venta ocurrió— pero el neto sí, que es el número
    que responde «cómo nos fue».
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)

    antes = _ventas_del_tablero(api, cabeceras_admin)
    assert Decimal(antes["monto_periodo"]) == PRECIO
    assert Decimal(antes["devuelto_periodo"]) == Decimal("0.00")
    assert Decimal(antes["neto_periodo"]) == PRECIO

    assert _devolver(api, cab, codigo, variantes[0], 1).status_code == 201

    despues = _ventas_del_tablero(api, cabeceras_admin)
    # El BRUTO no se toca: una devolución no corrige la venta.
    assert Decimal(despues["monto_periodo"]) == PRECIO
    assert Decimal(despues["devuelto_periodo"]) == PRECIO
    assert Decimal(despues["neto_periodo"]) == Decimal("0.00")


def test_el_tablero_no_cuenta_dos_veces_un_cambio(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    variantes: list[int],
    stock,
    db,
) -> None:
    """El caso que destapó el problema.

    Se vende un cinturón de 250 y se cambia por uno de 300. A la tienda le
    quedó una prenda de 300 vendida y nada más: el neto tiene que decir 300.

    En bruto son 550 —la venta original más la del cambio— y así fue siempre.
    Lo que faltaba era restar los 250 que volvieron a la percha.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _fijar_precio(db, variantes[1], "300.00")

    r = _cambiar(
        api, cab, codigo, devuelve=(variantes[0], 1), lleva=(variantes[1], 1),
        metodo="EFECTIVO",
    )
    assert r.status_code == 201, r.text

    ventas = _ventas_del_tablero(api, cabeceras_admin)
    assert Decimal(ventas["monto_periodo"]) == Decimal("550.00")
    assert Decimal(ventas["devuelto_periodo"]) == PRECIO
    # Lo único que de verdad quedó vendido: la prenda que se llevó.
    assert Decimal(ventas["neto_periodo"]) == Decimal("300.00")


def test_el_ticket_promedio_sigue_saliendo_del_bruto(
    api: TestClient, mostrador: dict, cabeceras_admin: dict, variantes: list[int], stock
) -> None:
    """A propósito: es cuánto gasta quien compra.

    Una devolución posterior no cambia lo que esa persona gastó ese día, y
    netearlo haría que el ticket promedio bajara sin que nadie comprara menos.
    """
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    _devolver(api, cab, codigo, variantes[0], 1)

    ventas = _ventas_del_tablero(api, cabeceras_admin)
    assert Decimal(ventas["ticket_promedio"]) == PRECIO


def test_el_reporte_de_devoluciones_trae_el_valor_devuelto(
    api: TestClient, mostrador: dict, cabeceras_admin: dict, variantes: list[int], stock
) -> None:
    """El reporte que no existía. Se pide en Excel para no parsear un PDF."""
    cab = mostrador["cabeceras"]
    codigo = _vender(api, cab, variantes[0], 1)
    assert _devolver(api, cab, codigo, variantes[0], 1).status_code == 201

    r = api.get(REPORTE_DEVOLUCIONES, headers=cabeceras_admin)
    assert r.status_code == 200, r.text
    assert len(r.content) > 0

    # Y que el catálogo lo ofrezca, que es de donde la pantalla saca la lista.
    catalogo = api.get("/api/v1/reportes/catalogo", headers=cabeceras_admin).json()
    devoluciones = next(f for f in catalogo if f["tipo"] == "devoluciones")
    assert "Valor devuelto" in devoluciones["columnas"]
