"""Probado por IA con los modelos de imagen de Google (Gemini).

Se elige con PROBADOR_IA_PROVEEDOR=gemini y necesita IA_API_KEY.

POR QUE GEMINI Y NO UN SERVICIO DE «VIRTUAL TRY-ON»
----------------------------------------------------
Hay servicios dedicados a esto y componen mejor. Todos los que se miraron
cobran por imagen desde la primera. El acuerdo del 11/09 --- anotado en la
seccion 6.6 --- es que **la IA de este proyecto tiene que ser de plan
gratuito**, por el riesgo R9: quedarse sin credito antes de la defensa. Gemini
ya estaba elegido para CU-33 a CU-35, tiene plan gratuito, y su modelo de
imagen sabe editar una foto a partir de otra.

Si el dia de manana hay presupuesto, agregar un proveedor dedicado es un modulo
hermano de este y una variable de entorno. Ningun caso de uso cambia.

LO QUE SE LE MANDA
------------------
Dos imagenes y una instruccion:

  1. la captura del vestidor --- la persona con la prenda plana ya encima ---
  2. el PNG de la prenda, como referencia de corte y color

Mandar la captura CON la superposicion y no la foto limpia no es un descuido:
le dice al modelo donde va la prenda, de que tamano y en que angulo. Es la
mitad del trabajo hecha, y con la foto limpia acierta bastante menos.

LA INSTRUCCION ES CONSERVADORA A PROPOSITO
-------------------------------------------
Se le pide que **no cambie la cara, el cuerpo ni el fondo**. Un modelo de
imagen, suelto, «mejora» a la persona: le cambia la cara, la adelgaza, le
arregla el pelo. Eso en una tienda de ropa no es un detalle estetico --- es
mostrarle al cliente un cuerpo que no es el suyo con una prenda que le
quedaria de otra forma.

PROBADO CONTRA EL SERVICIO REAL EL 18/09/2026, Y NO FUNCIONA GRATIS
--------------------------------------------------------------------
Con una clave de Google AI Studio recien creada, los TRES modelos de imagen
contestan lo mismo en la PRIMERA llamada:

    gemini-3.1-flash-image       -> 429, "limit: 0 input tokens per minute"
    gemini-3.1-flash-lite-image  -> 429, "limit: 0 requests per day"
    gemini-2.5-flash-image       -> 429, "limit: 0 input tokens per minute"

**La generacion de imagenes no esta en el plan gratuito.** No es cuota
agotada ni un modelo mal escrito: el limite es CERO, y esperar no lo cambia.

La clave SI sirve, y esto importa para CU-33 a CU-35: los modelos de texto
`gemini-3.6-flash` y `gemini-3.5-flash-lite` responden 200 con esa misma clave.
Lo que esta detras de facturacion es la imagen.

Ojo tambien con los nombres: `gemini-2.5-flash` y `gemini-2.5-flash-lite` ya
NO estan disponibles para cuentas nuevas --- el propio error manda a
`gemini-3.6-flash` y `gemini-3.5-flash-lite`.

CONSECUENCIA: el proveedor por defecto vuelve a ser `no_disponible`, y el
vestidor funciona entero sin esto. Este modulo queda escrito y probado hasta
donde se puede: el dia que haya facturacion, o que aparezca un proveedor
gratuito, es cambiar una variable.

Por eso ademas `_extraer` BUSCA la imagen en vez de leer una ruta fija: la
parte que devuelve imagen nunca se pudo ejercitar. Ver su nota.
"""

import base64
import logging

import httpx

from app.core.config import settings
from app.integrations.probador_ia.base import (
    ErrorDelProbador,
    ResultadoDeProbado,
    SolicitudDeProbado,
)

_log = logging.getLogger("violetboutique.probador")

_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

#: El modelo de imagen. Se cambia sin tocar codigo con PROBADOR_IA_MODELO, **y
#: hace falta poder hacerlo**: al 18/09/2026 los nombres son
#: `gemini-3.1-flash-image` (el de uso general), `gemini-3.1-flash-lite-image`
#: (el mas rapido y barato) y `gemini-3-pro-image` (mas calidad, detras de
#: facturacion). Los `gemini-2.5-*` quedaron como heredados. Esta familia se
#: renombra seguido.
_MODELO_POR_DEFECTO = "gemini-3.1-flash-image"

_INSTRUCCION = (
    "Esta es la foto de una persona probandose una prenda en un vestidor "
    "virtual. La prenda esta superpuesta de forma plana y rigida. "
    "Genera la MISMA foto pero con la prenda ajustada al cuerpo de forma "
    "realista: que siga la postura, se pliegue en los hombros y la cintura, y "
    "caiga con el peso de la tela. La segunda imagen es la prenda de "
    "referencia ({descripcion}): respeta su color, su corte y su largo.\n\n"
    "MUY IMPORTANTE: no cambies la cara, el cuerpo, el peinado ni el fondo de "
    "la persona. No la adelgaces ni la retoques. Lo unico que cambia es como "
    "se asienta la prenda."
)


class ProbadorGemini:
    """Compone la imagen con el modelo de imagen de Google."""

    nombre = "gemini"
    disponible = True

    def __init__(self) -> None:
        if not settings.IA_API_KEY:
            raise ValueError(
                "PROBADOR_IA_PROVEEDOR=gemini exige IA_API_KEY. Sin la clave, "
                "toda peticion se rechaza y el cliente veria un error al tocar "
                "el boton."
            )
        self._clave = settings.IA_API_KEY
        self._modelo = settings.PROBADOR_IA_MODELO or _MODELO_POR_DEFECTO

    def probar(self, solicitud: SolicitudDeProbado) -> ResultadoDeProbado:
        cuerpo = {
            "model": self._modelo,
            "input": [
                {
                    "type": "text",
                    "text": _INSTRUCCION.format(descripcion=solicitud.descripcion),
                },
                {
                    "type": "image",
                    "mime_type": "image/png",
                    "data": base64.b64encode(solicitud.foto).decode(),
                },
                {
                    "type": "image",
                    "mime_type": "image/png",
                    "data": base64.b64encode(solicitud.prenda).decode(),
                },
            ],
        }

        try:
            respuesta = httpx.post(
                _URL,
                # La clave va en CABECERA y no en la cadena de consulta: una
                # clave en la URL termina en los registros de acceso de
                # cualquier intermediario que haya en el camino.
                headers={"x-goog-api-key": self._clave},
                json=cuerpo,
                # Holgado: componer una imagen tarda bastante mas que contestar
                # texto, y un timeout corto se leeria como «el servicio no
                # anda» cuando en realidad estaba trabajando.
                timeout=httpx.Timeout(90.0, connect=15.0),
            )
        except httpx.HTTPError as e:
            _log.warning("El probador de IA no respondio: %s", e)
            raise ErrorDelProbador(f"No se pudo consultar el servicio: {e}") from e

        if respuesta.status_code == 429:
            # Un 429 son DOS cosas distintas, y confundirlas hace perder horas.
            #
            # Google devuelve 429 tanto cuando se gasto la cuota del dia ---que
            # se arregla esperando--- como cuando el modelo **no esta en el
            # plan gratuito**, y ahi el mensaje dice `limit: 0`. Esperar a
            # manana no arregla un limite de cero.
            #
            # Comprobado el 18/09/2026 con una clave recien creada: los tres
            # modelos de imagen ---`gemini-3.1-flash-image`,
            # `gemini-3.1-flash-lite-image` y `gemini-2.5-flash-image`---
            # contestan `limit: 0` en la primera llamada. La generacion de
            # imagenes NO esta en el plan gratuito. Los modelos de TEXTO si:
            # `gemini-3.6-flash` y `gemini-3.5-flash-lite` responden 200 con la
            # misma clave.
            texto = respuesta.text
            if "limit: 0" in texto:
                _log.warning(
                    "El modelo %s no esta habilitado en este plan: %s",
                    self._modelo,
                    texto[:300],
                )
                raise ErrorDelProbador(
                    f"El modelo de imágenes «{self._modelo}» no está "
                    "habilitado en el plan de esta cuenta. No se arregla "
                    "esperando: hay que habilitar facturación o elegir otro "
                    "proveedor."
                )
            raise ErrorDelProbador(
                "Se agotó la cuota diaria del servicio de imágenes. "
                "Vuelva a intentarlo mañana."
            )
        if respuesta.status_code >= 400:
            _log.warning(
                "El probador de IA devolvio %s: %s",
                respuesta.status_code,
                respuesta.text[:400],
            )
            raise ErrorDelProbador(
                f"El servicio de imágenes respondió {respuesta.status_code}."
            )

        return self._extraer(respuesta.json())

    def _extraer(self, datos: dict) -> ResultadoDeProbado:
        """Saca la imagen de la respuesta, sin casarse con una forma exacta.

        POR QUE SE BUSCA EN VEZ DE LEER UN CAMPO
        -----------------------------------------
        La respuesta documentada trae la imagen en `output_image`, y los casos
        con varias salidas la traen dentro de `steps`. Pero **esta API se movio
        dos veces en poco tiempo** --- de `:generateContent` a `interactions`,
        y los modelos se renombraron enteros ---, y este proveedor no se pudo
        probar contra el servicio real.

        Asi que en vez de leer una ruta fija se recorre la respuesta buscando
        el primer bloque con pinta de imagen. Si la forma cambia otra vez, esto
        sigue andando; y si no encuentra nada, deja el cuerpo recortado en el
        log, que es lo que hace falta para arreglarlo en un minuto.
        """
        hallazgo = _buscar_imagen(datos)
        if hallazgo is not None:
            crudo, tipo = hallazgo
            return ResultadoDeProbado(
                imagen=base64.b64decode(crudo),
                tipo_mime=tipo or "image/png",
                generada_por=f"{self.nombre}:{self._modelo}",
            )

        # Llego una respuesta valida sin imagen. Casi siempre es el filtro de
        # contenido del modelo, que se niega a editar fotos de personas.
        motivo = _motivo_de_corte(datos)
        _log.warning(
            "El probador de IA no devolvio imagen%s. Respuesta: %s",
            motivo,
            str(datos)[:400],
        )
        raise ErrorDelProbador("El servicio no devolvió una imagen" + motivo + ".")


def _buscar_imagen(nodo, profundidad: int = 0) -> tuple[str, str | None] | None:
    """El primer `data` con pinta de imagen en base64, y su tipo declarado.

    Se acota la profundidad para que una respuesta inesperadamente anidada no
    haga trabajar de mas: seis niveles cubren de sobra todas las formas que
    esta API tuvo hasta ahora.
    """
    if profundidad > 6:
        return None

    if isinstance(nodo, dict):
        crudo = nodo.get("data")
        if isinstance(crudo, str) and len(crudo) > 256:
            tipo = nodo.get("mime_type") or nodo.get("mimeType")
            # Sin tipo declarado se acepta igual: un `data` de mas de 256
            # caracteres dentro de la respuesta de un modelo de imagen no es
            # otra cosa. Pero si declara tipo, tiene que ser de imagen --- para
            # no confundirlo con un adjunto de otra clase.
            if tipo is None or str(tipo).startswith("image/"):
                return crudo, tipo
        for valor in nodo.values():
            hallado = _buscar_imagen(valor, profundidad + 1)
            if hallado is not None:
                return hallado
        return None

    if isinstance(nodo, list):
        for elemento in nodo:
            hallado = _buscar_imagen(elemento, profundidad + 1)
            if hallado is not None:
                return hallado
    return None


def _motivo_de_corte(datos: dict) -> str:
    """Por que el modelo no devolvio imagen, si lo dice."""
    for clave in ("finish_reason", "finishReason", "status", "error"):
        valor = datos.get(clave)
        if valor:
            return f" (motivo: {valor})"
    return ""
