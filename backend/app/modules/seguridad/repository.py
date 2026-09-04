"""
P1 - Seguridad y Usuarios  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Row, func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.modules.organizacion.models import Ciudad, Empleado, Proveedor, Sucursal
from app.modules.seguridad.models import (
    Cliente,
    DireccionCliente,
    Rol,
    SesionToken,
    Usuario,
)

# Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna
# validacion de permisos, ningun commit de transaccion compuesta.
#
# En particular: NINGUNA funcion de este archivo hace commit. El control de la
# transaccion vive en el servicio, porque CU-01 crea dos entidades (Usuario y
# Cliente) que tienen que aparecer juntas o no aparecer (excepcion E2).


# --- Consultas -----------------------------------------------------------

def obtener_usuario_por_correo(db: Session, correo: str) -> Usuario | None:
    """Devuelve el usuario con ese correo, o None si no existe."""
    return db.scalar(select(Usuario).where(Usuario.correo == correo))


def obtener_rol_por_nombre(db: Session, nombre: str) -> Rol | None:
    """Devuelve el rol con ese nombre, o None si no existe."""
    return db.scalar(select(Rol).where(Rol.nombre == nombre))


def existe_cliente_con_documento(db: Session, documento: str) -> bool:
    """Indica si ya hay un cliente con ese documento.

    cliente.documento es UNIQUE pero acepta NULL, asi que solo tiene sentido
    preguntar cuando el visitante informo el dato.
    """
    return (
        db.scalar(select(Cliente.id).where(Cliente.documento == documento)) is not None
    )


# --- Altas ---------------------------------------------------------------

def agregar_usuario(
    db: Session,
    *,
    correo: str,
    hash_contrasena: str,
    nombres: str,
    apellidos: str,
    rol_id: int,
) -> Usuario:
    """Agrega el usuario a la sesion y le asigna su id, sin confirmar.

    Usa flush y no commit: el id se necesita para crear el Cliente que lo
    referencia, pero la transaccion la cierra el servicio.
    """
    usuario = Usuario(
        correo=correo,
        hash_contrasena=hash_contrasena,
        nombres=nombres,
        apellidos=apellidos,
        rol_id=rol_id,
    )
    db.add(usuario)
    db.flush()
    return usuario


def agregar_cliente(
    db: Session,
    *,
    usuario_id: int,
    documento: str | None,
    telefono: str | None,
) -> Cliente:
    """Agrega la ficha de cliente asociada al usuario, sin confirmar."""
    cliente = Cliente(
        usuario_id=usuario_id,
        documento=documento,
        telefono=telefono,
    )
    db.add(cliente)
    db.flush()
    return cliente


# --- CU-02 Iniciar y cerrar sesion ---------------------------------------

def obtener_usuario_con_rol(db: Session, correo: str) -> Usuario | None:
    """Igual que obtener_usuario_por_correo, pero trae el rol en la misma
    consulta.

    El login necesita el nombre del rol para armar el token. Sin joinedload
    SQLAlchemy lo pediria en una segunda consulta, y si el objeto sale de la
    sesion antes de eso, falla.
    """
    return db.scalar(
        select(Usuario).options(joinedload(Usuario.rol)).where(Usuario.correo == correo)
    )


def obtener_usuario_con_id(db: Session, usuario_id: int) -> Usuario | None:
    """Usuario por identificador, con su rol cargado."""
    return db.scalar(
        select(Usuario).options(joinedload(Usuario.rol)).where(Usuario.id == usuario_id)
    )


def obtener_sucursal_de_usuario(db: Session, usuario_id: int) -> int | None:
    """Sucursal a la que pertenece el usuario, si es un empleado.

    Para Cliente y Administrador devuelve None: su ambito no es una sucursal.
    """
    return db.scalar(select(Empleado.sucursal_id).where(Empleado.usuario_id == usuario_id))


def agregar_sesion(
    db: Session,
    *,
    usuario_id: int,
    jti: uuid.UUID,
    expira_en: datetime,
) -> SesionToken:
    """Registra la sesion emitida. No confirma: la transaccion es del servicio."""
    sesion = SesionToken(usuario_id=usuario_id, jti=jti, expira_en=expira_en)
    db.add(sesion)
    db.flush()
    return sesion


def obtener_sesion_por_jti(db: Session, jti: uuid.UUID) -> SesionToken | None:
    """Devuelve la sesion con ese identificador, revocada o no."""
    return db.scalar(select(SesionToken).where(SesionToken.jti == jti))


def revocar_sesion(db: Session, jti: uuid.UUID) -> int:
    """Marca la sesion como revocada. Devuelve cuantas filas cambio.

    Solo toca las que siguen vigentes, para que cerrar sesion dos veces no
    reescriba la fecha de la primera.
    """
    resultado = db.execute(
        update(SesionToken)
        .where(SesionToken.jti == jti, SesionToken.revocado_en.is_(None))
        .values(revocado_en=datetime.now(timezone.utc))
    )
    return resultado.rowcount


def revocar_sesiones_de_usuario(db: Session, usuario_id: int) -> int:
    """Revoca todas las sesiones vigentes de un usuario.

    Lo necesita CU-03: al desactivar una cuenta hay que cortarle el acceso en
    el acto, no esperar a que sus tokens venzan.
    """
    resultado = db.execute(
        update(SesionToken)
        .where(SesionToken.usuario_id == usuario_id, SesionToken.revocado_en.is_(None))
        .values(revocado_en=datetime.now(timezone.utc))
    )
    return resultado.rowcount


# --- CU-03 Gestionar usuarios y roles ------------------------------------

def listar_roles(db: Session) -> list[Rol]:
    """Todos los roles asignables, en orden alfabetico."""
    return list(db.scalars(select(Rol).order_by(Rol.nombre)))


def contar_y_listar_usuarios(
    db: Session,
    *,
    busqueda: str | None,
    rol: str | None,
    activo: bool | None,
    pagina: int,
    tamano: int,
) -> tuple[int, list[Row]]:
    """Listado paginado con busqueda y filtros (paso 2 del flujo principal).

    Devuelve el total ANTES de paginar --el paginador lo necesita-- y la pagina
    pedida. La sucursal sale de `empleado`, que es donde vive; para Cliente y
    Administrador queda en nulo.
    """
    origen = (
        select(
            Usuario.id,
            Usuario.correo,
            Usuario.nombres,
            Usuario.apellidos,
            Usuario.activo,
            Usuario.creado_en,
            Rol.nombre.label("rol"),
            Empleado.sucursal_id,
            Sucursal.nombre.label("sucursal"),
        )
        .join(Rol, Rol.id == Usuario.rol_id)
        .outerjoin(Empleado, Empleado.usuario_id == Usuario.id)
        .outerjoin(Sucursal, Sucursal.id == Empleado.sucursal_id)
    )

    condiciones = []
    if busqueda:
        # Busqueda por nombre o correo, sin distinguir mayusculas.
        patron = f"%{busqueda.strip().lower()}%"
        condiciones.append(
            or_(
                func.lower(Usuario.correo).like(patron),
                func.lower(Usuario.nombres).like(patron),
                func.lower(Usuario.apellidos).like(patron),
            )
        )
    if rol:
        condiciones.append(Rol.nombre == rol.upper())
    if activo is not None:
        condiciones.append(Usuario.activo.is_(activo))

    if condiciones:
        origen = origen.where(*condiciones)

    total = db.scalar(select(func.count()).select_from(origen.subquery())) or 0

    filas = db.execute(
        origen.order_by(Usuario.creado_en.desc(), Usuario.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    ).all()
    return total, list(filas)


def obtener_detalle_usuario(db: Session, usuario_id: int) -> Row | None:
    """Una sola fila del listado, para devolver el usuario recien tocado."""
    return db.execute(
        select(
            Usuario.id,
            Usuario.correo,
            Usuario.nombres,
            Usuario.apellidos,
            Usuario.activo,
            Usuario.creado_en,
            Rol.nombre.label("rol"),
            Empleado.sucursal_id,
            Sucursal.nombre.label("sucursal"),
        )
        .join(Rol, Rol.id == Usuario.rol_id)
        .outerjoin(Empleado, Empleado.usuario_id == Usuario.id)
        .outerjoin(Sucursal, Sucursal.id == Empleado.sucursal_id)
        .where(Usuario.id == usuario_id)
    ).one_or_none()


def obtener_empleado_de_usuario(db: Session, usuario_id: int) -> Empleado | None:
    """Ficha de empleado del usuario, si la tiene."""
    return db.scalar(select(Empleado).where(Empleado.usuario_id == usuario_id))


def existe_sucursal_activa(db: Session, sucursal_id: int) -> bool:
    """La sucursal existe y esta operativa."""
    return (
        db.scalar(
            select(Sucursal.id).where(
                Sucursal.id == sucursal_id, Sucursal.activa.is_(True)
            )
        )
        is not None
    )


def agregar_empleado(
    db: Session,
    *,
    usuario_id: int,
    sucursal_id: int,
    documento: str,
    cargo: str,
    fecha_ingreso: date,
) -> Empleado:
    """Crea la ficha de empleado que guarda la sucursal del usuario."""
    empleado = Empleado(
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
        documento=documento,
        cargo=cargo,
        fecha_ingreso=fecha_ingreso,
    )
    db.add(empleado)
    db.flush()
    return empleado


def tiene_operaciones_asociadas(db: Session, usuario_id: int) -> bool:
    """Indica si el usuario esta referenciado por algo que impida borrarlo.

    En el Ciclo 1 son `empleado` y `proveedor`: sus claves foraneas hacia
    usuario NO tienen ON DELETE CASCADE, asi que el borrado fallaria con una
    violacion de integridad. `cliente` y `sesion_token` si cascadean, por eso
    no cuentan.

    En los ciclos siguientes hay que sumar aca ventas, reservas y movimientos
    de inventario.
    """
    if db.scalar(select(Empleado.id).where(Empleado.usuario_id == usuario_id)):
        return True
    if db.scalar(select(Proveedor.id).where(Proveedor.usuario_id == usuario_id)):
        return True
    return False


def eliminar_usuario(db: Session, usuario: Usuario) -> None:
    """Borra el usuario. Su ficha de cliente y sus sesiones cascadean."""
    db.delete(usuario)
    db.flush()


# --- CU-04 Gestionar perfil del cliente ----------------------------------

def obtener_cliente_de_usuario(db: Session, usuario_id: int) -> Cliente | None:
    """Ficha de cliente del usuario, con su usuario ya cargado.

    El joinedload evita la consulta extra al leer nombres, apellidos y correo,
    que viven en usuario y no en cliente.
    """
    return db.scalar(
        select(Cliente)
        .options(joinedload(Cliente.usuario))
        .where(Cliente.usuario_id == usuario_id)
    )


def listar_direcciones(db: Session, cliente_id: int) -> list[Row]:
    """Direcciones del cliente con el nombre de su ciudad.

    La predeterminada va primero: es la que la interfaz ofrece por defecto.
    """
    return list(
        db.execute(
            select(
                DireccionCliente.id,
                DireccionCliente.ciudad_id,
                Ciudad.nombre.label("ciudad"),
                DireccionCliente.alias,
                DireccionCliente.direccion,
                DireccionCliente.referencia,
                DireccionCliente.predeterminada,
            )
            .join(Ciudad, Ciudad.id == DireccionCliente.ciudad_id)
            .where(DireccionCliente.cliente_id == cliente_id)
            .order_by(DireccionCliente.predeterminada.desc(), DireccionCliente.alias)
        ).all()
    )


def existe_ciudad(db: Session, ciudad_id: int) -> bool:
    """Indica si la ciudad existe. La clave foranea cruza al paquete P2."""
    return db.scalar(select(Ciudad.id).where(Ciudad.id == ciudad_id)) is not None


def obtener_direccion(
    db: Session, direccion_id: int, cliente_id: int
) -> DireccionCliente | None:
    """Direccion del cliente indicado, o None.

    Filtra SIEMPRE por cliente_id ademas de por id: es lo que impide que un
    cliente borre o modifique la direccion de otro pasando un id ajeno.
    """
    return db.scalar(
        select(DireccionCliente).where(
            DireccionCliente.id == direccion_id,
            DireccionCliente.cliente_id == cliente_id,
        )
    )


def desmarcar_predeterminadas(db: Session, cliente_id: int) -> None:
    """Quita la marca de predeterminada a todas las direcciones del cliente.

    Hay que ejecutarlo ANTES de marcar la nueva, dentro de la misma
    transaccion: el indice parcial uq_direccion_predeterminada solo admite una
    fila con predeterminada = true por cliente, y rechazaria la segunda.
    """
    db.execute(
        update(DireccionCliente)
        .where(
            DireccionCliente.cliente_id == cliente_id,
            DireccionCliente.predeterminada.is_(True),
        )
        .values(predeterminada=False)
    )
    db.flush()


def agregar_direccion(
    db: Session,
    *,
    cliente_id: int,
    ciudad_id: int,
    alias: str,
    direccion: str,
    referencia: str | None,
    predeterminada: bool,
) -> DireccionCliente:
    """Agrega una direccion de entrega, sin confirmar."""
    fila = DireccionCliente(
        cliente_id=cliente_id,
        ciudad_id=ciudad_id,
        alias=alias,
        direccion=direccion,
        referencia=referencia,
        predeterminada=predeterminada,
    )
    db.add(fila)
    db.flush()
    return fila


def eliminar_direccion(db: Session, direccion: DireccionCliente) -> None:
    """Borra la direccion. Si era la predeterminada, el cliente queda sin una.

    Es lo que pide el flujo alternativo 3b: no se promueve otra en su lugar.
    """
    db.delete(direccion)
    db.flush()
