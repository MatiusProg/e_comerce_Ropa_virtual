"""
P11 - Reportes / CU-37  |  capa: salida (PDF y Excel)

Convierte UNA tabla en un archivo. No sabe nada de ventas, de inventario ni de
la base: recibe titulo, encabezados y filas.

POR QUE UN SOLO EXPORTADOR Y NO UNO POR REPORTE
------------------------------------------------
CU-37 pide seis reportes en dos formatos. Escritos por separado son doce
funciones que dibujan tablas, y **las doce se ven distinto**: una pone el
total en negrita y otra no, una escribe la fecha de una forma y otra de otra.
Peor: arreglar el ancho de una columna hay que hacerlo doce veces.

Aca hay dos funciones. Cada reporte solo decide QUE filas tiene y como se
llaman sus columnas.

LO QUE NO HACE, Y ES A PROPOSITO
---------------------------------
No pagina el PDF por contenido ni agrupa. Un reporte que necesite eso ---por
ejemplo ventas agrupadas por sucursal con subtotales--- se resuelve armando
las filas ya agrupadas, con su fila de subtotal adentro. Meter agrupacion aca
convertiria esto en un motor de informes, que es mucho mas de lo que el caso
de uso pide.
"""

from __future__ import annotations

from app.core import tiempo

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO


@dataclass
class Tabla:
    """Lo que cualquier reporte le entrega al exportador."""

    titulo: str

    #: Los nombres de las columnas, en orden.
    encabezados: list[str]

    #: Las filas. Cada una tiene tantos elementos como encabezados.
    filas: list[list[object]]

    #: Lineas de contexto que van bajo el titulo: el periodo, la sucursal, los
    #: filtros aplicados. **Importa mas de lo que parece**: un PDF de ventas
    #: sin el periodo impreso es un papel que no se puede archivar, porque
    #: dentro de un mes nadie sabe de cuando es.
    subtitulos: list[str] = field(default_factory=list)

    #: Una fila final destacada: totales. Opcional.
    total: list[object] | None = None


def _texto(valor: object) -> str:
    """Como se escribe cada tipo. En UN solo lugar.

    Sin esto, la misma fecha sale `2026-09-19` en un reporte y
    `2026-09-19 22:41:03.512` en otro, y los importes con dos decimales o con
    seis segun de que consulta vengan.
    """
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, Decimal):
        return f"{valor:,.2f}"
    if isinstance(valor, datetime):
        # En hora BOLIVIANA. La base guarda instantes en UTC ---que es lo
        # correcto--- pero un reporte lo lee una persona al lado del reloj de
        # la tienda: sin convertir, una venta de las 21:00 figuraba a la 01:00
        # del dia siguiente. Ver `app/core/tiempo.py`.
        return tiempo.formatear(valor)
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, float):
        return f"{valor:,.2f}"
    return str(valor)


def a_pdf(tabla: Tabla) -> bytes:
    """El reporte como PDF apaisado.

    APAISADO Y NO VERTICAL: estos reportes tienen entre cinco y ocho columnas,
    y en A4 vertical el texto se parte o se sale. Se probo con el de
    movimientos, que es el mas ancho.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    memoria = BytesIO()
    documento = SimpleDocTemplate(
        memoria,
        pagesize=landscape(A4),
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=tabla.titulo,
        author="Violet Boutique",
    )

    estilos = getSampleStyleSheet()
    partes = [Paragraph(tabla.titulo, estilos["Title"])]
    for linea in tabla.subtitulos:
        partes.append(Paragraph(linea, estilos["Normal"]))
    partes.append(Spacer(1, 8 * mm))

    if not tabla.filas:
        # Un reporte vacio NO es un error: puede que en ese periodo no haya
        # pasado nada. Se dice, en vez de entregar una hoja con encabezados
        # sueltos que se lee como que algo fallo.
        partes.append(
            Paragraph(
                "No hay datos para los filtros elegidos.", estilos["Italic"]
            )
        )
    else:
        datos = [tabla.encabezados]
        datos += [[_texto(c) for c in fila] for fila in tabla.filas]
        if tabla.total is not None:
            datos.append([_texto(c) for c in tabla.total])

        cuadro = Table(datos, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8E4A67")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8CBD2")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FBF6F4")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]
        if tabla.total is not None:
            estilo += [
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F6E6EC")),
            ]
        cuadro.setStyle(TableStyle(estilo))
        partes.append(cuadro)

    # `repeatRows=1` de arriba es lo que hace que el encabezado se repita en
    # cada pagina. Sin eso, a partir de la hoja 2 las columnas no se sabe que
    # son --- y estos reportes pasan de una hoja seguido.
    documento.build(partes)
    return memoria.getvalue()


def a_excel(tabla: Tabla) -> bytes:
    """El reporte como hoja de calculo.

    A DIFERENCIA DEL PDF, ACA LOS NUMEROS VAN COMO NUMEROS.
    Es la razon de ser del formato: quien pide el Excel lo pide para sumar,
    filtrar y hacer una tabla dinamica. Si los importes fueran texto
    ---«1.234,56»--- no se podria hacer nada de eso, y el archivo seria un PDF
    con otra extension.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    libro = Workbook()
    hoja = libro.active
    # El nombre de la hoja no admite mas de 31 caracteres ni : \\ / ? * [ ]
    hoja.title = "".join(c for c in tabla.titulo if c not in ':\\/?*[]')[:31]

    fila = 1
    hoja.cell(row=fila, column=1, value=tabla.titulo).font = Font(bold=True, size=14)
    fila += 1
    for linea in tabla.subtitulos:
        hoja.cell(row=fila, column=1, value=linea)
        fila += 1
    fila += 1

    encabezado_fila = fila
    relleno = PatternFill("solid", fgColor="8E4A67")
    for columna, nombre in enumerate(tabla.encabezados, start=1):
        celda = hoja.cell(row=fila, column=columna, value=nombre)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(horizontal="center")
    fila += 1

    def escribir(valores: list[object], negrita: bool = False) -> None:
        nonlocal fila
        for columna, valor in enumerate(valores, start=1):
            # Decimal y los numeros van CRUDOS: es lo que permite sumar.
            if isinstance(valor, Decimal):
                celda = hoja.cell(row=fila, column=columna, value=float(valor))
                celda.number_format = "#,##0.00"
            elif isinstance(valor, (int, float)) and not isinstance(valor, bool):
                celda = hoja.cell(row=fila, column=columna, value=valor)
            elif isinstance(valor, datetime):
                celda = hoja.cell(row=fila, column=columna, value=valor.replace(tzinfo=None))
                celda.number_format = "DD/MM/YYYY HH:MM"
            elif isinstance(valor, date):
                celda = hoja.cell(row=fila, column=columna, value=valor)
                celda.number_format = "DD/MM/YYYY"
            else:
                celda = hoja.cell(row=fila, column=columna, value=_texto(valor))
            if negrita:
                celda.font = Font(bold=True)
        fila += 1

    for datos in tabla.filas:
        escribir(datos)
    if tabla.total is not None:
        escribir(tabla.total, negrita=True)

    # El ancho se estima con el contenido: sin esto todas las columnas salen
    # igual de angostas y los nombres de producto quedan como `####`.
    for columna in range(1, len(tabla.encabezados) + 1):
        ancho = len(str(tabla.encabezados[columna - 1]))
        for datos in tabla.filas[:200]:  # una muestra alcanza y no cuesta
            if columna <= len(datos):
                ancho = max(ancho, len(_texto(datos[columna - 1])))
        hoja.column_dimensions[get_column_letter(columna)].width = min(ancho + 3, 45)

    # Congelar el encabezado y dejar los filtros puestos: quien abre un reporte
    # de 300 filas lo primero que hace es filtrar.
    hoja.freeze_panes = hoja.cell(row=encabezado_fila + 1, column=1)
    hoja.auto_filter.ref = (
        f"A{encabezado_fila}:"
        f"{get_column_letter(len(tabla.encabezados))}{encabezado_fila + len(tabla.filas)}"
    )

    memoria = BytesIO()
    libro.save(memoria)
    return memoria.getvalue()


#: El tipo MIME y la extension de cada formato.
FORMATOS = {
    "pdf": ("application/pdf", "pdf", a_pdf),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx",
        a_excel,
    ),
}
