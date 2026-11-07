"""
P19 - Analítica con ML / CU-29 y CU-30  |  capa: servicio

CU-29 ENTRENAR: junta los datos reales de la empresa, los completa con los
sintéticos, entrena los dos modelos y guarda cada entrenamiento.
CU-30 CONSULTAR: arma el dashboard con lo último que se entrenó, y clasifica a
los clientes de HOY con el modelo de segmentos guardado (sin reentrenar).

Integración con el sistema: el modelo no ve la base. El servicio le pasa
arreglos numéricos ya filtrados por el RLS de la empresa de la sesión.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy.orm import Session

from app.core import tiempo
from app.modules.analitica import modelos, repository as repo, sinteticos
from app.modules.analitica.models import ModeloAnalitica
from app.modules.reportes.exportador import Tabla


class ErrorDeAnalitica(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


def _lunes_de(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


def _semanas(semanas: int) -> list[date]:
    """Los lunes de las `semanas` semanas COMPLETAS que terminan antes de esta."""
    ultimo = _lunes_de(tiempo.hoy()) - timedelta(days=7)
    return [ultimo - timedelta(weeks=semanas - 1 - i) for i in range(semanas)]


def _productos(db: Session) -> list[sinteticos.ProductoBase]:
    filas = repo.productos_activos(db)
    if not filas:
        return sinteticos.productos_de_relleno()
    return [
        sinteticos.ProductoBase(
            id=f.id, nombre=f.nombre, categoria=f.categoria,
            precio=float(f.precio_base), con_temporada=f.temporada_id is not None,
        )
        for f in filas
    ]


def _matriz_real(
    db: Session, productos: list[sinteticos.ProductoBase], lunes: list[date]
) -> np.ndarray:
    indice_p = {p.id: i for i, p in enumerate(productos) if p.id is not None}
    indice_s = {d: j for j, d in enumerate(lunes)}
    real = np.zeros((len(productos), len(lunes)))
    desde = datetime.combine(lunes[0], datetime.min.time(), tzinfo=tiempo.BOLIVIA)
    for fila in repo.ventas_semanales(db, desde):
        semana = fila.semana.date() if isinstance(fila.semana, datetime) else fila.semana
        i, j = indice_p.get(fila.producto_id), indice_s.get(semana)
        if i is not None and j is not None:
            real[i, j] += float(fila.unidades)
    return real


def _rfm_real(db: Session) -> tuple[list, np.ndarray]:
    ahora = tiempo.ahora()
    filas = repo.rfm_de_clientes(db)
    rfm = np.array(
        [[max(0.0, (ahora - f.ultima).total_seconds() / 86400), float(f.compras), float(f.monto)]
         for f in filas]
    ).reshape(len(filas), 3)
    return filas, rfm


def _guardar(db: Session, tipo: str, e: modelos.Entrenado, inicio: float,
             usuario_id: int | None) -> ModeloAnalitica:
    return repo.guardar(db, ModeloAnalitica(
        tipo=tipo, parametros=e.parametros, metricas=e.metricas, resultado=e.resultado,
        filas_entrenamiento=e.filas, filas_reales=e.filas_reales,
        filas_sinteticas=e.filas_sinteticas,
        duracion_ms=int((time.perf_counter() - inicio) * 1000),
        modelo=e.modelo, entrenado_por=usuario_id,
    ))


# =====================================================================
#  CU-29 · Entrenar
# =====================================================================

def entrenar(db: Session, usuario_id: int | None, semilla: int = sinteticos.SEMILLA) -> dict:
    """Entrena los dos modelos y deja guardados sus entrenamientos."""
    inicio = time.perf_counter()
    productos = _productos(db)
    lunes = _semanas(sinteticos.SEMANAS)
    semana_iso = np.array([d.isocalendar()[1] for d in lunes])
    sint = sinteticos.demanda_semanal(productos, semana_iso, semilla)
    real = _matriz_real(db, productos, lunes)
    demanda = modelos.entrenar_demanda(productos, sint, real, lunes, semilla)
    _guardar(db, "DEMANDA", demanda, inicio, usuario_id)

    inicio = time.perf_counter()
    _, rfm = _rfm_real(db)
    segmentos = modelos.entrenar_segmentos(
        sinteticos.clientes_rfm(semilla=semilla), rfm, semilla
    )
    _guardar(db, "SEGMENTOS", segmentos, inicio, usuario_id)
    db.commit()
    return resumen(db)


# =====================================================================
#  CU-30 · Consultar
# =====================================================================

def _entrenamiento(m: ModeloAnalitica | None) -> dict | None:
    if m is None:
        return None
    return {
        "id": m.id,
        "entrenado_en": m.entrenado_en,
        "parametros": m.parametros,
        "metricas": m.metricas,
        "filas_entrenamiento": m.filas_entrenamiento,
        "filas_reales": m.filas_reales,
        "filas_sinteticas": m.filas_sinteticas,
        "duracion_ms": m.duracion_ms,
    }


def resumen(db: Session) -> dict:
    """Todo lo que muestra el dashboard: métricas, predicciones y segmentos."""
    demanda = repo.ultimo(db, "DEMANDA")
    segmentos = repo.ultimo(db, "SEGMENTOS")
    return {
        "entrenado": demanda is not None and segmentos is not None,
        "demanda": _entrenamiento(demanda),
        "segmentos": _entrenamiento(segmentos),
        "predicciones": demanda.resultado if demanda else None,
        "grupos": segmentos.resultado["segmentos"] if segmentos else [],
    }


def historial(db: Session) -> list[dict]:
    return [dict(f._mapping) for f in repo.historial(db)]


def clientes_por_segmento(db: Session) -> list[dict]:
    """Los clientes reales de hoy, cada uno en su segmento (modelo guardado)."""
    modelo = repo.ultimo(db, "SEGMENTOS")
    if modelo is None:
        raise ErrorDeAnalitica("Todavía no se entrenaron los modelos.", 409)
    filas, rfm = _rfm_real(db)
    nombres = modelos.clasificar(modelo.modelo, rfm)
    clientes = [
        {
            "cliente_id": f.cliente_id,
            "cliente": f"{f.nombres} {f.apellidos}".strip(),
            "segmento": nombre,
            "recencia_dias": round(float(r[0]), 1),
            "compras": int(r[1]),
            "monto": round(float(r[2]), 2),
        }
        for f, r, nombre in zip(filas, rfm, nombres)
    ]
    clientes.sort(key=lambda c: -c["monto"])
    return clientes


def reporte(db: Session) -> Tabla:
    """El reporte inteligente: predicciones con sus métricas, para PDF o Excel."""
    datos = resumen(db)
    if not datos["entrenado"]:
        raise ErrorDeAnalitica("Todavía no se entrenaron los modelos.", 409)
    m = datos["demanda"]["metricas"]
    s = datos["segmentos"]["metricas"]
    pred = datos["predicciones"]
    grupos = ", ".join(f"{g['nombre']} ({g['clientes']})" for g in datos["grupos"])
    return Tabla(
        titulo="Analítica · Demanda prevista para la semana que viene",
        encabezados=["Producto", "Categoría", "Prevista (u.)", "Última semana",
                     "Media 4 semanas", "Tendencia"],
        filas=[
            [f["producto"], f["categoria"], f["prevista"], f["ultima_semana"],
             f["media_4_semanas"], f["tendencia"].capitalize()]
            for f in pred["predicciones"]
        ],
        subtitulos=[
            f"Semana del {date.fromisoformat(pred['semana_prevista']).strftime('%d/%m/%Y')} · "
            f"entrenado el {tiempo.formatear(datos['demanda']['entrenado_en'])}",
            f"Validación (últimas {m['semanas_de_prueba']} semanas): MAE {m['mae']} · "
            f"RMSE {m['rmse']} · R² {m['r2']} · {m['mejora_sobre_base_pct']} % mejor que la línea base",
            f"Segmentos de clientes (K-means, k={s['k']}, silueta {s['silueta']}): {grupos}",
        ],
        total=["Total", "", pred["total_previsto"], "", "", ""],
    )
