"""
P3 - Catalogo / CU-08  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1
Caso de uso: CU-08 Gestionar categorias, tallas y colores

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit: el control de la transaccion vive en el servicio.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Categoria, Color, Talla


# --- Categorias ----------------------------------------------------------

def listar_categorias(db: Session) -> list[Categoria]:
    """Todas las categorias, ordenadas como se muestran.

    Se traen planas de una sola consulta y el servicio arma el arbol en
    memoria. Con una taxonomia de prendas -- decenas de nodos, no miles -- es
    mas barato que una consulta recursiva, y mucho mas barato que recorrer la
    relacion `subcategorias` nodo por nodo, que dispara una consulta por rama.
    """
    return list(
        db.scalars(select(Categoria).order_by(Categoria.orden, Categoria.nombre))
    )


def obtener_categoria(db: Session, categoria_id: int) -> Categoria | None:
    return db.scalar(select(Categoria).where(Categoria.id == categoria_id))


def existe_hermana_con_nombre(
    db: Session,
    *,
    nombre: str,
    categoria_padre_id: int | None,
    excepto_id: int | None = None,
) -> bool:
    """Excepcion E1: el nombre no se repite entre categorias hermanas.

    La restriccion uq_categoria_padre_nombre cubre las que tienen padre, pero
    NO las raices: en PostgreSQL dos NULL no son iguales, asi que la
    restriccion no compara dos categorias sin padre y dejaria crear dos
    'Ropa' de primer nivel. Esta consulta es la que lo impide de verdad.
    """
    consulta = select(Categoria.id).where(Categoria.nombre.ilike(nombre))
    if categoria_padre_id is None:
        consulta = consulta.where(Categoria.categoria_padre_id.is_(None))
    else:
        consulta = consulta.where(Categoria.categoria_padre_id == categoria_padre_id)
    if excepto_id is not None:
        consulta = consulta.where(Categoria.id != excepto_id)
    return db.scalar(consulta) is not None


def ids_de_descendientes(db: Session, categoria_id: int) -> set[int]:
    """Todos los identificadores que cuelgan de una categoria, a cualquier nivel.

    Es lo que necesita la excepcion E2: asignar como padre a un descendiente
    formaria un ciclo (A -> B -> A) que dejaria esa rama fuera del arbol para
    siempre, sin que ninguna consulta normal la volviera a encontrar.

    El CHECK ck_categoria_no_autopadre de la base solo impide el ciclo de
    longitud uno -- ser su propia madre --. Los mas largos hay que detectarlos
    aqui, y por eso esta consulta es recursiva.
    """
    raiz = (
        select(Categoria.id)
        .where(Categoria.categoria_padre_id == categoria_id)
        .cte("descendientes", recursive=True)
    )
    hijos = select(Categoria.id).join(raiz, Categoria.categoria_padre_id == raiz.c.id)
    arbol = raiz.union_all(hijos)

    return set(db.scalars(select(arbol.c.id)))


def contar_subcategorias(db: Session, categoria_id: int) -> int:
    """Excepcion E3: una categoria con subcategorias no se elimina."""
    return db.scalar(
        select(func.count(Categoria.id)).where(
            Categoria.categoria_padre_id == categoria_id
        )
    ) or 0


def agregar_categoria(
    db: Session,
    *,
    nombre: str,
    categoria_padre_id: int | None,
    orden: int,
    activa: bool,
) -> Categoria:
    categoria = Categoria(
        nombre=nombre,
        categoria_padre_id=categoria_padre_id,
        orden=orden,
        activa=activa,
    )
    db.add(categoria)
    db.flush()
    return categoria


def eliminar_categoria(db: Session, categoria: Categoria) -> None:
    db.delete(categoria)
    db.flush()


# --- Tallas --------------------------------------------------------------

def listar_tallas(
    db: Session, *, tipo_prenda: str | None = None, activa: bool | None = None
) -> list[Talla]:
    """Tallas en el orden en que se muestran en la ficha de producto."""
    consulta = select(Talla)
    if tipo_prenda is not None:
        consulta = consulta.where(Talla.tipo_prenda == tipo_prenda)
    if activa is not None:
        consulta = consulta.where(Talla.activa.is_(activa))
    return list(db.scalars(consulta.order_by(Talla.tipo_prenda, Talla.orden, Talla.codigo)))


def listar_tipos_de_prenda(db: Session) -> list[str]:
    """Los tipos ya usados, para que el formulario los ofrezca.

    El tipo es texto libre; ofrecer los existentes evita que la misma familia
    termine partida en 'SUPERIOR' y 'PARTE SUPERIOR'.
    """
    return list(db.scalars(select(Talla.tipo_prenda).distinct().order_by(Talla.tipo_prenda)))


def obtener_talla(db: Session, talla_id: int) -> Talla | None:
    return db.scalar(select(Talla).where(Talla.id == talla_id))


def existe_talla(
    db: Session, *, tipo_prenda: str, codigo: str, excepto_id: int | None = None
) -> bool:
    """Excepcion E1, sobre la restriccion uq_talla_tipo_codigo."""
    consulta = select(Talla.id).where(
        Talla.tipo_prenda == tipo_prenda, Talla.codigo == codigo
    )
    if excepto_id is not None:
        consulta = consulta.where(Talla.id != excepto_id)
    return db.scalar(consulta) is not None


def agregar_talla(
    db: Session, *, tipo_prenda: str, codigo: str, orden: int, activa: bool
) -> Talla:
    talla = Talla(tipo_prenda=tipo_prenda, codigo=codigo, orden=orden, activa=activa)
    db.add(talla)
    db.flush()
    return talla


def eliminar_talla(db: Session, talla: Talla) -> None:
    db.delete(talla)
    db.flush()


# --- Colores -------------------------------------------------------------

def listar_colores(db: Session, *, activo: bool | None = None) -> list[Color]:
    consulta = select(Color)
    if activo is not None:
        consulta = consulta.where(Color.activo.is_(activo))
    return list(db.scalars(consulta.order_by(Color.nombre)))


def obtener_color(db: Session, color_id: int) -> Color | None:
    return db.scalar(select(Color).where(Color.id == color_id))


def existe_color_con_nombre(
    db: Session, nombre: str, *, excepto_id: int | None = None
) -> bool:
    """Excepcion E1. Compara sin distinguir mayusculas.

    La restriccion uq_color_nombre si las distingue, asi que sin esta consulta
    'Rojo' y 'rojo' entrarian como dos colores distintos.
    """
    consulta = select(Color.id).where(Color.nombre.ilike(nombre))
    if excepto_id is not None:
        consulta = consulta.where(Color.id != excepto_id)
    return db.scalar(consulta) is not None


def agregar_color(db: Session, *, nombre: str, hexadecimal: str, activo: bool) -> Color:
    color = Color(nombre=nombre, hexadecimal=hexadecimal, activo=activo)
    db.add(color)
    db.flush()
    return color


def eliminar_color(db: Session, color: Color) -> None:
    db.delete(color)
    db.flush()


# TODO Ciclo 2: cuando exista `producto`, la excepcion E3 tiene que contar
# tambien los productos asociados a la categoria, y las variantes que usan la
# talla o el color. Hoy ninguna tabla los referencia, asi que la unica
# dependencia posible es la de una categoria con subcategorias.
