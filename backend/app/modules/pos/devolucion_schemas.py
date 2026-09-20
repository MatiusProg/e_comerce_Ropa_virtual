"""
P7 - Punto de Venta / CU-32  |  capa: contrato (Pydantic)

Registrar devolucion. Archivos propios dentro del paquete propio, con el mismo
patron que `carrito_*` en P7 y `consolidado_*` en P4: CU-31 y CU-32 son dos
casos de uso distintos y conviene poder leer cual es cual sin abrir el archivo.

QUE SIGNIFICA `monto` --- Y POR QUE NO ES SIEMPRE LO QUE VALE LA PRENDA
------------------------------------------------------------------------
`devolucion.monto` no es «el valor de lo devuelto»: es **lo que sale del
cajon**. Lo fija CU-30, que lo resta del monto esperado del turno:

    monto_esperado = apertura + efectivo cobrado - devoluciones

Si una venta se cobro con tarjeta y su devolucion sumara ahi, el arqueo
cerraria con un faltante que nadie puede explicar: esa plata nunca entro al
cajon, asi que tampoco puede salir de el. La devolucion de una venta con
tarjeta o QR **vuelve por donde vino**, y `monto` queda en cero.

Por eso el contrato saca dos numeros separados:

  `valor_devuelto`  lo que valen las prendas que volvieron, siempre
  `sale_del_cajon`  si ese dinero se entrega en billetes ahora mismo

La pantalla necesita los dos: decirle al cliente «son Bs 250» y decirle al
cajero «no los saque del cajon» son dos frases distintas y las dos hacen falta.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class LineaDevolvibleOut(BaseModel):
    """Una prenda de la venta y cuantas unidades todavia se pueden devolver."""

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    #: Lo que se vendio en esta venta.
    vendidas: int
    #: Lo que ya volvio en devoluciones anteriores.
    devueltas: int
    #: `vendidas - devueltas`. Es el tope de lo que se puede devolver hoy.
    devolvibles: int
    #: El precio CONGELADO de la venta, no el vigente. Se reintegra lo que se
    #: pago, no lo que la prenda cuesta hoy.
    precio_unitario: Decimal


class VentaDevolvibleOut(BaseModel):
    """La venta que se va a devolver, con lo que queda por devolver de ella."""

    codigo: str
    estado: str
    metodo_pago: str
    creado_en: datetime
    cliente: str | None
    total: Decimal
    #: Si el reintegro sale del cajon. Falso con tarjeta y QR.
    sale_del_cajon: bool
    lineas: list[LineaDevolvibleOut]


class LineaDevolucionIn(BaseModel):
    variante_id: int
    cantidad: int = Field(gt=0, le=1_000)


class DevolucionIn(BaseModel):
    """Lo que el cajero confirma al recibir una prenda de vuelta.

    `motivo` es obligatorio y no tiene valor por defecto: una devolucion sin
    motivo es una salida de mercaderia y de plata que nadie puede auditar
    despues. Dejarlo opcional garantiza que quede vacio siempre.
    """

    venta_codigo: str = Field(min_length=3, max_length=20)
    motivo: str = Field(min_length=3, max_length=200)
    lineas: list[LineaDevolucionIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _sin_variantes_repetidas(self) -> "DevolucionIn":
        # `detalle_devolucion` tiene UNIQUE (devolucion_id, variante_id), igual
        # que `detalle_venta`. Se rechaza antes, con el motivo.
        vistas = [linea.variante_id for linea in self.lineas]
        if len(vistas) != len(set(vistas)):
            raise ValueError(
                "La misma prenda aparece dos veces. Use la cantidad en vez de repetirla."
            )
        return self


class LineaDevueltaOut(BaseModel):
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


class DevolucionOut(BaseModel):
    """El comprobante de la devolucion."""

    id: int
    venta_codigo: str
    caja_nombre: str
    motivo: str
    creado_en: datetime

    lineas: list[LineaDevueltaOut]
    #: Lo que valen las prendas que volvieron. Siempre.
    valor_devuelto: Decimal
    #: Lo que efectivamente sale del cajon. Cero si se cobro con tarjeta o QR.
    monto: Decimal
    sale_del_cajon: bool
