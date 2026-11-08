# 3ra presentación (08/11) en el Word: lo que sale de los diagramas de EA y de las fichas.
#   2.3.2 / 2.3.3  los traspasos pasan a «pedidos en clase»; RF-67 (aviso de talla) y RF-68 (anomalías) como
#                  aportes propios nuevos;
#   2.4            RN-24;
#   2.5            CU-44 y CU-45 en la tabla, los totales, y el diagrama general nuevo (CU-01 a CU-45);
#   2.6            las fichas de CU-21 a CU-45, con su diagrama de casos de uso, en lugar de los títulos sueltos
#                  de «PARA SIGUIENTES PRESENTACIONES»;
#   3.2            la robustez de CU-21 a CU-45, con la leyenda de sus grupos de mensajes;
#   3.4            el diseño de clases de CU-21 a CU-45.
# Las fichas salen de scripts/p3-especificaciones.json y los grupos de scripts/ea-p3.datos.json
# (los arma scripts/p3_datos.py).
# Uso: python editar_08_11_p3.py <documento.docx> <carpeta con los JPG de EA (busca en subcarpetas)>
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
GRUPOS = {r['cu']: r['grupos'] for r in json.load(open(os.path.join(SCRIPTS, 'ea-p3.datos.json'), encoding='utf-8'))['robustez']}

ed = Editor(docx.Document(DOC))
T = ed.texto
BLIP = '{http://schemas.openxmlformats.org/drawingml/2006/main}blip'
NUEVOS = [f'CU-{n}' for n in range(21, 46)]
NOMBRES = ESP['casos']
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


def poner_lineas(tc, lineas):
    """Texto de una celda en un solo párrafo, con un salto de línea entre renglones (como las fichas de CU-13..20)."""
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


def nombre(cu):
    return f'{cu} — {NOMBRES[cu]}'


# =====================================================================
# 2.3.2 y 2.3.3: los traspasos los pidió la docente; dos aportes propios nuevos
h232 = titulo('2.3.2.', 'Titulo2')
h233 = titulo('2.3.3.', 'Titulo2')
intro232 = h232.getnext()
assert ed.reemplazar(intro232, r'automáticamente\.$', 'automáticamente. También pidió que las transferencias entre sucursales pasen a ser traspasos con '
              'pedido, seguimiento y sugerencias.') == 1
h_trasp = titulo('Traspasos entre sucursales', 'Titulo3', desde=h233)
bloque = [h_trasp]
el = h_trasp.getnext()
while not es_titulo(el, 'Titulo3'):
    bloque.append(el); el = el.getnext()
h_probador = el
for x in bloque:
    x.getparent().remove(x)
ed.insertar_despues(h233.getprevious(), bloque)
assert ed.reemplazar(h233.getnext(), r'propone 17 requisitos en cuatro frentes', 'propone 15 requisitos en cinco frentes') == 1

modelo_h3 = h_probador
modelo_texto = h_probador.getnext()
modelo_tabla = ed.tabla_despues(titulo('Cambio de prenda con diferencia de precio', 'Titulo3', desde=h232))  # 2 filas
assert len(modelo_tabla.findall(qn('w:tr'))) == 2
h234 = titulo('2.3.4.', 'Titulo2')
piezas = []
for tit, texto, rf, req in [
    ('Aviso de talla disponible',
     'Una prenda agotada en su talla deja de ser un callejón sin salida: el cliente pide el aviso y le llega apenas '
     'vuelve, y la empresa ve cuántos clientes esperan cada talla y color, lo que orienta las reposiciones y los '
     'traspasos.',
     'RF-67', 'Que el cliente pida un aviso cuando vuelva a haber unidades de una talla y un color agotados, y que '
              'la empresa consulte la demanda en espera'),
    ('Detección de anomalías en caja y devoluciones',
     'Usa la misma infraestructura de la analítica para vigilar el dinero: marca los turnos de caja y las '
     'devoluciones que se apartan de lo habitual y explica por qué, sin revisar turno por turno.',
     'RF-68', 'Detectar con aprendizaje no supervisado los turnos de caja y las devoluciones que se apartan de lo '
              'habitual, explicando el motivo de cada caso')]:
    t = copy.deepcopy(modelo_tabla)
    tr = t.findall(qn('w:tr'))[1]
    tcs = tr.findall(qn('w:tc'))
    ed.poner_celda(tcs[0], f'**{rf}**'); ed.poner_celda(tcs[1], req)
    piezas += [ed.copiar_parrafo(modelo_h3, tit), ed.copiar_parrafo(modelo_texto, texto), t, ed.nuevo_parrafo('')]
ed.insertar_despues(h234.getprevious(), piezas)

# =====================================================================
# 2.4: RN-24
rn = ed.tabla_despues(titulo('2.4.', 'Titulo11'))
ed.agregar_fila(rn, ['RN-24', 'Un cliente tiene como máximo un aviso pendiente por talla y color, y el aviso se '
                              'dispara una sola vez, cuando la existencia de la red pasa de cero a más de cero.'])
ed.recebrar(rn)

# =====================================================================
# 2.5: tabla, totales y el general nuevo
h25 = titulo('2.5.', 'Titulo11')
assert ed.reemplazar(h25.getnext(), r'Son 43 casos de uso', 'Son 45 casos de uso') == 1
assert ed.reemplazar(h25.getnext().getnext(), r'del RF-01 al RF-66', 'del RF-01 al RF-68') == 1
tabla25 = ed.tabla_despues(h25)
fila35 = ed.fila(tabla25, 'CU-35')
ed.reemplazar(fila35, r' \(propio\)', '')
# Lo que el código dice distinto de la tabla (lo vieron los agentes que leyeron el código):
# el CU-29 lo dispara el administrador con «Entrenar los modelos»; el probador (CU-37, CU-38) está en la web.
fila29 = ed.fila(tabla25, 'CU-29')
assert ed.reemplazar(fila29, r'^(.*)Sistema', lambda m: m.group(1) + 'Administrador de la empresa') == 1
assert ed.reemplazar(fila29, r'Backend', 'Web') == 1
for cu in ('CU-37', 'CU-38'):
    assert ed.reemplazar(ed.fila(tabla25, cu), r'Móvil', 'Web') == 1
ed.agregar_fila(tabla25, ['CU-44', 'Pedir aviso de talla disponible (propio)', 'Cliente', 'Web', '—', 'RF-67'])
ed.agregar_fila(tabla25, ['CU-45', 'Detectar anomalías en caja y devoluciones (propio)', 'Administrador de la empresa',
                          'Web', '—', 'RF-68'])
ed.recebrar(tabla25)
viejo = tabla25
while not list(viejo.iter(BLIP)):
    viejo = viejo.getnext()
viejo.addnext(parrafo_imagen(jpg('2.5 Diagrama general de casos de uso (CU-01 a CU-45)'), alto=22.0))
viejo.getparent().remove(viejo)

# =====================================================================
# 2.6: las fichas de CU-21 a CU-45
h26 = titulo('2.6.', 'Titulo11')
h20 = titulo('CU-20', 'Titulo3', desde=h26)
tabla20 = ed.tabla_despues(h20)
siguientes = titulo('PARA SIGUIENTES PRESENTACIONES', 'Titulo2', desde=h26)
# se quitan el título y los títulos sueltos hasta el capítulo III (queda el párrafo vacío que lo precede)
ancla = siguientes.getprevious()
el = siguientes
while not es_titulo(el.getnext(), 'CAPITULO'):
    nxt = el.getnext()
    el.getparent().remove(el)
    el = nxt
assert not T(el).strip(), T(el)
CAMPOS = ['Caso de uso', 'Descripción', 'Actores', 'Iniciador', 'Precondiciones', 'Flujo principal',
          'Flujos alternativos', 'Postcondiciones', 'Rastreo']
for cu in NUEVOS:
    e = ESP['espec'][cu]
    t = copy.deepcopy(tabla20)
    filas = t.findall(qn('w:tr'))
    assert [T(f.find(qn('w:tc'))).strip() for f in filas] == CAMPOS
    valores = [nombre(cu), e['descripcion'], e['actores'], e['iniciador'], e['precondiciones'],
               [f'{i}. {x}' for i, x in enumerate(e['flujo'], 1)], list(e['alternativos']),
               e['postcondiciones'], e['rastreo']]
    for f, v in zip(filas, valores):
        tc = f.findall(qn('w:tc'))[1]
        poner_lineas(tc, v if isinstance(v, list) else [v])
    ancla = ed.insertar_despues(ancla, [ed.copiar_parrafo(h20, nombre(cu)),
                                        parrafo_imagen(jpg(f'2.5 {cu} '), alto=9.0), t, ed.nuevo_parrafo('')])

# =====================================================================
# 3.2: robustez, con la leyenda de los grupos (como CU-13..20)
h33 = titulo('3.3.', 'Titulo11')
leyenda = ed.parrafo('Grupo 1:', desde=titulo('CU-20', 'Titulo3', desde=titulo('3.2.', 'Titulo11')))
h20_32 = titulo('CU-20', 'Titulo3', desde=titulo('3.2.', 'Titulo11'))
ancla = h33.getprevious()
for cu in NUEVOS:
    piezas = [ed.copiar_parrafo(h20_32, nombre(cu)), parrafo_imagen(jpg(f'3.2 {cu} '), alto=17.0)]
    piezas += [ed.copiar_parrafo(leyenda, f'Grupo {i}: {g}') for i, g in enumerate(GRUPOS[cu], 1)]
    ancla = ed.insertar_despues(ancla, piezas)

# =====================================================================
# 3.4: diseño de clases
h35 = titulo('3.5.', 'Titulo11')
h20_34 = titulo('CU-20', 'Titulo3', desde=titulo('3.4.', 'Titulo11'))
ancla = h35.getprevious()
for cu in NUEVOS:
    ancla = ed.insertar_despues(ancla, [ed.copiar_parrafo(h20_34, nombre(cu)),
                                        parrafo_imagen(jpg(f'3.4 {cu} '), alto=16.0)])

ed.cerrar(DOC)
print('ok', DOC)
