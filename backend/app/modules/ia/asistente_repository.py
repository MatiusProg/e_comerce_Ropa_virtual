"""
P10 - Inteligencia Artificial / CU-34  |  capa: repositorio

Regla: aqui solo van consultas. Ninguna regla de negocio, ningun commit.

POR QUE CONSULTAS PROPIAS Y NO LAS DE CADA PAQUETE
----------------------------------------------------
Los datos que el asistente necesita ya existen ---el catalogo en P5, los
pedidos en P7, las reservas en P6--- pero cada uno los devuelve con la forma
de SU pantalla: paginados, con imagenes, con colores, con todo lo que hace
falta para dibujar una ficha.

Lo unico que se hace con esto es armar un texto para un prompt. Traer la
ficha completa de cincuenta productos para quedarse con el nombre y el
precio serian cincuenta veces mas datos de los que se usan, y cada campo de
mas es un token que se paga.

Son consultas chicas, de solo lectura, y con el minimo que la pregunta puede
necesitar.

`existencia` sigue sin consultarse desde aqui: entra por la costura C1, igual
que en CU-33.
"""

from __future__ import annotations

from sqlalchemy import Select, and_, exists, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Categoria, Producto, VarianteProducto
from app.modules.reservas.models import Reserva
from app.modules.ventas.models import Venta


def _ofrecible():
    return and_(
        VarianteProducto.producto_id == Producto.id,
        VarianteProducto.activa.is_(True),
    )


def catalogo(db: Session, limite: int = 60) -> list[tuple]:
    """El catalogo publico, comprimido: `(id, nombre, categoria, desde, hasta)`.

    **Solo producto activo con variante activa**, que es exactamente lo que
    la vitrina ofrece: el asistente no puede nombrar algo que el cliente no
    va a encontrar.

    El limite es alto a proposito ---sesenta prendas son unos 1.500 tokens---
    porque partir el catalogo obligaria a adivinar de que va la pregunta
    antes de leerla, que es la ida y vuelta que este caso de uso evita.
    """
    precio_desde = (
        select(func.min(VarianteProducto.precio))
        .where(_ofrecible())
        .correlate(Producto)
        .scalar_subquery()
    )
    precio_hasta = (
        select(func.max(VarianteProducto.precio))
        .where(_ofrecible())
        .correlate(Producto)
        .scalar_subquery()
    )

    consulta: Select = (
        select(
            Producto.id,
            Producto.nombre,
            func.coalesce(Categoria.nombre, "Sin categoría"),
            precio_desde,
            precio_hasta,
        )
        .join(Categoria, Categoria.id == Producto.categoria_id, isouter=True)
        .where(
            Producto.activo.is_(True),
            exists(select(VarianteProducto.id).where(_ofrecible())),
        )
        .order_by(Producto.nombre)
        .limit(limite)
    )
    return [tuple(f) for f in db.execute(consulta).all()]


def colores_de(db: Session, producto_ids: list[int]) -> dict[int, list[str]]:
    """Que colores ofrecibles tiene cada producto.

    Sin esto el asistente no puede contestar «¿la tienen en negro?» ni «¿que
    color combina con esta?», que en una tienda de ropa son dos de las
    preguntas mas frecuentes. Y lo peor: sin la lista, un modelo al que se
    le pregunta por un color **inventa uno plausible**.
    """
    if not producto_ids:
        return {}

    from app.modules.catalogo.models import Color

    filas = db.execute(
        select(VarianteProducto.producto_id, Color.nombre)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(
            VarianteProducto.producto_id.in_(producto_ids),
            VarianteProducto.activa.is_(True),
        )
        .distinct()
        .order_by(VarianteProducto.producto_id, Color.nombre)
    ).all()

    por_producto: dict[int, list[str]] = {}
    for producto_id, nombre in filas:
        por_producto.setdefault(producto_id, []).append(nombre)
    return por_producto


def tabla_de_tallas(db: Session) -> list[tuple]:
    """La equivalencia centimetros <-> talla, GENERAL.

    POR QUE GENERAL Y NO POR PRODUCTO
    -----------------------------------
    `medida_talla` guarda la tabla **por producto**, y con razon: una blusa y
    un pantalon no miden igual en la misma talla. Pero son 185 filas, y
    meterlas todas en el prompt cuesta mas tokens que el catalogo entero.

    Se promedia por codigo de talla y se manda el rango. Con eso el
    asistente contesta «con 100 de busto te va la M» ---que es la pregunta
    real--- y puede aclarar que es orientativo. Para el numero exacto de una
    prenda concreta esta el ajuste de CU-21, que no adivina nada.

    Devuelve `(codigo, orden, busto_min, busto_max, cintura_min,
    cintura_max, cadera_min, cadera_max)`.
    """
    from app.modules.catalogo.models import Talla
    from app.modules.medidas.models import MedidaTalla

    return [
        tuple(f)
        for f in db.execute(
            select(
                Talla.codigo,
                Talla.orden,
                func.min(MedidaTalla.busto_cm),
                func.max(MedidaTalla.busto_cm),
                func.min(MedidaTalla.cintura_cm),
                func.max(MedidaTalla.cintura_cm),
                func.min(MedidaTalla.cadera_cm),
                func.max(MedidaTalla.cadera_cm),
            )
            .join(Talla, Talla.id == MedidaTalla.talla_id)
            .group_by(Talla.codigo, Talla.orden)
            .order_by(Talla.orden)
        ).all()
    ]


def tallas_de(db: Session, producto_ids: list[int]) -> dict[int, list[str]]:
    """Que tallas ofrecibles tiene cada producto.

    Es la pregunta mas frecuente de una tienda de ropa ---«¿la tienen en
    M?»--- y sin esto el asistente tendria que contestar que no sabe sobre
    un dato que el sistema tiene a mano.
    """
    if not producto_ids:
        return {}

    from app.modules.catalogo.models import Talla

    filas = db.execute(
        select(VarianteProducto.producto_id, Talla.codigo, Talla.orden)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .where(
            VarianteProducto.producto_id.in_(producto_ids),
            VarianteProducto.activa.is_(True),
        )
        .distinct()
        .order_by(VarianteProducto.producto_id, Talla.orden)
    ).all()

    por_producto: dict[int, list[str]] = {}
    for producto_id, codigo, _orden in filas:
        por_producto.setdefault(producto_id, []).append(codigo)
    return por_producto


def pedidos_del_cliente(db: Session, cliente_id: int, limite: int = 5) -> list[tuple]:
    """Sus ultimos pedidos: `(codigo, estado, total, creado_en)`.

    **Los suyos y nada mas.** El filtro va en la consulta y no en el prompt:
    pedirle al modelo que no mire lo ajeno no es un control de acceso.
    """
    return [
        tuple(f)
        for f in db.execute(
            select(Venta.codigo, Venta.estado, Venta.total, Venta.creado_en)
            .where(Venta.cliente_id == cliente_id)
            .order_by(Venta.creado_en.desc())
            .limit(limite)
        ).all()
    ]


def reservas_del_cliente(db: Session, cliente_id: int, limite: int = 5) -> list[tuple]:
    """Sus reservas: `(id, estado, franja_inicio, sucursal)`."""
    from app.modules.organizacion.models import Sucursal

    return [
        tuple(f)
        for f in db.execute(
            select(
                Reserva.id,
                Reserva.estado,
                Reserva.franja_inicio,
                Sucursal.nombre,
            )
            .join(Sucursal, Sucursal.id == Reserva.sucursal_id)
            .where(Reserva.cliente_id == cliente_id)
            .order_by(Reserva.creado_en.desc())
            .limit(limite)
        ).all()
    ]


def sucursales(db: Session) -> list[tuple]:
    """Donde se puede retirar: `(nombre, ciudad, apertura, cierre)`."""
    from app.modules.organizacion.models import Ciudad, Sucursal

    return [
        tuple(f)
        for f in db.execute(
            select(
                Sucursal.nombre,
                Ciudad.nombre,
                Sucursal.horario_apertura,
                Sucursal.horario_cierre,
            )
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .where(Sucursal.activa.is_(True))
            .order_by(Sucursal.nombre)
        ).all()
    ]
