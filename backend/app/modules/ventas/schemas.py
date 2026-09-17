"""
P7 - Ventas y Punto de Venta  |  capa: esquemas (Pydantic)

Ciclo de desarrollo: 3
Caso de uso: CU-27 Realizar pedido y pagar en linea  (RF15, RF16, RF19)

Regla: NUNCA se expone un modelo SQLAlchemy directamente.

CU-26 tiene los suyos en `carrito_schemas.py`, que son de Karen.
"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.modules.ventas.carrito_schemas import LineaCarritoOut

#: Las dos formas de recibir la compra. Se repiten aca en vez de importarse de
#: `models.py` porque el esquema es el contrato con la web y no deberia cambiar
#: solo porque alguien agregue un valor al modelo.
MODALIDAD_RETIRO = "RETIRO"
MODALIDAD_ENVIO = "ENVIO"


# --- Paso 1: que puede elegir el cliente ---------------------------------

class SucursalParaRetiroOut(BaseModel):
    """Una sucursal donde se puede retirar ESTE pedido.

    `abastece_todo` es la razon de ser de este esquema: no alcanza con listar
    las sucursales activas, porque el pedido se despacha desde UNA sola y no
    todas tienen todas las prendas. Una lista sin esa marca dejaria al cliente
    elegir una sucursal y recibir el error recien al confirmar.
    """

    id: int
    nombre: str
    direccion: str
    ciudad: str
    #: Si tiene stock de TODAS las lineas del carrito.
    abastece_todo: bool
    #: Cuando no abastece todo, que prendas le faltan. La pantalla las nombra
    #: en vez de decir «no disponible», que obliga al cliente a adivinar.
    faltantes: list[str] = Field(default_factory=list)


class DireccionParaEnvioOut(BaseModel):
    """Una direccion registrada del cliente (CU-04)."""

    id: int
    alias: str
    direccion: str
    ciudad: str
    referencia: str | None
    predeterminada: bool


class OpcionesDePedidoOut(BaseModel):
    """Todo lo que la pantalla de confirmacion necesita, en UNA peticion.

    Junta el carrito, las sucursales que pueden abastecerlo y las direcciones
    del cliente. Pedirlo en tres viajes dejaria la pantalla pintandose por
    partes, y ademas abriria una ventana entre leer el carrito y leer el stock
    en la que el total podria cambiar.
    """

    lineas: list[LineaCarritoOut]
    total: Decimal
    unidades: int

    #: Si es `false`, el boton de confirmar va deshabilitado y la pantalla dice
    #: por que. Es `false` con el carrito vacio, con lineas no disponibles, o
    #: cuando ninguna sucursal abastece el pedido entero.
    se_puede_pedir: bool
    #: El motivo, en texto, cuando `se_puede_pedir` es `false`.
    motivo: str | None = None

    sucursales: list[SucursalParaRetiroOut]
    direcciones: list[DireccionParaEnvioOut]

    #: Si el proveedor de pago configurado mueve dinero de verdad. La pantalla
    #: lo dice con todas las letras cuando es `false`: en la demostracion el
    #: pago es de mentira, y hacerlo pasar por real seria enganar al tribunal.
    pago_real: bool
    #: Cuantos minutos aguanta el pedido sin pagar antes de cancelarse solo.
    minutos_para_pagar: int


# --- Paso 2: confirmar -----------------------------------------------------

class CrearPedidoIn(BaseModel):
    """Lo que el cliente confirma.

    `total_esperado` es la mitad interesante. Ver `CrearPedidoOut`.
    """

    modalidad_entrega: str = Field(pattern=f"^({MODALIDAD_RETIRO}|{MODALIDAD_ENVIO})$")

    #: Obligatorio en RETIRO: de que sucursal la retira.
    sucursal_id: int | None = None
    #: Obligatorio en ENVIO: a cual de sus direcciones.
    direccion_id: int | None = None

    #: El total que el cliente VIO en la pantalla cuando pulso confirmar.
    #:
    #: El carrito no congela precios ---es una intencion, no un contrato: ver
    #: `carrito_models.py`--- asi que entre que el cliente miro el carrito y
    #: confirmo, la tienda pudo cambiar un precio o desactivar una prenda. Sin
    #: este campo, el sistema cobraria el precio nuevo callado, y el cliente se
    #: enteraria leyendo el comprobante.
    #:
    #: Con el, el servidor compara y se planta: devuelve 409 con el total nuevo
    #: para que la pantalla lo muestre y el cliente decida de nuevo. Es el
    #: corolario que quedo anotado en el docstring de `ventas/models.py` al
    #: decidir que el precio se congela en la venta y no en el carrito.
    total_esperado: Decimal

    @model_validator(mode="after")
    def _coherencia(self):
        """Que el destino corresponda a la modalidad.

        Se valida aca y no solo en el servicio porque es una regla de FORMA:
        un RETIRO con direccion no es un caso de negocio que haya que evaluar,
        es una peticion mal armada. El CHECK `direccion_si_envio` de la base
        dice lo mismo; esto lo convierte en un 422 con un mensaje legible en
        vez de en un error de PostgreSQL.
        """
        if self.modalidad_entrega == MODALIDAD_RETIRO:
            if self.sucursal_id is None:
                raise ValueError("Para retirar hay que elegir una sucursal.")
            if self.direccion_id is not None:
                raise ValueError("Un retiro en sucursal no lleva dirección de envío.")
        else:
            if self.direccion_id is None:
                raise ValueError("Para el envío hay que elegir una dirección.")
            if self.sucursal_id is not None:
                raise ValueError(
                    "En un envío la sucursal que despacha la elige el sistema."
                )
        return self


class LineaPedidoOut(BaseModel):
    """Una linea ya vendida, con su precio CONGELADO.

    Es distinta de `LineaCarritoOut` justamente en eso: aquella lleva el precio
    vigente y esta lleva el que se cobro. Si fueran el mismo esquema, el
    historial de compras de CU-29 mostraria precios que cambian solos.
    """

    variante_id: int
    sku: str
    producto_nombre: str
    talla_codigo: str | None
    color_nombre: str | None
    imagen_url: str | None
    cantidad: int
    precio_unitario: Decimal
    descuento_unitario: Decimal
    subtotal: Decimal


class PedidoOut(BaseModel):
    """Un pedido. Es una `venta`, no hay tabla `pedido` (decision D2)."""

    codigo: str
    estado: str
    canal: str
    modalidad_entrega: str | None

    sucursal_id: int
    sucursal_nombre: str
    #: Nula en un retiro.
    direccion_envio: str | None

    lineas: list[LineaPedidoOut]
    subtotal: Decimal
    descuento: Decimal
    total: Decimal

    creado_en: datetime
    #: Hasta cuando se puede pagar. Nula si el pedido ya no esta esperando
    #: pago. Se calcula, no se guarda: es `creado_en` mas la vigencia, y
    #: guardarla seria una columna que puede quedar desincronizada de la
    #: variable de entorno que la define.
    pagar_antes_de: datetime | None

    #: Estado del pago, de la tabla `pago`. Nulo si todavia no se creo.
    estado_pago: str | None


class CrearPedidoOut(BaseModel):
    """La respuesta de confirmar: el pedido y adonde ir a pagar."""

    pedido: PedidoOut
    #: Adonde mandar el navegador. La pantalla redirige aca.
    url_pago: str
    #: `false` con el proveedor `simulada`. La pantalla lo avisa antes de
    #: redirigir: en la demostracion no se cobra nada.
    pago_real: bool


class ConflictoDePrecioOut(BaseModel):
    """El cuerpo del 409 cuando el total cambio entre mirar y confirmar.

    Devuelve el carrito ENTERO y no solo el total nuevo: el cliente necesita
    ver que linea cambio para decidir, y un numero suelto lo obligaria a
    recargar y comparar de memoria.
    """

    detalle: str
    total_esperado: Decimal
    total_actual: Decimal
    lineas: list[LineaCarritoOut]


class ExpiracionDePedidosOut(BaseModel):
    """Resultado de la barrida de pedidos sin pagar.

    Mismo esquema que la de CU-25 para reservas vencidas, y por la misma razon:
    quien la dispara necesita saber si hizo algo, sin tener que leer el log.
    """

    revisados: int
    cancelados: int
    unidades_devueltas: int
