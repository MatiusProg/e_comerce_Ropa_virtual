"""
P12 - Bitacora / CU-42  |  capa: servicio

Escribe y lee la bitacora. Las dos mitades tienen reglas propias y opuestas:
**escribir no puede fallar nunca**, y **leer no puede mostrarlo todo a
cualquiera**.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.bitacora import repository

_log = logging.getLogger("violetboutique.bitacora")

#: Claves que NUNCA se guardan, aunque vengan en el detalle.
#:
#: La bitacora se consulta desde una pantalla y se exporta; una contrasena
#: ahi dentro es una filtracion con fecha y nombre. Se comparan en minuscula
#: y por coincidencia parcial, para que `contrasena_actual` y `new_password`
#: caigan igual.
SENSIBLES = (
    "contrasena",
    "contrasenia",
    "password",
    "clave",
    "token",
    "secret",
    "authorization",
    "hash",
    "tarjeta",
    "cvv",
)

#: Cuantos asientos devuelve una pagina como maximo.
TAMANO_MAXIMO = 200


class ErrorDeBitacora(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def limpiar(detalle: dict[str, Any] | None) -> dict[str, Any] | None:
    """Saca del detalle todo lo que no puede quedar escrito.

    Recorre en profundidad: un cuerpo de peticion trae los datos anidados y
    filtrar solo el primer nivel dejaria pasar `{"acceso": {"contrasena":
    ...}}`, que es exactamente la forma que tiene el alta de un proveedor.
    """
    if not detalle:
        return None

    def _recorrer(valor: Any) -> Any:
        if isinstance(valor, dict):
            limpio = {}
            for clave, dentro in valor.items():
                if any(s in str(clave).lower() for s in SENSIBLES):
                    limpio[clave] = "«omitido»"
                else:
                    limpio[clave] = _recorrer(dentro)
            return limpio
        if isinstance(valor, list):
            return [_recorrer(v) for v in valor]
        return valor

    return _recorrer(detalle)


def registrar(
    db: Session,
    *,
    accion: str,
    metodo: str,
    ruta: str,
    estado_http: int,
    exito: bool,
    usuario_id: int | None = None,
    actor: str | None = None,
    rol: str | None = None,
    entidad: str | None = None,
    entidad_id: str | None = None,
    ip: str | None = None,
    agente: str | None = None,
    detalle: dict[str, Any] | None = None,
) -> None:
    """Escribe un asiento. **Hace commit, y no propaga errores.**

    POR QUE SE TRAGA LA EXCEPCION
    ------------------------------
    Es la regla que define este modulo. Si la bitacora falla ---la base no
    responde, la tabla no existe todavia porque falta migrar--- **la
    operacion del usuario tiene que seguir adelante igual**. Una tienda que
    no puede vender porque no puede anotar que vendio esta peor que una que
    vende sin anotar.

    El fallo se registra en el log de la aplicacion, que es donde se mira
    cuando algo no cuadra.

    POR QUE HACE COMMIT PROPIO
    ---------------------------
    El asiento se escribe en su **propia sesion**, no en la de la peticion.
    Si compartieran: una peticion que termina en error hace `rollback` y se
    llevaria puesto el asiento --- justo el de la operacion fallida, que es
    la que mas interesa registrar.
    """
    try:
        repository.agregar(
            db,
            usuario_id=usuario_id,
            actor=(actor or None) and actor[:160],
            rol=rol,
            accion=accion,
            entidad=entidad,
            entidad_id=(entidad_id or None) and str(entidad_id)[:60],
            metodo=metodo,
            ruta=ruta[:300],
            estado_http=estado_http,
            exito=exito,
            ip=ip,
            agente=(agente or None) and agente[:200],
            detalle=limpiar(detalle),
        )
        db.commit()
    except Exception as e:  # noqa: BLE001 - a proposito: no puede escalar
        db.rollback()
        _log.warning("No se pudo escribir en la bitácora (%s %s): %s", metodo, ruta, e)


# --- La lectura -------------------------------------------------------------


@dataclass(frozen=True)
class Pagina:
    total: int
    pagina: int
    tamano: int
    items: list


def listar(
    db: Session,
    *,
    desde: date | None = None,
    hasta: date | None = None,
    usuario_id: int | None = None,
    accion: str | None = None,
    entidad: str | None = None,
    exito: bool | None = None,
    busqueda: str | None = None,
    pagina: int = 1,
    tamano: int = 50,
) -> Pagina:
    """Los asientos que coinciden, del mas reciente al mas viejo.

    **El orden es siempre descendente y no se puede cambiar.** Una bitacora
    se abre para ver que acaba de pasar; ofrecer «mas viejo primero» seria un
    control que nadie usa y que deja la primera pagina llena de la puesta en
    marcha del sistema.

    El periodo se corta en **hora boliviana**, igual que los reportes: pedir
    «el 20» tiene que incluir hasta la medianoche del 20 en la tienda, no
    hasta las 20:00.
    """
    tamano = max(1, min(tamano, TAMANO_MAXIMO))
    pagina = max(1, pagina)

    if desde and hasta and desde > hasta:
        raise ErrorDeBitacora("La fecha inicial es posterior a la final.", 422)

    inicio = tiempo.inicio_del_dia(desde) if desde else None
    fin = tiempo.fin_del_dia(hasta) if hasta else None

    total = repository.contar(
        db,
        desde=inicio,
        hasta=fin,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        exito=exito,
        busqueda=busqueda,
    )
    filas = repository.listar(
        db,
        desde=inicio,
        hasta=fin,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        exito=exito,
        busqueda=busqueda,
        limite=tamano,
        desplazamiento=(pagina - 1) * tamano,
    )
    return Pagina(total=total, pagina=pagina, tamano=tamano, items=filas)


def opciones(db: Session) -> dict[str, list[str]]:
    """Las acciones y entidades que REALMENTE hay registradas.

    Se leen de la tabla y no de una lista escrita en el codigo: la bitacora
    crece con las rutas que existen, y una lista fija se desactualizaria en
    silencio --- el filtro ofreceria una accion que no dio ningun resultado y
    esconderia una que si.
    """
    return {
        "acciones": repository.acciones(db),
        "entidades": repository.entidades(db),
    }


def en_boliviana(momento: datetime) -> datetime:
    """Atajo para la capa de salida. Ver `app.core.tiempo`."""
    return tiempo.en_boliviana(momento)
