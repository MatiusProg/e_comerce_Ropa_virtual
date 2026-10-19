"""
P13 - Notificaciones / CU-40  |  capa: repositorio (consultas)

Ninguna funcion de aca hace `commit`. La transaccion la controla quien llama,
que es la regla del proyecto y que en este caso importa mas que en otros: un
aviso de «reserva creada» tiene que nacer y morir junto con la reserva. Si el
repositorio confirmara por su cuenta, una reserva que despues falla dejaria al
Encargado avisado de algo que no existe.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.modules.notificaciones.models import Notificacion


def crear(
    db: Session,
    *,
    destinatario_id: int,
    tipo: str,
    titulo: str,
    cuerpo: str,
    enlace: str | None,
    entidad: str | None,
    entidad_id: int | None,
    correo_estado: str,
) -> Notificacion:
    """Inserta el aviso y lo deja en la sesion, SIN confirmar."""
    fila = Notificacion(
        destinatario_id=destinatario_id,
        tipo=tipo,
        titulo=titulo,
        cuerpo=cuerpo,
        enlace=enlace,
        entidad=entidad,
        entidad_id=entidad_id,
        correo_estado=correo_estado,
    )
    db.add(fila)
    # `flush` y no `commit`: le da el id a la fila ---que el llamador puede
    # necesitar--- sin cerrar la transaccion de quien nos llamo.
    db.flush()
    return fila


def contar_de(db: Session, destinatario_id: int, *, solo_no_leidas: bool = False) -> int:
    consulta = select(func.count(Notificacion.id)).where(
        Notificacion.destinatario_id == destinatario_id
    )
    if solo_no_leidas:
        consulta = consulta.where(Notificacion.leida_en.is_(None))
    return int(db.execute(consulta).scalar_one())


def listar_de(
    db: Session,
    destinatario_id: int,
    *,
    solo_no_leidas: bool = False,
    pagina: int = 1,
    tamano: int = 20,
) -> list[Notificacion]:
    """Las suyas, de la mas nueva a la mas vieja."""
    consulta = select(Notificacion).where(
        Notificacion.destinatario_id == destinatario_id
    )
    if solo_no_leidas:
        consulta = consulta.where(Notificacion.leida_en.is_(None))
    consulta = (
        consulta.order_by(Notificacion.creada_en.desc(), Notificacion.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return list(db.execute(consulta).scalars().all())


def obtener_de(db: Session, notificacion_id: int, destinatario_id: int) -> Notificacion | None:
    """Una suya, o None.

    El `destinatario_id` va en el WHERE y no se comprueba despues de leer: es
    la regla de ambito del proyecto ---«un dato de ambito no se acepta y se
    comprueba: no se acepta»---. Asi no hay dos lugares donde el mismo olvido
    abra el agujero, y el aviso de otro sale como 404 y no como 403.
    """
    return db.execute(
        select(Notificacion).where(
            Notificacion.id == notificacion_id,
            Notificacion.destinatario_id == destinatario_id,
        )
    ).scalar_one_or_none()


def marcar_leidas(
    db: Session,
    destinatario_id: int,
    *,
    momento: datetime,
    notificacion_id: int | None = None,
) -> int:
    """Marca una o todas las no leidas. Devuelve cuantas cambio.

    Solo toca las que estan sin leer: volver a marcar una ya leida moveria su
    fecha y borraria cuando se entero de verdad.
    """
    sentencia = (
        update(Notificacion)
        .where(
            Notificacion.destinatario_id == destinatario_id,
            Notificacion.leida_en.is_(None),
        )
        .values(leida_en=momento)
    )
    if notificacion_id is not None:
        sentencia = sentencia.where(Notificacion.id == notificacion_id)
    return int(db.execute(sentencia).rowcount or 0)


def listar_pendientes_de_correo(db: Session, *, limite: int) -> list[Notificacion]:
    """Las que esperan salir por correo, de la mas vieja a la mas nueva.

    De la mas vieja primero a proposito: si el proveedor estuvo caido un rato,
    lo que se acumulo se manda en el orden en que ocurrio.
    """
    return list(
        db.execute(
            select(Notificacion)
            .where(Notificacion.correo_estado == "PENDIENTE")
            .order_by(Notificacion.creada_en.asc(), Notificacion.id.asc())
            .limit(limite)
        )
        .scalars()
        .all()
    )
