"""
P2 - Organizacion  |  CU-07 Gestionar proveedores  |  capa: esquemas

Ciclo de desarrollo: 1

---- POR QUE EL CU-07 VIVE EN ARCHIVOS PROPIOS ----

El paquete P2 realiza CU-05, CU-06 y CU-07, y la convencion del proyecto es un
archivo por capa y por paquete. El CU-07 se aparta de eso a proposito: el CU-06
lo esta implementando Karen al mismo tiempo, sobre los mismos cuatro archivos.
Si los dos escribieramos ahi, cada capa daria conflicto al mergear --- en los
imports, en el `_traducir` del router y en el comentario TODO del final, que es
justo donde los dos anadiriamos.

Con archivos separados las dos ramas no comparten ni una linea, salvo dos en
`app/main.py` que el CU-06 no necesita tocar.

Una vez mergeadas las dos ramas esto se puede consolidar en los archivos por
capa, si se prefiere la convencion original. Es una decision de coordinacion,
no de arquitectura: el paquete sigue siendo uno solo.
"""
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.modules.seguridad.schemas import CONTRASENA_LONGITUD_MINIMA

#: Misma exigencia de fortaleza que CU-01 y CU-03, que realiza el RNF01. Se
#: repiten aqui las expresiones porque en seguridad.schemas son privadas; lo
#: que se comparte es la constante de longitud, que es la que podria cambiar.
_TIENE_LETRA = re.compile(r"[A-Za-z]")
_TIENE_DIGITO = re.compile(r"\d")

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Las longitudes maximas replican el esquema fisico de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.2.


class ProveedorOut(BaseModel):
    """Fila del listado de proveedores (paso 2 del flujo principal).

    `tiene_acceso` y `correo_acceso` describen el vinculo con un usuario del
    sistema, que es el flujo alternativo 3c. Van aparte de `correo`, que es el
    correo de contacto comercial de la empresa: son dos cosas distintas y
    mezclarlas obligaria a que el contacto pudiera iniciar sesion.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    razon_social: str
    identificacion_tributaria: str
    contacto: str | None = None
    telefono: str | None = None
    correo: EmailStr | None = None
    direccion: str | None = None
    activo: bool

    usuario_id: int | None = None
    tiene_acceso: bool = False
    correo_acceso: EmailStr | None = None


class ProveedorCrearIn(BaseModel):
    """Alta de proveedor (paso 4 del flujo principal).

    `correo` es EmailStr: la excepcion E2 pide rechazar un formato invalido, y
    esto lo resuelve devolviendo un 422 que senala el campo.
    """

    razon_social: str = Field(min_length=1, max_length=120)
    identificacion_tributaria: str = Field(min_length=1, max_length=30)
    contacto: str | None = Field(default=None, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)
    correo: EmailStr | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=200)
    activo: bool = True

    @field_validator("razon_social", "identificacion_tributaria", "contacto",
                     "telefono", "direccion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        """Recorta los extremos; el texto vacio significa ausencia de dato."""
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str | None) -> str | None:
        return valor.strip().lower() if valor else None


class ProveedorEditarIn(BaseModel):
    """Edicion de proveedor (flujo alternativo 3a). Solo viaja lo que cambia."""

    razon_social: str | None = Field(default=None, min_length=1, max_length=120)
    identificacion_tributaria: str | None = Field(
        default=None, min_length=1, max_length=30
    )
    contacto: str | None = Field(default=None, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)
    correo: EmailStr | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=200)

    @field_validator("razon_social", "identificacion_tributaria", "contacto",
                     "telefono", "direccion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str | None) -> str | None:
        return valor.strip().lower() if valor else None


class CambioEstadoProveedorIn(BaseModel):
    """Alta o baja de un proveedor (flujo alternativo 3b).

    Dar de baja no borra la ficha: sus productos historicos se conservan, que
    es lo que pide el caso de uso.
    """

    activo: bool


class AccesoProveedorIn(BaseModel):
    """Habilitar acceso al Proveedor (flujo alternativo 3c).

    Crea un usuario con rol PROVEEDOR vinculado a la ficha. El correo de acceso
    se pide aparte del de contacto: el de contacto puede ser un buzon
    compartido, y el de acceso identifica a una persona que inicia sesion.
    """

    correo: EmailStr = Field(max_length=120)
    contrasena: str = Field(min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128)
    nombres: str = Field(min_length=1, max_length=80)
    apellidos: str = Field(min_length=1, max_length=80)

    @field_validator("nombres", "apellidos")
    @classmethod
    def _recortar(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str) -> str:
        """Misma normalizacion que en el registro de CU-01.

        La unicidad de usuario.correo se aplica con un UNIQUE, que distingue
        mayusculas; sin esto, 'A@x.com' y 'a@x.com' serian dos cuentas.
        """
        return valor.strip().lower()

    @field_validator("contrasena")
    @classmethod
    def _contrasena_fuerte(cls, valor: str) -> str:
        """Exige al menos una letra y un digito, igual que CU-01 y CU-03."""
        if not _TIENE_LETRA.search(valor) or not _TIENE_DIGITO.search(valor):
            raise ValueError(
                "La contraseña debe incluir al menos una letra y un número."
            )
        return valor
