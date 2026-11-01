# Capturas de CU-01 a CU-03 en el 3.6 del Word de la 2da presentación (01/11), con el
# mismo formato que editar_01_11_diagramas_2.py.
# Uso: python editar_01_11_capturas_cu01_03.py <documento.docx> <carpeta_prototipos>
import io, os, sys
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from PIL import Image
from docx_util import Editor

DOC, PROTO = sys.argv[1:3]
ed = Editor(docx.Document(DOC))
T = ed.texto


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return st is not None and st.get(qn('w:val')) == estilo


def titulo(texto, estilo='Titulo11', desde=None):
    return ed.buscar(lambda e: e.tag == qn('w:p') and es_titulo(e, estilo) and T(e).strip().startswith(texto), desde)


def parrafo_imagen(ruta, alto=12.0):
    blob = open(ruta, 'rb').read()
    w, h = Image.open(io.BytesIO(blob)).size
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(min(15.5, alto * w / h)))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0); pf.alignment = 1
    return p._p


modelo_leyenda = ed.parrafo('Modelo de casos de uso estructurado del primer parcial, parte 1 de 3')


def leyenda(t):
    el = ed.copiar_parrafo(modelo_leyenda, t)
    Paragraph(el, None).paragraph_format.keep_with_next = True
    return el


CAPTURAS = {
    'CU-01': [('cu01-lista-de-empresas.png', 'Web: las empresas de la plataforma, con su plan, vencimiento, sucursales, usuarios y estado.'),
              ('cu01-formulario-nueva-empresa.png', 'Web: el alta de una empresa, con su plan y su sucursal principal.'),
              ('cu01-formulario-editar-empresa.png', 'Web: la edición de los datos de una empresa.')],
    'CU-02': [('cu02-lista-de-planes.png', 'Web: los planes, con precio, límites, cupos de IA, funciones y empresas suscritas.'),
              ('cu02-formulario-plan-limites.png', 'Web: la edición de un plan: precio, duración y límites.'),
              ('cu02-formulario-plan-funciones.png', 'Web: las funciones incluidas en el plan.')],
    'CU-03': [('cu03-suscripcion-historial-y-pagos.png', 'Web: la suscripción vigente de una empresa, sus acciones, el historial y los pagos simulados.'),
              ('cu03-cambiar-plan-pago-simulado.png', 'Web: cambiar de plan, con el vencimiento, el pago simulado y los límites nuevos.'),
              ('cu03-renovar-suscripcion-confirmacion.png', 'Web: renovar la suscripción, que suma 30 días y registra un pago simulado.'),
              ('cu03-suspender-suscripcion-confirmacion.png', 'Web: suspender la suscripción deja a la empresa en modo solo consulta.')],
}
cap3_6 = titulo('3.6.')
for cu, capturas in CAPTURAS.items():
    ancla = titulo(cu, 'Titulo3', desde=cap3_6)
    piezas = []
    for archivo, t in capturas:
        piezas += [leyenda(t), parrafo_imagen(os.path.join(PROTO, archivo))]
    ed.insertar_despues(ancla, piezas)

ed.cerrar(DOC)
print('ok')
