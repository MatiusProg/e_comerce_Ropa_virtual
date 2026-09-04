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

from app.core.dependencies import DbSession
from app.modules.seguridad import service
from app.modules.seguridad.schemas import ClienteRegistradoOut, ClienteRegistroIn

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
            detail="Ya existe una cuenta con ese correo electronico.",
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
            detail="El sistema no esta inicializado. Contacte al administrador.",
        )


# TODO CU-02, CU-03 y CU-04: declarar sus endpoints.
