"""
P5 - Catalogo Publico / CU-17 y CU-18  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2
Casos de uso:
  CU-17 Consultar catalogo
  CU-18 Consultar ficha de producto

Regla: NUNCA se expone un modelo SQLAlchemy directamente.

Estos esquemas son la cara PUBLICA del catalogo y no son los de CU-10. La
diferencia no es cosmetica: la vitrina no muestra el proveedor, ni el precio
base, ni el estado activo, ni los conteos de gestion. Reutilizar `ProductoOut`
del router de Administrador filtraria al cliente quien abastece cada prenda y a
que precio entro.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# --- Piezas compartidas --------------------------------------------------

class ColorOut(BaseModel):
    """Un color, con su valor hexadecimal para dibujar la muestra."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    hexadecimal: str


class TallaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_prenda: str
    codigo: str
    orden: int


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    categoria_padre_id: int | None
    nombre: str


class TemporadaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class ColeccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    temporada_id: int
    nombre: str


# --- CU-17 · La vitrina --------------------------------------------------

class ProductoVitrinaOut(BaseModel):
    """Una tarjeta del listado.

    No trae las variantes. Un listado de veinte productos con sus variantes
    dentro son cientos de filas que la tarjeta no muestra; lo que necesita es el
    rango de precios, la foto y en que colores viene.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    categoria_id: int
    categoria_nombre: str | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None

    #: Extremos del precio de las variantes activas. Cuando coinciden, la
    #: interfaz muestra un precio solo; cuando no, muestra «desde».
    precio_desde: Decimal | None = None
    precio_hasta: Decimal | None = None

    #: URL de la imagen principal, ya prefijada por el servidor. Nula si el
    #: producto todavia no tiene fotos: la interfaz dibuja su marcador.
    imagen_url: str | None = None

    colores: list[ColorOut] = []

    #: Si alguna de sus variantes tiene el PNG transparente del vestidor. Viaja
    #: en el listado para poder rotular la tarjeta sin abrir la ficha.
    tiene_vestidor: bool = False


class PaginaVitrina(BaseModel):
    """Listado paginado de la vitrina.

    El total viaja aparte por lo mismo que en CU-10: la interfaz dibuja el
    paginador antes de saber cuantas paginas hay.
    """

    total: int
    pagina: int
    tamano: int
    items: list[ProductoVitrinaOut]


# --- CU-18 · La ficha ----------------------------------------------------

class ImagenVitrinaOut(BaseModel):
    """Una foto de la galeria. Sin `ruta`: al cliente le sirve la URL, no donde
    esta guardado el archivo en el volumen."""

    id: int
    url: str
    variante_id: int | None = None
    es_principal: bool = False
    orden: int = 0


class VarianteVitrinaOut(BaseModel):
    """Una combinacion talla x color ofrecible, con su precio propio.

    `imagen_vestidor_url` es la mitad de la costura C5: es el PNG con fondo
    transparente de ESTA variante, el activo del que depende el vestidor
    virtual (supuesto S5). Viaja en la ficha para que la pantalla de realidad
    aumentada reciba todo lo que necesita al navegar y no tenga que volver a
    consultar la API ni conocer la tabla de imagenes.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    precio: Decimal
    talla_id: int
    talla_codigo: str | None = None
    color_id: int
    color_nombre: str | None = None
    color_hexadecimal: str | None = None
    imagen_vestidor_url: str | None = None


class FichaProductoOut(BaseModel):
    """El detalle del paso 3 de CU-18.

    Trae las variantes ofrecibles y, aparte, las tallas y los colores en los que
    se ofrece. Los dos ultimos son derivables de la lista de variantes, pero
    derivarlos en cada cliente --- web y movil --- es escribir dos veces la misma
    logica y arriesgar que difieran.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_id: int
    categoria_nombre: str | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None

    precio_desde: Decimal | None = None
    precio_hasta: Decimal | None = None

    imagenes: list[ImagenVitrinaOut] = []
    variantes: list[VarianteVitrinaOut] = []
    tallas: list[TallaOut] = []
    colores: list[ColorOut] = []

    #: Verdadero si al menos una variante tiene su PNG transparente. Es lo que
    #: habilita el boton «Probar en vestidor virtual» de la ficha movil.
    tiene_vestidor: bool = False


# --- Opciones de filtrado ------------------------------------------------

class FiltrosOut(BaseModel):
    """Todo lo que la vitrina necesita para dibujar su panel de filtros.

    Va en un solo endpoint y no en cinco: son cinco listas cortas que la pantalla
    pide siempre juntas al abrirse, y cinco peticiones en el arranque del movil
    se notan.
    """

    categorias: list[CategoriaOut] = []
    tallas: list[TallaOut] = []
    colores: list[ColorOut] = []
    temporadas: list[TemporadaOut] = []
    colecciones: list[ColeccionOut] = []
    precio_min: Decimal | None = None
    precio_max: Decimal | None = None
