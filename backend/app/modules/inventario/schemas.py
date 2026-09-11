"""
P4 - Inventario  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal

Implementados en este archivo: CU-13 y CU-15.

Las longitudes maximas replican el esquema fisico de la seccion 6.4 de
docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md y las columnas de
`app/modules/inventario/models.py`.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Regla: NUNCA se expone un modelo SQLAlchemy directamente.

#: Los tipos que un usuario puede originar a mano. Es un subconjunto de
#: TIPOS_MOVIMIENTO: RESERVA, LIBERACION, VENTA y DEVOLUCION las genera el
#: sistema desde CU-22, CU-23, CU-25 y las ventas del Ciclo 3, y dejar que
#: alguien las escriba a mano desde esta pantalla descuadraria el saldo contra
#: la reserva o la venta que las justifica.
TIPOS_MANUALES = ("INGRESO", "TRANSFERENCIA", "AJUSTE")

#: Longitud minima del motivo de CU-15. El RF28 pide trazabilidad del motivo;
#: un motivo de dos letras la cumple en la forma y no en el fondo, asi que se
#: exige algo que se pueda leer dentro de seis meses.
MOTIVO_LONGITUD_MINIMA = 5


def _texto_o_none(valor: str | None) -> str | None:
    if valor is None:
        return None
    return valor.strip() or None


# =====================================================================
# Piezas compartidas por los dos casos de uso
# =====================================================================

class VarianteResumenOut(BaseModel):
    """Como se nombra una prenda en las pantallas de inventario.

    La variante es lo que tiene existencia (decision D1), pero «variante 412»
    no le dice nada a quien esta recibiendo cajas en el deposito. Por eso todo
    lo que sale de este paquete la nombra con su SKU y con el producto, la
    talla y el color ya resueltos, en vez de con el identificador pelado.

    Los cuatro campos vienen de tablas de P3, que es una dependencia permitida:
    la seccion 2 de docs/04-analisis-arquitectura.md dice que P4 depende de P3
    (variante) y de P2 (sucursal).
    """

    model_config = ConfigDict(from_attributes=True)

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str


class ExistenciaOut(VarianteResumenOut):
    """Saldo de una variante en una sucursal."""

    existencia_id: int
    sucursal_id: int
    sucursal: str
    cantidad_disponible: int
    cantidad_reservada: int
    #: Lo que hay fisicamente en el local. Viaja calculado porque es el numero
    #: contra el que se compara un conteo fisico (CU-15) y la interfaz no
    #: deberia tener que deducir esa regla por su cuenta.
    cantidad_fisica: int


# =====================================================================
# CU-13 - Registrar ingreso de mercaderia
# =====================================================================

class LineaIngresoIn(BaseModel):
    """Una prenda y cuantas unidades llegaron de ella."""

    variante_id: int
    cantidad: int = Field(gt=0, le=100_000)


class IngresoIn(BaseModel):
    """Recepcion de un envio de un proveedor en una sucursal (pasos 4 a 7).

    La cabecera y las lineas viajan juntas en una sola peticion porque el
    ingreso es **una** transaccion: o entran todas las prendas del remito o no
    entra ninguna. Aceptar las lineas de a una dejaria medio remito cargado si
    se corta la conexion, y el deposito no tendria como saber por donde iba.
    """

    sucursal_id: int
    proveedor_id: int
    referencia: str | None = Field(default=None, max_length=40)
    observacion: str | None = Field(default=None, max_length=120)
    lineas: list[LineaIngresoIn] = Field(min_length=1)

    @field_validator("referencia", "observacion")
    @classmethod
    def _recortar(cls, valor: str | None) -> str | None:
        return _texto_o_none(valor)

    @model_validator(mode="after")
    def _sin_variantes_repetidas(self) -> "IngresoIn":
        """Excepcion E4: la misma prenda no puede venir en dos lineas.

        Se rechaza en vez de sumarlas. Dos lineas de la misma variante casi
        siempre son un error de carga -la misma caja contada dos veces- y
        sumarlas en silencio guardaria el error como si fuera un dato.
        """
        vistas = set()
        for linea in self.lineas:
            if linea.variante_id in vistas:
                raise ValueError(
                    "La misma prenda aparece en dos líneas del ingreso. "
                    "Únalas en una sola con la cantidad total."
                )
            vistas.add(linea.variante_id)
        return self


class LineaIngresoOut(VarianteResumenOut):
    """Una linea ya registrada, con el saldo que dejo."""

    cantidad: int
    #: Cuanto quedo disponible de esa prenda en esa sucursal despues del
    #: ingreso. Es la confirmacion que el encargado necesita ver sin tener que
    #: ir a otra pantalla a comprobar que el saldo subio.
    disponible_resultante: int


class IngresoOut(BaseModel):
    """Comprobante del ingreso registrado (paso 7).

    No corresponde a una fila de ninguna tabla: se arma con las lineas que la
    transaccion acaba de escribir. Ver la nota «POR QUE NO HAY TABLA `ingreso`»
    en models.py.
    """

    registrado_en: datetime
    sucursal_id: int
    sucursal: str
    proveedor_id: int
    proveedor: str
    referencia: str | None
    usuario_id: int | None
    usuario: str | None
    #: Suma de las cantidades de todas las lineas.
    unidades: int
    lineas: list[LineaIngresoOut]


class IngresoResumenOut(BaseModel):
    """Una fila del historial de ingresos (paso 2).

    Cada fila es un grupo de movimientos INGRESO que comparten proveedor,
    sucursal, remito, usuario e instante de transaccion.
    """

    registrado_en: datetime
    sucursal_id: int
    sucursal: str
    proveedor_id: int | None
    proveedor: str | None
    referencia: str | None
    usuario_id: int | None
    usuario: str | None
    #: Cuantas prendas distintas trajo el ingreso.
    lineas: int
    #: Cuantas unidades en total.
    unidades: int


class PaginaIngresos(BaseModel):
    """Historial de ingresos, paginado.

    El total viaja aparte por el mismo motivo que en CU-10: la interfaz dibuja
    el paginador antes de tener las filas.
    """

    total: int
    pagina: int
    tamano: int
    items: list[IngresoResumenOut]


# =====================================================================
# CU-15 - Registrar movimiento de inventario
# =====================================================================

class AjusteIn(BaseModel):
    """Ajuste por conteo fisico (flujo principal de CU-15).

    Se envia **lo que se conto**, no la diferencia. Es la unica forma de que la
    pantalla refleje lo que hace la persona: nadie cuenta «menos tres camisas»,
    cuenta «hay diecisiete». La diferencia con signo la calcula el servicio, que
    es quien sabe cual era el saldo en ese momento.
    """

    variante_id: int
    sucursal_id: int
    #: Unidades contadas fisicamente en el local, reservadas incluidas: una
    #: prenda apartada para una reserva sigue estando en la percha.
    cantidad_contada: int = Field(ge=0, le=1_000_000)
    motivo: str = Field(min_length=MOTIVO_LONGITUD_MINIMA, max_length=200)

    @field_validator("motivo")
    @classmethod
    def _motivo_legible(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < MOTIVO_LONGITUD_MINIMA:
            raise ValueError(
                "Explique el motivo del ajuste: es lo que va a quedar en el "
                "historial."
            )
        return valor


class TransferenciaIn(BaseModel):
    """Traslado de unidades entre dos sucursales (flujo alternativo 3a)."""

    variante_id: int
    sucursal_origen_id: int
    sucursal_destino_id: int
    cantidad: int = Field(gt=0, le=100_000)
    motivo: str = Field(min_length=MOTIVO_LONGITUD_MINIMA, max_length=200)

    @field_validator("motivo")
    @classmethod
    def _motivo_legible(cls, valor: str) -> str:
        valor = valor.strip()
        if len(valor) < MOTIVO_LONGITUD_MINIMA:
            raise ValueError(
                "Explique el motivo de la transferencia: es lo que va a quedar "
                "en el historial."
            )
        return valor

    @model_validator(mode="after")
    def _sucursales_distintas(self) -> "TransferenciaIn":
        """Excepcion E5."""
        if self.sucursal_origen_id == self.sucursal_destino_id:
            raise ValueError(
                "El origen y el destino de la transferencia son la misma sucursal."
            )
        return self


class MovimientoOut(BaseModel):
    """Una fila del historial de movimientos.

    `cantidad` conserva el signo con el que se guardo -positiva entra, negativa
    sale-. La interfaz lo necesita: es lo que distingue la punta de salida de
    una transferencia de la de entrada, y las dos filas dicen `TRANSFERENCIA`.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    creado_en: datetime
    tipo: str
    cantidad: int
    motivo: str | None
    referencia: str | None

    existencia_id: int
    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str

    sucursal_id: int
    sucursal: str

    proveedor_id: int | None
    proveedor: str | None
    usuario_id: int | None
    usuario: str | None


class PaginaMovimientos(BaseModel):
    """Historial de movimientos, paginado."""

    total: int
    pagina: int
    tamano: int
    items: list[MovimientoOut]


class TransferenciaOut(BaseModel):
    """Las dos puntas de una transferencia, tal como quedaron registradas.

    Se devuelven las dos filas y no una confirmacion escueta porque una
    transferencia mal leida -origen y destino invertidos- es el error mas facil
    de cometer en esta pantalla y el mas caro de descubrir despues.
    """

    salida: MovimientoOut
    entrada: MovimientoOut
    origen: ExistenciaOut
    destino: ExistenciaOut


class AjusteOut(BaseModel):
    """Resultado de un conteo fisico."""

    movimiento: MovimientoOut
    existencia: ExistenciaOut
    #: Diferencia con signo entre lo contado y lo que decia el sistema. Es el
    #: mismo numero que `movimiento.cantidad`; se repite arriba para que la
    #: interfaz pueda decir «faltaban 3» sin abrir el movimiento.
    diferencia: int
