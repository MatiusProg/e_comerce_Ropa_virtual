# Capítulo II para la 2da presentación (01/11). Va después de editar_01_11_cap1.py:
#   - F1 y F2 de la ing: roles y permisos por empresa, avisos push y devolución automática del pago
#     (RF-64 a RF-66, CU-41 a CU-43, para la 3ra presentación);
#   - la nota de devolución con su detalle por prenda y la conformidad del cliente (RF-37, RN-20);
#   - la tabla 2.5 corregida contra lo construido (CU-13 a CU-16);
#   - las fichas de CU-13 a CU-20, escritas sobre el código ya hecho.
# Uso: python editar_01_11_cap2.py <documento.docx>
import copy, sys
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx_util import Editor, XML_SPACE

DOC = sys.argv[1]
ed = Editor(docx.Document(DOC))
T = ed.texto


def celdas(tr):
    return tr.findall(qn('w:tc'))


def agregar_al_final(p, txt):
    """Agrega texto al final de un párrafo, con el formato de su último run."""
    r = copy.deepcopy(p.findall(qn('w:r'))[-1])
    for hijo in list(r):
        if hijo.tag != qn('w:rPr'):
            r.remove(hijo)
    t = OxmlElement('w:t'); t.text = txt; t.set(XML_SPACE, 'preserve')
    r.append(t)
    p.append(r)


def celda_lineas(tc, lineas):
    """Deja la celda con varias líneas separadas por saltos de línea, como las fichas hechas a mano."""
    ps = tc.findall(qn('w:p'))
    for p in ps[1:]:
        tc.remove(p)
    p = ps[0]
    runs = p.findall(qn('w:r'))
    rpr = runs[0].find(qn('w:rPr')) if runs else None
    for r in runs:
        p.remove(r)

    def run():
        r = OxmlElement('w:r')
        if rpr is not None:
            r.append(copy.deepcopy(rpr))
        return r

    for i, linea in enumerate(lineas):
        if i:
            r = run(); r.append(OxmlElement('w:br')); p.append(r)
        r = run()
        t = OxmlElement('w:t'); t.text = linea; t.set(XML_SPACE, 'preserve')
        r.append(t)
        p.append(r)


# =====================================================================
# 2.3.2 Lo pedido en clase: la nota de devolución y lo nuevo de la 2da presentación
intro = ed.parrafo('La docente los pidió en clase')
agregar_al_final(intro, ' En la 2da presentación pidió además que el administrador de cada empresa gestione los '
                        'roles y los permisos de su personal según su plan, avisos push para las operaciones sin '
                        'conexión y que el pago de una operación rechazada se devuelva automáticamente.')

tabla_dev = ed.tabla_despues(ed.parrafo('Devoluciones vía web', exacto=True))
ed.poner_celda(celdas(ed.fila(tabla_dev, 'RF-37'))[1],
               'Registrar una nota de devolución con el detalle de cada prenda devuelta o cambiada (la talla y el '
               'precio de la original y de la nueva, la diferencia cobrada o devuelta y el motivo) y la '
               'conformidad del cliente. La nota mueve el inventario y mantiene coherentes los ingresos y egresos')

titulo_cambio = ed.parrafo('Cambio de prenda con diferencia de precio', exacto=True)
tabla_cambio = ed.tabla_despues(titulo_cambio)
GRUPOS = [
    ('Roles y permisos por empresa', [
        ('RF-64', 'Que el administrador de la empresa cree roles propios, les asigne permisos y se los asigne a su '
                  'personal, sin afectar a las otras empresas y dentro de lo que permite su plan'),
    ]),
    ('Avisos push y devolución automática del pago', [
        ('RF-65', 'Enviar un aviso push al cliente o al cajero cuando una operación sin conexión se confirma o se '
                  'rechaza al sincronizar'),
        ('RF-66', 'Devolver automáticamente el pago de una operación sin conexión rechazada, por el mismo medio con '
                  'que se cobró: el QR se reintegra solo (simulado) y el efectivo queda registrado para entregarse '
                  'en la sucursal; en los dos casos se avisa al cliente'),
    ]),
]
ancla = tabla_cambio
for titulo, filas in GRUPOS:
    vacio = copy.deepcopy(titulo_cambio.getprevious())
    sub = ed.copiar_parrafo(titulo_cambio, titulo)
    tbl = copy.deepcopy(tabla_cambio)
    for tr in tbl.findall(qn('w:tr'))[2:]:
        tbl.remove(tr)
    primera = tbl.findall(qn('w:tr'))[1]
    ed.poner_celda(celdas(primera)[0], f'**{filas[0][0]}**')
    ed.poner_celda(celdas(primera)[1], filas[0][1])
    ultima = primera
    for rf, texto in filas[1:]:
        ultima = ed.agregar_fila(tbl, [rf, texto], despues_de=ultima)
    ed.recebrar(tbl)
    ancla = ed.insertar_despues(ancla, [vacio, sub, tbl])

# =====================================================================
# 2.4 Reglas de negocio
tabla_rn = ed.tabla_despues(ed.parrafo('Son las reglas que el código hace cumplir'))
ultima = ed.fila(tabla_rn, 'RN-19')
for rn, texto in (
    ('RN-20', 'Una nota de devolución registra la conformidad del cliente: si aceptó el cambio o la devolución y su '
              'observación. Sin esa conformidad la nota no se cierra'),
    ('RN-21', 'El pago de una operación sin conexión rechazada se devuelve una sola vez, por el mismo medio con que '
              'se cobró, y la devolución queda registrada con quién, cuándo y cómo'),
    ('RN-22', 'Los roles y permisos que crea una empresa son solo suyos: no los ve ni los usa ninguna otra, y no '
              'pueden dar acceso a funciones que su plan no incluye'),
):
    ultima = ed.agregar_fila(tabla_rn, [rn, texto], despues_de=ultima)
ed.recebrar(tabla_rn)

# =====================================================================
# 2.5 Tabla de casos de uso: lo construido y los tres nuevos
p25 = ed.parrafo('Son 40 casos de uso')
assert ed.reemplazar(p25, 'Son 40 casos de uso', 'Son 43 casos de uso') == 1
p25b = ed.parrafo('Todos los RF, del RF-01 al RF-63')
assert ed.reemplazar(p25b, 'del RF-01 al RF-63', 'del RF-01 al RF-66') == 1

tabla_cu = ed.tabla_despues(p25)
CORRECCIONES = {  # columna -> valor, contra lo que hace el código
    'CU-13': {2: 'Cajero o cliente'},
    'CU-14': {3: 'Web'},
    'CU-15': {2: 'Cliente', 3: 'Móvil'},
    'CU-16': {2: 'Cajero', 3: 'Web'},
}
for cu, cambios in CORRECCIONES.items():
    tcs = celdas(ed.fila(tabla_cu, cu))
    for col, valor in cambios.items():
        ed.poner_celda(tcs[col], valor)

ultima = ed.fila(tabla_cu, 'CU-40')
NUEVOS = [
    ('CU-41', 'Gestionar roles y permisos de la empresa', 'Administrador de la empresa', 'Web', '—', 'RF-64'),
    ('CU-42', 'Enviar avisos push de las operaciones sin conexión', 'Sistema', 'Web y móvil', '—', 'RF-65'),
    ('CU-43', 'Devolver automáticamente el pago de una operación rechazada', 'Sistema', 'Backend', '—', 'RF-66'),
]
for fila in NUEVOS:
    ultima = ed.agregar_fila(tabla_cu, list(fila), despues_de=ultima)
ed.recebrar(tabla_cu)

# =====================================================================
# 2.6 Fichas de CU-13 a CU-20
FICHAS = {
    'CU-13': dict(
        descripcion='Permite al cajero, desde la PWA, y al cliente, desde la aplicación móvil, descargar con conexión '
                    'los datos que necesitan para trabajar sin ella.',
        actores='Cajero, cliente', iniciador='Cajero o cliente',
        pre='El usuario inició sesión con conexión. Si es cajero, tiene su turno de caja abierto.',
        flujo=[
            '1. El usuario abre la pantalla «Sin conexión» y elige preparar el dispositivo.',
            '2. El sistema verifica el rol y, si es cajero, que tenga un turno de caja abierto.',
            '3. El sistema arma el paquete de su empresa. Al cajero: las prendas con existencia en su sucursal, con '
            'su precio y su descuento vigente, los clientes de la empresa y su turno. Al cliente: las sucursales '
            'activas con su horario y las prendas con su foto, su categoría y su existencia por sucursal.',
            '4. El sistema marca el paquete con la hora en que se generó y su vigencia de 12 horas.',
            '5. El dispositivo guarda el paquete (IndexedDB en la PWA, SQLite en el móvil) y reemplaza el anterior '
            'en una sola transacción. En el móvil, lo ya apartado en reservas pendientes se descuenta de la '
            'existencia.',
            '6. El móvil descarga las fotos de las prendas a su memoria.',
            '7. El sistema muestra la fecha de los datos y cuántas sucursales y prendas guardó.',
        ],
        alternos=[
            '2a. El cajero no tiene turno abierto: el sistema le pide abrirlo antes de preparar (CU-20).',
            '3a. Sin conexión: el sistema avisa que no pudo descargar y conserva el paquete anterior.',
            '6a. Una foto no se descarga: la prenda se muestra con un ícono y se puede reservar igual.',
            '7a. Pasaron más de 12 horas: al consultar, el sistema avisa que los datos pueden estar '
            'desactualizados, pero no bloquea.',
        ],
        post='El dispositivo tiene en local lo necesario para vender o reservar sin conexión, y sobrevive a cerrar '
             'la aplicación.',
        rastreo='RF-10, RF-11, RF-12, RF-13, RF-17 · RN-05',
    ),
    'CU-14': dict(
        descripcion='Permite al cajero vender de contado en la PWA cuando no hay conexión, con los datos guardados '
                    'en el navegador. La venta queda en la cola hasta que el servidor la confirma.',
        actores='Cajero', iniciador='Cajero',
        pre='El dispositivo está preparado (CU-13), el turno de caja está abierto y no hay conexión con el '
            'servidor.',
        flujo=[
            '1. El sistema detecta que no hay conexión y muestra la caja en modo sin conexión.',
            '2. El cajero busca las prendas en los datos guardados y las agrega con su cantidad.',
            '3. El sistema calcula el total con el precio y el descuento guardados.',
            '4. El cajero cobra en efectivo o con QR (incluye CU-16).',
            '5. El sistema genera el identificador único de la operación y guarda la venta en el navegador con '
            'estado «guardada»: su turno, sus líneas, el pago y la hora.',
            '6. El sistema descuenta lo vendido de la existencia guardada y muestra el comprobante provisional.',
        ],
        alternos=[
            '4a. Tarjeta: no está disponible sin conexión; el cajero cobra en efectivo o con QR.',
            '5a. No se pudo guardar en el navegador: el sistema avisa y la venta no se registra.',
        ],
        post='La venta queda en la cola del navegador, pendiente de sincronizar (CU-17). No es definitiva hasta que '
             'el servidor la confirma.',
        rastreo='RF-12, RF-15, RF-16, RF-19 · RN-05, RN-07',
    ),
    'CU-15': dict(
        descripcion='Permite al cliente reservar sin conexión, desde la aplicación móvil, prendas para probárselas '
                    'en una sucursal, eligiéndolas en una vitrina con fotos guardada en el teléfono.',
        actores='Cliente', iniciador='Cliente',
        pre='El cliente preparó el teléfono (CU-13) con su sesión iniciada.',
        flujo=[
            '1. El cliente abre «Nueva reserva sin conexión».',
            '2. El cliente elige la sucursal donde se las va a probar.',
            '3. El cliente elige el día (hasta tres días adelante), la hora de llegada y la duración de la franja.',
            '4. El sistema muestra la vitrina: los productos con existencia en esa sucursal, con su foto, su '
            'categoría y su precio, y permite filtrar por categoría o buscar por nombre.',
            '5. El cliente toca un producto y elige la talla, el color y la cantidad.',
            '6. El cliente guarda la reserva.',
            '7. El sistema verifica la hora contra el horario de la sucursal, genera el identificador único y guarda '
            'la reserva en SQLite con estado «guardada».',
            '8. El sistema descuenta lo apartado de la existencia guardada y muestra la reserva en la cola.',
        ],
        alternos=[
            '4a. Los datos tienen más de 12 horas: el sistema avisa que pueden estar desactualizados y deja seguir.',
            '5a. Se alcanzó un máximo (10 prendas distintas, 10 unidades de una o la existencia conocida): el '
            'sistema no deja agregar más.',
            '7a. La hora ya pasó o la franja cae fuera del horario de la sucursal: el sistema lo avisa y vuelve al '
            'paso 3.',
        ],
        post='La reserva queda en el teléfono, pendiente de sincronizar (CU-17). La confirma el servidor con las '
             'mismas reglas que la reserva en línea.',
        rastreo='RF-12, RF-14, RF-16, RF-17, RF-19 · RN-05, RN-06, RN-07',
    ),
    'CU-16': dict(
        descripcion='Permite al cajero cobrar una venta sin conexión, en efectivo o con QR anotando la referencia. '
                    'El cobro no confirma la venta: la confirma el servidor al sincronizar.',
        actores='Cajero', iniciador='Cajero',
        pre='Se está registrando una venta sin conexión (CU-14).',
        flujo=[
            '1. El sistema muestra el total y los métodos que funcionan sin conexión: efectivo y QR.',
            '2. El cajero elige el método.',
            '3. En efectivo, el cajero ingresa lo recibido y el sistema calcula el vuelto.',
            '4. El sistema guarda el pago con la venta: el método, el monto que se quedó la tienda y la referencia.',
        ],
        alternos=[
            '2a. QR: el cajero anota la referencia que muestra el banco del cliente; sin referencia, el sistema no '
            'deja continuar.',
            '3a. Lo recibido no alcanza: el sistema no deja cobrar.',
        ],
        post='El pago viaja con la operación. Si al sincronizar la venta se rechaza, queda marcada para devolver el '
             'dinero (CU-19).',
        rastreo='RF-54, RF-55 · RN-05, RN-06',
    ),
    'CU-17': dict(
        descripcion='Envía al servidor las operaciones guardadas sin conexión. El servidor confirma o rechaza cada una '
                    'contra el inventario central, sin aplicar ninguna dos veces.',
        actores='Sistema; cajero o cliente', iniciador='El sistema, al volver la conexión, o el usuario con '
                                                         '«Sincronizar ahora»',
        pre='Hay operaciones guardadas, esperando al servidor o en conflicto, y hay conexión.',
        flujo=[
            '1. El dispositivo detecta que volvió la conexión, o el usuario pide sincronizar.',
            '2. El dispositivo marca las operaciones como «esperando al servidor» y las envía en lotes de hasta 50, '
            'cada una con su identificador único.',
            '3. El servidor verifica que el identificador de cada operación no esté ya registrado.',
            '4. El servidor aplica cada operación en su propia transacción: bloquea la existencia de cada prenda y, '
            'si alcanza, registra la venta en el turno del cajero o la reserva, con las mismas reglas que en línea '
            '(horario, probadores y existencia).',
            '5. El servidor guarda la operación con su resultado y la confirma por separado de las demás.',
            '6. El servidor devuelve el resultado de cada una: confirmada, con el código de la venta o de la '
            'reserva, o rechazada, con su motivo.',
            '7. El dispositivo actualiza el estado de cada operación.',
        ],
        alternos=[
            '2a. El servidor no responde: las operaciones siguen esperando y se reintenta cada minuto; nada se '
            'pierde.',
            '3a. El identificador ya existe: el servidor devuelve el resultado que registró la primera vez y no la '
            'aplica de nuevo.',
            '4a. Ya no alcanza la existencia: gana la operación que llegó primero al servidor y esta queda rechazada '
            'con el motivo; si se había cobrado, queda para devolver el dinero (CU-19).',
            '4b. Una venta en un turno ajeno o una reserva fuera de horario: se rechaza con el motivo.',
            '6a. El servidor no pudo decidir una operación porque el pedido llegó mal formado: queda «en conflicto», '
            'a la vista y sin borrarse.',
        ],
        post='Cada operación tiene su resultado. Las confirmadas ya movieron el inventario central; una rechazada no '
             'deja nada a medias y no deshace a las demás del lote.',
        rastreo='RF-18, RF-19, RF-20, RF-21, RF-22, RF-23 · RN-06, RN-07',
    ),
    'CU-18': dict(
        descripcion='Permite al cajero y al cliente ver lo que registraron sin conexión, con el estado de cada '
                    'operación y el motivo de las rechazadas.',
        actores='Cajero, cliente', iniciador='Cajero o cliente',
        pre='El usuario inició sesión en el dispositivo.',
        flujo=[
            '1. El usuario abre la pantalla «Sin conexión».',
            '2. El sistema lee la cola guardada en el dispositivo, que sobrevive a cerrar la aplicación.',
            '3. El sistema muestra cada operación con su resumen, su fecha, su estado (guardada, esperando al '
            'servidor, confirmada, rechazada o en conflicto), los intentos y, si corresponde, el motivo del '
            'rechazo.',
            '4. El sistema muestra cuántas siguen pendientes y si hay conexión.',
        ],
        alternos=[
            '3a. Sincronizar ahora: el usuario pide enviar las pendientes (incluye CU-17).',
            '3b. Limpiar historial: el usuario quita de la lista las que el servidor ya decidió; las pendientes no se '
            'quitan nunca.',
        ],
        post='El usuario sabe qué llegó al servidor y qué no. La cola no cambia, salvo por la limpieza de las ya '
             'decididas.',
        rastreo='RF-16, RF-17, RF-20, RF-23',
    ),
    'CU-19': dict(
        descripcion='Permite al encargado de sucursal ver las operaciones sin conexión que el servidor rechazó '
                    'después de cobrarse, y registrar la devolución del dinero al cliente.',
        actores='Encargado de sucursal', iniciador='Encargado de sucursal',
        pre='El encargado inició sesión con conexión.',
        flujo=[
            '1. El encargado abre «Operaciones sin conexión».',
            '2. El sistema muestra las operaciones de su sucursal por devolver: quién la registró, cuándo, el '
            'resumen, el monto cobrado, el método y el motivo del rechazo.',
            '3. El encargado elige una y registra la devolución: el método (por omisión, el mismo con que se '
            'cobró), la referencia si es QR y una observación.',
            '4. El sistema verifica que la operación esté rechazada, cobrada y todavía sin devolver.',
            '5. El sistema registra la devolución con quién, cuándo y cómo, y la quita de la lista por devolver.',
        ],
        alternos=[
            '2a. Ver todas: el encargado ve también las confirmadas y las ya devueltas.',
            '3a. QR sin referencia: el sistema la pide y no deja continuar.',
            '4a. La operación se confirmó, no se cobró o ya se devolvió: el sistema lo informa y no registra nada.',
        ],
        post='La devolución queda registrada una sola vez. Si fue en efectivo, el arqueo del turno donde se cobró '
             'deja de contar ese dinero (CU-20).',
        rastreo='RF-22, RF-55 · RN-06, RN-21',
    ),
    'CU-20': dict(
        descripcion='Extiende la apertura y el cierre de caja del primer parcial para que el arqueo cuente lo vendido '
                    'sin conexión y el turno no se cierre con ventas sin subir al servidor.',
        actores='Cajero', iniciador='Cajero',
        pre='El cajero inició sesión con conexión y hay una caja libre en su sucursal.',
        flujo=[
            '1. El cajero elige una caja libre e ingresa el monto de apertura.',
            '2. El sistema abre el turno. Con él se puede preparar el dispositivo (CU-13) y vender, con o sin '
            'conexión.',
            '3. Al terminar, el cajero abre el cierre del turno.',
            '4. El sistema muestra el arqueo: apertura, efectivo cobrado, devoluciones, cambios y lo por devolver de '
            'las ventas sin conexión rechazadas; el monto esperado, y cuántas ventas fueron sin conexión.',
            '5. El cajero cuenta el cajón e ingresa el monto contado.',
            '6. El sistema muestra la diferencia antes de confirmar.',
            '7. El cajero confirma y el sistema verifica que no queden ventas sin conexión de ese turno sin subir.',
            '8. El sistema guarda el monto esperado y el contado, cierra el turno y muestra el arqueo final.',
        ],
        alternos=[
            '1a. Todas las cajas están ocupadas: el sistema las muestra apagadas y no deja abrir.',
            '7a. Quedan ventas de este turno sin subir: el sistema intenta sincronizarlas (CU-17). Si no suben, no '
            'cierra; si suben, el monto esperado cambió y lo muestra para que el cajero vuelva a confirmar.',
            '8a. La caja no cuadra: el sistema registra igual el faltante o el sobrante, porque el arqueo es '
            'justamente esa diferencia.',
        ],
        post='El turno queda cerrado con el monto esperado y el contado, incluidas las ventas sin conexión de ese '
             'turno.',
        rastreo='RF-15, RF-21 · RN-06',
    ),
}

inicio26 = ed.parrafo('2.6. Especificación de casos de uso')
titulo12 = ed.parrafo('CU-12 — Personalizar la tienda de la empresa', desde=inicio26)
modelo_tabla = ed.tabla_despues(titulo12)
siguientes = ed.parrafo('PARA SIGUIENTES PRESENTACIONES', desde=inicio26, exacto=True)
vacio = siguientes.getprevious()

ancla = siguientes.getprevious()
for cu, f in FICHAS.items():
    titulo = ed.parrafo(cu + ' —', desde=siguientes)
    titulo.getparent().remove(titulo)
    tbl = copy.deepcopy(modelo_tabla)
    filas = tbl.findall(qn('w:tr'))
    valores = [
        [T(titulo).strip()], [f['descripcion']], [f['actores']], [f['iniciador']], [f['pre']],
        f['flujo'], f['alternos'], [f['post']], [f['rastreo']],
    ]
    for tr, lineas in zip(filas, valores):
        celda_lineas(celdas(tr)[1], lineas)
    ancla = ed.insertar_despues(ancla, [titulo, tbl, copy.deepcopy(vacio)])

# Los tres casos de uso nuevos, al final de la lista de las siguientes presentaciones
ultimo = ed.parrafo('CU-40 — Gestionar copias de seguridad de la empresa', desde=siguientes)
ed.insertar_despues(ultimo, [ed.copiar_parrafo(ultimo, f'{cu} — {nombre}') for cu, nombre, *_ in NUEVOS])

ed.cerrar(DOC)
print('ok')
