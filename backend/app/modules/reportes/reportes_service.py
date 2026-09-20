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
class Filtro:
    """Un filtro que ESTE reporte admite.

    Se declara aca y la pantalla lo dibuja sola: si manana un reporte acepta
    uno mas, aparece en la interfaz sin tocar el front. Es la misma razon por
    la que `/catalogo` expone las columnas.
    """

    campo: str
    etiqueta: str
    #: `sucursal`, `proveedor` y `temporada` los resuelve el servidor contra
    #: la base; `opciones` trae su lista fija escrita aca.
    origen: str
    opciones: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Definicion:
    titulo: str
    encabezados: list[str]
    consulta: Callable
    #: Indices de las columnas que se suman en la fila de totales.
    sumar: tuple[int, ...] = ()
    #: Si ignora el periodo. El inventario es una foto de ahora.
    sin_periodo: bool = False
    #: Los filtros PROPIOS. La sucursal la tienen todos y se declara aparte.
    filtros: tuple[Filtro, ...] = ()


#: La sucursal la admiten los seis, asi que se declara una sola vez.
_SUCURSAL = Filtro(campo="sucursal_id", etiqueta="Sucursal", origen="sucursal")

REPORTES: dict[str, Definicion] = {
    "ventas": Definicion(
        titulo="Reporte de ventas",
        encabezados=["Código", "Fecha", "Sucursal", "Canal", "Estado", "Pago", "Total"],
        consulta=repo.ventas,
        sumar=(6,),
        filtros=(
            _SUCURSAL,
            Filtro(
                campo="canal",
                etiqueta="Canal",
                origen="opciones",
                opciones=(("DIGITAL", "En linea"), ("PRESENCIAL", "En tienda")),
            ),
            # Solo PAGADA y ENTREGADA: el reporte cuenta las ventas
            # consumadas, y ofrecer «cancelada» prometeria filas que la
            # consulta nunca devuelve.
            Filtro(
                campo="estado",
                etiqueta="Estado",
                origen="opciones",
                opciones=(("PAGADA", "Pagada"), ("ENTREGADA", "Entregada")),
            ),
            Filtro(
                campo="metodo_pago",
                etiqueta="Forma de pago",
                origen="opciones",
                opciones=(
                    ("EFECTIVO", "Efectivo"),
                    ("TARJETA", "Tarjeta"),
                    ("QR", "QR"),
                ),
            ),
        ),
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
        filtros=(
            _SUCURSAL,
            Filtro(
                campo="bajo_minimo",
                etiqueta="Solo lo que hay que reponer",
                origen="opciones",
                opciones=(("si", "Si"),),
            ),
        ),
    ),
    "movimientos": Definicion(
        titulo="Reporte de movimientos de inventario",
        encabezados=[
            "Fecha", "Sucursal", "Tipo", "Prenda", "Talla", "Color",
            "Cantidad", "Usuario",
        ],
        consulta=repo.movimientos,
        sumar=(6,),
        filtros=(
            _SUCURSAL,
            Filtro(
                campo="tipo",
                etiqueta="Tipo",
                origen="opciones",
                opciones=(
                    ("INGRESO", "Ingreso"),
                    ("VENTA", "Venta"),
                    ("RESERVA", "Reserva"),
                    ("LIBERACION", "Liberacion"),
                    ("DEVOLUCION", "Devolucion"),
                    ("TRANSFERENCIA", "Transferencia"),
                    ("AJUSTE", "Ajuste"),
                ),
            ),
        ),
    ),
    "reservas": Definicion(
        titulo="Reporte de reservas",
        encabezados=["N.º", "Franja", "Sucursal", "Estado", "Cliente"],
        consulta=repo.reservas,
        filtros=(
            _SUCURSAL,
            Filtro(
                campo="estado",
                etiqueta="Estado",
                origen="opciones",
                opciones=(
                    ("PENDIENTE", "Pendiente"),
                    ("PREPARADA", "Preparada"),
                    ("ATENDIDA", "Atendida"),
                    ("CANCELADA", "Cancelada"),
                    ("EXPIRADA", "Expirada"),
                ),
            ),
        ),
    ),
    "rendimiento": Definicion(
        titulo="Rendimiento por temporada y colección",
        encabezados=["Temporada", "Colección", "Ventas", "Unidades", "Importe"],
        consulta=repo.rendimiento,
        sumar=(2, 3, 4),
        filtros=(
            _SUCURSAL,
            Filtro(campo="temporada_id", etiqueta="Temporada", origen="temporada"),
        ),
    ),
    "compras": Definicion(
        titulo="Compras por proveedor",
        encabezados=["Proveedor", "Sucursal", "Ingresos", "Unidades"],
        consulta=repo.compras,
        sumar=(2, 3),
        filtros=(
            _SUCURSAL,
            Filtro(campo="proveedor_id", etiqueta="Proveedor", origen="proveedor"),
        ),
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


def opciones_de(db: Session, filtro: Filtro) -> list[dict]:
    """Las opciones de un filtro, resueltas contra la base si hace falta."""
    match filtro.origen:
        case "sucursal":
            pares = repo.opciones_de_sucursal(db)
        case "proveedor":
            pares = repo.opciones_de_proveedor(db)
        case "temporada":
            pares = repo.opciones_de_temporada(db)
        case _:
            pares = list(filtro.opciones)
    return [{"valor": v, "etiqueta": e} for v, e in pares]


def generar(
    db: Session,
    *,
    tipo: str,
    desde: date | None,
    hasta: date | None,
    sucursal_id: int | None,
    extras: dict | None = None,
) -> Tabla:
    definicion = REPORTES.get(tipo)
    if definicion is None:
        raise ErrorDeReporte(
            f"No existe el reporte «{tipo}». Disponibles: "
            + ", ".join(sorted(REPORTES)),
            404,
        )

    # SOLO los filtros que ESTE reporte declara. Un `tipo` mandado al reporte
    # de ventas se descarta en vez de reventar la consulta: la URL la puede
    # escribir cualquiera, y un 500 por un parametro de mas seria culpar a la
    # peticion de algo que el servidor sabe ignorar.
    admitidos = {f.campo for f in definicion.filtros}
    propios = {
        k: v
        for k, v in (extras or {}).items()
        if k in admitidos and v not in (None, "")
    }

    subtitulos = []
    if definicion.sin_periodo:
        filas = definicion.consulta(db, sucursal_id=sucursal_id, **propios)
        subtitulos.append(
            f"Saldos al {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
    else:
        inicio, fin = _rango(desde, hasta)
        filas = definicion.consulta(
            db, desde=inicio, hasta=fin, sucursal_id=sucursal_id, **propios
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

    # LOS FILTROS APLICADOS SE IMPRIMEN. Un reporte de ventas filtrado por
    # «efectivo» que no lo diga es un papel que en una semana nadie sabe por
    # que suma menos que el del tablero.
    por_campo = {f.campo: f for f in definicion.filtros}
    for campo, valor in propios.items():
        if campo == "sucursal_id":
            continue
        filtro = por_campo[campo]
        etiquetas = {v: e for v, e in filtro.opciones}
        subtitulos.append(f"{filtro.etiqueta}: {etiquetas.get(str(valor), valor)}")

    return Tabla(
        titulo=definicion.titulo,
        encabezados=list(definicion.encabezados),
        filas=[list(f) for f in filas],
        subtitulos=subtitulos,
        total=_totales(definicion, filas),
    )


# --- CU-35 · el pedido por voz ---------------------------------------------


def catalogo_para_el_interprete(es_admin: bool) -> list:
    """Los reportes, descritos como el interprete los necesita.

    Se arma del MISMO diccionario `REPORTES` que usa la descarga. No hay una
    lista aparte para el modelo: si la hubiera, el dia que se agregue un
    reporte el interprete seguiria sin conocerlo y diria «no entendi» a un
    pedido perfectamente valido.
    """
    from app.integrations.interprete import ReporteConocido

    salida = []
    for tipo, definicion in sorted(REPORTES.items()):
        filtros: dict[str, list[str]] = {}
        for filtro in definicion.filtros:
            # La sucursal NO se le ofrece al modelo: sus valores son ids de
            # base de datos y nadie dice «sucursal 3» hablando. Ademas al
            # encargado se le fuerza la suya, asi que ni siquiera aplica.
            if filtro.campo == "sucursal_id" or not filtro.opciones:
                continue
            filtros[filtro.campo] = [v for v, _ in filtro.opciones]
        salida.append(
            ReporteConocido(
                tipo=tipo,
                titulo=definicion.titulo,
                filtros=filtros,
                usa_periodo=not definicion.sin_periodo,
            )
        )
    return salida


#: Frases que SI funcionan, para mostrarlas cuando no se entendio.
#:
#: Se escriben aca y no en la pantalla porque dependen de los reportes que
#: existen: si manana se agrega uno, el ejemplo se actualiza donde estan los
#: reportes y no en dos frentes.
EJEMPLOS = (
    "las ventas de este mes en Excel",
    "el inventario de lo que hay que reponer",
    "los movimientos de ingreso de la semana pasada",
    "las reservas atendidas de septiembre en PDF",
    "el rendimiento por temporada del año",
)
