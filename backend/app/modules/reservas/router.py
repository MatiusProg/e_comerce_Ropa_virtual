"""
P6 - Reservas  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Implementados en este archivo: CU-22, CU-23, CU-24 y CU-25.

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.

DOS ROUTERS, PORQUE SON DOS AMBITOS
-----------------------------------
`router` es del **Cliente** y vive en `/reservas`: son SUS reservas, las cree
(CU-22) o las cancele (CU-23).

`sucursal_router` es del **Encargado** y vive en `/sucursal/reservas`: son las
reservas dirigidas a SU local, que prepara y atiende (CU-24). El Administrador
entra tambien, con alcance a toda la red.

No es el mismo recurso con dos permisos: son dos colecciones distintas --- «las
mias» y «las de mi sucursal» --- que casi nunca coinciden. La exigencia de rol
se declara UNA vez por router, por la regla de la seccion 6.11.4 de
docs/06-decisiones-tecnicas.md.

LA PROPIEDAD DE LA RESERVA NO SE COMPRUEBA AQUI
-----------------------------------------------
Que una reserva sea de quien la pide se resuelve en el servicio, porque hace
falta leer la fila para saberlo. El router no puede autorizar lo que todavia no
leyo.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    DbSession,
    Usuario,
    UsuarioActual,
    requiere_roles,
)
from app.modules.inventario import service as inventario
from app.modules.reservas import service
from app.modules.reservas.models import ESTADOS_RESERVA
from app.modules.reservas.schemas import (
    AtenderReservaIn,
    CancelarReservaIn,
    ExpiracionOut,
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
    if isinstance(error, service.ReservaDeOtraSucursal):
        # Acá sí un 403 y no un 404, al revés que con el Cliente: el Encargado
        # es personal de la empresa y sabe que las otras sucursales existen, así
        # que ocultárselo no protege a nadie y sí le esconde el motivo real.
        return HTTPException(403, "Esa reserva es de otra sucursal.")
    if isinstance(error, service.ReservaNoAtendible):
        motivos = {
            "PREPARADA": "Esa reserva ya estaba preparada.",
            "ATENDIDA": "Esa reserva ya fue atendida.",
            "CANCELADA": "El cliente canceló esa reserva.",
            "EXPIRADA": "Esa reserva venció y el stock ya se liberó.",
        }
        return HTTPException(
            409, motivos.get(error.estado, "Esa reserva ya no se puede atender.")
        )
    if isinstance(error, service.ResultadosIncompletos):
        # Excepcion E11. Se distinguen las dos mitades porque son errores
        # distintos: olvidarse de una prenda y mandar una que no es de esa
        # reserva no se arreglan igual.
        if error.faltantes:
            return HTTPException(
                422,
                {
                    "mensaje": (
                        "Falta indicar qué pasó con alguna prenda. Si no se "
                        "marcan todas, sus unidades quedarían apartadas en una "
                        "reserva ya cerrada."
                    ),
                    "detalles": error.faltantes,
                },
            )
        return HTTPException(
            422,
            {
                "mensaje": "Hay prendas que no pertenecen a esta reserva.",
                "detalles": error.ajenos,
            },
        )
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


# =====================================================================
# CU-24 - Atender reserva en sucursal  (Encargado)
# =====================================================================

sucursal_router = APIRouter(
    prefix="/sucursal/reservas",
    tags=["Reservas · Sucursal"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR", "ENCARGADO"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no tiene un rol habilitado."},
    },
)


def _ambito(usuario: UsuarioActual) -> int | None:
    """Sobre qué sucursal trabaja quien pregunta.

    El Administrador ve toda la red —devuelve None, que el servicio lee como
    «sin filtro»— y el Encargado, la suya y solo la suya. El ámbito viaja en el
    token, así que no hay parámetro que un cliente pueda manipular: no existe
    forma de pedir otra sucursal.
    """
    return None if usuario.rol == "ADMINISTRADOR" else usuario.sucursal_id


@sucursal_router.get(
    "",
    response_model=PaginaReservas,
    summary="CU-24 Reservas dirigidas a mi sucursal",
)
def listar_reservas_de_sucursal(
    db: DbSession,
    usuario: Usuario,
    estado: Annotated[str | None, Query(pattern=_PATRON_ESTADO)] = None,
    vivas: Annotated[bool | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaReservas:
    """Paso 2: la agenda del local, **la franja más próxima arriba**.

    Ordena al revés que «mis reservas» del Cliente, y es correcto: el Cliente
    mira un historial —lo último que hizo va arriba—, el Encargado mira una
    agenda —lo que tiene que atender primero es lo que empieza antes—.
    """
    return service.listar_reservas_de_sucursal(
        db,
        sucursal_id=_ambito(usuario),
        pagina=pagina,
        tamano=tamano,
        estado=estado,
        vivas=vivas,
    )


@sucursal_router.get(
    "/{reserva_id}",
    response_model=ReservaOut,
    summary="CU-24 Detalle de una reserva del local",
    responses={403: {"description": "La reserva es de otra sucursal."}},
)
def obtener_reserva_de_sucursal(
    reserva_id: int, db: DbSession, usuario: Usuario
) -> ReservaOut:
    """Las prendas que hay que ir a buscar a la percha."""
    try:
        return service.obtener_reserva_de_sucursal(
            db, reserva_id, sucursal_id=_ambito(usuario)
        )
    except service.ErrorDeReservas as error:
        raise _traducir(error)


@sucursal_router.patch(
    "/{reserva_id}/preparacion",
    response_model=ReservaOut,
    summary="CU-24 Marcar la reserva como preparada",
    responses={409: {"description": "La reserva ya no está pendiente."}},
)
def preparar_reserva(
    reserva_id: int, db: DbSession, usuario: Usuario
) -> ReservaOut:
    """Paso 3: el Encargado ya juntó las prendas. `PENDIENTE` → `PREPARADA`.

    **No mueve stock**, y es la única transición de la reserva que no lo hace:
    las unidades ya estaban apartadas desde CU-22 y siguen estándolo. Lo único
    que cambia es que alguien las fue a buscar.

    Tampoco impide que el cliente cancele: `PREPARADA` sigue siendo un estado
    vivo y el RF29 le deja cancelar hasta que se atienda.
    """
    try:
        return service.preparar_reserva(
            db, reserva_id, sucursal_id=_ambito(usuario)
        )
    except service.ErrorDeReservas as error:
        raise _traducir(error)


@sucursal_router.patch(
    "/{reserva_id}/atencion",
    response_model=ReservaOut,
    summary="CU-24 Cerrar la reserva con el resultado de la prueba",
    responses={
        409: {"description": "La reserva ya no está viva."},
        422: {"description": "Faltan o sobran resultados (E11)."},
    },
)
def atender_reserva(
    reserva_id: int,
    datos: AtenderReservaIn,
    db: DbSession,
    usuario: Usuario,
) -> ReservaOut:
    """Pasos 5 a 7: el cliente se probó las prendas y se cierra la reserva.

    Cada prenda mueve stock según su resultado: las que **no** se lleva vuelven
    al disponible con una `LIBERACION`; las que **sí**, una `LIBERACION` y una
    `VENTA` —el neto sobre el disponible es cero y las unidades salen de la
    tienda—.

    Los resultados de **todas** las líneas viajan juntos: cerrar a medias
    dejaría una reserva `ATENDIDA` con parte de su mercadería todavía apartada,
    y eso no lo limpia nadie después.
    """
    try:
        return service.atender_reserva(
            db,
            reserva_id,
            datos,
            sucursal_id=_ambito(usuario),
            usuario_id=usuario.id,
        )
    except (service.ErrorDeReservas, inventario.ErrorDeInventario) as error:
        raise _traducir(error)


# =====================================================================
# CU-25 - Expirar reservas vencidas  (tarea programada)
# =====================================================================
#
# PREFIJO PROPIO, Y NO `/reservas/expiracion`
# -------------------------------------------
# `/reservas/{reserva_id}` ya existe y su parametro es un entero. Una ruta
# `/reservas/expiracion` declarada despues nunca se alcanzaria: FastAPI probaria
# primero la parametrizada, fallaria al convertir «expiracion» a int y devolveria
# un 422 en vez de caer en la siguiente. Declararla antes funcionaria, pero
# dejaria el orden del archivo como una trampa para quien lo edite manana.
#
# Con prefijo propio el problema no existe, y ademas el nombre dice lo que es:
# no es una operacion sobre una reserva, es mantenimiento del sistema.

mantenimiento_router = APIRouter(
    prefix="/mantenimiento/reservas",
    tags=["Reservas · Mantenimiento"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


@mantenimiento_router.post(
    "/expiracion",
    response_model=ExpiracionOut,
    summary="CU-25 Expirar las reservas vencidas y liberar su stock",
)
def expirar_reservas_vencidas(db: DbSession) -> ExpiracionOut:
    """Realiza el **RF30**: devuelve al inventario lo que nadie fue a buscar.

    Es el único caso de uso cuyo actor es **A6, el Sistema**. Está pensado para
    que lo llame un planificador —una tarea de Railway, un cron— y por eso
    **es idempotente**: correrlo dos veces seguidas no libera nada la segunda
    vez.

    Se expone además como endpoint, y no solo como script, por dos motivos: se
    puede disparar a mano en la defensa para mostrar el efecto, y devuelve
    **qué hizo** —cuántas, cuáles y cuántas unidades— en vez de un «listo». Una
    tarea programada que no dice lo que hizo es imposible de verificar: si un
    día deja de funcionar, el síntoma sería stock retenido sin que nada lo
    denuncie.

    Una reserva se considera vencida cuando su franja terminó **y** además pasó
    la tolerancia de `RESERVA_VIGENCIA_HORAS`, que existe para el cliente que
    llega tarde.
    """
    return service.expirar_reservas_vencidas(db)
