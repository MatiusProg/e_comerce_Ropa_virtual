"""
P9 - Vestidor Virtual (RA)  |  capa: repositorio (consultas)

Ciclo de desarrollo: 3
Caso de uso: CU-21

Regla: aqui vive el SQL. Ninguna regla de negocio y ningun `commit`.

UNA SOLA CONSULTA, Y CRUZA A P3
-------------------------------
P9 no tiene tablas propias todavia --- `SesionVestidorVirtual` esta declarada
en la arquitectura y sin escribir ---, asi que lo unico que hace este modulo
es leer de `imagen_producto`, que es de P3. Es la dependencia que la seccion
4.2 ya declara: «depende de P3 (imagen y variante de la prenda)».
"""
from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import (
    Color,
    ImagenProducto,
    Producto,
    Talla,
    VarianteProducto,
)


def prenda_de_variante(db: Session, variante_id: int) -> Row | None:
    """El PNG del vestidor de una variante, con como se llama la prenda.

    Se exige `es_transparente` Y `variante_id`: son las dos condiciones que
    vuelven a una imagen un activo de realidad aumentada. Sin la primera es una
    foto de catalogo con fondo; sin la segunda es una figura «del producto» sin
    talla ni color, que por la decision D1 no existe.

    Tambien se exige que la variante y el producto sigan ACTIVOS: probarse algo
    que la tienda dejo de ofrecer termina en un carrito que no se puede pagar.
    """
    return db.execute(
        select(
            ImagenProducto.ruta,
            Producto.nombre.label("producto"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
        )
        .join(VarianteProducto, VarianteProducto.id == ImagenProducto.variante_id)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .where(
            ImagenProducto.variante_id == variante_id,
            ImagenProducto.es_transparente.is_(True),
            VarianteProducto.activa.is_(True),
            Producto.activo.is_(True),
        )
    ).first()
