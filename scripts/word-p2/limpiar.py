# Quita del .docx las relaciones y archivos de media que el cuerpo ya no usa
# (quedan del documento del 1er parcial que sirvió de plantilla).
import re, sys, zipfile

ent, sal = sys.argv[1], sys.argv[2]
zin = zipfile.ZipFile(ent)
doc = zin.read('word/document.xml').decode('utf8')
rels = zin.read('word/_rels/document.xml.rels').decode('utf8')
usados = set(re.findall(r'r:(?:id|embed|link|pict)="([^"]+)"', doc))
quitar_rel, quitar_arch = [], set()
for m in re.finditer(r'<Relationship [^>]*/>', rels):
    r = m.group(0)
    rid = re.search(r'Id="([^"]+)"', r).group(1)
    tipo = re.search(r'Type="([^"]+)"', r).group(1)
    destino = re.search(r'Target="([^"]+)"', r).group(1)
    if rid not in usados and tipo.endswith(('/image', '/oleObject', '/package')) and 'External' not in r:
        quitar_rel.append(r)
        quitar_arch.add('word/' + destino.lstrip('/').removeprefix('word/'))
for r in quitar_rel:
    rels = rels.replace(r, '')
# un archivo puede estar referenciado por otra parte (encabezado, pie): se conserva
otras = ''.join(zin.read(n).decode('utf8', 'ignore') for n in zin.namelist()
                if n.endswith('.rels') and n != 'word/_rels/document.xml.rels')
quitar_arch = {a for a in quitar_arch if a.split('/')[-1] not in otras}
zout = zipfile.ZipFile(sal, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    if item.filename in quitar_arch:
        continue
    datos = rels.encode('utf8') if item.filename == 'word/_rels/document.xml.rels' else zin.read(item.filename)
    zout.writestr(item, datos)
zout.close()
print('relaciones quitadas', len(quitar_rel), 'archivos quitados', len(quitar_arch))
