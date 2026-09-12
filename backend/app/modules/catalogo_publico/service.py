"""
P5 - Catalogo Publico / CU-17 y CU-18  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2
Casos de uso:
  CU-17 Consultar catalogo
  CU-18 Consultar ficha de producto

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

Los dos casos de uso son de solo lectura, asi que no hay transaccion que
controlar. Lo que si vive aqui es la regla que los define: **la vitrina solo
ofrece lo comprable**. Producto inactivo, o sin ninguna variante activa, no
existe para el cliente --- ni en el listado, ni en la ficha.
"""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.catalogo import imagenes_almacen as almacen
# Costura C1: la unica lectura de `existencia` que hace P5 pasa por aqui.
# Es una importacion de funcion, no un SELECT sobre una tabla ajena ni una
# llamada HTTP interna --- el contrato esta en la seccion 6 del documento de
# organizacion del ciclo.
from app.modules.inventario import service as inventario
# Costura P5 -> P1: quien es el cliente del token lo resuelve el dueno de
# `cliente`, que es P1. Mismo criterio que la costura C1.
from app.modules.seguridad import service as seguridad
from app.modules.catalogo_publico import repository
from app.modules.catalogo_publico.schemas import (
    CategoriaOut,
    ColeccionOut,
    ColorOut,
    FichaProductoOut,
    FiltrosOut,
    DisponibilidadOut,
    DisponibilidadSucursalOut,
    ImagenVitrinaOut,
    PaginaFavoritos,
    PaginaVitrina,
    ProductoVitrinaOut,
    TallaOut,
    TemporadaOut,
    VarianteVitrinaOut,
)


# --- Errores de negocio --------------------------------------------------

class ErrorDeVitrina(Exception):
    """Base de los errores previstos de CU-17 y CU-18."""


class VarianteNoDisponible(ErrorDeVitrina):
    """Excepcion E1 de CU-19.

    Igual que en CU-18: la variante no existe, esta desactivada, o su producto
    lo esta. Las tres se responden igual para que recorrer identificadores no
    delate lo que esta retirado del catalogo.
    """


class ProductoNoDisponible(ErrorDeVitrina):
    """Excepcion E1 de CU-18.

    Cubre tres situaciones que el cliente no puede distinguir y que a proposito
    se responden igual: el producto no existe, esta desactivado, o no le queda
    ninguna variante activa. Responder distinto convertiria la ficha en un
    detector de productos ocultos --- bastaria recorrer identificadores para saber
    cuales existen desactivados y cuantos hay.
    """


# --- CU-17 · Consultar catalogo ------------------------------------------

def listar_productos(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    orden: str = "novedades",
    busqueda: str | None = None,
    categoria_id: int | None = None,
    talla_id: int | None = None,
    color_id: int | None = None,
    temporada_id: int | None = None,
    coleccion_id: int | None = None,
    precio_min: Decimal | None = None,
    precio_max: Decimal | None = None,
) -> PaginaVitrina:
    """Paso 2: la vitrina con sus filtros, su orden y su paginacion.

    Filtrar por categoria incluye a sus descendientes: elegir «Mujer» tiene que
    devolver lo que esta cargado en «Mujer > Blusas», que es donde estan los
    productos de verdad.

    **Falta el filtro por sucursal**, que el caso de uso tambien enuncia. Depende
    de `existencia`, que es tabla de Mateo, y entra por la costura C1 junto con
    CU-19 --- ver la seccion 6.1 del documento de organizacion. Se deja fuera en
    vez de declararlo y no aplicarlo: un filtro que no filtra es peor que uno que
    todavia no esta.
    """
    categoria_ids = (
        repository.ids_de_categoria_y_descendientes(db, categoria_id)
        if categoria_id is not None
        else None
    )

    filtros = dict(
        busqueda=busqueda,
        categoria_ids=categoria_ids,
        talla_id=talla_id,
        color_id=color_id,
        temporada_id=temporada_id,
        coleccion_id=coleccion_id,
        precio_min=precio_min,
        precio_max=precio_max,
    )

    total = repository.contar_productos(db, **filtros)
    productos = repository.listar_productos(
        db,
        limite=tamano,
        desplazamiento=(pagina - 1) * tamano,
        orden=orden,
        **filtros,
    )

    return PaginaVitrina(
        total=total, pagina=pagina, tamano=tamano, items=_tarjetas(db, productos)
    )


def _tarjetas(db: Session, productos: list) -> list[ProductoVitrinaOut]:
    """Arma las tarjetas de una pagina de productos.

    Esta en una funcion porque la usan la vitrina (CU-17) y los favoritos
    (CU-20), que muestran exactamente la misma tarjeta. Duplicarla obligaria a
    agregar dos veces cada dato nuevo, y el dia que difieran la pantalla de
    favoritos mostraria una prenda distinta de como la muestra el catalogo.

    Todo lo que la tarjeta necesita se resuelve en **cinco consultas agregadas
    para la pagina entera**, no en cinco por producto.
    """
    if not productos:
        return []

    ids = [p.id for p in productos]
    precios = repository.rango_de_precios(db, ids)
    imagenes = repository.imagen_principal(db, ids)
    colores = repository.colores_por_producto(db, ids)
    con_vestidor = repository.variantes_con_vestidor(db, ids)
    categorias = repository.nombres_de_categorias(db, [p.categoria_id for p in productos])

    items = []
    for producto in productos:
        fila = ProductoVitrinaOut.model_validate(producto, from_attributes=True)
        fila.categoria_nombre = categorias.get(producto.categoria_id)
        fila.precio_desde, fila.precio_hasta = precios.get(producto.id, (None, None))
        ruta = imagenes.get(producto.id)
        fila.imagen_url = almacen.url_de(ruta) if ruta else None
        fila.colores = [
            ColorOut(id=cid, nombre=nombre, hexadecimal=hexadecimal)
            for cid, nombre, hexadecimal in colores.get(producto.id, [])
        ]
        fila.tiene_vestidor = producto.id in con_vestidor
        items.append(fila)
    return items


# --- CU-18 · Consultar ficha de producto ---------------------------------

def obtener_ficha(db: Session, producto_id: int) -> FichaProductoOut:
    """Paso 3: el detalle de una prenda, con su galeria y sus variantes.

    Las variantes inactivas se descartan aqui y no en el repositorio: la regla
    «solo se ofrece lo comprable» es de negocio, y el repositorio devuelve lo
    que hay.
    """
    producto = repository.obtener_producto(db, producto_id)
    if producto is None or not producto.activo:
        raise ProductoNoDisponible(str(producto_id))

    ofrecibles = [v for v in producto.variantes if v.activa]
    if not ofrecibles:
        # Sin variantes activas no hay nada que elegir, ni precio que mostrar,
        # ni SKU que reservar. Es la misma respuesta que un producto inactivo.
        raise ProductoNoDisponible(str(producto_id))

    # Los campos se copian a mano en vez de con `model_validate(producto)`, y no
    # es verbosidad: `imagenes` y `variantes` se llaman igual en el esquema y en
    # el modelo, asi que la validacion desde atributos intentaria construir la
    # galeria a partir de la relacion del ORM --- que no tiene `url`, porque la
    # arma el servidor --- y fallaria antes de llegar a la linea que si la arma.
    ficha = FichaProductoOut(
        id=producto.id,
        codigo=producto.codigo,
        nombre=producto.nombre,
        descripcion=producto.descripcion,
        categoria_id=producto.categoria_id,
        categoria_nombre=repository.nombre_de_categoria(db, producto.categoria_id),
        temporada_id=producto.temporada_id,
        coleccion_id=producto.coleccion_id,
    )

    precios = [v.precio for v in ofrecibles]
    ficha.precio_desde = min(precios)
    ficha.precio_hasta = max(precios)

    vestidor = repository.rutas_de_vestidor(db, producto_id)
    ficha.variantes = [_variante(v, vestidor) for v in _ordenadas(ofrecibles)]
    ficha.tiene_vestidor = any(v.imagen_vestidor_url for v in ficha.variantes)

    ficha.imagenes = [
        ImagenVitrinaOut(
            id=imagen.id,
            url=almacen.url_de(imagen.ruta),
            variante_id=imagen.variante_id,
            es_principal=imagen.es_principal,
            orden=imagen.orden,
        )
        for imagen in repository.imagenes_de_producto(db, producto_id)
        # La transparente es el activo del vestidor, no una foto de la galeria:
        # viaja dentro de su variante, no suelta entre las fotos del producto.
        if not imagen.es_transparente
    ]

    ficha.tallas, ficha.colores = _opciones(ofrecibles)
    return ficha


def _ordenadas(variantes: list) -> list:
    """Las variantes en el orden en que la ficha las muestra.

    Por talla y despues por color. El orden de la talla es el del maestro y no
    el alfabetico: sin el, XL aparece antes que S --- es para lo que existe
    `Talla.orden`, y la ficha es donde se nota.
    """
    return sorted(
        variantes,
        key=lambda v: (
            v.talla.orden if v.talla else 0,
            v.talla.codigo if v.talla else "",
            v.color.nombre if v.color else "",
        ),
    )


def _variante(variante, vestidor: dict[int, str]) -> VarianteVitrinaOut:
    salida = VarianteVitrinaOut.model_validate(variante, from_attributes=True)
    if variante.talla is not None:
        salida.talla_codigo = variante.talla.codigo
    if variante.color is not None:
        salida.color_nombre = variante.color.nombre
        salida.color_hexadecimal = variante.color.hexadecimal
    ruta = vestidor.get(variante.id)
    salida.imagen_vestidor_url = almacen.url_de(ruta) if ruta else None
    return salida


def _opciones(variantes: list) -> tuple[list[TallaOut], list[ColorOut]]:
    """Las tallas y los colores distintos en los que se ofrece el producto.

    Se recorren las variantes ya cargadas en vez de consultar de nuevo: los
    maestros vinieron con `selectinload` y volver a la base seria pedir lo que
    ya esta en memoria.
    """
    tallas: dict[int, TallaOut] = {}
    colores: dict[int, ColorOut] = {}
    for variante in variantes:
        if variante.talla is not None and variante.talla_id not in tallas:
            tallas[variante.talla_id] = TallaOut.model_validate(
                variante.talla, from_attributes=True
            )
        if variante.color is not None and variante.color_id not in colores:
            colores[variante.color_id] = ColorOut.model_validate(
                variante.color, from_attributes=True
            )
    return (
        sorted(tallas.values(), key=lambda t: (t.orden, t.codigo)),
        sorted(colores.values(), key=lambda c: c.nombre),
    )


# --- CU-19 · Consultar disponibilidad por sucursal ------------------------

def disponibilidad_de_variante(db: Session, variante_id: int) -> DisponibilidadOut:
    """Paso 2: en que sucursales hay stock de la variante elegida.

    Dos pasos, y el orden importa:

    1. **Se comprueba que la variante sea ofrecible**, con tablas de P3. Sin
       esto, una variante retirada del catalogo seguiria informando donde hay
       stock de ella --- la disponibilidad seria una puerta trasera a lo que el
       resto del paquete oculta.
    2. **Se pide el stock por la costura C1.** `existencia` es de Mateo; P5 no
       la consulta, importa la funcion que su servicio expone.

    Las sucursales sin stock se descartan aca y no en el inventario: para
    Mateo, un saldo en cero es un dato legitimo --- es lo que hace falta para
    reponer ---; para la vitrina es ruido.
    """
    variante = repository.variante_ofrecible(db, variante_id)
    if variante is None:
        raise VarianteNoDisponible(str(variante_id))

    filas = inventario.disponibilidad_por_sucursal(db, variante_id)
    sucursales = [
        DisponibilidadSucursalOut(**fila)
        for fila in filas
        if fila["cantidad_disponible"] > 0
    ]

    return DisponibilidadOut(
        variante_id=variante.id,
        sku=variante.sku,
        talla_codigo=variante.talla.codigo if variante.talla else None,
        color_nombre=variante.color.nombre if variante.color else None,
        total_disponible=sum(s.cantidad_disponible for s in sucursales),
        sucursales=sucursales,
    )


# --- CU-20 · Favoritos ----------------------------------------------------

def _cliente(db: Session, usuario_id: int) -> int:
    """El cliente del token, por la costura con P1.

    Si la cuenta no tiene ficha de cliente --- un Administrador, por ejemplo ---
    P1 levanta `PerfilInexistente` y el router lo traduce a 403. P5 no necesita
    saber como se resuelve.
    """
    return seguridad.cliente_id_de_usuario(db, usuario_id)


def listar_favoritos(
    db: Session, usuario_id: int, *, pagina: int, tamano: int
) -> PaginaFavoritos:
    """Paso 2 de CU-20: la lista del cliente, lo ultimo marcado primero."""
    cliente_id = _cliente(db, usuario_id)
    total = repository.contar_favoritos(db, cliente_id)
    productos = repository.listar_favoritos(
        db, cliente_id, limite=tamano, desplazamiento=(pagina - 1) * tamano
    )
    return PaginaFavoritos(
        total=total, pagina=pagina, tamano=tamano, items=_tarjetas(db, productos)
    )


def ids_de_favoritos(db: Session, usuario_id: int) -> list[int]:
    """Los identificadores marcados, para pintar los corazones de la vitrina.

    Va aparte del listado y no como un campo de la tarjeta porque **la vitrina
    es publica**: agregarle `es_favorito` obligaria a que CU-17 supiera quien
    esta mirando, y hoy no lo sabe ni tiene por que. La pantalla pide esta lista
    una vez al entrar, si hay sesion de Cliente, y marca las tarjetas del lado
    del navegador.
    """
    return repository.ids_de_favoritos(db, _cliente(db, usuario_id))


def marcar_favorito(db: Session, usuario_id: int, producto_id: int) -> None:
    """Paso 3: marca la prenda.

    **Es idempotente**: marcar dos veces deja lo mismo y responde igual. El
    corazon de una interfaz se puede tocar dos veces sin querer, y fallar por
    eso seria convertir un doble toque en un error.

    Solo se puede marcar lo ofrecible. Sin esta comprobacion, el favorito seria
    una forma de guardar referencias a productos que el catalogo oculta.
    """
    cliente_id = _cliente(db, usuario_id)

    producto = repository.obtener_producto(db, producto_id)
    if (
        producto is None
        or not producto.activo
        or not any(v.activa for v in producto.variantes)
    ):
        # Las tres situaciones se responden igual, por el mismo motivo que en
        # CU-18: distinguirlas convertiria el favorito en un detector de
        # productos ocultos.
        raise ProductoNoDisponible(str(producto_id))

    repository.agregar_favorito(db, cliente_id, producto_id)
    db.commit()


def desmarcar_favorito(db: Session, usuario_id: int, producto_id: int) -> None:
    """Paso 4: quita la prenda de la lista.

    Tambien es idempotente, y **a proposito no comprueba que el producto siga
    siendo ofrecible**: si una prenda se desactivo despues de marcarla, el
    cliente tiene que poder sacarla igual. Exigir que sea ofrecible para
    desmarcar dejaria favoritos imposibles de borrar.
    """
    repository.quitar_favorito(db, _cliente(db, usuario_id), producto_id)
    db.commit()


# --- Opciones de filtrado ------------------------------------------------

def obtener_filtros(db: Session) -> FiltrosOut:
    """Las opciones del panel de filtros, con lo que el catalogo realmente ofrece."""
    precio_min, precio_max = repository.extremos_de_precio(db)
    return FiltrosOut(
        categorias=[
            CategoriaOut.model_validate(c, from_attributes=True)
            for c in repository.categorias_con_oferta(db)
        ],
        tallas=[
            TallaOut.model_validate(t, from_attributes=True)
            for t in repository.tallas_con_oferta(db)
        ],
        colores=[
            ColorOut.model_validate(c, from_attributes=True)
            for c in repository.colores_con_oferta(db)
        ],
        temporadas=[
            TemporadaOut.model_validate(t, from_attributes=True)
            for t in repository.temporadas_con_oferta(db)
        ],
        colecciones=[
            ColeccionOut.model_validate(c, from_attributes=True)
            for c in repository.colecciones_con_oferta(db)
        ],
        precio_min=precio_min,
        precio_max=precio_max,
    )


__all__ = [
    "ErrorDeVitrina",
    "ProductoNoDisponible",
    "VarianteNoDisponible",
    "desmarcar_favorito",
    "ids_de_favoritos",
    "listar_favoritos",
    "marcar_favorito",
    "disponibilidad_de_variante",
    "listar_productos",
    "obtener_ficha",
    "obtener_filtros",
]
