"""
P15 - Devoluciones por la web / CU-24  |  capa: contrato (Pydantic)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# =====================================================================
# Precondición: entregar el pedido (encargado)
# =====================================================================

class PedidoDeSucursalOut(BaseModel):
    codigo: str
    estado: str
    modalidad_entrega: str | None
    cliente: str | None
    total: Decimal
    unidades: int
    creado_en: datetime
    entregado_en: datetime | None


# =====================================================================
# CU-24: lo que el cliente puede pedir
# =====================================================================

class OpcionDeCambioOut(BaseModel):
    """La misma prenda en otra talla o color, con lo que hay en la sucursal."""

    variante_id: int
    sku: str
    talla: str
    color: str
    precio: Decimal
    disponible: int


class LineaDevolvibleWebOut(BaseModel):
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    vendidas: int
    #: Lo que ya volvió o ya está pedido en otra solicitud abierta.
    comprometidas: int
    devolvibles: int
    precio_pagado: Decimal
    opciones_de_cambio: list[OpcionDeCambioOut]


class PedidoDevolvibleOut(BaseModel):
    codigo: str
    sucursal: str
    entregado_en: datetime
    ventana_horas: int
    vence_en: datetime
    dentro_de_plazo: bool
    lineas: list[LineaDevolvibleWebOut]


class LineaSolicitudIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=1_000)
    #: Solo en un CAMBIO: la variante que se quiere a cambio.
    variante_nueva_id: int | None = None


class SolicitudIn(BaseModel):
    venta_codigo: str = Field(min_length=3, max_length=20)
    tipo: Literal["DEVOLUCION", "CAMBIO"]
    motivo: str = Field(min_length=5, max_length=300)
    lineas: list[LineaSolicitudIn] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def _coherente(self) -> "SolicitudIn":
        vistas = [l.variante_id for l in self.lineas]
        if len(vistas) != len(set(vistas)):
            raise ValueError("La misma prenda aparece dos veces.")
        for l in self.lineas:
            if self.tipo == "CAMBIO" and l.variante_nueva_id is None:
                raise ValueError("En un cambio, cada prenda dice por cuál se cambia.")
            if self.tipo == "DEVOLUCION" and l.variante_nueva_id is not None:
                raise ValueError("Una devolución no lleva prenda a cambio.")
        return self


class LineaSolicitudOut(BaseModel):
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_pagado: Decimal
    variante_nueva_id: int | None
    talla_nueva: str | None
    color_nueva: str | None
    precio_nuevo: Decimal | None


class SolicitudOut(BaseModel):
    id: int
    venta_codigo: str
    sucursal: str
    cliente: str
    tipo: str
    estado: str
    motivo: str
    respuesta: str | None
    creado_en: datetime
    atendida_en: datetime | None
    lineas: list[LineaSolicitudOut]
    #: Lo que valen las prendas que vuelven, a lo que se pagó.
    valor_devuelto: Decimal
    #: En un cambio: lo que valen las nuevas hoy, y la diferencia (+ paga el
    #: cliente, - devuelve la tienda). Se salda al retirar, en caja.
    valor_nuevo: Decimal | None
    diferencia: Decimal | None
