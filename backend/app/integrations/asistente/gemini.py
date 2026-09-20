"""CU-34 · El asistente conversacional, contra Gemini.

MISMO CLIENTE QUE EL INTERPRETE Y EL RECOMENDADOR
---------------------------------------------------
La misma URL, la misma cabecera, la misma pareja de modelos y el mismo
respaldo cuando el primero esta saturado. Se repite a proposito en vez de
factorizarlo: las tres costuras son independientes por diseno ---cada una
puede cambiar de proveedor sin tocar a las otras--- y un cliente compartido
las volveria a atar justo por donde se las separo.

EL TIEMPO AGOTADO TAMBIEN ES SATURACION
-----------------------------------------
Es la leccion que costo media medicion en CU-35: si el respaldo solo se
dispara con 429 y 503, el modelo liviano nunca llega a probarse y tres de
cada siete pedidos mueren esperando. Aca esta desde el principio.
"""

from __future__ import annotations

import logging
import re

import httpx

from app.core.config import settings
from app.integrations.asistente.base import (
    Contexto,
    ErrorDelAsistente,
    Respuesta,
)

_log = logging.getLogger("violetboutique.asistente")

_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

#: El rapido primero y el liviano de respaldo. Ver la nota de CU-35.
_MODELOS_POR_DEFECTO = ("gemini-3.6-flash", "gemini-3.5-flash-lite")

#: Cuantos turnos anteriores se le recuerdan.
#:
#: Seis, no todos. Una conversacion larga crece sin limite y termina costando
#: mas tokens el historial que la pregunta; y lo que hace falta para entender
#: «¿y en talla M?» son los dos o tres turnos de antes, no los veinte.
TURNOS_RECORDADOS = 6

_INSTRUCCION = """\
Sos el asistente de Violet Boutique, una tienda de ropa en Santa Cruz, Bolivia.
Estás atendiendo a {nombre}. Tuteá, sé breve y cordial.

REGLA PRINCIPAL, Y NO TIENE EXCEPCIONES
Contestá ÚNICAMENTE con la información que está más abajo. Si la respuesta no
está ahí, decí que no lo sabés y ofrecé dónde mirarlo. **Nunca inventes una
prenda, un precio, una talla, un estado ni una fecha.** Es preferible un «no
lo tengo» a un dato plausible: quien pregunta va a venir a la tienda con esa
respuesta en la mano.

Tampoco prometas nada en nombre de la tienda —descuentos, envíos, plazos— que
no figure abajo.

CÓMO RESPONDER
- En dos o tres frases. Esto se lee en un teléfono.
- Cuando menciones prendas concretas, escribí su código entre corchetes así:
  [#12]. La pantalla los convierte en enlaces. Solo códigos de la lista.
- Si la pregunta no es sobre la tienda, decilo amablemente y volvé al tema.
- Los precios son en bolivianos (Bs).
- **Nada de generalizaciones.** No digas «todas», «siempre» ni «cualquiera»
  sobre el catálogo: nombrá las prendas concretas que cumplen lo que se
  pregunta. Una frase como «tenemos stock en todas las tallas» es falsa en
  cuanto una prenda no lo tenga, y quien la lea va a venir a buscarla.

EL CATÁLOGO
{catalogo}

{pedidos}
{reservas}
{medidas}
{datos}
{historial}
PREGUNTA DE {nombre}
{pregunta}
"""


class _Saturado(ErrorDelAsistente):
    """El modelo no pudo atender AHORA. Otro modelo puede contestar."""


class AsistenteGemini:
    nombre = "gemini"
    disponible = True

    def __init__(self) -> None:
        if not settings.IA_API_KEY:
            raise ValueError(
                "IA_PROVEEDOR=gemini exige IA_API_KEY. Sin la clave, el "
                "asistente no puede contestar."
            )
        self._clave = settings.IA_API_KEY
        self._modelos = (
            (settings.IA_MODELO,) if settings.IA_MODELO else _MODELOS_POR_DEFECTO
        )

    def responder(
        self, pregunta: str, contexto: Contexto, historial: list[tuple[str, str]]
    ) -> Respuesta:
        instruccion = _INSTRUCCION.format(
            nombre=contexto.nombre,
            catalogo="\n".join(contexto.catalogo) or "(el catálogo está vacío)",
            pedidos=_seccion("SUS PEDIDOS", contexto.pedidos),
            reservas=_seccion("SUS RESERVAS", contexto.reservas),
            medidas=(
                f"SUS MEDIDAS\n{contexto.medidas}\n\n" if contexto.medidas else ""
            ),
            datos=_seccion("DATOS DE LA TIENDA", contexto.datos),
            historial=_historial(historial),
            pregunta=pregunta.strip()[:500],
        )

        ultimo: ErrorDelAsistente | None = None
        for modelo in self._modelos:
            try:
                return self._intentar(modelo, instruccion, contexto)
            except _Saturado as e:
                _log.warning("El modelo %s esta saturado; se prueba otro.", modelo)
                ultimo = ErrorDelAsistente(str(e))
        raise ultimo or ErrorDelAsistente("Ningún modelo respondió.")

    def _intentar(self, modelo: str, instruccion: str, contexto: Contexto) -> Respuesta:
        try:
            respuesta = httpx.post(
                _URL,
                headers={"x-goog-api-key": self._clave},
                json={
                    "model": modelo,
                    "input": [{"type": "text", "text": instruccion}],
                },
                timeout=httpx.Timeout(22.0, connect=8.0),
            )
        except httpx.TimeoutException as e:
            # UN TIEMPO AGOTADO TAMBIEN ES SATURACION. Ver la cabecera.
            raise _Saturado(f"El modelo {modelo} no contestó a tiempo.") from e
        except httpx.HTTPError as e:
            raise ErrorDelAsistente(f"No se pudo hablar con el modelo: {e}") from e

        if respuesta.status_code in (429, 503):
            raise _Saturado(f"El modelo {modelo} no atendió ({respuesta.status_code}).")
        if respuesta.status_code >= 400:
            _log.warning(
                "El asistente devolvio %s: %s",
                respuesta.status_code,
                respuesta.text[:300],
            )
            raise ErrorDelAsistente(f"El servicio respondió {respuesta.status_code}.")

        texto = _texto_de(respuesta.json()).strip()
        if not texto:
            raise ErrorDelAsistente("El servicio respondió sin texto.")

        return _leer(texto, contexto)


def _seccion(titulo: str, lineas: tuple[str, ...]) -> str:
    if not lineas:
        return ""
    return f"{titulo}\n" + "\n".join(lineas) + "\n\n"


def _historial(turnos: list[tuple[str, str]]) -> str:
    """Los turnos anteriores, para que «¿y en talla M?» signifique algo."""
    if not turnos:
        return ""
    recientes = turnos[-TURNOS_RECORDADOS:]
    lineas = [f"{p}\n  -> {r}" for p, r in recientes]
    return "LO QUE YA SE HABLÓ\n" + "\n".join(lineas) + "\n\n"


#: `[#12]` en el texto de la respuesta.
#:
#: Tolera lo que el modelo meta adentro del corchete. Se le pide `[#12]` y
#: escribe `[*#12*]` cuando quiere resaltarlo ---medido el 20/09---, y con un
#: patron estricto esa respuesta se quedaba SIN prendas enlazables: el texto
#: nombraba la prenda y la pantalla no la podia ofrecer.
_CODIGO = re.compile(r"\[[^\]]*?#(\d+)[^\]]*?\]")


def _leer(texto: str, contexto: Contexto) -> Respuesta:
    """Saca los productos mencionados y **los valida contra el catalogo**.

    Un codigo que el modelo invente no llega a la pantalla. Es la misma
    comprobacion que hace CU-35 con el tipo de reporte, y por el mismo
    motivo: lo que el modelo devuelve es una propuesta, no un hecho.
    """
    validos = set()
    for linea in contexto.catalogo:
        m = re.match(r"\s*#(\d+)", linea)
        if m:
            validos.add(int(m.group(1)))

    mencionados = []
    for bruto in _CODIGO.findall(texto):
        cual = int(bruto)
        if cual in validos and cual not in mencionados:
            mencionados.append(cual)

    return Respuesta(texto=texto, productos=tuple(mencionados))


def _texto_de(datos: dict) -> str:
    """Busca el texto sin depender de una ruta fija de la respuesta."""
    partes: list[str] = []

    def recorrer(nodo) -> None:
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                if clave in ("text", "output_text") and isinstance(valor, str):
                    partes.append(valor)
                else:
                    recorrer(valor)
        elif isinstance(nodo, list):
            for elemento in nodo:
                recorrer(elemento)

    recorrer(datos)
    return "\n".join(partes)
