"""
P19 - Analítica con ML / CU-29  |  los dos modelos

Funciones puras: reciben arreglos y devuelven el modelo entrenado, sus
métricas y el resultado para el dashboard. No tocan la base; de eso se ocupa
el servicio. Así se prueban solas y con datos fijos.

1. DEMANDA SEMANAL (supervisado, regresión)
-------------------------------------------
Variable objetivo: las unidades que vende un producto en una semana.
Variables (selección y preprocesamiento):
  - la época del año, como seno y coseno de la semana (la semana 52 y la 1
    quedan cerca, cosa que un número del 1 al 52 no dice) y el mes;
  - lo que vendió antes: las semanas -1, -2 y -4 y la media de las últimas 4;
  - el precio, la categoría (codificada) y si el producto es de temporada.
Algoritmo: gradient boosting de árboles. Aprende relaciones no lineales sin
escalar las variables y entrena en segundos.
Validación: CORTE TEMPORAL. Se entrena con todo menos las últimas 12 semanas
y se mide sobre esas 12, que el modelo nunca vio, como pasaría en la tienda.
Mezclar al azar dejaría que el modelo «viera el futuro». Métricas: MAE, RMSE
y R², comparadas con una línea base ingenua («la semana que viene vende lo
mismo que esta»): si el modelo no le gana, no sirve.
Después se reentrena con todo y se predice la semana que viene.

2. SEGMENTOS DE CLIENTES (no supervisado, agrupamiento)
-------------------------------------------------------
Variables RFM: recencia (días desde la última compra), frecuencia (compras)
y monto (Bs). Frecuencia y monto se pasan por log1p (tienen colas largas) y
las tres se estandarizan: K-means mide distancias y, sin escalar, el monto en
bolivianos taparía a las otras dos.
Se prueba k de 2 a 6 y se elige el de mejor coeficiente de silueta (de -1 a
1: cuánto más cerca está cada cliente de su grupo que del vecino).
A cada grupo se le pone nombre mirando su centro: el de recencia más alta son
los dormidos, el de más compras y monto los fieles, etcétera.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import joblib
import numpy as np
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from app.modules.analitica.sinteticos import ProductoBase

SEMANAS_DE_PRUEBA = 12
#: Las semanas de historia que necesita una fila: la -4 es el rezago más largo.
REZAGO_MAXIMO = 4
VARIABLES_DEMANDA = (
    "semana_seno", "semana_coseno", "mes", "rezago_1", "rezago_2", "rezago_4",
    "media_4", "precio", "categoria", "de_temporada",
)
PARAMETROS_GB = {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05, "subsample": 0.9}
K_CANDIDATOS = range(2, 7)


@dataclass
class Entrenado:
    """Lo que devuelve un entrenamiento, listo para guardar."""

    modelo: bytes
    parametros: dict
    metricas: dict
    resultado: dict
    filas: int
    filas_reales: int
    filas_sinteticas: int
    extra: dict = field(default_factory=dict)


def _serializar(objeto) -> bytes:
    buffer = io.BytesIO()
    joblib.dump(objeto, buffer, compress=3)
    return buffer.getvalue()


def _deserializar(datos: bytes):
    return joblib.load(io.BytesIO(datos))


def _r(valor: float, digitos: int = 3) -> float:
    return round(float(valor), digitos)


# =====================================================================
#  1. Demanda semanal
# =====================================================================

def _fila(y: np.ndarray, t: int, lunes: date, p: ProductoBase, cat: int) -> list[float]:
    semana = lunes.isocalendar()[1]
    angulo = semana / 52 * 2 * math.pi
    return [
        math.sin(angulo), math.cos(angulo), lunes.month,
        y[t - 1], y[t - 2], y[t - 4], float(np.mean(y[t - 4:t])),
        p.precio, cat, 1.0 if p.con_temporada else 0.0,
    ]


def entrenar_demanda(
    productos: list[ProductoBase],
    sinteticas: np.ndarray,
    reales: np.ndarray,
    lunes: list[date],
    semilla: int,
) -> Entrenado:
    """Entrena, valida con corte temporal y predice la semana que viene.

    `sinteticas` y `reales` son matrices (productos × semanas) alineadas con
    `lunes`, el lunes de cada semana. La serie que aprende el modelo es la
    suma: lo real se apoya sobre el fondo sintético.
    """
    serie = sinteticas + reales
    n = serie.shape[1]
    categorias = sorted({p.categoria for p in productos})
    codigo = {c: i for i, c in enumerate(categorias)}
    corte = n - SEMANAS_DE_PRUEBA

    x_tr, y_tr, x_te, y_te, base_te, semana_te = [], [], [], [], [], []
    for i, p in enumerate(productos):
        y = serie[i]
        for t in range(REZAGO_MAXIMO, n):
            fila = _fila(y, t, lunes[t], p, codigo[p.categoria])
            if t < corte:
                x_tr.append(fila)
                y_tr.append(y[t])
            else:
                x_te.append(fila)
                y_te.append(y[t])
                base_te.append(y[t - 1])
                semana_te.append(t - corte)
    x_tr, y_tr, x_te, y_te = map(np.asarray, (x_tr, y_tr, x_te, y_te))

    validador = GradientBoostingRegressor(random_state=semilla, **PARAMETROS_GB)
    validador.fit(x_tr, y_tr)
    pred_te = np.clip(validador.predict(x_te), 0, None)
    mae = mean_absolute_error(y_te, pred_te)
    mae_base = mean_absolute_error(y_te, base_te)
    metricas = {
        "mae": _r(mae),
        "rmse": _r(math.sqrt(mean_squared_error(y_te, pred_te))),
        "r2": _r(r2_score(y_te, pred_te)),
        "mae_linea_base": _r(mae_base),
        "mejora_sobre_base_pct": _r((1 - mae / mae_base) * 100 if mae_base else 0, 1),
        "filas_entrenamiento": int(len(y_tr)),
        "filas_prueba": int(len(y_te)),
        "semanas_de_prueba": SEMANAS_DE_PRUEBA,
    }

    # La serie del gráfico «previsto vs real»: el total de cada semana de prueba.
    semana_te = np.asarray(semana_te)
    serie_validacion = [
        {
            "semana": lunes[corte + s].isoformat(),
            "real": _r(y_te[semana_te == s].sum(), 1),
            "prevista": _r(pred_te[semana_te == s].sum(), 1),
        }
        for s in range(SEMANAS_DE_PRUEBA)
    ]

    # Reentrenado con todo para predecir hacia adelante.
    final = GradientBoostingRegressor(random_state=semilla, **PARAMETROS_GB)
    final.fit(np.vstack([x_tr, x_te]), np.concatenate([y_tr, y_te]))
    proximo = lunes[-1] + timedelta(days=7)
    predicciones = []
    for i, p in enumerate(productos):
        y = np.append(serie[i], 0.0)  # el hueco de la semana que se predice
        fila = _fila(y, n, proximo, p, codigo[p.categoria])
        valor = max(0.0, float(final.predict([fila])[0]))
        media4 = float(np.mean(serie[i][-4:]))
        if media4 and valor > media4 * 1.1:
            tendencia = "SUBE"
        elif media4 and valor < media4 * 0.9:
            tendencia = "BAJA"
        else:
            tendencia = "ESTABLE"
        predicciones.append({
            "producto_id": p.id,
            "producto": p.nombre,
            "categoria": p.categoria,
            "prevista": _r(valor, 1),
            "ultima_semana": _r(serie[i][-1], 1),
            "media_4_semanas": _r(media4, 1),
            "reales_ultimas_4": _r(reales[i][-4:].sum(), 1),
            "tendencia": tendencia,
        })
    predicciones.sort(key=lambda f: f["prevista"], reverse=True)

    importancia = sorted(
        ({"variable": v, "peso": _r(w)} for v, w in zip(VARIABLES_DEMANDA, final.feature_importances_)),
        key=lambda f: f["peso"], reverse=True,
    )
    historia = [
        {"semana": lunes[t].isoformat(), "unidades": _r(serie[:, t].sum(), 1)}
        for t in range(max(0, n - 26), n)
    ]
    filas = len(productos) * (n - REZAGO_MAXIMO)
    filas_reales = int((reales[:, REZAGO_MAXIMO:] > 0).sum())
    return Entrenado(
        modelo=_serializar({"modelo": final, "variables": VARIABLES_DEMANDA,
                            "categorias": categorias}),
        parametros={
            "algoritmo": "GradientBoostingRegressor",
            "hiperparametros": PARAMETROS_GB,
            "variables": list(VARIABLES_DEMANDA),
            "validacion": f"corte temporal: últimas {SEMANAS_DE_PRUEBA} semanas",
            "semanas": n,
            "productos": len(productos),
            "semilla": semilla,
        },
        metricas=metricas,
        resultado={
            "semana_prevista": proximo.isoformat(),
            "predicciones": predicciones,
            "serie_validacion": serie_validacion,
            "historia": historia,
            "importancia": importancia,
            "total_previsto": _r(sum(f["prevista"] for f in predicciones), 1),
        },
        filas=filas,
        filas_reales=filas_reales,
        filas_sinteticas=filas - filas_reales,
    )


# =====================================================================
#  2. Segmentos de clientes
# =====================================================================

ACCIONES = {
    "Fieles de alto gasto": "Cuidarlos: preventa, envío sin costo y avisos de colección nueva.",
    "Dormidos (en riesgo)": "Reactivarlos con un cupón por tiempo limitado antes de perderlos.",
    "Nuevos": "Darles la bienvenida y una segunda compra con descuento.",
    "Ocasionales": "Subir la frecuencia con recomendaciones y ofertas de temporada.",
    "Regulares": "Mantener el contacto con novedades de sus categorías preferidas.",
    "Compradores medios": "Ofrecer combos para subir el ticket medio.",
}
_DE_RELLENO = ("Ocasionales", "Regulares", "Compradores medios")


def _preprocesar(rfm: np.ndarray) -> np.ndarray:
    return np.column_stack([rfm[:, 0], np.log1p(rfm[:, 1]), np.log1p(rfm[:, 2])])


def _nombrar(centros: np.ndarray) -> dict[int, str]:
    """Nombre de cada grupo según su centro en unidades reales (R, F, M)."""
    k = len(centros)
    libres = set(range(k))
    nombres: dict[int, str] = {}

    riesgo = max(libres, key=lambda c: centros[c, 0])
    nombres[riesgo] = "Dormidos (en riesgo)"
    libres.discard(riesgo)

    if libres:
        rango_f = np.argsort(np.argsort(centros[:, 1]))
        rango_m = np.argsort(np.argsort(centros[:, 2]))
        fieles = max(libres, key=lambda c: rango_f[c] + rango_m[c])
        nombres[fieles] = "Fieles de alto gasto"
        libres.discard(fieles)

    if libres:
        nuevos = min(libres, key=lambda c: (centros[c, 1], centros[c, 0]))
        if centros[nuevos, 1] <= 2.5:
            nombres[nuevos] = "Nuevos"
            libres.discard(nuevos)

    for i, c in enumerate(sorted(libres, key=lambda c: -centros[c, 2])):
        nombres[c] = _DE_RELLENO[i] if i < len(_DE_RELLENO) else f"Grupo {c + 1}"
    return nombres


def entrenar_segmentos(
    sinteticos: np.ndarray, reales: np.ndarray, semilla: int
) -> Entrenado:
    """K-means sobre RFM, con k elegido por silueta.

    `reales` es (clientes reales × 3) y puede venir vacío.
    """
    datos = np.vstack([sinteticos, reales]) if len(reales) else sinteticos
    escalador = StandardScaler()
    x = escalador.fit_transform(_preprocesar(datos))

    siluetas = []
    mejor = None
    for k in K_CANDIDATOS:
        km = KMeans(n_clusters=k, n_init=10, random_state=semilla).fit(x)
        s = silhouette_score(x, km.labels_)
        siluetas.append({"k": k, "silueta": _r(s), "inercia": _r(km.inertia_, 1)})
        if mejor is None or s > mejor[1]:
            mejor = (km, s)
    kmeans, silueta = mejor
    etiquetas = kmeans.labels_
    centros = np.array([datos[etiquetas == c].mean(axis=0) for c in range(kmeans.n_clusters)])
    nombres = _nombrar(centros)
    es_real = np.zeros(len(datos), dtype=bool)
    es_real[len(sinteticos):] = True

    segmentos = sorted(
        (
            {
                "grupo": int(c),
                "nombre": nombres[c],
                "accion": ACCIONES.get(nombres[c], "Analizar el grupo."),
                "clientes": int((etiquetas == c).sum()),
                "clientes_reales": int(((etiquetas == c) & es_real).sum()),
                "recencia_dias": _r(centros[c, 0], 1),
                "compras": _r(centros[c, 1], 1),
                "monto": _r(centros[c, 2], 2),
            }
            for c in range(kmeans.n_clusters)
        ),
        key=lambda s: -s["monto"],
    )
    return Entrenado(
        modelo=_serializar({"escalador": escalador, "kmeans": kmeans, "nombres": nombres}),
        parametros={
            "algoritmo": "KMeans",
            "hiperparametros": {"n_init": 10, "k_probados": list(K_CANDIDATOS)},
            "variables": ["recencia_dias", "log1p(compras)", "log1p(monto)"],
            "preprocesamiento": "log1p en frecuencia y monto; StandardScaler",
            "seleccion_de_k": "máximo coeficiente de silueta",
            "semilla": semilla,
        },
        metricas={
            "k": int(kmeans.n_clusters),
            "silueta": _r(silueta),
            "inercia": _r(kmeans.inertia_, 1),
            "siluetas": siluetas,
        },
        resultado={"segmentos": segmentos},
        filas=len(datos),
        filas_reales=int(len(reales)),
        filas_sinteticas=int(len(sinteticos)),
    )


def clasificar(modelo: bytes, rfm: np.ndarray) -> list[str]:
    """Con el modelo GUARDADO, el segmento de cada fila RFM (sin reentrenar)."""
    if not len(rfm):
        return []
    guardado = _deserializar(modelo)
    x = guardado["escalador"].transform(_preprocesar(rfm))
    return [guardado["nombres"][int(c)] for c in guardado["kmeans"].predict(x)]
