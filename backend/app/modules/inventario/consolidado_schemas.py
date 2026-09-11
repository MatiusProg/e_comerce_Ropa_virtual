"""
P4 - Inventario / CU-14  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 2
Caso de uso: CU-14 Consultar inventario consolidado

Archivo propio dentro del paquete de Mateo, con el mismo patron que `catalogo/`
usa para `imagenes_*` y `temporadas_*`: CU-14 es de Karen por la seccion 4.1 de
la contrapropuesta --- es el unico caso de uso de inventario que no escribe
ninguna tabla --- y separarlo en archivos evita que las dos personas toquen los
mismos.

Regla: NUNCA se expone un modelo SQLAlchemy directamente.
"""
from enum import StrEnum

from pydantic import BaseModel


class EstadoExistencia(StrEnum):
    """Los estados que el enunciado pide distinguir en el inventario consolidado.

    El enunciado (seccion 1) enumera cuatro: «disponibles, reservadas, vendidas,
    agotadas o proximas a ingresar». En el modelo de este proyecto:

    - **vendidas** no es un estado de la existencia sino un movimiento --- una
      venta baja el saldo y queda en `movimiento_inventario` ---, asi que se
      consulta en el historial de CU-15 y no aca.
    - **proxima a ingresar** no tiene hoy ningun caso de uso que la produzca.
      CU-13 registra la mercaderia **cuando ya llego**; nada anuncia lo que esta
      por llegar. Es el agujero H1 del analisis de alcance del 10/09, y lo que
      lo cerraria es el CU-39 propuesto ahi (el Proveedor informa disponibilidad
      y plazo). Se declara el valor para no cambiar el contrato despues, pero
      **hoy ninguna fila lo devuelve**, y esa es la unica razon por la que
      falta: no es un olvido.
    """

    DISPONIBLE = "disponible"
    RESERVADA = "reservada"
    AGOTADA = "agotada"
    PROXIMA_A_INGRESAR = "proxima_a_ingresar"


class SaldoEnSucursalOut(BaseModel):
    """Cuanto hay de una variante en una sucursal concreta."""

    sucursal_id: int
    sucursal: str
    cantidad_disponible: int
    cantidad_reservada: int


class ExistenciaConsolidadaOut(BaseModel):
    """Una variante, con su saldo sumado y su reparto entre sucursales.

    **Agrupa por variante y no por (variante, sucursal)**, que es la diferencia
    de fondo con la pestaña de existencias de CU-13 y CU-15. Aquella responde
    «sobre que fila opero»; esta responde «como esta repartida la prenda en la
    red», que es lo que hace falta para ver el desbalance entre tiendas --- uno
    de los problemas que el proyecto dice resolver --- y lo que un listado plano
    de (variante, sucursal) obliga a reconstruir a ojo.
    """

    variante_id: int
    sku: str
    producto: str
    talla: str
    color: str

    total_disponible: int
    total_reservado: int
    #: Lo que hay fisicamente en la red: disponible + reservado.
    total_fisico: int

    estado: EstadoExistencia

    #: En cuantas sucursales hay algo. Viaja calculado porque es la lectura
    #: rapida del desbalance: «60 unidades en 1 sucursal» y «60 en 5» son
    #: situaciones distintas y la lista larga no lo dice de un vistazo.
    sucursales_con_saldo: int

    sucursales: list[SaldoEnSucursalOut] = []


class PaginaInventarioConsolidado(BaseModel):
    """Listado paginado del inventario de la red."""

    total: int
    pagina: int
    tamano: int
    items: list[ExistenciaConsolidadaOut]


class ResumenInventarioOut(BaseModel):
    """Los totales de la cabecera de la pantalla.

    Se calculan sobre **todo lo filtrado**, no sobre la pagina: un resumen que
    solo suma las veinte filas visibles no es un resumen.
    """

    variantes: int
    total_disponible: int
    total_reservado: int
    agotadas: int
