# 4.3 Implementación de la base de datos, en el Word de la 2da presentación (01/11).
#   4.3.1 Modelo lógico: una tabla por entidad, de tres filas: el nombre de la entidad; sus atributos,
#         uno por columna; y debajo de cada uno «PK» o «FK» según corresponda (formato pedido por la ing).
#         Las entidades con muchos atributos siguen en otro par de filas, para que se lean en la hoja.
#   4.3.2 Modelo físico: la tabla de volumen de cada entidad, con el formato del 3.3.2 del 1er parcial
#         (Campo, Tipo de dato, Tamaño, Descripción, Llave, Nulo).
# Son las mismas 32 tablas del 3.5, en el mismo orden, y salen de los mismos datos:
#   scripts/ea-p2-bd.datos.json   columnas, tipos, PK/FK y nulos (de information_schema de la QA);
#   columnas_unicas.json          las columnas con UNIQUE (de pg_index, solo lectura);
#   volumen_1er_parcial.json      las descripciones del 1er parcial, que se reusan tal cual.
# Las descripciones que faltan (las tablas y columnas nuevas del 2do parcial) están abajo, tomadas de los
# modelos y sus comentarios en backend/app/modules/*/models.py.
# Uso: python editar_01_11_bd_4_3.py <documento.docx>
import json, os, re, sys
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx_util import Editor

AQUI = os.path.dirname(os.path.abspath(__file__))
DOC = sys.argv[1]
ed = Editor(docx.Document(DOC))
T = ed.texto
datos = json.load(open(os.path.join(AQUI, '..', 'ea-p2-bd.datos.json'), encoding='utf-8'))
unicas = json.load(open(os.path.join(AQUI, 'columnas_unicas.json'), encoding='utf-8'))
vol_p1 = json.load(open(os.path.join(AQUI, 'volumen_1er_parcial.json'), encoding='utf-8'))
parte = datos['partes'][0]
ORDEN = [t for col in [
    ["plan", "suscripcion", "pago_simulado", "consumo_cupo"],
    ["empresa", "cliente_empresa", "cliente"],
    ["usuario", "rol", "sesion_token", "bitacora"],
    ["ciudad", "sucursal", "caja", "empleado"],
    ["turno_caja", "venta", "detalle_venta", "comprobante", "devolucion"],
    ["operacion_offline", "reserva", "reserva_detalle"],
    ["existencia", "movimiento_inventario", "variante_producto"],
    ["producto", "categoria", "talla", "color", "imagen_producto", "promocion"]] for t in col]
assert sorted(ORDEN) == sorted(parte['propias']), set(ORDEN) ^ set(parte['propias'])

DESCRIPCION = {
    'cliente_empresa': {'cliente_id': 'Cliente que compra en la empresa',
                        'empresa_id': 'Empresa en la que compra el cliente',
                        'creado_en': 'Cuándo empezó a comprar en la empresa'},
    'consumo_cupo': {'empresa_id': 'Empresa que consume el cupo',
                     'recurso': 'Cupo del plan que se consume: reportes con IA o fotos con IA',
                     'periodo': 'Primer día del mes, en hora de Bolivia',
                     'usados': 'Cuántas veces se usó el cupo en el mes'},
    'devolucion': {'tipo': 'DEVOLUCION o CAMBIO',
                   'venta_cambio_id': 'En un cambio, la venta de la prenda que se lleva',
                   'diferencia': 'Lo que se cobra o se devuelve por la diferencia de precio de un cambio',
                   'metodo_diferencia': 'Cómo se pagó la diferencia'},
    'empresa': {'id': 'Identificador de la empresa: el tenant',
                'nombre': 'Nombre comercial',
                'razon_social': 'Razón social para la facturación',
                'nit': 'NIT de la empresa',
                'slug': 'Identifica a la empresa en el login y en la dirección de su tienda; no se cambia',
                'correo_contacto': 'Correo de contacto de la empresa',
                'estado': 'ACTIVA o BAJA',
                'logo': 'Ruta del logo de su tienda (CU-12); vacío usa el de Violet',
                'color_principal': 'Color principal de su tienda, en hexadecimal',
                'color_secundario': 'Color secundario de su tienda, en hexadecimal'},
    'operacion_offline': {
        'uuid': 'Identificador que genera el dispositivo: si la operación llega dos veces no se duplica',
        'tipo': 'VENTA o RESERVA',
        'estado': 'CONFIRMADA o RECHAZADA, según lo que decidió el servidor',
        'sucursal_id': 'Sucursal de la operación; si se rechaza, es la que atiende la devolución',
        'usuario_id': 'Cajero o cliente que la hizo',
        'dispositivo': 'Dispositivo desde el que se envió',
        'creada_en_cliente': 'Cuándo se hizo, según el reloj del dispositivo',
        'recibida_en': 'Cuándo llegó al servidor; decide quién llegó primero',
        'intentos': 'Cuántas veces llegó; más de una, el dispositivo reintentó',
        'metodo_pago': 'EFECTIVO o QR, si se cobró sin conexión',
        'monto_cobrado': 'Lo que se cobró sin conexión',
        'referencia_pago': 'Número de la operación QR que da el banco',
        'carga': 'Lo que envió el dispositivo, tal cual',
        'venta_id': 'Venta que creó al confirmarse',
        'reserva_id': 'Reserva que creó al confirmarse',
        'motivo_rechazo': 'Por qué el servidor la rechazó',
        'devuelto_en': 'Cuándo se devolvió el dinero de una operación rechazada (CU-19)',
        'devuelto_por': 'Encargado que registró la devolución',
        'metodo_devolucion': 'Cómo se devolvió el dinero',
        'referencia_devolucion': 'Referencia de la devolución por QR',
        'observacion_devolucion': 'Observación del encargado sobre la devolución'},
    'pago_simulado': {'suscripcion_id': 'Suscripción que se pagó',
                      'plan_id': 'Plan que se cobró',
                      'concepto': 'ALTA, CAMBIO o RENOVACION',
                      'monto': 'Monto cobrado, en bolivianos',
                      'comprobante': 'Número del comprobante simulado',
                      'pagado_en': 'Cuándo se registró el pago'},
    'plan': {'codigo': 'Código corto del plan',
             'nombre': 'Nombre del plan: Básico, Profesional o Empresarial',
             'precio_mensual': 'Precio por período, en bolivianos',
             'duracion_dias': 'Días que dura cada período',
             'max_sucursales': 'Sucursales activas permitidas; vacío es ilimitado',
             'max_empleados': 'Empleados activos permitidos; vacío es ilimitado',
             'cupo_reportes_ia': 'Reportes con IA por mes; vacío es ilimitado',
             'cupo_fotos_ia': 'Fotos realistas con IA por mes; vacío es ilimitado',
             'funciones': 'Funciones que incluye el plan, en JSON',
             'activo': 'Si se puede contratar'},
    'suscripcion': {'plan_id': 'Plan contratado',
                    'inicio': 'Primer día de la suscripción',
                    'vencimiento': 'Día en que vence',
                    'estado': 'VIGENTE, SUSPENDIDA, VENCIDA o REEMPLAZADA',
                    'empresa_id': 'Empresa que contrata'},
}
GENERICAS = {'id': 'Identificador de la fila', 'creado_en': 'Cuándo se creó la fila',
             'actualizado_en': 'Cuándo se modificó por última vez'}


def descripcion(tabla, col, nulo):
    if col in DESCRIPCION.get(tabla, {}):
        return DESCRIPCION[tabla][col]
    previa = vol_p1.get(tabla.upper(), {}).get(col.upper())
    if previa:
        return previa[3]
    if col == 'empresa_id':
        if nulo:
            return 'Empresa a la que pertenece; vacío para el administrador de la plataforma y los clientes'
        return 'Empresa dueña de la fila; la usa Row Level Security'
    if col in GENERICAS:
        return GENERICAS[col]
    raise LookupError(f'{tabla}.{col} sin descripción')


def tipo_y_tamano(t):
    m = re.match(r'(\w+)(?:\((.+)\))?', t)
    base, arg = m.group(1), m.group(2)
    return {'BIGINT': 'ENTERO GRANDE', 'BIGSERIAL': 'ENTERO GRANDE', 'INTEGER': 'ENTERO', 'SERIAL': 'ENTERO',
            'SMALLINT': 'ENTERO CORTO', 'VARCHAR': 'CADENA', 'CHAR': 'CADENA FIJA', 'NUMERIC': 'DECIMAL',
            'TIMESTAMPTZ': 'FECHA Y HORA', 'TIMESTAMP': 'FECHA Y HORA', 'DATE': 'FECHA', 'TIME': 'HORA',
            'BOOLEAN': 'BOOLEANO', 'JSONB': 'JSON', 'JSON': 'JSON', 'UUID': 'UUID', 'TEXT': 'TEXTO'}[base], (arg or '-')


def llave(tabla, c):
    partes = []
    if 'PK' in c['k']:
        partes.append('PRIMARIA')
    if 'FK' in c['k']:
        partes.append('FORÁNEA')
    if c['n'] in unicas.get(tabla, []) and 'PK' not in c['k']:
        partes.append('ÚNICA')
    return ' / '.join(partes)


def columnas(tabla):
    """La PK primero, después las demás en el orden de la tabla."""
    cols = datos['tablas'][tabla]['columnas']
    return [c for c in cols if 'PK' in c['k']] + [c for c in cols if 'PK' not in c['k']]


# ---------------------------------------------------------------- piezas de Word --
def titulo(texto, estilo='Titulo11', desde=None):
    def es(el):
        st = el.find('.//' + qn('w:pStyle'))
        return el.tag == qn('w:p') and st is not None and st.get(qn('w:val')) == estilo and T(el).strip().startswith(texto)
    return ed.buscar(es, desde)


modelo_texto = ed.parrafo('Cada ficha sigue el formato de ICONIX')
modelo_h2 = titulo('2.3.1.', 'Titulo2')


def texto(t):
    return ed.copiar_parrafo(modelo_texto, t)


def rotulo(t):
    """El nombre de la tabla antes de su tabla de volumen, en negrita y pegado a ella (como en el 1er parcial)."""
    p = ed.nuevo_parrafo(f'**{t}**', con_siguiente=True)
    return p


def achicar(tbl, tam):
    for r in tbl.iter(qn('w:r')):
        rpr = r.find(qn('w:rPr'))
        if rpr is None:
            rpr = OxmlElement('w:rPr'); r.insert(0, rpr)
        for s in rpr.findall(qn('w:sz')):
            rpr.remove(s)
        sz = OxmlElement('w:sz'); sz.set(qn('w:val'), str(tam * 2)); rpr.append(sz)


def no_partir(tbl):
    """Que una tabla corta no se parta entre dos páginas."""
    for tr in tbl.findall(qn('w:tr')):
        for p in tr.iter(qn('w:p')):
            ppr = p.find(qn('w:pPr'))
            if ppr is None:
                ppr = OxmlElement('w:pPr'); p.insert(0, ppr)
            ppr.append(OxmlElement('w:keepNext'))


POR_FILA = 6
TOTAL = 9782


def tabla_logica(tabla):
    cols = columnas(tabla)
    grupos = [cols[i:i + POR_FILA] for i in range(0, len(cols), POR_FILA)]
    n = min(POR_FILA, len(cols))
    anchos = [TOTAL // n] * n
    anchos[-1] += TOTAL - sum(anchos)
    # Fila 1: el nombre; después, por cada grupo, la fila de atributos y la de claves.
    filas = []
    for g in grupos:
        filas.append([c['n'] for c in g] + [''] * (n - len(g)))
        filas.append([c['k'].replace(',', ', ') for c in g] + [''] * (n - len(g)))
    tbl = ed.tabla([datos['tablas'][tabla]['nombre']] + [''] * (n - 1), filas, anchos)
    # La fila del nombre ocupa todo el ancho.
    fila0 = tbl.findall(qn('w:tr'))[0]
    celdas = fila0.findall(qn('w:tc'))
    celdas[0].find(qn('w:tcPr')).find(qn('w:tcW')).set(qn('w:w'), str(TOTAL))
    gs = OxmlElement('w:gridSpan'); gs.set(qn('w:val'), str(n))
    celdas[0].find(qn('w:tcPr')).insert(1, gs)
    for c in celdas[1:]:
        fila0.remove(c)
    # Los atributos en negrita sobre blanco; las claves centradas sobre gris, como pie de cada atributo.
    for i, tr in enumerate(tbl.findall(qn('w:tr'))[1:]):
        es_clave = i % 2 == 1
        for tc in tr.findall(qn('w:tc')):
            tc.find(qn('w:tcPr')).find(qn('w:shd')).set(qn('w:fill'), 'F6F8FA' if es_clave else 'FFFFFF')
            for p in tc.iter(qn('w:p')):
                ppr = p.find(qn('w:pPr'))
                jc = OxmlElement('w:jc'); jc.set(qn('w:val'), 'center'); ppr.append(jc)
            for r in tc.iter(qn('w:r')):
                rpr = r.find(qn('w:rPr'))
                if rpr is None:
                    rpr = OxmlElement('w:rPr'); r.insert(0, rpr)
                for b in rpr.findall(qn('w:b')):
                    rpr.remove(b)
                if not es_clave:
                    rpr.insert(0, OxmlElement('w:b'))
    achicar(tbl, 8)
    no_partir(tbl)
    return tbl


def tabla_volumen(tabla):
    filas = []
    for c in columnas(tabla):
        tipo, tam = tipo_y_tamano(c['t'])
        filas.append([c['n'].upper(), tipo, tam, descripcion(tabla, c['n'], c['nulo']),
                      llave(tabla, c), 'SÍ' if c['nulo'] else 'NO'])
    tbl = ed.tabla(['Campo', 'Tipo de dato', 'Tamaño', 'Descripción', 'Llave', 'Nulo'], filas,
                   [2350, 1500, 850, 3282, 1250, 550])
    achicar(tbl, 8)
    return tbl


# ------------------------------------------------------------------------- 4.3 --
cap4_3 = titulo('4.3.')
pendiente = cap4_3.getnext()
assert T(pendiente).startswith('[Pendiente]'), T(pendiente)
piezas = [
    texto('La base de datos es PostgreSQL 17 en Supabase. El esquema lo crean las migraciones de Alembic, que se '
          'aplican solas al desplegar la API; las del segundo parcial son de la 0022 a la 0028: la base '
          'multitenant con la columna de empresa y Row Level Security (0022), el rol de la plataforma (0023), el '
          'consumo de cupos (0024), el correo por empresa (0025), la marca de la tienda (0026), el pago simulado '
          '(0027) y la operación sin conexión (0028). Las 38 tablas del tenant tienen Row Level Security: cada '
          'consulta ve solo las filas de la empresa del usuario, porque la API se conecta con el rol violet_app y '
          'fija la empresa en cada petición. Se describen las 32 tablas que usan CU-01 a CU-20, las mismas del '
          'diseño de la base de datos (3.5).'),
    ed.copiar_parrafo(modelo_h2, '4.3.1. Modelo lógico'),
    texto('Una tabla por entidad: en la primera fila su nombre, en la segunda sus atributos y en la tercera, '
          'debajo de cada atributo, si es clave primaria (PK) o foránea (FK). Las entidades con más de seis '
          'atributos siguen en otro par de filas.'),
]
for t in ORDEN:
    piezas += [tabla_logica(t), ed.nuevo_parrafo('')]
piezas += [
    ed.copiar_parrafo(modelo_h2, '4.3.2. Modelo físico'),
    texto('La tabla de volumen de cada entidad, con el mismo formato que en el primer parcial: el campo, el tipo de '
          'dato, su tamaño, qué guarda, si es llave primaria, foránea o única, y si admite nulo. Los tipos y las '
          'llaves salen del esquema real de la base.'),
]
for t in ORDEN:
    piezas += [rotulo(datos['tablas'][t]['nombre']), tabla_volumen(t), ed.nuevo_parrafo('')]
ed.insertar_despues(pendiente, piezas)
pendiente.getparent().remove(pendiente)

ed.cerrar(DOC)
print('ok', len(ORDEN), 'tablas')
