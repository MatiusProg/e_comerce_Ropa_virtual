"""
P10 - Inteligencia Artificial / CU-34  |  capa: ruta

DOS ENDPOINTS: PREGUNTAR Y SABER SI SE PUEDE
----------------------------------------------
El segundo existe por lo mismo que en CU-35: la pantalla pregunta primero y
esconde el asistente cuando no hay modelo, en vez de ofrecerlo y fallar al
tocarlo. **Sin modelo no hay degradacion posible** --- un asistente que
contesta «no entendi» a todo es un cartel que engana.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.ia import asistente_service as service
from app.modules.ia.asistente_schemas import (
    DisponibleOut,
    PreguntaIn,
    RespuestaOut,
)

router = APIRouter(
    prefix="/asistente",
    tags=["CU-34 · Conversar con el asistente virtual"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El asistente es para clientes."},
    },
)


@router.get(
    "/disponible",
    response_model=DisponibleOut,
    summary="CU-34 Si se puede conversar",
)
def hay_asistente() -> DisponibleOut:
    """La pantalla lo pregunta ANTES de ofrecer el asistente."""
    return DisponibleOut(
        disponible=service.esta_disponible(),
        ejemplos=list(service.EJEMPLOS),
    )


@router.post(
    "",
    response_model=RespuestaOut,
    summary="CU-34 Preguntarle al asistente",
    responses={
        422: {"description": "La pregunta está vacía o es demasiado larga."},
        503: {"description": "No hay modelo, o no respondió."},
    },
)
def preguntar(datos: PreguntaIn, db: DbSession, usuario: Usuario) -> RespuestaOut:
    """Contesta sobre el catálogo y sobre **los datos del que pregunta**.

    El modelo no consulta la base: se le arma el contexto con datos reales
    ya filtrados por cliente, y solo redacta sobre eso. Ver
    `integrations/asistente/base.py`.
    """
    try:
        respuesta = service.responder(
            db,
            usuario.id,
            pregunta=datos.pregunta,
            historial=[(t.pregunta, t.respuesta) for t in datos.historial],
        )
    except service.ErrorDeAsistente as e:
        raise HTTPException(e.codigo, detail=e.mensaje) from e

    return RespuestaOut(texto=respuesta.texto, productos=respuesta.productos)
