"""
P7 - Ventas y POS / CU-30  |  capa: repositorio (consultas, sin logica ni commit)
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Sucursal
from app.modules.ventas.models import Caja, Devolucion, TurnoCaja, Venta


def caja_por_id(db: Session, caja_id: int) -> Caja | None:
    return db.get(Caja, caja_id)


def sucursal_activa(db: Session, sucursal_id: int) -> Sucursal | None:
    return db.scalar(
        select(Sucursal).where(
            Sucursal.id == sucursal_id, Sucursal.activa.is_(True)
        )
    )


def cajas_de_sucursal(db: Session, sucursal_id: int) -> list[Caja]:
    return list(
        db.scalars(
            select(Caja)
            .where(Caja.sucursal_id == sucursal_id, Caja.activa.is_(True))
            .order_by(Caja.nombre)
        )
    )


def turno_abierto_de_caja(db: Session, caja_id: int) -> TurnoCaja | None:
    return db.scalar(
        select(TurnoCaja).where(
            TurnoCaja.caja_id == caja_id, TurnoCaja.cerrado_en.is_(None)
        )
    )


def turno_abierto_de_usuario(db: Session, usuario_id: int) -> TurnoCaja | None:
    """El turno que esta persona tiene abierto, si tiene alguno.

    Es lo que la pantalla pregunta al entrar: sin esto, el cajero no sabe si
    ya abrio y tendria que acordarse.
    """
    return db.scalar(
        select(TurnoCaja).where(
            TurnoCaja.usuario_id == usuario_id, TurnoCaja.cerrado_en.is_(None)
        )
    )


def bloquear_caja(db: Session, caja_id: int) -> Caja | None:
    """Serializa las aperturas de UNA caja. **Sin commit.**

    POR QUE HACE FALTA, SI YA HAY UN INDICE UNICO PARCIAL
    ------------------------------------------------------
    El indice `ix_turno_caja_abierto` impide dos turnos abiertos en la misma
    caja, asi que la base nunca queda mal. Lo que el bloqueo evita es el
    SINTOMA: sin el, dos aperturas simultaneas llegan las dos a la insercion y
    una revienta con un error de integridad --- que el cajero ve como «error
    del sistema» cuando lo correcto es decirle «esta caja ya esta abierta».
    Con el bloqueo, la segunda espera, encuentra el turno y recibe el mensaje
    que explica que pasa.

    Se bloquea la CAJA y no el turno porque el turno que estorba todavia no
    existe: no se puede bloquear una fila que la otra peticion esta por
    insertar.
    """
    return db.scalar(select(Caja).where(Caja.id == caja_id).with_for_update())


def efectivo_cobrado(db: Session, turno_id: int) -> Decimal:
    """Lo que entro al cajon durante el turno.

    SOLO EFECTIVO, Y SOLO PAGADAS O ENTREGADAS.
    Tarjeta y QR no entran al cajon: sumarlos haria que el turno apareciera
    descuadrado por cada pago que no fue en billetes. Y una venta cancelada no
    se cobro, aunque quede colgada del turno.
    """
    total = db.scalar(
        select(func.coalesce(func.sum(Venta.total), 0)).where(
            Venta.turno_caja_id == turno_id,
            Venta.metodo_pago == "EFECTIVO",
            Venta.estado.in_(("PAGADA", "ENTREGADA")),
        )
    )
    return Decimal(total or 0)


def devoluciones_del_turno(db: Session, turno_id: int) -> Decimal:
    """Lo que salio del cajon por devoluciones (CU-32).

    Hoy da siempre cero porque CU-32 no esta construido. Se consulta igual, y
    no se deja para despues: cuando la devolucion exista, el arqueo tiene que
    contarla **sin que nadie se acuerde de volver aca**. Es una consulta
    barata contra una tabla vacia.
    """
    total = db.scalar(
        select(func.coalesce(func.sum(Devolucion.monto), 0)).where(
            Devolucion.turno_caja_id == turno_id
        )
    )
    return Decimal(total or 0)


def ventas_del_turno(db: Session, turno_id: int) -> list[tuple[str, int, Decimal]]:
    """Cuantas ventas y cuanto, por metodo de pago. Para el detalle del cierre."""
    return [
        (fila[0], int(fila[1]), Decimal(fila[2] or 0))
        for fila in db.execute(
            select(
                Venta.metodo_pago,
                func.count(Venta.id),
                func.coalesce(func.sum(Venta.total), 0),
            )
            .where(
                Venta.turno_caja_id == turno_id,
                Venta.estado.in_(("PAGADA", "ENTREGADA")),
            )
            .group_by(Venta.metodo_pago)
            .order_by(Venta.metodo_pago)
        ).all()
    ]


def turno_por_id(db: Session, turno_id: int) -> TurnoCaja | None:
    return db.get(TurnoCaja, turno_id)


def abrir(
    db: Session, *, caja_id: int, usuario_id: int, monto_apertura: Decimal
) -> TurnoCaja:
    """Crea el turno. **Sin commit.**"""
    turno = TurnoCaja(
        caja_id=caja_id, usuario_id=usuario_id, monto_apertura=monto_apertura
    )
    db.add(turno)
    db.flush()
    return turno
