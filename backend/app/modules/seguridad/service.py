"""
P1 - Seguridad y Usuarios  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
import uuid
from datetime import date
from math import ceil

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import crear_access_token, hash_password, verify_password
from app.modules.seguridad import repository
from app.modules.seguridad.models import Cliente
from app.modules.seguridad.schemas import (
    ROLES_CON_SUCURSAL,
    CambioContrasenaIn,
    CambioEstadoIn,  # noqa: F401  (lo usa el router)
    ClienteRegistradoOut,
    ClienteRegistroIn,
    DireccionIn,
    DireccionOut,
    LoginIn,
    PaginaUsuarios,
    PerfilEditarIn,
    PerfilOut,
    RolOut,
    TokenOut,
    UsuarioAutenticadoOut,
    UsuarioCrearIn,
    UsuarioEditarIn,
    UsuarioResumenOut,
)

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


# --- CU-02 Iniciar y cerrar sesion ---------------------------------------

class ErrorDeAutenticacion(Exception):
    """Base de los errores previstos de CU-02."""


class CredencialesInvalidas(ErrorDeAutenticacion):
    """Excepcion E1: el correo no existe o la contrasena no coincide.

    Deliberadamente NO distingue entre ambos casos. Si el sistema dijera cual
    de los dos fallo, cualquiera podria averiguar que correos estan
    registrados probando de a uno.
    """


class CuentaDesactivada(ErrorDeAutenticacion):
    """Excepcion E2: el usuario existe y sus credenciales son correctas, pero
    su cuenta fue dada de baja."""


def autenticar(db: Session, datos: LoginIn) -> TokenOut:
    """Verifica las credenciales y emite un token, registrando la sesion.

      1. buscar el usuario por correo
      2. verificar que la cuenta este activa
      3. verificar el hash de la contrasena
      4. emitir el token con su jti
      5. registrar la sesion
      6. devolver el token
    """
    usuario = repository.obtener_usuario_con_rol(db, datos.correo)

    # El orden importa: primero se comprueba que exista y que la contrasena
    # sea correcta, y recien despues si esta activo. Al reves, un atacante
    # distinguiria "cuenta desactivada" de "no existe" sin saber la
    # contrasena, y eso ya revela que el correo esta registrado.
    if usuario is None or not verify_password(datos.contrasena, usuario.hash_contrasena):
        raise CredencialesInvalidas(datos.correo)

    if not usuario.activo:
        raise CuentaDesactivada(datos.correo)

    emitido = crear_access_token(
        usuario_id=usuario.id,
        rol=usuario.rol.nombre,
        sucursal_id=repository.obtener_sucursal_de_usuario(db, usuario.id),
    )

    try:
        repository.agregar_sesion(
            db,
            usuario_id=usuario.id,
            jti=emitido.jti,
            expira_en=emitido.expira_en,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return TokenOut(
        access_token=emitido.token,
        expira_en=emitido.expira_en,
        usuario=UsuarioAutenticadoOut(
            id=usuario.id,
            correo=usuario.correo,
            nombres=usuario.nombres,
            apellidos=usuario.apellidos,
            rol=usuario.rol.nombre,
            sucursal_id=repository.obtener_sucursal_de_usuario(db, usuario.id),
        ),
    )


def obtener_usuario_autenticado(db: Session, usuario_id: int) -> UsuarioAutenticadoOut:
    """Datos del usuario que porta el token, leidos de la base.

    No se arman desde el token: si el nombre o el rol cambiaron despues de
    emitirlo, el token seguiria diciendo lo viejo.
    """
    usuario = repository.obtener_usuario_con_id(db, usuario_id)
    if usuario is None:
        raise CredencialesInvalidas(str(usuario_id))
    return UsuarioAutenticadoOut(
        id=usuario.id,
        correo=usuario.correo,
        nombres=usuario.nombres,
        apellidos=usuario.apellidos,
        rol=usuario.rol.nombre,
        sucursal_id=repository.obtener_sucursal_de_usuario(db, usuario.id),
    )


def cerrar_sesion(db: Session, jti: uuid.UUID) -> None:
    """Revoca la sesion del token presentado.

    Es idempotente: cerrar sesion dos veces con el mismo token no es un error,
    la segunda vez sencillamente no cambia nada.
    """
    try:
        repository.revocar_sesion(db, jti)
        db.commit()
    except Exception:
        db.rollback()
        raise


# --- CU-03 Gestionar usuarios y roles ------------------------------------

class ErrorDeGestion(Exception):
    """Base de los errores previstos de CU-03."""


class UsuarioInexistente(ErrorDeGestion):
    """El identificador no corresponde a ningun usuario."""


class RolInexistente(ErrorDeGestion):
    """El rol indicado no existe en la tabla rol."""


class SucursalRequerida(ErrorDeGestion):
    """Excepcion E2: el rol exige sucursal y no se indico ninguna."""


class SucursalInvalida(ErrorDeGestion):
    """La sucursal indicada no existe o no esta activa."""


class DatosDeEmpleadoRequeridos(ErrorDeGestion):
    """Falta el documento para poder crear la ficha de empleado."""


class AutodesactivacionProhibida(ErrorDeGestion):
    """Excepcion E3: nadie puede desactivarse ni borrarse a si mismo."""


class UsuarioConOperaciones(ErrorDeGestion):
    """Flujo 3c: tiene operaciones asociadas; corresponde desactivar, no borrar."""


def _fila_a_resumen(fila) -> UsuarioResumenOut:
    return UsuarioResumenOut(
        id=fila.id,
        correo=fila.correo,
        nombres=fila.nombres,
        apellidos=fila.apellidos,
        rol=fila.rol,
        sucursal_id=fila.sucursal_id,
        sucursal=fila.sucursal,
        activo=fila.activo,
        creado_en=fila.creado_en,
    )


def listar_roles(db: Session) -> list[RolOut]:
    """Roles asignables, marcando cuales exigen sucursal."""
    return [
        RolOut(
            id=r.id,
            nombre=r.nombre,
            descripcion=r.descripcion,
            exige_sucursal=r.nombre in ROLES_CON_SUCURSAL,
        )
        for r in repository.listar_roles(db)
    ]


def listar_usuarios(
    db: Session,
    *,
    busqueda: str | None = None,
    rol: str | None = None,
    activo: bool | None = None,
    pagina: int = 1,
    tamano: int = 20,
) -> PaginaUsuarios:
    """Listado paginado con busqueda y filtros (paso 2)."""
    total, filas = repository.contar_y_listar_usuarios(
        db, busqueda=busqueda, rol=rol, activo=activo, pagina=pagina, tamano=tamano
    )
    return PaginaUsuarios(
        items=[_fila_a_resumen(f) for f in filas],
        total=total,
        pagina=pagina,
        tamano=tamano,
        paginas=max(1, ceil(total / tamano)),
    )


def obtener_usuario(db: Session, usuario_id: int) -> UsuarioResumenOut:
    fila = repository.obtener_detalle_usuario(db, usuario_id)
    if fila is None:
        raise UsuarioInexistente(str(usuario_id))
    return _fila_a_resumen(fila)


def _validar_ambito(
    db: Session, rol_nombre: str, sucursal_id: int | None
) -> None:
    """Comprueba la coherencia entre el rol y la sucursal (excepcion E2)."""
    if rol_nombre in ROLES_CON_SUCURSAL:
        if sucursal_id is None:
            raise SucursalRequerida(rol_nombre)
        if not repository.existe_sucursal_activa(db, sucursal_id):
            raise SucursalInvalida(str(sucursal_id))


def crear_usuario(db: Session, datos: UsuarioCrearIn) -> UsuarioResumenOut:
    """Alta de usuario desde el panel (pasos 5 a 7).

    Cuando el rol exige sucursal se crea tambien la ficha de empleado, en la
    MISMA transaccion: es esa ficha la que guarda la sucursal, y un usuario
    Encargado sin ella no tendria ambito de datos.
    """
    if repository.obtener_usuario_por_correo(db, datos.correo) is not None:
        raise CorreoYaRegistrado(datos.correo)

    rol = repository.obtener_rol_por_nombre(db, datos.rol)
    if rol is None:
        raise RolInexistente(datos.rol)

    _validar_ambito(db, rol.nombre, datos.sucursal_id)

    exige_empleado = rol.nombre in ROLES_CON_SUCURSAL
    if exige_empleado and not datos.documento:
        raise DatosDeEmpleadoRequeridos(rol.nombre)

    try:
        usuario = repository.agregar_usuario(
            db,
            correo=datos.correo,
            hash_contrasena=hash_password(datos.contrasena),
            nombres=datos.nombres,
            apellidos=datos.apellidos,
            rol_id=rol.id,
        )
        if exige_empleado:
            repository.agregar_empleado(
                db,
                usuario_id=usuario.id,
                sucursal_id=datos.sucursal_id,  # type: ignore[arg-type]
                documento=datos.documento,  # type: ignore[arg-type]
                cargo=rol.nombre,
                fecha_ingreso=datos.fecha_ingreso or date.today(),
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "usuario", "correo"):
            raise CorreoYaRegistrado(datos.correo) from exc
        if _viola(exc, "empleado", "documento"):
            raise DocumentoYaRegistrado(datos.documento or "") from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_usuario(db, usuario.id)


def editar_usuario(
    db: Session, usuario_id: int, datos: UsuarioEditarIn
) -> UsuarioResumenOut:
    """Edición de un usuario (flujo alternativo 3a)."""
    usuario = repository.obtener_usuario_con_id(db, usuario_id)
    if usuario is None:
        raise UsuarioInexistente(str(usuario_id))

    if datos.correo and datos.correo != usuario.correo:
        otro = repository.obtener_usuario_por_correo(db, datos.correo)
        if otro is not None and otro.id != usuario_id:
            raise CorreoYaRegistrado(datos.correo)

    rol = usuario.rol
    if datos.rol and datos.rol != usuario.rol.nombre:
        rol = repository.obtener_rol_por_nombre(db, datos.rol)
        if rol is None:
            raise RolInexistente(datos.rol)

    empleado = repository.obtener_empleado_de_usuario(db, usuario_id)
    sucursal_id = datos.sucursal_id if datos.sucursal_id is not None else (
        empleado.sucursal_id if empleado else None
    )
    _validar_ambito(db, rol.nombre, sucursal_id)

    try:
        if datos.nombres is not None:
            usuario.nombres = datos.nombres
        if datos.apellidos is not None:
            usuario.apellidos = datos.apellidos
        if datos.correo is not None:
            usuario.correo = datos.correo
        # La contrasena SOLO cambia si se envio una nueva (flujo 3a).
        if datos.contrasena is not None:
            usuario.hash_contrasena = hash_password(datos.contrasena)
            # Cambiar la contrasena invalida las sesiones abiertas: si alguien
            # la cambio porque la cuenta estaba comprometida, dejar vivos los
            # tokens anteriores no serviria de nada.
            repository.revocar_sesiones_de_usuario(db, usuario_id)
        usuario.rol_id = rol.id

        if empleado is not None and sucursal_id is not None:
            empleado.sucursal_id = sucursal_id
            empleado.cargo = rol.nombre if rol.nombre in ROLES_CON_SUCURSAL else empleado.cargo

        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _viola(exc, "usuario", "correo"):
            raise CorreoYaRegistrado(datos.correo or "") from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_usuario(db, usuario_id)


def cambiar_estado(
    db: Session, usuario_id: int, activo: bool, *, solicitante_id: int
) -> UsuarioResumenOut:
    """Activa o desactiva una cuenta (flujo alternativo 3b).

    Al desactivar se revocan todas las sesiones vigentes del usuario. Sin eso,
    quien ya tenia un token seguiria entrando hasta que venciera, y la
    postcondicion del caso de uso --"un usuario desactivado no puede iniciar
    sesion"-- se cumpliria solo a medias.
    """
    usuario = repository.obtener_usuario_con_id(db, usuario_id)
    if usuario is None:
        raise UsuarioInexistente(str(usuario_id))

    # Excepcion E3.
    if not activo and usuario_id == solicitante_id:
        raise AutodesactivacionProhibida(str(usuario_id))

    try:
        usuario.activo = activo
        if not activo:
            repository.revocar_sesiones_de_usuario(db, usuario_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return obtener_usuario(db, usuario_id)


def eliminar_usuario(db: Session, usuario_id: int, *, solicitante_id: int) -> None:
    """Baja de un usuario (flujo alternativo 3c).

    Solo se permite si no tiene operaciones asociadas; si las tiene, el caso de
    uso indica ofrecer desactivar en su lugar, y eso lo resuelve la interfaz
    con el error que devuelve este servicio.
    """
    usuario = repository.obtener_usuario_con_id(db, usuario_id)
    if usuario is None:
        raise UsuarioInexistente(str(usuario_id))

    # Excepcion E3: tampoco puede borrarse a si mismo.
    if usuario_id == solicitante_id:
        raise AutodesactivacionProhibida(str(usuario_id))

    if repository.tiene_operaciones_asociadas(db, usuario_id):
        raise UsuarioConOperaciones(str(usuario_id))

    try:
        repository.eliminar_usuario(db, usuario)
        db.commit()
    except IntegrityError as exc:
        # Red de seguridad: si alguna clave foranea que todavia no contemplamos
        # bloquea el borrado, se informa como "tiene operaciones" en vez de
        # devolver un 500.
        db.rollback()
        raise UsuarioConOperaciones(str(usuario_id)) from exc
    except Exception:
        db.rollback()
        raise


# --- CU-04 Gestionar perfil del cliente ----------------------------------

class ErrorDePerfil(Exception):
    """Base de los errores previstos de CU-04."""


class PerfilInexistente(ErrorDePerfil):
    """El usuario autenticado no tiene ficha de cliente.

    No deberia ocurrir: CU-01 crea usuario y cliente en la misma transaccion, y
    el endpoint exige rol CLIENTE. Se contempla igual porque un administrador
    puede haber creado por CU-03 una cuenta con rol Cliente sin ficha.
    """


class CiudadInexistente(ErrorDePerfil):
    """La ciudad indicada para la direccion no existe."""


class DireccionInexistente(ErrorDePerfil):
    """La direccion no existe o no pertenece a este cliente."""


class ContrasenaActualIncorrecta(ErrorDePerfil):
    """Excepcion E1 del flujo alternativo 3c."""


def _cliente_del_usuario(db: Session, usuario_id: int) -> Cliente:
    """Ficha de cliente del usuario autenticado, o error.

    Toda operacion de CU-04 pasa por aqui: es el unico punto donde se resuelve
    de quien es el perfil, y lo resuelve a partir del usuario_id del token,
    nunca de un identificador enviado en el cuerpo de la peticion.
    """
    cliente = repository.obtener_cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise PerfilInexistente(str(usuario_id))
    return cliente


def _direcciones(db: Session, cliente_id: int) -> list[DireccionOut]:
    """Direcciones del cliente ya convertidas al esquema de salida."""
    return [
        DireccionOut.model_validate(f, from_attributes=True)
        for f in repository.listar_direcciones(db, cliente_id)
    ]


def obtener_perfil(db: Session, usuario_id: int) -> PerfilOut:
    """Pasos 1 y 2: devuelve los datos del perfil del cliente autenticado."""
    cliente = _cliente_del_usuario(db, usuario_id)
    return PerfilOut(
        nombres=cliente.usuario.nombres,
        apellidos=cliente.usuario.apellidos,
        correo=cliente.usuario.correo,
        documento=cliente.documento,
        telefono=cliente.telefono,
        talla_superior=cliente.talla_superior,
        talla_inferior=cliente.talla_inferior,
        talla_calzado=cliente.talla_calzado,
        direcciones=_direcciones(db, cliente.id),
    )


def editar_perfil(db: Session, usuario_id: int, datos: PerfilEditarIn) -> PerfilOut:
    """Pasos 3 a 5: valida los datos recibidos y los guarda.

    Solo se toca lo que vino en la peticion. `model_fields_set` distingue el
    campo ausente -- que se deja como esta -- del campo enviado vacio, que el
    validador convirtio en None y que aqui significa borrar el dato.
    """
    cliente = _cliente_del_usuario(db, usuario_id)
    usuario = cliente.usuario
    enviados = datos.model_fields_set

    # Excepcion E2: el correo nuevo no puede estar en uso por otra cuenta.
    if datos.correo and datos.correo != usuario.correo:
        otro = repository.obtener_usuario_por_correo(db, datos.correo)
        if otro is not None and otro.id != usuario_id:
            raise CorreoYaRegistrado(datos.correo)

    if (
        "documento" in enviados
        and datos.documento is not None
        and datos.documento != cliente.documento
        and repository.existe_cliente_con_documento(db, datos.documento)
    ):
        raise DocumentoYaRegistrado(datos.documento)

    try:
        # nombres, apellidos y correo son NOT NULL: vaciarlos no es borrar un
        # dato opcional, es dejar la fila invalida. Por eso solo se asignan
        # cuando traen valor, y el esquema les exige min_length=1.
        if datos.nombres is not None:
            usuario.nombres = datos.nombres
        if datos.apellidos is not None:
            usuario.apellidos = datos.apellidos
        if datos.correo is not None:
            usuario.correo = datos.correo

        # Los de cliente si son opcionales en la base, asi que aca enviar el
        # campo vacio significa borrarlo.
        for campo in (
            "documento",
            "telefono",
            "talla_superior",
            "talla_inferior",
            "talla_calzado",
        ):
            if campo in enviados:
                setattr(cliente, campo, getattr(datos, campo))

        db.commit()
    except IntegrityError as exc:
        # Misma carrera que en CU-01: entre la verificacion y el commit puede
        # colarse otra cuenta con ese correo. La restriccion UNIQUE es la que
        # lo impide de verdad.
        db.rollback()
        if _viola(exc, "usuario", "correo"):
            raise CorreoYaRegistrado(datos.correo or "") from exc
        if _viola(exc, "cliente", "documento"):
            raise DocumentoYaRegistrado(datos.documento or "") from exc
        raise
    except Exception:
        db.rollback()
        raise

    return obtener_perfil(db, usuario_id)


def agregar_direccion(
    db: Session, usuario_id: int, datos: DireccionIn
) -> list[DireccionOut]:
    """Flujo alternativo 3a: registra una direccion de entrega.

    Si llega marcada como predeterminada hay que desmarcar la anterior primero,
    en la misma transaccion: el indice parcial uq_direccion_predeterminada
    admite una sola por cliente y, sin ese paso, la insercion fallaria.
    """
    cliente = _cliente_del_usuario(db, usuario_id)

    if not repository.existe_ciudad(db, datos.ciudad_id):
        raise CiudadInexistente(str(datos.ciudad_id))

    # La primera direccion de un cliente queda como predeterminada aunque no la
    # haya marcado: tener direcciones y ninguna preferida no le sirve a nadie.
    predeterminada = datos.predeterminada or not repository.listar_direcciones(
        db, cliente.id
    )

    try:
        if predeterminada:
            repository.desmarcar_predeterminadas(db, cliente.id)
        repository.agregar_direccion(
            db,
            cliente_id=cliente.id,
            ciudad_id=datos.ciudad_id,
            alias=datos.alias,
            direccion=datos.direccion,
            referencia=datos.referencia,
            predeterminada=predeterminada,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _direcciones(db, cliente.id)


def marcar_direccion_predeterminada(
    db: Session, usuario_id: int, direccion_id: int
) -> list[DireccionOut]:
    """Deja una direccion como la predeterminada del cliente."""
    cliente = _cliente_del_usuario(db, usuario_id)
    direccion = repository.obtener_direccion(db, direccion_id, cliente.id)
    if direccion is None:
        raise DireccionInexistente(str(direccion_id))

    try:
        repository.desmarcar_predeterminadas(db, cliente.id)
        direccion.predeterminada = True
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _direcciones(db, cliente.id)


def eliminar_direccion(
    db: Session, usuario_id: int, direccion_id: int
) -> list[DireccionOut]:
    """Flujo alternativo 3b: elimina una direccion.

    Si era la predeterminada, el cliente queda sin predeterminada; el caso de
    uso no pide promover otra en su lugar.
    """
    cliente = _cliente_del_usuario(db, usuario_id)
    direccion = repository.obtener_direccion(db, direccion_id, cliente.id)
    if direccion is None:
        raise DireccionInexistente(str(direccion_id))

    try:
        repository.eliminar_direccion(db, direccion)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return _direcciones(db, cliente.id)


def cambiar_contrasena(db: Session, usuario_id: int, datos: CambioContrasenaIn) -> None:
    """Flujo alternativo 3c: reemplaza la contrasena del propio cliente.

    Verifica la actual ANTES de reemplazar el hash (excepcion E1) y revoca las
    sesiones abiertas, por el mismo motivo que CU-03: si la contrasena se
    cambio porque la cuenta estaba comprometida, dejar vivos los tokens ya
    emitidos no serviria de nada.
    """
    cliente = _cliente_del_usuario(db, usuario_id)
    usuario = cliente.usuario

    if not verify_password(datos.contrasena_actual, usuario.hash_contrasena):
        raise ContrasenaActualIncorrecta(str(usuario_id))

    try:
        usuario.hash_contrasena = hash_password(datos.contrasena_nueva)
        repository.revocar_sesiones_de_usuario(db, usuario_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
