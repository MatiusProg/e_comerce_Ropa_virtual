"""
P19 - Analítica con ML / Aporte propio  |  detección de anomalías

Funciones puras, como `modelos.py`: reciben una matriz de variables y
devuelven el modelo entrenado, qué filas marcó y POR QUÉ. No tocan la base.

3. ANOMALÍAS EN CAJA Y DEVOLUCIONES (no supervisado, Isolation Forest)
---------------------------------------------------------------------
Nadie etiqueta un turno como «sospechoso»: no hay variable objetivo. El
Isolation Forest arma muchos árboles que parten los datos al azar (una
variable al azar, un corte al azar entre su mínimo y su máximo). Una fila
rara queda AISLADA en pocos cortes; una normal necesita muchos, porque se
parece a todas las demás. El largo medio del camino hasta aislarla da el
puntaje: cerca de 1 es muy anómala, alrededor de 0,5 o menos es normal.

`contamination` es la proporción que se espera marcar (5 %). No se escala:
cada corte es dentro del rango de UNA variable, así que los bolivianos no
tapan a los conteos como pasaría con una distancia.

La EXPLICACIÓN no sale del modelo (el bosque no dice por qué), sino de los
datos: para cada fila marcada se mide cuánto se aparta cada variable de la
mediana, en unidades de su dispersión robusta (MAD), y se cuentan las dos que
más se apartan. Así el administrador lee «diferencia de arqueo 8× la
habitual» y no un número.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from app.modules.analitica.modelos import _r, _serializar

CONTAMINACION = 0.05
PARAMETROS_IF = {"n_estimators": 200, "max_samples": "auto"}
#: Debajo de esto el bosque no tiene con qué comparar.
MIN_TURNOS = 20
MIN_DEVOLUCIONES = 15
#: Cuántas variables se nombran en la explicación.
MOTIVOS = 2
#: Desvío robusto mínimo para nombrar una variable.
UMBRAL_DESVIO = 2.0


@dataclass(frozen=True)
class Variable:
    clave: str
    nombre: str
    #: "bs", "pct", "num" u "h": cómo se escribe el valor.
    unidad: str


VARIABLES_TURNO = (
    Variable("diferencia_arqueo", "diferencia de arqueo", "bs"),
    Variable("devoluciones", "devoluciones en el turno", "num"),
    Variable("monto_devuelto", "monto devuelto", "bs"),
    Variable("descuento_pct", "descuento sobre lo vendido", "pct"),
    Variable("efectivo_pct", "parte cobrada en efectivo", "pct"),
    Variable("ventas", "ventas del turno", "num"),
    Variable("duracion_h", "duración del turno", "h"),
)

VARIABLES_DEVOLUCION = (
    Variable("valor", "valor devuelto", "bs"),
    Variable("horas_desde_venta", "tiempo desde la venta", "h"),
    Variable("tasa_cajero", "devoluciones por venta de quien la atendió", "pct"),
    Variable("viene_de_cambio", "prenda que ya venía de un cambio", "num"),
    Variable("es_cambio", "es un cambio", "num"),
    Variable("hora", "hora del día", "hora"),
)


@dataclass
class Detectado:
    modelo: IsolationForest
    #: Para cada fila: si quedó marcada, su puntaje y su explicación.
    marcadas: list[bool]
    puntajes: list[float]
    explicaciones: list[str]
    medianas: dict[str, float]


def _formatear(valor: float, unidad: str) -> str:
    if unidad == "bs":
        return f"Bs {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if unidad == "pct":
        return f"{valor * 100:.0f} %"
    if unidad == "h":
        return f"{valor:.1f} h" if valor < 48 else f"{valor / 24:.0f} días"
    if unidad == "hora":
        return f"{int(valor) % 24:02d}:00"
    return f"{valor:g}"


def _frase(v: Variable, x: float, mediana: float) -> str:
    if v.unidad == "num" and v.clave in ("viene_de_cambio", "es_cambio"):
        return v.nombre if x >= 0.5 else f"no {v.nombre}"
    habitual = _formatear(mediana, v.unidad)
    valor = _formatear(x, v.unidad)
    if v.unidad == "hora":
        return f"{v.nombre} fuera de lo habitual ({valor}; lo habitual es {habitual})"
    veces = x / mediana if mediana > 0 else 0.0
    if veces >= 1.5:
        cifra = f"{veces:.0f}" if veces >= 2 else f"{veces:.1f}".replace(".", ",")
        return f"{v.nombre} {cifra}× la habitual ({valor} contra {habitual})"
    if x > mediana:
        return f"{v.nombre} alta: {valor} (lo habitual es {habitual})"
    return f"{v.nombre} baja: {valor} (lo habitual es {habitual})"


def explicar(x: np.ndarray, matriz: np.ndarray, variables: tuple[Variable, ...]) -> str:
    """Las variables de `x` que más se apartan de la mediana, en castellano."""
    medianas = np.median(matriz, axis=0)
    mad = np.median(np.abs(matriz - medianas), axis=0) * 1.4826
    # Si la mitad de los datos son iguales la MAD es 0: se usa el desvío estándar
    # y, si también es 0, un piso para no dividir por cero.
    respaldo = np.where(matriz.std(axis=0) > 0, matriz.std(axis=0), 1.0)
    escala = np.where(mad > 1e-9, mad, respaldo)
    desvios = np.abs(x - medianas) / escala
    orden = np.argsort(-desvios)
    frases = [
        _frase(variables[i], float(x[i]), float(medianas[i]))
        for i in orden[:MOTIVOS]
        if desvios[i] >= UMBRAL_DESVIO
    ]
    if not frases:  # marcada por la combinación, no por una sola variable
        i = int(orden[0])
        frases = [_frase(variables[i], float(x[i]), float(medianas[i]))]
    texto = "; ".join(frases)
    return texto[:1].upper() + texto[1:]


def detectar(matriz: np.ndarray, variables: tuple[Variable, ...], semilla: int) -> Detectado:
    """Entrena el bosque sobre `matriz` y marca las filas anómalas."""
    modelo = IsolationForest(
        contamination=CONTAMINACION, random_state=semilla, **PARAMETROS_IF
    ).fit(matriz)
    marcadas = modelo.predict(matriz) == -1
    # score_samples devuelve -s(x): se le da la vuelta para que 1 sea lo más raro.
    puntajes = -modelo.score_samples(matriz)
    explicaciones = [
        explicar(fila, matriz, variables) if m else "" for fila, m in zip(matriz, marcadas)
    ]
    medianas = {v.clave: _r(m, 2) for v, m in zip(variables, np.median(matriz, axis=0))}
    return Detectado(
        modelo=modelo,
        marcadas=[bool(m) for m in marcadas],
        puntajes=[_r(p) for p in puntajes],
        explicaciones=explicaciones,
        medianas=medianas,
    )


def serializar(modelos: dict) -> bytes:
    return _serializar(modelos)
