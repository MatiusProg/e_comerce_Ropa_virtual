"""
P7 - Ventas / CU-29  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 3
Caso de uso: CU-29 Consultar historial de compras

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit.

SE APOYA EN `_seleccion_pedido` DE CU-27
-----------------------------------------
La consulta del historial y la de la ficha de un pedido devuelven **lo mismo**:
la venta con su sucursal y el estado de su pago. Escribir un segundo `SELECT`
con las mismas columnas dejaria dos lugares donde agregar un campo, y el dia que
alguien agregue uno solo a la ficha, el historial mostraria menos sin que nada
falle.
"""
from sqlalchemy import Row, func, select
from sqlalchemy.orm import Session

from app.modules.ventas.models import Comprobante, Venta
from app.modules.ventas.repository import _seleccion_pedido


def contar_compras(db: Session, cliente_id: int) -> int:
    return db.scalar(
        select(func.count(Venta.id)).where(Venta.cliente_id == cliente_id)
    ) or 0


def listar_compras(
    db: Session, *, cliente_id: int, limite: int, desplazamiento: int
) -> list[Row]:
    """Las compras del cliente, de la mas nueva a la mas vieja.

    **Van TODAS, incluidas las canceladas y las que esperan pago.** Un historial
    que solo mostrara lo pagado dejaria al cliente sin forma de encontrar el
    pedido que acaba de hacer ---que es justo el que va a buscar--- ni de
    entender por que un cobro que recuerda no aparece. El estado se muestra; la
    fila no se esconde.

    Desempata por `id` descendente: dos pedidos del mismo segundo ---que pasa
    cuando alguien pulsa dos veces--- se intercambiarian entre recargas sin un
    segundo criterio, y la lista parpadearia sin que nada haya cambiado.
    """
    return list(
        db.execute(
            _seleccion_pedido()
            .where(Venta.cliente_id == cliente_id)
            .order_by(Venta.creado_en.desc(), Venta.id.desc())
            .limit(limite)
            .offset(desplazamiento)
        ).all()
    )


def obtener_comprobante(db: Session, venta_id: int) -> Comprobante | None:
    """El comprobante de una venta, si ya se emitio.

    `venta_id` es UNICO en `comprobante`, asi que esto devuelve uno o ninguno.
    Reimprimir no es reemitir: la segunda descarga devuelve **este mismo**, con
    su numero y su fecha de emision originales.
    """
    return db.scalar(select(Comprobante).where(Comprobante.venta_id == venta_id))


def agregar_comprobante(
    db: Session, *, venta_id: int, tipo: str, numero: str
) -> Comprobante:
    """Emite el comprobante de una venta. **Sin commit.**

    `nit_ci` y `razon_social` quedan nulos: es un RECIBO, y el CHECK
    `factura_con_datos` solo los exige en una FACTURA. Facturar con datos
    fiscales es otra conversacion ---hay que pedirselos al cliente--- y no entra
    en el alcance de este ciclo.
    """
    comprobante = Comprobante(venta_id=venta_id, tipo=tipo, numero=numero)
    db.add(comprobante)
    db.flush()
    return comprobante
