"""
P7 - Punto de Venta / CU-32  |  capa: servicio (reglas de negocio)

Registrar devolucion: la prenda vuelve al inventario de la sucursal y, si se
habia pagado en efectivo, la plata sale del cajon.

DOS FLUJOS, UN SOLO CASO DE USO (0020)
---------------------------------------
    DEVOLUCION  la prenda vuelve y la plata se reintegra
    CAMBIO      la prenda vuelve, otra sale, y solo se mueve la diferencia

Son un caso de uso y no dos porque el cliente elige entre los dos **con la
prenda ya sobre el mostrador**: la decision es parte del mismo tramite, no un
tramite distinto. Comparten el actor, la precondicion ---una venta cobrada en
esta sucursal, dentro del plazo--- y la mitad del recorrido: lo que vuelve se
valida igual en los dos (`_lineas_que_vuelven`).

Se separan en el ultimo paso, que es a donde va el valor de lo devuelto: al
cajon, o contra una prenda nueva.

EL PLAZO SE INFORMA AL BUSCAR Y SE EXIGE AL REGISTRAR
------------------------------------------------------
`buscar_venta` devuelve una venta vencida igual, con `dentro_de_plazo` en
falso: el cajero necesita poder abrirla para explicarle al cliente por que no
se puede y desde cuando. Lo que no se puede es registrar contra ella.

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

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.config import settings
from app.modules.catalogo import promociones_service as promociones
from app.modules.inventario import service as inventario
from app.modules.pos import devolucion_repository as repository
from app.modules.pos import repository as pos_repository
from app.modules.pos.devolucion_schemas import (
    CambioIn,
    CambioOut,
    DevolucionIn,
    DevolucionOut,
    LineaDevolvibleOut,
    LineaDevueltaOut,
    LineaLlevadaOut,
    VentaDevolvibleOut,
)
from app.modules.pos.service import (
    ErrorDeMostrador,
    PrendaNoVendible,
    SinStock,
    generar_codigo_de_venta,
    mostrador_de,
)
from app.modules.ventas import historial_service

CERO = Decimal("0.00")

#: Solo lo cobrado en billetes puede devolverse en billetes.
METODO_EFECTIVO = "EFECTIVO"

#: Lo que lleva `venta.metodo_pago` en la venta que nace de un cambio. No es
#: una forma de cobrar --- ver `ventas.models.METODOS_VENTA` ---.
METODO_CAMBIO = "CAMBIO"


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


class FueraDePlazo(ErrorDeMostrador):
    """La venta es mas vieja que el plazo que la tienda da para volver.

    409 y no 422: el pedido esta bien formado y la prenda existe: lo que pasa
    es que el mundo cambio de estado desde que se vendio. Es el mismo codigo
    que `DevuelveDeMas`, por el mismo motivo.
    """

    def __init__(self, vencio_en: datetime, plazo_dias: int) -> None:
        self.vencio_en = vencio_en
        self.plazo_dias = plazo_dias
        dias = "1 día" if plazo_dias == 1 else f"{plazo_dias} días"
        super().__init__(
            f"El plazo para devolver o cambiar es de {dias} desde la compra,"
            f" y venció el {tiempo.en_bolivia(vencio_en):%d/%m/%Y a las %H:%M}.",
            409,
        )


class CambioSinMetodo(ErrorDeMostrador):
    """Hay diferencia que saldar y nadie dijo por donde se salda."""

    def __init__(self, diferencia: Decimal) -> None:
        self.diferencia = diferencia
        if diferencia > CERO:
            que = f"cobrar Bs {diferencia}"
        else:
            que = f"entregar Bs {-diferencia}"
        super().__init__(
            f"Hay que {que} de diferencia: indique la forma de pago.", 422
        )


class CambioSinNada(ErrorDeMostrador):
    """Se mando un metodo de diferencia y el cambio salio parejo.

    No se ignora en silencio: guardarlo dejaria en la base un metodo de pago
    contra una diferencia de cero, y el CHECK
    `ck_devolucion_metodo_si_hay_diferencia` lo rechazaria con un error de
    integridad --- que la pantalla mostraria como «error del sistema» ---.
    """

    def __init__(self) -> None:
        super().__init__(
            "Las dos prendas valen lo mismo: no hay diferencia que cobrar"
            " ni que entregar.",
            422,
        )


class DiferenciaCambiada(ErrorDeMostrador):
    """La pantalla calculo una diferencia y el servidor calculo otra.

    Mismo espiritu que `ConflictoDePrecio` en CU-31: entre que el cajero armo
    el cambio y confirmo, una promocion de CU-12 pudo empezar o terminar. Se
    frena y se le muestra el numero nuevo, en vez de cobrarle al cliente algo
    distinto de lo que vio en pantalla.
    """

    def __init__(self, esperada: Decimal, real: Decimal) -> None:
        self.esperada = esperada
        self.real = real
        super().__init__(
            f"La diferencia cambió: la pantalla decía Bs {esperada} y ahora es"
            f" Bs {real}. Revise el cambio antes de confirmarlo.",
            409,
        )


def _vence_en(venta) -> datetime:
    """Hasta cuando se acepta que esta venta vuelva.

    Se cuenta en HORAS desde el cobro y no en fechas de calendario: con fechas,
    quien compra un lunes a las 23:50 tendria casi tres dias y quien compra ese
    mismo lunes a las 08:00 tendria poco mas de dos. El plazo es el mismo para
    los dos o no es un plazo.
    """
    creado = venta.creado_en
    if creado.tzinfo is None:  # pragma: no cover - la columna es timestamptz
        creado = creado.replace(tzinfo=timezone.utc)
    return creado + timedelta(days=settings.DEVOLUCION_PLAZO_DIAS)


def _exigir_plazo(venta) -> None:
    vence = _vence_en(venta)
    if tiempo.ahora() > vence:
        raise FueraDePlazo(vence, settings.DEVOLUCION_PLAZO_DIAS)


def _nombre(fila) -> str:
    return " · ".join(p for p in (fila.producto, fila.talla, fila.color) if p)


def _unitario(fila) -> Decimal:
    """Lo que el cliente pago por unidad: precio congelado menos su descuento."""
    return fila.precio_unitario - fila.descuento_unitario


def _sale_del_cajon(venta) -> bool:
    return venta.metodo_pago == METODO_EFECTIVO


def _lineas_que_vuelven(db: Session, venta, pedidas):
    """Valida lo que el cliente trae y lo resuelve a lineas con precio y nombre.

    Lo comparten los dos flujos de CU-32: lo que vuelve en un cambio se
    comprueba exactamente igual que lo que vuelve en una devolucion ---que este
    en esa venta, que no se haya devuelto ya, y a que precio se pago---. Lo
    unico que cambia despues es a donde va ese valor: al cajon o contra una
    prenda nueva.

    **Exige que la venta este bloqueada** (`bloquear_venta`) antes de llamarla:
    lee «lo ya devuelto» y decide contra eso, asi que sin el bloqueo dos
    operaciones simultaneas leen el mismo saldo y las dos se lo gastan.

    Devuelve `(lineas, vendidas)`: las lineas como tuplas
    `(variante_id, cantidad, precio_pagado, nombre)`, y el indice de lo vendido
    para que quien llama arme el comprobante sin volver a consultar.
    """
    vendidas = {f.variante_id: f for f in repository.lineas_vendidas(db, venta.id)}
    ya = repository.ya_devuelto(db, venta.id)

    ajenas = [l.variante_id for l in pedidas if l.variante_id not in vendidas]
    if ajenas:
        raise PrendaNoVendidaEnEsaVenta(ajenas)

    lineas: list[tuple[int, int, Decimal, str]] = []
    for pedida in pedidas:
        fila = vendidas[pedida.variante_id]
        devolvibles = fila.cantidad - ya.get(pedida.variante_id, 0)
        if pedida.cantidad > devolvibles:
            raise DevuelveDeMas(_nombre(fila), devolvibles, pedida.cantidad)
        lineas.append(
            (pedida.variante_id, pedida.cantidad, _unitario(fila), _nombre(fila))
        )
    return lineas, vendidas


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

    # El plazo se INFORMA aca y se EXIGE al registrar. Buscar una venta vencida
    # no es un error: el cajero necesita poder mirarla para explicarle al
    # cliente por que no se puede, y con que fecha.
    vence = _vence_en(venta)

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
        plazo_dias=settings.DEVOLUCION_PLAZO_DIAS,
        vence_en=vence,
        dentro_de_plazo=tiempo.ahora() <= vence,
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

    _exigir_plazo(venta)

    # Serializa las devoluciones de esta venta ANTES de leer lo ya devuelto: sin
    # el bloqueo, dos devoluciones simultaneas leen el mismo saldo y las dos
    # devuelven la ultima unidad.
    repository.bloquear_venta(db, venta.id)

    lineas, vendidas = _lineas_que_vuelven(db, venta, datos.lineas)

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


# =====================================================================
# El segundo flujo: cambiar una prenda por otra
# =====================================================================

def registrar_cambio(db: Session, usuario_id: int, datos: CambioIn) -> CambioOut:
    """Recibe una prenda y entrega otra en su lugar. **Hace commit.**

    TODO EN UNA SOLA TRANSACCION, y es el motivo por el que existe esta funcion
    en vez de dos llamadas desde la pantalla. Si se cayera en el medio, el
    cliente quedaria sin la prenda que trajo y sin la que se lleva.

    EL ORDEN NO ES CASUAL: PRIMERO ENTRA LO VIEJO, DESPUES SALE LO NUEVO
    ---------------------------------------------------------------------
    Es el orden del mostrador ---el cliente entrega y despues recibe--- y
    ademas es el unico que resuelve el caso mas comun de todos: cambiar una
    prenda fallada por **otra igual**. Si se descontara primero, la ultima
    unidad no estaria disponible todavia y el cambio se rechazaria por falta de
    stock de una prenda que el cliente tiene en la mano.
    """
    mostrador = mostrador_de(db, usuario_id)

    venta = repository.venta_devolvible(
        db, codigo=datos.venta_codigo, sucursal_id=mostrador.sucursal_id
    )
    if venta is None:
        raise VentaNoDevolvible(datos.venta_codigo)

    _exigir_plazo(venta)
    repository.bloquear_venta(db, venta.id)

    # --- Lo que vuelve, al precio que se pago ----------------------------
    vueltas, vendidas = _lineas_que_vuelven(db, venta, datos.devueltas)
    valor_devuelto = sum((precio * cantidad for _, cantidad, precio, _ in vueltas), CERO)

    # --- Lo que se lleva, al precio y las promociones de HOY --------------
    #
    # A precio de hoy y no al de la venta original: es una prenda distinta, que
    # nunca se vendio. Usar el precio viejo seria regalarle al cliente una
    # promocion que ya vencio, o cobrarsela si empezo ayer.
    pedidas = [(l.variante_id, l.cantidad) for l in datos.llevadas]
    prendas = pos_repository.prendas_por_id(
        db,
        variante_ids=[v for v, _ in pedidas],
        sucursal_id=mostrador.sucursal_id,
    )
    faltantes = [v for v, _ in pedidas if v not in prendas]
    if faltantes:
        raise PrendaNoVendible(faltantes)

    descuentos = promociones.descuentos_por_variante(
        db, {v: prendas[v].precio for v, _ in pedidas}
    )
    subtotal = sum((prendas[v].precio * c for v, c in pedidas), CERO)
    descuento = sum(
        (descuentos[v].monto_unitario * c for v, c in pedidas if v in descuentos),
        CERO,
    )
    total_llevado = subtotal - descuento

    # --- La diferencia, que es lo unico que mueve plata -------------------
    diferencia = total_llevado - valor_devuelto

    if (
        datos.diferencia_esperada is not None
        and datos.diferencia_esperada != diferencia
    ):
        raise DiferenciaCambiada(datos.diferencia_esperada, diferencia)

    # Las dos mitades de la misma regla, y las dos hacen falta: sin la primera
    # se escribiria una diferencia que nadie salda; sin la segunda, un metodo
    # de pago contra cero --- y el CHECK de la 0020 lo rechazaria con un error
    # de integridad, que para el cajero es un «error del sistema» sin causa.
    if diferencia != CERO and datos.metodo_diferencia is None:
        raise CambioSinMetodo(diferencia)
    if diferencia == CERO and datos.metodo_diferencia is not None:
        raise CambioSinNada()

    # --- La venta nueva: la prenda que sale SE VENDIO ---------------------
    codigo = generar_codigo_de_venta(db)
    venta_nueva = pos_repository.agregar_venta_presencial(
        db,
        codigo=codigo,
        # Hereda el cliente de la venta original: es la misma persona. En una
        # venta de mostrador anonima sigue siendo None, como corresponde.
        cliente_id=venta.cliente_id,
        sucursal_id=mostrador.sucursal_id,
        turno_caja_id=mostrador.turno_id,
        reserva_id=None,
        # No se cobro en billetes: la pago una prenda devuelta. Es lo que deja
        # a `efectivo_cobrado` de CU-30 ignorarla sin ninguna condicion nueva.
        metodo_pago=METODO_CAMBIO,
        subtotal=subtotal,
        descuento=descuento,
        total=total_llevado,
    )

    for variante_id, cantidad in pedidas:
        pos_repository.agregar_detalle(
            db,
            venta_id=venta_nueva.id,
            variante_id=variante_id,
            cantidad=cantidad,
            # CONGELADOS los dos, igual que en CU-31: manana este comprobante
            # tiene que seguir explicando por que la diferencia fue la que fue.
            precio_unitario=prendas[variante_id].precio,
            descuento_unitario=(
                descuentos[variante_id].monto_unitario
                if variante_id in descuentos
                else CERO
            ),
        )

    # --- La devolucion, que es lo que ata las dos puntas ------------------
    devolucion = repository.agregar_devolucion(
        db,
        venta_id=venta.id,
        turno_caja_id=mostrador.turno_id,
        motivo=datos.motivo,
        # CERO y no `valor_devuelto`: la prenda vieja no se paga, se acredita
        # contra la nueva. Si valiera algo, el arqueo la restaria ademas de la
        # diferencia y descontaria dos veces la misma plata.
        monto=CERO,
        tipo="CAMBIO",
        venta_cambio_id=venta_nueva.id,
        diferencia=diferencia,
        metodo_diferencia=datos.metodo_diferencia,
    )

    # 1) entra lo viejo
    for variante_id, cantidad, _precio, _n in vueltas:
        repository.agregar_detalle(
            db,
            devolucion_id=devolucion.id,
            variante_id=variante_id,
            cantidad=cantidad,
        )
        inventario.reingresar_por_devolucion(
            db,
            variante_id=variante_id,
            sucursal_id=mostrador.sucursal_id,
            cantidad=cantidad,
            usuario_id=usuario_id,
            motivo=f"Cambio de {venta.codigo} por {codigo}: {datos.motivo}"[:200],
        )

    # 2) sale lo nuevo
    for variante_id, cantidad in pedidas:
        try:
            inventario.descontar_por_venta(
                db,
                variante_id=variante_id,
                sucursal_id=mostrador.sucursal_id,
                cantidad=cantidad,
                usuario_id=usuario_id,
                motivo=f"Cambio de {venta.codigo}, sale en {codigo}",
            )
        except inventario.StockInsuficiente as e:
            # La transaccion entera se deshace: no queda la prenda vieja
            # reingresada contra un cambio que no ocurrio.
            raise SinStock(_nombre(prendas[variante_id]), e.disponible, cantidad) from e
        except inventario.ExistenciaInexistente as e:  # pragma: no cover
            raise PrendaNoVendible([variante_id]) from e

    # La prenda nueva sale con su papel, igual que en CU-31: el cliente se va
    # del mostrador con algo que dice que se la llevo legitimamente.
    comprobante = historial_service.asegurar_comprobante(db, venta_nueva)

    db.commit()
    db.refresh(devolucion)

    return CambioOut(
        id=devolucion.id,
        venta_codigo=venta.codigo,
        venta_nueva_codigo=codigo,
        comprobante_numero=comprobante.numero,
        caja_nombre=mostrador.caja_nombre,
        motivo=devolucion.motivo,
        creado_en=devolucion.creado_en,
        devueltas=[
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
            for variante_id, cantidad, precio, _n in vueltas
        ],
        valor_devuelto=valor_devuelto,
        llevadas=[
            LineaLlevadaOut(
                variante_id=variante_id,
                sku=prendas[variante_id].sku,
                producto=prendas[variante_id].producto,
                talla=prendas[variante_id].talla,
                color=prendas[variante_id].color,
                cantidad=cantidad,
                precio_unitario=prendas[variante_id].precio,
                descuento_unitario=(
                    descuentos[variante_id].monto_unitario
                    if variante_id in descuentos
                    else CERO
                ),
                subtotal=(
                    prendas[variante_id].precio
                    - (
                        descuentos[variante_id].monto_unitario
                        if variante_id in descuentos
                        else CERO
                    )
                )
                * cantidad,
            )
            for variante_id, cantidad in pedidas
        ],
        total_llevado=total_llevado,
        diferencia=diferencia,
        a_favor_de=_a_favor_de(diferencia),
        metodo_diferencia=devolucion.metodo_diferencia,
        toca_el_cajon=datos.metodo_diferencia == METODO_EFECTIVO,
    )


def _a_favor_de(diferencia: Decimal) -> str:
    """Quien pone la plata. Se resuelve aca y no en la pantalla.

    El signo de un numero es facil de leer al reves cuando hay que decidir
    entre «cobrar» y «entregar» con el cliente esperando. Un texto explicito
    no se puede confundir.
    """
    if diferencia > CERO:
        return "CLIENTE"
    if diferencia < CERO:
        return "TIENDA"
    return "NADIE"


__all__ = [
    "CambioSinMetodo",
    "CambioSinNada",
    "DiferenciaCambiada",
    "DevuelveDeMas",
    "FueraDePlazo",
    "PrendaNoVendidaEnEsaVenta",
    "VentaNoDevolvible",
    "buscar_venta",
    "registrar",
    "registrar_cambio",
]
