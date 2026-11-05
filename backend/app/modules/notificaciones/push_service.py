"""
P13 - Notificaciones / CU-42 Enviar avisos push  |  capa: servicio

El push es un CANAL más de la notificación de CU-40, como el correo: el aviso
nace en la tabla `notificacion` dentro de la transacción del hecho, y el push
sale DESPUÉS del commit. Mandarlo antes sería avisar algo que todavía se puede
deshacer, y un push no se puede retirar.

QUIÉN LO DESPACHA Y CUÁNDO
--------------------------
  - `despachar(db, ids)`: lo llama quien acaba de crear avisos y ya confirmó
    —la sincronización de CU-17 al terminar el lote—, para que el teléfono
    vibre en el momento y no cuando pase el planificador.
  - `despachar(db)`: sin ids, toma las PENDIENTES. Es lo que corre el
    mantenimiento (`POST /mantenimiento/notificaciones/despacho`), igual que
    el correo, y recoge cualquier aviso de otro caso de uso.

UN FALLO DEL PUSH NO ROMPE NADA
-------------------------------
Misma regla que el correo: el aviso ya está en la campanita. Un canal caído
deja la notificación FALLIDA con el motivo; un dispositivo que ya no existe
(app desinstalada, permiso revocado) se borra para no volver a intentarlo.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.config import settings
from app.integrations.push import AvisoPush, Destino, ErrorDePush, enviar
from app.modules.notificaciones.models import Notificacion, SuscripcionPush
from app.modules.notificaciones.schemas import (
    ConfiguracionPushOut,
    DespachoOut,
    SuscripcionPushIn,
    SuscripcionPushOut,
)

log = logging.getLogger(__name__)

TOPE_POR_DESPACHO = 100


# =====================================================================
# Los dispositivos
# =====================================================================

def configuracion() -> ConfiguracionPushOut:
    return ConfiguracionPushOut(
        clave_publica_vapid=settings.PUSH_VAPID_PUBLICA or None,
        simulado=settings.PUSH_PROVEEDOR.strip().lower() == "simulado",
    )


def tiene_dispositivos(db: Session, usuario_id: int) -> bool:
    return bool(
        db.scalar(select(exists().where(SuscripcionPush.usuario_id == usuario_id)))
    )


def registrar(db: Session, usuario_id: int, datos: SuscripcionPushIn) -> SuscripcionPushOut:
    """Alta (o renovación) de un dispositivo. **Hace commit.**

    Idempotente por la dirección: la app registra su token en cada inicio de
    sesión y el navegador reenvía su suscripción; no se duplican. Si el
    dispositivo era de otra persona de la misma tienda —el mismo teléfono de
    la caja con otro cajero—, pasa a quien inició sesión ahora.
    """
    fila = db.scalar(select(SuscripcionPush).where(SuscripcionPush.direccion == datos.direccion))
    if fila is None:
        fila = SuscripcionPush(direccion=datos.direccion)
        db.add(fila)
    fila.usuario_id = usuario_id
    fila.canal = datos.canal
    fila.clave_p256dh = datos.clave_p256dh
    fila.clave_auth = datos.clave_auth
    fila.dispositivo = (datos.dispositivo or "").strip() or None
    db.commit()
    db.refresh(fila)
    return SuscripcionPushOut(
        id=fila.id, canal=fila.canal, dispositivo=fila.dispositivo, creada_en=fila.creada_en
    )


def dar_de_baja(db: Session, usuario_id: int, direccion: str) -> bool:
    """El usuario cerró sesión o apagó los avisos en ese dispositivo."""
    r = db.execute(
        delete(SuscripcionPush).where(
            SuscripcionPush.usuario_id == usuario_id, SuscripcionPush.direccion == direccion
        )
    )
    db.commit()
    return bool(r.rowcount)


def mis_dispositivos(db: Session, usuario_id: int) -> list[SuscripcionPushOut]:
    filas = db.scalars(
        select(SuscripcionPush)
        .where(SuscripcionPush.usuario_id == usuario_id)
        .order_by(SuscripcionPush.creada_en.desc())
    )
    return [
        SuscripcionPushOut(id=f.id, canal=f.canal, dispositivo=f.dispositivo, creada_en=f.creada_en)
        for f in filas
    ]


# =====================================================================
# El despachador
# =====================================================================

def _aviso_de(n: Notificacion) -> AvisoPush:
    datos = {"notificacion_id": str(n.id), "tipo": n.tipo}
    if n.entidad:
        datos["entidad"] = n.entidad
    if n.entidad_id is not None:
        datos["entidad_id"] = str(n.entidad_id)
    return AvisoPush(titulo=n.titulo, cuerpo=n.cuerpo, enlace=n.enlace, datos=datos)


def _entregar(db: Session, n: Notificacion) -> tuple[bool, str | None]:
    """Manda a todos los dispositivos de la persona. (llegó a alguno, error)."""
    dispositivos = list(
        db.scalars(select(SuscripcionPush).where(SuscripcionPush.usuario_id == n.destinatario_id))
    )
    if not dispositivos:
        return False, None
    aviso = _aviso_de(n)
    alguno, ultimo_error = False, None
    for d in dispositivos:
        destino = Destino(
            canal=d.canal,
            direccion=d.direccion,
            clave_p256dh=d.clave_p256dh,
            clave_auth=d.clave_auth,
        )
        try:
            enviar(destino, aviso)
        except ErrorDePush as e:
            ultimo_error = str(e)[:300]
            if e.invalida:
                db.delete(d)
            log.warning("CU-42: push %s a %s falló: %s", n.id, d.canal, e)
        except Exception as e:  # noqa: BLE001
            ultimo_error = f"{type(e).__name__}: {e}"[:300]
            log.exception("CU-42: error inesperado mandando el push %s", n.id)
        else:
            alguno = True
            d.usada_en = tiempo.ahora()
    return alguno, ultimo_error


def despachar(
    db: Session, ids: list[int] | None = None, *, limite: int = TOPE_POR_DESPACHO
) -> DespachoOut:
    """Manda por push los avisos PENDIENTES (todos, o solo `ids`). Confirma
    uno por uno, por la misma razón que el correo: un corte a la mitad no
    puede hacer que se repitan los que ya salieron."""
    consulta = select(Notificacion).where(Notificacion.push_estado == "PENDIENTE")
    if ids is not None:
        if not ids:
            return DespachoOut(intentadas=0, enviadas=0, fallidas=0)
        consulta = consulta.where(Notificacion.id.in_(ids))
    pendientes = list(
        db.scalars(consulta.order_by(Notificacion.creada_en.asc()).limit(limite))
    )
    enviadas = fallidas = 0
    for n in pendientes:
        llego, error = _entregar(db, n)
        if llego:
            n.push_estado = "ENVIADO"
            n.push_enviado_en = tiempo.ahora()
            n.push_error = None
            enviadas += 1
        elif error is None:
            # Se quedó sin dispositivos entre que nació y ahora.
            n.push_estado = "OMITIDO"
        else:
            n.push_estado = "FALLIDO"
            n.push_error = error
            fallidas += 1
        db.commit()
    return DespachoOut(intentadas=len(pendientes), enviadas=enviadas, fallidas=fallidas)


def despachar_sin_fallar(db: Session, ids: list[int]) -> None:
    """Para llamar al final de una operación ya confirmada: el push es un
    extra y nunca puede convertir un éxito en un error 500."""
    try:
        despachar(db, ids)
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("CU-42: no se pudieron despachar los push %s", ids)
