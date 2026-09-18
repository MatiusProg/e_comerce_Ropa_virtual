"""CU-21 · Contratos de las medidas y del ajuste por talla."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MedidasEntrada(BaseModel):
    """Lo que el cliente carga de su cuerpo.

    Los rangos son los mismos CHECK que tiene la tabla, a proposito: aca dan un
    422 con un mensaje que se puede mostrar, y en la base son la red que atrapa
    lo que entre por otro camino. Si solo estuvieran en un lado, el otro seria
    el que falla feo.
    """

    busto_cm: Decimal = Field(ge=50, le=200)
    cintura_cm: Decimal = Field(ge=40, le=200)
    cadera_cm: Decimal = Field(ge=50, le=200)
    altura_cm: Decimal | None = Field(default=None, ge=100, le=230)


class MedidasSalida(MedidasEntrada):
    model_config = ConfigDict(from_attributes=True)


class AjusteDeTalla(BaseModel):
    """Como le queda UNA talla a quien pregunta, y como hay que dibujarla."""

    talla_id: int
    codigo: str
    busto_cm: Decimal
    cintura_cm: Decimal
    cadera_cm: Decimal
    largo_cm: Decimal

    #: NO_ENTRA · AJUSTADA · A_TU_MEDIDA · HOLGADA · MUY_HOLGADA.
    #: Va como codigo y no como texto listo para mostrar porque el telefono y
    #: la web lo escriben distinto, y porque un texto en la API se vuelve
    #: imposible de traducir despues sin romper a quien ya lo muestra.
    ajuste: str

    #: Cuanto ensanchar o angostar la prenda al dibujarla. 1.0 = la talla que
    #: corresponde al cuerpo, que se dibuja como se dibujaba siempre.
    factor_ancho: float

    #: Lo mismo para el largo. Es lo que hace que una XS se vea CORTA.
    factor_largo: float


class AjusteDeProducto(BaseModel):
    """La respuesta de `/tienda/productos/{id}/ajuste`.

    Trae TODAS las tallas y no solo la recomendada porque el vestidor deja
    cambiar de talla sin volver a pedir nada al servidor: con la lista entera,
    pasar de M a L es instantaneo.
    """

    producto_id: int

    #: False cuando el cliente todavia no cargo sus medidas. La pantalla
    #: entonces dibuja como siempre y ofrece cargarlas; no es un error.
    hay_medidas: bool

    #: False cuando el producto no tiene tabla de tallas --- pantalones,
    #: carteras, cinturones. Tambien se dibuja como siempre.
    hay_tabla: bool

    talla_recomendada_id: int | None = None
    talla_recomendada: str | None = None

    tallas: list[AjusteDeTalla] = []
