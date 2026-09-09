"""
P3 - Catalogo / CU-11  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2
Caso de uso: CU-11 Gestionar imagenes de producto

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit: el control de la transaccion vive en el servicio.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.catalogo.models import ImagenProducto, VarianteProducto


def listar_de_producto(db: Session, producto_id: int) -> list[ImagenProducto]:
    """Las imagenes de un producto, en el orden en que se muestran.

    La principal primero: es la que representa al producto en el listado del
    catalogo, asi que encabezar con ella hace que la galeria se lea igual que
    la vitrina. Despues por `orden` y, a igualdad, por `id`, que es estable.
    """
    return list(
        db.scalars(
            select(ImagenProducto)
            .where(ImagenProducto.producto_id == producto_id)
            .order_by(
                ImagenProducto.es_principal.desc(),
                ImagenProducto.orden,
                ImagenProducto.id,
            )
            .options(selectinload(ImagenProducto.variante))
            .execution_options(populate_existing=True)
        )
    )


def obtener(db: Session, imagen_id: int) -> ImagenProducto | None:
    return db.scalar(
        select(ImagenProducto)
        .where(ImagenProducto.id == imagen_id)
        .options(selectinload(ImagenProducto.variante))
        .execution_options(populate_existing=True)
    )


def variante_de_producto(
    db: Session, *, producto_id: int, variante_id: int
) -> VarianteProducto | None:
    """La variante, solo si pertenece a ese producto.

    Se comprueba la pertenencia en la propia consulta: asociar una imagen a la
    variante de OTRO producto pasaria las claves foraneas sin problema --- las
    dos existen --- y dejaria la foto de una camisa colgando de un pantalon.
    """
    return db.scalar(
        select(VarianteProducto).where(
            VarianteProducto.id == variante_id,
            VarianteProducto.producto_id == producto_id,
        )
    )


def principal_de(db: Session, producto_id: int) -> ImagenProducto | None:
    return db.scalar(
        select(ImagenProducto).where(
            ImagenProducto.producto_id == producto_id,
            ImagenProducto.es_principal.is_(True),
        )
    )


def transparente_de_variante(db: Session, variante_id: int) -> ImagenProducto | None:
    return db.scalar(
        select(ImagenProducto).where(
            ImagenProducto.variante_id == variante_id,
            ImagenProducto.es_transparente.is_(True),
        )
    )


def siguiente_orden(db: Session, producto_id: int) -> int:
    """El orden que le toca a una imagen nueva: al final de la galeria."""
    maximo = db.scalar(
        select(func.max(ImagenProducto.orden)).where(
            ImagenProducto.producto_id == producto_id
        )
    )
    return 0 if maximo is None else int(maximo) + 1


def contar_de_producto(db: Session, producto_id: int) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(ImagenProducto).where(
                ImagenProducto.producto_id == producto_id
            )
        )
        or 0
    )


def agregar(db: Session, **campos) -> ImagenProducto:
    imagen = ImagenProducto(**campos)
    db.add(imagen)
    db.flush()
    return imagen


def eliminar(db: Session, imagen: ImagenProducto) -> None:
    db.delete(imagen)
    db.flush()
