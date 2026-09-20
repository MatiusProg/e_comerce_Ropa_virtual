"""
P7 - Punto de Venta / CU-31  |  capa: repositorio (consultas, sin logica ni commit)

POR QUE HAY UNA CONSULTA PROPIA Y NO SE REUSA `inventario.listar_existencias`
------------------------------------------------------------------------------
Porque el mostrador necesita **el precio**, y esa consulta no lo trae: devuelve
`ExistenciaOut`, que nombra la prenda y da el saldo pero no dice cuanto cuesta
--- el precio es de P3 y el paquete de inventario no tiene por que mirarlo ---.
Encadenar las dos obligaria a pedir una pagina de existencias, sacar los
identificadores y pedir los precios aparte, con la paginacion de una mandando
sobre la otra.

Esto no rompe la convencion de no reimplementar reglas ajenas: **una consulta
de lectura no es una regla**. La regla de que significa «disponible» vive en la
columna `existencia.cantidad_disponible` y en los movimientos que la mueven, y
eso se lee, no se recalcula. Lo que CU-31 nunca hace por su cuenta es
*modificar* inventario: para eso llama a las costuras de P4.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Row, Select, func, or_, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Sucursal
from app.modules.reservas.models import DetalleReserva, Reserva
from app.modules.seguridad.models import Cliente, Usuario
from app.modules.ventas.models import DetalleVenta, Venta

CANAL_PRESENCIAL = "PRESENCIAL"

#: Una venta de mostrador nace pagada: el dinero se recibe en el acto y no hay
#: pasarela que confirme nada.
ESTADO_PAGADA = "PAGADA"


def _seleccion_prenda() -> Select:
    """Variante + prenda resuelta + precio + saldo en una sucursal.

    Los `join` son todos internos salvo el de existencia, que va por dentro
    tambien: una variante sin fila de existencia en esta sucursal **no se puede
    vender aca**, asi que quedarse afuera es el comportamiento correcto.
    """
    return (
        select(
            VarianteProducto.id.label("variante_id"),
            VarianteProducto.sku,
            Producto.nombre.label("producto"),
            Talla.codigo.label("talla"),
            Color.nombre.label("color"),
            VarianteProducto.precio,
            Existencia.cantidad_disponible.label("disponible"),
        )
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Talla, Talla.id == VarianteProducto.talla_id)
        .join(Color, Color.id == VarianteProducto.color_id)
        .join(Existencia, Existencia.variante_id == VarianteProducto.id)
    )


def prendas_vendibles(
    db: Session,
    *,
    sucursal_id: int,
    busqueda: str | None,
    pagina: int,
    tamano: int,
) -> tuple[int, list[Row]]:
    """Lo que hay para vender en el mostrador de esta sucursal.

    SOLO CON SALDO, Y NO ES UN FILTRO OPCIONAL
    -------------------------------------------
    El inventario deja elegir si se quieren ver las prendas en cero, porque al
    depositero le importa saber que una esta agotada. En el mostrador no: una
    prenda sin unidades **no se puede vender**, y ofrecerla lleva al cajero a
    armar un ticket que va a fallar al confirmarlo, con el cliente delante.
    """
    filtros = [
        Existencia.sucursal_id == sucursal_id,
        Existencia.cantidad_disponible > 0,
        VarianteProducto.activa.is_(True),
        Producto.activo.is_(True),
    ]
    if busqueda:
        # El cajero escribe el SKU si lo tiene a mano y el nombre si no. Las
        # dos cosas en el mismo campo: obligarlo a elegir entre «buscar por
        # codigo» y «buscar por nombre» es hacerle recordar cual de los dos
        # esta mirando.
        patron = f"%{busqueda.strip()}%"
        filtros.append(
            or_(VarianteProducto.sku.ilike(patron), Producto.nombre.ilike(patron))
        )

    total = db.scalar(
        select(func.count())
        .select_from(VarianteProducto)
        .join(Producto, Producto.id == VarianteProducto.producto_id)
        .join(Existencia, Existencia.variante_id == VarianteProducto.id)
        .where(*filtros)
    )

    filas = db.execute(
        _seleccion_prenda()
        .where(*filtros)
        .order_by(Producto.nombre, Talla.codigo, Color.nombre)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()
    return int(total or 0), list(filas)


def prendas_por_id(
    db: Session, *, variante_ids: list[int], sucursal_id: int
) -> dict[int, Row]:
    """Las prendas del ticket, indexadas. Sin filtrar por saldo.

    NO se exige saldo aca: si falta stock, quien lo dice es la costura de P4 al
    descontar, con su bloqueo de fila. Filtrarlo en esta consulta daria un «no
    existe esa prenda» cuando lo que pasa es que se agoto, que es otra cosa y
    se arregla de otra manera.
    """
    if not variante_ids:
        return {}
    filas = db.execute(
        _seleccion_prenda().where(
            VarianteProducto.id.in_(variante_ids),
            Existencia.sucursal_id == sucursal_id,
        )
    ).all()
    return {fila.variante_id: fila for fila in filas}


# =====================================================================
# El puente de D2: la reserva ya atendida
# =====================================================================

def _cobradas() -> Select:
    """Las reservas que ya tienen una venta colgada.

    `venta.reserva_id` es UNICO: una reserva no se cobra dos veces. Esta
    subconsulta es lo que deja de ofrecer las que ya se cobraron.
    """
    return select(Venta.reserva_id).where(Venta.reserva_id.is_not(None))


def reservas_por_cobrar(db: Session, *, sucursal_id: int) -> list[Row]:
    """Reservas ATENDIDAS de esta sucursal con algo que cobrar y sin venta aun.

    El `EXISTS` sobre las lineas con `LLEVA` no es un adorno: una reserva donde
    el cliente se probo todo y no se llevo nada esta atendida y cerrada, y no
    hay nada que cobrar. Ofrecerla dejaria al cajero abriendo reservas vacias.
    """
    llevadas = (
        select(DetalleReserva.id)
        .where(
            DetalleReserva.reserva_id == Reserva.id,
            DetalleReserva.resultado_prueba == "LLEVA",
        )
        .exists()
    )
    return list(
        db.execute(
            select(
                Reserva.id.label("reserva_id"),
                Reserva.actualizado_en.label("atendida_en"),
                Usuario.nombres,
                Usuario.apellidos,
            )
            .join(Cliente, Cliente.id == Reserva.cliente_id)
            .join(Usuario, Usuario.id == Cliente.usuario_id)
            .where(
                Reserva.sucursal_id == sucursal_id,
                Reserva.estado == "ATENDIDA",
                llevadas,
                Reserva.id.not_in(_cobradas()),
            )
            .order_by(Reserva.actualizado_en.desc())
        ).all()
    )


def reserva_cobrable(db: Session, *, reserva_id: int, sucursal_id: int) -> Row | None:
    """Una reserva concreta, si es de esta sucursal, esta atendida y no se cobro.

    Las tres condiciones van en el WHERE y no en comprobaciones despues: una
    reserva de otra sucursal **no existe** para este cajero --- convencion 1 ---
    y separar los motivos le diria que existe una que no puede ver.
    """
    return db.execute(
        select(
            Reserva.id.label("reserva_id"),
            Reserva.cliente_id,
            Reserva.actualizado_en.label("atendida_en"),
            Usuario.nombres,
            Usuario.apellidos,
        )
        .join(Cliente, Cliente.id == Reserva.cliente_id)
        .join(Usuario, Usuario.id == Cliente.usuario_id)
        .where(
            Reserva.id == reserva_id,
            Reserva.sucursal_id == sucursal_id,
            Reserva.estado == "ATENDIDA",
            Reserva.id.not_in(_cobradas()),
        )
    ).first()


def lineas_llevadas(db: Session, *, reserva_id: int) -> list[Row]:
    """Lo que el cliente se llevo de su reserva, con el precio de hoy.

    `resultado_prueba = 'LLEVA'` y nada mas: lo que devolvio a la percha ya
    volvio al disponible en CU-24 y cobrarlo seria cobrarle una prenda que no
    se llevo.

    NO lleva `sucursal_id`: la reserva ya se acoto a la sucursal en
    `reserva_cobrable`, y volver a filtrar aca daria a entender que esta
    consulta se puede llamar sin haber pasado por ahi --- que es justo lo que
    no hay que hacer.
    """
    return list(
        db.execute(
            select(
                DetalleReserva.variante_id,
                DetalleReserva.cantidad,
                VarianteProducto.sku,
                Producto.nombre.label("producto"),
                Talla.codigo.label("talla"),
                Color.nombre.label("color"),
                VarianteProducto.precio,
            )
            .join(
                VarianteProducto, VarianteProducto.id == DetalleReserva.variante_id
            )
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(
                DetalleReserva.reserva_id == reserva_id,
                DetalleReserva.resultado_prueba == "LLEVA",
            )
            .order_by(Producto.nombre, Talla.codigo)
        ).all()
    )


# =====================================================================
# Releer una venta del mostrador
# =====================================================================

def venta_de_sucursal(db: Session, *, codigo: str, sucursal_id: int) -> Venta | None:
    """La venta presencial, si es de esta sucursal.

    El `sucursal_id` va en el WHERE, no en un `if` despues: una venta de otra
    sucursal no existe para este cajero.
    """
    return db.scalar(
        select(Venta).where(
            Venta.codigo == codigo,
            Venta.canal == "PRESENCIAL",
            Venta.sucursal_id == sucursal_id,
        )
    )


def nombre_de_sucursal(db: Session, sucursal_id: int) -> str:
    return db.scalar(select(Sucursal.nombre).where(Sucursal.id == sucursal_id)) or "—"


def cliente_de_venta(db: Session, cliente_id: int | None) -> str | None:
    if cliente_id is None:
        return None
    fila = db.execute(
        select(Usuario.nombres, Usuario.apellidos)
        .join(Cliente, Cliente.usuario_id == Usuario.id)
        .where(Cliente.id == cliente_id)
    ).first()
    return f"{fila.nombres} {fila.apellidos}".strip() if fila else None


def existe_codigo(db: Session, codigo: str) -> bool:
    return db.scalar(select(Venta.id).where(Venta.codigo == codigo)) is not None



# =====================================================================
# Escritura
# =====================================================================

def agregar_venta_presencial(
    db: Session,
    *,
    codigo: str,
    cliente_id: int | None,
    sucursal_id: int,
    turno_caja_id: int,
    reserva_id: int | None,
    metodo_pago: str,
    subtotal: Decimal,
    descuento: Decimal,
    total: Decimal,
) -> Venta:
    """Inserta la venta del mostrador. **Sin commit.**

    POR QUE NO SE REUSA `ventas.repository.agregar_venta`
    ------------------------------------------------------
    Esa funcion no acepta `metodo_pago` --- no lo necesita, porque CU-27 solo
    crea ventas DIGITALES y en esas el CHECK `ck_venta_metodo_segun_canal`
    exige que sea NULL ---. Agregarle el parametro seria editar un archivo de
    Mateo a un dia de la entrega, justo lo que la convencion del ciclo evita.

    Ademas, esta version **no puede armar una venta presencial invalida**: el
    turno es obligatorio y la modalidad y la direccion ni siquiera son
    parametros, porque en el mostrador siempre van en NULL. Los tres CHECK
    (`turno_segun_canal`, `modalidad_segun_canal`, `direccion_si_envio`) quedan
    satisfechos por construccion y no por disciplina de quien la llama.
    """
    venta = Venta(
        codigo=codigo,
        canal=CANAL_PRESENCIAL,
        estado=ESTADO_PAGADA,
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        turno_caja_id=turno_caja_id,
        reserva_id=reserva_id,
        modalidad_entrega=None,
        direccion_id=None,
        metodo_pago=metodo_pago,
        subtotal=subtotal,
        descuento=descuento,
        total=total,
    )
    db.add(venta)
    db.flush()
    return venta


def agregar_detalle(
    db: Session,
    *,
    venta_id: int,
    variante_id: int,
    cantidad: int,
    precio_unitario: Decimal,
    descuento_unitario: Decimal,
) -> DetalleVenta:
    """Una linea de la venta. **Sin commit.**"""
    detalle = DetalleVenta(
        venta_id=venta_id,
        variante_id=variante_id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        descuento_unitario=descuento_unitario,
    )
    db.add(detalle)
    return detalle
