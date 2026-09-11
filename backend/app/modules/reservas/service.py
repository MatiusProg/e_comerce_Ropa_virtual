"""
P6 - Reservas  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 2

Casos de uso que realiza este paquete:
  CU-22 Crear reserva de prendas
  CU-23 Consultar y cancelar reserva
  CU-24 Atender reserva en sucursal
  CU-25 Expirar reservas vencidas (proceso automatico)

Implementados en este archivo: CU-22 y CU-23.

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
    CancelarReservaIn,
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
