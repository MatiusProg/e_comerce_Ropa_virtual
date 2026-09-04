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
                "La contrasena debe incluir al menos una letra y un numero."
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


# TODO CU-02, CU-03 y CU-04: definir sus esquemas.
