"""CU-31 · Registrar venta presencial.

Dos caminos de entrada —buscar las prendas, o cargar una reserva ya atendida—
y un solo resultado: una venta PRESENCIAL que nace PAGADA, colgada de un turno
abierto, con su comprobante emitido y el inventario en su lugar.

Lo que más importa cubrir
-------------------------
- **La reserva ya atendida NO se vuelve a descontar.** CU-24 escribió
  `LIBERACION +n` y `VENTA −n` al cerrar la reserva: el cliente se llevó la
  prenda del probador. Un segundo descuento contaría las mismas unidades dos
  veces y dejaría el inventario mintiendo sin que nada reventara. Es el
  agujero más caro de este caso de uso y el más fácil de abrir sin darse
  cuenta.
- **El arqueo de CU-30 tiene que ver estas ventas.** Si `turno_caja_id` o
  `metodo_pago` quedaran mal, el turno cerraría con un descuadre que nadie
  puede explicar — y un arqueo que siempre descuadra enseña a ignorarlo.
- **Tarjeta y QR no entran al cajón.** La venta se registra igual, pero el
  esperado no se mueve.
- **Sin turno abierto no se cobra.** El CHECK `ck_venta_turno_segun_canal` lo
  exige; el servicio lo dice con palabras en vez de dejar que reviente.
- **El ámbito sale del turno, nunca del cuerpo.** Una prenda de otra sucursal
  no existe para este cajero.
- **Si falta stock no queda nada a medias**: ni venta, ni comprobante, ni
  inventario tocado.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

PRENDAS = "/api/v1/pos/prendas"
VENTAS = "/api/v1/pos/ventas"
RESERVAS_POS = "/api/v1/pos/reservas"

CAJA_TURNOS = "/api/v1/caja/turnos"
CAJA_MIO = "/api/v1/caja/turnos/mio"

RESERVAS = "/api/v1/reservas"
PANEL = "/api/v1/sucursal/reservas"
EXISTENCIAS = "/api/v1/inventario/existencias"
INGRESOS = "/api/v1/inventario/ingresos"

SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EMPLEADOS = "/api/v1/organizacion/empleados"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"

BOLIVIA = timezone(timedelta(hours=-4))

PRECIO = Decimal("250.00")


# =====================================================================
# Ayudantes
# =====================================================================

def _crear_sucursal(api: TestClient, admin: dict, *, nombre: str) -> int:
    ciudad_id = api.get(CIUDADES, headers=admin).json()[0]["id"]
    r = api.post(
        SUCURSALES,
        headers=admin,
        json={
            "ciudad_id": ciudad_id,
            "nombre": nombre,
            "direccion": f"Avenida {nombre} 100",
            "telefono": None,
            "horario_apertura": "09:00:00",
            "horario_cierre": "20:00:00",
            "capacidad_vestidores": 4,
            "activa": True,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_variantes(api: TestClient, admin: dict) -> list[int]:
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Camisas", "orden": 0, "activa": True}
    )
    producto = api.post(
        PRODUCTOS,
        headers=admin,
        json={
            "codigo": "CAM-001",
            "nombre": "Camisa Oxford manga larga",
            "categoria_id": categoria.json()["id"],
            "precio_base": str(PRECIO),
            "activo": True,
        },
    )
    tallas = []
    for indice, codigo in enumerate(("S", "M")):
        t = api.post(
            TALLAS,
            headers=admin,
            json={"tipo_prenda": "Superior", "codigo": codigo, "orden": indice, "activa": True},
        )
        tallas.append(t.json()["id"])
    color = api.post(
        COLORES, headers=admin, json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True}
    )
    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=admin,
        json={"tallas": tallas, "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text
    return [v["id"] for v in generadas.json()["variantes"]]


def _ingresar(
    api: TestClient, admin: dict, *, sucursal_id: int, lineas: list[tuple[int, int]]
) -> None:
    creado = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Textiles del Sur SRL",
            "identificacion_tributaria": "1023456789",
            "activo": True,
        },
    )
    proveedor_id = (
        api.get(PROVEEDORES, headers=admin).json()[0]["id"]
        if creado.status_code == 409
        else creado.json()["id"]
    )
    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": "REM-POS",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


def _empleado(
    api: TestClient, admin: dict, *, cargo: str, sucursal_id: int, sufijo: str
) -> dict[str, str]:
    correo = f"{cargo.lower()}{sufijo}@violetboutique.bo"
    clave = "Mostrador12"
    r = api.post(
        EMPLEADOS,
        headers=admin,
        json={
            "nombres": "Ana",
            "apellidos": f"{cargo.title()}{sufijo}",
            "correo": correo,
            "contrasena": clave,
            "documento": f"91{cargo[:2]}{sufijo}0001",
            "telefono": "70000001",
            "cargo": cargo,
            "sucursal_id": sucursal_id,
            "fecha_ingreso": (date.today() - timedelta(days=10)).isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    entrada = api.post("/api/v1/auth/login", json={"correo": correo, "contrasena": clave})
    assert entrada.status_code == 200, entrada.text
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


def _caja(db, sucursal_id: int, nombre: str = "Caja 1") -> int:
    """Una caja en la base: el alta de cajas no tiene endpoint (ver CU-30)."""
    from app.modules.ventas.models import Caja

    fila = Caja(sucursal_id=sucursal_id, nombre=nombre, activa=True)
    db.add(fila)
    db.commit()
    db.refresh(fila)
    return fila.id


def _abrir_turno(api: TestClient, cab: dict, caja_id: int, monto: str = "100.00") -> int:
    r = api.post(CAJA_TURNOS, headers=cab, json={"caja_id": caja_id, "monto_apertura": monto})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _disponible(api: TestClient, admin: dict, *, sucursal_id: int, variante_id: int) -> int:
    filas = api.get(
        EXISTENCIAS, headers=admin, params={"tamano": 100, "sucursal_id": sucursal_id}
    ).json()["items"]
    for f in filas:
        if f["variante_id"] == variante_id:
            return f["cantidad_disponible"]
    raise AssertionError(f"no hay existencia de {variante_id} en {sucursal_id}")


def _manana(hora: int) -> datetime:
    dia = datetime.now(BOLIVIA) + timedelta(days=1)
    return dia.replace(hour=hora, minute=0, second=0, microsecond=0)


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variantes(api: TestClient, cabeceras_admin: dict) -> list[int]:
    return _crear_variantes(api, cabeceras_admin)


@pytest.fixture
def stock(api: TestClient, cabeceras_admin: dict, sucursal: int, variantes: list[int]):
    """10 unidades de la primera prenda y 4 de la segunda, en Centro."""
    _ingresar(
        api,
        cabeceras_admin,
        sucursal_id=sucursal,
        lineas=[(variantes[0], 10), (variantes[1], 4)],
    )


@pytest.fixture
def cajero(api: TestClient, cabeceras_admin: dict, sucursal: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=sucursal, sufijo="1")


@pytest.fixture
def encargado(api: TestClient, cabeceras_admin: dict, sucursal: int) -> dict:
    return _empleado(api, cabeceras_admin, cargo="ENCARGADO", sucursal_id=sucursal, sufijo="1")


@pytest.fixture
def mostrador(api: TestClient, cajero: dict, db, sucursal: int) -> dict:
    """Un cajero de Centro con su turno ya abierto. El punto de partida real."""
    caja_id = _caja(db, sucursal)
    turno_id = _abrir_turno(api, cajero, caja_id)
    return {"cabeceras": cajero, "caja_id": caja_id, "turno_id": turno_id}


@pytest.fixture
def reserva_atendida(
    api: TestClient,
    cabeceras_admin: dict,
    cabeceras_cliente: dict,
    encargado: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> dict:
    """Una reserva cerrada con una prenda LLEVA y otra NO_LLEVA.

    Es el puente de D2 tal como llega al mostrador: CU-24 ya movió el
    inventario de las dos —liberó las dos, descontó la que se llevó— y lo único
    que falta es cobrar.
    """
    creada = api.post(
        RESERVAS,
        headers=cabeceras_cliente,
        json={
            "sucursal_id": sucursal,
            "franja_inicio": _manana(15).isoformat(),
            "franja_fin": _manana(16).isoformat(),
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 2},
                {"variante_id": variantes[1], "cantidad": 1},
            ],
        },
    )
    assert creada.status_code == 201, creada.text
    reserva = creada.json()

    preparada = api.patch(f"{PANEL}/{reserva['id']}/preparacion", headers=encargado)
    assert preparada.status_code == 200, preparada.text

    resultados = {
        "resultados": [
            {"detalle_id": reserva["lineas"][0]["id"], "resultado": "LLEVA"},
            {"detalle_id": reserva["lineas"][1]["id"], "resultado": "NO_LLEVA"},
        ]
    }
    atendida = api.patch(
        f"{PANEL}/{reserva['id']}/atencion", headers=encargado, json=resultados
    )
    assert atendida.status_code == 200, atendida.text
    return reserva


# =====================================================================
# Autorización y ámbito
# =====================================================================

def test_sin_token_no_se_entra_al_mostrador(api: TestClient) -> None:
    assert api.get(PRENDAS).status_code == 401
    assert api.post(VENTAS, json={"metodo_pago": "EFECTIVO"}).status_code == 401


def test_un_cliente_no_cobra_en_el_mostrador(
    api: TestClient, cabeceras_cliente: dict
) -> None:
    assert api.get(PRENDAS, headers=cabeceras_cliente).status_code == 403


def test_el_administrador_tampoco(api: TestClient, cabeceras_admin: dict) -> None:
    """No está en una sucursal y no tiene turno: una venta suya no tendría arqueo."""
    assert api.get(PRENDAS, headers=cabeceras_admin).status_code == 403


# =====================================================================
# Sin turno abierto no se hace nada
# =====================================================================

def test_sin_turno_abierto_no_se_pueden_ni_ver_las_prendas(
    api: TestClient, cajero: dict, stock
) -> None:
    r = api.get(PRENDAS, headers=cajero)
    assert r.status_code == 409
    assert "abra su turno" in r.json()["detail"].lower()


def test_sin_turno_abierto_no_se_puede_cobrar(
    api: TestClient, cajero: dict, variantes: list[int], stock
) -> None:
    r = api.post(
        VENTAS,
        headers=cajero,
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert r.status_code == 409


def test_al_cerrar_el_turno_se_deja_de_poder_cobrar(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """El cierre no es cosmético: cierra la puerta de CU-31."""
    cierre = api.post(
        f"{CAJA_TURNOS}/{mostrador['turno_id']}/cierre",
        headers=mostrador["cabeceras"],
        json={"monto_cierre": "100.00"},
    )
    assert cierre.status_code == 200, cierre.text

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert r.status_code == 409


# =====================================================================
# Buscar qué vender
# =====================================================================

def test_las_prendas_llegan_con_precio_y_saldo(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    r = api.get(PRENDAS, headers=mostrador["cabeceras"])
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["total"] == 2

    por_id = {i["variante_id"]: i for i in cuerpo["items"]}
    assert por_id[variantes[0]]["disponible"] == 10
    # El dinero viaja como cadena, nunca como float: un centavo perdido acá lo
    # encuentra el arqueo al cierre del turno.
    assert por_id[variantes[0]]["precio"] == str(PRECIO)
    assert por_id[variantes[0]]["sku"]


def test_una_prenda_agotada_no_se_ofrece(
    api: TestClient, mostrador: dict, cabeceras_admin: dict, variantes: list[int], sucursal: int
) -> None:
    """Sin stock no se puede vender; ofrecerla lleva a armar un ticket que falla."""
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variantes[0], 3)])
    cuerpo = api.get(PRENDAS, headers=mostrador["cabeceras"]).json()
    assert [i["variante_id"] for i in cuerpo["items"]] == [variantes[0]]


def test_la_busqueda_toma_el_sku_y_el_nombre(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    por_nombre = api.get(
        PRENDAS, headers=mostrador["cabeceras"], params={"busqueda": "Oxford"}
    ).json()
    assert por_nombre["total"] == 2

    sku = por_nombre["items"][0]["sku"]
    por_sku = api.get(
        PRENDAS, headers=mostrador["cabeceras"], params={"busqueda": sku}
    ).json()
    assert por_sku["total"] == 1

    vacia = api.get(
        PRENDAS, headers=mostrador["cabeceras"], params={"busqueda": "zapatos"}
    ).json()
    assert vacia["total"] == 0


def test_el_mostrador_solo_ve_su_sucursal(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    variantes: list[int],
    stock,
) -> None:
    """El ámbito sale del turno. Lo de la otra sucursal no existe."""
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _ingresar(api, cabeceras_admin, sucursal_id=otra, lineas=[(variantes[0], 50)])

    cuerpo = api.get(PRENDAS, headers=mostrador["cabeceras"]).json()
    assert {i["disponible"] for i in cuerpo["items"]} == {10, 4}


# =====================================================================
# Cobrar: el camino de la búsqueda libre
# =====================================================================

def test_una_venta_en_efectivo_nace_pagada_y_con_comprobante(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 2},
                {"variante_id": variantes[1], "cantidad": 1},
            ],
            "monto_recibido": "1000.00",
        },
    )
    assert r.status_code == 201, r.text
    venta = r.json()

    assert venta["estado"] == "PAGADA"
    assert venta["metodo_pago"] == "EFECTIVO"
    assert venta["codigo"].startswith("VP-")
    assert venta["total"] == "750.00"
    assert venta["vuelto"] == "250.00"
    assert venta["comprobante_numero"].startswith("R-")
    # Venta de mostrador: anónima y sin reserva detrás.
    assert venta["cliente"] is None
    assert venta["reserva_id"] is None
    assert len(venta["lineas"]) == 2


def test_la_venta_descuenta_el_inventario(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    antes = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
    api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "TARJETA",
            "lineas": [{"variante_id": variantes[0], "cantidad": 3}],
        },
    )
    despues = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
    assert despues == antes - 3


def test_la_venta_queda_colgada_del_turno_y_es_presencial(
    api: TestClient, db, mostrador: dict, variantes: list[int], stock
) -> None:
    """Sin esto el arqueo de CU-30 no encuentra la venta."""
    from app.modules.ventas.models import Venta

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert r.status_code == 201, r.text

    venta = db.query(Venta).filter(Venta.codigo == r.json()["codigo"]).one()
    assert venta.canal == "PRESENCIAL"
    assert venta.turno_caja_id == mostrador["turno_id"]
    assert venta.metodo_pago == "EFECTIVO"
    # Los CHECK del canal: en presencial no hay modalidad ni dirección.
    assert venta.modalidad_entrega is None
    assert venta.direccion_id is None


def test_el_precio_queda_congelado_aunque_cambie_despues(
    api: TestClient,
    db,
    mostrador: dict,
    variantes: list[int],
    stock,
) -> None:
    """Un comprobante impreso tiene que seguir coincidiendo con el sistema."""
    from app.modules.catalogo.models import VarianteProducto

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "QR",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    codigo = r.json()["codigo"]

    variante = db.get(VarianteProducto, variantes[0])
    variante.precio = Decimal("999.00")
    db.commit()

    vuelta = api.get(f"{VENTAS}/{codigo}", headers=mostrador["cabeceras"]).json()
    assert vuelta["lineas"][0]["precio_unitario"] == str(PRECIO)
    assert vuelta["total"] == str(PRECIO)


# =====================================================================
# El arqueo de CU-30 tiene que ver estas ventas
# =====================================================================

def test_el_efectivo_cobrado_sube_el_esperado_del_turno(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 2}],
        },
    )
    turno = api.get(CAJA_MIO, headers=mostrador["cabeceras"]).json()
    assert turno["efectivo_cobrado"] == "500.00"
    # apertura 100 + efectivo 500
    assert turno["monto_esperado"] == "600.00"


def test_tarjeta_y_qr_no_entran_al_cajon(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Sumarlos haría que todo turno con tarjeta apareciera descuadrado."""
    for metodo in ("TARJETA", "QR"):
        r = api.post(
            VENTAS,
            headers=mostrador["cabeceras"],
            json={
                "metodo_pago": metodo,
                "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            },
        )
        assert r.status_code == 201, r.text

    turno = api.get(CAJA_MIO, headers=mostrador["cabeceras"]).json()
    # Se compara el valor y no el texto: sin ninguna venta en efectivo la suma
    # llega sin escala («0») y con ventas llega con dos decimales («500.00»).
    # El formato es de quien dibuja; lo que este caso de uso promete es que
    # tarjeta y QR NO suman.
    assert Decimal(turno["efectivo_cobrado"]) == 0
    assert Decimal(turno["monto_esperado"]) == Decimal("100.00")
    # Pero el detalle por método sí las cuenta: el cajero tiene que poder
    # conciliar el voucher del POS contra el sistema.
    por_metodo = {l["metodo"]: l for l in turno["por_metodo"]}
    assert por_metodo["TARJETA"]["ventas"] == 1
    assert por_metodo["QR"]["total"] == str(PRECIO)


# =====================================================================
# Lo que el mostrador tiene que rechazar
# =====================================================================

def test_no_se_cobra_ni_sin_lineas_ni_con_las_dos_cosas(
    api: TestClient, mostrador: dict, variantes: list[int], stock, reserva_atendida: dict
) -> None:
    vacia = api.post(VENTAS, headers=mostrador["cabeceras"], json={"metodo_pago": "EFECTIVO"})
    assert vacia.status_code == 422

    ambas = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            "reserva_id": reserva_atendida["id"],
        },
    )
    assert ambas.status_code == 422


def test_la_misma_prenda_dos_veces_se_rechaza_con_motivo(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """`detalle_venta` tiene UNIQUE (venta_id, variante_id).

    Dejarlo llegar a la base daría un error de integridad que el cajero leería
    como «error del sistema» en vez de «use la cantidad».
    """
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 1},
                {"variante_id": variantes[0], "cantidad": 2},
            ],
        },
    )
    assert r.status_code == 422


def test_una_prenda_de_otra_sucursal_no_existe(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    variantes: list[int],
    stock,
) -> None:
    otra = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    ajenas = _crear_variantes_ajenas(api, cabeceras_admin)
    _ingresar(api, cabeceras_admin, sucursal_id=otra, lineas=[(ajenas[0], 5)])

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": ajenas[0], "cantidad": 1}],
        },
    )
    assert r.status_code == 404


def _crear_variantes_ajenas(api: TestClient, admin: dict) -> list[int]:
    categoria = api.post(
        CATEGORIAS, headers=admin, json={"nombre": "Pantalones", "orden": 1, "activa": True}
    )
    producto = api.post(
        PRODUCTOS,
        headers=admin,
        json={
            "codigo": "PAN-001",
            "nombre": "Pantalón recto",
            "categoria_id": categoria.json()["id"],
            "precio_base": "300.00",
            "activo": True,
        },
    )
    talla = api.post(
        TALLAS,
        headers=admin,
        json={"tipo_prenda": "Inferior", "codigo": "40", "orden": 0, "activa": True},
    )
    color = api.post(
        COLORES, headers=admin, json={"nombre": "Azul", "hexadecimal": "#1020A0", "activo": True}
    )
    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=admin,
        json={"tallas": [talla.json()["id"]], "colores": [color.json()["id"]]},
    )
    return [v["id"] for v in generadas.json()["variantes"]]


def test_sin_stock_no_queda_nada_a_medias(
    api: TestClient,
    db,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    """Se piden 5 de una prenda que tiene 4. Ni venta, ni comprobante, ni descuento."""
    from app.modules.ventas.models import Venta

    antes_otra = _disponible(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0]
    )
    cuantas_antes = db.query(Venta).count()

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [
                {"variante_id": variantes[0], "cantidad": 1},
                {"variante_id": variantes[1], "cantidad": 5},
            ],
        },
    )
    assert r.status_code == 409
    assert "quedan 4" in r.json()["detail"]

    assert db.query(Venta).count() == cuantas_antes
    # La primera línea alcanzó a descontarse antes de que reventara la segunda:
    # si la transacción no se deshiciera entera, esto quedaría en antes-1.
    assert (
        _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
        == antes_otra
    )


def test_si_el_precio_cambio_se_avisa_en_vez_de_cobrar_callado(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            "total_esperado": "200.00",
        },
    )
    assert r.status_code == 409
    assert "250.00" in r.json()["detail"]


def test_el_total_esperado_que_coincide_deja_pasar(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            "total_esperado": "250.00",
        },
    )
    assert r.status_code == 201, r.text


def test_no_se_cobra_con_menos_plata_de_la_que_vale(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            "monto_recibido": "100.00",
        },
    )
    assert r.status_code == 422


def test_con_tarjeta_no_hay_vuelto(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    """Dar vuelto por un cobro con tarjeta es sacar plata del cajón por nada."""
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "TARJETA",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
            "monto_recibido": "1000.00",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["vuelto"] is None


# =====================================================================
# El puente de D2: cobrar una reserva ya atendida
# =====================================================================

def test_la_reserva_atendida_aparece_por_cobrar_solo_con_lo_que_se_llevo(
    api: TestClient, mostrador: dict, reserva_atendida: dict, variantes: list[int]
) -> None:
    r = api.get(RESERVAS_POS, headers=mostrador["cabeceras"])
    assert r.status_code == 200, r.text
    filas = r.json()
    assert len(filas) == 1

    fila = filas[0]
    assert fila["reserva_id"] == reserva_atendida["id"]
    # La prenda que devolvió a la percha NO se cobra: mostrarla invitaría a
    # cobrarla.
    assert [l["variante_id"] for l in fila["lineas"]] == [variantes[0]]
    assert fila["total"] == "500.00"
    assert fila["cliente"]


def test_cobrar_la_reserva_deja_la_venta_atada_a_ella(
    api: TestClient, db, mostrador: dict, reserva_atendida: dict
) -> None:
    from app.modules.ventas.models import Venta

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={"metodo_pago": "EFECTIVO", "reserva_id": reserva_atendida["id"]},
    )
    assert r.status_code == 201, r.text
    venta = r.json()

    assert venta["reserva_id"] == reserva_atendida["id"]
    assert venta["total"] == "500.00"
    # Viniendo de una reserva la venta NO es anónima: hay un cliente con nombre.
    assert venta["cliente"]

    fila = db.query(Venta).filter(Venta.codigo == venta["codigo"]).one()
    assert fila.canal == "PRESENCIAL"
    assert fila.estado == "PAGADA"
    assert fila.turno_caja_id == mostrador["turno_id"]


def test_cobrar_una_reserva_no_vuelve_a_descontar(
    api: TestClient,
    mostrador: dict,
    cabeceras_admin: dict,
    sucursal: int,
    variantes: list[int],
    reserva_atendida: dict,
) -> None:
    """LA PRUEBA QUE SOSTIENE TODO EL CAMINO B.

    CU-24 ya escribió `LIBERACION +2` y `VENTA −2` al cerrar la reserva: las
    unidades salieron del inventario cuando el cliente se llevó la prenda del
    probador. Si CU-31 descontara otra vez al cobrar, las mismas dos unidades se
    contarían dos veces y el disponible quedaría mintiendo —sin que nada
    reventara, que es lo peor—.

    Si alguien borra el `if desde_reserva: return` de `_descontar` por
    parecerle de más, esta prueba es lo que lo detiene.
    """
    antes = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={"metodo_pago": "EFECTIVO", "reserva_id": reserva_atendida["id"]},
    )
    assert r.status_code == 201, r.text

    despues = _disponible(api, cabeceras_admin, sucursal_id=sucursal, variante_id=variantes[0])
    assert despues == antes, "cobrar la reserva descontó el stock por segunda vez"


def test_una_reserva_no_se_cobra_dos_veces(
    api: TestClient, mostrador: dict, reserva_atendida: dict
) -> None:
    """`venta.reserva_id` es UNIQUE, y el servicio lo dice antes de llegar ahí."""
    cuerpo = {"metodo_pago": "EFECTIVO", "reserva_id": reserva_atendida["id"]}
    assert api.post(VENTAS, headers=mostrador["cabeceras"], json=cuerpo).status_code == 201

    segunda = api.post(VENTAS, headers=mostrador["cabeceras"], json=cuerpo)
    assert segunda.status_code == 404

    # Y deja de ofrecerse.
    assert api.get(RESERVAS_POS, headers=mostrador["cabeceras"]).json() == []


def test_una_reserva_sin_atender_no_se_puede_cobrar(
    api: TestClient,
    mostrador: dict,
    cabeceras_cliente: dict,
    sucursal: int,
    variantes: list[int],
    stock,
) -> None:
    creada = api.post(
        RESERVAS,
        headers=cabeceras_cliente,
        json={
            "sucursal_id": sucursal,
            "franja_inicio": _manana(17).isoformat(),
            "franja_fin": _manana(18).isoformat(),
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    )
    assert creada.status_code == 201, creada.text

    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={"metodo_pago": "EFECTIVO", "reserva_id": creada.json()["id"]},
    )
    assert r.status_code == 404
    assert api.get(RESERVAS_POS, headers=mostrador["cabeceras"]).json() == []


def test_una_reserva_inexistente_da_404(api: TestClient, mostrador: dict) -> None:
    r = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={"metodo_pago": "EFECTIVO", "reserva_id": 987654},
    )
    assert r.status_code == 404


# =====================================================================
# Releer e imprimir
# =====================================================================

def test_la_venta_se_puede_releer_para_reimprimir(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    codigo = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    ).json()["codigo"]

    r = api.get(f"{VENTAS}/{codigo}", headers=mostrador["cabeceras"])
    assert r.status_code == 200, r.text
    assert r.json()["codigo"] == codigo
    assert r.json()["comprobante_numero"].startswith("R-")


def test_el_comprobante_sale_en_pdf(
    api: TestClient, mostrador: dict, variantes: list[int], stock
) -> None:
    codigo = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    ).json()["codigo"]

    r = api.get(f"{VENTAS}/{codigo}/comprobante", headers=mostrador["cabeceras"])
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    assert "inline" in r.headers["content-disposition"]


def test_una_venta_de_otra_sucursal_no_existe(
    api: TestClient,
    db,
    mostrador: dict,
    cabeceras_admin: dict,
    variantes: list[int],
    stock,
) -> None:
    """El cajero de Norte no ve el ticket de Centro. Convención 1: 404, no 403."""
    codigo = api.post(
        VENTAS,
        headers=mostrador["cabeceras"],
        json={
            "metodo_pago": "EFECTIVO",
            "lineas": [{"variante_id": variantes[0], "cantidad": 1}],
        },
    ).json()["codigo"]

    norte = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    otro = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=norte, sufijo="2")
    _abrir_turno(api, otro, _caja(db, norte, "Caja N1"))

    assert api.get(f"{VENTAS}/{codigo}", headers=otro).status_code == 404
    assert api.get(f"{VENTAS}/{codigo}/comprobante", headers=otro).status_code == 404


def test_una_reserva_de_otra_sucursal_no_se_cobra_aca(
    api: TestClient, db, mostrador: dict, cabeceras_admin: dict, reserva_atendida: dict
) -> None:
    norte = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    otro = _empleado(api, cabeceras_admin, cargo="CAJERO", sucursal_id=norte, sufijo="2")
    _abrir_turno(api, otro, _caja(db, norte, "Caja N1"))

    assert api.get(RESERVAS_POS, headers=otro).json() == []
    r = api.post(
        VENTAS,
        headers=otro,
        json={"metodo_pago": "EFECTIVO", "reserva_id": reserva_atendida["id"]},
    )
    assert r.status_code == 404
