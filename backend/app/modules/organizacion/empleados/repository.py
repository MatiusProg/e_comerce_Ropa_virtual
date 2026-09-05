"""
P2 - Organizacion / CU-06  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1
Caso de uso: CU-06 Gestionar empleados

Regla: aqui solo van consultas. Ninguna regla de negocio, ninguna validacion de
permisos, ningun commit. El control de la transaccion vive en el servicio,
porque el alta de un empleado crea dos entidades que tienen que aparecer juntas
o no aparecer (excepcion E3).

Este modulo consulta tablas de P1 (usuario). Es la direccion permitida por la
regla de dependencias de la seccion 2.4: P2 conoce a P1, no al reves.
"""
from datetime import date

from sqlalchemy import Row, and_, exists, or_, select
from sqlalchemy.orm import Session

from app.modules.organizacion.models import Ciudad, Empleado, Proveedor, Sucursal
from app.modules.seguridad.models import Rol, Usuario


def _seleccion_empleado():
    """Columnas del listado, con el nombre de la sucursal y de su ciudad.

    El listado del paso 2 muestra nombre, cargo, sucursal y estado; los tres
    ultimos vienen de tres tablas distintas, asi que se resuelven en una sola
    consulta en vez de con accesos perezosos por fila.
    """
    return (
        select(
            Empleado.id,
            Empleado.usuario_id,
            Usuario.nombres,
            Usuario.apellidos,
            Usuario.correo,
            Usuario.activo.label("usuario_activo"),
            Empleado.documento,
            Empleado.telefono,
            Empleado.cargo,
            Empleado.sucursal_id,
            Sucursal.nombre.label("sucursal"),
            Ciudad.nombre.label("ciudad"),
            Empleado.fecha_ingreso,
            Empleado.fecha_baja,
        )
        .join(Usuario, Usuario.id == Empleado.usuario_id)
        .join(Sucursal, Sucursal.id == Empleado.sucursal_id)
        .join(Ciudad, Ciudad.id == Sucursal.ciudad_id)
    )


def listar_empleados(
    db: Session,
    *,
    busqueda: str | None = None,
    sucursal_id: int | None = None,
    cargo: str | None = None,
    activo: bool | None = None,
) -> list[Row]:
    """Empleados con los filtros del paso 2.

    `activo` se resuelve sobre `fecha_baja`, no sobre el estado del usuario:
    son cosas distintas y el caso de uso filtra por la primera.
    """
    consulta = _seleccion_empleado()

    if busqueda:
        patron = f"%{busqueda.strip()}%"
        consulta = consulta.where(
            or_(
                Usuario.nombres.ilike(patron),
                Usuario.apellidos.ilike(patron),
                Empleado.documento.ilike(patron),
            )
        )
    if sucursal_id is not None:
        consulta = consulta.where(Empleado.sucursal_id == sucursal_id)
    if cargo is not None:
        consulta = consulta.where(Empleado.cargo == cargo)
    if activo is True:
        consulta = consulta.where(Empleado.fecha_baja.is_(None))
    elif activo is False:
        consulta = consulta.where(Empleado.fecha_baja.is_not(None))

    return list(
        db.execute(
            consulta.order_by(Ciudad.nombre, Sucursal.nombre, Usuario.apellidos)
        ).all()
    )


def obtener_empleado_con_detalle(db: Session, empleado_id: int) -> Row | None:
    """Una fila del listado, para un empleado."""
    return db.execute(
        _seleccion_empleado().where(Empleado.id == empleado_id)
    ).first()


def obtener_empleado(db: Session, empleado_id: int) -> Empleado | None:
    """La entidad, para modificarla."""
    return db.scalar(select(Empleado).where(Empleado.id == empleado_id))


def existe_documento(
    db: Session, documento: str, *, excepto_empleado_id: int | None = None
) -> bool:
    """Excepcion E1. Al editar se excluye el propio empleado.

    Sin esa exclusion, guardar un empleado sin tocarle el documento fallaria
    diciendo que su propio documento ya esta registrado.
    """
    consulta = select(Empleado.id).where(Empleado.documento == documento)
    if excepto_empleado_id is not None:
        consulta = consulta.where(Empleado.id != excepto_empleado_id)
    return db.scalar(consulta) is not None


def obtener_sucursal_activa(db: Session, sucursal_id: int) -> Sucursal | None:
    """Excepcion E2: solo una sucursal activa puede recibir empleados."""
    return db.scalar(
        select(Sucursal).where(Sucursal.id == sucursal_id, Sucursal.activa.is_(True))
    )


def existe_sucursal(db: Session, sucursal_id: int) -> bool:
    """Distingue «no existe» de «existe pero esta dada de baja» (E2)."""
    return db.scalar(select(Sucursal.id).where(Sucursal.id == sucursal_id)) is not None


#: Roles cuyas cuentas no pueden convertirse en empleado.
#:
#: Un Cliente es la cuenta con la que alguien compra; un Proveedor es la cuenta
#: con la que una empresa consulta sus propios productos (CU-07). Vincular
#: cualquiera de las dos a una ficha de empleado le cambiaria el rol y le
#: quitaria el acceso a lo suyo, sin avisar.
ROLES_NO_VINCULABLES = ("CLIENTE", "PROVEEDOR")


def _condiciones_de_vinculable():
    """Que hace que una cuenta pueda convertirse en empleado (flujo 3c).

    Se comparte entre el listado y la verificacion del alta: si las dos no
    dijeran exactamente lo mismo, la interfaz ofreceria candidatos que el
    servidor despues rechaza.
    """
    tiene_empleado = exists().where(Empleado.usuario_id == Usuario.id)
    # El CU-07 vincula la ficha de proveedor a una cuenta propia. Sin esta
    # condicion, esa cuenta apareceria como disponible y asignarla como
    # empleado le cambiaria el rol, dejando al proveedor sin acceso a su ficha.
    tiene_proveedor = exists().where(Proveedor.usuario_id == Usuario.id)

    return (
        ~tiene_empleado,
        ~tiene_proveedor,
        Usuario.activo.is_(True),
        Rol.nombre.not_in(ROLES_NO_VINCULABLES),
    )


def listar_usuarios_vinculables(db: Session) -> list[Row]:
    """Cuentas que pueden convertirse en empleado (flujo alternativo 3c)."""
    return list(
        db.execute(
            select(
                Usuario.id,
                Usuario.correo,
                Usuario.nombres,
                Usuario.apellidos,
                Rol.nombre.label("rol"),
            )
            .join(Rol, Rol.id == Usuario.rol_id)
            .where(*_condiciones_de_vinculable())
            .order_by(Usuario.apellidos, Usuario.nombres)
        ).all()
    )


def obtener_usuario_vinculable(db: Session, usuario_id: int) -> Usuario | None:
    """El usuario del flujo 3c, solo si sigue cumpliendo las condiciones.

    Se vuelve a comprobar aunque la interfaz haya ofrecido una lista ya
    filtrada: entre que se muestra el formulario y se confirma, otro
    administrador pudo haberlo vinculado o haberle dado acceso como proveedor.
    """
    return db.scalar(
        select(Usuario)
        .join(Rol, Rol.id == Usuario.rol_id)
        .where(and_(Usuario.id == usuario_id, *_condiciones_de_vinculable()))
    )


def obtener_rol_por_nombre(db: Session, nombre: str) -> Rol | None:
    return db.scalar(select(Rol).where(Rol.nombre == nombre))


def obtener_usuario_por_correo(db: Session, correo: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.correo == correo))


def agregar_usuario(
    db: Session,
    *,
    correo: str,
    hash_contrasena: str,
    nombres: str,
    apellidos: str,
    rol_id: int,
) -> Usuario:
    """Crea la cuenta del empleado, sin confirmar."""
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


def agregar_empleado(
    db: Session,
    *,
    usuario_id: int,
    sucursal_id: int,
    documento: str,
    telefono: str | None,
    cargo: str,
    fecha_ingreso: date,
) -> Empleado:
    """Crea la ficha de empleado, sin confirmar."""
    empleado = Empleado(
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
        documento=documento,
        telefono=telefono,
        cargo=cargo,
        fecha_ingreso=fecha_ingreso,
    )
    db.add(empleado)
    db.flush()
    return empleado


def obtener_usuario(db: Session, usuario_id: int) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.id == usuario_id))
