"""Interprete de pedidos de reporte en lenguaje natural (CU-35).

    from app.integrations import interprete

    pedido = interprete.interpretar(texto, reportes, date.today())
    if pedido is None:
        ...  # no se entendio: se le pide que lo repita

POR QUE HAY `esta_disponible()`, COMO EN EL PROBADOR
-----------------------------------------------------
Porque sin modelo **no hay nada que ofrecer**: a diferencia del recomendador,
que degrada a popularidad y sigue sirviendo prendas, aca no se puede adivinar
que reporte se pidio. La pantalla pregunta antes y esconde el boton del
microfono, en vez de ofrecerlo y fallar al tocarlo.
"""

from datetime import date
from functools import lru_cache

from app.core.config import settings
from app.integrations.interprete.base import (
    ErrorDelInterprete,
    InterpreteNoConfigurado,
    Pedido,
    ProveedorInterprete,
    ReporteConocido,
)
from app.integrations.interprete.gemini import InterpreteGemini
from app.integrations.interprete.no_disponible import InterpreteNoDisponible

__all__ = [
    "ErrorDelInterprete",
    "InterpreteNoConfigurado",
    "Pedido",
    "ProveedorInterprete",
    "ReporteConocido",
    "esta_disponible",
    "interpretar",
    "obtener_proveedor",
]

_PROVEEDORES: dict[str, type] = {
    InterpreteNoDisponible.nombre: InterpreteNoDisponible,
    InterpreteGemini.nombre: InterpreteGemini,
}


@lru_cache
def obtener_proveedor() -> ProveedorInterprete:
    """El configurado, construido una vez. Degrada si falta la clave."""
    nombre = settings.IA_PROVEEDOR.strip().lower()
    clase = _PROVEEDORES.get(nombre)
    if clase is None:
        import logging

        logging.getLogger("violetboutique.interprete").warning(
            "IA_PROVEEDOR=%r no existe. El pedido por voz queda apagado.",
            settings.IA_PROVEEDOR,
        )
        return InterpreteNoDisponible()
    try:
        return clase()
    except Exception as e:
        import logging

        logging.getLogger("violetboutique.interprete").warning(
            "No se pudo construir el interprete %r (%s). Queda apagado.", nombre, e
        )
        return InterpreteNoDisponible()


def esta_disponible() -> bool:
    """Si hay con que interpretar. La pantalla esconde el microfono si no."""
    return obtener_proveedor().disponible


def interpretar(
    texto: str, reportes: list[ReporteConocido], hoy: date
) -> Pedido | None:
    return obtener_proveedor().interpretar(texto, reportes, hoy)
