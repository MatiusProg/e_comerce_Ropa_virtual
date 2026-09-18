"""
P8 - Pagos  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3

Casos de uso que realiza este paquete:
  CU-27 Iniciar el pago electronico contra la pasarela
  CU-28 Confirmar pago del pedido (webhook firmado e idempotente)

Regla: NUNCA se expone un modelo SQLAlchemy directamente.

EL WEBHOOK NO TIENE ESQUEMA DE ENTRADA, Y ES A PROPOSITO
---------------------------------------------------------
`POST /pagos/webhook` recibe el cuerpo **en bytes y sin interpretar**: la firma
se calcula sobre los bytes exactos que la pasarela mando, y hacerlos pasar por
un modelo de Pydantic obligaria a volver a serializarlos para verificar ---
cambiando espacios y orden de claves --- con lo que la verificacion fallaria
aunque el mensaje fuera legitimo.

Quien traduce ese cuerpo a algo con forma es el proveedor de la pasarela, y lo
hace DESPUES de verificar. Ver `integrations/pasarela_pago/base.py`.
"""
from pydantic import BaseModel, Field


class RespuestaWebhookOut(BaseModel):
    """Lo que se le contesta a la pasarela.

    El cuerpo casi no importa --- lo que la pasarela mira es el codigo HTTP ---
    pero decir que se hizo con el evento convierte el log de Stripe en algo que
    se puede leer cuando algo no cuadra, en vez de una lista de 200 iguales.
    """

    #: Uno de los `RESULTADO_*` del servicio: aplicado, repetido, ignorado,
    #: sin_pago o rechazado.
    resultado: str


class SimularPagoIn(BaseModel):
    """Lo que hace falta para fabricar una notificacion del proveedor simulado.

    Solo existe con `PAGO_PROVEEDOR=simulada`; con una pasarela de verdad la
    ruta que lo consume responde 404.
    """

    #: El identificador de la sesion, tal como lo devolvio `crear_sesion`. Es
    #: lo que se guardo en `pago.referencia_externa`.
    sesion: str = Field(min_length=1, max_length=100)

    #: El codigo de la venta. Va como respaldo, igual que en el evento real:
    #: si la sesion no se encuentra, es por aca que se llega a la venta.
    pedido: str | None = Field(default=None, max_length=20)

    #: Que se simula. `False` produce un rechazo, que es tan util de demostrar
    #: como la aprobacion --- deja ver que el pedido NO pasa a pagado ---.
    aprobado: bool = True
