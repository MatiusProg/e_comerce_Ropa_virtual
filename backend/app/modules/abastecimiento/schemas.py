"""P4 - Inventario / CU-39  |  capa: contratos"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AnunciarIn(BaseModel):
    variante_id: int = Field(ge=1)
    cantidad: int = Field(ge=1, le=100000)
    #: 0 es valido: «lo tengo ahora». 365 es el tope de lo creible.
    dias_plazo: int = Field(ge=0, le=365)
    observacion: str | None = Field(default=None, max_length=200)


class AnuncioOut(BaseModel):
    id: int
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    cantidad: int
    dias_plazo: int
    observacion: str | None = None
    estado: str
    creado_en: datetime

    #: Cuanto de lo anunciado ya entro al inventario, y cuanto falta.
    #:
    #: ES LA DEVOLUCION QUE EL PROVEEDOR NO TENIA. Anunciaba y despues no se
    #: enteraba de nada: el aviso quedaba «ANUNCIADO» para siempre aunque la
    #: mercaderia hubiera llegado hacia semanas. Ahora ve «ingresaron 30 de
    #: 45» sin tener que llamar por telefono.
    cantidad_recibida: int = 0
    cantidad_pendiente: int = 0

    #: Cuando se completo. Nulo mientras siga en camino.
    recibido_en: datetime | None = None


class VarianteAnunciableOut(BaseModel):
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
