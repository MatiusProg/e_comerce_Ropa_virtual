"""
P4 - Inventario / CU-39  |  capa: repositorio (consultas, sin logica ni commit)
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Abastecimiento
from app.modules.organizacion.models import Proveedor


def proveedor_de_usuario(db: Session, usuario_id: int) -> Proveedor | None:
    return db.scalar(select(Proveedor).where(Proveedor.usuario_id == usuario_id))


def variante_de(db: Session, variante_id: int):
    """La variante con su prenda, si existe y se puede abastecer."""
    return db.execute(
        select(
            VarianteProducto.id,
            VarianteProducto.sku,
            Producto.id,
            Producto.nombre,
            Producto.proveedor_id,
            Talla.codigo,
            Color.nombre,
            VarianteProducto.activa,
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(VarianteProducto.id == variante_id)
    ).one_or_none()


def vigente(db: Session, proveedor_id: int, variante_id: int) -> Abastecimiento | None:
    return db.scalar(
        select(Abastecimiento).where(
            Abastecimiento.proveedor_id == proveedor_id,
            Abastecimiento.variante_id == variante_id,
            Abastecimiento.estado == "ANUNCIADO",
        )
    )


def por_id(db: Session, anuncio_id: int) -> Abastecimiento | None:
    return db.get(Abastecimiento, anuncio_id)


def mios(db: Session, proveedor_id: int, *, incluir_cancelados: bool) -> list[tuple]:
    consulta = (
        select(
            Abastecimiento.id,
            Abastecimiento.variante_id,
            VarianteProducto.sku,
            Producto.nombre,
            Talla.codigo,
            Color.nombre,
            Abastecimiento.cantidad,
            Abastecimiento.dias_plazo,
            Abastecimiento.observacion,
            Abastecimiento.estado,
            Abastecimiento.creado_en,
            Abastecimiento.cantidad_recibida,
            Abastecimiento.recibido_en,
        )
        .join(VarianteProducto, VarianteProducto.id == Abastecimiento.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(Abastecimiento.proveedor_id == proveedor_id)
        .order_by(Abastecimiento.creado_en.desc())
    )
    if not incluir_cancelados:
        # Los RECIBIDO se muestran SIEMPRE, aunque no se pidan los cancelados.
        # Son la devolucion que el proveedor no tenia: ocultarlos dejaria su
        # pantalla igual que antes ---solo lo que todavia no llego--- y el
        # lote entregado desapareceria sin decir que se entrego.
        consulta = consulta.where(Abastecimiento.estado != "CANCELADO")
    return [tuple(f) for f in db.execute(consulta).all()]


def variantes_del_proveedor(db: Session, proveedor_id: int) -> list[tuple]:
    """Las variantes que este proveedor puede anunciar.

    SOLO LAS DE SUS PROPIOS PRODUCTOS. Un proveedor no puede prometer una
    prenda de otro: el anuncio alimenta el inventario consolidado, y un
    «proxima a ingresar» respaldado por quien no la abastece es peor que no
    tener el dato.
    """
    return [
        tuple(f)
        for f in db.execute(
            select(
                VarianteProducto.id,
                VarianteProducto.sku,
                Producto.nombre,
                Talla.codigo,
                Color.nombre,
            )
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(
                Producto.proveedor_id == proveedor_id,
                VarianteProducto.activa.is_(True),
                Producto.activo.is_(True),
            )
            .order_by(Producto.nombre, Talla.codigo, Color.nombre)
        ).all()
    ]


def crear(
    db: Session,
    *,
    proveedor_id: int,
    variante_id: int,
    cantidad: int,
    dias_plazo: int,
    observacion: str | None,
) -> Abastecimiento:
    """**Sin commit.**"""
    fila = Abastecimiento(
        proveedor_id=proveedor_id,
        variante_id=variante_id,
        cantidad=cantidad,
        dias_plazo=dias_plazo,
        observacion=observacion,
        estado="ANUNCIADO",
    )
    db.add(fila)
    db.flush()
    return fila


# --- Lo que consume el inventario consolidado (CU-16) -----------------------


def anunciado_por_variante(db: Session, variante_ids: list[int]) -> dict[int, tuple[int, int]]:
    """Cuanto hay anunciado y en cuantos dias, por variante.

    EN BLOQUE Y NO UNA CONSULTA POR FILA. El consolidado muestra paginas de
    decenas de variantes; preguntar una por una serian decenas de viajes para
    pintar una columna.

    Devuelve `{variante_id: (cantidad_total, dias_minimos)}`.

    **Se suma entre proveedores y se toma el plazo MENOR.** Si dos proveedores
    anuncian la misma variante, van a llegar las dos cantidades; y lo que le
    importa a quien mira el inventario es cuando llega la primera.

    SE SUMA LO QUE FALTA, NO LO ANUNCIADO (ver la 0018)
    -----------------------------------------------------
    `cantidad - cantidad_recibida`. Sumando `cantidad` a secas, una entrega
    parcial se cuenta dos veces: las unidades que ya llegaron estan en el
    saldo disponible Y siguen apareciendo como «en camino». El encargado ve
    mas mercaderia de la que hay.

    Las filas ya completas se descartan con el `WHERE`, no restando cero:
    asi no entran al grupo y una variante enteramente recibida desaparece
    del resultado en vez de devolver `(0, n)` --- que la pantalla tendria
    que aprender a distinguir de «no hay nada anunciado».
    """
    if not variante_ids:
        return {}
    pendiente = Abastecimiento.cantidad - Abastecimiento.cantidad_recibida
    filas = db.execute(
        select(
            Abastecimiento.variante_id,
            func.sum(pendiente),
            func.min(Abastecimiento.dias_plazo),
        )
        .where(
            Abastecimiento.variante_id.in_(variante_ids),
            Abastecimiento.estado == "ANUNCIADO",
            pendiente > 0,
        )
        .group_by(Abastecimiento.variante_id)
    ).all()
    return {f[0]: (int(f[1] or 0), int(f[2] or 0)) for f in filas}


# --- La recepcion: CU-13 cierra lo que CU-39 anuncio ------------------------


def pendientes_de_recibir(
    db: Session, *, proveedor_id: int | None = None, variante_ids: list[int] | None = None
) -> list[tuple]:
    """Los anuncios que todavia esperan mercaderia.

    Devuelve `(Abastecimiento, razon_social, sku, prenda, talla, color)`,
    del que llega antes al que llega despues.

    ORDENADOS POR PLAZO Y NO POR FECHA DE ANUNCIO. La pantalla de ingreso los
    muestra arriba como avisos, y lo que le sirve a quien recibe es «esto
    tendria que estar llegando», no «esto se anuncio primero».
    """
    from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
    from app.modules.organizacion.models import Proveedor

    pendiente = Abastecimiento.cantidad - Abastecimiento.cantidad_recibida
    consulta = (
        select(
            Abastecimiento,
            Proveedor.razon_social,
            VarianteProducto.sku,
            Producto.nombre,
            Talla.codigo,
            Color.nombre,
        )
        .join(Proveedor, Proveedor.id == Abastecimiento.proveedor_id)
        .join(VarianteProducto, VarianteProducto.id == Abastecimiento.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(Abastecimiento.estado == "ANUNCIADO", pendiente > 0)
        .order_by(Abastecimiento.dias_plazo.asc(), Abastecimiento.id.asc())
    )
    if proveedor_id is not None:
        consulta = consulta.where(Abastecimiento.proveedor_id == proveedor_id)
    if variante_ids is not None:
        consulta = consulta.where(Abastecimiento.variante_id.in_(variante_ids))
    return [tuple(f) for f in db.execute(consulta).all()]


def para_recibir(db: Session, anuncio_ids: list[int]) -> dict[int, Abastecimiento]:
    """Los anuncios que un ingreso dice estar cerrando, BLOQUEADOS.

    `with_for_update` porque dos recepciones simultaneas del mismo anuncio
    ---dos depositos descargando el mismo lote--- leerian las dos el mismo
    `cantidad_recibida` y la segunda pisaria a la primera. Es el mismo
    bloqueo que ya usa la existencia (RNF11).
    """
    if not anuncio_ids:
        return {}
    filas = db.scalars(
        select(Abastecimiento)
        .where(Abastecimiento.id.in_(anuncio_ids))
        .with_for_update()
    ).all()
    return {a.id: a for a in filas}
