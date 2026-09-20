"""
P3 - Catalogo / CU-12  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 3
Caso de uso: CU-12 Gestionar promociones  (RF35)

ARCHIVO PROPIO DENTRO DEL PAQUETE AJENO
----------------------------------------
`models.py` de catalogo lo tocan CU-08, CU-09, CU-10 y CU-11. La tabla de
promociones vive aparte con el mismo patron que `carrito_models.py` en P7 y
`temporadas_*` en este mismo paquete: dos personas no editan las mismas lineas.

EL DESCUENTO ES UN PORCENTAJE, NO UN MONTO
-------------------------------------------
Se eligio uno solo y es el porcentaje, por tres razones:

1. **El alcance es amplio.** Una promocion se define sobre un producto, una
   CATEGORIA o una TEMPORADA. «Bs 50 de descuento» sobre una categoria cuyas
   prendas van de Bs 80 a Bs 900 es regalar la primera y no mover la ultima.
2. **No puede dejar el precio en negativo.** Con un porcentaje acotado a
   (0, 100] el descuento nunca supera el precio, que es justo lo que exige el
   CHECK `ck_detalle_venta_descuento_acotado` cuando la venta se congela.
3. **Sobrevive a un cambio de precio.** Si la tienda sube una prenda, el
   porcentaje sigue significando lo mismo; un monto fijo pasaria a ser otra
   cosa sin que nadie lo tocara.

Agregar el monto fijo despues es una columna mas y un discriminador; no obliga
a reescribir lo que ya este guardado, porque cada promocion diria de que tipo
es. Queda anotado en la ficha.

LA VIGENCIA SE GUARDA EN FECHAS, NO EN MARCAS DE TIEMPO
--------------------------------------------------------
Quien carga una promocion piensa «del 1 al 15 de octubre», no «del 1 a las
00:00:00-04:00». Guardar `timestamptz` obligaria a inventar una hora de corte
que el Administrador nunca eligio.

El precio de esa decision es que hay que preguntar **que dia es en Bolivia**,
no en el servidor: Railway corre en UTC, y `date.today()` ahi adelanta el dia a
las 20:00 hora boliviana. Una promocion que termina «el 30» dejaria de aplicar
con cuatro horas de tienda todavia abierta y clientes adentro. Eso se resuelve
en el servicio, con `_hoy()`.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Auditoria, Base

#: Sobre que se define la promocion. Los tres alcances del RF35, y nada mas:
#: una promocion «sobre todo el catalogo» no esta pedida y se puede armar con
#: una por categoria, que ademas deja rastro de cual se aplico.
ALCANCES_PROMOCION = ("PRODUCTO", "CATEGORIA", "TEMPORADA")


class Promocion(Auditoria, Base):
    """Un descuento con vigencia sobre un producto, una categoria o una temporada.

    NO GUARDA A QUE VARIANTES ALCANZA, Y ES A PROPOSITO
    ----------------------------------------------------
    Se guarda el alcance ---«la categoria 4»--- y no la lista de variantes que
    hoy caen dentro. Materializar la lista obligaria a recalcularla cada vez que
    entra un producto nuevo a la categoria, y el dia que alguien se olvidara, la
    promocion dejaria afuera prendas que el cartel de la vitrina promete.

    Con el alcance guardado, un producto que entra a una categoria en promocion
    entra ya con el descuento puesto, sin que nadie haga nada.

    POR QUE TRES COLUMNAS NULABLES Y NO UNA GENERICA
    -------------------------------------------------
    Una sola columna `objetivo_id` con el `alcance` de discriminador seria mas
    corta y **no tendria clave foranea**: nada impediria apuntar a una categoria
    que ya no existe, y el borrado de un producto dejaria promociones colgadas
    apuntando al vacio. Con tres FK, la base garantiza que el objetivo existe y
    el CHECK garantiza que hay exactamente uno.
    """

    __tablename__ = "promocion"
    __table_args__ = (
        CheckConstraint(
            "alcance IN ('" + "', '".join(ALCANCES_PROMOCION) + "')", name="alcance"
        ),
        # (0, 100]. El cero no es una promocion, es no tener ninguna ---y una
        # fila que no descuenta nada solo sirve para confundir al que la lea---.
        # El 100 si: regalar una prenda en liquidacion es una decision real.
        CheckConstraint(
            "porcentaje > 0 AND porcentaje <= 100", name="porcentaje_acotado"
        ),
        CheckConstraint("hasta IS NULL OR hasta >= desde", name="vigencia_coherente"),
        # EXACTAMENTE UN OBJETIVO, y que coincida con el alcance declarado. Sin
        # esto se puede guardar una promocion de alcance CATEGORIA apuntando a
        # un producto, que es una fila que ninguna consulta va a encontrar y
        # nadie va a entender por que no se aplica.
        CheckConstraint(
            "(alcance = 'PRODUCTO'  AND producto_id  IS NOT NULL"
            " AND categoria_id IS NULL AND temporada_id IS NULL)"
            " OR (alcance = 'CATEGORIA' AND categoria_id IS NOT NULL"
            " AND producto_id IS NULL AND temporada_id IS NULL)"
            " OR (alcance = 'TEMPORADA' AND temporada_id IS NOT NULL"
            " AND producto_id IS NULL AND categoria_id IS NULL)",
            name="un_objetivo_segun_alcance",
        ),
        # La consulta que corre en CADA pagina de la vitrina, en cada carrito y
        # en cada cobro es «las promociones activas vigentes hoy». Sin este
        # indice recorre la tabla entera cada vez.
        Index("ix_promocion_vigencia", "activa", "desde", "hasta"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80))

    alcance: Mapped[str] = mapped_column(String(10), index=True)

    #: Exactamente uno de los tres no es nulo. Lo garantiza el CHECK.
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("producto.id"), index=True
    )
    categoria_id: Mapped[int | None] = mapped_column(
        ForeignKey("categoria.id"), index=True
    )
    temporada_id: Mapped[int | None] = mapped_column(
        ForeignKey("temporada.id"), index=True
    )

    #: (0, 100]. Con dos decimales porque «12,5 %» es una promocion corriente.
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    desde: Mapped[date] = mapped_column(Date)
    #: Nulo = sin fecha de fin. Una liquidacion «hasta agotar stock» no tiene
    #: una fecha que el Administrador pueda saber de antemano, y obligarlo a
    #: inventar una lo llevaria a poner un ano cualquiera.
    hasta: Mapped[date | None] = mapped_column(Date)

    #: Apagarla sin borrarla. Se desactiva y no se elimina porque las ventas ya
    #: hechas la nombran en su historial ---y porque volver a encenderla en la
    #: proxima temporada es lo normal---.
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


__all__ = ["ALCANCES_PROMOCION", "Promocion"]
