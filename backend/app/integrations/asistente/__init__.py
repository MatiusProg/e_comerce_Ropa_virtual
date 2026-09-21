"""CU-34 · El asistente conversacional. Fabrica del proveedor.

Un caso de uso que necesita contestar una pregunta importa `responder` de
aca. Nunca importa un proveedor concreto: cual se usa lo decide la variable
de entorno IA_PROVEEDOR, no el codigo que llama.

    from app.integrations import asistente
    respuesta = asistente.responder(pregunta, contexto, historial)

Para agregar un proveedor:
1. Un modulo hermano de `gemini.py` que cumpla `ProveedorAsistente`.
2. Registrarlo en `_PROVEEDORES`.
3. IA_PROVEEDOR en las variables de Railway.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.integrations.asistente.base import (
    AsistenteNoConfigurado,
    Contexto,
    ErrorDelAsistente,
    ProveedorAsistente,
    Respuesta,
)
from app.integrations.asistente.gemini import AsistenteGemini
from app.integrations.asistente.no_disponible import AsistenteNoDisponible

__all__ = [
    "AsistenteNoConfigurado",
    "Contexto",
    "ErrorDelAsistente",
    "ProveedorAsistente",
    "Respuesta",
    "esta_disponible",
    "obtener_proveedor",
    "responder",
]

_PROVEEDORES: dict[str, type] = {
    AsistenteNoDisponible.nombre: AsistenteNoDisponible,
    AsistenteGemini.nombre: AsistenteGemini,
}


@lru_cache
def obtener_proveedor() -> ProveedorAsistente:
    """El proveedor configurado, construido una sola vez.

    Degrada al no disponible si el nombre no existe o si no se puede
    construir ---casi siempre por falta de clave--- en vez de reventar: que
    falte una clave no puede impedir que la aplicacion arranque.
    """
    nombre = settings.IA_PROVEEDOR.strip().lower()
    clase = _PROVEEDORES.get(nombre)
    if clase is None:
        import logging

        logging.getLogger("violetboutique.asistente").warning(
            "IA_PROVEEDOR=%r no existe. Disponibles: %s. El asistente no se "
            "va a ofrecer.",
            settings.IA_PROVEEDOR,
            ", ".join(sorted(_PROVEEDORES)),
        )
        return AsistenteNoDisponible()
    try:
        return clase()
    except Exception as e:
        import logging

        logging.getLogger("violetboutique.asistente").warning(
            "No se pudo construir el asistente %r (%s). No se va a ofrecer.",
            nombre,
            e,
        )
        return AsistenteNoDisponible()


def esta_disponible() -> bool:
    """Si se puede conversar. La pantalla lo pregunta ANTES de ofrecerlo.

    Mismo criterio que el microfono de CU-35: esconder lo que no funciona es
    mejor que ofrecerlo y fallar al tocarlo.
    """
    return bool(getattr(obtener_proveedor(), "disponible", False))


def responder(
    pregunta: str, contexto: Contexto, historial: list[tuple[str, str]]
) -> Respuesta:
    return obtener_proveedor().responder(pregunta, contexto, historial)
