# Diagramas de EA y capturas de los prototipos en el Word de la 2da presentación (01/11):
#   2.5  el diagrama general nuevo (CU-01 a CU-20) en lugar del de CU-01 a CU-12;
#   2.6  el diagrama de casos de uso de CU-13 a CU-20, debajo del título de cada ficha;
#   3.2  la robustez de CU-13 a CU-20, con su título, después de la de CU-12;
#   3.4  el diseño de clases de los 20 casos de uso;
#   3.6  las capturas de los prototipos de CU-13 a CU-20.
# Lo de CU-01 a CU-12 en el 2.6, el 3.2 y el 3.3 lo cargó Karen y no se toca.
# Uso: python editar_01_11_diagramas.py <documento.docx> <carpeta_jpg_de_EA> <carpeta_prototipos>
import copy, glob, io, os, sys
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from PIL import Image
from docx_util import Editor

DOC, JPG, PROTO = sys.argv[1:4]
ed = Editor(docx.Document(DOC))
T = ed.texto
BLIP = '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'
NUEVOS = [f'CU-{n}' for n in range(13, 21)]
TODOS = [f'CU-{n:02d}' for n in range(1, 21)]
ANCHO, ALTO = 15.5, 21.0  # cm útiles


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return st is not None and st.get(qn('w:val')) == estilo


def titulo(texto, estilo='Titulo11', desde=None):
    return ed.buscar(lambda e: e.tag == qn('w:p') and es_titulo(e, estilo) and T(e).strip().startswith(texto), desde)


def jpg(prefijo):
    """El JPG exportado de EA cuyo nombre empieza con `prefijo` (EA estropea los acentos del nombre)."""
    hay = sorted(glob.glob(os.path.join(JPG, glob.escape(prefijo) + '*.jpg')))
    if len(hay) != 1:
        raise LookupError(f'{prefijo}: {hay}')
    return open(hay[0], 'rb').read()


def parrafo_imagen(blob, alto=ALTO):
    w, h = Image.open(io.BytesIO(blob)).size
    ancho = min(ANCHO, alto * w / h)
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(ancho))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0)
    pf.alignment = 1  # centrado
    return p._p


# Modelos de formato que ya están en el documento.
cap2_6 = titulo('2.6.')
modelo_h3 = titulo('CU-13', 'Titulo3', desde=cap2_6)              # título de ficha sin imagen
modelo_texto = ed.parrafo('Cada ficha sigue el formato de ICONIX')  # párrafo de texto normal
modelo_leyenda = ed.parrafo('Modelo de casos de uso estructurado del primer parcial, parte 1 de 3')


def h3(txt):
    return ed.copiar_parrafo(modelo_h3, txt)


def leyenda(txt):
    el = ed.copiar_parrafo(modelo_leyenda, txt)
    Paragraph(el, None).paragraph_format.keep_with_next = True
    return el


# Nombres de los casos de uso, tal como están en los títulos de las fichas del 2.6.
nombres = {}
el = cap2_6
while True:
    el = el.getnext()
    if es_titulo(el, 'Titulo2'):
        break
    if es_titulo(el, 'Titulo3') and T(el).strip()[:5] in TODOS:
        nombres[T(el).strip()[:5]] = T(el).strip()

# --- 2.5: el general nuevo --------------------------------------------------------
cap2_5 = titulo('2.5.')
viejo = cap2_5
while not list(viejo.iter(BLIP)):
    viejo = viejo.getnext()
nuevo = parrafo_imagen(jpg('2.5 Diagrama general de casos de uso (CU-01 a CU-20)'))
viejo.addnext(nuevo)
viejo.getparent().remove(viejo)

# --- 2.6: el diagrama de cada CU nuevo, debajo de su título --------------------------
for cu in NUEVOS:
    t = titulo(cu, 'Titulo3', desde=cap2_6)
    t.addnext(parrafo_imagen(jpg(f'2.5 {cu} '), alto=9.0))

# --- 3.2: robustez de CU-13 a CU-20, antes del 3.3 --------------------------------------
ancla = titulo('3.3.').getprevious()
for cu in NUEVOS:
    ancla = ed.insertar_despues(ancla, [h3(nombres[cu]), parrafo_imagen(jpg(f'3.2 {cu} '))])

# --- 3.4: diseño de clases de los 20 -------------------------------------------------------
cap3_4 = titulo('3.4.')
pendiente = cap3_4.getnext()
assert T(pendiente).startswith('[Pendiente]'), T(pendiente)
intro = ed.copiar_parrafo(modelo_texto,
    'Un diagrama por caso de uso, con las clases de interfaz, de control y de entidad que intervienen. '
    'Las interfaces muestran las acciones de la pantalla; los controladores, los métodos del backend y del '
    'servicio de la web o del móvil que usa el caso; las entidades, sus columnas con el tipo de la base y sus '
    'métodos. Las relaciones entre entidades son las claves foráneas reales, con su multiplicidad. Los casos '
    'que modifican datos en el servidor muestran el control BitacoraMiddleware, que deja cada operación '
    'registrada en AsientoBitacora.')
pendiente.addnext(intro)
pendiente.getparent().remove(pendiente)
cap3_5 = titulo('3.5.')
ultimo = None
for cu in TODOS:
    try:
        t = titulo(cu, 'Titulo3', desde=cap3_4)
        if list(ed.body.iterchildren()).index(t) > list(ed.body.iterchildren()).index(cap3_5):
            raise LookupError
    except LookupError:
        t = h3(nombres[cu])
        ed.insertar_despues(ultimo, [t])
    else:
        # Los títulos que ya estaban usan el nombre del 2.6.
        pass
    img = parrafo_imagen(jpg(f'3.4 {cu} '), alto=16.0)
    t.addnext(img)
    ultimo = img

# --- 3.6: capturas de los prototipos de CU-13 a CU-20 ---------------------------------------
CAPTURAS = {
    'CU-13': [('cu13-dispositivo-preparado.png', 'Web: el dispositivo preparado para trabajar sin conexión.'),
              ('cu13-sin-conexion-datos-desactualizados.png', 'Web: sin conexión, con el aviso de datos desactualizados.')],
    'CU-14': [('cu14-cu16-venta-sin-conexion-efectivo-qr.png', 'Web: venta sin conexión, con el cobro en efectivo o por QR.'),
              ('cu14-comprobante-provisional-venta-sin-conexion.png', 'Web: comprobante provisional de la venta sin conexión.')],
    'CU-15': [('movil-cu15-vitrina-con-fotos-sin-conexion.png', 'Móvil: la vitrina sin conexión, con las fotos guardadas, para reservar.')],
    'CU-16': [('cu16-cola-operacion-guardada.png', 'Web: la operación con su pago, guardada en la cola del dispositivo.')],
    'CU-17': [('cu17-sincronizacion-confirmada.png', 'Web: la sincronización, con las operaciones confirmadas por el servidor.'),
              ('movil-cu17-sincronizado-todo-confirmado.png', 'Móvil: todo sincronizado y confirmado.')],
    'CU-18': [('cu18-cola-dos-pendientes-sin-conexion.png', 'Web: dos operaciones pendientes sin conexión.'),
              ('movil-cu13-cu18-sin-conexion-dos-pendientes.png', 'Móvil: sin conexión, con dos reservas esperando al servidor.')],
    'CU-19': [('cu19-operaciones-sin-conexion-todas-rechazada-devuelta.png', 'Web: las operaciones sin conexión, con una rechazada y devuelta.'),
              ('cu19-por-devolver-vacia.png', 'Web: la lista por devolver, ya sin pendientes.')],
    'CU-20': [('cu20-arqueo-turno-abierto.png', 'Web: el arqueo del turno abierto.'),
              ('cu20-arqueo-con-ventas-sin-conexion.png', 'Web: el arqueo con las ventas sin conexión y lo que falta devolver.')],
}
cap3_6 = titulo('3.6.')
ancla = titulo('CU-12', 'Titulo3', desde=cap3_6)
for cu in NUEVOS:
    piezas = [h3(nombres[cu])]
    for archivo, texto in CAPTURAS[cu]:
        piezas += [leyenda(texto), parrafo_imagen(open(os.path.join(PROTO, archivo), 'rb').read(), alto=12.0)]
    ancla = ed.insertar_despues(ancla, piezas)

ed.cerrar(DOC)
print('ok')
