"""
P7 - Ventas y POS / CU-30  |  capa: servicio (reglas de negocio)

Abrir y cerrar caja. Es la puerta de CU-31: la base exige `turno_caja_id` en
toda venta presencial, asi que **sin un turno abierto no se puede cobrar en el
mostrador**. Por eso este caso de uso va primero.

EL ARQUEO ES LA RAZON DE SER DE ESTE MODULO
--------------------------------------------
Abrir un turno es escribir una fila. Lo que importa es el cierre: el sistema
dice cuanto DEBERIA haber en el cajon y la persona dice cuanto HAY. Los dos
numeros se guardan, y la diferencia es el arqueo.

**Se guardan los dos y no el resultado.** Un descuadre sin los dos numeros no
se puede auditar: saber que faltaron 50 Bs no dice si se conto mal, si se
cobro de menos o si falta plata.

QUE ENTRA AL ESPERADO
---------------------
`apertura + efectivo cobrado - devoluciones`.

Tarjeta y QR **no**: no entran al cajon. Sumarlos haria que todo turno con un
pago con tarjeta apareciera descuadrado, y un arqueo que siempre descuadra
ensena a ignorarlo --- que es peor que no tenerlo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.caja import repository
from app.modules.ventas.models import TurnoCaja


class ErrorDeCaja(Exception):
    """Algo que el cajero puede entender y corregir."""

    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


@dataclass(frozen=True)
class LineaDeArqueo:
    metodo: str
    ventas: int
    total: Decimal


@dataclass(frozen=True)
class EstadoDelTurno:
    turno: TurnoCaja
    caja_nombre: str
    sucursal_nombre: str
    efectivo: Decimal
    devoluciones: Decimal
    esperado: Decimal
    por_metodo: list[LineaDeArqueo]

    #: Solo al cerrar: contado menos esperado. Positivo es que sobra.
    diferencia: Decimal | None = None


def _esperado(db: Session, turno: TurnoCaja) -> tuple[Decimal, Decimal, Decimal]:
    efectivo = repository.efectivo_cobrado(db, turno.id)
    devoluciones = repository.devoluciones_del_turno(db, turno.id)
    return efectivo, devoluciones, turno.monto_apertura + efectivo - devoluciones


def _armar(
    db: Session, turno: TurnoCaja, diferencia: Decimal | None = None
) -> EstadoDelTurno:
    efectivo, devoluciones, esperado = _esperado(db, turno)
    caja = repository.caja_por_id(db, turno.caja_id)
    sucursal = repository.sucursal_activa(db, caja.sucursal_id) if caja else None
    return EstadoDelTurno(
        turno=turno,
        caja_nombre=caja.nombre if caja else "—",
        sucursal_nombre=sucursal.nombre if sucursal else "—",
        efectivo=efectivo,
        devoluciones=devoluciones,
        esperado=esperado,
        por_metodo=[
            LineaDeArqueo(metodo=m or "—", ventas=n, total=t)
            for m, n, t in repository.ventas_del_turno(db, turno.id)
        ],
        diferencia=diferencia,
    )


def cajas_disponibles(db: Session, sucursal_id: int) -> list[tuple]:
    """Las cajas activas de la sucursal, y si cada una esta ocupada.

    Se dice cual esta ocupada en vez de esconderla: el cajero necesita saber
    que la caja existe y que alguien la tiene abierta, no que desaparecio.
    """
    salida = []
    for caja in repository.cajas_de_sucursal(db, sucursal_id):
        abierto = repository.turno_abierto_de_caja(db, caja.id)
        salida.append((caja, abierto is not None))
    return salida


def mi_turno(db: Session, usuario_id: int) -> EstadoDelTurno | None:
    """El turno que esta persona tiene abierto. `None` si no tiene ninguno."""
    turno = repository.turno_abierto_de_usuario(db, usuario_id)
    return _armar(db, turno) if turno else None


def abrir(
    db: Session, *, caja_id: int, usuario_id: int, monto_apertura: Decimal
) -> EstadoDelTurno:
    if monto_apertura < 0:
        raise ErrorDeCaja("El monto de apertura no puede ser negativo.", 422)

    # UNA PERSONA, UN TURNO. Se comprueba ANTES de bloquear la caja: si el
    # cajero ya tiene otro turno abierto en otra caja, el problema no es la
    # caja que pidio y bloquearla seria hacer esperar a quien si puede usarla.
    propio = repository.turno_abierto_de_usuario(db, usuario_id)
    if propio is not None:
        raise ErrorDeCaja(
            "Ya tiene un turno abierto. Ciérrelo antes de abrir otro."
        )

    caja = repository.caja_por_id(db, caja_id)
    if caja is None or not caja.activa:
        raise ErrorDeCaja("Esa caja no existe o está desactivada.", 404)

    # Serializa las aperturas de ESTA caja. Ver el porque en el repositorio.
    repository.bloquear_caja(db, caja_id)

    ocupada = repository.turno_abierto_de_caja(db, caja_id)
    if ocupada is not None:
        raise ErrorDeCaja(
            "Esa caja ya tiene un turno abierto. Tiene que cerrarse antes."
        )

    turno = repository.abrir(
        db, caja_id=caja_id, usuario_id=usuario_id, monto_apertura=monto_apertura
    )
    db.commit()
    db.refresh(turno)
    return _armar(db, turno)


def cerrar(
    db: Session, *, turno_id: int, usuario_id: int, monto_cierre: Decimal
) -> EstadoDelTurno:
    if monto_cierre < 0:
        raise ErrorDeCaja("El monto contado no puede ser negativo.", 422)

    turno = repository.turno_por_id(db, turno_id)
    if turno is None:
        raise ErrorDeCaja("Ese turno no existe.", 404)

    # CIERRA QUIEN ABRIO.
    #
    # No es burocracia: el arqueo le atribuye un descuadre a una persona. Que
    # otro cajero pueda cerrar el turno ajeno significa que el faltante le
    # queda anotado a quien no estuvo en la caja. Un encargado que necesite
    # cerrar un turno olvidado necesita otra operacion, con su propio registro.
    if turno.usuario_id != usuario_id:
        raise ErrorDeCaja("Solo puede cerrar el turno quien lo abrió.", 403)

    if turno.cerrado_en is not None:
        raise ErrorDeCaja("Ese turno ya está cerrado.")

    _, _, esperado = _esperado(db, turno)

    turno.monto_esperado = esperado
    turno.monto_cierre = monto_cierre
    turno.cerrado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(turno)

    # La diferencia se CALCULA al leer y no se guarda: es resta de dos
    # columnas que si estan. Guardarla seria un tercer numero que puede
    # contradecir a los otros dos.
    return _armar(db, turno, diferencia=monto_cierre - esperado)
