"""
P9 - Vestidor Virtual  |  capa: servicio (reglas de negocio)
2do parcial, 3ra presentacion:
  CU-36 Preparar prenda para el probador   (Administrador)
  CU-37 Probarse una prenda con su talla real (Cliente)
  CU-38 Generar foto realista de la prueba  (Cliente, plan con `foto_ia`)

POR QUE SE AMPLIA P9 Y NO UN MODULO NUEVO
-----------------------------------------
La arquitectura ya ponia aca la `SesionVestidorVirtual`, y el probado por IA
del 1er parcial (`service.probar`) vive en este paquete. Un modulo `probador`
aparte partiria en dos la misma funcion: la prenda, su escala y la foto son un
solo recorrido. Lo que SI se reusa de otro lado es la tabla de tallas y la
recomendacion (`medidas`): no se duplica esa regla.

LA IDEA, EN UNA LINEA
---------------------
Los modelos generativos acomodan la prenda al cuerpo y no respetan la talla
(la critica de Karen del 19/10). Aca la escala la ponen los CENTIMETROS: los
puntos de la imagen (CU-36) dicen cuantos pixeles son un cm de tela, las
medidas del cliente dicen cuantos pixeles son un cm de su cuerpo en la foto, y
la prenda se dibuja a su tamano real (CU-37). Si la talla le queda grande, SE
VE grande. La foto con IA (CU-38) parte de esa composicion y se le pide que no
la cambie de tamano.

LA COMPOSICION SE HACE EN EL NAVEGADOR
-------------------------------------
La foto del cliente no viaja al servidor para probarse una prenda: la pose y
la superposicion corren en su dispositivo. Solo sube una imagen si pide la
foto del CU-38, y esa si se guarda (para que la vuelva a ver en «Mis pruebas»)
con un nombre aleatorio de 128 bits, y se borra al borrar la prueba.
"""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import probador_ia
from app.integrations.probador_ia import SolicitudDeProbado
from app.modules.catalogo import imagenes_almacen as almacen
from app.modules.catalogo.models import ImagenProducto
from app.modules.medidas import repository as medidas_repo
from app.modules.medidas import service as medidas_service
from app.modules.medidas.models import MedidaTalla
from app.modules.plataforma import verificador
from app.modules.vestidor_virtual import probador_repository as repo
from app.modules.vestidor_virtual import repository as vestidor_repo
from app.modules.vestidor_virtual import service as vestidor_service
from app.modules.vestidor_virtual.models import PuntoPrenda, SesionVestidorVirtual
from app.modules.vestidor_virtual.probador_schemas import (
    ImagenParaPreparar,
    MedidaDeTalla,
    MedidasDelCuerpo,
    PrendaDelProbador,
    PrendaParaPreparar,
    ProductoDelProbador,
    Punto,
    PuntosDePrenda,
    PruebaDeProducto,
    SesionSalida,
    TallaParaPreparar,
)

_log = logging.getLogger("violetboutique.probador")

#: Separacion minima entre los hombros, en fraccion del ancho de la imagen.
#: Menos que esto es un doble clic, no dos hombros: la escala saldria absurda.
SEPARACION_MINIMA_HOMBROS = 0.10
#: Cuanto puede estar un hombro mas alto que el otro (fraccion del alto). Una
#: prenda fotografiada torcida se dibujaria torcida.
DESNIVEL_MAXIMO_HOMBROS = 0.15
#: Distancia minima entre la linea de hombros y el ruedo (fraccion del alto).
LARGO_MINIMO = 0.10


class Rechazo(Exception):
    """Un error previsto del probador, con su codigo HTTP."""

    def __init__(self, mensaje: str, codigo: int = 422):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


# --- Utilidades -------------------------------------------------------------

def _puntos(fila: PuntoPrenda | None) -> PuntosDePrenda | None:
    if fila is None:
        return None
    return PuntosDePrenda(
        hombro_izq=Punto(x=float(fila.hombro_izq_x), y=float(fila.hombro_izq_y)),
        hombro_der=Punto(x=float(fila.hombro_der_x), y=float(fila.hombro_der_y)),
        ruedo=Punto(x=float(fila.ruedo_x), y=float(fila.ruedo_y)),
    )


def _medida(fila: MedidaTalla | None) -> MedidaDeTalla | None:
    if fila is None:
        return None
    return MedidaDeTalla(
        talla_id=fila.talla_id,
        busto_cm=fila.busto_cm,
        cintura_cm=fila.cintura_cm,
        cadera_cm=fila.cadera_cm,
        largo_cm=fila.largo_cm,
    )


def _producto_o_404(db: Session, producto_id: int):
    producto = repo.producto(db, producto_id)
    if producto is None:
        raise Rechazo("El producto indicado no existe.", 404)
    return producto


def _cliente_o_404(db: Session, usuario_id: int) -> int:
    cliente = medidas_repo.cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise Rechazo("Esta cuenta no tiene ficha de cliente.", 404)
    return cliente.id


# --- CU-36 · Preparar prenda para el probador -------------------------------

def productos(db: Session) -> list[ProductoDelProbador]:
    """Los productos con imagen de vestidor y que tanto falta para dejarlos listos."""
    salida = []
    for fila in repo.productos_con_vestidor(db):
        imagenes = repo.imagenes_de_vestidor(db, fila.id)
        tallas = repo.tallas_del_producto(db, fila.id)
        calibradas = sum(1 for i in imagenes if i.PuntoPrenda is not None)
        medidas = sum(1 for t in tallas if t.MedidaTalla is not None)
        salida.append(
            ProductoDelProbador(
                producto_id=fila.id,
                nombre=fila.nombre,
                activo=fila.activo,
                imagenes=len(imagenes),
                imagenes_calibradas=calibradas,
                tallas=len(tallas),
                tallas_medidas=medidas,
                lista=calibradas > 0 and len(tallas) > 0 and medidas == len(tallas),
            )
        )
    return salida


def preparacion(db: Session, producto_id: int) -> PrendaParaPreparar:
    producto = _producto_o_404(db, producto_id)
    imagenes = [
        ImagenParaPreparar(
            imagen_id=i.imagen_id,
            url=almacen.url_de(i.ruta),
            variante_id=i.variante_id,
            talla=i.talla,
            color=i.color,
            puntos=_puntos(i.PuntoPrenda),
        )
        for i in repo.imagenes_de_vestidor(db, producto_id)
    ]
    tallas = [
        TallaParaPreparar(talla_id=t.id, codigo=t.codigo, medidas=_medida(t.MedidaTalla))
        for t in repo.tallas_del_producto(db, producto_id)
    ]
    faltan: list[str] = []
    if not imagenes:
        faltan.append(
            "Subí en la galería una imagen PNG sin fondo asociada a una variante."
        )
    elif not any(i.puntos for i in imagenes):
        faltan.append("Marcá los hombros y el ruedo en al menos una imagen.")
    sin_medida = [t.codigo for t in tallas if t.medidas is None]
    if sin_medida:
        faltan.append("Cargá las medidas de la prenda en: " + ", ".join(sin_medida) + ".")
    return PrendaParaPreparar(
        producto_id=producto.id,
        nombre=producto.nombre,
        imagenes=imagenes,
        tallas=tallas,
        lista=not faltan,
        faltan=faltan,
    )


def validar_puntos(puntos: PuntosDePrenda) -> None:
    """Las reglas que la base no puede expresar con un CHECK legible."""
    izq, der, ruedo = puntos.hombro_izq, puntos.hombro_der, puntos.ruedo
    if izq.x >= der.x:
        raise Rechazo(
            "El hombro izquierdo tiene que quedar a la izquierda del derecho, "
            "tal como se ve la imagen."
        )
    if der.x - izq.x < SEPARACION_MINIMA_HOMBROS:
        raise Rechazo("Los hombros están demasiado juntos: marcalos en los bordes de la prenda.")
    if abs(izq.y - der.y) > DESNIVEL_MAXIMO_HOMBROS:
        raise Rechazo(
            "Un hombro quedó mucho más alto que el otro. Revisá los puntos o "
            "usá una imagen de la prenda derecha."
        )
    if ruedo.y - max(izq.y, der.y) < LARGO_MINIMO:
        raise Rechazo("El ruedo tiene que quedar debajo de los hombros, donde termina la prenda.")


def guardar_puntos(db: Session, imagen_id: int, puntos: PuntosDePrenda) -> PuntosDePrenda:
    imagen: ImagenProducto | None = repo.imagen(db, imagen_id)
    if imagen is None:
        raise Rechazo("La imagen indicada no existe.", 404)
    if not imagen.es_transparente or imagen.variante_id is None:
        raise Rechazo(
            "Solo se calibran las imágenes de vestidor: PNG sin fondo y asociadas "
            "a una variante."
        )
    validar_puntos(puntos)
    fila = repo.puntos_de(db, imagen_id)
    if fila is None:
        fila = PuntoPrenda(imagen_id=imagen_id)
        db.add(fila)
    fila.hombro_izq_x, fila.hombro_izq_y = puntos.hombro_izq.x, puntos.hombro_izq.y
    fila.hombro_der_x, fila.hombro_der_y = puntos.hombro_der.x, puntos.hombro_der.y
    fila.ruedo_x, fila.ruedo_y = puntos.ruedo.x, puntos.ruedo.y
    db.flush()
    return puntos


def guardar_medidas(
    db: Session, producto_id: int, tallas: list[MedidaDeTalla]
) -> PrendaParaPreparar:
    _producto_o_404(db, producto_id)
    del_producto = {t.id: t for t in repo.tallas_del_producto(db, producto_id)}
    vistas: set[int] = set()
    for t in tallas:
        if t.talla_id not in del_producto:
            raise Rechazo("Una de las tallas no se vende en este producto.")
        if t.talla_id in vistas:
            raise Rechazo("Hay una talla repetida.")
        vistas.add(t.talla_id)

    # La serie tiene que crecer: una L que mide menos de busto que la M es un
    # dato mal cargado, y el probador recomendaria al reves.
    busto = {
        tid: float(f.MedidaTalla.busto_cm)
        for tid, f in del_producto.items()
        if f.MedidaTalla is not None
    }
    busto.update({t.talla_id: float(t.busto_cm) for t in tallas})
    ordenadas = sorted(busto, key=lambda tid: del_producto[tid].orden)
    for anterior, siguiente in zip(ordenadas, ordenadas[1:]):
        if busto[siguiente] < busto[anterior]:
            raise Rechazo(
                f"La talla {del_producto[siguiente].codigo} no puede medir menos de busto "
                f"que la {del_producto[anterior].codigo}."
            )

    for t in tallas:
        fila = repo.medida_talla(db, producto_id, t.talla_id)
        if fila is None:
            fila = MedidaTalla(producto_id=producto_id, talla_id=t.talla_id)
            db.add(fila)
        fila.busto_cm = t.busto_cm
        fila.cintura_cm = t.cintura_cm
        fila.cadera_cm = t.cadera_cm
        fila.largo_cm = t.largo_cm
    db.flush()
    return preparacion(db, producto_id)


# --- CU-37 · Probarse una prenda con su talla real -------------------------

def prueba(db: Session, producto_id: int, usuario_id: int) -> PruebaDeProducto:
    producto = _producto_o_404(db, producto_id)
    if not producto.activo:
        raise Rechazo("El producto indicado no existe.", 404)
    # Una imagen calibrada por variante y, de respaldo, una por color: la
    # imagen calibrada de un color sirve para TODAS sus tallas, porque la forma
    # de la prenda es la misma y lo que cambia son los centimetros (que se
    # dibujan a escala). Asi el cliente compara la S con la XL aunque el
    # administrador haya fotografiado una sola talla.
    calibradas = [
        i for i in repo.imagenes_de_vestidor(db, producto_id, solo_activas=True)
        if i.PuntoPrenda is not None
    ]
    por_variante: dict[int, object] = {}
    por_color: dict[int, object] = {}
    for i in calibradas:
        por_variante.setdefault(i.variante_id, i)
        por_color.setdefault(i.color_id, i)
    prendas = []
    for v in repo.variantes_activas(db, producto_id):
        img = por_variante.get(v.variante_id) or por_color.get(v.color_id)
        if img is None:
            continue
        prendas.append(
            PrendaDelProbador(
                variante_id=v.variante_id,
                talla_id=v.talla_id,
                talla=v.talla,
                color_id=v.color_id,
                color=v.color,
                imagen_url=almacen.url_de(img.ruta),
                puntos=_puntos(img.PuntoPrenda),
            )
        )
    cliente_id = _cliente_o_404(db, usuario_id)
    cuerpo = medidas_repo.medidas_de(db, cliente_id)
    return PruebaDeProducto(
        producto_id=producto.id,
        nombre=producto.nombre,
        prendas=prendas,
        ajuste=medidas_service.ajuste_de_producto(db, producto_id, usuario_id),
        medidas=(
            MedidasDelCuerpo(busto_cm=cuerpo.busto_cm, altura_cm=cuerpo.altura_cm)
            if cuerpo
            else None
        ),
        foto_ia=vestidor_service.estado(db),
    )


def _salida(fila) -> SesionSalida:
    s: SesionVestidorVirtual = fila.SesionVestidorVirtual
    return SesionSalida(
        id=s.id,
        variante_id=s.variante_id,
        producto_id=fila.producto_id,
        producto=fila.producto,
        talla=fila.talla,
        color=fila.color,
        metodo=s.metodo,
        ajuste=s.ajuste,
        talla_recomendada=s.talla_recomendada,
        foto_url=almacen.url_de(s.foto_ruta) if s.foto_ruta else None,
        foto_generada_por=s.foto_generada_por,
        creado_en=s.creado_en,
    )


def registrar_sesion(
    db: Session, usuario_id: int, variante_id: int, metodo: str
) -> SesionSalida:
    """Anota la prueba. El ajuste lo calcula el SERVIDOR, no lo trae la pantalla."""
    cliente_id = _cliente_o_404(db, usuario_id)
    variante = repo.variante_preparada(db, variante_id)
    if variante is None:
        raise Rechazo("Esa prenda no está preparada para el probador.", 404)
    ajuste = medidas_service.ajuste_de_producto(db, variante.producto_id, usuario_id)
    de_la_talla = next((t for t in ajuste.tallas if t.talla_id == variante.talla_id), None)
    sesion = SesionVestidorVirtual(
        cliente_id=cliente_id,
        variante_id=variante_id,
        metodo=metodo,
        ajuste=de_la_talla.ajuste if de_la_talla else None,
        talla_recomendada=ajuste.talla_recomendada,
    )
    db.add(sesion)
    db.flush()
    return _salida(repo.una_sesion_con_detalle(db, sesion.id))


def mis_sesiones(db: Session, usuario_id: int) -> list[SesionSalida]:
    return [_salida(f) for f in repo.sesiones_de(db, _cliente_o_404(db, usuario_id))]


def _sesion_propia(db: Session, usuario_id: int, sesion_id: int) -> SesionVestidorVirtual:
    cliente_id = _cliente_o_404(db, usuario_id)
    sesion = repo.sesion(db, sesion_id)
    # Una prueba ajena responde igual que una inexistente: no se confirma que exista.
    if sesion is None or sesion.cliente_id != cliente_id:
        raise Rechazo("La prueba indicada no existe.", 404)
    return sesion


def borrar_sesion(db: Session, usuario_id: int, sesion_id: int) -> None:
    sesion = _sesion_propia(db, usuario_id, sesion_id)
    ruta = sesion.foto_ruta
    db.delete(sesion)
    db.flush()
    if ruta:
        almacen.borrar(ruta)


# --- CU-38 · Generar foto realista de la prueba -----------------------------

def _guardar_foto(contenido: bytes) -> str:
    relativa = Path("probador") / f"{secrets.token_hex(16)}.png"
    destino = Path(settings.MEDIA_ROOT) / relativa
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return relativa.as_posix()


def generar_foto(
    db: Session,
    usuario_id: int,
    sesion_id: int,
    composicion: bytes,
    tipo_mime: str | None,
) -> SesionSalida:
    """La foto realista a partir de la composicion del CU-37.

    El ORDEN importa: primero todo lo que puede rechazar sin gastar (la prueba,
    que no tenga ya foto, la imagen), despues el proveedor, y recien con la foto
    hecha se descuenta el cupo. Una foto que fallo no gasta el cupo de la tienda.
    """
    sesion = _sesion_propia(db, usuario_id, sesion_id)
    if sesion.foto_ruta:
        raise Rechazo("Esta prueba ya tiene su foto. Hacé otra prueba para generar una nueva.", 409)
    if not composicion:
        raise Rechazo("La composición llegó vacía.")
    if len(composicion) > vestidor_service.TAMANO_MAXIMO_CAPTURA:
        megas = vestidor_service.TAMANO_MAXIMO_CAPTURA // (1024 * 1024)
        raise Rechazo(f"La composición supera los {megas} MB.", 413)
    if tipo_mime and not tipo_mime.startswith("image/"):
        raise Rechazo("El archivo no es una imagen.")

    prenda = vestidor_repo.prenda_de_variante(db, sesion.variante_id)
    if prenda is None:
        raise Rechazo("Esa prenda ya no está disponible en el probador.", 404)
    try:
        bytes_prenda = almacen.leer(prenda.ruta)
    except FileNotFoundError as e:
        _log.warning("Falta el archivo de la prenda %s: %s", prenda.ruta, e)
        raise Rechazo("La imagen de esa prenda no está disponible en este entorno.", 404) from e

    como_queda = (sesion.ajuste or "").replace("_", " ").lower()
    descripcion = " · ".join(
        p for p in (prenda.producto, f"talla {prenda.talla}", prenda.color,
                    f"le queda {como_queda}" if como_queda else None) if p
    )
    resultado = probador_ia.probar(
        SolicitudDeProbado(foto=composicion, prenda=bytes_prenda, descripcion=descripcion)
    )
    ruta = _guardar_foto(resultado.imagen)
    try:
        verificador.consumir_cupo(db, "fotos_ia")
    except Exception:
        almacen.borrar(ruta)
        raise
    sesion.foto_ruta = ruta
    sesion.foto_generada_por = resultado.generada_por[:60]
    db.flush()
    return _salida(repo.una_sesion_con_detalle(db, sesion.id))
