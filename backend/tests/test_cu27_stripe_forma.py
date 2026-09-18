"""La forma de la llamada a Stripe, sin llamar a Stripe.

POR QUE EXISTE ESTE ARCHIVO
---------------------------
El proveedor de Stripe **no tenia ni una prueba**, y eso dejo llegar a
produccion un defecto que el cliente vio como «pérdida de comunicación con la
pasarela de pago»: la clave de idempotencia viajaba dentro de `params` en vez de
en `options`, y Stripe rechazaba la peticion entera con

    Received unknown parameter: idempotency_key

El mensaje del sistema era honesto y enganoso a la vez --- Stripe contestaba
perfecto; lo que estaba mal era lo que le mandabamos ---. Lo encontro una
persona probando la web, no la suite.

COMO SE PRUEBA SIN SALIR A INTERNET
------------------------------------
Se sustituye el cliente del SDK por un doble que **solo anota como lo llamaron**.
No hay red, no hace falta clave, y la prueba corre en milisegundos.

Lo que se fija no es que Stripe responda ---eso es de Stripe--- sino **el
contrato de la llamada**: que cada cosa vaya donde el SDK la espera. Es
exactamente el tipo de defecto que una prueba de integracion no atraparia
tampoco, porque exigiria una cuenta real.

`conftest.py` impone `PAGO_PROVEEDOR=simulada` para toda la suite, asi que el
proveedor de Stripe se construye aqui a mano, a proposito.
"""

from decimal import Decimal

import pytest

from app.integrations.pasarela_pago.base import LineaDePago, SolicitudDePago
from app.integrations.pasarela_pago.stripe_hospedado import (
    ProveedorStripe,
    a_unidad_minima,
)


class _SesionesFalsas:
    """Anota como la llamaron y devuelve una sesion de mentira."""

    def __init__(self) -> None:
        self.params: dict | None = None
        self.options: dict | None = None

    def create(self, params=None, options=None):
        self.params = params
        self.options = options
        return type("Sesion", (), {"id": "cs_test_falsa", "url": "https://pasarela.test/x"})()


class _ClienteFalso:
    def __init__(self) -> None:
        self.sesiones = _SesionesFalsas()
        self.v1 = type("V1", (), {"checkout": type("C", (), {"sessions": self.sesiones})()})()


@pytest.fixture
def proveedor(monkeypatch) -> ProveedorStripe:
    """Un ProveedorStripe con el SDK sustituido por el doble."""
    from app.core import config

    monkeypatch.setattr(config.settings, "PAGO_API_KEY", "sk_test_de_mentira", raising=False)
    p = ProveedorStripe()
    p._cliente = _ClienteFalso()
    return p


def _solicitud() -> SolicitudDePago:
    return SolicitudDePago(
        referencia="VB-20260918-ABC123",
        lineas=[
            LineaDePago(descripcion="Blusa de seda", cantidad=2, precio_unitario=Decimal("250.00"))
        ],
        moneda="usd",
        url_exito="https://web.test/pago/exito",
        url_cancelado="https://web.test/pago/cancelado",
        correo_cliente="cliente@ejemplo.test",
        metadatos={"venta_id": "7", "codigo": "VB-20260918-ABC123"},
    )


def test_la_clave_de_idempotencia_va_en_options_y_no_en_params(
    proveedor: ProveedorStripe,
) -> None:
    """**La prueba que faltaba.**

    `params` es el cuerpo de la peticion, y Stripe rechaza los parametros que no
    conoce. Con la clave ahi adentro fallaba TODA la llamada, no solo la
    idempotencia.
    """
    proveedor.crear_sesion(_solicitud())
    sesiones = proveedor._cliente.sesiones

    assert "idempotency_key" not in sesiones.params, (
        "la clave de idempotencia en `params` hace que Stripe rechace la peticion "
        "entera con «Received unknown parameter»"
    )
    assert sesiones.options == {"idempotency_key": "pedido-VB-20260918-ABC123"}


def test_la_clave_se_deriva_del_pedido(proveedor: ProveedorStripe) -> None:
    """Dos intentos del MISMO pedido tienen que pedir la misma clave.

    Es lo que hace que un reintento ---por un corte de red al responder---
    reciba la sesion que ya existia en vez de abrir una segunda cobrable.
    """
    proveedor.crear_sesion(_solicitud())
    primera = proveedor._cliente.sesiones.options
    proveedor.crear_sesion(_solicitud())
    segunda = proveedor._cliente.sesiones.options

    assert primera == segunda


def test_el_retorno_lleva_la_sesion_y_el_pedido(proveedor: ProveedorStripe) -> None:
    """Sin el `pedido` en la URL, la pantalla de retorno no sabe que consultar.

    Stripe solo sustituye `{CHECKOUT_SESSION_ID}`; el codigo hay que ponerlo.
    """
    proveedor.crear_sesion(_solicitud())
    params = proveedor._cliente.sesiones.params

    assert "{CHECKOUT_SESSION_ID}" in params["success_url"]
    assert "pedido=VB-20260918-ABC123" in params["success_url"]
    assert "pedido=VB-20260918-ABC123" in params["cancel_url"]


def test_el_monto_viaja_en_la_unidad_minima(proveedor: ProveedorStripe) -> None:
    """Stripe cobra en centavos: 250.00 son 25000, no 250.

    Mandar 250 cobraria dos bolivianos y medio.
    """
    proveedor.crear_sesion(_solicitud())
    linea = proveedor._cliente.sesiones.params["line_items"][0]

    assert linea["price_data"]["unit_amount"] == 25_000
    assert linea["quantity"] == 2


def test_la_conversion_a_centavos_no_pierde_el_ultimo(proveedor: ProveedorStripe) -> None:
    """150.55 son 15055, no 15054.

    Con `float` el precio se guarda como 150.54999999999998 y truncar despues de
    multiplicar pierde un centavo por linea, que no cuadra con `venta.total`.
    """
    assert a_unidad_minima(Decimal("150.55")) == 15_055
    assert a_unidad_minima(Decimal("150.50")) == 15_050
    assert a_unidad_minima(Decimal("0.01")) == 1


def test_sin_clave_de_api_el_proveedor_no_se_construye(monkeypatch) -> None:
    """Fallar al construirlo es mejor que aceptar pedidos que nadie cobra."""
    from app.core import config

    monkeypatch.setattr(config.settings, "PAGO_API_KEY", "", raising=False)
    with pytest.raises(ValueError):
        ProveedorStripe()
