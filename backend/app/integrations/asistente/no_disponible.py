"""El asistente cuando no hay proveedor de IA.

NO CONTESTA CON UNA RESPUESTA DE RESPALDO, Y ES LA DECISION
-------------------------------------------------------------
El recomendador de CU-33 degrada a popularidad, y esta bien: una lista de
prendas ordenada por ventas sigue siendo util. Aca no hay equivalente.

Un asistente que contesta «no entendi» a todo no es una version degradada de
un asistente: es un cartel que engana. Y contestar con frases armadas seria
peor ---daria respuestas que parecen del sistema y no salen de sus datos---.

Asi que este proveedor **lanza**, y la pantalla no ofrece el asistente
cuando no esta disponible. Lo mismo que hace CU-35 con el microfono.
"""

from __future__ import annotations

from app.integrations.asistente.base import (
    AsistenteNoConfigurado,
    Contexto,
    Respuesta,
)


class AsistenteNoDisponible:
    nombre = "no_disponible"
    disponible = False

    def responder(
        self, pregunta: str, contexto: Contexto, historial: list[tuple[str, str]]
    ) -> Respuesta:
        raise AsistenteNoConfigurado(
            "No hay proveedor de IA configurado para el asistente."
        )
