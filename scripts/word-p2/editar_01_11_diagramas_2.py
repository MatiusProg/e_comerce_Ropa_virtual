# Segunda tanda de diagramas en el Word de la 2da presentación (01/11):
#   3.1  el modelo de dominio;
#   3.3  la secuencia de CU-13 a CU-20, después de la de CU-12 (las de CU-01 a CU-12 son de Karen);
#   3.5  el diseño de la base de datos, en cuatro partes;
#   3.6  las capturas de los prototipos de CU-04 a CU-12.
# Uso: python editar_01_11_diagramas_2.py <documento.docx> <carpeta_jpg_de_EA> <carpeta_prototipos>
import os, sys
import docx
from docx.oxml.ns import qn
from docx_util import Editor

DOC, JPG, PROTO = sys.argv[1:4]
ed = Editor(docx.Document(DOC))
T = ed.texto

# El mismo formato de imagen que editar_01_11_diagramas.py.
import io
from docx.shared import Cm
from docx.text.paragraph import Paragraph
from PIL import Image

ANCHO = 15.5
NUEVOS = [f'CU-{n}' for n in range(13, 21)]


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return st is not None and st.get(qn('w:val')) == estilo


def parrafo_imagen(ruta, alto=21.0):
    blob = open(ruta, 'rb').read()
    w, h = Image.open(io.BytesIO(blob)).size
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(min(ANCHO, alto * w / h)))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0); pf.alignment = 1
    return p._p


def titulo(texto, estilo='Titulo11', desde=None):
    return ed.buscar(lambda e: e.tag == qn('w:p') and es_titulo(e, estilo) and T(e).strip().startswith(texto), desde)


modelo_texto = ed.parrafo('Cada ficha sigue el formato de ICONIX')
modelo_leyenda = ed.parrafo('Modelo de casos de uso estructurado del primer parcial, parte 1 de 3')
cap2_6 = titulo('2.6.')


def texto(t):
    return ed.copiar_parrafo(modelo_texto, t)


def leyenda(t):
    el = ed.copiar_parrafo(modelo_leyenda, t)
    Paragraph(el, None).paragraph_format.keep_with_next = True
    return el


def reemplazar_pendiente(cap, nuevos):
    pendiente = cap.getnext()
    assert T(pendiente).startswith('[Pendiente]'), T(pendiente)
    ed.insertar_despues(pendiente, nuevos)
    pendiente.getparent().remove(pendiente)


# --- 3.1 --------------------------------------------------------------------------
reemplazar_pendiente(titulo('3.1.'), [
    texto('El modelo de dominio reúne las entidades del negocio que aparecen en la robustez de CU-01 a CU-20, '
          'más el producto y su variante, que hacen falta para entender la existencia y la venta. No lleva '
          'atributos: muestra qué conceptos hay y cómo se relacionan, con el nombre y la multiplicidad de '
          'cada asociación. Las columnas de cada tabla están en el diseño de la base de datos (3.5). En '
          'celeste, lo que se guarda en el dispositivo para trabajar sin conexión.'),
    parrafo_imagen(os.path.join(JPG, '3.1.jpg'), alto=12.0),
])

# --- 3.3: CU-13 a CU-20, antes del 3.4 --------------------------------------------------
modelo_h3 = titulo('CU-13', 'Titulo3', desde=cap2_6)
ancla = titulo('3.4.').getprevious()
for cu in NUEVOS:
    nombre = T(titulo(cu, 'Titulo3', desde=cap2_6)).strip()
    ancla = ed.insertar_despues(ancla, [ed.copiar_parrafo(modelo_h3, nombre),
                                        parrafo_imagen(os.path.join(JPG, f'3.3_{cu}.jpg'), alto=16.0)])

# --- 3.5 --------------------------------------------------------------------------------
PARTES = ['Plataforma, empresas y seguridad', 'Organización y clientes',
          'Catálogo e inventario', 'Ventas, caja, reservas y sin conexión']
piezas = [texto('Las 51 tablas de la base, en cuatro partes. Cada tabla lleva su nombre, todas sus columnas '
                'con el tipo de PostgreSQL y la marca «PK» o «FK». Las relaciones se nombran con un verbo y la '
                'cardinalidad sale de lo que la base obliga: 1 si la clave foránea es NOT NULL y 0..1 si admite '
                'nulo; del otro lado, 0..1 si la clave foránea es UNIQUE y 0..* si no. Las tablas marcadas con '
                '«rls» filtran por empresa con Row Level Security: su empresa_id apunta a EMPRESA, que se dibuja '
                'en la parte 1. Una tabla de otra parte aparece en gris, solo con su clave primaria. El contenido '
                'se generó del esquema real de la base (information_schema).')]
for i, nombre in enumerate(PARTES, start=1):
    piezas += [leyenda(f'Parte {i} de 4: {nombre}.'), parrafo_imagen(os.path.join(JPG, f'3.5_Parte_{i}.jpg'), alto=16.0)]
reemplazar_pendiente(titulo('3.5.'), piezas)

# --- 3.6: capturas de CU-04 a CU-12 -------------------------------------------------------
CAPTURAS = {
    'CU-04': [('cu04-mi-plan-y-consumo.png', 'Web: «Mi plan», con el plan vigente, el uso de los límites, los cupos del mes y las funciones incluidas.')],
    'CU-05': [('cu05-limite-de-sucursales-alcanzado.png', 'Web: el sistema rechaza una sucursal más porque el plan ya llegó a su límite.'),
              ('cu05-mi-plan-limite-alcanzado.png', 'Web: «Mi plan» marca el límite de sucursales alcanzado.')],
    'CU-06': [('cu06-login-con-empresa.png', 'Web: inicio de sesión con el nombre de la empresa, el correo y la contraseña.'),
              ('cu06-login-empresa-no-encontrada.png', 'Web: la empresa escrita no existe.')],
    'CU-07': [('cu07-registro-de-cliente.png', 'Web: el formulario de registro del cliente.')],
    'CU-08': [('cu08-lista-de-usuarios.png', 'Web: los usuarios de la empresa, con su rol, sucursal y estado.'),
              ('cu08-formulario-nuevo-usuario.png', 'Web: el formulario de un usuario nuevo.')],
    'CU-09': [('cu09-lista-de-sucursales.png', 'Web: las sucursales, con el contador del plan.'),
              ('cu09-formulario-nueva-sucursal.png', 'Web: el formulario de una sucursal nueva.')],
    'CU-10': [('cu10-lista-de-empleados.png', 'Web: los empleados, con el contador del plan.'),
              ('cu10-formulario-registrar-empleado.png', 'Web: registrar un empleado, creando su cuenta o vinculando una existente.')],
    'CU-11': [('cu11-planes-publicos.png', 'Web: la página pública con los planes, sus precios, límites y funciones.'),
              ('cu11-contratar-paso1-empresa.png', 'Web: contratar un plan, paso 1: los datos de la empresa.'),
              ('cu11-contratar-paso2-sucursal-y-administrador.png', 'Web: paso 2: la sucursal principal y la cuenta del administrador.'),
              ('cu11-contratar-paso3-pago-qr-simulado.png', 'Web: paso 3: el pago por QR simulado.'),
              ('cu11-empresa-creada-comprobante.png', 'Web: la empresa creada, con el comprobante simulado.')],
    'CU-12': [('cu12-mi-tienda-logo-y-colores.png', 'Web: «Mi tienda», con el logo, los colores y la vista previa de la tienda.')],
}
cap3_6 = titulo('3.6.')
reemplazar_pendiente(cap3_6, [texto(
    'Capturas de los prototipos de cada caso de uso, tomadas del sistema funcionando contra la base de pruebas: '
    'la web (PWA) y, en los casos sin conexión del cliente, la aplicación móvil. Las pantallas de CU-04 y de '
    'CU-08 a CU-12 son de una empresa de prueba, Boutique Aurora, dada de alta con el propio CU-11.')])
for cu, capturas in CAPTURAS.items():
    ancla = titulo(cu, 'Titulo3', desde=cap3_6)
    piezas = []
    for archivo, t in capturas:
        piezas += [leyenda(t), parrafo_imagen(os.path.join(PROTO, archivo), alto=12.0)]
    ed.insertar_despues(ancla, piezas)

ed.cerrar(DOC)
print('ok')
