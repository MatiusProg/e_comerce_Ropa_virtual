# 08/11 (noche): la ficha del CU-37 en el 2.6 suma el probador nativo del móvil (cámara en vivo,
# «Medirme» con la cámara, compartir) y deja de decir que es solo web.
# Uso: python editar_08_11_ficha_cu37_movil.py <documento.docx>
import copy, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word-p2'))
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx_util import Editor

ed = Editor(docx.Document(sys.argv[1]))
h26 = ed.buscar(lambda e: e.tag == qn('w:p') and ed.texto(e).strip().startswith('2.6.'))
h = ed.buscar(lambda e: e.tag == qn('w:p') and ed.texto(e).strip().startswith('CU-37 —'), h26)
tabla = ed.tabla_despues(h)


def celda(campo):
    return ed.fila(tabla, campo).findall(qn('w:tc'))[1]


def agregar_lineas(tc, lineas):
    p = tc.findall(qn('w:p'))[-1]
    base = p.findall(qn('w:r'))[-1]
    for ln in lineas:
        r = copy.deepcopy(base)
        for hijo in list(r):
            if hijo.tag != qn('w:rPr'):
                r.remove(hijo)
        r.append(OxmlElement('w:br'))
        t = OxmlElement('w:t'); t.text = ln; t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t)
        p.append(r)


assert ed.reemplazar(celda('Descripción'), r'antes de comprar\.', 'antes de comprar. En la web trabaja sobre una '
                     'foto; en la aplicación móvil, sobre la cámara en vivo.') == 1
assert ed.reemplazar(celda('Precondiciones'), r'en la tienda en línea de la empresa \(web\)\.',
                     'en la tienda de la empresa, en la web o en la aplicación móvil.') == 1
agregar_lineas(celda('Flujos alternativos'), [
    '3a. En el móvil: el cliente entra por «Probador con talla real» (las prendas recién preparadas primero) o desde '
    'la ficha; la cámara queda en vivo y ML Kit detecta los hombros en cada cuadro, así que la prenda sigue a la '
    'persona mientras se mueve. Nada se sube al servidor para probarse.',
    '3b. Medirse con la cámara (móvil): la persona escribe su estatura y se para de cuerpo entero; el teléfono estima '
    'el ancho de hombros y el busto. La talla recomendada, el «cómo te queda» y el tamaño de la prenda pasan a ser los '
    'de esa persona, aunque use la cuenta de otra.',
    '6a. Compartir la prueba (móvil): el cliente captura la cámara con la prenda y la comparte con la hoja del '
    'teléfono (galería, WhatsApp, etc.).',
])
ed.cerrar(sys.argv[1])
print('ok')
