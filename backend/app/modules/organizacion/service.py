"""
P2 - Organizacion  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.organizacion import repository
from app.modules.organizacion.schemas import (
    CiudadCrearIn,
    CiudadEditarIn,
    CiudadOut,
    SucursalCrearIn,
    SucursalEditarIn,
    SucursalOut,
)

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeOrganizacion(Exception):
    """Base de los errores previstos de CU-05."""


class CiudadInexistente(ErrorDeOrganizacion):
    """El identificador no corresponde a ninguna ciudad."""


class CiudadDuplicada(ErrorDeOrganizacion):
    """Ya existe una ciudad con ese nombre."""


class CiudadConSucursalesActivas(ErrorDeOrganizacion):
    """Excepcion E2: primero hay que dar de baja sus sucursales."""


class CiudadConHistorial(ErrorDeOrganizacion):
    """Tiene sucursales dadas de baja, que se conservan para trazabilidad.

    No es la excepcion E2 --- ahi las sucursales estan activas y se pueden dar
    de baja --- sino un caso sin salida: borrar la ciudad arrastraria historia
    que el sistema debe conservar.
    """


class SucursalInexistente(ErrorDeOrganizacion):
    """El identificador no corresponde a ninguna sucursal."""


class NombreDeSucursalDuplicado(ErrorDeOrganizacion):
    """Excepcion E1: ese nombre ya esta usado en la misma ciudad."""


class HorarioInvalido(ErrorDeOrganizacion):
    """El cierre no es posterior a la apertura."""


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    """Indica si la violacion corresponde a esa restriccion.

    Se apoya en los nombres de app/db/base.py y de los __table_args__ del
    modelo. PostgreSQL nombra asi tambien el indice implicito, de modo que
    alcanza con buscar el nombre en el mensaje.
    """
    return restriccion in str(exc.orig)


# --- CU-05 Ciudades (flujo alternativo 3a) -------------------------------

def _fila_a_ciudad(fila) -> CiudadOut:
    return CiudadOut(
        id=fila.id,
        nombre=fila.nombre,
        departamento=fila.departamento,
        sucursales=fila.sucursales,
        sucursales_activas=fila.sucursales_activas,
    )


def listar_ciudades(db: Session, *, busqueda: str | None = None) -> list[CiudadOut]:
    """Ciudades con el recuento de sus sucursales."""
    return [_fila_a_ciudad(f) for f in repository.listar_ciudades(db, busqueda=busqueda)]


def obtener_ciudad(db: Session, ciudad_id: int) -> CiudadOut:
    fila = repository.obtener_ciudad_con_recuento(db, ciudad_id)
    if fila is None:
        raise CiudadInexistente(str(ciudad_id))
    return _fila_a_ciudad(fila)


def crear_ciudad(db: Session, datos: CiudadCrearIn) -> CiudadOut:
    """Alta de ciudad. El nombre es unico en todo el sistema."""
    if repository.obtener_ciudad_por_nombre(db, datos.nombre) is not None:
        raise CiudadDuplicada(datos.nombre)

    try:
        ciudad = repository.agregar_ciudad(
            db, nombre=datos.nombre, departamento=datos.departamento
        )
        db.commit()
    except IntegrityError as exc:
        # Entre la consulta previa y el commit puede colarse otra alta con el
        # mismo nombre. El UNIQUE de la base es el que lo impide de verdad.
        db.rollback()
        if _viola(exc, "uq_ciudad_nombre"):
            raise CiudadDuplicada(datos.nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_ciudad(db, ciudad.id)


def editar_ciudad(db: Session, ciudad_id: int, datos: CiudadEditarIn) -> CiudadOut:
    """Edicion de ciudad (flujo alternativo 3a)."""
    ciudad = repository.obtener_ciudad(db, ciudad_id)
    if ciudad is None:
        raise CiudadInexistente(str(ciudad_id))

    if datos.nombre and datos.nombre != ciudad.nombre:
        otra = repository.obtener_ciudad_por_nombre(db, datos.nombre)
        if otra is not None and otra.id != ciudad_id:
            raise CiudadDuplicada(datos.nombre)

    try:
        if datos.nombre is not None:
            ciudad.nombre = datos.nombre
        if datos.departamento is not None:
            ciudad.departamento = datos.departamento
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_ciudad_nombre"):
            raise CiudadDuplicada(datos.nombre or "") from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_ciudad(db, ciudad_id)


def eliminar_ciudad(db: Session, ciudad_id: int) -> None:
    """Baja de ciudad.

    `ciudad` no tiene indicador de estado: darla de baja es eliminarla. Solo
    procede si no le queda ninguna sucursal, activa ni historica, porque
    `sucursal.ciudad_id` no cascadea.
    """
    ciudad = repository.obtener_ciudad(db, ciudad_id)
    if ciudad is None:
        raise CiudadInexistente(str(ciudad_id))

    total, activas = repository.contar_sucursales_de_ciudad(db, ciudad_id)
    if activas:
        raise CiudadConSucursalesActivas(str(activas))
    if total:
        raise CiudadConHistorial(str(total))

    try:
        repository.eliminar_ciudad(db, ciudad)
        db.commit()
    except Exception:
        db.rollback()
        raise


# --- CU-05 Sucursales ----------------------------------------------------

def _fila_a_sucursal(fila) -> SucursalOut:
    return SucursalOut(
        id=fila.id,
        nombre=fila.nombre,
        ciudad_id=fila.ciudad_id,
        ciudad=fila.ciudad,
        direccion=fila.direccion,
        telefono=fila.telefono,
        horario_apertura=fila.horario_apertura,
        horario_cierre=fila.horario_cierre,
        capacidad_vestidores=fila.capacidad_vestidores,
        activa=fila.activa,
    )


def listar_sucursales(
    db: Session,
    *,
    busqueda: str | None = None,
    ciudad_id: int | None = None,
    activa: bool | None = None,
) -> list[SucursalOut]:
    """Listado del paso 2, y tambien el selector de CU-03 con `activa=True`."""
    return [
        _fila_a_sucursal(f)
        for f in repository.listar_sucursales(
            db, busqueda=busqueda, ciudad_id=ciudad_id, activa=activa
        )
    ]


def obtener_sucursal(db: Session, sucursal_id: int) -> SucursalOut:
    fila = repository.obtener_sucursal_con_ciudad(db, sucursal_id)
    if fila is None:
        raise SucursalInexistente(str(sucursal_id))
    return _fila_a_sucursal(fila)


def crear_sucursal(db: Session, datos: SucursalCrearIn) -> SucursalOut:
    """Alta de sucursal (pasos 5 a 7 del flujo principal).

    El paso 6 pide validar los datos y verificar que el nombre no se repita
    dentro de la misma ciudad.
    """
    if repository.obtener_ciudad(db, datos.ciudad_id) is None:
        raise CiudadInexistente(str(datos.ciudad_id))

    # Paso 6 - excepcion E1.
    if repository.existe_sucursal_con_nombre(
        db, ciudad_id=datos.ciudad_id, nombre=datos.nombre
    ):
        raise NombreDeSucursalDuplicado(datos.nombre)

    try:
        sucursal = repository.agregar_sucursal(
            db,
            ciudad_id=datos.ciudad_id,
            nombre=datos.nombre,
            direccion=datos.direccion,
            telefono=datos.telefono,
            horario_apertura=datos.horario_apertura,
            horario_cierre=datos.horario_cierre,
            capacidad_vestidores=datos.capacidad_vestidores,
            activa=datos.activa,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_sucursal_ciudad_nombre"):
            raise NombreDeSucursalDuplicado(datos.nombre) from exc
        if _viola(exc, "ck_sucursal_horario"):
            raise HorarioInvalido(datos.nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_sucursal(db, sucursal.id)


def editar_sucursal(
    db: Session, sucursal_id: int, datos: SucursalEditarIn
) -> SucursalOut:
    """Edicion de sucursal (flujo alternativo 3b)."""
    sucursal = repository.obtener_sucursal(db, sucursal_id)
    if sucursal is None:
        raise SucursalInexistente(str(sucursal_id))

    ciudad_id = datos.ciudad_id if datos.ciudad_id is not None else sucursal.ciudad_id
    if datos.ciudad_id is not None and repository.obtener_ciudad(db, ciudad_id) is None:
        raise CiudadInexistente(str(ciudad_id))

    # El horario se comprueba contra los valores que quedarian, no contra los
    # que llegaron: cambiar solo la apertura tambien puede invertirlo.
    apertura = datos.horario_apertura or sucursal.horario_apertura
    cierre = datos.horario_cierre or sucursal.horario_cierre
    if cierre <= apertura:
        raise HorarioInvalido(str(sucursal_id))

    # Excepcion E1. Se comprueba contra la ciudad y el nombre resultantes:
    # mover la sucursal a otra ciudad puede chocar con una que ya esta ahi.
    nombre = datos.nombre or sucursal.nombre
    if repository.existe_sucursal_con_nombre(
        db, ciudad_id=ciudad_id, nombre=nombre, excepto_id=sucursal_id
    ):
        raise NombreDeSucursalDuplicado(nombre)

    try:
        sucursal.ciudad_id = ciudad_id
        if datos.nombre is not None:
            sucursal.nombre = datos.nombre
        if datos.direccion is not None:
            sucursal.direccion = datos.direccion
        # El telefono es opcional: se permite borrarlo mandando cadena vacia,
        # que el esquema ya convirtio en None.
        if "telefono" in datos.model_fields_set:
            sucursal.telefono = datos.telefono
        if datos.horario_apertura is not None:
            sucursal.horario_apertura = datos.horario_apertura
        if datos.horario_cierre is not None:
            sucursal.horario_cierre = datos.horario_cierre
        if datos.capacidad_vestidores is not None:
            sucursal.capacidad_vestidores = datos.capacidad_vestidores
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_sucursal_ciudad_nombre"):
            raise NombreDeSucursalDuplicado(nombre) from exc
        if _viola(exc, "ck_sucursal_horario"):
            raise HorarioInvalido(str(sucursal_id)) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_sucursal(db, sucursal_id)


def cambiar_estado_sucursal(
    db: Session, sucursal_id: int, activa: bool
) -> SucursalOut:
    """Alta o baja de una sucursal (flujo alternativo 3c).

    Dar de baja no borra la fila: la sucursal deja de ofrecerse para reservas y
    compras, pero se conserva para la trazabilidad historica. Es tambien lo que
    la saca del selector de CU-03, que pide `activa=True`.
    """
    sucursal = repository.obtener_sucursal(db, sucursal_id)
    if sucursal is None:
        raise SucursalInexistente(str(sucursal_id))

    try:
        sucursal.activa = activa
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_sucursal(db, sucursal_id)


# TODO CU-06 y CU-07: implementar el resto de las reglas.
