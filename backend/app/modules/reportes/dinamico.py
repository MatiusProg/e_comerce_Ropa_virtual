"""
P11 - Reportes / CU-27 Generar reporte con IA por texto o voz  |  capa: motor

El reporte que se ARMA según lo que se pidió, en vez de elegirse de una lista.

QUÉ CAMBIA RESPECTO DEL PEDIDO POR VOZ DEL 1ER PARCIAL
-----------------------------------------------------
El de CU-35 elegía uno de los siete reportes fijos. El enunciado del 2do parcial
pide más: «ventas de septiembre agrupadas por sucursal», «gráfico de ventas por
semana», «compará las sucursales en los últimos tres meses». Ninguno de esos es
un reporte fijo: es una MEDIDA, agrupada por una o dos DIMENSIONES, con FILTROS
y un PERÍODO. Este módulo es eso.

LA IA NO ESCRIBE SQL (enunciado, 8.4 «Seguridad»)
------------------------------------------------
El modelo devuelve una `Especificacion` en JSON —qué medida, por qué agrupar,
qué filtros— y este módulo la valida contra una LISTA BLANCA antes de tocar la
base:

  - la medida tiene que estar en `MEDIDAS`;
  - cada dimensión, en las que ESA medida admite;
  - cada filtro, en los suyos, y cada id tiene que existir en la empresa;
  - el límite va de 1 a 200.

Lo que no pasa se descarta o se rechaza con un motivo. La consulta la arma
SIEMPRE este código con SQLAlchemy, con parámetros: no hay texto del modelo que
llegue a la base. Y el aislamiento entre empresas lo pone RLS, igual que en
cualquier otra consulta (CU-01): aunque el modelo nombrara un id de otra
empresa, la fila no se ve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Callable

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.catalogo.models import (
    Categoria,
    Color,
    Producto,
    Talla,
    Temporada,
    VarianteProducto,
)
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Sucursal
from app.modules.reservas.models import DetalleReserva, Reserva
from app.modules.ventas.models import (
    Caja,
    DetalleDevolucion,
    DetalleVenta,
    Devolucion,
    TurnoCaja,
    Venta,
)

ZONA = "America/La_Paz"
VENDIDAS = ("PAGADA", "ENTREGADA")
LIMITE_MAXIMO = 200
#: Con dos dimensiones el gráfico dibuja una serie por valor de la segunda;
#: más de ocho líneas ya no se leen.
SERIES_MAXIMAS = 8
GRAFICOS = ("barras", "lineas", "torta", "tabla")


class ErrorDeEspecificacion(Exception):
    """El pedido no se puede armar. El mensaje es para el usuario."""


# --- El vocabulario -----------------------------------------------------------


@dataclass(frozen=True)
class Dimension:
    clave: str
    etiqueta: str
    #: Si es de tiempo, el gráfico la pone en el eje X y prefiere líneas.
    temporal: bool = False


DIMENSIONES: dict[str, Dimension] = {
    d.clave: d
    for d in (
        Dimension("sucursal", "Sucursal"),
        Dimension("categoria", "Categoría"),
        Dimension("producto", "Producto"),
        Dimension("talla", "Talla"),
        Dimension("color", "Color"),
        Dimension("temporada", "Temporada"),
        Dimension("canal", "Canal"),
        Dimension("metodo_pago", "Método de pago"),
        Dimension("tipo", "Tipo"),
        Dimension("estado", "Estado"),
        Dimension("dia", "Día", temporal=True),
        Dimension("semana", "Semana", temporal=True),
        Dimension("mes", "Mes", temporal=True),
    )
}

#: Los filtros por id: se validan contra la base antes de usarse.
FILTROS_POR_ID = ("sucursal", "categoria", "producto", "temporada")
#: Los filtros por valor fijo, con sus valores admitidos.
FILTROS_POR_VALOR: dict[str, tuple[str, ...]] = {
    "canal": ("PRESENCIAL", "DIGITAL"),
    "tipo": ("DEVOLUCION", "CAMBIO"),
}


@dataclass(frozen=True)
class Medida:
    clave: str
    etiqueta: str
    #: De qué hecho sale: arma el FROM con sus joins y devuelve las columnas
    #: que las dimensiones y los filtros necesitan.
    hecho: str
    usa_periodo: bool = True
    es_dinero: bool = False
    dimensiones: tuple[str, ...] = ()
    filtros: tuple[str, ...] = ()


_DIM_VENTA = ("sucursal", "categoria", "producto", "talla", "color", "temporada",
              "canal", "metodo_pago", "dia", "semana", "mes")
_FIL_VENTA = ("sucursal", "categoria", "producto", "temporada", "canal")
_DIM_DEV = ("sucursal", "categoria", "producto", "talla", "color", "tipo", "dia",
            "semana", "mes")
_FIL_DEV = ("sucursal", "categoria", "producto", "tipo")
_DIM_STOCK = ("sucursal", "categoria", "producto", "talla", "color", "temporada")
_FIL_STOCK = ("sucursal", "categoria", "producto", "temporada", "bajo_minimo")
_DIM_RES = ("sucursal", "categoria", "producto", "estado", "dia", "semana", "mes")
_FIL_RES = ("sucursal", "categoria", "producto")

MEDIDAS: dict[str, Medida] = {
    m.clave: m
    for m in (
        Medida("ventas_monto", "Monto vendido (Bs)", "venta", es_dinero=True,
               dimensiones=_DIM_VENTA, filtros=_FIL_VENTA),
        Medida("unidades_vendidas", "Unidades vendidas", "venta",
               dimensiones=_DIM_VENTA, filtros=_FIL_VENTA),
        Medida("cantidad_ventas", "Cantidad de ventas", "venta",
               dimensiones=_DIM_VENTA, filtros=_FIL_VENTA),
        Medida("ticket_promedio", "Ticket promedio (Bs)", "venta", es_dinero=True,
               dimensiones=_DIM_VENTA, filtros=_FIL_VENTA),
        Medida("devoluciones_monto", "Valor devuelto (Bs)", "devolucion", es_dinero=True,
               dimensiones=_DIM_DEV, filtros=_FIL_DEV),
        Medida("unidades_devueltas", "Unidades devueltas", "devolucion",
               dimensiones=_DIM_DEV, filtros=_FIL_DEV),
        Medida("existencias", "Existencias disponibles", "existencia", usa_periodo=False,
               dimensiones=_DIM_STOCK, filtros=_FIL_STOCK),
        Medida("reservas", "Reservas", "reserva",
               dimensiones=_DIM_RES, filtros=_FIL_RES),
    )
}


# --- La especificación ----------------------------------------------------------


@dataclass
class Especificacion:
    """Lo que se pidió, ya validado. Es lo único que llega a la consulta."""

    medida: str
    agrupar: list[str] = field(default_factory=list)
    filtros: dict[str, object] = field(default_factory=dict)
    desde: date | None = None
    hasta: date | None = None
    orden: str = "desc"
    limite: int | None = None
    grafico: str = "barras"
    resumen: str = ""

    def a_dict(self) -> dict:
        return {
            "medida": self.medida,
            "agrupar": list(self.agrupar),
            "filtros": dict(self.filtros),
            "desde": self.desde.isoformat() if self.desde else None,
            "hasta": self.hasta.isoformat() if self.hasta else None,
            "orden": self.orden,
            "limite": self.limite,
            "grafico": self.grafico,
            "resumen": self.resumen,
        }


def _fecha(valor) -> date | None:
    if isinstance(valor, date):
        return valor
    if not isinstance(valor, str) or not valor.strip():
        return None
    try:
        return date.fromisoformat(valor.strip()[:10])
    except ValueError:
        return None


def _ids(valor) -> list[int]:
    if valor in (None, "", []):
        return []
    lista = valor if isinstance(valor, list) else [valor]
    salida = []
    for v in lista:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n > 0 and n not in salida:
            salida.append(n)
    return salida[:20]


_TABLA_DE_FILTRO = {
    "sucursal": Sucursal,
    "categoria": Categoria,
    "producto": Producto,
    "temporada": Temporada,
}


def validar(db: Session, crudo: dict) -> Especificacion:
    """De lo que devolvió el modelo (o la pantalla) a una especificación segura.

    Lo que no se reconoce se descarta en silencio cuando es accesorio (un
    gráfico raro, un límite fuera de rango) y se rechaza con motivo cuando
    cambia el sentido del reporte (una medida desconocida, un id que no es de
    la empresa).
    """
    if not isinstance(crudo, dict):
        raise ErrorDeEspecificacion("El pedido no tiene la forma esperada.")

    medida = MEDIDAS.get(str(crudo.get("medida") or ""))
    if medida is None:
        raise ErrorDeEspecificacion(
            "No sé calcular eso. Puedo informar ventas (monto, unidades, cantidad o "
            "ticket promedio), devoluciones, existencias y reservas."
        )

    agrupar: list[str] = []
    for d in crudo.get("agrupar") or []:
        d = str(d)
        if d not in medida.dimensiones:
            raise ErrorDeEspecificacion(
                f"«{medida.etiqueta}» no se puede agrupar por «{d}». "
                f"Se puede por: {', '.join(DIMENSIONES[x].etiqueta.lower() for x in medida.dimensiones)}."
            )
        if d not in agrupar:
            agrupar.append(d)
    if len(agrupar) > 2:
        raise ErrorDeEspecificacion("Se puede agrupar por dos criterios como máximo.")
    if sum(DIMENSIONES[d].temporal for d in agrupar) > 1:
        raise ErrorDeEspecificacion("Elija una sola escala de tiempo: día, semana o mes.")

    filtros: dict[str, object] = {}
    for campo, valor in (crudo.get("filtros") or {}).items():
        if campo not in medida.filtros:
            continue  # un filtro que esta medida no admite no cambia nada
        if campo in FILTROS_POR_ID:
            ids = _ids(valor)
            if not ids:
                continue
            tabla = _TABLA_DE_FILTRO[campo]
            # RLS deja ver solo los de la empresa: un id ajeno no aparece.
            existentes = set(db.scalars(select(tabla.id).where(tabla.id.in_(ids))))
            faltan = [i for i in ids if i not in existentes]
            if faltan:
                raise ErrorDeEspecificacion(
                    f"No encontré {campo} con id {', '.join(map(str, faltan))} en su empresa."
                )
            filtros[campo] = ids
        elif campo in FILTROS_POR_VALOR:
            v = str(valor or "").upper()
            if v in FILTROS_POR_VALOR[campo]:
                filtros[campo] = v
        elif campo == "bajo_minimo":
            if valor in (True, "true", "si", "sí", 1, "1"):
                filtros[campo] = True

    desde = hasta = None
    if medida.usa_periodo:
        desde, hasta = _fecha(crudo.get("desde")), _fecha(crudo.get("hasta"))
        hoy = tiempo.hoy()
        if hasta is None or hasta > hoy:
            hasta = hoy
        if desde is None:
            desde = hasta - timedelta(days=29)
        if desde > hasta:
            desde, hasta = hasta, desde

    orden = "asc" if str(crudo.get("orden") or "").lower() == "asc" else "desc"

    limite = crudo.get("limite")
    try:
        limite = int(limite) if limite not in (None, "") else None
    except (TypeError, ValueError):
        limite = None
    if limite is not None:
        limite = max(1, min(LIMITE_MAXIMO, limite))

    grafico = str(crudo.get("grafico") or "").lower()
    if grafico not in GRAFICOS:
        grafico = "lineas" if any(DIMENSIONES[d].temporal for d in agrupar) else "barras"
    if not agrupar:
        grafico = "tabla"
    if grafico == "torta" and len(agrupar) > 1:
        grafico = "barras"

    return Especificacion(
        medida=medida.clave,
        agrupar=agrupar,
        filtros=filtros,
        desde=desde,
        hasta=hasta,
        orden=orden,
        limite=limite,
        grafico=grafico,
        resumen=str(crudo.get("resumen") or "")[:160],
    )


# --- La consulta -------------------------------------------------------------------


@dataclass
class _Hecho:
    """El FROM de una familia de medidas y sus columnas con nombre."""

    consulta: Select
    columnas: dict[str, object]
    fecha: object | None


def _con_producto(consulta: Select, variante_col) -> Select:
    return (
        consulta.join(VarianteProducto, VarianteProducto.id == variante_col)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Categoria, Categoria.id == Producto.categoria_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .outerjoin(Temporada, Temporada.id == Producto.temporada_id)
    )


def _columnas_de_producto() -> dict[str, object]:
    return {
        "categoria": (Categoria.id, Categoria.nombre),
        "producto": (Producto.id, Producto.nombre),
        "talla": (Talla.id, Talla.codigo),
        "color": (Color.id, Color.nombre),
        "temporada": (Temporada.id, func.coalesce(Temporada.nombre, "Sin temporada")),
    }


def _hecho_venta() -> _Hecho:
    base = select().select_from(DetalleVenta).join(Venta, Venta.id == DetalleVenta.venta_id)
    base = _con_producto(base, DetalleVenta.variante_id)
    base = base.join(Sucursal, Sucursal.id == Venta.sucursal_id).where(Venta.estado.in_(VENDIDAS))
    columnas = {
        "sucursal": (Sucursal.id, Sucursal.nombre),
        "canal": (Venta.canal, Venta.canal),
        "metodo_pago": (Venta.metodo_pago, func.coalesce(Venta.metodo_pago, "—")),
        **_columnas_de_producto(),
    }
    return _Hecho(base, columnas, Venta.creado_en)


def _hecho_devolucion() -> _Hecho:
    base = (
        select()
        .select_from(DetalleDevolucion)
        .join(Devolucion, Devolucion.id == DetalleDevolucion.devolucion_id)
        .join(Venta, Venta.id == Devolucion.venta_id)
        .join(
            DetalleVenta,
            (DetalleVenta.venta_id == Devolucion.venta_id)
            & (DetalleVenta.variante_id == DetalleDevolucion.variante_id),
        )
    )
    base = _con_producto(base, DetalleDevolucion.variante_id)
    # Igual que el reporte fijo: la sucursal es donde volvió (la caja), y si
    # fue por la web (CU-25, sin turno), la del pedido.
    base = (
        base.outerjoin(TurnoCaja, TurnoCaja.id == Devolucion.turno_caja_id)
        .outerjoin(Caja, Caja.id == TurnoCaja.caja_id)
        .join(Sucursal, Sucursal.id == func.coalesce(Caja.sucursal_id, Venta.sucursal_id))
    )
    columnas = {
        "sucursal": (Sucursal.id, Sucursal.nombre),
        "tipo": (Devolucion.tipo, Devolucion.tipo),
        **_columnas_de_producto(),
    }
    return _Hecho(base, columnas, Devolucion.creado_en)


def _hecho_existencia() -> _Hecho:
    base = select().select_from(Existencia)
    base = _con_producto(base, Existencia.variante_id)
    base = base.join(Sucursal, Sucursal.id == Existencia.sucursal_id)
    columnas = {"sucursal": (Sucursal.id, Sucursal.nombre), **_columnas_de_producto()}
    return _Hecho(base, columnas, None)


def _hecho_reserva() -> _Hecho:
    base = (
        select()
        .select_from(DetalleReserva)
        .join(Reserva, Reserva.id == DetalleReserva.reserva_id)
    )
    base = _con_producto(base, DetalleReserva.variante_id)
    base = base.join(Sucursal, Sucursal.id == Reserva.sucursal_id)
    columnas = {
        "sucursal": (Sucursal.id, Sucursal.nombre),
        "estado": (Reserva.estado, Reserva.estado),
        **_columnas_de_producto(),
    }
    return _Hecho(base, columnas, Reserva.creado_en)


_HECHOS: dict[str, Callable[[], _Hecho]] = {
    "venta": _hecho_venta,
    "devolucion": _hecho_devolucion,
    "existencia": _hecho_existencia,
    "reserva": _hecho_reserva,
}


def _valor_de_medida(clave: str):
    subtotal = DetalleVenta.cantidad * (
        DetalleVenta.precio_unitario - DetalleVenta.descuento_unitario
    )
    if clave == "ventas_monto":
        return func.coalesce(func.sum(subtotal), 0)
    if clave == "unidades_vendidas":
        return func.coalesce(func.sum(DetalleVenta.cantidad), 0)
    if clave == "cantidad_ventas":
        return func.count(distinct(Venta.id))
    if clave == "ticket_promedio":
        return func.coalesce(func.sum(subtotal), 0) / func.nullif(func.count(distinct(Venta.id)), 0)
    if clave == "devoluciones_monto":
        return func.coalesce(
            func.sum(
                DetalleDevolucion.cantidad
                * (DetalleVenta.precio_unitario - DetalleVenta.descuento_unitario)
            ),
            0,
        )
    if clave == "unidades_devueltas":
        return func.coalesce(func.sum(DetalleDevolucion.cantidad), 0)
    if clave == "existencias":
        return func.coalesce(func.sum(Existencia.cantidad_disponible), 0)
    if clave == "reservas":
        return func.count(distinct(Reserva.id))
    raise ErrorDeEspecificacion("Medida desconocida.")


_TRUNC = {"dia": "day", "semana": "week", "mes": "month"}


@dataclass
class Resultado:
    titulo: str
    subtitulos: list[str]
    encabezados: list[str]
    filas: list[list[object]]
    total: list[object] | None
    grafico: dict
    narrativa: str
    especificacion: dict


def _etiqueta_de_tiempo(dimension: str, valor) -> str:
    if valor is None:
        return "—"
    dia = valor.date() if isinstance(valor, datetime) else valor
    if dimension == "mes":
        meses = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep",
                 "oct", "nov", "dic")
        return f"{meses[dia.month - 1]} {dia.year}"
    if dimension == "semana":
        return f"Sem. del {dia.strftime('%d/%m')}"
    return dia.strftime("%d/%m/%Y")


_NOMBRES_DE_CODIGO = {
    "PRESENCIAL": "Presencial",
    "DIGITAL": "En línea",
    "DEVOLUCION": "Devolución",
    "CAMBIO": "Cambio",
}


def _numero(valor) -> float | int:
    if isinstance(valor, Decimal):
        return round(float(valor), 2)
    if isinstance(valor, float):
        return round(valor, 2)
    return int(valor or 0)


def ejecutar(db: Session, espec: Especificacion, *, sucursal_forzada: int | None) -> Resultado:
    """Corre la especificación. `sucursal_forzada` es la del encargado."""
    medida = MEDIDAS[espec.medida]
    hecho = _HECHOS[medida.hecho]()
    valor = _valor_de_medida(medida.clave).label("valor")

    seleccion = []
    agrupacion = []
    for d in espec.agrupar:
        if DIMENSIONES[d].temporal:
            col = func.date_trunc(_TRUNC[d], func.timezone(ZONA, hecho.fecha)).label(d)
            seleccion.append(col)
            agrupacion.append(col)
        else:
            clave, nombre = hecho.columnas[d]
            seleccion.append(nombre.label(d))
            agrupacion.extend([clave, nombre] if clave is not nombre else [nombre])
    consulta = hecho.consulta.add_columns(*seleccion, valor)
    if agrupacion:
        consulta = consulta.group_by(*agrupacion)

    # --- filtros
    sucursales = espec.filtros.get("sucursal")
    if sucursal_forzada is not None:
        sucursales = [sucursal_forzada]
    if sucursales:
        consulta = consulta.where(Sucursal.id.in_(sucursales))
    for campo, columna in (("categoria", Categoria.id), ("producto", Producto.id),
                           ("temporada", Temporada.id)):
        if espec.filtros.get(campo):
            consulta = consulta.where(columna.in_(espec.filtros[campo]))
    if espec.filtros.get("canal"):
        consulta = consulta.where(Venta.canal == espec.filtros["canal"])
    if espec.filtros.get("tipo"):
        consulta = consulta.where(Devolucion.tipo == espec.filtros["tipo"])
    if espec.filtros.get("bajo_minimo"):
        consulta = consulta.where(Existencia.cantidad_disponible <= Existencia.stock_minimo)
    if medida.usa_periodo and hecho.fecha is not None and espec.desde and espec.hasta:
        inicio = datetime.combine(espec.desde, datetime.min.time(), tiempo.BOLIVIA)
        fin = datetime.combine(espec.hasta + timedelta(days=1), datetime.min.time(),
                               tiempo.BOLIVIA)
        consulta = consulta.where(hecho.fecha >= inicio, hecho.fecha < fin)

    # --- orden: el tiempo va en orden cronológico; lo demás, por el valor
    temporal = next((d for d in espec.agrupar if DIMENSIONES[d].temporal), None)
    if temporal:
        consulta = consulta.order_by(seleccion[espec.agrupar.index(temporal)])
    else:
        consulta = consulta.order_by(valor.asc() if espec.orden == "asc" else valor.desc())
    limite = espec.limite or (LIMITE_MAXIMO if espec.agrupar else None)
    if limite and not temporal:
        consulta = consulta.limit(limite)

    filas_crudas = db.execute(consulta).all()

    filas: list[list[object]] = []
    for f in filas_crudas:
        fila: list[object] = []
        for i, d in enumerate(espec.agrupar):
            v = f[i]
            if DIMENSIONES[d].temporal:
                fila.append(_etiqueta_de_tiempo(d, v))
            else:
                fila.append(_NOMBRES_DE_CODIGO.get(v, v) if isinstance(v, str) else (v or "—"))
        fila.append(_numero(f[-1]))
        filas.append(fila)

    encabezados = [DIMENSIONES[d].etiqueta for d in espec.agrupar] + [medida.etiqueta]
    total = None
    if espec.agrupar and medida.clave != "ticket_promedio" and filas:
        suma = sum(f[-1] for f in filas)
        total = ["Total"] + [""] * (len(espec.agrupar) - 1) + [_numero(suma)]

    subtitulos = []
    if medida.usa_periodo and espec.desde:
        subtitulos.append(
            f"Período: {espec.desde.strftime('%d/%m/%Y')} al {espec.hasta.strftime('%d/%m/%Y')}"
        )
    else:
        subtitulos.append(f"Situación al {tiempo.hoy().strftime('%d/%m/%Y')}")
    subtitulos.extend(_describir_filtros(db, espec, sucursal_forzada))

    titulo = medida.etiqueta.split(" (")[0]
    if espec.agrupar:
        titulo += " por " + " y ".join(DIMENSIONES[d].etiqueta.lower() for d in espec.agrupar)

    return Resultado(
        titulo=titulo,
        subtitulos=subtitulos,
        encabezados=encabezados,
        filas=filas,
        total=total,
        grafico=_grafico(espec, filas, medida),
        narrativa=_narrar(espec, filas, medida),
        especificacion=espec.a_dict(),
    )


def _describir_filtros(db: Session, espec: Especificacion, forzada: int | None) -> list[str]:
    lineas = []
    for campo in FILTROS_POR_ID:
        ids = [forzada] if campo == "sucursal" and forzada else espec.filtros.get(campo)
        if not ids:
            continue
        tabla = _TABLA_DE_FILTRO[campo]
        nombres = list(db.scalars(select(tabla.nombre).where(tabla.id.in_(ids))))
        lineas.append(f"{campo.capitalize()}: {', '.join(nombres)}")
    for campo in FILTROS_POR_VALOR:
        if espec.filtros.get(campo):
            lineas.append(f"{campo.capitalize()}: {_NOMBRES_DE_CODIGO.get(espec.filtros[campo])}")
    if espec.filtros.get("bajo_minimo"):
        lineas.append("Solo lo que está en o bajo el stock mínimo")
    return lineas


def _grafico(espec: Especificacion, filas: list[list[object]], medida: Medida) -> dict:
    """Lo que la pantalla necesita para dibujar, sin saber de reportes."""
    if not espec.agrupar or espec.grafico == "tabla" or not filas:
        return {"tipo": "tabla", "etiquetas": [], "series": []}
    if len(espec.agrupar) == 1:
        return {
            "tipo": espec.grafico,
            "etiquetas": [str(f[0]) for f in filas],
            "series": [{"nombre": medida.etiqueta, "datos": [f[1] for f in filas]}],
        }
    # Dos dimensiones: el eje X es la temporal si la hay; la otra hace series.
    temporal_primero = DIMENSIONES[espec.agrupar[1]].temporal
    x_i, s_i = (1, 0) if temporal_primero else (0, 1)
    etiquetas: list[str] = []
    for f in filas:
        if str(f[x_i]) not in etiquetas:
            etiquetas.append(str(f[x_i]))
    # Las series más grandes primero; el resto se suma en «Otros».
    totales: dict[str, float] = {}
    for f in filas:
        totales[str(f[s_i])] = totales.get(str(f[s_i]), 0) + f[2]
    nombres = sorted(totales, key=lambda n: -totales[n])
    principales = nombres[:SERIES_MAXIMAS]
    series = {n: [0] * len(etiquetas) for n in principales}
    if len(nombres) > SERIES_MAXIMAS:
        series["Otros"] = [0] * len(etiquetas)
    for f in filas:
        n = str(f[s_i]) if str(f[s_i]) in series else "Otros"
        series[n][etiquetas.index(str(f[x_i]))] += f[2]
    return {
        "tipo": espec.grafico,
        "etiquetas": etiquetas,
        "series": [{"nombre": n, "datos": [_numero(v) for v in d]} for n, d in series.items()],
    }


def _bs(valor: float, dinero: bool) -> str:
    texto = f"{valor:,.2f}" if dinero else f"{valor:,.0f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Bs {texto}" if dinero else texto


def _narrar(espec: Especificacion, filas: list[list[object]], medida: Medida) -> str:
    """Una lectura en castellano de lo que muestran los números.

    SALE DE LOS DATOS, NO DEL MODELO. La narrativa la escribe este código a
    partir de las filas: un modelo que «resume» puede inventar una cifra, y
    una cifra inventada en un reporte de gestión es peor que no tener texto.
    """
    if not filas:
        return "No hay datos para lo que se pidió en ese período."
    dinero = medida.es_dinero
    nombre = medida.etiqueta.split(" (")[0].lower()
    if not espec.agrupar:
        return f"{medida.etiqueta.split(' (')[0]}: {_bs(filas[0][-1], dinero)}."
    if len(espec.agrupar) == 1 and DIMENSIONES[espec.agrupar[0]].temporal:
        valores = [f[1] for f in filas]
        mayor = max(filas, key=lambda f: f[1])
        texto = (f"El punto más alto de {nombre} fue {mayor[0]} con {_bs(mayor[1], dinero)}.")
        if len(valores) >= 2 and valores[0]:
            cambio = (valores[-1] - valores[0]) / valores[0] * 100
            sentido = "subió" if cambio >= 0 else "bajó"
            texto += f" Entre el primer y el último período {sentido} un {abs(cambio):.0f}%."
        return texto
    if len(espec.agrupar) == 1:
        primero = filas[0]
        texto = f"{'El menor' if espec.orden == 'asc' else 'El primero'} es {primero[0]} con {_bs(primero[1], dinero)}"
        total = sum(f[1] for f in filas)
        if total and medida.clave != "ticket_promedio" and espec.orden != "asc":
            texto += f", el {primero[1] / total * 100:.0f}% de lo listado"
        texto += f". Se listan {len(filas)} resultados."
        return texto
    return (f"Se comparan {len({f[0] for f in filas})} valores de "
            f"{DIMENSIONES[espec.agrupar[0]].etiqueta.lower()} a lo largo de "
            f"{len({f[1] for f in filas})} de {DIMENSIONES[espec.agrupar[1]].etiqueta.lower()}.")


# --- Lo que se le describe al modelo -------------------------------------------------


def vocabulario(db: Session, *, sucursal_forzada: int | None) -> dict:
    """Las medidas, dimensiones y los valores de filtro, con sus nombres.

    Se resuelve en CADA pedido y solo con filas activas (regla del 20/09): el
    modelo recibe el par id → nombre para poder traducir «sucursal Centro» al
    id, y nada más de la base.
    """
    def pares(tabla, activo=True):
        consulta = select(tabla.id, tabla.nombre).order_by(tabla.nombre)
        bandera = getattr(tabla, "activo", None) or getattr(tabla, "activa", None)
        if activo and bandera is not None:
            consulta = consulta.where(bandera.is_(True))
        return {str(i): n for i, n in db.execute(consulta.limit(300)).all()}

    sucursales = pares(Sucursal)
    if sucursal_forzada is not None:
        sucursales = {k: v for k, v in sucursales.items() if k == str(sucursal_forzada)}
    return {
        "medidas": {
            m.clave: {
                "etiqueta": m.etiqueta,
                "dimensiones": list(m.dimensiones),
                "filtros": list(m.filtros),
                "usa_periodo": m.usa_periodo,
            }
            for m in MEDIDAS.values()
        },
        "valores": {
            "sucursal": sucursales,
            "categoria": pares(Categoria),
            "producto": pares(Producto),
            "temporada": pares(Temporada),
            "canal": {"PRESENCIAL": "en tienda", "DIGITAL": "en línea"},
            "tipo": {"DEVOLUCION": "devolución", "CAMBIO": "cambio"},
        },
    }
