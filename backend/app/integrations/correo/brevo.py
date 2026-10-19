"""Proveedor de correo real por la API HTTPS de Brevo.

POR QUE BREVO Y NO EL SMTP DE GMAIL
-----------------------------------
`smtp.py` dejo escrito el riesgo: no se sabia si Railway deja salir por el
puerto 587. Ya se sabe que no. Railway bloquea los puertos de correo salientes
(465 y 587) en los planes Free, Trial y Hobby, y el SMTP de Gmail ahi no conecta
nunca: cada envio termina en un tiempo de espera agotado. Lo comprobamos en
PROYECTO_MEDICOS, que por eso manda su correo de produccion por Brevo desde el
04/10/2026 (su PR #65).

Un POST por HTTPS no corre ese riesgo: el contenedor ya sale a internet para
Supabase y para la IA. Es lo que `base.py` pedia desde el principio.

Brevo resuelve ademas la trampa que `config.py` anota sobre el remitente: no
hace falta tener un dominio propio. Alcanza con verificar UNA casilla como
remitente, y desde ella se le escribe a cualquier destinatario. La capa
gratuita da 300 correos por dia, de sobra para el prototipo.

COMO SE CONFIGURA
-----------------
1. En Brevo: SMTP & API -> API Keys -> generar una clave (empieza con
   `xkeysib-`). Se puede usar la misma cuenta de PROYECTO_MEDICOS.
2. En Brevo: Senders -> verificar la casilla que va a figurar como remitente.
3. En Railway:

       CORREO_PROVEEDOR = brevo
       CORREO_API_KEY   = la clave xkeysib-...
       CORREO_REMITENTE = la casilla verificada en el paso 2

**El remitente tiene que estar verificado en Brevo**, o Brevo rechaza el envio
con un 400. Ese rechazo llega aca como ErrorDeEnvio con el mensaje de Brevo
adentro, y CU-40 lo deja escrito como motivo de la notificacion FALLIDA.
"""

import httpx

from app.core.config import settings
from app.integrations.correo.base import ErrorDeEnvio, Mensaje

#: Endpoint de correo transaccional de la API v3 de Brevo.
URL_BREVO = "https://api.brevo.com/v3/smtp/email"


class ProveedorBrevo:
    """Entrega el correo con un POST a la API transaccional de Brevo."""

    nombre = "brevo"

    def enviar(self, mensaje: Mensaje) -> None:
        clave = settings.CORREO_API_KEY.strip()
        if not clave:
            # Igual que en `smtp.py`: ErrorDeEnvio y no ValueError, para que el
            # despachador de CU-40 marque FALLIDO y siga con el siguiente.
            raise ErrorDeEnvio("CORREO_API_KEY está vacía: falta la clave de Brevo.")

        cuerpo = {
            "sender": {
                "name": settings.CORREO_REMITENTE_NOMBRE,
                "email": settings.CORREO_REMITENTE.strip(),
            },
            "to": [{"email": mensaje.destinatario}],
            "subject": mensaje.asunto,
            "htmlContent": mensaje.cuerpo_html,
            "textContent": mensaje.cuerpo_texto,
        }

        try:
            respuesta = httpx.post(
                URL_BREVO,
                json=cuerpo,
                headers={"api-key": clave, "accept": "application/json"},
                # La misma espera que el SMTP: es el tope que ya se acepto para
                # que un proveedor lento no deje colgado el despacho.
                timeout=settings.CORREO_SMTP_ESPERA_SEGUNDOS,
            )
        except httpx.HTTPError as error:
            raise ErrorDeEnvio(f"No se pudo hablar con Brevo: {error}") from error

        if respuesta.status_code >= 400:
            # Brevo explica el rechazo en `message` (remitente sin verificar,
            # clave invalida, cupo diario agotado). Se lo pasa tal cual: es lo
            # que hace falta leer para arreglarlo. El cuerpo del correo no se
            # copia, porque en CU-41 lleva el enlace de recuperacion.
            try:
                motivo = respuesta.json().get("message", respuesta.text)
            except ValueError:
                motivo = respuesta.text
            raise ErrorDeEnvio(f"Brevo rechazó el envío ({respuesta.status_code}): {motivo}")
