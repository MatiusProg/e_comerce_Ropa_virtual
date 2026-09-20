"""
P11 - Reportes / CU-37  |  capa: servicio

Realiza el **RF36**: exportar los reportes en PDF y Excel. Es lo que vuelve
utilizables fuera del sistema los datos que CU-36 solo muestra en pantalla.

UN CATALOGO DE REPORTES, NO SEIS FUNCIONES SUELTAS
---------------------------------------------------
Cada reporte declara su titulo, sus encabezados, de donde saca las filas y si
lleva una fila de totales. El router no conoce ninguno por nombre: recibe un
tipo, lo busca aca y exporta. Agregar el septimo reporte es una entrada mas en
el diccionario, sin tocar el router ni el exportador.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from app.modules.reportes import reportes_repository as repo
from app.modules.reportes.exportador import Tabla


class ErrorDeReporte(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


@dataclass(frozen=True)
class Definicion:
    titulo: str
    encabezados: list[str]
    consulta: Callable
    #: Indices de las columnas que se suman en la fila de totales.
    sumar: tuple[int, ...] = ()
    #: Si ignora el periodo. El inventario es una foto de ahora.
    sin_periodo: bool = False


REPORTES: dict[str, Definicion] = {
    "ventas": Definicion(
        titulo="Reporte de ventas",
        encabezados=["Código", "Fecha", "Sucursal", "Canal", "Estado", "Pago", "Total"],
        consulta=repo.ventas,
        sumar=(6,),
    ),
    "inventario": Definicion(
        titulo="Reporte de inventario",
        encabezados=[
            "Sucursal", "Código", "Prenda", "Talla", "Color",
            "Disponible", "Reservado", "Mínimo",
        ],
        consulta=repo.inventario,
        sumar=(5, 6),
        sin_periodo=True,
    ),
    "movimientos": Definicion(
        titulo="Reporte de movimientos de inventario",
        encabezados=[
            "Fecha", "Sucursal", "Tipo", "Prenda", "Talla", "Color",
            "Cantidad", "Usuario",
        ],
        consulta=repo.movimientos,
        sumar=(6,),
    ),
    "reservas": Definicion(
        titulo="Reporte de reservas",
        encabezados=["N.º", "Franja", "Sucursal", "Estado", "Cliente"],
        consulta=repo.reservas,
    ),
    "rendimiento": Definicion(
        titulo="Rendimiento por temporada y colección",
        encabezados=["Temporada", "Colección", "Ventas", "Unidades", "Importe"],
        consulta=repo.rendimiento,
        sumar=(2, 3, 4),
    ),
    "compras": Definicion(
        titulo="Compras por proveedor",
        encabezados=["Proveedor", "Sucursal", "Ingresos", "Unidades"],
        consulta=repo.compras,
        sumar=(2, 3),
    ),
}


def _rango(desde: date | None, hasta: date | None) -> tuple[datetime, datetime]:
    """El periodo, en instantes con zona.

    `hasta` es INCLUSIVO para quien pide el reporte: pedir del 1 al 30 tiene
    que incluir el 30 entero. Por dentro se convierte en «< 1 del mes
    siguiente», que es lo unico que funciona con marcas de tiempo --- comparar
    `<= 30` deja fuera todo lo que paso ese dia despues de medianoche, y es el
    defecto clasico de los reportes por fecha.
    """
    hoy = date.today()
    inicio = desde or (hoy - timedelta(days=30))
    fin = hasta or hoy
    if inicio > fin:
        raise ErrorDeReporte("La fecha inicial es posterior a la final.", 422)
    return (
        datetime.combine(inicio, time.min, tzinfo=timezone.utc),
        datetime.combine(fin + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def _totales(definicion: Definicion, filas: list[tuple]) -> list[object] | None:
    if not definicion.sumar or not filas:
        return None
    total: list[object] = [""] * len(definicion.encabezados)
    total[0] = "TOTAL"
    for indice in definicion.sumar:
        acumulado = Decimal(0)
        entero = True
        for fila in filas:
            valor = fila[indice]
            if valor is None:
                continue
            if not isinstance(valor, int):
                entero = False
            acumulado += Decimal(str(valor))
        total[indice] = int(acumulado) if entero else acumulado
    return total


def generar(
    db: Session,
    *,
    tipo: str,
    desde: date | None,
    hasta: date | None,
    sucursal_id: int | None,
) -> Tabla:
    definicion = REPORTES.get(tipo)
    if definicion is None:
        raise ErrorDeReporte(
            f"No existe el reporte «{tipo}». Disponibles: "
            + ", ".join(sorted(REPORTES)),
            404,
        )

    subtitulos = []
    if definicion.sin_periodo:
        filas = definicion.consulta(db, sucursal_id=sucursal_id)
        subtitulos.append(
            f"Saldos al {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
    else:
        inicio, fin = _rango(desde, hasta)
        filas = definicion.consulta(
            db, desde=inicio, hasta=fin, sucursal_id=sucursal_id
        )
        subtitulos.append(
            "Período: "
            f"{inicio.strftime('%d/%m/%Y')} al "
            f"{(fin - timedelta(days=1)).strftime('%d/%m/%Y')}"
        )

    # SIEMPRE se imprime el alcance. Un PDF de ventas sin decir de que
    # sucursal y de que periodo es un papel que no se puede archivar.
    if sucursal_id is not None:
        nombre = repo.nombre_de_sucursal(db, sucursal_id)
        subtitulos.append(f"Sucursal: {nombre or sucursal_id}")
    else:
        subtitulos.append("Sucursal: todas")

    return Tabla(
        titulo=definicion.titulo,
        encabezados=list(definicion.encabezados),
        filas=[list(f) for f in filas],
        subtitulos=subtitulos,
        total=_totales(definicion, filas),
    )
