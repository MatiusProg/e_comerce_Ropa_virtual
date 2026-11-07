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


_INSTRUCCION_CONSULTA = """Sos el analista de datos de una cadena de tiendas de ropa. Un usuario pidió un reporte en lenguaje natural. NO escribís SQL ni inventás datos: traducís el pedido a una ESPECIFICACIÓN en JSON con el vocabulario de abajo, y el sistema la valida y la ejecuta.

Hoy es {hoy}.

MEDIDAS (cada una con las dimensiones por las que se puede agrupar y sus filtros)
{medidas}

VALORES DE FILTRO (id es nombre)
{valores}

Reglas:
- `medida`: UNA clave de MEDIDAS. «Ventas» o «ingresos» sin más es ventas_monto; «más vendidos» es unidades_vendidas; «menor existencia» o «stock» es existencias.
- `agrupar`: lista de 0 a 2 dimensiones de esa medida. «por sucursal» → ["sucursal"]; «por semana» → ["semana"]; «compará las sucursales en los últimos tres meses» → ["mes", "sucursal"]. Como mucho una de tiempo (dia, semana, mes).
- `filtros`: solo los que la medida admite. Para sucursal, categoria, producto y temporada va una LISTA DE IDS (el id, nunca el nombre). canal: PRESENCIAL o DIGITAL. tipo: DEVOLUCION o CAMBIO. bajo_minimo: true para «lo que hay que reponer».
- `desde` y `hasta` en YYYY-MM-DD. «Septiembre» sin año es el último septiembre que ya empezó. «Este mes» es del 1 a hoy; «últimos tres meses» son los 3 meses calendario hasta hoy. Si no dice período, null (el sistema usa los últimos 30 días).
- `orden`: "desc" (lo más alto primero) o "asc" («menor», «peores», «menos»).
- `limite`: «los diez más…» → 10. Si no dice, null.
- `grafico`: "barras", "lineas", "torta" o "tabla". Si pide «gráfico» y agrupa por tiempo, "lineas"; si no, "barras". «torta» o «porcentaje» → "torta".
- `resumen`: frase corta en castellano de lo que entendiste, para que el usuario lo confirme. Ejemplo: "Monto vendido de septiembre por sucursal".
- Si el pedido es AMBIGUO o le falta algo indispensable, o pide algo que ninguna medida cubre (por ejemplo sueldos, clima, datos de otra empresa), respondé {{"entendido": false, "motivo": "<por qué, y qué debería aclarar>"}}.

Respondé SOLO el JSON, sin texto alrededor:
{{"entendido": true, "medida": "...", "agrupar": [], "filtros": {{}}, "desde": null, "hasta": null, "orden": "desc", "limite": null, "grafico": "barras", "resumen": "..."}}

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

    # --- CU-27 · reporte dinámico ------------------------------------------

    def interpretar_consulta(self, texto: str, vocabulario: dict, hoy: date) -> dict | None:
        if not texto.strip():
            return None
        instruccion = _INSTRUCCION_CONSULTA.format(
            hoy=hoy.isoformat(),
            medidas=_describir_medidas(vocabulario),
            valores=_describir_valores(vocabulario),
            texto=texto.strip()[:500],
        )
        ultimo: ErrorDelInterprete | None = None
        for modelo in self._modelos:
            try:
                return self._pedir_json(modelo, instruccion)
            except _Saturado as e:
                _log.warning("El modelo %s esta saturado; se prueba otro.", modelo)
                ultimo = ErrorDelInterprete(str(e))
        raise ultimo or ErrorDelInterprete("Ningún modelo respondió.")

    def _pedir_json(self, modelo: str, instruccion: str) -> dict | None:
        try:
            respuesta = httpx.post(
                _URL,
                headers={"x-goog-api-key": self._clave},
                json={"model": modelo, "input": [{"type": "text", "text": instruccion}]},
                timeout=httpx.Timeout(22.0, connect=8.0),
            )
        except httpx.TimeoutException as e:
            raise _Saturado(f"El modelo {modelo} no contestó a tiempo.") from e
        except httpx.HTTPError as e:
            raise ErrorDelInterprete(f"No se pudo consultar: {e}") from e
        if respuesta.status_code in (429, 503):
            raise _Saturado(f"El modelo {modelo} no atendió ({respuesta.status_code}).")
        if respuesta.status_code >= 400:
            _log.warning("El interprete devolvio %s: %s", respuesta.status_code,
                         respuesta.text[:300])
            raise ErrorDelInterprete(f"El servicio respondió {respuesta.status_code}.")
        texto = _texto_de(respuesta.json())
        if not texto:
            raise ErrorDelInterprete("El servicio respondió sin texto.")
        try:
            crudo = json.loads(_solo_el_json(texto))
        except (ValueError, TypeError) as e:
            raise ErrorDelInterprete("La respuesta no era JSON.") from e
        return crudo if isinstance(crudo, dict) else None


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


def _describir_medidas(vocabulario: dict) -> str:
    lineas = []
    for clave, m in vocabulario.get("medidas", {}).items():
        extra = "" if m.get("usa_periodo", True) else " (NO usa período: es la foto de hoy)"
        lineas.append(
            f"- {clave}: {m['etiqueta']}{extra} | agrupar: {', '.join(m['dimensiones'])}"
            f" | filtros: {', '.join(m['filtros'])}"
        )
    return "\n".join(lineas)


def _describir_valores(vocabulario: dict) -> str:
    lineas = []
    for campo, valores in vocabulario.get("valores", {}).items():
        if valores:
            lineas.append(f"{campo}=[" + ", ".join(f"{k} es {v}" for k, v in valores.items()) + "]")
    return "\n".join(lineas)
