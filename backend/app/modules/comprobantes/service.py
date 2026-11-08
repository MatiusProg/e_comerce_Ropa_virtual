"""
P16 - Mis comprobantes / CU-46 Consultar mis comprobantes por voz  |  capa: servicio

El cliente pide, hablando o escribiendo, «mis últimas 3 compras», «mis recibos
de octubre» o «mis devoluciones», y recibe la lista: cada comprobante con su
fecha, número, total y estado, y el token de su verificación pública para el QR.

QUÉ REUSA
---------
- El intérprete de reglas de CU-27 (`reportes.interprete_reglas`) para los
  períodos; ver `interprete.py`. **Sin IA**: no gasta el cupo de la tienda.
- El número del recibo de CU-29 (`historial_service._numero_de`): una compra
  pagada cuyo recibo todavía no se descargó muestra el número que va a tener,
  que es el mismo porque se deriva del id de la venta. **La consulta no emite
  nada**: es una lectura.
- La nota de devolución de CU-22/CU-25 (`ND-000007`).

AISLAMIENTO
-----------
El cliente sale del token (nunca del cuerpo), las consultas filtran por su
`cliente_id`, el RLS las limita a la empresa de la sesión, y además se exige
que el cliente esté asociado a la tienda en `cliente_empresa`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core import tiempo
from app.core.tenencia import fijar_empresa
from app.modules.comprobantes import interprete
from app.modules.comprobantes import repository
from app.modules.comprobantes import verificacion
from app.modules.comprobantes.schemas import (
    ComprobanteOut,
    ConsultaOut,
    CriterioOut,
    VerificacionOut,
)
from app.modules.plataforma.models import Empresa
from app.modules.ventas import service as ventas_service
from app.modules.ventas.historial_service import ESTADOS_CON_COMPROBANTE

FORMATO_FECHA = "%d/%m/%Y %H:%M"


class ComprobanteInexistente(Exception):
    """El token no es válido o el comprobante no existe. El router da 404."""


def _numero_recibo(venta_id: int) -> str:
    # El mismo formato que `historial_service._numero_de`, que necesita la
    # venta entera; acá basta el id.
    return f"R-{venta_id:08d}"


def _detalle_compra(fila) -> str:
    if fila.canal == "PRESENCIAL":
        return f"Venta en mostrador · {fila.sucursal}"
    if fila.modalidad_entrega == "ENVIO":
        return "Envío a domicilio"
    return f"Retiro en {fila.sucursal}"


def _compra(fila) -> ComprobanteOut:
    con_recibo = fila.estado in ESTADOS_CON_COMPROBANTE
    token = verificacion.firmar(verificacion.RECIBO, fila.empresa_id, fila.id) if con_recibo else None
    momento = fila.creado_en
    return ComprobanteOut(
        tipo="COMPRA",
        documento="RECIBO" if con_recibo else None,
        codigo=(fila.comprobante_numero or _numero_recibo(fila.id)) if con_recibo else fila.codigo,
        referencia=fila.codigo,
        fecha=tiempo.en_bolivia(momento),
        fecha_texto=tiempo.formatear(momento, FORMATO_FECHA),
        total=fila.total,
        estado=fila.estado,
        detalle=_detalle_compra(fila),
        token=token,
        url_verificacion=verificacion.url_publica(token) if token else None,
        descargable=con_recibo,
    )


def _devolucion(fila) -> ComprobanteOut:
    token = verificacion.firmar(verificacion.NOTA, fila.empresa_id, fila.id)
    cambio = fila.tipo == "CAMBIO"
    return ComprobanteOut(
        tipo="DEVOLUCION",
        documento="NOTA_CAMBIO" if cambio else "NOTA_DEVOLUCION",
        codigo=f"ND-{fila.id:06d}",
        referencia=fila.venta_codigo,
        fecha=tiempo.en_bolivia(fila.creado_en),
        fecha_texto=tiempo.formatear(fila.creado_en, FORMATO_FECHA),
        total=Decimal(fila.valor_devuelto or 0).quantize(Decimal("0.01")),
        estado=fila.estado,
        detalle=f"{'Cambio' if cambio else 'Devolución'} de {fila.venta_codigo} · {fila.sucursal}",
        token=token,
        url_verificacion=verificacion.url_publica(token),
        descargable=False,
    )


def _no_entendido(motivo: str) -> ConsultaOut:
    return ConsultaOut(entendido=False, motivo=motivo, ejemplos=interprete.EJEMPLOS)


def consultar(db: Session, usuario_id: int, texto: str) -> ConsultaOut:
    """Interpreta el pedido y devuelve los comprobantes del cliente. Solo lee."""
    cliente_id = ventas_service._cliente(db, usuario_id)

    criterio = interprete.interpretar(texto, tiempo.hoy())
    if criterio is None:
        return _no_entendido(
            "No entendí qué comprobantes querés ver. Probá diciendo qué (compras, "
            "recibos o devoluciones), cuántos o de cuándo."
        )

    respuesta = ConsultaOut(
        entendido=True,
        resumen=interprete.resumir(criterio),
        criterio=CriterioOut(
            tipo=criterio.tipo,
            cantidad=criterio.cantidad,
            desde=criterio.desde,
            hasta=criterio.hasta,
            estado=criterio.estado,
        ),
        avisos=list(criterio.avisos),
    )
    if not repository.es_cliente_de_la_tienda(db, cliente_id):
        respuesta.avisos.append("Todavía no tenés comprobantes en esta tienda.")
        return respuesta

    desde = tiempo.inicio_del_dia(criterio.desde) if criterio.desde else None
    hasta = tiempo.fin_del_dia(criterio.hasta) if criterio.hasta else None
    limite = criterio.limite
    items: list[ComprobanteOut] = []
    encontrados = 0

    estados_compra = {"PAGADA", "ENTREGADA", "PENDIENTE_PAGO", "CANCELADA"}
    estados_nota = {"ABIERTA", "CERRADA"}
    if criterio.tipo in (interprete.COMPRAS, interprete.TODO) and (
        criterio.estado is None or criterio.estado in estados_compra
    ):
        filas, total = repository.compras(
            db, cliente_id=cliente_id, desde=desde, hasta=hasta,
            estado=criterio.estado, limite=limite,
        )
        items += [_compra(f) for f in filas]
        encontrados += total
    if criterio.tipo in (interprete.DEVOLUCIONES, interprete.TODO) and (
        criterio.estado is None or criterio.estado in estados_nota
    ):
        filas, total = repository.devoluciones(
            db, cliente_id=cliente_id, desde=desde, hasta=hasta,
            estado=criterio.estado, limite=limite,
        )
        items += [_devolucion(f) for f in filas]
        encontrados += total

    # Mezcladas, de la más nueva a la más vieja, y recortadas al límite.
    items.sort(key=lambda c: c.fecha, reverse=True)
    respuesta.items = items[:limite]
    respuesta.encontrados = encontrados
    if encontrados > len(respuesta.items):
        respuesta.avisos.append(
            f"Hay {encontrados} en total; se muestran {len(respuesta.items)}."
        )
    return respuesta


# --------------------------------------------------------------------------
#  Verificación pública (la página que abre el QR)
# --------------------------------------------------------------------------
def referencia(token: str) -> verificacion.Referencia:
    ref = verificacion.leer(token)
    if ref is None:
        raise ComprobanteInexistente()
    return ref


def verificar(db: Session, token: str) -> VerificacionOut:
    """Los datos públicos del comprobante: tienda, número, fecha, total y estado.

    **Nada del cliente**: ni su nombre, ni su documento, ni su dirección, ni lo
    que compró. El QR puede terminar en manos de cualquiera.
    """
    ref = referencia(token)
    # La empresa del token fija el RLS: la consulta no puede ver otra.
    fijar_empresa(db, ref.empresa_id)
    tienda = db.get(Empresa, ref.empresa_id)
    if tienda is None:
        raise ComprobanteInexistente()

    if ref.clase == verificacion.RECIBO:
        fila = repository.venta_para_verificar(db, ref.id)
        if fila is None or fila.estado not in ESTADOS_CON_COMPROBANTE + ("CANCELADA",):
            raise ComprobanteInexistente()
        momento: datetime = fila.comprobante_emitido_en or fila.creado_en
        return VerificacionOut(
            tienda=tienda.nombre,
            documento="RECIBO",
            codigo=fila.comprobante_numero or _numero_recibo(fila.id),
            referencia=fila.codigo,
            fecha=tiempo.en_bolivia(momento),
            fecha_texto=tiempo.formatear(momento, FORMATO_FECHA),
            total=fila.total,
            estado=fila.estado,
        )

    fila = repository.devolucion_para_verificar(db, ref.id)
    if fila is None:
        raise ComprobanteInexistente()
    return VerificacionOut(
        tienda=tienda.nombre,
        documento="NOTA_CAMBIO" if fila.tipo == "CAMBIO" else "NOTA_DEVOLUCION",
        codigo=f"ND-{fila.id:06d}",
        referencia=fila.venta_codigo,
        fecha=tiempo.en_bolivia(fila.creado_en),
        fecha_texto=tiempo.formatear(fila.creado_en, FORMATO_FECHA),
        total=Decimal(fila.valor_devuelto or 0).quantize(Decimal("0.01")),
        estado=fila.estado,
    )
