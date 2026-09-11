"""
P6 - Reservas  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit. El control de la transaccion vive en el servicio,
porque una reserva escribe su cabecera, sus lineas y un movimiento de inventario
por linea, y las tres cosas tienen que aparecer juntas o no aparecer.

LO QUE ESTE MODULO **NO** HACE
------------------------------
No toca `existencia` ni `movimiento_inventario`. Apartar y liberar stock son
funciones de P4 --- `apartar_para_reserva` y `liberar_de_reserva` de
`inventario/service.py` --- y se las llama desde el servicio. La regla «ninguna
cantidad se modifica sin generar un movimiento» es de P4, y si P6 escribiera
esas tablas por su cuenta habria dos lugares que la conocen.

Las dependencias hacia P1 (cliente), P2 (sucursal, ciudad) y P3 (variante,
producto, talla, color) son las permitidas: la seccion 2 de
docs/04-analisis-arquitectura.md dice que P6 depende de P1, P2, P3 y P4.
"""
from datetime import datetime

from sqlalchemy import Row, Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.reservas.models import DetalleReserva, Reserva
from app.modules.seguridad.models import Cliente

#: Estados en los que una reserva sigue viva: ocupa vestidor y retiene stock.
#: Se declara una vez porque lo usan el control de capacidad de CU-22, la
#: cancelacion de CU-23 y la expiracion de CU-25, y si cada uno lo escribiera
#: por su cuenta, el dia que se agregue un estado quedarian diciendo cosas
#: distintas.
ESTADOS_VIVOS = ("PENDIENTE", "PREPARADA")


def obtener_cliente_de_usuario(db: Session, usuario_id: int) -> Cliente | None:
    """La ficha de cliente de la cuenta que hizo la peticion.

    `reserva.cliente_id` apunta a `cliente`, no a `usuario`, y el token trae el
    identificador de usuario. Una cuenta con rol CLIENTE siempre tiene ficha
    --- la crea CU-01 en la misma transaccion que la cuenta ---, pero se
    comprueba igual en vez de asumirlo: si faltara, el error tiene que decir
    que falta la ficha y no reventar en la clave foranea.
    """
    return db.scalar(select(Cliente).where(Cliente.usuario_id == usuario_id))


def obtener_sucursal(db: Session, sucursal_id: int) -> Sucursal | None:
    """Distingue «no existe» de «existe pero esta dada de baja»."""
    return db.scalar(select(Sucursal).where(Sucursal.id == sucursal_id))


# --- Capacidad de vestidores (CU-22, excepcion E6) -----------------------

def contar_reservas_solapadas(
    db: Session, *, sucursal_id: int, inicio: datetime, fin: datetime
) -> int:
    """Cuantas reservas vivas de esa sucursal se pisan con esa franja.

    DOS FRANJAS SE SOLAPAN SI `inicio_a < fin_b AND inicio_b < fin_a`.
    Es la comparacion estandar y se escribe con `<` estricto a proposito: una
    reserva de 15:00 a 16:00 y otra de 16:00 a 17:00 **no** se solapan, porque
    la primera termina justo cuando empieza la segunda. Con `<=` no se podrian
    encadenar turnos consecutivos, que es el uso normal de un probador.

    Solo cuentan las vivas: una cancelada o expirada libero su vestidor.
    """
    return (
        db.scalar(
            select(func.count())
            .select_from(Reserva)
            .where(
                Reserva.sucursal_id == sucursal_id,
                Reserva.estado.in_(ESTADOS_VIVOS),
                Reserva.franja_inicio < fin,
                inicio < Reserva.franja_fin,
            )
        )
        or 0
    )


# --- Escritura -----------------------------------------------------------

def agregar_reserva(
    db: Session,
    *,
    cliente_id: int,
    sucursal_id: int,
    franja_inicio: datetime,
    franja_fin: datetime,
    estado: str,
    observacion: str | None,
) -> Reserva:
    """Crea la cabecera, sin confirmar."""
    reserva = Reserva(
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        franja_inicio=franja_inicio,
        franja_fin=franja_fin,
        estado=estado,
        observacion=observacion,
    )
    db.add(reserva)
    db.flush()
    return reserva


def agregar_detalle(
    db: Session, *, reserva_id: int, variante_id: int, cantidad: int
) -> DetalleReserva:
    """Crea una linea, sin confirmar."""
    detalle = DetalleReserva(
        reserva_id=reserva_id, variante_id=variante_id, cantidad=cantidad
    )
    db.add(detalle)
    db.flush()
    return detalle


# --- Lectura -------------------------------------------------------------

def _seleccion_reserva() -> Select:
    """Cabecera con la sucursal y la ciudad ya resueltas."""
    return (
        select(
            Reserva.id,
            Reserva.cliente_id,
            Reserva.sucursal_id,
            Sucursal.nombre.label("sucursal"),
            Ciudad.nombre.label("ciudad"),
            Reserva.franja_inicio,
            Reserva.franja_fin,
            Reserva.estado,
            Reserva.observacion,
            Reserva.creado_en,
        )
        .join(Sucursal, Sucursal.id == Reserva.sucursal_id)
        .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
    )


def obtener_reserva(db: Session, reserva_id: int) -> Row | None:
    return db.execute(_seleccion_reserva().where(Reserva.id == reserva_id)).first()


def listar_detalles(db: Session, reserva_id: int) -> list[Row]:
    """Las lineas de una reserva, con la prenda nombrada."""
    return list(
        db.execute(
            select(
                DetalleReserva.id,
                DetalleReserva.variante_id,
                VarianteProducto.sku,
                Producto.nombre.label("producto"),
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
                DetalleReserva.cantidad,
                DetalleReserva.resultado_prueba,
            )
            .join(VarianteProducto, VarianteProducto.id == DetalleReserva.variante_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(DetalleReserva.reserva_id == reserva_id)
            .order_by(DetalleReserva.id)
        ).all()
    )


def _filtrar(
    consulta: Select,
    *,
    cliente_id: int | None,
    sucursal_id: int | None,
    estado: str | None,
    vivas: bool | None,
) -> Select:
    """Los filtros del listado, compartidos por el conteo y por las filas.

    Se comparten para que el total del paginador y lo que se muestra salgan del
    mismo criterio: si se escribieran dos veces, la primera diferencia se veria
    como un paginador que promete una pagina que despues llega vacia.
    """
    if cliente_id is not None:
        consulta = consulta.where(Reserva.cliente_id == cliente_id)
    if sucursal_id is not None:
        consulta = consulta.where(Reserva.sucursal_id == sucursal_id)
    if estado is not None:
        consulta = consulta.where(Reserva.estado == estado)
    if vivas is True:
        consulta = consulta.where(Reserva.estado.in_(ESTADOS_VIVOS))
    elif vivas is False:
        consulta = consulta.where(Reserva.estado.not_in(ESTADOS_VIVOS))
    return consulta


def contar_reservas(
    db: Session,
    *,
    cliente_id: int | None = None,
    sucursal_id: int | None = None,
    estado: str | None = None,
    vivas: bool | None = None,
) -> int:
    consulta = _filtrar(
        select(func.count()).select_from(Reserva),
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        estado=estado,
        vivas=vivas,
    )
    return db.scalar(consulta) or 0


def listar_reservas(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    cliente_id: int | None = None,
    sucursal_id: int | None = None,
    estado: str | None = None,
    vivas: bool | None = None,
) -> list[Row]:
    """Listado con el recuento de prendas y unidades de cada reserva.

    Los dos recuentos salen de subconsultas correlacionadas y no de un JOIN con
    GROUP BY: con el JOIN habria que agrupar por las diez columnas de la
    cabecera, y agregar una columna al listado obligaria a acordarse de sumarla
    tambien al GROUP BY.
    """
    prendas = (
        select(func.count())
        .select_from(DetalleReserva)
        .where(DetalleReserva.reserva_id == Reserva.id)
        .correlate(Reserva)
        .scalar_subquery()
    )
    unidades = (
        select(func.coalesce(func.sum(DetalleReserva.cantidad), 0))
        .select_from(DetalleReserva)
        .where(DetalleReserva.reserva_id == Reserva.id)
        .correlate(Reserva)
        .scalar_subquery()
    )

    consulta = _filtrar(
        select(
            Reserva.id,
            Reserva.sucursal_id,
            Sucursal.nombre.label("sucursal"),
            Ciudad.nombre.label("ciudad"),
            Reserva.franja_inicio,
            Reserva.franja_fin,
            Reserva.estado,
            prendas.label("prendas"),
            unidades.label("unidades"),
        )
        .join(Sucursal, Sucursal.id == Reserva.sucursal_id)
        .join(Ciudad, Ciudad.id == Sucursal.ciudad_id),
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        estado=estado,
        vivas=vivas,
    )

    return list(
        db.execute(
            # La franja mas proxima primero: es la que el cliente necesita ver.
            # El desempate por id descendente evita que dos reservas de la misma
            # franja salgan en orden distinto en cada consulta, que haria que
            # una se repitiera en dos paginas y otra no apareciera en ninguna.
            consulta.order_by(Reserva.franja_inicio.desc(), Reserva.id.desc())
            .offset((pagina - 1) * tamano)
            .limit(tamano)
        ).all()
    )


def listar_variantes(db: Session, ids: list[int]) -> list[Row]:
    """Las variantes indicadas, con su nombre y si estan activas.

    Se traen todas de una consulta y no de a una: una reserva de diez lineas
    haria diez viajes a la base para responder la misma pregunta.
    """
    return list(
        db.execute(
            select(
                VarianteProducto.id.label("variante_id"),
                VarianteProducto.sku,
                Producto.nombre.label("producto"),
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
                VarianteProducto.activa,
            )
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(VarianteProducto.id.in_(ids))
        ).all()
    )
