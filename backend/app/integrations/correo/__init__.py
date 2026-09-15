"""Correo saliente. Punto de entrada unico del sistema hacia el correo.

Un caso de uso que necesita mandar un correo importa `enviar` de aca y arma un
`Mensaje`. Nunca importa un proveedor concreto: cual se usa lo decide la
variable de entorno CORREO_PROVEEDOR, no el codigo que llama.

    from app.integrations.correo import Mensaje, enviar

    enviar(Mensaje(destinatario=..., asunto=..., cuerpo_texto=..., cuerpo_html=...))

COMO SE AGREGA UN PROVEEDOR REAL
--------------------------------
1. Un modulo hermano de `consola.py` con una clase que tenga `nombre` y
   `enviar(mensaje)`, que hable por HTTP y levante `ErrorDeEnvio` si falla.
2. Su entrada en `_PROVEEDORES`, de abajo.
3. CORREO_PROVEEDOR y CORREO_API_KEY en las variables de Railway.

No hay paso 4: ningun caso de uso cambia.
"""

from functools import lru_cache

from app.core.config import settings
from app.integrations.correo.base import ErrorDeEnvio, Mensaje, ProveedorCorreo
from app.integrations.correo.consola import ProveedorConsola

__all__ = ["ErrorDeEnvio", "Mensaje", "ProveedorCorreo", "enviar", "obtener_proveedor"]


#: Proveedores disponibles, por el nombre con el que se los elige.
_PROVEEDORES: dict[str, type[ProveedorCorreo]] = {
    ProveedorConsola.nombre: ProveedorConsola,
}


@lru_cache
def obtener_proveedor() -> ProveedorCorreo:
    """El proveedor configurado, construido una sola vez.

    Un nombre desconocido NO degrada en silencio al proveedor de consola:
    levanta el error al construirlo. Degradar seria peor que fallar --- el
    sistema parecería mandar correos que nadie recibe, y en CU-41 eso deja a
    los usuarios sin poder entrar sin que nada avise.
    """
    nombre = settings.CORREO_PROVEEDOR.strip().lower()
    try:
        return _PROVEEDORES[nombre]()
    except KeyError:
        raise ValueError(
            f"CORREO_PROVEEDOR={settings.CORREO_PROVEEDOR!r} no existe. "
            f"Disponibles: {', '.join(sorted(_PROVEEDORES))}."
        ) from None


def enviar(mensaje: Mensaje) -> None:
    """Entrega el mensaje con el proveedor configurado.

    Levanta `ErrorDeEnvio` si el proveedor no pudo entregarlo.
    """
    obtener_proveedor().enviar(mensaje)
