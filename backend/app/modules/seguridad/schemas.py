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

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

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


# --- CU-04 Gestionar perfil del cliente ----------------------------------
# El perfil es del usuario autenticado. Ningun esquema de entrada lleva
# cliente_id ni usuario_id: esos salen del token. Si viajaran en el cuerpo,
# cualquiera podria editar el perfil de otro cambiando un numero.


class DireccionOut(BaseModel):
    """Una direccion de entrega del cliente (paso 2)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ciudad_id: int
    ciudad: str
    alias: str
    direccion: str
    referencia: str | None
    predeterminada: bool


class PerfilOut(BaseModel):
    """El perfil completo que muestra el paso 2 del flujo principal.

    Las categorias preferidas que menciona ese paso quedan fuera del Ciclo 1:
    dependen de CU-08, que todavia no crea ninguna categoria. Ver la seccion
    6.11.3 de docs/06-decisiones-tecnicas.md.
    """

    nombres: str
    apellidos: str
    correo: EmailStr
    documento: str | None
    telefono: str | None
    talla_superior: str | None
    talla_inferior: str | None
    talla_calzado: str | None
    direcciones: list[DireccionOut]


class PerfilEditarIn(BaseModel):
    """Datos personales y tallas habituales que el Cliente modifica (paso 3).

    Todos los campos son opcionales, pero la ausencia y el vaciado son cosas
    distintas: no enviar `telefono` lo deja como esta; enviarlo vacio lo borra.
    Por eso los validadores devuelven None ante una cadena vacia y el servicio
    distingue ambos casos con `model_fields_set`.
    """

    nombres: str | None = Field(default=None, min_length=1, max_length=80)
    apellidos: str | None = Field(default=None, min_length=1, max_length=80)
    correo: EmailStr | None = Field(default=None, max_length=120)
    documento: str | None = Field(default=None, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    talla_superior: str | None = Field(default=None, max_length=10)
    talla_inferior: str | None = Field(default=None, max_length=10)
    talla_calzado: str | None = Field(default=None, max_length=10)

    @field_validator(
        "nombres",
        "apellidos",
        "documento",
        "telefono",
        "talla_superior",
        "talla_inferior",
        "talla_calzado",
    )
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str | None) -> str | None:
        """Normaliza el correo, por el mismo motivo que en CU-01.

        Sin esto la excepcion E2 (correo en uso) no se disparia para un par que
        solo difiere en mayusculas.
        """
        return valor.strip().lower() if valor else None


class DireccionIn(BaseModel):
    """Alta de una direccion de entrega (flujo alternativo 3a)."""

    ciudad_id: int
    alias: str = Field(min_length=1, max_length=40)
    direccion: str = Field(min_length=1, max_length=200)
    referencia: str | None = Field(default=None, max_length=200)
    predeterminada: bool = False

    @field_validator("alias", "direccion")
    @classmethod
    def _obligatorio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Este dato no puede quedar vacío.")
        return valor

    @field_validator("referencia")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class CambioContrasenaIn(BaseModel):
    """Cambio de contrasena del propio cliente (flujo alternativo 3c).

    El flujo pide la contrasena nueva DOS veces. La confirmacion se valida aqui
    y no solo en el navegador: un cliente de la API que no sea la web tambien
    tiene que respetar el caso de uso.
    """

    contrasena_actual: str = Field(min_length=1, max_length=128)
    contrasena_nueva: str = Field(
        min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128
    )
    contrasena_repetida: str = Field(min_length=1, max_length=128)

    @field_validator("contrasena_nueva")
    @classmethod
    def _contrasena_fuerte(cls, valor: str) -> str:
        if not _TIENE_LETRA.search(valor) or not _TIENE_DIGITO.search(valor):
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return valor

    @model_validator(mode="after")
    def _coinciden(self) -> "CambioContrasenaIn":
        if self.contrasena_nueva != self.contrasena_repetida:
            raise ValueError("Las dos contraseñas nuevas no coinciden.")
        if self.contrasena_nueva == self.contrasena_actual:
            raise ValueError("La contraseña nueva debe ser distinta de la actual.")
        return self
