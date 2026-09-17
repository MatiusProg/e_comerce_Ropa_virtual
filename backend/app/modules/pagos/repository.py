"""
P8 - Pagos  |  capa: repositorio (consultas)

Ciclo de desarrollo: 3
Casos de uso: CU-27 (iniciar el pago), CU-28 (confirmarlo)

Regla: aqui vive el SQL. Ninguna regla de negocio y ningun `commit`.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pagos.models import Pago, TransaccionPasarela


def agregar_pago(
    db: Session,
    *,
    venta_id: int,
    metodo: str,
    estado: str,
    monto,
    referencia_externa: str | None,
) -> Pago:
    pago = Pago(
        venta_id=venta_id,
        metodo=metodo,
        estado=estado,
        monto=monto,
        referencia_externa=referencia_externa,
    )
    db.add(pago)
    db.flush()
    return pago


def obtener_por_venta(db: Session, venta_id: int, *, bloquear: bool = False) -> Pago | None:
    consulta = select(Pago).where(Pago.venta_id == venta_id)
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def obtener_por_referencia(
    db: Session, referencia_externa: str, *, bloquear: bool = False
) -> Pago | None:
    """El pago de una sesion de la pasarela. Lo usa CU-28.

    `referencia_externa` es UNICO, asi que esto devuelve uno o ninguno.
    """
    consulta = select(Pago).where(Pago.referencia_externa == referencia_externa)
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def agregar_transaccion(
    db: Session,
    *,
    pago_id: int | None,
    evento_id: str,
    tipo_evento: str,
    firma_valida: bool,
    carga_util: str,
) -> TransaccionPasarela:
    """Guarda lo que la pasarela dijo. Lo usa CU-28.

    El `UNIQUE` sobre `evento_id` hace que un evento repetido reviente aca con
    `IntegrityError`, y ESO es la idempotencia: el servicio lo atrapa y lo
    trata como «ya visto» sin volver a tocar la venta. Ver el modelo.
    """
    transaccion = TransaccionPasarela(
        pago_id=pago_id,
        evento_id=evento_id,
        tipo_evento=tipo_evento,
        firma_valida=firma_valida,
        carga_util=carga_util,
    )
    db.add(transaccion)
    db.flush()
    return transaccion
