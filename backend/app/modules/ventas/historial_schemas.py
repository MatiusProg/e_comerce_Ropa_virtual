"""
P7 - Ventas / CU-29  |  capa: esquemas de entrada y salida (Pydantic)

Ciclo de desarrollo: 3
Caso de uso: CU-29 Consultar historial de compras

Archivo propio dentro del paquete, con el mismo patron que `carrito_*` y
`consolidado_*`. CU-27 es de Mateo y CU-29 de Karen; separarlos en archivos
evita que las dos ramas toquen las mismas lineas.

SE REUSA `PedidoOut` DE CU-27, NO SE DECLARA OTRO
--------------------------------------------------
La ficha de una compra y la de un pedido son **la misma cosa**: mismo codigo,
mismo estado, mismas lineas con el precio congelado, mismo total. Declarar un
`CompraOut` paralelo obligaria a mantener dos formas sincronizadas, y el dia que
una gane un campo la otra lo perderia sin que nada avise.

Lo unico que CU-29 agrega es la **paginacion** ---un historial crece--- y el
comprobante, que no es un campo sino un archivo aparte.
"""
from pydantic import BaseModel

from app.modules.ventas.schemas import PedidoOut


class PaginaCompras(BaseModel):
    """Las compras del cliente, de la mas nueva a la mas vieja.

    Pagina, a diferencia de casi todo lo del cliente: el carrito y las
    direcciones tienen un tope natural ---nadie guarda cuarenta direcciones---
    pero el historial solo crece. Una cuenta de dos anios traeria cientos de
    pedidos con sus lineas en cada carga.
    """

    total: int
    pagina: int
    tamano: int
    items: list[PedidoOut]
