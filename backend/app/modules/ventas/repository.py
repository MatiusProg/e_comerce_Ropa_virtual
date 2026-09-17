"""
P7 - Ventas y Punto de Venta  |  capa: repositorio (consultas)

Ciclo de desarrollo: 3
Caso de uso: CU-27 Realizar pedido y pagar en linea

Regla: aqui vive el SQL. Ninguna regla de negocio y ningun `commit`: quien
abre y cierra la transaccion es el servicio.

CU-26 tiene el suyo en `carrito_repository.py`, que es de Karen. Este modulo
lo IMPORTA para no reescribir la lectura del carrito: la ficha del pedido y la
del carrito tienen que mostrar exactamente las mismas lineas, y dos consultas
paralelas se desincronizan en cuanto alguien toca una.
"""
from datetime import datetime

from sqlalchemy import Row, Select, func, select
from sqlalchemy.orm import Session

from app.modules.catalogo.models import Color, Producto, Talla, VarianteProducto
from app.modules.inventario.models import Existencia
from app.modules.organizacion.models import Ciudad, Sucursal
from app.modules.seguridad.models import Cliente, DireccionCliente, Usuario
from app.modules.ventas.models import DetalleVenta, Venta
from app.modules.pagos.models import Pago


# --- Sucursales y su capacidad de abastecer ------------------------------

def stock_por_sucursal(
    db: Session, variante_ids: list[int]
) -> dict[int, dict[int, int]]:
    """Unidades DISPONIBLES de cada variante en cada sucursal activa.

    Devuelve `{sucursal_id: {variante_id: unidades}}`.

    UNA consulta para todo el carrito y todas las sucursales. La alternativa
    ---preguntar por variante, o por sucursal--- haria N consultas para pintar
    una pantalla que el cliente mira una sola vez, y es el mismo defecto que la
    pantalla de inventario ya pago una vez.

    Se mira `cantidad_disponible` y NO se suma `cantidad_reservada`: lo
    reservado esta apartado para una reserva de CU-22 o para otro pedido sin
    pagar, y ofrecerlo seria prometer lo que ya es de alguien.

    Las sucursales inactivas quedan afuera de la consulta, no del resultado:
    una sucursal cerrada no despacha aunque tenga mercaderia adentro.
    """
    if not variante_ids:
        return {}

    filas = db.execute(
        select(
            Existencia.sucursal_id,
            Existencia.variante_id,
            Existencia.cantidad_disponible,
        )
        .join(Sucursal, Sucursal.id == Existencia.sucursal_id)
        .where(
            Existencia.variante_id.in_(variante_ids),
            Existencia.cantidad_disponible > 0,
            Sucursal.activa.is_(True),
        )
    ).all()

    por_sucursal: dict[int, dict[int, int]] = {}
    for fila in filas:
        por_sucursal.setdefault(fila.sucursal_id, {})[fila.variante_id] = (
            fila.cantidad_disponible
        )
    return por_sucursal


def listar_sucursales_activas(db: Session) -> list[Row]:
    """Las sucursales que despachan, con su ciudad ya resuelta."""
    return list(
        db.execute(
            select(
                Sucursal.id,
                Sucursal.nombre,
                Sucursal.direccion,
                Ciudad.nombre.label("ciudad"),
            )
            .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
            .where(Sucursal.activa.is_(True))
            .order_by(Ciudad.nombre, Sucursal.nombre)
        ).all()
    )


def obtener_sucursal(db: Session, sucursal_id: int) -> Sucursal | None:
    return db.get(Sucursal, sucursal_id)


# --- Direcciones del cliente (las escribe CU-04) -------------------------

def listar_direcciones(db: Session, cliente_id: int) -> list[Row]:
    """Las direcciones registradas, la predeterminada primero.

    El orden no es cosmetico: la pantalla preselecciona la primera, y que esa
    sea la predeterminada es lo que hace que el caso normal ---comprar a la
    direccion de siempre--- no exija ninguna eleccion.
    """
    return list(
        db.execute(
            select(
                DireccionCliente.id,
                DireccionCliente.alias,
                DireccionCliente.direccion,
                DireccionCliente.referencia,
                DireccionCliente.predeterminada,
                Ciudad.nombre.label("ciudad"),
            )
            .join(Ciudad, Ciudad.id == DireccionCliente.ciudad_id)
            .where(DireccionCliente.cliente_id == cliente_id)
            .order_by(DireccionCliente.predeterminada.desc(), DireccionCliente.alias)
        ).all()
    )


def direccion_de_venta(db: Session, direccion_id: int) -> Row | None:
    """La direccion que una venta guardo, para pintar su ficha.

    NO se acota al cliente, a diferencia de `obtener_direccion`: la venta ya
    viene acotada a su duenio, y esta es la direccion que esa venta eligio.
    Volver a filtrar por cliente haria desaparecer la direccion de la ficha si
    el cliente la borro despues de comprar --- y el pedido tiene que seguir
    diciendo adonde se mando.
    """
    return db.execute(
        select(
            DireccionCliente.direccion,
            Ciudad.nombre.label("ciudad"),
        )
        .join(Ciudad, Ciudad.id == DireccionCliente.ciudad_id)
        .where(DireccionCliente.id == direccion_id)
    ).first()


def correo_del_cliente(db: Session, cliente_id: int) -> str | None:
    """El correo de la cuenta del cliente, para el comprobante de la pasarela."""
    return db.scalar(
        select(Usuario.correo)
        .join(Cliente, Cliente.usuario_id == Usuario.id)
        .where(Cliente.id == cliente_id)
    )


def obtener_direccion(
    db: Session, *, direccion_id: int, cliente_id: int
) -> Row | None:
    """Una direccion, **acotada al cliente del token**.

    El `cliente_id` va en el WHERE y no se comprueba despues: asi una direccion
    ajena se ve igual que una inexistente, y no hay forma de averiguar que
    direcciones tiene otra persona probando numeros.
    """
    return db.execute(
        select(
            DireccionCliente.id,
            DireccionCliente.alias,
            DireccionCliente.direccion,
            DireccionCliente.referencia,
            Ciudad.nombre.label("ciudad"),
        )
        .join(Ciudad, Ciudad.id == DireccionCliente.ciudad_id)
        .where(
            DireccionCliente.id == direccion_id,
            DireccionCliente.cliente_id == cliente_id,
        )
    ).first()


# --- Escritura de la venta -----------------------------------------------

def agregar_venta(
    db: Session,
    *,
    codigo: str,
    canal: str,
    estado: str,
    cliente_id: int | None,
    sucursal_id: int,
    turno_caja_id: int | None,
    reserva_id: int | None,
    modalidad_entrega: str | None,
    direccion_id: int | None,
    subtotal,
    descuento,
    total,
) -> Venta:
    venta = Venta(
        codigo=codigo,
        canal=canal,
        estado=estado,
        cliente_id=cliente_id,
        sucursal_id=sucursal_id,
        turno_caja_id=turno_caja_id,
        reserva_id=reserva_id,
        modalidad_entrega=modalidad_entrega,
        direccion_id=direccion_id,
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
    precio_unitario,
    descuento_unitario,
) -> DetalleVenta:
    detalle = DetalleVenta(
        venta_id=venta_id,
        variante_id=variante_id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        descuento_unitario=descuento_unitario,
    )
    db.add(detalle)
    return detalle


def existe_codigo(db: Session, codigo: str) -> bool:
    return db.scalar(select(func.count()).select_from(Venta).where(Venta.codigo == codigo)) > 0


# --- Lectura de la venta --------------------------------------------------

def obtener_venta_entidad(
    db: Session, *, codigo: str, cliente_id: int | None = None, bloquear: bool = False
) -> Venta | None:
    """La venta como entidad, para poder cambiarle el estado.

    `bloquear` toma `SELECT ... FOR UPDATE`, y hace falta en toda operacion que
    cambie el estado. El caso que lo obliga es el mismo que en CU-23: si el
    cliente cancela su pedido en el momento exacto en que la barrida lo esta
    expirando, sin bloqueo las dos leen PENDIENTE_PAGO, las dos pasan la
    comprobacion y las dos liberan el stock. El inventario terminaria con MAS
    unidades de las que hay.
    """
    consulta = select(Venta).where(Venta.codigo == codigo)
    if cliente_id is not None:
        # Acotado al duenio, con el mismo criterio que `obtener_direccion`: un
        # pedido ajeno se ve igual que uno inexistente.
        consulta = consulta.where(Venta.cliente_id == cliente_id)
    if bloquear:
        consulta = consulta.with_for_update()
    return db.scalar(consulta)


def _seleccion_pedido() -> Select:
    return (
        select(
            Venta.id,
            Venta.codigo,
            Venta.estado,
            Venta.canal,
            Venta.modalidad_entrega,
            Venta.sucursal_id,
            Venta.direccion_id,
            Venta.subtotal,
            Venta.descuento,
            Venta.total,
            Venta.creado_en,
            Sucursal.nombre.label("sucursal_nombre"),
            Pago.estado.label("estado_pago"),
        )
        .join(Sucursal, Sucursal.id == Venta.sucursal_id)
        # LEFT JOIN: una venta recien creada todavia no tiene pago, y con un
        # JOIN normal desapareceria de su propia ficha.
        .outerjoin(Pago, Pago.venta_id == Venta.id)
    )


def obtener_pedido(
    db: Session, *, codigo: str, cliente_id: int | None = None
) -> Row | None:
    consulta = _seleccion_pedido().where(Venta.codigo == codigo)
    if cliente_id is not None:
        consulta = consulta.where(Venta.cliente_id == cliente_id)
    return db.execute(consulta).first()


def lineas_de_pedido(db: Session, venta_id: int) -> list[Row]:
    """Las lineas con la prenda resuelta, para la ficha del pedido.

    Lee `detalle_venta.precio_unitario` y NO `variante_producto.precio`: el
    precio del pedido es el que se congelo al confirmarlo. Es la diferencia
    con `carrito_repository.lineas_resueltas`, que sí lee el vigente porque el
    carrito es una intencion.
    """
    return list(
        db.execute(
            select(
                DetalleVenta.variante_id,
                DetalleVenta.cantidad,
                DetalleVenta.precio_unitario,
                DetalleVenta.descuento_unitario,
                VarianteProducto.sku,
                VarianteProducto.producto_id,
                Producto.nombre.label("producto_nombre"),
                Talla.codigo.label("talla_codigo"),
                Color.nombre.label("color_nombre"),
            )
            .join(VarianteProducto, VarianteProducto.id == DetalleVenta.variante_id)
            .join(Producto, Producto.id == VarianteProducto.producto_id)
            .join(Talla, Talla.id == VarianteProducto.talla_id)
            .join(Color, Color.id == VarianteProducto.color_id)
            .where(DetalleVenta.venta_id == venta_id)
            .order_by(DetalleVenta.id)
        ).all()
    )


def detalles_de(db: Session, venta_id: int) -> list[DetalleVenta]:
    """Las lineas como entidades, para recorrerlas al devolver el stock."""
    return list(
        db.scalars(
            select(DetalleVenta)
            .where(DetalleVenta.venta_id == venta_id)
            .order_by(DetalleVenta.id)
        ).all()
    )


def bloquear_cliente(db: Session, cliente_id: int) -> None:
    """Serializa las confirmaciones de pedido de UN cliente. **Sin commit.**

    POR QUE HACE FALTA, Y POR QUE NO ALCANZABA EL `FOR UPDATE` DE ABAJO
    -------------------------------------------------------------------
    `pedido_pendiente_de` toma `SELECT ... FOR UPDATE` sobre la venta pendiente,
    y eso protege bien cuando la venta existe --- es lo que impide que cancelar
    y expirar se crucen ---. Pero **una consulta que no devuelve filas no
    bloquea nada**: cuando el cliente todavia no tiene pedido pendiente, dos
    peticiones simultaneas leen las dos "no hay ninguno", las dos pasan la
    comprobacion y las dos crean su pedido.

    No es teorico: se reprodujo el 17/09 disparando dos POST a la vez contra el
    servidor --- los dos devolvieron 201 ---. El caso real es el cliente que
    pulsa "Confirmar" dos veces porque la primera tardo, o el reintento
    automatico de una peticion que parecio fallar.

    El dano no es sobreventa --- el inventario sigue cuadrando, porque quien lo
    protege es el `FOR UPDATE` de `apartar_para_reserva` --- sino que el cliente
    inmoviliza el doble de mercaderia y queda con dos sesiones de pago abiertas.

    LA SOLUCION: BLOQUEAR UNA FILA QUE SI EXISTE
    ---------------------------------------------
    Se toma el `FOR UPDATE` sobre la fila de `cliente`, que existe siempre. La
    segunda peticion espera ahi, y cuando entra ya ve el pedido que creo la
    primera. Es el patron de "bloquear al padre para poder crear un hijo unico".

    La alternativa de fondo es un indice unico parcial
    ---`UNIQUE (cliente_id) WHERE estado = 'PENDIENTE_PAGO'`--- que lo
    garantizaria en la base y no en el servicio. Es mejor y queda anotado: exige
    una migracion, y el 17/09 no se abrio una para no dejar el arbol con dos
    cabezas mientras otra persona trabajaba en el backend.
    """
    db.execute(
        select(Cliente.id).where(Cliente.id == cliente_id).with_for_update()
    ).first()


def pedido_pendiente_de(db: Session, cliente_id: int) -> Venta | None:
    """El pedido sin pagar que el cliente ya tenga abierto, si hay alguno.

    Se usa para no dejar abrir un segundo: cada pedido sin pagar aparta stock,
    y un cliente que confirma cinco veces seguidas ---porque la pasarela tardo
    y volvio atras--- dejaria cinco veces la mercaderia inmovilizada.

    **El `FOR UPDATE` de aqui NO alcanza solo.** Ver `bloquear_cliente`, que hay
    que llamar antes.
    """
    return db.scalar(
        select(Venta)
        .where(Venta.cliente_id == cliente_id, Venta.estado == "PENDIENTE_PAGO")
        .order_by(Venta.creado_en)
        .limit(1)
        .with_for_update()
    )


def listar_pendientes_vencidos(
    db: Session, *, corte: datetime, tope: int
) -> list[Venta]:
    """Pedidos sin pagar creados antes del corte.

    Copia deliberada de `reservas.repository.listar_vencidas`, con sus tres
    decisiones intactas y por las mismas razones:

    **`with_for_update(skip_locked=True)`** saltea las filas que otra
    transaccion ya tiene tomadas en vez de esperarlas. Si el cliente esta
    pagando la suya justo en ese momento, la barrida la deja pasar y la agarra
    en la proxima vuelta.

    **El tope**, para que la primera corrida sobre una base con historial no
    abra una transaccion enorme.

    **El orden por antiguedad**: los que mas tiempo llevan reteniendo stock.
    """
    return list(
        db.scalars(
            select(Venta)
            .where(Venta.estado == "PENDIENTE_PAGO", Venta.creado_en < corte)
            .order_by(Venta.creado_en)
            .limit(tope)
            .with_for_update(skip_locked=True)
        ).all()
    )
