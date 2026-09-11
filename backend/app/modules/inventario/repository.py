"""
P4 - Inventario  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit. El control de la transaccion vive en el servicio,
porque un ingreso escribe una existencia y un movimiento por linea y las dos
cosas tienen que aparecer juntas o no aparecer.

DEPENDENCIAS HACIA P2 Y P3
--------------------------
Este modulo consulta `sucursal` y `proveedor` (P2) y `variante_producto`,
`producto`, `talla` y `color` (P3). Es la direccion permitida: la seccion 2 de
docs/04-analisis-arquitectura.md dice que P4 «depende de P2 (sucursal) y P3
(variante)». La direccion contraria -que P3 lea `existencia`- es la que NO se
hace, y por eso el servicio expone las funciones de la costura C1 en vez de que
P5 consulte estas tablas por su cuenta.
"""
from datetime import datetime

from sqlalchemy import Row, Select, and_, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia, MovimientoInventario
from app.modules.organizacion.models import Ciudad, Proveedor, Sucursal
from app.modules.seguridad.models import Usuario


# --- Como se nombra una prenda -------------------------------------------
# Las cuatro columnas que convierten «variante 412» en «Blusa Aurora · M ·
# Negro». Se declaran una sola vez porque las usan el ingreso, el historial, el
# consolidado y la disponibilidad, y si cada consulta las armara por su cuenta
# terminarian diciendo cosas distintas.

def _columnas_de_variante():
    return (
        VarianteProducto.id.label("variante_id"),
        VarianteProducto.sku,
        Producto.nombre.label("producto"),
        Talla.codigo.label("talla"),
        Color.nombre.label("color"),
    )


def _unir_variante(consulta: Select) -> Select:
    return (
        consulta.join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
    )


# --- Existencias ---------------------------------------------------------

def _bajo_minimo():
    """Cuando una prenda esta en alerta de reposicion (CU-16).

    Dos condiciones, y las dos hacen falta: que haya umbral --- cero significa
    «sin alerta» y es el valor por defecto --- y que el disponible no lo supere.
    Se compara contra el DISPONIBLE y no contra el fisico: lo reservado ya tiene
    dueño y no sirve para atender al proximo cliente que entre, que es
    justamente lo que la alerta quiere evitar que pase.

    Se usa `<=` y no `<`: estar exactamente en el minimo ya es estar en el punto
    de reposicion. Ese es el sentido de la palabra «minimo».
    """
    return and_(
        Existencia.stock_minimo > 0,
        Existencia.cantidad_disponible <= Existencia.stock_minimo,
    )


def _seleccion_existencia() -> Select:
    """Saldo de una variante en una sucursal, con todo ya resuelto."""
    return _unir_variante(
        select(
            Existencia.id.label("existencia_id"),
            *_columnas_de_variante(),
            Existencia.sucursal_id,
            Sucursal.nombre.label("sucursal"),
            Existencia.cantidad_disponible,
            Existencia.cantidad_reservada,
            (Existencia.cantidad_disponible + Existencia.cantidad_reservada).label(
                "cantidad_fisica"
            ),
            Existencia.stock_minimo,
            # La regla de la alerta se resuelve en SQL y no en Python porque
            # tambien hace falta para FILTRAR (CU-16 lista solo las que estan
            # en alerta) y para ORDENAR por urgencia. Calcularla despues, sobre
            # las filas ya traidas, obligaria a traerlas todas.
            _bajo_minimo().label("bajo_minimo"),
        )
        .join(VarianteProducto, VarianteProducto.id == Existencia.variante_id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
    )


def obtener_existencia(
    db: Session, *, variante_id: int, sucursal_id: int, bloquear: bool = False
) -> Existencia | None:
    """La entidad, para modificarle el saldo.

    Con `bloquear=True` toma un `SELECT ... FOR UPDATE` sobre la fila. Es el
    mecanismo contra el riesgo R5 (sobreventa): mientras una transaccion la
    tiene tomada, otra que quiera la misma fila espera en vez de leer un saldo
    que esta por cambiar. CU-22 lo va a usar en serio; aqui ya se usa porque
    dos ingresos simultaneos de la misma prenda tendrian el mismo problema en
    chico -leer 10, sumar 5 los dos, y guardar 15 en vez de 20-.
    """
    consulta = select(Existencia).where(
        Existencia.variante_id == variante_id,
        Existencia.sucursal_id == sucursal_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def obtener_existencia_con_detalle(db: Session, existencia_id: int) -> Row | None:
    """Una fila del listado, para una existencia."""
    return db.execute(
        _seleccion_existencia().where(Existencia.id == existencia_id)
    ).first()


def agregar_existencia(db: Session, *, variante_id: int, sucursal_id: int) -> Existencia:
    """Crea el saldo en cero de una variante en una sucursal, sin confirmar.

    La primera vez que una prenda llega a una sucursal no hay fila que
    actualizar. Se crea con las dos cantidades en cero y el movimiento que sigue
    es el que la sube: asi la afirmacion de D4 -el saldo es la suma de sus
    movimientos- se cumple tambien para la primera unidad.
    """
    existencia = Existencia(
        variante_id=variante_id,
        sucursal_id=sucursal_id,
        cantidad_disponible=0,
        cantidad_reservada=0,
    )
    db.add(existencia)
    db.flush()
    return existencia


# --- Movimientos ---------------------------------------------------------

def agregar_movimiento(
    db: Session,
    *,
    existencia_id: int,
    tipo: str,
    cantidad: int,
    motivo: str | None = None,
    proveedor_id: int | None = None,
    referencia: str | None = None,
    usuario_id: int | None = None,
) -> MovimientoInventario:
    """Escribe el movimiento, sin confirmar.

    `cantidad` llega con signo desde el servicio. El repositorio no lo deduce
    del tipo: hay dos tipos que van en las dos direcciones (AJUSTE y
    TRANSFERENCIA) y decidirlo aqui obligaria a repetir la regla.
    """
    movimiento = MovimientoInventario(
        existencia_id=existencia_id,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo,
        proveedor_id=proveedor_id,
        referencia=referencia,
        usuario_id=usuario_id,
    )
    db.add(movimiento)
    db.flush()
    return movimiento


def _seleccion_movimiento() -> Select:
    """Historial con la prenda, la sucursal, el proveedor y el usuario."""
    interno = _unir_variante(
        select(
            MovimientoInventario.id,
            MovimientoInventario.creado_en,
            MovimientoInventario.tipo,
            MovimientoInventario.cantidad,
            MovimientoInventario.motivo,
            MovimientoInventario.referencia,
            MovimientoInventario.existencia_id,
            *_columnas_de_variante(),
            Existencia.sucursal_id,
            Sucursal.nombre.label("sucursal"),
            MovimientoInventario.proveedor_id,
            Proveedor.razon_social.label("proveedor"),
            MovimientoInventario.usuario_id,
            (Usuario.nombres + " " + Usuario.apellidos).label("usuario"),
        )
        .join(Existencia, Existencia.id == MovimientoInventario.existencia_id)
        .join(VarianteProducto, VarianteProducto.id == Existencia.variante_id)
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
    )
    # Las dos ultimas son externas a proposito y van al final: el proveedor
    # solo lo lleva el INGRESO, y el usuario queda nulo cuando el movimiento lo
    # genera una tarea programada (la expiracion de reservas de CU-25). Si se
    # declararan antes de las internas de la variante, quedarian uniones
    # internas colgando de una externa, que es dificil de leer y facil de
    # romper el dia que alguien agregue una columna nueva.
    return interno.outerjoin(
        Proveedor, Proveedor.id == MovimientoInventario.proveedor_id
    ).outerjoin(Usuario, Usuario.id == MovimientoInventario.usuario_id)


def obtener_movimiento(db: Session, movimiento_id: int) -> Row | None:
    return db.execute(
        _seleccion_movimiento().where(MovimientoInventario.id == movimiento_id)
    ).first()


def _filtrar_movimientos(
    consulta: Select,
    *,
    sucursal_id: int | None,
    variante_id: int | None,
    tipo: str | None,
    desde: datetime | None,
    hasta: datetime | None,
) -> Select:
    """Los filtros del historial, compartidos por el listado y por el conteo.

    Se comparten para que el total del paginador y las filas que se muestran
    salgan del mismo criterio: si se escribieran dos veces, la primera
    diferencia entre ambas se veria como un paginador que promete una pagina
    que despues llega vacia.
    """
    if sucursal_id is not None:
        consulta = consulta.where(Existencia.sucursal_id == sucursal_id)
    if variante_id is not None:
        consulta = consulta.where(Existencia.variante_id == variante_id)
    if tipo is not None:
        consulta = consulta.where(MovimientoInventario.tipo == tipo)
    if desde is not None:
        consulta = consulta.where(MovimientoInventario.creado_en >= desde)
    if hasta is not None:
        consulta = consulta.where(MovimientoInventario.creado_en <= hasta)
    return consulta


def contar_movimientos(
    db: Session,
    *,
    sucursal_id: int | None = None,
    variante_id: int | None = None,
    tipo: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> int:
    consulta = select(func.count()).select_from(MovimientoInventario).join(
        Existencia, Existencia.id == MovimientoInventario.existencia_id
    )
    consulta = _filtrar_movimientos(
        consulta,
        sucursal_id=sucursal_id,
        variante_id=variante_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )
    return db.scalar(consulta) or 0


def listar_movimientos(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    sucursal_id: int | None = None,
    variante_id: int | None = None,
    tipo: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> list[Row]:
    """Historial ordenado del mas reciente al mas viejo.

    El desempate por `id` descendente no es decorativo: las lineas de un mismo
    ingreso comparten `creado_en` al milisegundo -es el instante de la
    transaccion- y sin un segundo criterio PostgreSQL puede devolverlas en
    orden distinto en cada consulta, con lo que una fila se repetiria en dos
    paginas y otra no aparaceria en ninguna.
    """
    consulta = _filtrar_movimientos(
        _seleccion_movimiento(),
        sucursal_id=sucursal_id,
        variante_id=variante_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )
    return list(
        db.execute(
            consulta.order_by(
                MovimientoInventario.creado_en.desc(), MovimientoInventario.id.desc()
            )
            .offset((pagina - 1) * tamano)
            .limit(tamano)
        ).all()
    )


# --- Historial de ingresos (CU-13, paso 2) -------------------------------
#
# Un ingreso no es una fila: es el grupo de movimientos INGRESO que comparten
# proveedor, sucursal, remito, usuario e instante de transaccion. Ver la nota
# «POR QUE NO HAY TABLA `ingreso`» en models.py.

#: Lo que define «un ingreso». Se declara una vez porque el listado y el conteo
#: tienen que agrupar exactamente igual, o el paginador miente.
def _agrupacion_de_ingreso():
    return (
        MovimientoInventario.creado_en,
        Existencia.sucursal_id,
        MovimientoInventario.proveedor_id,
        MovimientoInventario.referencia,
        MovimientoInventario.usuario_id,
    )


def _base_de_ingresos(
    *, sucursal_id: int | None, proveedor_id: int | None
) -> Select:
    consulta = (
        select(*_agrupacion_de_ingreso())
        .join(Existencia, Existencia.id == MovimientoInventario.existencia_id)
        .where(MovimientoInventario.tipo == "INGRESO")
        .group_by(*_agrupacion_de_ingreso())
    )
    if sucursal_id is not None:
        consulta = consulta.where(Existencia.sucursal_id == sucursal_id)
    if proveedor_id is not None:
        consulta = consulta.where(MovimientoInventario.proveedor_id == proveedor_id)
    return consulta


def contar_ingresos(
    db: Session, *, sucursal_id: int | None = None, proveedor_id: int | None = None
) -> int:
    agrupados = _base_de_ingresos(
        sucursal_id=sucursal_id, proveedor_id=proveedor_id
    ).subquery()
    return db.scalar(select(func.count()).select_from(agrupados)) or 0


def listar_ingresos(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    sucursal_id: int | None = None,
    proveedor_id: int | None = None,
) -> list[Row]:
    """Los ingresos registrados, del mas reciente al mas viejo."""
    consulta = (
        _base_de_ingresos(sucursal_id=sucursal_id, proveedor_id=proveedor_id)
        .add_columns(
            Sucursal.nombre.label("sucursal"),
            Proveedor.razon_social.label("proveedor"),
            (Usuario.nombres + " " + Usuario.apellidos).label("usuario"),
            func.count().label("lineas"),
            func.sum(MovimientoInventario.cantidad).label("unidades"),
        )
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .outerjoin(Proveedor, Proveedor.id == MovimientoInventario.proveedor_id)
        .outerjoin(Usuario, Usuario.id == MovimientoInventario.usuario_id)
        # Los tres nombres entran al GROUP BY porque dependen de columnas que ya
        # estan agrupadas; PostgreSQL no lo deduce solo salvo que se agrupe por
        # la clave primaria de cada tabla, y nombrarlos es mas claro que
        # apoyarse en esa inferencia.
        .group_by(Sucursal.nombre, Proveedor.razon_social, Usuario.nombres, Usuario.apellidos)
        .order_by(MovimientoInventario.creado_en.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return list(db.execute(consulta).all())


def lineas_de_ingreso(
    db: Session,
    *,
    registrado_en: datetime,
    sucursal_id: int,
    referencia: str | None,
) -> list[Row]:
    """Las lineas de un ingreso concreto, para el detalle del historial."""
    consulta = _seleccion_movimiento().where(
        MovimientoInventario.tipo == "INGRESO",
        MovimientoInventario.creado_en == registrado_en,
        Existencia.sucursal_id == sucursal_id,
    )
    # `referencia is None` y `referencia = ''` no son lo mismo para SQL, y un
    # `== None` genera `= NULL`, que nunca es cierto.
    if referencia is None:
        consulta = consulta.where(MovimientoInventario.referencia.is_(None))
    else:
        consulta = consulta.where(MovimientoInventario.referencia == referencia)
    return list(db.execute(consulta.order_by(MovimientoInventario.id)).all())


# --- Validaciones de existencia de las entidades ajenas ------------------

def listar_variantes(db: Session, ids: list[int]) -> list[Row]:
    """Las variantes indicadas, con su nombre y si estan activas.

    Se traen todas de una consulta y no de a una: un ingreso de veinte lineas
    haria veinte viajes a la base para responder la misma pregunta.
    """
    return list(
        db.execute(
            _unir_variante(
                select(*_columnas_de_variante(), VarianteProducto.activa)
            ).where(VarianteProducto.id.in_(ids))
        ).all()
    )


def obtener_sucursal(db: Session, sucursal_id: int) -> Sucursal | None:
    """Distingue «no existe» de «existe pero esta dada de baja»."""
    return db.scalar(select(Sucursal).where(Sucursal.id == sucursal_id))


def obtener_proveedor(db: Session, proveedor_id: int) -> Proveedor | None:
    return db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id))


# --- CU-16: disponibilidad de la sucursal --------------------------------

def listar_alertas(db: Session, *, sucursal_id: int | None = None) -> list[Row]:
    """Las prendas que llegaron a su punto de reposicion.

    Ordenadas por lo lejos que estan del umbral, de peor a mejor: una prenda en
    cero con minimo diez urge mas que una en nueve con el mismo minimo, y quien
    abre esta pantalla a primera hora necesita ver arriba lo que tiene que
    pedir hoy.
    """
    consulta = _seleccion_existencia().where(_bajo_minimo())
    if sucursal_id is not None:
        consulta = consulta.where(Existencia.sucursal_id == sucursal_id)
    return list(
        db.execute(
            consulta.order_by(
                (Existencia.cantidad_disponible - Existencia.stock_minimo).asc(),
                Producto.nombre,
            )
        ).all()
    )


def obtener_existencia_por_id(db: Session, existencia_id: int) -> Existencia | None:
    """La entidad, para fijarle el umbral."""
    return db.scalar(select(Existencia).where(Existencia.id == existencia_id))


# --- Costura C1: lo que P5 le consume a P4 -------------------------------
#
# Estas dos consultas existen para que CU-19 y CU-14 no hagan SELECT sobre
# `existencia`. El contrato esta en la seccion 6 del documento de organizacion
# del ciclo. El servicio las envuelve; aqui va solo el SQL.

def disponibilidad_por_sucursal(db: Session, variante_id: int) -> list[Row]:
    """En que sucursales hay stock disponible de una variante (CU-19).

    Solo sucursales activas y solo con saldo mayor que cero: al cliente no le
    sirve saber que una prenda existe con cero unidades en un local cerrado.
    """
    return list(
        db.execute(
            select(
                Existencia.sucursal_id,
                Sucursal.nombre.label("sucursal_nombre"),
                Ciudad.nombre.label("ciudad_nombre"),
                Existencia.cantidad_disponible,
            )
            .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .where(
                Existencia.variante_id == variante_id,
                Existencia.cantidad_disponible > 0,
                Sucursal.activa.is_(True),
            )
            .order_by(Ciudad.nombre, Sucursal.nombre)
        ).all()
    )


def inventario_consolidado(
    db: Session,
    *,
    sucursal_id: int | None = None,
    producto_id: int | None = None,
    solo_con_saldo: bool = False,
) -> list[Row]:
    """Existencias con la prenda y la sucursal resueltas (CU-14 y CU-16)."""
    consulta = _seleccion_existencia()
    if sucursal_id is not None:
        consulta = consulta.where(Existencia.sucursal_id == sucursal_id)
    if producto_id is not None:
        consulta = consulta.where(VarianteProducto.producto_id == producto_id)
    if solo_con_saldo:
        consulta = consulta.where(
            (Existencia.cantidad_disponible + Existencia.cantidad_reservada) > 0
        )
    return list(
        db.execute(
            consulta.order_by(Sucursal.nombre, Producto.nombre, VarianteProducto.sku)
        ).all()
    )
