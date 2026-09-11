# CU-25 · Expirar reservas vencidas

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
>
> **Es el único caso de uso del sistema cuyo actor es A6, el Sistema.** No lo inicia una persona y
> no tiene pantalla propia.

| Campo | Contenido |
|---|---|
| **Código** | CU-25 |
| **Nombre** | Expirar reservas vencidas |
| **Descripción** | El Sistema detecta las reservas cuya franja horaria venció sin atención, las marca como expiradas y devuelve el stock reservado a disponible. |
| **Propósito** | Que una reserva olvidada no inmovilice inventario para siempre. Sin él, cada cliente que no aparece deja prendas apartadas que nadie vuelve a poner a la venta. |
| **Actores** | **A6 · Sistema (procesos automáticos)** |
| **Paquete** | P6 · Reservas |
| **Prioridad** | Media |
| **Requisitos que realiza** | **RF30**, RF22 |
| **Precondiciones** | Existen reservas en `PENDIENTE` o `PREPARADA` cuya franja terminó hace más de `RESERVA_VIGENCIA_HORAS`. |
| **Postcondiciones** | Esas reservas quedan en `EXPIRADA`, sus unidades vuelven a `cantidad_disponible` y cada prenda deja un `movimiento_inventario` de tipo `LIBERACION` **sin usuario**. |

**Flujo principal**

1. El planificador dispara la tarea.
2. El sistema calcula el corte: `ahora − RESERVA_VIGENCIA_HORAS`.
3. El sistema busca las reservas vivas cuya `franja_fin` es anterior a ese corte, hasta un tope por corrida, las más viejas primero.
4. Por cada una, devuelve las unidades de cada prenda a disponible con su movimiento de `LIBERACION`, y la deja en `EXPIRADA`.
5. El sistema informa cuántas encontró, cuántas expiró, cuántas unidades liberó y cuáles fueron.

**Flujos alternativos**

- **1a. Disparo manual.** El Administrador la ejecuta desde la API, que es como se demuestra en la defensa.
- **3a. Nada que expirar.** La corrida informa cero y no escribe nada.
- **3b. Reserva tomada por otra transacción.** Si un cliente está cancelando la suya justo en ese momento, la tarea la saltea y la toma en la próxima vuelta.

**Excepciones**

- No hay excepciones de usuario: no hay usuario. Los estados que no corresponden —`CANCELADA`, `ATENDIDA`, `EXPIRADA`— simplemente no entran en la consulta.

---

## Lo que no se lee en la ficha

### Cuándo se considera vencida: no basta con que la franja termine

Se espera además **`RESERVA_VIGENCIA_HORAS`**. Esa tolerancia existe para el cliente que llega
tarde —o al día siguiente— y encuentra su reserva todavía en pie. El precio es tener stock retenido
ese rato, y por eso es una **variable de entorno y no una constante**: una tienda con poco
inventario va a querer bajarla.

Es lo que distingue esta variable de `RESERVA_ANTICIPACION_MAXIMA_HORAS`, que se estrenó en CU-22:
aquella limita **hacia adelante** —con cuánta anticipación se puede reservar— y esta **hacia atrás**
—cuánto se aguanta después—. Darle dos significados a una sola variable es cómo se rompen las
configuraciones, y por eso son dos.

### Tres detalles de la consulta que no son adorno

**`with_for_update(skip_locked=True)`.** Bloquea las filas que va a modificar —para que no se crucen
con una cancelación o una atención en curso— pero **saltea** las que otra transacción ya tiene
tomadas en vez de esperarlas. Es lo correcto para una tarea programada: si dos corridas se pisan, la
segunda se lleva las que quedaron libres y no se queda colgada; y si un cliente está cancelando la
suya justo entonces, la tarea la deja pasar.

**El tope por corrida.** Sin él, la primera ejecución sobre una base con meses de historial abriría
una transacción enorme y mantendría bloqueadas miles de filas. Doscientas alcanzan de sobra para el
ritmo real de una tienda; si quedaran más, la siguiente corrida las toma.

**El orden por `franja_fin`.** Las más viejas primero, que son las que más tiempo llevan reteniendo
stock.

### Es idempotente, y eso no es un lujo

Una tarea programada se dispara sola y se puede solapar consigo misma. Correrla dos veces seguidas
no libera nada la segunda vez, porque las reservas ya quedaron en `EXPIRADA`. Si no lo fuera, el
efecto sería **inventar mercadería** — el mismo problema que la doble cancelación de CU-23.

### Los movimientos quedan sin usuario

`usuario_id` en nulo. Es exactamente para lo que esa columna admite nulo, según la nota de
`inventario/models.py`: «queda nulo cuando el movimiento lo genera el sistema y no una persona: la
expiración de reservas de CU-25 es una tarea programada, sin usuario». Este es el caso de uso que
esa nota anticipaba.

### Un commit al final, no uno por reserva

O la corrida entera cuadra o no se escribe nada. Con un *commit* por reserva, un fallo a mitad
dejaría media tanda expirada, la otra media con los bloqueos sueltos y el stock sin devolver.

### Por qué devuelve qué hizo, y no un «listo»

Una tarea programada que no informa es imposible de verificar. Si un día deja de funcionar, el
síntoma sería stock retenido **sin que nada lo denuncie**, y eso se descubre semanas después
contando prendas a mano. Por eso la respuesta trae cuántas encontró, cuántas expiró, cuántas
unidades liberó, **cuáles** —para poder rastrear una en el historial— y hasta qué instante se
consideró vencida, que es lo que permite explicar por qué una reserva de ayer todavía no expiró.

### Por qué un prefijo propio y no `/reservas/expiracion`

`/reservas/{reserva_id}` ya existe y su parámetro es un entero. Una ruta `/reservas/expiracion`
declarada después **nunca se alcanzaría**: FastAPI probaría primero la parametrizada, fallaría al
convertir «expiracion» a entero y devolvería un 422 en vez de caer en la siguiente. Declararla antes
funcionaría, pero dejaría el orden del archivo como una trampa para quien lo edite mañana.

Con `/mantenimiento/reservas` el problema no existe, y además el nombre dice lo que es: no es una
operación sobre una reserva, es mantenimiento del sistema.

### Se expone como endpoint además de correr solo

Dos motivos: se puede disparar a mano en la defensa para mostrar el efecto en vivo, y devuelve lo
que hizo. El planificador —una tarea de Railway, un cron— llama a esa misma ruta.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `POST` | `/mantenimiento/reservas/expiracion` | 1-5 · una corrida completa |

Rol **Administrador**, declarado una sola vez en `mantenimiento_router`.

## Pantallas

Ninguna propia: el actor es el Sistema, y la tabla de la §2.2 del acuerdo ya lo anota así
—«— (tarea programada)»—.

Sí hay un **disparador manual** en `/admin/reservas`, visible solo para el Administrador. No es una
pantalla del caso de uso: es la forma de mostrar el efecto en vivo en la defensa, y de correrlo si
el planificador falla. El resultado se informa con lo que hizo —cuántas expiró y cuántas unidades
devolvió— y no con un «listo».

## Pruebas

`backend/tests/test_cu25_expirar_reservas.py` — 12 pruebas. Las que cubren lo que la base **no**
garantiza por sí sola:

- `test_una_reserva_recien_vencida_todavia_no_expira` — la tolerancia. Expirarla antes le quitaría
  la prenda al cliente que va en camino.
- `test_correrla_dos_veces_no_libera_el_stock_dos_veces` — la idempotencia.
- `test_no_expira_una_reserva_ya_atendida` — el cliente se llevó las prendas; devolverlas al
  inventario las inventaría.
- `test_los_movimientos_de_expiracion_no_tienen_usuario` — el actor es el Sistema.
- `test_una_preparada_tambien_expira` — que el Encargado haya juntado las prendas no significa que
  el cliente haya venido.
- `test_el_invariante_se_sostiene_despues_de_expirar` — **D4** sobre el ciclo completo.

Las reservas se crean **por la puerta normal** —CU-22, con todas sus validaciones— y recién después
se les corre el reloj. Escribir la fila a mano haría que estas pruebas no se enteraran si CU-22
dejara de apartar stock.
