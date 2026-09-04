"""
P1 - Seguridad y Usuarios  |  capa: repositorio (consultas, sin logica de negocio)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.seguridad.models import Cliente, Rol, Usuario

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


# TODO CU-02, CU-03 y CU-04: implementar sus consultas.
