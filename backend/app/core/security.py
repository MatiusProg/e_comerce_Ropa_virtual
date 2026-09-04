"""Primitivas de seguridad: hash de contrasenas y tokens JWT (RNF01).

Este modulo no conoce la base de datos ni FastAPI. Solo transforma datos.
La verificacion de identidad contra la base vive en app/core/dependencies.py.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Contrasenas ---------------------------------------------------------

def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro."""
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verifica una contrasena en claro contra su hash almacenado."""
    return _pwd.verify(password, hashed)


# --- Tokens --------------------------------------------------------------

class TokenEmitido(NamedTuple):
    """Un token recien emitido, con lo que hace falta para registrarlo.

    El `jti` y la expiracion se devuelven aparte porque el servicio los guarda
    en la fila de `sesion_token`: es esa fila la que permite revocar el token
    antes de que expire solo.
    """

    token: str
    jti: uuid.UUID
    expira_en: datetime


def crear_access_token(
    *,
    usuario_id: int,
    rol: str,
    sucursal_id: int | None = None,
    vigencia: timedelta | None = None,
) -> TokenEmitido:
    """Emite un token de acceso.

    El token porta el identificador del usuario, su rol y -- cuando aplica --
    la sucursal a la que pertenece. El ambito de sucursal es lo que impide
    que un Encargado opere sobre una sucursal que no es la suya.

    Ademas lleva un `jti` unico. Sin el, un token no se puede relacionar con
    ninguna fila de `sesion_token` y por lo tanto NO SE PUEDE REVOCAR: cerrar
    sesion no invalidaria nada y el token seguiria sirviendo hasta expirar.
    """
    ahora = datetime.now(timezone.utc)
    expiracion = ahora + (
        vigencia or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti = uuid.uuid4()
    payload: dict[str, Any] = {
        "sub": str(usuario_id),
        "rol": rol,
        "sucursal_id": sucursal_id,
        "jti": str(jti),
        "iat": ahora,
        "exp": expiracion,
        "tipo": "access",
    }
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return TokenEmitido(token=token, jti=jti, expira_en=expiracion)


def decodificar_token(token: str) -> dict[str, Any] | None:
    """Devuelve el contenido del token, o None si es invalido o expiro."""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None
