"""
P1 - Seguridad y Usuarios  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-01 Registrar cliente
  CU-02 Iniciar y cerrar sesion
  CU-03 Gestionar usuarios y roles
  CU-04 Gestionar perfil del cliente
"""
import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).
#
# Las longitudes maximas replican el esquema fisico de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.2. Validar aqui
# evita que un dato demasiado largo llegue a la base y reviente con un error de
# PostgreSQL en vez de con un 422 explicando cual es el campo.


# --- CU-01 Registrar cliente ---------------------------------------------

#: Longitud minima de contrasena. El paso 4 del flujo principal de CU-01 exige
#: verificar "la fortaleza de la contrasena"; esta es la regla concreta que se
#: adopta para ello, y realiza el RNF01.
CONTRASENA_LONGITUD_MINIMA = 8

_TIENE_LETRA = re.compile(r"[A-Za-z]")
_TIENE_DIGITO = re.compile(r"\d")


class ClienteRegistroIn(BaseModel):
    """Datos que envia el visitante en el formulario de registro (paso 3)."""

    nombres: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=80)
    documento: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    correo: EmailStr = Field(max_length=120)
    contrasena: str = Field(min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128)

    @field_validator("nombres", "apellidos", "documento", "telefono")
    @classmethod
    def _sin_espacios_sobrantes(cls, valor: str | None) -> str | None:
        """Recorta los extremos y convierte el texto vacio en ausencia de dato."""
        if valor is None:
            return None
        valor = valor.strip()
        return valor or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str) -> str:
        """Normaliza el correo.

        La unicidad de usuario.correo se aplica en la base con un UNIQUE, que
        distingue mayusculas de minusculas. Sin esta normalizacion,
        'Ana@x.com' y 'ana@x.com' serian dos cuentas distintas y la excepcion E1
        no se disparia nunca para ese par.
        """
        return valor.strip().lower()

    @field_validator("contrasena")
    @classmethod
    def _contrasena_fuerte(cls, valor: str) -> str:
        """Exige al menos una letra y un digito (paso 4 del flujo principal)."""
        if not _TIENE_LETRA.search(valor) or not _TIENE_DIGITO.search(valor):
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return valor


class ClienteRegistradoOut(BaseModel):
    """Confirmacion del registro (paso 8).

    No incluye el hash de la contrasena ni ningun token: CU-01 termina
    invitando a iniciar sesion, y la emision del token es CU-02.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    correo: EmailStr
    nombres: str
    apellidos: str
    rol: str


# --- CU-02 Iniciar y cerrar sesion ---------------------------------------

class LoginIn(BaseModel):
    """Credenciales que envia el usuario (paso 2 del flujo principal)."""

    correo: EmailStr = Field(max_length=120)
    contrasena: str = Field(min_length=1, max_length=128)

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str) -> str:
        """Misma normalizacion que en el registro, o el login no encontraria
        al usuario que se registro escribiendo su correo con mayusculas."""
        return valor.strip().lower()


class UsuarioAutenticadoOut(BaseModel):
    """Datos del usuario que la interfaz necesita para armar su menu."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    correo: EmailStr
    nombres: str
    apellidos: str
    rol: str
    sucursal_id: int | None = None


class TokenOut(BaseModel):
    """Respuesta del login.

    `expira_en` viaja para que la interfaz sepa cuando pedir credenciales de
    nuevo sin tener que abrir el token.
    """

    access_token: str
    token_type: str = "bearer"
    expira_en: datetime
    usuario: UsuarioAutenticadoOut


# --- CU-03 Gestionar usuarios y roles ------------------------------------

#: Roles cuyo ambito de datos es una sucursal concreta. Para ellos la sucursal
#: es obligatoria: sin ella el token no puede acotar sobre que puede operar
#: (excepcion E2).
ROLES_CON_SUCURSAL = frozenset({"ENCARGADO", "CAJERO"})


class RolOut(BaseModel):
    """Un rol asignable, para poblar el selector del formulario."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    exige_sucursal: bool = False


class UsuarioResumenOut(BaseModel):
    """Fila del listado de usuarios (paso 2 del flujo principal)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    correo: EmailStr
    nombres: str
    apellidos: str
    rol: str
    sucursal_id: int | None = None
    sucursal: str | None = None
    activo: bool
    creado_en: datetime


class PaginaUsuarios(BaseModel):
    """Listado paginado. El total viaja aparte para poder dibujar el paginador."""

    items: list[UsuarioResumenOut]
    total: int
    pagina: int
    tamano: int
    paginas: int


class UsuarioCrearIn(BaseModel):
    """Alta de usuario desde el panel de administración (paso 4).

    `documento` y `fecha_ingreso` no figuran en el paso 4 del caso de uso, pero
    la tabla `empleado` los exige NOT NULL, y es esa tabla la que guarda la
    sucursal. Sin ellos no se puede crear un Encargado ni un Cajero. Solo se
    piden cuando el rol lo requiere.
    """

    nombres: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=80)
    correo: EmailStr = Field(max_length=120)
    contrasena: str = Field(min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128)
    rol: str = Field(min_length=1, max_length=30)

    sucursal_id: int | None = None
    documento: str | None = Field(default=None, max_length=20)
    fecha_ingreso: date | None = None

    @field_validator("nombres", "apellidos", "documento")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str) -> str:
        return valor.strip().lower()

    @field_validator("rol")
    @classmethod
    def _rol_en_mayusculas(cls, valor: str) -> str:
        return valor.strip().upper()

    @field_validator("contrasena")
    @classmethod
    def _contrasena_fuerte(cls, valor: str) -> str:
        if not _TIENE_LETRA.search(valor) or not _TIENE_DIGITO.search(valor):
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return valor


class UsuarioEditarIn(BaseModel):
    """Edición de un usuario (flujo alternativo 3a).

    Todos los campos son opcionales: solo se modifica lo que llega. En
    particular, **la contraseña solo cambia si se envía una nueva**, tal como
    dice el flujo alternativo.
    """

    nombres: str | None = Field(default=None, min_length=1, max_length=80)
    apellidos: str | None = Field(default=None, min_length=1, max_length=80)
    correo: EmailStr | None = Field(default=None, max_length=120)
    contrasena: str | None = Field(
        default=None, min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128
    )
    rol: str | None = Field(default=None, min_length=1, max_length=30)
    sucursal_id: int | None = None

    @field_validator("nombres", "apellidos")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str | None) -> str | None:
        return valor.strip().lower() if valor else None

    @field_validator("rol")
    @classmethod
    def _rol_en_mayusculas(cls, valor: str | None) -> str | None:
        return valor.strip().upper() if valor else None

    @field_validator("contrasena")
    @classmethod
    def _contrasena_fuerte(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if not _TIENE_LETRA.search(valor) or not _TIENE_DIGITO.search(valor):
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return valor


class CambioEstadoIn(BaseModel):
    """Activación o desactivación de una cuenta (flujo alternativo 3b)."""

    activo: bool


# TODO CU-04: definir sus esquemas.
