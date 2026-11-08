# 08/11 (noche): el probador nativo en el móvil y el CU-46, probados en el teléfono.
#   3.6  capturas del móvil en el CU-37 (lista, dos personas medidas con la cámara, vestido en XS y XL),
#        el CU-38 (foto realista y compartir) y el CU-46 nuevo (mis comprobantes por voz con QR);
#   5.5  dos filas más en la tabla de resultados.
# Uso: python editar_08_11_probador_movil.py <documento.docx>
import io, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word-p2'))
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image
from docx_util import Editor

DOC = sys.argv[1]
MOVIL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'entregas', 'Presentacion-3',
                     'pruebas', 'movil')
ed = Editor(docx.Document(DOC))
T = ed.texto


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return el.tag == qn('w:p') and st is not None and st.get(qn('w:val')) == estilo


def titulo(texto, estilo='Titulo11', desde=None):
    return ed.buscar(lambda e: es_titulo(e, estilo) and T(e).strip().startswith(texto), desde)


def imagen(archivo, alto, ancho_max=15.5):
    blob = open(os.path.join(MOVIL, archivo), 'rb').read()
    w, h = Image.open(io.BytesIO(blob)).size
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(min(ancho_max, alto * w / h)))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0); pf.alignment = 1
    return p._p


LEYENDA = ed.parrafo('Web: las empresas de la plataforma')


def figura(archivo, texto, alto):
    return [ed.copiar_parrafo(LEYENDA, texto), imagen(archivo, alto)]


def fin_de_bloque(h3):
    """El último elemento del bloque de un CU en el 3.6 (antes del título siguiente)."""
    el = h3
    while True:
        nxt = el.getnext()
        if nxt is None or es_titulo(nxt, 'Titulo3') or es_titulo(nxt, 'Titulo11') or es_titulo(nxt, 'CAPITULO'):
            return el
        el = nxt


h36 = titulo('3.6.')
h37 = titulo('CU-37', 'Titulo3', desde=h36)
ed.insertar_despues(fin_de_bloque(h37), figura(
    'movil-cu37-tira-probador-nativo.png',
    'Móvil (probado el 08/11 en un Android 16): 1) la lista del probador, lo último calibrado primero; 2) Karen, '
    'medida con la cámara (167 cm, busto estimado 87 cm): le va la S; 3) Luis, con la misma cuenta (181 cm, 104 cm): '
    'le va la XL; 4) el vestido en su talla (XS) y 5) en XL, «muy holgada». La prenda sigue los hombros en vivo.', 8.5))
h38 = titulo('CU-38', 'Titulo3', desde=h36)
ed.insertar_despues(fin_de_bloque(h38), figura(
    'movil-cu38-tira-foto-y-compartir.png',
    'Móvil: 1) la foto de la prueba, guardada en «Mis pruebas» (en producción, vista simulada: la clave gratuita de '
    'Gemini no genera imágenes); 2) «Compartir foto», con la hoja de compartir del teléfono.', 9.0))
h45 = titulo('CU-45', 'Titulo3', desde=h36)
nombre46 = 'CU-46 — Consultar mis comprobantes por voz'
ed.insertar_despues(fin_de_bloque(h45), [ed.copiar_parrafo(h45, nombre46)] + figura(
    'movil-cu46-tira-mis-comprobantes.png',
    'Móvil: 1) «mis últimas 3 compras»: lo que entendió y cada recibo con su QR de verificación; 2) «mis '
    'devoluciones».', 9.0))

h55 = titulo('5.5.')
tabla = ed.tabla_despues(h55)
ultima = ed.fila(tabla, 'Analítica y anomalías en producción')
fila = ed.agregar_fila(tabla, ['Mis comprobantes por voz (CU-46)', 'Aprobado',
                               'En la web y el móvil: «mis últimas 3 compras» y «mis devoluciones» devuelven la lista '
                               'correcta, cada recibo con su QR de verificación pública'], despues_de=ultima)
ed.agregar_fila(tabla, ['Probador nativo en el teléfono (CU-37 y CU-38)', 'Aprobado',
                        'Dos personas con la misma cuenta, medidas con la cámara, reciben su talla (S y XL); la prenda '
                        'real sigue los hombros en vivo; la foto y «Compartir» funcionan'], despues_de=fila)
ed.recebrar(tabla)

ed.cerrar(DOC)
print('ok', DOC)
