# Anexo 1 para la 2da presentación (notas de Karen, 01/11): además de la lista y el diagrama de casos de uso
# del primer parcial, el diagrama de clases, las secuencias de los casos de uso principales y la arquitectura.
# Las imágenes se copian del Word final del primer parcial.
# Uso: python editar_01_11_anexo.py <documento.docx> <word_del_1er_parcial.docx>
import copy, io, sys
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image
from docx_util import Editor

DOC, EX1 = sys.argv[1], sys.argv[2]
ed = Editor(docx.Document(DOC))
ex1 = docx.Document(EX1)
T = ed.texto
BLIP = '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'
EMBED = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed'

# --- Las imágenes del 1er parcial, por el título que las precede ---------------
hijos1 = list(ex1.element.body.iterchildren())


def es_titulo(el):
    """Solo los títulos de verdad: el índice (TOC) repite los mismos textos."""
    estilo = el.find('.//' + qn('w:pStyle'))
    return estilo is not None and estilo.get(qn('w:val')).startswith(('Titulo', 'CAPITULO'))


def imagen_despues(titulo, desde=0, salto=0):
    """Bytes de la primera imagen después del título que empieza con `titulo` (y `salto` imágenes más)."""
    i = next(k for k in range(desde, len(hijos1))
             if es_titulo(hijos1[k]) and T(hijos1[k]).strip().startswith(titulo))
    vistas = 0
    for el in hijos1[i:]:
        for b in el.iter(BLIP):
            if vistas == salto:
                return ex1.part.related_parts[b.get(EMBED)].blob, i
            vistas += 1
    raise LookupError(titulo)


def indice(titulo):
    return next(k for k, e in enumerate(hijos1) if es_titulo(e) and T(e).strip().startswith(titulo))


secuencias = indice('3.2 Diseño de Casos de Uso')
datos = indice('3.3.1 Diseño de datos lógico')

# --- Piezas del Anexo, con el formato de las que ya están -----------------------
anexo1 = ed.parrafo('Anexo 1. Casos de uso del primer parcial', exacto=True)
sub_modelo = ed.parrafo('Diagrama de casos de uso', desde=anexo1, exacto=True)
leyenda_modelo = ed.parrafo('Modelo de casos de uso estructurado del primer parcial, parte 1 de 3', desde=anexo1)
img_modelo = leyenda_modelo.getnext()
anexo2 = ed.parrafo('Anexo 2. Enlaces', exacto=True)
ancla = anexo2.getprevious().getprevious()  # la última imagen, antes del párrafo vacío del Anexo 2

ANCHO, ALTO = 16.0, 21.0  # cm útiles


def parrafo_imagen(blob):
    w, h = Image.open(io.BytesIO(blob)).size
    ancho = min(ANCHO, ALTO * w / h)
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(ancho))
    el = p._p
    # El formato del párrafo de imagen que ya está en el Anexo (centrado, sin sangría).
    ppr = img_modelo.find(qn('w:pPr'))
    if ppr is not None:
        vieja = el.find(qn('w:pPr'))
        if vieja is not None:
            el.remove(vieja)
        el.insert(0, copy.deepcopy(ppr))
    return el


def leyenda(txt):
    el = ed.copiar_parrafo(leyenda_modelo, txt)
    from docx.text.paragraph import Paragraph
    Paragraph(el, None).paragraph_format.keep_with_next = True
    return el


nuevos = []

# Diagrama de clases (el diseño de datos lógico del 1er parcial, uno por ciclo)
nuevos.append(ed.copiar_parrafo(sub_modelo, 'Diagrama de clases'))
for n, ciclo in enumerate(('CICLO #1', 'CICLO #2', 'CICLO #3'), start=1):
    blob, _ = imagen_despues(ciclo, desde=datos)
    nuevos += [leyenda(f'Diagrama de clases del primer parcial, parte {n} de 3.'), parrafo_imagen(blob)]

# Secuencia de los casos de uso principales
nuevos.append(ed.copiar_parrafo(sub_modelo, 'Diagramas de secuencia de los casos de uso principales'))
nuevos.append(ed.copiar_parrafo(leyenda_modelo,
                                'Se incluyen los casos de uso que sostienen el negocio del primer parcial: la reserva '
                                'para probarse, la venta en línea con su pago, la venta en caja, el vestidor con '
                                'realidad aumentada y las recomendaciones con inteligencia artificial.'))
for titulo, nombre in (('CU22', 'CU-22 Crear reserva de prendas'),
                       ('CU27', 'CU-27 Realizar pedido y pagar en línea'),
                       ('CU31', 'CU-31 Registrar venta presencial'),
                       ('CU21', 'CU-21 Utilizar vestidor virtual (RA)'),
                       ('CU33', 'CU-33 Recibir recomendaciones de prendas')):
    blob, _ = imagen_despues(titulo, desde=secuencias)
    nuevos += [leyenda(f'Diagrama de secuencia del {nombre}.'), parrafo_imagen(blob)]

# Arquitectura
nuevos.append(ed.copiar_parrafo(sub_modelo, 'Diagrama de arquitectura'))
for titulo, texto in (('3.1.1 Diseño lógico', 'Arquitectura lógica del primer parcial: las capas del sistema.'),
                      ('3.1.2 Diseño Físico', 'Arquitectura física del primer parcial: el diagrama de despliegue.'),
                      ('4.2 Implementación Arquitectura Sistema Principal',
                       'Implementación de la arquitectura del sistema principal: el diagrama de componentes.')):
    blob, _ = imagen_despues(titulo)
    nuevos += [leyenda(texto), parrafo_imagen(blob)]

ed.insertar_despues(ancla, nuevos)
ed.cerrar(DOC)
print('ok', len(nuevos))
