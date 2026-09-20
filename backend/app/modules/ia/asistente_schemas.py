"""
P10 - Inteligencia Artificial / CU-34  |  contrato de la API
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TurnoIn(BaseModel):
    """Un intercambio anterior de esta misma conversacion."""

    pregunta: str = Field(max_length=500)
    respuesta: str = Field(max_length=2000)


class PreguntaIn(BaseModel):
    """Lo que el cliente escribe, con lo que ya se hablo.

    EL HISTORIAL LO MANDA LA PANTALLA
    ----------------------------------
    No hay tabla de conversaciones: ver el porque en `asistente_service`. La
    pantalla guarda los turnos mientras esta abierta y los reenvia, que es
    lo que permite entender «¿y en talla M?».

    Se acota a diez para que el cuerpo de la peticion no crezca sin limite;
    el proveedor ademas se queda con los ultimos seis.
    """

    pregunta: str = Field(min_length=2, max_length=500)
    historial: list[TurnoIn] = Field(default_factory=list, max_length=10)


class RespuestaOut(BaseModel):
    texto: str

    #: Los productos que la respuesta menciona, para enlazarlos.
    #:
    #: **Ya validados contra el catalogo**: un codigo que el modelo invente
    #: no llega hasta aca.
    productos: list[int] = Field(default_factory=list)


class DisponibleOut(BaseModel):
    """Si se puede conversar, y con que empezar si no se sabe que preguntar."""

    disponible: bool
    ejemplos: list[str] = Field(default_factory=list)
