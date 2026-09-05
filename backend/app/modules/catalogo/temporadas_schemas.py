"""
P3 - Catalogo  |  CU-09 Gestionar temporadas y colecciones  |  capa: esquemas

Ciclo de desarrollo: 1

---- POR QUE EL CU-09 VIVE EN ARCHIVOS PROPIOS ----

El paquete P3 realiza CU-08 y CU-09 en este ciclo, y Karen esta implementando
el CU-08 en paralelo sobre schemas.py, repository.py, service.py y router.py.
Si los dos escribieramos ahi, las cuatro capas darian conflicto al mergear.
Es la misma separacion que se uso para CU-06 y CU-07 en el paquete P2, y que
salio bien: las dos ramas no compartieron ni una linea.

El paquete sigue siendo uno solo; esto es coordinacion, no arquitectura.
"""
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.
# Las longitudes maximas replican el esquema fisico de
# docs/entregas/ciclo-1/cap-2-3-analisis-y-diseno.md seccion 3.3.2.


# --- Temporadas ----------------------------------------------------------

class TemporadaOut(BaseModel):
    """Fila del listado de temporadas (paso 2 del flujo principal).

    `vigente` NO es una columna: se calcula como "esta abierta y hoy cae
    dentro de su rango". Guardarla obligaria a un proceso que la apague sola al
    pasar la fecha de fin, y a que ese proceso nunca fallara. Calculada, no
    puede quedar desactualizada.

    Los recuentos de colecciones viajan porque la interfaz los necesita para
    decidir si ofrecer la eliminacion: una temporada con colecciones no se
    puede borrar (excepcion E3), y conviene decirlo antes de que lo intenten.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None = None
    fecha_inicio: date
    fecha_fin: date
    activa: bool
    vigente: bool = False
    colecciones: int = 0
    colecciones_activas: int = 0


class _RangoDeFechas(BaseModel):
    """Excepcion E1: la fecha de fin tiene que ser posterior a la de inicio.

    La base tambien lo exige con el check `ck_temporada_rango`, pero validarlo
    aqui devuelve un 422 que senala el campo en vez de un 500. Comprueba solo
    cuando llegan las dos fechas; si viene una sola, la comparacion contra el
    valor guardado la hace el servicio, que es quien conoce la fila.
    """

    @model_validator(mode="after")
    def _fin_despues_de_inicio(self):
        inicio = getattr(self, "fecha_inicio", None)
        fin = getattr(self, "fecha_fin", None)
        if inicio is not None and fin is not None and fin <= inicio:
            raise ValueError(
                "La fecha de fin debe ser posterior a la de inicio."
            )
        return self


class _ConfirmacionDeSolapamiento(BaseModel):
    """Excepcion E2: el solapamiento advierte, no rechaza.

    El caso de uso dice que si el rango se superpone con otra temporada activa
    el sistema "advierte y pide confirmacion explicita antes de guardar". Por
    eso no es un error duro: el primer intento devuelve 409 con los nombres de
    las temporadas que se cruzan, y la interfaz reenvia con este campo en true.

    Va por separado del rango porque son cosas distintas: E1 nunca se puede
    confirmar --- unas fechas invertidas no tienen lectura valida --- y E2 si.
    """

    confirmar_solapamiento: bool = False


class TemporadaCrearIn(_RangoDeFechas, _ConfirmacionDeSolapamiento):
    """Alta de temporada (paso 4 del flujo principal)."""

    nombre: str = Field(min_length=1, max_length=60)
    descripcion: str | None = Field(default=None, max_length=200)
    fecha_inicio: date
    fecha_fin: date
    activa: bool = True

    @field_validator("nombre", "descripcion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class TemporadaEditarIn(_RangoDeFechas, _ConfirmacionDeSolapamiento):
    """Edicion de temporada (flujo alternativo 3a). Solo viaja lo que cambia."""

    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    descripcion: str | None = Field(default=None, max_length=200)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None

    @field_validator("nombre", "descripcion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class CambioEstadoTemporadaIn(BaseModel):
    """Cerrar o reabrir una temporada (flujo alternativo 3b).

    Cerrarla no borra nada: sus productos siguen siendo consultables, solo
    dejan de considerarse de temporada vigente.
    """

    activa: bool
    #: Reabrir una temporada cerrada puede volver a cruzarla con otra abierta,
    #: asi que tambien pasa por la advertencia de E2.
    confirmar_solapamiento: bool = False


# --- Colecciones (flujo alternativo 1a) ----------------------------------

class ColeccionOut(BaseModel):
    """Fila del listado de colecciones, con el nombre de su temporada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    temporada_id: int
    temporada: str
    nombre: str
    descripcion: str | None = None
    activa: bool


class ColeccionCrearIn(BaseModel):
    """Alta de coleccion (flujo alternativo 1a)."""

    temporada_id: int
    nombre: str = Field(min_length=1, max_length=60)
    descripcion: str | None = Field(default=None, max_length=200)
    activa: bool = True

    @field_validator("nombre", "descripcion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class ColeccionEditarIn(BaseModel):
    """Edicion de coleccion (flujo alternativo 3a)."""

    temporada_id: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    descripcion: str | None = Field(default=None, max_length=200)

    @field_validator("nombre", "descripcion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class CambioEstadoColeccionIn(BaseModel):
    """Dar de baja o reactivar una coleccion.

    La coleccion no se elimina: es la misma politica que sucursal y proveedor
    --- se conserva por trazabilidad --- y ademas en el Ciclo 2 va a tener
    productos colgando.
    """

    activa: bool
