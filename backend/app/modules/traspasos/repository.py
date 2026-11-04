"""P15 - Traspasos / CU-33, CU-34 y CU-35  |  capa: repositorio"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Sucursal
from app.modules.seguridad.models import Usuario
from app.modules.traspasos.models import ESTADOS_ABIERTOS, Traspaso
from app.modules.ventas.models import DetalleVenta, Venta

#: Las ventas que cuentan como vendidas para sugerir: las cobradas.
ESTADOS_VENDIDOS = ("PAGADA", "ENTREGADA")


def agregar(db: Session, **valores) -> Traspaso:
    fila = Traspaso(**valores)
    db.add(fila)
    db.flush()
    return fila


def obtener(db: Session, traspaso_id: int, *, bloquear: bool = False) -> Traspaso | None:
    consulta = select(Traspaso).where(Traspaso.id == traspaso_id)
    if bloquear:
        # Dos encargados apretando «enviar» a la vez no pueden descontar dos
        # veces: el segundo espera, relee el estado y ya no lo encuentra APROBADO.
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def hay_abierto(db: Session, *, variante_id: int, origen_id: int, destino_id: int) -> bool:
    return (
        db.scalar(
            select(func.count(Traspaso.id)).where(
                Traspaso.variante_id == variante_id,
                Traspaso.sucursal_origen_id == origen_id,
                Traspaso.sucursal_destino_id == destino_id,
                Traspaso.estado.in_(("SOLICITADO", "APROBADO")),
            )
        )
        or 0
    ) > 0


def disponible(db: Session, *, variante_id: int, sucursal_id: int) -> int | None:
    """El disponible de la prenda en la sucursal, o None si nunca estuvo."""
    return db.scalar(
        select(Existencia.cantidad_disponible).where(
            Existencia.variante_id == variante_id, Existencia.sucursal_id == sucursal_id
        )
    )


# --------------------------------------------------------------------------
#  Lectura con todo resuelto
# --------------------------------------------------------------------------
_Origen = aliased(Sucursal, name="origen")
_Destino = aliased(Sucursal, name="destino")
_USUARIOS = {
    col: aliased(Usuario, name=f"u_{col}")
    for col in ("solicitado_por", "aprobado_por", "enviado_por", "recibido_por", "rechazado_por")
}


def _nombre(alias):
    return func.trim(func.concat(alias.nombres, " ", alias.apellidos))


def _consulta() -> Select:
    consulta = (
        select(
            Traspaso,
            VarianteProducto.sku,
            Producto.nombre.label("prenda"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
            _Origen.nombre.label("origen"),
            _Destino.nombre.label("destino"),
            *[_nombre(alias).label(col) for col, alias in _USUARIOS.items()],
        )
        .join(VarianteProducto, VarianteProducto.id == Traspaso.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(_Origen, _Origen.id == Traspaso.sucursal_origen_id)
        .join(_Destino, _Destino.id == Traspaso.sucursal_destino_id)
    )
    for col, alias in _USUARIOS.items():
        consulta = consulta.outerjoin(alias, alias.id == getattr(Traspaso, col))
    return consulta


def _filtros(
    consulta: Select,
    *,
    sucursal_id: int | None,
    bandeja: str | None,
    estado: str | None,
    abiertos: bool,
) -> Select:
    if sucursal_id is not None:
        if bandeja == "ENTRANTES":
            consulta = consulta.where(Traspaso.sucursal_destino_id == sucursal_id)
        elif bandeja == "SALIENTES":
            consulta = consulta.where(Traspaso.sucursal_origen_id == sucursal_id)
        else:
            consulta = consulta.where(
                or_(
                    Traspaso.sucursal_origen_id == sucursal_id,
                    Traspaso.sucursal_destino_id == sucursal_id,
                )
            )
    if estado is not None:
        consulta = consulta.where(Traspaso.estado == estado)
    elif abiertos:
        consulta = consulta.where(Traspaso.estado.in_(ESTADOS_ABIERTOS))
    return consulta


def listar(
    db: Session,
    *,
    sucursal_id: int | None,
    bandeja: str | None,
    estado: str | None,
    abiertos: bool,
    pagina: int,
    tamano: int,
) -> tuple[int, list[Row]]:
    filtros = dict(sucursal_id=sucursal_id, bandeja=bandeja, estado=estado, abiertos=abiertos)
    total = db.scalar(
        _filtros(select(func.count(Traspaso.id)), **filtros)
    ) or 0
    filas = db.execute(
        _filtros(_consulta(), **filtros)
        .order_by(Traspaso.actualizado_en.desc(), Traspaso.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()
    return total, list(filas)


def detalle(db: Session, traspaso_id: int) -> Row | None:
    return db.execute(_consulta().where(Traspaso.id == traspaso_id)).first()


def origenes_posibles(db: Session, *, variante_id: int, excluir: int | None) -> list[Row]:
    """Las sucursales activas con unidades disponibles de la prenda."""
    consulta = (
        select(Sucursal.id, Sucursal.nombre, Existencia.cantidad_disponible)
        .join(Existencia, Existencia.sucursal_id == Sucursal.id)
        .where(
            Existencia.variante_id == variante_id,
            Existencia.cantidad_disponible > 0,
            Sucursal.activa.is_(True),
        )
        .order_by(Existencia.cantidad_disponible.desc(), Sucursal.nombre)
    )
    if excluir is not None:
        consulta = consulta.where(Sucursal.id != excluir)
    return list(db.execute(consulta).all())


def prendas_en_otras(
    db: Session, *, busqueda: str | None, excluir: int | None, limite: int = 20
) -> list[Row]:
    """CU-33: las prendas activas que alguna OTRA sucursal tiene disponibles.

    Es el buscador del formulario de pedido: no sirve pedir algo que nadie
    tiene. Busca por SKU y por nombre de la prenda.
    """
    consulta = (
        select(
            VarianteProducto.id,
            VarianteProducto.sku,
            Producto.nombre.label("prenda"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
            func.sum(Existencia.cantidad_disponible).label("disponible"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(Existencia, Existencia.variante_id == VarianteProducto.id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .where(
            VarianteProducto.activa.is_(True),
            Sucursal.activa.is_(True),
            Existencia.cantidad_disponible > 0,
        )
        .group_by(VarianteProducto.id, Producto.nombre, Talla.codigo, Color.nombre)
        .order_by(Producto.nombre, VarianteProducto.sku)
        .limit(limite)
    )
    if excluir is not None:
        consulta = consulta.where(Existencia.sucursal_id != excluir)
    if busqueda:
        patron = f"%{busqueda.strip()}%"
        consulta = consulta.where(
            or_(VarianteProducto.sku.ilike(patron), Producto.nombre.ilike(patron))
        )
    return list(db.execute(consulta).all())


# --------------------------------------------------------------------------
#  CU-35: lo que hace falta para sugerir
# --------------------------------------------------------------------------
def vendidas_por_sucursal(db: Session, *, desde: datetime) -> list[Row]:
    """(variante_id, sucursal_id, vendidas) de las ventas cobradas desde `desde`."""
    return list(
        db.execute(
            select(
                DetalleVenta.variante_id,
                Venta.sucursal_id,
                func.sum(DetalleVenta.cantidad).label("vendidas"),
            )
            .join(Venta, Venta.id == DetalleVenta.venta_id)
            .where(Venta.estado.in_(ESTADOS_VENDIDOS), Venta.creado_en >= desde)
            .group_by(DetalleVenta.variante_id, Venta.sucursal_id)
        ).all()
    )


def existencias_de(db: Session, variante_ids: list[int]) -> list[Row]:
    """Saldos de las prendas en las sucursales activas, con la prenda activa."""
    return list(
        db.execute(
            select(
                Existencia.variante_id,
                Existencia.sucursal_id,
                Existencia.cantidad_disponible,
                Existencia.stock_minimo,
            )
            .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
            .join(VarianteProducto, VarianteProducto.id == Existencia.variante_id)
            .where(
                Existencia.variante_id.in_(variante_ids),
                Sucursal.activa.is_(True),
                VarianteProducto.activa.is_(True),
            )
        ).all()
    )


def en_traspaso(db: Session, variante_ids: list[int]) -> tuple[dict, dict]:
    """Lo que ya viene en camino a cada sucursal y lo que ya prometió cada una.

    Entrante: todo traspaso abierto hacia la sucursal. Saliente: lo pedido o
    aprobado que todavía no salió; lo ENVIADO ya se descontó del disponible.
    """
    entrante: dict[tuple[int, int], int] = {}
    saliente: dict[tuple[int, int], int] = {}
    filas = db.execute(
        select(
            Traspaso.variante_id,
            Traspaso.sucursal_origen_id,
            Traspaso.sucursal_destino_id,
            Traspaso.estado,
            Traspaso.cantidad,
        ).where(Traspaso.variante_id.in_(variante_ids), Traspaso.estado.in_(ESTADOS_ABIERTOS))
    ).all()
    for variante_id, origen, destino, estado, cantidad in filas:
        entrante[(variante_id, destino)] = entrante.get((variante_id, destino), 0) + cantidad
        if estado != "ENVIADO":
            saliente[(variante_id, origen)] = saliente.get((variante_id, origen), 0) + cantidad
    return entrante, saliente


def sucursales_activas(db: Session) -> dict[int, str]:
    return dict(db.execute(select(Sucursal.id, Sucursal.nombre).where(Sucursal.activa.is_(True))).all())


def variantes(db: Session, ids: list[int]) -> dict[int, Row]:
    filas = db.execute(
        select(
            VarianteProducto.id,
            VarianteProducto.sku,
            Producto.nombre.label("prenda"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(VarianteProducto.id.in_(ids))
    ).all()
    return {f.id: f for f in filas}
