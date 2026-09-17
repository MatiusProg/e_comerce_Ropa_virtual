"""
P11 - Reportes y Tablero / CU-36  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3
Caso de uso: CU-36 Consultar tablero de indicadores

Archivo propio dentro del paquete, con el mismo patron que `consolidado_*` en
`inventario/` y `carrito_*` en `ventas/`. El paquete P11 realiza dos casos de
uso ---CU-36 y CU-37--- y el plan (seccion 5.5) los reparte por capas; el
acuerdo del Ciclo 2 los convirtio en unidades verticales. Separar en archivos
`tablero_*` deja `router.py`, `service.py` y `repository.py` libres para CU-37
(exportar a PDF y Excel), que es el otro caso de uso del paquete.

Regla: NUNCA se expone un modelo SQLAlchemy directamente.

EL CONTRATO SE DECLARA ENTERO AUNQUE MEDIO NO TENGA DATOS TODAVIA
-----------------------------------------------------------------
El enunciado pide siete indicadores (seccion 1 de docs/03-captura-requisitos.md,
fila CU-36): ventas del dia y del mes, ticket promedio, reservas pendientes y
atendidas, conversion de reserva a venta, productos mas vendidos y stock
critico. **Cuatro de ellos salen de tablas que hoy no existen**: `venta` y
`detalle_venta` nacen con la `0006_ciclo3_ventas`, que es de Mateo.

El bloque `ventas` viaja igual, con `disponible = False` y sus cifras en nulo.
Es la misma decision que se tomo en CU-14 con `EstadoExistencia.PROXIMA_A_INGRESAR`
---declarado en el contrato, sin filas que lo devuelvan, y documentado el por
que---. La razon es la misma: cuando la `0006` aterrice, la pantalla no cambia.
Un bloque que aparece de la nada obliga a tocar la interfaz dos veces.
"""
from datetime import date, datetime

from pydantic import BaseModel


# =====================================================================
# Reservas  -  P6, disponible hoy
# =====================================================================

class ReservasPorEstadoOut(BaseModel):
    """Cuantas reservas hay en cada estado dentro del periodo consultado.

    Los cinco estados son los de `ESTADOS_RESERVA` (P6). Se devuelven los cinco
    siempre, incluso en cero: una pantalla que solo recibe los estados con
    filas tendria que inventar los que faltan para dibujar el grafico, y en un
    dia sin cancelaciones la barra de canceladas desapareceria en vez de
    quedarse en cero, que es una lectura distinta.
    """

    pendientes: int
    preparadas: int
    atendidas: int
    canceladas: int
    expiradas: int

    #: La suma de los cinco. Viaja calculada por el mismo motivo que
    #: `cantidad_fisica` en CU-14: es el denominador de todos los porcentajes
    #: de la pantalla y no conviene que cada cliente lo sume por su cuenta.
    total: int

    #: Las que siguen vivas: PENDIENTE + PREPARADA. Es el numero que el
    #: enunciado llama «reservas pendientes», y no coincide con `pendientes`:
    #: una reserva PREPARADA tambien esta esperando a que el cliente llegue.
    abiertas: int


class ConversionOut(BaseModel):
    """Que pasa con las reservas que ya se cerraron.

    **Dos tasas, no una, y la diferencia importa.**

    `tasa_atencion` es sobre reservas cerradas: de las que ya terminaron su
    ciclo ---atendidas, canceladas o expiradas---, cuantas terminaron con el
    cliente en la tienda. Mide si la gente aparece.

    `tasa_prueba` es sobre lineas atendidas: de las prendas que el cliente
    efectivamente se probo, cuantas se llevo. Sale de
    `reserva_detalle.resultado_prueba`, que CU-24 escribe. Mide si la prenda
    convence una vez puesta.

    Las reservas **abiertas no entran en ningun denominador**: todavia no
    fracasaron, solo no terminaron. Meterlas hundiria la tasa cada vez que se
    consulta un dia con reservas para mas tarde.
    """

    cerradas: int
    atendidas: int
    #: `atendidas / cerradas`, en porcentaje de 0 a 100. Nulo si no hay ninguna
    #: cerrada: cero por ciento y «no hay dato» son cosas distintas, y una
    #: pantalla que las confunde muestra un tablero en rojo el dia que se
    #: estrena el sistema.
    tasa_atencion: float | None

    lineas_probadas: int
    lineas_llevadas: int
    tasa_prueba: float | None


class PrendaReservadaOut(BaseModel):
    """Una variante y cuantas unidades se reservaron de ella en el periodo."""

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    unidades: int
    #: En cuantas reservas distintas aparecio. Una prenda con 20 unidades en
    #: una sola reserva no es lo mismo que con 20 unidades en 20 reservas, y el
    #: ranking por unidades solo no deja verlo.
    reservas: int


# =====================================================================
# Inventario  -  P4, disponible hoy
# =====================================================================

class SaludInventarioOut(BaseModel):
    """El estado del stock ahora mismo. **No depende del periodo.**

    Un saldo es una foto del instante, no un acumulado: `existencia` guarda
    cuanto hay, no cuanto hubo. Filtrar «stock critico entre el 1 y el 15» no
    significa nada, asi que este bloque ignora `desde` y `hasta` a proposito, y
    el router lo dice en la respuesta para que la pantalla lo aclare.
    """

    total_disponible: int
    total_reservado: int
    #: Cuantas filas (variante, sucursal) estan en alerta de reposicion. La
    #: regla ---umbral mayor que cero y disponible que no lo supera--- es de
    #: P4 y se consume por su costura, no se reimplementa aca.
    en_alerta: int
    variantes_sin_stock: int


class AlertaStockOut(BaseModel):
    """Una fila en alerta de reposicion, para la lista corta del tablero."""

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str
    sucursal_id: int
    sucursal: str
    cantidad_disponible: int
    stock_minimo: int


# =====================================================================
# Ventas  -  P7, TODAVIA NO EXISTE
# =====================================================================

class VentasOut(BaseModel):
    """Los cuatro indicadores que dependen de la `0006_ciclo3_ventas`.

    Viaja siempre, con `disponible = False` mientras las tablas no existan. Ver
    la nota de cabecera de este archivo.
    """

    #: False hasta que exista la tabla `venta`. Es lo unico que la pantalla
    #: tiene que mirar para decidir si dibuja las tarjetas o el aviso.
    disponible: bool

    monto_hoy: float | None = None
    monto_periodo: float | None = None
    cantidad_periodo: int | None = None
    ticket_promedio: float | None = None

    #: Las mas vendidas del periodo. Lista vacia mientras no haya ventas.
    mas_vendidas: list[PrendaReservadaOut] = []

    #: Por que no hay datos, en una frase, para que la pantalla no tenga que
    #: traer su propia explicacion. Nulo cuando `disponible` es True.
    motivo: str | None = None


# =====================================================================
# La respuesta completa
# =====================================================================

class PeriodoOut(BaseModel):
    """El periodo que efectivamente se consulto, ya resuelto.

    Viaja de vuelta porque los dos extremos son opcionales en la entrada y el
    servicio les pone un valor por omision. Sin esto, una pantalla que no mando
    fechas no puede rotular su propio grafico.
    """

    desde: date
    hasta: date
    #: Nulo cuando se miro la red entera.
    sucursal_id: int | None
    sucursal: str | None


class TableroOut(BaseModel):
    """Todo el tablero en una sola respuesta.

    **Un endpoint y no seis**, por la misma razon que CU-14 devuelve listado y
    resumen juntos: la pantalla los muestra siempre a la vez y salen del mismo
    filtrado. Seis endpoints serian seis viajes que recorren lo mismo, y
    abririan la posibilidad de que dos tarjetas del mismo tablero muestren
    periodos distintos si una llega tarde.
    """

    periodo: PeriodoOut
    #: Cuando se calculo. El tablero es «en tiempo real» (RF24) y conviene que
    #: la pantalla pueda decir desde cuando no se refresca.
    calculado_en: datetime

    reservas: ReservasPorEstadoOut
    conversion: ConversionOut
    mas_reservadas: list[PrendaReservadaOut]

    inventario: SaludInventarioOut
    alertas: list[AlertaStockOut]

    ventas: VentasOut
