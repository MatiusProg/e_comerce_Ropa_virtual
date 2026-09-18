"""CU-28 · Confirmar pago del pedido.

Realiza el **RF19** y cierra el criterio del Ciclo 3: catálogo → carrito →
pedido → **pago** → inventario descontado. Es el único camino por el que una
venta llega a `PAGADA`.

Lo que más importa cubrir
-------------------------
Este caso de uso tiene una sola idea difícil y tres formas de romperla:

- **La idempotencia es una restricción, no lógica.** El `UNIQUE` sobre
  `transaccion_pasarela.evento_id` es lo que impide que una notificación
  repetida descuente el inventario dos veces. Stripe reenvía hasta tres días si
  no recibe un 2xx, así que esto no es un caso de borde: pasa.
- **Los dos movimientos.** CU-27 apartó el stock, así que vender es
  `LIBERACION +n` seguido de `VENTA −n`. Un `VENTA −n` a secas descontaría por
  segunda vez unidades que ya habían salido del disponible.
- **La firma es lo único que protege el endpoint**, que no lleva token porque
  quien lo llama no tiene cuenta. Un cuerpo sin firma válida no puede mover
  nada — si pudiera, cualquiera daría por pagado su propio pedido.

Y la que ordena todo lo demás:

- **D5: el estado lo determina la pasarela.** Se comprueba que la ruta de
  simulación no sea un segundo camino a `PAGADA`, sino la misma puerta.
"""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.pasarela_pago.simulada import TIPO_APROBADO, TIPO_RECHAZADO

WEBHOOK = "/api/v1/pagos/webhook"
SIMULACION = "/api/v1/pagos/simulacion"
CONFIGURACION = "/api/v1/pagos/configuracion"

CARRITO = "/api/v1/tienda/carrito"
ITEMS = f"{CARRITO}/items"
PEDIDOS = "/api/v1/tienda/pedidos"

CATEGORIAS = "/api/v1/catalogo/categorias"
TALLAS = "/api/v1/catalogo/tallas"
COLORES = "/api/v1/catalogo/colores"
PRODUCTOS = "/api/v1/catalogo/productos"
CIUDADES = "/api/v1/organizacion/ciudades"
SUCURSALES = "/api/v1/organizacion/sucursales"
INGRESOS = "/api/v1/inventario/ingresos"
PROVEEDORES = "/api/v1/organizacion/proveedores"
EXISTENCIAS = "/api/v1/inventario/existencias"
MOVIMIENTOS = "/api/v1/inventario/movimientos"


# --- Armado del escenario -------------------------------------------------

def _sucursal(api: TestClient, admin: dict[str, str], nombre: str) -> int:
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


def _ingresar(api: TestClient, admin: dict[str, str], *, sucursal_id: int, lineas) -> None:
    creado = api.post(
        PROVEEDORES,
        headers=admin,
        json={
            "razon_social": "Sedas Andinas SRL",
            "identificacion_tributaria": "1098765432",
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
            "referencia": "REM-CU28",
            "lineas": [{"variante_id": v, "cantidad": c} for v, c in lineas],
        },
    )
    assert r.status_code == 201, r.text


@pytest.fixture
def tienda(api: TestClient, cabeceras_admin: dict[str, str]) -> dict:
    """Una sucursal con stock de una variante de precio conocido."""
    categoria = api.post(
        CATEGORIAS, headers=cabeceras_admin, json={"nombre": "Blusas", "orden": 0, "activa": True}
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
    producto = api.post(
        PRODUCTOS,
        headers=cabeceras_admin,
        json={
            "codigo": "BLU-001",
            "nombre": "Blusa de seda",
            "categoria_id": categoria,
            "precio_base": "250.00",
            "activo": True,
        },
    ).json()["id"]
    variante = api.post(
        f"{PRODUCTOS}/{producto}/variantes",
        headers=cabeceras_admin,
        json={"talla_id": talla, "color_id": color, "precio": "250.00", "activa": True},
    ).json()["id"]

    sucursal = _sucursal(api, cabeceras_admin, "Centro")
    _ingresar(api, cabeceras_admin, sucursal_id=sucursal, lineas=[(variante, 10)])
    return {"variante": variante, "sucursal": sucursal, "precio": "250.00"}


@pytest.fixture
def pedido(
    api: TestClient, cabeceras_cliente: dict[str, str], tienda: dict
) -> dict:
    """Un pedido de 2 unidades, esperando pago, con su sesión de pasarela."""
    agregado = api.post(
        ITEMS,
        headers=cabeceras_cliente,
        json={"variante_id": tienda["variante"], "cantidad": 2},
    )
    assert agregado.status_code in (200, 201), agregado.text

    r = api.post(
        PEDIDOS,
        headers=cabeceras_cliente,
        json={
            "modalidad_entrega": "RETIRO",
            "sucursal_id": tienda["sucursal"],
            "total_esperado": "500.00",
        },
    )
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    return {
        **tienda,
        "codigo": cuerpo["pedido"]["codigo"],
        # La sesión viaja dentro de la URL de pago del proveedor simulado.
        "sesion": cuerpo["url_pago"].split("sesion=")[1].split("&")[0],
    }


def _saldos(api: TestClient, admin: dict[str, str], variante_id: int, sucursal_id: int):
    filas = api.get(EXISTENCIAS, headers=admin, params={"sucursal_id": sucursal_id}).json()["items"]
    for fila in filas:
        if fila["variante_id"] == variante_id:
            return fila["cantidad_disponible"], fila["cantidad_reservada"]
    return 0, 0


def _firmar(cuerpo: bytes) -> str | None:
    secreto = settings.PAGO_WEBHOOK_SECRET.strip()
    if not secreto:
        return None
    return hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()


def _evento(*, sesion: str, pedido_codigo: str | None = None, aprobado: bool = True,
            id_evento: str = "ev_prueba_1") -> tuple[bytes, dict[str, str]]:
    cuerpo = json.dumps(
        {
            "id_evento": id_evento,
            "tipo": TIPO_APROBADO if aprobado else TIPO_RECHAZADO,
            "sesion": sesion,
            "pedido": pedido_codigo,
        },
        separators=(",", ":"),
    ).encode()
    firma = _firmar(cuerpo)
    cabeceras = {"Content-Type": "application/json"}
    if firma:
        cabeceras["X-Firma-Simulada"] = firma
    return cuerpo, cabeceras


def _estado(api: TestClient, cab: dict[str, str], codigo: str) -> str:
    return api.get(f"{PEDIDOS}/{codigo}", headers=cab).json()["estado"]


# =====================================================================
# El endpoint y su acceso
# =====================================================================

def test_el_webhook_no_pide_token(api: TestClient, pedido: dict) -> None:
    """Quien lo llama es la pasarela, que no tiene cuenta en el sistema.

    Lo que lo protege es la firma, no un token: un token compartido no prueba
    nada sobre el contenido del mensaje, mientras que la firma cubre los bytes
    exactos que viajaron.
    """
    cuerpo, cabeceras = _evento(sesion=pedido["sesion"])
    respuesta = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert respuesta.status_code == 200, respuesta.text


def test_la_configuracion_no_devuelve_secretos(api: TestClient) -> None:
    cuerpo = api.get(CONFIGURACION).json()

    assert cuerpo["proveedor"]
    assert "cobra_de_verdad" in cuerpo
    texto = json.dumps(cuerpo)
    assert "sk_" not in texto
    assert "whsec_" not in texto


# =====================================================================
# El camino feliz: el pago mueve la venta y el inventario
# =====================================================================

def test_el_pago_confirmado_deja_la_venta_pagada(
    api: TestClient, cabeceras_cliente: dict[str, str], pedido: dict
) -> None:
    assert _estado(api, cabeceras_cliente, pedido["codigo"]) == "PENDIENTE_PAGO"

    cuerpo, cabeceras = _evento(sesion=pedido["sesion"], pedido_codigo=pedido["codigo"])
    respuesta = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultado"] == "aplicado"
    assert _estado(api, cabeceras_cliente, pedido["codigo"]) == "PAGADA"


def test_el_pago_descuenta_de_lo_apartado_y_no_del_disponible(
    api: TestClient, cabeceras_admin: dict[str, str], pedido: dict
) -> None:
    """Los dos movimientos: `LIBERACION +n` y después `VENTA −n`.

    CU-27 apartó las 2 unidades, así que quedaron 8 disponibles y 2 reservadas.
    Al pagar, las 2 reservadas se van: **8 y 0**, no 6 y 0.

    Si se escribiera un `VENTA −n` a secas, esas unidades se descontarían por
    segunda vez —ya habían salido del disponible al apartarse— y el saldo
    quedaría en 6, que es mercadería que la tienda cree no tener.
    """
    antes = _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"])
    assert antes == (8, 2)

    cuerpo, cabeceras = _evento(sesion=pedido["sesion"])
    api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"]) == (8, 0)


def test_el_pago_deja_los_dos_movimientos_en_el_historial(
    api: TestClient, cabeceras_admin: dict[str, str], pedido: dict
) -> None:
    """El historial tiene que leerse como lo que pasó, no como el neto.

    «Volvieron del apartado y se vendieron» son dos hechos, y el invariante del
    paquete —`disponible == suma(movimientos)`— sólo se sostiene con los dos.
    """
    cuerpo, cabeceras = _evento(sesion=pedido["sesion"])
    api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    movimientos = api.get(
        MOVIMIENTOS,
        headers=cabeceras_admin,
        params={"variante_id": pedido["variante"], "tamano": 50},
    ).json()["items"]
    tipos = [m["tipo"] for m in movimientos]

    assert "VENTA" in tipos
    assert "LIBERACION" in tipos


def test_el_pago_vacia_el_carrito(
    api: TestClient, cabeceras_cliente: dict[str, str], pedido: dict
) -> None:
    """Se vacía acá y no al confirmar el pedido.

    Es la decisión de CU-27: si se vaciara antes, un pago que nunca llega
    dejaría al cliente sin carrito y sin compra, y tendría que rearmarlo entero
    para reintentar. Se vacía cuando el dinero entró.
    """
    assert api.get(CARRITO, headers=cabeceras_cliente).json()["items"] == 1

    cuerpo, cabeceras = _evento(sesion=pedido["sesion"])
    api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert api.get(CARRITO, headers=cabeceras_cliente).json()["items"] == 0


# =====================================================================
# La idempotencia, que es de lo que se trata este caso de uso
# =====================================================================

def test_la_misma_notificacion_dos_veces_no_descuenta_dos_veces(
    api: TestClient, cabeceras_admin: dict[str, str], pedido: dict
) -> None:
    """**La prueba que justifica el UNIQUE de `evento_id`.**

    Stripe reenvía hasta tres días si no recibe un 2xx, así que la segunda
    entrega del mismo evento no es hipotética. Sin la restricción, el segundo
    intento volvería a mover el inventario y el saldo quedaría mal.
    """
    cuerpo, cabeceras = _evento(sesion=pedido["sesion"], id_evento="ev_repetido")

    primera = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)
    segunda = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert primera.json()["resultado"] == "aplicado"
    assert segunda.status_code == 200, "un repetido NO es un error: reintentar no lo arregla"
    assert segunda.json()["resultado"] == "repetido"
    assert _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"]) == (8, 0)


def test_dos_eventos_distintos_del_mismo_cobro_tampoco_aplican_dos_veces(
    api: TestClient, cabeceras_admin: dict[str, str], pedido: dict
) -> None:
    """La segunda red, para lo que el `UNIQUE` no puede atrapar.

    Dos notificaciones **con identificadores distintos** sobre el mismo cobro
    pasan la restricción sin chocar. Lo que las frena es comprobar que el pago
    ya estaba aprobado antes de volver a mover nada.
    """
    uno, cab_uno = _evento(sesion=pedido["sesion"], id_evento="ev_a")
    dos, cab_dos = _evento(sesion=pedido["sesion"], id_evento="ev_b")

    api.post(WEBHOOK, content=uno, headers=cab_uno)
    segunda = api.post(WEBHOOK, content=dos, headers=cab_dos)

    assert segunda.json()["resultado"] == "repetido"
    assert _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"]) == (8, 0)


# =====================================================================
# Lo que NO tiene que mover nada
# =====================================================================

def test_un_rechazo_no_deja_la_venta_pagada_ni_toca_el_stock(
    api: TestClient,
    cabeceras_admin: dict[str, str],
    cabeceras_cliente: dict[str, str],
    pedido: dict,
) -> None:
    """El stock sigue apartado: el pedido no fracasó todavía, sólo no se pagó.

    Devolverlo acá sería adelantarse: quien lo devuelve es la cancelación o la
    barrida de vencidos, que son las que saben que ya no hay esperanza.
    """
    cuerpo, cabeceras = _evento(sesion=pedido["sesion"], aprobado=False)
    respuesta = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert respuesta.json()["resultado"] == "rechazado"
    assert _estado(api, cabeceras_cliente, pedido["codigo"]) == "PENDIENTE_PAGO"
    assert _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"]) == (8, 2)


def test_un_evento_de_una_sesion_desconocida_se_registra_y_no_mueve_nada(
    api: TestClient, cabeceras_admin: dict[str, str], pedido: dict
) -> None:
    """200, no error: reintentar no va a hacer que la sesión exista."""
    cuerpo, cabeceras = _evento(sesion="sim_que_no_existe", id_evento="ev_huerfano")
    respuesta = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert respuesta.status_code == 200
    assert respuesta.json()["resultado"] == "sin_pago"
    assert _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"]) == (8, 2)


def test_un_evento_de_otro_tipo_se_registra_y_no_mueve_nada(
    api: TestClient, cabeceras_cliente: dict[str, str], pedido: dict
) -> None:
    """Una cuenta de pasarela emite decenas de tipos que no interesan.

    Se registran igual —el registro es de todo lo que la pasarela dijo— y no se
    los confunde con un rechazo.
    """
    cuerpo = json.dumps(
        {
            "id_evento": "ev_otro_tipo",
            "tipo": "cliente.actualizado",
            "sesion": pedido["sesion"],
            "pedido": None,
        },
        separators=(",", ":"),
    ).encode()
    cabeceras = {"Content-Type": "application/json"}
    firma = _firmar(cuerpo)
    if firma:
        cabeceras["X-Firma-Simulada"] = firma

    respuesta = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert respuesta.json()["resultado"] == "ignorado"
    assert _estado(api, cabeceras_cliente, pedido["codigo"]) == "PENDIENTE_PAGO"


def test_un_cuerpo_sin_identificador_de_evento_se_rechaza(
    api: TestClient, pedido: dict
) -> None:
    """Sin `id_evento` no hay idempotencia posible: dos entregas se aplicarían
    las dos."""
    cuerpo = json.dumps({"tipo": TIPO_APROBADO, "sesion": pedido["sesion"]}).encode()
    cabeceras = {"Content-Type": "application/json"}
    firma = _firmar(cuerpo)
    if firma:
        cabeceras["X-Firma-Simulada"] = firma

    respuesta = api.post(WEBHOOK, content=cuerpo, headers=cabeceras)

    assert respuesta.status_code == 400


def test_un_cuerpo_que_no_es_json_se_rechaza(api: TestClient) -> None:
    cuerpo = b"esto no es json"
    cabeceras = {"Content-Type": "application/json"}
    firma = _firmar(cuerpo)
    if firma:
        cabeceras["X-Firma-Simulada"] = firma

    assert api.post(WEBHOOK, content=cuerpo, headers=cabeceras).status_code == 400


# =====================================================================
# La ruta de simulación: la misma puerta, no una segunda
# =====================================================================

def test_la_simulacion_confirma_el_pago_por_el_mismo_camino(
    api: TestClient, cabeceras_cliente: dict[str, str], pedido: dict
) -> None:
    """**Es lo que mantiene honesta la demostración.**

    Si esta ruta aplicara el pago por su cuenta, lo que se enseña en la defensa
    sería un flujo distinto del real. Fabrica el mismo cuerpo, lo firma con el
    mismo secreto y lo entrega a la misma función.
    """
    respuesta = api.post(
        SIMULACION,
        json={"sesion": pedido["sesion"], "pedido": pedido["codigo"], "aprobado": True},
    )

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["resultado"] == "aplicado"
    assert _estado(api, cabeceras_cliente, pedido["codigo"]) == "PAGADA"


def test_la_simulacion_tambien_sabe_rechazar(
    api: TestClient, cabeceras_cliente: dict[str, str], pedido: dict
) -> None:
    """Demostrar el rechazo importa tanto como demostrar el cobro: deja ver que
    el pedido NO pasa a pagado."""
    respuesta = api.post(
        SIMULACION,
        json={"sesion": pedido["sesion"], "pedido": pedido["codigo"], "aprobado": False},
    )

    assert respuesta.json()["resultado"] == "rechazado"
    assert _estado(api, cabeceras_cliente, pedido["codigo"]) == "PENDIENTE_PAGO"


def test_dos_simulaciones_seguidas_no_aplican_dos_veces(
    api: TestClient, cabeceras_admin: dict[str, str], pedido: dict
) -> None:
    """Cada simulación fabrica un `id_evento` distinto, así que el `UNIQUE` no
    las frena: lo que las frena es que el pago ya esté aprobado."""
    cuerpo = {"sesion": pedido["sesion"], "pedido": pedido["codigo"], "aprobado": True}

    api.post(SIMULACION, json=cuerpo)
    segunda = api.post(SIMULACION, json=cuerpo)

    assert segunda.json()["resultado"] == "repetido"
    assert _saldos(api, cabeceras_admin, pedido["variante"], pedido["sucursal"]) == (8, 0)
