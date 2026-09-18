"""Probado por IA con los modelos de imagen de Google (Gemini).

Se elige con PROBADOR_IA_PROVEEDOR=gemini y necesita IA_API_KEY.

POR QUE GEMINI Y NO UN SERVICIO DE «VIRTUAL TRY-ON»
----------------------------------------------------
Hay servicios dedicados a esto y componen mejor. Todos los que se miraron
cobran por imagen desde la primera. El acuerdo del 11/09 --- anotado en la
seccion 6.6 --- es que **la IA de este proyecto tiene que ser de plan
gratuito**, por el riesgo R9: quedarse sin credito antes de la defensa. Gemini
ya estaba elegido para CU-33 a CU-35, tiene plan gratuito con cuota diaria, y
su modelo de imagen sabe editar una foto a partir de otra.

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

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

#: El modelo de imagen del plan gratuito. Se puede cambiar sin tocar codigo con
#: PROBADOR_IA_MODELO: los nombres de los modelos cambian seguido.
_MODELO_POR_DEFECTO = "gemini-2.5-flash-image"

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
            "contents": [
                {
                    "parts": [
                        {
                            "text": _INSTRUCCION.format(
                                descripcion=solicitud.descripcion
                            )
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(solicitud.foto).decode(),
                            }
                        },
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": base64.b64encode(solicitud.prenda).decode(),
                            }
                        },
                    ]
                }
            ]
        }

        try:
            respuesta = httpx.post(
                _URL.format(modelo=self._modelo),
                params={"key": self._clave},
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
            # La cuota del plan gratuito. Se distingue del resto porque tiene
            # arreglo esperando, y el mensaje lo tiene que decir.
            raise ErrorDelProbador(
                "Se agotó la cuota diaria del servicio de imágenes. "
                "Vuelva a intentarlo mañana."
            )
        if respuesta.status_code >= 400:
            _log.warning(
                "El probador de IA devolvio %s: %s",
                respuesta.status_code,
                respuesta.text[:300],
            )
            raise ErrorDelProbador(
                f"El servicio de imágenes respondió {respuesta.status_code}."
            )

        return self._extraer(respuesta.json())

    def _extraer(self, datos: dict) -> ResultadoDeProbado:
        """Saca la imagen de la respuesta.

        Se recorren TODAS las partes y no se toma la primera: el modelo suele
        devolver un texto explicativo antes de la imagen, y quedarse con la
        parte [0] devolveria la explicacion en vez del dibujo.
        """
        for candidato in datos.get("candidates", []):
            for parte in candidato.get("content", {}).get("parts", []):
                # La API usa `inlineData` en la respuesta y `inline_data` en la
                # peticion. No es un error de tipeo: es como esta definida.
                datos_en_linea = parte.get("inlineData") or parte.get("inline_data")
                if not datos_en_linea:
                    continue
                crudo = datos_en_linea.get("data")
                if not crudo:
                    continue
                return ResultadoDeProbado(
                    imagen=base64.b64decode(crudo),
                    tipo_mime=datos_en_linea.get("mimeType")
                    or datos_en_linea.get("mime_type")
                    or "image/png",
                    generada_por=f"{self.nombre}:{self._modelo}",
                )

        # Llego una respuesta valida sin imagen. Casi siempre es el filtro de
        # contenido del modelo, que se niega a editar fotos de personas.
        motivo = ""
        for candidato in datos.get("candidates", []):
            if candidato.get("finishReason"):
                motivo = f" (motivo: {candidato['finishReason']})"
                break
        _log.warning("El probador de IA no devolvio imagen%s", motivo)
        raise ErrorDelProbador(
            "El servicio no devolvió una imagen" + motivo + "."
        )
