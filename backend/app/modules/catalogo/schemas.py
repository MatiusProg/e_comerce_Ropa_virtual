"""
P3 - Catalogo / CU-10  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2
Caso de uso: CU-10 Gestionar productos y variantes

Regla: NUNCA se expone un modelo SQLAlchemy directamente. Por cada operacion se
define su esquema de entrada (Crear/Editar) y su esquema de salida (Out).

Las longitudes maximas replican la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md, que es el acuerdo de
nombres del ciclo.
"""
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

#: Tope del precio: NUMERIC(10,2) admite hasta 99.999.999,99. Validarlo aqui
#: devuelve un 422 que nombra el campo, en vez de un error crudo de PostgreSQL.
_PRECIO_MAXIMO = Decimal("99999999.99")


def _limpiar(valor: str) -> str:
    valor = valor.strip()
    if not valor:
        raise ValueError("El campo no puede quedar vacío.")
    return valor


# --- Variantes -----------------------------------------------------------

class VarianteOut(BaseModel):
    """Una combinacion talla x color. Es el SKU y la unidad de negocio (D1)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    talla_id: int
    color_id: int
    sku: str
    precio: Decimal
    activa: bool
    #: Se resuelven en el servidor para que la tabla de variantes se pueda
    #: mostrar sin que la interfaz tenga que cruzar los maestros a mano.
    talla_codigo: str | None = None
    color_nombre: str | None = None
    color_hexadecimal: str | None = None


class VarianteCrearIn(BaseModel):
    """Alta suelta de una variante (flujo alternativo 7a).

    `precio` es opcional: si no viene, el servicio copia el precio base del
    producto. Es lo mismo que hace la generacion masiva del paso 7.
    """

    talla_id: int
    color_id: int
    precio: Decimal | None = Field(default=None, gt=0, le=_PRECIO_MAXIMO)
    activa: bool = True


class VarianteEditarIn(BaseModel):
    """Edicion de una variante (flujo alternativo 7b).

    Solo el precio y el estado. La talla y el color NO se editan: cambiarlos
    convertiria la variante en otra distinta, con existencias y reservas ya
    apuntando a ella. Para eso se desactiva esta y se crea la que corresponda.
    """

    precio: Decimal | None = Field(default=None, gt=0, le=_PRECIO_MAXIMO)
    activa: bool | None = None


class GenerarVariantesIn(BaseModel):
    """Paso 7: generacion masiva del producto cartesiano talla x color.

    Las combinaciones que ya existen se omiten en silencio en vez de fallar: la
    restriccion uq_variante_producto_talla_color garantiza que no se dupliquen,
    y asi el Administrador puede volver a generar despues de agregar una talla
    sin tener que deseleccionar todo lo anterior.
    """

    tallas: list[int] = Field(min_length=1)
    colores: list[int] = Field(min_length=1)
    #: Si no viene, cada variante nace con el precio base del producto.
    precio: Decimal | None = Field(default=None, gt=0, le=_PRECIO_MAXIMO)


class GenerarVariantesOut(BaseModel):
    """Resultado de la generacion, para que la interfaz pueda explicarlo."""

    creadas: int
    omitidas: int
    variantes: list[VarianteOut]


# --- Productos -----------------------------------------------------------

class ProductoResumenOut(BaseModel):
    """Fila del listado del paso 2.

    No trae las variantes: un listado de cien productos con sus variantes
    dentro son miles de filas que nadie mira. El conteo alcanza para decidir si
    hay que entrar.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    categoria_id: int
    proveedor_id: int | None
    temporada_id: int | None
    coleccion_id: int | None
    precio_base: Decimal
    activo: bool
    categoria_nombre: str | None = None
    variantes_totales: int = 0
    variantes_activas: int = 0
    #: Cuantas imagenes tiene. Cero significa que en el catalogo sale sin foto.
    imagenes_totales: int = 0
    #: Cuantas de sus variantes ya tienen el PNG transparente del vestidor
    #: virtual. Viaja en el listado porque es la dependencia del prototipo de
    #: realidad aumentada (supuesto S5) y conviene poder ver de un vistazo
    #: cuanto falta, en vez de abrir producto por producto.
    variantes_con_vestidor: int = 0


class ProductoOut(ProductoResumenOut):
    """Detalle de un producto con sus variantes (pasos 3 a 7)."""

    descripcion: str | None = None
    variantes: list[VarianteOut] = []


class PaginaProductos(BaseModel):
    """Listado paginado.

    El total viaja aparte porque la interfaz necesita dibujar el paginador antes
    de saber cuantas paginas hay, y contar en el cliente exigiria traerlas todas.
    """

    total: int
    pagina: int
    tamano: int
    items: list[ProductoResumenOut]


class ProductoCrearIn(BaseModel):
    """Alta de un producto (pasos 4 a 6)."""

    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria_id: int
    proveedor_id: int | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None
    precio_base: Decimal = Field(gt=0, le=_PRECIO_MAXIMO)
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def _codigo_limpio(cls, valor: str) -> str:
        # El codigo se guarda en mayusculas para que "cam-001" y "CAM-001" no
        # entren los dos: el UNIQUE de PostgreSQL distingue mayusculas.
        return _limpiar(valor).upper()

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str) -> str:
        return _limpiar(valor)

    @field_validator("descripcion")
    @classmethod
    def _descripcion_limpia(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class ProductoEditarIn(BaseModel):
    """Edicion de un producto (flujo alternativo 3a).

    Todo opcional: se envia solo lo que cambia. Para temporada y coleccion se
    distingue «no enviado» de «enviado en null» con `model_fields_set`, porque
    mandarlas en null significa sacar el producto de la temporada o de la
    coleccion, que es una operacion legitima.
    """

    codigo: str | None = Field(default=None, min_length=1, max_length=30)
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria_id: int | None = None
    proveedor_id: int | None = None
    temporada_id: int | None = None
    coleccion_id: int | None = None
    precio_base: Decimal | None = Field(default=None, gt=0, le=_PRECIO_MAXIMO)

    @field_validator("codigo")
    @classmethod
    def _codigo_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _limpiar(valor).upper()

    @field_validator("nombre")
    @classmethod
    def _nombre_limpio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return _limpiar(valor)


class CambioEstadoIn(BaseModel):
    """Flujo alternativo 3b: desactivar sin borrar.

    Un producto desactivado deja de ofrecerse, pero se conserva en las
    existencias, reservas y ventas que ya lo referencian.
    """

    activo: bool
