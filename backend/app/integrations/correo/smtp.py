"""Proveedor de correo real por SMTP. Sirve para Gmail con contrasena de aplicacion.

POR QUE SMTP SI `base.py` PREFIERE UNA API HTTP
------------------------------------------------
`base.py` dice, con razon, que un proveedor deberia hablar por HTTP: muchas
plataformas de hospedaje bloquean los puertos de correo de salida y eso se
descubre tarde. Esa sigue siendo la preferencia, y este modulo no la contradice
--- la pone a prueba.

Se eligio SMTP para el 28/09 por una razon concreta: **es el unico camino que no
depende de dar de alta una cuenta nueva en un servicio de terceros**. La cuenta
de Google ya existe, la contrasena de aplicacion se genera en dos minutos desde
la propia cuenta, y desde ahi se le puede escribir a CUALQUIER direccion. Los
servicios transaccionales gratuitos, en cambio, o piden verificar un dominio
---que el proyecto no tiene--- o solo dejan escribirle a la casilla verificada
de la cuenta, que es justo lo que arruina una demostracion frente al tribunal.

EL RIESGO, ESCRITO PARA QUE NO SORPRENDA
------------------------------------------
No se verifico si Railway deja salir por el puerto 587. Si lo bloquea, el envio
falla con un tiempo de espera agotado y el sistema **no se rompe**: el aviso
dentro de la aplicacion ya esta guardado ---esa es la degradacion acordada el
13/09--- y la notificacion queda FALLIDA con el motivo, visible desde el
endpoint de mantenimiento. Comprobarlo es disparar el despacho una vez en
produccion y mirar el resultado.

Si resultara bloqueado, la salida es un modulo hermano que hable HTTP contra un
servicio transaccional. Nada de CU-40 ni de CU-41 cambia: es una entrada mas en
`_PROVEEDORES` y una variable distinta en Railway.

COMO SE CONFIGURA CON GMAIL
-----------------------------
1. La cuenta necesita la verificacion en dos pasos activada.
2. Se genera una **contrasena de aplicacion** de 16 caracteres.
3. En Railway:

       CORREO_PROVEEDOR   = smtp
       CORREO_SMTP_USUARIO= la direccion de Gmail
       CORREO_API_KEY     = la contrasena de aplicacion (sin espacios)
       CORREO_REMITENTE   = la misma direccion de Gmail

**El remitente tiene que ser la misma cuenta que se autentica.** Gmail reescribe
el `From` al de la cuenta, asi que poner `no-responder@violetboutique.bo` ---un
dominio que no es de nadie--- no lo hace aparecer: lo unico que consigue es que
el correo llegue con otro remitente del que dice el codigo. Por eso el modulo
avisa cuando los dos no coinciden.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings
from app.integrations.correo.base import ErrorDeEnvio, Mensaje

_log = logging.getLogger("violetboutique.correo")


class ProveedorSmtp:
    """Entrega el correo por SMTP con STARTTLS."""

    nombre = "smtp"

    def enviar(self, mensaje: Mensaje) -> None:
        usuario = (settings.CORREO_SMTP_USUARIO or settings.CORREO_REMITENTE).strip()
        clave = settings.CORREO_API_KEY.strip()

        if not clave:
            # Sin clave no hay nada que intentar. Se levanta ErrorDeEnvio y no
            # ValueError para que el despachador de CU-40 lo trate como
            # cualquier otro fallo de envio: marca FALLIDO con el motivo y
            # sigue con el siguiente, en vez de cortar la corrida entera.
            raise ErrorDeEnvio(
                "CORREO_API_KEY está vacía: falta la contraseña de aplicación."
            )

        remitente = settings.CORREO_REMITENTE.strip()
        if remitente.lower() != usuario.lower():
            # Aviso y no error: el correo igual sale, solo que con otro
            # remitente del que dice la configuracion. Callarlo dejaria a
            # alguien buscando por que el `From` no es el que puso.
            _log.warning(
                "CORREO_REMITENTE (%s) no es la cuenta que se autentica (%s). "
                "El servidor va a reescribir el remitente.",
                remitente,
                usuario,
            )

        correo = EmailMessage()
        correo["From"] = f"{settings.CORREO_REMITENTE_NOMBRE} <{usuario}>"
        correo["To"] = mensaje.destinatario
        correo["Subject"] = mensaje.asunto
        # El texto plano primero y el HTML como alternativa: es el orden que
        # exige MIME, y el que hace que un lector sin HTML muestre algo legible
        # en vez de las etiquetas.
        correo.set_content(mensaje.cuerpo_texto)
        correo.add_alternative(mensaje.cuerpo_html, subtype="html")

        contexto = ssl.create_default_context()
        try:
            with smtplib.SMTP(
                settings.CORREO_SMTP_HOST,
                settings.CORREO_SMTP_PUERTO,
                timeout=settings.CORREO_SMTP_ESPERA_SEGUNDOS,
            ) as servidor:
                servidor.starttls(context=contexto)
                servidor.login(usuario, clave)
                servidor.send_message(correo)
        except smtplib.SMTPAuthenticationError as error:
            # El caso mas frecuente: la contrasena normal de la cuenta en vez de
            # la de aplicacion, o la verificacion en dos pasos sin activar.
            raise ErrorDeEnvio(
                "El servidor rechazó las credenciales. Con Gmail hace falta una "
                f"contraseña de aplicación, no la de la cuenta ({error.smtp_code})."
            ) from error
        except (OSError, smtplib.SMTPException) as error:
            # OSError cubre el tiempo de espera agotado, que es exactamente la
            # forma que toma un puerto 587 bloqueado por la plataforma.
            raise ErrorDeEnvio(f"No se pudo entregar por SMTP: {error}") from error
