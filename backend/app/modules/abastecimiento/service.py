"""
P4 - Inventario / CU-39  |  capa: servicio

Realiza el **RF38**: el proveedor informa que puede abastecer y en que plazo,
alimentando el estado «proxima a ingresar» del inventario consolidado.

CIERRA EL AGUJERO H1
--------------------
`EstadoExistencia.PROXIMA_A_INGRESAR` esta declarado desde el Ciclo 2 y
ninguna fila lo devolvia: CU-13 registra la mercaderia **cuando ya llego** y
nada anunciaba lo que estaba por llegar. Esto es lo que faltaba.
"""

from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.modules.abastecimiento import repository


class ErrorDeAbastecimiento(Exception):
    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


@dataclass(frozen=True)
class Anuncio:
    id: int
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    cantidad: int
    dias_plazo: int
    observacion: str | None
    estado: str
    creado_en: object
    cantidad_recibida: int = 0
    cantidad_pendiente: int = 0
    recibido_en: object | None = None


def _proveedor(db: Session, usuario_id: int) -> int:
    proveedor = repository.proveedor_de_usuario(db, usuario_id)
    if proveedor is None:
        # Un usuario con rol PROVEEDOR pero sin ficha. Es 409 y no 500: el
        # dato falta y alguien puede arreglarlo.
        raise ErrorDeAbastecimiento(
            "Su usuario no está vinculado a ningún proveedor. "
            "Pídale al administrador que lo vincule.",
            409,
        )
    return proveedor.id


def _a_anuncio(fila: tuple) -> Anuncio:
    return Anuncio(
        id=fila[0],
        variante_id=fila[1],
        sku=fila[2],
        prenda=fila[3],
        talla=fila[4],
        color=fila[5],
        cantidad=fila[6],
        dias_plazo=fila[7],
        observacion=fila[8],
        estado=fila[9],
        creado_en=fila[10],
        cantidad_recibida=fila[11],
        cantidad_pendiente=max(fila[6] - fila[11], 0),
        recibido_en=fila[12],
    )


def mis_anuncios(
    db: Session, usuario_id: int, *, incluir_cancelados: bool = False
) -> list[Anuncio]:
    proveedor_id = _proveedor(db, usuario_id)
    return [
        _a_anuncio(f)
        for f in repository.mios(
            db, proveedor_id, incluir_cancelados=incluir_cancelados
        )
    ]


def mis_variantes(db: Session, usuario_id: int) -> list[dict]:
    """Las variantes que puede anunciar. Las de SUS productos, solo."""
    proveedor_id = _proveedor(db, usuario_id)
    return [
        {
            "variante_id": f[0],
            "sku": f[1],
            "prenda": f[2],
            "talla": f[3],
            "color": f[4],
        }
        for f in repository.variantes_del_proveedor(db, proveedor_id)
    ]


def anunciar(
    db: Session,
    usuario_id: int,
    *,
    variante_id: int,
    cantidad: int,
    dias_plazo: int,
    observacion: str | None,
) -> Anuncio:
    proveedor_id = _proveedor(db, usuario_id)

    variante = repository.variante_de(db, variante_id)
    if variante is None:
        raise ErrorDeAbastecimiento("Esa prenda no existe.", 404)

    (_, _, _, _, proveedor_del_producto, _, _, activa) = variante

    # SOLO SUS PROPIOS PRODUCTOS.
    #
    # El anuncio alimenta el inventario consolidado, y un «próxima a ingresar»
    # respaldado por quien no abastece esa prenda es peor que no tener el
    # dato: promete algo que nadie se comprometio a traer.
    if proveedor_del_producto != proveedor_id:
        raise ErrorDeAbastecimiento(
            "Solo puede informar abastecimiento de sus propios productos.", 403
        )
    if not activa:
        raise ErrorDeAbastecimiento("Esa combinación ya no se ofrece.", 409)

    # Un anuncio vigente por proveedor y variante. El indice unico parcial ya
    # lo impide; comprobarlo aca es lo que convierte un error de integridad en
    # un mensaje que dice que hacer.
    if repository.vigente(db, proveedor_id, variante_id) is not None:
        raise ErrorDeAbastecimiento(
            "Ya informó abastecimiento de esa prenda. Cancélelo antes de "
            "informar uno nuevo."
        )

    fila = repository.crear(
        db,
        proveedor_id=proveedor_id,
        variante_id=variante_id,
        cantidad=cantidad,
        dias_plazo=dias_plazo,
        observacion=observacion,
    )
    db.commit()
    db.refresh(fila)

    datos = repository.mios(db, proveedor_id, incluir_cancelados=True)
    return _a_anuncio(next(f for f in datos if f[0] == fila.id))


def cancelar(db: Session, usuario_id: int, anuncio_id: int) -> None:
    proveedor_id = _proveedor(db, usuario_id)
    fila = repository.por_id(db, anuncio_id)
    if fila is None:
        raise ErrorDeAbastecimiento("Ese aviso no existe.", 404)
    # CADA PROVEEDOR CANCELA EL SUYO. Sin esto, cualquier proveedor podria
    # borrar el compromiso de otro y el inventario perderia informacion sin
    # que su dueño se entere.
    if fila.proveedor_id != proveedor_id:
        raise ErrorDeAbastecimiento("Ese aviso no es suyo.", 403)
    if fila.estado != "ANUNCIADO":
        raise ErrorDeAbastecimiento("Ese aviso ya estaba cancelado.")

    fila.estado = "CANCELADO"
    db.commit()


# =====================================================================
# La recepcion: donde CU-13 cierra lo que CU-39 anuncio
# =====================================================================


@dataclass(frozen=True)
class AvisoDeIngreso:
    """Un anuncio que todavia espera mercaderia, listo para recibirse."""

    id: int
    proveedor_id: int
    proveedor: str
    variante_id: int
    sku: str
    prenda: str
    talla: str
    color: str
    cantidad_anunciada: int
    cantidad_recibida: int
    cantidad_pendiente: int
    dias_plazo: int
    observacion: str | None
    anunciado_en: object


def _a_aviso(fila: tuple) -> AvisoDeIngreso:
    anuncio, proveedor, sku, prenda, talla, color = fila
    return AvisoDeIngreso(
        id=anuncio.id,
        proveedor_id=anuncio.proveedor_id,
        proveedor=proveedor,
        variante_id=anuncio.variante_id,
        sku=sku,
        prenda=prenda,
        talla=talla,
        color=color,
        cantidad_anunciada=anuncio.cantidad,
        cantidad_recibida=anuncio.cantidad_recibida,
        cantidad_pendiente=anuncio.cantidad - anuncio.cantidad_recibida,
        dias_plazo=anuncio.dias_plazo,
        observacion=anuncio.observacion,
        anunciado_en=anuncio.creado_en,
    )


def avisos_de_ingreso(
    db: Session, *, proveedor_id: int | None = None
) -> list[AvisoDeIngreso]:
    """Lo que esta anunciado y todavia no llego.

    Es lo que la pantalla de ingreso muestra ARRIBA, antes del buscador de
    prendas: quien recibe un camion casi siempre esta recibiendo algo que ya
    estaba anunciado, y obligarlo a buscar la variante a mano es hacerle
    reconstruir un dato que el sistema ya tiene --- y es como el anuncio
    terminaba sin cerrarse nunca.
    """
    return [_a_aviso(f) for f in repository.pendientes_de_recibir(db, proveedor_id=proveedor_id)]


def recibir(
    db: Session, recepciones: dict[int, int], *, proveedor_id: int, ahora
) -> dict[int, int]:
    """Descuenta de los anuncios lo que acaba de llegar. **Sin commit.**

    `recepciones` es `{abastecimiento_id: cantidad_que_llego}`. Devuelve
    `{abastecimiento_id: cantidad_que_todavia_falta}`.

    La llama `inventario.service.registrar_ingreso` DENTRO de su transaccion:
    si el ingreso se cae, el anuncio no puede quedar cerrado sobre mercaderia
    que no entro.

    LAS TRES REGLAS
    ----------------
    - Llega **todo** -> `RECIBIDO`, y deja de sumar al «proximo a ingresar».
    - Llega **menos** -> sigue `ANUNCIADO` por el resto. Cerrarlo haria
      desaparecer de la pantalla mercaderia que el proveedor todavia debe.
    - Llega **mas** -> entra todo al inventario y el anuncio se cierra. El
      sobrante es un dato del remito, no un error: la mercaderia ya esta
      fisicamente en la tienda, y rechazar el ingreso por eso dejaria el
      deposito con cajas que el sistema dice que no existen.
    """
    if not recepciones:
        return {}

    anuncios = repository.para_recibir(db, list(recepciones))
    faltantes: dict[int, int] = {}

    for anuncio_id, llegaron in recepciones.items():
        anuncio = anuncios.get(anuncio_id)
        if anuncio is None:
            raise ErrorDeAbastecimiento(
                f"El aviso de ingreso {anuncio_id} no existe.", 404
            )
        # El aviso tiene que ser DE ESTE proveedor. Sin esta comprobacion, un
        # ingreso podria cerrar el anuncio de otro: la mercaderia llegaria de
        # uno y el sistema descontaria la deuda del otro.
        if anuncio.proveedor_id != proveedor_id:
            raise ErrorDeAbastecimiento(
                f"El aviso de ingreso {anuncio_id} es de otro proveedor.", 422
            )
        if anuncio.estado != "ANUNCIADO":
            raise ErrorDeAbastecimiento(
                f"El aviso de ingreso {anuncio_id} ya está {anuncio.estado.lower()}.",
                409,
            )

        anuncio.cantidad_recibida += llegaron
        if anuncio.cantidad_recibida >= anuncio.cantidad:
            anuncio.estado = "RECIBIDO"
            anuncio.recibido_en = ahora
            faltantes[anuncio_id] = 0
        else:
            faltantes[anuncio_id] = anuncio.cantidad - anuncio.cantidad_recibida

    db.flush()
    return faltantes


def variante_del_aviso(db: Session, anuncio_id: int) -> int | None:
    """De que variante es ese aviso. Lo usa el ingreso para comprobar que la
    linea y el aviso hablen de la misma prenda."""
    anuncios = repository.para_recibir(db, [anuncio_id])
    anuncio = anuncios.get(anuncio_id)
    return anuncio.variante_id if anuncio else None
