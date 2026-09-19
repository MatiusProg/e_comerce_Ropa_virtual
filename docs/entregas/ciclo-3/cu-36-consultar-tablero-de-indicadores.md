# CU-36 · Consultar tablero de indicadores

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-36 |
| **Nombre** | Consultar tablero de indicadores |
| **Descripción** | Permite al Administrador visualizar los KPIs del negocio en tiempo real: ventas del día y del mes, ticket promedio, reservas pendientes y atendidas, conversión de reserva a venta, productos más vendidos y stock crítico. |
| **Propósito** | Que quien decide sobre la red vea de un vistazo cómo se mueve el negocio, sin armar consultas a mano. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P11 · Reportes y Tablero |
| **Prioridad** | Alta |
| **Requisitos que realiza** | **RF24** |
| **Precondiciones** | El Administrador tiene sesión iniciada. |
| **Postcondiciones** | Ninguna. **El caso de uso no escribe nada**: P11 es de solo lectura. |

**Flujo principal**

1. El Administrador abre *Tablero* desde el menú de administración.
2. El sistema calcula los indicadores de los últimos 30 días sobre toda la red y los muestra.
3. El Administrador acota el período con las dos fechas o con un atajo (7, 30, 90 días).
4. El Administrador acota a una sucursal.
5. El sistema recalcula y vuelve a mostrar.

**Flujos alternativos**

- **3a. Rango invertido.** Se **ordena** en vez de rechazarse: un rango al revés se entiende perfectamente.
- **3b. Solo una de las dos fechas.** La que falta se completa hacia atrás desde hoy.
- **4a. Sucursal inexistente.** Devuelve ceros, **no un 404** — ver más abajo.
- **2a. No hay datos en el período.** Las cuentas van en cero y las **tasas en nulo**, que no es lo mismo.

**Excepciones**

- **E1. El usuario no es Administrador.** 403. Alcanza a Cliente, Encargado, Cajero y Proveedor.
- **E2. No hay sesión.** 401.

---

## Lo que no se lee en la ficha

### 1. Los siete indicadores están completos — desde el 19/09

Se entregó con **cuatro apagados** —ventas del día y del mes, ticket promedio y
prendas más vendidas— porque `venta` y `detalle_venta` nacían con la `0006` de
Mateo y todavía no existían. El bloque viajaba igual, con `disponible: false` y
un motivo en texto.

**Ya existen, y hay ventas pagadas de verdad**, así que se encendió.

> **Lo que la decisión prometía se cumplió: hubo que tocar UNA sola función**,
> `_ventas`. El contrato, el router y la pantalla no cambiaron — la web ya traía
> escrita la rama de `disponible: true` desde el primer día. Es la prueba de que
> declarar el contrato entero antes de tener los datos valió la pena.

| Indicador | De dónde sale |
|---|---|
| Reservas pendientes y atendidas | `reserva` |
| Conversión, **en dos tasas** | `reserva` y `reserva_detalle.resultado_prueba` |
| Stock crítico | costura de P4 (`alertas_de_stock`) |
| Prendas más reservadas (propio) | `reserva_detalle` |
| **Vendido hoy y del período** | `venta` |
| **Ticket promedio** | `venta` |
| **Prendas más vendidas** | `detalle_venta` |

#### Qué cuenta como venta

**Sólo `PAGADA` y `ENTREGADA`.** Un pedido en `PENDIENTE_PAGO` no es una venta:
es una intención con stock apartado, el dinero no entró, y la barrida de
vencidos puede cancelarlo en veinte minutos. Contarlo **inflaría el monto del
día con compras que nadie pagó**.

`ENTREGADA` sí, porque es una `PAGADA` que además se entregó: excluirla haría
que el monto del mes bajara solo a medida que los pedidos se entregan.

Hay una prueba dedicada a esto, porque es la decisión más fácil de romper sin
darse cuenta.

#### «Vendido hoy» es siempre hoy

Aunque se esté mirando otro período. Es el pulso del negocio, lo que el
Administrador mira al abrir la pantalla. Si siguiera al período, al consultar la
semana pasada diría «vendido hoy: 0» sobre un día que no es hoy — una lectura
que confunde más de lo que informa.

#### El dinero va en `Decimal`, no en `float`

Se entregó mal la primera vez: los tres montos estaban declarados `float`. Lo
encontró una prueba al comparar `0.0` con `"0.00"`.

Es la misma regla que rige `variante_producto.precio` y `venta.total`, y la
razón está escrita en `stripe_hospedado.py`: con `float`, 150.55 se guarda como
150.54999999999998 y cualquier truncado pierde un centavo. **Un tablero que
informa un monto distinto del que suma la tabla de ventas es peor que uno que no
informa nada.**

Y todos los importes salen con **dos decimales siempre**. `SUM` sobre cero filas
devuelve el entero `0`, así que sin normalizar el tablero diría «0» un día y
«640.00» al siguiente para el mismo campo.

### 2. La conversión son DOS tasas, y la diferencia es la que importa

El enunciado dice «conversión de reserva a venta». Se responde con más
precisión de la que pedía, porque CU-24 escribe
`reserva_detalle.resultado_prueba`:

- **Tasa de atención** = atendidas / cerradas. **Mide si la gente aparece.**
- **Tasa de prueba** = líneas `LLEVA` / líneas probadas. **Mide si la prenda
  convence una vez puesta.**

Son dos negocios distintos. Una tienda con 90 % de atención y 20 % de prueba
tiene un problema de catálogo; una con 30 % de atención y 80 % de prueba tiene
un problema de recordatorios. Una sola tasa promedia las dos y no deja ver
ninguna.

**Las reservas abiertas no entran en ningún denominador.** Todavía no
fracasaron: solo no terminaron. Meterlas hundiría la tasa cada vez que se
consulta un día con reservas para más tarde, que es justo lo que uno hace por la
mañana.

### 3. Una tasa sin denominador viaja en nulo, no en cero

`tasa_atencion: null` significa «no se cerró ninguna reserva todavía».
`tasa_atencion: 0` significaría «se cerraron y ninguna se atendió». Son
opuestas, y devolver `0.0` en la primera **pinta el tablero en rojo el día que
se estrena el sistema** — que, con el calendario de este proyecto, es el día de
la defensa. La pantalla muestra una raya.

### 4. El inventario NO depende del período, y la pantalla lo dice

`existencia` guarda cuánto hay, no cuánto hubo: no tiene fecha contra la que
filtrar. «Stock crítico entre el 1 y el 15» no significa nada.

Es contraintuitivo leer un bloque que ignora las dos fechas que están arriba,
así que la tarjeta lleva la etiqueta **ahora** y un tooltip que lo explica, en
vez de esperar que se deduzca. El histórico de movimientos es CU-15.

### 5. P11 sí consulta tablas ajenas — y dónde está la línea

La regla del Ciclo 2 es que nadie hace `SELECT` sobre la tabla del otro; por eso
CU-14 pide el consolidado por la costura C1. **Acá se hace distinto**, y la razón
está en la arquitectura, no en la conveniencia: la §4.1.1 dice que P11 «depende
de todos los paquetes transaccionales (P4, P6, P7, P8) **en modo de solo
lectura**», y eso es lo que justificó documentarlo como paquete aparte. Un
tablero que pidiera una costura por indicador obligaría a Mateo a escribir una
función de agregación en P6 por cada tarjeta que se agregue a la pantalla.

**La línea que sí se respeta es otra: una regla de negocio ajena no se
reimplementa.**

- «Qué es stock crítico» —umbral mayor que cero y disponible que no lo supera—
  es una **regla de P4**. Se pide por `inventario.service.alertas_de_stock` y no
  se copia. Si se copiara, el día que P4 cambie el `<=` por un `<`, CU-16 y el
  tablero dirían cosas distintas sobre la misma prenda. **Hay una prueba que lo
  fija**: mueve el umbral por la API de CU-16 y exige que el tablero lo note.
- «Cuántas reservas hay en cada estado» no es una regla, es un `COUNT`. No hay
  nada que P6 sepa y el repositorio del tablero no.

### 6. El borde del período es el error que no se nota

«Hasta el 15» tiene que incluir el 15 **entero**. El servicio traduce la fecha al
comienzo del día siguiente y el repositorio compara con `<`. Comparar `<=`
contra el 15 a las 00:00:00 deja afuera todo salvo lo que caiga justo en la
medianoche — o sea, todo.

Mirando un mes no se nota. Se nota el día que alguien consulta un solo día y ve
el tablero vacío. Hay dos pruebas: una consulta «hoy a hoy» y espera ver la
reserva recién hecha, y otra consulta un día viejo y espera no verla.

### 7. Una sucursal inexistente devuelve ceros, no 404

Es de solo lectura y no hay nada que proteger. Un 404 obligaría a la pantalla a
distinguir «no existe» de «no tuvo movimiento», que se ven igual y se atienden
igual. **No contradice la convención 1 del ciclo** («lo que no es tuyo no
existe: 404, nunca 403»), que es sobre ocultar la existencia de datos ajenos: acá
no hay dato ajeno ninguno, solo un identificador sin filas.

### 8. El ranking excluye canceladas y expiradas

Una reserva que el cliente anuló a los cinco minutos no dice nada sobre qué
prenda interesa. Dejarlas dentro convierte el ranking en un **ranking de
arrepentimientos**. Quedan `PENDIENTE`, `PREPARADA` y `ATENDIDA`: las tres son
intención sostenida.

El ranking devuelve dos cifras por prenda —unidades y reservas distintas—
porque veinte unidades en una reserva no es lo mismo que veinte en veinte, y el
orden por unidades solo no deja verlo.

---

## Dónde vive

**Backend** — archivos propios dentro de P11, con el mismo patrón que
`consolidado_*` en `inventario/` y `carrito_*` en `ventas/`. El `router.py`,
`service.py` y `repository.py` del paquete quedan **libres para CU-37**
(exportar a PDF y Excel), que es el otro caso de uso de P11.

| Archivo | Qué |
|---|---|
| `backend/app/modules/reportes/tablero_schemas.py` | el contrato |
| `backend/app/modules/reportes/tablero_repository.py` | los agregados en SQL |
| `backend/app/modules/reportes/tablero_service.py` | período, tasas y el bloque de ventas |
| `backend/app/modules/reportes/tablero_router.py` | `GET /api/v1/reportes/tablero` |
| `backend/tests/test_cu36_tablero.py` | **27 pruebas** (21 + 6 de ventas) |

**No hay migración.** P11 no define ninguna entidad: es el primer caso de uso
del proyecto que no toca el esquema. La cadena de Alembic queda como estaba.

**Web**

| Archivo | Qué |
|---|---|
| `frontend-web/src/app/core/models/tablero.models.ts` | espejo del contrato |
| `frontend-web/src/app/core/services/tablero.service.ts` | el cliente HTTP |
| `frontend-web/src/app/features/reportes/tablero/` | la pantalla |

Ruta `admin/tablero`, dentro de la cáscara de administración: la guarda del
padre ya resuelve el rol.

> La entrada del menú que decía **Tablero** y apuntaba a `/admin` —la bienvenida
> genérica, que no calcula nada— pasó a llamarse **Inicio**. Tener dos entradas
> con el mismo nombre hacía que la que no hace nada pareciera la buena.

---

## Dos cosas que aparecieron construyendo esto

### Chart.js no puede registrarse en `app.config.ts`

La §6 de las decisiones técnicas fija **Chart.js vía `ng2-charts`** para este
tablero, y la versión 10 acepta Angular ≥ 21, así que la decisión se cumplió tal
cual estaba escrita.

Pero `provideCharts(...)` en `app.config.ts` **sumó 211 kB al bundle inicial**
—de 678 kB a 890 kB, medido—: la vitrina pública descargaría el motor de
gráficos en un teléfono para no dibujar ninguno. Ponerlo en la ruta no arregla
nada, porque `app.routes.ts` también viaja en el bundle inicial.

Va en el `providers` del **componente**, que sí es diferido. El inicial vuelve
exacto a 678 kB y Chart.js queda dentro del trozo del tablero (227 kB), que es
el único que lo usa.

### `MatDatepicker` no tiene un `DateAdapter` provisto en este proyecto

`MatDatepickerModule` **no trae su propio `DateAdapter`**: hay que proveerlo en
la configuración de la aplicación (`provideNativeDateAdapter()`). Sin él,
`MatDatepicker` lanza **en tiempo de ejecución al abrirse** — no falla la
compilación, así que no se nota construyendo.

En todo `frontend-web/src` no hay ni un `provideNativeDateAdapter` ni un
`DateAdapter`, y `features/cliente/reservas/reserva-formulario.html` **sí declara
un `<mat-datepicker>`** (CU-22).

**Conviene abrir esa pantalla antes de la defensa.** Si lanza, es una línea en
`app.config.ts`. No se tocó desde acá porque es de otro caso de uso y
`app.config.ts` es archivo compartido.

Este tablero usa `<input type="date">` nativo, y no solo por eso: el valor nativo
**ya es** la cadena `YYYY-MM-DD` que el contrato espera. Con `Date` habría que
convertirla, y `toISOString()` —que es lo que uno escribe sin pensar— pasa por
UTC, así que en Bolivia (−4) devuelve el día anterior para cualquier hora antes
de las 20:00. Elegir «hoy» en el calendario y recibir el tablero de ayer es un
error que acá no puede pasar.

---

## Deuda que queda anotada

- **El corte del día se interpreta en UTC.** Es la zona en que guarda
  `timestamptz` y en la que P6 escribe `creado_en`. Para una boutique en Bolivia
  eso corre el corte cuatro horas: una reserva hecha a las 21:00 del día 15
  cuenta en el 16. Arreglarlo es **elegir una zona horaria del negocio**, y eso
  no está decidido en ningún documento del proyecto. Se deja anotado en vez de
  inventar una.
- **`/caja` sigue sin cáscara propia.** No es de este caso de uso, pero es la
  cuarta vez que aparece el mismo hueco.
