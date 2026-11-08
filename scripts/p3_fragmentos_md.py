# Escribe docs/diagramas/2do Parcial/3.3-fragmentos-cu21-45.md: los fragmentos combinados de la secuencia
# de la 3ra presentación, sacados de los guiones (scripts/ea-secuencia-p3-<a..e>.datos.ps1), con el mismo
# formato que 3.3-fragmentos-cu13-20.md. Sirve para revisarlos o volver a dibujarlos a mano en EA.
# Uso: python -X utf8 scripts/p3_fragmentos_md.py
import glob
import os
import re

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, '..', 'docs', 'diagramas', '2do Parcial', '3.3-fragmentos-cu21-45.md')
TIPOS = ('alt', 'opt', 'loop', 'break', 'critical')
campo = lambda k, s: (re.search(k + r"\s*=\s*'((?:[^']|'')*)'", s) or [None, None])[1]


def casos():
    for f in sorted(glob.glob(os.path.join(AQUI, 'ea-secuencia-p3-*.datos.ps1'))):
        texto = open(f, encoding='utf-8-sig').read()
        for bloque in re.split(r"\n@\{\s*\n", texto)[1:]:
            nombre = campo('nombre', bloque)
            guion = bloque[bloque.index('guion'):]
            pasos = [l.strip() for l in guion.splitlines() if l.strip().startswith("@{ t=")]
            yield nombre, pasos


def fragmentos(pasos):
    abiertos, cerrados, n = [], [], 0
    for p in pasos:
        t = campo('t', p)
        if t in TIPOS:
            n += 1
            fr = {'n': n, 't': t, 'padre': abiertos[-1]['n'] if abiertos else None, 'ops': []}
            if t != 'alt':
                fr['ops'].append({'g': campo('g', p), 'msgs': []})
            abiertos.append(fr); cerrados.append(fr)
        elif t == 'op':
            abiertos[-1]['ops'].append({'g': campo('g', p), 'msgs': []})
        elif t == 'fin':
            abiertos.pop()
        elif t == 'msg' and "ret=$true" not in p:
            for fr in abiertos:
                if fr['ops']:
                    fr['ops'][-1]['msgs'].append(campo('n', p))
    return cerrados


def rango(msgs):
    if not msgs:
        return 'sin mensajes'
    if len(msgs) == 1:
        return f'solo «{msgs[0]}»'
    return f'desde «{msgs[0]}» hasta «{msgs[-1]}» ({len(msgs)} mensajes)'


def nivel(fr, todos):
    d, p = 0, fr['padre']
    while p:
        d += 1; p = next(x for x in todos if x['n'] == p)['padre']
    return d


out = ['# 3.3 Diagramas de secuencia de la 3ra presentación: los fragmentos combinados', '',
       '*Lo genera `scripts/p3_fragmentos_md.py` a partir de los guiones `scripts/ea-secuencia-p3-<a..e>.datos.ps1`; '
       'no se edita a mano.*', '',
       'Cada fragmento sale de una estructura de control del código (el comentario de cada guion dice el archivo y la '
       'línea): **alt** = if/else o `raise` excluyentes, **opt** = if sin else, **loop** = for, **break** = `raise` '
       'temprano, **critical** = commit con rollback. Para cada operando se indica su guarda y entre qué mensajes va. '
       'El generador (`scripts/ea-secuencia-p3.ps1`) ya los dibuja; esta lista sirve para revisarlos o rehacerlos a '
       'mano en EA si se mueve algo.', '']
total = 0
for nombre, pasos in casos():
    frs = fragmentos(pasos)
    total += len(frs)
    out += [f'## {nombre}']
    if not frs:
        out += ['Sin fragmentos.', '']
        continue
    for fr in frs:
        sangria = '   ' * nivel(fr, frs)
        dentro = f' — dentro del fragmento {fr["padre"]}' if fr['padre'] else ''
        out.append(f'{sangria}{fr["n"]}. **{fr["t"]}**{dentro}')
        for op in fr['ops']:
            g = f'[{op["g"]}]' if op['g'] else '(sin guarda)'
            out.append(f'{sangria}   - {g}: {rango(op["msgs"])}')
    out.append('')
open(SALIDA, 'w', encoding='utf-8').write('\n'.join(out))
print('ok', SALIDA, total, 'fragmentos')
