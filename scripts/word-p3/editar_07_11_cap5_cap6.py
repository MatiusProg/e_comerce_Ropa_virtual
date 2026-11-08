# Capítulos V (pruebas) y VI (conclusiones y recomendaciones) para la 3ra presentación, según los tips
# del auxiliar (06/11): 5.1 plan con pipeline y puntos críticos; 5.2 funcionales (un CU o una tabla);
# 5.3 integración (2+ módulos, verificada en la base); 5.4 una tabla por error; 5.5 resultados con
# capturas; 5.6 casos de prueba detallados; 6.1 una conclusión por objetivo específico; 6.2 recomendaciones
# estructurales y de uso. Además agrega la RN-23 al 2.4 y actualiza el objetivo de los aportes propios.
# Uso: python editar_07_11_cap5_cap6.py <documento.docx>
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'word-p2'))
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx_util import Editor

DOC = sys.argv[1]
ed = Editor(docx.Document(DOC))
ANCHO = 9782
VINETA = ed.parrafo('Aislamiento: un usuario de la empresa A')  # modelo de viñeta del 5.1


def p(txt, con_siguiente=False):
    return ed.nuevo_parrafo(txt, con_siguiente=con_siguiente)


def v(txt):
    return ed.copiar_parrafo(VINETA, txt)


def sub(txt):
    """Subtítulo en negrita dentro de una sección (sin estilo de título, para no tocar el índice)."""
    return ed.nuevo_parrafo(f'**{txt}**', con_siguiente=True)


def ficha(codigo, titulo, filas):
    """Tabla vertical: una fila por campo (el formato que pidió el auxiliar para el 5.4 y el 5.6)."""
    t = ed.tabla([codigo, titulo], filas, [2300, ANCHO - 2300])
    filas_xml = t.findall(qn('w:tr'))
    for tr in filas_xml[:-1]:  # que la ficha no se parta entre dos páginas
        for par in tr.iter(qn('w:p')):
            ppr = par.find(qn('w:pPr'))
            if ppr is None:
                ppr = OxmlElement('w:pPr'); par.insert(0, ppr)
            estilo = ppr.find(qn('w:pStyle'))  # keepNext va justo después del estilo (orden del esquema)
            ppr.insert(1 if estilo is not None else 0, OxmlElement('w:keepNext'))
    return [t, p('')]


def llenar(titulo, elementos):
    """Reemplaza el párrafo «[Pendiente]» que sigue al título por los elementos dados."""
    h = ed.parrafo(titulo, exacto=True)
    pendiente = h.getnext()
    assert ed.texto(pendiente).startswith('[Pendiente]'), (titulo, ed.texto(pendiente))
    ancla = ed.insertar_despues(pendiente, elementos)
    pendiente.getparent().remove(pendiente)
    return ancla


# =====================================================================
# 2.4 RN-23
rn = ed.tabla_despues(ed.parrafo('2.4. Reglas de negocio', exacto=True))
fila = ed.agregar_fila(rn, ['RN-23', 'Lo que el cliente se llevó en un cambio de prenda no se devuelve por dinero: '
                            'solo se puede volver a cambiar, dentro de la ventana de devolución.'])
ed.recebrar(rn)

# =====================================================================
# 1.3.2 objetivo de lo pedido en clase y los aportes propios (los traspasos los pidió la docente)
obj = ed.parrafo('Implementar lo pedido por la docente en clase')
ed.poner_texto(obj, 'Implementar lo pedido por la docente en clase (devoluciones vía web, inventario por sucursal y '
               'traspasos entre sucursales, pago sin conexión, ofertas con precios mayoristas y cambios de prenda con '
               'diferencia de precio) y los aportes propios del grupo: un probador virtual que distinga tallas, el '
               'aviso al cliente cuando llega la talla que estaba agotada y la detección de anomalías en la caja y '
               'en las devoluciones con aprendizaje automático.')

# =====================================================================
# 5.1 Plan de pruebas (se conserva la introducción y las cuatro viñetas; se agrega lo demás después)
ultima = ed.parrafo('Conflictos de inventario: una venta offline sin existencia')
intro = ed.parrafo('Las pruebas siguen la trazabilidad de ICONIX')
ed.poner_texto(intro, 'Las pruebas siguen la trazabilidad de ICONIX: cada requisito crítico tiene al menos una '
               'prueba automatizada que lo verifica. Se parte de la batería del primer parcial (más de 800 pruebas '
               'con pytest sobre una base PostgreSQL local) y se agregan cuatro familias nuevas:')
plan = [
    p('Además de esas cuatro familias, cada caso de uso nuevo (CU-01 a CU-43) y cada aporte propio trae su propio '
      'archivo de pruebas. El plan responde a tres preguntas:'),
    v('**Qué se prueba.** Las reglas de negocio del 2.4, los límites y funciones de cada plan, los permisos de cada '
      'rol, el aislamiento entre empresas, la sincronización sin conexión, el dinero (caja, arqueo, pagos y '
      'reembolsos), la inteligencia artificial (que nunca escriba SQL) y la analítica.'),
    v('**Cómo se prueba.** Las pruebas funcionales verifican un caso de uso a la vez, con las mismas peticiones que '
      'envía el formulario de la web o de la aplicación. Las de integración recorren dos o más módulos y comprueban '
      'en la base de datos lo que quedó escrito. Los flujos que dependen de servicios externos (Stripe, Web Push, '
      'Firebase y el teléfono) se prueban a mano sobre el sistema desplegado.'),
    v('**Con qué herramientas.** pytest y el TestClient de FastAPI contra una base PostgreSQL 16 local, separada de '
      'producción (variable TEST_DATABASE_URL) y con Row Level Security activo, igual que en la nube; Alembic para '
      'subir y bajar las migraciones en una base vacía; el compilador de Angular (ng build) y flutter analyze para '
      'la web y el móvil; y el navegador, el panel de Stripe en modo de prueba y un teléfono Android para las '
      'pruebas manuales.'),
    sub('Pipeline del proceso de pruebas'),
    p('Cada cambio pasa por los mismos siete pasos antes de llegar a producción:'),
    ed.tabla(['Paso', 'Qué se hace', 'Criterio para avanzar'], [
        ['1. Pruebas del CU', 'Se escriben y corren las pruebas del caso de uso en su rama', 'Todas aprobadas'],
        ['2. Módulos vecinos', 'Se corren las pruebas de los módulos que el cambio toca (por ejemplo, '
         'inventario, caja y devoluciones)', 'Todas aprobadas'],
        ['3. Migraciones', 'La migración nueva se sube, se baja y se vuelve a subir en una base vacía',
         'Sin errores y una sola cabeza en Alembic'],
        ['4. Compilación', 'ng build de la web y flutter analyze del móvil', 'Sin errores'],
        ['5. Suite completa', 'Antes de cada merge se corre la batería entera sobre la rama ya combinada con '
         'las demás', '0 fallas'],
        ['6. Despliegue', 'Al mergear, Railway construye, migra y arranca el backend', 'Migraciones aplicadas y '
         'servicio activo'],
        ['7. Prueba manual', 'Los flujos con servicios externos se recorren en el sistema desplegado',
         'El resultado esperado del caso de prueba (5.6)'],
    ], [2200, 4882, 2700]),
    p(''),
    sub('Puntos críticos y por qué'),
    ed.tabla(['Punto crítico', 'Por qué se prueba con prioridad'], [
        ['Aislamiento entre empresas', 'Un error expone los datos de una empresa a otra; es la promesa central de '
         'un SaaS multitenant.'],
        ['Límites y funciones del plan', 'Es lo que diferencia lo que paga cada empresa; si no se verifica en el '
         'backend, cualquiera usa el plan superior.'],
        ['Sincronización sin conexión', 'Una operación enviada dos veces no puede vender dos veces; una que falla no '
         'puede perderse.'],
        ['Inventario', 'Ninguna operación (venta offline, traspaso, devolución) puede dejar existencias negativas.'],
        ['Dinero', 'Caja, arqueo, pagos y reembolsos: un error se traduce en plata de menos o de más.'],
        ['Inteligencia artificial', 'El modelo nunca escribe SQL: su respuesta se valida contra una lista blanca '
         'antes de ejecutarse.'],
        ['Permisos por rol', 'Cada rol ve y hace solo lo suyo, también con los roles propios que crea la empresa.'],
    ], [3000, ANCHO - 3000]),
    p(''),
]
ed.insertar_despues(ultima, plan)

# =====================================================================
# 5.2 Pruebas funcionales: un caso de uso (o una tabla) a la vez
FUNC = [
    ['CU-01', 'Registrar, editar, dar de baja y reactivar empresas; slug y plan válidos', '13'],
    ['CU-02', 'Crear, editar, desactivar y reactivar planes; empresas por encima de un límite', '15'],
    ['CU-03', 'Asignar, cambiar, renovar, suspender y vencer suscripciones', '15'],
    ['CU-04', 'Consultar el plan y el consumo de la empresa', '13'],
    ['CU-05', 'Rechazar lo que excede un límite o una función que el plan no incluye', '24'],
    ['CU-06', 'Iniciar sesión eligiendo la empresa; empresa suspendida o dada de baja', '20'],
    ['CU-07', 'Cuenta única del cliente en varias tiendas', '10'],
    ['CU-08', 'Usuarios de la empresa y sus roles', '19'],
    ['CU-10', 'Empleados de la empresa', '4'],
    ['CU-11', 'Contratar un plan desde la web', '14'],
    ['CU-12', 'Personalizar la tienda (logo, colores)', '17'],
    ['CU-13 a CU-17', 'Preparar el dispositivo, vender, reservar y pagar sin conexión, y sincronizar', '18'],
    ['CU-20', 'Abrir y cerrar caja con ventas offline', '5'],
    ['CU-21', 'Inventario de la sucursal, también contado sin conexión', '18'],
    ['CU-22 y CU-23', 'Cambio o devolución en caja y ventana de devolución', '11'],
    ['CU-24', 'Solicitar cambio o devolución por la web', '14'],
    ['CU-25', 'Atender la solicitud y devolver el dinero por la pasarela', '11'],
    ['CU-26, CU-39 y CU-40', 'Correo según el plan, exportación de datos y copias de seguridad', '27'],
    ['CU-27', 'Reporte con IA por texto o voz, con gráfico, PDF y Excel', '26'],
    ['CU-29 y CU-30', 'Entrenar la demanda semanal y los segmentos de clientes; dashboard', '12'],
    ['CU-31 y CU-32', 'Ofertas, precios mayoristas y ofertas de fuera de temporada', '23'],
    ['CU-33 a CU-35', 'Solicitar, atender y sugerir traspasos', '19'],
    ['CU-36 a CU-38', 'Preparar la prenda, probarla con la talla real y la foto realista', '26'],
    ['CU-41', 'Roles y permisos propios de la empresa', '19'],
    ['CU-42 y CU-43', 'Avisos push y devolución automática del pago rechazado', '28'],
    ['Aporte propio', '«Avísame cuando llegue mi talla»', '12'],
    ['Aporte propio', 'Anomalías en caja y devoluciones', '10'],
]
llenar('5.2. Pruebas funcionales', [
    p('Verifican que cada caso de uso haga lo que dice su especificación, uno a la vez y sobre las tablas que le '
      'pertenecen. Cada prueba envía las mismas peticiones que el formulario de la web o de la aplicación (crear, '
      'editar, listar, dar de baja) y revisa la respuesta: los datos correctos, el mensaje de error cuando algo '
      'falta y el rechazo cuando el rol o el plan no lo permiten. El CU-28 se verifica con la batería de reportes '
      'del primer parcial, ampliada con el reporte de devoluciones.'),
    ed.tabla(['Caso de uso', 'Qué se verifica', 'Pruebas'], FUNC + [
        ['Total', 'Pruebas funcionales de los casos de uso del segundo parcial y de la 3ra presentación', '443'],
    ], [2300, 6282, 1200]),
    p(''),
    p('Además de las automatizadas, los flujos principales se recorren llenando los formularios en la web '
      'desplegada; sus capturas están en el 5.5.'),
])

# =====================================================================
# 5.3 Pruebas de integración: 2 o más módulos, verificadas en la base
INTEG = [
    ['Venta offline → sincronización → inventario → caja', 'La venta se confirma una sola vez aunque se reenvíe, '
     'descuenta la existencia y queda en el turno de caja', 'venta_offline, existencia, turno_caja'],
    ['Venta offline sin stock → rechazo → devolución del pago', 'Si otra venta llegó primero, la offline queda '
     'rechazada, no deja existencia negativa y el pago se devuelve una sola vez', 'operacion_offline, pago, devolucion'],
    ['Devolución web → pasarela → nota → inventario', 'Al recibir la prenda se pide el reembolso a Stripe, nace la '
     'nota ABIERTA y la prenda vuelve al stock', 'solicitud_devolucion, devolucion, movimiento_inventario'],
    ['Cambio en caja → diferencia de precio → arqueo', 'La diferencia se cobra o se devuelve y el arqueo del turno '
     'la refleja', 'devolucion, venta, pago, turno_caja'],
    ['Traspaso → inventario de dos sucursales', 'Al enviar sale del origen, al recibir entra al destino; dos '
     'recepciones simultáneas no duplican', 'traspaso, existencia, movimiento_inventario'],
    ['Inventario → aviso de talla → notificación → push', 'La talla que pasa de 0 a más de 0 avisa una sola vez, '
     'en la misma transacción del movimiento', 'existencia, aviso_talla, notificacion'],
    ['Plan → verificador → cualquier módulo', 'Bajar de plan apaga la función en todos los módulos sin borrar '
     'datos; el cupo se consume solo si la operación sale bien', 'suscripcion, plan, consumo'],
    ['Empresa A ↔ empresa B (todos los módulos)', 'Ninguna tabla del tenant queda sin Row Level Security y ningún '
     'endpoint deja ver o tocar datos ajenos', 'todas las tablas del tenant'],
    ['Copia de seguridad → restauración', 'La restauración reemplaza los datos de la empresa sin mezclar y sin '
     'perder relaciones (por ejemplo, las categorías de cliente)', 'respaldo y todas las tablas de la empresa'],
    ['Reporte con IA → validación → consulta', 'El pedido se traduce a una especificación, se valida contra la '
     'lista blanca y se ejecuta solo sobre los datos de la empresa', 'venta, detalle_venta, existencia'],
    ['Tareas automáticas → varias empresas', 'Una sola vuelta cada 15 minutos aunque haya dos procesos; una tarea '
     'que falla no corta las demás', 'tarea_automatica, respaldo, notificacion'],
]
llenar('5.3. Pruebas de integración', [
    p('Verifican que dos o más módulos se comuniquen bien: la operación entra por un módulo y la prueba revisa, '
      'consultando la base de datos, lo que quedó escrito en las tablas de los demás. Se hacen con pytest y el '
      'TestClient de FastAPI contra PostgreSQL con Row Level Security, y cada prueba arranca con la base limpia.'),
    ed.tabla(['Recorrido', 'Qué se comprueba en la base', 'Tablas verificadas'], INTEG, [2900, 4382, 2500]),
    p(''),
    p('A estas se suman las pruebas de las migraciones (subir, bajar y volver a subir en una base vacía) y la '
      'integración de la PWA y de Flutter con el backend, que se recorre a mano: el móvil se prepara, se pone en modo '
      'avión, registra operaciones y, al volver la conexión, las sincroniza.'),
])

# =====================================================================
# 5.4 Corrección de errores: una tabla por error
ERRORES = [
    ('E-01', 'Tareas automáticas', 'Las tareas de cada vuelta (copias, ofertas, correos, push) corrían dos veces '
     'seguidas en producción.', 'Media', 'El backend corre con dos procesos; el segundo tomaba el candado un segundo '
     'después de que el primero lo soltaba.', 'Se guarda la marca de la última vuelta (migración 0035) y el segundo '
     'proceso no repite una vuelta reciente.', 'Prueba «el segundo worker no repite la vuelta» y logs de Railway con '
     'una sola vuelta cada 15 minutos.'),
    ('E-02', 'Exportación de datos', 'Un texto que empieza con «=», «+», «-» o «@» se ejecutaba como fórmula al '
     'abrir el Excel exportado.', 'Alta', 'Los textos se escribían tal cual en la celda.', 'Se escapan esos textos '
     'y se excluyen de la exportación las suscripciones push y la carga de la pasarela.', 'Pruebas de exportación '
     '(CU-39) con textos maliciosos.'),
    ('E-03', 'Avisos push', 'Un usuario podía registrar como suyo el dispositivo de otra persona y recibir sus '
     'avisos.', 'Alta', 'El alta del dispositivo reasignaba la dirección sin comprobar a quién pertenecía.',
     'Web Push solo se reasigna con las mismas claves (si no, 409) y se valida el servidor de destino con una lista '
     'blanca.', 'Pruebas de CU-42 sobre dispositivos ajenos.'),
    ('E-04', 'Roles propios', 'Un rol propio que no se encontraba dejaba pasar la petición, y cambiar el rol base '
     'no le quitaba el rol propio.', 'Alta', 'La verificación tomaba la ausencia del rol como «sin restricción».',
     'Si el rol propio no se encuentra, se responde 403; al cambiar el rol base se limpia el rol propio.',
     'Pruebas «un rol propio que no se encuentra cierra en vez de abrir» y «cambiar de rol base le quita el rol '
     'propio».'),
    ('E-05', 'Copias de seguridad', 'Las copias se cifraban con la misma clave que firma las sesiones, y restaurar '
     'borraba las categorías de los clientes.', 'Alta', 'Clave compartida; el borrado en cascada alcanzaba la tabla '
     'cliente_categoria.', 'Clave propia (RESPALDO_SECRET, con la anterior como respaldo) y la restauración '
     'repone esa relación.', 'Pruebas de CU-40 de copia y restauración.'),
    ('E-06', 'Traspasos', 'Un traspaso enviado a una sucursal dada de baja quedaba trabado, y dos recepciones '
     'simultáneas daban error 500.', 'Media', 'No había salida para un destino inactivo y la recepción no bloqueaba '
     'la fila.', 'Acción DEVOLVER para el destino dado de baja y bloqueo de la fila al recibir.', 'Pruebas de '
     'CU-34 de destino dado de baja y de recepción simultánea.'),
    ('E-07', 'Operación sin conexión', 'Una reserva offline podía traer un pago, y lo por devolver de una venta '
     'rechazada podía superar su total.', 'Alta', 'El contrato de sincronización no validaba esos dos casos.',
     'Se rechaza la reserva con pago y lo por devolver se acota al total de la venta.', 'Pruebas «una reserva '
     'offline no puede traer pago» y «lo por devolver no supera su total».'),
    ('E-08', 'Devoluciones web', 'El plazo para devolver un pedido web se contaba desde la compra y no desde la '
     'entrega.', 'Media', 'La ventana usaba la fecha de la venta.', 'El plazo corre desde que el encargado marca '
     'la entrega (venta.entregado_en).', 'Pruebas de CU-24 y CU-25.'),
    ('E-09', 'Cambio de prenda', 'Lo que el cliente se llevó en un cambio se podía devolver por dinero.', 'Media',
     'No había regla para la prenda que salió de un cambio.', 'Nueva regla RN-23: solo se vuelve a cambiar.',
     'Pruebas de CU-22.'),
    ('E-10', 'Ofertas de fuera de temporada', 'Apagar la regla no cerraba sus ofertas, y la tarea reabría una '
     'oferta que el administrador había cerrado.', 'Media', 'La oferta no guardaba quién la cerró.', 'Se guarda '
     'si la cerró la regla (migración 0034); apagar la regla cierra las suyas y no se reabren las del administrador.',
     'Pruebas de CU-32.'),
    ('E-11', 'Conformidad del cliente', 'Un doble clic enviaba dos veces la conformidad de la devolución.', 'Baja',
     'El botón seguía activo mientras se enviaba.', 'El botón se deshabilita y muestra el estado de carga.',
     'Prueba manual en la web.'),
    ('E-12', 'Reporte con IA (CU-27)', 'Sin el modelo de IA, la frase «compará las ventas de las sucursales» no se '
     'reconocía.', 'Baja', 'La expresión regular perdió el límite de palabra al escribirse en una cadena normal.',
     'Se escribió como cadena cruda (raw string).', 'Prueba de las frases del enunciado con el intérprete por '
     'reglas.'),
]
cuarto = [p('Se anotan los errores encontrados en la sesión de pruebas y en la auditoría previa a la 3ra '
            'presentación, con su corrección. Cada corrección quedó cubierta por una prueba automatizada, de modo '
            'que el error no puede volver sin que la suite lo detecte.')]
for cod, func, desc, grav, causa, corr, verif in ERRORES:
    cuarto += ficha(cod, func, [['Descripción', desc], ['Gravedad', grav], ['Causa', causa],
                                ['Corrección aplicada', corr], ['Verificación', verif]])
llenar('5.4. Corrección de errores', cuarto)

# =====================================================================
# 5.5 Resultados de las pruebas
llenar('5.5. Resultados de las pruebas', [
    p('La batería completa se corrió el 07/11/2026 sobre la rama con todos los cambios de la 3ra presentación ya '
      'combinados:'),
    ed.tabla(['Prueba', 'Resultado', 'Comentario'], [
        ['Suite completa (pytest)', '1303 aprobadas, 0 fallas', '77 archivos de prueba; 33 minutos contra '
         'PostgreSQL local con Row Level Security'],
        ['Pruebas funcionales', '443 aprobadas', 'Una o más por cada caso de uso del segundo parcial y de la 3ra '
         'presentación (5.2)'],
        ['Aislamiento y planes', 'Aprobadas', 'Ninguna tabla del tenant sin Row Level Security; cada límite se '
         'rechaza al excederse'],
        ['Regresión del primer parcial', 'Aprobadas', 'La batería del primer parcial sigue pasando con el '
         'multitenant encima'],
        ['Migraciones 0029 a 0043', 'Suben y bajan', 'En una base vacía, sin errores y con una sola cabeza'],
        ['Web (ng build)', 'Compila', 'Sin errores de tipos'],
        ['Móvil (flutter analyze)', 'Sin problemas', ''],
        ['Despliegue en Railway', 'Activo', 'Migraciones aplicadas hasta la 0043 y tareas automáticas cada 15 '
         'minutos'],
        ['Pago con Stripe (modo de prueba)', 'Aprobado', 'Pago con la tarjeta de prueba confirmado por el webhook'],
        ['Web Push en producción', 'Aprobado', 'Llegó la notificación «Pago confirmado» al navegador del cliente'],
        ['Reembolso con Stripe', '[Pendiente]', '[Completar tras la prueba manual]'],
        ['Push en el teléfono (FCM)', '[Pendiente]', '[Completar tras la prueba manual]'],
        ['Inventario offline en el teléfono (CU-21)', '[Pendiente]', '[Completar tras la prueba manual]'],
    ], [3100, 2300, 4382]),
    p(''),
    p('[Capturas: resultado de la suite completa; pago y reembolso en el panel de Stripe; notificación push en el '
      'navegador y en el teléfono; conteo offline y su movimiento en el inventario.]'),
])

# =====================================================================
# 5.6 Casos de prueba
CASOS = [
    ('CP-01', 'Aislamiento entre empresas', 'Backend con PostgreSQL y Row Level Security; dos empresas con sus '
     'administradores.', 'Cada administrador inicia sesión en su empresa.', '1. El administrador A lista productos, '
     'ventas y clientes. 2. Intenta ver, editar y borrar un producto de B por su id. 3. Se revisa en la base qué '
     'filas ve el rol violet_app con la empresa A.', 'A solo ve lo suyo; los ids de B responden 404 y en la base no '
     'aparece ninguna fila de B.', 'Aprobado'),
    ('CP-02', 'Límite del plan', 'Empresa con plan Básico.', 'La empresa ya tiene el máximo de sucursales de su '
     'plan.', '1. El administrador intenta crear otra sucursal. 2. Intenta usar el reporte con IA.', 'Se rechazan '
     'las dos con el motivo y la invitación a mejorar el plan; no se crea nada.', 'Aprobado'),
    ('CP-03', 'Venta offline sin duplicados', 'Cajero con turno abierto; PWA o móvil preparado.', 'Sin conexión.',
     '1. Registra una venta offline. 2. Vuelve la conexión y sincroniza. 3. Se reenvía la misma operación.',
     'Una sola venta en la base, la existencia descontada una vez y la venta dentro del turno.', 'Aprobado'),
    ('CP-04', 'Conflicto de inventario', 'Una prenda con una sola unidad.', 'Un dispositivo vende la unidad sin '
     'conexión mientras otro la vende en línea.', '1. Se confirma la venta en línea. 2. Se sincroniza la offline.',
     'La offline queda rechazada con su motivo, la existencia no queda negativa y el pago se devuelve una sola '
     'vez.', 'Aprobado'),
    ('CP-05', 'Devolución web con reembolso', 'Web desplegada; Stripe en modo de prueba.', 'Pedido pagado con la '
     'tarjeta 4242 4242 4242 4242 y marcado como entregado.', '1. El cliente pide la devolución. 2. El encargado la '
     'aprueba y recibe la prenda. 3. El cliente da su conformidad.', 'El pago figura como reembolsado en Stripe, la '
     'nota queda CERRADA y la prenda vuelve al stock.', '[Pendiente]'),
    ('CP-06', 'Reporte con IA por voz', 'Empresa con plan Profesional o Empresarial.', 'Hay ventas registradas.',
     '1. El administrador dicta «ventas de septiembre agrupadas por sucursal». 2. Exporta a PDF y Excel.', 'Muestra '
     'lo que entendió, la tabla, el gráfico y la lectura; los archivos traen los mismos datos.', 'Aprobado'),
    ('CP-07', 'Entrenar la analítica', 'Empresa con plan Empresarial.', 'Ventas de varias semanas y clientes con '
     'compras.', '1. El administrador entrena la demanda semanal. 2. Entrena los segmentos. 3. Abre el dashboard.',
     'Se guardan los modelos con sus métricas (MAE, R², silueta) y el dashboard muestra la predicción y los '
     'segmentos.', 'Aprobado'),
    ('CP-08', 'Probador con la talla real', 'Prenda preparada con sus medidas por talla.', 'El cliente tiene sus '
     'medidas cargadas.', '1. Se prueba la talla S y luego la L con una foto.', 'La prenda se dibuja a su tamaño '
     'real: la talla chica se ve ajustada y la grande holgada; se recomienda una talla.', 'Aprobado'),
    ('CP-09', 'Avísame cuando llegue mi talla', 'Talla sin stock en todas las sucursales.', 'Cliente con sesión '
     'iniciada.', '1. El cliente pide el aviso. 2. El encargado registra un ingreso de esa talla. 3. Registra otro '
     'ingreso.', 'Un solo aviso en la campanita (y por push y correo); el segundo ingreso no vuelve a avisar.',
     'Aprobado'),
    ('CP-10', 'Anomalías en la caja', 'Empresa con plan Empresarial y al menos 20 turnos cerrados.', 'Uno de los '
     'turnos tiene un descuadre de Bs 500.', '1. El administrador entrena el modelo de anomalías. 2. Abre la '
     'pestaña «Anomalías».', 'Ese turno sale entre los marcados, con una explicación que menciona el arqueo.',
     'Aprobado'),
]
sexto = [p('Cada caso describe la funcionalidad, el entorno, las condiciones y los pasos. Los resultados de los '
           'casos automatizados salen de la suite del 5.5; los que dependen de servicios externos se recorren a mano '
           'en el sistema desplegado.')]
for cod, func, ent, cond, pasos, esperado, obtenido in CASOS:
    sexto += ficha(cod, func, [['Entorno', ent], ['Condiciones', cond], ['Pasos', pasos],
                               ['Resultado esperado', esperado], ['Resultado obtenido', obtenido]])
llenar('5.6. Casos de prueba', sexto)

# =====================================================================
# 6.1 Conclusiones: una por objetivo específico (1.3.2)
CONCL = [
    ('Recolectar los requerimientos', 'Se recolectaron del enunciado, de las correcciones de la docente en clase y '
     'del funcionamiento del sistema del primer parcial, y quedaron en el 2.3 separados por su origen.'),
    ('Especificar los requisitos', 'Cada requisito funcional y no funcional quedó asociado a un caso de uso '
     '(CU-01 a CU-43), con su especificación en el 2.6.'),
    ('Modelo de dominio y robustez', 'Se elaboró el modelo de dominio con las entidades del multitenant y los '
     'diagramas de robustez de los casos de uso nuevos y de los modificados, en Enterprise Architect.'),
    ('Secuencia y clases', 'Los diagramas de secuencia y de clases se refinaron hasta el nivel de implementación, '
     'con la clase control y la bitácora visibles, como pidió la docente.'),
    ('Modelo de datos multitenant', 'Cada tabla del tenant lleva la empresa y Row Level Security con FORCE; la '
     'prueba que recorre todas las tablas confirma que ninguna queda sin política (CP-01).'),
    ('Contrato de sincronización', 'La PWA y Flutter usan el mismo contrato, con un identificador único y un estado '
     'por operación; reenviar una operación no la duplica (CP-03).'),
    ('Empresas, planes y límites', 'Se implementaron el registro de empresas, los tres planes y el verificador que '
     'controla límites, funciones y cupos en cada operación (CP-02).'),
    ('PWA', 'La aplicación Angular se instala como PWA, guarda en IndexedDB y vende y reserva sin conexión.'),
    ('SQLite en Flutter', 'La aplicación móvil registra ventas, reservas e inventario sin conexión en SQLite y los '
     'sincroniza al volver la red.'),
    ('Sincronización y conflictos', 'La sincronización reintenta sin duplicar y detecta los conflictos de '
     'inventario: la operación que llega tarde se rechaza y su pago se devuelve una sola vez (CP-04).'),
    ('Reportes con IA', 'Los reportes se piden por texto o por voz; Gemini arma una especificación que el backend '
     'valida contra una lista blanca y ejecuta, sin que el modelo escriba SQL (CP-06).'),
    ('Analítica', 'Se entrenan un modelo supervisado (demanda semanal por producto) y uno no supervisado '
     '(segmentos de clientes con K-means), con sus métricas y su dashboard (CP-07).'),
    ('Lo pedido en clase y los aportes propios', 'Se implementaron las devoluciones web, el inventario por sucursal '
     'y los traspasos, el pago sin conexión, las ofertas con mayoristas y los cambios con diferencia; y como aportes '
     'propios, el probador con la talla real, el aviso de talla y la detección de anomalías (CP-08 a CP-10).'),
    ('Verificar el sistema', 'La batería final suma 1303 pruebas automatizadas aprobadas, más las pruebas manuales '
     'de los servicios externos (5.5).'),
    ('Desplegar en la nube', 'La versión está desplegada en Railway con la base en Supabase; las migraciones se '
     'aplican solas en cada despliegue.'),
    ('Actualizar la documentación', 'Este documento y los modelos UML 2.5 en Enterprise Architect reflejan el '
     'software construido.'),
]
llenar('6.1. Conclusiones', [
    p('Se retoma cada objetivo específico del 1.3.2 y se indica cómo se cumplió:'),
    ed.tabla(['Objetivo', 'Cómo se cumplió'], CONCL, [3000, ANCHO - 3000]),
    p(''),
    p('En conjunto, se cumplió el objetivo general: Violet Boutique pasó a ser una plataforma SaaS multitenant que '
      'atiende a varias empresas aisladas entre sí, opera sin conexión en la web y en el móvil, sincroniza sin '
      'perder ni duplicar operaciones e incorpora inteligencia artificial y aprendizaje automático, desarrollada con '
      'ICONIX y modelada en UML 2.5.'),
])

# =====================================================================
# 6.2 Recomendaciones: estructurales y de uso
llenar('6.2. Recomendaciones', [
    sub('Recomendaciones estructurales'),
    p('Funcionalidades que se pueden agregar más adelante para mejorar la experiencia del usuario final:'),
    v('**Talla aprendida de las devoluciones.** Usar los cambios por talla para ajustar la recomendación del probador '
      'a cada cliente y a cada prenda.'),
    v('**Programa de puntos de fidelidad**, apoyado en los segmentos de clientes que ya calcula la analítica.'),
    v('**Probador nativo en Flutter**, con la detección de pose en el propio teléfono, en lugar de abrirlo desde el '
      'navegador.'),
    v('**Fotos del probador protegidas por sesión.** Hoy se guardan con un nombre aleatorio y se ven con la URL; '
      'conviene servirlas solo al cliente que las subió.'),
    v('**Detalle del turno y de la devolución en la web del administrador**, para abrir desde la anomalía el turno '
      'o la nota marcada.'),
    v('**Pasarela con bolivianos.** El modo de prueba de Stripe no admite BOB; en producción conviene una pasarela '
      'local o una cuenta que cobre en la moneda del negocio.'),
    sub('Recomendaciones de uso'),
    p('Lo que el usuario debe tener en cuenta para que las funcionalidades trabajen bien:'),
    v('Preparar el dispositivo para trabajar sin conexión al abrir la caja, y sincronizar antes de cerrarla.'),
    v('Cargar las medidas de cada prenda por talla antes de habilitarla en el probador, y que el cliente cargue sus '
      'medidas reales.'),
    v('Volver a entrenar los modelos de analítica cada mes; el de anomalías necesita al menos 20 turnos cerrados y el '
      'de demanda varias semanas de ventas.'),
    v('Revisar las anomalías como señales para mirar, no como pruebas de un error o un fraude.'),
    v('Configurar la ventana de devolución de la empresa y marcar la entrega de los pedidos web, porque desde ahí '
      'corre el plazo.'),
    v('Aceptar las notificaciones en el navegador y en el teléfono para recibir los avisos push.'),
    v('Descargar periódicamente la copia de seguridad y guardar la exportación de los datos fuera de la plataforma.'),
])

ed.cerrar(DOC)
print('listo')
