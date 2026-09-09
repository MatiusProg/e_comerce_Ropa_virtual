"""
P3 - Catalogo / CU-11  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2
Caso de uso: CU-11 Gestionar imagenes de producto

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

Este caso de uso tiene una particularidad que el resto no: escribe en DOS
lugares, la base y el volumen de archivos, y no hay transaccion que los abarque.
El orden esta elegido para que la unica inconsistencia posible sea la barata:

  - al crear se guarda PRIMERO el archivo y despues la fila; si la fila falla,
    se borra el archivo recien escrito;
  - al eliminar se borra PRIMERO la fila y despues el archivo.

Asi, si algo se corta a la mitad, lo que queda es un archivo huerfano en el
volumen --- invisible y sin costo mas que unos kilobytes --- y nunca una fila
que apunta a un archivo inexistente, que si se ve como una imagen rota.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalogo import imagenes_almacen as almacen
from app.modules.catalogo import imagenes_repository as repository
from app.modules.catalogo import repository as productos_repository
from app.modules.catalogo.imagenes_schemas import (
    ImagenEditarIn,
    ImagenOut,
    MarcarPrincipalIn,
    MarcarTransparenteIn,
    ReordenarIn,
)
from app.modules.catalogo.models import ImagenProducto


# --- Errores de negocio --------------------------------------------------

class ErrorDeImagenes(Exception):
    """Base de los errores previstos de CU-11."""


class ProductoInexistente(ErrorDeImagenes):
    """No hay producto con ese identificador."""


class ImagenInexistente(ErrorDeImagenes):
    """No hay imagen con ese identificador."""


class VarianteAjena(ErrorDeImagenes):
    """La variante existe, pero es de otro producto."""


class ArchivoInvalido(ErrorDeImagenes):
    """Excepciones E1 y E2: el archivo no sirve. El mensaje explica por que."""

    def __init__(self, motivo: str):
        super().__init__(motivo)
        self.motivo = motivo


class SinTransparencia(ErrorDeImagenes):
    """No se puede marcar para el vestidor virtual una imagen sin canal alfa."""


class TransparenteSinVariante(ErrorDeImagenes):
    """El PNG del vestidor pertenece a una variante concreta, no al producto."""


class ImagenAjena(ErrorDeImagenes):
    """Se intento reordenar con imagenes que no son de ese producto."""


#: Nombres de los indices parciales, tal como se llaman en PostgreSQL. Se
#: nombran aqui por el mismo motivo que en CU-08 y CU-10: un nombre mal escrito
#: hace que el `except IntegrityError` no entre y un 409 salga como 500.
UQ_PRINCIPAL = "uq_imagen_principal_producto"
UQ_TRANSPARENTE = "uq_imagen_transparente_variante"


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    return restriccion in str(exc.orig)


def _salida(imagen: ImagenProducto) -> ImagenOut:
    salida = ImagenOut.model_validate(imagen, from_attributes=True)
    salida.url = almacen.url_de(imagen.ruta)
    if imagen.variante is not None:
        salida.variante_sku = imagen.variante.sku
        talla = imagen.variante.talla.codigo if imagen.variante.talla else None
        color = imagen.variante.color.nombre if imagen.variante.color else None
        salida.variante_etiqueta = " · ".join(p for p in (talla, color) if p)
    return salida


def _traducir_error_de_archivo(exc: almacen.ErrorDeArchivo) -> ArchivoInvalido:
    """Convierte el problema tecnico del archivo en algo que se pueda leer."""
    if isinstance(exc, almacen.ArchivoVacio):
        return ArchivoInvalido("El archivo llegó vacío.")
    if isinstance(exc, almacen.ArchivoDemasiadoGrande):
        megas = almacen.TAMANO_MAXIMO // (1024 * 1024)
        return ArchivoInvalido(f"La imagen supera los {megas} MB permitidos.")
    if isinstance(exc, almacen.ImagenDemasiadoGrande):
        return ArchivoInvalido(
            f"La imagen supera los {almacen.LADO_MAXIMO} píxeles de lado."
        )
    formatos = ", ".join(sorted(almacen.FORMATOS))
    return ArchivoInvalido(f"El archivo no es una imagen {formatos} válida.")


def _asegurar_producto(db: Session, producto_id: int) -> None:
    if productos_repository.obtener_producto(db, producto_id) is None:
        raise ProductoInexistente(str(producto_id))


def _asegurar_variante(db: Session, *, producto_id: int, variante_id: int | None) -> None:
    if variante_id is None:
        return
    if repository.variante_de_producto(
        db, producto_id=producto_id, variante_id=variante_id
    ) is None:
        raise VarianteAjena(str(variante_id))


# --- Consulta ------------------------------------------------------------

def listar(db: Session, producto_id: int) -> list[ImagenOut]:
    """Paso 2: la galeria del producto."""
    _asegurar_producto(db, producto_id)
    return [_salida(i) for i in repository.listar_de_producto(db, producto_id)]


def obtener(db: Session, imagen_id: int) -> ImagenOut:
    imagen = repository.obtener(db, imagen_id)
    if imagen is None:
        raise ImagenInexistente(str(imagen_id))
    return _salida(imagen)


# --- Alta ----------------------------------------------------------------

def subir(
    db: Session,
    producto_id: int,
    *,
    contenido: bytes,
    variante_id: int | None = None,
) -> ImagenOut:
    """Pasos 3 y 4: valida el archivo, lo guarda en el volumen y registra la fila.

    La PRIMERA imagen de un producto queda como principal sin que haya que
    marcarla: un producto con fotos pero sin principal no se puede dibujar en el
    listado del catalogo, y esperar a que alguien se acuerde de marcarla es
    garantizar que algun producto salga sin foto.
    """
    _asegurar_producto(db, producto_id)
    _asegurar_variante(db, producto_id=producto_id, variante_id=variante_id)

    try:
        datos = almacen.inspeccionar(contenido)
    except almacen.ErrorDeArchivo as exc:
        raise _traducir_error_de_archivo(exc) from exc

    es_primera = repository.contar_de_producto(db, producto_id) == 0
    ruta = almacen.guardar(contenido, producto_id=producto_id, formato=datos.formato)

    try:
        imagen = repository.agregar(
            db,
            producto_id=producto_id,
            variante_id=variante_id,
            ruta=ruta,
            es_principal=es_primera,
            # La transparencia NO se declara al subir: se marca despues, con el
            # flujo 3c, y solo si la imagen pertenece a una variante. Aqui se
            # registra en falso aunque el archivo tenga alfa.
            es_transparente=False,
            orden=repository.siguiente_orden(db, producto_id),
        )
        db.commit()
    except Exception:
        db.rollback()
        # El archivo ya estaba escrito: se retira para no dejarlo huerfano.
        almacen.borrar(ruta)
        raise

    return obtener(db, imagen.id)


# --- Flujos alternativos -------------------------------------------------

def editar(db: Session, imagen_id: int, datos: ImagenEditarIn) -> ImagenOut:
    """Flujos 3a y 3d sobre una imagen: a que variante pertenece y su orden."""
    imagen = repository.obtener(db, imagen_id)
    if imagen is None:
        raise ImagenInexistente(str(imagen_id))

    enviado = datos.model_fields_set
    if "variante_id" in enviado:
        _asegurar_variante(
            db, producto_id=imagen.producto_id, variante_id=datos.variante_id
        )
        # Desasociar una imagen marcada para el vestidor la dejaria como PNG
        # transparente «del producto», que es una figura que no existe: el
        # vestidor superpone la prenda de UNA variante.
        if datos.variante_id is None and imagen.es_transparente:
            raise TransparenteSinVariante(str(imagen_id))

    try:
        if "variante_id" in enviado:
            imagen.variante_id = datos.variante_id
        if datos.orden is not None:
            imagen.orden = datos.orden
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_TRANSPARENTE):
            raise SinTransparencia(str(imagen_id)) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener(db, imagen_id)


def marcar_principal(
    db: Session, imagen_id: int, datos: MarcarPrincipalIn
) -> list[ImagenOut]:
    """Flujo alternativo 3b. Devuelve la galeria entera, no solo la imagen.

    Marcar una principal DESMARCA la anterior, asi que la respuesta de una sola
    imagen dejaria a la interfaz mostrando dos principales hasta la siguiente
    recarga. El indice parcial uq_imagen_principal_producto garantiza que no
    haya dos en la base; devolver la galeria garantiza que tampoco se vean dos
    en pantalla.
    """
    imagen = repository.obtener(db, imagen_id)
    if imagen is None:
        raise ImagenInexistente(str(imagen_id))

    try:
        if datos.es_principal:
            anterior = repository.principal_de(db, imagen.producto_id)
            if anterior is not None and anterior.id != imagen.id:
                anterior.es_principal = False
                # El flush intermedio no es opcional: sin el, PostgreSQL ve las
                # dos filas en true a la vez y el indice parcial rechaza el
                # cambio antes de que se limpie la anterior.
                db.flush()
        imagen.es_principal = datos.es_principal
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ErrorDeImagenes(str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return listar(db, imagen.producto_id)


def marcar_transparente(
    db: Session, imagen_id: int, datos: MarcarTransparenteIn
) -> list[ImagenOut]:
    """Flujo alternativo 3c: el activo del vestidor virtual (supuesto S5).

    Se verifica que el archivo tenga transparencia DE VERDAD, releyendolo del
    volumen. Un PNG guardado sobre fondo blanco es un PNG valido y pasaria
    cualquier comprobacion de formato, pero en el vestidor superpondria un
    rectangulo blanco sobre el torso. Que el prototipo de realidad aumentada
    descubra eso en el dia 4 es tarde; se descubre aqui.
    """
    imagen = repository.obtener(db, imagen_id)
    if imagen is None:
        raise ImagenInexistente(str(imagen_id))

    if datos.es_transparente:
        if imagen.variante_id is None:
            raise TransparenteSinVariante(str(imagen_id))
        if not _archivo_tiene_transparencia(imagen.ruta):
            raise SinTransparencia(str(imagen_id))

    try:
        if datos.es_transparente:
            anterior = repository.transparente_de_variante(db, imagen.variante_id)
            if anterior is not None and anterior.id != imagen.id:
                anterior.es_transparente = False
                db.flush()  # mismo motivo que en marcar_principal
        imagen.es_transparente = datos.es_transparente
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ErrorDeImagenes(str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return listar(db, imagen.producto_id)


def _archivo_tiene_transparencia(ruta: str) -> bool:
    """Relee el archivo del volumen. Si ya no esta, no se puede afirmar que si."""
    from pathlib import Path

    from app.core.config import settings

    destino = Path(settings.MEDIA_ROOT) / ruta
    try:
        contenido = destino.read_bytes()
    except OSError:
        return False
    try:
        return almacen.inspeccionar(contenido).tiene_transparencia
    except almacen.ErrorDeArchivo:
        return False


def reordenar(db: Session, producto_id: int, datos: ReordenarIn) -> list[ImagenOut]:
    """Flujo alternativo 3d: el orden completo, de una sola vez."""
    _asegurar_producto(db, producto_id)
    galeria = repository.listar_de_producto(db, producto_id)
    por_id = {i.id: i for i in galeria}

    ajenas = [i for i in datos.imagenes if i not in por_id]
    if ajenas:
        raise ImagenAjena(str(ajenas[0]))

    try:
        for posicion, imagen_id in enumerate(datos.imagenes):
            por_id[imagen_id].orden = posicion
        # Las que no vengan en la lista van despues, conservando su orden
        # relativo: reordenar cuatro de seis no debe reventar las otras dos.
        siguiente = len(datos.imagenes)
        for imagen in galeria:
            if imagen.id not in set(datos.imagenes):
                imagen.orden = siguiente
                siguiente += 1
        db.commit()
    except Exception:
        db.rollback()
        raise

    return listar(db, producto_id)


def eliminar(db: Session, imagen_id: int) -> None:
    """Flujo alternativo 3e.

    Si se borra la principal y quedan otras, la primera de la galeria toma su
    lugar: dejar al producto sin principal lo sacaria del listado del catalogo
    por un descuido de mantenimiento.
    """
    imagen = repository.obtener(db, imagen_id)
    if imagen is None:
        raise ImagenInexistente(str(imagen_id))

    producto_id = imagen.producto_id
    ruta = imagen.ruta
    era_principal = imagen.es_principal

    try:
        repository.eliminar(db, imagen)
        if era_principal:
            quedan = repository.listar_de_producto(db, producto_id)
            if quedan:
                quedan[0].es_principal = True
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Recien ahora el archivo: si esto falla, queda un huerfano y no una fila
    # apuntando a la nada.
    almacen.borrar(ruta)
