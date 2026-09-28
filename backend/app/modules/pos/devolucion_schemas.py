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

    # --- El plazo (0020) ---------------------------------------------------
    #
    # Los tres viajan aunque el servicio ya rechace lo que esta vencido: la
    # pantalla tiene que poder decir «le quedan 9 horas» ANTES de que el cajero
    # arme la devolucion entera y reciba un 409. Un plazo que solo se descubre
    # al confirmar hace perder el trabajo hecho y ademas deja al cajero
    # discutiendo con el cliente sin un numero que mostrarle.
    #: Los dias que la tienda da para volver. Es politica, no constante.
    plazo_dias: int
    #: El instante exacto en que se cierra. `creado_en + plazo_dias`.
    vence_en: datetime
    #: Si HOY todavia se puede devolver o cambiar contra esta venta.
    dentro_de_plazo: bool


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


# =====================================================================
# El segundo flujo: el cambio de prenda (0020)
# =====================================================================
#
# POR QUE EL CAMBIO NO ES «UNA DEVOLUCION Y DESPUES UNA VENTA»
# -------------------------------------------------------------
# Podria armarse llamando a CU-32 y despues a CU-31 desde la pantalla, sin una
# sola linea de backend nueva. No se hace, por tres motivos que el mostrador
# nota:
#
# 1. **No seria atomico.** Entre las dos llamadas se puede caer la red o
#    agotarse el stock de la prenda nueva, y el cliente queda sin la vieja
#    ---ya reingresada--- y sin la nueva.
# 2. **El cajon quedaria mal.** La devolucion sacaria Bs 200 y la venta metria
#    Bs 250, cuando lo que paso sobre el mostrador fue que el cliente puso 50.
#    El arqueo daria el mismo total, pero el desglose mentiria, y el cajero
#    contaria billetes que nunca movio.
# 3. **Se perderia el vinculo.** Nada diria que esa venta salio de ese cambio,
#    y ni el tablero ni la bitacora podrian reconstruirlo despues.


class LineaLlevadaIn(BaseModel):
    """Una prenda que el cliente se lleva a cambio."""

    variante_id: int
    cantidad: int = Field(gt=0, le=1_000)


class CambioIn(BaseModel):
    """Lo que el cajero confirma al cambiar una prenda por otra.

    `metodo_diferencia` es OPCIONAL en el contrato y OBLIGATORIO cuando hay
    diferencia que saldar, y esa asimetria es a proposito: el precio final lo
    fija el servidor ---las promociones de CU-12 se leen al cobrar, no antes---
    asi que la pantalla no puede saber con certeza si va a haber diferencia.
    Exigirlo siempre obligaria a mandar un metodo inventado en los cambios que
    salen parejos, y ese metodo terminaria en la base diciendo que se movio
    plata que no se movio.
    """

    venta_codigo: str = Field(min_length=3, max_length=20)
    motivo: str = Field(min_length=3, max_length=200)
    #: Lo que vuelve. Mismo contrato que una devolucion pura.
    devueltas: list[LineaDevolucionIn] = Field(min_length=1)
    #: Lo que se lleva. Al menos una: un cambio sin prenda nueva es una
    #: devolucion, y tiene su propio endpoint.
    llevadas: list[LineaLlevadaIn] = Field(min_length=1)
    #: Como se salda la diferencia, si la hay.
    metodo_diferencia: str | None = None
    #: Guarda contra un precio movido, igual que `total_esperado` en CU-31: si
    #: la pantalla calculo una diferencia y el servidor otra, se rechaza en vez
    #: de cobrar callado un numero que el cliente no vio.
    diferencia_esperada: Decimal | None = None

    @model_validator(mode="after")
    def _sin_variantes_repetidas(self) -> "CambioIn":
        for nombre, lineas in (("devueltas", self.devueltas), ("llevadas", self.llevadas)):
            vistas = [linea.variante_id for linea in lineas]
            if len(vistas) != len(set(vistas)):
                raise ValueError(
                    f"En «{nombre}» la misma prenda aparece dos veces."
                    " Use la cantidad en vez de repetirla."
                )
        return self


class LineaLlevadaOut(BaseModel):
    """Una prenda que salio en el cambio, al precio con que se registro."""

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    precio_unitario: Decimal
    #: Lo que CU-12 descontó, congelado junto con el precio.
    descuento_unitario: Decimal
    subtotal: Decimal


class CambioOut(BaseModel):
    """El comprobante del cambio: lo que volvio, lo que salio y la diferencia."""

    id: int
    #: La venta original, la que trajo la prenda devuelta.
    venta_codigo: str
    #: La venta NUEVA que se genero con lo que se llevo. Tiene su comprobante y
    #: aparece en los reportes como cualquier otra: la prenda se vendio.
    venta_nueva_codigo: str
    comprobante_numero: str
    caja_nombre: str
    motivo: str
    creado_en: datetime

    devueltas: list[LineaDevueltaOut]
    #: Lo que valia lo devuelto, a precio congelado de la venta original.
    valor_devuelto: Decimal

    llevadas: list[LineaLlevadaOut]
    #: Lo que vale lo que se lleva, a precio de hoy y con las promociones de hoy.
    total_llevado: Decimal

    #: `total_llevado - valor_devuelto`, CON SIGNO.
    diferencia: Decimal
    #: CLIENTE si el cliente puso plata, TIENDA si la puso la tienda, NADIE si
    #: el cambio salio parejo. Es lo que la pantalla lee para elegir el texto:
    #: «cobrar Bs 50» y «entregar Bs 50» no se pueden confundir.
    a_favor_de: str
    metodo_diferencia: str | None
    #: Si esa diferencia movio billetes del cajon. Falso con tarjeta y QR, y
    #: falso cuando no hay diferencia.
    toca_el_cajon: bool
