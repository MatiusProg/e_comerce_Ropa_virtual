"""
P6 - Reservas  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Implementados en este archivo: CU-22, CU-23, CU-24 y CU-25.

Los nombres y tipos replican el esquema fisico de la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md y las columnas de
`app/modules/reservas/models.py`.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.reservas.models import RESULTADOS_PRUEBA

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
    lineas: list[LineaReservaIn] = Field(min_length=1, max_length=MAXIMO_LINEAS)

    # NO hay `observacion` acá, y es a proposito.
    #
    # El 11/09 este esquema la aceptaba al crear, y al escribir CU-23 quedo a la
    # vista que eso rompia el modelo: `reserva.observacion` esta declarada en
    # models.py como la nota de CIERRE --- «lo escribe CU-23 cuando la cancela
    # el cliente y CU-24 cuando el Encargado la cierra» ---. Con las dos cosas
    # en la misma columna, el motivo de la cancelacion pisaria la nota que el
    # cliente dejo al reservar, y se perderia justo el dato que explica por que
    # se cancelo.
    #
    # Una nota del cliente al reservar es util, pero no la pide ningun RF y
    # necesita columna propia. Si se agrega, se agrega como `nota_cliente` y con
    # su migracion; no compartiendo esta.

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


class CancelarReservaIn(BaseModel):
    """Cancelacion de una reserva por el cliente (CU-23).

    El motivo es **opcional**: cancelar no es un tramite y exigir una
    justificacion para no ir a probarse ropa solo consigue que la gente escriba
    «asdf». Lo que si se guarda siempre es QUIEN y CUANDO, que es lo que le
    sirve a la sucursal.
    """

    motivo: str | None = Field(default=None, max_length=150)

    @field_validator("motivo")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


# =====================================================================
# CU-24 - Atender reserva en sucursal
# =====================================================================

class ResultadoLineaIn(BaseModel):
    """Que paso con una prenda cuando el cliente se la probo."""

    detalle_id: int
    #: LLEVA o NO_LLEVA. Los valores los fija RESULTADOS_PRUEBA en models.py y
    #: el CHECK `ck_reserva_detalle_resultado` los aplica en la base; aqui se
    #: rechazan antes, para devolver un 422 que nombre el campo en vez de un
    #: error de PostgreSQL.
    resultado: str

    @field_validator("resultado")
    @classmethod
    def _valido(cls, valor: str) -> str:
        valor = valor.strip().upper()
        if valor not in RESULTADOS_PRUEBA:
            raise ValueError("El resultado debe ser LLEVA o NO_LLEVA.")
        return valor


class AtenderReservaIn(BaseModel):
    """Cierre de la reserva con el resultado de la prueba (CU-24).

    Los resultados de TODAS las lineas viajan juntos porque el cierre es una
    sola transaccion: cada prenda mueve stock --- las que no se lleva vuelven al
    disponible, las que se lleva salen --- y cerrar a medias dejaria una reserva
    ATENDIDA con parte de su mercaderia todavia apartada, que es un estado que
    nadie limpia despues.
    """

    resultados: list[ResultadoLineaIn] = Field(min_length=1)
    observacion: str | None = Field(default=None, max_length=200)

    @field_validator("observacion")
    @classmethod
    def _recortar_observacion(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @model_validator(mode="after")
    def _sin_lineas_repetidas(self) -> "AtenderReservaIn":
        vistas = set()
        for resultado in self.resultados:
            if resultado.detalle_id in vistas:
                raise ValueError(
                    "Hay una prenda con dos resultados distintos en el mismo "
                    "cierre."
                )
            vistas.add(resultado.detalle_id)
        return self


# =====================================================================
# CU-25 - Expirar reservas vencidas
# =====================================================================

class ExpiracionOut(BaseModel):
    """Lo que hizo una corrida de la tarea de expiracion.

    Devuelve **cuantas** y **cuales**, no solo un «listo». Una tarea programada
    que no dice lo que hizo es imposible de verificar: si un dia deja de
    funcionar, el sintoma seria stock retenido sin que nada lo denuncie, y eso
    se descubre semanas despues contando prendas a mano.
    """

    #: Cuantas reservas vencidas encontro esta corrida.
    encontradas: int
    #: Cuantas expiro de verdad. Puede ser menor que `encontradas` si otra
    #: transaccion las estaba tocando; esas quedan para la proxima vuelta.
    expiradas: int
    #: Unidades devueltas a `cantidad_disponible` en total.
    unidades_liberadas: int
    #: Los identificadores, para poder rastrear una en el historial.
    reservas: list[int]
    #: Hasta que instante se considero vencida una reserva. Viaja para que la
    #: pantalla pueda explicar por que una reserva de ayer todavia no expiro.
    corte: datetime


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
    """Fila del listado, tanto de «mis reservas» como del panel de la sucursal.

    `cliente` viaja para la pantalla del Encargado de CU-24 --- que necesita
    saber a quien esta atendiendo --- y se ignora en la del Cliente, que ya sabe
    que las reservas son suyas. Un esquema y no dos: son la misma fila mirada
    desde dos lados, y duplicarla garantizaria que algun dia digan cosas
    distintas.
    """

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
    cliente: str | None = None


class PaginaReservas(BaseModel):
    """Listado paginado, con el total aparte para dibujar el paginador."""

    total: int
    pagina: int
    tamano: int
    items: list[ReservaResumenOut]
