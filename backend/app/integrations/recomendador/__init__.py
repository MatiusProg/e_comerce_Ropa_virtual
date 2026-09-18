"""Recomendador de prendas. Punto de entrada unico hacia el servicio que
ORDENA las candidatas de CU-33.

Ciclo 3 - realiza el paso 2 de la decision tecnica de CU-33.

    from app.integrations import recomendador

    try:
        sugerencias = recomendador.ordenar(perfil, candidatas, 6)
    except recomendador.ErrorDelRecomendador:
        ...  # el servicio degrada a popularidad

POR QUE NO HAY `esta_disponible()` COMO EN EL PROBADOR
-------------------------------------------------------
Porque no habria quien lo usara. En CU-21 la pantalla pregunta antes para
esconder el boton; aca **la pantalla pide recomendaciones y siempre recibe
algo**: con modelo van ordenadas y explicadas, sin modelo van por popularidad.
Preguntar antes no cambiaria nada de lo que se dibuja.

COMO SE AGREGA UN PROVEEDOR
---------------------------
1. Un modulo hermano de `gemini.py` con `nombre`, `disponible` y
   `ordenar(perfil, candidatas, cuantas)`.
2. Su entrada en `_PROVEEDORES`.
3. IA_PROVEEDOR en las variables de Railway.
"""

from functools import lru_cache

from app.core.config import settings
from app.integrations.recomendador.base import (
    Candidata,
    ErrorDelRecomendador,
    PerfilDelCliente,
    ProveedorRecomendador,
    RecomendadorNoConfigurado,
    Sugerencia,
)
from app.integrations.recomendador.gemini import RecomendadorGemini
from app.integrations.recomendador.no_disponible import RecomendadorNoDisponible

__all__ = [
    "Candidata",
    "ErrorDelRecomendador",
    "PerfilDelCliente",
    "ProveedorRecomendador",
    "RecomendadorNoConfigurado",
    "Sugerencia",
    "nombre_del_proveedor",
    "obtener_proveedor",
    "ordenar",
]


_PROVEEDORES: dict[str, type] = {
    RecomendadorNoDisponible.nombre: RecomendadorNoDisponible,
    RecomendadorGemini.nombre: RecomendadorGemini,
}


@lru_cache
def obtener_proveedor() -> ProveedorRecomendador:
    """El proveedor configurado, construido una sola vez.

    Degrada al no disponible si el nombre no existe o si no se puede construir
    ---casi siempre por falta de clave--- en vez de reventar. Lo mismo que el
    probador y por el mismo motivo: que falte una clave de una funcion que
    sabe degradar no puede impedir que la aplicacion arranque.
    """
    nombre = settings.IA_PROVEEDOR.strip().lower()
    clase = _PROVEEDORES.get(nombre)
    if clase is None:
        import logging

        logging.getLogger("violetboutique.recomendador").warning(
            "IA_PROVEEDOR=%r no existe. Disponibles: %s. Se recomienda por "
            "popularidad.",
            settings.IA_PROVEEDOR,
            ", ".join(sorted(_PROVEEDORES)),
        )
        return RecomendadorNoDisponible()
    try:
        return clase()
    except Exception as e:
        import logging

        logging.getLogger("violetboutique.recomendador").warning(
            "No se pudo construir el recomendador %r (%s). Se recomienda por "
            "popularidad.",
            nombre,
            e,
        )
        return RecomendadorNoDisponible()


def nombre_del_proveedor() -> str:
    """Con que se ordeno. Se guarda en `recomendacion.motor`."""
    return obtener_proveedor().nombre


def ordenar(
    perfil: PerfilDelCliente, candidatas: list[Candidata], cuantas: int
) -> list[Sugerencia]:
    return obtener_proveedor().ordenar(perfil, candidatas, cuantas)
