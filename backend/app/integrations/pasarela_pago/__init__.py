"""Pasarela de pago. Punto de entrada unico del sistema hacia el cobro.

Ciclo 3 - paquete P8.

Un caso de uso que necesita cobrar importa `crear_sesion` de aca y arma una
`SolicitudDePago`. Nunca importa un proveedor concreto: cual se usa lo decide
la variable de entorno PAGO_PROVEEDOR, no el codigo que llama.

    from app.integrations.pasarela_pago import (
        LineaDePago, SolicitudDePago, crear_sesion,
    )

    sesion = crear_sesion(SolicitudDePago(referencia=..., lineas=[...], ...))

Responsabilidades del paquete:
  - crear la sesion de pago y devolver la URL de redireccion   (CU-27)
  - verificar la firma del webhook antes de creer su contenido (CU-28)
  - traducir el evento de la pasarela a un estado de Venta     (CU-28)

REGLA D5, QUE ES LA QUE ORDENA TODO ESTO
-----------------------------------------
El estado del pago lo determina UNICAMENTE el webhook verificado, nunca la
redireccion del navegador del cliente. Esa redireccion es una URL que el
cliente puede escribir a mano; si alcanzara para marcar una venta como pagada,
cualquiera se llevaria la mercaderia gratis escribiendo una direccion.

COMO SE AGREGA UN PROVEEDOR
---------------------------
1. Un modulo hermano de `simulada.py` con una clase que tenga `nombre`,
   `cobra_de_verdad` y `crear_sesion(solicitud)`, que levante `ErrorDePasarela`
   si falla.
2. Su entrada en `_PROVEEDORES`, de abajo.
3. PAGO_PROVEEDOR y PAGO_API_KEY en las variables de Railway.

No hay paso 4: ningun caso de uso cambia.
"""

from functools import lru_cache

from app.core.config import settings
from app.integrations.pasarela_pago.base import (
    ErrorDePasarela,
    FirmaInvalida,
    LineaDePago,
    ProveedorPasarela,
    SesionDePago,
    SolicitudDePago,
)
from app.integrations.pasarela_pago.simulada import ProveedorSimulado
from app.integrations.pasarela_pago.stripe_hospedado import ProveedorStripe

__all__ = [
    "ErrorDePasarela",
    "FirmaInvalida",
    "LineaDePago",
    "ProveedorPasarela",
    "SesionDePago",
    "SolicitudDePago",
    "cobra_de_verdad",
    "crear_sesion",
    "obtener_proveedor",
]


#: Proveedores disponibles, por el nombre con el que se los elige.
_PROVEEDORES: dict[str, type] = {
    ProveedorSimulado.nombre: ProveedorSimulado,
    ProveedorStripe.nombre: ProveedorStripe,
}


@lru_cache
def obtener_proveedor() -> ProveedorPasarela:
    """El proveedor configurado, construido una sola vez.

    Un nombre desconocido NO degrada en silencio al proveedor simulado:
    levanta el error al construirlo. Degradar seria muchisimo peor que fallar
    --- el sistema aceptaria pedidos que nadie cobra y la tienda entregaria
    mercaderia sin haber recibido un peso ---. Mismo criterio que el correo.
    """
    nombre = settings.PAGO_PROVEEDOR.strip().lower()
    try:
        return _PROVEEDORES[nombre]()
    except KeyError:
        raise ValueError(
            f"PAGO_PROVEEDOR={settings.PAGO_PROVEEDOR!r} no existe. "
            f"Disponibles: {', '.join(sorted(_PROVEEDORES))}."
        ) from None


def crear_sesion(solicitud: SolicitudDePago) -> SesionDePago:
    """Abre la sesion de pago con el proveedor configurado.

    Levanta `ErrorDePasarela` si el proveedor no pudo abrirla.
    """
    return obtener_proveedor().crear_sesion(solicitud)


def cobra_de_verdad() -> bool:
    """Si el proveedor configurado mueve dinero real.

    Lo consume CU-27 para avisarle al cliente, en la propia respuesta, que el
    pago es de mentira. Es preferible a que la pantalla lo deduzca del nombre
    del proveedor: eso obligaria a la web a conocer la lista.
    """
    return obtener_proveedor().cobra_de_verdad
