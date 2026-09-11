"""
P4 - Inventario  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-13 Registrar ingreso de mercaderia
  CU-14 Consultar inventario consolidado
  CU-15 Registrar movimiento de inventario
  CU-16 Gestionar disponibilidad de la sucursal

Implementados en este archivo: CU-13 y CU-15, mas las dos funciones de la
costura C1 que consumen CU-14 y CU-19 (que son de Karen).

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

LA REGLA QUE CONCENTRA ESTE PAQUETE
-----------------------------------
«Ninguna cantidad se modifica sin generar un movimiento» (P4 en
docs/04-analisis-arquitectura.md). En este archivo eso es literal: no hay un
solo lugar que le asigne un valor a `cantidad_disponible` fuera de
`_aplicar_movimiento`, y esa funcion siempre escribe la fila del historial. Si
manana alguien necesita mover stock por un motivo nuevo, el camino sigue siendo
ese y la trazabilidad de D4 se mantiene sin que haya que acordarse de ella.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.modules.inventario import repository
from app.modules.inventario.models import Existencia
from app.modules.inventario.schemas import (
    AjusteIn,
    AjusteOut,
    ExistenciaOut,
    IngresoIn,
    IngresoOut,
    IngresoResumenOut,
    LineaIngresoOut,
    MovimientoOut,
    PaginaIngresos,
    PaginaMovimientos,
    TransferenciaIn,
    TransferenciaOut,
)


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeInventario(Exception):
    """Base de los errores previstos de P4."""


class SucursalInexistente(ErrorDeInventario):
    """La sucursal indicada no existe."""


class SucursalInactiva(ErrorDeInventario):
    """Excepcion E2: no entra ni sale mercaderia de una sucursal dada de baja."""


class ProveedorInexistente(ErrorDeInventario):
    """El proveedor indicado no existe."""


class ProveedorInactivo(ErrorDeInventario):
    """Excepcion E3: un proveedor dado de baja no puede enviar mercaderia."""


class VarianteInexistente(ErrorDeInventario):
    """Excepcion E1: alguna de las prendas del ingreso no existe.

    Lleva la lista de identificadores para que la interfaz pueda senalar las
    lineas en vez de invalidar el formulario entero.
    """

    def __init__(self, ids: list[int]):
        self.ids = ids
        super().__init__(f"Variantes inexistentes: {ids}")


class VarianteInactiva(ErrorDeInventario):
    """Excepcion E1: la prenda existe pero esta desactivada (CU-10, flujo 7c)."""

    def __init__(self, ids: list[int]):
        self.ids = ids
        super().__init__(f"Variantes desactivadas: {ids}")


class ExistenciaInexistente(ErrorDeInventario):
    """No hay saldo registrado de esa prenda en esa sucursal."""


class StockInsuficiente(ErrorDeInventario):
    """Excepcion E6: se quiso sacar mas de lo que hay disponible."""

    def __init__(self, disponible: int, solicitado: int):
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(f"Disponible {disponible}, solicitado {solicitado}")


class ConteoSinDiferencia(ErrorDeInventario):
    """Excepcion E7: lo contado coincide con lo registrado.

    No es un error del usuario, pero tampoco es un movimiento: el CHECK
    `ck_movimiento_inventario_cantidad_no_nula` rechaza una cantidad cero, y
    guardar una fila de cero unidades llenaria el historial de ruido.
    """


class ConteoMenorQueLoReservado(ErrorDeInventario):
    """Excepcion E8: el conteo fisico no alcanza a cubrir lo ya comprometido.

    Si hay 4 unidades apartadas para reservas y el conteo dice que hay 3
    prendas en total, el ajuste dejaria una reserva sin respaldo fisico. Se
    frena y se avisa: primero se cancela la reserva (CU-23) y despues se
    ajusta.
    """

    def __init__(self, contada: int, reservada: int):
        self.contada = contada
        self.reservada = reservada
        super().__init__(f"Contadas {contada}, reservadas {reservada}")


# --- El unico camino por el que cambia una cantidad ----------------------

def _aplicar_movimiento(
    db: Session,
    existencia: Existencia,
    *,
    tipo: str,
    cantidad: int,
    motivo: str | None = None,
    proveedor_id: int | None = None,
    referencia: str | None = None,
    usuario_id: int | None = None,
):
    """Cambia el saldo y deja la fila del historial que lo explica.

    `cantidad` viene con signo: positiva suma al disponible, negativa resta. No
    se deduce del tipo porque AJUSTE y TRANSFERENCIA van en las dos
    direcciones.

    Verifica que el saldo no quede negativo **antes** de tocarlo. El CHECK de la
    base tambien lo impide, pero un CHECK aborta la transaccion entera con un
    mensaje de PostgreSQL: eso convierte «no hay tantas unidades en la sucursal
    de origen» en un error 500 sin nombre. Comprobarlo aqui deja un mensaje que
    la persona puede leer y una transferencia que no se escribio a medias.
    """
    if existencia.cantidad_disponible + cantidad < 0:
        raise StockInsuficiente(existencia.cantidad_disponible, abs(cantidad))

    existencia.cantidad_disponible += cantidad
    db.flush()

    return repository.agregar_movimiento(
        db,
        existencia_id=existencia.id,
        tipo=tipo,
        cantidad=cantidad,
        motivo=motivo,
        proveedor_id=proveedor_id,
        referencia=referencia,
        usuario_id=usuario_id,
    )


def _existencia_o_crearla(db: Session, *, variante_id: int, sucursal_id: int) -> Existencia:
    """El saldo de esa prenda en esa sucursal; en cero si es la primera vez.

    Se toma con `FOR UPDATE` cuando ya existe: dos personas registrando el
    mismo producto al mismo tiempo leerian el mismo saldo y la segunda pisaria
    a la primera. Es el mismo bloqueo del riesgo R5, aplicado en chico.
    """
    existencia = repository.obtener_existencia(
        db, variante_id=variante_id, sucursal_id=sucursal_id, bloquear=True
    )
    if existencia is None:
        existencia = repository.agregar_existencia(
            db, variante_id=variante_id, sucursal_id=sucursal_id
        )
    return existencia


# --- Validaciones compartidas --------------------------------------------

def _sucursal_activa(db: Session, sucursal_id: int):
    sucursal = repository.obtener_sucursal(db, sucursal_id)
    if sucursal is None:
        raise SucursalInexistente()
    if not sucursal.activa:
        raise SucursalInactiva()
    return sucursal


def _variantes_validas(db: Session, ids: list[int]) -> dict[int, object]:
    """Comprueba que todas las prendas existan y esten activas (E1).

    Devuelve un diccionario por identificador para que quien llama pueda
    nombrarlas sin volver a consultar.
    """
    filas = repository.listar_variantes(db, ids)
    por_id = {fila.variante_id: fila for fila in filas}

    faltantes = [i for i in ids if i not in por_id]
    if faltantes:
        raise VarianteInexistente(faltantes)

    inactivas = [i for i in ids if not por_id[i].activa]
    if inactivas:
        raise VarianteInactiva(inactivas)

    return por_id


def _fila_a_existencia(fila) -> ExistenciaOut:
    return ExistenciaOut(
        existencia_id=fila.existencia_id,
        variante_id=fila.variante_id,
        sku=fila.sku,
        producto=fila.producto,
        talla=fila.talla,
        color=fila.color,
        sucursal_id=fila.sucursal_id,
        sucursal=fila.sucursal,
        cantidad_disponible=fila.cantidad_disponible,
        cantidad_reservada=fila.cantidad_reservada,
        cantidad_fisica=fila.cantidad_fisica,
    )


def _fila_a_movimiento(fila) -> MovimientoOut:
    return MovimientoOut.model_validate(fila, from_attributes=True)


# =====================================================================
# CU-13 - Registrar ingreso de mercaderia
# =====================================================================

def registrar_ingreso(
    db: Session, datos: IngresoIn, *, usuario_id: int | None
) -> IngresoOut:
    """Pasos 4 a 7: recibe el envio de un proveedor y sube los saldos.

    Todo el ingreso es **una** transaccion. Si la linea catorce falla, las
    trece anteriores no quedan cargadas: el remito se vuelve a intentar entero
    y el deposito no tiene que averiguar por donde iba (excepcion E9).
    """
    sucursal = _sucursal_activa(db, datos.sucursal_id)

    proveedor = repository.obtener_proveedor(db, datos.proveedor_id)
    if proveedor is None:
        raise ProveedorInexistente()
    if not proveedor.activo:
        raise ProveedorInactivo()

    variantes = _variantes_validas(db, [linea.variante_id for linea in datos.lineas])

    # El motivo se compone una vez y se repite en todas las lineas: es lo que
    # se va a leer en el historial de CU-15, donde el ingreso ya no tiene
    # cabecera que lo explique.
    motivo = f"Ingreso de {proveedor.razon_social}"
    if datos.observacion:
        motivo = f"{motivo}. {datos.observacion}"
    motivo = motivo[:200]

    lineas: list[LineaIngresoOut] = []
    primer_movimiento = None

    for linea in datos.lineas:
        existencia = _existencia_o_crearla(
            db, variante_id=linea.variante_id, sucursal_id=datos.sucursal_id
        )
        movimiento = _aplicar_movimiento(
            db,
            existencia,
            tipo="INGRESO",
            cantidad=linea.cantidad,
            motivo=motivo,
            proveedor_id=proveedor.id,
            referencia=datos.referencia,
            usuario_id=usuario_id,
        )
        primer_movimiento = primer_movimiento or movimiento

        variante = variantes[linea.variante_id]
        lineas.append(
            LineaIngresoOut(
                variante_id=variante.variante_id,
                sku=variante.sku,
                producto=variante.producto,
                talla=variante.talla,
                color=variante.color,
                cantidad=linea.cantidad,
                disponible_resultante=existencia.cantidad_disponible,
            )
        )

    # `creado_en` lo pone la base con now(), que en PostgreSQL es el instante de
    # la TRANSACCION: las lineas de este ingreso comparten el valor, y es lo que
    # despues las agrupa en el historial. Hay que leerlo de vuelta porque el
    # valor lo genero el servidor, no Python.
    db.refresh(primer_movimiento)
    registrado_en = primer_movimiento.creado_en

    db.commit()

    return IngresoOut(
        registrado_en=registrado_en,
        sucursal_id=sucursal.id,
        sucursal=sucursal.nombre,
        proveedor_id=proveedor.id,
        proveedor=proveedor.razon_social,
        referencia=datos.referencia,
        usuario_id=usuario_id,
        usuario=None,
        unidades=sum(linea.cantidad for linea in datos.lineas),
        lineas=lineas,
    )


def listar_ingresos(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    sucursal_id: int | None = None,
    proveedor_id: int | None = None,
) -> PaginaIngresos:
    """Paso 2: los ingresos ya registrados, del mas reciente al mas viejo."""
    total = repository.contar_ingresos(
        db, sucursal_id=sucursal_id, proveedor_id=proveedor_id
    )
    filas = repository.listar_ingresos(
        db,
        pagina=pagina,
        tamano=tamano,
        sucursal_id=sucursal_id,
        proveedor_id=proveedor_id,
    )
    return PaginaIngresos(
        total=total,
        pagina=pagina,
        tamano=tamano,
        items=[
            IngresoResumenOut(
                registrado_en=fila.creado_en,
                sucursal_id=fila.sucursal_id,
                sucursal=fila.sucursal,
                proveedor_id=fila.proveedor_id,
                proveedor=fila.proveedor,
                referencia=fila.referencia,
                usuario_id=fila.usuario_id,
                usuario=fila.usuario,
                lineas=fila.lineas,
                unidades=fila.unidades,
            )
            for fila in filas
        ],
    )


def detalle_de_ingreso(
    db: Session,
    *,
    registrado_en: datetime,
    sucursal_id: int,
    referencia: str | None = None,
) -> list[MovimientoOut]:
    """Las lineas de un ingreso del historial."""
    filas = repository.lineas_de_ingreso(
        db,
        registrado_en=registrado_en,
        sucursal_id=sucursal_id,
        referencia=referencia,
    )
    if not filas:
        raise ExistenciaInexistente()
    return [_fila_a_movimiento(fila) for fila in filas]


# =====================================================================
# CU-15 - Registrar movimiento de inventario
# =====================================================================

def registrar_ajuste(
    db: Session, datos: AjusteIn, *, usuario_id: int | None
) -> AjusteOut:
    """Flujo principal: ajuste por conteo fisico.

    LO QUE SE CUENTA ES EL TOTAL FISICO, NO EL DISPONIBLE
    -----------------------------------------------------
    Quien recorre la percha cuenta prendas, y una prenda apartada para una
    reserva sigue estando en la percha. Por eso lo contado se compara contra
    `disponible + reservada` y no contra `disponible` a secas. Comparar contra
    el disponible haria que cada reserva viva pareciera un faltante, y el
    ajuste «corregiria» un descuadre que no existe -robandole las unidades a la
    reserva-.

    La diferencia se aplica al disponible, que es la unica cantidad que este
    caso de uso puede tocar: lo reservado lo mueven CU-22, CU-23 y CU-25.
    """
    _sucursal_activa(db, datos.sucursal_id)
    _variantes_validas(db, [datos.variante_id])

    existencia = _existencia_o_crearla(
        db, variante_id=datos.variante_id, sucursal_id=datos.sucursal_id
    )

    if datos.cantidad_contada < existencia.cantidad_reservada:
        # E8. Se deshace la existencia recien creada si la hubo: dejarla en
        # cero seria escribir una fila por un ajuste que se rechazo.
        db.rollback()
        raise ConteoMenorQueLoReservado(
            datos.cantidad_contada, existencia.cantidad_reservada
        )

    fisica = existencia.cantidad_disponible + existencia.cantidad_reservada
    diferencia = datos.cantidad_contada - fisica

    if diferencia == 0:
        db.rollback()
        raise ConteoSinDiferencia()

    movimiento = _aplicar_movimiento(
        db,
        existencia,
        tipo="AJUSTE",
        cantidad=diferencia,
        motivo=datos.motivo,
        usuario_id=usuario_id,
    )
    db.commit()

    return AjusteOut(
        movimiento=_fila_a_movimiento(repository.obtener_movimiento(db, movimiento.id)),
        existencia=_fila_a_existencia(
            repository.obtener_existencia_con_detalle(db, existencia.id)
        ),
        diferencia=diferencia,
    )


def registrar_transferencia(
    db: Session, datos: TransferenciaIn, *, usuario_id: int | None
) -> TransferenciaOut:
    """Flujo alternativo 3a: traslado de unidades entre dos sucursales.

    SON DOS FILAS, NO UNA
    ---------------------
    Una salida negativa en el origen y una entrada positiva en el destino, las
    dos de tipo TRANSFERENCIA. Es lo que hace que el saldo de cada sucursal se
    pueda reconstruir mirando solo sus propios movimientos, que es la promesa
    de D4. Una sola fila con dos sucursales obligaria a que cada consulta de
    saldo supiera interpretar el signo segun de que lado se la mire.

    Las dos comparten `motivo`, `usuario_id` y `creado_en` -el instante de la
    transaccion-, y eso es lo que las emparenta en el historial.
    """
    origen = _sucursal_activa(db, datos.sucursal_origen_id)
    destino = _sucursal_activa(db, datos.sucursal_destino_id)
    _variantes_validas(db, [datos.variante_id])

    # Primero se mira sin bloquear, solo para poder dar un mensaje que nombre el
    # problema. Que la prenda nunca haya estado en esa sucursal no es lo mismo
    # que que no alcancen las unidades, y quien opera necesita distinguirlo.
    vistazo = repository.obtener_existencia(
        db, variante_id=datos.variante_id, sucursal_id=datos.sucursal_origen_id
    )
    if vistazo is None:
        raise ExistenciaInexistente()
    if vistazo.cantidad_disponible < datos.cantidad:
        raise StockInsuficiente(vistazo.cantidad_disponible, datos.cantidad)

    # LOS DOS BLOQUEOS SE TOMAN EN ORDEN ASCENDENTE DE SUCURSAL
    # ---------------------------------------------------------
    # Si cada transferencia bloqueara «primero el origen, despues el destino»,
    # dos transferencias cruzadas -de la 1 a la 2 y de la 2 a la 1, a la vez-
    # tomarian los mismos dos bloqueos en orden inverso y se esperarian
    # mutuamente para siempre: un interbloqueo. PostgreSQL lo detecta y mata a
    # una de las dos, pero la que muere es una transferencia legitima que
    # alguien tuvo que volver a cargar.
    #
    # Ordenar por identificador de sucursal lo vuelve imposible: dos
    # transacciones que compitan por el mismo par lo piden en el mismo orden,
    # asi que una espera a la otra y ninguna se traba.
    por_sucursal: dict[int, Existencia] = {}
    for sucursal_id in sorted((datos.sucursal_origen_id, datos.sucursal_destino_id)):
        por_sucursal[sucursal_id] = _existencia_o_crearla(
            db, variante_id=datos.variante_id, sucursal_id=sucursal_id
        )

    existencia_origen = por_sucursal[datos.sucursal_origen_id]
    existencia_destino = por_sucursal[datos.sucursal_destino_id]

    motivo = f"Transferencia {origen.nombre} → {destino.nombre}. {datos.motivo}"[:200]

    salida = _aplicar_movimiento(
        db,
        existencia_origen,
        tipo="TRANSFERENCIA",
        cantidad=-datos.cantidad,
        motivo=motivo,
        usuario_id=usuario_id,
    )
    entrada = _aplicar_movimiento(
        db,
        existencia_destino,
        tipo="TRANSFERENCIA",
        cantidad=datos.cantidad,
        motivo=motivo,
        usuario_id=usuario_id,
    )
    db.commit()

    return TransferenciaOut(
        salida=_fila_a_movimiento(repository.obtener_movimiento(db, salida.id)),
        entrada=_fila_a_movimiento(repository.obtener_movimiento(db, entrada.id)),
        origen=_fila_a_existencia(
            repository.obtener_existencia_con_detalle(db, existencia_origen.id)
        ),
        destino=_fila_a_existencia(
            repository.obtener_existencia_con_detalle(db, existencia_destino.id)
        ),
    )


def listar_movimientos(
    db: Session,
    *,
    pagina: int,
    tamano: int,
    sucursal_id: int | None = None,
    variante_id: int | None = None,
    tipo: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
) -> PaginaMovimientos:
    """Historial trazable que pide el RF22: que se movio, cuanto, por que,
    quien y cuando."""
    total = repository.contar_movimientos(
        db,
        sucursal_id=sucursal_id,
        variante_id=variante_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )
    filas = repository.listar_movimientos(
        db,
        pagina=pagina,
        tamano=tamano,
        sucursal_id=sucursal_id,
        variante_id=variante_id,
        tipo=tipo,
        desde=desde,
        hasta=hasta,
    )
    return PaginaMovimientos(
        total=total,
        pagina=pagina,
        tamano=tamano,
        items=[_fila_a_movimiento(fila) for fila in filas],
    )


# =====================================================================
# Costura C1 - lo que P5 le consume a P4
# =====================================================================
#
# Las firmas son las acordadas en la seccion 6 del documento de organizacion
# del ciclo. Karen las importa desde `catalogo_publico/service.py` para CU-19 y
# CU-14; no hace SELECT sobre `existencia` ni llamadas HTTP internas.
#
# Devuelven esquemas de este paquete, no filas de SQLAlchemy: si devolvieran
# `Row`, el contrato seria la forma de una consulta y cambiarla del lado de acá
# rompería la pantalla del otro lado sin que nada avisara.

def disponibilidad_por_sucursal(db: Session, variante_id: int) -> list[dict]:
    """CU-19: en que sucursales hay stock disponible de una variante.

    Forma acordada: [{sucursal_id, sucursal_nombre, ciudad_nombre,
    cantidad_disponible}].
    """
    return [
        {
            "sucursal_id": fila.sucursal_id,
            "sucursal_nombre": fila.sucursal_nombre,
            "ciudad_nombre": fila.ciudad_nombre,
            "cantidad_disponible": fila.cantidad_disponible,
        }
        for fila in repository.disponibilidad_por_sucursal(db, variante_id)
    ]


def inventario_consolidado(
    db: Session,
    *,
    sucursal_id: int | None = None,
    producto_id: int | None = None,
    solo_con_saldo: bool = False,
) -> list[ExistenciaOut]:
    """CU-14 y CU-16: existencias con la prenda y la sucursal ya resueltas."""
    return [
        _fila_a_existencia(fila)
        for fila in repository.inventario_consolidado(
            db,
            sucursal_id=sucursal_id,
            producto_id=producto_id,
            solo_con_saldo=solo_con_saldo,
        )
    ]
