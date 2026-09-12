"""
P5 - Catalogo Publico y Disponibilidad  |  capa: modelo (SQLAlchemy)

Ciclo de desarrollo: 2 (catalogo) / 3 (favoritos)

Casos de uso que realiza este paquete:
  CU-17 Consultar catalogo                          [ciclo 2]
  CU-18 Consultar ficha de producto                 [ciclo 2]
  CU-19 Consultar disponibilidad por sucursal       [ciclo 2]
  CU-20 Gestionar favoritos                         [ciclo 3]

Durante el Ciclo 2 este archivo quedo VACIO a proposito: los tres casos de uso
del catalogo publico solo leen tablas de P3 y P4. La primera tabla propia del
paquete llega con CU-20.

`EventoNavegacion` --- la otra entidad que el analisis de arquitectura le asigna
a P5 --- sigue sin declararse: es el historial de navegacion que alimenta al
recomendador del CU-33, y se escribe cuando se construya P10. Registrar cada
vista de producto sin nadie que lo consuma seria escribir una tabla que solo
crece.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Favorito(Base):
    """Una prenda que el Cliente marco para volver a mirarla (CU-20).

    **Es del PRODUCTO, no de la variante, y es la unica excepcion a la decision
    D1 en todo el sistema.** Existencia, reserva y venta apuntan a la variante
    porque son operaciones sobre unidades concretas; un favorito es una
    intencion, y el cliente la declara antes de elegir talla y color --- de
    hecho la declara justamente para volver a decidirlas despues. Guardarlo por
    variante obligaria a marcar «me gusta esta blusa en S negra» y perderia el
    favorito si esa combinacion se desactiva.

    Tambien es lo que lo vuelve util para el **RF31**: lo que el recomendador
    del CU-33 necesita de aca es la CATEGORIA del producto, que es atributo del
    producto y no de la variante.

    No lleva el mixin `Auditoria`: `actualizado_en` no significa nada en una
    fila que solo se crea y se borra. Pero si lleva `creado_en` propio, que es
    lo que permite mostrar la lista con lo ultimo marcado primero --- y es la
    diferencia con `cliente_categoria`, que es una tabla puente sin atributos y
    por eso se declara con `Table(...)` y no con una clase.
    """

    __tablename__ = "favorito"
    __table_args__ = (
        # El listado del cliente siempre filtra por cliente y ordena por fecha.
        # Sin este indice, cada consulta recorre la tabla entera.
        Index("ix_favorito_cliente_creado", "cliente_id", "creado_en"),
    )

    # Clave primaria compuesta: un cliente marca una prenda una vez. La base lo
    # garantiza, de modo que marcar dos veces no puede duplicar --- que es lo
    # que vuelve idempotente al endpoint de alta.
    cliente_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cliente.id", ondelete="CASCADE"), primary_key=True
    )
    producto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("producto.id", ondelete="CASCADE"), primary_key=True
    )

    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
