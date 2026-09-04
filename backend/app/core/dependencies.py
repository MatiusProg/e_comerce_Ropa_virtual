"""Dependencias compartidas de FastAPI: sesion de base de datos y autorizacion.

Toda ruta protegida declara aqui su exigencia de rol. La regla del sistema es
que el ambito de datos de un Encargado o un Cajero esta limitado a SU sucursal,
y ese ambito viaja en el token, no en el cuerpo de la peticion.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decodificar_token
from app.db.session import get_db
# Se importa con alias a proposito: mas abajo este modulo define
# `Usuario = Annotated[UsuarioActual, ...]` como atajo para las rutas, y ese
# nombre pisaria al modelo de SQLAlchemy.
from app.modules.seguridad.models import SesionToken
from app.modules.seguridad.models import Usuario as UsuarioDB

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


class UsuarioActual:
    """Identidad resuelta a partir del token y verificada contra la base."""

    def __init__(
        self,
        usuario_id: int,
        rol: str,
        sucursal_id: int | None,
        jti: uuid.UUID,
    ):
        self.id = usuario_id
        self.rol = rol
        self.sucursal_id = sucursal_id
        # El jti se conserva para que el cierre de sesion sepa que fila de
        # sesion_token revocar.
        self.jti = jti

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UsuarioActual id={self.id} rol={self.rol} sucursal={self.sucursal_id}>"


def _rechazar(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_usuario_actual(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> UsuarioActual:
    """Resuelve el usuario del token o rechaza la peticion.

    No alcanza con que la firma del token sea valida. Un token correctamente
    firmado puede corresponder a una sesion ya cerrada o a una cuenta que fue
    desactivada despues de emitirlo, y en ambos casos debe dejar de servir de
    inmediato. Por eso esta dependencia consulta la base:

      1. la firma y la vigencia del token
      2. que la sesion exista y NO este revocada
      3. que el usuario siga activo

    Omitir el paso 2 convierte a sesion_token en un adorno: cerrar sesion no
    cerraria nada.
    """
    datos = decodificar_token(token)
    if datos is None or datos.get("tipo") != "access":
        raise _rechazar("Su sesión expiró. Por favor, inicie sesión nuevamente.")

    try:
        jti = uuid.UUID(datos["jti"])
    except (KeyError, ValueError, TypeError):
        # Token viejo, emitido antes de que existiera el jti, o manipulado.
        raise _rechazar("Su sesión no es válida. Inicie sesión nuevamente.")

    sesion = db.scalar(select(SesionToken).where(SesionToken.jti == jti))
    if sesion is None or sesion.revocado_en is not None:
        raise _rechazar("Su sesión fue cerrada. Inicie sesión nuevamente.")

    usuario_activo = db.scalar(
        select(UsuarioDB.activo).where(UsuarioDB.id == int(datos["sub"]))
    )
    if not usuario_activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Su cuenta fue desactivada. Contacte al administrador.",
        )

    return UsuarioActual(
        usuario_id=int(datos["sub"]),
        rol=datos["rol"],
        sucursal_id=datos.get("sucursal_id"),
        jti=jti,
    )


Usuario = Annotated[UsuarioActual, Depends(get_usuario_actual)]


def requiere_roles(*roles: str):
    """Fabrica una dependencia que exige que el usuario tenga uno de los roles.

    Uso:
        @router.post("/", dependencies=[Depends(requiere_roles("ADMINISTRADOR"))])
    """

    def _verificar(usuario: Usuario) -> UsuarioActual:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta operación.",
            )
        return usuario

    return _verificar


def verificar_ambito_sucursal(usuario: UsuarioActual, sucursal_id: int) -> None:
    """Impide que un usuario de sucursal opere sobre otra sucursal.

    El Administrador queda exento: su ambito es toda la red.
    """
    if usuario.rol == "ADMINISTRADOR":
        return
    if usuario.sucursal_id != sucursal_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puede operar sobre su propia sucursal.",
        )
