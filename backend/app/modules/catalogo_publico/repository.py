"""
P5 - Catalogo Publico / CU-17 y CU-18  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2
Casos de uso:
  CU-17 Consultar catalogo
  CU-18 Consultar ficha de producto
  CU-19 Consultar disponibilidad por sucursal

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit.

P5 no tiene tablas propias en este ciclo --- `models.py` queda vacio a proposito,
segun la seccion 3.1 del documento de organizacion --- asi que todo lo de aqui
LEE las tablas de P3, que son de la misma duena.

`existencia` es de Mateo y **no se consulta desde aqui**, ni siquiera ahora que
CU-19 la necesita: entra por la costura C1, importando la funcion que expone
`inventario/service.py`. Es el contrato de la seccion 6 del documento de
organizacion, y lo unico que hay en este archivo sobre CU-19 es la comprobacion
de que la variante sea ofrecible, que se hace sobre tablas de P3.
"""
from decimal import Decimal

from sqlalchemy import Select, and_, delete, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogo_publico.models import Favorito
from app.modules.catalogo.models import (
    Categoria,
    Coleccion,
    Color,
    ImagenProducto,
    Producto,
    Talla,
    Temporada,
    VarianteProducto,
)


# --- La jerarquia de categorias ------------------------------------------

def ids_de_categoria_y_descendientes(db: Session, categoria_id: int) -> list[int]:
    """El identificador de la categoria y el de todas las que cuelgan de ella.

    Sin esto, filtrar por «Mujer» no devolveria nada cuando los productos estan
    cargados en «Mujer > Blusas», que es como los siembra el seed y como los
    carga cualquier administrador razonable. `Categoria` es autorreferente, asi
    que el arbol se recorre con un CTE recursivo en vez de con una consulta por
    nivel.
    """
    raiz = (
        select(Categoria.id)
        .where(Categoria.id == categoria_id)
        .cte("arbol_categorias", recursive=True)
    )
    hijas = select(Categoria.id).join(raiz, Categoria.categoria_padre_id == raiz.c.id)
    arbol = raiz.union_all(hijas)
    return list(db.scalars(select(arbol.c.id)))


# --- La vitrina (CU-17) --------------------------------------------------

def _variante_ofrecible():
    """La condicion que vuelve comprable a una variante.

    Se usa en todos lados: en el filtro base, en los filtros de talla y color, y
    en el calculo del rango de precios. Esta en una funcion para que no se
    desincronicen entre si --- si el listado contara variantes inactivas y el
    precio no, la ficha mostraria un precio que el listado no promete.
    """
    return and_(
        VarianteProducto.producto_id == Producto.id,
        VarianteProducto.activa.is_(True),
    )


def _filtrar(
    consulta: Select,
    *,
    busqueda: str | None,
    categoria_ids: list[int] | None,
    talla_id: int | None,
    color_id: int | None,
    temporada_id: int | None,
    coleccion_id: int | None,
    precio_min: Decimal | None,
    precio_max: Decimal | None,
) -> Select:
    """Los filtros del paso 2 de CU-17, compartidos entre el listado y el conteo.

    Se comparten a proposito, por el mismo motivo que en CU-10: si el conteo
    filtrara distinto que el listado, el paginador anunciaria paginas que no
    existen y el defecto solo aparece cuando alguien pagina hasta el final.

    Los filtros de talla, color y precio se resuelven con EXISTS y no con un
    JOIN. Con JOIN, un producto con seis variantes rojas apareceria seis veces
    en la pagina y el LIMIT cortaria por la mitad de un producto; con EXISTS la
    fila del producto sigue siendo una sola.
    """
    # Solo se ofrece lo que se puede comprar: producto activo y con al menos una
    # variante activa. Un producto sin variantes activas no tiene precio, ni
    # existencia, ni SKU que reservar --- mostrarlo es prometer algo que no se
    # puede cumplir.
    consulta = consulta.where(
        Producto.activo.is_(True),
        exists(select(VarianteProducto.id).where(_variante_ofrecible())),
    )

    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.where(
            or_(
                Producto.nombre.ilike(patron),
                Producto.descripcion.ilike(patron),
                Producto.codigo.ilike(patron),
            )
        )
    if categoria_ids:
        consulta = consulta.where(Producto.categoria_id.in_(categoria_ids))
    if temporada_id is not None:
        consulta = consulta.where(Producto.temporada_id == temporada_id)
    if coleccion_id is not None:
        consulta = consulta.where(Producto.coleccion_id == coleccion_id)
    if talla_id is not None:
        consulta = consulta.where(
            exists(
                select(VarianteProducto.id).where(
                    _variante_ofrecible(), VarianteProducto.talla_id == talla_id
                )
            )
        )
    if color_id is not None:
        consulta = consulta.where(
            exists(
                select(VarianteProducto.id).where(
                    _variante_ofrecible(), VarianteProducto.color_id == color_id
                )
            )
        )
    if precio_min is not None:
        consulta = consulta.where(
            exists(
                select(VarianteProducto.id).where(
                    _variante_ofrecible(), VarianteProducto.precio >= precio_min
                )
            )
        )
    if precio_max is not None:
        consulta = consulta.where(
            exists(
                select(VarianteProducto.id).where(
                    _variante_ofrecible(), VarianteProducto.precio <= precio_max
                )
            )
        )
    return consulta


#: Precio mas bajo entre las variantes ofrecibles del producto de la fila.
#: Es subconsulta correlacionada y no un JOIN con GROUP BY porque se necesita
#: como expresion de ORDER BY, donde un agregado obligaria a agrupar toda la
#: consulta por cada columna del producto.
_PRECIO_DESDE = (
    select(func.min(VarianteProducto.precio))
    .where(_variante_ofrecible())
    .correlate(Producto)
    .scalar_subquery()
)

#: Los ordenamientos que admite la vitrina. La clave es lo que viaja por la URL.
ORDENES = {
    "novedades": (Producto.id.desc(),),
    "precio_asc": (_PRECIO_DESDE.asc(), Producto.id.asc()),
    "precio_desc": (_PRECIO_DESDE.desc(), Producto.id.asc()),
    "nombre": (Producto.nombre.asc(), Producto.id.asc()),
}


def contar_productos(db: Session, **filtros) -> int:
    consulta = _filtrar(select(func.count()).select_from(Producto), **filtros)
    return db.scalar(consulta) or 0


def listar_productos(
    db: Session, *, limite: int, desplazamiento: int, orden: str, **filtros
) -> list[Producto]:
    """Una pagina de la vitrina.

    Todo ordenamiento termina desempatando por `id`. Sin desempate, dos
    productos del mismo precio pueden salir en distinto orden entre la pagina 1
    y la 2, y el mismo producto aparecer dos veces o ninguna.
    """
    consulta = _filtrar(select(Producto), **filtros)
    consulta = consulta.order_by(*ORDENES[orden]).limit(limite).offset(desplazamiento)
    return list(db.scalars(consulta))


def rango_de_precios(db: Session, producto_ids: list[int]) -> dict[int, tuple[Decimal, Decimal]]:
    """Precio minimo y maximo de las variantes activas, por producto.

    Una sola consulta agregada para toda la pagina. La vitrina muestra «desde
    Bs 180» cuando las variantes valen distinto, asi que necesita los dos
    extremos y no un precio suelto.
    """
    if not producto_ids:
        return {}
    filas = db.execute(
        select(
            VarianteProducto.producto_id,
            func.min(VarianteProducto.precio),
            func.max(VarianteProducto.precio),
        )
        .where(
            VarianteProducto.producto_id.in_(producto_ids),
            VarianteProducto.activa.is_(True),
        )
        .group_by(VarianteProducto.producto_id)
    ).all()
    return {fila[0]: (fila[1], fila[2]) for fila in filas}


def imagen_principal(db: Session, producto_ids: list[int]) -> dict[int, str]:
    """La ruta de la imagen principal de cada producto de la pagina.

    Si un producto no tiene ninguna marcada como principal se toma la de menor
    `orden`: el indice parcial garantiza que no haya DOS principales, no que
    haya una. `DISTINCT ON` deja una fila por producto en una sola consulta.
    """
    if not producto_ids:
        return {}
    filas = db.execute(
        select(ImagenProducto.producto_id, ImagenProducto.ruta)
        .where(
            ImagenProducto.producto_id.in_(producto_ids),
            # La transparente es el activo del vestidor virtual, no una foto de
            # catalogo: mostrarla en la vitrina se veria como un recorte suelto.
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
    return {fila[0]: fila[1] for fila in filas}


def colores_por_producto(
    db: Session, producto_ids: list[int]
) -> dict[int, list[tuple[int, str, str]]]:
    """Los colores en los que se ofrece cada producto, para las muestras del listado."""
    if not producto_ids:
        return {}
    filas = db.execute(
        select(
            VarianteProducto.producto_id,
            Color.id,
            Color.nombre,
            Color.hexadecimal,
        )
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(
            VarianteProducto.producto_id.in_(producto_ids),
            VarianteProducto.activa.is_(True),
        )
        .distinct()
        .order_by(VarianteProducto.producto_id, Color.nombre)
    ).all()
    agrupado: dict[int, list[tuple[int, str, str]]] = {}
    for producto_id, color_id, nombre, hexadecimal in filas:
        agrupado.setdefault(producto_id, []).append((color_id, nombre, hexadecimal))
    return agrupado


def variantes_con_vestidor(db: Session, producto_ids: list[int]) -> set[int]:
    """Los productos que tienen al menos un PNG transparente de vestidor.

    Es lo que decide si la ficha muestra el boton «Probar en vestidor virtual».
    Viaja ya en el listado para que la vitrina pueda rotular las prendas que se
    pueden probar sin abrir una por una.
    """
    if not producto_ids:
        return set()
    return set(
        db.scalars(
            select(ImagenProducto.producto_id)
            .where(
                ImagenProducto.producto_id.in_(producto_ids),
                ImagenProducto.es_transparente.is_(True),
                ImagenProducto.variante_id.is_not(None),
            )
            .distinct()
        )
    )


# --- La ficha (CU-18) ----------------------------------------------------

def obtener_producto(db: Session, producto_id: int) -> Producto | None:
    """El producto con sus variantes y los maestros de cada una ya cargados.

    `selectinload` resuelve toda la ficha en un numero fijo de consultas; sin el,
    dibujar el selector de tallas dispara una consulta por talla y otra por
    color de cada variante.

    Trae tambien las inactivas: filtrarlas es decision del servicio, que es
    quien sabe que la vitrina solo ofrece lo comprable. El repositorio devuelve
    lo que hay.
    """
    return db.scalar(
        select(Producto)
        .where(Producto.id == producto_id)
        .options(
            selectinload(Producto.variantes).selectinload(VarianteProducto.talla),
            selectinload(Producto.variantes).selectinload(VarianteProducto.color),
        )
    )


def imagenes_de_producto(db: Session, producto_id: int) -> list[ImagenProducto]:
    """La galeria completa, en el orden en que el administrador la dejo."""
    return list(
        db.scalars(
            select(ImagenProducto)
            .where(ImagenProducto.producto_id == producto_id)
            .order_by(
                ImagenProducto.es_principal.desc(),
                ImagenProducto.orden,
                ImagenProducto.id,
            )
        )
    )


def rutas_de_vestidor(db: Session, producto_id: int) -> dict[int, str]:
    """La ruta del PNG transparente de cada variante del producto.

    Es la mitad de la costura C5: la ficha entrega, por variante, el activo que
    el vestidor virtual necesita, para que la pantalla de realidad aumentada no
    tenga que volver a consultar la API ni conocer la tabla de imagenes. El
    indice parcial uq_imagen_transparente_variante garantiza uno por variante,
    asi que el diccionario no pierde nada.
    """
    filas = db.execute(
        select(ImagenProducto.variante_id, ImagenProducto.ruta).where(
            ImagenProducto.producto_id == producto_id,
            ImagenProducto.es_transparente.is_(True),
            ImagenProducto.variante_id.is_not(None),
        )
    ).all()
    return {fila[0]: fila[1] for fila in filas}


def variante_ofrecible(db: Session, variante_id: int) -> VarianteProducto | None:
    """La variante, si existe y se puede ofrecer (CU-19).

    «Ofrecible» es lo mismo que en el resto del paquete: variante activa de un
    producto activo. Se comprueba antes de consultar el inventario para que la
    disponibilidad no se convierta en una puerta trasera --- sin esto, una
    variante retirada del catalogo seguiria diciendo en que sucursales hay
    stock de ella.
    """
    return db.scalar(
        select(VarianteProducto)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .where(
            VarianteProducto.id == variante_id,
            VarianteProducto.activa.is_(True),
            Producto.activo.is_(True),
        )
        .options(
            selectinload(VarianteProducto.talla),
            selectinload(VarianteProducto.color),
            selectinload(VarianteProducto.producto),
        )
    )


def nombre_de_categoria(db: Session, categoria_id: int) -> str | None:
    return db.scalar(select(Categoria.nombre).where(Categoria.id == categoria_id))


def nombres_de_categorias(db: Session, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    filas = db.execute(
        select(Categoria.id, Categoria.nombre).where(Categoria.id.in_(ids))
    ).all()
    return {fila[0]: fila[1] for fila in filas}


# --- Las opciones de filtrado (paso 2 de CU-17) --------------------------
# La vitrina es publica y los maestros de CU-08 y CU-09 solo los sirve el router
# de Administrador. Sin estas consultas, el cliente no tendria de donde sacar la
# lista de tallas o de colores para armar los filtros.
#
# Las cuatro devuelven solo lo que EL CATALOGO OFRECE, no el maestro entero: una
# talla que ningun producto activo usa es una opcion que al elegirla vacia la
# vitrina, y el cliente no tiene forma de saber por que.

def categorias_con_oferta(db: Session) -> list[Categoria]:
    return list(
        db.scalars(
            select(Categoria)
            .where(
                Categoria.activa.is_(True),
                exists(
                    select(Producto.id).where(
                        Producto.categoria_id == Categoria.id,
                        Producto.activo.is_(True),
                    )
                ),
            )
            .order_by(Categoria.orden, Categoria.nombre)
        )
    )


def tallas_con_oferta(db: Session) -> list[Talla]:
    return list(
        db.scalars(
            select(Talla)
            .where(
                Talla.activa.is_(True),
                exists(
                    select(VarianteProducto.id)
                    .join(Producto, Producto.id == VarianteProducto.producto_id)
                    .where(
                        VarianteProducto.talla_id == Talla.id,
                        VarianteProducto.activa.is_(True),
                        Producto.activo.is_(True),
                    )
                ),
            )
            .order_by(Talla.tipo_prenda, Talla.orden, Talla.codigo)
        )
    )


def colores_con_oferta(db: Session) -> list[Color]:
    return list(
        db.scalars(
            select(Color)
            .where(
                Color.activo.is_(True),
                exists(
                    select(VarianteProducto.id)
                    .join(Producto, Producto.id == VarianteProducto.producto_id)
                    .where(
                        VarianteProducto.color_id == Color.id,
                        VarianteProducto.activa.is_(True),
                        Producto.activo.is_(True),
                    )
                ),
            )
            .order_by(Color.nombre)
        )
    )


def temporadas_con_oferta(db: Session) -> list[Temporada]:
    return list(
        db.scalars(
            select(Temporada)
            .where(
                Temporada.activa.is_(True),
                exists(
                    select(Producto.id).where(
                        Producto.temporada_id == Temporada.id,
                        Producto.activo.is_(True),
                    )
                ),
            )
            .order_by(Temporada.fecha_inicio.desc())
        )
    )


def colecciones_con_oferta(db: Session) -> list[Coleccion]:
    return list(
        db.scalars(
            select(Coleccion)
            .where(
                Coleccion.activa.is_(True),
                exists(
                    select(Producto.id).where(
                        Producto.coleccion_id == Coleccion.id,
                        Producto.activo.is_(True),
                    )
                ),
            )
            .order_by(Coleccion.nombre)
        )
    )


def extremos_de_precio(db: Session) -> tuple[Decimal | None, Decimal | None]:
    """El precio mas bajo y el mas alto de todo lo ofrecible.

    Es lo que fija los topes del control deslizante de precio. Calcularlo en la
    interfaz exigiria traer el catalogo entero.
    """
    fila = db.execute(
        select(func.min(VarianteProducto.precio), func.max(VarianteProducto.precio))
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .where(VarianteProducto.activa.is_(True), Producto.activo.is_(True))
    ).one()
    return fila[0], fila[1]


# --- CU-20 · Favoritos ----------------------------------------------------

def ids_de_favoritos(db: Session, cliente_id: int) -> list[int]:
    """Los identificadores de producto que el cliente marco.

    Se devuelve la lista pelada y no las tarjetas: es lo que la vitrina necesita
    para pintar los corazones, y traer el producto entero de cada uno solo para
    saber cuales estan marcados seria pedir de mas.
    """
    return list(
        db.scalars(
            select(Favorito.producto_id).where(Favorito.cliente_id == cliente_id)
        )
    )


def es_favorito(db: Session, cliente_id: int, producto_id: int) -> bool:
    return (
        db.scalar(
            select(Favorito.producto_id).where(
                Favorito.cliente_id == cliente_id,
                Favorito.producto_id == producto_id,
            )
        )
        is not None
    )


def agregar_favorito(db: Session, cliente_id: int, producto_id: int) -> None:
    """Marca la prenda. Si ya estaba, no hace nada.

    La comprobacion previa evita chocar contra la clave primaria compuesta; la
    clave sigue siendo la garantia de que no se duplique, pero preguntar antes
    convierte un error de base en una operacion idempotente, que es lo que el
    endpoint promete.
    """
    if es_favorito(db, cliente_id, producto_id):
        return
    db.add(Favorito(cliente_id=cliente_id, producto_id=producto_id))
    db.flush()


def quitar_favorito(db: Session, cliente_id: int, producto_id: int) -> None:
    """Desmarca la prenda. Si no estaba, no hace nada: tambien es idempotente."""
    db.execute(
        delete(Favorito).where(
            Favorito.cliente_id == cliente_id, Favorito.producto_id == producto_id
        )
    )
    db.flush()


def _favoritos_ofrecibles(cliente_id: int):
    """La condicion del listado de favoritos.

    Solo se listan los que **siguen siendo ofrecibles**: producto activo y con
    al menos una variante activa, igual que en la vitrina. La fila del favorito
    NO se borra cuando el producto se desactiva --- es historial de preferencia
    y el recomendador del CU-33 lo usa (RF31) --- pero mostrarlo seria ofrecer
    algo que no se puede comprar.
    """
    return (
        select(Producto)
        .join(Favorito, Favorito.producto_id == Producto.id)
        .where(
            Favorito.cliente_id == cliente_id,
            Producto.activo.is_(True),
            exists(select(VarianteProducto.id).where(_variante_ofrecible())),
        )
    )


def contar_favoritos(db: Session, cliente_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(
                _favoritos_ofrecibles(cliente_id).subquery()
            )
        )
        or 0
    )


def listar_favoritos(
    db: Session, cliente_id: int, *, limite: int, desplazamiento: int
) -> list[Producto]:
    """Una pagina de favoritos, lo ultimo marcado primero.

    El orden es por `creado_en` descendente y desempata por `id`: sin desempate,
    dos prendas marcadas en el mismo instante --- que es posible, porque el
    `server_default` es `now()` y dos altas en la misma transaccion comparten
    marca --- podrian salir en distinto orden entre dos paginas.
    """
    return list(
        db.scalars(
            _favoritos_ofrecibles(cliente_id)
            .order_by(Favorito.creado_en.desc(), Producto.id.desc())
            .limit(limite)
            .offset(desplazamiento)
        )
    )

