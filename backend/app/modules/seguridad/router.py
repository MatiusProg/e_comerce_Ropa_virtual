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
    CambioContrasenaIn,
    CambioEstadoIn,
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


# --- CU-04 Gestionar perfil del cliente ----------------------------------
# Todo el perfil cuelga de un router propio que exige rol CLIENTE. Igual que en
# CU-03, la dependencia se declara una sola vez a nivel de router.
#
# Ningun endpoint recibe el identificador del cliente: sale del token. Un
# cliente no puede leer ni tocar el perfil de otro porque no existe forma de
# nombrarlo en la peticion.

perfil_router = APIRouter(
    prefix="/perfil",
    tags=["Seguridad · Perfil"],
    dependencies=[Depends(requiere_roles("CLIENTE"))],
    responses={
        401: {"description": "Falta el token o ya no es válido."},
        403: {"description": "El usuario no es Cliente."},
    },
)


def _traducir_perfil(error: service.ErrorDePerfil) -> HTTPException:
    """Convierte los errores de negocio de CU-04 en respuestas HTTP."""
    if isinstance(error, service.PerfilInexistente):
        return HTTPException(404, "Su cuenta no tiene una ficha de cliente asociada.")
    if isinstance(error, service.CiudadInexistente):
        return HTTPException(422, "La ciudad indicada no existe.")
    if isinstance(error, service.DireccionInexistente):
        return HTTPException(404, "La dirección indicada no existe.")
    if isinstance(error, service.ContrasenaActualIncorrecta):
        # Excepcion E1: el flujo devuelve el control al paso 3c.
        return HTTPException(422, "La contraseña actual no es correcta.")
    return HTTPException(400, "No se pudo completar la operación.")


@perfil_router.get("", response_model=PerfilOut, summary="CU-04 Ver mi perfil")
def obtener_perfil(db: DbSession, usuario: Usuario) -> PerfilOut:
    """Pasos 1 y 2: datos personales, tallas habituales y direcciones."""
    try:
        return service.obtener_perfil(db, usuario.id)
    except service.ErrorDePerfil as error:
        raise _traducir_perfil(error)


@perfil_router.patch(
    "",
    response_model=PerfilOut,
    summary="CU-04 Editar mi perfil",
    responses={409: {"description": "El correo ya está en uso (excepción E2)."}},
)
def editar_perfil(datos: PerfilEditarIn, db: DbSession, usuario: Usuario) -> PerfilOut:
    """Pasos 3 a 5: guarda los datos personales y las tallas habituales."""
    try:
        return service.editar_perfil(db, usuario.id, datos)
    except service.CorreoYaRegistrado:
        # Excepcion E2.
        raise HTTPException(409, "Ya existe una cuenta con ese correo electrónico.")
    except service.DocumentoYaRegistrado:
        raise HTTPException(409, "Ya existe un cliente con ese documento.")
    except service.ErrorDePerfil as error:
        raise _traducir_perfil(error)


@perfil_router.post(
    "/direcciones",
    response_model=list[DireccionOut],
    status_code=status.HTTP_201_CREATED,
    summary="CU-04 Agregar dirección",
)
def agregar_direccion(
    datos: DireccionIn, db: DbSession, usuario: Usuario
) -> list[DireccionOut]:
    """Flujo alternativo 3a. Devuelve la lista completa ya reordenada."""
    try:
        return service.agregar_direccion(db, usuario.id, datos)
    except service.ErrorDePerfil as error:
        raise _traducir_perfil(error)


@perfil_router.patch(
    "/direcciones/{direccion_id}/predeterminada",
    response_model=list[DireccionOut],
    summary="CU-04 Marcar dirección predeterminada",
)
def marcar_predeterminada(
    direccion_id: int, db: DbSession, usuario: Usuario
) -> list[DireccionOut]:
    """Deja esa dirección como la predeterminada y desmarca la anterior."""
    try:
        return service.marcar_direccion_predeterminada(db, usuario.id, direccion_id)
    except service.ErrorDePerfil as error:
        raise _traducir_perfil(error)


@perfil_router.delete(
    "/direcciones/{direccion_id}",
    response_model=list[DireccionOut],
    summary="CU-04 Eliminar dirección",
)
def eliminar_direccion(
    direccion_id: int, db: DbSession, usuario: Usuario
) -> list[DireccionOut]:
    """Flujo alternativo 3b. La confirmación previa la pide la interfaz."""
    try:
        return service.eliminar_direccion(db, usuario.id, direccion_id)
    except service.ErrorDePerfil as error:
        raise _traducir_perfil(error)


@perfil_router.put(
    "/contrasena",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="CU-04 Cambiar mi contraseña",
    responses={422: {"description": "La contraseña actual no es correcta (E1)."}},
)
def cambiar_contrasena(
    datos: CambioContrasenaIn, db: DbSession, usuario: Usuario
) -> None:
    """Flujo alternativo 3c.

    Al cambiar la contraseña se revocan las sesiones abiertas, incluida la que
    hizo esta petición: el cliente tiene que volver a iniciar sesión.
    """
    try:
        service.cambiar_contrasena(db, usuario.id, datos)
    except service.ErrorDePerfil as error:
        raise _traducir_perfil(error)
