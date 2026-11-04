"""Avisos push (CU-42). Punto de entrada único del sistema hacia el push.

    from app.integrations.push import AvisoPush, Destino, enviar

    enviar(Destino(canal="FCM", direccion=token), AvisoPush(titulo=..., cuerpo=...))

Con PUSH_PROVEEDOR=simulado (local y pruebas) los dos canales van al simulado.
Con PUSH_PROVEEDOR=real, FCM va a Firebase y WEBPUSH al servicio del navegador.
Como en el correo, un nombre desconocido falla al construir: degradar en
silencio haría parecer que salen avisos que no recibe nadie.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.integrations.push.base import CANALES, AvisoPush, Destino, ErrorDePush, ProveedorPush
from app.integrations.push.fcm import ProveedorFcm
from app.integrations.push.simulado import ProveedorSimulado
from app.integrations.push.webpush import ProveedorWebPush

__all__ = ["CANALES", "AvisoPush", "Destino", "ErrorDePush", "enviar", "proveedor_de"]


@lru_cache
def _proveedores() -> dict[str, ProveedorPush]:
    modo = settings.PUSH_PROVEEDOR.strip().lower()
    if modo == "simulado":
        simulado = ProveedorSimulado()
        return {"FCM": simulado, "WEBPUSH": simulado}
    if modo == "real":
        return {"FCM": ProveedorFcm(), "WEBPUSH": ProveedorWebPush()}
    raise ValueError(f"PUSH_PROVEEDOR={settings.PUSH_PROVEEDOR!r} no existe. Use simulado o real.")


def proveedor_de(canal: str) -> ProveedorPush:
    return _proveedores()[canal]


def enviar(destino: Destino, aviso: AvisoPush) -> None:
    """Entrega el aviso por el canal del destino. Levanta `ErrorDePush`."""
    proveedor_de(destino.canal).enviar(destino, aviso)
