# Mejoras del capítulo I para la 2da presentación (notas de la ing, 01/11):
#   - el alcance, amplio y por plataforma (web de la plataforma, web de la empresa, tienda en línea y móvil);
#   - las limitaciones, claras y con el trabajo sin conexión aparte;
#   - F1 (roles y permisos por empresa) y F2 (avisos push y devolución automática del pago) en el alcance;
#   - la nota de devolución con su detalle por prenda y la conformidad del cliente;
#   - la 2da presentación se recorta a CU-13..CU-20 y el resto pasa a la 3ra;
#   - dos títulos cortados del 3.3.
# Uso: python editar_01_11_cap1.py <documento.docx>
import copy, sys
import docx
from docx.oxml.ns import qn
from docx_util import Editor

DOC = sys.argv[1]
ed = Editor(docx.Document(DOC))
T = ed.texto

# =====================================================================
# 1.5.1 Alcance
alcance = ed.parrafo('1.5.1. Alcance', exacto=True)
intro = alcance.getnext()
ed.poner_texto(intro, 'Se conserva todo lo construido en el primer parcial: el catálogo con sus tallas, colores, '
               'temporadas y colecciones; los proveedores; el inventario de varias sucursales; las reservas para '
               'probarse; las ventas en caja y en línea con la pasarela de pago; el vestidor con realidad aumentada; '
               'la inteligencia artificial (recomendaciones de prendas, asistente virtual y reportes por voz); los '
               'reportes de gestión y el tablero de indicadores; los avisos, la recuperación de la contraseña y la '
               'bitácora. El sistema llega a sus usuarios por cuatro frentes, todos sobre el mismo backend '
               '(FastAPI) y la misma base de datos (PostgreSQL con Row Level Security):')

limitacion = ed.parrafo('El cobro de las suscripciones se simula')  # modelo de viñeta
VINETAS = [
    '**Web de la plataforma.** El administrador de la plataforma registra las empresas, define los planes con '
    'sus límites y funciones, y asigna, renueva o suspende las suscripciones. Una página pública permite a una '
    'empresa interesada contratar un plan y dar de alta su empresa.',
    '**Web de la empresa.** El administrador, el encargado y el cajero gestionan sucursales, usuarios, roles y '
    'permisos; el catálogo, las ofertas y el inventario por sucursal; la caja, las ventas y las reservas en '
    'mostrador, también sin conexión; los cambios, las devoluciones y los traspasos; los reportes convencionales '
    'y con IA, el dashboard analítico, la bitácora, la exportación de los datos y las copias de seguridad. Se '
    'instala como PWA.',
    '**Tienda en línea.** El cliente navega el catálogo con la marca de la empresa, compra y paga en línea, '
    'reserva para probarse, usa el probador y pide cambios o devoluciones.',
    '**Aplicación móvil.** El cliente consulta el catálogo, compra y reserva, se prueba prendas con realidad '
    'aumentada y su talla real, recibe avisos push y reserva sin conexión desde una vitrina con fotos guardada '
    'en el teléfono.',
]
nuevos = [ed.copiar_parrafo(limitacion, v) for v in VINETAS]
modulo1 = ed.parrafo('Módulo 1 —')
por_modulo = ed.copiar_parrafo(intro, 'Por módulo, lo que se agrega sobre el primer parcial:')
ed.insertar_despues(intro, nuevos + [por_modulo])

MODULOS = {
    'Módulo 1 —': '**Módulo 1 — Plataforma SaaS (web).** Registro de empresas contratantes, administrador por '
    'empresa, asociación de usuarios y sucursales, y un administrador de la plataforma por encima de todas. El '
    'administrador de cada empresa gestiona los roles y los permisos de su propio personal, dentro de lo que '
    'permite su plan.',
    'Módulo 2 —': '**Módulo 2 — Planes y suscripciones (web).** Planes Básico, Profesional y Empresarial con '
    'límites y funciones configurables desde el backend: cada empresa puede hacer solo lo que incluye su plan, y '
    'el backend lo verifica en cada operación. Asignación, cambio, renovación y suspensión de la suscripción, con '
    'el cobro simulado.',
    'Módulo 4 —': '**Módulo 4 — PWA offline (web).** La aplicación Angular se instala como PWA. Con conexión, '
    'el cajero prepara el equipo: descarga a IndexedDB las prendas de su sucursal con su precio y su existencia, '
    'los clientes y su turno de caja. Sin conexión registra ventas de contado, cobradas en efectivo o con QR, y '
    'las ve en una cola con su estado. Todo sobrevive a cerrar el navegador.',
    'Módulo 5 —': '**Módulo 5 — Móvil offline (móvil).** La aplicación Flutter guarda en SQLite las '
    'sucursales, las prendas con su foto, su precio y su existencia por sucursal, y las reservas pendientes. Sin '
    'conexión, el cliente elige sus prendas en una vitrina con fotos y registra la reserva para probárselas.',
    'Módulo 7 —': '**Módulo 7 — Ventas offline, caja y devolución del pago (web y backend).** El servidor '
    'confirma o rechaza cada venta y cada pago offline contra el inventario central, y gana la operación que '
    'llega primero. El arqueo de la caja cuenta lo vendido sin conexión. Si una operación ya pagada se rechaza, '
    'el cliente recibe un aviso push y el pago se le devuelve automáticamente. Los cambios de prenda se '
    'gestionan dentro de un plazo.',
    'Módulo 10 —': '**Módulo 10 — Devoluciones vía web (web).** Pedido de la docente en clase: el cliente '
    'solicita el cambio o la devolución desde la tienda en línea, dentro de una ventana configurable por '
    'empresa. Cada devolución deja una nota de devolución con el detalle de cada prenda (talla, precio y '
    'diferencia a cobrar o a devolver) y la conformidad del cliente; la nota mueve el inventario y se ve en los '
    'reportes.',
}
for prefijo, texto in MODULOS.items():
    ed.poner_texto(ed.parrafo(prefijo, desde=alcance), texto)

# A los que no se reescriben se les agrega la plataforma en el título.
PLATAFORMA = {
    'Módulo 3 — Aislamiento multitenant.': 'Módulo 3 — Aislamiento multitenant (backend y base de datos).',
    'Módulo 6 — Sincronización.': 'Módulo 6 — Sincronización (web, móvil y backend).',
    'Módulo 8 — Reportes generativos.': 'Módulo 8 — Reportes generativos (web).',
    'Módulo 9 — Analítica con aprendizaje automático.':
        'Módulo 9 — Analítica con aprendizaje automático (web y backend).',
    'Módulo 11 — Aportes propios.': 'Módulo 11 — Aportes propios (web y móvil).',
    'Módulo 12 — Inventario, pago sin conexión y ofertas.':
        'Módulo 12 — Inventario, pago sin conexión y ofertas (web y móvil).',
}
modulo12 = ed.parrafo('Módulo 12 —', desde=alcance)
modulo12.addnext(ed.copiar_parrafo(
    modulo12, '**Módulo 13 — Inteligencia artificial (web y móvil).** Reúne lo que usa IA: los reportes '
    'generativos por texto o voz (módulo 8), la analítica con aprendizaje automático (módulo 9) y la foto realista '
    'del probador (módulo 11), que se suman a las recomendaciones de prendas y al asistente virtual del primer '
    'parcial. La IA es un modelo gratuito consumido por API (Gemini) que nunca accede a la base: el backend arma '
    'las consultas, y su uso tiene un cupo mensual según el plan.'))

for viejo, nuevo in PLATAFORMA.items():
    p = ed.parrafo(viejo.split('.')[0], desde=alcance)
    assert ed.reemplazar(p, '^' + viejo.replace('(', r'\(').replace(')', r'\)'), nuevo) == 1, viejo

# =====================================================================
# 1.5.2 Limitaciones: las generales y, aparte, las del trabajo sin conexión
lim = ed.parrafo('1.5.2. Limitaciones', exacto=True)
generales = ed.copiar_parrafo(por_modulo, '**Generales.**')
lim.addnext(generales)

cobro_offline = ed.parrafo('Sin conexión se cobra en efectivo o con QR', desde=lim)
cobro_offline.getparent().remove(cobro_offline)

ultima = ed.parrafo('La aplicación móvil se prueba en Android', desde=lim)
OFFLINE = [
    'Para trabajar sin conexión el equipo se prepara antes, con conexión: el cajero, con su turno de caja '
    'abierto; el cliente, con su sesión iniciada. Sin ese paso no hay nada que consultar ni registrar.',
    'Sin conexión solo se registran ventas de contado, en la PWA del cajero, y reservas, en la aplicación móvil '
    'del cliente. El resto (catálogo, inventario, cambios y devoluciones, traspasos, reportes y administración) '
    'necesita conexión.',
    'Sin conexión se cobra en efectivo o con QR, anotando la referencia del pago; la pasarela de pago en línea '
    'necesita conexión.',
    'Lo descargado es una foto del momento: hasta 2.000 prendas y 1.000 clientes, con una vigencia de 12 horas. '
    'Pasado ese plazo se avisa que los datos pueden estar desactualizados, pero no se bloquea.',
    'Ninguna operación sin conexión es definitiva: la confirma o la rechaza el servidor al sincronizar. Si otra '
    'venta con conexión se llevó la prenda antes, gana la que llegó primero al servidor y la offline se rechaza '
    'con su motivo.',
    'Sin conexión no se registran clientes nuevos: la venta offline se hace con un cliente descargado o sin '
    'cliente.',
    'La caja no se cierra mientras queden ventas sin conexión de ese turno sin subir al servidor.',
    'Se sincroniza en lotes de hasta 50 operaciones; mientras no hay conexión, se vuelve a intentar cada minuto.',
]
titulo_offline = ed.copiar_parrafo(por_modulo, '**Del trabajo sin conexión.**')
ed.insertar_despues(ultima, [titulo_offline] + [ed.copiar_parrafo(limitacion, v) for v in OFFLINE])

# =====================================================================
# 1.6 La 2da presentación se recorta a CU-13..CU-20; el resto pasa a la 3ra
tabla_pres = ed.tabla_despues(ed.parrafo('Cómo se aplica en este proyecto.'))
tr2 = ed.fila(tabla_pres, 'Presentación 2')
ed.poner_celda(tr2.findall(qn('w:tc'))[2],
               'CU-13 a CU-20: preparar el dispositivo; ventas, reservas y pagos sin conexión; sincronización y '
               'operaciones pendientes; devolución del dinero de las rechazadas; caja con ventas sin conexión')
tr3 = ed.fila(tabla_pres, 'Presentación 3')
ed.poner_celda(tr3.findall(qn('w:tc'))[2],
               'CU-21 a CU-43: inventario de la sucursal; cambios de prenda, devoluciones web con su nota y '
               'avisos por correo; reportes con IA y voz; analítica con ML; ofertas y precios mayoristas; '
               'traspasos y probador por talla; exportación de datos y copias de seguridad. Y lo pedido en la '
               '2da presentación (CU-41 a CU-43): roles y permisos por empresa, avisos push y devolución '
               'automática del pago')

# =====================================================================
# 3.3: dos títulos cortados
for viejo, nuevo in (('CU-02 — Gestionar plane', 'CU-02 — Gestionar planes'),
                     ('CU-04 — Consultar plan y consum', 'CU-04 — Consultar plan y consumo')):
    p = ed.parrafo(viejo, desde=ed.parrafo('3.3. Diagramas de secuencia'), exacto=True)
    assert ed.reemplazar(p, viejo + '$', nuevo) == 1

# =====================================================================
# 1.3.1 El objetivo general es el título de la portada con «Desarrollar» adelante
general = ed.parrafo('1.3.1. Objetivo general', exacto=True).getnext()
ed.poner_texto(general, 'Desarrollar Violet Boutique, plataforma SaaS multitenant de comercio electrónico para '
               'empresas de venta de ropa, con un probador virtual que distingue tallas, operación offline en web '
               'y móvil, sincronización de datos y reportes generativos con inteligencia artificial, con la '
               'metodología ICONIX y modelos UML.')

# El texto base va en negro: el color por defecto del documento era gris (404040). Lo que tiene color
# propio (los encabezados rojos de las tablas, los alternativos) no cambia.
color = ed.doc.styles.element.find(qn('w:docDefaults')).find('.//' + qn('w:color'))
color.set(qn('w:val'), '000000')

# Los subtítulos no quedan solos al pie de una página.
from docx.text.paragraph import Paragraph
for p in (por_modulo, generales, titulo_offline):
    Paragraph(p, None).paragraph_format.keep_with_next = True

ed.cerrar(DOC)
print('ok')
