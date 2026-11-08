# CU-46 (pedido de la ing, 08/11): Consultar mis comprobantes por voz. Solo entra al 2.5 (caso de uso)
# y al 2.6 (ficha); no lleva robustez, secuencia ni diseño de clases (decisión de Luis, para no atrasar).
# Lo une scripts/p3_datos.py con los grupos a..e.

CASOS = [
    ('CU-46', 'Consultar mis comprobantes por voz', ['Cliente'], [],
     'Pedido de la docente. El cliente pide por voz o texto sus recibos y notas de devolución; cada uno con su QR '
     'de verificación pública. RF-69.'),
]
ROBUSTEZ = []
DESCRIPCION = {}
CLASES = {}
CUS = {}
ESPEC = {
    'CU-46': {
        'descripcion': 'Permite al cliente pedir, hablando o escribiendo, un reporte de sus comprobantes de la tienda '
                       '(recibos de compra y notas de devolución) y verificar cada uno con un código QR.',
        'actores': 'Cliente',
        'iniciador': 'Cliente',
        'precondiciones': 'El cliente inició sesión en la tienda (CU-06) y está asociado a ella.',
        'flujo': [
            'El cliente entra a «Mis comprobantes», en la web o en el móvil.',
            'Dicta su pedido con el micrófono, lo escribe o elige un ejemplo («mis últimas 3 compras», «mis recibos '
            'de octubre»).',
            'El sistema transcribe la voz en el dispositivo y envía solo el texto.',
            'El sistema interpreta el pedido por reglas, sin gastar el cupo de IA de la tienda: tipo, cantidad, '
            'período y estado.',
            'El sistema busca los comprobantes del cliente en esa tienda, con un máximo de 50.',
            'El sistema muestra lo que entendió y la lista: fecha, código, total, estado y el QR de cada uno.',
            'El cliente abre la verificación, descarga el PDF del recibo o exporta la lista.',
        ],
        'alternativos': [
            '2a. Sin reconocimiento de voz: se oculta el micrófono y el pedido se escribe.',
            '4a. No se entiende el pedido: el sistema responde «No entendí» con ejemplos y no muestra datos.',
            '4b. Pide más de 50: se muestran 50 con un aviso.',
            '5a. No hay comprobantes que coincidan: se informa que la lista está vacía.',
            '7a. Un tercero escanea el QR: la página pública muestra solo tienda, número, fecha, total y estado; si el '
            'código fue alterado, responde que no existe.',
        ],
        'postcondiciones': 'El cliente ve sus comprobantes; no se modifica ningún dato. La consulta queda en la '
                           'bitácora.',
        'rastreo': 'RF-69 · RN-13',
    },
}
