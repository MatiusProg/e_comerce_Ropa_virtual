"""
P19 - Analítica con ML / CU-29  |  generación de datos sintéticos

POR QUÉ HACEN FALTA
-------------------
Una tienda recién suscrita tiene pocas semanas de ventas: con eso ningún
modelo aprende nada. El enunciado lo prevé (8.4): se genera un conjunto de
datos artificiales para entrenar y evaluar, y encima se suman los datos reales
de la empresa. A medida que la tienda vende, lo real pesa cada vez más.

REPRODUCIBLE
------------
Todo sale de un generador con semilla: la misma semilla y los mismos productos
dan exactamente los mismos datos. Así una métrica se puede volver a obtener y
las pruebas no dependen del azar.

QUÉ FORMA TIENEN
----------------
- Demanda semanal por producto: un nivel base que baja con el precio, una
  estacionalidad anual propia de la categoría (las camperas en invierno, las
  poleras en verano), una tendencia suave, el pico de fin de año y ruido de
  Poisson, que es como se reparten las cuentas de unidades.
- Clientes: cuatro perfiles (fieles de alto gasto, ocasionales, nuevos y
  dormidos) con su recencia, frecuencia y monto. El modelo NO recibe el
  perfil: tiene que encontrar los grupos solo (no supervisado).
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np

SEMILLA = 2026
SEMANAS = 104
CLIENTES_SINTETICOS = 240


@dataclass(frozen=True)
class ProductoBase:
    """Lo que el generador necesita saber de un producto."""

    id: int | None
    nombre: str
    categoria: str
    precio: float
    con_temporada: bool


def productos_de_relleno(cantidad: int = 20) -> list[ProductoBase]:
    """Para la empresa que todavía no cargó productos: un catálogo inventado."""
    categorias = ("Poleras", "Pantalones", "Vestidos", "Camperas")
    return [
        ProductoBase(
            id=None,
            nombre=f"Prenda sintética {i + 1}",
            categoria=categorias[i % len(categorias)],
            precio=float(80 + (i * 37) % 420),
            con_temporada=i % 3 == 0,
        )
        for i in range(cantidad)
    ]


def _fase_de_categoria(categoria: str) -> float:
    """La semana del año en que la categoría vende más. Fija por nombre."""
    return (zlib.crc32(categoria.lower().encode()) % 52) / 52 * 2 * np.pi


def demanda_semanal(
    productos: list[ProductoBase],
    semanas_del_anio: np.ndarray,
    semilla: int = SEMILLA,
) -> np.ndarray:
    """Matriz (productos × semanas) de unidades vendidas sintéticas.

    `semanas_del_anio` es la semana ISO (1..53) de cada columna, para que la
    estacionalidad caiga en la época del año correcta.
    """
    rng = np.random.default_rng(semilla)
    n = len(semanas_del_anio)
    t = np.arange(n)
    angulo = semanas_del_anio / 52 * 2 * np.pi
    filas = []
    for p in productos:
        base = rng.uniform(4, 10) * (150 / max(p.precio, 30)) ** 0.5
        amplitud = rng.uniform(0.2, 0.5) * (1.4 if p.con_temporada else 1.0)
        estacion = 1 + amplitud * np.cos(angulo - _fase_de_categoria(p.categoria))
        tendencia = 1 + rng.uniform(-0.002, 0.005) * t
        fin_de_anio = np.where(semanas_del_anio >= 49, 1.4, 1.0)
        media = np.clip(base * estacion * tendencia * fin_de_anio, 0.2, None)
        filas.append(rng.poisson(media))
    return np.array(filas, dtype=float).reshape(len(productos), n)


#: nombre, proporción, recencia (días), compras, ticket medio (Bs)
_PERFILES = (
    ("Fieles de alto gasto", 0.20, (1, 30), (8, 16), (280, 480)),
    ("Ocasionales", 0.35, (25, 120), (2, 5), (130, 260)),
    ("Nuevos", 0.25, (1, 25), (1, 2), (100, 300)),
    ("Dormidos", 0.20, (150, 400), (1, 4), (120, 300)),
)


def clientes_rfm(cantidad: int = CLIENTES_SINTETICOS, semilla: int = SEMILLA) -> np.ndarray:
    """Matriz (clientes × 3): recencia en días, compras y monto total."""
    rng = np.random.default_rng(semilla + 1)
    filas = []
    for _, proporcion, rec, frec, ticket in _PERFILES:
        k = max(1, round(cantidad * proporcion))
        recencia = rng.uniform(*rec, size=k)
        compras = rng.integers(frec[0], frec[1] + 1, size=k)
        monto = compras * rng.uniform(*ticket, size=k)
        filas.append(np.column_stack([recencia, compras, monto]))
    return np.vstack(filas)
