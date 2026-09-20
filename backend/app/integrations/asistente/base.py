"""El asistente conversacional: el contrato que cumple cualquier proveedor.

Este modulo no conoce la base de datos, ni FastAPI, ni ningun caso de uso.
Define que se le pregunta al asistente y que contesta; nada mas.

LA DECISION DE FONDO: EL MODELO NO CONSULTA, LE CONSULTAN
-----------------------------------------------------------
Es la misma de CU-33 y CU-35, y por tercera vez es la que sostiene todo.

Lo natural seria darle al modelo acceso a la base ---herramientas, SQL
generado, lo que sea--- y dejarlo buscar. Se descarto por dos razones y
cualquiera de las dos alcanza:

1. **Un modelo con acceso a la base puede leer lo que no le toca.** La
   pregunta «cuanto gasto Karen el mes pasado» tendria respuesta. Acotar eso
   desde el prompt es pedirle al modelo que se autolimite, y eso no es un
   control de acceso.
2. **Inventa.** Preguntado por una prenda que no existe, un modelo suelto
   describe una plausible. En una tienda eso no es un error de formato: es
   prometer algo que no se puede vender.

Aca el orden es el inverso: **el sistema arma el contexto con datos reales y
ya filtrados por quien pregunta, y el modelo solo redacta sobre eso.** Lo
peor que puede hacer entonces es explicar mal algo cierto.

POR QUE UNA SOLA LLAMADA Y NO DOS
----------------------------------
La alternativa era clasificar primero la pregunta ---«esto es sobre pedidos»---
y recien despues buscar. Son dos viajes al modelo, y CU-35 ya midio lo que
cuesta cada uno: entre 3 y 25 segundos. Cuarenta segundos para contestar
«cuanto sale la blusa» no es un asistente, es una espera.

Se manda todo el contexto de una: es mas largo en tokens y mucho mas corto
en tiempo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ErrorDelAsistente(Exception):
    """El asistente no pudo contestar. La pantalla lo dice y ofrece el menu."""


class AsistenteNoConfigurado(ErrorDelAsistente):
    """No hay proveedor de IA. Distinto de «fallo»: nunca hubo con que."""


@dataclass(frozen=True)
class Contexto:
    """Los datos REALES sobre los que el asistente puede contestar.

    Todo lo de aca ya salio de la base filtrado por quien pregunta: los
    pedidos y las reservas son **suyos**, y el catalogo es el publico. El
    proveedor no tiene forma de pedir mas.
    """

    #: Como se llama quien pregunta, para que la respuesta no sea impersonal.
    nombre: str

    #: Lineas del catalogo: «Blusa Aurora | Blusas | desde Bs 250 | hay».
    #:
    #: Texto plano y no objetos: lo unico que se hace con esto es ponerlo en
    #: un prompt, y una estructura obligaria a serializarla igual.
    catalogo: tuple[str, ...] = ()

    #: Los pedidos del cliente, del mas nuevo al mas viejo.
    pedidos: tuple[str, ...] = ()

    #: Sus reservas vivas.
    reservas: tuple[str, ...] = ()

    #: Sus medidas, si las cargo (CU-21). Sirve para «que talla me queda».
    medidas: str | None = None

    #: Datos sueltos que no entran en las listas: cuantas sucursales hay, el
    #: horario, lo que haga falta contestar sin buscar.
    datos: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Respuesta:
    """Lo que el asistente contesto."""

    texto: str

    #: Codigos de producto que la respuesta menciona, para que la pantalla
    #: los pueda ofrecer como enlaces.
    #:
    #: **Se validan contra el catalogo antes de devolverse**: un codigo que
    #: el modelo invente no llega a la pantalla. Es la misma comprobacion que
    #: hace CU-35 con el tipo de reporte.
    productos: tuple[int, ...] = ()


@runtime_checkable
class ProveedorAsistente(Protocol):
    """Lo que tiene que saber hacer un asistente."""

    nombre: str
    disponible: bool

    def responder(
        self, pregunta: str, contexto: Contexto, historial: list[tuple[str, str]]
    ) -> Respuesta:
        """Contesta la pregunta usando SOLO lo que hay en el contexto.

        `historial` son los turnos anteriores de esta conversacion, como
        pares `(pregunta, respuesta)`. Sin el, «¿y en talla M?» no significa
        nada --- y esa es la mitad de lo que hace conversacional a un
        asistente.

        Lanza `ErrorDelAsistente` si no puede. **No devuelve una respuesta
        inventada como respaldo**: decir «no pude» es correcto, contestar
        cualquier cosa no.
        """
        ...
