"""CU-42 · Los canales reales de push, sin salir a internet.

FCM se prueba con `httpx.post` reemplazado: se verifica que firme el JWT de la
cuenta de servicio, que canjee el token una sola vez, que arme el mensaje de la
API v1 y que distinga un token vencido (se borra) de otro error. Web Push, que
el cuerpo tenga la forma que muestra el service worker de Angular.
"""

from __future__ import annotations

import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt

from app.core.config import settings
from app.integrations.push.base import AvisoPush, Destino, ErrorDePush
from app.integrations.push.fcm import ProveedorFcm
from app.integrations.push.webpush import ProveedorWebPush, carga_para_angular


@pytest.fixture
def cuenta_de_servicio(monkeypatch) -> dict:
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = clave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    cred = {
        "project_id": "violet-pruebas",
        "client_email": "push@violet-pruebas.iam.gserviceaccount.com",
        "private_key": pem,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    monkeypatch.setattr(settings, "PUSH_FCM_CREDENCIALES", json.dumps(cred))
    cred["publica"] = clave.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return cred


class _Http:
    """Hace de Google: responde el token y después lo que se le pida."""

    def __init__(self, envio: httpx.Response):
        self.envio = envio
        self.llamadas: list[tuple[str, dict]] = []

    def __call__(self, url, **kw):
        self.llamadas.append((url, kw))
        pedido = httpx.Request("POST", url)
        if "oauth2" in url:
            return httpx.Response(200, json={"access_token": "ya29.token", "expires_in": 3600}, request=pedido)
        self.envio.request = pedido
        return self.envio


AVISO = AvisoPush(titulo="Sincronización", cuerpo="2 confirmadas", enlace="/caja/pendientes",
                  datos={"tipo": "OPERACION_OFFLINE", "notificacion_id": "7"})


def test_fcm_firma_canjea_y_manda_el_mensaje_v1(monkeypatch, cuenta_de_servicio) -> None:
    http = _Http(httpx.Response(200, json={"name": "projects/x/messages/1"}))
    monkeypatch.setattr(httpx, "post", http)
    proveedor = ProveedorFcm()

    proveedor.enviar(Destino(canal="FCM", direccion="token-telefono"), AVISO)
    proveedor.enviar(Destino(canal="FCM", direccion="token-telefono"), AVISO)

    canjes = [c for c in http.llamadas if "oauth2" in c[0]]
    envios = [c for c in http.llamadas if "fcm.googleapis.com" in c[0]]
    assert len(canjes) == 1, "el token de acceso se reutiliza"
    assert len(envios) == 2

    afirmacion = canjes[0][1]["data"]["assertion"]
    reclamos = jwt.decode(
        afirmacion, cuenta_de_servicio["publica"], algorithms=["RS256"],
        audience=cuenta_de_servicio["token_uri"],
    )
    assert reclamos["iss"] == cuenta_de_servicio["client_email"]
    assert "firebase.messaging" in reclamos["scope"]

    url, kw = envios[0]
    assert url.endswith("/projects/violet-pruebas/messages:send")
    assert kw["headers"]["Authorization"] == "Bearer ya29.token"
    mensaje = kw["json"]["message"]
    assert mensaje["token"] == "token-telefono"
    assert mensaje["notification"] == {"title": "Sincronización", "body": "2 confirmadas"}
    assert mensaje["data"]["enlace"] == "/caja/pendientes"
    assert mensaje["data"]["tipo"] == "OPERACION_OFFLINE"


def test_fcm_un_token_vencido_es_invalido(monkeypatch, cuenta_de_servicio) -> None:
    monkeypatch.setattr(httpx, "post", _Http(httpx.Response(404, text='{"error":{"status":"NOT_FOUND","details":[{"errorCode":"UNREGISTERED"}]}}')))
    with pytest.raises(ErrorDePush) as e:
        ProveedorFcm().enviar(Destino(canal="FCM", direccion="viejo"), AVISO)
    assert e.value.invalida is True


def test_fcm_otro_error_no_borra_el_dispositivo(monkeypatch, cuenta_de_servicio) -> None:
    monkeypatch.setattr(httpx, "post", _Http(httpx.Response(503, text="Unavailable")))
    with pytest.raises(ErrorDePush) as e:
        ProveedorFcm().enviar(Destino(canal="FCM", direccion="t"), AVISO)
    assert e.value.invalida is False


def test_fcm_sin_credenciales_falla_con_el_motivo(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PUSH_FCM_CREDENCIALES", "")
    with pytest.raises(ErrorDePush, match="PUSH_FCM_CREDENCIALES"):
        ProveedorFcm().enviar(Destino(canal="FCM", direccion="t"), AVISO)


def test_fcm_acepta_las_credenciales_en_base64(monkeypatch, cuenta_de_servicio) -> None:
    import base64

    crudo = settings.PUSH_FCM_CREDENCIALES
    monkeypatch.setattr(settings, "PUSH_FCM_CREDENCIALES", base64.b64encode(crudo.encode()).decode())
    http = _Http(httpx.Response(200, json={}))
    monkeypatch.setattr(httpx, "post", http)
    ProveedorFcm().enviar(Destino(canal="FCM", direccion="t"), AVISO)
    assert any("violet-pruebas" in url for url, _ in http.llamadas)


def test_webpush_arma_lo_que_entiende_el_service_worker_de_angular() -> None:
    carga = carga_para_angular(AVISO)
    n = carga["notification"]
    assert n["title"] == "Sincronización"
    assert n["body"] == "2 confirmadas"
    assert n["data"]["onActionClick"]["default"] == {
        "operation": "navigateLastFocusedOrOpen",
        "url": "/caja/pendientes",
    }


def test_webpush_sin_claves_vapid_falla_con_el_motivo(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PUSH_VAPID_PRIVADA", "")
    destino = Destino(canal="WEBPUSH", direccion="https://push.example/x", clave_p256dh="a", clave_auth="b")
    with pytest.raises(ErrorDePush, match="PUSH_VAPID_PRIVADA"):
        ProveedorWebPush().enviar(destino, AVISO)


def test_webpush_cifra_y_firma_contra_un_navegador_simulado(monkeypatch) -> None:
    """Una suscripción con claves de verdad: pywebpush cifra y firma, y el POST
    sale al endpoint con la cabecera VAPID. El servicio push responde 410: el
    navegador anuló la suscripción, así que el error dice «inválida»."""
    import base64

    import requests
    from cryptography.hazmat.primitives.asymmetric import ec

    def b64(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    servidor = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(
        settings, "PUSH_VAPID_PRIVADA", b64(servidor.private_numbers().private_value.to_bytes(32, "big"))
    )
    navegador = ec.generate_private_key(ec.SECP256R1())
    p256dh = b64(navegador.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    ))
    visto = {}

    def _post(url, data=None, headers=None, timeout=None, **kw):
        visto.update(url=url, headers=headers, data=data)
        r = requests.Response()
        r.status_code = 410
        r._content = b"Gone"
        return r

    monkeypatch.setattr(requests, "post", _post)
    destino = Destino(canal="WEBPUSH", direccion="https://push.example/abc",
                      clave_p256dh=p256dh, clave_auth=b64(b"0123456789abcdef"))
    with pytest.raises(ErrorDePush) as e:
        ProveedorWebPush().enviar(destino, AVISO)
    assert e.value.invalida is True
    assert visto["url"] == "https://push.example/abc"
    assert visto["headers"]["Authorization"].startswith("vapid ")
    assert visto["headers"]["Content-Encoding"] == "aes128gcm"
    assert b"Sincronizaci" not in visto["data"], "el cuerpo viaja cifrado"
