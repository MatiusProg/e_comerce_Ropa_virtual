"""Firebase Cloud Messaging, API HTTP v1: los avisos a la app Flutter.

SIN EL SDK DE GOOGLE
--------------------
La API v1 pide un token OAuth2 de la cuenta de servicio. Ese token se obtiene
firmando un JWT con la clave privada de la cuenta (RS256) y canjeándolo en
`token_uri`. El proyecto ya firma JWT con `python-jose`, así que no hace falta
sumar `google-auth` ni `firebase-admin` (que arrastran decenas de paquetes)
para dos POST. El token dura una hora y se reutiliza mientras le queden más de
cinco minutos.

LA CUENTA DE SERVICIO
---------------------
Firebase → Configuración del proyecto → Cuentas de servicio → Generar nueva
clave privada. El JSON va entero en PUSH_FCM_CREDENCIALES (o en base64).
"""

from __future__ import annotations

import base64
import json
import threading
import time

import httpx
from jose import jwt

from app.core.config import settings
from app.integrations.push.base import AvisoPush, Destino, ErrorDePush

_ALCANCE = "https://www.googleapis.com/auth/firebase.messaging"


def _credenciales() -> dict:
    crudo = settings.PUSH_FCM_CREDENCIALES.strip()
    if not crudo:
        raise ErrorDePush("FCM no está configurado: falta PUSH_FCM_CREDENCIALES.")
    if not crudo.startswith("{"):
        try:
            crudo = base64.b64decode(crudo).decode("utf-8")
        except Exception as e:  # noqa: BLE001
            raise ErrorDePush("PUSH_FCM_CREDENCIALES no es un JSON ni un base64 válido.") from e
    try:
        datos = json.loads(crudo)
    except json.JSONDecodeError as e:
        raise ErrorDePush("PUSH_FCM_CREDENCIALES no es un JSON válido.") from e
    for clave in ("project_id", "client_email", "private_key", "token_uri"):
        if not datos.get(clave):
            raise ErrorDePush(f"A la cuenta de servicio de FCM le falta «{clave}».")
    return datos


class ProveedorFcm:
    nombre = "fcm"

    def __init__(self) -> None:
        self._token: str | None = None
        self._vence = 0.0
        self._candado = threading.Lock()

    def _token_de_acceso(self, cred: dict) -> str:
        with self._candado:
            if self._token and time.time() < self._vence - 300:
                return self._token
            ahora = int(time.time())
            afirmacion = jwt.encode(
                {
                    "iss": cred["client_email"],
                    "scope": _ALCANCE,
                    "aud": cred["token_uri"],
                    "iat": ahora,
                    "exp": ahora + 3600,
                },
                cred["private_key"],
                algorithm="RS256",
            )
            try:
                r = httpx.post(
                    cred["token_uri"],
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": afirmacion,
                    },
                    timeout=settings.PUSH_ESPERA_SEGUNDOS,
                )
            except httpx.HTTPError as e:
                raise ErrorDePush(f"No se pudo pedir el token de FCM: {e}") from e
            if r.status_code != 200:
                raise ErrorDePush(f"Google rechazó la cuenta de servicio ({r.status_code}).")
            cuerpo = r.json()
            self._token = cuerpo["access_token"]
            self._vence = time.time() + int(cuerpo.get("expires_in", 3600))
            return self._token

    def enviar(self, destino: Destino, aviso: AvisoPush) -> None:
        cred = _credenciales()
        token = self._token_de_acceso(cred)
        datos = {k: str(v) for k, v in aviso.datos.items()}
        if aviso.enlace:
            datos["enlace"] = aviso.enlace
        mensaje = {
            "message": {
                "token": destino.direccion,
                "notification": {"title": aviso.titulo, "body": aviso.cuerpo},
                "data": datos,
                "android": {
                    "priority": "HIGH",
                    "notification": {"channel_id": "avisos", "click_action": "FLUTTER_NOTIFICATION_CLICK"},
                },
            }
        }
        try:
            r = httpx.post(
                f"https://fcm.googleapis.com/v1/projects/{cred['project_id']}/messages:send",
                json=mensaje,
                headers={"Authorization": f"Bearer {token}"},
                timeout=settings.PUSH_ESPERA_SEGUNDOS,
            )
        except httpx.HTTPError as e:
            raise ErrorDePush(f"FCM no respondió: {e}") from e
        if r.status_code == 200:
            return
        texto = r.text[:200]
        # 404 UNREGISTERED: la app se desinstaló o el token rotó.
        invalida = r.status_code == 404 or "UNREGISTERED" in texto
        raise ErrorDePush(f"FCM respondió {r.status_code}: {texto}", invalida=invalida)
