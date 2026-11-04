"""
P16 - Ofertas / CU-31 y CU-32  |  capa: modelo (SQLAlchemy)

3ra presentación.
- CU-31 Gestionar ofertas y precios mayoristas (RF-56, RF-58)
- CU-32 Aplicar ofertas de fuera de temporada (RF-57)

QUÉ HAY ACÁ Y QUÉ NO
--------------------
Las ofertas manuales de RF-58 YA EXISTEN: son las promociones de CU-12 del
primer parcial (`promociones_models.Promocion`), con su vigencia sobre una
prenda, una categoría o una temporada. No se duplican.

Acá viven las dos cosas nuevas:

- `PrecioMayorista`: «desde N prendas de este producto, cada una a Bs X».
- `ReglaFueraDeTemporada`: el factor medible de RF-57, guardado en la base,
  una fila por empresa.

La oferta automática NO tiene tabla propia: es una `Promocion` con
`origen = 'AUTOMATICA'`. Así la vitrina, la caja y el carrito ya la aplican
sin cambiar nada, y el Administrador la apaga con el mismo interruptor que
cualquier promoción (RN-16).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Auditoria, Base, DeEmpresa


class PrecioMayorista(DeEmpresa, Auditoria, Base):
    """Un escalón de precio mayorista de un producto (RF-56).

    POR PRODUCTO Y NO POR VARIANTE
    ------------------------------
    Quien compra al por mayor lleva «doce poleras», no «doce poleras M
    negras»: mezcla tallas y colores. Por eso la cantidad mínima se cuenta
    sumando TODAS las variantes del producto que van en el ticket o en el
    carrito, y el escalón se define una sola vez por producto.

    UN PRECIO Y NO UN PORCENTAJE
    ----------------------------
    Lo que el mayorista negocia es «a Bs 70 la unidad». Las variantes de un
    mismo producto pueden tener precios distintos; si alguna ya es más barata
    que el mayorista, se queda con su precio, porque RN-15 cobra siempre el
    más bajo y nunca suma descuentos.

    Puede haber varios escalones (desde 6, desde 12...): se aplica el más alto
    que se alcanza.
    """

    __tablename__ = "precio_mayorista"
    __table_args__ = (
        # Desde 2: «desde 1 unidad» no es un precio mayorista, es cambiar el
        # precio de lista.
        CheckConstraint("cantidad_minima >= 2", name="cantidad_minima_mayorista"),
        CheckConstraint("precio_unitario > 0", name="precio_positivo"),
        UniqueConstraint(
            "empresa_id", "producto_id", "cantidad_minima",
            name="uq_precio_mayorista_producto_cantidad",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("producto.id"), index=True
    )
    cantidad_minima: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class ReglaFueraDeTemporada(DeEmpresa, Auditoria, Base):
    """El factor medible de RF-57, uno por empresa.

    Una prenda califica cuando se cumplen LAS DOS condiciones (RN-16):

    - su temporada terminó hace al menos `dias_desde_fin` días, y
    - le quedan al menos `existencia_minima` unidades disponibles, sumando
      todas las sucursales (la «existencia sobrante»).

    Entonces se le crea una promoción automática de `porcentaje`. Con
    `activa = false` no se crea ninguna nueva; las que ya existen se apagan
    una por una desde promociones.
    """

    __tablename__ = "regla_fuera_de_temporada"
    __table_args__ = (
        UniqueConstraint("empresa_id", name="uq_regla_fuera_de_temporada_empresa"),
        CheckConstraint("dias_desde_fin >= 0", name="dias_no_negativos"),
        CheckConstraint("existencia_minima >= 1", name="existencia_positiva"),
        CheckConstraint(
            "porcentaje > 0 AND porcentaje <= 90", name="porcentaje_regla_acotado"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    dias_desde_fin: Mapped[int] = mapped_column(Integer, server_default=text("30"))
    existencia_minima: Mapped[int] = mapped_column(Integer, server_default=text("10"))
    porcentaje: Mapped[Decimal] = mapped_column(Numeric(5, 2), server_default=text("30"))


__all__ = ["PrecioMayorista", "ReglaFueraDeTemporada"]
