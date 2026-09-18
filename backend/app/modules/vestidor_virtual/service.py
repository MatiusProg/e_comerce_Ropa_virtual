"""
P9 - Vestidor Virtual (RA)  |  capa: servicio (reglas de negocio)

Ciclo de desarrollo: 3
Caso de uso: CU-21, la parte OPCIONAL de «amoldar» la prenda por IA

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

QUE HACE ESTE PAQUETE DEL LADO DEL SERVIDOR, Y QUE NO
------------------------------------------------------
**Casi nada, y es correcto.** La seccion 4.2 de la arquitectura dice que P9
«reside principalmente en la aplicacion movil»: la camara, la deteccion de
pose y la superposicion corren en el telefono. El servidor sirve los activos
--- y eso ya lo hace P3 con `imagen_producto` --- y ofrece esta unica
operacion, que es la que NO puede correr en el telefono porque necesita un
modelo grande y una clave.
"""
import logging

from sqlalchemy.orm import Session

from app.integrations import probador_ia
from app.integrations.probador_ia import ErrorDelProbador, SolicitudDeProbado
from app.modules.catalogo import imagenes_almacen as almacen
from app.modules.vestidor_virtual import repository
from app.modules.vestidor_virtual.schemas import EstadoDelProbador

_log = logging.getLogger("violetboutique.probador")

#: Tope del archivo que sube el cliente. Mas chico que el de las imagenes de
#: catalogo (5 MB) a proposito: esto es una captura de pantalla de un telefono,
#: no una foto de producto, y lo que llegue mas grande que esto casi seguro es
#: un error del cliente. Ademas cada peticion viaja entera a un tercero.
TAMANO_MAXIMO_CAPTURA = 4 * 1024 * 1024


class ErrorDelVestidor(Exception):
    """Base de los errores previstos de P9."""


class VarianteSinPrenda(ErrorDelVestidor):
    """La variante no tiene PNG de vestidor, asi que no hay que componer."""


class CapturaInvalida(ErrorDelVestidor):
    """Lo que subio el cliente no sirve como captura."""


def estado() -> EstadoDelProbador:
    """Si el probado por IA se puede ofrecer. Lo consulta la app al abrir."""
    if probador_ia.esta_disponible():
        return EstadoDelProbador(disponible=True)
    return EstadoDelProbador(
        disponible=False,
        motivo=(
            "El probado con inteligencia artificial no está habilitado en "
            "este entorno."
        ),
    )


def probar(
    db: Session, *, variante_id: int, captura: bytes, tipo_mime: str | None
) -> tuple[bytes, str, str]:
    """Compone la captura con la prenda. Devuelve `(imagen, mime, generada_por)`.

    NO GUARDA NADA
    --------------
    Ni la captura que sube el cliente, ni la imagen que devuelve el modelo. Es
    una decision, no una omision: la captura es **la foto del cuerpo de una
    persona**, y guardarla obligaria a decidir cuanto se conserva, quien puede
    verla y como se borra --- tres preguntas que este caso de uso no necesita
    contestar para funcionar ---. La imagen vuelve por la respuesta y vive en
    el telefono del cliente, que es de donde salio.

    La tabla `SesionVestidorVirtual` que declara la arquitectura registraria el
    HECHO de la sesion ---quien, cuando, que variante--- sin la foto. Todavia
    no existe; queda anotado.
    """
    if not captura:
        raise CapturaInvalida("La captura llegó vacía.")
    if len(captura) > TAMANO_MAXIMO_CAPTURA:
        megas = TAMANO_MAXIMO_CAPTURA // (1024 * 1024)
        raise CapturaInvalida(f"La captura supera los {megas} MB.")
    if tipo_mime and not tipo_mime.startswith("image/"):
        raise CapturaInvalida("El archivo no es una imagen.")

    prenda = repository.prenda_de_variante(db, variante_id)
    if prenda is None:
        raise VarianteSinPrenda(
            "Esa prenda no tiene imagen para el vestidor virtual."
        )

    try:
        bytes_prenda = almacen.leer(prenda.ruta)
    except FileNotFoundError as e:
        # La fila existe pero el archivo no. Pasa cuando la base se restaura
        # sin el volumen, que es exactamente lo que le pasa hoy a Railway.
        _log.warning("Falta el archivo de la prenda %s: %s", prenda.ruta, e)
        raise VarianteSinPrenda(
            "La imagen de esa prenda no está disponible en este entorno."
        ) from e

    descripcion = " · ".join(
        p for p in (prenda.producto, prenda.talla, prenda.color) if p
    )

    resultado = probador_ia.probar(
        SolicitudDeProbado(
            foto=captura, prenda=bytes_prenda, descripcion=descripcion
        )
    )
    return resultado.imagen, resultado.tipo_mime, resultado.generada_por


__all__ = [
    "CapturaInvalida",
    "ErrorDelProbador",
    "ErrorDelVestidor",
    "VarianteSinPrenda",
    "estado",
    "probar",
]
