"""
P13 - Notificaciones / CU-40  |  contrato de la API

No hay ningun esquema de ENTRADA para crear un aviso, y es a proposito: CU-40
lo inicia el **Sistema**, no una persona. Un `POST /notificaciones` dejaria que
cualquiera con sesion se mande avisos a si mismo ---o peor, a otro--- y el
unico actor del caso de uso pasaria a ser cualquier usuario autenticado. Los
avisos nacen desde los servicios de P6, P8 y P4, que son los que saben que el
hecho ocurrio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NotificacionOut(BaseModel):
    """Un aviso tal como lo ve su destinatario."""

    id: int
    tipo: str
    titulo: str
    cuerpo: str

    #: Ruta relativa de la web. La pantalla la usa tal cual en su `routerLink`.
    enlace: str | None

    entidad: str | None
    entidad_id: int | None

    #: **En hora boliviana**, por la misma razon que la bitacora: la convierte
    #: el servidor para que la web y el movil no formateen cada uno con la zona
    #: del aparato. Ver docs/entregas/ciclo-3/hora-boliviana.md.
    creada_en: datetime
    leida_en: datetime | None

    #: El estado del correo viaja al cliente para poder mostrarlo en la
    #: pantalla del Administrador. Para el destinatario comun es informativo:
    #: el aviso ya le llego, lo este leyendo donde lo este leyendo.
    correo_estado: str
    #: CU-42: si el aviso salió también por push.
    push_estado: str = "OMITIDO"


class PaginaNotificacionesOut(BaseModel):
    total: int
    pagina: int
    tamano: int
    #: Cuantas de TODAS las suyas estan sin leer, no cuantas de esta pagina.
    #: Es lo que pinta la campanita, y calcularlo sobre la pagina daria un
    #: numero que cambia al pasar de hoja.
    no_leidas: int
    items: list[NotificacionOut]


class ResumenNotificacionesOut(BaseModel):
    """Lo minimo para la campanita del encabezado.

    Existe aparte de la pagina porque se pide en CADA pantalla: devolver la
    lista entera para pintar un numero seria traer decenas de filas que nadie
    va a mirar.
    """

    no_leidas: int


class MarcadasOut(BaseModel):
    """Cuantas quedaron marcadas como leidas."""

    marcadas: int


class DespachoOut(BaseModel):
    """Resultado de una corrida del despachador de correos.

    `pendientes` son las que quedaron sin salir ---fallaron y se reintentaran---
    y no las que no se intentaron: el despachador intenta todas las que
    encuentra.
    """

    intentadas: int
    enviadas: int
    fallidas: int


# =====================================================================
# CU-42: los dispositivos que reciben push
# =====================================================================


class SuscripcionPushIn(BaseModel):
    """Un dispositivo que acepta avisos push.

    FCM manda el token que Firebase le dio a la app. WEBPUSH manda lo que
    devuelve `PushManager.subscribe()` en el navegador: el endpoint y las dos
    claves con que se cifra el mensaje.
    """

    canal: Literal["FCM", "WEBPUSH"]
    direccion: str = Field(min_length=10, max_length=2000)
    clave_p256dh: str | None = Field(default=None, max_length=200)
    clave_auth: str | None = Field(default=None, max_length=100)
    dispositivo: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def _webpush_con_claves(self) -> "SuscripcionPushIn":
        if self.canal == "WEBPUSH":
            if not (self.clave_p256dh and self.clave_auth):
                raise ValueError("Una suscripción web necesita sus claves p256dh y auth.")
            if not self.direccion.startswith("https://"):
                raise ValueError("El endpoint de Web Push tiene que ser https.")
        return self


class SuscripcionPushOut(BaseModel):
    id: int
    canal: str
    dispositivo: str | None
    creada_en: datetime


class BajaPushIn(BaseModel):
    direccion: str = Field(min_length=10, max_length=2000)


class ConfiguracionPushOut(BaseModel):
    """Lo que la web necesita para suscribirse. Sin clave pública, el botón no
    se muestra: Web Push no está configurado en este servidor."""

    clave_publica_vapid: str | None
    simulado: bool
