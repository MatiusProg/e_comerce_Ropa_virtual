# CICLO 2 · Respuesta de Mateo al análisis de alcance

> **Respuesta a la §10 de [`02-analisis-de-alcance-y-vestidor-virtual.md`](02-analisis-de-alcance-y-vestidor-virtual.md).**
> Escrita el **11/09/2026**, al cierre del día 3.
>
> Las cuatro cosas que Karen pedía están contestadas, en el orden en que las pidió. El fondo del
> análisis se acepta; lo que cambia son tres detalles, y hay **una corrección** a hacerle: uno de
> los agujeros que lista ya está tapado desde hoy.
>
> **Lo que sí se ejecutó y no queda como propuesta:** la elección del proveedor de LLM (§2), porque
> era lo único que el propio documento marcaba como tarde.

---

## 0. Antes que nada — el estado real al cierre del día 3

La §2 del análisis pinta el estado al 10/09. Con el día 3 cerrado queda así:

| | Entregado | Pendiente |
|---|---|---|
| **Karen** | CU-10, CU-11, *seed* (I2), **CU-17, CU-18** web y móvil | CU-04 preferencias, CU-19, CU-14, I5 |
| **Mateo** | Modelos + `0003`, *shell* móvil, CU-01/02/04 móviles, **CU-13, CU-15, CU-16** | CU-22, CU-23, CU-24, CU-25, I3, diagramas EA, CAP. 4.1 y 4.2 |

**Casos de uso con backend y web funcionando: 16 de 37**, contra los 11 del análisis. Karen se
adelantó un día con CU-17 y CU-18 —iban para el día 4 y están, con pantalla móvil incluida—.

**La válvula de escape de §4.3 ya no hace falta para CU-16: está entregado.** Era el primero de la
lista —«si el día 3 Mateo va retrasado, pasa CU-16 a Karen»— y el día 3 cerró con CU-13, CU-15 y
CU-16 completos, sus 49 pruebas y sus tres fichas. **CU-15, que era el segundo de la lista, tampoco
se pasa.**

Lo que sigue sin resolverse es lo que el análisis señala bien: **quedan cuatro casos de uso de
reservas, el prototipo de RA, todos los diagramas y dos secciones del CAP. 4 en dos días.** Eso está
apretado y se dice en §4.

---

## 1. Los cuatro casos de uso nuevos — se aceptan los cuatro

**CU-38, CU-39, CU-40 y CU-41 entran.** El razonamiento de §4 es correcto y los tres agujeros son
reales: verificados uno por uno contra el repositorio, no contra el recuerdo.

- **H1** se confirma: `grep` sobre los 37 casos de uso no devuelve ningún flujo cuyo actor iniciador
  sea el Proveedor, y `app.routes.ts` tiene la ruta `proveedor` reservada apuntando a la pantalla de
  bienvenida desde el Ciclo 1. El actor existe en la tabla de actores, en el `seed` y en el control
  de acceso, y no hace nada.
- **H3** se confirma: no hay ningún endpoint de recuperación en `seguridad/router.py`. Hoy la
  respuesta a «olvidé mi contraseña» es pedírselo al Administrador, en una plataforma donde el
  cliente se autorregistra.

Lo que **sí** hay que corregirle al análisis es el alcance de H2, y es por trabajo de hoy:

> **H2 encogió: la alerta de stock bajo ya existe.** El análisis la lista entre lo que falta —«ni la
> alerta de stock bajo que el propio A6 tiene declarada como responsabilidad en §3.1.1»—. **Se
> entregó hoy con CU-16**: `existencia.stock_minimo` en la migración `0004`, el endpoint
> `GET /inventario/alertas` y el panel de reposición de `/sucursal/disponibilidad`.
>
> Lo que queda de H2 es real pero más chico: la alerta **existe y se consulta**, lo que no hace es
> **buscar al usuario**. CU-40 sigue haciendo falta, con un disparador menos que inventar: ya tiene
> de dónde leer.

### 1.1 Los dos opcionales — uno entra como opcional, el otro se descarta

- **CU-43, *delivery*: se descarta ahora, no «queda como opcional».** Y conviene ser preciso con el
  motivo, porque el documento de alcance no dice exactamente lo que parece. `01-perfil.md` §1.4.2
  excluye **«asignación de repartidores, cálculo de rutas ni seguimiento en tiempo real»** — o sea
  la mitad de «seguir la entrega» del CU-43 está explícitamente fuera desde el Ciclo 1. La otra
  mitad es más matizada: esa misma línea dice que el envío **«se registra como modalidad de entrega
  con dirección y costo»**, así que *guardar* un costo ya está previsto; lo que CU-43 agrega es
  **calcularlo** con zonas y tarifas, que es tabla nueva y lógica nueva.

  Con eso, el saldo es: una mitad ya está descartada por escrito y la otra es trabajo nuevo en el
  ciclo más cargado, para algo que el enunciado pide como **fundamentación teórica** y no como
  sistema —§1.4.2 lo dice con esas palabras—. Dejarlo como opcional obliga a defender en la
  presentación por qué está enunciado y no hecho; sacarlo obliga a defender una decisión de alcance
  ya tomada y documentada, que es mucho más fácil. Si sobra tiempo —no va a sobrar— se reabre.
- **CU-42, bitácora: se mantiene como opcional, y es el primero de la cola si aparece aire.** Cuatro
  horas, una tabla y un *middleware*, y responde a una pregunta que la materia sí hace. Pero no
  desplaza a nada del enunciado.

### 1.2 Una cosa que el análisis no dice, y conviene anotar

**CU-39 cae en P4, que es paquete de Mateo.** El análisis lo ubica bien en la tabla pero no saca la
consecuencia: la tabla nueva —`abastecimiento_previsto`— y el estado *próximo a ingresar* del CU-14
son esquema de inventario. Con la regla del ciclo —quien estrena una tabla la escribe—, **CU-39 es
de Mateo** y CU-38, CU-40 y CU-41 son discutibles entre los dos. No hace falta decidirlo hoy: los
cuatro son del Ciclo 3.

Y hay una pieza que ya está puesta y que CU-39 va a necesitar: **`movimiento_inventario.proveedor_id`,
agregada ayer con CU-13.** Registra de qué proveedor vino cada lote, así que la pregunta «qué me
entregaste y cuándo» —que es la mitad de la pantalla del Proveedor— ya tiene sus datos.

### 1.3 Una advertencia sobre CU-40 y CU-41, para no repetir el error de la IA

Los dos **estrenan el envío de correo**, y eso es un proveedor externo que todavía no está elegido.
Es exactamente la misma forma del problema que el análisis denuncia en su §6: una decisión de
proveedor que nadie toma, que no parece urgente hasta que bloquea, y que además tiene que ser
gratuita por el mismo riesgo **R9**.

**Se anota ahora para que no se decida a último momento:** antes de empezar CU-41 hay que elegir
servicio de correo, verificar que su plan gratuito alcance para una demostración en vivo, y dejarlo
en `.env.example` con nombres sin marca —`CORREO_PROVEEDOR`, `CORREO_API_KEY`—, por el mismo motivo
que se explica en §2.

---

## 2. El proveedor de LLM — **elegido: Gemini**, y la contradicción está cerrada

Era lo único que el análisis marcaba como impostergable, así que no queda como propuesta: **está
hecho y commiteado**.

**Gemini (Google AI Studio), plan gratuito.** El criterio eliminatorio estaba escrito desde el 08/09
en la §2.5 de la contrapropuesta y es uno solo: **uso de herramientas fiable**, porque CU-34 y CU-35
están diseñados sobre funciones declaradas y no sobre generación de SQL. Gemini declara *function
calling* en su API, tiene plan gratuito y SDK de Python mantenido por Google. DeepSeek era el otro
candidato y queda descartado sin drama: no había nada que lo hiciera mejor para este criterio.

**Lo que NO se decidió, a propósito:** el límite exacto del plan gratuito y qué modelo concreto de la
familia se usa. Los planes gratuitos cambian de condiciones y el propio análisis pide verificarlos
«en el momento de elegir»; el momento útil es cuando se construya P10, no doce días antes. Queda
anotado en §6.6 como paso previo obligatorio, con la degradación determinista del CU-33 como red.

**La contradicción del repositorio quedó cerrada en tres archivos:**

| Archivo | Antes | Ahora |
|---|---|---|
| `docs/06-decisiones-tecnicas.md` §6.6 | «API de Claude (Anthropic), `claude-opus-5`» | Gemini, plan gratuito, con el porqué del cambio y qué verificar al construir |
| `backend/.env.example` | `ANTHROPIC_API_KEY`, `IA_MODELO=claude-opus-5` | `IA_PROVEEDOR`, `IA_API_KEY`, `IA_MODELO` |
| `backend/requirements.txt` | `anthropic==1.3.0` | quitado; el SDK se fija al construir P10 |

**Las variables no llevan el nombre del proveedor adentro.** Con `ANTHROPIC_API_KEY` en el `.env`,
cambiar de modelo obligaba a tocar el despliegue además del código — que es literalmente lo que
acaba de pasar. Y P10 va a declarar una sola función, `completar(mensajes, herramientas)`, para que
la próxima vez sea cambiar una clase.

### 2.1 Sobre subir CU-34 a prioridad Alta — **de acuerdo, con una condición**

Se acepta: **CU-34 sube a Alta y sale del orden de sacrificio.** El argumento es bueno y es el
correcto —un asistente que consulta datos reales es lo más visible de la defensa—.

La condición es que no se lleve por delante al CU-33. El recomendador es el que **el enunciado
menciona explícitamente** y el que tiene la degradación determinista ya diseñada; el asistente es el
que más luce. Si el Ciclo 3 obliga a elegir, primero existe CU-33 completo y después CU-34, aunque
CU-34 tenga más prioridad para *empezar*. No es contradictorio: lo que sube es cuándo se ataca, no
qué se salva si hay que salvar uno solo.

---

## 3. El vestidor virtual — se acepta la propuesta tal como está escrita

**Movimiento uno (probar el prototipo contra el PNG real del *seed*, día 4): sí, sin reservas.**
Costo nulo y descubre en el día 4 si las proporciones y la transparencia del activo sirven. Es
además lo que la §2.4 de la contrapropuesta ya pedía como condición del *seed*, y el *seed* está.

**Movimiento dos (el botón desde la ficha móvil, día 5): sí, con la condición que el propio análisis
le pone en su §7.4** — «si el día 4 termina y el prototipo no está andando, el movimiento dos no se
hace». Se acepta esa condición literal y no se promete más que eso.

Lo honesto es decir que el día 5 ya tiene CU-24, CU-25, los diagramas de EA y el CAP. 4.1 y 4.2, y
que el movimiento dos entra **solo si el día 4 cierra bien**. No se compra tiempo pasando CU-16 a
Karen —ya está hecho— ni CU-15 —también—. Si hace falta comprarlo, lo que se puede ceder es **la
redacción del CAP. 4.2**, que es documento y no código, y eso se avisa el día 5 por la mañana, no a
la noche.

**La costura C5 se acepta tal cual está redactada**, incluida la parte de que la ruta
`/vestidor/:varianteId` es de Mateo y va al final de su sección del `router.dart`.

---

## 4. Quién regenera el diagrama general — **Mateo**, y con una precisión de calendario

Confirmado: los once `scripts/ea-*.ps1` son de Mateo por la §2.3 de la contrapropuesta, y el 1.3.2
regenerado con CU-38 a CU-41 también.

**La precisión:** no se regenera hasta que los cuatro casos de uso nuevos estén **acordados y
escritos en `03-captura-requisitos.md`**. Regenerar el diagrama con una lista que todavía se está
discutiendo obliga a hacerlo dos veces, y cada corrida exige abrir EA a mano — que es justamente el
trabajo que la §2.3 dijo que no tiene retorno transferir.

**Orden propuesto:** primero Karen agrega las filas de CU-38 a CU-41 y RF37 a RF39 en las §1.1.2,
§1.1.3 y §1.2 (es edición de tablas, no hay conflicto con nada de Mateo), y **después** Mateo corre
el *script* una sola vez. Si eso no llega para la Presentación #2 del 13/09, el 1.3.2 va con los 37
y los cuatro nuevos se presentan como refinamiento del Ciclo 2 en el texto — que es lo que la §8 del
análisis ya propone decir, y se sostiene solo.

---

## 5. Resumen — qué queda decidido

| # | Punto de la §10 | Respuesta |
|:---:|---|---|
| 1 | Los cuatro CU nuevos | **Aceptados los cuatro.** CU-42 queda opcional; **CU-43 se descarta** — la logística ya estaba fuera de alcance por escrito |
| 2 | El proveedor de LLM | **Gemini, plan gratuito. Hecho y commiteado**, con §6.6, `.env.example` y `requirements.txt` corregidos |
| 3 | El vestidor virtual | **Movimiento uno sí; movimiento dos con la condición de la §7.4.** La válvula de escape no se usa: CU-16 y CU-15 están entregados |
| 4 | El diagrama general | **Mateo**, después de que las tablas del capítulo 1 tengan los CU nuevos |

**Correcciones al análisis:** H2 encogió —la alerta de stock bajo existe desde hoy—, y CU-39 cae en
P4, que es paquete de Mateo.

**Lo que hace falta de Karen, y es poco:**

1. **Decir si acepta descartar CU-43 de una vez** en vez de dejarlo como opcional (§1.1).
2. **Confirmar que CU-39 es de Mateo** por la regla de propiedad de tablas (§1.2).
3. **Traer su rama al día.** `feat/cu-10-productos-variantes` todavía no tiene el PR #18, y el
   `git diff` contra `main` aparenta borrar el módulo de inventario entero. Es un espejismo del
   diff, no un conflicto — pero conviene mergear `main` antes de que lo sea de verdad.
4. **Avisar antes de escribir una migración nueva.** La §4 del acuerdo solo fijó la `0002` y la
   `0003`; hoy existe una **`0004_stock_minimo`**, de Mateo, colgando de la `0003`. Si Karen
   necesita una para las categorías preferidas del CU-04, hay que acordar el identificador primero:
   dos revisiones con el mismo `down_revision` dejan el árbol con dos cabezas y `alembic upgrade
   head` falla pidiendo cuál.
