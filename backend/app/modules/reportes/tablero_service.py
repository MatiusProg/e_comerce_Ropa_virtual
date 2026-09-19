"""
P11 - Reportes y Tablero / CU-36  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 3
Caso de uso: CU-36 Consultar tablero de indicadores

Es de solo lectura, asi que no hay transaccion que controlar. Lo que vive aqui
son las tres cosas que la consulta no sabe: que periodo se mira cuando nadie lo
dice, como se calculan las tasas, y que cuenta como venta.

LOS SIETE INDICADORES YA ESTAN COMPLETOS
-----------------------------------------
Se entrego con cuatro apagados ---ventas del dia y del mes, ticket promedio y
prendas mas vendidas--- porque `venta` y `detalle_venta` nacian con la `0006` y
todavia no existian. Ya existen y hay ventas pagadas de verdad, asi que el
bloque se encendio el 19/09.

Lo que la nota vieja prometia se cumplio: **hubo que tocar UNA sola funcion**,
`_ventas`. El contrato, el router y la pantalla no cambiaron --- la web ya traia
escrita la rama de `disponible: true` desde el primer dia.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.modules.inventario import service as inventario_service
from app.modules.reportes import tablero_repository as repository
from app.modules.reportes.tablero_schemas import (
    AlertaStockOut,
    ConversionOut,
    PeriodoOut,
    PrendaReservadaOut,
    ReservasPorEstadoOut,
    SaludInventarioOut,
    TableroOut,
    VentasOut,
)
from app.modules.reservas.models import ESTADOS_RESERVA

#: Cuantos dias mira el tablero cuando nadie pide un periodo. Treinta y no siete:
#: una semana de una boutique con pocas reservas diarias da tarjetas en cero y un
#: grafico de una sola barra, que no se lee como «poca actividad» sino como
#: «esto esta roto».
DIAS_POR_OMISION = 30

#: Cuantas prendas entran en cada ranking. Cinco es lo que cabe en una tarjeta
#: sin que el tablero se convierta en un listado --- para el listado completo
#: esta CU-37, que exporta.
TOPE_RANKING = 5

#: Cuantas alertas de stock se muestran. Mismo criterio, con una diferencia: el
#: TOTAL de filas en alerta viaja igual aunque la lista se corte, porque «hay 40
#: prendas por reponer» es el dato que importa y «estas 5 son las peores» es
#: nada mas por donde empezar.
TOPE_ALERTAS = 8

#: Los estados finales de una reserva. Una reserva cerrada es una que ya no
#: puede cambiar: es el denominador de la tasa de atencion. Se derivan de
#: ESTADOS_RESERVA en vez de escribirse a mano para que agregar un estado a P6
#: no deje esta cuenta silenciosamente vieja.
ESTADOS_CERRADOS = ("ATENDIDA", "CANCELADA", "EXPIRADA")

#: Los que siguen vivos. Los dos juegos tienen que cubrir ESTADOS_RESERVA entero
#: y no solaparse; la prueba lo comprueba.
ESTADOS_ABIERTOS = ("PENDIENTE", "PREPARADA")


def _ahora() -> datetime:
    """El instante actual, siempre con zona horaria.

    Mismo criterio que `reservas/service.py::_ahora`: `creado_en` es
    `timestamptz` y comparar un `datetime` con zona contra uno sin zona es un
    TypeError en tiempo de ejecucion, no un numero equivocado.
    """
    return datetime.now(timezone.utc)


def _resolver_periodo(desde: date | None, hasta: date | None) -> tuple[date, date]:
    """Los dos extremos, con los huecos rellenados.

    Las cuatro combinaciones se resuelven hacia atras desde hoy, porque un
    tablero se abre para mirar lo reciente: sin nada, los ultimos 30 dias; con
    solo `desde`, de ahi hasta hoy; con solo `hasta`, los 30 dias que terminan
    ahi.

    **Si vienen invertidos se intercambian en vez de rechazarse.** Un rango al
    reves no es un dato ambiguo ---se entiende perfectamente que se queria---
    y devolver un 422 por eso obliga a la pantalla a ordenar dos fechas que el
    usuario acaba de elegir en un calendario.
    """
    hoy = _ahora().date()

    if desde is None and hasta is None:
        hasta = hoy
        desde = hoy - timedelta(days=DIAS_POR_OMISION - 1)
    elif hasta is None:
        hasta = hoy
    elif desde is None:
        desde = hasta - timedelta(days=DIAS_POR_OMISION - 1)

    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


def _limites(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """De dos fechas a los dos instantes que encierran el periodo.

    El extremo derecho es el comienzo del dia SIGUIENTE, y el repositorio
    compara con `<`. Es lo que hace que «hasta el 15» incluya el 15 entero:
    comparar `<=` contra el 15 a las 00:00:00 dejaria afuera todo salvo lo que
    caiga justo en la medianoche, y es el error que no se nota hasta que alguien
    consulta un solo dia y ve el tablero vacio.

    Se interpreta en UTC, que es la zona en que guarda `timestamptz` y la misma
    en que P6 escribe `creado_en`. Para una boutique en Bolivia eso corre el
    corte cuatro horas; conviene saberlo antes de la defensa, pero arreglarlo es
    elegir una zona del negocio, y eso no esta decidido en ningun documento
    todavia. Se deja anotado aca en vez de inventar una.
    """
    inicio = datetime.combine(desde, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(hasta + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return inicio, fin


def _porcentaje(parte: int, total: int) -> float | None:
    """La tasa, o nada si no hay denominador.

    Nulo y no cero: «ninguna reserva se cerro todavia» y «se cerraron diez y
    ninguna se atendio» son dos situaciones opuestas, y devolver 0.0 en la
    primera pinta el tablero en rojo el dia que se estrena el sistema.
    """
    if total <= 0:
        return None
    return round(parte * 100 / total, 1)


def _reservas(por_estado: dict[str, int]) -> ReservasPorEstadoOut:
    """Los cinco estados, completando con cero los que la consulta no trajo."""
    cuenta = {estado: por_estado.get(estado, 0) for estado in ESTADOS_RESERVA}
    return ReservasPorEstadoOut(
        pendientes=cuenta["PENDIENTE"],
        preparadas=cuenta["PREPARADA"],
        atendidas=cuenta["ATENDIDA"],
        canceladas=cuenta["CANCELADA"],
        expiradas=cuenta["EXPIRADA"],
        total=sum(cuenta.values()),
        abiertas=sum(cuenta[estado] for estado in ESTADOS_ABIERTOS),
    )


def _conversion(
    por_estado: dict[str, int], por_resultado: dict[str, int]
) -> ConversionOut:
    """Las dos tasas. Ver la docstring de `ConversionOut` para la diferencia."""
    cerradas = sum(por_estado.get(estado, 0) for estado in ESTADOS_CERRADOS)
    atendidas = por_estado.get("ATENDIDA", 0)

    llevadas = por_resultado.get("LLEVA", 0)
    probadas = llevadas + por_resultado.get("NO_LLEVA", 0)

    return ConversionOut(
        cerradas=cerradas,
        atendidas=atendidas,
        tasa_atencion=_porcentaje(atendidas, cerradas),
        lineas_probadas=probadas,
        lineas_llevadas=llevadas,
        tasa_prueba=_porcentaje(llevadas, probadas),
    )


def _inventario(db: Session, sucursal_id: int | None) -> tuple[SaludInventarioOut, list[AlertaStockOut]]:
    """Los saldos y las alertas.

    Las alertas se piden por la costura `inventario.service.alertas_de_stock` y
    no con SQL propio: «que es stock critico» es una regla de P4, y copiarla
    haria que el dia que cambie, CU-16 y el tablero digan cosas distintas sobre
    la misma prenda. Ver la cabecera de `tablero_repository.py`.

    La costura devuelve la lista entera, asi que el total en alerta sale de
    contarla y no de una segunda consulta. Esta acotada por definicion ---solo
    las que estan bajo el minimo--- y si algun dia deja de estarlo, el problema
    no seria el tablero.
    """
    saldos = repository.salud_inventario(db, sucursal_id=sucursal_id)
    alertas = inventario_service.alertas_de_stock(db, sucursal_id=sucursal_id)

    salud = SaludInventarioOut(
        total_disponible=saldos.total_disponible,
        total_reservado=saldos.total_reservado,
        en_alerta=len(alertas),
        variantes_sin_stock=saldos.variantes_sin_stock,
    )
    cortadas = [
        AlertaStockOut(
            variante_id=fila.variante_id,
            sku=fila.sku,
            producto=fila.producto,
            talla=fila.talla,
            color=fila.color,
            sucursal_id=fila.sucursal_id,
            sucursal=fila.sucursal,
            cantidad_disponible=fila.cantidad_disponible,
            stock_minimo=fila.stock_minimo,
        )
        for fila in alertas[:TOPE_ALERTAS]
    ]
    return salud, cortadas


def _dinero(valor) -> Decimal:
    """Un monto con dos decimales, siempre.

    `SUM` sobre cero filas devuelve el entero 0 del `coalesce`, y sin esto el
    tablero diria «0» un dia y «640.00» al siguiente para el mismo campo. Que un
    importe cambie de forma segun si hubo ventas obliga a cada pantalla a
    normalizarlo por su cuenta, y basta con que una se olvide para que el
    numero se vea distinto en dos lugares.

    Redondeo comercial, el mismo que usa la conversion a centavos de Stripe.
    """
    return Decimal(valor or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ventas(
    db: Session, *, desde: datetime, hasta: datetime, sucursal_id: int | None
) -> VentasOut:
    """Los cuatro indicadores que dependen de `venta` y `detalle_venta`.

    Estuvo devolviendo `disponible=False` desde que se escribio CU-36: las
    tablas nacian con la `0006` de Mateo y todavia no existian. Ya existen, y
    **hay ventas pagadas de verdad**, asi que se enciende.

    Se cumplio lo que decia la nota vieja: fue el UNICO lugar que hubo que
    tocar. Ni el contrato ni el router ni la pantalla cambiaron --- la web ya
    tenia escrita la rama de `disponible: true` desde el primer dia.

    QUE CUENTA COMO VENTA
    ---------------------
    Solo PAGADA y ENTREGADA. Un pedido en PENDIENTE_PAGO no es una venta: es una
    intencion con stock apartado, el dinero no entro, y la barrida de vencidos
    puede cancelarlo en veinte minutos. Contarlo inflaria el monto del dia con
    compras que nadie pago. La regla vive en `ESTADOS_VENDIDOS`, en el
    repositorio, junto a las consultas que la usan.

    EL TICKET PROMEDIO SE DIVIDE ACA, NO EN SQL
    --------------------------------------------
    Porque el caso de cero ventas es una decision de negocio y no de consulta:
    **nulo, no cero**. Cero pesos de ticket promedio se lee como «vendemos y no
    cobramos»; la ausencia de ventas se lee como «todavia no vendimos». Es el
    mismo criterio que rige las dos tasas de conversion --- ver `_porcentaje`.
    """
    resumen = repository.resumen_de_ventas(
        db, desde=desde, hasta=hasta, sucursal_id=sucursal_id
    )
    monto = _dinero(resumen.monto)
    cantidad = int(resumen.cantidad or 0)

    ranking = repository.top_variantes_vendidas(
        db, desde=desde, hasta=hasta, sucursal_id=sucursal_id, limite=TOPE_RANKING
    )

    return VentasOut(
        disponible=True,
        # «Vendido hoy» es SIEMPRE hoy, aunque se este mirando otro periodo:
        # es el pulso del negocio. Ver `monto_vendido_hoy`.
        monto_hoy=_dinero(repository.monto_vendido_hoy(db, sucursal_id=sucursal_id)),
        monto_periodo=monto,
        cantidad_periodo=cantidad,
        ticket_promedio=_dinero(monto / cantidad) if cantidad else None,
        mas_vendidas=[_prenda(fila) for fila in ranking],
        motivo=None,
    )


def _prenda(fila) -> PrendaReservadaOut:
    return PrendaReservadaOut(
        variante_id=fila.variante_id,
        sku=fila.sku,
        producto=fila.producto,
        talla=fila.talla,
        color=fila.color,
        unidades=int(fila.unidades or 0),
        reservas=int(fila.reservas or 0),
    )


def consultar(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    sucursal_id: int | None = None,
) -> TableroOut:
    """Paso 2 del caso de uso: los indicadores del negocio, en una respuesta.

    Una sucursal inexistente **no es un error**: el tablero responde con sus
    cifras en cero y sin nombre de sucursal. Es de solo lectura y no hay nada
    que proteger, y un 404 obligaria a la pantalla a distinguir «no existe» de
    «no tuvo movimiento», que se ven igual y se atienden igual.
    """
    desde, hasta = _resolver_periodo(desde, hasta)
    inicio, fin = _limites(desde, hasta)

    por_estado = repository.contar_reservas_por_estado(
        db, desde=inicio, hasta=fin, sucursal_id=sucursal_id
    )
    por_resultado = repository.contar_lineas_probadas(
        db, desde=inicio, hasta=fin, sucursal_id=sucursal_id
    )
    ranking = repository.top_variantes_reservadas(
        db, desde=inicio, hasta=fin, sucursal_id=sucursal_id, limite=TOPE_RANKING
    )
    salud, alertas = _inventario(db, sucursal_id)

    return TableroOut(
        periodo=PeriodoOut(
            desde=desde,
            hasta=hasta,
            sucursal_id=sucursal_id,
            sucursal=(
                repository.nombre_de_sucursal(db, sucursal_id)
                if sucursal_id is not None
                else None
            ),
        ),
        calculado_en=_ahora(),
        reservas=_reservas(por_estado),
        conversion=_conversion(por_estado, por_resultado),
        mas_reservadas=[_prenda(fila) for fila in ranking],
        inventario=salud,
        alertas=alertas,
        ventas=_ventas(db, desde=inicio, hasta=fin, sucursal_id=sucursal_id),
    )
