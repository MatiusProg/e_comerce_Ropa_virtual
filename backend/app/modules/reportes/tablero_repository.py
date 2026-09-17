"""
P11 - Reportes y Tablero / CU-36  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 3
Caso de uso: CU-36 Consultar tablero de indicadores

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit.

POR QUE ESTE PAQUETE SI CONSULTA TABLAS AJENAS, Y CU-14 NO
-----------------------------------------------------------
La regla del Ciclo 2 es que nadie hace SELECT sobre la tabla del otro: por eso
CU-14 pide el consolidado por la costura C1 en vez de leer `existencia`. Aca se
hace distinto, y conviene decir por que antes de que parezca un descuido.

**P11 es, por definicion de la arquitectura, un lector de los demas.** La
seccion 4.1.1 de docs/04-analisis-arquitectura.md lo dice con todas las letras:
«Depende de todos los paquetes transaccionales (P4, P6, P7, P8) en modo de solo
lectura», y esa es justamente la razon por la que se documento como paquete
aparte en lugar de repartir los reportes dentro de cada uno. Un tablero que
pidiera una costura por indicador obligaria a Mateo a escribir una funcion de
agregacion en P6 por cada tarjeta que Karen agregue a la pantalla.

**La linea que si se respeta es otra, y es la que importa: una regla de negocio
ajena no se reimplementa.** De ahi sale el reparto:

- «Que es stock critico» ---umbral mayor que cero y disponible que no lo
  supera--- es una REGLA de P4, escrita en `_bajo_minimo()`. El tablero la pide
  por la costura `inventario.service.alertas_de_stock` y no la copia. Si se
  copiara, el dia que P4 cambie el `<=` por un `<` la pantalla de CU-16 y el
  tablero dirian cosas distintas sobre la misma prenda.
- «Cuantas reservas hay en cada estado» no es una regla, es un COUNT. No hay
  nada que P6 sepa y este archivo no: los estados estan en `ESTADOS_RESERVA`,
  que se importa en vez de escribirse a mano.

Un agregado plano se escribe aca; una regla se pide prestada.

Y todo lo de este archivo es agregacion en SQL, no en memoria: es la diferencia
con CU-14, que pagina en Python porque la costura le entrega el consolidado
entero. Un tablero que contara filas en Python tendria que traerse las reservas
de todo el mes para decir cuantas hay.
"""
from datetime import datetime

from sqlalchemy import Row, Select, and_, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Sucursal
from app.modules.reservas.models import DetalleReserva, Reserva


# --- Ayudas comunes ------------------------------------------------------

def _columnas_de_variante():
    """Las cinco columnas con que se nombra una prenda en toda la aplicacion.

    Mismo juego que `inventario/repository.py::_columnas_de_variante`. Se repite
    la forma, no la regla: es la manera de rotular una variante en la interfaz,
    y ya aparece igual en el consolidado, la disponibilidad y la vitrina.
    """
    return (
        VarianteProducto.id.label("variante_id"),
        VarianteProducto.sku,
        Producto.nombre.label("producto"),
        Talla.codigo.label("talla"),
        Color.nombre.label("color"),
    )


def _unir_variante(consulta: Select) -> Select:
    return (
        consulta.join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
    )


def _del_periodo(desde: datetime, hasta: datetime, sucursal_id: int | None):
    """El filtro que comparten todas las consultas de reservas.

    Se filtra por `creado_en` ---cuando se hizo la reserva--- y no por
    `franja_inicio` ---cuando el cliente iba a venir---. Son fechas distintas y
    la eleccion cambia el numero: una reserva hecha el 30 para el 2 del mes que
    viene cuenta en el mes en que se hizo. El tablero mide la ACTIVIDAD del
    periodo, que es lo que responde «como nos fue esta semana»; medir por franja
    responde otra pregunta ---cuanta gente esperamos--- y esa es la agenda del
    Encargado, que ya existe en CU-24.

    El extremo derecho es `<` y no `<=` porque quien llama pasa el instante
    siguiente al ultimo dia: comparar `<=` contra una medianoche exacta dejaria
    afuera todo lo del ultimo dia salvo lo que caiga justo a las 00:00:00.
    """
    condiciones = [Reserva.creado_en >= desde, Reserva.creado_en < hasta]
    if sucursal_id is not None:
        condiciones.append(Reserva.sucursal_id == sucursal_id)
    return and_(*condiciones)


# --- Reservas (P6) -------------------------------------------------------

def contar_reservas_por_estado(
    db: Session, *, desde: datetime, hasta: datetime, sucursal_id: int | None
) -> dict[str, int]:
    """Cuantas reservas del periodo hay en cada estado.

    Devuelve solo los estados con filas; completar los que faltan con cero es
    del servicio, porque «los cinco estados siempre viajan» es una decision del
    contrato y no de la consulta.
    """
    filas = db.execute(
        select(Reserva.estado, func.count(Reserva.id))
        .where(_del_periodo(desde, hasta, sucursal_id))
        .group_by(Reserva.estado)
    ).all()
    return {estado: cantidad for estado, cantidad in filas}


def contar_lineas_probadas(
    db: Session, *, desde: datetime, hasta: datetime, sucursal_id: int | None
) -> dict[str, int]:
    """Cuantas lineas de reserva terminaron en LLEVA y cuantas en NO_LLEVA.

    Solo cuenta las que tienen resultado escrito, que son las de reservas
    atendidas: CU-24 es lo unico que llena `resultado_prueba`. Las lineas de
    reservas canceladas o expiradas lo tienen en nulo y quedan afuera del
    `GROUP BY` sin necesidad de excluirlas ---pero se excluyen igual, explicito,
    porque depender de que un nulo no agrupe es depender de un detalle del
    motor---.
    """
    filas = db.execute(
        select(DetalleReserva.resultado_prueba, func.count(DetalleReserva.id))
        .join(Reserva, Reserva.id == DetalleReserva.reserva_id)
        .where(
            _del_periodo(desde, hasta, sucursal_id),
            DetalleReserva.resultado_prueba.is_not(None),
        )
        .group_by(DetalleReserva.resultado_prueba)
    ).all()
    return {resultado: cantidad for resultado, cantidad in filas}


def top_variantes_reservadas(
    db: Session,
    *,
    desde: datetime,
    hasta: datetime,
    sucursal_id: int | None,
    limite: int,
) -> list[Row]:
    """Las prendas mas reservadas del periodo, de mas a menos unidades.

    **No cuenta las canceladas ni las expiradas.** Una reserva que el cliente
    anulo a los cinco minutos no dice nada sobre que prenda interesa, y dejarla
    dentro convierte el ranking en un ranking de arrepentimientos. Quedan
    PENDIENTE, PREPARADA y ATENDIDA: las tres son intencion sostenida.

    El desempate es por SKU y no se deja al azar: sin `ORDER BY` estable, dos
    prendas con las mismas unidades se intercambian entre recargas y la pantalla
    parpadea sin que nada haya cambiado.
    """
    # `select_from` explicito: la lista de columnas empieza por `VarianteProducto`
    # y sin esto SQLAlchemy la tomaria como tabla de la izquierda, dejando el
    # primer JOIN sin el `detalle_reserva` del que cuelga.
    consulta = _unir_variante(
        select(
            *_columnas_de_variante(),
            func.sum(DetalleReserva.cantidad).label("unidades"),
            func.count(func.distinct(DetalleReserva.reserva_id)).label("reservas"),
        )
        .select_from(DetalleReserva)
        .join(Reserva, Reserva.id == DetalleReserva.reserva_id)
        .join(VarianteProducto, VarianteProducto.id == DetalleReserva.variante_id)
    ).where(
        _del_periodo(desde, hasta, sucursal_id),
        Reserva.estado.in_(("PENDIENTE", "PREPARADA", "ATENDIDA")),
    )

    return list(
        db.execute(
            consulta.group_by(
                VarianteProducto.id,
                VarianteProducto.sku,
                Producto.nombre,
                Talla.codigo,
                Color.nombre,
            )
            .order_by(
                func.sum(DetalleReserva.cantidad).desc(),
                VarianteProducto.sku,
            )
            .limit(limite)
        ).all()
    )


# --- Inventario (P4) -----------------------------------------------------

def salud_inventario(db: Session, *, sucursal_id: int | None) -> Row:
    """Los saldos sumados de la red, o de una sucursal.

    **Sin filtro de fechas, y no es un olvido.** `existencia` guarda cuanto hay
    ahora, no cuanto hubo: no tiene columna de fecha contra la que filtrar. El
    historico vive en `movimiento_inventario` y es otro caso de uso (CU-15).

    `variantes_sin_stock` cuenta filas (variante, sucursal) en cero disponible,
    no variantes distintas: una prenda agotada en una tienda y con saldo en otra
    cuenta una vez, porque lo que se mide es en cuantos mostradores falta.
    """
    consulta = select(
        func.coalesce(func.sum(Existencia.cantidad_disponible), 0).label(
            "total_disponible"
        ),
        func.coalesce(func.sum(Existencia.cantidad_reservada), 0).label(
            "total_reservado"
        ),
        func.count(Existencia.id)
        .filter(Existencia.cantidad_disponible == 0)
        .label("variantes_sin_stock"),
    )
    if sucursal_id is not None:
        consulta = consulta.where(Existencia.sucursal_id == sucursal_id)
    return db.execute(consulta).one()


# --- Organizacion (P2) ---------------------------------------------------

def nombre_de_sucursal(db: Session, sucursal_id: int) -> str | None:
    """El nombre, para rotular el periodo. Nulo si no existe."""
    return db.scalar(select(Sucursal.nombre).where(Sucursal.id == sucursal_id))
