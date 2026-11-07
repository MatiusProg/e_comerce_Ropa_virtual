"""
P11 - Reportes / CU-27  |  capa: servicio (intérprete de respaldo, sin IA)

Traduce la frase a la misma especificación que arma Gemini, con reglas.

POR QUÉ EXISTE
--------------
Medido el 20/09 con el pedido por voz: Gemini tarda entre 2 y 31 s y a veces no
atiende (429/503). En la defensa eso es un reporte que no sale. Si el modelo no
está configurado o no contesta, este intérprete cubre las frases comunes
—las del enunciado— y la pantalla avisa que el pedido se resolvió «sin IA».
No reemplaza al modelo: entiende menos variantes y no maneja ambigüedades
finas; las que no entiende las devuelve como no entendidas.

La salida pasa por `dinamico.validar` igual que la del modelo.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
NUMEROS = {"un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
           "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "doce": 12, "quince": 15,
           "veinte": 20}


def _normal(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")


def _numero(palabra: str) -> int | None:
    if palabra.isdigit():
        return int(palabra)
    return NUMEROS.get(palabra)


def _fin_de_mes(anio: int, mes: int) -> date:
    siguiente = date(anio + (mes == 12), 1 if mes == 12 else mes + 1, 1)
    return siguiente - timedelta(days=1)


def _restar_meses(dia: date, meses: int) -> date:
    total = dia.year * 12 + dia.month - 1 - meses
    return date(total // 12, total % 12 + 1, 1)


def _periodo(t: str, hoy: date) -> tuple[date | None, date | None]:
    if "hoy" in t:
        return hoy, hoy
    if "ayer" in t:
        return hoy - timedelta(days=1), hoy - timedelta(days=1)
    if "esta semana" in t:
        return hoy - timedelta(days=hoy.weekday()), hoy
    if "semana pasada" in t:
        inicio = hoy - timedelta(days=hoy.weekday() + 7)
        return inicio, inicio + timedelta(days=6)
    if "este mes" in t:
        return hoy.replace(day=1), hoy
    if "mes pasado" in t:
        inicio = _restar_meses(hoy, 1)
        return inicio, _fin_de_mes(inicio.year, inicio.month)
    if "este ano" in t:
        return date(hoy.year, 1, 1), hoy
    m = re.search(r"ultim[oa]s? (\w+) (meses|semanas|dias)", t)
    if m and (n := _numero(m.group(1))):
        if m.group(2) == "meses":
            return _restar_meses(hoy, n - 1), hoy
        if m.group(2) == "semanas":
            return hoy - timedelta(weeks=n) + timedelta(days=1), hoy
        return hoy - timedelta(days=n - 1), hoy
    for nombre, mes in MESES.items():
        if re.search(rf"\b{nombre}\b", t):
            anio = hoy.year if mes <= hoy.month else hoy.year - 1
            return date(anio, mes, 1), min(_fin_de_mes(anio, mes), hoy)
    return None, None


def _buscar_valores(t: str, valores: dict[str, str]) -> list[str]:
    """Los ids cuyo nombre aparece en la frase («sucursal centro» → Centro)."""
    encontrados = []
    for id_, nombre in valores.items():
        n = _normal(nombre)
        if len(n) >= 3 and re.search(rf"\b{re.escape(n)}\b", t):
            encontrados.append(id_)
    return encontrados


def interpretar(texto: str, vocabulario: dict, hoy: date) -> dict | None:
    t = _normal(texto)
    valores = vocabulario.get("valores", {})

    # --- medida
    if re.search(r"devol|devuel", t):
        medida = "unidades_devueltas" if "unidades" in t or "prendas" in t else "devoluciones_monto"
    elif re.search(r"existencia|stock|inventario|reponer", t):
        medida = "existencias"
    elif "reserva" in t:
        medida = "reservas"
    elif "ticket" in t or "promedio" in t:
        medida = "ticket_promedio"
    elif re.search(r"mas vendid|menos vendid|unidades|prendas vendidas", t):
        medida = "unidades_vendidas"
    elif re.search(r"cuantas ventas|cantidad de ventas|numero de ventas", t):
        medida = "cantidad_ventas"
    elif re.search(r"venta|vend|ingres|factur|recaud", t):
        medida = "ventas_monto"
    else:
        return None
    admitidas = vocabulario["medidas"][medida]["dimensiones"]

    # --- agrupar
    agrupar: list[str] = []
    for patron, dimension in (
        (r"\bpor dia\b|diari", "dia"), (r"\bpor semana\b|semanal", "semana"),
        (r"\bpor mes\b|mensual", "mes"),
    ):
        if re.search(patron, t):
            agrupar.append(dimension)
            break
    if re.search(r"compar\w*.*sucursales", t) and not agrupar:
        agrupar.append("mes")
    for patron, dimension in (
        (r"sucursal", "sucursal"), (r"categori", "categoria"),
        (r"producto|mas vendid|menos vendid|menor existencia|mayor existencia", "producto"),
        (r"\btalla", "talla"), (r"\bcolor", "color"), (r"temporada", "temporada"),
        (r"\bcanal", "canal"), (r"metodo de pago|forma de pago", "metodo_pago"),
        (r"\bestado", "estado"), (r"\btipo", "tipo"),
    ):
        if re.search(patron, t) and dimension in admitidas and dimension not in agrupar:
            # «de la sucursal Centro» es un filtro, no una agrupación.
            if dimension == "sucursal" and _buscar_valores(t, valores.get("sucursal", {})) \
                    and not re.search(r"por sucursal|sucursales", t):
                continue
            agrupar.append(dimension)
        if len(agrupar) == 2:
            break
    agrupar = [d for d in agrupar if d in admitidas]

    # --- filtros
    filtros: dict[str, object] = {}
    for campo in ("sucursal", "categoria", "producto", "temporada"):
        if campo in vocabulario["medidas"][medida]["filtros"]:
            ids = _buscar_valores(t, valores.get(campo, {}))
            if ids and campo not in agrupar:
                filtros[campo] = ids
    if re.search(r"en linea|online|web|digital", t):
        filtros["canal"] = "DIGITAL"
    elif re.search(r"presencial|en tienda|mostrador", t):
        filtros["canal"] = "PRESENCIAL"
    if "cambio" in t and medida.startswith(("devoluciones", "unidades_dev")):
        filtros["tipo"] = "CAMBIO"
    if re.search(r"reponer|bajo (el )?minimo", t):
        filtros["bajo_minimo"] = True

    # --- orden, límite, gráfico
    orden = "asc" if re.search(r"\bmenor|\bmenos\b|peor", t) else "desc"
    limite = None
    m = re.search(r"\b(?:los|las|top)\s+(\w+)\b", t)
    if m and (n := _numero(m.group(1))) and n > 1:
        limite = n
    if "torta" in t or "porcentaje" in t or "pastel" in t:
        grafico = "torta"
    elif "tabla" in t and "grafic" not in t:
        grafico = "tabla"
    elif any(d in agrupar for d in ("dia", "semana", "mes")):
        grafico = "lineas"
    else:
        grafico = "barras"

    desde, hasta = _periodo(t, hoy)
    etiqueta = vocabulario["medidas"][medida]["etiqueta"].split(" (")[0]
    resumen = etiqueta + (" por " + " y ".join(agrupar) if agrupar else "")
    return {
        "entendido": True,
        "medida": medida,
        "agrupar": agrupar,
        "filtros": filtros,
        "desde": desde.isoformat() if desde else None,
        "hasta": hasta.isoformat() if hasta else None,
        "orden": orden,
        "limite": limite,
        "grafico": grafico,
        "resumen": resumen,
    }
