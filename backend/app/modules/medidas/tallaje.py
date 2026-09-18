"""CU-21 · Tallaje de referencia y como se decide si una prenda te queda.

Esto es **dato de dominio compartido**: lo usa el sembrado de `medida_talla` y
lo usa el servicio que recomienda la talla. Vive aca y no en el seed para que
no haya dos copias que se separen --- si la tabla del cuerpo cambiara en el
seed y no en el servicio, el vestidor recomendaria contra una referencia que ya
no es la que se sembro, y el sintoma seria «recomienda mal» sin mas pistas.

DE DONDE SALEN LOS NUMEROS DEL CUERPO
--------------------------------------
Tallaje boliviano publicado (Nativa Denim: cintura y cadera por talla), puntos
medios de cada rango. El busto no tiene dato boliviano publicado y se derivo
manteniendo el paso de 5 cm de la serie. Ver `app/db/seed_medidas.py` para el
detalle y para por que SHEIN no sirve como referencia fija.
"""

from __future__ import annotations

#: Medidas del CUERPO al que le corresponde cada talla, en centimetros:
#: (busto, cintura, cadera).
CUERPO_POR_TALLA: dict[str, tuple[float, float, float]] = {
    "XS": (82.0, 62.5, 89.0),
    "S": (87.0, 67.5, 95.0),
    "M": (92.0, 72.5, 101.0),
    "L": (97.0, 77.5, 107.0),
    "XL": (102.0, 82.5, 113.0),
    "XXL": (107.0, 87.5, 119.0),
    "XXXL": (112.0, 92.5, 125.0),
}

#: El orden de la serie. Sirve para calcular cuanto se aleja una talla de otra.
ORDEN = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]

#: Que tan lejos de la holgura de diseno puede estar una prenda y seguir
#: quedando bien, en centimetros de busto. Los tramos van de menos a mas holgado.
#:
#: Se comparan contra la HOLGURA DE DISENO de esa prenda, no contra un numero
#: fijo, porque cuanta holgura es la correcta depende de que sea la prenda: un
#: abrigo lleva 18 cm y una blusa 8, y los dos quedan bien. Con umbrales fijos,
#: todos los abrigos saldrian marcados como «holgado».
TRAMOS: list[tuple[float, str]] = [
    (-8.0, "NO_ENTRA"),
    (-3.0, "AJUSTADA"),
    (3.0, "A_TU_MEDIDA"),
    (8.0, "HOLGADA"),
]
ULTIMO_TRAMO = "MUY_HOLGADA"

#: Hasta donde se deja deformar la prenda en el vestidor.
#:
#: Sin tope, unas medidas mal cargadas ---centimetros donde iban pulgadas, un
#: cero que paso el CHECK--- dibujan una prenda absurda sobre el cuerpo. Con
#: tope, lo peor que pasa es que la prenda se vea algo mas grande o mas chica
#: de lo que deberia: sigue siendo una prenda.
FACTOR_MINIMO = 0.75
FACTOR_MAXIMO = 1.35


def holgura_de_diseno(busto_prenda: float, codigo_talla: str) -> float | None:
    """Cuanta holgura le puso el fabricante a esta prenda, en centimetros.

    Es la diferencia entre lo que mide la prenda y el cuerpo al que esa talla
    esta destinada. Por como se construye la tabla, da el mismo numero en todas
    las tallas de un producto --- la prenda y el cuerpo crecen al mismo paso ---
    asi que alcanza con mirar una.
    """
    cuerpo = CUERPO_POR_TALLA.get(codigo_talla)
    if cuerpo is None:
        return None
    return busto_prenda - cuerpo[0]


def clasificar(busto_prenda: float, busto_cuerpo: float, diseno: float) -> str:
    """Como le queda esta talla a este cuerpo."""
    desvio = (busto_prenda - busto_cuerpo) - diseno
    for limite, etiqueta in TRAMOS:
        if desvio < limite:
            return etiqueta
    return ULTIMO_TRAMO


def factor_de_ancho(busto_prenda: float, busto_cuerpo: float, diseno: float) -> float:
    """Cuanto mas ancha que «la que te queda» hay que dibujar esta talla.

    1.0 es la talla que le corresponde al cuerpo: se dibuja como se dibujaba
    antes de que existieran las medidas. Por debajo se ve ajustada, por encima
    holgada --- que es todo el punto: **hasta hoy la XS y la XXL se veian
    identicas en pantalla**.
    """
    ideal = busto_cuerpo + diseno
    if ideal <= 0:
        return 1.0
    return max(FACTOR_MINIMO, min(FACTOR_MAXIMO, busto_prenda / ideal))
