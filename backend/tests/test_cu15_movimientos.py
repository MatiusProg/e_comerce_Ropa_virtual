"""CU-15 · Registrar movimiento de inventario.

Cubre el flujo principal (ajuste por conteo físico), el flujo alternativo 3a
(transferencia entre sucursales) y las excepciones de la ficha
(docs/entregas/ciclo-2/cu-15-registrar-movimiento-de-inventario.md).

Las pruebas que más importan son las que cubren lo que la base **no** garantiza
por sí sola:

- **El conteo se compara contra el total físico, no contra el disponible.** Una
  prenda apartada para una reserva sigue estando en la percha. Comparar contra
  el disponible haría que cada reserva viva pareciera un faltante y el ajuste
  «corregiría» un descuadre inexistente, robándole las unidades a la reserva.
- **Una transferencia son dos filas.** Es lo que permite reconstruir el saldo de
  cada sucursal mirando solo sus propios movimientos (D4).
- **Ningún saldo se toca sin dejar movimiento.** Es la regla que concentra P4, y
  acá se verifica sobre las dos operaciones.
- **La transferencia es solo del Administrador.** El ajuste NO: esa mitad es
  CU-16 y la hace el Encargado sobre su propia sucursal.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.modules.inventario.models import Existencia

AJUSTE = "/api/v1/inventario/movimientos/ajuste"
TRANSFERENCIA = "/api/v1/inventario/movimientos/transferencia"
MOVIMIENTOS = "/api/v1/inventario/movimientos"
EXISTENCIAS = "/api/v1/inventario/existencias"
TIPOS = "/api/v1/inventario/tipos-movimiento"
INGRESOS = "/api/v1/inventario/ingresos"

SUCURSALES = "/api/v1/organizacion/sucursales"
CIUDADES = "/api/v1/organizacion/ciudades"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EMPLEADOS = "/api/v1/organizacion/empleados"
PRODUCTOS = "/api/v1/catalogo/productos"
CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"

MOTIVO = "Conteo físico de cierre de mes"


# --- Ayudantes -----------------------------------------------------------

def _crear_sucursal(
    api: TestClient, admin: dict[str, str], *, nombre: str, activa: bool = True
) -> int:
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
            "activa": activa,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _variante(api: TestClient, admin: dict[str, str]) -> int:
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
            "precio_base": "250.00",
            "activo": True,
        },
    )
    talla = api.post(
        TALLAS,
        headers=admin,
        json={"tipo_prenda": "Superior", "codigo": "M", "orden": 1, "activa": True},
    )
    color = api.post(
        COLORES,
        headers=admin,
        json={"nombre": "Negro", "hexadecimal": "#101010", "activo": True},
    )
    generadas = api.post(
        f"{PRODUCTOS}/{producto.json()['id']}/variantes/generar",
        headers=admin,
        json={"tallas": [talla.json()["id"]], "colores": [color.json()["id"]]},
    )
    assert generadas.status_code == 201, generadas.text
    return generadas.json()["variantes"][0]["id"]


def _sembrar_stock(
    api: TestClient,
    admin: dict[str, str],
    *,
    sucursal_id: int,
    variante_id: int,
    cantidad: int,
) -> None:
    """Deja stock por la puerta de CU-13, que es la única que hay.

    No se escribe la existencia a mano a propósito: si el ingreso deja de
    funcionar, estas pruebas tienen que enterarse.
    """
    proveedor = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Textiles del Sur SRL",
            "identificacion_tributaria": "1023456789",
            "activo": True,
        },
    )
    if proveedor.status_code == 409:  # ya existía, de una llamada anterior
        proveedor_id = api.get(PROVEEDORES, headers=admin).json()[0]["id"]
    else:
        assert proveedor.status_code == 201, proveedor.text
        proveedor_id = proveedor.json()["id"]

    r = api.post(
        INGRESOS,
        headers=admin,
        json={
            "sucursal_id": sucursal_id,
            "proveedor_id": proveedor_id,
            "referencia": "REM-SEED",
            "lineas": [{"variante_id": variante_id, "cantidad": cantidad}],
        },
    )
    assert r.status_code == 201, r.text


def _saldo(api: TestClient, admin: dict[str, str], *, sucursal_id: int) -> dict:
    filas = api.get(
        EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}
    ).json()
    return filas[0] if filas else {}


# --- Fixtures ------------------------------------------------------------

@pytest.fixture
def sucursal(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _crear_sucursal(api, cabeceras_admin, nombre="Centro")


@pytest.fixture
def variante(api: TestClient, cabeceras_admin: dict[str, str]) -> int:
    return _variante(api, cabeceras_admin)


@pytest.fixture
def cabeceras_encargado(api: TestClient, cabeceras_admin: dict[str, str], sucursal: int):
    correo = "encargado.centro@violetboutique.bo"
    clave = "Encargado12"
    alta = api.post(
        EMPLEADOS,
        headers=cabeceras_admin,
        json={
            "nombres": "Luz",
            "apellidos": "Vargas",
            "correo": correo,
            "contrasena": clave,
            "documento": "5544332",
            "telefono": "70000000",
            "cargo": "ENCARGADO",
            "sucursal_id": sucursal,
            "fecha_ingreso": (date.today() - timedelta(days=30)).isoformat(),
        },
    )
    assert alta.status_code == 201, alta.text
    entrada = api.post(
        "/api/v1/auth/login", json={"correo": correo, "contrasena": clave}
    )
    return {"Authorization": f"Bearer {entrada.json()['access_token']}"}


# --- Autorizacion --------------------------------------------------------

def test_sin_token_no_se_ajusta_el_inventario(api: TestClient) -> None:
    assert api.post(AJUSTE, json={}).status_code == 401


def test_el_encargado_no_transfiere_entre_sucursales(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_encargado: dict[str, str],
    sucursal: int,
    variante: int,
) -> None:
    """La transferencia es solo del Administrador, y el ajuste no.

    El 10/09 esta prueba decía que el Encargado tampoco ajustaba, leyendo solo
    la fila de CU-15 del documento de organización. Estaba incompleta: **CU-16
    es ese mismo ajuste visto desde el Encargado**, acotado a su sucursal — y
    es justamente por eso que CU-15 figura como de Administrador.

    Lo que sigue siendo solo del Administrador es la transferencia, porque cruza
    dos sucursales y el Encargado responde por una sola.
    """
    destino = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )

    transferencia = api.post(
        TRANSFERENCIA,
        headers=cabeceras_encargado,
        json={
            "variante_id": variante,
            "sucursal_origen_id": sucursal,
            "sucursal_destino_id": destino,
            "cantidad": 2,
            "motivo": "Reposición para la vitrina del norte",
        },
    )
    assert transferencia.status_code == 403

    # El historial sí lo ve: es la trazabilidad de su propia sucursal.
    assert api.get(MOVIMIENTOS, headers=cabeceras_encargado).status_code == 200


# --- Ajuste por conteo fisico --------------------------------------------

def test_el_ajuste_hacia_arriba_deja_un_movimiento_positivo(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )

    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 13,
            "motivo": "Aparecieron 3 en el depósito",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["diferencia"] == 3
    assert cuerpo["movimiento"]["tipo"] == "AJUSTE"
    assert cuerpo["movimiento"]["cantidad"] == 3
    assert cuerpo["movimiento"]["motivo"] == "Aparecieron 3 en el depósito"
    assert cuerpo["existencia"]["cantidad_disponible"] == 13


def test_el_ajuste_hacia_abajo_deja_un_movimiento_negativo(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """El signo va en la cantidad y no se deduce del tipo: un AJUSTE va en las
    dos direcciones."""
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )

    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 7,
            "motivo": MOTIVO,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["diferencia"] == -3
    assert respuesta.json()["movimiento"]["cantidad"] == -3
    assert respuesta.json()["existencia"]["cantidad_disponible"] == 7


def test_el_conteo_se_compara_contra_el_total_fisico_no_contra_el_disponible(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    db,
    sucursal: int,
    variante: int,
) -> None:
    """La prueba más importante de este caso de uso.

    Con 10 unidades, 4 de ellas apartadas para reservas, el disponible es 6 y el
    total físico sigue siendo 10. Quien recorre la percha cuenta 10, porque las
    reservadas están ahí. Si el ajuste comparara contra el disponible, vería un
    sobrante de 4 y subiría el saldo a 14 —inventando cuatro prendas—.

    Comparando contra el total físico, un conteo de 10 no genera movimiento
    ninguno, que es lo correcto.
    """
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )

    # CU-22 todavía no existe, así que las reservas se simulan sobre la fila.
    existencia = db.scalar(
        select(Existencia).where(
            Existencia.variante_id == variante, Existencia.sucursal_id == sucursal
        )
    )
    existencia.cantidad_disponible = 6
    existencia.cantidad_reservada = 4
    db.commit()

    coincide = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 10,
            "motivo": MOTIVO,
        },
    )
    assert coincide.status_code == 409, coincide.text
    assert "coincide" in coincide.json()["detail"]

    # Y un faltante real de una unidad se descuenta del disponible, no de lo
    # reservado: lo reservado lo mueven CU-22, CU-23 y CU-25.
    faltante = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 9,
            "motivo": MOTIVO,
        },
    )
    assert faltante.status_code == 201, faltante.text
    assert faltante.json()["existencia"]["cantidad_disponible"] == 5
    assert faltante.json()["existencia"]["cantidad_reservada"] == 4


def test_excepcion_e8_el_conteo_no_puede_ser_menor_que_lo_reservado(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    db,
    sucursal: int,
    variante: int,
) -> None:
    """Si hay 4 apartadas y el conteo dice 3, una reserva se quedaría sin
    respaldo físico. Se frena: primero se cancela la reserva (CU-23)."""
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )
    existencia = db.scalar(
        select(Existencia).where(
            Existencia.variante_id == variante, Existencia.sucursal_id == sucursal
        )
    )
    existencia.cantidad_disponible = 6
    existencia.cantidad_reservada = 4
    db.commit()

    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 3,
            "motivo": MOTIVO,
        },
    )
    assert respuesta.status_code == 409
    assert "reservas" in respuesta.json()["detail"]

    # Y no tocó nada.
    saldo = _saldo(api, cabeceras_admin, sucursal_id=sucursal)
    assert saldo["cantidad_disponible"] == 6
    assert saldo["cantidad_reservada"] == 4


def test_excepcion_e7_un_conteo_sin_diferencia_no_genera_movimiento(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """No es un fallo, pero tampoco es un movimiento: el CHECK
    `ck_movimiento_inventario_cantidad_no_nula` rechaza una cantidad cero, y una
    fila de cero unidades solo llenaría el historial de ruido."""
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=8
    )
    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 8,
            "motivo": MOTIVO,
        },
    )
    assert respuesta.status_code == 409

    ajustes = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "AJUSTE"}
    ).json()
    assert ajustes["total"] == 0


def test_el_motivo_del_ajuste_es_obligatorio_y_legible(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """El RF28 pide trazabilidad del motivo; «ok» la cumple en la forma y no en
    el fondo."""
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=8
    )
    for motivo in ("", "ok"):
        respuesta = api.post(
            AJUSTE,
            headers=cabeceras_admin,
            json={
                "variante_id": variante,
                "sucursal_id": sucursal,
                "cantidad_contada": 5,
                "motivo": motivo,
            },
        )
        assert respuesta.status_code == 422, f"el motivo «{motivo}» fue aceptado"


def test_un_conteo_sobre_una_prenda_que_nunca_estuvo_crea_su_saldo(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """Apareció mercadería que el sistema no tenía registrada.

    Es un caso legítimo del conteo físico y no un error: se crea la existencia
    en cero y el ajuste la sube, de modo que D4 se cumple también para la
    primera unidad.
    """
    respuesta = api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 4,
            "motivo": "Cajas sin remito encontradas en el depósito",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["diferencia"] == 4
    assert respuesta.json()["existencia"]["cantidad_disponible"] == 4


# --- Transferencia entre sucursales --------------------------------------

def test_la_transferencia_deja_dos_movimientos_y_mueve_los_dos_saldos(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """Flujo alternativo 3a.

    Son dos filas y no una: es lo que permite reconstruir el saldo de cada
    sucursal mirando solo sus propios movimientos (D4).
    """
    destino = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )

    respuesta = api.post(
        TRANSFERENCIA,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_origen_id": sucursal,
            "sucursal_destino_id": destino,
            "cantidad": 4,
            "motivo": "Reposición para la vitrina del norte",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()

    assert cuerpo["salida"]["cantidad"] == -4
    assert cuerpo["entrada"]["cantidad"] == 4
    assert cuerpo["salida"]["tipo"] == cuerpo["entrada"]["tipo"] == "TRANSFERENCIA"
    # Las dos puntas comparten el motivo: es lo que las emparenta.
    assert cuerpo["salida"]["motivo"] == cuerpo["entrada"]["motivo"]
    assert "Centro" in cuerpo["salida"]["motivo"] and "Norte" in cuerpo["salida"]["motivo"]

    assert cuerpo["origen"]["cantidad_disponible"] == 6
    assert cuerpo["destino"]["cantidad_disponible"] == 4

    # Y cada sucursal reconstruye su saldo con sus propias filas.
    del_norte = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"sucursal_id": destino}
    ).json()
    assert sum(m["cantidad"] for m in del_norte["items"]) == 4


def test_excepcion_e6_no_se_transfiere_mas_de_lo_disponible(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    destino = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=3
    )

    respuesta = api.post(
        TRANSFERENCIA,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_origen_id": sucursal,
            "sucursal_destino_id": destino,
            "cantidad": 5,
            "motivo": "Reposición para la vitrina del norte",
        },
    )
    assert respuesta.status_code == 409
    assert "3" in respuesta.json()["detail"]

    # No se movió nada, ni siquiera se creó el saldo del destino.
    assert _saldo(api, cabeceras_admin, sucursal_id=sucursal)["cantidad_disponible"] == 3
    assert api.get(
        EXISTENCIAS, headers=cabeceras_admin, params={"sucursal_id": destino}
    ).json() == []


def test_excepcion_e5_no_se_transfiere_una_sucursal_a_si_misma(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=5
    )
    respuesta = api.post(
        TRANSFERENCIA,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_origen_id": sucursal,
            "sucursal_destino_id": sucursal,
            "cantidad": 2,
            "motivo": "Movimiento interno de prueba",
        },
    )
    assert respuesta.status_code == 422


def test_no_se_transfiere_una_prenda_que_nunca_estuvo_en_el_origen(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """No es lo mismo que un stock insuficiente, y el mensaje tiene que
    distinguirlo: una es «no alcanzan», la otra «nunca estuvo acá»."""
    destino = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    respuesta = api.post(
        TRANSFERENCIA,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_origen_id": sucursal,
            "sucursal_destino_id": destino,
            "cantidad": 1,
            "motivo": "Reposición para la vitrina del norte",
        },
    )
    assert respuesta.status_code == 404


# --- Historial -----------------------------------------------------------

def test_el_historial_filtra_por_tipo_y_por_sucursal(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    destino = _crear_sucursal(api, cabeceras_admin, nombre="Norte")
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )
    api.post(
        AJUSTE,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_id": sucursal,
            "cantidad_contada": 9,
            "motivo": MOTIVO,
        },
    )
    api.post(
        TRANSFERENCIA,
        headers=cabeceras_admin,
        json={
            "variante_id": variante,
            "sucursal_origen_id": sucursal,
            "sucursal_destino_id": destino,
            "cantidad": 2,
            "motivo": "Reposición para la vitrina del norte",
        },
    )

    todos = api.get(MOVIMIENTOS, headers=cabeceras_admin).json()
    # 1 ingreso + 1 ajuste + 2 puntas de la transferencia.
    assert todos["total"] == 4

    transferencias = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"tipo": "TRANSFERENCIA"}
    ).json()
    assert transferencias["total"] == 2

    del_norte = api.get(
        MOVIMIENTOS, headers=cabeceras_admin, params={"sucursal_id": destino}
    ).json()
    assert del_norte["total"] == 1
    assert del_norte["items"][0]["sucursal"] == "Norte"


def test_el_historial_nombra_la_prenda_y_a_quien_la_movio(
    api: TestClient, cabeceras_admin: dict[str, str], sucursal: int, variante: int
) -> None:
    """«Variante 412» no le dice nada a nadie: el historial tiene que ser
    legible seis meses después."""
    _sembrar_stock(
        api, cabeceras_admin, sucursal_id=sucursal, variante_id=variante, cantidad=10
    )
    fila = api.get(MOVIMIENTOS, headers=cabeceras_admin).json()["items"][0]

    assert fila["producto"] == "Camisa Oxford manga larga"
    assert fila["talla"] == "M"
    assert fila["color"] == "Negro"
    assert fila["sucursal"] == "Centro"
    assert fila["usuario"] == "Root Pruebas"
    assert fila["proveedor"] == "Textiles del Sur SRL"


def test_los_tipos_manuales_son_solo_tres(
    api: TestClient, cabeceras_admin: dict[str, str]
) -> None:
    """RESERVA, LIBERACION, VENTA y DEVOLUCION las genera el sistema.

    Ofrecerlas en el selector dejaría descuadrar un saldo contra la reserva o la
    venta que lo justifica.
    """
    respuesta = api.get(TIPOS, headers=cabeceras_admin)
    assert respuesta.status_code == 200
    assert respuesta.json() == ["INGRESO", "TRANSFERENCIA", "AJUSTE"]
