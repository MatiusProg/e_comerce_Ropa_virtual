# Respuesta de Mateo al dataset de operación — 13/09/2026

Respuesta a los PR #24 y #25 de Karen: el dataset de operación, la responsividad
móvil de la web y el estado del despliegue.

**Resumen: sí, sembramos la base desplegada. Antes va un arreglo de una línea que
ya está hecho y probado, en este mismo commit.**

---

## 1. Lo que está bien y no hace falta discutir

**El seed no escribe ninguna tabla mía a mano.** Llama a `registrar_ingreso`,
`registrar_ajuste`, `registrar_transferencia`, `apartar_para_reserva`,
`liberar_de_reserva`, `descontar_por_venta` y `crear_reserva`. Es exactamente lo
que pedía la regla de P4 —*ninguna cantidad se modifica sin generar un
movimiento*— y por eso el dataset cumple las reglas del paquete en vez de
inventar filas que mi propio código rechazaría.

**Lo comprobé, no lo acepté de palabra.** Corrí el seed completo contra una base
local levantada desde las migraciones:

| Comprobación | Resultado |
|---|---|
| Invariante **D4** — `cantidad_disponible` = suma de sus movimientos | **0 existencias rotas** de 2.351 |
| `cantidad_reservada` = −suma(`RESERVA`) − suma(`LIBERACION`) | **0 rotas** |
| Saldos negativos | **0** |
| Movimientos | 5.689, con **748 marcas distintas** de `creado_en` |
| Rango del historial | **179 días** |
| Reservas | 300 en los cinco estados, 40 vivas con franja futura |

Los dos invariantes que sostienen todo P4 se mantienen sobre un dataset de
cinco mil movimientos. Es la mejor prueba que tuvo el paquete hasta ahora —
mejor que las mías, que lo ejercitan de a una operación.

**Que haya 94 existencias agotadas y 12 variantes sin stock en ninguna sucursal
es acierto, no descuido.** Un catálogo donde todo está disponible no ejercita
ninguna de las respuestas interesantes: CU-19 contestaría siempre que sí y la
vitrina no mostraría un agotado nunca.

---

## 2. Lo que había que arreglar, y por qué no era opinable

`_retrasar_movimientos` hacía esto:

```sql
UPDATE movimiento_inventario SET creado_en = :cuando WHERE id > :desde
```

sin tope por arriba. El docstring lo justificaba así, y **contra la base local es
cierto**:

> El rango de id es exacto porque el seed es de un solo hilo: nadie más está
> escribiendo en esta tabla mientras corre.

**Contra la base desplegada deja de ser cierto.** La aplicación está publicada,
el tribunal puede estar mirándola, y CU-25 expira reservas por su cuenta sin que
nadie la llame. Un movimiento escrito por alguien de verdad entre `desde` y ese
`UPDATE` se retrofecha a hace meses — y `movimiento_inventario` es **historial
inmutable**: es de lo que depende el invariante D4 y es lo que agrupa las líneas
de un remito en CU-13. Con 5 sitios de llamada y miles de vueltas de bucle, la
ventana no es teórica.

**El arreglo, ya aplicado:** el rango va acotado por los dos lados. `hasta` se lee
justo después de la operación que se quiere fechar, así que contiene exactamente
sus filas.

```sql
UPDATE movimiento_inventario SET creado_en = :cuando
WHERE id > :desde AND id <= :hasta
```

Volví a correr el seed entero con el cambio: los números de la tabla de arriba
son de esa corrida. El historial sigue repartido en 179 días y con 748 marcas
distintas, que era el efecto que el retrofechado buscaba.

---

## 3. El procedimiento para sembrar la desplegada

Va por la pestaña **Console** del servicio, como dejaste documentado para el
catálogo. Tres cosas, en este orden:

1. **`git pull` primero.** Sin este commit, el seed retrofecha lo que no debe.
2. **Correrlo en una ventana en la que nadie esté usando la aplicación.** El
   arreglo achica la ventana de días a microsegundos, pero lo barato es no
   tenerla: si nadie escribe, no hay nada que pisar.
3. `DEMO_PASSWORD` y `SEMBRAR_EN_DESPLEGADA=1`, que son las dos que el script
   pide a propósito.

**Confirmo que los identificadores de migración me sirven** —`0006_ciclo3_ventas`
y `0007_ciclo3_promociones`—, que era lo único que quedaba pendiente de mi lado
en tu §4.

---

## 4. Una cosa menor, para que no sorprenda

Quedan **38 movimientos con `creado_en` unas horas por delante de `now()`** —37
`INGRESO` y 1 `AJUSTE`, todos fechados **hoy**. Sale de que la fecha del día en
curso se sortea con una hora al azar, que a veces cae más tarde que el momento de
la corrida.

**No lo toqué y no creo que valga la pena.** No rompe ningún invariante, no
afecta a ninguna consulta —ninguna pantalla filtra por `creado_en <= now()`— y en
la defensa nadie va a mirar la hora de un remito. Lo dejo anotado para que no
parezca un hallazgo si aparece.

---

## 5. Lo del móvil, que es mío

Los tres arreglos de responsividad tocan `inventario.ts`, `disponibilidad.ts` y
las hojas de estilo de consolidado, inventario, variantes y catálogo. Cuatro de
esos siete archivos son de mis paquetes.

**Está bien y no hay nada que devolver:** son `maxWidth` en diálogos y puntos de
corte de los filtros, no reglas de negocio. Lo digo explícitamente para que no
quede la duda de si cruzaste un límite del acuerdo — el reparto de la §5 es sobre
quién *escribe* cada caso de uso, no sobre quién puede arreglar un diálogo que se
sale de la pantalla.

**Lo que sigue pendiente es mirarlo a 390 px**, como vos misma anotaste. El
teléfono lo tengo yo, así que cuando termine con los diagramas lo abro y te
confirmo. Si algo se rompe, lo arreglo yo y no te lo devuelvo.
