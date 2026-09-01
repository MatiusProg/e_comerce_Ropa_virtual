"""Dependencias compartidas de FastAPI: sesion de base de datos y autorizacion.

Toda ruta protegida declara aqui su exigencia de rol. La regla del sistema es
que el ambito de datos de un Encargado o un Cajero esta limitado a SU sucursal,
y ese ambito viaja en el token, no en el cuerpo de la peticion.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decodificar_token
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


class UsuarioActual:
    """Identidad resuelta a partir del token, sin tocar la base de datos."""

    def __init__(self, usuario_id: int, rol: str, sucursal_id: int | None):
        self.id = usuario_id
        self.rol = rol
        self.sucursal_id = sucursal_id

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UsuarioActual id={self.id} rol={self.rol} sucursal={self.sucursal_id}>"


def get_usuario_actual(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UsuarioActual:
    """Resuelve el usuario del token o rechaza la peticion."""
    datos = decodificar_token(token)
    if datos is None or datos.get("tipo") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Su sesion expiro. Por favor, inicie sesion nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UsuarioActual(
        usuario_id=int(datos["sub"]),
        rol=datos["rol"],
        sucursal_id=datos.get("sucursal_id"),
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
                detail="No tiene permisos para realizar esta operacion.",
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
