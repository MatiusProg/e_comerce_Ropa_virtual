# 08/11 (tarde), tercera tanda en el Word:
#   2.3.2  RF-69: el reporte transaccional del cliente (pedido de la docente);
#   2.5    CU-46 en la tabla, los totales (46 CU, RF-01 a RF-69) y el diagrama general CU-01 a CU-46;
#   2.6    la ficha del CU-46 con su diagrama de casos de uso;
#   3.1    UN SOLO modelo de dominio (CU-01 a CU-46) en lugar de los dos;
#   3.5    UN SOLO diseño de la base de datos (CU-01 a CU-46) en lugar de los dos;
#   6.1/6.2 y bibliografía al día (CU-46, el probador nativo ya existe, fuentes de la 3ra presentación).
# Uso: python editar_08_11_cu46_y_unicos.py <documento.docx> <carpeta JPG de EA>
import copy, glob, io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word-p2'))
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image
from docx_util import Editor

DOC, JPG = sys.argv[1:3]
SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ESP = json.load(open(os.path.join(SCRIPTS, 'p3-especificaciones.json'), encoding='utf-8'))
ed = Editor(docx.Document(DOC))
T = ed.texto
BLIP = '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'


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


def parrafo_imagen(blob, alto, ancho_max=15.5):
    w, h = Image.open(io.BytesIO(blob)).size
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(min(ancho_max, alto * w / h)))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0); pf.alignment = 1
    return p._p


def tiene_imagen(el):
    return bool(list(el.iter(BLIP)))


def poner_lineas(tc, lineas):
    ed.poner_celda(tc, lineas[0])
    p = tc.find(qn('w:p'))
    base = p.findall(qn('w:r'))[-1]
    for ln in lineas[1:]:
        r = copy.deepcopy(base)
        for hijo in list(r):
            if hijo.tag != qn('w:rPr'):
                r.remove(hijo)
        r.append(OxmlElement('w:br'))
        t = OxmlElement('w:t'); t.text = ln; t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t)
        p.append(r)


# ---- 2.3.2: RF-69 -----------------------------------------------------------------------------
h232 = titulo('2.3.2.', 'Titulo2')
h233 = titulo('2.3.3.', 'Titulo2')
assert ed.reemplazar(h232.getnext(), r'pedido, seguimiento y sugerencias\.$',
                     'pedido, seguimiento y sugerencias. En la 3ra presentación pidió además un reporte '
                     'transaccional para el cliente, que pueda pedir por voz.') == 1
modelo_h3 = titulo('Traspasos entre sucursales', 'Titulo3', desde=h232)
modelo_tabla = ed.tabla_despues(titulo('Cambio de prenda con diferencia de precio', 'Titulo3', desde=h232))
t = copy.deepcopy(modelo_tabla)
tcs = t.findall(qn('w:tr'))[1].findall(qn('w:tc'))
ed.poner_celda(tcs[0], '**RF-69**')
ed.poner_celda(tcs[1], 'Que el cliente consulte por voz o texto sus comprobantes (compras y devoluciones), filtrando por '
                       'cantidad, período y tipo, y vea de cada uno la fecha, el código, el total, el estado y un QR de '
                       'verificación pública que no expone datos personales')
ed.insertar_despues(h233.getprevious(), [ed.copiar_parrafo(modelo_h3, 'Reporte transaccional del cliente'), t,
                                          ed.nuevo_parrafo('')])

# ---- 2.5 --------------------------------------------------------------------------------------
h25 = titulo('2.5.')
assert ed.reemplazar(h25.getnext(), r'Son 45 casos de uso', 'Son 46 casos de uso') == 1
assert ed.reemplazar(h25.getnext().getnext(), r'del RF-01 al RF-68', 'del RF-01 al RF-69') == 1
tabla25 = ed.tabla_despues(h25)
ed.agregar_fila(tabla25, ['CU-46', 'Consultar mis comprobantes por voz', 'Cliente', 'Web y móvil', '—', 'RF-69'])
ed.recebrar(tabla25)
viejo = tabla25
while not tiene_imagen(viejo):
    viejo = viejo.getnext()
viejo.addnext(parrafo_imagen(jpg('2.5 Diagrama general de casos de uso (CU-01 a CU-46)'), alto=22.0))
viejo.getparent().remove(viejo)

# ---- 2.6: ficha del CU-46, después de la del CU-45 --------------------------------------------
h26 = titulo('2.6.')
h45 = titulo('CU-45', 'Titulo3', desde=h26)
tabla45 = ed.tabla_despues(h45)
e = ESP['espec']['CU-46']
nombre46 = f"CU-46 — {ESP['casos']['CU-46']}"
t = copy.deepcopy(tabla45)
valores = [nombre46, e['descripcion'], e['actores'], e['iniciador'], e['precondiciones'],
           [f'{i}. {x}' for i, x in enumerate(e['flujo'], 1)], list(e['alternativos']),
           e['postcondiciones'], e['rastreo']]
for fila, v in zip(t.findall(qn('w:tr')), valores):
    poner_lineas(fila.findall(qn('w:tc'))[1], v if isinstance(v, list) else [v])
ancla = tabla45.getnext()  # el párrafo vacío que sigue a la ficha del CU-45
ed.insertar_despues(ancla, [ed.copiar_parrafo(h45, nombre46),
                            parrafo_imagen(jpg('2.5 CU-46 '), alto=6.0), t, ed.nuevo_parrafo('')])

# ---- 3.1 y 3.5: uno solo -------------------------------------------------------------------------
for seccion, sigue, prefijo, texto, alto in [
        ('3.1.', '3.2.', '3.1 Modelo de dominio (CU-01 a CU-46)',
         'El modelo de dominio reúne, en un solo diagrama, las entidades del negocio que aparecen en la robustez de '
         'todos los casos de uso del segundo parcial (CU-01 a CU-46): la plataforma y sus planes, la organización, '
         'los clientes, la caja, las ventas, las devoluciones y los traspasos, el catálogo con sus ofertas, la '
         'analítica, el probador y lo que vive en el dispositivo sin conexión. Va corto, como pide la docente: '
         'entidades sin atributos, con el verbo y la multiplicidad de cada asociación; las tablas de detalle se '
         'dibujan como asociación y lo que se guarda en el dispositivo va en otro color.', 15.0),
        ('3.5.', '3.6.', '3.5 Dise',
         'El diseño de la base de datos muestra, en un solo diagrama, las 52 tablas que usan los casos de uso del '
         'segundo parcial (CU-01 a CU-46), leídas de la base en la última migración (0043): cada una con todas sus '
         'columnas, su tipo y «PK»/«FK», y las relaciones con su verbo y la cardinalidad que obliga la base (1 si la '
         'FK es NOT NULL, 0..1 si admite nulo; 0..1 del otro lado si la FK es única). Las tablas del tenant llevan el '
         'estereotipo «rls»; las del primer parcial que este parcial no toca están en el Anexo.', 15.0)]:
    h = titulo(seccion)
    fin = titulo(sigue)
    el = h.getnext()
    while el is not fin:   # se quitan los textos e imágenes de los dos diagramas anteriores
        nxt = el.getnext()
        el.getparent().remove(el)
        el = nxt
    intro = ed.nuevo_parrafo(texto)
    # Un diagrama muy ancho queda ilegible en una hoja vertical: se rota 90° y ocupa la hoja entera.
    blob = jpg(prefijo)
    img = Image.open(io.BytesIO(blob))
    if img.width > 1.3 * img.height:
        salida = io.BytesIO()
        img.rotate(90, expand=True).save(salida, format='JPEG', quality=92)
        blob = salida.getvalue()
        alto = 21.5
    ed.insertar_despues(h, [intro, parrafo_imagen(blob, alto=alto), ed.nuevo_parrafo('')])

# ---- 6.1 y 6.2 -------------------------------------------------------------------------------------
h61 = titulo('6.1.')
conclusiones = ed.tabla_despues(h61)
assert ed.reemplazar(conclusiones, r'\(CU-01 a CU-43\)', '(CU-01 a CU-46)') == 1
fila = ed.fila(conclusiones, 'Lo pedido en clase y los aportes propios')
celda = fila.findall(qn('w:tc'))[1]
assert ed.reemplazar(celda, r'(\S)$', lambda m: (m.group(1) if m.group(1) != '.' else '') + '. A pedido de la docente se sumó el reporte transaccional del cliente por voz, con el '
                                 'QR de verificación de cada comprobante (CU-46).') == 1
probador = ed.parrafo('Probador nativo en Flutter')
ed.poner_texto(probador, 'Probador con fotos de la prenda en todas sus tallas y colores, y que siga también la cadera y '
                         'el giro del torso (hoy se ancla en los hombros), para que la prenda acompañe mejor el '
                         'movimiento.')

# ---- Bibliografía -----------------------------------------------------------------------------------
ultima = ed.parrafo('FastAPI. Documentación oficial: dependencias y seguridad.')
nuevas = [
    'Liu, F. T., Ting, K. M. y Zhou, Z.-H. (2008). Isolation Forest. IEEE International Conference on Data Mining.',
    'Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, 12.',
    'Google. ML Kit: Pose Detection. Documentación oficial para Android y Flutter.',
    'Google. MediaPipe: Pose Landmarker. Documentación oficial.',
    'Google. Firebase Cloud Messaging. Documentación oficial.',
    'Google. Gemini API. Documentación oficial: generación de texto e imágenes.',
    'Thomson, M., Damaggio, E. y Raymor, B. (2016). RFC 8030: Generic Event Delivery Using HTTP Push. IETF.',
    'Thomson, M. y Beverloo, P. (2017). RFC 8292: Voluntary Application Server Identification (VAPID) for Web Push. IETF.',
    'Stripe. API Reference: Checkout Sessions y Refunds. Documentación oficial.',
]
ed.insertar_despues(ultima, [ed.copiar_parrafo(ultima, x) for x in nuevas])

ed.cerrar(DOC)
print('ok', DOC)
