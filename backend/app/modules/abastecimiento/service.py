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
