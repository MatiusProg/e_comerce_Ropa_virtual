"""
P7 - Ventas y POS / CU-30  |  capa: contratos
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CajaOut(BaseModel):
    id: int
    nombre: str

    #: Si otra persona la tiene abierta. Se informa en vez de esconder la
    #: caja: el cajero necesita saber que existe y esta ocupada, no que
    #: desaparecio.
    ocupada: bool


class AbrirTurnoIn(BaseModel):
    caja_id: int = Field(ge=1)
    #: Lo que hay en el cajon al empezar. Puede ser cero.
    monto_apertura: Decimal = Field(ge=0, le=999999)


class CerrarTurnoIn(BaseModel):
    #: Lo que la persona CONTO. No se compara con nada antes de guardarlo: el
    #: arqueo es justamente la diferencia, y rechazar un conteo que no cuadra
    #: seria impedir registrar el problema que hay que registrar.
    monto_cierre: Decimal = Field(ge=0, le=999999)


class LineaDeArqueoOut(BaseModel):
    metodo: str
    ventas: int
    total: Decimal


class TurnoOut(BaseModel):
    id: int
    caja_id: int
    caja_nombre: str
    sucursal_nombre: str
    abierto_en: datetime
    cerrado_en: datetime | None = None

    monto_apertura: Decimal

    #: Lo que entro al cajon en efectivo durante el turno.
    efectivo_cobrado: Decimal
    #: Lo que salio por devoluciones (CU-32). Cero mientras no exista.
    devoluciones: Decimal
    #: `apertura + efectivo - devoluciones`. Lo que el sistema dice que hay.
    monto_esperado: Decimal

    #: Lo que la persona conto. Nulo mientras el turno sigue abierto.
    monto_cierre: Decimal | None = None
    #: `contado - esperado`. Positivo es que sobra. Nulo hasta cerrar.
    diferencia: Decimal | None = None

    #: El desglose por metodo, para que el cierre se pueda revisar.
    por_metodo: list[LineaDeArqueoOut] = []
