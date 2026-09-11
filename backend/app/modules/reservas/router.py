"""
P6 - Reservas  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Implementados en este archivo: CU-22 y CU-23.

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.

UN SOLO ROUTER, DE CLIENTE
--------------------------
CU-22 y CU-23 son del Cliente y van bajo `/reservas`. CU-24 es del Encargado y
mira las reservas *de su sucursal*, que es otro ambito de datos: cuando se
implemente va en un router aparte --- `sucursal_router` --- con su propia
exigencia de rol declarada una sola vez, por la regla de la seccion 6.11.4 de
docs/06-decisiones-tecnicas.md.

LA PROPIEDAD DE LA RESERVA NO SE COMPRUEBA AQUI
-----------------------------------------------
Que una reserva sea de quien la pide se resuelve en el servicio, porque hace
falta leer la fila para saberlo. El router no puede autorizar lo que todavia no
leyo.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.inventario import service as inventario
from app.modules.reservas import service
from app.modules.reservas.models import ESTADOS_RESERVA
from app.modules.reservas.schemas import (
    CancelarReservaIn,
    PaginaReservas,
    ReservaCrearIn,
    ReservaOut,
)

#: Patron para el filtro por estado. Se arma con la constante del modelo para
#: que agregar un estado no exija acordarse de este archivo.
_PATRON_ESTADO = "^(" + "|".join(ESTADOS_RESERVA) + ")$"

router = APIRouter(
    prefix="/reservas",
    tags=["Reservas"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)


def _traducir(error: Exception) -> HTTPException:
    """Convierte los errores de negocio de P6 --- y los de P4 que se filtran
    desde el apartado de stock --- en respuestas HTTP."""
    if isinstance(error, service.ClienteSinFicha):
        return HTTPException(
            409,
            "Su cuenta no tiene una ficha de cliente. Complete su perfil antes "
            "de reservar.",
        )
    if isinstance(error, service.SucursalInexistente):
        return HTTPException(404, "La sucursal indicada no existe.")
    if isinstance(error, service.SucursalInactiva):
        # Excepcion E2.
        return HTTPException(422, "Esa sucursal no está atendiendo.")
    if isinstance(error, service.VarianteInexistente):
        # Excepcion E1. Se devuelven los identificadores para que la interfaz
        # señale las prendas en vez de invalidar la reserva entera.
        return HTTPException(
            422,
            {
                "mensaje": "Alguna de las prendas ya no está en el catálogo.",
                "variantes": error.ids,
            },
        )
    if isinstance(error, service.VarianteInactiva):
        return HTTPException(
            422,
            {
                "mensaje": "Alguna de las prendas dejó de ofrecerse.",
                "variantes": error.ids,
            },
        )
    if isinstance(error, service.FranjaEnElPasado):
        # Excepcion E3.
        return HTTPException(422, "La franja elegida ya pasó.")
    if isinstance(error, service.FranjaDemasiadoLejos):
        # Excepcion E5.
        return HTTPException(
            422,
            f"Solo se puede reservar con hasta {error.horas} horas de "
            "anticipación.",
        )
    if isinstance(error, service.DuracionInvalida):
        # Excepcion E4.
        return HTTPException(
            422,
            f"La franja debe durar entre {error.minimo} y {error.maximo} minutos.",
        )
    if isinstance(error, service.FueraDeHorario):
        # Excepcion E8.
        return HTTPException(
            422,
            f"Esa sucursal atiende de {error.apertura:%H:%M} a "
            f"{error.cierre:%H:%M}. Elija una franja dentro de ese horario.",
        )
    if isinstance(error, service.SinVestidoresLibres):
        # Excepcion E6.
        return HTTPException(
            409,
            f"No quedan probadores libres en esa franja: la sucursal tiene "
            f"{error.capacidad}. Elija otro horario.",
        )
    if isinstance(error, service.ReservaAjena):
        # A propósito un 404 y no un 403: un 403 confirmaría que esa reserva
        # existe, y eso ya es información sobre otro cliente.
        return HTTPException(404, "No encontramos esa reserva.")
    if isinstance(error, service.ReservaInexistente):
        return HTTPException(404, "No encontramos esa reserva.")
    if isinstance(error, service.ReservaNoCancelable):
        # Excepcion E10. El mensaje distingue POR QUE no se puede, porque cada
        # motivo lleva a algo distinto: si ya fue atendida no hay nada que
        # hacer; si ya estaba cancelada, la pantalla solo tiene que refrescar.
        motivos = {
            "ATENDIDA": "Esa reserva ya fue atendida en la sucursal.",
            "CANCELADA": "Esa reserva ya estaba cancelada.",
            "EXPIRADA": "Esa reserva venció y el stock ya se liberó.",
        }
        return HTTPException(
            409, motivos.get(error.estado, "Esa reserva ya no se puede cancelar.")
        )

    # --- Errores que vienen de P4, al apartar el stock ------------------
    if isinstance(error, inventario.StockInsuficiente):
        # Excepcion E9, y el desenlace de una carrera perdida contra otro
        # cliente (riesgo R5).
        return HTTPException(
            409,
            f"Quedan {error.disponible} unidades de una de las prendas y se "
            f"pidieron {error.solicitado}. Puede que alguien la haya reservado "
            "mientras confirmaba.",
        )
    if isinstance(error, inventario.ExistenciaInexistente):
        return HTTPException(
            409, "Una de las prendas no está disponible en esa sucursal."
        )
    return HTTPException(400, "No se pudo completar la operación.")


@router.post(
    "",
    response_model=ReservaOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-22 Crear reserva de prendas",
    responses={
        409: {"description": "Sin probadores libres (E6) o sin stock (E9)."},
        422: {"description": "Prenda o franja inválidas (E1, E3, E4, E5, E8)."},
    },
)
def crear_reserva(
    datos: ReservaCrearIn, db: DbSession, usuario: Usuario
) -> ReservaOut:
    """Pasos 4 a 7: aparta las prendas y deja la reserva en PENDIENTE.

    El cliente sale del token, no del cuerpo: si viniera en el JSON, cualquiera
    podría reservar a nombre de otro.

    Toda la reserva es una sola transacción. Si una prenda se queda sin stock,
    no queda apartada ninguna — y eso importa más acá que en un ingreso, porque
    stock apartado sin reserva que lo explique no lo libera nadie.
    """
    try:
        return service.crear_reserva(db, datos, usuario_id=usuario.id)
    except (service.ErrorDeReservas, inventario.ErrorDeInventario) as error:
        raise _traducir(error)


@router.get(
    "",
    response_model=PaginaReservas,
    summary="CU-22/CU-23 Mis reservas",
)
def listar_mis_reservas(
    db: DbSession,
    usuario: Usuario,
    estado: Annotated[str | None, Query(pattern=_PATRON_ESTADO)] = None,
    vivas: Annotated[
        bool | None,
        Query(description="true: solo PENDIENTE o PREPARADA; false: las cerradas"),
    ] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaReservas:
    """Las reservas del cliente, de la franja más próxima a la más vieja.

    `vivas` existe además del filtro por estado porque la pregunta que hace la
    pantalla casi siempre es «¿qué tengo pendiente?», y eso son dos estados, no
    uno.
    """
    try:
        return service.listar_mis_reservas(
            db,
            usuario_id=usuario.id,
            pagina=pagina,
            tamano=tamano,
            estado=estado,
            vivas=vivas,
        )
    except service.ErrorDeReservas as error:
        raise _traducir(error)


@router.get(
    "/{reserva_id}",
    response_model=ReservaOut,
    summary="CU-22/CU-23 Detalle de una reserva",
    responses={404: {"description": "No existe, o es de otro cliente."}},
)
def obtener_reserva(
    reserva_id: int, db: DbSession, usuario: Usuario
) -> ReservaOut:
    """El detalle de una reserva propia, con sus prendas."""
    try:
        return service.obtener_reserva_de_cliente(
            db, reserva_id, usuario_id=usuario.id
        )
    except service.ErrorDeReservas as error:
        raise _traducir(error)


@router.patch(
    "/{reserva_id}/cancelacion",
    response_model=ReservaOut,
    summary="CU-23 Cancelar una reserva",
    responses={
        404: {"description": "No existe, o es de otro cliente."},
        409: {"description": "Ya fue atendida, cancelada o expiró (E10)."},
    },
)
def cancelar_reserva(
    reserva_id: int,
    datos: CancelarReservaIn,
    db: DbSession,
    usuario: Usuario,
) -> ReservaOut:
    """Cancela una reserva propia y devuelve el stock apartado.

    Realiza el **RF29**: sin cancelación, el stock queda retenido hasta que la
    franja venza y CU-25 la expire — o sea, hasta un día entero de mercadería
    inmovilizada porque alguien cambió de planes.

    Es `PATCH` sobre un sub-recurso y no `DELETE` sobre la reserva: cancelar
    **no** la borra. La reserva cancelada se conserva —con su motivo, su fecha y
    sus prendas— porque es historia del cliente y de la sucursal, y porque los
    movimientos de `LIBERACION` que deja apuntan a ella.
    """
    try:
        return service.cancelar_reserva(
            db, reserva_id, datos, usuario_id=usuario.id
        )
    except (service.ErrorDeReservas, inventario.ErrorDeInventario) as error:
        raise _traducir(error)
