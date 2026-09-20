"""El proveedor por defecto: no interpreta nada y lo dice.

A diferencia del recomendador ---que degrada a popularidad y sigue sirviendo
prendas--- aca NO hay degradacion posible: sin un modelo que entienda la
frase, no hay forma de saber que reporte se pidio. Lo unico honesto es
decirlo y dejar que el administrador elija a mano en la pantalla de reportes,
que sigue funcionando igual.
"""

from datetime import date

from app.integrations.interprete.base import (
    InterpreteNoConfigurado,
    Pedido,
    ReporteConocido,
)


class InterpreteNoDisponible:
    nombre = "no_disponible"
    disponible = False

    def interpretar(
        self, texto: str, reportes: list[ReporteConocido], hoy: date
    ) -> Pedido | None:
        raise InterpreteNoConfigurado(
            "El pedido por voz no está configurado. Se habilita con "
            "IA_PROVEEDOR y IA_API_KEY."
        )
