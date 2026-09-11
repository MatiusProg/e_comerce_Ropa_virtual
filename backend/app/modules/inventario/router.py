"""
P4 - Inventario  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal

Implementados en este archivo: CU-13, CU-15 y CU-16.

Regla: el router valida la entrada, resuelve la autorizacion y delega en el
servicio. Ninguna regla de negocio vive aqui.

DOS ROUTERS, PORQUE SON DOS AMBITOS DE ROL
------------------------------------------
`operacion_router` es de Administrador Y Encargado: el ingreso de mercaderia
(CU-13, que el Encargado hace porque es quien recibe las cajas), el ajuste por
conteo, el umbral de reposicion y las lecturas del deposito. `router` es solo
del Administrador, y ahi vive lo unico que cruza sucursales: la transferencia.

La exigencia se declara UNA vez por router y no endpoint por endpoint: es la
regla de la seccion 6.11.4 de docs/06-decisiones-tecnicas.md, y el motivo es que
olvidarla en un solo endpoint abre un agujero que nada avisa.

El ambito de datos del Encargado -su sucursal y ninguna otra- no lo resuelve el
rol sino `verificar_ambito_sucursal`, porque la sucursal viaja en el token y no
en el cuerpo de la peticion.

POR QUE EL AJUSTE CAMBIO DE ROUTER
----------------------------------
El 10/09 el ajuste se declaro solo para el Administrador, leyendo la fila de
CU-15 de la seccion 2.2 del documento de organizacion, que dice «web: Admin».
Estaba incompleto: **CU-16 es el mismo ajuste visto desde el Encargado** -«le
permite consultar y AJUSTAR la disponibilidad de las prendas de su propia
sucursal»-, y es justamente el motivo por el que CU-15 figura como de
Administrador: la mitad del Encargado tiene caso de uso propio.

Asi que es un endpoint con dos ambitos y no dos endpoints. Duplicarlo
-`/movimientos/ajuste` y `/disponibilidad/ajuste`- expondria el mismo recurso en
dos rutas, que es lo que la seccion 6.11.2 decidio no hacer, y dejaria dos
copias de la regla del conteo fisico esperando a divergir.

La transferencia NO se mueve: cruza dos sucursales y el Encargado responde por
una sola.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    DbSession,
    Usuario,
    requiere_roles,
    verificar_ambito_sucursal,
)
from app.modules.inventario import service
from app.modules.inventario.schemas import (
    TIPOS_MANUALES,
    AjusteIn,
    AjusteOut,
    ExistenciaOut,
    IngresoIn,
    IngresoOut,
    MovimientoOut,
    PaginaIngresos,
    PaginaMovimientos,
    StockMinimoIn,
    TransferenciaIn,
    TransferenciaOut,
)
from app.modules.inventario.models import TIPOS_MOVIMIENTO

#: Patron para el filtro por tipo del historial. Se arma con la constante del
#: modelo para que agregar un tipo nuevo no exija acordarse de este archivo.
_PATRON_TIPO = "^(" + "|".join(TIPOS_MOVIMIENTO) + ")$"


# CU-15: solo Administrador.
router = APIRouter(
    prefix="/inventario",
    tags=["Inventario"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)

# CU-13 y las consultas del deposito: Administrador y Encargado. El Encargado
# queda limitado a su propia sucursal por `verificar_ambito_sucursal`.
operacion_router = APIRouter(
    prefix="/inventario",
    tags=["Inventario"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR", "ENCARGADO"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no tiene un rol habilitado."},
    },
)


def _traducir(error: service.ErrorDeInventario) -> HTTPException:
    """Convierte los errores de negocio de P4 en respuestas HTTP."""
    if isinstance(error, service.SucursalInexistente):
        return HTTPException(404, "La sucursal indicada no existe.")
    if isinstance(error, service.SucursalInactiva):
        # Excepcion E2.
        return HTTPException(
            422,
            "La sucursal está dada de baja. Reactívela antes de mover mercadería.",
        )
    if isinstance(error, service.ProveedorInexistente):
        return HTTPException(404, "El proveedor indicado no existe.")
    if isinstance(error, service.ProveedorInactivo):
        # Excepcion E3.
        return HTTPException(
            422, "El proveedor está dado de baja y no puede enviar mercadería."
        )
    if isinstance(error, service.VarianteInexistente):
        # Excepcion E1. Se devuelven los identificadores para que la interfaz
        # señale las líneas del remito en vez de invalidar el formulario entero.
        return HTTPException(
            422,
            {
                "mensaje": "Alguna de las prendas del ingreso ya no existe.",
                "variantes": error.ids,
            },
        )
    if isinstance(error, service.VarianteInactiva):
        # Excepcion E1, segunda mitad.
        return HTTPException(
            422,
            {
                "mensaje": (
                    "Alguna de las prendas está desactivada. Reactívela en el "
                    "catálogo antes de recibirla."
                ),
                "variantes": error.ids,
            },
        )
    if isinstance(error, service.StockInsuficiente):
        # Excepcion E6.
        return HTTPException(
            409,
            f"No hay unidades suficientes: hay {error.disponible} disponibles y "
            f"se pidieron {error.solicitado}.",
        )
    if isinstance(error, service.ConteoMenorQueLoReservado):
        # Excepcion E8.
        return HTTPException(
            409,
            f"El conteo dice {error.contada} unidades, pero hay "
            f"{error.reservada} comprometidas en reservas. Cancele las reservas "
            "antes de ajustar.",
        )
    if isinstance(error, service.ConteoSinDiferencia):
        # Excepcion E7. No es un fallo, pero tampoco es un movimiento.
        return HTTPException(
            409, "El conteo coincide con el saldo registrado. No hay nada que ajustar."
        )
    if isinstance(error, service.ExistenciaInexistente):
        return HTTPException(
            404, "No hay existencia registrada de esa prenda en esa sucursal."
        )
    return HTTPException(400, "No se pudo completar la operación.")


def _sucursal_del_usuario(usuario, sucursal_id: int | None) -> int | None:
    """Resuelve sobre que sucursal mira una consulta.

    El Administrador ve todas y puede filtrar por una; el Encargado ve la suya y
    solo la suya, pida lo que pida. Devolver su sucursal en vez de rechazar la
    peticion hace que la misma pantalla sirva para los dos roles sin que el
    cliente tenga que saber cual es.
    """
    if usuario.rol == "ADMINISTRADOR":
        return sucursal_id
    if sucursal_id is not None:
        verificar_ambito_sucursal(usuario, sucursal_id)
    return usuario.sucursal_id


# =====================================================================
# CU-13 - Registrar ingreso de mercaderia
# =====================================================================

@operacion_router.post(
    "/ingresos",
    response_model=IngresoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-13 Registrar ingreso de mercadería",
    responses={
        404: {"description": "Sucursal o proveedor inexistentes."},
        422: {"description": "Prenda inexistente o desactivada (excepción E1)."},
    },
)
def registrar_ingreso(
    datos: IngresoIn, db: DbSession, usuario: Usuario
) -> IngresoOut:
    """Pasos 4 a 7: recibe el envío de un proveedor y sube los saldos.

    Todo el remito entra en una sola transacción: si una línea falla, no queda
    cargada ninguna (excepción E9).
    """
    verificar_ambito_sucursal(usuario, datos.sucursal_id)
    try:
        registrado = service.registrar_ingreso(db, datos, usuario_id=usuario.id)
    except service.ErrorDeInventario as error:
        raise _traducir(error)
    return registrado


@operacion_router.get(
    "/ingresos",
    response_model=PaginaIngresos,
    summary="CU-13 Historial de ingresos",
)
def listar_ingresos(
    db: DbSession,
    usuario: Usuario,
    sucursal_id: Annotated[int | None, Query()] = None,
    proveedor_id: Annotated[int | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaIngresos:
    """Paso 2: los ingresos ya registrados, del más reciente al más viejo.

    El Encargado ve los de su sucursal aunque no la indique.
    """
    return service.listar_ingresos(
        db,
        pagina=pagina,
        tamano=tamano,
        sucursal_id=_sucursal_del_usuario(usuario, sucursal_id),
        proveedor_id=proveedor_id,
    )


@operacion_router.get(
    "/ingresos/detalle",
    response_model=list[MovimientoOut],
    summary="CU-13 Líneas de un ingreso del historial",
)
def detalle_de_ingreso(
    db: DbSession,
    usuario: Usuario,
    registrado_en: Annotated[datetime, Query(description="Instante exacto del ingreso")],
    sucursal_id: Annotated[int, Query()],
    referencia: Annotated[str | None, Query(max_length=40)] = None,
) -> list[MovimientoOut]:
    """Las líneas de un ingreso concreto.

    Se identifica por los mismos datos que lo agrupan en el listado —instante,
    sucursal y remito— porque el ingreso no tiene fila propia. Ver la nota
    «POR QUE NO HAY TABLA `ingreso`» en `models.py`.
    """
    verificar_ambito_sucursal(usuario, sucursal_id)
    try:
        return service.detalle_de_ingreso(
            db,
            registrado_en=registrado_en,
            sucursal_id=sucursal_id,
            referencia=referencia,
        )
    except service.ErrorDeInventario as error:
        raise _traducir(error)


# =====================================================================
# Consultas del depósito, compartidas por CU-13 y CU-15
# =====================================================================

@operacion_router.get(
    "/existencias",
    response_model=list[ExistenciaOut],
    summary="CU-13/CU-15 Existencias, para elegir sobre cuál operar",
)
def listar_existencias(
    db: DbSession,
    usuario: Usuario,
    sucursal_id: Annotated[int | None, Query()] = None,
    producto_id: Annotated[int | None, Query()] = None,
    solo_con_saldo: Annotated[bool, Query()] = False,
) -> list[ExistenciaOut]:
    """Los saldos con la prenda y la sucursal ya resueltas.

    Es la misma función que consume CU-14 por la costura C1; acá se expone por
    HTTP para que los formularios de ajuste y transferencia puedan mostrar
    cuánto hay antes de que la persona escriba un número.
    """
    return service.inventario_consolidado(
        db,
        sucursal_id=_sucursal_del_usuario(usuario, sucursal_id),
        producto_id=producto_id,
        solo_con_saldo=solo_con_saldo,
    )


# =====================================================================
# CU-16 - Gestionar disponibilidad de la sucursal
# =====================================================================

@operacion_router.get(
    "/alertas",
    response_model=list[ExistenciaOut],
    summary="CU-16 Prendas en punto de reposición",
)
def listar_alertas(
    db: DbSession,
    usuario: Usuario,
    sucursal_id: Annotated[int | None, Query()] = None,
) -> list[ExistenciaOut]:
    """Las prendas que llegaron a su punto de reposición, de peor a mejor.

    Solo aparecen las que tienen umbral: cero significa «sin alerta», y una
    existencia recién creada por un ingreso no debería empezar a avisar sola con
    un número que nadie eligió.

    El Encargado ve las de su sucursal aunque no la indique.
    """
    return service.alertas_de_stock(
        db, sucursal_id=_sucursal_del_usuario(usuario, sucursal_id)
    )


@operacion_router.patch(
    "/existencias/{existencia_id}/stock-minimo",
    response_model=ExistenciaOut,
    summary="CU-16 Fijar el punto de reposición de una prenda",
    responses={
        403: {"description": "Un Encargado intentó tocar otra sucursal."},
        404: {"description": "Esa existencia no existe."},
    },
)
def fijar_stock_minimo(
    existencia_id: int, datos: StockMinimoIn, db: DbSession, usuario: Usuario
) -> ExistenciaOut:
    """Fija cuándo esta prenda tiene que avisar que hay que reponerla.

    Es la única escritura del paquete que **no** genera movimiento, y no es una
    excepción a la regla: lo que no se toca sin movimiento es una *cantidad de
    mercadería*, y el umbral no lo es — es una preferencia de quien administra
    el local.

    Se comprueba el ámbito **antes** de escribir, y para eso hace falta saber de
    qué sucursal es la existencia: por eso se la busca primero. Confiar en el
    identificador de la URL sin resolverlo dejaría a un Encargado cambiándole el
    umbral a cualquier prenda de la red con solo probar números.
    """
    actual = service.existencia_por_id(db, existencia_id)
    if actual is None:
        raise HTTPException(404, "Esa existencia no existe.")
    verificar_ambito_sucursal(usuario, actual.sucursal_id)

    try:
        return service.fijar_stock_minimo(db, existencia_id, datos.stock_minimo)
    except service.ErrorDeInventario as error:
        raise _traducir(error)


@operacion_router.get(
    "/movimientos",
    response_model=PaginaMovimientos,
    summary="CU-15 Historial de movimientos",
)
def listar_movimientos(
    db: DbSession,
    usuario: Usuario,
    sucursal_id: Annotated[int | None, Query()] = None,
    variante_id: Annotated[int | None, Query()] = None,
    tipo: Annotated[str | None, Query(pattern=_PATRON_TIPO)] = None,
    desde: Annotated[datetime | None, Query()] = None,
    hasta: Annotated[datetime | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaMovimientos:
    """La trazabilidad que pide el RF22: qué se movió, cuánto, por qué, quién y
    cuándo."""
    return service.listar_movimientos(
        db,
        pagina=pagina,
        tamano=tamano,
        sucursal_id=_sucursal_del_usuario(usuario, sucursal_id),
        variante_id=variante_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )


@operacion_router.get(
    "/tipos-movimiento",
    response_model=list[str],
    summary="CU-15 Tipos que un usuario puede originar",
)
def listar_tipos_manuales() -> list[str]:
    """Los tres tipos que se cargan a mano, para el selector del formulario.

    Es una constante y no una consulta, por el mismo motivo que los cargos de
    CU-06: el CHECK los fija en la base y repetirlos en la interfaz garantiza
    que algún día digan cosas distintas. Los otros cuatro tipos existen pero los
    genera el sistema, y ofrecerlos acá dejaría descuadrar un saldo contra la
    reserva o la venta que lo justifica.
    """
    return list(TIPOS_MANUALES)


# =====================================================================
# CU-15 - Registrar movimiento de inventario  (solo Administrador)
# =====================================================================

@operacion_router.post(
    "/movimientos/ajuste",
    response_model=AjusteOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-15/CU-16 Ajuste por conteo físico",
    responses={
        403: {"description": "Un Encargado intentó ajustar otra sucursal."},
        409: {
            "description": (
                "El conteo coincide con el saldo (E7) o no cubre lo reservado (E8)."
            )
        },
    },
)
def registrar_ajuste(datos: AjusteIn, db: DbSession, usuario: Usuario) -> AjusteOut:
    """Se envía lo contado y el sistema calcula la diferencia.

    Lo contado es el total físico —lo reservado sigue estando en la percha—, no
    lo disponible.

    Es **CU-15** cuando lo hace el Administrador, que puede ajustar cualquier
    sucursal, y **CU-16** cuando lo hace el Encargado sobre la suya. La misma
    operación, dos alcances; quien los separa es el token.
    """
    verificar_ambito_sucursal(usuario, datos.sucursal_id)
    try:
        return service.registrar_ajuste(db, datos, usuario_id=usuario.id)
    except service.ErrorDeInventario as error:
        raise _traducir(error)


@router.post(
    "/movimientos/transferencia",
    response_model=TransferenciaOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-15 Transferencia entre sucursales",
    responses={
        404: {"description": "La prenda nunca estuvo en la sucursal de origen."},
        409: {"description": "No hay unidades suficientes en el origen (E6)."},
    },
)
def registrar_transferencia(
    datos: TransferenciaIn, db: DbSession, usuario: Usuario
) -> TransferenciaOut:
    """Flujo alternativo 3a. Deja dos movimientos: la salida y la entrada."""
    try:
        return service.registrar_transferencia(db, datos, usuario_id=usuario.id)
    except service.ErrorDeInventario as error:
        raise _traducir(error)
