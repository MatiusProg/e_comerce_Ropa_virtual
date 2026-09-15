"""Configuracion del registro de eventos (logging) de la aplicacion.

POR QUE ESTE ARCHIVO EXISTE
---------------------------
Uvicorn instala su propia configuracion de logging al arrancar: define los
manejadores de `uvicorn`, `uvicorn.error` y `uvicorn.access`, y **deja el logger
raiz sin ninguno**. Un logger propio de la aplicacion --- `violetboutique.*` ---
propaga hasta el raiz, no encuentra manejador, y cae en el `lastResort` de la
biblioteca estandar, que solo emite WARNING o peor.

Consecuencia concreta, y por eso se escribio esto: el proveedor de correo
`consola` escribia el mensaje con `INFO` y **no aparecia por ningun lado**. Ese
proveedor existe justamente para que el enlace de recuperacion (CU-41) se pueda
leer de la consola en desarrollo; sin esto, no servia para nada.

No lo atrapo ninguna prueba porque `caplog`, de pytest, agrega su propio
manejador al raiz: dentro de la prueba el mensaje llegaba perfecto. Se descubrio
levantando la aplicacion de verdad. La prueba que lo cubre ahora
--- tests/test_registro_logging.py --- corre en un subproceso por ese motivo.

POR QUE NO `basicConfig`
------------------------
`basicConfig` cuelga el manejador del logger RAIZ, y eso cambia el
comportamiento de todo lo demas. En concreto: con DEBUG activo, SQLAlchemy pone
`echo=True`, que le agrega su propio manejador a `sqlalchemy.engine`; si ademas
el raiz tuviera uno, **cada sentencia SQL se imprimiria dos veces** --- y ese
ruido es justo lo que taparia el correo que esto viene a hacer visible.

Asi que el manejador se cuelga del logger de la aplicacion y nada mas, con
`propagate = False` para que lo suyo no suba al raiz ni se duplique si alguien
mas lo configura despues.
"""

import logging
import sys

from app.core.config import settings

#: Prefijo de todos los loggers propios. Cualquier modulo que quiera escribir
#: en el log usa `logging.getLogger("violetboutique.<lo que sea>")` y hereda
#: esta configuracion.
RAIZ = "violetboutique"

_FORMATO = "%(asctime)s %(levelname)-8s %(name)s %(message)s"


def configurar_logging() -> None:
    """Deja el logger de la aplicacion escribiendo por la salida estandar.

    Es idempotente: si ya tiene manejador no agrega otro. Sin esa guarda, dos
    llamadas ---o dos importaciones en una suite de pruebas--- dejarian cada
    mensaje repetido tantas veces como se hubiera llamado.
    """
    logger = logging.getLogger(RAIZ)

    if not logger.handlers:
        manejador = logging.StreamHandler(sys.stdout)
        manejador.setFormatter(logging.Formatter(_FORMATO))
        logger.addHandler(manejador)

    # Lo de la aplicacion no sube al raiz: ya se escribio aca.
    logger.propagate = False

    # En produccion el log es lo unico que queda de lo que paso, asi que INFO
    # tambien alli. Lo que no debe entrar en el log son los secretos, y eso se
    # resuelve no escribiendolos, no subiendo el nivel.
    logger.setLevel(
        logging.DEBUG if settings.DEBUG and not settings.es_produccion else logging.INFO
    )
