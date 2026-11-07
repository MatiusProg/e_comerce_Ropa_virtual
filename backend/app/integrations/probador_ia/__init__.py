"""Probado por IA. Punto de entrada unico hacia el servicio que «amolda» la
prenda al cuerpo.

Ciclo 3 - apoya a CU-21 (P9), **como opcion y no como parte del flujo**.

    from app.integrations import probador_ia

    if probador_ia.esta_disponible():
        resultado = probador_ia.probar(SolicitudDeProbado(...))

LA DIFERENCIA CON EL VESTIDOR DE CU-21
---------------------------------------
El vestidor pega un PNG recortado sobre el cuerpo, en el telefono, a tantos
fotogramas por segundo como de el. Es el caso de uso.

Esto manda la captura a un modelo que la recompone para que la prenda se vea
puesta de verdad --- plegada, ajustada al torso ---. Tarda segundos, depende de
un tercero y consume cuota. Por eso es un boton aparte, despues de capturar, y
el recorrido obligatorio funciona entero sin tocarlo.

POR QUE `esta_disponible()` EXISTE
-----------------------------------
Para que la pantalla pueda **esconder el boton** en vez de ofrecerlo y fallar
al tocarlo. Un boton que siempre da error es peor que no tenerlo: el cliente
lo prueba tres veces antes de creer que no funciona.

COMO SE AGREGA UN PROVEEDOR
---------------------------
1. Un modulo hermano de `gemini.py` con una clase que tenga `nombre`,
   `disponible` y `probar(solicitud)`, que levante `ErrorDelProbador` si falla.
2. Su entrada en `_PROVEEDORES`, de abajo.
3. PROBADOR_IA_PROVEEDOR en las variables de Railway.

No hay paso 4.
"""

from functools import lru_cache

from app.core.config import settings
from app.integrations.probador_ia.base import (
    ErrorDelProbador,
    ProbadorNoConfigurado,
    ProveedorProbador,
    ResultadoDeProbado,
    SolicitudDeProbado,
)
from app.integrations.probador_ia.gemini import ProbadorGemini
from app.integrations.probador_ia.no_disponible import ProbadorNoDisponible
from app.integrations.probador_ia.simulado import ProbadorSimulado

__all__ = [
    "ErrorDelProbador",
    "ProbadorNoConfigurado",
    "ProveedorProbador",
    "ResultadoDeProbado",
    "SolicitudDeProbado",
    "esta_disponible",
    "obtener_proveedor",
    "probar",
]


_PROVEEDORES: dict[str, type] = {
    ProbadorNoDisponible.nombre: ProbadorNoDisponible,
    ProbadorGemini.nombre: ProbadorGemini,
    ProbadorSimulado.nombre: ProbadorSimulado,
}


@lru_cache
def obtener_proveedor() -> ProveedorProbador:
    """El proveedor configurado, construido una sola vez.

    A DIFERENCIA DEL CORREO Y DE LA PASARELA, ESTE DEGRADA
    -------------------------------------------------------
    Si el nombre no existe, o si el proveedor no se puede construir --- casi
    siempre por falta de clave ---, **se cae al proveedor no disponible en vez
    de reventar**.

    Es lo contrario de lo que hacen las otras dos costuras, y a proposito: alli
    degradar seria grave --- el sistema pareceria mandar correos que nadie
    recibe, o aceptar pagos que nadie cobra ---. Aca lo unico que se pierde es
    una funcion OPCIONAL, y hacer que toda la aplicacion no arranque porque
    falta una clave de una comodidad seria desproporcionado.

    El aviso va al log, que es donde tiene que estar.
    """
    nombre = settings.PROBADOR_IA_PROVEEDOR.strip().lower()
    clase = _PROVEEDORES.get(nombre)
    if clase is None:
        import logging

        logging.getLogger("violetboutique.probador").warning(
            "PROBADOR_IA_PROVEEDOR=%r no existe. Disponibles: %s. "
            "Se usa el simulado.",
            settings.PROBADOR_IA_PROVEEDOR,
            ", ".join(sorted(_PROVEEDORES)),
        )
        return ProbadorSimulado()
    try:
        return clase()
    except Exception as e:
        import logging

        # 2do parcial (CU-38): sin clave se cae al SIMULADO, no al apagado. El
        # simulado no cuesta nada, y el caso de uso se puede recorrer igual.
        logging.getLogger("violetboutique.probador").warning(
            "No se pudo construir el probador %r (%s). Se usa el simulado.", nombre, e
        )
        return ProbadorSimulado()


def esta_disponible() -> bool:
    """Si hay con qué componer. La pantalla pregunta esto antes de ofrecerlo."""
    return obtener_proveedor().disponible


def probar(solicitud: SolicitudDeProbado) -> ResultadoDeProbado:
    """Compone la imagen con el proveedor configurado.

    2do parcial (CU-38): si el proveedor real FALLA --- Gemini sin facturacion
    contesta 429, o se cae ---, la foto sale igual con el simulado y
    `generada_por` lo dice. `no_disponible` sigue rechazando: ese es el
    apagado a proposito, no un fallo.
    """
    proveedor = obtener_proveedor()
    try:
        return proveedor.probar(solicitud)
    except ProbadorNoConfigurado:
        raise
    except ErrorDelProbador as e:
        if isinstance(proveedor, ProbadorSimulado):
            raise
        import logging

        logging.getLogger("violetboutique.probador").warning(
            "El probador %r falló (%s). Se devuelve la vista simulada.",
            proveedor.nombre, e,
        )
        resultado = ProbadorSimulado().probar(solicitud)
        return ResultadoDeProbado(
            imagen=resultado.imagen,
            tipo_mime=resultado.tipo_mime,
            generada_por=f"simulado (falló {proveedor.nombre})",
        )
