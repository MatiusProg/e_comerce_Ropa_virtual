"""
P10 - Inteligencia Artificial / CU-34  |  capa: servicio

Realiza el **RF25** junto con CU-33 y CU-35. Es el tercero de los tres casos
de uso de P10, y el que el plan dejaba caer primero.

LA MISMA DECISION QUE EN CU-33 Y CU-35, POR TERCERA VEZ
---------------------------------------------------------
El modelo **no busca**: se le busca. El servicio arma el contexto con datos
reales ---ya filtrados por quien pregunta--- y el modelo solo redacta sobre
eso.

Lo escrito en `integrations/asistente/base.py` explica por que se descarto
darle acceso a la base. En una frase: un modelo que puede consultar puede
leer lo que no le toca, y acotarlo desde el prompt no es un control de
acceso.

QUE VE EL ASISTENTE, EXACTAMENTE
---------------------------------
- El **catalogo publico**: lo mismo que cualquiera ve en la vitrina.
- **Los pedidos y las reservas DE QUIEN PREGUNTA.** El filtro va en el
  `WHERE`, no en la instruccion.
- **Sus medidas**, si las cargo, para poder hablar de tallas.
- Las sucursales y sus horarios.

No ve: precios base, proveedores, margenes, datos de otros clientes, ni nada
del panel de administracion.

EL HISTORIAL LO GUARDA LA PANTALLA, NO LA BASE
------------------------------------------------
No hay tabla de conversaciones, y es una decision. Lo que se ganaria es
poder retomar una charla de ayer; lo que cuesta es una tabla que crece sin
limite con texto libre de un modelo, mas la pregunta de cuanto se guarda y
quien lo puede leer ---justo en el caso de uso que mas cerca esta de los
datos personales---.

La conversacion vive mientras la pantalla esta abierta. Al cerrarla se
pierde, que es lo que espera cualquiera de un chat de atencion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import tiempo
from app.integrations import asistente
from app.integrations.asistente import Contexto
from app.modules.ia import asistente_repository as repo
from app.modules.ia import repository as repo_ia
from app.modules.inventario import service as inventario

_log = logging.getLogger("violetboutique.asistente")

#: Cuantas prendas del catalogo entran en el contexto.
CUANTAS_PRENDAS = 60

#: Largo maximo de una pregunta. Lo mismo que CU-35.
LARGO_MAXIMO = 500


class ErrorDeAsistente(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


@dataclass(frozen=True)
class RespuestaAlCliente:
    texto: str
    productos: list[int]


def esta_disponible() -> bool:
    return asistente.esta_disponible()


def _importe(valor: Decimal | None) -> str:
    return f"{valor:.2f}" if valor is not None else "—"


def armar_contexto(db: Session, cliente, nombre: str) -> Contexto:
    """Los datos REALES sobre los que el modelo va a contestar.

    Se arma entero en cada pregunta y no se guarda: el catalogo cambia, los
    pedidos avanzan, y un contexto cacheado haria que el asistente conteste
    sobre el estado de hace media hora --- que en «¿ya llegó mi pedido?» es
    exactamente la pregunta que no se puede contestar mal.
    """
    filas = repo.catalogo(db, limite=CUANTAS_PRENDAS)
    ids = [f[0] for f in filas]

    # La existencia por la costura C1 y en bloque, igual que CU-33.
    con_stock = inventario.productos_con_stock(db, ids)
    tallas = repo.tallas_de(db, ids)
    colores = repo.colores_de(db, ids)

    catalogo = []
    for producto_id, nombre_prenda, categoria, desde, hasta in filas:
        precio = (
            f"Bs {_importe(desde)}"
            if desde == hasta
            else f"Bs {_importe(desde)} a {_importe(hasta)}"
        )
        cuales = ", ".join(tallas.get(producto_id, [])) or "sin tallas cargadas"
        tonos = ", ".join(colores.get(producto_id, [])) or "sin color cargado"
        hay = "hay stock" if producto_id in con_stock else "AGOTADA"
        catalogo.append(
            f"#{producto_id} {nombre_prenda} | {categoria} | {precio} "
            f"| tallas: {cuales} | colores: {tonos} | {hay}"
        )

    pedidos = []
    for codigo, estado, total, creado in repo.pedidos_del_cliente(db, cliente.id):
        cuando = tiempo.en_bolivia(creado).strftime("%d/%m/%Y")
        pedidos.append(f"{codigo} | {estado} | Bs {_importe(total)} | {cuando}")

    reservas = []
    for reserva_id, estado, franja, sucursal in repo.reservas_del_cliente(
        db, cliente.id
    ):
        cuando = tiempo.en_bolivia(franja).strftime("%d/%m/%Y %H:%M")
        reservas.append(f"Reserva {reserva_id} | {estado} | {sucursal} | {cuando}")

    datos = [
        f"{n} ({c}), abre {a} y cierra {ci}"
        for n, c, a, ci in repo.sucursales(db)
    ]
    datos.append(f"Hoy es {tiempo.hoy().strftime('%d/%m/%Y')}.")

    # La equivalencia cm <-> talla. Ver `repo.tabla_de_tallas`.
    tabla = [
        f"{codigo}: busto {bmin}-{bmax} cm, cintura {cmin}-{cmax} cm, "
        f"cadera {dmin}-{dmax} cm"
        for codigo, _orden, bmin, bmax, cmin, cmax, dmin, dmax in (
            repo.tabla_de_tallas(db)
        )
    ]

    return Contexto(
        nombre=nombre,
        catalogo=tuple(catalogo),
        tallas=tuple(tabla),
        pedidos=tuple(pedidos),
        reservas=tuple(reservas),
        medidas=_medidas_de(db, cliente),
        datos=tuple(datos),
    )


def _medidas_de(db: Session, cliente) -> str | None:
    """Las medidas del cliente, si las cargo (CU-21).

    Sirven para «¿qué talla me queda?», que sin esto el asistente tiene que
    contestar que no sabe sobre un dato que el sistema ya tiene.
    """
    from app.modules.medidas import repository as medidas_repo

    try:
        medidas = medidas_repo.medidas_de(db, cliente.id)
    except Exception as e:  # noqa: BLE001 - la falta de medidas no rompe nada
        _log.info("No se pudieron leer las medidas del cliente %s: %s", cliente.id, e)
        return None

    if medidas is None:
        return None

    partes = [
        f"busto {medidas.busto_cm} cm",
        f"cintura {medidas.cintura_cm} cm",
        f"cadera {medidas.cadera_cm} cm",
    ]
    if medidas.altura_cm:
        partes.append(f"altura {medidas.altura_cm} cm")
    talla = getattr(cliente, "talla_superior", None)
    if talla:
        partes.append(f"talla habitual {talla}")
    return ", ".join(partes)


def responder(
    db: Session,
    usuario_id: int,
    *,
    pregunta: str,
    historial: list[tuple[str, str]],
) -> RespuestaAlCliente:
    """Contesta la pregunta de un cliente sobre SUS datos y el catalogo."""
    pregunta = (pregunta or "").strip()
    if not pregunta:
        raise ErrorDeAsistente("Escribí una pregunta.", 422)
    if len(pregunta) > LARGO_MAXIMO:
        raise ErrorDeAsistente(
            f"La pregunta es demasiado larga (máximo {LARGO_MAXIMO} caracteres).",
            422,
        )

    cliente = repo_ia.cliente_de_usuario(db, usuario_id)
    if cliente is None:
        # Un administrador tiene usuario pero no perfil de compra. El
        # asistente habla de «tus pedidos» y «tus reservas»: sin cliente no
        # hay de que hablar, y contestar igual seria hablar de nadie.
        raise ErrorDeAsistente(
            "El asistente es para clientes: responde sobre tus compras y tus "
            "reservas.",
            403,
        )

    # El nombre esta en `usuario`, no en `cliente`: la ficha de compra no
    # repite los datos de la persona.
    nombre = (getattr(cliente.usuario, "nombres", "") or "").strip() or "el cliente"
    contexto = armar_contexto(db, cliente, nombre)

    try:
        respuesta = asistente.responder(pregunta, contexto, historial)
    except asistente.AsistenteNoConfigurado as e:
        raise ErrorDeAsistente(
            "El asistente no está habilitado en este servidor.", 503
        ) from e
    except asistente.ErrorDelAsistente as e:
        # Se registra y se avisa. NO se contesta con una frase armada: una
        # respuesta que parece del sistema y no sale de sus datos es peor
        # que decir que no se pudo.
        _log.warning("El asistente no contestó a %r: %s", pregunta[:60], e)
        raise ErrorDeAsistente(
            "No pude responder ahora. Probá de nuevo en un momento.", 503
        ) from e

    return RespuestaAlCliente(
        texto=respuesta.texto,
        productos=list(respuesta.productos),
    )


#: Preguntas que SI funcionan, para mostrarlas al abrir la conversacion.
#:
#: Se escriben aca y no en la pantalla porque dependen de lo que el
#: asistente puede contestar: si manana ve algo mas, el ejemplo se actualiza
#: donde esta el contexto y no en dos frentes. Mismo criterio que los
#: ejemplos de CU-35.
EJEMPLOS = (
    "¿Tienen vestidos en talla M?",
    "¿Cuánto sale la campera de jean?",
    "¿Ya llegó mi pedido?",
    "¿Cuándo tengo que ir a buscar mi reserva?",
    "¿Qué talla me quedaría según mis medidas?",
)
