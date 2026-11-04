"""
P15 - Traspasos entre sucursales  |  capa: servicio

  CU-33 Solicitar traspaso entre sucursales   (RF-39, RF-40)
  CU-34 Atender traspaso                      (RF-41, RN-09)
  CU-35 Consultar traspasos sugeridos         (RF-42)

QUIÉN HACE CADA PASO
--------------------
  pedir      el ENCARGADO, para SU sucursal (el destino sale del token)
  ordenar    el ADMINISTRADOR, entre dos sucursales cualesquiera: nace APROBADO
  aprobar    el encargado del ORIGEN, que es quien da la mercadería
  enviar     el encargado del ORIGEN: descuenta del origen (RN-09)
  recibir    el encargado del DESTINO: suma al destino (RN-09)
  rechazar   el ORIGEN mientras no se envió; el DESTINO puede retirar su pedido
             mientras siga SOLICITADO
El administrador puede hacer cualquiera de los pasos, en cualquier sucursal.

RN-09, «NUNCA QUEDA EXISTENCIA NEGATIVA»
----------------------------------------
Lo cuida `_aplicar_movimiento` del inventario, el mismo que usa la venta: si al
enviar ya no alcanza, se rechaza el envío con el disponible a la vista y no se
escribe nada. Aprobar no aparta las unidades: entre aprobar y despachar se
puede vender, y es al despachar cuando las unidades salen de verdad.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.modules.inventario import repository as inventario_repo
from app.modules.inventario import service as inventario
from app.modules.notificaciones import service as notificaciones
from app.modules.traspasos import repository
from app.modules.traspasos.models import Traspaso
from app.modules.traspasos.schemas import (
    AprobarIn,
    OrigenPosibleOut,
    PaginaTraspasos,
    PrendaPedibleOut,
    PuntaSugerida,
    RechazarIn,
    SolicitarTraspasoIn,
    SucursalBreve,
    SugerenciasOut,
    TraspasoOut,
    TraspasoSugeridoOut,
)

ADMINISTRADOR = "ADMINISTRADOR"


class ErrorDeTraspaso(Exception):
    def __init__(self, mensaje: str, codigo: int = 409):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


@dataclass(frozen=True)
class Quien:
    """Lo que el servicio necesita saber de quien opera."""

    usuario_id: int
    rol: str
    sucursal_id: int | None

    @property
    def es_admin(self) -> bool:
        return self.rol == ADMINISTRADOR


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _traducir_inventario(error: inventario.ErrorDeInventario) -> ErrorDeTraspaso:
    if isinstance(error, inventario.SucursalInexistente):
        return ErrorDeTraspaso("La sucursal indicada no existe.", 404)
    if isinstance(error, inventario.SucursalInactiva):
        return ErrorDeTraspaso("La sucursal está dada de baja: no entra ni sale mercadería.", 422)
    if isinstance(error, inventario.VarianteInexistente):
        return ErrorDeTraspaso("La prenda indicada no existe.", 404)
    if isinstance(error, inventario.VarianteInactiva):
        return ErrorDeTraspaso("La prenda está desactivada en el catálogo.", 422)
    if isinstance(error, inventario.StockInsuficiente):
        return _sin_stock(error.disponible, error.solicitado)
    return ErrorDeTraspaso(str(error), 409)


def _sin_stock(disponible: int, pedido: int) -> ErrorDeTraspaso:
    return ErrorDeTraspaso(
        f"La sucursal de origen tiene {disponible} unidades disponibles y el traspaso "
        f"es de {pedido}. Ninguna sucursal puede quedar con existencia negativa (RN-09).",
        409,
    )


# =====================================================================
#  Permisos de cada paso
# =====================================================================

def _acciones(t: Traspaso, quien: Quien) -> list[str]:
    es_origen = quien.es_admin or quien.sucursal_id == t.sucursal_origen_id
    es_destino = quien.es_admin or quien.sucursal_id == t.sucursal_destino_id
    if t.estado == "SOLICITADO":
        return (["APROBAR"] if es_origen else []) + (
            ["RECHAZAR"] if es_origen or es_destino else []
        )
    if t.estado == "APROBADO":
        return ["ENVIAR", "RECHAZAR"] if es_origen else []
    if t.estado == "ENVIADO":
        return ["RECIBIR"] if es_destino else []
    return []


def _exigir(t: Traspaso, quien: Quien, accion: str) -> None:
    if accion in _acciones(t, quien):
        return
    if t.estado in ("RECIBIDO", "RECHAZADO"):
        raise ErrorDeTraspaso(f"El traspaso ya está {t.estado.lower()}: no admite cambios.", 409)
    esperados = {
        "APROBAR": ("SOLICITADO",),
        "RECHAZAR": ("SOLICITADO", "APROBADO"),
        "ENVIAR": ("APROBADO",),
        "RECIBIR": ("ENVIADO",),
    }[accion]
    if t.estado not in esperados:
        raise ErrorDeTraspaso(
            f"El traspaso está {t.estado.lower()} y no se puede {accion.lower()} en ese estado.",
            409,
        )
    raise ErrorDeTraspaso(
        "Este paso le corresponde a la otra sucursal del traspaso.", 403
    )


def _visible(t: Traspaso | None, quien: Quien) -> Traspaso:
    """El encargado solo ve los traspasos de su sucursal. Los demás no existen."""
    if t is None or not (
        quien.es_admin or quien.sucursal_id in (t.sucursal_origen_id, t.sucursal_destino_id)
    ):
        raise ErrorDeTraspaso("El traspaso no existe.", 404)
    return t


# =====================================================================
#  Lectura
# =====================================================================

def _a_salida(fila, quien: Quien) -> TraspasoOut:
    t: Traspaso = fila[0]
    return TraspasoOut(
        id=t.id,
        tipo=t.tipo,
        estado=t.estado,
        variante_id=t.variante_id,
        sku=fila.sku,
        prenda=fila.prenda,
        talla=fila.talla,
        color=fila.color,
        origen=SucursalBreve(id=t.sucursal_origen_id, nombre=fila.origen),
        destino=SucursalBreve(id=t.sucursal_destino_id, nombre=fila.destino),
        cantidad=t.cantidad,
        cantidad_solicitada=t.cantidad_solicitada,
        motivo=t.motivo,
        motivo_rechazo=t.motivo_rechazo,
        solicitado_por=fila.solicitado_por,
        creado_en=t.creado_en,
        aprobado_por=fila.aprobado_por,
        aprobado_en=t.aprobado_en,
        enviado_por=fila.enviado_por,
        enviado_en=t.enviado_en,
        recibido_por=fila.recibido_por,
        recibido_en=t.recibido_en,
        rechazado_por=fila.rechazado_por,
        rechazado_en=t.rechazado_en,
        acciones=_acciones(t, quien),
    )


def _detalle(db: Session, traspaso_id: int, quien: Quien) -> TraspasoOut:
    return _a_salida(repository.detalle(db, traspaso_id), quien)


def listar(
    db: Session,
    quien: Quien,
    *,
    bandeja: str | None,
    estado: str | None,
    abiertos: bool,
    sucursal_id: int | None,
    pagina: int,
    tamano: int,
) -> PaginaTraspasos:
    """El seguimiento (RF-41). El encargado ve solo los de su sucursal; el
    administrador, todos, o los de una sucursal si la filtra."""
    ambito = sucursal_id if quien.es_admin else quien.sucursal_id
    total, filas = repository.listar(
        db,
        sucursal_id=ambito,
        bandeja=bandeja if ambito is not None else None,
        estado=estado,
        abiertos=abiertos,
        pagina=pagina,
        tamano=tamano,
    )
    return PaginaTraspasos(
        total=total, pagina=pagina, tamano=tamano, items=[_a_salida(f, quien) for f in filas]
    )


def obtener(db: Session, quien: Quien, traspaso_id: int) -> TraspasoOut:
    _visible(repository.obtener(db, traspaso_id), quien)
    return _detalle(db, traspaso_id, quien)


def prendas_pedibles(db: Session, quien: Quien, busqueda: str | None) -> list[PrendaPedibleOut]:
    """Qué se puede pedir: lo que tienen las otras sucursales."""
    return [
        PrendaPedibleOut(
            variante_id=f.id, sku=f.sku, prenda=f.prenda, talla=f.talla, color=f.color,
            disponible=int(f.disponible),
        )
        for f in repository.prendas_en_otras(
            db, busqueda=busqueda, excluir=None if quien.es_admin else quien.sucursal_id
        )
    ]


def origenes_posibles(db: Session, quien: Quien, variante_id: int) -> list[OrigenPosibleOut]:
    """A quién se le puede pedir la prenda: las otras sucursales que la tienen."""
    return [
        OrigenPosibleOut(sucursal_id=f[0], sucursal=f[1], disponible=f[2])
        for f in repository.origenes_posibles(
            db, variante_id=variante_id, excluir=None if quien.es_admin else quien.sucursal_id
        )
    ]


# =====================================================================
#  CU-33 Solicitar traspaso entre sucursales
# =====================================================================

def solicitar(db: Session, quien: Quien, datos: SolicitarTraspasoIn) -> TraspasoOut:
    """El encargado lo pide para su sucursal (RF-39) o el administrador lo
    ordena sin pedido previo (RF-40)."""
    if quien.es_admin:
        if datos.sucursal_destino_id is None:
            raise ErrorDeTraspaso("Indique la sucursal de destino del traspaso.", 422)
        destino_id = datos.sucursal_destino_id
    else:
        if quien.sucursal_id is None:
            raise ErrorDeTraspaso("Su usuario no tiene una sucursal asignada.", 409)
        # El destino no se acepta del cuerpo: es la sucursal del encargado.
        if datos.sucursal_destino_id not in (None, quien.sucursal_id):
            raise ErrorDeTraspaso("Solo puede pedir mercadería para su propia sucursal.", 403)
        destino_id = quien.sucursal_id
    if destino_id == datos.sucursal_origen_id:
        raise ErrorDeTraspaso("La sucursal de origen y la de destino son la misma.", 422)

    try:
        origen = inventario._sucursal_activa(db, datos.sucursal_origen_id)
        destino = inventario._sucursal_activa(db, destino_id)
        inventario._variantes_validas(db, [datos.variante_id])
    except inventario.ErrorDeInventario as e:
        raise _traducir_inventario(e) from e

    disponible = repository.disponible(
        db, variante_id=datos.variante_id, sucursal_id=origen.id
    )
    if not disponible:
        raise ErrorDeTraspaso(f"La sucursal {origen.nombre} no tiene unidades de esa prenda.", 409)
    if disponible < datos.cantidad:
        raise _sin_stock(disponible, datos.cantidad)
    if repository.hay_abierto(
        db, variante_id=datos.variante_id, origen_id=origen.id, destino_id=destino.id
    ):
        raise ErrorDeTraspaso(
            f"Ya hay un traspaso de esa prenda de {origen.nombre} a {destino.nombre} sin "
            "despachar. Espere a que se atienda o pida que lo rechacen.",
            409,
        )

    ahora = _ahora()
    if quien.es_admin:
        tipo = "SUGERIDO" if datos.desde_sugerencia else "ORDEN"
        extra = dict(estado="APROBADO", aprobado_por=quien.usuario_id, aprobado_en=ahora)
    else:
        tipo = "PEDIDO"
        extra = dict(estado="SOLICITADO")

    t = repository.agregar(
        db,
        tipo=tipo,
        variante_id=datos.variante_id,
        sucursal_origen_id=origen.id,
        sucursal_destino_id=destino.id,
        cantidad=datos.cantidad,
        cantidad_solicitada=datos.cantidad,
        motivo=(datos.motivo or "").strip() or None,
        solicitado_por=quien.usuario_id,
        **extra,
    )
    etiqueta = inventario._etiqueta_de_variante(db, t.variante_id)
    if tipo == "PEDIDO":
        titulo = f"{destino.nombre} le pide {t.cantidad} de {etiqueta}"
        cuerpo = f"Traspaso #{t.id}: apruébelo o recházelo desde Traspasos."
    else:
        titulo = f"Envíe {t.cantidad} de {etiqueta} a {destino.nombre}"
        cuerpo = f"El administrador ordenó el traspaso #{t.id}. Despáchelo desde Traspasos."
    notificaciones.avisar_traspaso(
        db, t, sucursal_id=origen.id, titulo=titulo[:120], cuerpo=cuerpo
    )
    db.commit()
    return _detalle(db, t.id, quien)


# =====================================================================
#  CU-34 Atender traspaso
# =====================================================================

def _bloquear(db: Session, quien: Quien, traspaso_id: int, accion: str) -> Traspaso:
    t = _visible(repository.obtener(db, traspaso_id, bloquear=True), quien)
    try:
        _exigir(t, quien, accion)
    except ErrorDeTraspaso:
        db.rollback()
        raise
    return t


def aprobar(db: Session, quien: Quien, traspaso_id: int, datos: AprobarIn) -> TraspasoOut:
    t = _bloquear(db, quien, traspaso_id, "APROBAR")
    cantidad = datos.cantidad or t.cantidad
    if cantidad > t.cantidad_solicitada:
        db.rollback()
        raise ErrorDeTraspaso(
            f"Se pidieron {t.cantidad_solicitada}: no se puede aprobar más de lo pedido.", 422
        )
    disponible = repository.disponible(
        db, variante_id=t.variante_id, sucursal_id=t.sucursal_origen_id
    ) or 0
    if disponible < cantidad:
        db.rollback()
        raise _sin_stock(disponible, cantidad)
    t.cantidad = cantidad
    t.estado = "APROBADO"
    t.aprobado_por = quien.usuario_id
    t.aprobado_en = _ahora()
    db.commit()
    return _detalle(db, t.id, quien)


def rechazar(db: Session, quien: Quien, traspaso_id: int, datos: RechazarIn) -> TraspasoOut:
    t = _bloquear(db, quien, traspaso_id, "RECHAZAR")
    t.estado = "RECHAZADO"
    t.rechazado_por = quien.usuario_id
    t.rechazado_en = _ahora()
    t.motivo_rechazo = datos.motivo.strip()
    # Se avisa a la punta que NO rechazó.
    otra = (
        t.sucursal_origen_id
        if quien.sucursal_id == t.sucursal_destino_id
        else t.sucursal_destino_id
    )
    etiqueta = inventario._etiqueta_de_variante(db, t.variante_id)
    notificaciones.avisar_traspaso(
        db,
        t,
        sucursal_id=otra,
        titulo=f"Traspaso #{t.id} rechazado: {etiqueta}"[:120],
        cuerpo=f"Motivo: {t.motivo_rechazo}",
    )
    db.commit()
    return _detalle(db, t.id, quien)


def enviar(db: Session, quien: Quien, traspaso_id: int) -> TraspasoOut:
    """Despacha: las unidades salen del origen (RN-09) y quedan en camino."""
    t = _bloquear(db, quien, traspaso_id, "ENVIAR")
    origen = inventario_repo.obtener_sucursal(db, t.sucursal_origen_id)
    destino = inventario_repo.obtener_sucursal(db, t.sucursal_destino_id)
    if not origen.activa or not destino.activa:
        db.rollback()
        raise ErrorDeTraspaso(
            "Una de las dos sucursales fue dada de baja: rechace el traspaso.", 422
        )
    existencia = inventario_repo.obtener_existencia(
        db, variante_id=t.variante_id, sucursal_id=t.sucursal_origen_id, bloquear=True
    )
    if existencia is None:
        db.rollback()
        raise _sin_stock(0, t.cantidad)
    try:
        salida = inventario._aplicar_movimiento(
            db,
            existencia,
            tipo="TRANSFERENCIA",
            cantidad=-t.cantidad,
            motivo=f"Traspaso #{t.id} {origen.nombre} → {destino.nombre}: enviado"[:200],
            referencia=f"TRASPASO-{t.id}",
            usuario_id=quien.usuario_id,
        )
    except inventario.ErrorDeInventario as e:
        db.rollback()
        raise _traducir_inventario(e) from e
    t.estado = "ENVIADO"
    t.enviado_por = quien.usuario_id
    t.enviado_en = _ahora()
    t.movimiento_salida_id = salida.id
    etiqueta = inventario._etiqueta_de_variante(db, t.variante_id)
    notificaciones.avisar_traspaso(
        db,
        t,
        sucursal_id=destino.id,
        titulo=f"En camino: {t.cantidad} de {etiqueta}"[:120],
        cuerpo=f"{origen.nombre} despachó el traspaso #{t.id}. Confírmelo al recibirlo.",
    )
    db.commit()
    return _detalle(db, t.id, quien)


def recibir(db: Session, quien: Quien, traspaso_id: int) -> TraspasoOut:
    """Confirma la llegada: las unidades entran al destino (RN-09)."""
    t = _bloquear(db, quien, traspaso_id, "RECIBIR")
    origen = inventario_repo.obtener_sucursal(db, t.sucursal_origen_id)
    destino = inventario_repo.obtener_sucursal(db, t.sucursal_destino_id)
    existencia = inventario._existencia_o_crearla(
        db, variante_id=t.variante_id, sucursal_id=t.sucursal_destino_id
    )
    entrada = inventario._aplicar_movimiento(
        db,
        existencia,
        tipo="TRANSFERENCIA",
        cantidad=t.cantidad,
        motivo=f"Traspaso #{t.id} {origen.nombre} → {destino.nombre}: recibido"[:200],
        referencia=f"TRASPASO-{t.id}",
        usuario_id=quien.usuario_id,
    )
    t.estado = "RECIBIDO"
    t.recibido_por = quien.usuario_id
    t.recibido_en = _ahora()
    t.movimiento_entrada_id = entrada.id
    db.commit()
    return _detalle(db, t.id, quien)


# =====================================================================
#  CU-35 Consultar traspasos sugeridos
# =====================================================================

#: Tope de sugerencias: una pantalla que se pueda leer.
TOPE_SUGERENCIAS = 100


def sugeridos(db: Session, *, dias: int) -> SugerenciasOut:
    """Mover lo que sobra donde no se vende hacia donde se vende y falta (RF-42).

    Por prenda (variante) y sucursal, con las ventas cobradas de los últimos
    `dias`:

      objetivo   = max(vendidas en el período, punto de reposición)
      falta      = objetivo - disponible - lo que ya viene en camino
      sobra      = disponible - lo que ya prometió - objetivo

    Una sucursal es DESTINO si vendió la prenda y le falta; es ORIGEN si le
    sobra. El objetivo es cubrir otro período igual de ventas: si vendió 12 en
    30 días, debería tener 12. Se reparte primero a la que más vende, desde la
    que más le sobra. Lo que ya está en traspaso cuenta, para no sugerir dos
    veces lo mismo.
    """
    desde = _ahora() - timedelta(days=dias)
    vendidas: dict[tuple[int, int], int] = {
        (v, s): int(n) for v, s, n in repository.vendidas_por_sucursal(db, desde=desde)
    }
    variante_ids = sorted({v for v, _ in vendidas})
    items: list[TraspasoSugeridoOut] = []
    if variante_ids:
        sucursales = repository.sucursales_activas(db)
        saldos = repository.existencias_de(db, variante_ids)
        entrante, saliente = repository.en_traspaso(db, variante_ids)
        info = repository.variantes(db, variante_ids)

        por_variante: dict[int, list[PuntaSugerida]] = {}
        for variante_id, sucursal_id, disponible, minimo in saldos:
            clave = (variante_id, sucursal_id)
            por_variante.setdefault(variante_id, []).append(
                PuntaSugerida(
                    sucursal_id=sucursal_id,
                    sucursal=sucursales.get(sucursal_id, f"Sucursal {sucursal_id}"),
                    disponible=disponible,
                    vendidas=vendidas.get(clave, 0),
                    stock_minimo=minimo,
                    en_traspaso=0,
                )
            )

        for variante_id, puntas in por_variante.items():
            destinos, origenes = [], []
            for p in puntas:
                clave = (variante_id, p.sucursal_id)
                objetivo = max(p.vendidas, p.stock_minimo)
                falta = objetivo - p.disponible - entrante.get(clave, 0)
                sobra = p.disponible - saliente.get(clave, 0) - objetivo
                if p.vendidas > 0 and falta > 0:
                    destinos.append([p.model_copy(update={"en_traspaso": entrante.get(clave, 0)}), falta])
                elif sobra > 0:
                    origenes.append([p.model_copy(update={"en_traspaso": saliente.get(clave, 0)}), sobra])
            destinos.sort(key=lambda d: (-d[0].vendidas, d[0].sucursal))
            origenes.sort(key=lambda o: (-o[1], o[0].vendidas))
            for destino in destinos:
                for origen in origenes:
                    if destino[1] <= 0:
                        break
                    if origen[1] <= 0:
                        continue
                    cantidad = min(destino[1], origen[1])
                    destino[1] -= cantidad
                    origen[1] -= cantidad
                    d, o, v = destino[0], origen[0], info[variante_id]
                    items.append(
                        TraspasoSugeridoOut(
                            variante_id=variante_id,
                            sku=v.sku,
                            prenda=v.prenda,
                            talla=v.talla,
                            color=v.color,
                            origen=o,
                            destino=d,
                            cantidad_sugerida=cantidad,
                            razon=(
                                f"{d.sucursal} vendió {d.vendidas} en {dias} días y le "
                                f"quedan {d.disponible}; a {o.sucursal} le sobran "
                                f"(vendió {o.vendidas} y tiene {o.disponible})."
                            ),
                        )
                    )
        items.sort(key=lambda i: (-i.destino.vendidas, -i.cantidad_sugerida, i.sku))
    return SugerenciasOut(dias=dias, generado_en=_ahora(), items=items[:TOPE_SUGERENCIAS])
