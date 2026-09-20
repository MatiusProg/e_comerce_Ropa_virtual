"""El tiempo del negocio: Bolivia.

POR QUE ESTE MODULO EXISTE
---------------------------
Todas las columnas de fecha son `TIMESTAMPTZ`, asi que **lo guardado siempre
es correcto**: un `timestamptz` no guarda «una hora», guarda un instante
absoluto y la zona se aplica al leer. Nada de esto se arregla con un script
en la base --- restarle cuatro horas a lo almacenado corromperia instantes
que ya eran los buenos.

Lo que si estaba mal es **quien decide que dia es hoy**. `date.today()` toma
el reloj del servidor, y el servidor corre en UTC: a las 21:00 de un martes
en Santa Cruz, para Railway ya es miercoles. Con la tienda abierta hasta las
20:00, eso mete la ultima hora de cada dia en el reporte del dia siguiente.

Ya estaba descubierto y resuelto para las promociones (CU-12), pero el
arreglo se habia quedado ahi. Este modulo lo vuelve uno solo.

QUE VA POR ACA Y QUE NO
------------------------
Por aca va todo lo que sea **un dia del calendario** o **una fecha que se
imprime**: el periodo de un reporte, el «hoy» del tablero, el correlativo de
una venta, la fecha de un archivo.

**NO va lo que sea un instante**: el vencimiento de un token, el `cerrado_en`
de un turno, la franja de una reserva, la vigencia de una recomendacion. Eso
se sigue calculando en UTC ---`datetime.now(timezone.utc)`--- porque un
instante no tiene zona y convertirlo solo agrega una oportunidad de
equivocarse.

POR QUE UN DESFASE FIJO Y NO `ZoneInfo`
----------------------------------------
Bolivia esta en UTC-4 **sin horario de verano desde 1932**: no hay
transiciones que una base de zonas horarias tenga que resolver. Un desfase
fijo da el mismo resultado sin depender de que el paquete `tzdata` este
instalado, que en Windows no viene de serie y haria fallar al importar.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

#: La zona horaria de Bolivia (UTC-4, sin horario de verano).
BOLIVIA = timezone(timedelta(hours=-4), name="BOT")


def ahora() -> datetime:
    """El instante actual, expresado en hora boliviana.

    Para **mostrar**. Para comparar da igual: un instante es el mismo aunque
    se escriba en otra zona.
    """
    return datetime.now(BOLIVIA)


def hoy() -> date:
    """Que dia es hoy EN BOLIVIA.

    Es el reemplazo de `date.today()` en todo lo que sea negocio. La
    diferencia aparece entre las 20:00 y la medianoche, que es justo cuando
    la tienda esta cerrando la caja.
    """
    return ahora().date()


def inicio_del_dia(dia: date) -> datetime:
    """La medianoche boliviana de ese dia, como instante.

    Es lo que hay que comparar contra una columna `timestamptz`. Construir el
    limite con `tzinfo=timezone.utc` ---que es lo que se hacia--- corre el
    dia cuatro horas: el «20 de septiembre» empezaba a las 20:00 del 19.
    """
    return datetime.combine(dia, time.min, tzinfo=BOLIVIA)


def fin_del_dia(dia: date) -> datetime:
    """El instante en que **termina** ese dia: la medianoche del siguiente.

    Se devuelve el limite abierto a proposito. `<= dia` deja fuera todo lo
    que paso despues de medianoche de ese mismo dia, y es el defecto clasico
    de los reportes por fecha.
    """
    return inicio_del_dia(dia + timedelta(days=1))


def en_boliviana(momento: datetime) -> datetime:
    """Traduce a hora boliviana un instante que viene de la base.

    Si llega sin zona se asume UTC: es lo que devuelve una columna leida por
    un camino que perdio el `tzinfo`, y suponer hora local seria suponer que
    el servidor esta en Bolivia --- que es justo lo que no pasa.
    """
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(BOLIVIA)


def marca(momento: datetime | None = None) -> str:
    """Una fecha y hora para imprimir: `20/09/2026 14:30`."""
    return en_boliviana(momento or ahora()).strftime("%d/%m/%Y %H:%M")
