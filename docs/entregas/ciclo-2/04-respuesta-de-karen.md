# CICLO 2 · Respuesta de Karen

> **Respuesta a la §5 de [`03-respuesta-de-mateo-al-analisis.md`](03-respuesta-de-mateo-al-analisis.md).**
> Escrita el **11/09/2026**, al cierre del día 3.
>
> Las cuatro cosas que pedía Mateo están contestadas, en su orden. **Se acepta todo**: no hay nada
> que discutir de vuelta. Lo que sí hay es una corrección a su punto 3 —ya está resuelto— y dos
> cosas que se agregan porque aparecieron al implementar.

---

## 1. Descartar CU-43 (*delivery*) — **de acuerdo, se descarta**

El argumento es mejor que el del análisis, y conviene decir por qué en vez de solo aceptarlo.

El análisis trataba el *delivery* como un agujero de expectativa: «si la ingeniera pide esa teoría,
es razonable que espere ver algo en el sistema». Mateo fue a mirar el documento y encontró que **la
mitad ya estaba descartada por escrito desde el Ciclo 1** —`01-perfil.md` §1.4.2 excluye
explícitamente asignación de repartidores, cálculo de rutas y seguimiento en tiempo real— y que la
otra mitad, *registrar* el costo de envío, ya está prevista como modalidad de entrega.

Lo que quedaba de CU-43, entonces, no era «el delivery» sino **calcular** el costo con zonas y
tarifas: tabla nueva y lógica nueva, en el ciclo más cargado, para algo que el enunciado pide como
**fundamentación teórica**.

Y el argumento de defensa es el que decide: explicar por qué algo enunciado no está hecho es más
caro que explicar una decisión de alcance ya tomada y documentada. **CU-43 sale.** Si sobra tiempo
—no va a sobrar— se reabre.

**CU-42 (bitácora) se mantiene como opcional**, y de acuerdo con que sea el primero de la cola si
aparece aire: cuatro horas, una tabla y un *middleware*, y responde a una pregunta que la materia sí
hace.

## 2. CU-39 es de Mateo — **confirmado**

Por la regla de propiedad del ciclo, sin discusión: CU-39 estrena `abastecimiento_previsto`, que es
tabla de P4, y quien estrena una tabla la escribe. El análisis lo ubicó bien en el paquete y no sacó
la consecuencia; está bien sacada.

**El reparto de los cuatro nuevos queda así**, y se propone cerrarlo ahora para no discutirlo en el
Ciclo 3:

| CU | Qué estrena | Dueño | Por qué |
|---|---|:---:|---|
| **CU-38** Registrar productos del proveedor | Nada: reusa `producto` y `variante_producto` con filtro por `proveedor_id` | **Karen** | Son sus tablas, y es el CRUD de CU-10 con otra guarda de rol |
| **CU-39** Informar disponibilidad y plazo | `abastecimiento_previsto` | **Mateo** | Tabla de P4, y alimenta el estado *próximo a ingresar* de CU-14 |
| **CU-40** Notificar eventos | Tabla de notificaciones | **Mateo** | Los tres disparadores son suyos: reserva creada, reserva preparada, stock bajo |
| **CU-41** Recuperar contraseña | Tabla de *tokens* de un solo uso | **Karen** | P1 Seguridad, y es donde ya vive el CU-04 de las preferencias |

CU-40 y CU-41 **comparten el envío de correo**, así que quien llegue primero lo estrena y el otro lo
consume. Conviene que sea CU-41, que es el más chico.

## 3. Traer la rama al día — **ya está, y con una corrección**

Cuando Mateo escribió esto era cierto; a esta altura ya no. Lo que pasó, para que quede en el
registro porque tiene una lección:

**`feat/cu-10-productos-variantes` quedó muerta, y con trabajo adentro.** El PR #17 se mergeó cuando
esa rama estaba en `d476a2d` —el análisis de alcance—, y los cuatro *commits* de CU-17 y CU-18
llegaron **después**. Quedaron en una rama cuyo PR ya estaba cerrado: invisibles, sin PR y fuera de
`main`. Se recuperaron abriendo el **PR #19** sobre una rama nueva, que ya está mergeado.

La lección, que vale para los dos en lo que queda: **mergear un PR cierra la rama para GitHub, pero
no impide que se le sigan empujando *commits*.** Los que lleguen después no están en ningún lado.
Antes de mergear conviene mirar que el último *commit* de la rama sea el que se está mirando.

**Estado actual:** `KarenCiclo2` existe —faltaba, junto a `KarenCiclo1`, `MateoCiclo1` y
`MateoCiclo2`— y está al día con `main`, incluido el PR #20. Es la rama de trabajo de acá en
adelante, igual que `MateoCiclo2` del otro lado.

## 4. Avisar antes de escribir una migración — **de acuerdo, y acá va el aviso**

El punto es correcto y el riesgo es real: dos revisiones con el mismo `down_revision` dejan el árbol
con dos cabezas y `alembic upgrade head` falla pidiendo cuál.

**CU-04 preferencias no necesitó migración**, así que no hubo problema: `cliente_categoria` ya había
entrado en la `0002`. La `0004_stock_minimo` de Mateo queda registrada y es la cabeza actual.

**Se reservan de antemano los identificadores del Ciclo 3**, con el mismo mecanismo que funcionó en
el Ciclo 2 —fijarlos antes de escribir nada, para que las migraciones se escriban en paralelo—:

| Archivo | `revision` | `down_revision` | Autor |
|---|---|---|:---:|
| `0005_ciclo3_favoritos.py` | `0005_ciclo3_favoritos` | `0004_stock_minimo` | **Karen** |
| `0006_ciclo3_ventas.py` | `0006_ciclo3_ventas` | `0005_ciclo3_favoritos` | **Mateo** |
| `0007_ciclo3_promociones.py` | `0007_ciclo3_promociones` | `0006_ciclo3_ventas` | **Mateo** |

El primero se estrena ya, con CU-20 (§6). Los otros dos quedan reservados; si el orden cambia, se
avisa acá antes de escribir.

---

## 5. Las dos correcciones que se aceptan

**H2 encogió, y está bien corregido.** La alerta de stock bajo existe desde el día 3 con CU-16:
`existencia.stock_minimo`, el endpoint `GET /inventario/alertas` y el panel de reposición. El
análisis la listaba entre lo que faltaba y ya no corresponde. **Lo que queda de H2 es que la alerta
no busca al usuario**, que es exactamente lo que CU-40 hace — con un disparador menos que inventar.

**La condición sobre CU-34 se acepta tal cual.** Sube a Alta y sale del orden de sacrificio, pero
**si el Ciclo 3 obliga a elegir, primero existe CU-33 completo.** Es el que el enunciado menciona
explícitamente y el que tiene la degradación determinista diseñada. No es contradictorio: lo que
sube es cuándo se ataca, no qué se salva.

**Sobre Gemini:** de acuerdo con dejar sin fijar el modelo concreto y el límite del plan gratuito
hasta construir P10. Y de acuerdo con el criterio de las variables sin marca —`IA_PROVEEDOR`,
`IA_API_KEY`— por el motivo que se dio: con `ANTHROPIC_API_KEY` en el `.env`, cambiar de modelo
obligaba a tocar el despliegue además del código.

**Sobre el correo (§1.3):** el paralelismo está bien traído y se acepta la anotación. Se agrega una
cosa: **conviene elegirlo cuando se elija el modelo de IA, no cuando toque CU-41.** Los dos son
decisiones de proveedor gratuito, las dos bloquean, y tomarlas juntas cuesta una tarde en vez de dos.

---

## 6. Lo que Karen hace ahora — y por qué esto y no otra cosa

El Ciclo 2 de Karen **está cerrado en código**: CU-10, CU-11, *seed*, CU-17, CU-18, CU-19, CU-14 y
CU-04 preferencias, con 235 pruebas en verde. Lo que sigue, en este orden:

1. **Escribir CU-38 a CU-41 y RF37 a RF39 en `03-captura-requisitos.md`** —§1.1.2, §1.1.3 y §1.2—.
   Es lo que la §4 de la respuesta de Mateo pide como paso previo para regenerar el 1.3.2 **una sola
   vez**. Es edición de tablas y no toca nada suyo.
2. **CU-20 Favoritos**, que es el único caso de uso de Ciclo 3 que es enteramente de P5 y por lo
   tanto no se cruza con las reservas.

**Por qué CU-20 primero, siendo prioridad Baja.** Porque no se elige por prioridad sola sino por lo
que desbloquea: el **RF31** dice con todas las letras que los favoritos *«alimentan el historial de
preferencias que necesita el recomendador del RF25»*. Con CU-04 preferencias entregado hoy, CU-20 es
**la otra mitad de la preferencia declarada** que consume CU-33 — y CU-33 es el caso de uso que el
enunciado menciona explícitamente y el que acaba de quedar como el que se salva si hay que salvar
uno solo.

Dicho de otro modo: CU-20 es barato, es de un paquete que nadie más toca, y deja al CU-33 con sus
datos de entrada listos antes de que empiece el ciclo donde hay que construirlo. Hacerlo en el
Ciclo 3, entre el carrito y la pasarela, sería hacerlo tarde.

**Lo que Karen NO está haciendo todavía, y hay que decirlo:** la **I5**, la consolidación del
`.docx` para la Presentación #2 del 13/09. Es lo único suyo que queda del Ciclo 2 y no es código.
Si el día 5 aprieta, I5 gana sobre CU-20 sin discusión — la entrega es el documento.

---

## 7. Resumen

| # | Lo que pedía Mateo | Respuesta |
|:---:|---|---|
| 1 | Descartar CU-43 | **Descartado.** CU-42 sigue opcional y primero de la cola |
| 2 | Confirmar que CU-39 es suyo | **Confirmado.** Y se cierra el reparto de los cuatro: CU-38 y CU-41 de Karen, CU-39 y CU-40 de Mateo |
| 3 | Traer la rama al día | **Hecho.** `KarenCiclo2` al día con `main`; queda registrado por qué murió `feat/cu-10-productos-variantes` |
| 4 | Avisar antes de una migración | **De acuerdo.** Reservados `0005`, `0006` y `0007` en §4 |

**Lo que hace falta de Mateo:** nada que bloquee. Solo confirmar que los identificadores de
migración de §4 le sirven, antes de escribir la `0006`.
