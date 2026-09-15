"""
P3 - Catalogo / CU-38  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 3
Caso de uso: CU-38 Registrar productos del proveedor  (RF37)

Realiza el RF37. Hasta el Ciclo 2, el Proveedor era un actor principal que **no
iniciaba ningun caso de uso**: existia como ficha que el Administrador daba de
alta (CU-07) y, si se le habilitaba acceso, podia mirar esa ficha. Nada mas.
Este caso de uso es lo que lo convierte en un actor de verdad.

QUE HACE ESTE ARCHIVO, QUE ES CASI NADA
---------------------------------------
El CRUD de productos ya existe: es CU-10, en `service.py`, con sus maestros,
su regla de coherencia entre temporada y coleccion y su generacion de SKU. Aqui
NO se reimplementa nada de eso --- duplicarlo dejaria dos reglas de negocio para
la misma tabla, y el dia que una cambie la otra no.

Lo unico que agrega este archivo es **el ambito**, y son tres reglas:

  1. El `proveedor_id` sale del TOKEN. Nunca del cuerpo de la peticion, que ni
     siquiera lo acepta --- ver `proveedor_schemas.py`.
  2. Un producto que no es suyo **no existe** para el. Se responde 404, no 403.
  3. Lo que registra el Proveedor **nace inactivo**; publicarlo es de CU-10.

La regla 2 merece su parrafo. Un 403 confirmaria que ese identificador
corresponde a un producto real de otro proveedor, y recorrer los numeros seria
un censo del catalogo ajeno --- que incluye a su competencia ---. Es el mismo
criterio por el que CU-02 no distingue correo inexistente de contrasena
incorrecta, y por el que CU-41 no distingue un enlace que nunca existio de uno
ya usado.
"""
from sqlalchemy.orm import Session

from app.modules.catalogo import repository, service
from app.modules.catalogo import temporadas_service
from app.modules.catalogo.maestros import service as maestros_service
from app.modules.catalogo.proveedor_schemas import (
    ListasDelFormularioOut,
    MiProductoCrearIn,
    MiProductoEditarIn,
)
from app.modules.catalogo.schemas import (
    CambioEstadoIn,
    GenerarVariantesIn,
    GenerarVariantesOut,
    PaginaProductos,
    ProductoCrearIn,
    ProductoEditarIn,
    ProductoOut,
)
from app.modules.organizacion import proveedores_repository

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.


# --- Errores de negocio --------------------------------------------------

class ErrorDelProveedor(Exception):
    """Base de los errores propios de CU-38."""


class SinFichaDeProveedor(ErrorDelProveedor):
    """El usuario tiene rol PROVEEDOR pero ninguna ficha de proveedor.

    Pasa si un Administrador le asigna el rol por CU-03 en vez de habilitarle el
    acceso desde la ficha por CU-07. No es un error del Proveedor y el mensaje
    lo dice: no hay nada que pueda hacer el desde su lado.
    """


class ProveedorDesactivado(ErrorDelProveedor):
    """La ficha existe pero esta dada de baja.

    Dejar de trabajar con un proveedor tiene que cortarle tambien la capacidad
    de seguir cargando productos; si no, la baja de CU-07 seria decorativa.
    """


class ProductoAjeno(ErrorDelProveedor):
    """El producto no existe, o existe y es de otro proveedor.

    Los dos casos son UNA sola excepcion a proposito. Ver la cabecera.
    """


# --- El ambito, que es todo el caso de uso -------------------------------

def _proveedor_del_usuario(db: Session, usuario_id: int) -> int:
    """El identificador de proveedor que le corresponde al token. Nunca otro.

    Es la unica puerta por la que entra un `proveedor_id` en este archivo: si
    alguna funcion de aqui aceptara uno por parametro, el caso de uso entero
    dependeria de que ningun router se olvide de comprobarlo.
    """
    fila = proveedores_repository.obtener_detalle_por_usuario(db, usuario_id)
    if fila is None:
        raise SinFichaDeProveedor(str(usuario_id))
    if not fila.activo:
        raise ProveedorDesactivado(str(fila.id))
    return fila.id


def _producto_propio(db: Session, usuario_id: int, producto_id: int) -> int:
    """Comprueba que el producto sea suyo y devuelve su `proveedor_id`.

    Un producto sin proveedor --- `proveedor_id` es nulo en el esquema, y el
    catalogo sembrado tiene varios asi --- tampoco es de nadie en particular, y
    por lo tanto tampoco es suyo.
    """
    proveedor_id = _proveedor_del_usuario(db, usuario_id)

    producto = repository.obtener_producto(db, producto_id)
    if producto is None or producto.proveedor_id != proveedor_id:
        raise ProductoAjeno(str(producto_id))

    return proveedor_id


# --- Listas para el formulario -------------------------------------------

def listas_del_formulario(db: Session) -> ListasDelFormularioOut:
    """Los maestros activos que el alta necesita para sus selectores.

    Solo lo ACTIVO: es lo unico que se puede elegir al registrar algo nuevo.
    Una categoria dada de baja sigue existiendo para los productos que ya la
    tienen, pero ofrecerla en un alta seria crear deuda a proposito.

    Las categorias vienen como arbol, tal cual las arma CU-08; aplanarlas aqui
    seria inventar una segunda forma de la misma lista.
    """
    return ListasDelFormularioOut(
        categorias=maestros_service.listar_categorias(db),
        tallas=maestros_service.listar_tallas(db, activa=True),
        colores=maestros_service.listar_colores(db, activo=True),
        temporadas=temporadas_service.listar_temporadas(db, activa=True),
        colecciones=temporadas_service.listar_colecciones(db, activa=True),
    )


# --- Flujo principal -----------------------------------------------------

def listar_mis_productos(
    db: Session,
    usuario_id: int,
    *,
    pagina: int,
    tamano: int,
    busqueda: str | None = None,
    categoria_id: int | None = None,
    temporada_id: int | None = None,
    coleccion_id: int | None = None,
    activo: bool | None = None,
) -> PaginaProductos:
    """Paso 2: lo que abastece este proveedor, y nada mas.

    `proveedor_id` no es un filtro que el cliente pueda mandar: se impone. Por
    eso esta funcion no lo recibe como parametro --- si lo recibiera, alguien
    podria pasarlo desde el router.
    """
    return service.listar_productos(
        db,
        pagina=pagina,
        tamano=tamano,
        busqueda=busqueda,
        categoria_id=categoria_id,
        temporada_id=temporada_id,
        coleccion_id=coleccion_id,
        proveedor_id=_proveedor_del_usuario(db, usuario_id),
        activo=activo,
    )


def obtener_mi_producto(db: Session, usuario_id: int, producto_id: int) -> ProductoOut:
    """Detalle de un producto propio, con sus variantes."""
    _producto_propio(db, usuario_id, producto_id)
    return service.obtener_producto(db, producto_id)


def registrar_mi_producto(
    db: Session, usuario_id: int, datos: MiProductoCrearIn
) -> ProductoOut:
    """Pasos 4 a 6: el Proveedor registra una prenda que abastece.

    NACE INACTIVA, y es la decision de fondo del caso de uso. El RF37 dice
    «registrar o enviar la informacion de los productos que abastece»: registrar
    no es publicar. Si naciera activa, cualquier proveedor con acceso podria
    poner prendas en la vitrina de la tienda sin que nadie las mire --- y la
    vitrina es lo que ve el cliente.

    Publicarla es del Administrador, por CU-10. Eso da el control que da una
    aprobacion sin inventar una tabla de aprobaciones ni un estado nuevo: el
    `activo` que ya existe alcanza.

    Todo lo demas ---maestros, coherencia entre temporada y coleccion, codigo
    duplicado--- lo valida CU-10, que es donde vive esa regla.
    """
    proveedor_id = _proveedor_del_usuario(db, usuario_id)

    return service.crear_producto(
        db,
        ProductoCrearIn(
            codigo=datos.codigo,
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            categoria_id=datos.categoria_id,
            proveedor_id=proveedor_id,
            temporada_id=datos.temporada_id,
            coleccion_id=datos.coleccion_id,
            precio_base=datos.precio_base,
            activo=False,
        ),
    )


def editar_mi_producto(
    db: Session, usuario_id: int, producto_id: int, datos: MiProductoEditarIn
) -> ProductoOut:
    """Flujo alternativo 3a: corregir los datos de una prenda propia.

    El `proveedor_id` no viaja en `ProductoEditarIn` --- se construye sin el ---
    asi que una edicion no puede mover un producto a otro proveedor ni robarse
    el de otro. CU-10 solo toca los campos que vinieron.
    """
    _producto_propio(db, usuario_id, producto_id)

    # Se conserva `model_fields_set`: CU-10 distingue «no enviado» de «enviado
    # en null», y armar el esquema campo por campo perderia esa distincion ---
    # mandar `coleccion_id: null` significa sacar el producto de la coleccion,
    # que es una operacion legitima.
    cambios = ProductoEditarIn.model_construct(
        _fields_set=set(datos.model_fields_set),
        **datos.model_dump(),
    )
    return service.editar_producto(db, producto_id, cambios)


def cambiar_estado_de_mi_producto(
    db: Session, usuario_id: int, producto_id: int, activo: bool
) -> ProductoOut:
    """Flujo alternativo 3b: el Proveedor retira una prenda que ya no abastece.

    SOLO PUEDE DESACTIVAR. `activo=True` se rechaza: publicar es de CU-10, por
    el mismo motivo por el que el alta nace inactiva. La asimetria es
    deliberada y el router la traduce a un 403 con un mensaje que la explica,
    porque un 422 pareceria un dato mal escrito.

    Desactivar no borra nada: el producto sigue en el inventario y en las ventas
    historicas. Es lo que hace que retirar una prenda sea seguro.
    """
    _producto_propio(db, usuario_id, producto_id)
    return service.cambiar_estado_producto(db, producto_id, CambioEstadoIn(activo=activo))


def generar_variantes_de_mi_producto(
    db: Session, usuario_id: int, producto_id: int, datos: GenerarVariantesIn
) -> GenerarVariantesOut:
    """Paso 7: las tallas y los colores en los que abastece esa prenda.

    Es la mitad que vuelve util al registro. Un producto sin variantes no tiene
    SKU, y sin SKU no hay existencia, ni reserva, ni venta: la decision D1 dice
    que la unidad del negocio es la variante, no el producto.

    Lo hace CU-10 entero, incluido el armado del SKU y el omitir las
    combinaciones que ya existen.
    """
    _producto_propio(db, usuario_id, producto_id)
    return service.generar_variantes(db, producto_id, datos)
