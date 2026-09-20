"""
P12 - Bitacora / CU-42  |  contrato de la API
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AsientoOut(BaseModel):
    id: int

    #: El instante, **en hora boliviana**.
    #:
    #: Se convierte en el servidor y no en la pantalla. La web y el movil
    #: formatearian cada uno con la zona del aparato, y un telefono con la
    #: hora mal puesta mostraria una bitacora que no coincide con la de la
    #: computadora de al lado --- sobre un registro cuyo unico valor es que
    #: todos vean lo mismo.
    ocurrido_en: datetime

    usuario_id: int | None
    #: El correo tal como estaba cuando paso.
    actor: str | None
    #: El nombre completo, si la cuenta todavia existe.
    nombre: str | None
    rol: str | None

    accion: str
    entidad: str | None
    entidad_id: str | None

    metodo: str
    ruta: str
    estado_http: int
    exito: bool

    ip: str | None
    agente: str | None
    detalle: dict[str, Any] | None


class PaginaBitacoraOut(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[AsientoOut]


class OpcionesBitacoraOut(BaseModel):
    """Lo que hay realmente registrado, para armar los filtros.

    Ver `service.opciones`: sale de la tabla, no de una lista fija.
    """

    acciones: list[str] = Field(default_factory=list)
    entidades: list[str] = Field(default_factory=list)
