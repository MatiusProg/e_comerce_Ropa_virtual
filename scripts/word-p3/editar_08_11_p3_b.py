# 3ra presentación (08/11), segunda tanda en el Word:
#   3.1  el modelo de dominio de CU-21 a CU-45, debajo del de la 2da presentación;
#   3.3  la secuencia de CU-21 a CU-45, con la leyenda de sus flujos (los grupos de la robustez);
#   3.5  las tablas de la 3ra presentación, debajo de las de la 2da;
#   3.6  las capturas de los prototipos de CU-21 a CU-45, si está el capturas.json.
# Uso: python editar_08_11_p3_b.py <documento.docx> <carpeta JPG de EA> [<carpeta de capturas con capturas.json>]
import glob, io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word-p2'))
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image
from docx_util import Editor

DOC, JPG = sys.argv[1:3]
CAPT = sys.argv[3] if len(sys.argv) > 3 else None
SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ESP = json.load(open(os.path.join(SCRIPTS, 'p3-especificaciones.json'), encoding='utf-8'))
GRUPOS = {r['cu']: r['grupos'] for r in json.load(open(os.path.join(SCRIPTS, 'ea-p3.datos.json'), encoding='utf-8'))['robustez']}
NOMBRES = ESP['casos']
NUEVOS = [f'CU-{n}' for n in range(21, 46)]
ed = Editor(docx.Document(DOC))
T = ed.texto
ANCHO = 15.5


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return el.tag == qn('w:p') and st is not None and st.get(qn('w:val')) == estilo


def titulo(texto, estilo='Titulo11', desde=None):
    return ed.buscar(lambda e: es_titulo(e, estilo) and T(e).strip().startswith(texto), desde)


def jpg(prefijo):
    hay = sorted(glob.glob(os.path.join(JPG, '**', glob.escape(prefijo) + '*.jpg'), recursive=True))
    if len(hay) != 1:
        raise LookupError(f'{prefijo}: {hay}')
    return open(hay[0], 'rb').read()


def parrafo_imagen(blob, alto):
    w, h = Image.open(io.BytesIO(blob)).size
    ancho = min(ANCHO, alto * w / h)
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(ancho))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0)
    pf.alignment = 1
    return p._p


def nombre(cu):
    return f'{cu} — {NOMBRES[cu]}'


def texto(modelo, txt):
    return ed.copiar_parrafo(modelo, txt)


# ---- 3.1 -------------------------------------------------------------------------
h31 = titulo('3.1.')
intro31 = h31.getnext()
img31 = intro31.getnext()
assert list(img31.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip'))
ed.insertar_despues(img31, [
    texto(intro31, 'Para la 3ra presentación (CU-21 a CU-45) el modelo de dominio suma las entidades de su robustez: '
                   'inventario y traspasos, devoluciones web, ofertas y precios mayoristas, la analítica, el probador, '
                   'las copias de seguridad, los roles propios, los avisos push y los dos aportes propios (el aviso de '
                   'talla y la detección de anomalías). Igual que antes, va corto: sin atributos, con el verbo y la '
                   'multiplicidad de cada asociación, y las tablas de detalle se dibujan como asociación.'),
    parrafo_imagen(jpg('3.1 Modelo de dominio - 3ra presentaci'), alto=12.0)])

# ---- 3.3 -------------------------------------------------------------------------
h34 = titulo('3.4.')
h20_33 = titulo('CU-20', 'Titulo3', desde=titulo('3.3.'))
leyenda = ed.parrafo('Grupo 1:', desde=titulo('CU-20', 'Titulo3', desde=titulo('3.2.')))
ancla = h34.getprevious()
for cu in NUEVOS:
    piezas = [ed.copiar_parrafo(h20_33, nombre(cu)), parrafo_imagen(jpg(f'3.3 {cu} '), alto=20.0)]
    piezas += [texto(leyenda, f'Flujo {i}: {g}') for i, g in enumerate(GRUPOS[cu], 1)]
    ancla = ed.insertar_despues(ancla, piezas)

# ---- 3.5 -------------------------------------------------------------------------
h35 = titulo('3.5.')
intro35 = h35.getnext()
img35 = intro35.getnext()
ed.insertar_despues(img35, [
    texto(intro35, 'Las tablas que usan los casos de uso de la 3ra presentación (CU-21 a CU-45), leídas de la base en la '
                   'última migración (0043): cada una con todas sus columnas, su tipo y «PK»/«FK», y las relaciones '
                   'con su verbo y la cardinalidad que obliga la base. Las que ya estaban en el diagrama anterior se '
                   'repiten cuando una tabla nueva las referencia (por ejemplo, usuario, sucursal y venta). De las cinco '
                   'claves foráneas de TRASPASO a USUARIO se dibuja solo la de quien lo solicita; las otras cuatro quedan '
                   'marcadas «FK» en su columna.'),
    parrafo_imagen(jpg('3.5 Dise'), alto=14.0)])

# ---- 3.6 -------------------------------------------------------------------------
if CAPT and os.path.exists(os.path.join(CAPT, 'capturas.json')):
    capturas = json.load(open(os.path.join(CAPT, 'capturas.json'), encoding='utf-8'))
    h36 = titulo('3.6.')
    h20_36 = titulo('CU-20', 'Titulo3', desde=h36)
    ley36 = h20_36.getnext()                       # «Web: …», la leyenda va antes de la imagen
    fin36 = h20_36
    el = h20_36.getnext()
    while not (es_titulo(el, 'Titulo11') or es_titulo(el, 'CAPITULO') or es_titulo(el, 'Titulo3')):
        fin36 = el; el = el.getnext()
    ancla = fin36
    for cu in NUEVOS:
        if cu not in capturas:
            continue
        piezas = [ed.copiar_parrafo(h20_36, nombre(cu))]
        for archivo, txt in capturas[cu]:
            l = texto(ley36, txt)
            piezas += [l, parrafo_imagen(open(os.path.join(CAPT, archivo), 'rb').read(), alto=11.0)]
        ancla = ed.insertar_despues(ancla, piezas)

ed.cerrar(DOC)
print('ok', DOC)
