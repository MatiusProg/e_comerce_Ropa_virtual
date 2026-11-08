"""
P16 - Mis comprobantes / CU-46  |  capa: esquemas de entrada y salida (Pydantic)
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class ConsultaIn(BaseModel):
    """La frase del cliente, escrita o dictada."""

    texto: str = Field(min_length=2, max_length=300)


class CriterioOut(BaseModel):
    """Lo que se entendió, para que la pantalla lo muestre tal cual."""

    tipo: Literal["COMPRAS", "DEVOLUCIONES", "TODO"]
    cantidad: int | None
    desde: date | None
    hasta: date | None
    estado: str | None


class ComprobanteOut(BaseModel):
    """Un comprobante de la lista."""

    #: COMPRA (la venta y su recibo) o DEVOLUCION (la nota ND-…).
    tipo: Literal["COMPRA", "DEVOLUCION"]
    #: RECIBO, NOTA_DEVOLUCION o NOTA_CAMBIO; None si la compra todavía no se
    #: pagó y por lo tanto no tiene comprobante.
    documento: str | None
    #: El número del comprobante (R-00000042, ND-000007) o, si no tiene, el
    #: código del pedido.
    codigo: str
    #: El código de la venta a la que pertenece (VB-20261015-A3F2).
    referencia: str
    #: En hora de Bolivia (con su desfase, -04:00).
    fecha: datetime
    fecha_texto: str
    total: Decimal
    estado: str
    detalle: str | None = None
    #: El token firmado de la verificación pública. None si no hay comprobante.
    token: str | None = None
    #: La página pública que abre el QR.
    url_verificacion: str | None = None
    #: Si se puede bajar el PDF del recibo (`/tienda/compras/{referencia}/comprobante`).
    descargable: bool = False


class ConsultaOut(BaseModel):
    entendido: bool
    #: Siempre «reglas»: la consulta del cliente no gasta el cupo de IA de la tienda.
    interprete: Literal["reglas"] = "reglas"
    resumen: str | None = None
    motivo: str | None = None
    ejemplos: list[str] = []
    criterio: CriterioOut | None = None
    avisos: list[str] = []
    #: Cuántos cumplen el criterio (puede ser más que los mostrados).
    encontrados: int = 0
    items: list[ComprobanteOut] = []


class VerificacionOut(BaseModel):
    """Lo que muestra la página pública del QR. **Sin datos personales.**"""

    valido: bool = True
    tienda: str
    documento: str
    codigo: str
    referencia: str
    fecha: datetime
    fecha_texto: str
    total: Decimal
    estado: str


class QrOut(BaseModel):
    """La matriz del QR, para quien lo dibuja por su cuenta (el móvil)."""

    texto: str
    modulos: list[str]
