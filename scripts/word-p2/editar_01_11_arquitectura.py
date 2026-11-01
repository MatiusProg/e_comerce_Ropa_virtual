# Word de la 2da presentación (01/11, tercera tanda):
#   3.5  un solo diagrama con las tablas que usa el 2do parcial, en lugar de las cuatro partes;
#   4.2  4.2.1 diagrama de despliegue y 4.2.2 diagrama de capas.
# Uso: python editar_01_11_arquitectura.py <documento.docx> <carpeta_jpg_de_EA>
#   (la carpeta tiene 3.5.jpg, 4.2.1.jpg y 4.2.2.jpg)
import io, os, sys
import docx
from docx.oxml.ns import qn
from docx.shared import Cm
from PIL import Image
from docx_util import Editor

DOC, JPG = sys.argv[1:3]
ed = Editor(docx.Document(DOC))
T = ed.texto


def es_titulo(el, estilo):
    st = el.find('.//' + qn('w:pStyle'))
    return st is not None and st.get(qn('w:val')) == estilo


def titulo(texto, estilo='Titulo11', desde=None):
    return ed.buscar(lambda e: e.tag == qn('w:p') and es_titulo(e, estilo) and T(e).strip().startswith(texto), desde)


def parrafo_imagen(ruta, alto=21.0):
    blob = open(ruta, 'rb').read()
    w, h = Image.open(io.BytesIO(blob)).size
    p = ed.doc.add_paragraph()
    p.add_run().add_picture(io.BytesIO(blob), width=Cm(min(15.5, alto * w / h)))
    pf = p.paragraph_format
    pf.first_line_indent = Cm(0); pf.left_indent = Cm(0); pf.alignment = 1
    return p._p


modelo_texto = ed.parrafo('Cada ficha sigue el formato de ICONIX')
modelo_h2 = titulo('2.3.1.', 'Titulo2')


def texto(t):
    return ed.copiar_parrafo(modelo_texto, t)


# --- 3.5: todo lo que hay entre el título y el 3.6 se reemplaza ----------------------
cap3_5, cap3_6 = titulo('3.5.'), titulo('3.6.')
el = cap3_5.getnext()
while el is not cap3_6:
    sig = el.getnext(); el.getparent().remove(el); el = sig
ed.insertar_despues(cap3_5, [
    texto('El diseño de la base de datos muestra las 32 tablas que usan los casos de uso de esta presentación '
          '(CU-01 a CU-20): las de la plataforma, la empresa y sus usuarios, la caja, la venta y la reserva, el '
          'inventario y el catálogo que se descargan al dispositivo, y la operación sin conexión. Las demás tablas '
          'son del primer parcial y están en el Anexo 1; una clave foránea hacia ellas queda marcada «FK» en su '
          'columna, sin línea. Cada tabla lleva su nombre, todas sus columnas con el tipo de PostgreSQL y la marca '
          '«PK» o «FK». Las relaciones se nombran con un verbo y la cardinalidad sale de lo que la base obliga: 1 si '
          'la clave foránea es NOT NULL y 0..1 si admite nulo; del otro lado, 0..1 si es UNIQUE y 0..* si no. Las '
          'tablas marcadas «rls» filtran por empresa con Row Level Security; su línea a EMPRESA se dibuja solo desde '
          'las tablas de la plataforma. El contenido se generó del esquema real de la base (information_schema).'),
    parrafo_imagen(os.path.join(JPG, '3.5.jpg'), alto=21.0),
])

# --- 4.2 ---------------------------------------------------------------------------------
cap4_2 = titulo('4.2.')
pendiente = cap4_2.getnext()
assert T(pendiente).startswith('[Pendiente]'), T(pendiente)
ed.insertar_despues(pendiente, [
    texto('La arquitectura se muestra con dos diagramas que se leen juntos. Cada nodo del despliegue tiene un color, '
          'y en el diagrama de capas cada elemento de la capa intermedia y de la capa de software lleva ese mismo '
          'color y, como estereotipo, el nombre del nodo donde corre; en el modelo de Enterprise Architect además '
          'queda unido a él con una relación «trace».'),
    ed.copiar_parrafo(modelo_h2, '4.2.1. Diagrama de despliegue'),
    texto('Los clientes son de dos tipos: la computadora o tablet, que usa la PWA desde el navegador y guarda en '
          'IndexedDB el paquete y la cola sin conexión, y el smartphone Android, con la aplicación Flutter y su base '
          'SQLite. Railway construye cada servicio desde su Dockerfile y lo corre en un contenedor Docker: la web en '
          'nginx:alpine y la API en python:3.13-slim con Gunicorn y workers Uvicorn, que al arrancar aplica las '
          'migraciones. La base está en Supabase, detrás de su session pooler, con Row Level Security por empresa. '
          'En desarrollo, docker-compose levanta PostgreSQL 16 en un contenedor. GitHub es el origen desde el que '
          'Railway construye las imágenes; Brevo envía los correos de acceso, y Gemini y Stripe son los servicios '
          'externos del primer parcial.'),
    parrafo_imagen(os.path.join(JPG, '4.2.1.jpg'), alto=21.0),
    ed.copiar_parrafo(modelo_h2, '4.2.2. Diagrama de capas'),
    texto('Capa 1, vista de análisis: los módulos del alcance que cubren CU-01 a CU-20. Capa 2: el backend, el '
          'frontend (PWA) y el móvil, con sus carpetas y archivos característicos; cada módulo se realiza en las '
          'aplicaciones que lo implementan. Capa 3, capa intermedia: el software sobre el que se ejecuta cada '
          'aplicación (Gunicorn y Uvicorn, SQLAlchemy y Alembic, nginx, el Service Worker con IndexedDB, Flutter con '
          'SQLite, PgBouncer y PostgreSQL). Capa 4, capa de software: el sistema sobre el que corre la capa '
          'intermedia (los contenedores Linux de Railway, Supabase en AWS, el sistema operativo y el navegador del '
          'cliente, Android y Docker Desktop en la PC de desarrollo).'),
    parrafo_imagen(os.path.join(JPG, '4.2.2.jpg'), alto=21.0),
])
pendiente.getparent().remove(pendiente)

ed.cerrar(DOC)
print('ok')
