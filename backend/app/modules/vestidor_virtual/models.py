"""
P9 - Vestidor Virtual (RA)  |  capa: modelo (SQLAlchemy)
Ciclo de desarrollo: 3, ampliado en la 3ra presentacion del 2do parcial
Casos de uso que realiza este paquete:
  CU-21 Utilizar vestidor virtual (1er parcial, en el telefono)
  CU-36 Preparar prenda para el probador
  CU-37 Probarse una prenda con su talla real
  CU-38 Generar foto realista de la prueba

Las dos tablas de la migracion `0041_cu36_probador`.

`PuntoPrenda` es la CALIBRACION de una imagen: donde estan los hombros y el
ruedo de la prenda dentro del PNG, en coordenadas relativas (0 a 1). Con eso y
los centimetros de `medida_talla` el probador sabe cuantos pixeles de la imagen
son un centimetro de tela, y puede dibujarla a su tamano real sobre la foto del
cliente.

`SesionVestidorVirtual` es la entidad que la arquitectura declaraba desde el
Ciclo 3 y nunca se escribio: el HECHO de una prueba ---quien, que variante,
como le quedaba--- y, si la pidio, la foto realista del CU-38.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Auditoria, Base, DeEmpresa

#: Como se ubicaron los hombros del cliente en su foto.
METODOS = ("POSE", "MANUAL")


class PuntoPrenda(DeEmpresa, Auditoria, Base):
    """Los puntos de referencia de una imagen de vestidor (CU-36)."""

    __tablename__ = "punto_prenda"
    __table_args__ = (
        CheckConstraint(
            "hombro_izq_x BETWEEN 0 AND 1 AND hombro_izq_y BETWEEN 0 AND 1 AND "
            "hombro_der_x BETWEEN 0 AND 1 AND hombro_der_y BETWEEN 0 AND 1 AND "
            "ruedo_x BETWEEN 0 AND 1 AND ruedo_y BETWEEN 0 AND 1",
            name="dentro_de_la_imagen",
        ),
        CheckConstraint("hombro_izq_x < hombro_der_x", name="hombros_en_orden"),
        CheckConstraint(
            "ruedo_y > hombro_izq_y AND ruedo_y > hombro_der_y", name="ruedo_debajo"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    imagen_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("imagen_producto.id", ondelete="CASCADE"),
        unique=True,
    )
    hombro_izq_x: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    hombro_izq_y: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    hombro_der_x: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    hombro_der_y: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    ruedo_x: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    ruedo_y: Mapped[Decimal] = mapped_column(Numeric(5, 4))


class SesionVestidorVirtual(DeEmpresa, Base):
    """Una prueba del cliente (CU-37) y su foto realista, si la pidio (CU-38)."""

    __tablename__ = "sesion_probador"
    __table_args__ = (
        CheckConstraint(f"metodo IN {METODOS}", name="metodo_valido"),
        CheckConstraint(
            "(foto_ruta IS NULL) = (foto_generada_por IS NULL)", name="foto_completa"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    variante_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("variante_producto.id", ondelete="CASCADE")
    )
    metodo: Mapped[str] = mapped_column(String(10))
    #: La clasificacion de `medidas.tallaje` (A_TU_MEDIDA, HOLGADA...), o None
    #: si el cliente no tenia medidas o la prenda no tenia tabla.
    ajuste: Mapped[str | None] = mapped_column(String(15))
    talla_recomendada: Mapped[str | None] = mapped_column(String(10))
    foto_ruta: Mapped[str | None] = mapped_column(String(255))
    foto_generada_por: Mapped[str | None] = mapped_column(String(60))
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
