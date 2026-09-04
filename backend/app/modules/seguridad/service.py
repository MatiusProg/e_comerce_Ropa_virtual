"""
P1 - Seguridad y Usuarios  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.modules.seguridad import repository
from app.modules.seguridad.schemas import ClienteRegistradoOut, ClienteRegistroIn

# Regla: aqui viven las reglas de negocio y el control de la transaccion.
# El servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

#: Nombre del rol que se asigna a quien se registra por CU-01. Debe existir en
#: la tabla rol, cargado por el seed. Los nombres de rol van en mayusculas,
#: igual que los que compara app/core/dependencies.py.
ROL_CLIENTE = "CLIENTE"


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeRegistro(Exception):
    """Base de los errores previstos de CU-01."""


class CorreoYaRegistrado(ErrorDeRegistro):
    """Excepcion E1: el correo ya corresponde a un usuario del sistema."""


class DocumentoYaRegistrado(ErrorDeRegistro):
    """El documento de identidad ya pertenece a otro cliente."""


class RolClienteInexistente(ErrorDeRegistro):
    """La tabla rol no tiene el rol CLIENTE. Falta correr el seed."""


# --- CU-01 Registrar cliente ---------------------------------------------

def registrar_cliente(db: Session, datos: ClienteRegistroIn) -> ClienteRegistradoOut:
    """Crea el usuario con rol Cliente y su ficha de cliente asociada.

    Realiza el flujo principal de CU-01 a partir del paso 5. Los pasos 1 a 4
    (presentar el formulario y validar el formato de los datos) ocurren en el
    cliente y en los esquemas de Pydantic.

      5. verificar que el correo no este registrado
      6. calcular el hash de la contrasena
      7. crear el usuario y la ficha de cliente
      8. confirmar

    Las dos entidades se crean en UNA sola transaccion: si falla cualquiera de
    las dos no se crea ninguna (excepcion E2).
    """
    # Paso 5 - precondicion del caso de uso (excepcion E1).
    if repository.obtener_usuario_por_correo(db, datos.correo) is not None:
        raise CorreoYaRegistrado(datos.correo)

    if datos.documento is not None and repository.existe_cliente_con_documento(
        db, datos.documento
    ):
        raise DocumentoYaRegistrado(datos.documento)

    rol = repository.obtener_rol_por_nombre(db, ROL_CLIENTE)
    if rol is None:
        raise RolClienteInexistente(ROL_CLIENTE)

    try:
        # Paso 6 - la contrasena en claro no se guarda ni se registra en el log.
        hash_contrasena = hash_password(datos.contrasena)

        # Paso 7 - las dos altas comparten transaccion.
        usuario = repository.agregar_usuario(
            db,
            correo=datos.correo,
            hash_contrasena=hash_contrasena,
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            rol_id=rol.id,
        )
        repository.agregar_cliente(
            db,
            usuario_id=usuario.id,
            documento=datos.documento,
            telefono=datos.telefono,
        )
        db.commit()
    except IntegrityError as exc:
        # Entre el paso 5 y el commit puede colarse otro registro con el mismo
        # correo. La restriccion UNIQUE de la base es la que lo impide de
        # verdad; la consulta previa solo sirve para dar un mensaje claro en el
        # caso normal. Sin este bloque, esa carrera devolveria un 500.
        db.rollback()
        if _viola(exc, "usuario", "correo"):
            raise CorreoYaRegistrado(datos.correo) from exc
        if _viola(exc, "cliente", "documento"):
            raise DocumentoYaRegistrado(datos.documento or "") from exc
        raise
    except Exception:
        # Excepcion E2: cualquier otro fallo deja la base como estaba.
        db.rollback()
        raise

    return ClienteRegistradoOut(
        id=usuario.id,
        correo=usuario.correo,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        rol=rol.nombre,
    )


def _viola(exc: IntegrityError, tabla: str, columna: str) -> bool:
    """Indica si la violacion de unicidad corresponde a esa tabla y columna.

    Se apoya en la convencion de nombres de app/db/base.py, que nombra las
    restricciones unicas como uq_<tabla>_<columna>. PostgreSQL tambien crea el
    indice implicito con ese nombre, asi que alcanza con buscarlo en el mensaje.
    """
    return f"uq_{tabla}_{columna}" in str(exc.orig)


# TODO CU-02, CU-03 y CU-04: implementar sus reglas de negocio.
