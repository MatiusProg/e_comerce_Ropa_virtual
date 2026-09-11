"""
P4 - Inventario / CU-14  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2
Caso de uso: CU-14 Consultar inventario consolidado

Es de solo lectura, asi que no hay transaccion que controlar. Lo que vive aqui
es la agrupacion por variante y la clasificacion por estado, que son las dos
cosas que distinguen este caso de uso del listado plano de existencias.

**Los datos salen de `service.inventario_consolidado`, no de una consulta
propia.** `existencia` es de Mateo y la regla del ciclo es que nadie consulte la
tabla del otro: la costura C1 expone esa funcion justamente para esto. El precio
es que el filtrado fino, el orden y la paginacion se resuelven en memoria en vez
de en SQL --- ver la nota al pie de este archivo.
"""
from app.modules.inventario import service
from app.modules.inventario.consolidado_schemas import (
    EstadoExistencia,
    ExistenciaConsolidadaOut,
    PaginaInventarioConsolidado,
    ResumenInventarioOut,
    SaldoEnSucursalOut,
)

#: Como se ordena el listado. La clave es lo que viaja por la URL.
ORDENES = ("prenda", "disponible_asc", "disponible_desc", "sucursales")


def _estado(disponible: int, reservado: int) -> EstadoExistencia:
    """El estado de una variante a partir de sus dos saldos.

    El orden de las comprobaciones es la regla: **agotada gana sobre
    reservada**. Una variante con 0 disponibles y 3 reservadas esta agotada para
    quien quiera comprarla hoy, aunque tenga unidades apartadas; decir
    «reservada» haria creer que hay algo que ofrecer.
    """
    if disponible > 0:
        return EstadoExistencia.DISPONIBLE
    if reservado > 0:
        return EstadoExistencia.RESERVADA
    return EstadoExistencia.AGOTADA


def _agrupar(filas) -> list[ExistenciaConsolidadaOut]:
    """De (variante, sucursal) a una fila por variante con su reparto.

    Es lo que convierte el listado operativo en una vista de red: la misma
    prenda deja de ocupar cinco filas --- una por tienda --- y pasa a ocupar una
    con el reparto adentro.
    """
    por_variante: dict[int, ExistenciaConsolidadaOut] = {}

    for fila in filas:
        consolidada = por_variante.get(fila.variante_id)
        if consolidada is None:
            consolidada = ExistenciaConsolidadaOut(
                variante_id=fila.variante_id,
                sku=fila.sku,
                producto=fila.producto,
                talla=fila.talla,
                color=fila.color,
                total_disponible=0,
                total_reservado=0,
                total_fisico=0,
                estado=EstadoExistencia.AGOTADA,
                sucursales_con_saldo=0,
                sucursales=[],
            )
            por_variante[fila.variante_id] = consolidada

        consolidada.total_disponible += fila.cantidad_disponible
        consolidada.total_reservado += fila.cantidad_reservada
        consolidada.total_fisico += fila.cantidad_fisica
        consolidada.sucursales.append(
            SaldoEnSucursalOut(
                sucursal_id=fila.sucursal_id,
                sucursal=fila.sucursal,
                cantidad_disponible=fila.cantidad_disponible,
                cantidad_reservada=fila.cantidad_reservada,
            )
        )

    for consolidada in por_variante.values():
        consolidada.estado = _estado(
            consolidada.total_disponible, consolidada.total_reservado
        )
        # Cuenta las sucursales donde hay ALGO, disponible o apartado. Una
        # tienda con la prenda entera reservada sigue teniendo la prenda.
        consolidada.sucursales_con_saldo = sum(
            1
            for s in consolidada.sucursales
            if s.cantidad_disponible > 0 or s.cantidad_reservada > 0
        )

    return list(por_variante.values())


def _ordenar(items: list[ExistenciaConsolidadaOut], orden: str):
    """El orden pedido, desempatando siempre por SKU.

    Sin desempate, dos variantes con el mismo disponible pueden salir en
    distinto orden entre dos paginas y una aparecer dos veces o ninguna. Es la
    misma razon que en CU-10 y CU-17.
    """
    match orden:
        case "disponible_asc":
            return sorted(items, key=lambda i: (i.total_disponible, i.sku))
        case "disponible_desc":
            return sorted(items, key=lambda i: (-i.total_disponible, i.sku))
        case "sucursales":
            return sorted(items, key=lambda i: (i.sucursales_con_saldo, i.sku))
        case _:
            return sorted(items, key=lambda i: (i.producto, i.talla, i.color, i.sku))


def consultar(
    db,
    *,
    pagina: int,
    tamano: int,
    orden: str = "prenda",
    busqueda: str | None = None,
    sucursal_id: int | None = None,
    producto_id: int | None = None,
    estado: EstadoExistencia | None = None,
) -> tuple[PaginaInventarioConsolidado, ResumenInventarioOut]:
    """Paso 2: el inventario de la red, agrupado por variante.

    `sucursal_id` **filtra las filas antes de agrupar**, no despues: preguntar
    «que hay en la Centro» tiene que devolver los saldos de la Centro, no las
    variantes que estan en la Centro con su reparto en toda la red. Es la
    diferencia entre una consulta de tienda y una de red, y se resuelve pasando
    el filtro a la costura en vez de aplicarlo despues.
    """
    filas = service.inventario_consolidado(
        db, sucursal_id=sucursal_id, producto_id=producto_id
    )
    items = _agrupar(filas)

    if busqueda:
        patron = busqueda.strip().lower()
        items = [
            i
            for i in items
            if patron in i.sku.lower()
            or patron in i.producto.lower()
            or patron in i.color.lower()
        ]

    if estado is not None:
        items = [i for i in items if i.estado == estado]

    # El resumen se calcula sobre todo lo filtrado y antes de paginar: un
    # resumen que solo suma las filas visibles no es un resumen.
    resumen = ResumenInventarioOut(
        variantes=len(items),
        total_disponible=sum(i.total_disponible for i in items),
        total_reservado=sum(i.total_reservado for i in items),
        agotadas=sum(1 for i in items if i.estado is EstadoExistencia.AGOTADA),
    )

    items = _ordenar(items, orden)
    desde = (pagina - 1) * tamano
    listado = PaginaInventarioConsolidado(
        total=len(items),
        pagina=pagina,
        tamano=tamano,
        items=items[desde : desde + tamano],
    )
    return listado, resumen


# --- Por que se agrupa y se pagina en memoria ----------------------------
#
# Porque el contrato del ciclo lo pide. La costura C1 dice que P5 y CU-14 no
# consultan `existencia`: importan la funcion que `inventario/service.py`
# expone. Esa funcion devuelve la lista completa de saldos, sin paginar.
#
# Al tamano de este catalogo no es un problema: `existencia` solo tiene filas
# donde hubo un ingreso, y el orden de magnitud son centenares. Si el inventario
# creciera a decenas de miles de filas, lo correcto **no** es empezar a
# consultar la tabla desde aca --- eso rompe el acuerdo y deja la tabla con dos
# duenos --- sino pedirle a Mateo que la costura acepte paginacion y devuelva el
# agrupado. Queda anotado para que la decision, si llega, se tome a proposito.
