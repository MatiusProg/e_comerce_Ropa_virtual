"""El proveedor por defecto: no compone nada y lo dice.

POR QUE EL VALOR POR DEFECTO ES ESTE, Y NO GEMINI
--------------------------------------------------
Es la misma decision que `correo/consola.py` y `pasarela_pago/simulada.py`,
con una razon propia: el riesgo **R9** del plan es quedarse sin credito de IA
antes de la defensa. Un valor por defecto que llama a un servicio de pago
gasta cuota cada vez que alguien abre el vestidor en una maquina recien
clonada.

Y hay algo mas importante: **el probado por IA es opcional**. Que no este
configurado NO es un error del sistema, es su estado normal mientras nadie
ponga una clave. Por eso `disponible` es False y no se levanta nada al
construirlo: la pantalla pregunta antes y esconde el boton.
"""

from app.integrations.probador_ia.base import (
    ProbadorNoConfigurado,
    ResultadoDeProbado,
    SolicitudDeProbado,
)


class ProbadorNoDisponible:
    """No hay probador por IA. La pantalla no deberia ni ofrecerlo."""

    nombre = "no_disponible"
    disponible = False

    def probar(self, solicitud: SolicitudDeProbado) -> ResultadoDeProbado:
        raise ProbadorNoConfigurado(
            "El probado por inteligencia artificial no está configurado. "
            "Se habilita poniendo PROBADOR_IA_PROVEEDOR y IA_API_KEY."
        )
