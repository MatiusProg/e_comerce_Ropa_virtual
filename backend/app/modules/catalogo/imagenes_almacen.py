"""
P3 - Catalogo / CU-11  |  almacenamiento de los archivos de imagen

Ciclo de desarrollo: 2
Caso de uso: CU-11 Gestionar imagenes de producto

Aisla el sistema de archivos del resto del caso de uso. La seccion 6.8 de
docs/06-decisiones-tecnicas.md eligio un volumen persistente de Railway montado
en MEDIA_ROOT, con la base guardando UNICAMENTE la ruta relativa. Si algun dia
se pasa a Supabase Storage o a Cloudinary, se reescribe este archivo y nada mas:
ni el servicio ni el router saben que hay debajo.
"""
import secrets
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.core.config import settings

#: Formatos que se aceptan, con la extension que se les da al guardar.
#:
#: La clave es el formato que reporta Pillow al ABRIR el archivo, no la
#: extension del nombre ni el `content-type` del navegador: los dos los pone
#: quien sube y los dos se pueden mentir.
FORMATOS = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}

#: Tope por archivo. Cinco megas sobran para una foto de catalogo y dejan fuera
#: el caso de subir sin querer un original de camara de 40 MB, que llenaria el
#: volumen en unas pocas cargas.
TAMANO_MAXIMO = 5 * 1024 * 1024

#: Lado maximo. Por encima de esto no aporta a la vitrina y solo pesa; ademas
#: acota lo que Pillow tiene que decodificar en memoria.
LADO_MAXIMO = 4000


class ErrorDeArchivo(Exception):
    """Base de los problemas del archivo en si."""


class ArchivoVacio(ErrorDeArchivo):
    """No llego contenido."""


class ArchivoDemasiadoGrande(ErrorDeArchivo):
    """Excepcion E2."""


class FormatoNoAdmitido(ErrorDeArchivo):
    """Excepcion E1: no es una imagen, o no es de un formato aceptado."""


class ImagenDemasiadoGrande(ErrorDeArchivo):
    """Muchos pixeles de lado."""


class DatosDeImagen:
    """Lo que se averiguo del archivo antes de guardarlo."""

    def __init__(self, formato: str, ancho: int, alto: int, tiene_transparencia: bool):
        self.formato = formato
        self.ancho = ancho
        self.alto = alto
        #: Si el archivo tiene canal alfa Y algun pixel realmente translucido.
        #: No es lo mismo que «es PNG»: un PNG guardado desde el fondo blanco
        #: sigue siendo PNG y no sirve para el vestidor virtual.
        self.tiene_transparencia = tiene_transparencia


def inspeccionar(contenido: bytes) -> DatosDeImagen:
    """Averigua que es el archivo de verdad, abriendolo.

    No se mira la extension ni el `content-type`: los pone quien sube. Abrir el
    archivo es la unica forma de saber si un `foto.png` es realmente un PNG y no
    un ejecutable renombrado.
    """
    if not contenido:
        raise ArchivoVacio()
    if len(contenido) > TAMANO_MAXIMO:
        raise ArchivoDemasiadoGrande(str(len(contenido)))

    from io import BytesIO

    try:
        with Image.open(BytesIO(contenido)) as imagen:
            formato = (imagen.format or "").upper()
            if formato not in FORMATOS:
                raise FormatoNoAdmitido(formato or "desconocido")
            ancho, alto = imagen.size
            if ancho > LADO_MAXIMO or alto > LADO_MAXIMO:
                raise ImagenDemasiadoGrande(f"{ancho}x{alto}")
            transparencia = _tiene_transparencia(imagen)
    except (UnidentifiedImageError, OSError) as exc:
        raise FormatoNoAdmitido(str(exc)) from exc

    return DatosDeImagen(formato, ancho, alto, transparencia)


def _tiene_transparencia(imagen: Image.Image) -> bool:
    """Si la imagen tiene pixeles realmente translucidos.

    Tener canal alfa no alcanza: lo habitual es guardar como PNG una foto con
    fondo blanco, que sale en modo RGBA con el alfa entero en 255. Para el
    vestidor virtual (supuesto S5) esa imagen es inservible --- superpondria un
    rectangulo blanco sobre el torso --- asi que se mira el minimo real del
    canal alfa y no el modo del archivo.
    """
    if imagen.mode in ("RGBA", "LA"):
        alfa = imagen.getchannel("A")
        minimo, _ = alfa.getextrema()
        return minimo < 255
    if imagen.mode == "P" and "transparency" in imagen.info:
        return True
    return False


def _raiz() -> Path:
    return Path(settings.MEDIA_ROOT)


def guardar(contenido: bytes, *, producto_id: int, formato: str) -> str:
    """Escribe el archivo y devuelve su ruta relativa, que es lo que va a la base.

    El nombre lo genera el servidor y NO se toma del que subio: un nombre de
    archivo elegido por quien sube puede traer '..', separadores o caracteres
    que el sistema de archivos interprete, y ademas dos personas subiendo
    'frente.png' se pisarian.

    Se agrupa por producto para que borrar un producto sea borrar una carpeta, y
    para que el volumen no termine con miles de archivos sueltos en un solo
    directorio.
    """
    extension = FORMATOS[formato]
    relativa = Path("productos") / str(producto_id) / f"{secrets.token_hex(16)}{extension}"
    destino = _raiz() / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    # Siempre con barras hacia adelante: la ruta se guarda en la base y se sirve
    # como URL, y en Windows Path usaria la barra invertida.
    return relativa.as_posix()


def borrar(ruta: str) -> None:
    """Borra el archivo. Que no exista no es un error.

    Si la fila esta y el archivo no --- un despliegue que perdio el volumen, un
    borrado a mano ---, lo que hay que poder hacer es justamente eliminar la
    fila. Fallar aqui dejaria la galeria con una imagen rota e imborrable.
    """
    destino = _raiz() / ruta
    try:
        destino.unlink(missing_ok=True)
    except OSError:
        # Tampoco se interrumpe por un archivo bloqueado: la fila se va igual y
        # queda a lo sumo un archivo huerfano en el volumen.
        pass


def url_de(ruta: str) -> str:
    """La ruta relativa, prefijada con MEDIA_URL, tal como la sirve la API."""
    return f"{settings.MEDIA_URL.rstrip('/')}/{ruta.lstrip('/')}"
