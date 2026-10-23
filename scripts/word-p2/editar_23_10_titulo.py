# El probador virtual que distingue tallas es el principal diferenciador del SaaS: va en el título de la
# portada (está dos veces, una por cada cuadro de texto) y en el objetivo general (pedido de Luis, 23/10).
# Uso: python editar_23_10_titulo.py <documento.docx>
import sys
import docx
from docx.oxml.ns import qn
from docx_util import Editor

ed = Editor(docx.Document(sys.argv[1]))
n = ed.reemplazar_en_todo(r'para empresas de venta de ropa, con operación offline en web y móvil',
                          'para empresas de venta de ropa, con un probador virtual que distingue tallas, '
                          'operación offline en web y móvil')
print('título:', n)
p = ed.parrafo('Evolucionar Violet Boutique hacia una plataforma de comercio electrónico')
ed.poner_texto(p, 'Evolucionar Violet Boutique hacia una plataforma de comercio electrónico **SaaS multitenant**, '
                  'con planes de suscripción, aplicación web progresiva, operación offline en web y móvil, '
                  'sincronización de datos y reportes generativos con inteligencia artificial, y con un **probador '
                  'virtual que distingue tallas** como principal diferenciador frente a otras plataformas, aplicando '
                  'la metodología ICONIX y manteniendo la coherencia entre los modelos UML 2.5+ y la implementación.')
ed.cerrar(sys.argv[1])
print('ok')
