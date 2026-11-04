"""Web Push con VAPID: los avisos a la web instalada (PWA).

No hace falta cuenta en ningún servicio: el navegador elige su servicio push
(el de Chrome, el de Firefox…) y el servidor se identifica con un par de claves
VAPID propio. `pywebpush` cifra el mensaje con las claves que mandó el
navegador al suscribirse y lo firma con la clave privada.

EL FORMATO ES EL DEL SERVICE WORKER DE ANGULAR
----------------------------------------------
`ngsw-worker.js` muestra solo un JSON con la forma `{"notification": {...}}`,
y `data.onActionClick` le dice a dónde llevar al tocarlo. Por eso el cuerpo se
arma acá así y no con un formato propio.

Las claves se generan una vez con `python -m app.integrations.push.webpush`.
"""

from __future__ import annotations

import json

from app.core.config import settings
from app.integrations.push.base import AvisoPush, Destino, ErrorDePush


def carga_para_angular(aviso: AvisoPush) -> dict:
    datos: dict = dict(aviso.datos)
    if aviso.enlace:
        datos["onActionClick"] = {
            "default": {"operation": "navigateLastFocusedOrOpen", "url": aviso.enlace}
        }
    return {
        "notification": {
            "title": aviso.titulo,
            "body": aviso.cuerpo,
            "icon": "/logo-violet-boutique.png",
            "badge": "/favicon.ico",
            "data": datos,
        }
    }


class ProveedorWebPush:
    nombre = "webpush"

    def enviar(self, destino: Destino, aviso: AvisoPush) -> None:
        if not settings.PUSH_VAPID_PRIVADA:
            raise ErrorDePush("Web Push no está configurado: falta PUSH_VAPID_PRIVADA.")
        if not (destino.clave_p256dh and destino.clave_auth):
            raise ErrorDePush("La suscripción web no trae sus claves.", invalida=True)
        from pywebpush import WebPushException, webpush

        try:
            webpush(
                subscription_info={
                    "endpoint": destino.direccion,
                    "keys": {"p256dh": destino.clave_p256dh, "auth": destino.clave_auth},
                },
                data=json.dumps(carga_para_angular(aviso)),
                vapid_private_key=settings.PUSH_VAPID_PRIVADA,
                vapid_claims={"sub": settings.PUSH_VAPID_CONTACTO},
                timeout=settings.PUSH_ESPERA_SEGUNDOS,
                ttl=24 * 3600,
            )
        except WebPushException as e:
            codigo = e.response.status_code if e.response is not None else None
            # 404/410: el navegador anuló la suscripción.
            raise ErrorDePush(f"Web Push falló ({codigo}): {e}", invalida=codigo in (404, 410)) from e
        except Exception as e:  # noqa: BLE001
            raise ErrorDePush(f"Web Push falló: {type(e).__name__}: {e}") from e


if __name__ == "__main__":  # pragma: no cover
    # Genera un par de claves VAPID para PUSH_VAPID_PUBLICA y PUSH_VAPID_PRIVADA.
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    clave = ec.generate_private_key(ec.SECP256R1())
    privada = clave.private_numbers().private_value.to_bytes(32, "big")
    publica = clave.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    def b64(b: bytes) -> str:
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    print(f"PUSH_VAPID_PUBLICA={b64(publica)}")
    print(f"PUSH_VAPID_PRIVADA={b64(privada)}")
