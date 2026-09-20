"""
P7 - Ventas y Punto de Venta  |  capa: servicio (reglas de negocio)

Ciclo de desarrollo: 3
Caso de uso: CU-27 Realizar pedido y pagar en linea  (RF15, RF16, RF19)

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

LAS CUATRO DECISIONES DE ESTE CASO DE USO
==========================================

1. EL PEDIDO APARTA STOCK; NO ESPERA AL PAGO
---------------------------------------------
Al confirmar, las unidades pasan de `cantidad_disponible` a
`cantidad_reservada` con un movimiento de tipo RESERVA, exactamente como hace
CU-22. La seccion 6.7 dice que el webhook «descuenta el inventario», y eso
sigue siendo cierto: CU-28 escribira LIBERACION + VENTA, que es la convencion
que ya fijo `inventario/service.py` para las unidades que venian apartadas.

La alternativa ---no apartar y validar recien en el webhook--- deja que dos
clientes paguen la ultima unidad. Devolverle la plata a uno de los dos es
muchisimo peor que decirle al segundo, ANTES de cobrarle, que ya no queda.

El precio de apartar es que un pedido que nadie paga inmoviliza mercaderia. Por
eso existe `expirar_pedidos_vencidos`, que es a este caso de uso lo que CU-25 a
las reservas.

2. UN PEDIDO SE DESPACHA DESDE UNA SOLA SUCURSAL
-------------------------------------------------
`detalle_venta` no tiene `sucursal_id`: la sucursal es de la venta entera. Asi
que una sucursal tiene que poder abastecer TODAS las lineas, y si ninguna
puede, el pedido no se puede hacer aunque entre todas sobre stock.

Es una limitacion consciente y no un descuido. Partir un pedido entre
sucursales obliga a una sucursal por linea, a dos despachos, a dos entregas y a
decidir que pasa si una mitad se cancela. Eso es un caso de uso propio, no una
linea mas en este.

Para que el cliente no choque con esto al confirmar, `opciones_de_pedido` le
dice de antemano que sucursales pueden y, cuando no pueden, que les falta.

3. EL PRECIO SE CONGELA ACA, Y SI CAMBIO SE AVISA
--------------------------------------------------
El carrito lee precios en vivo (decision de CU-26). Entre que el cliente mira
el carrito y confirma, la tienda pudo cambiar un precio. El cliente manda el
total que VIO; si no coincide, esto devuelve 409 con el total nuevo y el
carrito entero, y no cobra nada.

Es el corolario que quedo anotado al decidir, el 17/09, que el precio se
congela en la venta y no en el carrito.

4. EL CARRITO NO SE VACIA ACA
------------------------------
Lo vacia CU-28 cuando el pago se confirma. Si se vaciara al confirmar el
pedido, un pago que falla o que el cliente abandona lo dejaria sin carrito y
teniendo que rearmarlo prenda por prenda.

Lo que impide que confirme cinco veces y aparte cinco veces el stock no es
vaciar el carrito, es la regla de UN SOLO pedido pendiente por cliente.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.pasarela_pago import LineaDePago
from app.modules.catalogo import imagenes_almacen as almacen
from app.modules.catalogo import promociones_service as promociones
from app.modules.catalogo_publico import service as catalogo_publico
from app.modules.inventario import service as inventario
from app.modules.pagos import service as pagos
from app.modules.ventas import carrito_repository, carrito_service, repository
from app.modules.ventas.schemas import (
    ConflictoDePrecioOut,
    CrearPedidoIn,
    CrearPedidoOut,
    DireccionParaEnvioOut,
    ExpiracionDePedidosOut,
    LineaPedidoOut,
    MODALIDAD_ENVIO,
    MODALIDAD_RETIRO,
    OpcionesDePedidoOut,
    PedidoOut,
    SucursalParaRetiroOut,
)

_log = logging.getLogger("violetboutique.ventas")

CANAL_DIGITAL = "DIGITAL"
ESTADO_PENDIENTE = "PENDIENTE_PAGO"
ESTADO_CANCELADA = "CANCELADA"

#: Cuantos pedidos revisa como mucho una corrida de la barrida. Mismo motivo
#: que el tope de CU-25: que la primera corrida sobre una base con historial no
#: abra una transaccion enorme.
TOPE_EXPIRACION = 200


# --- Errores de negocio --------------------------------------------------

class ErrorDelPedido(Exception):
    """Base de los errores previstos de CU-27."""


class CarritoVacio(ErrorDelPedido):
    """No hay nada que pedir."""


class CarritoConPrendasCaidas(ErrorDelPedido):
    """Alguna linea dejo de ofrecerse. No se pide un carrito a medias.

    Se podria pedir solo lo disponible, y es peor: el cliente confirmaria un
    total y recibiria otro pedido. Que las saque el, que es quien decide si
    todavia quiere el resto.
    """


class PrecioCambiado(ErrorDelPedido):
    """El total cambio entre mirar el carrito y confirmar. Ver la decision 3."""

    def __init__(self, esperado: Decimal, actual: Decimal):
        self.esperado = esperado
        self.actual = actual


class YaTienePedidoPendiente(ErrorDelPedido):
    """Ya hay un pedido esperando pago. Ver la decision 4."""

    def __init__(self, codigo: str):
        self.codigo = codigo


class SucursalNoAbastece(ErrorDelPedido):
    """La sucursal elegida no tiene todas las prendas. Ver la decision 2."""

    def __init__(self, faltantes: list[str]):
        self.faltantes = faltantes


class NingunaSucursalAbastece(ErrorDelPedido):
    """Ninguna sucursal sola puede con el pedido entero. Ver la decision 2."""


class DestinoInvalido(ErrorDelPedido):
    """La sucursal o la direccion no existen, o no son de este cliente."""


class PedidoInexistente(ErrorDelPedido):
    """No hay pedido con ese codigo, o no es de este cliente."""


class PedidoNoCancelable(ErrorDelPedido):
    """Solo se cancela un pedido que todavia espera pago."""

    def __init__(self, estado: str):
        self.estado = estado


# --- Apoyo ----------------------------------------------------------------

def _cliente(db: Session, usuario_id: int) -> int:
    """El cliente del token, por la misma costura con P1 que usa CU-26."""
    return catalogo_publico._cliente(db, usuario_id)


def _generar_codigo(db: Session) -> str:
    """Un codigo legible y unico, de la forma `VB-20260917-A3F2`.

    Legible porque es lo que el cliente lee por telefono cuando llama a
    preguntar por su pedido; el `id` no sirve para eso.

    NO es correlativo a proposito. Un `VB-000123` le dice a cualquiera cuantas
    ventas lleva el negocio, y ademas obligaria a un contador que se vuelve un
    punto de contencion entre transacciones. La parte aleatoria tiene 16 bits,
    asi que dentro de un mismo dia hay colisiones posibles: por eso se
    comprueba y se reintenta. Con `UNIQUE` en la columna, una colision que se
    escapara seria un error, no un cobro cruzado.
    """
    hoy = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(10):
        codigo = f"VB-{hoy}-{secrets.token_hex(2).upper()}"
        if not repository.existe_codigo(db, codigo):
            return codigo
    # Diez colisiones seguidas no es mala suerte, es un defecto. Se frena.
    raise RuntimeError("No se pudo generar un código de venta único.")


def _vence_en(creado_en: datetime) -> datetime:
    return creado_en + timedelta(minutes=settings.PEDIDO_VIGENCIA_MINUTOS)


def _cobertura(db: Session, lineas) -> tuple[dict[int, list[str]], list]:
    """Que le falta a cada sucursal para abastecer el carrito entero.

    Devuelve `({sucursal_id: [nombres que le faltan]}, [filas que pueden])`.

    Las que pueden vuelven como FILAS y no como identificadores porque quien
    elige necesita ademas su `ciudad_id`: ver `_elegir_sucursal_de_envio`.

    Se calcula en memoria sobre UNA consulta de stock, no con una consulta por
    sucursal.
    """
    necesario = {linea.variante_id: linea.cantidad for linea in lineas}
    nombre_de = {
        linea.variante_id: f"{linea.producto_nombre} ({linea.sku})" for linea in lineas
    }
    stock = repository.stock_por_sucursal(db, list(necesario))

    faltantes: dict[int, list[str]] = {}
    completas: list = []
    for fila in repository.listar_sucursales_activas(db):
        de_esta = stock.get(fila.id, {})
        le_faltan = [
            nombre_de[v]
            for v, cantidad in necesario.items()
            if de_esta.get(v, 0) < cantidad
        ]
        faltantes[fila.id] = le_faltan
        if not le_faltan:
            completas.append(fila)
    return faltantes, completas


def _elegir_sucursal_de_envio(completas: list, ciudad_destino: int) -> int:
    """De que sucursal sale un envio. Ver la decision 2.

    **Primero, una de la ciudad del destino.** No es un lujo: con el orden
    alfabetico a secas, un cliente de Santa Cruz recibia su pedido desde
    Cochabamba si esa sucursal podia abastecerlo --- las sucursales se listan
    por ciudad y nombre, y Cochabamba va antes que La Paz y que Santa Cruz.
    Nadie lo habria notado hasta ver un envio cruzando el pais.

    Si ninguna de la ciudad puede con el pedido entero, se toma la primera que
    pueda. Sigue siendo mejor mandarlo de lejos que no venderlo, y la lista
    viene ordenada, asi que la eleccion es estable y reproducible --- no depende
    del orden en que PostgreSQL devuelva las filas.

    Elegir «la mas cercana» de verdad exigiria geolocalizar la direccion, que es
    otro caso de uso. Esto es lo que se puede hacer con los datos que hay.
    """
    del_destino = [f for f in completas if f.ciudad_id == ciudad_destino]
    return (del_destino or completas)[0].id


def _linea_pedido(fila, imagenes: dict[int, str]) -> LineaPedidoOut:
    unitario = fila.precio_unitario - fila.descuento_unitario
    ruta = imagenes.get(fila.producto_id)
    return LineaPedidoOut(
        variante_id=fila.variante_id,
        sku=fila.sku,
        producto_nombre=fila.producto_nombre,
        talla_codigo=fila.talla_codigo,
        color_nombre=fila.color_nombre,
        imagen_url=almacen.url_de(ruta) if ruta else None,
        cantidad=fila.cantidad,
        precio_unitario=fila.precio_unitario,
        descuento_unitario=fila.descuento_unitario,
        subtotal=unitario * fila.cantidad,
    )


def _armar_pedido(db: Session, fila) -> PedidoOut:
    """La ficha del pedido a partir de la fila de la venta."""
    lineas = repository.lineas_de_pedido(db, fila.id)
    imagenes = carrito_repository.imagen_principal(
        db, [linea.producto_id for linea in lineas]
    )

    direccion = None
    if fila.direccion_id is not None:
        # No se acota al cliente: ya se acoto la venta, y esta direccion es la
        # que la venta guardo.
        encontrada = repository.direccion_de_venta(db, fila.direccion_id)
        if encontrada:
            direccion = f"{encontrada.direccion} — {encontrada.ciudad}"

    return PedidoOut(
        codigo=fila.codigo,
        estado=fila.estado,
        canal=fila.canal,
        modalidad_entrega=fila.modalidad_entrega,
        sucursal_id=fila.sucursal_id,
        sucursal_nombre=fila.sucursal_nombre,
        direccion_envio=direccion,
        lineas=[_linea_pedido(l, imagenes) for l in lineas],
        subtotal=fila.subtotal,
        descuento=fila.descuento,
        total=fila.total,
        creado_en=fila.creado_en,
        pagar_antes_de=(
            _vence_en(fila.creado_en) if fila.estado == ESTADO_PENDIENTE else None
        ),
        estado_pago=fila.estado_pago,
    )


# --- Paso 1: que puede elegir ---------------------------------------------

def opciones_de_pedido(db: Session, usuario_id: int) -> OpcionesDePedidoOut:
    """Paso 1: el carrito, las sucursales que pueden y las direcciones.

    Todo en una peticion. Ver el esquema.
    """
    cliente_id = _cliente(db, usuario_id)
    carrito = carrito_repository.obtener_carrito(db, cliente_id)
    resumen = carrito_service._armar_carrito(db, carrito.id if carrito else None)

    direcciones = [
        DireccionParaEnvioOut(
            id=d.id,
            alias=d.alias,
            direccion=d.direccion,
            ciudad=d.ciudad,
            referencia=d.referencia,
            predeterminada=d.predeterminada,
        )
        for d in repository.listar_direcciones(db, cliente_id)
    ]

    # El carrito vacio o con prendas caidas ni siquiera necesita mirar stock.
    if not resumen.lineas:
        return OpcionesDePedidoOut(
            lineas=[], total=Decimal("0.00"), unidades=0,
            se_puede_pedir=False,
            motivo="Su carrito está vacío.",
            sucursales=[], direcciones=direcciones,
            pago_real=pagos.cobra_de_verdad(),
            minutos_para_pagar=settings.PEDIDO_VIGENCIA_MINUTOS,
        )

    if resumen.no_disponibles:
        return OpcionesDePedidoOut(
            lineas=resumen.lineas, total=resumen.total, unidades=resumen.unidades,
            se_puede_pedir=False,
            motivo=(
                "Hay prendas en su carrito que ya no se ofrecen. "
                "Quítelas para continuar."
            ),
            sucursales=[], direcciones=direcciones,
            pago_real=pagos.cobra_de_verdad(),
            minutos_para_pagar=settings.PEDIDO_VIGENCIA_MINUTOS,
        )

    lineas_crudas = carrito_repository.lineas_resueltas(db, carrito.id)
    faltantes, completas = _cobertura(db, lineas_crudas)

    sucursales = [
        SucursalParaRetiroOut(
            id=fila.id,
            nombre=fila.nombre,
            direccion=fila.direccion,
            ciudad=fila.ciudad,
            abastece_todo=not faltantes.get(fila.id),
            faltantes=faltantes.get(fila.id, []),
        )
        for fila in repository.listar_sucursales_activas(db)
    ]

    se_puede = bool(completas)
    return OpcionesDePedidoOut(
        lineas=resumen.lineas,
        total=resumen.total,
        unidades=resumen.unidades,
        se_puede_pedir=se_puede,
        motivo=(
            None
            if se_puede
            else (
                "Ninguna de nuestras sucursales tiene todas las prendas de su "
                "pedido. Puede dividirlo en dos compras."
            )
        ),
        sucursales=sucursales,
        direcciones=direcciones,
        pago_real=pagos.cobra_de_verdad(),
        minutos_para_pagar=settings.PEDIDO_VIGENCIA_MINUTOS,
    )


# --- Paso 2: confirmar ----------------------------------------------------

def crear_pedido(
    db: Session, usuario_id: int, datos: CrearPedidoIn
) -> CrearPedidoOut:
    """Pasos 2 a 5: confirmar, apartar stock, congelar precios e iniciar pago.

    EL ORDEN DE LAS OPERACIONES, QUE NO ES CASUAL
    ----------------------------------------------
    La sesion de pago se pide ANTES de tomar los bloqueos de inventario.

    Al reves ---apartar stock y llamar a la pasarela con las filas de
    `existencia` bloqueadas--- mantendria esos bloqueos durante una llamada de
    red a un tercero. Dos clientes comprando la misma prenda se serializarian
    detras del tiempo de respuesta de Stripe, no del de la base.

    El precio de este orden es que, si el apartado falla despues de abrir la
    sesion, queda una sesion huerfana en la pasarela. Es inofensiva y esta
    prevista: expira sola, y si alguien llegara a pagarla, CU-28 la guarda en
    `transaccion_pasarela` con `pago_id` nulo. Esta explicado en
    `pagos/service.iniciar_cobro`.

    La comprobacion de stock de `_cobertura` es SIN bloqueo y por eso es un
    aviso, no una garantia: entre elegir la sucursal y apartar, otro cliente
    pudo llevarse la ultima unidad. Quien garantiza es
    `inventario.apartar_para_reserva`, que toma `SELECT ... FOR UPDATE`. Lo que
    puede pasar es que el cliente vea un error tras haber abierto la sesion, y
    eso es correcto: es preferible a venderle algo que no hay.
    """
    cliente_id = _cliente(db, usuario_id)

    # Un solo pedido pendiente por cliente, y en ese orden: PRIMERO se bloquea
    # la fila del cliente y DESPUES se busca su pendiente.
    #
    # Al reves no sirve: si el cliente todavia no tiene pedido, la consulta no
    # devuelve filas y el `FOR UPDATE` no bloquea nada --- dos peticiones
    # simultaneas pasan las dos. Se reprodujo el 17/09 y esta explicado en
    # `repository.bloquear_cliente`.
    repository.bloquear_cliente(db, cliente_id)
    pendiente = repository.pedido_pendiente_de(db, cliente_id)
    if pendiente is not None:
        raise YaTienePedidoPendiente(pendiente.codigo)

    carrito = carrito_repository.obtener_carrito(db, cliente_id)
    if carrito is None:
        raise CarritoVacio()

    lineas = carrito_repository.lineas_resueltas(db, carrito.id)
    if not lineas:
        raise CarritoVacio()
    if any(not linea.ofrecible for linea in lineas):
        raise CarritoConPrendasCaidas()

    # --- El total, y la comparacion con lo que el cliente vio -------------
    #
    # CU-12: las promociones vigentes se leen AHORA, no cuando el cliente agrego
    # la prenda al carrito. Es la misma regla que el precio --- el carrito es una
    # intencion y no guarda ninguno de los dos --- y es lo que hace que una
    # promocion vencida no se honre indefinidamente.
    #
    # Se pide una sola vez para todo el pedido, no una por linea.
    descuentos = promociones.descuentos_por_variante(
        db, {linea.variante_id: linea.precio for linea in lineas}
    )

    subtotal = sum(
        (linea.precio * linea.cantidad for linea in lineas), Decimal("0.00")
    )
    # El subtotal es a precio de LISTA y el descuento sale aparte: asi lo pide
    # el CHECK `total = subtotal - descuento`, y asi la venta guarda cuanto se
    # rebajo --- que es lo que el tablero de CU-36 necesita para poder decirlo ---.
    descuento = sum(
        (
            descuentos[linea.variante_id].monto_unitario * linea.cantidad
            for linea in lineas
            if linea.variante_id in descuentos
        ),
        Decimal("0.00"),
    )
    total = subtotal - descuento

    if Decimal(datos.total_esperado) != total:
        raise PrecioCambiado(Decimal(datos.total_esperado), total)

    # --- De donde sale la mercaderia --------------------------------------
    faltantes, completas = _cobertura(db, lineas)

    if datos.modalidad_entrega == MODALIDAD_RETIRO:
        sucursal = repository.obtener_sucursal(db, datos.sucursal_id)
        if sucursal is None or not sucursal.activa:
            raise DestinoInvalido()
        if faltantes.get(sucursal.id):
            raise SucursalNoAbastece(faltantes[sucursal.id])
        sucursal_id = sucursal.id
        direccion_id = None
    else:
        direccion = repository.obtener_direccion(
            db, direccion_id=datos.direccion_id, cliente_id=cliente_id
        )
        if direccion is None:
            raise DestinoInvalido()
        if not completas:
            raise NingunaSucursalAbastece()
        sucursal_id = _elegir_sucursal_de_envio(completas, direccion.ciudad_id)
        direccion_id = direccion.id

    # --- La sesion de pago, ANTES de bloquear inventario ------------------
    codigo = _generar_codigo(db)
    lineas_pago = [
        LineaDePago(
            descripcion=f"{linea.producto_nombre} · {linea.talla_codigo or ''} "
            f"{linea.color_nombre or ''}".strip(),
            cantidad=linea.cantidad,
            # Con el descuento YA aplicado: la pasarela cobra lo que se cobra.
            # Mandarle el precio de lista le cobraria al cliente de mas y el
            # webhook de CU-28 confirmaria un importe que no coincide con la
            # venta guardada.
            precio_unitario=(
                descuentos[linea.variante_id].precio_final
                if linea.variante_id in descuentos
                else linea.precio
            ),
        )
        for linea in lineas
    ]

    # --- La venta, sus lineas y el apartado -------------------------------
    venta = repository.agregar_venta(
        db,
        codigo=codigo,
        canal=CANAL_DIGITAL,
        estado=ESTADO_PENDIENTE,
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        turno_caja_id=None,  # una venta digital no pasa por caja
        reserva_id=None,
        modalidad_entrega=datos.modalidad_entrega,
        direccion_id=direccion_id,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
    )

    for linea in lineas:
        # Aqui vive la mitigacion de R5, y no en este archivo: el bloqueo esta
        # dentro de `apartar_para_reserva`. Si no alcanza el stock levanta
        # StockInsuficiente, la transaccion entera se deshace y no queda ni
        # venta ni apartado a medias.
        inventario.apartar_para_reserva(
            db,
            variante_id=linea.variante_id,
            sucursal_id=sucursal_id,
            cantidad=linea.cantidad,
            usuario_id=usuario_id,
            motivo=f"Pedido {codigo}",
        )
        repository.agregar_detalle(
            db,
            venta_id=venta.id,
            variante_id=linea.variante_id,
            cantidad=linea.cantidad,
            # CONGELADOS LOS DOS. Desde aca ni el precio ni el descuento de esta
            # linea cambian nunca: si manana la promocion se apaga, este pedido
            # sigue explicando por que se cobro lo que se cobro.
            precio_unitario=linea.precio,
            descuento_unitario=(
                descuentos[linea.variante_id].monto_unitario
                if linea.variante_id in descuentos
                else Decimal("0.00")
            ),
        )

    url_pago, _ = pagos.iniciar_cobro(
        db,
        venta_id=venta.id,
        referencia=codigo,
        total=total,
        lineas=lineas_pago,
        correo_cliente=repository.correo_del_cliente(db, cliente_id),
    )

    db.commit()

    fila = repository.obtener_pedido(db, codigo=codigo, cliente_id=cliente_id)
    return CrearPedidoOut(
        pedido=_armar_pedido(db, fila),
        url_pago=url_pago,
        pago_real=pagos.cobra_de_verdad(),
    )


def conflicto_de_precio(
    db: Session, usuario_id: int, error: PrecioCambiado
) -> ConflictoDePrecioOut:
    """El cuerpo del 409, con el carrito al dia para que el cliente compare."""
    cliente_id = _cliente(db, usuario_id)
    carrito = carrito_repository.obtener_carrito(db, cliente_id)
    resumen = carrito_service._armar_carrito(db, carrito.id if carrito else None)
    return ConflictoDePrecioOut(
        detalle=(
            "El precio de alguna prenda cambió mientras usted decidía. "
            "Revise el total y vuelva a confirmar."
        ),
        total_esperado=error.esperado,
        total_actual=error.actual,
        lineas=resumen.lineas,
    )


# --- Consultar y cancelar --------------------------------------------------

def ver_pedido(db: Session, usuario_id: int, codigo: str) -> PedidoOut:
    """La ficha del pedido. Es lo que consulta la pantalla de retorno.

    D5 EN LA PRACTICA
    -----------------
    Esta es la pantalla a la que vuelve el cliente desde la pasarela, y lo que
    devuelve es el estado que dice la BASE, no el que diga la URL de retorno.
    Si el webhook todavia no llego, el pedido sigue en PENDIENTE_PAGO y la
    pantalla dice «estamos confirmando su pago». Decir «pagado» porque el
    navegador volvio por la URL de exito seria regalar mercaderia a quien
    escriba esa direccion a mano.
    """
    cliente_id = _cliente(db, usuario_id)
    fila = repository.obtener_pedido(db, codigo=codigo, cliente_id=cliente_id)
    if fila is None:
        raise PedidoInexistente()
    return _armar_pedido(db, fila)


def cancelar_pedido(db: Session, usuario_id: int, codigo: str) -> PedidoOut:
    """El cliente se arrepiente antes de pagar. Devuelve el stock apartado."""
    cliente_id = _cliente(db, usuario_id)
    venta = repository.obtener_venta_entidad(
        db, codigo=codigo, cliente_id=cliente_id, bloquear=True
    )
    if venta is None:
        raise PedidoInexistente()
    if venta.estado != ESTADO_PENDIENTE:
        # Una venta ya pagada no se cancela: se devuelve (CU-32), que es otra
        # cosa y mueve dinero.
        raise PedidoNoCancelable(venta.estado)

    _liberar(db, venta, motivo=f"Pedido {venta.codigo} cancelado por el cliente")
    venta.estado = ESTADO_CANCELADA
    db.commit()

    fila = repository.obtener_pedido(db, codigo=codigo, cliente_id=cliente_id)
    return _armar_pedido(db, fila)


def _liberar(db: Session, venta, *, motivo: str) -> int:
    """Devuelve a disponible lo que el pedido tenia apartado.

    Devuelve cuantas unidades libero. **Sin commit.**
    """
    unidades = 0
    for detalle in repository.detalles_de(db, venta.id):
        inventario.liberar_de_reserva(
            db,
            variante_id=detalle.variante_id,
            sucursal_id=venta.sucursal_id,
            cantidad=detalle.cantidad,
            usuario_id=None,
            motivo=motivo,
        )
        unidades += detalle.cantidad
    return unidades


def expirar_pedidos_vencidos(db: Session) -> ExpiracionDePedidosOut:
    """Cancela los pedidos que nadie pago y devuelve su stock.

    Es a CU-27 lo que CU-25 es a las reservas, y esta escrita igual: misma
    forma de consulta, mismo tope, mismo `skip_locked`. No hay planificador en
    el proceso; se dispara desde afuera, igual que la de reservas.

    SIN ESTO, APARTAR STOCK AL CONFIRMAR SERIA UN DEFECTO
    ------------------------------------------------------
    La decision 1 dice que el pedido aparta mercaderia antes de cobrarla. Eso
    solo es defendible si existe quien la devuelva cuando el pago no llega: de
    otro modo, cada cliente que abre la pasarela y cierra la pestana se lleva
    unidades del inventario para siempre.
    """
    corte = datetime.now(timezone.utc) - timedelta(
        minutes=settings.PEDIDO_VIGENCIA_MINUTOS
    )
    vencidos = repository.listar_pendientes_vencidos(db, corte=corte, tope=TOPE_EXPIRACION)

    unidades = 0
    for venta in vencidos:
        unidades += _liberar(
            db, venta, motivo=f"Pedido {venta.codigo} vencido sin pago"
        )
        venta.estado = ESTADO_CANCELADA

    if vencidos:
        db.commit()
        _log.info(
            "Expiracion de pedidos: %d cancelados, %d unidades devueltas.",
            len(vencidos),
            unidades,
        )

    return ExpiracionDePedidosOut(
        revisados=len(vencidos), cancelados=len(vencidos), unidades_devueltas=unidades
    )
