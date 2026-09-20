"""
P7 - Ventas / CU-29  |  capa: servicio (reglas de negocio y transacciones)

Ciclo de desarrollo: 3
Caso de uso: CU-29 Consultar historial de compras

Dos cosas: listar lo que el cliente compro, y darle el comprobante de cada
compra pagada.

EL COMPROBANTE SE EMITE UNA VEZ Y SE REIMPRIME SIEMPRE
-------------------------------------------------------
`comprobante.venta_id` es UNICO y el modelo lo dice con todas las letras:
«reimprimir no es reemitir». La primera descarga crea la fila con su numero y su
fecha; todas las siguientes generan el PDF **a partir de esa misma fila**, con
el mismo numero y la misma fecha de emision.

Si el PDF se armara sin fila, cada descarga seria un comprobante distinto para
la misma compra --- y un comprobante que cambia de numero cada vez que se lo
mira no sirve como comprobante de nada.

POR QUE SE EMITE TAMBIEN AL CONFIRMARSE EL PAGO
------------------------------------------------
`asegurar_comprobante` la llama CU-28 dentro de la transaccion del cobro, para
que el recibo exista desde el instante en que el dinero entro --- que es cuando
corresponde emitirlo --- y no cuando alguien se acuerda de descargarlo.

Pero **la misma funcion la llama la descarga**, y no es redundante: las ventas
que se pagaron ANTES de que existiera CU-29 no tienen comprobante, y sin esa
segunda llamada su boton de descarga fallaria para siempre. El UNIQUE hace que
llamarla dos veces sea inofensivo.
"""
import logging
from io import BytesIO

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import tiempo

from app.modules.ventas import historial_repository as repository
from app.modules.ventas import repository as ventas_repository
from app.modules.ventas import service as ventas_service
from app.modules.ventas.historial_schemas import PaginaCompras
from app.modules.ventas.models import Comprobante, Venta

_log = logging.getLogger("violetboutique.ventas")

#: El recibo simple, sin datos fiscales. La FACTURA exige NIT y razon social
#: ---lo dice el CHECK `factura_con_datos`--- y pedirselos al cliente es otra
#: conversacion que no entra en este ciclo.
TIPO_RECIBO = "RECIBO"

#: Los estados en los que una compra ya se cobro y por lo tanto tiene
#: comprobante. Un pedido que espera pago no tiene que recibir uno: seria un
#: papel que dice que se pago algo que no se pago.
ESTADOS_CON_COMPROBANTE = ("PAGADA", "ENTREGADA")


class SinComprobante(Exception):
    """La compra existe pero todavia no se cobro. El router lo traduce a 409."""


def listar_compras(
    db: Session, usuario_id: int, *, pagina: int, tamano: int
) -> PaginaCompras:
    """Paso 2: las compras del cliente, de la mas nueva a la mas vieja."""
    cliente_id = ventas_service._cliente(db, usuario_id)
    filas = repository.listar_compras(
        db, cliente_id=cliente_id, limite=tamano, desplazamiento=(pagina - 1) * tamano
    )
    return PaginaCompras(
        total=repository.contar_compras(db, cliente_id),
        pagina=pagina,
        tamano=tamano,
        items=[ventas_service._armar_pedido(db, fila) for fila in filas],
    )


def _numero_de(venta: Venta) -> str:
    """El numero del comprobante, derivado del identificador de la venta.

    `R-00000042`. Es unico porque el identificador lo es, y ademas **estable**:
    reintentar la emision de la misma venta produce el mismo numero, asi que el
    choque contra el UNIQUE se resuelve leyendo la fila que ya estaba en vez de
    generando otro.

    Un contador propio ---«el recibo numero 7 del dia»--- seria lo que pide una
    numeracion fiscal de verdad, sin huecos y correlativa. Eso exige una
    secuencia dedicada y una conversacion sobre facturacion que este ciclo no
    tuvo; queda anotado en la ficha.
    """
    return f"R-{venta.id:08d}"


def asegurar_comprobante(db: Session, venta: Venta) -> Comprobante:
    """El comprobante de la venta, emitiendolo si todavia no existe. **Sin commit.**

    Idempotente por el UNIQUE sobre `venta_id`: dos llamadas simultaneas ---el
    webhook y una descarga, por ejemplo--- no producen dos comprobantes. La
    segunda choca, se recupera la fila que gano y se devuelve esa.
    """
    existente = repository.obtener_comprobante(db, venta.id)
    if existente is not None:
        return existente

    try:
        with db.begin_nested():
            return repository.agregar_comprobante(
                db, venta_id=venta.id, tipo=TIPO_RECIBO, numero=_numero_de(venta)
            )
    except IntegrityError:
        # Otro lo emitio en el medio. La fila que gano es la buena.
        emitido = repository.obtener_comprobante(db, venta.id)
        if emitido is None:  # pragma: no cover - solo si el UNIQUE no fue el motivo
            raise
        return emitido


def comprobante_en_pdf(db: Session, usuario_id: int, codigo: str) -> tuple[str, bytes]:
    """El comprobante de una compra propia, como PDF. **Hace commit.**

    Devuelve `(nombre_del_archivo, bytes)`.

    Una compra ajena **no existe**: 404, nunca 403 --- convencion 1 del ciclo.
    Lo resuelve la consulta, que lleva el `cliente_id` en el WHERE.
    """
    cliente_id = ventas_service._cliente(db, usuario_id)
    fila = ventas_repository.obtener_pedido(db, codigo=codigo, cliente_id=cliente_id)
    if fila is None:
        raise ventas_service.PedidoInexistente(codigo)
    if fila.estado not in ESTADOS_CON_COMPROBANTE:
        raise SinComprobante(fila.estado)

    venta = db.get(Venta, fila.id)
    comprobante = asegurar_comprobante(db, venta)
    db.commit()

    pedido = ventas_service._armar_pedido(db, fila)
    cuerpo = _dibujar_pdf(comprobante, pedido)
    return f"{comprobante.numero}.pdf", cuerpo


def _dibujar_pdf(comprobante: Comprobante, pedido) -> bytes:
    """El PDF, con ReportLab.

    Se dibuja a mano y no con una plantilla HTML convertida: agregar un motor de
    HTML a PDF traeria dependencias del sistema ---navegador sin cabeza o
    librerias de C--- que habria que instalar tambien en el contenedor de
    Railway. ReportLab ya esta en `requirements.txt` y es Python puro.

    El texto se dibuja por coordenadas, que es tosco pero predecible: un recibo
    de una pagina no justifica un motor de maquetado.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    ancho, alto = A4
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Comprobante {comprobante.numero}")

    y = alto - 25 * mm

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(20 * mm, y, "Violet Boutique")
    pdf.setFont("Helvetica", 10)
    y -= 6 * mm
    pdf.drawString(20 * mm, y, "Recibo de compra")

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(ancho - 20 * mm, alto - 25 * mm, comprobante.numero)
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(
        ancho - 20 * mm,
        alto - 31 * mm,
        comprobante.emitido_en.strftime("Emitido el %d/%m/%Y %H:%M"),
    )

    y -= 10 * mm
    pdf.line(20 * mm, y, ancho - 20 * mm, y)

    y -= 8 * mm
    pdf.setFont("Helvetica", 10)
    # CU-31 emite su comprobante con este mismo dibujo, y una venta de mostrador
    # no es un «pedido» ni se «retira»: el cliente ya se fue con la prenda.
    # Decirle «Retiro en Centro» a quien acaba de pagar en Centro es raro, y el
    # recibo es lo unico que se lleva del sistema.
    presencial = pedido.canal == "PRESENCIAL"
    etiqueta = "Venta" if presencial else "Pedido"
    pdf.drawString(20 * mm, y, f"{etiqueta}: {pedido.codigo}")
    y -= 5 * mm
    pdf.drawString(20 * mm, y, f"Fecha de compra: {pedido.creado_en.strftime('%d/%m/%Y %H:%M')}")
    y -= 5 * mm
    if presencial:
        entrega = f"Venta en mostrador · {pedido.sucursal_nombre}"
    elif pedido.direccion_envio:
        entrega = f"Envío a {pedido.direccion_envio}"
    else:
        entrega = f"Retiro en {pedido.sucursal_nombre}"
    pdf.drawString(20 * mm, y, entrega)

    # --- Las lineas ---
    y -= 12 * mm
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(20 * mm, y, "PRENDA")
    pdf.drawRightString(120 * mm, y, "CANT.")
    pdf.drawRightString(150 * mm, y, "P. UNIT.")
    pdf.drawRightString(ancho - 20 * mm, y, "SUBTOTAL")
    y -= 2 * mm
    pdf.line(20 * mm, y, ancho - 20 * mm, y)

    pdf.setFont("Helvetica", 9)
    for linea in pedido.lineas:
        y -= 6 * mm
        if y < 30 * mm:  # pragma: no cover - un recibo de una compra no llega
            pdf.showPage()
            y = alto - 25 * mm
            pdf.setFont("Helvetica", 9)
        detalle = " · ".join(
            p for p in (linea.producto_nombre, linea.talla_codigo, linea.color_nombre) if p
        )
        pdf.drawString(20 * mm, y, detalle[:60])
        pdf.drawRightString(120 * mm, y, str(linea.cantidad))
        pdf.drawRightString(150 * mm, y, f"Bs {linea.precio_unitario}")
        pdf.drawRightString(ancho - 20 * mm, y, f"Bs {linea.subtotal}")

    y -= 4 * mm
    pdf.line(110 * mm, y, ancho - 20 * mm, y)
    y -= 7 * mm
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawRightString(150 * mm, y, "TOTAL")
    pdf.drawRightString(ancho - 20 * mm, y, f"Bs {pedido.total}")

    # El aviso de abajo NO es decorativo: un recibo sin datos fiscales que no lo
    # diga se puede confundir con una factura, y no lo es.
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(
        20 * mm,
        20 * mm,
        "Documento sin validez fiscal. Para factura, solicitarla en la sucursal.",
    )
    pdf.drawRightString(
        ancho - 20 * mm,
        20 * mm,
        tiempo.ahora().strftime("Descargado el %d/%m/%Y"),
    )

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
