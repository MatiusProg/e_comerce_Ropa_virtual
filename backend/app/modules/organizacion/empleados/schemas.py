"""
P2 - Organizacion / CU-06  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 1
Caso de uso: CU-06 Gestionar empleados
"""
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
#
# Las longitudes maximas replican el esquema fisico de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.2.

#: Los dos unicos cargos que admite la tabla. El CHECK
#: ck_empleado_cargo los aplica en la base; aqui se rechazan antes, para
#: devolver un 422 que nombre el campo en vez de un error de PostgreSQL.
CARGOS = ("ENCARGADO", "CAJERO")

#: A cada cargo le corresponde un rol del sistema. Es lo que hace que el
#: ambito de sucursal del token coincida con la sucursal del empleado.
ROL_DE_CARGO = {"ENCARGADO": "ENCARGADO", "CAJERO": "CAJERO"}

#: Replica CONTRASENA_LONGITUD_MINIMA de seguridad/schemas.py. No se importa
#: para no invertir la direccion de dependencia entre paquetes (P2 -> P1 esta
#: permitido, pero un esquema no deberia depender de otro esquema).
CONTRASENA_LONGITUD_MINIMA = 8

_TIENE_LETRA = re.compile(r"[A-Za-z]")
_TIENE_DIGITO = re.compile(r"\d")


class EmpleadoOut(BaseModel):
    """Fila del listado de empleados (paso 2 del flujo principal)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    nombres: str
    apellidos: str
    correo: EmailStr
    documento: str
    telefono: str | None
    cargo: str
    sucursal_id: int
    sucursal: str
    ciudad: str
    fecha_ingreso: date
    fecha_baja: date | None
    #: Un empleado esta de alta mientras no tenga fecha de baja. Viaja
    #: calculado para que la interfaz no tenga que deducirlo.
    activo: bool
    #: Estado de la cuenta. Puede diferir de `activo`: dar de baja al empleado
    #: desactiva su usuario, pero un usuario desactivado por CU-03 no da de
    #: baja al empleado.
    usuario_activo: bool


class UsuarioVinculableOut(BaseModel):
    """Usuario sin ficha de empleado, candidato del flujo alternativo 3c."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    correo: EmailStr
    nombres: str
    apellidos: str
    rol: str


class _DatosDeEmpleado(BaseModel):
    """Campos comunes al alta y a la edicion."""

    documento: str = Field(min_length=1, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    cargo: str = Field(min_length=1, max_length=30)
    sucursal_id: int
    fecha_ingreso: date

    @field_validator("documento")
    @classmethod
    def _documento_limpio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El documento no puede quedar vacío.")
        return valor

    @field_validator("telefono")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("cargo")
    @classmethod
    def _cargo_valido(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in CARGOS:
            raise ValueError("El cargo debe ser Encargado de Sucursal o Cajero.")
        return valor


class EmpleadoCrearIn(_DatosDeEmpleado):
    """Alta de un empleado (pasos 4 a 7) y flujo alternativo 3c.

    El caso de uso admite dos caminos y este esquema los cubre a los dos:

      - **usuario nuevo**: se envian nombres, apellidos, correo y contrasena.
      - **flujo 3c, usuario existente**: se envia `usuario_id` y ninguno de
        los anteriores.

    Son excluyentes. Aceptar los dos a la vez obligaria a decidir en el
    servicio cual gana, y esa ambiguedad no la resuelve nadie bien.
    """

    usuario_id: int | None = None
    nombres: str | None = Field(default=None, min_length=1, max_length=80)
    apellidos: str | None = Field(default=None, min_length=1, max_length=80)
    correo: EmailStr | None = Field(default=None, max_length=120)
    contrasena: str | None = Field(
        default=None, min_length=CONTRASENA_LONGITUD_MINIMA, max_length=128
    )

    @field_validator("nombres", "apellidos")
    @classmethod
    def _recortar_nombre(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("correo")
    @classmethod
    def _correo_en_minusculas(cls, valor: str | None) -> str | None:
        """Normaliza el correo, por el mismo motivo que CU-01 y CU-03.

        La unicidad de usuario.correo la aplica un UNIQUE, que distingue
        mayusculas. Sin normalizar, 'Ana@x.com' y 'ana@x.com' serian dos
        cuentas distintas.
        """
        return valor.strip().lower() if valor else None

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

    @model_validator(mode="after")
    def _un_camino_u_otro(self) -> "EmpleadoCrearIn":
        datos_de_cuenta = (self.nombres, self.apellidos, self.correo, self.contrasena)

        if self.usuario_id is not None:
            if any(d is not None for d in datos_de_cuenta):
                raise ValueError(
                    "Indique un usuario existente o los datos de una cuenta nueva, "
                    "no ambas cosas."
                )
            return self

        if any(d is None for d in datos_de_cuenta):
            raise ValueError(
                "Para crear la cuenta hacen falta nombres, apellidos, correo y "
                "contraseña."
            )
        return self


class EmpleadoEditarIn(BaseModel):
    """Edicion y reasignacion de sucursal (flujo alternativo 3a).

    Todos los campos son opcionales: solo se modifica lo que llega. El cargo y
    la sucursal se pueden cambiar, y ambos arrastran al usuario vinculado --
    el rol y el ambito viajan en el token.
    """

    documento: str | None = Field(default=None, min_length=1, max_length=20)
    telefono: str | None = Field(default=None, max_length=20)
    cargo: str | None = Field(default=None, min_length=1, max_length=30)
    sucursal_id: int | None = None
    fecha_ingreso: date | None = None
    nombres: str | None = Field(default=None, min_length=1, max_length=80)
    apellidos: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("documento", "nombres", "apellidos")
    @classmethod
    def _recortar_obligatorio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("telefono")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("cargo")
    @classmethod
    def _cargo_valido(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        valor = valor.strip().upper()
        if valor not in CARGOS:
            raise ValueError("El cargo debe ser Encargado de Sucursal o Cajero.")
        return valor


class BajaEmpleadoIn(BaseModel):
    """Baja de un empleado (flujo alternativo 3b)."""

    #: Si no se indica, el servicio usa la fecha de hoy. El CHECK
    #: ck_empleado_fechas exige que no sea anterior al ingreso.
    fecha_baja: date | None = None
