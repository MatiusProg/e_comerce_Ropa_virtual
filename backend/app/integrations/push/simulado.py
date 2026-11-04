"""Canal push que no envía nada: lo escribe en el log y lo guarda en memoria.

Es el de local y el de las pruebas. `ENVIADOS` es lo que las pruebas leen para
comprobar a quién le habría llegado qué; se vacía con `ENVIADOS.clear()`.

Una dirección que empieza con `invalida-` responde como un dispositivo que ya
desinstaló la app: así se prueba que la suscripción vencida se borra.
"""

from __future__ import annotations

import logging

from app.integrations.push.base import AvisoPush, Destino, ErrorDePush

_log = logging.getLogger("violetboutique.push")

ENVIADOS: list[tuple[Destino, AvisoPush]] = []


class ProveedorSimulado:
    nombre = "simulado"

    def enviar(self, destino: Destino, aviso: AvisoPush) -> None:
        if destino.direccion.startswith("invalida-"):
            raise ErrorDePush("El dispositivo ya no está registrado.", invalida=True)
        ENVIADOS.append((destino, aviso))
        _log.info(
            "PUSH NO ENVIADO (canal simulado) %s -> %s…: %s | %s",
            destino.canal,
            destino.direccion[:24],
            aviso.titulo,
            aviso.cuerpo,
        )
