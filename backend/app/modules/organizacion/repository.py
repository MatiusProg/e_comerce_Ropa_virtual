"""
P2 - Organizacion  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from datetime import time

from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Ciudad, Sucursal

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.


# --- CU-05 Ciudades ------------------------------------------------------

def listar_ciudades(db: Session, *, busqueda: str | None = None) -> list[Row]:
    """Ciudades con el recuento de sus sucursales, totales y activas.

    Los dos recuentos salen en la misma consulta: pedirlos por separado seria
    una consulta por ciudad, y la interfaz los necesita para las dos filas
    (cuantas tiene y si se puede eliminar).
    """
    consulta = (
        select(
            Ciudad.id,
            Ciudad.nombre,
            Ciudad.departamento,
            func.count(Sucursal.id).label("sucursales"),
            func.count(Sucursal.id)
            .filter(Sucursal.activa.is_(True))
            .label("sucursales_activas"),
        )
        .outerjoin(Sucursal, Sucursal.ciudad_id == Ciudad.id)
        .group_by(Ciudad.id, Ciudad.nombre, Ciudad.departamento)
        .order_by(Ciudad.nombre)
    )

    if busqueda:
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            func.lower(Ciudad.nombre).like(patron)
            | func.lower(Ciudad.departamento).like(patron)
        )

    return list(db.execute(consulta).all())


def obtener_ciudad_con_recuento(db: Session, ciudad_id: int) -> Row | None:
    """Una sola fila del listado, para devolver la ciudad recien tocada."""
    return db.execute(
        select(
            Ciudad.id,
            Ciudad.nombre,
            Ciudad.departamento,
            func.count(Sucursal.id).label("sucursales"),
            func.count(Sucursal.id)
            .filter(Sucursal.activa.is_(True))
            .label("sucursales_activas"),
        )
        .outerjoin(Sucursal, Sucursal.ciudad_id == Ciudad.id)
        .where(Ciudad.id == ciudad_id)
        .group_by(Ciudad.id, Ciudad.nombre, Ciudad.departamento)
    ).one_or_none()


def obtener_ciudad(db: Session, ciudad_id: int) -> Ciudad | None:
    """La fila de ciudad, para editarla o borrarla."""
    return db.get(Ciudad, ciudad_id)


def obtener_ciudad_por_nombre(db: Session, nombre: str) -> Ciudad | None:
    """Busca por nombre exacto, para detectar el duplicado antes de insertar."""
    return db.scalar(select(Ciudad).where(Ciudad.nombre == nombre))


def agregar_ciudad(db: Session, *, nombre: str, departamento: str) -> Ciudad:
    """Crea la ciudad. No confirma: la transaccion es del servicio."""
    ciudad = Ciudad(nombre=nombre, departamento=departamento)
    db.add(ciudad)
    db.flush()
    return ciudad


def contar_sucursales_de_ciudad(db: Session, ciudad_id: int) -> tuple[int, int]:
    """Devuelve (total, activas) de las sucursales de la ciudad.

    Las dos cifras deciden cosas distintas: las activas disparan la excepcion
    E2, y el total impide el borrado aunque esten todas dadas de baja, porque
    `sucursal.ciudad_id` no cascadea.
    """
    fila = db.execute(
        select(
            func.count(Sucursal.id),
            func.count(Sucursal.id).filter(Sucursal.activa.is_(True)),
        ).where(Sucursal.ciudad_id == ciudad_id)
    ).one()
    return int(fila[0]), int(fila[1])


def eliminar_ciudad(db: Session, ciudad: Ciudad) -> None:
    """Borra la ciudad. El servicio ya comprobo que no tenga sucursales."""
    db.delete(ciudad)
    db.flush()


# --- CU-05 Sucursales ----------------------------------------------------

def _seleccion_sucursal():
    """Las columnas del listado de sucursales, con el nombre de su ciudad.

    Se comparte entre el listado y el detalle para que las dos respuestas
    tengan exactamente la misma forma.
    """
    return (
        select(
            Sucursal.id,
            Sucursal.nombre,
            Sucursal.ciudad_id,
            Ciudad.nombre.label("ciudad"),
            Sucursal.direccion,
            Sucursal.telefono,
            Sucursal.horario_apertura,
            Sucursal.horario_cierre,
            Sucursal.capacidad_vestidores,
            Sucursal.activa,
        )
        .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
    )


def listar_sucursales(
    db: Session,
    *,
    busqueda: str | None = None,
    ciudad_id: int | None = None,
    activa: bool | None = None,
) -> list[Row]:
    """Sucursales con el nombre de su ciudad, ordenadas por ciudad y nombre.

    `activa=None` devuelve todas, que es lo que necesita CU-05 para poder dar
    de alta una sucursal que estaba de baja. El selector de CU-03 pide
    `activa=True` explicitamente.
    """
    consulta = _seleccion_sucursal()

    if busqueda:
        patron = f"%{busqueda.strip().lower()}%"
        consulta = consulta.where(
            func.lower(Sucursal.nombre).like(patron)
            | func.lower(Sucursal.direccion).like(patron)
            | func.lower(Ciudad.nombre).like(patron)
        )
    if ciudad_id is not None:
        consulta = consulta.where(Sucursal.ciudad_id == ciudad_id)
    if activa is not None:
        consulta = consulta.where(Sucursal.activa.is_(activa))

    return list(db.execute(consulta.order_by(Ciudad.nombre, Sucursal.nombre)).all())


def obtener_sucursal_con_ciudad(db: Session, sucursal_id: int) -> Row | None:
    """Una sola fila del listado, para devolver la sucursal recien tocada."""
    return db.execute(
        _seleccion_sucursal().where(Sucursal.id == sucursal_id)
    ).one_or_none()


def obtener_sucursal(db: Session, sucursal_id: int) -> Sucursal | None:
    """La fila de sucursal, para editarla."""
    return db.get(Sucursal, sucursal_id)


def existe_sucursal_con_nombre(
    db: Session, *, ciudad_id: int, nombre: str, excepto_id: int | None = None
) -> bool:
    """Excepcion E1: el nombre ya esta usado dentro de esa misma ciudad.

    `excepto_id` deja fuera a la propia sucursal al editarla; sin eso, guardar
    sin cambiarle el nombre se rechazaria a si misma.
    """
    consulta = select(Sucursal.id).where(
        Sucursal.ciudad_id == ciudad_id,
        func.lower(Sucursal.nombre) == nombre.strip().lower(),
    )
    if excepto_id is not None:
        consulta = consulta.where(Sucursal.id != excepto_id)
    return db.scalar(consulta) is not None


def agregar_sucursal(
    db: Session,
    *,
    ciudad_id: int,
    nombre: str,
    direccion: str,
    telefono: str | None,
    horario_apertura: time,
    horario_cierre: time,
    capacidad_vestidores: int,
    activa: bool,
) -> Sucursal:
    """Crea la sucursal. No confirma: la transaccion es del servicio."""
    sucursal = Sucursal(
        ciudad_id=ciudad_id,
        nombre=nombre,
        direccion=direccion,
        telefono=telefono,
        horario_apertura=horario_apertura,
        horario_cierre=horario_cierre,
        capacidad_vestidores=capacidad_vestidores,
        activa=activa,
    )
    db.add(sucursal)
    db.flush()
    return sucursal


# TODO CU-06 y CU-07: implementar el resto de las consultas.
