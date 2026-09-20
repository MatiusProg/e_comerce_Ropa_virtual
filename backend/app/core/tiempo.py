"""
Nucleo | El tiempo, y cual de las dos preguntas se esta haciendo.

POR QUE EXISTE ESTE ARCHIVO
----------------------------
El 20/09/2026 Karen reporto que «la hora en general no es hora boliviana». Al
buscarlo aparecio que no habia UN lugar donde cambiarla, y que el problema no
era parejo: **hay dos preguntas distintas sobre el tiempo y solo una estaba
mal**.

**1. «¿En que instante paso esto?»** --- `turno.cerrado_en`, el vencimiento de
un token, `revocado_en`, la franja de una reserva. La respuesta correcta es un
instante en UTC, guardado en una columna `timestamptz`. **Eso ya estaba bien** y
no hay que tocarlo: la base guarda el instante, el navegador lo convierte a la
zona de quien mira, y el mismo dato se lee bien desde Santa Cruz y desde
cualquier otro lado. Para eso esta `ahora()`.

**2. «¿Que dia es hoy?» y «¿como se escribe esta fecha?»** --- el codigo de una
venta (`VP-20260920-A3F2`), «las ventas de HOY» del tablero, la vigencia de una
promocion, la fecha impresa en un comprobante. Acá **la zona importa**, porque
la respuesta cambia segun donde se pregunte.

Y ahi estaba el defecto: **Railway corre en UTC**, donde el dia cambia a las
20:00 hora boliviana. Entre las 20:00 y la medianoche, con la tienda todavia
abierta:

- una venta se guardaba con el codigo del dia siguiente;
- el tablero decia «vendido hoy: 0» y empezaba a contar el dia que viene;
- una promocion que terminaba «el 30» dejaba de aplicar cuatro horas antes;
- un comprobante se imprimia con la fecha de manana.

Ninguna de esas cosas falla ni avisa. Se ven raras y se explican mal.

COMO SE USA
-----------
- Guardar un instante -> `ahora()`.
- Preguntar que dia es, o formatear para que lo lea una persona -> `hoy()` y
  `en_bolivia()`.

`datetime.now()` a secas **no se usa nunca**: es la hora del reloj del servidor,
sin zona, que en Railway es UTC y en la maquina de desarrollo es Bolivia. Ese es
el peor de los tres, porque anda bien mientras se prueba y falla desplegado.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

#: Bolivia no tiene horario de verano, asi que el desfase es fijo y no hace
#: falta `zoneinfo` --- que en Windows necesita el paquete `tzdata` instalado
#: aparte y es una dependencia mas que puede faltar justo en el despliegue.
BOLIVIA = timezone(timedelta(hours=-4))


def ahora() -> datetime:
    """El instante actual, en UTC y con zona.

    Es lo que va a una columna `timestamptz`. No se convierte a Bolivia al
    guardar: un instante no tiene nacionalidad, y guardarlo ya corrido dejaria
    a la base sin saber si el valor es UTC o local.
    """
    return datetime.now(timezone.utc)


def en_bolivia(momento: datetime) -> datetime:
    """El mismo instante, visto desde Bolivia.

    Para **mostrar**: un comprobante, un reporte, cualquier texto que lea una
    persona. Si el dato viene sin zona se asume UTC, que es lo que guarda la
    base; suponer lo contrario haria que un valor viejo se corriera cuatro
    horas al imprimirlo.
    """
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(BOLIVIA)


def hoy() -> date:
    """Que dia es **en Bolivia**.

    Para la vigencia de una promocion, el corte de «las ventas de hoy» y la
    fecha que forma parte del codigo de una venta.
    """
    return datetime.now(BOLIVIA).date()


def inicio_del_dia(dia: date | None = None) -> datetime:
    """La medianoche boliviana de ese dia, como instante en UTC.

    Es lo que hace falta para comparar contra una columna `timestamptz`: «las
    ventas de hoy» son las que ocurrieron entre las 00:00 y las 24:00 **de
    Bolivia**, no las del dia UTC. Con el corte en UTC, todo lo vendido despues
    de las 20:00 se contaba como del dia siguiente.
    """
    dia = dia or hoy()
    return datetime.combine(dia, datetime.min.time(), tzinfo=BOLIVIA).astimezone(
        timezone.utc
    )


def fin_del_dia(dia: date | None = None) -> datetime:
    """El instante en que TERMINA ese dia: la medianoche boliviana del
    siguiente.

    AGREGADO EL 20/09 PARA EL PERIODO DE LOS REPORTES (CU-37 y CU-36).

    Se devuelve el limite **abierto** a proposito, para compararlo con `<`.
    Con `<=` queda fuera todo lo que paso ese dia despues de medianoche ---el
    defecto clasico de los reportes por fecha--- y ahi el corte por zona ya
    no importa porque igual falta media jornada.
    """
    return inicio_del_dia((dia or hoy()) + timedelta(days=1))


def formatear(momento: datetime, patron: str = "%d/%m/%Y %H:%M") -> str:
    """Un instante escrito para que lo lea una persona, en hora boliviana."""
    return en_bolivia(momento).strftime(patron)


__all__ = [
    "BOLIVIA",
    "ahora",
    "en_bolivia",
    "fin_del_dia",
    "formatear",
    "hoy",
    "inicio_del_dia",
]
