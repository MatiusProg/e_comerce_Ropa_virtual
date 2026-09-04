"""
P2 - Organizacion  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 1

Casos de uso que realiza este paquete:
  CU-05 Gestionar ciudades y sucursales
  CU-06 Gestionar empleados
  CU-07 Gestionar proveedores
"""
from datetime import time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Por cada operacion se define su esquema de entrada (Create/Update)
# y su esquema de salida (Read).
#
# Las longitudes maximas replican el esquema fisico de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.2.


# --- CU-05 Gestionar ciudades y sucursales -------------------------------

#: Capacidad minima de vestidores. La excepcion E3 pide rechazar un valor no
#: positivo; la base tambien lo impide con el check `ck_sucursal_capacidad`,
#: pero validarlo aqui devuelve un 422 que senala el campo en vez de un 500.
CAPACIDAD_VESTIDORES_MINIMA = 1


class CiudadOut(BaseModel):
    """Una ciudad del listado, con cuantas sucursales tiene.

    Los contadores viajan porque la interfaz los necesita para decidir si
    ofrecer la baja: una ciudad con sucursales activas no se puede eliminar
    (excepcion E2), y conviene decirlo antes de que lo intenten.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    departamento: str
    sucursales: int = 0
    sucursales_activas: int = 0


class CiudadCrearIn(BaseModel):
    """Alta de ciudad (flujo alternativo 3a)."""

    nombre: str = Field(min_length=1, max_length=60)
    departamento: str = Field(min_length=1, max_length=60)

    @field_validator("nombre", "departamento")
    @classmethod
    def _recortar(cls, valor: str) -> str:
        return valor.strip()


class CiudadEditarIn(BaseModel):
    """Edicion de ciudad (flujo alternativo 3a). Solo viaja lo que cambia."""

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    departamento: str | None = Field(default=None, min_length=1, max_length=60)

    @field_validator("nombre", "departamento")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class SucursalOut(BaseModel):
    """Fila del listado de sucursales (paso 2 del flujo principal).

    Incluye `id`, `nombre` y `ciudad`, que es lo unico que necesita el selector
    del formulario de CU-03. Ese endpoint es el mismo: se extendio en vez de
    declarar otro con la misma ruta (ver 6.11.2 de las decisiones tecnicas).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    ciudad_id: int
    ciudad: str
    direccion: str
    telefono: str | None = None
    horario_apertura: time
    horario_cierre: time
    capacidad_vestidores: int
    activa: bool


class _SucursalHorario(BaseModel):
    """Parte comun del alta y la edicion: la coherencia del horario.

    Se comprueba en los dos esquemas porque la base tambien lo exige con el
    check `ck_sucursal_horario`, y sin esta validacion una edicion que invierta
    los horarios reventaria con un error de PostgreSQL en vez de un 422.
    """

    @model_validator(mode="after")
    def _cierre_despues_de_apertura(self):
        apertura = getattr(self, "horario_apertura", None)
        cierre = getattr(self, "horario_cierre", None)
        if apertura is not None and cierre is not None and cierre <= apertura:
            raise ValueError(
                "El horario de cierre debe ser posterior al de apertura."
            )
        return self


class SucursalCrearIn(_SucursalHorario):
    """Alta de sucursal (paso 4 del flujo principal)."""

    ciudad_id: int
    nombre: str = Field(min_length=1, max_length=80)
    direccion: str = Field(min_length=1, max_length=200)
    telefono: str | None = Field(default=None, max_length=20)
    horario_apertura: time
    horario_cierre: time
    capacidad_vestidores: int = Field(
        default=CAPACIDAD_VESTIDORES_MINIMA, ge=CAPACIDAD_VESTIDORES_MINIMA
    )
    activa: bool = True

    @field_validator("nombre", "direccion", "telefono")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class SucursalEditarIn(_SucursalHorario):
    """Edicion de sucursal (flujo alternativo 3b). Solo viaja lo que cambia.

    El horario se valida solo cuando llegan los dos extremos; si viene uno
    solo, la comprobacion contra el valor guardado la hace el servicio, que es
    quien conoce la fila.
    """

    ciudad_id: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=80)
    direccion: str | None = Field(default=None, min_length=1, max_length=200)
    telefono: str | None = Field(default=None, max_length=20)
    horario_apertura: time | None = None
    horario_cierre: time | None = None
    capacidad_vestidores: int | None = Field(
        default=None, ge=CAPACIDAD_VESTIDORES_MINIMA
    )

    @field_validator("nombre", "direccion", "telefono")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        """Recorta los extremos; el texto vacio significa borrar el dato.

        Solo el telefono admite quedar en nulo: nombre y direccion son
        obligatorios, y para ellos el minimo de longitud ya lo impide antes.
        """
        if valor is None:
            return None
        return valor.strip() or None


class CambioEstadoSucursalIn(BaseModel):
    """Alta o baja de una sucursal (flujo alternativo 3c).

    Dar de baja no borra: la sucursal deja de ofrecerse para reservas y
    compras, pero se conserva para la trazabilidad historica.
    """

    activa: bool


# TODO CU-06 y CU-07: definir el resto de los esquemas.
