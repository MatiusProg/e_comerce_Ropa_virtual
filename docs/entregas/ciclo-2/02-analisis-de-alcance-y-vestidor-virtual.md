# CICLO 2 · Análisis de alcance — ¿alcanzan los 37 casos de uso?

> **Escrito por Karen el 10/09/2026, para discutir con Mateo.** Es el tercer documento del Ciclo 2
> y se lee después de [`00-organizacion-por-caso-de-uso.md`](00-organizacion-por-caso-de-uso.md) y
> de [`01-contrapropuesta-de-mateo.md`](01-contrapropuesta-de-mateo.md). No cambia el reparto ni la
> propiedad de las tablas: **ninguna decisión de esos dos documentos se toca**.
>
> Lo que decide es otra cosa: si el alcance de 37 casos de uso es suficiente para la defensa del
> **22/09**, qué falta de verdad, y qué se adelanta del vestidor virtual en los tres días que
> quedan del ciclo.
>
> **Nada de esto está implementado todavía.** Es una propuesta; lo que se acepte se escribe
> después.

---

## 1. Por qué existe este documento

Tres cosas dispararon la revisión, y conviene separarlas porque solo una es un problema real:

1. Hay compañeros con el **chatbot ya conectado**, y el nuestro no tiene ni proveedor elegido.
2. Corre la versión de que **un grupo tiene unos 70 casos de uso** contra nuestros 37.
3. Quedan **doce días** para la defensa y vamos por el 30% del sistema.

La primera es un problema de calendario. La segunda no es un problema (§3). La tercera es **el**
problema, y es la que ordena todo lo que sigue: cualquier caso de uso que se agregue a partir de
hoy compite por las mismas horas que el pago, la IA y la realidad aumentada, que son exigencias
explícitas del enunciado. Por eso este documento no propone inflar el conteo, sino **cerrar los
agujeros de cobertura que sí existen**, que son pocos y baratos.

---

## 2. El punto de partida — estado real al 10/09/2026

| | |
|---|---|
| Presentación #2 | **13/09** — quedan 3 días |
| Presentación final | **20/09** |
| Defensa | **22/09** — quedan 12 días |
| **Casos de uso con backend y web funcionando** | **11 de 37** (CU-01 a CU-11) — 30% |
| Casos de uso con pantalla móvil | 3 (CU-01, CU-02, CU-04) |
| Tablas de detalle (1.3.1) redactadas | 11 |
| **Casos de uso restantes** | **26** — y son todos los difíciles |

Siguen como cascarón de menos de veinte líneas los *routers* de `catalogo_publico`, `inventario`,
`reservas`, `ventas`, `pagos`, `ia`, `reportes` y `vestidor_virtual`.

**Ciclo 2, día 2 de 5:**

| | Entregado | Pendiente |
|---|---|---|
| **Karen** | CU-10, CU-11, *seed* (I2) — el *seed* era del día 2 y CU-11 del día 3 | CU-04 preferencias, CU-17, CU-18, CU-19, CU-14, I5 |
| **Mateo** | Modelos + migración `0003`, *shell* móvil, CU-01/CU-02/CU-04 móviles (I1) | CU-13, CU-15, CU-16, CU-22, CU-23, CU-24, CU-25, I3, diagramas EA, CAP. 4.1 y 4.2 |

Es el dato que hay que mirar antes que cualquier otro: **Mateo tiene siete casos de uso, el
prototipo de RA, todos los diagramas y dos secciones del CAP. 4 en tres días.** La válvula de
escape de §4.3 de la contrapropuesta —pasar CU-16 y después CU-15 a Karen— existe justamente para
esto y hoy es más relevante que hace dos días.

---

## 3. El número de casos de uso — la cuestión queda cerrada

### 3.1 Los 30 casos de uso eran falsos

`docs/00-indice-oficial.md` §0.5 dejó la cuestión abierta como **«Estado: no confirmado»** desde el
04/09. Ya está consultado: **la ingeniera nunca pidió una cantidad de casos de uso**, ni por ciclo
ni por proyecto. La versión que circulaba entre los compañeros no era cierta.

Eso elimina la única razón externa que había para tocar el conteo. **No hay un número que
alcanzar.** Lo que se corrige de acá en adelante se corrige porque falta, no porque haya que llegar
a una cifra.

§0.5 del índice oficial queda cerrada con esta respuesta.

### 3.2 La aritmética del grupo de 70

Los 70 casos de uso no son más sistema: son el mismo sistema contado con otra granularidad.

Nuestros 37 contienen **trece casos de uso «Gestionar X»** que cubren **diecinueve entidades**
—CU-05 son ciudades *y* sucursales, CU-08 son categorías, tallas *y* colores, CU-09 son temporadas
*y* colecciones, CU-10 son productos *y* variantes—. Si en vez de un caso de uso por entidad se
escribe uno por operación:

> 19 entidades × 3 o 4 operaciones ≈ **60 a 76 casos de uso**, reemplazando a trece.
> Total: **85 a 100**.

Setenta sale del mismo enunciado partiendo los ABM en «Registrar producto / Modificar producto /
Eliminar producto / Consultar producto» donde nosotros tenemos CU-10.

### 3.3 Cuál granularidad es la correcta

La nuestra, y no es una opinión de conveniencia. Jacobson define el caso de uso como **una
secuencia completa de acciones con un valor observable para un actor**; un alta, una baja y una
modificación sobre la misma entidad no son tres valores distintos, son variantes de flujo del mismo
caso de uso. Partirlos multiplica los artefactos —tabla de detalle, diagrama, comunicación,
secuencia, prototipo, por cada uno— sin agregar una línea de sistema.

Nuestro modelo, además, ya usa la herramienta que el PUDS da para esto: el CU-02 *Iniciar y cerrar
sesión* está incluido con `include` desde los demás, y la verificación de correo entra con
`extend`. Eso es estructura, no conteo.

**Decisión propuesta: la granularidad no se toca.** Si en la defensa alguien pregunta por el
número, la respuesta es la de arriba y se sostiene sola.

---

## 4. Lo que sí falta — cinco agujeros de cobertura

Ninguno de estos es granularidad. Son funcionalidades que **no existen en ningún caso de uso** de
los 37.

### H1 · El actor Proveedor no inicia ningún caso de uso

Es el más grave y el más fácil de detectar en una revisión.

El enunciado (§4) le da al **Proveedor** tres responsabilidades explícitas: *registrar o enviar
información de productos*, *informar disponibilidad de productos* y *asociar productos con
temporadas y colecciones*. Nuestro `03-captura-requisitos.md` §3.1.1 lo reconoce y hasta lo promete
por escrito —«su participación se modela con alcance acotado: registro y consulta de sus productos
y su disponibilidad»—, y después **ningún caso de uso lo realiza**: CU-07 es el Administrador
gestionando proveedores y CU-10 es el Administrador gestionando productos. En los 37, el actor A5
aparece como dato de una tabla, nunca como iniciador.

Queda hasta el rastro en el código: `frontend-web/src/app/app.routes.ts:118` tiene reservada la
ruta `proveedor` y no lleva nada adentro.

**Y hay un segundo agujero encadenado a este.** El enunciado pide que el inventario consolidado
distinga las prendas «disponibles, reservadas, vendidas, agotadas o **próximas a ingresar**», y
nuestro CU-14 promete exactamente esos cuatro estados. Pero **nada en los 37 casos de uso produce
el estado *próximo a ingresar***: CU-13 registra la mercadería cuando ya llegó. El estado es
inalcanzable porque falta quien lo anuncie, y quien lo anuncia es el Proveedor.

### H2 · El RF11 no tiene mecanismo

«El sistema deberá notificar las reservas a la sucursal correspondiente» está trazado a CU-22 y
CU-24, pero lo que esos casos de uso hacen es que la reserva **aparezca en la lista** del Encargado
cuando entra a mirar. Eso es consulta, no notificación.

En los 37 casos de uso no hay **ningún** mecanismo de notificación: ni correo de confirmación del
pedido, ni aviso al cliente de que su reserva está preparada, ni la alerta de stock bajo que el
propio A6 tiene declarada como responsabilidad en §3.1.1.

### H3 · No existe recuperar contraseña

En una plataforma donde el cliente se autorregistra. Es la pregunta gratis de la defensa y hoy la
respuesta sería que hay que pedírselo al Administrador.

### H4 · No hay bitácora del sistema

El RNF10 exige trazabilidad, pero solo de los movimientos de inventario. No hay registro de quién
creó, modificó o eliminó nada más: ni un producto, ni un precio, ni un usuario, ni una promoción.
No lo pide el enunciado; sí lo espera la materia, y es de lo más barato que hay.

### H5 · El delivery está solo enunciado

La Parte I dedica una sección entera a *cómo funcionan los deliverys* y *cómo calculan los pagos
(distancia, peso, frecuencia, tamaño)*. En el sistema, el envío a domicilio es una opción suelta
dentro de CU-27 y `01-perfil.md` §1.4.2 declara la logística fuera de alcance. Que se pida esa
teoría hace razonable que se espere ver, al menos, **un costo de envío calculado y un estado de la
entrega**.

Es el más caro de los cinco y el único que toca CU-27, que está en el ciclo más cargado. **Va como
opcional.**

---

## 5. La propuesta — de 37 a 41, con dos opcionales

Seis casos de uso nuevos, numerados **a continuación** de los existentes.

> **Los 37 no se renumeran.** CU-01 a CU-37 mantienen su número. La lista se entregó completa el
> 05/09 y sus códigos están citados en la priorización, en la trazabilidad RF→CU, en la matriz
> paquete–caso de uso, en los diagramas de EA y en los nombres de los *commits*. Renumerar por
> insertar en el medio rompería todo eso a cambio de nada.

| ID | Caso de uso | Actor | Agujero | RF | Paquete | Prior. | Ciclo |
|---|---|---|:---:|---|---|:---:|:---:|
| **CU-38** | Registrar productos del proveedor | A5 Proveedor | H1 | **RF37** | P2 Organización | Media | 3 |
| **CU-39** | Informar disponibilidad y plazo de abastecimiento | A5 Proveedor | H1 | **RF38** | P4 Inventario | Media | 3 |
| **CU-40** | Notificar eventos a los usuarios | A6 Sistema | H2 | **RF11** | P6 / P7 | Media | 3 |
| **CU-41** | Recuperar contraseña | A1 Cliente (todos) | H3 | **RF39** | P1 Seguridad | Media | 3 |
| *CU-42* | *Consultar bitácora del sistema* | *A2 Administrador* | *H4* | ***RF40*** | *P1 Seguridad* | *Baja* | *3* |
| *CU-43* | *Calcular costo de envío y seguir la entrega* | *A1 Cliente* | *H5* | ***RF41*** | *P7 Ventas* | *Baja* | *3* |

En cursiva, los dos opcionales.

**Requisitos funcionales nuevos.** Se numeran a continuación de RF36, en la misma línea que los
once adicionales del equipo de §3.3.2:

| RF | Enunciado | CU |
|---|---|---|
| **RF37** | El proveedor deberá poder registrar la información de los productos que abastece y asociarlos a una temporada y una colección. | CU-38 |
| **RF38** | El proveedor deberá poder informar la disponibilidad y el plazo de abastecimiento de sus productos, alimentando el estado *próximo a ingresar* del inventario consolidado. | CU-39 |
| **RF39** | El sistema deberá permitir a un usuario recuperar el acceso a su cuenta mediante un enlace de un solo uso enviado a su correo. | CU-41 |
| *RF40* | *El sistema deberá registrar en una bitácora toda operación de alta, modificación y baja, con usuario, fecha y entidad afectada.* | *CU-42* |
| *RF41* | *El sistema deberá calcular el costo del envío a domicilio y permitir consultar el estado de la entrega.* | *CU-43* |

RF11 no se agrega: ya existe y es del enunciado. Lo que cambia es que **pasa a tener un caso de uso
que lo realiza de verdad**, en vez de estar trazado a dos que no notifican.

### 5.1 Qué cuesta cada uno

Estimaciones gruesas, para decidir el orden, no para comprometerse:

| CU | Costo | Por qué es barato (o no) |
|---|:---:|---|
| **CU-41** Recuperar contraseña | ~4 h | Token de un solo uso, dos endpoints, dos pantallas. Estrena el envío de correo |
| **CU-40** Notificaciones | ~1 día | Reutiliza el correo que estrena CU-41. Tres disparadores: reserva creada, reserva preparada, pedido pagado. En la app, notificación dentro de la aplicación; *push* solo si sobra tiempo |
| **CU-38** Productos del proveedor | ~1 día | Reutiliza entero el CRUD de CU-10 con filtro por `proveedor_id` y guarda de rol. La ruta ya está reservada |
| **CU-39** Disponibilidad del proveedor | ~1 día | Una tabla (`abastecimiento_previsto`) y el estado *próximo a ingresar* en la consulta de CU-14 |
| *CU-42* Bitácora | *~4 h* | *Una tabla, un middleware en el* router *y una pantalla de consulta con filtros* |
| *CU-43* Delivery | *~1,5 días* | *Tabla de zonas y tarifas, cálculo en el* checkout*, estados de la entrega. Toca CU-27* |

**Los cuatro primeros suman entre tres y cuatro días** de un Ciclo 3 que ya tiene quince casos de
uso en siete días. No entran gratis: entran **después** de lo que el enunciado exige y **antes** de
los opcionales.

### 5.2 Orden de sacrificio actualizado

`05-plan-y-cronograma.md` §5.5 fija que si el plazo aprieta se sacrifica primero CU-20 y CU-32,
después CU-34. Con los nuevos, el orden queda así, de lo primero que se cae a lo último:

1. **CU-43** delivery y **CU-42** bitácora (los dos opcionales)
2. **CU-20** favoritos y **CU-32** devoluciones (prioridad Baja del enunciado)
3. **CU-39** disponibilidad del proveedor
4. **CU-40** notificaciones (degradadas a aviso dentro de la aplicación, sin correo)
5. **CU-38** y **CU-41**

**No se sacrifican nunca:** CU-21 vestidor virtual, CU-27 y CU-28 pago en línea, CU-33 a CU-35
inteligencia artificial. Son exigencias explícitas del enunciado, y esto no cambia respecto de
§5.5.

**Cambio propuesto sobre §5.5:** **CU-34 sale del orden de sacrificio y sube de Media a Alta.**
El motivo está en §6.

---

## 6. La inteligencia artificial — lo que nos separa de verdad

El asistente conversacional no nos falta como caso de uso: **CU-34 existe desde el 01/09**. Lo que
falta es haberlo construido, y hay una decisión trabada que lo impide.

| | Estado |
|---|---|
| Prioridad de CU-34 | Media, Ciclo 3, **tercero en el orden de sacrificio** |
| Proveedor de LLM | **Sin elegir** — I7 quedó diferido en §4.2 de la contrapropuesta |
| Llamadas hechas al modelo | Ninguna |

Y sigue viva la contradicción que Mateo mismo señaló el 08/09 en §2.5 y que nadie corrigió:
`06-decisiones-tecnicas.md` §6.6 dice **«API de Claude (Anthropic), modelo `claude-opus-5`»** y
`backend/.env.example` declara `ANTHROPIC_API_KEY` e `IA_MODELO=claude-opus-5`. Los dos son de pago
por *token* y contradicen la decisión del 04/09 de usar un modelo sin costo por uso. El paquete
`anthropic` está además instalado en el entorno del *backend*.

**Tres propuestas:**

1. **Elegir el proveedor esta semana.** No es trabajo, es una decisión, y cuesta una tarde de
   prueba. Lo único eliminatorio ya está escrito en §2.5 de la contrapropuesta: **uso de
   herramientas fiable**, porque CU-34 y CU-35 están diseñados sobre funciones declaradas y no
   sobre generación de SQL. Gemini (AI Studio) y DeepSeek son los candidatos que ya estaban sobre
   la mesa.
2. **Subir CU-34 a prioridad Alta** y sacarlo del orden de sacrificio. Un asistente que consulta
   datos reales es lo más visible de toda la defensa, y el nuestro está diseñado mejor que un
   chatbot que genera SQL: herramientas acotadas, `cliente_id` inyectado desde el *token* y nunca
   tomado de la conversación. Eso solo puntúa si existe.
3. **Corregir §6.6 y `.env.example`** cuando se elija, tal como ya lo dejó anotado §9 de la
   contrapropuesta.

Que el compañero tenga el chatbot «conectado» no dice nada sobre si consulta datos reales. Pero a
doce días de la defensa, lo que existe le gana a lo que está bien diseñado en un documento.

---

## 7. El vestidor virtual — qué se adelanta en este ciclo

**La RA se queda con Mateo.** Se confirma §2.2 de la contrapropuesta: `google_mlkit_pose_detection`
corre sobre los fotogramas de la cámara del dispositivo, un emulador entrega una cámara sintética,
y el teléfono está de su lado. No se mueve.

Lo que se propone no es mover la tarea, es **subirle el techo al mismo día de trabajo**.

### 7.1 Las dependencias del CU-21 ya están casi todas

| Pieza | Estado |
|---|---|
| PNG con fondo transparente, uno por variante (requisito S5) | **✔ Ya existe.** El *seed* los genera por variante — `backend/app/db/seed_catalogo.py:448` — con el índice parcial que garantiza uno solo por variante |
| `camera`, `google_mlkit_pose_detection`, `image`, `permission_handler` | ✔ Declaradas en `pubspec.yaml` |
| *Shell* móvil con sesión viva | ✔ Entregado el día 1 |
| El PNG viaja hasta el cliente | **✔ Ya viaja.** `ImagenOut` expone `url`, `es_transparente`, `variante_id` y `variante_sku` |
| Prototipo pose + superposición | ✘ Día 4 — I3, de Mateo |
| Ficha de producto móvil (CU-18) | ✘ Día 4 — de Karen |
| Carrito y «agregar a la reserva» | ✘ Ciclo 3, y no se toca |

### 7.2 La propuesta, en dos movimientos

**Uno · El prototipo del día 4 se prueba contra el PNG real, no contra un activo de mentira.**
Ya está en §2.4 de la contrapropuesta como condición del *seed*, y el *seed* está entregado. Es
cambiar de dónde sale la imagen del prototipo: en vez de un PNG de prueba en `assets/`, la `url`
de la imagen transparente de una variante sembrada. Costo: nulo. Beneficio: se descubre en el día 4
si las proporciones y la transparencia del activo sirven, y no en el Ciclo 3.

**Dos · El día 5, el botón desde la ficha real.** Que la ficha de producto móvil (CU-18) tenga
**«Probar en vestidor virtual»** y navegue al prototipo con la variante seleccionada. No es el
CU-21 completo —no hay selector de talla y color en vivo, ni captura compartible, ni derivación al
carrito, y eso sigue siendo del Ciclo 3—, pero es **realidad aumentada funcionando sobre productos
reales el 13/09**.

Lo que compra:

1. **Mata el riesgo R3 doce días antes de la defensa**, en el teléfono de la defensa. R3 es el
   riesgo técnico más alto del proyecto y el plan es explícito en que no puede descubrirse que no
   funciona el 15/09.
2. **Es lo que más nos diferencia en la Presentación #2.** La RA es lo único del enunciado que casi
   nadie tiene andando; pesa más que treinta casos de uso de papel.
3. **Convierte el CU-21 en integración y no en investigación**, que es el objetivo declarado en
   §5.4 del plan.

### 7.3 La costura que esto crea — C5

Se suma a las dos vigentes de §6 de la contrapropuesta, y es la más barata de las tres porque **no
necesita ni una línea de *backend***.

> **C5 · Ficha móvil → vestidor virtual** (Mateo consume de Karen)
>
> **Contrato:** la ficha pública de CU-18 devuelve, por variante, la `url` de su imagen con
> `es_transparente = true`. El esquema ya lo expone; lo que Karen fija es que el detalle público
> la incluya y que la pantalla tenga el botón que navega a `/vestidor/:varianteId`.
>
> **La ruta `/vestidor/:varianteId` es de Mateo**, en su sección del `router.dart`, con el mismo
> protocolo de §5: cada uno agrega su bloque al final de su sección y nadie reordena lo ajeno.
>
> Mientras la ficha no exista, el prototipo se abre desde una ruta suelta con un `varianteId`
> escrito a mano. **La costura no bloquea a nadie: es un punto de encuentro, no una espera.**

### 7.4 Lo que hay que decir del costo

El día 5 Mateo ya tiene CU-24, CU-25, los diagramas de EA y el CAP. 4.1 y 4.2. **El movimiento dos
le cae encima a él**, y es de las dos personas la que peor está de tiempo. Si el día 4 termina y el
prototipo no está andando, **el movimiento dos no se hace** y el prototipo se entrega aislado, como
estaba previsto. No se sacrifica ningún caso de uso del Ciclo 2 por esto.

La válvula de escape de §4.3 —CU-16 primero y CU-15 después a Karen— es lo que hay que usar si hace
falta comprar ese tiempo. Está acordada desde el 08/09 y todavía no se usó.

---

## 8. Impacto en el documento de entrega

Los casos de uso nuevos tocan secciones que **ya se entregaron completas el 05/09**:

| Sección | Qué hay que rehacer |
|---|---|
| 1.1.2 Casos de Uso | Agregar las filas CU-38 a CU-41 (más las opcionales) |
| 1.1.3 Requisitos Funcionales | Agregar RF37 a RF39 (más las opcionales) y corregir la traza de RF11 |
| 1.2 Priorización | Agregar las filas nuevas con su prioridad, ciclo y paquete |
| 1.3.2 Diagrama general de casos de uso | Regenerar con los nuevos — *script* de EA, de Mateo |
| 2.1.2 Matriz paquete–caso de uso | Agregar las columnas nuevas |
| 1.3.1, 2.2, 3.2 del Ciclo 3 | Las tablas y diagramas de los nuevos, cuando se implementen |

**Esto no es un parche que haya que disimular, y conviene decirlo así en la defensa.** El PUDS es
iterativo por definición: los requisitos se refinan ciclo a ciclo a medida que el sistema se
construye, y que la captura de requisitos se corrija en la elaboración es exactamente lo que el
proceso predice. Se anota como refinamiento del Ciclo 2 —igual que las categorías preferidas del
CU-04, que §6.11.3 difirió del Ciclo 1 a este— y queda mejor que si la lista hubiera salido
perfecta de una.

Lo que **no** hay que hacer es cambiar la granularidad de los 37 ya entregados. Eso sí sería
rehacer el capítulo entero, y §3.3 explica por qué no hace falta.

---

## 9. Resumen de lo que se propone

1. **La granularidad de los 37 no se toca.** La cuestión de los 30 casos de uso era falsa y el
   grupo de 70 cuenta los ABM por operación (§3).
2. **Se agregan cuatro casos de uso** —CU-38 a CU-41— que cierran tres agujeros reales: el actor
   Proveedor sin ningún caso de uso, el RF11 sin mecanismo de notificación, y la ausencia de
   recuperación de contraseña. Dos más quedan como opcionales (§5).
3. **Se numeran a continuación, sin renumerar nada.** Van todos al Ciclo 3, con un orden de
   sacrificio explícito que los pone detrás de lo que el enunciado exige (§5.2).
4. **CU-34 sube a prioridad Alta** y sale del orden de sacrificio; el proveedor de LLM se elige
   esta semana y se corrige la contradicción de §6.6 y `.env.example` (§6).
5. **El vestidor virtual se queda con Mateo.** El prototipo del día 4 se prueba contra el PNG real
   del *seed*, y si el día 4 cierra bien, el día 5 se enchufa el botón desde la ficha móvil.
   Costura **C5**, sin trabajo de *backend* (§7).
6. **§0.5 del índice oficial queda cerrada** con la respuesta de la ingeniera.

---

## 10. Qué hace falta de Mateo

1. **Aceptar o discutir los cuatro casos de uso nuevos**, y decir si los dos opcionales entran o se
   descartan de una vez.
2. **Decidir el proveedor de LLM**, o fijar el día en que se decide. Es lo único de todo este
   documento que ya está tarde.
3. **Decir si el movimiento dos del vestidor virtual (§7.2) le entra el día 5**, y si no,
   **usar la válvula de escape** y pasar CU-16 a Karen. Lo segundo no depende de lo primero.
4. Confirmar quién regenera el diagrama general de casos de uso con los nuevos: los *scripts* de EA
   son suyos por §2.3 de la contrapropuesta.

Nada de esto es un ultimátum, con el mismo criterio con el que él escribió el suyo: los seis puntos
de §9 se pueden dar vuelta. Lo único que no admite postergarse es el punto 2.
