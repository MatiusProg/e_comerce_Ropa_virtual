"""Aporte propio · «Avísame cuando llegue mi talla»  |  capa: servicio.

CUÁNDO SE AVISA
---------------
Cuando la variante pasa de **cero a más de cero unidades disponibles en la
red** (las sucursales activas), que es lo que el cliente ve en la ficha: «sin
unidades por ahora en ninguna sucursal». Reponer en una sucursal cuando otra
todavía tenía no es noticia para nadie, porque el botón no se ofreció.

POR DÓNDE ENTRA EL AVISO
------------------------
Por un solo lugar: `inventario.service._aplicar_movimiento`, el único que
cambia un saldo. Así lo dispara cualquier camino que reponga ---un ingreso, un
traspaso recibido, una devolución o un cambio que reingresa la prenda, un
ajuste por conteo o una reserva que se libera--- sin que ninguno de esos
módulos sepa que este existe.

El aviso queda en la misma transacción que el movimiento (si el movimiento se
deshace, el aviso también) y sale por la campanita, el correo y el push con el
despachador de siempre, que corre en las tareas automáticas.

UNA SOLA VEZ
------------
Los pedidos pendientes de la variante se toman con `FOR UPDATE` y se marcan
`notificado_en`. Si dos sucursales reponen al mismo tiempo, la segunda espera,
vuelve a evaluar el `notificado_en IS NULL` y ya no encuentra nada.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.avisos_talla.models import AvisoTalla
from app.modules.avisos_talla.schemas import AvisoOut, DemandaOut
from app.modules.catalogo import imagenes_almacen as almacen
from app.modules.catalogo.models import Color, ImagenProducto, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Sucursal
from app.modules.seguridad import service as seguridad

#: Los avisos ya enviados se siguen mostrando en «Mis avisos» este tiempo,
#: para que el cliente vea que llegó; después ya no le dicen nada.
VIGENCIA_DE_LOS_AVISADOS = timedelta(days=30)


class ErrorAvisoTalla(Exception):
    codigo = 400
    mensaje = "No se pudo completar la operación."


class VarianteNoDisponible(ErrorAvisoTalla):
    codigo = 404
    mensaje = "Esa combinación de talla y color ya no está disponible."


class YaHayUnidades(ErrorAvisoTalla):
    codigo = 409
    mensaje = "Esa talla ya tiene unidades: puede comprarla o reservarla ahora."


class AvisoInexistente(ErrorAvisoTalla):
    codigo = 404
    mensaje = "Ese aviso no existe o ya no está pendiente."


# =====================================================================
# Apoyo
# =====================================================================


def total_disponible(db: Session, variante_id: int) -> int:
    """Lo disponible de la variante en las sucursales activas (lo de la ficha)."""
    return int(
        db.scalar(
            select(func.coalesce(func.sum(Existencia.cantidad_disponible), 0))
            .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
            .where(Existencia.variante_id == variante_id, Sucursal.activa.is_(True))
        )
        or 0
    )


def _variante_ofrecible(db: Session, variante_id: int) -> VarianteProducto | None:
    return db.scalar(
        select(VarianteProducto)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .where(
            VarianteProducto.id == variante_id,
            VarianteProducto.activa.is_(True),
            Producto.activo.is_(True),
        )
    )


def _detalle_de_variantes(db: Session, ids: set[int]) -> dict[int, dict]:
    """Producto, talla, color, SKU e imagen de cada variante, en dos consultas."""
    if not ids:
        return {}
    filas = db.execute(
        select(
            VarianteProducto.id,
            VarianteProducto.sku,
            VarianteProducto.activa,
            Producto.id.label("producto_id"),
            Producto.nombre.label("producto"),
            Producto.activo.label("producto_activo"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(VarianteProducto.id.in_(ids))
    ).mappings().all()
    productos = {f["producto_id"] for f in filas}
    imagenes = dict(
        db.execute(
            select(ImagenProducto.producto_id, ImagenProducto.ruta)
            .where(
                ImagenProducto.producto_id.in_(productos),
                ImagenProducto.es_transparente.is_(False),
            )
            .distinct(ImagenProducto.producto_id)
            .order_by(
                ImagenProducto.producto_id,
                ImagenProducto.es_principal.desc(),
                ImagenProducto.orden,
                ImagenProducto.id,
            )
        ).all()
    ) if productos else {}
    salida = {}
    for f in filas:
        ruta = imagenes.get(f["producto_id"])
        salida[f["id"]] = {
            **f,
            "ofrecible": bool(f["activa"] and f["producto_activo"]),
            "imagen_url": almacen.url_de(ruta) if ruta else None,
        }
    return salida


# =====================================================================
# Lo que hace el cliente
# =====================================================================


def suscribir(db: Session, usuario_id: int, variante_id: int) -> AvisoOut:
    """Deja el pedido de aviso. Idempotente: pedirlo dos veces deja uno solo.

    Solo se puede pedir lo ofrecible y lo que de verdad no tiene unidades: si
    hay, el aviso no tiene nada que esperar y la respuesta lo dice.
    """
    cliente_id = seguridad.cliente_id_de_usuario(db, usuario_id)
    if _variante_ofrecible(db, variante_id) is None:
        raise VarianteNoDisponible()

    existente = db.scalar(
        select(AvisoTalla).where(
            AvisoTalla.cliente_id == cliente_id,
            AvisoTalla.variante_id == variante_id,
            AvisoTalla.notificado_en.is_(None),
        )
    )
    if existente is None:
        if total_disponible(db, variante_id) > 0:
            raise YaHayUnidades()
        existente = AvisoTalla(cliente_id=cliente_id, variante_id=variante_id)
        db.add(existente)
        try:
            db.flush()
        except IntegrityError:
            # Dos toques simultáneos: el índice único parcial dejó entrar uno.
            db.rollback()
            existente = db.scalar(
                select(AvisoTalla).where(
                    AvisoTalla.cliente_id == cliente_id,
                    AvisoTalla.variante_id == variante_id,
                    AvisoTalla.notificado_en.is_(None),
                )
            )
        db.commit()
    return _a_salida(db, [existente])[0]


def mis_avisos(db: Session, usuario_id: int) -> list[AvisoOut]:
    """Los pendientes y los avisados en los últimos 30 días, lo nuevo primero."""
    cliente_id = seguridad.cliente_id_de_usuario(db, usuario_id)
    desde = tiempo.ahora() - VIGENCIA_DE_LOS_AVISADOS
    filas = db.scalars(
        select(AvisoTalla)
        .where(
            AvisoTalla.cliente_id == cliente_id,
            (AvisoTalla.notificado_en.is_(None)) | (AvisoTalla.notificado_en >= desde),
        )
        .order_by(AvisoTalla.creado_en.desc(), AvisoTalla.id.desc())
    ).all()
    return _a_salida(db, list(filas))


def variantes_esperadas(db: Session, usuario_id: int) -> list[int]:
    """Las variantes con aviso pendiente del cliente, para pintar la ficha."""
    cliente_id = seguridad.cliente_id_de_usuario(db, usuario_id)
    return list(
        db.scalars(
            select(AvisoTalla.variante_id).where(
                AvisoTalla.cliente_id == cliente_id, AvisoTalla.notificado_en.is_(None)
            )
        ).all()
    )


def cancelar(db: Session, usuario_id: int, aviso_id: int) -> None:
    """Borra un pedido pendiente PROPIO. El de otro cliente responde 404."""
    cliente_id = seguridad.cliente_id_de_usuario(db, usuario_id)
    aviso = db.scalar(
        select(AvisoTalla).where(
            AvisoTalla.id == aviso_id,
            AvisoTalla.cliente_id == cliente_id,
            AvisoTalla.notificado_en.is_(None),
        )
    )
    if aviso is None:
        raise AvisoInexistente()
    db.delete(aviso)
    db.commit()


def _a_salida(db: Session, avisos: list[AvisoTalla]) -> list[AvisoOut]:
    detalle = _detalle_de_variantes(db, {a.variante_id for a in avisos})
    salida = []
    for a in avisos:
        d = detalle.get(a.variante_id, {})
        salida.append(
            AvisoOut(
                id=a.id,
                variante_id=a.variante_id,
                producto_id=d.get("producto_id"),
                producto=d.get("producto", "Prenda retirada"),
                talla=d.get("talla", ""),
                color=d.get("color", ""),
                sku=d.get("sku", ""),
                imagen_url=d.get("imagen_url"),
                ofrecible=d.get("ofrecible", False),
                estado="AVISADO" if a.notificado_en else "ESPERANDO",
                creado_en=a.creado_en,
                notificado_en=a.notificado_en,
            )
        )
    return salida


# =====================================================================
# Lo que ve el personal: la demanda que espera
# =====================================================================


def demanda(db: Session) -> list[DemandaOut]:
    """Cuántos clientes esperan cada talla y color, lo más pedido primero.

    Es de la empresa entera: el cliente no espera en una sucursal sino en la
    tienda. Al encargado le sirve igual, para pedir un traspaso o reponer.
    """
    filas = db.execute(
        select(
            AvisoTalla.variante_id,
            func.count().label("clientes"),
            func.min(AvisoTalla.creado_en).label("desde"),
        )
        .where(AvisoTalla.notificado_en.is_(None))
        .group_by(AvisoTalla.variante_id)
        .order_by(func.count().desc(), func.min(AvisoTalla.creado_en))
    ).all()
    detalle = _detalle_de_variantes(db, {f.variante_id for f in filas})
    salida = []
    for f in filas:
        d = detalle.get(f.variante_id)
        if d is None:
            continue
        salida.append(
            DemandaOut(
                variante_id=f.variante_id,
                producto_id=d["producto_id"],
                producto=d["producto"],
                talla=d["talla"],
                color=d["color"],
                sku=d["sku"],
                clientes=f.clientes,
                esperando_desde=f.desde,
            )
        )
    return salida


# =====================================================================
# El gancho del inventario
# =====================================================================


def avisar_si_volvio(db: Session, existencia: Existencia, *, cantidad: int) -> int:
    """Lo llama el inventario DESPUÉS de sumar `cantidad` al disponible.

    Devuelve cuántos clientes quedaron avisados. No confirma: el movimiento
    que lo llamó es el dueño de la transacción.

    Primero mira si hay alguien esperando esa variante (una consulta por índice
    parcial, casi siempre vacía) y recién entonces calcula el total de la red,
    para que el costo en el camino común ---nadie espera--- sea mínimo.
    """
    if cantidad <= 0:
        return 0
    hay_pendientes = db.scalar(
        select(AvisoTalla.id)
        .where(
            AvisoTalla.variante_id == existencia.variante_id,
            AvisoTalla.notificado_en.is_(None),
        )
        .limit(1)
    )
    if hay_pendientes is None:
        return 0

    sucursal_activa = db.scalar(
        select(Sucursal.activa).where(Sucursal.id == existencia.sucursal_id)
    )
    if not sucursal_activa:
        # Lo que entra a una sucursal cerrada no se ofrece en la tienda.
        return 0
    ahora_total = total_disponible(db, existencia.variante_id)
    antes_total = ahora_total - cantidad
    if not (antes_total <= 0 < ahora_total):
        return 0

    pendientes = db.scalars(
        select(AvisoTalla)
        .where(
            AvisoTalla.variante_id == existencia.variante_id,
            AvisoTalla.notificado_en.is_(None),
        )
        .order_by(AvisoTalla.creado_en)
        .with_for_update()
    ).all()
    if not pendientes:
        return 0

    from app.modules.notificaciones import service as notificaciones

    d = _detalle_de_variantes(db, {existencia.variante_id}).get(existencia.variante_id)
    if d is None or not d["ofrecible"]:
        return 0
    etiqueta = f"{d['producto']} talla {d['talla']}, {d['color']}"
    momento = tiempo.ahora()
    avisados = 0
    for aviso in pendientes:
        destinatario = notificaciones.usuario_del_cliente(db, aviso.cliente_id)
        nota = None
        if destinatario is not None:
            nota = notificaciones.notificar(
                db,
                destinatario=destinatario,
                tipo="STOCK_DISPONIBLE",
                titulo=f"Volvió su talla: {d['producto']}",
                cuerpo=(
                    f"Ya hay unidades de {etiqueta}, la que pidió que le avisáramos. "
                    f"Son pocas: si la quiere, cómprela o resérvela pronto."
                ),
                enlace=f"/tienda/producto/{d['producto_id']}",
                entidad="variante_producto",
                entidad_id=existencia.variante_id,
            )
            avisados += 1
        aviso.notificado_en = momento
        aviso.notificacion_id = nota.id if nota is not None else None
    db.flush()
    return avisados


__all__ = [
    "AvisoInexistente",
    "ErrorAvisoTalla",
    "VarianteNoDisponible",
    "YaHayUnidades",
    "avisar_si_volvio",
    "cancelar",
    "demanda",
    "mis_avisos",
    "suscribir",
    "total_disponible",
    "variantes_esperadas",
]
