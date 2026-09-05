"""
P3 - Catalogo  |  CU-09 Gestionar temporadas y colecciones  |  capa: repositorio

Ciclo de desarrollo: 1

Archivos propios para no chocar con el CU-08; el motivo esta en
`temporadas_schemas.py`.
"""
from datetime import date

from sqlalchemy import Row, func, or_, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Coleccion, Temporada

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.


# --- Temporadas ----------------------------------------------------------

def _seleccion_temporada():
    """Columnas del listado, con el recuento de colecciones.

    El `outerjoin` es lo que hace falta: una temporada recien creada no tiene
    colecciones, y con un join normal no aparecería en el listado.
    """
    return (
        select(
            Temporada.id,
            Temporada.nombre,
            Temporada.descripcion,
            Temporada.fecha_inicio,
            Temporada.fecha_fin,
            Temporada.activa,
            func.count(Coleccion.id).label("colecciones"),
            func.count(Coleccion.id)
            .filter(Coleccion.activa.is_(True))
            .label("colecciones_activas"),
        )
        .outerjoin(Coleccion, Coleccion.temporada_id == Temporada.id)
        .group_by(
            Temporada.id,
            Temporada.nombre,
            Temporada.descripcion,
            Temporada.fecha_inicio,
            Temporada.fecha_fin,
            Temporada.activa,
        )
    )


def listar_temporadas(
    db: Session, *, busqueda: str | None = None, activa: bool | None = None
) -> list[Row]:
    """Temporadas de la mas reciente a la mas antigua.

    Se ordena por fecha de inicio descendente y no por nombre: lo que se
    consulta a diario es la que esta corriendo, y esa es la de arriba.
    """
    consulta = _seleccion_temporada()

    if busqueda:
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Temporada.nombre).like(patron),
                func.lower(Temporada.descripcion).like(patron),
            )
        )
    if activa is not None:
        consulta = consulta.where(Temporada.activa.is_(activa))

    return list(
        db.execute(
            consulta.order_by(Temporada.fecha_inicio.desc(), Temporada.nombre)
        ).all()
    )


def obtener_temporada_detalle(db: Session, temporada_id: int) -> Row | None:
    """Una sola fila del listado, para devolver la temporada recien tocada."""
    return db.execute(
        _seleccion_temporada().where(Temporada.id == temporada_id)
    ).one_or_none()


def obtener_temporada(db: Session, temporada_id: int) -> Temporada | None:
    """La fila de temporada, para editarla o borrarla."""
    return db.get(Temporada, temporada_id)


def obtener_temporada_por_nombre(db: Session, nombre: str) -> Temporada | None:
    """Busca por nombre exacto, para detectar el duplicado antes de insertar."""
    return db.scalar(
        select(Temporada).where(func.lower(Temporada.nombre) == nombre.strip().lower())
    )


def temporadas_que_se_cruzan(
    db: Session,
    *,
    fecha_inicio: date,
    fecha_fin: date,
    excepto_id: int | None = None,
) -> list[Temporada]:
    """Temporadas ABIERTAS cuyo rango se superpone con el indicado.

    Dos rangos se cruzan cuando cada uno empieza antes de que el otro termine:
    `inicio_a <= fin_b AND inicio_b <= fin_a`. Es la formulacion que no deja
    fuera el caso de uno contenido dentro del otro, que es el que se escapa
    cuando se compara solo el inicio.

    Solo mira las abiertas: el caso de uso habla de "otra temporada activa", y
    una cerrada ya no compite por ser la vigente.
    """
    consulta = select(Temporada).where(
        Temporada.activa.is_(True),
        Temporada.fecha_inicio <= fecha_fin,
        fecha_inicio <= Temporada.fecha_fin,
    )
    if excepto_id is not None:
        consulta = consulta.where(Temporada.id != excepto_id)
    return list(db.scalars(consulta.order_by(Temporada.fecha_inicio)))


def agregar_temporada(
    db: Session,
    *,
    nombre: str,
    descripcion: str | None,
    fecha_inicio: date,
    fecha_fin: date,
    activa: bool,
) -> Temporada:
    """Crea la temporada. No confirma: la transaccion es del servicio."""
    temporada = Temporada(
        nombre=nombre,
        descripcion=descripcion,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        activa=activa,
    )
    db.add(temporada)
    db.flush()
    return temporada


def contar_colecciones_de_temporada(db: Session, temporada_id: int) -> tuple[int, int]:
    """Devuelve (total, activas) de las colecciones de la temporada.

    Las dos cifras deciden cosas distintas: el total impide la eliminacion
    (excepcion E3) porque `coleccion.temporada_id` no cascadea, y las activas
    dan el mensaje que la interfaz muestra.
    """
    fila = db.execute(
        select(
            func.count(Coleccion.id),
            func.count(Coleccion.id).filter(Coleccion.activa.is_(True)),
        ).where(Coleccion.temporada_id == temporada_id)
    ).one()
    return int(fila[0]), int(fila[1])


def eliminar_temporada(db: Session, temporada: Temporada) -> None:
    """Borra la temporada. El servicio ya comprobo que no tenga colecciones."""
    db.delete(temporada)
    db.flush()


# --- Colecciones (flujo alternativo 1a) ----------------------------------

def _seleccion_coleccion():
    """Columnas del listado de colecciones, con el nombre de su temporada."""
    return select(
        Coleccion.id,
        Coleccion.temporada_id,
        Temporada.nombre.label("temporada"),
        Coleccion.nombre,
        Coleccion.descripcion,
        Coleccion.activa,
    ).join(Temporada, Temporada.id == Coleccion.temporada_id)


def listar_colecciones(
    db: Session,
    *,
    busqueda: str | None = None,
    temporada_id: int | None = None,
    activa: bool | None = None,
) -> list[Row]:
    """Colecciones agrupadas por temporada, de la mas reciente a la mas vieja."""
    consulta = _seleccion_coleccion()

    if busqueda:
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Coleccion.nombre).like(patron),
                func.lower(Coleccion.descripcion).like(patron),
                func.lower(Temporada.nombre).like(patron),
            )
        )
    if temporada_id is not None:
        consulta = consulta.where(Coleccion.temporada_id == temporada_id)
    if activa is not None:
        consulta = consulta.where(Coleccion.activa.is_(activa))

    return list(
        db.execute(
            consulta.order_by(Temporada.fecha_inicio.desc(), Coleccion.nombre)
        ).all()
    )


def obtener_coleccion_detalle(db: Session, coleccion_id: int) -> Row | None:
    """Una sola fila del listado, para devolver la coleccion recien tocada."""
    return db.execute(
        _seleccion_coleccion().where(Coleccion.id == coleccion_id)
    ).one_or_none()


def obtener_coleccion(db: Session, coleccion_id: int) -> Coleccion | None:
    """La fila de coleccion, para editarla."""
    return db.get(Coleccion, coleccion_id)


def existe_coleccion_con_nombre(
    db: Session, *, temporada_id: int, nombre: str, excepto_id: int | None = None
) -> bool:
    """El nombre ya esta usado dentro de esa misma temporada.

    `excepto_id` deja fuera a la propia coleccion al editarla; sin eso, guardar
    sin cambiarle el nombre se rechazaria a si misma.
    """
    consulta = select(Coleccion.id).where(
        Coleccion.temporada_id == temporada_id,
        func.lower(Coleccion.nombre) == nombre.strip().lower(),
    )
    if excepto_id is not None:
        consulta = consulta.where(Coleccion.id != excepto_id)
    return db.scalar(consulta) is not None


def agregar_coleccion(
    db: Session,
    *,
    temporada_id: int,
    nombre: str,
    descripcion: str | None,
    activa: bool,
) -> Coleccion:
    """Crea la coleccion. No confirma: la transaccion es del servicio."""
    coleccion = Coleccion(
        temporada_id=temporada_id,
        nombre=nombre,
        descripcion=descripcion,
        activa=activa,
    )
    db.add(coleccion)
    db.flush()
    return coleccion
