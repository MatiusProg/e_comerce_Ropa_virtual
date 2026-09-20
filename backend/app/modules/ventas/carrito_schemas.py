"""
P7 - Ventas y Punto de Venta / CU-26  |  capa: esquemas (Pydantic)

Ciclo de desarrollo: 3
Caso de uso: CU-26 Gestionar carrito de compras

Regla: NUNCA se expone un modelo SQLAlchemy directamente.
"""
from decimal import Decimal

from pydantic import BaseModel, Field

from app.modules.catalogo.promociones_schemas import DescuentoOut

#: Tope de unidades por linea. No sale de una regla de negocio escrita: existe
#: para que un dedo apoyado en el boton de sumar no deje un carrito con miles de
#: unidades que despues hay que validar contra el inventario. Si alguna vez hace
#: falta pedir mas, es un pedido mayorista y no este caso de uso.
CANTIDAD_MAXIMA = 20


class LineaCarritoOut(BaseModel):
    """Una prenda del carrito, con lo que hace falta para pintarla y decidir.

    Los datos del producto vienen resueltos --- nombre, talla, color, imagen ---
    porque una pantalla de carrito que tuviera que pedir la ficha de cada linea
    haria una consulta por prenda.
    """

    variante_id: int
    producto_id: int
    sku: str
    producto_nombre: str
    talla_codigo: str | None
    color_nombre: str | None
    color_hexadecimal: str | None
    imagen_url: str | None

    cantidad: int
    #: Precio VIGENTE de la variante, no el que tenia al agregarla. El carrito
    #: no guarda precios: ver el modelo.
    #:
    #: Es el precio SIN descuento. La promocion viaja aparte, en `descuento`,
    #: en vez de venir ya restada: el cliente tiene que ver de cuanto era y
    #: cuanto paga, que es lo que vuelve creible la oferta. Un solo numero ya
    #: rebajado se lee como «este es el precio» y la promocion no existe.
    precio_unitario: Decimal
    #: La promocion vigente que gano para esta prenda, o nada (CU-12).
    descuento: DescuentoOut | None = None
    #: Ya con el descuento aplicado: `(precio - descuento) * cantidad`.
    subtotal: Decimal

    #: `false` si la prenda dejo de ofrecerse despues de agregarla --- producto
    #: o variante desactivados ---. La linea NO se borra sola: el cliente tiene
    #: que ver que estaba ahi y sacarla el, o entender por que bajo el total.
    #: No suma al total.
    disponible: bool
    #: Unidades que hay en toda la red. Es un aviso, no una reserva: el carrito
    #: no inmoviliza inventario y la validacion de verdad es de CU-27.
    stock_total: int


class CarritoOut(BaseModel):
    """El carrito completo (paso 2 del flujo principal).

    Un carrito vacio NO es un 404: es un carrito con cero lineas. La diferencia
    importa porque la pantalla tiene que poder pintarse antes de que el cliente
    agregue nada, sin tratar el caso normal como un error.
    """

    lineas: list[LineaCarritoOut]
    #: Cuantas prendas distintas. Es lo que va en la burbuja del icono.
    items: int
    #: Cuantas unidades en total, sumando cantidades.
    unidades: int
    #: Suma de los subtotales de las lineas DISPONIBLES.
    total: Decimal
    #: Cuantas lineas dejaron de ofrecerse. Si es mayor que cero la pantalla lo
    #: dice arriba: el cliente tiene que enterarse de por que su total bajo.
    no_disponibles: int


class AgregarAlCarritoIn(BaseModel):
    """Paso 3: agregar una prenda.

    SUMA a lo que ya hubiera de esa variante. Es lo que espera quien pulsa
    «Agregar» dos veces desde la ficha del producto: la segunda vez no reemplaza
    la primera.
    """

    variante_id: int
    cantidad: int = Field(default=1, ge=1, le=CANTIDAD_MAXIMA)


class CambiarCantidadIn(BaseModel):
    """Flujo alternativo 3a: el selector de cantidad del carrito.

    FIJA la cantidad, no la suma. Es la operacion contraria a agregar y va por
    otro verbo a proposito: un mismo endpoint que a veces suma y a veces fija
    seria imposible de usar sin mirar el codigo.
    """

    cantidad: int = Field(ge=1, le=CANTIDAD_MAXIMA)
