"""
P1 - Seguridad y Usuarios  |  capa: router (HTTP, validacion y autorizacion)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import DbSession, Usuario
from app.modules.seguridad import service
from app.modules.seguridad.schemas import (
    ClienteRegistradoOut,
    ClienteRegistroIn,
    LoginIn,
    TokenOut,
    UsuarioAutenticadoOut,
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


# TODO CU-03 y CU-04: declarar sus endpoints.
