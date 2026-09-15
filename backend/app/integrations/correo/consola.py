"""Proveedor de correo que no envia nada: lo escribe en el log.

Es el proveedor por defecto y el unico que existe hoy. Permite construir y
probar entero cualquier caso de uso que use correo --- CU-41 incluido, con su
token de un solo uso, sus dos endpoints y sus dos pantallas --- sin haber
contratado ningun servicio.

En desarrollo el enlace de recuperacion se lee de la consola de uvicorn y se
pega en el navegador. El flujo es el mismo que sera con un proveedor real: lo
unico que cambia es de donde se saca el enlace.

CUIDADO EN PRODUCCION
---------------------
Este proveedor escribe el cuerpo del mensaje en el log, y en CU-41 ese cuerpo
lleva el enlace de recuperacion, que ES la credencial. Por eso `enviar` avisa
con un WARNING cuando esta corriendo en produccion: si alguien despliega sin
configurar CORREO_PROVEEDOR, el log de Railway termina con enlaces de
recuperacion adentro y ningun usuario recibe nada.
"""

import logging

from app.core.config import settings
from app.integrations.correo.base import Mensaje

_log = logging.getLogger("violetboutique.correo")

_SEPARADOR = "-" * 72


class ProveedorConsola:
    """Escribe el correo en el log en vez de entregarlo."""

    nombre = "consola"

    def enviar(self, mensaje: Mensaje) -> None:
        if settings.es_produccion:
            _log.warning(
                "CORREO_PROVEEDOR=consola en PRODUCCION: el mensaje para %s no "
                "se envio a nadie y su contenido queda escrito en este log.",
                mensaje.destinatario,
            )

        # Una sola llamada y no cuatro: el log de uvicorn intercala lineas de
        # peticiones entre registros separados, y el correo quedaria partido.
        _log.info(
            "\n%s\nCORREO NO ENVIADO (proveedor 'consola')\n"
            "De:     %s <%s>\n"
            "Para:   %s\n"
            "Asunto: %s\n%s\n%s\n%s",
            _SEPARADOR,
            settings.CORREO_REMITENTE_NOMBRE,
            settings.CORREO_REMITENTE,
            mensaje.destinatario,
            mensaje.asunto,
            _SEPARADOR,
            mensaje.cuerpo_texto,
            _SEPARADOR,
        )
