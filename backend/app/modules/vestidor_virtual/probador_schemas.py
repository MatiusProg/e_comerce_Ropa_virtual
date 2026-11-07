"""
P9 - Vestidor Virtual  |  capa: contratos (Pydantic)
2do parcial, 3ra presentacion: CU-36, CU-37 y CU-38.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.medidas.schemas import AjusteDeProducto
from app.modules.vestidor_virtual.schemas import EstadoDelProbador


class Punto(BaseModel):
    """Un punto de la imagen, relativo a su ancho y alto (0 = borde izquierdo/superior)."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class PuntosDePrenda(BaseModel):
    """Los tres puntos que calibran una imagen (CU-36).

    «Izquierdo» y «derecho» son como se VEN en la imagen, no los de quien
    llevaria puesta la prenda: es lo que el administrador ve al marcar.
    """

    hombro_izq: Punto
    hombro_der: Punto
    ruedo: Punto


# --- CU-36 · El administrador prepara la prenda -----------------------------

class ImagenParaPreparar(BaseModel):
    imagen_id: int
    url: str
    variante_id: int
    talla: str
    color: str
    puntos: PuntosDePrenda | None = None


class MedidaDeTalla(BaseModel):
    """Lo que mide LA PRENDA en una talla, con la holgura adentro. Mismos rangos que la base."""

    talla_id: int = Field(ge=1)
    busto_cm: Decimal = Field(ge=30, le=250, max_digits=5, decimal_places=1)
    cintura_cm: Decimal = Field(ge=30, le=250, max_digits=5, decimal_places=1)
    cadera_cm: Decimal = Field(ge=30, le=250, max_digits=5, decimal_places=1)
    largo_cm: Decimal = Field(ge=20, le=200, max_digits=5, decimal_places=1)


class TallaParaPreparar(BaseModel):
    talla_id: int
    codigo: str
    medidas: MedidaDeTalla | None = None


class PrendaParaPreparar(BaseModel):
    producto_id: int
    nombre: str
    imagenes: list[ImagenParaPreparar]
    tallas: list[TallaParaPreparar]
    #: True cuando ya se puede probar: al menos una imagen calibrada y todas
    #: las tallas con medidas.
    lista: bool
    #: Lo que falta, en palabras, para que la pantalla lo muestre tal cual.
    faltan: list[str]


class MedidasDelProducto(BaseModel):
    tallas: list[MedidaDeTalla] = Field(min_length=1, max_length=20)


class ProductoDelProbador(BaseModel):
    producto_id: int
    nombre: str
    activo: bool
    imagenes: int
    imagenes_calibradas: int
    tallas: int
    tallas_medidas: int
    lista: bool


# --- CU-37 · El cliente se prueba la prenda ---------------------------------

class PrendaDelProbador(BaseModel):
    """Una imagen calibrada que el cliente puede probarse."""

    variante_id: int
    talla_id: int
    talla: str
    color_id: int
    color: str
    imagen_url: str
    puntos: PuntosDePrenda


class MedidasDelCuerpo(BaseModel):
    busto_cm: Decimal
    altura_cm: Decimal | None = None


class PruebaDeProducto(BaseModel):
    producto_id: int
    nombre: str
    prendas: list[PrendaDelProbador]
    ajuste: AjusteDeProducto
    medidas: MedidasDelCuerpo | None = None
    #: Si se puede pedir la foto realista (CU-38): proveedor, plan y cupo.
    foto_ia: EstadoDelProbador


class SesionEntrada(BaseModel):
    variante_id: int = Field(ge=1)
    metodo: Literal["POSE", "MANUAL"]


class SesionSalida(BaseModel):
    id: int
    variante_id: int
    producto_id: int
    producto: str
    talla: str
    color: str
    metodo: str
    ajuste: str | None = None
    talla_recomendada: str | None = None
    foto_url: str | None = None
    foto_generada_por: str | None = None
    creado_en: datetime
