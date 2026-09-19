"""Recomendador: el contrato que cumple cualquier proveedor.

Este modulo no conoce la base de datos, ni FastAPI, ni ningun caso de uso.

QUE HACE EL PROVEEDOR, Y QUE NO
--------------------------------
**Solo ORDENA.** Recibe una lista de candidatas que ya paso el filtro
determinista de CU-33 --- temporada vigente, existencia real, talla del
cliente --- y devuelve las mejores con una justificacion corta.

Nunca elige de la nada. Esa es la decision de fondo del enfoque hibrido y vale
la pena decir por que: un modelo al que se le pide «recomendale algo» inventa
prendas que no existen, o recomienda una talla agotada. Filtrando primero,
**lo peor que puede hacer es ordenar mal** --- y eso no le promete nada al
cliente que la tienda no pueda cumplir.

POR QUE EL PROVEEDOR PUEDE FALLAR SIN QUE PASE NADA
----------------------------------------------------
Depende de un tercero, de una clave y de una cuota. El servicio que lo llama
se queda con las candidatas ordenadas por popularidad cuando esto falla: el
cliente ve recomendaciones igual, sin personalizar. Es el punto 3 de la
decision tecnica, y es lo que evita que el riesgo R9 ---quedarse sin credito
antes de la defensa--- deje una pantalla vacia.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ErrorDelRecomendador(Exception):
    """El proveedor no pudo ordenar. Lo atrapa el servicio y degrada."""


class RecomendadorNoConfigurado(ErrorDelRecomendador):
    """No hay proveedor, o le falta la clave.

    Se distingue de un fallo porque no es que el servicio se cayo: es que
    nadie lo encendio. El servicio degrada igual, pero lo registra distinto
    --- si no, un despliegue sin clave se ve en los registros como un
    proveedor que falla todo el tiempo.
    """


@dataclass(frozen=True)
class Candidata:
    """Una prenda que el filtro determinista ya aprobo."""

    producto_id: int
    nombre: str
    categoria: str
    precio_desde: str
    #: Cuantas se vendieron en la temporada vigente. Es la senal de
    #: popularidad, y tambien el criterio de reserva si el modelo no responde.
    vendidas: int


@dataclass(frozen=True)
class PerfilDelCliente:
    """Lo que se le cuenta al modelo sobre quien pregunta.

    **No lleva nombre, correo ni documento.** El modelo no los necesita para
    ordenar prendas y son datos de una persona que salen hacia un tercero; lo
    que viaja es lo que describe su gusto, no quien es.
    """

    talla_habitual: str | None
    categorias_preferidas: list[str]
    #: Nombres de prendas que compro o marco como favoritas. Es lo que permite
    #: justificar con «combina con la chaqueta que compraste».
    prendas_conocidas: list[str]
    temporada: str | None


@dataclass(frozen=True)
class Sugerencia:
    producto_id: int
    #: Una linea que se le muestra al cliente. Corta a proposito: es una
    #: etiqueta bajo la prenda, no un parrafo.
    motivo: str


@runtime_checkable
class ProveedorRecomendador(Protocol):
    """Lo unico que el sistema le pide a un servicio de recomendacion."""

    nombre: str
    disponible: bool

    def ordenar(
        self,
        perfil: PerfilDelCliente,
        candidatas: list[Candidata],
        cuantas: int,
    ) -> list[Sugerencia]:
        """Devuelve hasta `cuantas` sugerencias, o levanta ErrorDelRecomendador."""
        ...
