"""Ordena las candidatas de CU-33 con un modelo de TEXTO de Google.

POR QUE ESTE SI FUNCIONA Y EL DEL PROBADOR NO
----------------------------------------------
Comprobado el 18/09/2026 con la clave de la cuenta: los modelos de IMAGEN de
Gemini contestan `limit: 0` en la primera llamada --- no estan en el plan
gratuito ---, y por eso el probador de CU-21 esta apagado. Los de TEXTO si
responden con la misma clave.

Esto ordena texto. Recibe una lista de prendas y devuelve cuales poner
primero: no genera imagenes, no necesita el plan de pago.

LO QUE SE LE MANDA
-------------------
Las candidatas que el filtro determinista ya aprobo, y un perfil SIN datos
personales --- talla, categorias preferidas, nombres de prendas que conoce ---.
El modelo no necesita saber quien es la persona para ordenar ropa, y esto sale
hacia un tercero.

LO QUE SE HACE CON LO QUE DEVUELVE
-----------------------------------
No se confia. Todo identificador que no este en las candidatas se descarta, y
los motivos se recortan. Un modelo puede inventar un producto que no existe, y
mostrarlo seria ofrecerle al cliente algo que la tienda no tiene.
"""

from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings
from app.integrations.recomendador.base import (
    Candidata,
    ErrorDelRecomendador,
    PerfilDelCliente,
    Sugerencia,
)

_log = logging.getLogger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

#: Los modelos de TEXTO que se prueban, EN ORDEN.
#:
#: POR QUE HAY UN SEGUNDO Y NO UNO SOLO
#: -------------------------------------
#: Medido el 18/09: `gemini-3.6-flash` contesta 503 «currently experiencing
#: high demand» de forma intermitente --- la misma peticion funciono un minuto
#: antes ---. Es saturacion del servicio, no un error nuestro, y la
#: degradacion a popularidad la absorbe sin romper nada.
#:
#: Pero degradar en la defensa significa mostrar la lista SIN los motivos, que
#: es justo lo que hay que lucir. El segundo modelo es mas chico y esta menos
#: pedido: cuando el primero se satura, este suele contestar.
#:
#: Solo se reintenta ante 503 y 429 de cuota. Un 400 ---peticion mal armada---
#: fallaria igual con el otro modelo, y reintentarlo seria gastar el doble
#: para obtener el mismo error.
_MODELOS_POR_DEFECTO = ("gemini-3.6-flash", "gemini-3.5-flash-lite")

#: Cuanto se recorta un motivo. Va debajo de la prenda, en una tarjeta de
#: catalogo: mas largo se corta en pantalla igual, y peor.
_LARGO_MAXIMO_MOTIVO = 90

_INSTRUCCION = """\
Sos el asistente de una tienda de ropa femenina en Bolivia. Te doy el perfil \
de una clienta y una lista de prendas DISPONIBLES en su talla.

Elegí las {cuantas} que mejor le quedarían y ordenálas de mejor a peor.

Reglas:
- Usá SOLO los id de la lista. No inventes prendas.
- Para cada una, escribí un motivo de una línea, menos de 15 palabras, \
dirigido a ella y en segundo persona informal («te», «tu»).
- Si podés, relacioná la prenda con algo que ya conoce.

Respondé SOLO con un JSON de esta forma, sin texto alrededor:
{{"sugerencias": [{{"producto_id": 1, "motivo": "..."}}]}}

PERFIL
{perfil}

PRENDAS DISPONIBLES
{candidatas}
"""


class _Saturado(ErrorDelRecomendador):
    """El modelo no pudo atender AHORA. Otro modelo puede contestar.

    Se distingue de los demas fallos porque es lo unico que tiene sentido
    reintentar: un 400 fallaria igual con otro modelo.
    """


class RecomendadorGemini:
    """Ordena candidatas con el modelo de texto de Google."""

    nombre = "gemini"
    disponible = True

    def __init__(self) -> None:
        if not settings.IA_API_KEY:
            raise ValueError(
                "IA_PROVEEDOR=gemini exige IA_API_KEY. Sin la clave, toda "
                "peticion se rechaza y el recomendador degradaria siempre."
            )
        self._clave = settings.IA_API_KEY
        # IA_MODELO fija UNO y desactiva la reserva: si alguien eligio un
        # modelo a mano, caer en otro distinto sin avisar seria desobedecerlo.
        self._modelos = (
            (settings.IA_MODELO,) if settings.IA_MODELO else _MODELOS_POR_DEFECTO
        )

    def ordenar(
        self,
        perfil: PerfilDelCliente,
        candidatas: list[Candidata],
        cuantas: int,
    ) -> list[Sugerencia]:
        if not candidatas:
            return []

        texto = _INSTRUCCION.format(
            cuantas=cuantas,
            perfil=_describir_perfil(perfil),
            candidatas=_describir_candidatas(candidatas),
        )

        ultimo: ErrorDelRecomendador | None = None
        for modelo in self._modelos:
            try:
                return self._intentar(modelo, texto, candidatas, cuantas)
            except _Saturado as e:
                _log.warning(
                    "El modelo %s esta saturado; se prueba el siguiente.", modelo
                )
                ultimo = ErrorDelRecomendador(str(e))
        raise ultimo or ErrorDelRecomendador("Ningún modelo respondió.")

    def _intentar(
        self,
        modelo: str,
        texto: str,
        candidatas: list[Candidata],
        cuantas: int,
    ) -> list[Sugerencia]:
        cuerpo = {"model": modelo, "input": [{"type": "text", "text": texto}]}

        try:
            respuesta = httpx.post(
                _URL,
                # En cabecera y no en la URL: una clave en la cadena de
                # consulta termina en los registros de cualquier intermediario.
                headers={"x-goog-api-key": self._clave},
                json=cuerpo,
                # 45 s y no 20. Medido el 18/09 con la instruccion real y 30
                # candidatas: el modelo tarda unos 8 s, pero la PRIMERA
                # llamada ---con el establecimiento de conexion TLS--- se paso
                # de 20 y degrado a popularidad sin que nada estuviera mal.
                #
                # Es holgado porque puede serlo: el resultado se guarda 12
                # horas, asi que este tiempo se paga una vez por cliente y por
                # dia, no en cada visita a la pantalla de inicio.
                timeout=httpx.Timeout(45.0, connect=10.0),
            )
        except httpx.HTTPError as e:
            _log.warning("El recomendador no respondio: %s", e)
            raise ErrorDelRecomendador(f"No se pudo consultar: {e}") from e

        if respuesta.status_code == 429:
            # Igual que en el probador: un 429 son dos cosas. `limit: 0` es que
            # el modelo no esta en el plan, y no se arregla esperando.
            texto = respuesta.text
            if "limit: 0" in texto:
                _log.warning(
                    "El modelo de texto %s no esta en el plan: %s",
                    modelo,
                    texto[:300],
                )
                raise ErrorDelRecomendador(
                    f"El modelo «{modelo}» no está habilitado en el plan."
                )
            raise _Saturado("Se agotó la cuota del servicio.")
        if respuesta.status_code == 503:
            # Saturacion del servicio, no un error de la peticion. Otro modelo
            # puede contestar.
            _log.warning(
                "El modelo %s devolvio 503: %s", modelo, respuesta.text[:200]
            )
            raise _Saturado(f"El modelo {modelo} está saturado.")
        if respuesta.status_code >= 400:
            _log.warning(
                "El recomendador devolvio %s: %s",
                respuesta.status_code,
                respuesta.text[:400],
            )
            raise ErrorDelRecomendador(
                f"El servicio respondió {respuesta.status_code}."
            )

        return _leer(respuesta.json(), candidatas, cuantas)


def _describir_perfil(perfil: PerfilDelCliente) -> str:
    lineas = []
    if perfil.talla_habitual:
        lineas.append(f"- Talla habitual: {perfil.talla_habitual}")
    if perfil.categorias_preferidas:
        lineas.append(
            f"- Le interesan: {', '.join(perfil.categorias_preferidas)}"
        )
    if perfil.prendas_conocidas:
        lineas.append(
            f"- Ya compró o guardó: {', '.join(perfil.prendas_conocidas)}"
        )
    if perfil.temporada:
        lineas.append(f"- Temporada vigente: {perfil.temporada}")
    # Una clienta nueva no tiene nada de esto, y el modelo tiene que saberlo en
    # vez de recibir un bloque vacio y suponer.
    return "\n".join(lineas) or "- Sin historial: es su primera visita."


def _describir_candidatas(candidatas: list[Candidata]) -> str:
    return "\n".join(
        f"- id={c.producto_id} | {c.nombre} | {c.categoria} | desde Bs {c.precio_desde}"
        for c in candidatas
    )


def _leer(
    datos: dict, candidatas: list[Candidata], cuantas: int
) -> list[Sugerencia]:
    """Saca las sugerencias de la respuesta, descartando lo que no cuadre."""
    texto = _texto_de(datos)
    if not texto:
        raise ErrorDelRecomendador("El servicio respondió sin texto.")

    try:
        crudo = json.loads(_solo_el_json(texto))
    except (ValueError, TypeError) as e:
        _log.warning("El recomendador no devolvio JSON: %s", texto[:300])
        raise ErrorDelRecomendador("La respuesta no era JSON.") from e

    validos = {c.producto_id for c in candidatas}
    salida: list[Sugerencia] = []
    vistos: set[int] = set()

    for fila in crudo.get("sugerencias", []) or []:
        if not isinstance(fila, dict):
            continue
        pid = fila.get("producto_id")
        if not isinstance(pid, int):
            continue
        # NO SE CONFIA EN LOS IDENTIFICADORES QUE DEVUELVE.
        #
        # El modelo puede nombrar una prenda que no esta en la lista --- pasa,
        # sobre todo con listas largas ---. Mostrarla seria ofrecerle al
        # cliente algo que la tienda no tiene, o que no hay en su talla, que es
        # justo lo que el filtro determinista existia para impedir.
        if pid not in validos or pid in vistos:
            continue
        vistos.add(pid)
        motivo = str(fila.get("motivo") or "").strip()
        if len(motivo) > _LARGO_MAXIMO_MOTIVO:
            motivo = motivo[: _LARGO_MAXIMO_MOTIVO - 1].rstrip() + "…"
        salida.append(Sugerencia(producto_id=pid, motivo=motivo))
        if len(salida) >= cuantas:
            break

    if not salida:
        raise ErrorDelRecomendador(
            "Ninguna de las prendas que devolvió estaba en la lista."
        )
    return salida


def _texto_de(datos: dict) -> str:
    """Busca el texto en la respuesta sin depender de una ruta fija.

    La forma de la respuesta cambio entre versiones de la API, y una ruta
    escrita a mano deja de funcionar sin aviso. Se recorre buscando cadenas.
    """
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
    """Quita lo que el modelo escriba alrededor del JSON.

    Aunque se le pida que responda solo JSON, a veces lo envuelve en un bloque
    de codigo o le antepone una frase. Se toma desde la primera llave hasta la
    ultima.
    """
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio == -1 or fin == -1 or fin <= inicio:
        return texto
    return texto[inicio : fin + 1]
