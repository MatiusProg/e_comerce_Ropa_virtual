"""Correo saliente: el contrato que cumple cualquier proveedor.

Este modulo no conoce la base de datos, ni FastAPI, ni ningun caso de uso.
Define que es un mensaje y que sabe hacer un proveedor; nada mas.

POR QUE HAY UNA COSTURA Y NO UNA LLAMADA DIRECTA
------------------------------------------------
Cuando se escribio esto (15/09/2026) el proyecto todavia NO tenia servicio de
correo contratado, y dos casos de uso lo estrenan: CU-40 (notificaciones) y
CU-41 (recuperar contrasena). La decision del 13/09 fue construir la costura
primero y elegir el proveedor despues, para que la falta de proveedor no
bloqueara el desarrollo.

Con esto, elegir proveedor es agregar un modulo hermano de `consola.py` y
cambiar la variable CORREO_PROVEEDOR en Railway. Ni un caso de uso se entera.

POR QUE API HTTP Y NO SMTP
--------------------------
El proveedor que se agregue deberia hablar por HTTP, no por SMTP. Muchas
plataformas de hospedaje bloquean los puertos de correo de salida y eso se
descubre tarde --- no se verifico si Railway lo hace ---. Un POST no corre ese
riesgo: el contenedor ya sale a internet para Supabase y para la IA.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ErrorDeEnvio(Exception):
    """El proveedor no pudo entregar el mensaje.

    La levanta el proveedor; quien la atrapa decide que hacer. En CU-41 el
    servicio la deja pasar hacia arriba pero el router NO la refleja en la
    respuesta: decirle a quien pide el enlace que el envio fallo revelaria que
    ese correo existe en el sistema.
    """


@dataclass(frozen=True)
class Mensaje:
    """Un correo listo para salir.

    Lleva las dos versiones del cuerpo a proposito. El HTML es lo que ve
    cualquier lector moderno; el texto plano es el respaldo para los que no
    pintan HTML y, sobre todo, lo que hace que el correo no se lea como basura
    en el log del proveedor `consola`.
    """

    destinatario: str
    asunto: str
    cuerpo_texto: str
    cuerpo_html: str


@runtime_checkable
class ProveedorCorreo(Protocol):
    """Lo unico que el sistema le pide a un servicio de correo."""

    #: Nombre con el que se lo elige en la variable CORREO_PROVEEDOR.
    nombre: str

    def enviar(self, mensaje: Mensaje) -> None:
        """Entrega el mensaje, o levanta ErrorDeEnvio si no pudo."""
        ...
