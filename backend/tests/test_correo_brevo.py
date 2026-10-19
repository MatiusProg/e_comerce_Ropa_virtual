"""El correo de produccion sale por la API HTTPS de Brevo, no por SMTP.

Railway bloquea el SMTP saliente fuera del plan Pro: sin este proveedor, CU-40
y CU-41 no le llegan a nadie en produccion. Estas pruebas no necesitan base ni
red: `httpx.post` queda interceptado y se mira lo que se le habria mandado.
"""

import httpx
import pytest

from app.core.config import settings
from app.integrations.correo import ErrorDeEnvio, Mensaje, obtener_proveedor
from app.integrations.correo import brevo
from app.integrations.correo.brevo import URL_BREVO, ProveedorBrevo

MENSAJE = Mensaje(
    destinatario="ana@violetboutique.bo",
    asunto="Su reserva vence mañana",
    cuerpo_texto="Pase a retirar su reserva R-12.",
    cuerpo_html="<p>Pase a retirar su reserva <b>R-12</b>.</p>",
)


@pytest.fixture
def configurado(monkeypatch):
    monkeypatch.setattr(settings, "CORREO_API_KEY", "xkeysib-prueba")
    monkeypatch.setattr(settings, "CORREO_REMITENTE", "remitente@gmail.com")
    monkeypatch.setattr(settings, "CORREO_REMITENTE_NOMBRE", "Violet Boutique")


def _responde(monkeypatch, status: int, cuerpo: dict) -> list[dict]:
    """Reemplaza `httpx.post` y devuelve la lista donde se anotan las llamadas."""
    llamadas: list[dict] = []

    def _post(url, **kwargs):
        llamadas.append({"url": url, **kwargs})
        return httpx.Response(status, json=cuerpo, request=httpx.Request("POST", url))

    monkeypatch.setattr(brevo.httpx, "post", _post)
    return llamadas


def test_el_correo_sale_por_la_api_de_brevo_con_la_clave(configurado, monkeypatch) -> None:
    llamadas = _responde(monkeypatch, 201, {"messageId": "<prueba@brevo>"})

    ProveedorBrevo().enviar(MENSAJE)

    assert len(llamadas) == 1
    llamada = llamadas[0]
    assert llamada["url"] == URL_BREVO
    assert llamada["headers"]["api-key"] == "xkeysib-prueba"
    cuerpo = llamada["json"]
    assert cuerpo["sender"] == {"name": "Violet Boutique", "email": "remitente@gmail.com"}
    assert cuerpo["to"] == [{"email": "ana@violetboutique.bo"}]
    assert cuerpo["subject"] == "Su reserva vence mañana"
    # Las dos versiones del cuerpo: el texto plano es el respaldo del HTML.
    assert "R-12" in cuerpo["htmlContent"]
    assert cuerpo["textContent"] == "Pase a retirar su reserva R-12."


def test_un_rechazo_de_brevo_llega_como_error_de_envio_con_su_motivo(
    configurado, monkeypatch
) -> None:
    """El caso tipico: el remitente no esta verificado en la cuenta de Brevo.

    El motivo tiene que viajar en el error, porque CU-40 lo guarda en la
    notificacion FALLIDA y es lo unico que dice que hay que arreglar.
    """
    _responde(monkeypatch, 400, {"code": "invalid_parameter", "message": "sender not valid"})

    with pytest.raises(ErrorDeEnvio, match="400.*sender not valid"):
        ProveedorBrevo().enviar(MENSAJE)


def test_un_fallo_de_red_llega_como_error_de_envio(configurado, monkeypatch) -> None:
    def _sin_red(url, **kwargs):
        raise httpx.ConnectTimeout("tiempo agotado")

    monkeypatch.setattr(brevo.httpx, "post", _sin_red)

    with pytest.raises(ErrorDeEnvio, match="No se pudo hablar con Brevo"):
        ProveedorBrevo().enviar(MENSAJE)


def test_sin_clave_no_intenta_enviar(monkeypatch) -> None:
    llamadas = _responde(monkeypatch, 201, {})
    monkeypatch.setattr(settings, "CORREO_API_KEY", "  ")

    with pytest.raises(ErrorDeEnvio, match="CORREO_API_KEY"):
        ProveedorBrevo().enviar(MENSAJE)
    assert llamadas == []


def test_brevo_se_elige_por_la_variable_de_entorno(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CORREO_PROVEEDOR", "Brevo")
    obtener_proveedor.cache_clear()
    try:
        assert isinstance(obtener_proveedor(), ProveedorBrevo)
    finally:
        # El proveedor se memoriza: sin esto, la eleccion sobreviviria a esta
        # prueba y las que vengan despues intentarian salir por Brevo.
        obtener_proveedor.cache_clear()
