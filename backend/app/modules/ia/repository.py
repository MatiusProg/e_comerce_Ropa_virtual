"""
P10 - Inteligencia Artificial / CU-33  |  capa: repositorio

Regla: aqui solo van consultas. Ninguna regla de negocio, ningun commit.

`existencia` es de P4 y **no se consulta desde aqui**: entra por la costura C1,
importando `inventario.service.productos_con_stock`. Es el mismo contrato que
cumple el catalogo publico.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core import tiempo

from app.modules.catalogo.models import (
    Categoria,
    Producto,
    Talla,
    Temporada,
    VarianteProducto,
)
from app.modules.catalogo_publico.models import Favorito
from app.modules.ia.models import Recomendacion
from app.modules.seguridad.models import Cliente, cliente_categoria
from app.modules.ventas.models import DetalleVenta, Venta


def cliente_de_usuario(db: Session, usuario_id: int) -> Cliente | None:
    return db.scalar(select(Cliente).where(Cliente.usuario_id == usuario_id))


def temporada_vigente(db: Session) -> Temporada | None:
    """La temporada que incluye hoy.

    Si hay mas de una solapada gana la que empezo mas tarde: es la que la
    tienda acaba de abrir, y es lo que se quiere empujar.
    """
    hoy = tiempo.hoy()
    return db.scalar(
        select(Temporada)
        .where(Temporada.fecha_inicio <= hoy, Temporada.fecha_fin >= hoy)
        .order_by(Temporada.fecha_inicio.desc())
        .limit(1)
    )


def categorias_preferidas(db: Session, cliente_id: int) -> list[tuple[int, str]]:
    """Las categorias que el cliente eligio en su perfil (CU-04)."""
    # `cliente_categoria` es una tabla puente sin atributos, declarada con
    # `Table(...)` y no con una clase --- por eso se usa directamente y no hay
    # modelo que importar.
    filas = db.execute(
        select(Categoria.id, Categoria.nombre)
        .join(cliente_categoria, Categoria.id == cliente_categoria.c.categoria_id)
        .where(cliente_categoria.c.cliente_id == cliente_id)
        .order_by(Categoria.nombre)
    ).all()
    return [(f[0], f[1]) for f in filas]


def prendas_conocidas(db: Session, cliente_id: int, limite: int = 8) -> list[str]:
    """Nombres de prendas que el cliente compro o marco como favoritas.

    Es lo que permite justificar con «combina con la chaqueta que compraste».
    Se mezclan las dos fuentes porque las dos dicen lo mismo sobre su gusto, y
    una clienta nueva que todavia no compro suele tener favoritos.
    """
    compradas = (
        select(Producto.nombre)
        .join(VarianteProducto, VarianteProducto.producto_id == Producto.id)
        .join(DetalleVenta, DetalleVenta.variante_id == VarianteProducto.id)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .where(Venta.cliente_id == cliente_id)
    )
    favoritas = (
        select(Producto.nombre)
        .join(Favorito, Favorito.producto_id == Producto.id)
        .where(Favorito.cliente_id == cliente_id)
    )
    filas = db.execute(compradas.union(favoritas).limit(limite)).all()
    return [f[0] for f in filas]


def _ofrecible():
    return and_(
        VarianteProducto.producto_id == Producto.id,
        VarianteProducto.activa.is_(True),
    )


def _vendidas_en(temporada_id: int | None):
    """Cuantas unidades se vendieron de este producto. La senal de popularidad.

    Subconsulta correlacionada y no un JOIN con GROUP BY: se usa como
    expresion de ORDER BY, donde un agregado obligaria a agrupar la consulta
    entera por cada columna del producto.
    """
    consulta = (
        select(func.coalesce(func.sum(DetalleVenta.cantidad), 0))
        .select_from(DetalleVenta)
        .join(VarianteProducto, VarianteProducto.id == DetalleVenta.variante_id)
        .where(VarianteProducto.producto_id == Producto.id)
    )
    return consulta.correlate(Producto).scalar_subquery()


def candidatas(
    db: Session,
    *,
    talla_codigo: str | None,
    categoria_ids: list[int],
    temporada_id: int | None,
    limite: int,
) -> list[tuple[int, str, str, Decimal | None, int]]:
    """El PASO 1 de CU-33: el filtro determinista.

    Devuelve `(producto_id, nombre, categoria, precio_desde, vendidas)`.

    LO QUE ESTE PASO GARANTIZA
    ---------------------------
    Que **jamas se recomiende una prenda agotada o de una talla que el cliente
    no usa**. El modelo del paso 2 solo reordena lo que salga de aca, asi que
    lo peor que puede hacer es ordenar mal --- nunca prometer algo que la
    tienda no puede cumplir.

    LOS FILTROS SON PREFERENCIAS, NO EXIGENCIAS
    --------------------------------------------
    La talla y las categorias ACOTAN cuando hay dato, pero no vacian el
    resultado cuando no lo hay: una clienta nueva, sin talla cargada ni
    categorias elegidas, tiene que recibir recomendaciones igual --- las mas
    vendidas de la temporada ---. Una pantalla de recomendaciones vacia se lee
    como que la tienda no tiene nada.

    La temporada, en cambio, se aplica con `OR temporada IS NULL`: hay
    productos sin temporada asignada y excluirlos dejaria fuera medio catalogo.
    """
    precio_desde = (
        select(func.min(VarianteProducto.precio))
        .where(_ofrecible())
        .correlate(Producto)
        .scalar_subquery()
    )

    consulta: Select = (
        select(
            Producto.id,
            Producto.nombre,
            func.coalesce(Categoria.nombre, "—"),
            precio_desde,
            _vendidas_en(temporada_id),
        )
        .join(Categoria, Categoria.id == Producto.categoria_id, isouter=True)
        .where(
            Producto.activo.is_(True),
            exists(select(VarianteProducto.id).where(_ofrecible())),
        )
    )

    if temporada_id is not None:
        consulta = consulta.where(
            or_(
                Producto.temporada_id == temporada_id,
                Producto.temporada_id.is_(None),
            )
        )

    if talla_codigo:
        consulta = consulta.where(
            exists(
                select(VarianteProducto.id)
                .join(Talla, Talla.id == VarianteProducto.talla_id)
                .where(_ofrecible(), Talla.codigo == talla_codigo)
            )
        )

    if categoria_ids:
        consulta = consulta.where(Producto.categoria_id.in_(categoria_ids))

    # Por popularidad, y el desempate por id. Sin desempate, dos productos con
    # cero ventas ---que son muchos en una tienda de demostracion--- salen en
    # distinto orden en cada llamada y la recomendacion «cambia sola».
    consulta = consulta.order_by(
        _vendidas_en(temporada_id).desc(), Producto.id.desc()
    ).limit(limite)

    return [tuple(f) for f in db.execute(consulta).all()]


def productos_por_id(db: Session, ids: list[int]) -> dict[int, Producto]:
    if not ids:
        return {}
    filas = db.scalars(select(Producto).where(Producto.id.in_(ids))).all()
    return {p.id: p for p in filas}


# --- La recomendacion guardada --------------------------------------------


def guardada(db: Session, cliente_id: int) -> Recomendacion | None:
    return db.scalar(
        select(Recomendacion).where(Recomendacion.cliente_id == cliente_id)
    )


def guardar(
    db: Session, cliente_id: int, motor: str, sugerencias: list[dict]
) -> Recomendacion:
    """Crea o reemplaza la recomendacion vigente. **Sin commit.**"""
    fila = guardada(db, cliente_id)
    if fila is None:
        fila = Recomendacion(cliente_id=cliente_id)
        db.add(fila)
    fila.motor = motor
    fila.sugerencias = sugerencias
    fila.generada_en = func.now()
    db.flush()
    return fila


def invalidar(db: Session, cliente_id: int) -> None:
    """Borra la recomendacion vigente. **Sin commit.**

    Se llama cuando el cliente compra o cambia sus preferencias: lo que se le
    recomendaba se calculo con un perfil que ya no es el suyo.
    """
    fila = guardada(db, cliente_id)
    if fila is not None:
        db.delete(fila)
        db.flush()


def nombres_de_categoria(db: Session, ids: list[int]) -> dict[int, str]:
    """El nombre de cada categoria. `Producto` no declara la relacion."""
    if not ids:
        return {}
    filas = db.execute(
        select(Categoria.id, Categoria.nombre).where(Categoria.id.in_(ids))
    ).all()
    return {f[0]: f[1] for f in filas}


def precio_desde_de(db: Session, ids: list[int]) -> dict[int, Decimal]:
    """El precio mas bajo entre las variantes ofrecibles de cada producto.

    Se lee ahora y no se guarda con la sugerencia: una prenda que cambio de
    precio en las ultimas doce horas tiene que mostrarse con el precio de hoy.
    """
    if not ids:
        return {}
    filas = db.execute(
        select(
            VarianteProducto.producto_id,
            func.min(VarianteProducto.precio),
        )
        .where(
            VarianteProducto.producto_id.in_(ids),
            VarianteProducto.activa.is_(True),
        )
        .group_by(VarianteProducto.producto_id)
    ).all()
    return {f[0]: f[1] for f in filas}
