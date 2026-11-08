# Cap. V con evidencias (08/11): las imágenes del 5.2, 5.3 y 5.4 (docs/entregas/Presentacion-3/pruebas/
# evidencias.json), los resultados de las pruebas manuales en producción en la tabla del 5.5 (reembolso con
# Stripe, push en el teléfono, inventario offline y la analítica) con sus capturas, y el resultado del CP-05.
# Uso: python editar_08_11_cap5_capturas.py <documento.docx>
import io, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word-p2'))
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image
from docx_util import Editor

DOC = sys.argv[1]
PRUEBAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'entregas', 'Presentacion-3', 'pruebas')
EVID = json.load(open(os.path.join(PRUEBAS, 'evidencias.json'), encoding='utf-8'))
ed = Editor(docx.Document(DOC))
T = ed.texto


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return el.tag == qn('w:p') and st is not None and st.get(qn('w:val')) == estilo


def titulo(texto):
    return ed.buscar(lambda e: es_titulo(e, 'Titulo11') and T(e).strip().startswith(texto))


def imagen(ruta, alto, ancho_max=15.5):
    blob = open(ruta, 'rb').read()
    w, h = Image.open(io.BytesIO(blob)).size
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(min(ancho_max, alto * w / h)))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0); pf.alignment = 1
    return p._p


LEYENDA = ed.parrafo('Web: las empresas de la plataforma')   # leyenda del 3.6, va antes de la imagen


def figura(archivo, texto, alto=9.0, ancho_max=15.5):
    return [ed.copiar_parrafo(LEYENDA, texto), imagen(os.path.join(PRUEBAS, archivo), alto, ancho_max)]


def sub(txt):
    return ed.nuevo_parrafo(f'**{txt}**', con_siguiente=True)


# ---- 5.2 y 5.3: después del párrafo que cierra cada apartado ----------------------------------
for seccion, sigue, intro in [
        ('5.2', '5.3.', 'Evidencia: la salida de pytest de los módulos de la 3ra presentación.'),
        ('5.3', '5.4.', 'Evidencia: la consulta a la base de datos después de cada flujo, que muestra lo que quedó en '
                        'cada tabla (base de pruebas local, con Row Level Security).')]:
    ancla = titulo(sigue).getprevious()
    piezas = [sub(intro)]
    for archivo, texto in EVID[seccion]:
        piezas += figura(archivo, texto)
    ed.insertar_despues(ancla, piezas)

# ---- 5.4: al final de las fichas -------------------------------------------------------------
ancla = titulo('5.5.').getprevious()
piezas = [sub('Verificación de las correcciones: las pruebas de regresión de algunos de los errores.')]
for archivo, texto in EVID['5.4']:
    piezas += figura(archivo, texto)
ed.insertar_despues(ancla, piezas)

# ---- 5.5: la tabla de resultados -------------------------------------------------------------
h55 = titulo('5.5.')
tabla = ed.tabla_despues(h55)
RESULTADOS = {
    'Reembolso con Stripe': ('Aprobado',
        'Devolución web del pedido VB-20261108-23D7: el encargado recibió la prenda, Stripe devolvió Bs 190 '
        '(re_3UZW…) y figura «Reembolsado» en el panel; el cliente dio su conformidad y la nota ND-000003 quedó CERRADA'),
    'Push en el teléfono (FCM)': ('Aprobado',
        'Con Firebase configurado, al sincronizar llegó al teléfono «Sincronización: 1 operación(es)…»; el '
        'dispositivo queda registrado en la bitácora'),
    'Inventario offline en el teléfono (CU-21)': ('Aprobado',
        'Conteo en modo avión (39 → 38) guardado en la cola; al volver la conexión se sincronizó y el kardex muestra '
        'el AJUSTE −1 marcado «sin conexión»'),
}
for prueba, (res, com) in RESULTADOS.items():
    tcs = ed.fila(tabla, prueba).findall(qn('w:tc'))
    ed.poner_celda(tcs[1], res)
    ed.poner_celda(tcs[2], com)
ultima = ed.fila(tabla, 'Inventario offline en el teléfono (CU-21)')
ed.agregar_fila(tabla, ['Analítica y anomalías en producción', 'Aprobado',
                        'Con los datos de demostración: MAE 2,96 u. (7,5 % mejor que la línea base), R² 0,495 y '
                        'silueta 0,565; anomalías: 3 de 51 turnos y 2 de 35 devoluciones, cada una con su motivo'],
                despues_de=ultima)
ed.recebrar(tabla)

marcador = ed.parrafo('[Capturas:', desde=h55)
piezas = [ed.copiar_parrafo(h55.getnext(), 'Las capturas de las pruebas manuales en el sistema desplegado:')]
for archivo, texto, alto in [
        ('cp05-nota-ND-000003-cerrada-reembolso-stripe.jpg', 'Web: la nota ND-000003 cerrada, con el reembolso por la pasarela y la conformidad del cliente.', 8.0),
        ('cp05-stripe-pago-reembolsado.jpg', 'Stripe (modo de prueba): el pago del 08/11 figura «Reembolsado».', 7.0),
        ('cp05-mis-devoluciones-completada.jpg', 'Web: en «Mis compras», la devolución completada.', 7.0),
        ('web/cp07-analitica-modelos-entrenados-produccion.jpg', 'Web: la analítica entrenada en producción, con sus métricas.', 8.0),
        ('web/cp10-anomalias-turnos-produccion.jpg', 'Web: los turnos de caja marcados como anómalos, con el motivo.', 8.0),
        ('web/cp10-anomalias-devoluciones-produccion.jpg', 'Web: las devoluciones marcadas como anómalas.', 8.0)]:
    piezas += figura(archivo, texto, alto)
piezas += figura('movil/movil-cu21-cu42-secuencia.png',
                 'Móvil (CU-21 y CU-42): 1) el inventario con conexión; 2) el conteo físico en modo avión (39 → 38); '
                 '3) guardado sin conexión, pendiente de sincronizar; 4) al volver la conexión se sincroniza y llega el '
                 'aviso push (FCM); 5) el kardex con el ajuste −1 hecho sin conexión.', alto=8.0)
ed.insertar_despues(marcador, piezas)
marcador.getparent().remove(marcador)

# ---- 5.6: CP-05 ---------------------------------------------------------------------------------
cp05 = ed.buscar(lambda e: e.tag == qn('w:tbl') and T(e).startswith('CP-05'))
tc = ed.fila(cp05, 'Resultado obtenido').findall(qn('w:tc'))[1]
ed.poner_celda(tc, 'Aprobado. Probado el 08/11 en producción: reembolso real en Stripe (modo de prueba) y nota ND-000003 '
                   'CERRADA con la conformidad del cliente (capturas en el 5.5).')

ed.cerrar(DOC)
print('ok', DOC)
