"""
P13 - Notificaciones / CU-40  |  capa: servicio

Aca vive el `GestorNotificaciones` del 2.3. Tiene dos caras y conviene no
confundirlas:

  1. **Lo que le consumen los otros paquetes.** Las cuatro funciones `avisar_*`
     las llaman P6 (reservas), P8 (pagos) y P4 (inventario) cuando el hecho
     ocurre. Reciben la fila del hecho, resuelven a QUIEN hay que avisarle y
     dejan la notificacion en la misma transaccion, sin confirmar.

  2. **Lo que le consume su propio router.** Listar las mias, contarlas,
     marcarlas leidas y despachar los correos pendientes.

POR QUE EL AVISO SE GUARDA ADENTRO DE LA TRANSACCION Y EL CORREO SALE AFUERA
-----------------------------------------------------------------------------
Son dos exigencias opuestas y por eso se separan.

El aviso tiene que nacer **con** el hecho: si la reserva se crea y despues algo
falla y la transaccion se deshace, el aviso tiene que deshacerse tambien. Por
eso `avisar_*` no confirma nada --- se apoya en el `commit` de quien la llamo.

El correo tiene que salir **despues** del `commit`. Mandarlo antes significa
avisarle al Encargado de una reserva que todavia puede no existir, y un correo
no se puede deshacer. Por eso el envio es un paso aparte: `despachar_pendientes`.

EL DESPACHADOR ES EL MISMO ARREGLO QUE CU-25
---------------------------------------------
`POST /mantenimiento/notificaciones/despacho` esta pensado para un planificador
---una tarea de Railway, un cron---, igual que la expiracion de reservas, y por
las mismas dos razones: es **idempotente** (una notificacion ENVIADA no se
vuelve a mandar) y se puede disparar a mano en la defensa para mostrar el correo
llegando.

Mientras tanto el aviso **dentro de la aplicacion ya esta**: aparece en la
campanita en el mismo momento en que ocurre el hecho. Esa es exactamente la
degradacion que se acordo el 13/09 cuando no habia proveedor de correo, y que
ahora es el piso y no el techo.

UN FALLO DEL CORREO NO PUEDE ROMPER LA OPERACION
--------------------------------------------------
Misma leccion que dejo CU-41: el proveedor puede estar caido, la direccion
puede ser invalida, la clave puede haber vencido. Nada de eso puede hacer que
una venta falle. `despachar_pendientes` atrapa `ErrorDeEnvio` por notificacion,
la marca FALLIDA con el motivo y sigue con la siguiente.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.config import settings
from app.integrations.correo import ErrorDeEnvio, Mensaje, enviar
from app.modules.notificaciones import repository
from app.modules.notificaciones.models import Notificacion
from app.modules.notificaciones.schemas import (
    DespachoOut,
    MarcadasOut,
    NotificacionOut,
    PaginaNotificacionesOut,
    ResumenNotificacionesOut,
)
from app.modules.organizacion.models import Empleado
from app.modules.seguridad.models import Cliente, Usuario

log = logging.getLogger(__name__)

#: Cuantas manda cada corrida del despachador. Acotado porque el proveedor
#: limita por minuto y porque una corrida que tarda cinco minutos deja al
#: planificador solapandose consigo mismo.
TOPE_POR_DESPACHO = 50


# =====================================================================
# A quien hay que avisarle
# =====================================================================
#
# Las tres funciones devuelven usuarios ACTIVOS. Un aviso dirigido a una cuenta
# desactivada no lo va a leer nadie y el correo rebota; que la fila igual se
# cree seria acumular ruido en la campanita de alguien que ya no entra.


def _usuario_activo(db: Session, usuario_id: int | None) -> Usuario | None:
    if usuario_id is None:
        return None
    usuario = db.get(Usuario, usuario_id)
    return usuario if usuario is not None and usuario.activo else None


def _usuario_del_cliente(db: Session, cliente_id: int | None) -> Usuario | None:
    """La cuenta detras de una ficha de cliente.

    Devuelve None cuando la venta es anonima ---el mostrador no exige datos, ver
    `Venta.cliente_id`---. No es un error: no hay a quien avisarle.
    """
    if cliente_id is None:
        return None
    cliente = db.get(Cliente, cliente_id)
    return _usuario_activo(db, cliente.usuario_id if cliente else None)


def _encargados_de(db: Session, sucursal_id: int) -> list[Usuario]:
    """Los Encargados EN ACTIVIDAD de una sucursal.

    Se filtra por `fecha_baja IS NULL`: un encargado dado de baja conserva su
    fila de empleado ---es historia--- y seguirle mandando las reservas de un
    local donde ya no trabaja es una fuga de informacion, no un descuido.

    Devuelve una lista y no uno solo porque nada en el modelo impide que una
    sucursal tenga dos, y elegir «el primero» en silencio dejaria al otro sin
    enterarse.
    """
    filas = db.execute(
        select(Usuario)
        .join(Empleado, Empleado.usuario_id == Usuario.id)
        .where(
            Empleado.sucursal_id == sucursal_id,
            Empleado.cargo == "ENCARGADO",
            Empleado.fecha_baja.is_(None),
            Usuario.activo.is_(True),
        )
    )
    return list(filas.scalars().all())


# =====================================================================
# Crear el aviso
# =====================================================================


def notificar(
    db: Session,
    *,
    destinatario: Usuario,
    tipo: str,
    titulo: str,
    cuerpo: str,
    enlace: str | None = None,
    entidad: str | None = None,
    entidad_id: int | None = None,
) -> Notificacion:
    """Deja el aviso en la transaccion en curso. NO confirma y NO manda correo.

    El estado inicial del correo sale de si hay a donde mandarlo: una cuenta sin
    direccion nace OMITIDO y no PENDIENTE, para que el despachador no la
    persiga en cada corrida por algo que no va a cambiar solo.
    """
    hay_direccion = bool((destinatario.correo or "").strip())
    return repository.crear(
        db,
        destinatario_id=destinatario.id,
        tipo=tipo,
        titulo=titulo,
        cuerpo=cuerpo,
        enlace=enlace,
        entidad=entidad,
        entidad_id=entidad_id,
        correo_estado="PENDIENTE" if hay_direccion else "OMITIDO",
    )


# =====================================================================
# Los cuatro hechos  -  lo que P6, P8 y P4 le consumen a P13
# =====================================================================
#
# Cada una recibe la fila del hecho YA escrita en la sesion. Ninguna confirma.
# Ninguna levanta si no hay destinatario: que una sucursal no tenga encargado
# cargado es un problema de datos maestros, no un motivo para que la reserva del
# cliente falle.


def avisar_reserva_en_sucursal(db: Session, reserva) -> list[Notificacion]:
    """RF11: al Encargado le llega la reserva dirigida a SU local (CU-22).

    NOTA SOBRE LOS ENLACES DE LOS CUATRO AVISOS
    --------------------------------------------
    Apuntan al LISTADO y no a la ficha ---`/sucursal/reservas` y no
    `/sucursal/reservas/12`--- porque la web no tiene rutas de detalle: ni
    reservas, ni compras, ni existencias. Inventarlas aca dejaria correos con
    enlaces que caen en la pantalla de «no encontrado», que es peor que un
    enlace al listado. El identificador igual viaja en `entidad_id`, asi que el
    dia que esas rutas existan es cambiar esta linea.
    """
    avisos = []
    for encargado in _encargados_de(db, reserva.sucursal_id):
        avisos.append(
            notificar(
                db,
                destinatario=encargado,
                tipo="RESERVA_EN_SUCURSAL",
                titulo=f"Nueva reserva en su sucursal (#{reserva.id})",
                cuerpo=(
                    f"Se registró la reserva #{reserva.id} para su sucursal. "
                    f"La franja de retiro vence el "
                    f"{tiempo.formatear(reserva.franja_fin)}. "
                    f"Prepárela antes de esa hora para que no expire."
                ),
                enlace="/sucursal/reservas",
                entidad="reserva",
                entidad_id=reserva.id,
            )
        )
    if not avisos:
        # No es un error, pero si un dato maestro incompleto que conviene ver.
        log.warning(
            "CU-40: la sucursal %s no tiene Encargado activo; "
            "la reserva %s no se notificó a nadie.",
            reserva.sucursal_id,
            reserva.id,
        )
    return avisos


def avisar_reserva_preparada(db: Session, reserva) -> Notificacion | None:
    """Al Cliente le avisan que su reserva está lista para retirar (CU-24)."""
    destinatario = _usuario_del_cliente(db, reserva.cliente_id)
    if destinatario is None:
        return None
    return notificar(
        db,
        destinatario=destinatario,
        tipo="RESERVA_PREPARADA",
        titulo=f"Su reserva #{reserva.id} está lista",
        cuerpo=(
            f"Preparamos su reserva #{reserva.id}. Puede pasar a retirarla "
            f"hasta el {tiempo.formatear(reserva.franja_fin)}. "
            f"Pasada esa hora las prendas vuelven a la venta."
        ),
        enlace="/mi-cuenta/reservas",
        entidad="reserva",
        entidad_id=reserva.id,
    )


def avisar_pedido_pagado(db: Session, venta) -> Notificacion | None:
    """Al Cliente le confirman que su pedido quedó pagado (CU-28).

    Sale del webhook, que es el unico que mueve el pago a APROBADO (D5). Avisar
    desde la pantalla de retorno seria avisar de algo que todavia no se
    verifico: el cliente vuelve de la pasarela antes de que el evento firmado
    llegue, y a veces no vuelve nunca.
    """
    destinatario = _usuario_del_cliente(db, venta.cliente_id)
    if destinatario is None:
        # Venta anonima del mostrador: no hay cuenta a la que avisarle.
        return None
    return notificar(
        db,
        destinatario=destinatario,
        tipo="PEDIDO_PAGADO",
        titulo=f"Pago confirmado del pedido {venta.codigo}",
        cuerpo=(
            f"Recibimos el pago de su pedido {venta.codigo} por "
            f"{venta.total} {settings.PAGO_MONEDA.upper()}. "
            f"Ya estamos preparándolo."
        ),
        enlace="/mi-cuenta/compras",
        entidad="venta",
        entidad_id=venta.id,
    )


def avisar_stock_bajo(db: Session, existencia, *, etiqueta: str) -> list[Notificacion]:
    """Al Encargado le avisan que una prenda llegó a su punto de reposición.

    `etiqueta` la arma quien llama, que es el que ya tiene la variante a mano;
    resolverla aca obligaria a P13 a conocer el catalogo.
    """
    avisos = []
    for encargado in _encargados_de(db, existencia.sucursal_id):
        avisos.append(
            notificar(
                db,
                destinatario=encargado,
                tipo="STOCK_BAJO",
                titulo=f"Stock bajo: {etiqueta}",
                cuerpo=(
                    f"Quedan {existencia.cantidad_disponible} unidades "
                    f"disponibles de {etiqueta} en su sucursal, y el punto de "
                    f"reposición está en {existencia.stock_minimo}. "
                    f"Conviene reponer."
                ),
                enlace="/sucursal/inventario",
                entidad="existencia",
                entidad_id=existencia.id,
            )
        )
    return avisos


# =====================================================================
# El despachador de correos
# =====================================================================


def _cuerpo_html(notificacion: Notificacion, url: str | None) -> str:
    boton = ""
    if url:
        boton = (
            f'<p style="margin:24px 0">'
            f'<a href="{url}" style="background:#6b2d5c;color:#fff;'
            f'padding:12px 20px;border-radius:6px;text-decoration:none;'
            f'display:inline-block">Ver en Violet Boutique</a></p>'
        )
    return (
        "<html><body style=\"font-family:system-ui,sans-serif;color:#222\">"
        f"<h2 style=\"color:#6b2d5c\">{notificacion.titulo}</h2>"
        f"<p>{notificacion.cuerpo}</p>"
        f"{boton}"
        '<p style="color:#666;font-size:13px">Este es un aviso automático de '
        "Violet Boutique. No responda a este correo.</p>"
        "</body></html>"
    )


def _mensaje_de(db: Session, notificacion: Notificacion) -> Mensaje | None:
    """Arma el correo, o None si ya no hay a quien mandarlo."""
    destinatario = db.get(Usuario, notificacion.destinatario_id)
    if destinatario is None or not (destinatario.correo or "").strip():
        return None

    url = None
    if notificacion.enlace:
        # El enlace se guarda relativo y se completa aca: el dominio cambia
        # entre local y Railway. WEB_BASE_URL apuntando a localhost en
        # produccion es un fallo silencioso ---el correo sale y el enlace no le
        # sirve a nadie---, por eso conviene que este puesta en Railway.
        url = f"{settings.WEB_BASE_URL.rstrip('/')}{notificacion.enlace}"

    return Mensaje(
        destinatario=destinatario.correo,
        asunto=notificacion.titulo,
        cuerpo_texto=(
            f"{notificacion.titulo}\n\n{notificacion.cuerpo}"
            + (f"\n\n{url}" if url else "")
        ),
        cuerpo_html=_cuerpo_html(notificacion, url),
    )


def despachar_pendientes(db: Session, *, limite: int = TOPE_POR_DESPACHO) -> DespachoOut:
    """Manda por correo las notificaciones que esperan salir.

    **Idempotente**: solo mira las PENDIENTES, y cada una que sale pasa a
    ENVIADO. Correrlo dos veces seguidas no manda nada dos veces.

    Confirma **una por una** a proposito. Si se confirmara al final, un fallo a
    la mitad dejaria correos ya entregados marcados como pendientes, y la
    corrida siguiente los mandaria de nuevo --- que es el unico error que el
    usuario nota.
    """
    pendientes = repository.listar_pendientes_de_correo(db, limite=limite)
    enviadas = fallidas = 0

    for notificacion in pendientes:
        mensaje = _mensaje_de(db, notificacion)
        if mensaje is None:
            notificacion.correo_estado = "OMITIDO"
            notificacion.correo_error = "El destinatario ya no tiene dirección."
            db.commit()
            continue

        try:
            enviar(mensaje)
        except ErrorDeEnvio as error:
            notificacion.correo_estado = "FALLIDO"
            notificacion.correo_error = str(error)[:300]
            fallidas += 1
            log.warning("CU-40: no se pudo enviar la notificación %s: %s", notificacion.id, error)
        except Exception as error:  # noqa: BLE001
            # Un proveedor mal configurado levanta lo que se le ocurra. Que la
            # corrida entera muera por una fila deja las otras sin salir.
            notificacion.correo_estado = "FALLIDO"
            notificacion.correo_error = f"{type(error).__name__}: {error}"[:300]
            fallidas += 1
            log.exception("CU-40: error inesperado enviando la notificación %s", notificacion.id)
        else:
            notificacion.correo_estado = "ENVIADO"
            notificacion.correo_enviado_en = tiempo.ahora()
            notificacion.correo_error = None
            enviadas += 1

        db.commit()

    return DespachoOut(
        intentadas=len(pendientes), enviadas=enviadas, fallidas=fallidas
    )


def reintentar_fallidas(db: Session, *, limite: int = TOPE_POR_DESPACHO) -> int:
    """Devuelve las FALLIDAS a PENDIENTE para que el despachador las tome.

    Se separa del despachador para que un proveedor caido no genere un ciclo
    infinito de reintentos dentro de la misma corrida. Reintentar es una
    decision de quien opera, no del despachador.
    """
    filas = list(
        db.execute(
            select(Notificacion)
            .where(Notificacion.correo_estado == "FALLIDO")
            .order_by(Notificacion.creada_en.asc())
            .limit(limite)
        )
        .scalars()
        .all()
    )
    for fila in filas:
        fila.correo_estado = "PENDIENTE"
        fila.correo_error = None
    db.commit()
    return len(filas)


# =====================================================================
# Lo que consume el router
# =====================================================================


def _a_salida(fila: Notificacion) -> NotificacionOut:
    return NotificacionOut(
        id=fila.id,
        tipo=fila.tipo,
        titulo=fila.titulo,
        cuerpo=fila.cuerpo,
        enlace=fila.enlace,
        entidad=fila.entidad,
        entidad_id=fila.entidad_id,
        creada_en=tiempo.en_bolivia(fila.creada_en),
        leida_en=tiempo.en_bolivia(fila.leida_en) if fila.leida_en else None,
        correo_estado=fila.correo_estado,
    )


def listar_mias(
    db: Session,
    usuario_id: int,
    *,
    solo_no_leidas: bool = False,
    pagina: int = 1,
    tamano: int = 20,
) -> PaginaNotificacionesOut:
    filas = repository.listar_de(
        db, usuario_id, solo_no_leidas=solo_no_leidas, pagina=pagina, tamano=tamano
    )
    return PaginaNotificacionesOut(
        total=repository.contar_de(db, usuario_id, solo_no_leidas=solo_no_leidas),
        pagina=pagina,
        tamano=tamano,
        no_leidas=repository.contar_de(db, usuario_id, solo_no_leidas=True),
        items=[_a_salida(fila) for fila in filas],
    )


def resumen(db: Session, usuario_id: int) -> ResumenNotificacionesOut:
    return ResumenNotificacionesOut(
        no_leidas=repository.contar_de(db, usuario_id, solo_no_leidas=True)
    )


def marcar_leida(db: Session, usuario_id: int, notificacion_id: int) -> bool:
    """True si la marco; False si no existe o no es suya.

    El router traduce el False a 404 y nunca a 403: un 403 confirmaria que ese
    identificador corresponde a un aviso real de otra persona, y recorrer
    numeros se volveria un censo. Es la convencion del proyecto.
    """
    if repository.obtener_de(db, notificacion_id, usuario_id) is None:
        return False
    repository.marcar_leidas(
        db, usuario_id, momento=tiempo.ahora(), notificacion_id=notificacion_id
    )
    db.commit()
    return True


def marcar_todas_leidas(db: Session, usuario_id: int) -> MarcadasOut:
    marcadas = repository.marcar_leidas(db, usuario_id, momento=tiempo.ahora())
    db.commit()
    return MarcadasOut(marcadas=marcadas)
