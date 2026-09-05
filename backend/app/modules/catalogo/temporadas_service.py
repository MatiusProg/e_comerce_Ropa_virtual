"""
P3 - Catalogo  |  CU-09 Gestionar temporadas y colecciones  |  capa: servicio

Ciclo de desarrollo: 1

Archivos propios para no chocar con el CU-08; el motivo esta en
`temporadas_schemas.py`.
"""
from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalogo import temporadas_repository as repository
from app.modules.catalogo.temporadas_schemas import (
    ColeccionCrearIn,
    ColeccionEditarIn,
    ColeccionOut,
    TemporadaCrearIn,
    TemporadaEditarIn,
    TemporadaOut,
)

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.


# --- Errores de negocio --------------------------------------------------

class ErrorDeTemporadas(Exception):
    """Base de los errores previstos de CU-09."""


class TemporadaInexistente(ErrorDeTemporadas):
    """El identificador no corresponde a ninguna temporada."""


class TemporadaDuplicada(ErrorDeTemporadas):
    """Ya existe una temporada con ese nombre."""


class RangoInvalido(ErrorDeTemporadas):
    """Excepcion E1: la fecha de fin no es posterior a la de inicio."""


class SolapamientoDeTemporadas(ErrorDeTemporadas):
    """Excepcion E2: el rango se cruza con otra temporada abierta.

    NO es un rechazo: el caso de uso pide advertir y pedir confirmacion. Lleva
    los nombres de las temporadas que se cruzan para que el mensaje diga con
    cuales, que es lo unico que permite decidir con criterio.
    """

    def __init__(self, nombres: list[str]):
        super().__init__(", ".join(nombres))
        self.nombres = nombres


class TemporadaConColecciones(ErrorDeTemporadas):
    """Excepcion E3: tiene colecciones asociadas; corresponde cerrarla."""


class ColeccionInexistente(ErrorDeTemporadas):
    """El identificador no corresponde a ninguna coleccion."""


class NombreDeColeccionDuplicado(ErrorDeTemporadas):
    """Ese nombre ya esta usado en la misma temporada."""


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    """Indica si la violacion corresponde a esa restriccion.

    Se apoya en los nombres de app/db/base.py y de los __table_args__ del
    modelo. PostgreSQL nombra asi tambien el indice implicito.
    """
    return restriccion in str(exc.orig)


# --- Temporadas ----------------------------------------------------------

def _fila_a_temporada(fila, hoy: date) -> TemporadaOut:
    return TemporadaOut(
        id=fila.id,
        nombre=fila.nombre,
        descripcion=fila.descripcion,
        fecha_inicio=fila.fecha_inicio,
        fecha_fin=fila.fecha_fin,
        activa=fila.activa,
        # Vigente = abierta y corriendo hoy. Se calcula, no se guarda.
        vigente=fila.activa and fila.fecha_inicio <= hoy <= fila.fecha_fin,
        colecciones=fila.colecciones,
        colecciones_activas=fila.colecciones_activas,
    )


def listar_temporadas(
    db: Session, *, busqueda: str | None = None, activa: bool | None = None
) -> list[TemporadaOut]:
    """Listado del paso 2, indicando cual es la vigente."""
    hoy = date.today()
    return [
        _fila_a_temporada(f, hoy)
        for f in repository.listar_temporadas(db, busqueda=busqueda, activa=activa)
    ]


def obtener_temporada(db: Session, temporada_id: int) -> TemporadaOut:
    fila = repository.obtener_temporada_detalle(db, temporada_id)
    if fila is None:
        raise TemporadaInexistente(str(temporada_id))
    return _fila_a_temporada(fila, date.today())


def _comprobar_solapamiento(
    db: Session,
    *,
    fecha_inicio: date,
    fecha_fin: date,
    excepto_id: int | None,
    confirmado: bool,
) -> None:
    """Excepcion E2. Advierte una sola vez; si ya se confirmo, deja pasar.

    Solo aplica a temporadas que van a quedar ABIERTAS: dos cerradas pueden
    cruzarse sin consecuencia, porque ninguna compite por ser la vigente.
    """
    if confirmado:
        return
    cruzadas = repository.temporadas_que_se_cruzan(
        db, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, excepto_id=excepto_id
    )
    if cruzadas:
        raise SolapamientoDeTemporadas([t.nombre for t in cruzadas])


def crear_temporada(db: Session, datos: TemporadaCrearIn) -> TemporadaOut:
    """Alta de temporada (pasos 5 a 7).

    El paso 6 pide validar que la fecha de fin sea posterior a la de inicio
    --- eso ya lo hizo el esquema --- y que el nombre no se repita.
    """
    if repository.obtener_temporada_por_nombre(db, datos.nombre) is not None:
        raise TemporadaDuplicada(datos.nombre)

    if datos.activa:
        _comprobar_solapamiento(
            db,
            fecha_inicio=datos.fecha_inicio,
            fecha_fin=datos.fecha_fin,
            excepto_id=None,
            confirmado=datos.confirmar_solapamiento,
        )

    try:
        temporada = repository.agregar_temporada(
            db,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            fecha_inicio=datos.fecha_inicio,
            fecha_fin=datos.fecha_fin,
            activa=datos.activa,
        )
        db.commit()
    except IntegrityError as exc:
        # Entre la consulta previa y el commit puede colarse otra alta con el
        # mismo nombre. El UNIQUE de la base es el que lo impide de verdad.
        db.rollback()
        if _viola(exc, "uq_temporada_nombre"):
            raise TemporadaDuplicada(datos.nombre) from exc
        if _viola(exc, "ck_temporada_rango"):
            raise RangoInvalido(datos.nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_temporada(db, temporada.id)


def editar_temporada(
    db: Session, temporada_id: int, datos: TemporadaEditarIn
) -> TemporadaOut:
    """Edicion de temporada (flujo alternativo 3a)."""
    temporada = repository.obtener_temporada(db, temporada_id)
    if temporada is None:
        raise TemporadaInexistente(str(temporada_id))

    if datos.nombre and datos.nombre.lower() != temporada.nombre.lower():
        otra = repository.obtener_temporada_por_nombre(db, datos.nombre)
        if otra is not None and otra.id != temporada_id:
            raise TemporadaDuplicada(datos.nombre)

    # El rango se comprueba contra los valores que quedarian, no contra los que
    # llegaron: cambiar solo el inicio tambien puede invertirlo.
    inicio = datos.fecha_inicio or temporada.fecha_inicio
    fin = datos.fecha_fin or temporada.fecha_fin
    if fin <= inicio:
        raise RangoInvalido(str(temporada_id))

    # La advertencia de E2 solo tiene sentido si el RANGO cambia. Un cruce que
    # ya existe fue aceptado cuando se creo la temporada; volver a preguntarlo
    # al corregir una descripcion es ruido, y ademas dejaria la temporada
    # inescapable: no se podria editar nada sin reconfirmar cada vez.
    rango_cambio = (
        inicio != temporada.fecha_inicio or fin != temporada.fecha_fin
    )
    if temporada.activa and rango_cambio:
        _comprobar_solapamiento(
            db,
            fecha_inicio=inicio,
            fecha_fin=fin,
            excepto_id=temporada_id,
            confirmado=datos.confirmar_solapamiento,
        )

    try:
        if datos.nombre is not None:
            temporada.nombre = datos.nombre
        # La descripcion es opcional: mandar cadena vacia --- que el esquema
        # convirtio en None --- significa borrarla, y eso hay que poder hacerlo.
        if "descripcion" in datos.model_fields_set:
            temporada.descripcion = datos.descripcion
        temporada.fecha_inicio = inicio
        temporada.fecha_fin = fin
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_temporada_nombre"):
            raise TemporadaDuplicada(datos.nombre or "") from exc
        if _viola(exc, "ck_temporada_rango"):
            raise RangoInvalido(str(temporada_id)) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_temporada(db, temporada_id)


def cambiar_estado_temporada(
    db: Session, temporada_id: int, activa: bool, *, confirmado: bool = False
) -> TemporadaOut:
    """Cerrar o reabrir una temporada (flujo alternativo 3b).

    Cerrarla no borra nada: sus productos siguen siendo consultables, solo
    dejan de considerarse de temporada vigente. Reabrirla si puede volver a
    cruzarla con otra abierta, asi que pasa por la advertencia de E2.
    """
    temporada = repository.obtener_temporada(db, temporada_id)
    if temporada is None:
        raise TemporadaInexistente(str(temporada_id))

    if activa and not temporada.activa:
        _comprobar_solapamiento(
            db,
            fecha_inicio=temporada.fecha_inicio,
            fecha_fin=temporada.fecha_fin,
            excepto_id=temporada_id,
            confirmado=confirmado,
        )

    try:
        temporada.activa = activa
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_temporada(db, temporada_id)


def eliminar_temporada(db: Session, temporada_id: int) -> None:
    """Excepcion E3: solo procede si no tiene colecciones asociadas.

    `coleccion.temporada_id` no cascadea, asi que el borrado fallaria con una
    violacion de integridad. El caso de uso pide, ademas, ofrecer cerrarla en
    su lugar; eso lo resuelve la interfaz con este error.
    """
    temporada = repository.obtener_temporada(db, temporada_id)
    if temporada is None:
        raise TemporadaInexistente(str(temporada_id))

    total, _ = repository.contar_colecciones_de_temporada(db, temporada_id)
    if total:
        raise TemporadaConColecciones(str(total))

    try:
        repository.eliminar_temporada(db, temporada)
        db.commit()
    except Exception:
        db.rollback()
        raise


# --- Colecciones (flujo alternativo 1a) ----------------------------------

def _fila_a_coleccion(fila) -> ColeccionOut:
    return ColeccionOut(
        id=fila.id,
        temporada_id=fila.temporada_id,
        temporada=fila.temporada,
        nombre=fila.nombre,
        descripcion=fila.descripcion,
        activa=fila.activa,
    )


def listar_colecciones(
    db: Session,
    *,
    busqueda: str | None = None,
    temporada_id: int | None = None,
    activa: bool | None = None,
) -> list[ColeccionOut]:
    return [
        _fila_a_coleccion(f)
        for f in repository.listar_colecciones(
            db, busqueda=busqueda, temporada_id=temporada_id, activa=activa
        )
    ]


def obtener_coleccion(db: Session, coleccion_id: int) -> ColeccionOut:
    fila = repository.obtener_coleccion_detalle(db, coleccion_id)
    if fila is None:
        raise ColeccionInexistente(str(coleccion_id))
    return _fila_a_coleccion(fila)


def crear_coleccion(db: Session, datos: ColeccionCrearIn) -> ColeccionOut:
    """Alta de coleccion (flujo alternativo 1a)."""
    if repository.obtener_temporada(db, datos.temporada_id) is None:
        raise TemporadaInexistente(str(datos.temporada_id))

    if repository.existe_coleccion_con_nombre(
        db, temporada_id=datos.temporada_id, nombre=datos.nombre
    ):
        raise NombreDeColeccionDuplicado(datos.nombre)

    try:
        coleccion = repository.agregar_coleccion(
            db,
            temporada_id=datos.temporada_id,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            activa=datos.activa,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_coleccion_temporada_nombre"):
            raise NombreDeColeccionDuplicado(datos.nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_coleccion(db, coleccion.id)


def editar_coleccion(
    db: Session, coleccion_id: int, datos: ColeccionEditarIn
) -> ColeccionOut:
    """Edicion de coleccion (flujo alternativo 3a)."""
    coleccion = repository.obtener_coleccion(db, coleccion_id)
    if coleccion is None:
        raise ColeccionInexistente(str(coleccion_id))

    temporada_id = (
        datos.temporada_id if datos.temporada_id is not None else coleccion.temporada_id
    )
    if (
        datos.temporada_id is not None
        and repository.obtener_temporada(db, temporada_id) is None
    ):
        raise TemporadaInexistente(str(temporada_id))

    # Se comprueba contra la temporada y el nombre resultantes: mover la
    # coleccion a otra temporada puede chocar con una que ya esta ahi.
    nombre = datos.nombre or coleccion.nombre
    if repository.existe_coleccion_con_nombre(
        db, temporada_id=temporada_id, nombre=nombre, excepto_id=coleccion_id
    ):
        raise NombreDeColeccionDuplicado(nombre)

    try:
        coleccion.temporada_id = temporada_id
        if datos.nombre is not None:
            coleccion.nombre = datos.nombre
        if "descripcion" in datos.model_fields_set:
            coleccion.descripcion = datos.descripcion
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "uq_coleccion_temporada_nombre"):
            raise NombreDeColeccionDuplicado(nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_coleccion(db, coleccion_id)


def cambiar_estado_coleccion(
    db: Session, coleccion_id: int, activa: bool
) -> ColeccionOut:
    """Dar de baja o reactivar una coleccion.

    No se elimina: misma politica que sucursal y proveedor --- se conserva por
    trazabilidad --- y en el Ciclo 2 va a tener productos colgando.
    """
    coleccion = repository.obtener_coleccion(db, coleccion_id)
    if coleccion is None:
        raise ColeccionInexistente(str(coleccion_id))

    try:
        coleccion.activa = activa
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_coleccion(db, coleccion_id)
