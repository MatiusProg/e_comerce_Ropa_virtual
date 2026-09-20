"""
P7 - Punto de Venta / CU-32  |  capa: servicio (reglas de negocio)

Registrar devolucion: la prenda vuelve al inventario de la sucursal y, si se
habia pagado en efectivo, la plata sale del cajon.

UNA DEVOLUCION NO CORRIGE LA VENTA: ES UN HECHO NUEVO
------------------------------------------------------
No se edita la `Venta`, no se borra el `DetalleVenta`, no se toca el
movimiento de `VENTA`. Los movimientos de inventario son INMUTABLES (D4), y la
venta lo es por el mismo motivo: si se editara, el historial diria que la
prenda nunca se vendio --- y el reporte de rotacion, el ticket promedio de
CU-36 y el arqueo del turno en que se cobro cambiarian solos, hacia atras ---.

Lo que la devolucion escribe es: una fila `Devolucion`, sus `DetalleDevolucion`
y un movimiento `DEVOLUCION +n` por cada prenda. La venta sigue diciendo lo que
dijo el dia que ocurrio.

EL `monto` ES LO QUE SALE DEL CAJON, NO LO QUE VALE LA PRENDA
-------------------------------------------------------------
Lo fija CU-30, que lo resta del esperado del turno. Si una venta cobrada con
tarjeta sumara ahi, el arqueo cerraria con un faltante inexplicable: esa plata
nunca entro al cajon y no puede salir de el.

Asi que `monto` vale el reintegro **solo si la venta se cobro en EFECTIVO**. En
los otros casos la prenda vuelve al inventario igual ---eso no depende de como
se pago--- y el dinero se reintegra por donde vino, que es una gestion fuera
del mostrador. El contrato lo dice con `sale_del_cajon`, para que la pantalla
pueda decirselo al cajero en vez de dejarlo suponer.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.inventario import service as inventario
from app.modules.pos import devolucion_repository as repository
from app.modules.pos import repository as pos_repository
from app.modules.pos.devolucion_schemas import (
    DevolucionIn,
    DevolucionOut,
    LineaDevolvibleOut,
    LineaDevueltaOut,
    VentaDevolvibleOut,
)
from app.modules.pos.service import ErrorDeMostrador, mostrador_de

CERO = Decimal("0.00")

#: Solo lo cobrado en billetes puede devolverse en billetes.
METODO_EFECTIVO = "EFECTIVO"


class VentaNoDevolvible(ErrorDeMostrador):
    """No hay una venta cobrada con ese codigo en esta sucursal.

    Un solo mensaje para «no existe», «es de otra sucursal», «no se llego a
    pagar» y «esta cancelada»: convencion 1 del ciclo.
    """

    def __init__(self, codigo: str) -> None:
        super().__init__(
            f"No hay ninguna venta cobrada con el código {codigo} en su sucursal.",
            404,
        )


class PrendaNoVendidaEnEsaVenta(ErrorDeMostrador):
    def __init__(self, variante_ids: list[int]) -> None:
        self.variante_ids = variante_ids
        super().__init__(
            "Alguna de las prendas no figura en esa venta.", 422
        )


class DevuelveDeMas(ErrorDeMostrador):
    """Se quiso devolver mas unidades de las que quedan por devolver."""

    def __init__(self, prenda: str, devolvibles: int, solicitado: int) -> None:
        self.prenda = prenda
        self.devolvibles = devolvibles
        self.solicitado = solicitado
        if devolvibles == 0:
            mensaje = f"«{prenda}» ya se devolvió entera."
        else:
            mensaje = (
                f"De «{prenda}» quedan {devolvibles} por devolver "
                f"y se pidieron {solicitado}."
            )
        super().__init__(mensaje, 409)


def _nombre(fila) -> str:
    return " · ".join(p for p in (fila.producto, fila.talla, fila.color) if p)


def _unitario(fila) -> Decimal:
    """Lo que el cliente pago por unidad: precio congelado menos su descuento."""
    return fila.precio_unitario - fila.descuento_unitario


def _sale_del_cajon(venta) -> bool:
    return venta.metodo_pago == METODO_EFECTIVO


# =====================================================================
# Paso 1: que se puede devolver de esta venta
# =====================================================================

def buscar_venta(db: Session, usuario_id: int, codigo: str) -> VentaDevolvibleOut:
    """La venta y lo que todavia queda por devolver de ella."""
    mostrador = mostrador_de(db, usuario_id)
    venta = repository.venta_devolvible(
        db, codigo=codigo, sucursal_id=mostrador.sucursal_id
    )
    if venta is None:
        raise VentaNoDevolvible(codigo)

    devueltas = repository.ya_devuelto(db, venta.id)
    lineas = [
        LineaDevolvibleOut(
            variante_id=fila.variante_id,
            sku=fila.sku,
            producto=fila.producto,
            talla=fila.talla,
            color=fila.color,
            vendidas=fila.cantidad,
            devueltas=devueltas.get(fila.variante_id, 0),
            devolvibles=fila.cantidad - devueltas.get(fila.variante_id, 0),
            precio_unitario=_unitario(fila),
        )
        for fila in repository.lineas_vendidas(db, venta.id)
    ]

    return VentaDevolvibleOut(
        codigo=venta.codigo,
        estado=venta.estado,
        # Una venta digital no tiene metodo: la cobro la pasarela.
        metodo_pago=venta.metodo_pago or "PASARELA",
        creado_en=venta.creado_en,
        cliente=pos_repository.cliente_de_venta(db, venta.cliente_id),
        total=venta.total,
        sale_del_cajon=_sale_del_cajon(venta),
        lineas=lineas,
    )


# =====================================================================
# Paso 2: registrarla
# =====================================================================

def registrar(db: Session, usuario_id: int, datos: DevolucionIn) -> DevolucionOut:
    """Recibe la prenda de vuelta. **Hace commit.**

    Todo en una transaccion: la devolucion, sus lineas y el reingreso al
    inventario. Si algo falla no queda ni una devolucion sin mercaderia ni
    mercaderia reingresada sin devolucion que la explique.
    """
    mostrador = mostrador_de(db, usuario_id)

    venta = repository.venta_devolvible(
        db, codigo=datos.venta_codigo, sucursal_id=mostrador.sucursal_id
    )
    if venta is None:
        raise VentaNoDevolvible(datos.venta_codigo)

    # Serializa las devoluciones de esta venta ANTES de leer lo ya devuelto: sin
    # el bloqueo, dos devoluciones simultaneas leen el mismo saldo y las dos
    # devuelven la ultima unidad.
    repository.bloquear_venta(db, venta.id)

    vendidas = {f.variante_id: f for f in repository.lineas_vendidas(db, venta.id)}
    devueltas = repository.ya_devuelto(db, venta.id)

    ajenas = [l.variante_id for l in datos.lineas if l.variante_id not in vendidas]
    if ajenas:
        raise PrendaNoVendidaEnEsaVenta(ajenas)

    lineas: list[tuple[int, int, Decimal, str]] = []
    for pedida in datos.lineas:
        fila = vendidas[pedida.variante_id]
        devolvibles = fila.cantidad - devueltas.get(pedida.variante_id, 0)
        if pedida.cantidad > devolvibles:
            raise DevuelveDeMas(_nombre(fila), devolvibles, pedida.cantidad)
        lineas.append(
            (pedida.variante_id, pedida.cantidad, _unitario(fila), _nombre(fila))
        )

    valor = sum((precio * cantidad for _, cantidad, precio, _ in lineas), CERO)
    sale = _sale_del_cajon(venta)

    devolucion = repository.agregar_devolucion(
        db,
        venta_id=venta.id,
        turno_caja_id=mostrador.turno_id,
        motivo=datos.motivo,
        # Cero si no se pago en efectivo: el arqueo del turno resta esto, y una
        # devolucion de una venta con tarjeta dejaria el cajon con un faltante
        # de plata que nunca entro.
        monto=valor if sale else CERO,
    )

    for variante_id, cantidad, _precio, nombre in lineas:
        repository.agregar_detalle(
            db,
            devolucion_id=devolucion.id,
            variante_id=variante_id,
            cantidad=cantidad,
        )
        # La prenda vuelve al inventario SIEMPRE, se haya pagado como se haya
        # pagado: lo que volvio al local esta en el local.
        inventario.reingresar_por_devolucion(
            db,
            variante_id=variante_id,
            sucursal_id=mostrador.sucursal_id,
            cantidad=cantidad,
            usuario_id=usuario_id,
            motivo=f"Devolución de {venta.codigo}: {datos.motivo}"[:200],
        )

    db.commit()
    db.refresh(devolucion)

    return DevolucionOut(
        id=devolucion.id,
        venta_codigo=venta.codigo,
        caja_nombre=mostrador.caja_nombre,
        motivo=devolucion.motivo,
        creado_en=devolucion.creado_en,
        lineas=[
            LineaDevueltaOut(
                variante_id=variante_id,
                sku=vendidas[variante_id].sku,
                producto=vendidas[variante_id].producto,
                talla=vendidas[variante_id].talla,
                color=vendidas[variante_id].color,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=precio * cantidad,
            )
            for variante_id, cantidad, precio, _nombre_legible in lineas
        ],
        valor_devuelto=valor,
        monto=devolucion.monto,
        sale_del_cajon=sale,
    )


__all__ = [
    "DevuelveDeMas",
    "PrendaNoVendidaEnEsaVenta",
    "VentaNoDevolvible",
    "buscar_venta",
    "registrar",
]
