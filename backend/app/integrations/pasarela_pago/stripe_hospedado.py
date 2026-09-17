"""Stripe Checkout: la sesion de pago la hospeda Stripe, no nosotros.

Se elige con PAGO_PROVEEDOR=stripe y PAGO_API_KEY=sk_test_...

POR QUE CHECKOUT HOSPEDADO Y NO UN FORMULARIO PROPIO
-----------------------------------------------------
Con Checkout, **el sistema nunca ve un numero de tarjeta**: el cliente los
escribe en una pagina de Stripe. Es lo que dice la seccion 6.7, y no es solo
comodidad --- un formulario propio nos metaria en el alcance de PCI-DSS, que es
un problema que un proyecto academico no puede resolver ni deberia simular.

EL MONTO VA EN LA UNIDAD MINIMA DE LA MONEDA
---------------------------------------------
Stripe cobra en centavos, no en bolivianos: 150.50 se manda como 15050. Es el
error clasico de esta integracion --- mandar 150.5 cobra un centavo y medio, y
mandar 150 cobra un boliviano y medio ---, asi que la conversion esta en una
funcion sola y con su prueba.

Se usa `Decimal` y se cuantiza antes de pasar a entero. Con `float` el precio
150.55 se guarda como 150.54999999999998 y truncar da 15054 en vez de 15055:
un centavo de diferencia por linea que no cuadra con `venta.total`, y un
descuadre de centavos en una pasarela es de los defectos mas caros de encontrar.

LA MONEDA
---------
Stripe no admite el boliviano (BOB) como moneda de cobro en la mayoria de las
cuentas de prueba, asi que `PAGO_MONEDA` existe y por defecto es 'usd'. Es una
limitacion del sandbox, no del diseno: la venta se guarda en su moneda y lo
unico que se traduce es lo que se le manda a la pasarela. Queda anotado como
deuda --- ver la ficha de CU-27 ---.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings
from app.integrations.pasarela_pago.base import (
    ErrorDePasarela,
    SesionDePago,
    SolicitudDePago,
)

_log = logging.getLogger("violetboutique.pago")


def a_unidad_minima(monto: Decimal) -> int:
    """Convierte 150.50 en 15050. Ver la nota de la cabecera.

    Cuantiza a dos decimales ANTES de multiplicar, con redondeo comercial. Si
    llegara un monto con mas decimales de los que la moneda admite, truncar
    despues de multiplicar perderia un centavo.
    """
    return int((Decimal(monto).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) * 100)


class ProveedorStripe:
    """Crea una Checkout Session y devuelve su URL."""

    nombre = "stripe"
    cobra_de_verdad = True

    def __init__(self) -> None:
        if not settings.PAGO_API_KEY:
            raise ValueError(
                "PAGO_PROVEEDOR=stripe exige PAGO_API_KEY. Con la clave vacia, "
                "Stripe rechaza toda peticion y el cliente veria un error al "
                "confirmar el pedido."
            )
        # Se importa aca y no arriba para que el modulo se pueda leer ---y el
        # resto de la costura se pueda usar--- sin tener el SDK instalado.
        import stripe

        self._stripe = stripe
        self._cliente = stripe.StripeClient(settings.PAGO_API_KEY)

    def crear_sesion(self, solicitud: SolicitudDePago) -> SesionDePago:
        lineas = [
            {
                "price_data": {
                    "currency": solicitud.moneda.lower(),
                    "product_data": {"name": linea.descripcion},
                    "unit_amount": a_unidad_minima(linea.precio_unitario),
                },
                "quantity": linea.cantidad,
            }
            for linea in solicitud.lineas
        ]

        try:
            sesion = self._cliente.checkout.sessions.create(
                params={
                    "mode": "payment",
                    "line_items": lineas,
                    "success_url": solicitud.url_exito
                    + "?sesion={CHECKOUT_SESSION_ID}",
                    "cancel_url": solicitud.url_cancelado,
                    "customer_email": solicitud.correo_cliente,
                    # Vuelven intactos en el webhook: es como CU-28 sabe a que
                    # venta corresponde el evento sin adivinarlo por el monto.
                    "metadata": solicitud.metadatos,
                    # Idempotencia del lado de Stripe: si esta peticion se
                    # reintenta ---por un corte de red al responder--- Stripe
                    # devuelve la MISMA sesion en vez de abrir una segunda.
                    # Sin esto, un reintento dejaria dos sesiones cobrables
                    # para un mismo pedido.
                    "idempotency_key": "pedido-" + solicitud.referencia,
                }
            )
        except Exception as e:  # el SDK levanta su propia jerarquia
            _log.exception("Stripe rechazo la sesion del pedido %s", solicitud.referencia)
            raise ErrorDePasarela(str(e)) from e

        if not sesion.url:
            raise ErrorDePasarela("Stripe devolvio una sesion sin URL de pago.")

        return SesionDePago(id_externo=sesion.id, url_redireccion=sesion.url)
