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
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.modules.organizacion.models import Empleado
from app.modules.seguridad.models import Cliente, Rol, SesionToken, Usuario

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


# TODO CU-03 y CU-04: implementar sus consultas.
