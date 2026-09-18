"""
P10 - Inteligencia Artificial / CU-33  |  capa: router

Un solo endpoint. CU-34 y CU-35 no estan construidos: son los que el plan deja
caer primero si falta tiempo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.ia import service
from app.modules.ia.schemas import RecomendacionesOut

router = APIRouter(
    prefix="/tienda/recomendaciones",
    tags=["CU-33 · Recomendaciones"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
)


@router.get("", response_model=RecomendacionesOut)
def mis_recomendaciones(
    db: DbSession,
    usuario: Usuario,
    forzar: Annotated[
        bool,
        Query(
            description=(
                "Vuelve a generar aunque la guardada siga vigente. Es para la "
                "demostración: sin esto, mostrar el efecto de cambiar las "
                "preferencias obligaría a esperar doce horas."
            )
        ),
    ] = False,
):
    """Las prendas recomendadas para quien pregunta (RF25).

    NUNCA FALLA POR FALTA DE DATOS NI POR EL MODELO
    ------------------------------------------------
    Sin talla cargada, sin categorias elegidas, sin historial, sin proveedor de
    IA o sin cuota, responde 200 igual --- con las prendas ordenadas por
    popularidad y `motor` en `popularidad`. Lo unico que se pierde es la
    personalizacion.

    Una lista vacia significa que la tienda no tiene NINGUNA prenda activa con
    existencia, no que algo se rompio.
    """
    resultado = service.recomendaciones(db, usuario.id, forzar=forzar)
    if resultado is None:
        # El rol ya lo filtro, asi que esto solo pasa con un CLIENTE sin ficha
        # --- dato inconsistente ---. Se responde vacio y no 404: no hay nada
        # que el cliente pueda hacer al respecto, y la pantalla ya sabe
        # dibujar una lista vacia.
        from datetime import datetime, timezone

        return RecomendacionesOut(
            prendas=[], motor="popularidad", generada_en=datetime.now(timezone.utc)
        )
    return resultado
