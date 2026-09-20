"""
P7 - Punto de Venta / CU-31  |  capa: contrato (Pydantic)

Registrar venta presencial. La ficha del caso de uso pide dos caminos de
entrada --- «buscando las variantes **o** cargando una reserva ya atendida» ---,
cobro en efectivo o tarjeta, comprobante y descuento de inventario.

PAQUETE PROPIO, NO ARCHIVOS DENTRO DE `ventas/`
-----------------------------------------------
CU-30 estreno `app/modules/caja/` como paquete aparte en vez de meterse en
`ventas/`. CU-31 sigue esa misma linea: el punto de venta es un paquete, y asi
`ventas/` ---que es de CU-27, de Mateo--- no se toca en ningun archivo. Es el
grado mas fuerte de la convencion de no pisarse: ni siquiera archivos propios
dentro del paquete ajeno, sino un paquete propio al lado.

EL DINERO VIAJA COMO `Decimal`, NUNCA COMO `float`
---------------------------------------------------
Pydantic lo serializa como cadena y el cliente lo formatea. Un `float` de 0.1 +
0.2 en un recibo es un centavo que no cuadra, y el arqueo de CU-30 lo va a
encontrar al cierre del turno.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.catalogo.promociones_schemas import DescuentoOut

#: Como se cobra en el mostrador. Es el mismo conjunto que
#: `ventas.models.METODOS_PAGO`, que es lo que el CHECK `ck_venta_metodo_pago`
#: acepta y lo que el arqueo de CU-30 sabe leer.
#:
#: `QR` esta porque en Bolivia el pago con codigo QR bancario es corriente y
#: **no es efectivo**: no entra al cajon. Meterlo dentro de EFECTIVO
#: descuadraria el turno por cada uno.
MetodoDePago = Literal["EFECTIVO", "TARJETA", "QR"]


# =====================================================================
# Buscar que vender
# =====================================================================

class PrendaEnMostradorOut(BaseModel):
    """Una prenda que se puede vender ahora mismo en esta sucursal.

    Lleva **el precio y el disponible juntos** porque el cajero decide con los
    dos a la vez: sin precio no puede cobrar y sin saldo no puede entregar.
    Pedirlos en dos consultas obligaria a la pantalla a cruzarlos y a decidir
    que hacer cuando una de las dos llega y la otra no.
    """

    model_config = ConfigDict(from_attributes=True)

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    #: El precio VIGENTE de la variante, SIN descuento. Se congela recien al
    #: vender, en `detalle_venta.precio_unitario`.
    precio: Decimal
    #: La promocion vigente que gano para esta prenda, o nada (CU-12).
    #:
    #: **Tiene que viajar hasta el mostrador.** La pantalla arma su total con
    #: estos precios y lo manda como `total_esperado`; si no supiera del
    #: descuento, su total seria mayor que el del servidor y CU-31 rechazaria
    #: con 409 *toda* venta de una prenda en promocion.
    descuento: DescuentoOut | None = None
    disponible: int


class PaginaDePrendas(BaseModel):
    """Lo que se puede vender, paginado.

    El total viaja aparte por el mismo motivo que en CU-14: el paginador se
    dibuja antes de tener las filas.
    """

    total: int
    pagina: int
    tamano: int
    items: list[PrendaEnMostradorOut]


# =====================================================================
# Cargar una reserva atendida (el puente de D2)
# =====================================================================

class LineaDeReservaOut(BaseModel):
    """Una prenda que el cliente se llevo de su reserva, con su precio de hoy."""

    model_config = ConfigDict(from_attributes=True)

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    #: Precio de lista. El descuento va aparte, como en la busqueda.
    precio: Decimal
    descuento: DescuentoOut | None = None
    #: Ya con el descuento aplicado.
    subtotal: Decimal


class ReservaPorCobrarOut(BaseModel):
    """Una reserva ya atendida cuyo cobro todavia no se registro.

    Solo trae las lineas con `resultado_prueba = 'LLEVA'`: lo que el cliente
    devolvio a la percha no se cobra, y mostrarlo invitaria a cobrarlo.
    """

    reserva_id: int
    cliente: str
    atendida_en: datetime
    lineas: list[LineaDeReservaOut]
    total: Decimal


# =====================================================================
# Registrar la venta
# =====================================================================

class LineaVentaIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=1_000)


class VentaPresencialIn(BaseModel):
    """Lo que el cajero confirma al cobrar.

    NO LLEVA `sucursal_id` NI `turno_caja_id`, A PROPOSITO
    ------------------------------------------------------
    Son datos de ambito y la convencion 2 del ciclo dice que un dato de ambito
    **no se acepta y se comprueba: no se acepta**. Los dos salen del turno
    abierto de quien esta cobrando. Aceptarlos abriria la puerta a que un
    cajero de Centro imputara una venta a la caja de Norte, y el arqueo de esa
    otra caja cerraria con un sobrante que nadie puede explicar.

    `cliente_id` si podria venir --- no es ambito, es quien compra --- pero
    tampoco se acepta: en el camino de busqueda libre la venta es **anonima**,
    que es lo que el modelo dice («quien entra, paga y se va no tiene por que
    dejar sus datos»), y en el camino de la reserva el cliente sale de la
    reserva, que es la fuente correcta.
    """

    metodo_pago: MetodoDePago

    #: Camino A: el cajero busco las prendas y las fue sumando.
    lineas: list[LineaVentaIn] = Field(default_factory=list)

    #: Camino B: se carga una reserva ya atendida. Excluyente con `lineas`.
    reserva_id: int | None = None

    #: Lo que la pantalla mostro. Si el precio cambio en el medio, se avisa en
    #: vez de cobrar callado --- misma decision que en CU-27.
    total_esperado: Decimal | None = Field(default=None, ge=0)

    #: Con cuanto paga el cliente, para calcular el vuelto. **No se guarda**:
    #: no hay columna donde ponerlo y inventarla para un numero que solo sirve
    #: durante treinta segundos en el mostrador seria cargar el esquema.
    monto_recibido: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _un_solo_camino(self) -> "VentaPresencialIn":
        if bool(self.lineas) == (self.reserva_id is not None):
            raise ValueError(
                "Envíe líneas sueltas o una reserva, no las dos cosas ni ninguna."
            )
        return self

    @model_validator(mode="after")
    def _sin_variantes_repetidas(self) -> "VentaPresencialIn":
        # `detalle_venta` tiene UNIQUE (venta_id, variante_id): dos lineas de la
        # misma prenda reventarian con un error de integridad que el cajero
        # leeria como «error del sistema». Se rechaza antes, con el motivo.
        vistas = [linea.variante_id for linea in self.lineas]
        if len(vistas) != len(set(vistas)):
            raise ValueError(
                "La misma prenda aparece dos veces. Use la cantidad en vez de repetirla."
            )
        return self


class LineaVendidaOut(BaseModel):
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    #: CONGELADO. Es lo que dice el comprobante y no vuelve a cambiar.
    precio_unitario: Decimal
    subtotal: Decimal


class VentaPresencialOut(BaseModel):
    """El ticket: lo que se vendio, con que se pago y que comprobante salio."""

    codigo: str
    estado: str
    metodo_pago: str
    sucursal_nombre: str
    caja_nombre: str
    #: Nulo en una venta anonima, que es el caso corriente del mostrador.
    cliente: str | None
    #: La reserva que se cobro, si vino de una.
    reserva_id: int | None

    lineas: list[LineaVendidaOut]
    subtotal: Decimal
    descuento: Decimal
    total: Decimal

    #: Solo si el cajero lo informo, y solo con EFECTIVO.
    monto_recibido: Decimal | None
    vuelto: Decimal | None

    comprobante_numero: str
    creado_en: datetime
