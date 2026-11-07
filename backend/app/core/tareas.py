"""
Las tareas automáticas: lo que hace el actor A6, el Sistema, sin que nadie
apriete un botón.

QUÉ CORRE
---------
Cada `TAREAS_INTERVALO_MINUTOS`, por cada empresa activa:

  - la copia de seguridad automática (CU-40, RF-61): sale sola si ya pasó el
    intervalo del plan; si no, no hace nada;
  - las ofertas de fuera de temporada (CU-32): crea y cierra las automáticas;
  - la expiración de reservas (CU-25) y de pedidos sin pagar (CU-27):
    devuelve el stock apartado que nadie fue a buscar o pagar;
  - el despacho de avisos por correo (CU-40) y por push (CU-42).

Y una vez por vuelta, para toda la plataforma, las suscripciones vencidas
(CU-03). Todas son idempotentes —ya lo eran, porque se pensaron para un
planificador—: correr una vuelta de más no repite nada.

Los endpoints de `/mantenimiento/...` siguen existiendo: sirven para
dispararlas a mano en la defensa y para ver qué hicieron.

POR QUÉ ADENTRO DEL BACKEND Y NO UN CRON APARTE
-----------------------------------------------
Decisión de Luis (05/11): es lo más barato en Railway. Un servicio de cron
aparte, o un `--loop &` en el arranque como en PROYECTO_MEDICOS, es otro
proceso Python con su propia RAM. Esto es una tarea `asyncio` que duerme en
el mismo proceso y despierta cada tanto.

DOS WORKERS, UNA SOLA VUELTA
----------------------------
gunicorn arranca 2 workers y cada uno arranca su tarea. Para que no corran
dos vueltas a la vez se toma `pg_try_advisory_lock` en la base: el que lo
consigue corre; el otro ve que está tomado y vuelve a dormir. Es un bloqueo
de SESIÓN, así que se pide sobre una conexión propia que se sostiene toda la
vuelta (con el session pooler de Supabase funciona: la conexión es nuestra).

SE PRENDE CON `TAREAS_AUTOMATICAS=on`
------------------------------------
Apagada por omisión: en local y en las pruebas no tiene que correr nada solo.
En Railway se prende con la variable.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.tenencia import EMPRESA_DE_BAJA, fijar_empresa, modo_plataforma

log = logging.getLogger(__name__)

#: La clave del advisory lock. Cualquier número fijo; este dice «VIOLET».
CLAVE_DEL_BLOQUEO = 0x56494F4C4554

#: Cuánto espera tras arrancar antes de la primera vuelta: que el proceso
#: termine de levantar y las migraciones del arranque ya hayan corrido.
ESPERA_INICIAL_SEGUNDOS = 60


@dataclass
class Vuelta:
    """Lo que hizo una vuelta, para el registro y para las pruebas."""

    tomada: bool = False
    empresas: int = 0
    hechas: int = 0
    errores: list[str] = field(default_factory=list)


# --- Las tareas ---------------------------------------------------------------
# Se importan adentro de cada función: este módulo lo importa `main` al
# arrancar, y los servicios importan medio sistema.

def _copia(db: Session, empresa_id: int) -> None:
    from app.modules.datos import respaldos

    respaldos.automatica(db, empresa_id)


def _fuera_de_temporada(db: Session, _: int) -> None:
    from app.modules.catalogo import ofertas_service

    ofertas_service.aplicar(db)


def _reservas(db: Session, _: int) -> None:
    from app.modules.reservas import service

    service.expirar_reservas_vencidas(db)


def _pedidos(db: Session, _: int) -> None:
    from app.modules.ventas import service

    service.expirar_pedidos_vencidos(db)


def _correos(db: Session, _: int) -> None:
    from app.modules.notificaciones import service

    service.despachar_pendientes(db)


def _push(db: Session, _: int) -> None:
    from app.modules.notificaciones import push_service

    push_service.despachar(db)


#: En este orden: primero lo que libera stock y crea avisos, al final el
#: despacho, para que esos avisos salgan en la misma vuelta.
TAREAS_POR_EMPRESA: tuple[tuple[str, Callable[[Session, int], None]], ...] = (
    ("copia automática", _copia),
    ("fuera de temporada", _fuera_de_temporada),
    ("reservas vencidas", _reservas),
    ("pedidos vencidos", _pedidos),
    ("avisos por correo", _correos),
    ("avisos push", _push),
)


def _suscripciones(db: Session) -> None:
    from app.modules.plataforma import suscripciones

    modo_plataforma(db)
    suscripciones.marcar_vencidas(db)


# --- Una vuelta -----------------------------------------------------------------

def _empresas_activas(db: Session) -> list[int]:
    from app.modules.plataforma.models import Empresa

    modo_plataforma(db)
    ids = list(db.scalars(
        select(Empresa.id).where(Empresa.estado != EMPRESA_DE_BAJA).order_by(Empresa.id)
    ))
    db.commit()
    return ids


def _intentar(vuelta: Vuelta, db: Session, nombre: str, tarea: Callable[[], None]) -> None:
    """Una tarea que falla no corta las demás: se deshace, se anota y sigue."""
    try:
        tarea()
        db.commit()
        vuelta.hechas += 1
    except Exception as e:  # noqa: BLE001
        db.rollback()
        vuelta.errores.append(f"{nombre}: {type(e).__name__}: {e}"[:300])
        log.exception("Tareas automáticas: falló «%s»", nombre)


def correr_vuelta(fabrica_de_sesiones: Callable[[], Session] | None = None) -> Vuelta:
    """Una vuelta completa, si nadie más la está corriendo. Sincrónica.

    `fabrica_de_sesiones` es para las pruebas; por omisión, la de la app.
    """
    from app.db.session import SessionLocal, engine

    fabrica = fabrica_de_sesiones or SessionLocal
    vuelta = Vuelta()
    db = fabrica()
    bloqueo = db.get_bind().connect() if fabrica_de_sesiones else engine.connect()
    try:
        tomado = bloqueo.scalar(
            text("SELECT pg_try_advisory_lock(:k)"), {"k": CLAVE_DEL_BLOQUEO}
        )
        bloqueo.commit()
        if not tomado:
            return vuelta  # la está corriendo el otro worker
        vuelta.tomada = True
        try:
            _intentar(vuelta, db, "suscripciones vencidas", lambda: _suscripciones(db))
            empresas = _empresas_activas(db)
            vuelta.empresas = len(empresas)
            for empresa_id in empresas:
                fijar_empresa(db, empresa_id)
                for nombre, tarea in TAREAS_POR_EMPRESA:
                    _intentar(
                        vuelta, db, f"{nombre} (empresa {empresa_id})",
                        lambda t=tarea, e=empresa_id: t(db, e),
                    )
        finally:
            bloqueo.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": CLAVE_DEL_BLOQUEO})
            bloqueo.commit()
    finally:
        bloqueo.close()
        db.close()
    if vuelta.errores:
        log.warning("Tareas automáticas: %d hechas, %d con error.", vuelta.hechas,
                    len(vuelta.errores))
    else:
        log.info("Tareas automáticas: %d hechas en %d empresas.", vuelta.hechas,
                 vuelta.empresas)
    return vuelta


# --- El bucle -----------------------------------------------------------------

def encendidas() -> bool:
    return settings.TAREAS_AUTOMATICAS.strip().lower() in ("on", "1", "true", "si", "sí")


async def _bucle() -> None:
    intervalo = max(1, settings.TAREAS_INTERVALO_MINUTOS) * 60
    await asyncio.sleep(ESPERA_INICIAL_SEGUNDOS)
    while True:
        try:
            # La base es sincrónica: la vuelta corre en un hilo para no
            # trabar las peticiones que atiende este mismo worker.
            await asyncio.to_thread(correr_vuelta)
        except Exception:  # noqa: BLE001 - el bucle no se muere nunca
            log.exception("Tareas automáticas: la vuelta falló entera")
        await asyncio.sleep(intervalo)


@asynccontextmanager
async def ciclo_de_vida(_app):
    """El `lifespan` de FastAPI: arranca el bucle y lo corta al apagar."""
    tarea = None
    if encendidas():
        log.info("Tareas automáticas encendidas: cada %d min.", settings.TAREAS_INTERVALO_MINUTOS)
        tarea = asyncio.create_task(_bucle())
    try:
        yield
    finally:
        if tarea is not None:
            tarea.cancel()
