"""Interpreta el pedido de reporte con el modelo de TEXTO de Google (CU-35).

Reutiliza el mismo modelo y la misma forma de llamada que el recomendador de
CU-33 --- incluido el modelo de reserva ante un 503 ---, porque es el mismo
problema: pedirle texto a Gemini y no confiar en lo que devuelve.

LO QUE SE LE MANDA
-------------------
La frase del usuario, el catalogo de reportes que el sistema sabe generar con
sus filtros validos, y la fecha de hoy. **La fecha importa**: sin ella, «este
mes» no significa nada y el modelo inventa un ano.

LO QUE SE HACE CON LO QUE DEVUELVE
-----------------------------------
Se valida TODO contra el catalogo: un tipo que no existe, un formato que no
es pdf ni xlsx, o un filtro con un valor que el reporte no admite, se
descartan. Lo que queda es necesariamente algo que el sistema puede generar.
"""

from __future__ import annotations

import json
import logging
from datetime import date

import httpx

from app.core.config import settings
from app.integrations.interprete.base import (
    ErrorDelInterprete,
    Pedido,
    ReporteConocido,
)

_log = logging.getLogger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

#: Los mismos que el recomendador, y por lo mismo: el primero se satura.
_MODELOS_POR_DEFECTO = ("gemini-3.6-flash", "gemini-3.5-flash-lite")

_FORMATOS = ("pdf", "xlsx")

_INSTRUCCION = """\
Sos el asistente de una tienda de ropa. El administrador pidió un reporte \
hablando. Traducí su pedido a UNA de las opciones de la lista.

Hoy es {hoy}.

REPORTES DISPONIBLES
{reportes}

FORMATOS: pdf (para imprimir), xlsx (Excel, para seguir trabajándolo).

Reglas:
- Usá SOLO un `tipo` de la lista. Si el pedido no encaja en ninguno, devolvé \
`{{"entendido": false}}`.
- Si no dice el formato, usá "xlsx".
- Interpretá el período en fechas concretas (YYYY-MM-DD). «Este mes» es el mes \
corriente hasta hoy; «el mes pasado» es el anterior completo; «hoy», «ayer», \
«esta semana», «este año» igual. Si no menciona período, dejá desde y hasta en null.
- Los filtros SOLO pueden ser los que el reporte declara, con los valores \
listados. Si no menciona ninguno, dejá el objeto vacío.
- Cada filtro se lista como `campo=[valor es Nombre, ...]`. En el JSON va \
SIEMPRE el **valor**, nunca el nombre: si se dice «proveedor Shein» y la \
lista dice `proveedor_id=[7 es Shein]`, va `"proveedor_id": "7"`. El nombre \
puede venir dicho con otras mayúsculas, acentos o palabras de más («la \
sucursal centro» es «Centro»); si aun así ninguno corresponde, omití ese \
filtro en vez de elegir el más parecido.
- `resumen` es una frase corta en castellano que se le va a mostrar para que \
confirme que entendiste bien. Ejemplo: "Ventas de septiembre, en Excel".

Respondé SOLO con un JSON de esta forma, sin texto alrededor:
{{"entendido": true, "tipo": "...", "formato": "xlsx", "desde": "2026-09-01", \
"hasta": "2026-09-30", "filtros": {{}}, "resumen": "..."}}

PEDIDO
{texto}
"""


class _Saturado(ErrorDelInterprete):
    """El modelo no pudo atender AHORA. Otro modelo puede contestar."""


class InterpreteGemini:
    nombre = "gemini"
    disponible = True

    def __init__(self) -> None:
        if not settings.IA_API_KEY:
            raise ValueError(
                "IA_PROVEEDOR=gemini exige IA_API_KEY. Sin la clave, el pedido "
                "por voz no se puede interpretar."
            )
        self._clave = settings.IA_API_KEY
        self._modelos = (
            (settings.IA_MODELO,) if settings.IA_MODELO else _MODELOS_POR_DEFECTO
        )

    def interpretar(
        self, texto: str, reportes: list[ReporteConocido], hoy: date
    ) -> Pedido | None:
        if not texto.strip() or not reportes:
            return None

        instruccion = _INSTRUCCION.format(
            hoy=hoy.isoformat(),
            reportes=_describir(reportes),
            texto=texto.strip()[:500],
        )

        ultimo: ErrorDelInterprete | None = None
        for modelo in self._modelos:
            try:
                return self._intentar(modelo, instruccion, reportes)
            except _Saturado as e:
                _log.warning("El modelo %s esta saturado; se prueba otro.", modelo)
                ultimo = ErrorDelInterprete(str(e))
        raise ultimo or ErrorDelInterprete("Ningún modelo respondió.")

    def _intentar(
        self, modelo: str, instruccion: str, reportes: list[ReporteConocido]
    ) -> Pedido | None:
        try:
            respuesta = httpx.post(
                _URL,
                headers={"x-goog-api-key": self._clave},
                json={
                    "model": modelo,
                    "input": [{"type": "text", "text": instruccion}],
                },
                # 22 s por modelo, y son dos: 45 s en el peor caso.
                #
                # Medido el 20/09 con frases reales: el modelo contesta entre
                # 7 y 31 segundos, con mucha varianza. Con un solo intento de
                # 30 s fallaban 3 de 7 pedidos --- inaceptable para algo que
                # se demuestra en vivo ---. Cortando antes y pasando al modelo
                # liviano, que suele responder en 2, se recupera casi siempre.
                timeout=httpx.Timeout(22.0, connect=8.0),
            )
        except httpx.TimeoutException as e:
            # UN TIEMPO AGOTADO TAMBIEN ES SATURACION, y por eso pasa al
            # modelo siguiente en vez de rendirse.
            #
            # Antes caia en `ErrorDelInterprete` y el modelo de reserva NUNCA
            # se probaba: el 20/09, 3 de 7 frases se perdian asi teniendo un
            # segundo modelo disponible que contestaba en 2 segundos.
            _log.warning("El modelo %s no contesto a tiempo: %s", modelo, e)
            raise _Saturado(f"El modelo {modelo} no contestó a tiempo.") from e
        except httpx.HTTPError as e:
            _log.warning("El interprete no respondio: %s", e)
            raise ErrorDelInterprete(f"No se pudo consultar: {e}") from e

        if respuesta.status_code in (429, 503):
            raise _Saturado(f"El modelo {modelo} no atendió ({respuesta.status_code}).")
        if respuesta.status_code >= 400:
            _log.warning(
                "El interprete devolvio %s: %s",
                respuesta.status_code,
                respuesta.text[:300],
            )
            raise ErrorDelInterprete(f"El servicio respondió {respuesta.status_code}.")

        return _leer(respuesta.json(), reportes)


def _describir(reportes: list[ReporteConocido]) -> str:
    lineas = []
    for r in reportes:
        detalle = f"- {r.tipo}: {r.titulo}"
        if not r.usa_periodo:
            detalle += " (NO usa período: es la situación actual)"
        if r.filtros:
            # Se le muestra `valor=etiqueta` para que pueda mapear lo que se
            # dijo ---«Shein»--- al identificador que el sistema espera. Con
            # solo los valores, un filtro por nombre es inalcanzable.
            filtros = "; ".join(
                f"{campo}=[" + ", ".join(f"{v} es {e}" for v, e in valores.items()) + "]"
                for campo, valores in r.filtros.items()
            )
            detalle += f" | filtros: {filtros}"
        lineas.append(detalle)
    return "\n".join(lineas)


def _fecha(valor) -> date | None:
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return date.fromisoformat(valor.strip()[:10])
    except ValueError:
        # Una fecha mal formada NO invalida el pedido entero: se pierde el
        # periodo y el reporte sale con el rango por omision, que es mejor
        # que decirle «no entendi» a alguien que dijo el reporte correcto.
        return None


def _leer(datos: dict, reportes: list[ReporteConocido]) -> Pedido | None:
    texto = _texto_de(datos)
    if not texto:
        raise ErrorDelInterprete("El servicio respondió sin texto.")

    try:
        crudo = json.loads(_solo_el_json(texto))
    except (ValueError, TypeError) as e:
        _log.warning("El interprete no devolvio JSON: %s", texto[:300])
        raise ErrorDelInterprete("La respuesta no era JSON.") from e

    if not crudo.get("entendido"):
        return None

    por_tipo = {r.tipo: r for r in reportes}
    tipo = crudo.get("tipo")
    # NO SE CONFIA EN EL TIPO. El modelo puede nombrar un reporte que no
    # existe; generar «lo mas parecido» seria entregarle al administrador algo
    # que no pidio sin que nada se lo advierta.
    if tipo not in por_tipo:
        _log.info("El interprete devolvio un tipo desconocido: %r", tipo)
        return None

    definicion = por_tipo[tipo]
    formato = crudo.get("formato")
    if formato not in _FORMATOS:
        formato = "xlsx"

    # Los filtros tambien se validan contra lo que ESE reporte admite.
    filtros: dict[str, str] = {}
    for campo, valor in (crudo.get("filtros") or {}).items():
        validos = definicion.filtros.get(campo)
        if validos and str(valor) in validos:
            filtros[campo] = str(valor)

    desde = _fecha(crudo.get("desde")) if definicion.usa_periodo else None
    hasta = _fecha(crudo.get("hasta")) if definicion.usa_periodo else None
    if desde and hasta and desde > hasta:
        desde, hasta = hasta, desde

    return Pedido(
        tipo=tipo,
        formato=formato,
        desde=desde,
        hasta=hasta,
        filtros=filtros,
        resumen=str(crudo.get("resumen") or definicion.titulo)[:120],
    )


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


def _solo_el_json(texto: str) -> str:
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1 or fin <= inicio:
        return texto
    return texto[inicio : fin + 1]
