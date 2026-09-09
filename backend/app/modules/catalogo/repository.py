"""
P3 - Catalogo / CU-10  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2
Caso de uso: CU-10 Gestionar productos y variantes

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit: el control de la transaccion vive en el servicio.
"""
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogo.models import (
    Categoria,
    Coleccion,
    Color,
    Producto,
    Talla,
    Temporada,
    VarianteProducto,
)
from app.modules.organizacion.models import Proveedor


# --- Maestros que el producto referencia ---------------------------------
# Se consultan desde aqui y no importando los repositorios de CU-08 y CU-09
# para no atar dos casos de uso entre si: son lecturas de una linea.

def existe_categoria(db: Session, categoria_id: int) -> bool:
    return db.scalar(select(Categoria.id).where(Categoria.id == categoria_id)) is not None


def existe_proveedor(db: Session, proveedor_id: int) -> bool:
    return db.scalar(select(Proveedor.id).where(Proveedor.id == proveedor_id)) is not None


def existe_temporada(db: Session, temporada_id: int) -> bool:
    return db.scalar(select(Temporada.id).where(Temporada.id == temporada_id)) is not None


def obtener_coleccion(db: Session, coleccion_id: int) -> Coleccion | None:
    return db.scalar(select(Coleccion).where(Coleccion.id == coleccion_id))


def tallas_existentes(db: Session, ids: list[int]) -> set[int]:
    return set(db.scalars(select(Talla.id).where(Talla.id.in_(ids))))


def colores_existentes(db: Session, ids: list[int]) -> set[int]:
    return set(db.scalars(select(Color.id).where(Color.id.in_(ids))))


# --- Productos -----------------------------------------------------------

def _filtrar(
    consulta: Select,
    *,
    busqueda: str | None,
    categoria_id: int | None,
    temporada_id: int | None,
    coleccion_id: int | None,
    proveedor_id: int | None,
    activo: bool | None,
) -> Select:
    """Aplica los filtros del paso 2. Se comparte entre el listado y el conteo.

    Estan en una funcion sola a proposito: si el conteo filtrara distinto que el
    listado, el paginador mostraria un numero de paginas que no existe, y es un
    defecto que no se ve hasta que alguien pagina hasta el final.
    """
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.where(
            or_(Producto.nombre.ilike(patron), Producto.codigo.ilike(patron))
        )
    if categoria_id is not None:
        consulta = consulta.where(Producto.categoria_id == categoria_id)
    if temporada_id is not None:
        consulta = consulta.where(Producto.temporada_id == temporada_id)
    if coleccion_id is not None:
        consulta = consulta.where(Producto.coleccion_id == coleccion_id)
    if proveedor_id is not None:
        consulta = consulta.where(Producto.proveedor_id == proveedor_id)
    if activo is not None:
        consulta = consulta.where(Producto.activo == activo)
    return consulta


def contar_productos(db: Session, **filtros) -> int:
    consulta = _filtrar(select(func.count()).select_from(Producto), **filtros)
    return db.scalar(consulta) or 0


def listar_productos(
    db: Session, *, limite: int, desplazamiento: int, **filtros
) -> list[Producto]:
    """Una pagina del listado, ordenada por codigo.

    El orden es estable y explicito: sin ORDER BY, PostgreSQL puede devolver las
    filas en distinto orden entre dos paginas y un producto aparecer dos veces o
    ninguna.
    """
    consulta = _filtrar(select(Producto), **filtros)
    consulta = consulta.order_by(Producto.codigo).limit(limite).offset(desplazamiento)
    return list(db.scalars(consulta))


def conteo_de_variantes(db: Session, producto_ids: list[int]) -> dict[int, tuple[int, int]]:
    """Total de variantes y cuantas estan activas, por producto.

    Una sola consulta agregada para toda la pagina. Contar recorriendo
    `producto.variantes` dispararia una consulta por fila del listado.
    """
    if not producto_ids:
        return {}
    filas = db.execute(
        select(
            VarianteProducto.producto_id,
            func.count().label("total"),
            func.count().filter(VarianteProducto.activa).label("activas"),
        )
        .where(VarianteProducto.producto_id.in_(producto_ids))
        .group_by(VarianteProducto.producto_id)
    ).all()
    return {fila.producto_id: (fila.total, fila.activas) for fila in filas}


def obtener_producto(db: Session, producto_id: int) -> Producto | None:
    """Un producto con sus variantes y los maestros de cada una ya cargados.

    `selectinload` trae todo en tres consultas fijas. Sin el, dibujar la tabla
    de variantes dispara una consulta por talla y otra por color de cada fila.

    `populate_existing` NO es decorativo. La sesion se abre con
    `expire_on_commit=False`, asi que despues de un commit el Producto sigue en
    el mapa de identidad con su coleccion `variantes` tal como se cargo. Volver
    a consultarlo devuelve ESA instancia y, si la coleccion ya estaba cargada,
    SQLAlchemy no la reemplaza: el detalle que se lee justo despues de generar
    variantes salia sin ninguna. Con esto, la consulta siempre refresca lo que
    trae.
    """
    return db.scalar(
        select(Producto)
        .where(Producto.id == producto_id)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Producto.variantes).selectinload(VarianteProducto.talla),
            selectinload(Producto.variantes).selectinload(VarianteProducto.color),
        )
    )


def nombre_de_categoria(db: Session, categoria_id: int) -> str | None:
    return db.scalar(select(Categoria.nombre).where(Categoria.id == categoria_id))


def nombres_de_categorias(db: Session, ids: list[int]) -> dict[int, str]:
    """Los nombres de todas las categorias de una pagina, en una consulta."""
    if not ids:
        return {}
    filas = db.execute(
        select(Categoria.id, Categoria.nombre).where(Categoria.id.in_(ids))
    ).all()
    return {fila.id: fila.nombre for fila in filas}


def existe_codigo(db: Session, codigo: str, *, excepto_id: int | None = None) -> bool:
    """Excepcion E1. Compara sin distinguir mayusculas.

    El UNIQUE de la base sí las distingue, asi que sin esta consulta 'cam-001' y
    'CAM-001' entrarian los dos. El esquema ya normaliza a mayusculas al crear;
    esto cubre los datos que hayan entrado por otra via, como el seed.
    """
    consulta = select(Producto.id).where(Producto.codigo.ilike(codigo))
    if excepto_id is not None:
        consulta = consulta.where(Producto.id != excepto_id)
    return db.scalar(consulta) is not None


def agregar_producto(db: Session, **campos) -> Producto:
    producto = Producto(**campos)
    db.add(producto)
    db.flush()
    return producto


def eliminar_producto(db: Session, producto: Producto) -> None:
    db.delete(producto)
    db.flush()


# --- Variantes -----------------------------------------------------------

def obtener_variante(db: Session, variante_id: int) -> VarianteProducto | None:
    return db.scalar(
        select(VarianteProducto)
        .where(VarianteProducto.id == variante_id)
        .options(
            selectinload(VarianteProducto.talla),
            selectinload(VarianteProducto.color),
        )
    )


def combinaciones_existentes(db: Session, producto_id: int) -> set[tuple[int, int]]:
    """Los pares (talla, color) que el producto ya tiene.

    Es lo que permite que volver a generar variantes omita lo que ya existe en
    vez de chocar contra uq_variante_producto_talla_color.
    """
    filas = db.execute(
        select(VarianteProducto.talla_id, VarianteProducto.color_id).where(
            VarianteProducto.producto_id == producto_id
        )
    ).all()
    return {(fila.talla_id, fila.color_id) for fila in filas}


def agregar_variante(db: Session, **campos) -> VarianteProducto:
    variante = VarianteProducto(**campos)
    db.add(variante)
    db.flush()
    return variante


def eliminar_variante(db: Session, variante: VarianteProducto) -> None:
    db.delete(variante)
    db.flush()


def codigos_de_talla(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    filas = db.execute(select(Talla.id, Talla.codigo).where(Talla.id.in_(ids))).all()
    return {fila.id: fila.codigo for fila in filas}


def nombres_de_color(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    filas = db.execute(select(Color.id, Color.nombre).where(Color.id.in_(ids))).all()
    return {fila.id: fila.nombre for fila in filas}
