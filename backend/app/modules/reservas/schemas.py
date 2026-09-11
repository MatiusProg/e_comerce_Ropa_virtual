"""
P6 - Reservas  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Implementado en este archivo: CU-22.

Los nombres y tipos replican el esquema fisico de la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md y las columnas de
`app/modules/reservas/models.py`.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.

#: Cuanto puede durar una franja de prueba, en minutos.
#:
#: No es configurable como la anticipacion porque no protege el inventario sino
#: la agenda del probador: dos horas es mucho mas de lo que lleva probarse
#: ropa, y sirve de tope contra el dedazo --- una franja de tres dias
#: inmovilizaria un vestidor entero y todo el stock de la reserva.
DURACION_MAXIMA_MINUTOS = 120

#: Minima, para que una franja no sea un instante.
DURACION_MINIMA_MINUTOS = 15

#: Cuantas prendas distintas admite una reserva.
#:
#: El RF09 pide «multiples prendas» y no dice cuantas. El tope existe porque
#: cada linea aparta stock real: sin el, una sola peticion podria inmovilizar la
#: vitrina entera de una sucursal.
MAXIMO_LINEAS = 10


class LineaReservaIn(BaseModel):
    """Una prenda y cuantas unidades se apartan de ella."""

    variante_id: int
    cantidad: int = Field(gt=0, le=10)


class ReservaCrearIn(BaseModel):
    """Creacion de una reserva (pasos 4 a 7 de CU-22).

    La franja y las lineas viajan juntas porque la reserva es **una**
    transaccion: o se apartan todas las prendas o no se aparta ninguna. Si se
    aceptaran de a una, un fallo a mitad dejaria stock inmovilizado sin ninguna
    reserva que lo explique --- y nadie lo liberaria, porque CU-25 expira
    reservas y eso no seria una.
    """

    sucursal_id: int
    franja_inicio: datetime
    franja_fin: datetime
    observacion: str | None = Field(default=None, max_length=200)
    lineas: list[LineaReservaIn] = Field(min_length=1, max_length=MAXIMO_LINEAS)

    @field_validator("observacion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @field_validator("franja_inicio", "franja_fin")
    @classmethod
    def _con_zona_horaria(cls, valor: datetime) -> datetime:
        """Las dos fechas tienen que traer zona horaria.

        Las columnas son `timestamptz`. Aceptar un valor sin zona obligaria al
        servidor a suponer cual es, y suponer mal significa que una reserva
        creada a las 23:00 en Bolivia expire cuatro horas antes de lo que dice
        la pantalla. Es preferible rechazarla y que el cliente mande el dato
        completo.
        """
        if valor.tzinfo is None:
            raise ValueError(
                "La fecha debe incluir la zona horaria (por ejemplo, "
                "2026-09-12T15:00:00-04:00)."
            )
        return valor

    @model_validator(mode="after")
    def _sin_variantes_repetidas(self) -> "ReservaCrearIn":
        """La misma prenda no puede venir en dos lineas (excepcion E7).

        Lo impide ademas `uq_reserva_detalle_reserva_variante`, pero un UNIQUE
        violado llega como un 500 de PostgreSQL; acá llega como un 422 que
        nombra el problema y dice qué hacer.
        """
        vistas = set()
        for linea in self.lineas:
            if linea.variante_id in vistas:
                raise ValueError(
                    "La misma prenda aparece dos veces. Si quiere más de una "
                    "unidad, suba la cantidad en lugar de repetirla."
                )
            vistas.add(linea.variante_id)
        return self


# --- Salida --------------------------------------------------------------

class LineaReservaOut(BaseModel):
    """Una linea de la reserva, con la prenda ya nombrada.

    Igual que en P4, la variante se nombra y no se numera: «variante 412» no le
    dice nada a un cliente mirando su reserva en el telefono.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    cantidad: int
    #: Lo escribe CU-24 al atender. Nulo mientras la reserva sigue viva.
    resultado_prueba: str | None = None


class ReservaOut(BaseModel):
    """Una reserva con su detalle."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    sucursal_id: int
    sucursal: str
    ciudad: str
    franja_inicio: datetime
    franja_fin: datetime
    estado: str
    observacion: str | None
    creado_en: datetime

    #: Suma de las cantidades de todas las lineas, para no recorrerlas en la
    #: interfaz solo para mostrar «3 prendas».
    unidades: int
    lineas: list[LineaReservaOut]


class ReservaResumenOut(BaseModel):
    """Fila del listado «mis reservas», sin el detalle."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sucursal_id: int
    sucursal: str
    ciudad: str
    franja_inicio: datetime
    franja_fin: datetime
    estado: str
    prendas: int
    unidades: int


class PaginaReservas(BaseModel):
    """Listado paginado, con el total aparte para dibujar el paginador."""

    total: int
    pagina: int
    tamano: int
    items: list[ReservaResumenOut]
