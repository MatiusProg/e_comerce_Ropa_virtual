"""
P3 - Catalogo / CU-08  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1
Caso de uso: CU-08 Gestionar categorias, tallas y colores

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalogo.maestros import repository
from app.modules.catalogo.maestros.schemas import (
    CategoriaCrearIn,
    CategoriaEditarIn,
    CategoriaOut,
    ColorCrearIn,
    ColorEditarIn,
    ColorOut,
    TallaCrearIn,
    TallaEditarIn,
    TallaOut,
)
from app.modules.catalogo.models import Categoria


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeMaestros(Exception):
    """Base de los errores previstos de CU-08."""


class CategoriaInexistente(ErrorDeMaestros):
    """No hay categoria con ese identificador."""


class TallaInexistente(ErrorDeMaestros):
    """No hay talla con ese identificador."""


class ColorInexistente(ErrorDeMaestros):
    """No hay color con ese identificador."""


class NombreDuplicado(ErrorDeMaestros):
    """Excepcion E1."""


class CicloEnLaJerarquia(ErrorDeMaestros):
    """Excepcion E2: el padre elegido cuelga de la propia categoria."""


class TieneDependencias(ErrorDeMaestros):
    """Excepcion E3: hay algo que depende del elemento y se conserva."""


#: Restricciones de unicidad de la base, tal como se llaman en PostgreSQL.
#:
#: Se nombran aqui y no sueltas en cada bloque porque un nombre mal escrito no
#: lo detecta nadie: el `except IntegrityError` simplemente no entra, y lo que
#: deberia ser un 409 sale como un 500. Con constantes, una sola prueba
#: --- test_los_nombres_de_restriccion_existen --- verifica que los tres estan
#: en la base.
UQ_CATEGORIA = "uq_categoria_padre_nombre"
UQ_TALLA = "uq_talla_tipo_codigo"
UQ_COLOR = "uq_color_nombre"


def _viola(exc: IntegrityError, restriccion: str) -> bool:
    """Indica si la violacion corresponde a esa restriccion.

    Se apoya en la convencion de nombres de app/db/base.py.
    """
    return restriccion in str(exc.orig)


# --- Categorias ----------------------------------------------------------

def _armar_arbol(categorias: list[Categoria]) -> list[CategoriaOut]:
    """Convierte la lista plana en el arbol del paso 2.

    Se arma en una sola pasada: primero un nodo por categoria, despues cada uno
    se cuelga de su padre. Recorrer la relacion `subcategorias` del ORM daria
    el mismo resultado disparando una consulta por rama.

    Una categoria cuyo padre no este en la lista se trata como raiz. No deberia
    pasar --- la clave foranea lo impide ---, pero si pasara, dejarla afuera
    la volveria invisible en la unica pantalla desde la que se puede arreglar.
    """
    nodos = {c.id: CategoriaOut.model_validate(c, from_attributes=True) for c in categorias}
    for nodo in nodos.values():
        nodo.subcategorias = []

    raices: list[CategoriaOut] = []
    for categoria in categorias:
        nodo = nodos[categoria.id]
        padre = nodos.get(categoria.categoria_padre_id) if categoria.categoria_padre_id else None
        if padre is None:
            raices.append(nodo)
        else:
            padre.subcategorias.append(nodo)
    return raices


def listar_categorias(db: Session) -> list[CategoriaOut]:
    """Paso 2: el arbol de categorias con su orden y estado."""
    return _armar_arbol(repository.listar_categorias(db))


def obtener_categoria(db: Session, categoria_id: int) -> CategoriaOut:
    categoria = repository.obtener_categoria(db, categoria_id)
    if categoria is None:
        raise CategoriaInexistente(str(categoria_id))
    nodo = CategoriaOut.model_validate(categoria, from_attributes=True)
    nodo.subcategorias = []
    return nodo


def _validar_padre(db: Session, categoria_padre_id: int | None) -> None:
    if categoria_padre_id is None:
        return
    if repository.obtener_categoria(db, categoria_padre_id) is None:
        raise CategoriaInexistente(str(categoria_padre_id))


def crear_categoria(db: Session, datos: CategoriaCrearIn) -> CategoriaOut:
    """Pasos 5 a 7: valida la unicidad entre hermanas y registra la categoria."""
    _validar_padre(db, datos.categoria_padre_id)

    # Excepcion E1.
    if repository.existe_hermana_con_nombre(
        db, nombre=datos.nombre, categoria_padre_id=datos.categoria_padre_id
    ):
        raise NombreDuplicado(datos.nombre)

    try:
        categoria = repository.agregar_categoria(
            db,
            nombre=datos.nombre,
            categoria_padre_id=datos.categoria_padre_id,
            orden=datos.orden,
            activa=datos.activa,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_CATEGORIA):
            raise NombreDuplicado(datos.nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_categoria(db, categoria.id)


def editar_categoria(
    db: Session, categoria_id: int, datos: CategoriaEditarIn
) -> CategoriaOut:
    """Flujo alternativo 3a, incluida la reubicacion en el arbol."""
    categoria = repository.obtener_categoria(db, categoria_id)
    if categoria is None:
        raise CategoriaInexistente(str(categoria_id))

    mueve_de_padre = "categoria_padre_id" in datos.model_fields_set
    padre_nuevo = datos.categoria_padre_id if mueve_de_padre else categoria.categoria_padre_id

    if mueve_de_padre and padre_nuevo != categoria.categoria_padre_id:
        _validar_padre(db, padre_nuevo)

        # Excepcion E2. Basta con que el padre elegido sea la propia categoria
        # o cualquiera de sus descendientes: en los dos casos la rama quedaria
        # colgada de si misma y desapareceria del arbol.
        if padre_nuevo is not None:
            if padre_nuevo == categoria_id:
                raise CicloEnLaJerarquia(str(padre_nuevo))
            if padre_nuevo in repository.ids_de_descendientes(db, categoria_id):
                raise CicloEnLaJerarquia(str(padre_nuevo))

    nombre_nuevo = datos.nombre if datos.nombre is not None else categoria.nombre
    if repository.existe_hermana_con_nombre(
        db,
        nombre=nombre_nuevo,
        categoria_padre_id=padre_nuevo,
        excepto_id=categoria_id,
    ):
        raise NombreDuplicado(nombre_nuevo)

    try:
        if datos.nombre is not None:
            categoria.nombre = datos.nombre
        if datos.orden is not None:
            categoria.orden = datos.orden
        if mueve_de_padre:
            categoria.categoria_padre_id = padre_nuevo
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_CATEGORIA):
            raise NombreDuplicado(nombre_nuevo) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_categoria(db, categoria_id)


def cambiar_estado_categoria(
    db: Session, categoria_id: int, activa: bool
) -> CategoriaOut:
    """Flujo alternativo 3b: deja de ofrecerse para variantes nuevas.

    Desactivar NO cascadea a las subcategorias: son elementos propios y el caso
    de uso no lo pide. Ocultarlas de un plumazo dejaria al administrador sin
    entender por que desaparecieron ramas enteras.
    """
    categoria = repository.obtener_categoria(db, categoria_id)
    if categoria is None:
        raise CategoriaInexistente(str(categoria_id))

    try:
        categoria.activa = activa
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_categoria(db, categoria_id)


def eliminar_categoria(db: Session, categoria_id: int) -> None:
    """Excepcion E3: no se elimina si algo cuelga de ella."""
    categoria = repository.obtener_categoria(db, categoria_id)
    if categoria is None:
        raise CategoriaInexistente(str(categoria_id))

    if repository.contar_subcategorias(db, categoria_id):
        raise TieneDependencias(str(categoria_id))

    try:
        repository.eliminar_categoria(db, categoria)
        db.commit()
    except IntegrityError as exc:
        # Red de seguridad: si en el Ciclo 2 aparece una clave foranea que
        # todavia no contemplamos, se informa como dependencia en vez de
        # devolver un 500.
        db.rollback()
        raise TieneDependencias(str(categoria_id)) from exc
    except Exception:
        db.rollback()
        raise


# --- Tallas (flujo alternativo 1a) ---------------------------------------

def listar_tallas(
    db: Session, *, tipo_prenda: str | None = None, activa: bool | None = None
) -> list[TallaOut]:
    return [
        TallaOut.model_validate(t, from_attributes=True)
        for t in repository.listar_tallas(db, tipo_prenda=tipo_prenda, activa=activa)
    ]


def listar_tipos_de_prenda(db: Session) -> list[str]:
    return repository.listar_tipos_de_prenda(db)


def crear_talla(db: Session, datos: TallaCrearIn) -> TallaOut:
    if repository.existe_talla(db, tipo_prenda=datos.tipo_prenda, codigo=datos.codigo):
        raise NombreDuplicado(datos.codigo)

    try:
        talla = repository.agregar_talla(
            db,
            tipo_prenda=datos.tipo_prenda,
            codigo=datos.codigo,
            orden=datos.orden,
            activa=datos.activa,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_TALLA):
            raise NombreDuplicado(datos.codigo) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return TallaOut.model_validate(talla, from_attributes=True)


def editar_talla(db: Session, talla_id: int, datos: TallaEditarIn) -> TallaOut:
    talla = repository.obtener_talla(db, talla_id)
    if talla is None:
        raise TallaInexistente(str(talla_id))

    tipo = datos.tipo_prenda if datos.tipo_prenda is not None else talla.tipo_prenda
    codigo = datos.codigo if datos.codigo is not None else talla.codigo

    if repository.existe_talla(db, tipo_prenda=tipo, codigo=codigo, excepto_id=talla_id):
        raise NombreDuplicado(codigo)

    try:
        talla.tipo_prenda = tipo
        talla.codigo = codigo
        if datos.orden is not None:
            talla.orden = datos.orden
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_TALLA):
            raise NombreDuplicado(codigo) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return TallaOut.model_validate(talla, from_attributes=True)


def cambiar_estado_talla(db: Session, talla_id: int, activa: bool) -> TallaOut:
    """Flujo 3b: deja de ofrecerse, pero se conserva en las variantes que la usan."""
    talla = repository.obtener_talla(db, talla_id)
    if talla is None:
        raise TallaInexistente(str(talla_id))

    try:
        talla.activa = activa
        db.commit()
    except Exception:
        db.rollback()
        raise

    return TallaOut.model_validate(talla, from_attributes=True)


def eliminar_talla(db: Session, talla_id: int) -> None:
    talla = repository.obtener_talla(db, talla_id)
    if talla is None:
        raise TallaInexistente(str(talla_id))

    try:
        repository.eliminar_talla(db, talla)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TieneDependencias(str(talla_id)) from exc
    except Exception:
        db.rollback()
        raise


# --- Colores (flujo alternativo 1b) --------------------------------------

def listar_colores(db: Session, *, activo: bool | None = None) -> list[ColorOut]:
    return [
        ColorOut.model_validate(c, from_attributes=True)
        for c in repository.listar_colores(db, activo=activo)
    ]


def crear_color(db: Session, datos: ColorCrearIn) -> ColorOut:
    if repository.existe_color_con_nombre(db, datos.nombre):
        raise NombreDuplicado(datos.nombre)

    try:
        color = repository.agregar_color(
            db,
            nombre=datos.nombre,
            hexadecimal=datos.hexadecimal,
            activo=datos.activo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_COLOR):
            raise NombreDuplicado(datos.nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return ColorOut.model_validate(color, from_attributes=True)


def editar_color(db: Session, color_id: int, datos: ColorEditarIn) -> ColorOut:
    color = repository.obtener_color(db, color_id)
    if color is None:
        raise ColorInexistente(str(color_id))

    nombre = datos.nombre if datos.nombre is not None else color.nombre
    if repository.existe_color_con_nombre(db, nombre, excepto_id=color_id):
        raise NombreDuplicado(nombre)

    try:
        color.nombre = nombre
        if datos.hexadecimal is not None:
            color.hexadecimal = datos.hexadecimal
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, UQ_COLOR):
            raise NombreDuplicado(nombre) from exc
        raise
    except Exception:
        db.rollback()
        raise

    return ColorOut.model_validate(color, from_attributes=True)


def cambiar_estado_color(db: Session, color_id: int, activo: bool) -> ColorOut:
    color = repository.obtener_color(db, color_id)
    if color is None:
        raise ColorInexistente(str(color_id))

    try:
        color.activo = activo
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ColorOut.model_validate(color, from_attributes=True)


def eliminar_color(db: Session, color_id: int) -> None:
    color = repository.obtener_color(db, color_id)
    if color is None:
        raise ColorInexistente(str(color_id))

    try:
        repository.eliminar_color(db, color)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TieneDependencias(str(color_id)) from exc
    except Exception:
        db.rollback()
        raise
