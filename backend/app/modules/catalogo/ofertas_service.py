"""
P16 - Ofertas / CU-31 y CU-32  |  capa: servicio

CU-31 GESTIONAR OFERTAS Y PRECIOS MAYORISTAS
--------------------------------------------
Las ofertas manuales (RF-58) son las promociones de CU-12 y se siguen
gestionando ahí. Lo nuevo es el precio mayorista (RF-56): escalones por
producto. Cómo se aplica al cobrar está en
`promociones_service.descuentos_por_variante`, que es la costura de precios
de todo el sistema: ahí se elige UN solo precio, el más bajo (RN-15).

CU-32 APLICAR OFERTAS DE FUERA DE TEMPORADA
-------------------------------------------
El factor medible (RF-57) se guarda en `regla_fuera_de_temporada`: los días
desde que terminó la temporada y la existencia sobrante. `aplicar` recorre los
productos y, a los que cumplen, les crea una promoción AUTOMATICA sobre el
producto. Es idempotente: correrla dos veces no crea nada dos veces.

- Si el producto ya tiene su automática encendida, se deja.
- Si el Administrador la apagó, **no se vuelve a crear** (RN-16: puede
  desactivarla, y eso tiene que durar).
- Si una automática encendida deja de cumplir el factor (se vendió el
  sobrante), se cierra poniéndole fecha de fin: deja de descontar y queda en
  el historial.

Se dispara con `POST /ofertas/fuera-de-temporada/aplicar`, pensado para un
planificador (como el despacho de avisos de CU-40) y para mostrarlo a mano en
la defensa.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.modules.catalogo import ofertas_repository as repository
from app.modules.catalogo import promociones_service
from app.modules.catalogo.ofertas_models import PrecioMayorista, ReglaFueraDeTemporada
from app.modules.catalogo.ofertas_schemas import (
    AplicacionOut,
    CandidataOut,
    MayoristaCrearIn,
    MayoristaEditarIn,
    MayoristaOut,
    ReglaIn,
    ReglaOut,
)
from app.modules.catalogo.promociones_models import Promocion

#: Los valores con que arranca una empresa que nunca guardó su regla. Apagada:
#: una oferta automática que nadie pidió es plata que se regala.
REGLA_POR_OMISION = ReglaOut(
    activa=False,
    dias_desde_fin=30,
    existencia_minima=10,
    porcentaje=Decimal("30.00"),
    por_omision=True,
)


class ErrorDeOfertas(Exception):
    def __init__(self, mensaje: str, codigo: int = 400) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _hoy() -> date:
    # El mismo día boliviano que usan las promociones (ver CU-12).
    return promociones_service._hoy()


# =====================================================================
#  CU-31 · Precios mayoristas
# =====================================================================

def _armar(fila) -> MayoristaOut:
    m: PrecioMayorista = fila[0]
    return MayoristaOut(
        id=m.id,
        producto_id=m.producto_id,
        producto=fila.producto_nombre,
        precio_base=fila.precio_base,
        cantidad_minima=m.cantidad_minima,
        precio_unitario=m.precio_unitario,
        activo=m.activo,
    )


def listar_mayoristas(
    db: Session, *, busqueda: str | None, pagina: int, tamano: int
) -> tuple[int, list[MayoristaOut]]:
    total, filas = repository.listar_mayoristas(
        db, busqueda=busqueda, pagina=pagina, tamano=tamano
    )
    return total, [_armar(f) for f in filas]


def obtener_mayorista(db: Session, mayorista_id: int) -> MayoristaOut:
    fila = repository.fila_de_mayorista(db, mayorista_id)
    if fila is None:
        raise ErrorDeOfertas("El precio mayorista no existe.", 404)
    return _armar(fila)


def _validar_precio(db: Session, producto_id: int, precio: Decimal) -> None:
    """Un mayorista que no es más barato que la prenda más barata no sirve.

    Se rechaza en vez de guardarlo, porque nunca ganaría (RN-15) y el
    Administrador creería que está aplicándose.
    """
    minimo = repository.precio_minimo_del_producto(db, producto_id)
    if minimo is not None and precio >= minimo:
        raise ErrorDeOfertas(
            f"El precio mayorista tiene que ser menor que Bs {minimo}, "
            "el precio más bajo del producto.",
            422,
        )


def crear_mayorista(db: Session, datos: MayoristaCrearIn) -> MayoristaOut:
    """Alta de un escalón. **Hace commit.**"""
    if repository.producto(db, datos.producto_id) is None:
        raise ErrorDeOfertas("El producto no existe.", 404)
    if repository.existe_escalon(db, datos.producto_id, datos.cantidad_minima):
        raise ErrorDeOfertas(
            f"Ese producto ya tiene un precio desde {datos.cantidad_minima} unidades.", 409
        )
    _validar_precio(db, datos.producto_id, datos.precio_unitario)

    escalon = PrecioMayorista(
        producto_id=datos.producto_id,
        cantidad_minima=datos.cantidad_minima,
        precio_unitario=datos.precio_unitario,
    )
    repository.agregar(db, escalon)
    db.commit()
    return obtener_mayorista(db, escalon.id)


def editar_mayorista(
    db: Session, mayorista_id: int, datos: MayoristaEditarIn
) -> MayoristaOut:
    """Edición parcial. **Hace commit.** El producto no se cambia."""
    escalon = repository.mayorista(db, mayorista_id)
    if escalon is None:
        raise ErrorDeOfertas("El precio mayorista no existe.", 404)
    if datos.cantidad_minima is not None and datos.cantidad_minima != escalon.cantidad_minima:
        if repository.existe_escalon(
            db, escalon.producto_id, datos.cantidad_minima, excepto_id=mayorista_id
        ):
            raise ErrorDeOfertas(
                f"Ese producto ya tiene un precio desde {datos.cantidad_minima} unidades.", 409
            )
        escalon.cantidad_minima = datos.cantidad_minima
    if datos.precio_unitario is not None:
        _validar_precio(db, escalon.producto_id, datos.precio_unitario)
        escalon.precio_unitario = datos.precio_unitario
    db.commit()
    return obtener_mayorista(db, mayorista_id)


def cambiar_estado_mayorista(db: Session, mayorista_id: int, activo: bool) -> MayoristaOut:
    """Encender o apagar. **Hace commit.** No se borra: las ventas lo cobraron."""
    escalon = repository.mayorista(db, mayorista_id)
    if escalon is None:
        raise ErrorDeOfertas("El precio mayorista no existe.", 404)
    escalon.activo = activo
    db.commit()
    return obtener_mayorista(db, mayorista_id)


# =====================================================================
#  CU-32 · Fuera de temporada
# =====================================================================

def _regla_out(regla: ReglaFueraDeTemporada | None) -> ReglaOut:
    if regla is None:
        return REGLA_POR_OMISION
    return ReglaOut(
        activa=regla.activa,
        dias_desde_fin=regla.dias_desde_fin,
        existencia_minima=regla.existencia_minima,
        porcentaje=regla.porcentaje,
    )


def obtener_regla(db: Session) -> ReglaOut:
    return _regla_out(repository.regla(db))


def guardar_regla(db: Session, datos: ReglaIn) -> ReglaOut:
    """Crea o reemplaza la regla de la empresa. **Hace commit.**

    No toca las ofertas ya creadas: eso lo hace la próxima aplicación. Cambiar
    el porcentaje no reescribe las automáticas vigentes, a propósito: una
    prenda no cambia de precio en la vitrina porque alguien movió un número.
    """
    regla = repository.regla(db)
    if regla is None:
        regla = ReglaFueraDeTemporada()
        repository.agregar(db, regla)
    regla.activa = datos.activa
    regla.dias_desde_fin = datos.dias_desde_fin
    regla.existencia_minima = datos.existencia_minima
    regla.porcentaje = datos.porcentaje
    db.commit()
    return _regla_out(regla)


def _candidatas(db: Session, regla: ReglaOut, hoy: date) -> list[CandidataOut]:
    filas = repository.candidatas_fuera_de_temporada(
        db,
        hasta_fin=hoy - timedelta(days=regla.dias_desde_fin),
        existencia_minima=regla.existencia_minima,
    )
    salida: list[CandidataOut] = []
    for f in filas:
        situacion = "NUEVA"
        if f.promocion_id is not None:
            promo = repository.promocion(db, f.promocion_id)
            if promo is not None and promo.activa and (promo.hasta is None or promo.hasta >= hoy):
                situacion = "VIGENTE"
            elif promo is not None and not promo.activa:
                situacion = "APAGADA"
            # Cerrada por la regla (con `hasta` pasado) y vuelve a sobrar: se
            # reabre como nueva, que es lo que pediría el Administrador.
        salida.append(
            CandidataOut(
                producto_id=f.producto_id,
                producto=f.producto,
                temporada=f.temporada,
                fin_de_temporada=f.fecha_fin,
                dias_desde_fin=(hoy - f.fecha_fin).days,
                disponible=int(f.disponible),
                situacion=situacion,
                promocion_id=f.promocion_id,
            )
        )
    return salida


def candidatas(db: Session) -> list[CandidataOut]:
    """Lo que haría `aplicar` hoy, sin escribir nada. Para la pantalla."""
    return _candidatas(db, obtener_regla(db), _hoy())


def aplicar(db: Session) -> AplicacionOut:
    """CU-32. Crea y cierra las ofertas automáticas. **Hace commit.**

    Con la regla apagada no crea ninguna; sí cierra las que ya no cumplen,
    porque una oferta que perdió su motivo no tiene por qué seguir.
    """
    hoy = _hoy()
    regla = obtener_regla(db)
    lista = _candidatas(db, regla, hoy)
    califican = {c.producto_id for c in lista}

    creadas = 0
    if regla.activa:
        for c in lista:
            if c.situacion != "NUEVA":
                continue
            promo = None
            if c.promocion_id is not None:
                promo = repository.promocion(db, c.promocion_id)
            if promo is not None:
                # La cerró la regla antes y volvió a sobrar: se reabre.
                promo.hasta = None
                promo.desde = hoy
                promo.porcentaje = regla.porcentaje
            else:
                promo = Promocion(
                    # El nombre de una promoción es único: el id del producto
                    # lo asegura aunque dos productos se llamen igual.
                    nombre=f"Fuera de temporada · {c.producto}"[:70] + f" #{c.producto_id}",
                    alcance="PRODUCTO",
                    producto_id=c.producto_id,
                    porcentaje=regla.porcentaje,
                    desde=hoy,
                    hasta=None,
                    activa=True,
                    origen="AUTOMATICA",
                )
                repository.agregar(db, promo)
            c.situacion = "CREADA"
            c.promocion_id = promo.id
            creadas += 1

    cerradas = 0
    for promo in repository.automaticas_vigentes(db):
        # Se cierra con fecha de ayer: `hasta` es inclusivo y hoy ya no tiene
        # por qué descontar. Una creada HOY se cierra recién mañana (el CHECK
        # no deja `hasta < desde`), y no se apaga: apagada se confundiría con
        # la que apagó el Administrador, que no se vuelve a crear.
        if promo.producto_id not in califican and promo.desde < hoy:
            promo.hasta = hoy - timedelta(days=1)
            cerradas += 1

    db.commit()
    return AplicacionOut(
        hoy=hoy,
        regla_activa=regla.activa,
        creadas=creadas,
        cerradas=cerradas,
        ya_vigentes=sum(1 for c in lista if c.situacion == "VIGENTE"),
        apagadas_por_admin=sum(1 for c in lista if c.situacion == "APAGADA"),
        candidatas=lista,
    )
