"""
P7 - Punto de Venta / CU-31  |  capa: servicio (reglas de negocio)

Registrar venta presencial. Dos caminos de entrada, un solo resultado.

LOS DOS CAMINOS NO DESCUENTAN LO MISMO, Y ESE ES EL PUNTO DEL CASO DE USO
-------------------------------------------------------------------------
**Camino A --- el cajero busca las prendas.** Las unidades estan en el
disponible y nadie las aparto. Se escribe UN movimiento: `VENTA -n`.

**Camino B --- se cobra una reserva ya atendida.** Las unidades **ya salieron
del inventario**. CU-24, al cerrar la reserva, escribio `LIBERACION +n` y
`VENTA -n` por cada prenda con resultado `LLEVA`: el cliente se la llevo puesta
del probador, y el inventario tenia que decir la verdad en ese momento aunque
el cobro todavia no existiera. Su propio docstring lo deja escrito:

    «Cuando P7 exista, CU-24 y el cobro pasan a ser una sola transaccion y el
    movimiento de VENTA lo va a escribir la venta, no este caso de uso; hasta
    entonces lo escribe aca, con el motivo que lo explica.»

P7 ya existe, pero **CU-24 es de Mateo y sigue escribiendo ese movimiento**. La
respuesta correcta hoy no es reescribirle su caso de uso a un dia de la entrega
---seria cambiar una regla ajena, romper sus pruebas y arriesgar el invariante
de P4 justo donde mas duele---, sino **respetar lo que ya hizo y no descontar
de nuevo**. Un segundo `VENTA -n` sobre las mismas unidades dejaria el
disponible en negativo o, peor, lo dejaria mintiendo sin que nada reventara.

Queda anotado como deuda con nombre y responsable: cuando CU-24 deje de
descontar, el camino B tiene que empezar a hacerlo. Hasta entonces, la linea
`if venta.reserva_id is None` de `_descontar` es lo unico que separa las dos
historias, y la prueba `test_cobrar_una_reserva_no_vuelve_a_descontar` es lo
que impide que alguien la borre por parecer de mas.

SIN TURNO ABIERTO NO SE COBRA
------------------------------
No es una decision de este modulo: el CHECK `ck_venta_turno_segun_canal` exige
`turno_caja_id` en toda venta PRESENCIAL. Lo que hace este servicio es decirlo
con palabras --- «abra su caja primero» --- en vez de dejar que la base lo
rechace con un error de integridad que el cajero leeria como una falla.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.caja import repository as caja_repository
from app.modules.catalogo import promociones_service as promociones
from app.modules.inventario import service as inventario
from app.modules.pos import repository
from app.modules.pos.schemas import (
    LineaDeReservaOut,
    LineaVendidaOut,
    PrendaEnMostradorOut,
    ReservaPorCobrarOut,
    VentaPresencialIn,
    VentaPresencialOut,
)
from app.modules.ventas import historial_service, repository as ventas_repository
from app.modules.ventas import service as ventas_service
from app.modules.ventas.models import Venta

#: Solo el efectivo genera vuelto. Con tarjeta o QR se cobra el importe exacto:
#: ofrecer vuelto ahi seria sacar plata del cajon por un cobro que no entro.
METODO_EFECTIVO = "EFECTIVO"

CERO = Decimal("0.00")


# =====================================================================
# Errores que el cajero puede entender y corregir
# =====================================================================

class ErrorDeMostrador(Exception):
    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


class SinTurnoAbierto(ErrorDeMostrador):
    def __init__(self) -> None:
        super().__init__(
            "No tiene ninguna caja abierta. Abra su turno antes de cobrar.", 409
        )


class PrendaNoVendible(ErrorDeMostrador):
    """La prenda no existe, o no tiene saldo en esta sucursal."""

    def __init__(self, variante_ids: list[int]) -> None:
        self.variante_ids = variante_ids
        super().__init__(
            "Alguna de las prendas no está disponible en su sucursal.", 404
        )


class SinStock(ErrorDeMostrador):
    def __init__(self, prenda: str, disponible: int, solicitado: int) -> None:
        self.prenda = prenda
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(
            f"De «{prenda}» quedan {disponible} y se pidieron {solicitado}.", 409
        )


class ConflictoDePrecio(ErrorDeMostrador):
    """El precio cambio entre que la pantalla lo mostro y el cajero confirmo.

    Es 409 y no un cobro silencioso: entregar un ticket por un importe distinto
    del que se le dijo al cliente es exactamente lo que no puede pasar en un
    mostrador.
    """

    def __init__(self, esperado: Decimal, actual: Decimal) -> None:
        self.esperado = esperado
        self.actual = actual
        super().__init__(
            f"El total cambió: la pantalla decía Bs {esperado} y ahora es Bs {actual}. "
            "Revise el detalle antes de cobrar.",
            409,
        )


class PagoInsuficiente(ErrorDeMostrador):
    def __init__(self, recibido: Decimal, total: Decimal) -> None:
        super().__init__(
            f"Recibió Bs {recibido} y el total es Bs {total}.", 422
        )


class ReservaNoCobrable(ErrorDeMostrador):
    """No existe esa reserva atendida y sin cobrar en esta sucursal.

    Un solo mensaje para «no existe», «es de otra sucursal», «todavia no se
    atendio» y «ya se cobro»: convencion 1 del ciclo --- lo que no es suyo no
    existe ---. Distinguirlos le confirmaria al cajero que hay una reserva en
    otra sucursal que no puede ver.
    """

    def __init__(self, reserva_id: int) -> None:
        super().__init__(
            f"No hay ninguna reserva atendida y sin cobrar con el número {reserva_id} "
            "en su sucursal.",
            404,
        )


class VentaInexistente(ErrorDeMostrador):
    def __init__(self, codigo: str) -> None:
        super().__init__(f"No existe la venta {codigo} en su sucursal.", 404)


# =====================================================================
# El turno: la puerta de entrada de todo el modulo
# =====================================================================

class Mostrador:
    """Donde y en que caja esta cobrando esta persona.

    Se arma UNA vez por peticion y de ahi salen `sucursal_id` y `turno_id`.
    Ninguno de los dos se acepta del cliente --- convencion 2 ---: si vinieran
    en el cuerpo, un cajero de Centro podria imputar una venta a la caja de
    Norte y el arqueo de esa otra caja cerraria con un sobrante inexplicable.
    """

    __slots__ = ("turno_id", "caja_id", "caja_nombre", "sucursal_id")

    def __init__(self, *, turno_id: int, caja_id: int, caja_nombre: str, sucursal_id: int):
        self.turno_id = turno_id
        self.caja_id = caja_id
        self.caja_nombre = caja_nombre
        self.sucursal_id = sucursal_id


def mostrador_de(db: Session, usuario_id: int) -> Mostrador:
    """El turno abierto de quien cobra, o `SinTurnoAbierto`.

    Se apoya en el repositorio de CU-30 y no en su servicio: `mi_turno` arma el
    arqueo entero ---tres consultas de agregacion--- y para cobrar solo hace
    falta saber en que caja se esta. La regla «un turno abierto por caja» sigue
    siendo de CU-30; aca solo se lee su resultado.
    """
    turno = caja_repository.turno_abierto_de_usuario(db, usuario_id)
    if turno is None:
        raise SinTurnoAbierto()
    caja = caja_repository.caja_por_id(db, turno.caja_id)
    if caja is None:  # pragma: no cover - la FK lo impide
        raise SinTurnoAbierto()
    return Mostrador(
        turno_id=turno.id,
        caja_id=caja.id,
        caja_nombre=caja.nombre,
        sucursal_id=caja.sucursal_id,
    )


# =====================================================================
# Paso 1: que hay para vender
# =====================================================================

def buscar_prendas(
    db: Session,
    usuario_id: int,
    *,
    busqueda: str | None,
    pagina: int,
    tamano: int,
) -> tuple[int, list[PrendaEnMostradorOut]]:
    mostrador = mostrador_de(db, usuario_id)
    total, filas = repository.prendas_vendibles(
        db,
        sucursal_id=mostrador.sucursal_id,
        busqueda=busqueda,
        pagina=pagina,
        tamano=tamano,
    )
    # CU-12. Una consulta para toda la pagina, no una por prenda.
    descuentos = promociones.descuentos_por_variante(
        db, {f.variante_id: f.precio for f in filas}
    )
    return total, [
        PrendaEnMostradorOut(
            variante_id=fila.variante_id,
            sku=fila.sku,
            producto=fila.producto,
            talla=fila.talla,
            color=fila.color,
            precio=fila.precio,
            descuento=promociones.a_contrato(descuentos.get(fila.variante_id)),
            disponible=fila.disponible,
        )
        for fila in filas
    ]


# =====================================================================
# Paso 1-bis: el puente de D2, las reservas atendidas sin cobrar
# =====================================================================

def _lineas_de_reserva(db: Session, reserva_id: int):
    filas = repository.lineas_llevadas(db, reserva_id=reserva_id)
    descuentos = promociones.descuentos_por_variante(
        db, {f.variante_id: f.precio for f in filas}
    )
    lineas = []
    for fila in filas:
        d = descuentos.get(fila.variante_id)
        unitario = d.precio_final if d else fila.precio
        lineas.append(
            LineaDeReservaOut(
                variante_id=fila.variante_id,
                sku=fila.sku,
                producto=fila.producto,
                talla=fila.talla,
                color=fila.color,
                cantidad=fila.cantidad,
                precio=fila.precio,
                descuento=promociones.a_contrato(d),
                subtotal=unitario * fila.cantidad,
            )
        )
    return lineas, sum((l.subtotal for l in lineas), CERO)


def reservas_por_cobrar(db: Session, usuario_id: int) -> list[ReservaPorCobrarOut]:
    """Las reservas que el Encargado ya atendio y que nadie cobro todavia."""
    mostrador = mostrador_de(db, usuario_id)
    salida: list[ReservaPorCobrarOut] = []
    for fila in repository.reservas_por_cobrar(db, sucursal_id=mostrador.sucursal_id):
        lineas, total = _lineas_de_reserva(db, fila.reserva_id)
        salida.append(
            ReservaPorCobrarOut(
                reserva_id=fila.reserva_id,
                cliente=f"{fila.nombres} {fila.apellidos}".strip(),
                atendida_en=fila.atendida_en,
                lineas=lineas,
                total=total,
            )
        )
    return salida


def ver_reserva(db: Session, usuario_id: int, reserva_id: int) -> ReservaPorCobrarOut:
    mostrador = mostrador_de(db, usuario_id)
    fila = repository.reserva_cobrable(
        db, reserva_id=reserva_id, sucursal_id=mostrador.sucursal_id
    )
    if fila is None:
        raise ReservaNoCobrable(reserva_id)
    lineas, total = _lineas_de_reserva(db, reserva_id)
    return ReservaPorCobrarOut(
        reserva_id=fila.reserva_id,
        cliente=f"{fila.nombres} {fila.apellidos}".strip(),
        atendida_en=fila.atendida_en,
        lineas=lineas,
        total=total,
    )


# =====================================================================
# Paso 2: cobrar
# =====================================================================

def _generar_codigo(db: Session) -> str:
    """Un codigo legible y unico, de la forma `VP-20260920-A3F2`.

    `VP` y no `VB`: las ventas de mostrador y los pedidos web comparten la misma
    columna unica, y el prefijo distinto deja saber de un vistazo ---en el
    arqueo, en el tablero, cuando alguien lee un numero por telefono--- de cual
    de los dos canales vino cada una, sin tener que ir a mirar la fila.
    """
    hoy = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(10):
        codigo = f"VP-{hoy}-{secrets.token_hex(2).upper()}"
        if not repository.existe_codigo(db, codigo):
            return codigo
    raise ErrorDeMostrador(  # pragma: no cover - 10 choques seguidos de 65.536
        "No se pudo generar el número de la venta. Intente otra vez.", 500
    )


def _lineas_del_ticket(db: Session, datos: VentaPresencialIn, mostrador: Mostrador):
    """Que se vende y a que precio, venga de donde venga.

    Los dos caminos terminan en la misma lista de tuplas
    `(variante_id, cantidad, precio, nombre_legible)`. Todo lo que viene
    despues --- el total, la venta, los detalles, el comprobante --- es igual
    para los dos, y por eso se unifica aca y no mas abajo.
    """
    if datos.reserva_id is not None:
        fila = repository.reserva_cobrable(
            db, reserva_id=datos.reserva_id, sucursal_id=mostrador.sucursal_id
        )
        if fila is None:
            raise ReservaNoCobrable(datos.reserva_id)
        crudas = repository.lineas_llevadas(db, reserva_id=datos.reserva_id)
        if not crudas:  # pragma: no cover - el EXISTS de la consulta ya lo filtra
            raise ReservaNoCobrable(datos.reserva_id)
        lineas = [
            (c.variante_id, c.cantidad, c.precio, _nombre(c)) for c in crudas
        ]
        return lineas, fila.cliente_id

    pedidas = [(l.variante_id, l.cantidad) for l in datos.lineas]
    prendas = repository.prendas_por_id(
        db,
        variante_ids=[v for v, _ in pedidas],
        sucursal_id=mostrador.sucursal_id,
    )
    faltantes = [v for v, _ in pedidas if v not in prendas]
    if faltantes:
        raise PrendaNoVendible(faltantes)

    lineas = [
        (v, cantidad, prendas[v].precio, _nombre(prendas[v]))
        for v, cantidad in pedidas
    ]
    # Una venta de mostrador es anonima: quien entra, paga y se va no tiene por
    # que dejar sus datos. El cliente solo aparece cuando la venta viene de una
    # reserva, que es de alguien con nombre.
    return lineas, None


def _nombre(fila) -> str:
    return " · ".join(p for p in (fila.producto, fila.talla, fila.color) if p)


def _descontar(
    db: Session,
    *,
    lineas,
    mostrador: Mostrador,
    usuario_id: int,
    codigo: str,
    desde_reserva: bool,
) -> None:
    """Saca del inventario lo que se vendio. **Sin commit.**

    NO HACE NADA SI LA VENTA VIENE DE UNA RESERVA. Ver el encabezado del
    modulo: CU-24 ya escribio `LIBERACION +n` y `VENTA -n` al cerrar la reserva,
    y un segundo descuento contaria las mismas unidades dos veces.
    """
    if desde_reserva:
        return

    for variante_id, cantidad, _precio, nombre in lineas:
        try:
            inventario.descontar_por_venta(
                db,
                variante_id=variante_id,
                sucursal_id=mostrador.sucursal_id,
                cantidad=cantidad,
                usuario_id=usuario_id,
                motivo=f"Venta {codigo} en mostrador",
            )
        except inventario.StockInsuficiente as e:
            # El bloqueo de fila esta dentro de la costura: si dos cajeros
            # venden la ultima prenda a la vez, uno gana y el otro llega aca.
            # La transaccion entera se deshace, asi que no queda ni venta ni
            # medio ticket.
            raise SinStock(nombre, e.disponible, cantidad) from e
        except inventario.ExistenciaInexistente as e:  # pragma: no cover
            raise PrendaNoVendible([variante_id]) from e


def registrar_venta(
    db: Session, usuario_id: int, datos: VentaPresencialIn
) -> VentaPresencialOut:
    """Cobra en el mostrador. **Hace commit.**

    La venta **nace PAGADA**: el dinero se recibe en el acto y no hay pasarela
    que confirme nada. Es lo contrario de CU-27, donde nace PENDIENTE_PAGO y
    solo el webhook firmado de CU-28 la mueve (decision D5).

    Todo pasa en una sola transaccion: la venta, sus lineas, el descuento de
    inventario y el comprobante. Si algo falla, no queda nada a medias --- ni
    una venta sin comprobante ni un inventario descontado sin venta ---.
    """
    mostrador = mostrador_de(db, usuario_id)
    lineas, cliente_id = _lineas_del_ticket(db, datos, mostrador)

    # CU-12. Las promociones vigentes se leen al cobrar, no antes: una que
    # vencio anoche no se honra hoy, y una que empieza hoy alcanza a la reserva
    # que se atendio ayer. Una sola consulta para todo el ticket.
    descuentos = promociones.descuentos_por_variante(
        db, {variante_id: precio for variante_id, _, precio, _ in lineas}
    )

    subtotal = sum((precio * cantidad for _, cantidad, precio, _ in lineas), CERO)
    # El subtotal va a precio de LISTA y el descuento aparte: lo exige el CHECK
    # `total = subtotal - descuento`, y ademas es lo que deja que el ticket
    # muestre de cuanto era y cuanto se pago.
    descuento = sum(
        (
            descuentos[variante_id].monto_unitario * cantidad
            for variante_id, cantidad, _precio, _ in lineas
            if variante_id in descuentos
        ),
        CERO,
    )
    total = subtotal - descuento

    if datos.total_esperado is not None and datos.total_esperado != total:
        raise ConflictoDePrecio(datos.total_esperado, total)

    # Con tarjeta o QR se cobra el importe exacto: no hay vuelto que dar, y un
    # «recibido» en el ticket solo confundiria. Se descarta en vez de
    # arrastrarlo hasta la pantalla.
    recibido = datos.monto_recibido if datos.metodo_pago == METODO_EFECTIVO else None
    vuelto: Decimal | None = None
    if recibido is not None:
        if recibido < total:
            raise PagoInsuficiente(recibido, total)
        vuelto = recibido - total

    codigo = _generar_codigo(db)

    venta = repository.agregar_venta_presencial(
        db,
        codigo=codigo,
        cliente_id=cliente_id,
        sucursal_id=mostrador.sucursal_id,
        turno_caja_id=mostrador.turno_id,
        reserva_id=datos.reserva_id,
        metodo_pago=datos.metodo_pago,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
    )

    for variante_id, cantidad, precio, _nombre_legible in lineas:
        repository.agregar_detalle(
            db,
            venta_id=venta.id,
            variante_id=variante_id,
            # CONGELADO. Desde aca el precio de esta linea ya no cambia nunca,
            # aunque la tienda toque el precio de la variante manana.
            precio_unitario=precio,
            # CONGELADO junto con el precio: si manana la promocion se apaga,
            # este ticket sigue explicando por que se cobro lo que se cobro.
            descuento_unitario=(
                descuentos[variante_id].monto_unitario
                if variante_id in descuentos
                else CERO
            ),
            cantidad=cantidad,
        )

    _descontar(
        db,
        lineas=lineas,
        mostrador=mostrador,
        usuario_id=usuario_id,
        codigo=codigo,
        desde_reserva=datos.reserva_id is not None,
    )

    # El comprobante sale con la venta y no cuando alguien lo pide: el cliente
    # se va del mostrador con el papel. Es la costura de CU-29, idempotente por
    # el UNIQUE sobre `venta_id`.
    comprobante = historial_service.asegurar_comprobante(db, venta)

    db.commit()
    db.refresh(venta)

    return _armar_ticket(
        db,
        venta=venta,
        mostrador=mostrador,
        comprobante_numero=comprobante.numero,
        monto_recibido=recibido,
        vuelto=vuelto,
    )


def _armar_ticket(
    db: Session,
    *,
    venta: Venta,
    mostrador: Mostrador,
    comprobante_numero: str,
    monto_recibido: Decimal | None = None,
    vuelto: Decimal | None = None,
) -> VentaPresencialOut:
    """El ticket que se devuelve y que la pantalla imprime.

    Las lineas se releen de `detalle_venta` y no se reusan las que entraron:
    lo que vale es lo que quedo guardado. Si alguna vez la escritura y la
    respuesta dejaran de coincidir, esto lo muestra en vez de esconderlo.
    """
    crudas = ventas_repository.lineas_de_pedido(db, venta.id)
    return VentaPresencialOut(
        codigo=venta.codigo,
        estado=venta.estado,
        metodo_pago=venta.metodo_pago or "—",
        sucursal_nombre=repository.nombre_de_sucursal(db, venta.sucursal_id),
        caja_nombre=mostrador.caja_nombre,
        cliente=repository.cliente_de_venta(db, venta.cliente_id),
        reserva_id=venta.reserva_id,
        lineas=[
            LineaVendidaOut(
                variante_id=fila.variante_id,
                sku=fila.sku,
                producto=fila.producto_nombre,
                talla=fila.talla_codigo or "—",
                color=fila.color_nombre or "—",
                cantidad=fila.cantidad,
                precio_unitario=fila.precio_unitario,
                subtotal=(fila.precio_unitario - fila.descuento_unitario)
                * fila.cantidad,
            )
            for fila in crudas
        ],
        subtotal=venta.subtotal,
        descuento=venta.descuento,
        total=venta.total,
        monto_recibido=monto_recibido,
        vuelto=vuelto,
        comprobante_numero=comprobante_numero,
        creado_en=venta.creado_en,
    )


# =====================================================================
# Paso 3: releer e imprimir
# =====================================================================

def ver_venta(db: Session, usuario_id: int, codigo: str) -> VentaPresencialOut:
    """Relee una venta del mostrador, para reimprimir el ticket.

    Se acota a la sucursal y no al turno: si el cliente vuelve al otro dia por
    su ticket, el cajero del turno siguiente tiene que poder dárselo.
    """
    mostrador = mostrador_de(db, usuario_id)
    venta = repository.venta_de_sucursal(
        db, codigo=codigo, sucursal_id=mostrador.sucursal_id
    )
    if venta is None:
        raise VentaInexistente(codigo)
    comprobante = historial_service.asegurar_comprobante(db, venta)
    db.commit()
    return _armar_ticket(
        db, venta=venta, mostrador=mostrador, comprobante_numero=comprobante.numero
    )


def comprobante_en_pdf(db: Session, usuario_id: int, codigo: str) -> tuple[str, bytes]:
    """El comprobante de una venta del mostrador, como PDF. **Hace commit.**

    Reusa el dibujo de CU-29 en vez de tener uno propio: dos funciones que
    dibujan el mismo recibo terminan divergiendo, y el dia que diverjan el
    cliente que compro por la web y el que compro en la tienda van a recibir
    papeles distintos de la misma tienda.
    """
    mostrador = mostrador_de(db, usuario_id)
    venta = repository.venta_de_sucursal(
        db, codigo=codigo, sucursal_id=mostrador.sucursal_id
    )
    if venta is None:
        raise VentaInexistente(codigo)

    comprobante = historial_service.asegurar_comprobante(db, venta)
    db.commit()

    fila = ventas_repository.obtener_pedido(db, codigo=codigo)
    pedido = ventas_service._armar_pedido(db, fila)
    cuerpo = historial_service._dibujar_pdf(comprobante, pedido)
    return f"{comprobante.numero}.pdf", cuerpo
