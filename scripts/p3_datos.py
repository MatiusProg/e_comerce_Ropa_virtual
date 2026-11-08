# Junta los datos de la 3ra presentación (CU-21 a CU-45) que levantaron los agentes en p3_datos_a..e.py y
# escribe lo que necesitan los generadores y el Word:
#   - scripts/ea-p3.datos.json          2.5 y 3.2 (con TODOS los casos, para el diagrama general)
#   - scripts/ea-p3-clases-<g>.datos.json  3.4, uno por grupo (cada uno trae sus propias clases)
#   - scripts/p3-especificaciones.json   las fichas del 2.6
#   - docs/diagramas/2do Parcial/3.2-robustez-mensajes-p3.md  los mensajes de la robustez
# Uso:  python -X utf8 scripts/p3_datos.py
import importlib
import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
import p2_datos  # noqa: E402

GRUPOS = ['a', 'b', 'c', 'd', 'e']
MD = AQUI.parent / 'docs' / 'diagramas' / '2do Parcial' / '3.2-robustez-mensajes-p3.md'


def cargar():
    mods = {}
    for g in GRUPOS:
        try:
            mods[g] = importlib.import_module(f'p3_datos_{g}')
        except ModuleNotFoundError:
            print(f'  (falta p3_datos_{g}.py, se saltea)')
    return mods


def validar_robustez(r):
    tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
             **{x: 'C' for x in r['c']}, **{x: 'E' for x in r['e']}}
    grupos = sorted({m[0] for m in r['m']})
    assert grupos == list(range(1, len(r['grupos']) + 1)), (r['cu'], grupos)
    for g, de, a, op in r['m']:
        assert de in tipos and a in tipos, (r['cu'], de, a)
        assert {tipos[de], tipos[a]} in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'}), (r['cu'], de, a, op)
    usados = {p for _, de, a, _ in r['m'] for p in (de, a)}
    assert usados == set(tipos), (r['cu'], set(tipos) - usados)


def main():
    mods = cargar()
    casos = list(p2_datos.CASOS)
    robustez, descripcion, espec = [], dict(p2_datos.DESCRIPCION), {}
    for g, m in mods.items():
        casos += list(m.CASOS)
        for r in m.ROBUSTEZ:
            validar_robustez(r)
            robustez.append(r)
        for k, v in m.DESCRIPCION.items():
            descripcion.setdefault(k, v)
        espec.update(m.ESPEC)
        clases = {'_convencion': 'igual que ea-p2-clases.datos.json', 'clases': m.CLASES, 'cus': m.CUS}
        (AQUI / f'ea-p3-clases-{g}.datos.json').write_text(
            json.dumps(clases, ensure_ascii=False, indent=1), encoding='utf-8')

    ids = [c[0] for c in casos]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
    conocidos = set(ids)
    for c in casos:
        for ac in c[2]:
            assert ac in p2_datos.ACTORES, (c[0], ac)
        for x in list(c[3]) + (list(c[5]) if len(c) > 5 else []):
            assert x in conocidos, (c[0], x)
    for r in robustez:
        assert r['cu'] in conocidos, r['cu']
        for ac in r['a']:
            assert ac in p2_datos.ACTORES, (r['cu'], ac)

    salida = {
        'actores': p2_datos.ACTORES,
        'casos': [dict(id=c[0], n=c[1], actores=c[2], incluye=c[3], notas=c[4],
                       extiende=c[5] if len(c) > 5 else []) for c in casos],
        'robustez': [dict(cu=r['cu'], n=r['n'], a=r['a'], f=r['f'], c=r['c'], e=r['e'], grupos=r['grupos'],
                          pares=sorted({tuple(sorted((de, a))) for _, de, a, _ in r['m'] if de != a}))
                     for r in robustez],
        'descripcion': descripcion,
    }
    (AQUI / 'ea-p3.datos.json').write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding='utf-8')
    (AQUI / 'p3-especificaciones.json').write_text(
        json.dumps({'casos': {c[0]: c[1] for c in casos}, 'espec': espec}, ensure_ascii=False, indent=1),
        encoding='utf-8')

    out = ['# 3.2 Diagramas de robustez de la 3ra presentación: los mensajes', '',
           '*Lo genera `scripts/p3_datos.py`; no se edita a mano.* Cómo cargarlos en EA: ver',
           '`3.2-robustez-mensajes.md`. El número es `grupo.orden`.', '']
    for r in sorted(robustez, key=lambda r: int(r['cu'][3:])):
        out += [f'## {r["cu"]} — {r["n"]}', '']
        out += [f'- **Grupo {i}:** {g}' for i, g in enumerate(r['grupos'], 1)]
        out += ['', '| N.º | De | A | Mensaje |', '|---|---|---|---|']
        orden = {}
        for g, de, a, op in r['m']:
            orden[g] = orden.get(g, 0) + 1
            nom = lambda x: x[2:] + ' (actor)' if x.startswith('A:') else x  # noqa: E731
            out.append(f'| {g}.{orden[g]} | {nom(de)} | {nom(a)} | `{op}` |')
        out.append('')
    MD.write_text('\n'.join(out), encoding='utf-8')
    nuevos = sorted({r['cu'] for r in robustez}, key=lambda x: int(x[3:]))
    print('ok:', len(casos), 'casos,', len(robustez), 'robusteces,', len(espec), 'fichas;', ', '.join(nuevos))


if __name__ == '__main__':
    main()
