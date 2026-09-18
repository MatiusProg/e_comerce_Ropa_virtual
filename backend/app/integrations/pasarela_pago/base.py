"""Pasarela de pago: el contrato que cumple cualquier proveedor.

Este modulo no conoce la base de datos, ni FastAPI, ni ningun caso de uso.
Define que es una sesion de pago y que sabe hacer un proveedor; nada mas.

POR QUE HAY UNA COSTURA Y NO UNA LLAMADA DIRECTA A STRIPE
---------------------------------------------------------
Es la misma forma que uso Karen para el correo, y por dos razones propias:

1. **Para poder demostrar sin claves.** El proveedor `simulada` aprueba el pago
   al instante y escribe la sesion en el log. Con el, CU-27 y CU-28 se pueden
   construir, probar y mostrar sin haber configurado Stripe. Sin la costura,
   toda prueba de pago exigiria red y una cuenta.

2. **Porque la seccion 6.7 ya declara un plan de respaldo.** PayPal queda como
   alternativa si Stripe presentara restricciones regionales. Con la costura,
   ese cambio es un modulo hermano y una variable de entorno.

LO QUE ESTA COSTURA NO HACE, Y ES DELIBERADO
---------------------------------------------
No decide el estado de la venta. Devuelve lo que la pasarela dijo y nada mas.
Quien traduce un evento en «esta venta esta pagada» es CU-28, y solo despues de
verificar la firma. Es la decision D5: **el estado del pago lo determina
unicamente el webhook verificado, nunca la redireccion del navegador**, que el
cliente puede escribir a mano en la barra de direcciones.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol, runtime_checkable


class ErrorDePasarela(Exception):
    """La pasarela no pudo crear la sesion, o contesto algo inesperado.

    La levanta el proveedor. CU-27 la deja subir y el router la traduce a un
    502: el pedido no se llega a crear, asi que el cliente puede reintentar sin
    que haya quedado nada a medias ni stock apartado.
    """


class FirmaInvalida(Exception):
    """El cuerpo del webhook no corresponde a la firma que lo acompana.

    La usa CU-28. Se guarda igual en `transaccion_pasarela` con
    `firma_valida = False` --- son justamente los eventos que uno quiere mirar
    cuando algo sale mal --- pero NO se aplica a la venta.
    """


@dataclass(frozen=True)
class LineaDePago:
    """Una linea del cobro, tal como la va a ver el cliente en la pasarela.

    Lleva el nombre de la prenda y no solo el monto porque la pantalla de la
    pasarela es lo ultimo que el cliente mira antes de poner la tarjeta: un
    total suelto, sin el detalle, es donde se abandona una compra.
    """

    descripcion: str
    cantidad: int
    #: Precio unitario YA con el descuento aplicado, en la moneda de `moneda`.
    precio_unitario: Decimal


@dataclass(frozen=True)
class SolicitudDePago:
    """Lo que CU-27 le pide a la pasarela."""

    #: El codigo legible de la venta (`venta.codigo`), no su id. Es lo que el
    #: cliente puede leer por telefono si algo sale mal.
    referencia: str
    lineas: list[LineaDePago]
    moneda: str
    url_exito: str
    url_cancelado: str
    #: Para que la pasarela mande el comprobante. Nulo en una venta anonima.
    correo_cliente: str | None = None
    #: Datos que vuelven intactos en el webhook. Es como CU-28 sabe a que venta
    #: corresponde un evento sin tener que adivinarlo por el monto.
    metadatos: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SesionDePago:
    """Lo que la pasarela devuelve cuando la sesion queda abierta."""

    #: El identificador de la sesion en la pasarela. Se guarda en
    #: `pago.referencia_externa`, que es UNICO: dos ventas colgando de la misma
    #: sesion es como un reintento mal hecho cobraria dos veces lo mismo.
    id_externo: str
    #: Adonde mandar el navegador del cliente.
    url_redireccion: str


@dataclass(frozen=True)
class EventoDePago:
    """Lo que el sistema entiende de una notificacion de la pasarela (CU-28).

    Es el traductor: cada proveedor manda su propio JSON con sus propios
    nombres, y a partir de aca **nadie mas vuelve a mirar ese JSON**. El
    servicio de CU-28 trabaja solo con esta forma, que es la misma para Stripe,
    para el simulado y para el que venga.

    Se declara `frozen` porque un evento es un hecho ya ocurrido: nada de lo
    que pase despues puede cambiar lo que la pasarela dijo.
    """

    #: El identificador del evento EN LA PASARELA. Es lo que se guarda en
    #: `transaccion_pasarela.evento_id`, que es UNICO, y por lo tanto **es toda
    #: la idempotencia de CU-28**: una notificacion repetida choca contra esa
    #: restriccion y no vuelve a tocar nada.
    id_evento: str

    #: El tipo, tal como lo nombra la pasarela. Se guarda sin traducir para que
    #: el registro diga lo que de verdad llego.
    tipo: str

    #: La sesion de pago. Es lo que cruza con `pago.referencia_externa` y la
    #: forma normal de encontrar la venta.
    id_sesion: str | None

    #: El codigo de la venta, si el proveedor lo devolvio en sus metadatos. Es
    #: el camino de respaldo cuando la sesion no se encuentra.
    referencia: str | None

    #: Si este evento dice que el dinero entro. `False` cubre tanto el rechazo
    #: como los eventos que no hablan de cobro --- ver `es_de_cobro`.
    aprobado: bool

    #: Si el evento habla del resultado de un cobro. Las pasarelas mandan
    #: muchos eventos que no interesan; los que no son de cobro **se registran
    #: igual** y no mueven nada. Distinguirlo evita que un evento cualquiera
    #: parezca un rechazo.
    es_de_cobro: bool

    #: El cuerpo tal cual llego, para `transaccion_pasarela.carga_util`. Es el
    #: registro de lo que la pasarela dijo, se haya aplicado o no, y es lo
    #: primero que uno quiere mirar cuando algo sale mal.
    carga_util: str


@runtime_checkable
class ProveedorPasarela(Protocol):
    """Lo unico que el sistema le pide a una pasarela de pago."""

    #: Nombre con el que se lo elige en la variable PAGO_PROVEEDOR.
    nombre: str

    #: Si el proveedor cobra de verdad. `simulada` lo tiene en False, y es lo
    #: que permite que la pantalla avise que el pago es de mentira en vez de
    #: dejar creer que se cobro.
    cobra_de_verdad: bool

    def crear_sesion(self, solicitud: SolicitudDePago) -> SesionDePago:
        """Abre la sesion de pago, o levanta ErrorDePasarela."""
        ...

    def interpretar_webhook(self, cuerpo: bytes, firma: str | None) -> EventoDePago:
        """Verifica la firma y traduce la notificacion (CU-28).

        **Verificar y traducir son la misma operacion, a proposito.** Separarlas
        dejaria abierta la puerta a leer el contenido antes de comprobar quien
        lo mando, que es exactamente el agujero que la firma existe para tapar:
        cualquiera puede hacer un POST al webhook diciendo que un pedido se
        pago. Con una sola funcion no hay forma de saltearse el paso.

        Recibe el cuerpo **en bytes y sin tocar**: la firma se calcula sobre
        los bytes exactos que viajaron, y volver a serializar un JSON ya
        interpretado cambia los espacios y el orden, y la verificacion falla
        aunque el mensaje sea legitimo.

        Levanta `FirmaInvalida` si no la puede verificar, y `ErrorDePasarela`
        si el cuerpo no se entiende.
        """
        ...
