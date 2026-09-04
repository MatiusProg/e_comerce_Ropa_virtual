"""
P3 - Catalogo  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 1 (maestros) / 2 (productos y variantes) / 3 (promociones)

Casos de uso del Ciclo 1 que realiza este paquete:
  CU-08 Gestionar categorias, tallas y colores
  CU-09 Gestionar temporadas y colecciones

Este archivo contiene solo los MAESTROS. Producto, VarianteProducto,
ImagenProducto y Promocion llegan en los ciclos 2 y 3.

Talla y Color son entidades propias, no texto libre: en el Ciclo 2 la variante
se define como producto x talla x color y necesita referenciarlas. Como texto
seria imposible filtrar el catalogo por talla, que es el RF07.
"""

from datetime import date

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Auditoria, Base


class Categoria(Auditoria, Base):
    """Clasificacion jerarquica de las prendas.

    La jerarquia es una autorreferencia: una categoria puede tener una padre.
    """

    __tablename__ = "categoria"
    __table_args__ = (
        UniqueConstraint("categoria_padre_id", "nombre", name="uq_categoria_padre_nombre"),
        # Impide que una categoria sea su propia padre. Los ciclos mas largos
        # (A -> B -> A) los valida el servicio: ver la excepcion E2 de CU-08.
        CheckConstraint("categoria_padre_id IS DISTINCT FROM id", name="no_autopadre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    categoria_padre_id: Mapped[int | None] = mapped_column(
        ForeignKey("categoria.id"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(60))
    orden: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    # Autorreferencia: 'padre' es el lado "muchos a uno", asi que es el que
    # lleva remote_side apuntando a la clave primaria.
    padre: Mapped["Categoria | None"] = relationship(
        "Categoria", back_populates="subcategorias", remote_side=[id]
    )
    subcategorias: Mapped[list["Categoria"]] = relationship(
        "Categoria", back_populates="padre"
    )


class Talla(Auditoria, Base):
    """Medida de una prenda. Junto al color define la variante.

    El orden importa: es el que decide como se muestran las tallas en la ficha
    de producto. Sin el, XL aparece antes que S por orden alfabetico.
    """

    __tablename__ = "talla"
    __table_args__ = (
        UniqueConstraint("tipo_prenda", "codigo", name="uq_talla_tipo_codigo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_prenda: Mapped[str] = mapped_column(String(30))
    codigo: Mapped[str] = mapped_column(String(10))
    orden: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Color(Auditoria, Base):
    """Color de una prenda. Junto a la talla define la variante."""

    __tablename__ = "color"
    __table_args__ = (
        # Evita que un valor mal formado llegue a la interfaz y rompa la
        # muestra de color.
        CheckConstraint("hexadecimal ~ '^#[0-9A-Fa-f]{6}$'", name="hex"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(40), unique=True)
    hexadecimal: Mapped[str] = mapped_column(CHAR(7))
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class Temporada(Auditoria, Base):
    """Ventana comercial a la que pertenecen los productos.

    Es lo que permite medir rotacion por temporada y detectar prendas de
    temporada vencida antes de tener que liquidarlas.
    """

    __tablename__ = "temporada"
    __table_args__ = (
        CheckConstraint("fecha_fin > fecha_inicio", name="rango"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(60), unique=True)
    descripcion: Mapped[str | None] = mapped_column(String(200))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    colecciones: Mapped[list["Coleccion"]] = relationship(back_populates="temporada")


class Coleccion(Auditoria, Base):
    """Conjunto de productos lanzado dentro de una temporada."""

    __tablename__ = "coleccion"
    __table_args__ = (
        UniqueConstraint("temporada_id", "nombre", name="uq_coleccion_temporada_nombre"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    temporada_id: Mapped[int] = mapped_column(ForeignKey("temporada.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(60))
    descripcion: Mapped[str | None] = mapped_column(String(200))
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))

    temporada: Mapped[Temporada] = relationship(back_populates="colecciones")
