"""El log de la aplicación tiene que llegar a alguna parte.

Por qué existe este archivo
---------------------------
Uvicorn instala su propia configuración de logging al arrancar: define los
manejadores de `uvicorn`, `uvicorn.error` y `uvicorn.access`, y **deja el logger
raíz sin ninguno**. Un logger propio de la aplicación propaga hasta el raíz, no
encuentra manejador, y cae en el `lastResort` de la biblioteca estándar — que
sólo emite WARNING o peor.

Ya pasó. El proveedor de correo `consola` escribía el mensaje con `INFO` y **no
aparecía por ningún lado**. Ese proveedor existe justamente para que el enlace
de recuperación de CU-41 pueda leerse de la consola en desarrollo; sin log, no
servía para nada, y el caso de uso no se podía probar a mano.

**Ninguna prueba lo atrapó**, porque `caplog` agrega su propio manejador al
raíz: dentro de una prueba el mensaje llegaba perfecto. Se descubrió levantando
la aplicación de verdad.

Por qué esto corre en un SUBPROCESO
-----------------------------------
El primer intento de cubrirlo fue en proceso: configurar el logging, mirar que
el logger tuviera manejador alcanzable y que dejara pasar `INFO`. **Esas pruebas
pasaban con el arreglo desactivado** — se comprobó a propósito—, porque el
propio pytest instala manejadores en el raíz y porque la prueba llamaba a la
función que quería verificar. Medían la cañería que ellas mismas acababan de
montar.

Lo único que prueba esto de verdad es un intérprete limpio, con la configuración
de uvicorn puesta como la pone uvicorn, importando la aplicación como la importa
el servidor, y mirando **si el texto sale o no sale**. Eso es un subproceso.
"""

import os
import subprocess
import sys
from pathlib import Path

#: Raíz del backend: es desde donde tiene que importarse `app`.
_BACKEND = Path(__file__).resolve().parents[1]

#: Marca que se busca en la salida. Va dentro del cuerpo del mensaje, que es
#: exactamente donde viaja el enlace de recuperación de CU-41.
_MARCA = "TOKEN-QUE-TIENE-QUE-APARECER"

_GUION = f"""
import logging.config

# Lo primero que hace uvicorn al arrancar. Define los manejadores de sus
# propios loggers y deja el raiz sin ninguno: es la condicion que rompia todo.
from uvicorn.config import LOGGING_CONFIG
logging.config.dictConfig(LOGGING_CONFIG)

# Y recien despues importa la aplicacion, igual que el servidor.
import app.main  # noqa: F401

from app.integrations.correo import Mensaje, enviar

enviar(
    Mensaje(
        destinatario="ana@violetboutique.bo",
        asunto="Recupere el acceso",
        cuerpo_texto="Abra http://localhost:4200/recuperar/{_MARCA}",
        cuerpo_html="<p>x</p>",
    )
)
"""


def test_el_correo_del_proveedor_consola_sale_bajo_la_configuracion_de_uvicorn(
    tmp_path,
) -> None:
    """El enlace tiene que verse en la consola de un servidor de verdad.

    Es el único camino que hay en desarrollo para completar CU-41 a mano, así
    que si esto se rompe el caso de uso deja de poder probarse — y el fallo es
    un silencio, no una excepción: nada avisa.

    Si esta prueba falla, mirar `app/core/registro.py` y que `app/main.py`
    siga llamando a `configurar_logging()`.
    """
    # Sin MEDIA_ROOT, `app.main` crearía el directorio por defecto —que es una
    # ruta absoluta— en la raíz del disco con sólo importarse.
    entorno = {**os.environ, "MEDIA_ROOT": str(tmp_path / "media")}

    resultado = subprocess.run(
        [sys.executable, "-c", _GUION],
        cwd=_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
        timeout=120,
    )

    salida = resultado.stdout + resultado.stderr
    assert resultado.returncode == 0, salida

    assert _MARCA in salida, (
        "El proveedor de correo `consola` no escribió nada visible bajo la "
        "configuración de logging de uvicorn. El enlace de recuperación de "
        "CU-41 se pierde en silencio y el caso de uso no se puede probar a "
        "mano.\n\nSalida completa:\n" + salida
    )
    assert "CORREO NO ENVIADO" in salida, salida
