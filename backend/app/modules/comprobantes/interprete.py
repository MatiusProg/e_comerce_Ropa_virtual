"""
P16 - Mis comprobantes / CU-46  |  intérprete por reglas (sin IA)

Traduce «mis últimas 3 compras», «mis recibos de octubre» o «mis devoluciones»
a un criterio de búsqueda: **tipo** (compras, devoluciones o todo),
**cantidad** y **período** (y, si lo dice, el estado).

POR QUÉ SOLO REGLAS Y NO GEMINI
-------------------------------
CU-27 usa Gemini con estas mismas reglas de respaldo, pero allí lo paga la
empresa con su cupo mensual (`reportes_ia`). Acá quien pregunta es el
**cliente**: si cada consulta gastara el cupo de la tienda, cualquier cliente
podría agotárselo pidiendo sus recibos. Además el vocabulario es chico ---tres
tipos, una cantidad, un período--- y las reglas lo cubren entero, en
milisegundos y sin depender de un servicio externo que a veces no contesta.

Lo que no entiende lo devuelve como no entendido (`None`): **nunca se inventa
un criterio** para mostrar algo.

Reusa las piezas del intérprete de CU-27 (`reportes.interprete_reglas`): la
normalización, los números en palabras y los períodos relativos («este mes»,
«el mes pasado», «los últimos tres meses», «octubre»).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.modules.reportes.interprete_reglas import (
    MESES,
    _fin_de_mes,
    _normal,
    _numero,
    _periodo,
)

#: Tope de comprobantes por consulta. Una lista más larga ya no se lee en una
#: pantalla, y pedir «mis últimas 10000 compras» no debe pegarle a la base.
MAXIMO = 50
#: Cuántos se muestran si el pedido no dice cuántos ni de cuándo.
POR_OMISION = 10

COMPRAS = "COMPRAS"
DEVOLUCIONES = "DEVOLUCIONES"
TODO = "TODO"

EJEMPLOS = [
    "Mis últimas 3 compras",
    "Mis recibos de octubre",
    "Mis devoluciones",
    "Mis compras del mes pasado",
    "Todos mis comprobantes de este año",
    "Mis compras pagadas de los últimos 3 meses",
]

_PALABRA_NUMERO = r"(\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|doce|quince|veinte)"
_SUSTANTIVOS = (
    r"(compras?|recibos?|facturas?|pedidos?|tickets?|devoluciones|devolucion|"
    r"notas?|comprobantes?|movimientos?|transacciones|transaccion|cambios?)"
)

_ESTADOS_COMPRA = (
    (r"\bpagad", "PAGADA"),
    (r"\bentregad", "ENTREGADA"),
    (r"\bpendiente|sin pagar|por pagar", "PENDIENTE_PAGO"),
    (r"\bcancelad|anulad", "CANCELADA"),
)
_ESTADOS_DEVOLUCION = (
    (r"\babierta", "ABIERTA"),
    (r"\bcerrada", "CERRADA"),
)


@dataclass
class Criterio:
    """Lo que se entendió del pedido. Es lo único que llega a la consulta."""

    tipo: str = TODO
    cantidad: int | None = None
    desde: date | None = None
    hasta: date | None = None
    estado: str | None = None
    avisos: list[str] = field(default_factory=list)

    @property
    def limite(self) -> int:
        if self.cantidad is not None:
            return self.cantidad
        # Con un período se muestra todo el período (hasta el tope); sin nada,
        # los más recientes.
        return MAXIMO if (self.desde or self.hasta) else POR_OMISION


def _tipo(t: str) -> tuple[str, bool]:
    """El tipo pedido, y si se nombró explícitamente."""
    devoluciones = bool(re.search(r"devol|devuel|reembols|\bnotas?\b|\bcambios?\b", t))
    # `\bcompra` y no `compr`: «comprobante» también empieza con «compr».
    compras = bool(re.search(r"\bcompra|\bcompre\b|recibo|factura|pedido|ticket", t))
    todo = bool(re.search(r"\btodo|comprobante|movimiento|transacc|historial", t))
    if devoluciones and compras:
        return TODO, True
    if devoluciones:
        return DEVOLUCIONES, True
    if compras:
        return COMPRAS, True
    return TODO, todo


def _cantidad(t: str) -> int | None:
    # «mis últimas 3 compras», «las 5 últimas», «mis 3 recibos».
    for patron in (
        rf"ultim[oa]s? {_PALABRA_NUMERO}\b(?! (meses|mes|semanas|semana|dias|dia|anos|ano)\b)",
        rf"\b{_PALABRA_NUMERO} ultim[oa]s?\b",
        rf"\b{_PALABRA_NUMERO} {_SUSTANTIVOS}\b",
    ):
        m = re.search(patron, t)
        if m and (n := _numero(m.group(1))) is not None:
            return n
    # «mi última compra», «el último recibo»: una sola.
    if re.search(r"\b(mi|el|la) ultim[oa]\b", t):
        return 1
    return None


def _fecha_numerica(dia: str, mes: str, anio: str | None, hoy: date) -> date | None:
    try:
        a = int(anio) if anio else hoy.year
        if a < 100:
            a += 2000
        return date(a, int(mes), int(dia))
    except ValueError:
        return None


def _periodo_explicito(t: str, hoy: date) -> tuple[date | None, date | None, bool]:
    """Rangos con fechas: «del 01/10 al 15/10», «desde el 3/9/2026», «octubre de 2025».

    El tercer valor dice si se encontró algo (aunque haya quedado abierto de un
    lado, como «desde el 1/10»).
    """
    fechas = [
        (m.start(), _fecha_numerica(m.group(1), m.group(2), m.group(3), hoy))
        for m in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", t)
    ]
    fechas = [(p, f) for p, f in fechas if f is not None]
    if len(fechas) >= 2:
        return fechas[0][1], fechas[1][1], True
    if len(fechas) == 1:
        posicion, fecha = fechas[0]
        antes = t[:posicion]
        if re.search(r"(desde|a partir)\D*$", antes):
            return fecha, None, True
        if re.search(r"(hasta|antes)\D*$", antes):
            return None, fecha, True
        return fecha, fecha, True

    meses = "|".join(MESES)
    # «del 1 al 15 de octubre (de 2025)»
    m = re.search(rf"\bdel? (\d{{1,2}}) al (\d{{1,2}}) de ({meses})(?: de(?:l)? (\d{{4}}))?", t)
    if m:
        mes = MESES[m.group(3)]
        anio = int(m.group(4)) if m.group(4) else (hoy.year if mes <= hoy.month else hoy.year - 1)
        try:
            return date(anio, mes, int(m.group(1))), date(anio, mes, int(m.group(2))), True
        except ValueError:
            return None, None, False
    # «octubre de 2025», «octubre 2025»
    m = re.search(rf"\b({meses})(?: de(?:l)?)? (\d{{4}})\b", t)
    if m:
        mes, anio = MESES[m.group(1)], int(m.group(2))
        return date(anio, mes, 1), _fin_de_mes(anio, mes), True
    if re.search(r"\b(el )?ano pasado\b", t):
        return date(hoy.year - 1, 1, 1), date(hoy.year - 1, 12, 31), True
    m = re.search(r"\b(?:en|del|de) (20\d{2})\b", t)
    if m:
        anio = int(m.group(1))
        return date(anio, 1, 1), date(anio, 12, 31), True
    return None, None, False


def _estado(t: str, tipo: str) -> str | None:
    tablas = []
    if tipo in (COMPRAS, TODO):
        tablas.append(_ESTADOS_COMPRA)
    if tipo in (DEVOLUCIONES, TODO):
        tablas.append(_ESTADOS_DEVOLUCION)
    for tabla in tablas:
        for patron, estado in tabla:
            if re.search(patron, t):
                return estado
    return None


def interpretar(texto: str, hoy: date) -> Criterio | None:
    """El criterio del pedido, o `None` si no se entendió nada útil."""
    t = re.sub(r"\s+", " ", _normal(texto)).strip()
    if not t:
        return None

    tipo, tipo_explicito = _tipo(t)
    cantidad = _cantidad(t)
    desde, hasta, explicito = _periodo_explicito(t, hoy)
    if not explicito:
        desde, hasta = _periodo(t, hoy)
    estado = _estado(t, tipo)

    if not (tipo_explicito or cantidad is not None or desde or hasta or estado):
        return None

    criterio = Criterio(tipo=tipo, cantidad=cantidad, desde=desde, hasta=hasta, estado=estado)
    if desde and hasta and desde > hasta:
        criterio.desde, criterio.hasta = hasta, desde
    if cantidad is not None:
        if cantidad < 1:
            criterio.cantidad = 1
        elif cantidad > MAXIMO:
            criterio.cantidad = MAXIMO
            criterio.avisos.append(
                f"Se muestran como máximo {MAXIMO} comprobantes por consulta."
            )
    return criterio


_NOMBRES = {
    COMPRAS: ("compra", "compras"),
    DEVOLUCIONES: ("devolución", "devoluciones"),
    TODO: ("comprobante", "comprobantes"),
}
_ESTADOS_LEGIBLES = {
    "PAGADA": "pagadas",
    "ENTREGADA": "entregadas",
    "PENDIENTE_PAGO": "pendientes de pago",
    "CANCELADA": "canceladas",
    "ABIERTA": "abiertas",
    "CERRADA": "cerradas",
}


def resumir(criterio: Criterio) -> str:
    """Lo que se entendió, en castellano, para mostrarlo arriba de la lista."""
    singular, plural = _NOMBRES[criterio.tipo]
    if criterio.cantidad == 1:
        frase = f"Tu última {singular}" if criterio.tipo != TODO else "Tu último comprobante"
    elif criterio.cantidad:
        ultimas = "últimos" if criterio.tipo == TODO else "últimas"
        frase = f"Tus {ultimas} {criterio.cantidad} {plural}"
    else:
        frase = f"Tus {plural}"
    if criterio.estado:
        frase += f" {_ESTADOS_LEGIBLES[criterio.estado]}"
    formato = "%d/%m/%Y"
    if criterio.desde and criterio.hasta:
        if criterio.desde == criterio.hasta:
            frase += f" del {criterio.desde.strftime(formato)}"
        else:
            frase += (
                f" del {criterio.desde.strftime(formato)}"
                f" al {criterio.hasta.strftime(formato)}"
            )
    elif criterio.desde:
        frase += f" desde el {criterio.desde.strftime(formato)}"
    elif criterio.hasta:
        frase += f" hasta el {criterio.hasta.strftime(formato)}"
    if criterio.cantidad is None and not (criterio.desde or criterio.hasta):
        frase += f" (las {POR_OMISION} más recientes)" if criterio.tipo != TODO else (
            f" (los {POR_OMISION} más recientes)"
        )
    return frase
