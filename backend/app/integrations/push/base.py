"""Avisos push: el contrato que cumple cualquier canal (CU-42).

Como el correo (`app/integrations/correo`), este módulo no conoce la base, ni
FastAPI, ni ningún caso de uso: define qué es un aviso push y qué sabe hacer un
canal. Quién lo recibe y cuándo lo decide `notificaciones/push_service.py`.

DOS CANALES, UNA FORMA
----------------------
  FCM       Firebase Cloud Messaging: la app Flutter. El destino es el token
            de registro que Firebase le da al teléfono.
  WEBPUSH   el estándar Web Push con VAPID: la web instalada (PWA). El
            destino es la URL del servicio push del navegador, y además viajan
            las dos claves con que el navegador descifra el mensaje.

Los dos llegan aunque la aplicación esté cerrada: eso es lo que los distingue
de la campanita, que solo se ve con la aplicación abierta.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

CANALES = ("FCM", "WEBPUSH")


class ErrorDePush(Exception):
    """El canal no pudo entregar el aviso.

    `invalida` dice que el destino ya no existe —el usuario desinstaló la app
    o revocó el permiso del navegador—: quien la atrapa borra la suscripción
    en vez de reintentarla para siempre.
    """

    def __init__(self, mensaje: str, *, invalida: bool = False):
        super().__init__(mensaje)
        self.invalida = invalida


@dataclass(frozen=True)
class Destino:
    canal: str
    #: El token de FCM o el endpoint de Web Push.
    direccion: str
    clave_p256dh: str | None = None
    clave_auth: str | None = None


@dataclass(frozen=True)
class AvisoPush:
    titulo: str
    cuerpo: str
    #: Ruta relativa de la web a la que lleva el aviso al tocarlo.
    enlace: str | None = None
    #: Datos para la app: tipo de aviso, entidad e id. Todo texto (FCM lo exige).
    datos: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class ProveedorPush(Protocol):
    nombre: str

    def enviar(self, destino: Destino, aviso: AvisoPush) -> None:
        """Entrega el aviso o levanta `ErrorDePush`."""
        ...
