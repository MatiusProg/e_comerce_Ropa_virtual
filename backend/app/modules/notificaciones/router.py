"""
P13 - Notificaciones / CU-40  |  capa: router

DOS ROUTERS, PORQUE SON DOS AMBITOS
-----------------------------------
`router` vive en `/notificaciones` y es de **cualquier usuario autenticado**:
son SUS avisos. No lleva `requiere_roles` y eso no es un olvido --- los cuatro
hechos de CU-40 le llegan a roles distintos (Encargado y Cliente), y exigir un
rol dejaria a la mitad de los destinatarios sin poder leer lo suyo. El ambito
lo pone el `usuario.id` en el WHERE, no el rol.

`mantenimiento_router` vive en `/mantenimiento/notificaciones` y es del
**Administrador**: dispara el envio de los correos pendientes. Es la misma
separacion y el mismo prefijo aparte que CU-25, por el mismo motivo que explica
`reservas/router.py`: no es una operacion sobre una notificacion, es
mantenimiento del sistema.

NO HAY `POST /notificaciones`
------------------------------
El actor de CU-40 es el **Sistema**. Un endpoint para crear avisos convertiria
a cualquier usuario con sesion en el iniciador del caso de uso, y permitiria
mandarle avisos a otro. Los avisos nacen en los servicios de P6, P8 y P4.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.notificaciones import service
from app.modules.notificaciones.schemas import (
    DespachoOut,
    MarcadasOut,
    PaginaNotificacionesOut,
    ResumenNotificacionesOut,
)

router = APIRouter(
    prefix="/notificaciones",
    tags=["Notificaciones · CU-40"],
    responses={401: {"description": "Falta el token o ya no es válido."}},
)


@router.get(
    "",
    response_model=PaginaNotificacionesOut,
    summary="CU-40 Listar mis avisos",
)
def listar_mis_notificaciones(
    db: DbSession,
    usuario: Usuario,
    solo_no_leidas: Annotated[bool, Query(description="Solo las que no leí.")] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaNotificacionesOut:
    """Los avisos del usuario de la sesión, del más nuevo al más viejo.

    `no_leidas` cuenta **todas** las suyas, no las de esta página: es el número
    de la campanita y no puede cambiar al pasar de hoja.
    """
    return service.listar_mias(
        db,
        usuario.id,
        solo_no_leidas=solo_no_leidas,
        pagina=pagina,
        tamano=tamano,
    )


@router.get(
    "/resumen",
    response_model=ResumenNotificacionesOut,
    summary="CU-40 Cuántos avisos tengo sin leer",
)
def resumen_de_notificaciones(db: DbSession, usuario: Usuario) -> ResumenNotificacionesOut:
    """Lo mínimo para pintar la campanita.

    Se pide en cada pantalla, así que devuelve un entero y no la lista: traer
    decenas de filas para mostrar un número es lo que haría lenta la navegación.
    """
    return service.resumen(db, usuario.id)


@router.post(
    "/{notificacion_id}/leer",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-40 Marcar un aviso como leído",
)
def marcar_leida(notificacion_id: int, db: DbSession, usuario: Usuario) -> None:
    """Marca uno como leído.

    Un aviso que no es suyo responde **404 y no 403**, igual que en CU-02,
    CU-38 y CU-41: un 403 confirmaría que ese número corresponde a un aviso
    real de otra persona.

    Vuelve a marcar uno ya leído sin error —es idempotente— pero no le mueve la
    fecha: cuándo se enteró es un dato histórico.
    """
    if not service.marcar_leida(db, usuario.id, notificacion_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe ese aviso.",
        )


@router.post(
    "/leer-todas",
    response_model=MarcadasOut,
    summary="CU-40 Marcar todos mis avisos como leídos",
)
def marcar_todas_leidas(db: DbSession, usuario: Usuario) -> MarcadasOut:
    """Deja la campanita en cero. Devuelve cuántos marcó."""
    return service.marcar_todas_leidas(db, usuario.id)


# =====================================================================
# Mantenimiento  -  el despachador de correos
# =====================================================================

mantenimiento_router = APIRouter(
    prefix="/mantenimiento/notificaciones",
    tags=["Notificaciones · Mantenimiento"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


@mantenimiento_router.post(
    "/despacho",
    response_model=DespachoOut,
    summary="CU-40 Enviar por correo los avisos pendientes",
)
def despachar(db: DbSession) -> DespachoOut:
    """Manda los avisos que esperan salir por correo.

    Mismo arreglo que la expiración de reservas de CU-25: está pensado para un
    planificador —una tarea de Railway, un cron— y **es idempotente**, porque
    solo mira las pendientes. Correrlo dos veces seguidas no manda nada dos
    veces.

    Se expone además como endpoint, y no solo como script, por los dos motivos
    de siempre: se dispara a mano en la defensa para mostrar el correo llegando,
    y devuelve el resumen de lo que hizo.

    **Un proveedor caído no hace fallar esta llamada**: cada aviso que no sale
    queda marcado FALLIDO con el motivo, y la respuesta lo cuenta.
    """
    return service.despachar_pendientes(db)


@mantenimiento_router.post(
    "/reintento",
    summary="CU-40 Devolver a la cola los avisos que fallaron",
)
def reintentar(db: DbSession) -> dict[str, int]:
    """Pone en PENDIENTE los avisos FALLIDOS para que el despacho los retome.

    Es un paso aparte a propósito: si el despachador reintentara solo, un
    proveedor caído lo dejaría girando sobre las mismas filas dentro de la
    misma corrida. Reintentar es una decisión de quien opera —después de
    arreglar la clave o el remitente—, no del despachador.
    """
    return {"encolados": service.reintentar_fallidas(db)}
