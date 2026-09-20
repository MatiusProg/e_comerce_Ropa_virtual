"""La hora del negocio es la de Bolivia, no la del servidor.

DE QUIEN ES `app/core/tiempo.py`
---------------------------------
**El modulo lo escribio Karen** (PR #58), que reporto el defecto. Este
archivo prueba lo que ella cubrio mas los sitios que quedaron afuera ---el
periodo de los reportes, que es el peor de todos--- y `fin_del_dia()`, que
se agrego para eso.

QUE SE ESTA PROBANDO, Y POR QUE NO ES UN DETALLE
-------------------------------------------------
Todas las columnas de fecha son `TIMESTAMPTZ`, asi que **lo guardado siempre
estuvo bien**: un `timestamptz` guarda un instante absoluto. El defecto
estaba en quien decide **que dia es hoy** y en donde se cortan los dias.

Railway corre en UTC. A las 21:00 de un martes en Santa Cruz, para el
servidor ya es miercoles. Con la tienda abierta hasta las 20:00, eso hacia
que:

- el reporte «del martes» corriera de las 20:00 del lunes a las 20:00 del
  martes, **dejando la ultima hora de ventas en el reporte del miercoles**;
- el «vendido hoy» del tablero sumara dos dias distintos entre las 20:00 y
  la medianoche;
- una venta de las 21:00 saliera numerada `VB-<miercoles>-XXXX`.

Y ninguno de los tres avisaba: el numero salia menor y se leia como bueno.

LO QUE ESTAS PRUEBAS NO TOCAN
------------------------------
Los **instantes** siguen en UTC a proposito: vencimiento de token,
`cerrado_en` de un turno, franja de reserva, vigencia de la recomendacion de
CU-33. Un instante no tiene zona, y convertirlo solo agrega una oportunidad
de equivocarse. Aca solo se prueba lo que es *un dia del calendario* o *una
fecha que se imprime*.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.core import tiempo


# --- El desfase, en abstracto ----------------------------------------------


def test_la_zona_es_la_de_bolivia() -> None:
    assert tiempo.BOLIVIA.utcoffset(None) == timedelta(hours=-4)


def test_EL_DIA_EMPIEZA_A_MEDIANOCHE_EN_BOLIVIA_no_en_utc() -> None:
    """Es el corazon del arreglo.

    La medianoche boliviana del 20 son las 04:00 UTC del 20. Cortar en
    00:00 UTC arranca el dia cuatro horas antes: a las 20:00 del 19.
    """
    inicio = tiempo.inicio_del_dia(date(2026, 9, 20))

    assert inicio.isoformat() == "2026-09-20T04:00:00+00:00"
    assert tiempo.en_bolivia(inicio).isoformat() == "2026-09-20T00:00:00-04:00"


def test_el_fin_del_dia_es_abierto_y_cubre_la_noche_entera() -> None:
    """`fin_del_dia` se agrego el 20/09 para el periodo de los reportes.

    `<= 30` deja fuera todo lo que paso ese dia despues de medianoche: es el
    defecto clasico de los reportes por fecha, y por eso el limite derecho
    es el comienzo del dia siguiente.
    """
    fin = tiempo.fin_del_dia(date(2026, 9, 20))
    assert fin == tiempo.inicio_del_dia(date(2026, 9, 21))

    ultima_venta = datetime(2026, 9, 20, 23, 59, 59, tzinfo=tiempo.BOLIVIA)
    assert tiempo.inicio_del_dia(date(2026, 9, 20)) <= ultima_venta < fin


def test_LAS_NUEVE_DE_LA_NOCHE_TODAVIA_ES_HOY() -> None:
    """El caso exacto que estaba roto.

    Las 21:00 del 20 en Bolivia son las 01:00 del 21 en UTC. El servidor
    decia «21» y la tienda decia «20»; manda la tienda.
    """
    de_noche = datetime(2026, 9, 21, 1, 0, tzinfo=timezone.utc)

    assert de_noche.date() == date(2026, 9, 21)
    assert tiempo.en_bolivia(de_noche).date() == date(2026, 9, 20)


def test_ahora_devuelve_un_INSTANTE_en_utc_no_el_dia_boliviano() -> None:
    """La distincion que define el modulo de Karen.

    `ahora()` responde «en que instante paso esto» y va a una columna
    `timestamptz`. El dia del calendario se pregunta con `hoy()`; sacarlo de
    aca con `.date()` daria el dia UTC --- que entre las 20:00 y la
    medianoche es el de manana.
    """
    assert tiempo.ahora().tzinfo == timezone.utc


def test_un_instante_sin_zona_se_lee_como_utc_no_como_hora_local() -> None:
    """Suponer hora local seria suponer que el servidor esta en Bolivia ---
    que es justo lo que no pasa."""
    sin_zona = datetime(2026, 9, 21, 1, 0)
    assert tiempo.en_bolivia(sin_zona).isoformat() == "2026-09-20T21:00:00-04:00"


def test_lo_que_se_imprime_sale_en_hora_boliviana() -> None:
    assert tiempo.formatear(datetime(2026, 9, 21, 1, 30, tzinfo=timezone.utc)) == (
        "20/09/2026 21:30"
    )


# --- Y que lo use quien tiene que usarlo ------------------------------------


def test_EL_PERIODO_DEL_REPORTE_CORTA_EN_HORA_BOLIVIANA() -> None:
    """Sin esto, «el reporte del 20» empieza a las 20:00 del 19.

    Se comprueba contra el servicio de verdad y no contra el modulo de
    tiempo: lo que estaba mal no era el calculo de la zona, era que el
    reporte no lo usaba.
    """
    from app.modules.reportes.reportes_service import _rango

    inicio, fin = _rango(date(2026, 9, 20), date(2026, 9, 20))

    assert inicio.astimezone(timezone.utc).isoformat() == "2026-09-20T04:00:00+00:00"
    assert fin.astimezone(timezone.utc).isoformat() == "2026-09-21T04:00:00+00:00"

    # Una venta de las 21:00 del 20, que es cuando la tienda esta cerrando:
    # tiene que caer DENTRO del reporte del 20.
    cierre = datetime(2026, 9, 20, 21, 0, tzinfo=tiempo.BOLIVIA)
    assert inicio <= cierre < fin

    # Y una de las 21:00 del 19 tiene que quedar FUERA. Antes entraba: el
    # periodo arrancaba a las 20:00 de ese dia.
    la_vispera = datetime(2026, 9, 19, 21, 0, tzinfo=tiempo.BOLIVIA)
    assert la_vispera < inicio


def test_el_periodo_del_tablero_corta_igual_que_el_del_reporte() -> None:
    """Dos pantallas que dicen «septiembre» tienen que sumar lo mismo.

    Si el tablero corta en UTC y el reporte en hora boliviana, el
    Administrador ve dos totales distintos del mismo mes y no hay forma de
    saber cual creer.
    """
    from app.modules.reportes.reportes_service import _rango
    from app.modules.reportes.tablero_service import _limites

    assert _limites(date(2026, 9, 1), date(2026, 9, 30)) == _rango(
        date(2026, 9, 1), date(2026, 9, 30)
    )
