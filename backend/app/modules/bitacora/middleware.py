"""
P12 - Bitacora / CU-42  |  quien escribe los asientos

POR QUE UN MIDDLEWARE Y NO UNA LLAMADA EN CADA SERVICIO
--------------------------------------------------------
La alternativa era sembrar `bitacora.registrar(...)` por los servicios, en
cada operacion que valga la pena anotar. Se descarto por una sola razon:
**se puede olvidar**. Una ruta nueva que nadie instrumenta no deja rastro, y
el agujero no se nota nunca ---la bitacora no se queja de lo que le falta---.
Justo la operacion que alguien quiera esconder es la que va a estar sin
anotar.

Desde el middleware la cobertura es automatica y completa: toda peticion que
cambia algo queda registrada aunque el caso de uso sea de la semana que
viene.

SOLO LO QUE CAMBIA ALGO
------------------------
`GET` no se anota. Registrar cada lectura llenaria la tabla con miles de
filas por dia ---cada pantalla del catalogo son varias--- y volveria
inutilizable justo la pantalla que existe para buscar. Se anotan POST, PUT,
PATCH y DELETE, que son las que dejan el sistema distinto.

La excepcion es **el inicio de sesion fallido**, que tambien es un POST, y
que es el asiento mas interesante de todos.

NUNCA PUEDE TUMBAR LA PETICION
-------------------------------
Todo lo de aca esta dentro de un `try`. Que la bitacora falle no puede
impedir vender: ver `service.registrar`.
"""

from __future__ import annotations

import logging
import re

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.db.session import get_db
from app.modules.bitacora import service

_log = logging.getLogger("violetboutique.bitacora")

#: Los metodos que dejan el sistema distinto.
METODOS = ("POST", "PUT", "PATCH", "DELETE")

#: Rutas que NO se anotan aunque cambien algo.
#:
#: - El webhook de la pasarela (CU-28) llega miles de veces con reintentos y
#:   no lo hace una persona; su rastro propio esta en `pago`.
#: - La bitacora misma no se anota a si misma: no cambia nada y solo se
#:   leeria.
SIN_ANOTAR = ("/webhooks/", "/bitacora")

#: De `POST /api/v1/catalogo/productos/12/variantes` saca («producto», «12»).
#:
#: Se queda con el PRIMER recurso identificado de la ruta, que es el que la
#: operacion tiene como sujeto: una variante que se crea bajo el producto 12
#: se anota contra ese producto, que es como lo va a buscar quien revise.
_SEGMENTO = re.compile(r"^[0-9]+$")

#: Como se llama cada operacion segun el metodo.
ACCIONES = {
    "POST": "CREAR",
    "PUT": "MODIFICAR",
    "PATCH": "MODIFICAR",
    "DELETE": "ELIMINAR",
}


def _singular(recurso: str) -> str:
    """`productos` -> `producto`. Sin diccionario: el plural castellano de
    los recursos de esta API es siempre `-s` o `-es`."""
    if recurso.endswith("es") and len(recurso) > 4:
        return recurso[:-2]
    return recurso[:-1] if recurso.endswith("s") else recurso


def _sujeto(ruta: str) -> tuple[str | None, str | None]:
    """El recurso y su identificador, deducidos de la ruta."""
    partes = [p for p in ruta.split("/") if p and p not in ("api", "v1")]
    entidad: str | None = None
    entidad_id: str | None = None
    for i, parte in enumerate(partes):
        if _SEGMENTO.match(parte):
            if i > 0:
                entidad = _singular(partes[i - 1])
                entidad_id = parte
            break
    if entidad is None and partes:
        # Sin identificador en la ruta: es un alta. El recurso es el ultimo
        # segmento, que es la coleccion donde se creo.
        entidad = _singular(partes[-1])
    return entidad, entidad_id


def _ip_de(peticion: Request) -> str | None:
    """La IP de quien pidio, detras del balanceador de Railway.

    `peticion.client.host` ahi dentro es la del balanceador, la misma para
    todos: inutil para una bitacora. La de verdad viene en `X-Forwarded-For`
    y es la PRIMERA de la lista ---las siguientes las agregaron los saltos
    intermedios---.
    """
    reenviada = peticion.headers.get("x-forwarded-for")
    if reenviada:
        return reenviada.split(",")[0].strip()[:60]
    return peticion.client.host if peticion.client else None


class BitacoraMiddleware(BaseHTTPMiddleware):
    """Anota toda peticion que cambie algo."""

    async def dispatch(self, peticion: Request, siguiente):
        respuesta = await siguiente(peticion)

        try:
            # EN UN HILO APARTE, no en el bucle de eventos. `dispatch` es
            # asincrono y la escritura del asiento es una consulta
            # bloqueante: hacerla aca dentro frena el servidor entero
            # mientras dura, en TODA peticion que cambie algo. Las rutas
            # sincronas de FastAPI ya corren asi; el middleware hay que
            # mandarlo a mano.
            await run_in_threadpool(self._anotar, peticion, respuesta)
        except Exception as e:  # noqa: BLE001 - jamas escala a la respuesta
            _log.warning("La bitácora falló y la petición siguió: %s", e)

        return respuesta

    def _anotar(self, peticion: Request, respuesta) -> None:
        ruta = peticion.url.path
        if peticion.method not in METODOS:
            return
        if any(t in ruta for t in SIN_ANOTAR):
            return

        estado = respuesta.status_code
        # 401 y 403 SI se anotan, y son de los asientos que mas importan: son
        # los intentos de hacer algo sin permiso. 404 y 422 tambien, porque
        # un barrido de rutas se ve como una hilera de ellos.
        exito = estado < 400

        # Puesto por `get_usuario_actual` cuando el token resolvio. En un
        # login fallido no hay nadie, y es justo lo que hay que registrar.
        usuario = getattr(peticion.state, "usuario", None)
        # Puesto por la ruta de login: el correo que se intento, que el
        # middleware no puede leer del cuerpo sin consumir el flujo.
        intento = getattr(peticion.state, "bitacora_actor", None)

        accion = ACCIONES.get(peticion.method, peticion.method)
        entidad, entidad_id = _sujeto(ruta)

        if ruta.endswith("/auth/login"):
            accion = "INICIAR_SESION" if exito else "INTENTO_FALLIDO"
            entidad, entidad_id = None, None
        elif ruta.endswith("/auth/logout"):
            accion = "CERRAR_SESION"
            entidad, entidad_id = None, None
        elif not exito:
            accion = f"{accion}_RECHAZADO"

        # SESION PROPIA, no la de la peticion: la de la peticion ya se
        # cerro cuando el middleware corre, y si hubiera fallado habria
        # hecho rollback --- llevandose el asiento de la operacion fallida,
        # que es justo la que mas interesa guardar.
        #
        # SE PIDE POR `get_db`, NO POR `SessionLocal` DIRECTO. Parece un
        # rodeo y no lo es: las pruebas sustituyen la dependencia `get_db`
        # para apuntar a la base de pruebas, pero NO tocan `SessionLocal`,
        # que sigue leyendo `DATABASE_URL` del `.env` --- o sea, produccion.
        # Llamando a `SessionLocal()` a secas, correr la bateria de pruebas
        # escribiria asientos en Supabase.
        generador = peticion.app.dependency_overrides.get(get_db, get_db)()
        db = next(generador)
        try:
            service.registrar(
                db,
                accion=accion,
                metodo=peticion.method,
                ruta=ruta,
                estado_http=estado,
                exito=exito,
                usuario_id=getattr(usuario, "id", None),
                actor=getattr(usuario, "correo", None) or intento,
                rol=getattr(usuario, "rol", None),
                entidad=entidad,
                entidad_id=entidad_id,
                ip=_ip_de(peticion),
                agente=peticion.headers.get("user-agent"),
                detalle=getattr(peticion.state, "bitacora_detalle", None),
            )
        finally:
            generador.close()
