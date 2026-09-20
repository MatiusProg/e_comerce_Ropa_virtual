"""
P3 - Catalogo / CU-12  |  capa: servicio (reglas de negocio y transacciones)

Gestionar promociones (RF35) **y aplicarlas**. Lo segundo no esta en el
enunciado del caso de uso, que dice «definir descuentos con vigencia», pero una
promocion que no descuenta nada no es una funcion: es una tabla.

LA REGLA QUE CONCENTRA ESTE MODULO: CUANDO DOS PROMOCIONES SE CRUZAN, GANA LA
MAYOR
------------------------------------------------------------------------------
Dos promociones pueden alcanzar la misma prenda a la vez ---una sobre el
producto y otra sobre su categoria--- y eso es legitimo: no hay forma razonable
de prohibirlo sin obligar al Administrador a revisar todo el catalogo cada vez
que carga una.

Habia tres salidas y se eligio la tercera:

1. **Sumarlas.** 20 % + 15 % = 35 %. Es lo que nadie quiere: dos promociones
   pensadas por separado terminan regalando la prenda sin que nadie lo haya
   decidido.
2. **Que gane la mas especifica** (producto > categoria > temporada). Suena
   ordenado y falla en el caso corriente: si una prenda tiene 10 % propio y
   despues se lanza «toda la categoria al 20 %», el cliente veria 10 % --- menos
   de lo que el cartel de la vitrina promete---.
3. **Que gane la mayor.** El cliente paga el mejor precio que la tienda
   anuncio. Si dos empatan, gana la mas especifica, que es la que alguien puso
   mirando esa prenda.

Se eligio (3). Una tienda que anuncia un descuento y despues cobra otro tiene
un problema peor que el de tener dos promociones cruzadas.

**NO SE ACUMULAN NUNCA.** Se aplica una sola, y el contrato dice cual: la
respuesta lleva el nombre de la promocion que gano, no solo el porcentaje.

EL REDONDEO SE HACE ACA Y UNA SOLA VEZ
---------------------------------------
`monto_unitario` viaja calculado y cuantizado a dos decimales. Si cada pantalla
aplicara el porcentaje por su cuenta, la web y el movil mostrarian precios
distintos de la misma prenda ---y el que se cobrara seria un tercero---.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.catalogo import promociones_repository as repository
from app.modules.catalogo.promociones_models import Promocion
from app.modules.catalogo.promociones_schemas import (
    CambioEstadoIn,
    DescuentoOut,
    PromocionCrearIn,
    PromocionEditarIn,
    PromocionOut,
)

CIEN = Decimal("100")
CENTAVO = Decimal("0.01")

#: Cuando dos promociones empatan en porcentaje, gana la mas especifica: es la
#: que alguien puso mirando esa prenda concreta.
ESPECIFICIDAD = {"PRODUCTO": 3, "CATEGORIA": 2, "TEMPORADA": 1}


def _hoy() -> date:
    """Que dia es **en Bolivia**, no en el servidor.

    Railway corre en UTC y ahi el dia cambia a las 20:00 hora boliviana. Con
    `date.today()`, una promocion que termina «el 30» dejaria de aplicar con
    cuatro horas de tienda todavia abierta y clientes adentro --- y una que
    empieza «el 1» arrancaria la noche anterior---.

    Este fue el primer lugar donde se noto. El 20/09 se llevo la constante y
    el criterio a `app.core.tiempo`, porque el mismo defecto estaba en los
    reportes, en el tablero y en el correlativo de las ventas.
    """
    return tiempo.hoy()


# =====================================================================
# Errores de negocio
# =====================================================================

class ErrorDePromociones(Exception):
    """Base de los errores previstos de CU-12."""


class PromocionInexistente(ErrorDePromociones):
    pass


class NombreDuplicado(ErrorDePromociones):
    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        super().__init__(nombre)


class ObjetivoInexistente(ErrorDePromociones):
    """El producto, la categoria o la temporada que se quiso alcanzar no existe."""

    def __init__(self, alcance: str, objetivo_id: int) -> None:
        self.alcance = alcance
        self.objetivo_id = objetivo_id
        super().__init__(f"{alcance} {objetivo_id}")


class VigenciaInvalida(ErrorDePromociones):
    pass


# =====================================================================
# La costura: que descuento tiene cada prenda
# =====================================================================

@dataclass(frozen=True)
class Descuento:
    """El descuento que gano, ya resuelto en dinero."""

    promocion_id: int
    nombre: str
    porcentaje: Decimal
    monto_unitario: Decimal
    precio_final: Decimal


def _redondear(valor: Decimal) -> Decimal:
    """A dos decimales, redondeo comercial.

    `ROUND_HALF_UP` y no el `ROUND_HALF_EVEN` que Python trae por omision: el
    banquero redondea 0,125 a 0,12 y cualquier persona espera 0,13. En un
    recibo que el cliente lee, la sorpresa vale mas que la simetria
    estadistica.
    """
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _elegir(candidatas: list) -> object | None:
    """La promocion que gana entre las que alcanzan a una prenda.

    Mayor porcentaje; a igualdad, la mas especifica. Ver el encabezado del
    modulo para por que no se suman y por que no gana siempre la especifica.
    """
    if not candidatas:
        return None
    return max(
        candidatas,
        key=lambda c: (c.porcentaje, ESPECIFICIDAD.get(c.alcance, 0)),
    )


def _descuento_de(fila, precio: Decimal) -> Descuento:
    monto = _redondear(precio * fila.porcentaje / CIEN)
    return Descuento(
        promocion_id=fila.promocion_id,
        nombre=fila.nombre,
        porcentaje=fila.porcentaje,
        monto_unitario=monto,
        precio_final=precio - monto,
    )


def descuentos_por_variante(
    db: Session, precios: dict[int, Decimal]
) -> dict[int, Descuento]:
    """COSTURA. El descuento vigente de cada variante, o nada.

    `precios` llega de afuera y no se consulta aca a proposito: quien llama ya
    tiene el precio en la mano ---la vitrina, el carrito, el mostrador--- y
    volver a buscarlo seria una consulta de mas por pantalla. Ademas deja
    probar la regla sin tocar la base.

    Solo devuelve las variantes que **tienen** descuento. Las que no, no
    aparecen: un diccionario con la mitad de las claves en `None` obliga a
    quien lo usa a distinguir «no hay» de «hay uno de cero», y con este
    contrato esa pregunta no existe.
    """
    if not precios:
        return {}

    filas = repository.descuentos_de_variantes(
        db, variante_ids=list(precios), hoy=_hoy()
    )

    por_variante: dict[int, list] = {}
    for fila in filas:
        por_variante.setdefault(fila.variante_id, []).append(fila)

    salida: dict[int, Descuento] = {}
    for variante_id, candidatas in por_variante.items():
        gana = _elegir(candidatas)
        if gana is not None:
            salida[variante_id] = _descuento_de(gana, precios[variante_id])
    return salida


def descuentos_por_producto(
    db: Session, precios: dict[int, Decimal]
) -> dict[int, Descuento]:
    """COSTURA. Igual, pero por producto: es lo que necesita la vitrina.

    Todas las variantes de un producto comparten el descuento, porque los tres
    alcances son del producto o de algo que lo contiene. El precio que se pasa
    suele ser el minimo de sus variantes, que es el que la grilla muestra.
    """
    if not precios:
        return {}

    filas = repository.descuentos_de_productos(
        db, producto_ids=list(precios), hoy=_hoy()
    )

    por_producto: dict[int, list] = {}
    for fila in filas:
        por_producto.setdefault(fila.producto_id, []).append(fila)

    salida: dict[int, Descuento] = {}
    for producto_id, candidatas in por_producto.items():
        gana = _elegir(candidatas)
        if gana is not None:
            salida[producto_id] = _descuento_de(gana, precios[producto_id])
    return salida


def a_contrato(descuento: Descuento | None) -> DescuentoOut | None:
    """De la costura al contrato. Nulo sigue siendo nulo."""
    if descuento is None:
        return None
    return DescuentoOut(
        promocion_id=descuento.promocion_id,
        nombre=descuento.nombre,
        porcentaje=descuento.porcentaje,
        monto_unitario=descuento.monto_unitario,
        precio_final=descuento.precio_final,
    )


# =====================================================================
# El CRUD del Administrador
# =====================================================================

_COLUMNA_DE = {
    "PRODUCTO": "producto_id",
    "CATEGORIA": "categoria_id",
    "TEMPORADA": "temporada_id",
}

_EXISTE = {
    "PRODUCTO": repository.producto_existe,
    "CATEGORIA": repository.categoria_existe,
    "TEMPORADA": repository.temporada_existe,
}


def _armar(fila, hoy: date) -> PromocionOut:
    promocion: Promocion = fila[0]
    nombres = {
        "PRODUCTO": fila.producto_nombre,
        "CATEGORIA": fila.categoria_nombre,
        "TEMPORADA": fila.temporada_nombre,
    }
    objetivo_id = getattr(promocion, _COLUMNA_DE[promocion.alcance])
    vigente = (
        promocion.activa
        and promocion.desde <= hoy
        and (promocion.hasta is None or promocion.hasta >= hoy)
    )
    return PromocionOut(
        id=promocion.id,
        nombre=promocion.nombre,
        alcance=promocion.alcance,
        objetivo_id=objetivo_id,
        objetivo_nombre=nombres[promocion.alcance] or "—",
        porcentaje=promocion.porcentaje,
        desde=promocion.desde,
        hasta=promocion.hasta,
        activa=promocion.activa,
        vigente=vigente,
    )


def listar(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    alcance: str | None = None,
    solo_vigentes: bool = False,
) -> tuple[int, list[PromocionOut]]:
    hoy = _hoy()
    total, filas = repository.listar(
        db,
        pagina=pagina,
        tamano=tamano,
        alcance=alcance,
        solo_vigentes=solo_vigentes,
        hoy=hoy,
    )
    return total, [_armar(f, hoy) for f in filas]


def obtener(db: Session, promocion_id: int) -> PromocionOut:
    fila = repository.obtener(db, promocion_id)
    if fila is None:
        raise PromocionInexistente(promocion_id)
    return _armar(fila, _hoy())


def crear(db: Session, datos: PromocionCrearIn) -> PromocionOut:
    """Alta. **Hace commit.**"""
    if repository.existe_nombre(db, datos.nombre):
        raise NombreDuplicado(datos.nombre)

    # El objetivo se comprueba ANTES de insertar: la clave foranea lo rechaza
    # igual, pero como error de integridad ---que el Administrador lee como
    # «error del sistema»--- en vez de «esa categoria no existe».
    if not _EXISTE[datos.alcance](db, datos.objetivo_id):
        raise ObjetivoInexistente(datos.alcance, datos.objetivo_id)

    promocion = Promocion(
        nombre=datos.nombre,
        alcance=datos.alcance,
        porcentaje=datos.porcentaje,
        desde=datos.desde,
        hasta=datos.hasta,
        activa=datos.activa,
    )
    setattr(promocion, _COLUMNA_DE[datos.alcance], datos.objetivo_id)

    repository.agregar(db, promocion)
    db.commit()
    return obtener(db, promocion.id)


def editar(db: Session, promocion_id: int, datos: PromocionEditarIn) -> PromocionOut:
    """Edicion parcial. **Hace commit.**

    El alcance y el objetivo NO se editan: ver `PromocionEditarIn`.
    """
    promocion = repository.entidad(db, promocion_id)
    if promocion is None:
        raise PromocionInexistente(promocion_id)

    if datos.nombre is not None:
        if repository.existe_nombre(db, datos.nombre, excepto_id=promocion_id):
            raise NombreDuplicado(datos.nombre)
        promocion.nombre = datos.nombre

    if datos.porcentaje is not None:
        promocion.porcentaje = datos.porcentaje

    desde = datos.desde if datos.desde is not None else promocion.desde
    if datos.quitar_hasta:
        hasta = None
    elif datos.hasta is not None:
        hasta = datos.hasta
    else:
        hasta = promocion.hasta

    if hasta is not None and hasta < desde:
        raise VigenciaInvalida()

    promocion.desde = desde
    promocion.hasta = hasta

    db.commit()
    return obtener(db, promocion_id)


def cambiar_estado(
    db: Session, promocion_id: int, datos: CambioEstadoIn
) -> PromocionOut:
    """Encender o apagar. **Hace commit.**

    No hay borrado: una promocion se apaga. Las ventas ya cobradas con ella la
    nombran en su historial, y volver a encenderla la temporada que viene es lo
    normal.
    """
    promocion = repository.entidad(db, promocion_id)
    if promocion is None:
        raise PromocionInexistente(promocion_id)

    promocion.activa = datos.activa
    db.commit()
    return obtener(db, promocion_id)
