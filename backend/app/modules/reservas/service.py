"""
P6 - Reservas  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Implementados en este archivo: CU-22, CU-23, CU-24 y CU-25.

Regla: aqui viven las reglas de negocio y el control de la transaccion. El
servicio orquesta repositorios; nunca conoce el objeto Request de HTTP.

QUIEN TOCA EL STOCK
-------------------
Este modulo **no** escribe `existencia` ni `movimiento_inventario`. Llama a
`inventario.service.apartar_para_reserva()`, que es donde vive el bloqueo del
riesgo R5 y la regla «ninguna cantidad se modifica sin generar un movimiento».
La direccion P6 -> P4 es la permitida por la seccion 2 de
docs/04-analisis-arquitectura.md.

Lo que P6 sí controla es **la transaccion**: se aparta el stock de todas las
lineas y se escribe la reserva entera, y recien ahi se confirma. Un fallo en la
linea tres deshace las dos anteriores, y eso importa mas aca que en un ingreso:
stock apartado sin reserva que lo explique no lo libera nadie --- CU-25 expira
reservas, y eso no seria una.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.inventario import service as inventario
from app.modules.reservas import repository
from app.modules.reservas.repository import ESTADOS_VIVOS
from app.modules.reservas.schemas import (
    DURACION_MAXIMA_MINUTOS,
    DURACION_MINIMA_MINUTOS,
    AtenderReservaIn,
    CancelarReservaIn,
    ExpiracionOut,
    LineaReservaOut,
    PaginaReservas,
    ReservaCrearIn,
    ReservaOut,
    ReservaResumenOut,
)

#: Estado con el que nace una reserva. El Encargado la pasa a PREPARADA en
#: CU-24; ver el diagrama de transiciones en `models.py`.
ESTADO_INICIAL = "PENDIENTE"

#: Tolerancia para el reloj del cliente.
#:
#: El navegador y el servidor casi nunca coinciden al segundo, y una reserva
#: para «dentro de un minuto» se rechazaria por unos pocos segundos de desfase.
#: Dos minutos alcanzan para eso sin permitir reservar en el pasado de verdad.
TOLERANCIA_RELOJ = timedelta(minutes=2)


# --- Errores de negocio --------------------------------------------------
# El servicio no habla HTTP: senala el problema con una excepcion propia y el
# router la traduce al codigo de estado que corresponda.

class ErrorDeReservas(Exception):
    """Base de los errores previstos de P6."""


class ClienteSinFicha(ErrorDeReservas):
    """La cuenta tiene rol CLIENTE pero no tiene ficha de cliente."""


class SucursalInexistente(ErrorDeReservas):
    """La sucursal indicada no existe."""


class SucursalInactiva(ErrorDeReservas):
    """Excepcion E2: no se reserva en una sucursal dada de baja."""


class VarianteInexistente(ErrorDeReservas):
    """Excepcion E1: alguna prenda de la reserva no existe."""

    def __init__(self, ids: list[int]):
        self.ids = ids
        super().__init__(f"Variantes inexistentes: {ids}")


class VarianteInactiva(ErrorDeReservas):
    """Excepcion E1: la prenda existe pero dejo de ofrecerse."""

    def __init__(self, ids: list[int]):
        self.ids = ids
        super().__init__(f"Variantes desactivadas: {ids}")


class FranjaEnElPasado(ErrorDeReservas):
    """Excepcion E3."""


class FranjaDemasiadoLejos(ErrorDeReservas):
    """Excepcion E5: mas alla de la anticipacion maxima."""

    def __init__(self, horas: int):
        self.horas = horas
        super().__init__(f"Maximo {horas} horas de anticipacion")


class DuracionInvalida(ErrorDeReservas):
    """Excepcion E4: la franja dura menos del minimo o mas del maximo."""

    def __init__(self, minimo: int, maximo: int):
        self.minimo = minimo
        self.maximo = maximo
        super().__init__(f"Entre {minimo} y {maximo} minutos")


class FueraDeHorario(ErrorDeReservas):
    """Excepcion E8: la franja cae fuera del horario de atencion."""

    def __init__(self, apertura, cierre):
        self.apertura = apertura
        self.cierre = cierre
        super().__init__(f"Atiende de {apertura} a {cierre}")


class SinVestidoresLibres(ErrorDeReservas):
    """Excepcion E6: la sucursal no tiene probador libre en esa franja."""

    def __init__(self, capacidad: int):
        self.capacidad = capacidad
        super().__init__(f"Capacidad {capacidad}")


class ReservaInexistente(ErrorDeReservas):
    """No hay reserva con ese identificador."""


class ReservaAjena(ErrorDeReservas):
    """La reserva existe pero es de otro cliente."""


class ReservaDeOtraSucursal(ErrorDeReservas):
    """El Encargado quiso tocar una reserva que no es de su local."""


class ReservaNoAtendible(ErrorDeReservas):
    """La reserva ya no esta viva y no se puede preparar ni atender."""

    def __init__(self, estado: str):
        self.estado = estado
        super().__init__(f"Estado {estado}")


class ResultadosIncompletos(ErrorDeReservas):
    """Excepcion E11: faltan o sobran resultados respecto de las lineas.

    Lleva las dos diferencias para que el mensaje pueda decir cual de las dos
    cosas pasa: olvidarse de una prenda y mandar una que no es de esa reserva
    son errores distintos.
    """

    def __init__(self, faltantes: list[int], ajenos: list[int]):
        self.faltantes = faltantes
        self.ajenos = ajenos
        super().__init__(f"Faltan {faltantes}, sobran {ajenos}")


class ReservaNoCancelable(ErrorDeReservas):
    """Excepcion E10: la reserva ya no esta viva.

    Lleva el estado en el que quedo para que el mensaje pueda decir POR QUE no
    se puede: «ya fue atendida» y «ya la cancelaste» llevan a acciones
    distintas.
    """

    def __init__(self, estado: str):
        self.estado = estado
        super().__init__(f"Estado {estado}")


# --- Validacion de la franja ---------------------------------------------

def _ahora() -> datetime:
    """El instante actual, siempre con zona horaria.

    Se centraliza para que ninguna comparacion mezcle un `datetime` con zona
    --- que es lo que llega del cliente y lo que guarda `timestamptz` --- con
    uno sin zona, que en Python es un TypeError en tiempo de ejecucion.
    """
    return datetime.now(timezone.utc)


def _validar_franja(datos: ReservaCrearIn, sucursal) -> None:
    """Las cinco condiciones que tiene que cumplir una franja.

    Se valida contra el horario de la sucursal y no solo contra el reloj: una
    reserva a las tres de la mañana es sintacticamente correcta y no la va a
    atender nadie. `sucursal.horario_apertura` y `horario_cierre` existen desde
    el Ciclo 1 y hasta ahora no los usaba ningun caso de uso.
    """
    ahora = _ahora()

    # E3. `franja_fin > franja_inicio` ya lo garantiza el CHECK de la base y el
    # esquema; lo que hace falta acá es que no sea en el pasado.
    if datos.franja_inicio < ahora - TOLERANCIA_RELOJ:
        raise FranjaEnElPasado()

    # E5.
    limite = ahora + timedelta(hours=settings.RESERVA_ANTICIPACION_MAXIMA_HORAS)
    if datos.franja_inicio > limite:
        raise FranjaDemasiadoLejos(settings.RESERVA_ANTICIPACION_MAXIMA_HORAS)

    # E4.
    duracion = datos.franja_fin - datos.franja_inicio
    if not (
        timedelta(minutes=DURACION_MINIMA_MINUTOS)
        <= duracion
        <= timedelta(minutes=DURACION_MAXIMA_MINUTOS)
    ):
        raise DuracionInvalida(DURACION_MINIMA_MINUTOS, DURACION_MAXIMA_MINUTOS)

    # E8. Se compara la hora LOCAL de la franja, tal como la mando el cliente:
    # `horario_apertura` es un `TIME` sin zona y representa la hora de pared de
    # esa tienda. Convertir a UTC antes de comparar haria que una sucursal que
    # abre a las 09:00 rechazara una reserva a las 09:30 por cuatro horas de
    # diferencia horaria.
    inicio_local = datos.franja_inicio.timetz()
    fin_local = datos.franja_fin.timetz()
    if (
        inicio_local.replace(tzinfo=None) < sucursal.horario_apertura
        or fin_local.replace(tzinfo=None) > sucursal.horario_cierre
    ):
        raise FueraDeHorario(sucursal.horario_apertura, sucursal.horario_cierre)


# --- Armado de la salida -------------------------------------------------

def _armar_reserva(db: Session, reserva_id: int) -> ReservaOut:
    """Lee la reserva recien escrita y la devuelve con su detalle."""
    cabecera = repository.obtener_reserva(db, reserva_id)
    if cabecera is None:
        raise ReservaInexistente()

    lineas = [
        LineaReservaOut(
            id=fila.id,
            variante_id=fila.variante_id,
            sku=fila.sku,
            producto=fila.producto,
            talla=fila.talla,
            color=fila.color,
            cantidad=fila.cantidad,
            resultado_prueba=fila.resultado_prueba,
        )
        for fila in repository.listar_detalles(db, reserva_id)
    ]

    return ReservaOut(
        id=cabecera.id,
        cliente_id=cabecera.cliente_id,
        sucursal_id=cabecera.sucursal_id,
        sucursal=cabecera.sucursal,
        ciudad=cabecera.ciudad,
        franja_inicio=cabecera.franja_inicio,
        franja_fin=cabecera.franja_fin,
        estado=cabecera.estado,
        observacion=cabecera.observacion,
        creado_en=cabecera.creado_en,
        unidades=sum(linea.cantidad for linea in lineas),
        lineas=lineas,
    )


# =====================================================================
# CU-22 - Crear reserva de prendas
# =====================================================================

def crear_reserva(
    db: Session, datos: ReservaCrearIn, *, usuario_id: int
) -> ReservaOut:
    """Pasos 4 a 7: aparta las prendas y deja la reserva en PENDIENTE.

    EL ORDEN DE LAS COMPROBACIONES NO ES CASUAL
    -------------------------------------------
    Primero va todo lo que se puede rechazar **sin tocar ninguna fila**
    --- cliente, sucursal, franja, prendas, capacidad del probador --- y recien
    al final se aparta el stock, que es lo unico que toma bloqueos. Al reves,
    una reserva con la franja mal escrita tendria tomada la existencia de tres
    variantes mientras se descubre el error, haciendo esperar a quien si estaba
    reservando bien.
    """
    cliente = repository.obtener_cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise ClienteSinFicha()

    sucursal = repository.obtener_sucursal(db, datos.sucursal_id)
    if sucursal is None:
        raise SucursalInexistente()
    if not sucursal.activa:
        raise SucursalInactiva()

    _validar_franja(datos, sucursal)

    # E1: las prendas existen y siguen ofreciendose.
    ids = [linea.variante_id for linea in datos.lineas]
    filas = repository.listar_variantes(db, ids)
    por_id = {fila.variante_id: fila for fila in filas}

    faltantes = [i for i in ids if i not in por_id]
    if faltantes:
        raise VarianteInexistente(faltantes)
    inactivas = [i for i in ids if not por_id[i].activa]
    if inactivas:
        raise VarianteInactiva(inactivas)

    # E6: el probador tiene capacidad finita.
    #
    # Es la regla que vuelve util a `sucursal.capacidad_vestidores`, declarada
    # en el Ciclo 1 y sin ningun caso de uso que la leyera. Sin esto, veinte
    # clientes pueden reservar la misma franja en una tienda con dos probadores
    # y el sistema promete algo que la sucursal no puede cumplir.
    solapadas = repository.contar_reservas_solapadas(
        db,
        sucursal_id=sucursal.id,
        inicio=datos.franja_inicio,
        fin=datos.franja_fin,
    )
    if solapadas >= sucursal.capacidad_vestidores:
        raise SinVestidoresLibres(sucursal.capacidad_vestidores)

    # --- A partir de aca se escribe -------------------------------------
    reserva = repository.agregar_reserva(
        db,
        cliente_id=cliente.id,
        sucursal_id=sucursal.id,
        franja_inicio=datos.franja_inicio,
        franja_fin=datos.franja_fin,
        estado=ESTADO_INICIAL,
        # Nace sin observacion: esa columna es la nota de CIERRE, y la escriben
        # CU-23 al cancelar y CU-24 al atender. Ver la nota en `schemas.py`.
        observacion=None,
    )

    motivo = f"Reserva #{reserva.id} de {sucursal.nombre}"[:200]

    try:
        for linea in datos.lineas:
            # Cada llamada toma el FOR UPDATE de SU existencia. Si la tercera
            # no tiene stock, el `except` deshace las dos primeras y se sueltan
            # los tres bloqueos juntos al terminar la transaccion.
            inventario.apartar_para_reserva(
                db,
                variante_id=linea.variante_id,
                sucursal_id=sucursal.id,
                cantidad=linea.cantidad,
                usuario_id=usuario_id,
                motivo=motivo,
            )
            repository.agregar_detalle(
                db,
                reserva_id=reserva.id,
                variante_id=linea.variante_id,
                cantidad=linea.cantidad,
            )
    except inventario.ErrorDeInventario:
        # Se deshace TODO, incluida la cabecera. Dejar la reserva creada con
        # media mercaderia apartada seria lo peor de los dos mundos: stock
        # inmovilizado y una reserva que no se puede atender.
        db.rollback()
        raise

    db.commit()
    return _armar_reserva(db, reserva.id)


# =====================================================================
# CU-23 - Consultar y cancelar reserva
# =====================================================================

def cancelar_reserva(
    db: Session, reserva_id: int, datos: CancelarReservaIn, *, usuario_id: int
) -> ReservaOut:
    """Cancela una reserva propia y devuelve el stock apartado.

    Realiza el **RF29**: sin cancelacion, el stock queda retenido hasta que la
    franja venza y CU-25 la expire --- o sea, hasta un dia entero de mercaderia
    inmovilizada porque alguien cambio de planes.

    LA RESERVA SE TOMA CON `FOR UPDATE`, Y NO ES DECORATIVO
    ------------------------------------------------------
    Si el cliente pulsa «cancelar» dos veces, o lo hace desde la web y el
    telefono a la vez, las dos peticiones leerian la reserva en PENDIENTE, las
    dos pasarian la comprobacion de estado y las dos liberarian el stock: el
    saldo terminaria con MAS unidades de las que hay en la tienda. Es el riesgo
    R5 visto del otro lado --- alli era vender de mas, aqui es inventar
    mercaderia --- y se resuelve con el mismo mecanismo.

    Con el bloqueo, la segunda peticion espera a que la primera confirme, vuelve
    a leer --- ahora CANCELADA --- y se rechaza sola con la excepcion E10.
    """
    cliente = repository.obtener_cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise ClienteSinFicha()

    reserva = repository.obtener_reserva_entidad(db, reserva_id, bloquear=True)
    if reserva is None:
        raise ReservaInexistente()
    if reserva.cliente_id != cliente.id:
        raise ReservaAjena()

    # E10. Se comprueba DESPUES de tomar el bloqueo, no antes: comprobarlo antes
    # seria leer un estado que puede cambiar entre la lectura y la escritura,
    # que es exactamente el agujero que el bloqueo viene a cerrar.
    if reserva.estado not in ESTADOS_VIVOS:
        raise ReservaNoCancelable(reserva.estado)

    motivo = f"Cancelacion de la reserva #{reserva.id}"
    if datos.motivo:
        motivo = f"{motivo}. {datos.motivo}"

    # Se libera prenda por prenda. Cada llamada toma el FOR UPDATE de SU
    # existencia y escribe su movimiento de LIBERACION.
    for detalle in repository.detalles_de(db, reserva.id):
        inventario.liberar_de_reserva(
            db,
            variante_id=detalle.variante_id,
            sucursal_id=reserva.sucursal_id,
            cantidad=detalle.cantidad,
            usuario_id=usuario_id,
            motivo=motivo[:200],
        )

    reserva.estado = "CANCELADA"
    reserva.observacion = (datos.motivo or "Cancelada por el cliente")[:200]
    db.commit()

    return _armar_reserva(db, reserva.id)


# =====================================================================
# CU-24 - Atender reserva en sucursal
# =====================================================================

def _reserva_de_la_sucursal(
    db: Session, reserva_id: int, *, sucursal_id: int | None, bloquear: bool = True
):
    """La reserva, comprobando que sea del local de quien pregunta.

    `sucursal_id` en None significa Administrador: su ambito es toda la red.

    Se resuelve **leyendo la fila**, igual que en CU-16: el identificador de la
    URL no dice a que sucursal pertenece, y sin este paso a un Encargado le
    bastaria probar numeros para cerrar reservas de otro local.
    """
    reserva = repository.obtener_reserva_entidad(db, reserva_id, bloquear=bloquear)
    if reserva is None:
        raise ReservaInexistente()
    if sucursal_id is not None and reserva.sucursal_id != sucursal_id:
        raise ReservaDeOtraSucursal()
    return reserva


def preparar_reserva(
    db: Session, reserva_id: int, *, sucursal_id: int | None
) -> ReservaOut:
    """PENDIENTE -> PREPARADA. El Encargado ya junto las prendas.

    **No mueve stock**, y es la unica transicion de la reserva que no lo hace:
    las unidades ya estaban apartadas desde CU-22 y siguen estandolo. Lo unico
    que cambia es que alguien las fue a buscar a la percha.

    Tampoco impide que el cliente cancele: PREPARADA sigue siendo un estado vivo
    y el RF29 le deja cancelar hasta que se atienda (CU-23).
    """
    reserva = _reserva_de_la_sucursal(db, reserva_id, sucursal_id=sucursal_id)

    if reserva.estado != "PENDIENTE":
        raise ReservaNoAtendible(reserva.estado)

    reserva.estado = "PREPARADA"
    db.commit()
    return _armar_reserva(db, reserva.id)


def atender_reserva(
    db: Session,
    reserva_id: int,
    datos: AtenderReservaIn,
    *,
    sucursal_id: int | None,
    usuario_id: int,
) -> ReservaOut:
    """Cierra la reserva con el resultado de la prueba. -> ATENDIDA.

    QUE PASA CON EL STOCK, PRENDA POR PRENDA
    ----------------------------------------
    **NO_LLEVA**: una `LIBERACION` de +n. Las unidades vuelven al disponible y
    la reserva las suelta. Es el mismo movimiento que una cancelacion.

    **LLEVA**: una `LIBERACION` de +n **y** una `VENTA` de -n. Parece un rodeo
    y es a proposito: esas unidades ya habian salido del disponible al crearse
    la reserva, asi que una VENTA de -n a secas las descontaria dos veces y
    dejaria el saldo en negativo; y un movimiento de cero lo rechaza el CHECK
    `cantidad_no_nula`. Con los dos, el neto sobre el disponible es cero, el
    invariante `disponible == suma(movimientos)` se sostiene, y el historial se
    lee como lo que paso: «volvieron del apartado y se vendieron».

    SOBRE LA DECISION D3 Y EL CICLO 3
    ---------------------------------
    D3 dice que «la venta descuenta de reservado si vino de una reserva». Eso
    describe el mundo del Ciclo 3, donde el punto de venta existe y el cobro
    ocurre en el mismo acto. En el Ciclo 2 no hay entidad `Venta` todavia, y
    habia que elegir entre dos males:

      a) dejar las unidades de LLEVA en `cantidad_reservada` esperando una venta
         que en este ciclo no puede ocurrir --- y que nadie liberaria despues,
         porque la reserva ya estaria ATENDIDA y CU-25 solo expira las vivas ---;
      b) descontarlas ahora, que es lo que de verdad paso: la prenda salio de la
         tienda con el cliente.

    Se eligio (b). El inventario queda diciendo la verdad y no hay stock
    atrapado. **Cuando P7 exista, CU-24 y el cobro pasan a ser una sola
    transaccion** y el movimiento de VENTA lo va a escribir la venta, no este
    caso de uso; hasta entonces lo escribe aca, con el motivo que lo explica.
    """
    reserva = _reserva_de_la_sucursal(db, reserva_id, sucursal_id=sucursal_id)

    if reserva.estado not in ESTADOS_VIVOS:
        raise ReservaNoAtendible(reserva.estado)

    detalles = repository.detalles_de(db, reserva.id)
    por_id = {detalle.id: detalle for detalle in detalles}
    enviados = {r.detalle_id: r.resultado for r in datos.resultados}

    # E11. Tienen que venir TODAS las lineas y ninguna ajena: si faltara una,
    # sus unidades quedarian apartadas en una reserva ya cerrada y no las
    # liberaria nadie.
    faltantes = sorted(set(por_id) - set(enviados))
    ajenos = sorted(set(enviados) - set(por_id))
    if faltantes or ajenos:
        raise ResultadosIncompletos(faltantes, ajenos)

    for detalle in detalles:
        resultado = enviados[detalle.id]
        if resultado == "LLEVA":
            motivo = f"Reserva #{reserva.id} atendida, el cliente se la lleva"
        else:
            motivo = f"Reserva #{reserva.id} atendida, prenda devuelta a la percha"
        motivo = motivo[:200]

        # Siempre se libera: la reserva suelta lo que tenia apartado.
        inventario.liberar_de_reserva(
            db,
            variante_id=detalle.variante_id,
            sucursal_id=reserva.sucursal_id,
            cantidad=detalle.cantidad,
            usuario_id=usuario_id,
            motivo=motivo,
        )

        if resultado == "LLEVA":
            inventario.descontar_por_venta(
                db,
                variante_id=detalle.variante_id,
                sucursal_id=reserva.sucursal_id,
                cantidad=detalle.cantidad,
                usuario_id=usuario_id,
                motivo=motivo,
            )

        detalle.resultado_prueba = resultado

    reserva.estado = "ATENDIDA"
    if datos.observacion:
        reserva.observacion = datos.observacion
    db.commit()

    return _armar_reserva(db, reserva.id)


def listar_reservas_de_sucursal(
    db: Session,
    *,
    sucursal_id: int | None,
    pagina: int,
    tamano: int,
    estado: str | None = None,
    vivas: bool | None = None,
) -> PaginaReservas:
    """El panel del Encargado: las reservas de su local, la mas proxima arriba.

    Ordena al reves que «mis reservas» del Cliente, y es correcto: el Cliente
    mira un historial y el Encargado mira una agenda.
    """
    total = repository.contar_reservas(
        db, sucursal_id=sucursal_id, estado=estado, vivas=vivas
    )
    filas = repository.listar_reservas(
        db,
        pagina=pagina,
        tamano=tamano,
        sucursal_id=sucursal_id,
        estado=estado,
        vivas=vivas,
        proximas_primero=True,
    )
    return PaginaReservas(
        total=total,
        pagina=pagina,
        tamano=tamano,
        items=[
            ReservaResumenOut.model_validate(fila, from_attributes=True)
            for fila in filas
        ],
    )


def obtener_reserva_de_sucursal(
    db: Session, reserva_id: int, *, sucursal_id: int | None
) -> ReservaOut:
    """El detalle de una reserva del local, para prepararla o atenderla."""
    _reserva_de_la_sucursal(db, reserva_id, sucursal_id=sucursal_id, bloquear=False)
    return _armar_reserva(db, reserva_id)


# =====================================================================
# CU-25 - Expirar reservas vencidas  (proceso automatico, actor A6)
# =====================================================================

#: Cuantas reservas procesa una corrida como maximo.
#:
#: Sin tope, la primera ejecucion sobre una base con meses de historial abriria
#: una transaccion enorme y mantendria bloqueadas miles de filas. Doscientas
#: alcanzan de sobra para el ritmo real de una tienda, y si quedaran mas, la
#: siguiente corrida las toma.
TOPE_POR_CORRIDA = 200


def expirar_reservas_vencidas(
    db: Session, *, tope: int = TOPE_POR_CORRIDA
) -> ExpiracionOut:
    """Devuelve al inventario el stock de las reservas que nadie fue a buscar.

    Realiza el **RF30**. Es el unico caso de uso del sistema cuyo actor es
    **A6, el Sistema**: no lo inicia una persona, y por eso los movimientos que
    deja llevan `usuario_id` nulo --- que es exactamente para lo que esa columna
    admite nulo, segun la nota de `inventario/models.py`.

    CUANDO SE CONSIDERA VENCIDA
    ---------------------------
    No basta con que la franja haya terminado: se espera ademas
    `RESERVA_VIGENCIA_HORAS` mas. Esa tolerancia existe para el cliente que
    llega tarde --- o al dia siguiente --- y encuentra su reserva todavia en
    pie. El precio es tener stock retenido ese rato, y por eso es una variable
    de entorno y no una constante: una tienda con poco inventario va a querer
    bajarla.

    POR QUE SE VUELVE A COMPROBAR EL ESTADO
    ---------------------------------------
    La consulta ya filtra por estados vivos, pero entre que devuelve las filas y
    que se procesan pudo cancelarse alguna. El bloqueo de la consulta lo impide
    para las filas que tomo, asi que la comprobacion es cinturon y tirantes; se
    deja igual porque el costo de equivocarse aca es liberar stock dos veces, y
    eso inventa mercaderia.

    **Es idempotente**: correrla dos veces seguidas no libera nada la segunda
    vez, porque las reservas ya quedaron EXPIRADA.
    """
    corte = _ahora() - timedelta(hours=settings.RESERVA_VIGENCIA_HORAS)
    vencidas = repository.listar_vencidas(db, corte=corte, tope=tope)

    expiradas: list[int] = []
    unidades = 0

    for reserva in vencidas:
        if reserva.estado not in ESTADOS_VIVOS:
            continue

        for detalle in repository.detalles_de(db, reserva.id):
            inventario.liberar_de_reserva(
                db,
                variante_id=detalle.variante_id,
                sucursal_id=reserva.sucursal_id,
                cantidad=detalle.cantidad,
                # Nulo a proposito: no hay persona detras de esta operacion.
                usuario_id=None,
                motivo=f"Reserva #{reserva.id} expirada sin atencion"[:200],
            )
            unidades += detalle.cantidad

        reserva.estado = "EXPIRADA"
        reserva.observacion = "Expirada: la franja venció sin que el cliente asistiera."
        expiradas.append(reserva.id)

    # Un solo commit al final: o la corrida entera cuadra o no se escribe nada.
    # Con un commit por reserva, un fallo a mitad dejaria media tanda expirada y
    # la otra media con los bloqueos sueltos y el stock sin devolver.
    db.commit()

    return ExpiracionOut(
        encontradas=len(vencidas),
        expiradas=len(expiradas),
        unidades_liberadas=unidades,
        reservas=expiradas,
        corte=corte,
    )


# --- Consultas -----------------------------------------------------------

def obtener_reserva_de_cliente(
    db: Session, reserva_id: int, *, usuario_id: int
) -> ReservaOut:
    """Una reserva, solo si es de quien la pide.

    Se comprueba la propiedad **aca** y no en el router porque hace falta leer
    la fila para saber de quien es. Devolver 404 en vez de 403 cuando es ajena
    es deliberado: un 403 confirmaria que esa reserva existe, y eso ya es
    informacion sobre otro cliente.
    """
    cliente = repository.obtener_cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise ClienteSinFicha()

    cabecera = repository.obtener_reserva(db, reserva_id)
    if cabecera is None:
        raise ReservaInexistente()
    if cabecera.cliente_id != cliente.id:
        raise ReservaAjena()

    return _armar_reserva(db, reserva_id)


def listar_mis_reservas(
    db: Session,
    *,
    usuario_id: int,
    pagina: int,
    tamano: int,
    estado: str | None = None,
    vivas: bool | None = None,
) -> PaginaReservas:
    """Las reservas del cliente que pregunta, de la mas proxima a la mas vieja."""
    cliente = repository.obtener_cliente_de_usuario(db, usuario_id)
    if cliente is None:
        raise ClienteSinFicha()

    total = repository.contar_reservas(
        db, cliente_id=cliente.id, estado=estado, vivas=vivas
    )
    filas = repository.listar_reservas(
        db,
        pagina=pagina,
        tamano=tamano,
        cliente_id=cliente.id,
        estado=estado,
        vivas=vivas,
    )
    return PaginaReservas(
        total=total,
        pagina=pagina,
        tamano=tamano,
        items=[ReservaResumenOut.model_validate(fila, from_attributes=True) for fila in filas],
    )
