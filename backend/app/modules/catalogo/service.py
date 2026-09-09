"""
P3 - Catalogo / CU-10  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2
Caso de uso: CU-10 Gestionar productos y variantes

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.
"""
import unicodedata
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalogo import repository
from app.modules.catalogo.models import Producto, VarianteProducto
from app.modules.catalogo.schemas import (
    CambioEstadoIn,
    GenerarVariantesIn,
    GenerarVariantesOut,
    PaginaProductos,
    ProductoCrearIn,
    ProductoEditarIn,
    ProductoOut,
    ProductoResumenOut,
    VarianteCrearIn,
    VarianteEditarIn,
    VarianteOut,
)


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeProductos(Exception):
    """Base de los errores previstos de CU-10."""


class ProductoInexistente(ErrorDeProductos):
    """No hay producto con ese identificador."""


class VarianteInexistente(ErrorDeProductos):
    """No hay variante con ese identificador."""


class MaestroInexistente(ErrorDeProductos):
    """La categoria, el proveedor, la temporada, la talla o el color no existen."""


class CodigoDuplicado(ErrorDeProductos):
    """Excepcion E1: ya hay un producto con ese codigo, o una variante con ese SKU."""


class ColeccionAjenaALaTemporada(ErrorDeProductos):
    """Excepcion E2: la coleccion elegida pertenece a otra temporada."""


class TieneDependencias(ErrorDeProductos):
    """Excepcion E3: algo referencia al producto o a la variante."""


class SkuDemasiadoLargo(ErrorDeProductos):
    """El codigo del producto no deja lugar para armar un SKU de 40 caracteres."""


#: Restricciones de unicidad de la base, tal como se llaman en PostgreSQL.
#: Se nombran aqui por el mismo motivo que en CU-08: un nombre mal escrito hace
#: que el `except IntegrityError` no entre y un 409 salga como 500.
UQ_PRODUCTO_CODIGO = "uq_producto_codigo"
UQ_VARIANTE_SKU = "uq_variante_producto_sku"
UQ_VARIANTE_COMBINACION = "uq_variante_producto_talla_color"

#: Tope de `variante_producto.sku` en la seccion 6.4.
LARGO_SKU = 40
#: Cuanto del nombre del color entra en el SKU. Doce alcanza para distinguir
#: los colores de una tienda de ropa sin comerse el codigo del producto.
LARGO_COLOR_EN_SKU = 12


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    """Indica si la violacion corresponde a esa restriccion.

    Se apoya en la convencion de nombres de app/db/base.py.
    """
    return restriccion in str(exc.orig)


def _sin_tildes(texto: str) -> str:
    """Quita tildes y enes para que el SKU sea ASCII imprimible.

    Un SKU viaja a etiquetas, lectores de codigo de barras y archivos de
    intercambio, donde una 'ñ' no siempre sobrevive el viaje de ida y vuelta.
    """
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _parte_de_sku(texto: str, largo: int, *, con_guiones: bool = False) -> str:
    """Normaliza un trozo del SKU: mayusculas, sin tildes y sin separadores.

    El codigo del producto conserva sus guiones --- 'CAM-001' es como lo escribe
    y lo busca el Administrador, y comerselos daria 'CAM001', que no es el
    codigo de nada ---. La talla y el color no: ahi el guion es el separador
    entre las tres partes, y dejarlo pasar permitiria que un color llamado
    'Rojo-Azul' partiera el SKU en cuatro.
    """
    permitido = (lambda c: c.isalnum() or (con_guiones and c == "-"))
    limpio = "".join(c for c in _sin_tildes(texto).upper() if permitido(c))
    return limpio[:largo]


def armar_sku(codigo_producto: str, codigo_talla: str, nombre_color: str) -> str:
    """El SKU es legible y deterministico: CODIGO-TALLA-COLOR.

    Deterministico importa: la generacion masiva del paso 7 se puede repetir
    despues de agregar una talla, y tiene que producir exactamente los mismos
    SKU para las combinaciones que ya existian.

    Si no entra en los 40 caracteres NO se trunca. Truncar dos colores parecidos
    --- 'VERDE MILITAR' y 'VERDE MENTA' --- produciria el mismo SKU para dos
    variantes distintas, que es precisamente lo que un SKU no puede hacer. Se
    avisa y se pide acortar el codigo del producto.
    """
    sku = (
        f"{_parte_de_sku(codigo_producto, len(codigo_producto), con_guiones=True)}"
        f"-{_parte_de_sku(codigo_talla, len(codigo_talla))}"
        f"-{_parte_de_sku(nombre_color, LARGO_COLOR_EN_SKU)}"
    )
    if len(sku) > LARGO_SKU:
        raise SkuDemasiadoLargo(sku)
    return sku


# --- Armado de las respuestas -------------------------------------------

def _variante_out(variante: VarianteProducto) -> VarianteOut:
    salida = VarianteOut.model_validate(variante, from_attributes=True)
    # Los maestros vienen precargados por el repositorio; leerlos aqui no
    # dispara consultas nuevas.
    if variante.talla is not None:
        salida.talla_codigo = variante.talla.codigo
    if variante.color is not None:
        salida.color_nombre = variante.color.nombre
        salida.color_hexadecimal = variante.color.hexadecimal
    return salida


def _producto_out(db: Session, producto: Producto) -> ProductoOut:
    salida = ProductoOut.model_validate(producto, from_attributes=True)
    salida.categoria_nombre = repository.nombre_de_categoria(db, producto.categoria_id)
    variantes = sorted(
        producto.variantes,
        key=lambda v: (
            v.talla.orden if v.talla is not None else 0,
            v.color.nombre if v.color is not None else "",
        ),
    )
    salida.variantes = [_variante_out(v) for v in variantes]
    salida.variantes_totales = len(variantes)
    salida.variantes_activas = sum(1 for v in variantes if v.activa)
    salida.imagenes_totales, salida.variantes_con_vestidor = (
        repository.conteo_de_imagenes(db, [producto.id]).get(producto.id, (0, 0))
    )
    return salida


# --- Validaciones compartidas -------------------------------------------

def _validar_maestros(
    db: Session,
    *,
    categoria_id: int | None,
    proveedor_id: int | None,
    temporada_id: int | None,
) -> None:
    if categoria_id is not None and not repository.existe_categoria(db, categoria_id):
        raise MaestroInexistente(f"categoria {categoria_id}")
    if proveedor_id is not None and not repository.existe_proveedor(db, proveedor_id):
        raise MaestroInexistente(f"proveedor {proveedor_id}")
    if temporada_id is not None and not repository.existe_temporada(db, temporada_id):
        raise MaestroInexistente(f"temporada {temporada_id}")


def _resolver_temporada(
    db: Session, *, temporada_id: int | None, coleccion_id: int | None
) -> int | None:
    """Excepcion E2 y la regla de coherencia de la seccion 6.4, decision 2.

    El esquema guarda `temporada_id` y `coleccion_id` a la vez, que es
    redundante y se decidio conservar. El precio de esa decision se paga aqui:

    - si vienen las dos, la coleccion tiene que pertenecer a esa temporada;
    - si viene solo la coleccion, la temporada se completa a partir de ella en
      vez de quedar nula, que es lo que haria inconsistente al reporte de
      rotacion.
    """
    if coleccion_id is None:
        return temporada_id

    coleccion = repository.obtener_coleccion(db, coleccion_id)
    if coleccion is None:
        raise MaestroInexistente(f"coleccion {coleccion_id}")

    if temporada_id is None:
        return coleccion.temporada_id
    if coleccion.temporada_id != temporada_id:
        raise ColeccionAjenaALaTemporada(str(coleccion_id))
    return temporada_id


# --- Productos -----------------------------------------------------------

def listar_productos(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    busqueda: str | None = None,
    categoria_id: int | None = None,
    temporada_id: int | None = None,
    coleccion_id: int | None = None,
    proveedor_id: int | None = None,
    activo: bool | None = None,
) -> PaginaProductos:
    """Paso 2: el listado con sus filtros y su paginacion."""
    filtros = dict(
        busqueda=busqueda,
        categoria_id=categoria_id,
        temporada_id=temporada_id,
        coleccion_id=coleccion_id,
        proveedor_id=proveedor_id,
        activo=activo,
    )
    total = repository.contar_productos(db, **filtros)
    productos = repository.listar_productos(
        db, limite=tamano, desplazamiento=(pagina - 1) * tamano, **filtros
    )

    ids = [p.id for p in productos]
    conteos = repository.conteo_de_variantes(db, ids)
    imagenes = repository.conteo_de_imagenes(db, ids)
    categorias = repository.nombres_de_categorias(db, [p.categoria_id for p in productos])

    items = []
    for producto in productos:
        fila = ProductoResumenOut.model_validate(producto, from_attributes=True)
        fila.categoria_nombre = categorias.get(producto.categoria_id)
        fila.variantes_totales, fila.variantes_activas = conteos.get(producto.id, (0, 0))
        fila.imagenes_totales, fila.variantes_con_vestidor = imagenes.get(producto.id, (0, 0))
        items.append(fila)

    return PaginaProductos(total=total, pagina=pagina, tamano=tamano, items=items)


def obtener_producto(db: Session, producto_id: int) -> ProductoOut:
    producto = repository.obtener_producto(db, producto_id)
    if producto is None:
        raise ProductoInexistente(str(producto_id))
    return _producto_out(db, producto)


def crear_producto(db: Session, datos: ProductoCrearIn) -> ProductoOut:
    """Pasos 5 y 6: valida los maestros, la unicidad del codigo y registra."""
    _validar_maestros(
        db,
        categoria_id=datos.categoria_id,
        proveedor_id=datos.proveedor_id,
        temporada_id=datos.temporada_id,
    )
    temporada_id = _resolver_temporada(
        db, temporada_id=datos.temporada_id, coleccion_id=datos.coleccion_id
    )

    # Excepcion E1.
    if repository.existe_codigo(db, datos.codigo):
        raise CodigoDuplicado(datos.codigo)

    try:
        producto = repository.agregar_producto(
            db,
            codigo=datos.codigo,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            categoria_id=datos.categoria_id,
            proveedor_id=datos.proveedor_id,
            temporada_id=temporada_id,
            coleccion_id=datos.coleccion_id,
            precio_base=datos.precio_base,
            activo=datos.activo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_PRODUCTO_CODIGO):
            raise CodigoDuplicado(datos.codigo) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_producto(db, producto.id)


def editar_producto(db: Session, producto_id: int, datos: ProductoEditarIn) -> ProductoOut:
    """Flujo alternativo 3a."""
    producto = repository.obtener_producto(db, producto_id)
    if producto is None:
        raise ProductoInexistente(str(producto_id))

    enviado = datos.model_fields_set
    categoria_id = datos.categoria_id if "categoria_id" in enviado else producto.categoria_id
    proveedor_id = datos.proveedor_id if "proveedor_id" in enviado else producto.proveedor_id
    temporada_id = datos.temporada_id if "temporada_id" in enviado else producto.temporada_id
    coleccion_id = datos.coleccion_id if "coleccion_id" in enviado else producto.coleccion_id

    if categoria_id is None:
        # La categoria es obligatoria: mandarla en null no es «sacar de la
        # categoria», es dejar el producto fuera de la taxonomia.
        raise MaestroInexistente("categoria")

    _validar_maestros(
        db, categoria_id=categoria_id, proveedor_id=proveedor_id, temporada_id=temporada_id
    )
    temporada_id = _resolver_temporada(
        db, temporada_id=temporada_id, coleccion_id=coleccion_id
    )

    codigo = datos.codigo if datos.codigo is not None else producto.codigo
    if repository.existe_codigo(db, codigo, excepto_id=producto_id):
        raise CodigoDuplicado(codigo)

    try:
        producto.codigo = codigo
        if datos.nombre is not None:
            producto.nombre = datos.nombre
        if "descripcion" in enviado:
            producto.descripcion = datos.descripcion
        if datos.precio_base is not None:
            # No repropaga a las variantes: cada una tiene su precio desde que
            # nacio, y cambiarlo hacia atras alteraria el de variantes ya
            # vendidas. Es la decision 1 de la seccion 6.4.
            producto.precio_base = datos.precio_base
        producto.categoria_id = categoria_id
        producto.proveedor_id = proveedor_id
        producto.temporada_id = temporada_id
        producto.coleccion_id = coleccion_id
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_PRODUCTO_CODIGO):
            raise CodigoDuplicado(codigo) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_producto(db, producto_id)


def cambiar_estado_producto(
    db: Session, producto_id: int, datos: CambioEstadoIn
) -> ProductoOut:
    """Flujo alternativo 3b: desactivar en vez de borrar.

    Desactivar el producto desactiva tambien sus variantes: dejar una variante
    activa colgando de un producto retirado la haria aparecer en el inventario
    y en las reservas de un producto que ya no se ofrece.
    """
    producto = repository.obtener_producto(db, producto_id)
    if producto is None:
        raise ProductoInexistente(str(producto_id))

    try:
        producto.activo = datos.activo
        if not datos.activo:
            for variante in producto.variantes:
                variante.activa = False
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_producto(db, producto_id)


def eliminar_producto(db: Session, producto_id: int) -> None:
    """Excepcion E3.

    El borrado arrastra variantes e imagenes por el ON DELETE CASCADE. Lo que no
    arrastra son las tablas de Mateo --- `existencia` y `reserva_detalle`
    apuntan a la variante sin cascada ---, asi que si el producto ya tuvo stock
    o reservas, PostgreSQL rechaza el borrado y aqui se traduce en el aviso de
    desactivar. Es la misma respuesta que da CU-08 al eliminar un maestro en uso.
    """
    producto = repository.obtener_producto(db, producto_id)
    if producto is None:
        raise ProductoInexistente(str(producto_id))

    try:
        repository.eliminar_producto(db, producto)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TieneDependencias(str(producto_id)) from exc
    except Exception:
        db.rollback()
        raise


# --- Variantes -----------------------------------------------------------

def _precio_de(datos_precio: Decimal | None, producto: Producto) -> Decimal:
    """El precio de una variante nueva.

    Si no se indica, hereda el precio base del producto. Es una copia y no una
    referencia: es lo que dice la decision 1 de la seccion 6.4.
    """
    return datos_precio if datos_precio is not None else producto.precio_base


def generar_variantes(
    db: Session, producto_id: int, datos: GenerarVariantesIn
) -> GenerarVariantesOut:
    """Paso 7: el producto cartesiano de las tallas por los colores elegidos.

    Las combinaciones que ya existen se omiten en vez de fallar, para que volver
    a generar despues de agregar una talla no obligue a deseleccionar lo demas.
    """
    producto = repository.obtener_producto(db, producto_id)
    if producto is None:
        raise ProductoInexistente(str(producto_id))

    tallas = list(dict.fromkeys(datos.tallas))
    colores = list(dict.fromkeys(datos.colores))

    faltan_tallas = set(tallas) - repository.tallas_existentes(db, tallas)
    if faltan_tallas:
        raise MaestroInexistente(f"talla {sorted(faltan_tallas)[0]}")
    faltan_colores = set(colores) - repository.colores_existentes(db, colores)
    if faltan_colores:
        raise MaestroInexistente(f"color {sorted(faltan_colores)[0]}")

    codigos_talla = repository.codigos_de_talla(db, tallas)
    nombres_color = repository.nombres_de_color(db, colores)
    ya_estan = repository.combinaciones_existentes(db, producto_id)
    precio = _precio_de(datos.precio, producto)

    creadas: list[int] = []
    omitidas = 0
    try:
        for talla_id in tallas:
            for color_id in colores:
                if (talla_id, color_id) in ya_estan:
                    omitidas += 1
                    continue
                sku = armar_sku(
                    producto.codigo, codigos_talla[talla_id], nombres_color[color_id]
                )
                variante = repository.agregar_variante(
                    db,
                    producto_id=producto_id,
                    talla_id=talla_id,
                    color_id=color_id,
                    sku=sku,
                    precio=precio,
                    activa=True,
                )
                creadas.append(variante.id)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_VARIANTE_SKU):
            # Dos productos con codigos distintos pero que se normalizan igual
            # --- 'CAM 001' y 'CAM-001' --- producirian el mismo SKU.
            raise CodigoDuplicado("SKU") from exc
        raise
    except Exception:
        db.rollback()
        raise

    detalle = obtener_producto(db, producto_id)
    nuevas = [v for v in detalle.variantes if v.id in set(creadas)]
    return GenerarVariantesOut(creadas=len(creadas), omitidas=omitidas, variantes=nuevas)


def crear_variante(db: Session, producto_id: int, datos: VarianteCrearIn) -> VarianteOut:
    """Flujo alternativo 7a: una sola combinacion, sin generar el resto."""
    producto = repository.obtener_producto(db, producto_id)
    if producto is None:
        raise ProductoInexistente(str(producto_id))

    if not repository.tallas_existentes(db, [datos.talla_id]):
        raise MaestroInexistente(f"talla {datos.talla_id}")
    if not repository.colores_existentes(db, [datos.color_id]):
        raise MaestroInexistente(f"color {datos.color_id}")

    if (datos.talla_id, datos.color_id) in repository.combinaciones_existentes(db, producto_id):
        raise CodigoDuplicado(f"{datos.talla_id}/{datos.color_id}")

    codigo_talla = repository.codigos_de_talla(db, [datos.talla_id])[datos.talla_id]
    nombre_color = repository.nombres_de_color(db, [datos.color_id])[datos.color_id]
    sku = armar_sku(producto.codigo, codigo_talla, nombre_color)

    try:
        variante = repository.agregar_variante(
            db,
            producto_id=producto_id,
            talla_id=datos.talla_id,
            color_id=datos.color_id,
            sku=sku,
            precio=_precio_de(datos.precio, producto),
            activa=datos.activa,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_VARIANTE_SKU) or _viola(exc, UQ_VARIANTE_COMBINACION):
            raise CodigoDuplicado(sku) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return _variante_out(repository.obtener_variante(db, variante.id))


def editar_variante(db: Session, variante_id: int, datos: VarianteEditarIn) -> VarianteOut:
    """Flujo alternativo 7b: precio y estado. La talla y el color no se editan."""
    variante = repository.obtener_variante(db, variante_id)
    if variante is None:
        raise VarianteInexistente(str(variante_id))

    try:
        if datos.precio is not None:
            variante.precio = datos.precio
        if datos.activa is not None:
            variante.activa = datos.activa
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _variante_out(repository.obtener_variante(db, variante_id))


def eliminar_variante(db: Session, variante_id: int) -> None:
    """Excepcion E3 a nivel de variante.

    Igual que con el producto: si `existencia` o `reserva_detalle` ya la
    referencian, la clave foranea lo impide y se ofrece desactivarla.
    """
    variante = repository.obtener_variante(db, variante_id)
    if variante is None:
        raise VarianteInexistente(str(variante_id))

    try:
        repository.eliminar_variante(db, variante)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TieneDependencias(str(variante_id)) from exc
    except Exception:
        db.rollback()
        raise
