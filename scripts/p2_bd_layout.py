"""Disposición de cajas para los diagramas del 3.1 y el 3.5.

EA dibuja cada asociación como una recta entre los centros de las dos cajas.
Con las cajas puestas a mano en columnas, esas rectas atravesaban otras cajas
y se cruzaban por todos lados. Acá se reparten las cajas en columnas (cada
columna, apilada de arriba hacia abajo) y se busca por recocido simulado el
reparto que menos castiga:
  - una recta que atraviesa una caja que no es la suya;
  - dos rectas que se cruzan;
  - el largo de las rectas.
Determinista: la semilla es fija, así que los mismos datos dan el mismo dibujo.
"""
import math
import random

HUECO_X, HUECO_Y = 130, 80   # aire entre columnas y entre cajas (para los rótulos)
X0, Y0 = 30, -40             # esquina del diagrama (EA: y crece hacia arriba)


def _posiciones(columnas, tam):
    pos, x = {}, X0
    for col in columnas:
        if not col:
            continue
        ancho = max(tam[n][0] for n in col)
        y = Y0
        for n in col:
            w, h = tam[n]
            pos[n] = (x + (ancho - w) / 2, y, w, h)   # centrada en su columna
            y -= h + HUECO_Y
        x += ancho + HUECO_X
    return pos


def _centro(p):
    l, t, w, h = p
    return l + w / 2, t - h / 2


def _cruza(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (orient(a, b, c) * orient(a, b, d) < 0) and (orient(c, d, a) * orient(c, d, b) < 0)


def _atraviesa(p, q, caja, margen=12):
    l, t, w, h = caja
    x0, x1, y0, y1 = l - margen, l + w + margen, t - h - margen, t + margen
    # Liang-Barsky
    dx, dy = q[0] - p[0], q[1] - p[1]
    u0, u1 = 0.0, 1.0
    for pp, qq in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pp == 0:
            if qq < 0:
                return False
        else:
            r = qq / pp
            if pp < 0:
                u0 = max(u0, r)
            else:
                u1 = min(u1, r)
            if u0 > u1:
                return False
    return True


def costo(columnas, tam, aristas):
    pos = _posiciones(columnas, tam)
    seg = [(a, b, _centro(pos[a]), _centro(pos[b])) for a, b in aristas if a != b]
    c = 0.0
    for a, b, p, q in seg:
        c += math.dist(p, q) / 100
        for n, caja in pos.items():
            if n != a and n != b and _atraviesa(p, q, caja):
                c += 60
    for i in range(len(seg)):
        a, b, p, q = seg[i]
        for j in range(i + 1, len(seg)):
            e, f, r, s = seg[j]
            if len({a, b, e, f}) == 4 and _cruza(p, q, r, s):
                c += 6
    # Que no quede muy apaisado ni muy alto: el Word es vertical.
    ancho = max(l + w for l, _, w, _ in pos.values())
    alto = -min(t - h for _, t, _, h in pos.values())
    c += max(0, ancho / max(alto, 1) - 2.2) * 40
    return c


def maquetar(tam, aristas, n_columnas, max_por_columna, iteraciones=6000, semilla=7, inicial=None):
    """tam: {nombre: (ancho, alto)}; aristas: [(a, b)]. Devuelve {nombre: [l, t, ancho, alto]}."""
    rnd = random.Random(semilla)
    if inicial:
        cols = [list(c) for c in inicial] + [[] for _ in range(max(0, n_columnas - len(inicial)))]
    else:
        nombres = list(tam)
        cols = [nombres[i::n_columnas] for i in range(n_columnas)]
    actual = costo(cols, tam, aristas)
    mejor, mejor_cols = actual, [list(c) for c in cols]
    temp = 40.0
    for it in range(iteraciones):
        nuevo = [list(c) for c in cols]
        if rnd.random() < 0.5:
            # mover una caja a otra columna (o a otro lugar de la suya)
            origen = rnd.choice([i for i, c in enumerate(nuevo) if c])
            n = nuevo[origen].pop(rnd.randrange(len(nuevo[origen])))
            destino = rnd.randrange(len(nuevo))
            if len(nuevo[destino]) >= max_por_columna:
                continue
            nuevo[destino].insert(rnd.randint(0, len(nuevo[destino])), n)
        else:
            # intercambiar dos cajas
            todas = [(i, j) for i, c in enumerate(nuevo) for j in range(len(c))]
            (i1, j1), (i2, j2) = rnd.sample(todas, 2)
            nuevo[i1][j1], nuevo[i2][j2] = nuevo[i2][j2], nuevo[i1][j1]
        c = costo(nuevo, tam, aristas)
        if c < actual or rnd.random() < math.exp((actual - c) / temp):
            cols, actual = nuevo, c
            if c < mejor:
                mejor, mejor_cols = c, [list(x) for x in nuevo]
        temp = max(0.5, temp * 0.999)
    pos = _posiciones([c for c in mejor_cols if c], tam)
    return {n: [round(v) for v in p] for n, p in pos.items()}, mejor


def maquetar_mejor(tam, aristas, semillas=(7, 11, 23, 41), **kw):
    """Corre maquetar() con varias semillas y se queda con la de menor costo."""
    return min((maquetar(tam, aristas, semilla=s, **kw) for s in semillas), key=lambda r: r[1])
