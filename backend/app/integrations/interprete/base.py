"""Interprete de pedidos en lenguaje natural: el contrato del proveedor.

Este modulo no conoce la base de datos, ni FastAPI, ni ningun caso de uso.

QUE HACE, Y QUE NO
------------------
**Traduce una frase a una eleccion entre opciones que ya existen.** Recibe
«dame las ventas de septiembre en Excel» y el catalogo de reportes que el
sistema sabe generar, y devuelve cual, con que periodo, en que formato y con
que filtros.

No genera el reporte, no consulta datos y no inventa reportes: lo unico que
puede devolver es algo que estaba en la lista que se le paso. Es la misma
decision que en el recomendador de CU-33 --- el modelo ORDENA o ELIGE entre
candidatas, nunca produce el contenido --- y por el mismo motivo: lo peor que
puede hacer entonces es elegir mal, no prometer algo que el sistema no tiene.

NO ENTENDER ES UNA RESPUESTA VALIDA
------------------------------------
Devolver `None` cuando la frase no encaja **no es un fallo**. Es preferible a
adivinar: el administrador que pidio ventas y recibe reservas no lo nota
hasta abrir el archivo, y para entonces ya lo mando por correo.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable


class ErrorDelInterprete(Exception):
    """El proveedor no pudo responder. El servicio lo traduce a «no entendi»."""


class InterpreteNoConfigurado(ErrorDelInterprete):
    """No hay proveedor, o le falta la clave. No es que se cayo: no lo encendieron."""


@dataclass(frozen=True)
class ReporteConocido:
    """Un reporte que el sistema sabe generar, tal como se le describe al modelo."""

    tipo: str
    titulo: str
    #: Los filtros que admite: `{campo: [valores validos]}`.
    filtros: dict[str, list[str]] = field(default_factory=dict)
    usa_periodo: bool = True


@dataclass(frozen=True)
class Pedido:
    """Lo que se entendio de la frase."""

    tipo: str
    formato: str
    desde: date | None = None
    hasta: date | None = None
    filtros: dict[str, str] = field(default_factory=dict)

    #: Como se lo va a contar al usuario: «Ventas de septiembre, en Excel».
    #: **Se muestra ANTES de descargar**: es lo que permite darse cuenta de
    #: que el modelo entendio otra cosa sin tener que abrir el archivo.
    resumen: str = ""


@runtime_checkable
class ProveedorInterprete(Protocol):
    nombre: str
    disponible: bool

    def interpretar(
        self, texto: str, reportes: list[ReporteConocido], hoy: date
    ) -> Pedido | None:
        """El pedido entendido, o `None` si la frase no encaja en ninguno."""
        ...
