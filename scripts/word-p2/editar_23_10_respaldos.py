# CU-40 «Gestionar copias de seguridad de la empresa» (aporte propio, pedido de Luis el 23/10): diferencia los
# planes y es una función básica de cualquier SaaS. Sigue lo que se hizo en PROYECTO_MEDICOS (backend/backups):
#   - copia lógica en JSON solo con los datos de la empresa (pasa por RLS), que se descarga y no se guarda;
#   - copias automáticas guardadas cifradas, conservando las últimas N según el plan;
#   - la frecuencia y la retención son funciones del plan; restaurar NUNCA lo limita el plan;
#   - la restauración reemplaza los datos de la empresa en una sola transacción y queda en la bitácora.
# Va al final de la presentación 3, así no se renumera nada.
# Uso: python editar_23_10_respaldos.py <documento.docx>
import copy, sys
import docx
from docx.oxml.ns import qn
from docx_util import Editor

ed = Editor(docx.Document(sys.argv[1]))
T = ed.texto
CU = 'CU-40'
NOMBRE = 'Gestionar copias de seguridad de la empresa'

# 1.5.1: alcance
p = ed.parrafo('Módulo 11 — Aportes propios.')
assert ed.reemplazar(p, r'; y la exportación de los datos de la empresa\.',
                     '; la exportación de los datos de la empresa; y las copias de seguridad con su '
                     'restauración, cuya frecuencia depende del plan.') == 1

# 1.6: la presentación 3 suma el CU-40
tbl = ed.tabla_despues(ed.parrafo('Cómo se aplica en este proyecto.'))
ed.poner_celda(ed.fila(tbl, 'Presentación 3').findall(qn('w:tc'))[2],
               'CU-27 a CU-40: reportes con IA y voz; analítica con ML; ofertas y precios mayoristas; traspasos y '
               'probador por talla; exportación de datos y copias de seguridad')

# 2.1.1: planes
tbl = ed.tabla_despues(ed.parrafo('2.1.1. Planes de suscripción'))
for fila in (['Copias de seguridad manuales (propio)', 'Una por semana', 'Una por día', 'A voluntad'],
             ['Copias automáticas cifradas (propio)', 'Semanal, conserva 4', 'Diaria, conserva 7',
              'Diaria, conserva 30'],
             ['Restaurar la empresa desde una copia (propio)', 'Sí', 'Sí', 'Sí']):
    ed.agregar_fila(tbl, fila)
ed.recebrar(tbl)

# 2.3.3: requisitos propios
p = ed.parrafo('El enunciado pide «otras funcionalidades como aporte propio»')
assert ed.reemplazar(p, r'propone 13 requisitos en tres frentes', 'propone 17 requisitos en cuatro frentes') == 1
tbl_plat = ed.tabla_despues(ed.parrafo('Plataforma y planes', exacto=True))
ancla = tbl_plat.getnext()  # el párrafo vacío que sigue a la tabla
ed.insertar_despues(ancla, [
    ed.nuevo_parrafo('Copias de seguridad', 'Titulo3', con_siguiente=True),
    ed.nuevo_parrafo('Toda empresa que confía sus datos a un SaaS necesita poder recuperarlos. La copia es lógica, '
                     'en JSON y solo con los datos de la empresa, de modo que se abre con cualquier herramienta y '
                     'se puede revisar. No reemplaza a la exportación a Excel del RF-48, que es para leer los '
                     'datos, no para restaurarlos.'),
    ed.tabla(['RF', 'El sistema deberá permitir…'], [
        ['RF-60', 'Que el administrador de la empresa genere una copia de seguridad de todos los datos de su '
                  'empresa y la descargue, con la frecuencia que permite su plan'],
        ['RF-61', 'Generar copias automáticas de cada empresa con la frecuencia de su plan, guardarlas cifradas y '
                  'conservar solo las últimas que el plan indica'],
        ['RF-62', 'Restaurar la empresa desde una copia, reemplazando sus datos en una sola transacción, después de '
                  'verificar que el archivo sea de esa empresa y no esté alterado'],
        ['RF-63', 'Consultar el historial de copias y restauraciones: cuándo, quién, tamaño y filas por tabla'],
    ], [1100, 8682]),
    ed.nuevo_parrafo(),
])

# 2.3.4: requisito no funcional
tbl = ed.tabla_despues(ed.parrafo('2.3.4. Requisitos no funcionales'))
ed.agregar_fila(tbl, ['RNF17', 'Seguridad de las copias (propio)',
                      'Las copias manuales se descargan y no quedan en el servidor; las automáticas se guardan '
                      'cifradas y con RLS. Cada copia lleva su SHA-256 para detectar un archivo alterado'])
ed.recebrar(tbl)

# 2.4: reglas de negocio
tbl = ed.tabla_despues(ed.parrafo('2.4. Reglas de negocio'))
for fila in (['RN-18', 'El plan limita cuántas copias manuales se generan, nunca la restauración: recuperarse de un '
                       'problema no depende de cuánto paga la empresa. Las copias automáticas no gastan la cuota de '
                       'las manuales'],
             ['RN-19', 'Una restauración reemplaza todos los datos de la empresa; no los mezcla con los actuales. Solo '
                       'la hace el administrador de la empresa, con un archivo de su propia empresa, y queda en la '
                       'bitácora con quién, cuándo y de qué archivo']):
    ed.agregar_fila(tbl, fila)
ed.recebrar(tbl)

# 2.5: lista de casos de uso
h25 = ed.parrafo('2.5. Diagrama UML de casos de uso')
intro = h25.getnext()
assert ed.reemplazar(intro, r'Son 39 casos de uso', 'Son 40 casos de uso') == 1
assert ed.reemplazar(intro.getnext(), r'del RF-01 al RF-59', 'del RF-01 al RF-63') == 1
tbl = ed.tabla_despues(intro)
ed.agregar_fila(tbl, [CU, f'{NOMBRE} (propio)', 'Administrador de la empresa', 'Web', '—', 'RF-60 a RF-63'])
ed.recebrar(tbl)

# 2.6: el título del CU en «PARA SIGUIENTES PRESENTACIONES»
h39 = ed.parrafo('CU-39 —')
h39.addnext(ed.copiar_parrafo(h39, f'{CU} — {NOMBRE}'))

ed.cerrar(sys.argv[1])
print('ok')
