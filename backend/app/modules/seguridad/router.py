"""
P1 - Seguridad y Usuarios  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import DbSession, Usuario, requiere_roles
from app.modules.seguridad import service
from app.modules.seguridad.schemas import (
    CambioEstadoIn,
    ClienteRegistradoOut,
    ClienteRegistroIn,
    LoginIn,
    PaginaUsuarios,
    RolOut,
    TokenOut,
    UsuarioAutenticadoOut,
    UsuarioCrearIn,
    UsuarioEditarIn,
    UsuarioResumenOut,
)

router = APIRouter(prefix="/auth", tags=["Seguridad"])

# Regla: el router valida la entrada, resuelve la autorizacion y delega
# en el servicio. Ninguna regla de negocio vive aqui.


@router.post(
    "/registro",
    response_model=ClienteRegistradoOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-01 Registrar cliente",
    responses={
        409: {"description": "El correo o el documento ya estan registrados."},
        422: {"description": "Datos invalidos (flujo alternativo 4a)."},
    },
)
def registrar_cliente(datos: ClienteRegistroIn, db: DbSession) -> ClienteRegistradoOut:
    """Crea una cuenta de cliente.

    Es el unico endpoint publico de alta de usuarios: no exige token, porque el
    actor de CU-01 es un visitante sin sesion. Las altas de empleados (CU-06) y
    de usuarios internos (CU-03) van por otros endpoints y exigen Administrador.
    """
    try:
        return service.registrar_cliente(db, datos)
    except service.CorreoYaRegistrado:
        # Excepcion E1. El caso de uso indica ofrecer iniciar sesion o
        # recuperar la contrasena; eso lo resuelve la interfaz con este 409.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo electrónico.",
        )
    except service.DocumentoYaRegistrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese documento de identidad.",
        )
    except service.RolClienteInexistente:
        # No es culpa de quien se registra: falta cargar el seed de roles.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El sistema no está inicializado. Contacte al administrador.",
        )


@router.post(
    "/login",
    response_model=TokenOut,
    summary="CU-02 Iniciar sesion",
    responses={
        401: {"description": "Credenciales invalidas (excepcion E1)."},
        403: {"description": "La cuenta esta desactivada (excepcion E2)."},
    },
)
def iniciar_sesion(datos: LoginIn, db: DbSession) -> TokenOut:
    """Verifica las credenciales y devuelve un token de acceso."""
    try:
        return service.autenticar(db, datos)
    except service.CredencialesInvalidas:
        # Un solo mensaje para correo inexistente y contrasena incorrecta: si
        # se distinguieran, se podria averiguar que correos estan registrados.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo o la contraseña son incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except service.CuentaDesactivada:
        # 403 y no 401: no es "no te reconozco", es "te reconozco y no podes
        # entrar". Son situaciones distintas y la interfaz las trata distinto.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Su cuenta está desactivada. Contacte al administrador.",
        )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-02 Cerrar sesion",
    responses={401: {"description": "Falta el token o ya no es valido."}},
)
def cerrar_sesion(usuario: Usuario, db: DbSession) -> None:
    """Revoca la sesion del token presentado.

    A partir de aca ese token deja de servir, aunque todavia no haya expirado.
    """
    service.cerrar_sesion(db, usuario.jti)


@router.get(
    "/yo",
    response_model=UsuarioAutenticadoOut,
    summary="Datos del usuario autenticado",
    responses={401: {"description": "Falta el token o ya no es valido."}},
)
def usuario_autenticado(usuario: Usuario, db: DbSession) -> UsuarioAutenticadoOut:
    """Devuelve quien es el portador del token.

    La web lo usa al recargar la pagina: en vez de confiar en lo que tenga
    guardado en el navegador, le pregunta al servidor. Si el token fue
    revocado, esta llamada falla y la sesion se cierra sola.
    """
    return service.obtener_usuario_autenticado(db, usuario.id)


# --- CU-03 Gestionar usuarios y roles ------------------------------------
#
# Router aparte porque el prefijo es otro y porque TODO lo de aca exige rol
# Administrador. La dependencia se declara una sola vez, a nivel de router: si
# se declarara endpoint por endpoint, olvidarla en uno solo abriria un agujero.

admin_router = APIRouter(
    prefix="/usuarios",
    tags=["Seguridad · Administración"],
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Administrador."},
    },
)


def _traducir(error: service.ErrorDeGestion) -> HTTPException:
    """Convierte los errores de negocio de CU-03 en respuestas HTTP."""
    if isinstance(error, service.UsuarioInexistente):
        return HTTPException(404, "El usuario indicado no existe.")
    if isinstance(error, service.RolInexistente):
        return HTTPException(422, "El rol indicado no existe.")
    if isinstance(error, service.SucursalRequerida):
        # Excepcion E2.
        return HTTPException(
            422, "Los roles Encargado y Cajero requieren una sucursal asignada."
        )
    if isinstance(error, service.SucursalInvalida):
        return HTTPException(422, "La sucursal indicada no existe o no está activa.")
    if isinstance(error, service.DatosDeEmpleadoRequeridos):
        return HTTPException(
            422,
            "Para un Encargado o Cajero hay que indicar su documento de identidad.",
        )
    if isinstance(error, service.AutodesactivacionProhibida):
        # Excepcion E3.
        return HTTPException(409, "No puede desactivar ni eliminar su propia cuenta.")
    if isinstance(error, service.UsuarioConOperaciones):
        # Flujo 3c: la interfaz usa este mensaje para ofrecer desactivar.
        return HTTPException(
            409,
            "El usuario tiene operaciones asociadas y no puede eliminarse. "
            "Puede desactivarlo en su lugar.",
        )
    return HTTPException(400, "No se pudo completar la operación.")


@router.get(
    "/roles",
    response_model=list[RolOut],
    summary="CU-03 Roles asignables",
    dependencies=[Depends(requiere_roles("ADMINISTRADOR"))],
)
def listar_roles(db: DbSession) -> list[RolOut]:
    """Roles que se pueden asignar, indicando cuáles exigen sucursal."""
    return service.listar_roles(db)


@admin_router.get("", response_model=PaginaUsuarios, summary="CU-03 Listar usuarios")
def listar_usuarios(
    db: DbSession,
    busqueda: Annotated[str | None, Query(max_length=120)] = None,
    rol: Annotated[str | None, Query(max_length=30)] = None,
    activo: Annotated[bool | None, Query()] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamano: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginaUsuarios:
    """Listado paginado con búsqueda por nombre o correo y filtros (paso 2)."""
    return service.listar_usuarios(
        db, busqueda=busqueda, rol=rol, activo=activo, pagina=pagina, tamano=tamano
    )


@admin_router.post(
    "",
    response_model=UsuarioResumenOut,
    status_code=status.HTTP_201_CREATED,
    summary="CU-03 Crear usuario",
    responses={409: {"description": "El correo ya está registrado (excepción E1)."}},
)
def crear_usuario(datos: UsuarioCrearIn, db: DbSession) -> UsuarioResumenOut:
    """Crea una cuenta con su rol y, si corresponde, su sucursal."""
    try:
        return service.crear_usuario(db, datos)
    except service.CorreoYaRegistrado:
        raise HTTPException(409, "Ya existe una cuenta con ese correo electrónico.")
    except service.DocumentoYaRegistrado:
        raise HTTPException(409, "Ya existe un empleado con ese documento.")
    except service.ErrorDeGestion as error:
        raise _traducir(error)


@admin_router.get(
    "/{usuario_id}", response_model=UsuarioResumenOut, summary="CU-03 Ver un usuario"
)
def obtener_usuario(usuario_id: int, db: DbSession) -> UsuarioResumenOut:
    try:
        return service.obtener_usuario(db, usuario_id)
    except service.ErrorDeGestion as error:
        raise _traducir(error)


@admin_router.patch(
    "/{usuario_id}", response_model=UsuarioResumenOut, summary="CU-03 Editar usuario"
)
def editar_usuario(
    usuario_id: int, datos: UsuarioEditarIn, db: DbSession
) -> UsuarioResumenOut:
    """Modifica los datos de una cuenta.

    La contraseña solo cambia si se envía una nueva (flujo alternativo 3a).
    """
    try:
        return service.editar_usuario(db, usuario_id, datos)
    except service.CorreoYaRegistrado:
        raise HTTPException(409, "Ya existe una cuenta con ese correo electrónico.")
    except service.ErrorDeGestion as error:
        raise _traducir(error)


@admin_router.patch(
    "/{usuario_id}/estado",
    response_model=UsuarioResumenOut,
    summary="CU-03 Activar o desactivar",
)
def cambiar_estado(
    usuario_id: int, datos: CambioEstadoIn, db: DbSession, usuario: Usuario
) -> UsuarioResumenOut:
    """Cambia el estado de la cuenta; al desactivar revoca sus sesiones."""
    try:
        return service.cambiar_estado(
            db, usuario_id, datos.activo, solicitante_id=usuario.id
        )
    except service.ErrorDeGestion as error:
        raise _traducir(error)


@admin_router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-03 Eliminar usuario",
)
def eliminar_usuario(usuario_id: int, db: DbSession, usuario: Usuario) -> None:
    """Elimina la cuenta, solo si no tiene operaciones asociadas (flujo 3c)."""
    try:
        service.eliminar_usuario(db, usuario_id, solicitante_id=usuario.id)
    except service.ErrorDeGestion as error:
        raise _traducir(error)


# TODO CU-04: declarar sus endpoints.
