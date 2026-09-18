"""Probador por IA: el contrato que cumple cualquier proveedor.

Este modulo no conoce la base de datos, ni FastAPI, ni ningun caso de uso.

QUE ES ESTO, Y QUE NO ES
------------------------
El vestidor de CU-21 pega un PNG recortado sobre el cuerpo siguiendo hombros y
cadera. Es rapido, corre en el telefono y no depende de nadie --- pero la
prenda es **plana**: no se pliega, no se ajusta al torso ni respeta como cae la
tela.

Esto es el otro camino: mandar la foto capturada y la prenda a un modelo que
las componga, y devolver una imagen donde la prenda se ve **puesta**.

**Es una OPCION y no parte del flujo.** El recorrido obligatorio de CU-21
--- camara, prenda encima, capturar, al carrito o a la reserva --- funciona
entero sin esto. Importa por tres razones:

1. **Tarda segundos, no milisegundos.** No puede estar en el camino de una
   camara en vivo.
2. **Depende de un tercero y de una clave.** Si el servicio no responde o la
   cuota se acabo, el caso de uso no se puede caer con el.
3. **Cuesta.** El riesgo R9 del plan es quedarse sin credito antes de la
   defensa, y por eso el proveedor por defecto NO llama a nadie.

LO QUE SE LE MANDA, Y POR QUE ESO
----------------------------------
La foto de la persona y el PNG de la prenda, los dos como bytes. El modelo
recibe las dos imagenes y una instruccion en texto. No se le manda el catalogo,
ni precios, ni el identificador del cliente: nada que no haga falta para
componer una imagen.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ErrorDelProbador(Exception):
    """El proveedor no pudo componer la imagen.

    La levanta el proveedor. El router la traduce a 502: no es un defecto
    nuestro, y el cliente se queda igual con su captura --- que es lo que el
    caso de uso le prometio.
    """


class ProbadorNoConfigurado(ErrorDelProbador):
    """No hay proveedor de IA configurado, o le falta la clave.

    Es distinto de un fallo: no es que el servicio se cayo, es que nadie lo
    encendio. El router lo traduce a 503 y la pantalla oculta el boton, en vez
    de ofrecerlo y fallar al tocarlo.
    """


@dataclass(frozen=True)
class SolicitudDeProbado:
    """Lo que hay que componer."""

    #: La captura del vestidor: la persona, con la prenda plana ya encima.
    #: Se manda CON la superposicion y no la foto limpia a proposito: le dice
    #: al modelo donde va la prenda y de que tamano, que es la mitad del
    #: trabajo. Sin eso hay que describirselo con palabras y acierta menos.
    foto: bytes

    #: El PNG transparente de la variante, tal cual lo sirve el catalogo. Es la
    #: referencia de como es la prenda de verdad: su corte, su color y su
    #: largo.
    prenda: bytes

    #: Como se llama la prenda, para nombrarla en la instruccion. Ayuda al
    #: modelo a entender que es una blusa y no un cartel.
    descripcion: str


@dataclass(frozen=True)
class ResultadoDeProbado:
    """La imagen compuesta."""

    imagen: bytes
    tipo_mime: str

    #: Con que proveedor y modelo se hizo. Viaja hasta la pantalla porque una
    #: imagen generada tiene que poder decir que lo es: mostrarla sin aclararlo
    #: seria hacer pasar por foto algo que no lo es.
    generada_por: str


@runtime_checkable
class ProveedorProbador(Protocol):
    """Lo unico que el sistema le pide a un servicio de probado."""

    #: Nombre con el que se lo elige en PROBADOR_IA_PROVEEDOR.
    nombre: str

    #: Si de verdad compone algo. El proveedor por defecto lo tiene en False, y
    #: es lo que permite que la pantalla esconda el boton en vez de ofrecerlo.
    disponible: bool

    def probar(self, solicitud: SolicitudDeProbado) -> ResultadoDeProbado:
        """Compone la imagen, o levanta ErrorDelProbador."""
        ...
