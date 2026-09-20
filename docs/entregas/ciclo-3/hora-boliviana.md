# La hora del negocio es la de Bolivia

> **Escrita el 20/09/2026.** No es un caso de uso: es un defecto que cruzaba
> reportes, tablero, ventas, promociones y temporadas.

---

## 1. Lo guardado siempre estuvo bien

**Todas** las columnas de fecha del sistema son `TIMESTAMPTZ`
(`DateTime(timezone=True)`), y no hay ni una `DateTime()` sin zona en las
migraciones. Se verificó columna por columna.

Un `timestamptz` **no guarda «una hora», guarda un instante absoluto**:
PostgreSQL lo normaliza internamente y la zona se aplica al leer.

> **Por eso este arreglo no lleva ningún script en la base — y correr uno
> habría sido el error.** Un `UPDATE ... - interval '4 hours'` le restaría
> cuatro horas a instantes que ya eran los correctos, y ahí sí quedarían mal
> para siempre.

## 2. Lo que estaba mal: quién decide qué día es hoy

`date.today()` toma el reloj del servidor, y **Railway corre en UTC**. A las
21:00 de un martes en Santa Cruz, para el servidor ya es miércoles.

Con la tienda abierta hasta las 20:00, eso significa que **las últimas cuatro
horas de cada día caen del lado equivocado**.

### Ya estaba descubierto, y el arreglo se había quedado en un solo lugar

`promociones_service.py` tenía desde CU-12 la constante `BOLIVIA` y este
comentario:

> *Railway corre en UTC y ahí el día cambia a las 20:00 hora boliviana. Con
> `date.today()`, una promoción que termina «el 30» dejaría de aplicar con
> cuatro horas de tienda todavía abierta y clientes adentro.*

El razonamiento era correcto y **no se había llevado a ningún otro lado**.

## 3. Los cinco sitios donde mordía

| | Dónde | Qué pasaba |
|---|---|---|
| 🔴 | `reportes_service._rango()` | Construía el período con `tzinfo=timezone.utc`. «El reporte del 20» corría de las **20:00 del 19** a las **20:00 del 20**: la última hora de ventas de cada día aparecía en el reporte del día siguiente. |
| 🔴 | `tablero_repository.ventas_de_hoy()` | «Hoy» arrancaba a las 00:00 UTC = **20:00 de ayer**. Entre esa hora y la medianoche, el «vendido hoy» sumaba dos días distintos. |
| 🟠 | `ventas/service.py`, `pos/service.py` | El correlativo lleva `%Y%m%d`: una venta de las 21:00 del 20 salía numerada `VB-<21>-XXXX`. El número que el cliente tiene en la mano no coincidía con el día del arqueo. |
| 🟠 | `reportes_service.generar()` | `datetime.now()` **sin zona ninguna** —hora local del servidor— impresa como «Saldos al …» en la cabecera del reporte de inventario. |
| 🟡 | `reportes_router.pedir_por_voz()` | El `hoy` que recibe el intérprete de CU-35: «este mes» y «hoy» se resolvían en UTC. |

Y varios menores: temporada vigente, nombre del archivo descargado,
«Descargado el …» del historial, las fechas por omisión de alta y baja de
empleado.

**Ninguno avisaba.** El número salía menor y se leía como bueno.

## 4. Lo que NO se tocó, a propósito

Los **instantes** siguen en UTC:

- el vencimiento de un token y de un enlace de recuperación;
- el `cerrado_en` de un turno de caja;
- la franja horaria de una reserva;
- la vigencia de 12 horas de la recomendación de CU-33.

Un instante no tiene zona. Convertirlo no lo mejora: solo agrega una
oportunidad de equivocarse.

**La regla:** por `app/core/tiempo.py` pasa lo que sea *un día del calendario*
o *una fecha que se imprime*. Lo demás sigue en `datetime.now(timezone.utc)`.

## 5. El módulo

```python
from app.core import tiempo

tiempo.BOLIVIA            # UTC-4
tiempo.hoy()              # qué día es hoy EN BOLIVIA
tiempo.ahora()            # el instante, en hora boliviana
tiempo.inicio_del_dia(d)  # la medianoche boliviana de ese día, como instante
tiempo.fin_del_dia(d)     # la medianoche del siguiente (límite abierto)
tiempo.en_boliviana(dt)   # traduce un instante que viene de la base
tiempo.marca(dt)          # «20/09/2026 14:30», para imprimir
```

### Por qué un desfase fijo y no `ZoneInfo`

Bolivia está en UTC-4 **sin horario de verano desde 1932**: no hay
transiciones que una base de zonas horarias tenga que resolver. Un desfase
fijo da el mismo resultado sin depender de que el paquete `tzdata` esté
instalado — que en Windows no viene de serie y haría fallar al importar.

### El límite derecho es abierto

`fin_del_dia(20)` devuelve la medianoche del **21**. Comparar `<= 20` deja
fuera todo lo que pasó ese día después de medianoche, y es el defecto clásico
de los reportes por fecha.

## 6. En el front también

El selector de fechas de la bitácora arma la cadena `YYYY-MM-DD` a mano en vez
de usar `toISOString()`: ese convierte a UTC y, con Bolivia en -4, **una fecha
elegida en el calendario se manda como el día anterior** — el mismo defecto,
del otro lado.

Y el `DatePipe` recibe la zona explícita (`'-0400'`), porque sin ella formatea
en la del navegador.

## 7. Lo que se prueba

`tests/test_hora_boliviana.py`, ocho pruebas. La que importa:

```python
inicio, fin = _rango(date(2026, 9, 20), date(2026, 9, 20))

# Una venta de las 21:00 del 20, cuando la tienda está cerrando:
cierre = datetime(2026, 9, 20, 21, 0, tzinfo=tiempo.BOLIVIA)
assert inicio <= cierre < fin          # antes quedaba fuera

# Y una de las 21:00 del 19 tiene que quedar afuera:
la_vispera = datetime(2026, 9, 19, 21, 0, tzinfo=tiempo.BOLIVIA)
assert la_vispera < inicio             # antes entraba
```

Y una que ata las dos pantallas: `_limites()` del tablero y `_rango()` del
reporte tienen que devolver **exactamente lo mismo** para el mismo mes. Si una
corta en UTC y la otra en hora boliviana, el Administrador ve dos totales
distintos de septiembre y no hay manera de saber cuál creer.
