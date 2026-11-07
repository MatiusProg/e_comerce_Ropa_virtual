"""P15 - Traspasos / CU-33, CU-34 y CU-35  |  capa: contratos"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Estado = Literal["SOLICITADO", "APROBADO", "ENVIADO", "RECIBIDO", "RECHAZADO"]


# --------------------------------------------------------------------------
#  CU-33 Solicitar traspaso
# --------------------------------------------------------------------------
class SolicitarTraspasoIn(BaseModel):
    """Lo que manda el encargado del destino, o el administrador.

    El ENCARGADO no manda `sucursal_destino_id`: es la suya, sale del token y
    no se acepta del cuerpo. El ADMINISTRADOR la manda siempre: ordena entre
    dos sucursales cualesquiera (RF-40).
    """

    variante_id: int = Field(ge=1)
    sucursal_origen_id: int = Field(ge=1)
    sucursal_destino_id: int | None = Field(default=None, ge=1)
    cantidad: int = Field(ge=1, le=10000)
    motivo: str | None = Field(default=None, max_length=200)
    #: CU-35: la orden sale de un traspaso sugerido. Solo cambia el tipo.
    desde_sugerencia: bool = False

    @model_validator(mode="after")
    def _origen_y_destino_distintos(self):
        if self.sucursal_destino_id is not None and (
            self.sucursal_destino_id == self.sucursal_origen_id
        ):
            raise ValueError("La sucursal de origen y la de destino son la misma.")
        return self


# --------------------------------------------------------------------------
#  CU-34 Atender traspaso
# --------------------------------------------------------------------------
class AprobarIn(BaseModel):
    #: El origen puede mandar menos de lo pedido si no le alcanza. Nunca más.
    cantidad: int | None = Field(default=None, ge=1, le=10000)


class RechazarIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=200)


# --------------------------------------------------------------------------
#  Lectura
# --------------------------------------------------------------------------
class SucursalBreve(BaseModel):
    id: int
    nombre: str


class TraspasoOut(BaseModel):
    id: int
    tipo: str
    estado: str
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    origen: SucursalBreve
    destino: SucursalBreve
    cantidad: int
    cantidad_solicitada: int
    motivo: str | None = None
    motivo_rechazo: str | None = None
    solicitado_por: str | None = None
    creado_en: datetime
    aprobado_por: str | None = None
    aprobado_en: datetime | None = None
    enviado_por: str | None = None
    enviado_en: datetime | None = None
    recibido_por: str | None = None
    recibido_en: datetime | None = None
    rechazado_por: str | None = None
    rechazado_en: datetime | None = None
    #: Lo que puede hacer QUIEN CONSULTA, ya resuelto por el servidor. La web
    #: muestra los botones con esto y no repite la regla.
    acciones: list[Literal["APROBAR", "RECHAZAR", "ENVIAR", "RECIBIR", "DEVOLVER"]] = []


class PaginaTraspasos(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[TraspasoOut]


class PrendaPedibleOut(BaseModel):
    """CU-33: una prenda que otra sucursal tiene, para elegir qué pedir."""

    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    #: Lo que suman las otras sucursales.
    disponible: int


class OrigenPosibleOut(BaseModel):
    """Una sucursal que tiene la prenda, para elegir a quién pedírsela."""

    sucursal_id: int
    sucursal: str
    disponible: int


# --------------------------------------------------------------------------
#  CU-35 Consultar traspasos sugeridos
# --------------------------------------------------------------------------
class PuntaSugerida(BaseModel):
    sucursal_id: int
    sucursal: str
    disponible: int
    #: Unidades vendidas en el período analizado.
    vendidas: int
    stock_minimo: int
    #: Lo que ya viene en camino (destino) o ya está comprometido (origen).
    en_traspaso: int


class TraspasoSugeridoOut(BaseModel):
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    origen: PuntaSugerida
    destino: PuntaSugerida
    cantidad_sugerida: int
    razon: str


class SugerenciasOut(BaseModel):
    dias: int
    generado_en: datetime
    items: list[TraspasoSugeridoOut]
