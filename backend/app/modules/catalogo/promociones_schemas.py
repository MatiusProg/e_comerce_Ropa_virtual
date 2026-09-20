"""
P3 - Catalogo / CU-12  |  capa: contrato (Pydantic)

Gestionar promociones. Archivos propios dentro del paquete ajeno, con el mismo
patron que `temporadas_*` e `imagenes_*`.

EL DINERO VIAJA COMO `Decimal`
-------------------------------
Tanto el porcentaje como el precio ya descontado. Un `float` de 12,5 % sobre
Bs 249,90 da un centavo que no cuadra, y ese centavo termina en el arqueo del
turno de CU-30.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: Los tres alcances del RF35.
Alcance = Literal["PRODUCTO", "CATEGORIA", "TEMPORADA"]


# =====================================================================
# Lo que el Administrador carga
# =====================================================================

class PromocionCrearIn(BaseModel):
    """Alta de una promocion.

    `objetivo_id` es UNO solo y su significado lo da `alcance`. Se prefirio eso
    a tres campos nulables ---`producto_id`, `categoria_id`, `temporada_id`---
    porque desde la pantalla el Administrador elige primero *sobre que* y
    despues *cual*: son dos preguntas, no tres campos de los que hay que dejar
    dos vacios. El servicio lo abre en la columna que corresponde, que es donde
    la base puede garantizarlo con una clave foranea.
    """

    nombre: str = Field(min_length=2, max_length=80)
    alcance: Alcance
    objetivo_id: int = Field(gt=0)
    #: (0, 100]. Con dos decimales porque «12,5 %» es corriente.
    porcentaje: Decimal = Field(gt=0, le=100, decimal_places=2)
    desde: date
    #: Nulo = sin fecha de fin.
    hasta: date | None = None
    activa: bool = True

    @field_validator("nombre")
    @classmethod
    def _recortar(cls, valor: str) -> str:
        return valor.strip()

    @model_validator(mode="after")
    def _vigencia_coherente(self) -> "PromocionCrearIn":
        # El CHECK de la base lo rechaza igual, pero un error de integridad
        # llega como «error del sistema» y este llega como una frase que el
        # Administrador puede corregir.
        if self.hasta is not None and self.hasta < self.desde:
            raise ValueError("La fecha de fin no puede ser anterior a la de inicio.")
        return self


class PromocionEditarIn(BaseModel):
    """Edicion parcial. Lo que no viene, no cambia.

    **El alcance y el objetivo no se editan.** Cambiarle el alcance a una
    promocion viva es otra promocion: la que estaba corriendo alcanzaba otras
    prendas, y los pedidos que ya se cobraron con ella quedarian explicados por
    una regla que ya no dice lo mismo. Para eso se desactiva esta y se crea
    otra, que ademas deja rastro de las dos.
    """

    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    porcentaje: Decimal | None = Field(default=None, gt=0, le=100, decimal_places=2)
    desde: date | None = None
    hasta: date | None = None
    #: Para borrar la fecha de fin hay que decirlo: `hasta=None` no alcanza,
    #: porque en una edicion parcial «no vino» y «vino en nulo» son lo mismo.
    quitar_hasta: bool = False

    @field_validator("nombre")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        return valor.strip() if valor else valor


class CambioEstadoIn(BaseModel):
    activa: bool


# =====================================================================
# Lo que sale
# =====================================================================

class PromocionOut(BaseModel):
    """Una promocion, con su objetivo ya nombrado y si hoy esta descontando."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    alcance: Alcance
    objetivo_id: int
    #: «Camisas», «Verano 2026», «Camisa Oxford manga larga». Resuelto en el
    #: servidor porque «la categoria 4» no le dice nada a nadie.
    objetivo_nombre: str
    porcentaje: Decimal
    desde: date
    hasta: date | None
    activa: bool

    #: Si HOY descuenta. No es lo mismo que `activa`: una promocion activa que
    #: empieza el mes que viene no esta descontando nada, y la lista tiene que
    #: poder distinguirlas o el Administrador cree que algo esta roto.
    vigente: bool


class PaginaPromociones(BaseModel):
    total: int
    pagina: int
    tamano: int
    items: list[PromocionOut]


class DescuentoOut(BaseModel):
    """El descuento que se le esta aplicando a una prenda, y por que.

    Viaja el NOMBRE de la promocion y no solo el porcentaje: el cliente que ve
    «−20 %» sin saber de que se pregunta si es un error, y el cajero que tiene
    que explicarlo en el mostrador necesita poder leerlo.
    """

    model_config = ConfigDict(from_attributes=True)

    promocion_id: int
    nombre: str
    porcentaje: Decimal
    #: Lo que se descuenta POR UNIDAD, en dinero y ya redondeado a dos
    #: decimales. Viaja calculado porque la regla ---como se redondea--- es del
    #: negocio: si cada pantalla la dedujera por su cuenta, la web y el movil
    #: mostrarian precios distintos de la misma prenda.
    monto_unitario: Decimal
    #: `precio - monto_unitario`. Es lo que se cobra.
    precio_final: Decimal
