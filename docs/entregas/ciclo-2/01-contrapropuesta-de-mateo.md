# CICLO 2 · Contrapropuesta al reparto por caso de uso

> **Respuesta de Mateo a [`00-organizacion-por-caso-de-uso.md`](00-organizacion-por-caso-de-uso.md).**
> El reparto de fondo se acepta: lo que cambia es **quién carga la infraestructura**, más el
> adelanto de RA e IA a este ciclo y la autoridad de Karen sobre el esquema del perfil del cliente.
>
> Escrito el **08/09/2026**. Sustituye a las §2.3, §7 y §8 del documento de Karen y a la última
> línea de su §5; todo lo demás de ese documento queda vigente tal cual.

---

## 1. Lo que se acepta sin discusión

Cuatro decisiones del documento de Karen son correctas y no se tocan:

1. **El caso de uso es la unidad de trabajo y es vertical** (§1). El argumento está en el propio
   historial: cada CU del Ciclo 1 necesitó dos commits de dos personas con una espera en medio.
2. **El corte por bloques cerrados de tabla** (§2). Las ocho tablas nuevas tienen exactamente un
   dueño cada una. No es un reparto arbitrario, está construido sobre una propiedad verificable.
3. **Los identificadores de revisión de Alembic acordados de antemano** (§4). Es la mejor idea del
   documento: rompe la linealidad de Alembic y deja las dos migraciones escribiéndose en paralelo.
4. **El protocolo de los cinco archivos compartidos** (§5). Verificado contra el código:
   `alembic/env.py` líneas 27/28/29 y `main.py` líneas 29/30/31 y 107/108/109 tienen las líneas
   comentadas exactamente donde el documento dice. El reparto es exacto y el conflicto es nulo.

También se acepta el argumento de §2.2 —reserva y existencia son la misma transacción y no se
reparten entre dos cabezas— y el de §10 para dejar CU-19 con Karen.

---

## 2. Lo que cambia — cinco movimientos

Ninguno toca la propiedad de tablas. Se mueve **infraestructura**, no dueños de datos.

### 2.1 · El *shell* móvil lo toma Mateo — y no es un *bootstrap*, es deuda del Ciclo 1

El documento asigna I1 a Karen con fecha límite el día 3, que es **hoy**, y `mobile/lib/` sigue
teniendo tres carpetas sin un solo `.dart`. Tres razones para moverlo:

**a) La herramienta y el dispositivo están de este lado.** En esta máquina hay **Flutter 3.47.2
(canal estable)** y un **teléfono físico conectado por `adb`**. El `README.md` de `mobile/` dice
todavía que «las carpetas de plataforma no existen porque Flutter no está instalado en la máquina
donde se generó la estructura»; eso ya no es cierto acá. Un `flutter create .` seguido de
`flutter run` sobre el teléfono real se puede hacer esta noche.

**b) El *shell* sin sesión no sirve para nada.** Un *bootstrap* que solo arranca una pantalla vacía
no desbloquea a nadie: todo lo que viene después —catálogo, ficha, disponibilidad, reservas,
vestidor virtual— cuelga del token. Lo que hace falta entregar es el *shell* **con sesión viva**:
cliente Dio con interceptor de JWT, `flutter_secure_storage`, `go_router` con guarda de sesión,
tema, y el manejo centralizado de errores de la API.

**c) Y eso obliga a cerrar tres casos de uso del Ciclo 1 que nunca tuvieron pantalla móvil.**

> **Respuesta a la pregunta de si hay que empezar ya con los CU del Ciclo 1: sí, con tres.**

De los nueve casos de uso del Ciclo 1, seis son de Administrador y son **solo web**. Los tres que
tienen actor **Cliente** son los que la app móvil necesita y nunca se construyeron:

| CU | Nombre | Actor | Alcance móvil del Ciclo 2 |
|---|---|:---:|---|
| **CU-01** | Registrar cliente | Cliente | Formulario de registro contra el alta de clientes |
| **CU-02** | Iniciar y cerrar sesión | Cliente | Login, guardado del token, cierre de sesión, renovación |
| **CU-04** | Gestionar perfil del cliente | Cliente | Datos personales, tallas habituales, direcciones y cambio de contraseña |

El `README.md` de `mobile/` ya los tenía anotados como `features/auth/ · ciclo 1`. No es alcance
nuevo: es alcance del Ciclo 1 que quedó sin entregar en la plataforma móvil, y hasta que exista no
hay ninguna pantalla móvil del Ciclo 2 que se pueda probar.

**La API contra la que se trabaja ya está desplegada:**
`https://ecomerceropavirtual-production.up.railway.app/api/v1`. No hace falta nada de nadie para
arrancar. CORS no aplica en una app nativa, así que tampoco hay que tocar `CORS_ORIGINS`.

**Fuera de alcance del *shell*:** las **categorías preferidas** del perfil (§3 de este documento)
son de Karen y van solo en web durante este ciclo; la pantalla móvil del CU-04 se construye sin ese
bloque y lo suma después, si hay tiempo.

**Se entrega el día 1 (09/09), no el día 3.** Es lo primero, porque bloquea a los dos.

### 2.2 · El prototipo del vestidor virtual (I3) va donde está el teléfono

Mismo motivo, y más fuerte: `google_mlkit_pose_detection` corre **en el dispositivo** sobre los
fotogramas de la cámara. Un emulador entrega una cámara sintética; no se puede validar ni la
detección de pose ni el encuadre del torso sin un teléfono real en la mano. El riesgo **R3** del
plan —«la realidad aumentada consume más tiempo del previsto **o no funciona en el dispositivo de
la defensa**»— se mitiga probando en el dispositivo de la defensa, que es el que está conectado acá.

El enfoque no se discute: sigue siendo la **opción B de §6.5** —superposición 2D guiada por pose—
que ya está decidida y cuyas dependencias ya están declaradas en `pubspec.yaml` (`camera`,
`google_mlkit_pose_detection`, `image`, `permission_handler`). No hay que elegir nada, hay que
construirlo.

**Alcance del prototipo en este ciclo** (aislado, sin integrar con el catálogo):

- [ ] Permiso de cámara y vista de cámara frontal en vivo.
- [ ] `google_mlkit_pose_detection` devolviendo puntos de hombros y caderas sobre cada fotograma.
- [ ] Cálculo de ancho, alto, centro e inclinación del torso a partir de esos cuatro puntos.
- [ ] Un `CustomPainter` que dibuja **un PNG de prueba con fondo transparente** transformado sobre
      esos valores, siguiendo el movimiento.
- [ ] Captura de la imagen resultante y medición de fotogramas por segundo en el teléfono real.

Lo que **no** entra: selector de talla y color, integración con la ficha de producto, ni «agregar a
la reserva». Eso es el CU-21 completo y es del Ciclo 3.

**Resultado esperado:** que al empezar el Ciclo 3 el CU-21 sea integración, no investigación.

### 2.3 · Los diagramas de EA (I4) vuelven a Mateo

Los once *scripts* `scripts/ea-*.ps1` y las 1309 líneas de `GUIA-DIAGRAMAS-EA.md` tienen un solo
autor. Ahí está el conocimiento más tácito del proyecto: que EA remaqueta los fragmentos del 3.2 al
volver a abrir el diagrama, que el estereotipo `FORM` se pasa a minúscula, que el círculo de
robustez solo se dibuja con los estereotipos en inglés, los cinco errores que arruinan el
despliegue, los tipos que EA 15 sí acepta. Transferir todo eso en un ciclo de cinco días no tiene
retorno.

**Se reparte así:** Mateo **genera** los diagramas del ciclo (extiende los *scripts* con los CU
nuevos y exporta); Karen **consolida** el `.docx`, el índice con F9 y la portada (I5), como ya
estaba previsto. Cada uno sigue redactando la sección de sus propios casos de uso.

### 2.4 · El *seed* (I2) pasa a Karen — y con eso desaparece la costura C3

El *seed* de ~60 productos siembra `producto`, `variante_producto` e `imagen_producto`: **las tres
son tablas de Karen**. Que lo escriba su dueña es lo natural, y la costura **C3 deja de existir**
—ya no hay que esperar a que la migración `0002` esté integrada, porque la escribe la misma persona
que escribe la migración—.

`backend/app/db/seed.py` pasa a ser **exclusivo de Karen** durante este ciclo, en lugar de exclusivo
de Mateo. El *seed* debe incluir, para al menos diez variantes, la **imagen PNG con fondo
transparente** que el vestidor virtual necesita (requisito S5 de §6.5): sin ella el prototipo de RA
se prueba con un activo de mentira.

### 2.5 · La IA arranca en este ciclo — y §6.6 hoy está en contra de la decisión ya tomada

El plan pone P10 entero en el Ciclo 3. Se adelanta **el inicio**, no los casos de uso: lo que se
construye ahora es el adaptador de proveedor y la elección del modelo, para que en el Ciclo 3 los
CU-33, CU-34 y CU-35 sean lógica de negocio y no una investigación de proveedores a cinco días de
la defensa.

**Hay una contradicción abierta en el repositorio que hay que cerrar.** El 04/09 se decidió que el
modelo de IA tiene que ser **gratuito, sin costo por uso** —el riesgo **R9** es justamente quedarse
sin crédito antes del 22/09—. Pero:

- `docs/06-decisiones-tecnicas.md` §6.6 sigue diciendo «**API de Claude (Anthropic)** […] modelo
  por defecto `claude-opus-5`».
- `backend/.env.example` sigue declarando `ANTHROPIC_API_KEY=` e `IA_MODELO=claude-opus-5`.

Los dos son de pago por *token*. Hay que reescribirlos.

**Dos tecnologías distintas, y a propósito:**

| Uso | Tecnología | Dónde corre | Costo |
|---|---|---|---|
| **RA · vestidor virtual (P9)** | `google_mlkit_pose_detection` (ML Kit) | En el teléfono | Ninguno, no hay API |
| **LLM · recomendador, asistente, reportes (P10)** | Proveedor con plan gratuito, por decidir | Solo desde el *backend* | Cero, dentro de la cuota |

La RA **no necesita ningún proveedor de IA**: la detección de pose es un modelo empaquetado que ML
Kit ejecuta en el dispositivo. Eso ya elimina de raíz el costo del riesgo técnico más alto, y es el
motivo por el que las dos mitades de «la IA del proyecto» se resuelven con tecnologías distintas.

**I7 (nuevo) · Prueba de concepto del proveedor de LLM — Mateo, día 4 (12/09).**

Candidatos: **Gemini** (plan gratuito de AI Studio) y **DeepSeek**. Se elige por prueba, no por
catálogo, y contra tres criterios en este orden:

1. **Uso de herramientas (*function calling*).** Es eliminatorio. El CU-34 y el CU-35 están
   diseñados en §6.6 sobre herramientas declaradas —`buscar_productos`,
   `consultar_disponibilidad`, `generar_reporte`…—, no sobre generación de SQL. Un proveedor que no
   las soporte de forma fiable obliga a rediseñar dos casos de uso.
2. **Cuota gratuita suficiente para una demostración en vivo** el 22/09, verificada en el momento de
   la prueba —los planes gratuitos cambian de condiciones y no se dan por sabidos—.
3. Latencia aceptable y SDK de Python o API REST simple.

**Lo que se entrega:** `backend/app/modules/ia/proveedor.py` con una interfaz única
—`completar(mensajes, herramientas)`— y **una** implementación concreta detrás; el resto del
sistema nunca ve el nombre del proveedor. Más las variables `IA_PROVEEDOR`, `IA_API_KEY` e
`IA_MODELO` en `.env.example` reemplazando a `ANTHROPIC_API_KEY`, un endpoint de diagnóstico y una
prueba de humo que hace una llamada real con una herramienta declarada.

**No entra nada de CU-33, CU-34 ni CU-35.** Solo el adaptador, el proveedor elegido y §6.6
reescrito. Si la prueba falla con los dos candidatos, la degradación de §6.6 punto 3 —recomendador
determinista por SQL, sin modelo— sigue siendo la red de seguridad y el proyecto no se cae.

---

## 3. Karen decide el esquema del perfil del cliente — autoridad plena

La §3 del documento de Karen congela las catorce tablas del Ciclo 1 y exige acuerdo previo para
tocarlas. **Para el perfil del cliente esa regla se levanta.**

El CU-04 quedó cortado a propósito en el Ciclo 1: §6.11.3 de `docs/06-decisiones-tecnicas.md`
difirió las **categorías preferidas** porque las categorías las crea el CU-08, que entonces no
existía. Ahora existe. Y al retomarlo van a aparecer más faltantes del mismo tipo, porque el flujo
principal del CU-04 promete «datos personales, tallas habituales, **preferencias** y direcciones» y
las preferencias nunca se modelaron enteras.

**Acuerdo:** Karen tiene **autoridad plena para agregar los campos y las tablas que considere
necesarios** en el alcance del perfil del cliente y su catálogo de preferencias —`cliente`,
`direccion_cliente`, `cliente_categoria` y cualquier tabla nueva que haga falta—. No necesita
consultar ni esperar. Las agrega a **su** migración `0002_ciclo2_catalogo` y las anota en §6.4 del
documento de organización cuando las fije.

La única condición es de forma, no de permiso: **los cambios son aditivos** —tablas nuevas y
columnas nuevas que admitan nulo, o con valor por defecto—. Renombrar o eliminar algo que ya existe
sí se avisa, porque `cliente.id` es clave foránea de `reserva` y romperlo deja al otro sin poder
migrar. Todo lo que agregue queda registrado en `docs/06-decisiones-tecnicas.md`, en la misma línea
de §6.11.3, para que el documento de la entrega lo explique.

---

## 4. Reparto resultante

### 4.1 Casos de uso — 7 y 7

| | Casos de uso | Total |
|---|---|:---:|
| **Karen** | CU-10 · CU-11 · **CU-14** · CU-17 · CU-18 · CU-19 · CU-04 *(preferencias)* | **7** |
| **Mateo** | CU-13 · CU-15 · CU-16 · CU-22 · CU-23 · CU-24 · CU-25 *(+ CU-01, CU-02 y CU-04 móviles)* | **7** |

**Único CU que se mueve: CU-14 (Consultar inventario consolidado), de Mateo a Karen.** Es el único
caso de uso de Mateo que es **solo de lectura** —no estrena ni escribe ninguna tabla—, así que
moverlo no toca la propiedad de datos. Agrupa además todas las vistas de lectura sobre `existencia`
(CU-14 y CU-19) en la misma persona y bajo el mismo contrato de la costura C1.

El bloque de escritura de inventario (CU-13, CU-15, CU-16) se queda entero con Mateo junto con las
reservas, que es el argumento de §2.2 del documento de Karen y sigue siendo válido.

### 4.2 Infraestructura

| # | Tarea | Antes | **Ahora** | Fecha |
|---|---|:---:|:---:|:---:|
| I1 | *Shell* móvil **+ CU-01, CU-02 y CU-04 móviles** | Karen | **Mateo** | día 1 · 09/09 |
| I2 | *Seed* completo, con PNG transparentes | Mateo | **Karen** | día 2 · 10/09 |
| I3 | Prototipo del vestidor virtual (RA) | Karen | **Mateo** | día 4 · 12/09 |
| I4 | Diagramas UML en EA | Karen | **Mateo** | continuo |
| I5 | Consolidación del `.docx`, índice, portada | Karen | Karen | día 5 · 13/09 |
| I6 | Redespliegue en Railway | Ambos | Ambos | continuo |
| **I7** | **Prueba y adaptador del proveedor de LLM** | — | **Mateo** | día 4 · 12/09 |

**CAP. 4 del documento:** 4.1 y 4.2 para Mateo, 4.3 y Anexos para Karen. Sin cambios.

### 4.3 El balance, dicho con franqueza

Mateo queda con **cuatro** piezas de infraestructura (I1, I3, I4, I7) contra **dos** de Karen
(I2, I5), aunque los casos de uso queden 7 a 7. Es deliberado —las cuatro dependen del teléfono
conectado o de los *scripts* de EA, y ninguna se puede hacer del otro lado sin pagar un costo de
transferencia—, pero es una carga real y hay que decirla en voz alta, no esconderla en un empate
de tabla.

**Válvula de escape, en este orden:** si el día 3 (11/09) Mateo va retrasado, pasa **CU-16**
(disponibilidad de la sucursal) a Karen; si sigue retrasado, pasa **CU-15**. Los dos escriben sobre
tablas de Mateo, así que el traspaso incluye ceder la propiedad de escritura de esa tabla por lo
que reste del ciclo, y se anota acá cuando ocurra.

---

## 5. Propiedad de tablas — actualizada

Sin cambios respecto de §3 de Karen, salvo lo que ella agregue por §3 de este documento:

| Tabla | Dueño | Migración |
|---|:---:|:---:|
| `producto`, `variante_producto`, `imagen_producto` | **Karen** | `0002_ciclo2_catalogo` |
| `cliente_categoria` **y lo que Karen agregue al perfil** | **Karen** | `0002_ciclo2_catalogo` |
| `existencia`, `movimiento_inventario` | **Mateo** | `0003_ciclo2_inv_res` |
| `reserva`, `reserva_detalle` | **Mateo** | `0003_ciclo2_inv_res` |

Los identificadores de revisión y su encadenamiento quedan **exactamente** como los fijó §4 de
Karen. La regla de escribir las migraciones a mano, sin `--autogenerate`, también.

---

## 6. Costuras — quedan dos, no tres

| | Costura | Estado |
|---|---|---|
| **C1** | `existencia` ← CU-19 y CU-14 (Karen consume de Mateo) | **Vigente.** Mismo contrato de §6.1: Mateo expone `disponibilidad_por_sucursal(db, variante_id)` en `inventario/service.py` y agrega `inventario_consolidado(db, filtros)` para el CU-14. Karen las importa; no hace `SELECT` sobre tablas ajenas ni llamadas HTTP internas. Mientras no existan, maqueta contra un *stub* con esa forma. |
| **C2** | `variante_producto` ← CU-22 (Mateo consume de Karen) | **Vigente.** Karen publica hoy en §6.4 el nombre de la tabla, el de su clave primaria y el del campo `sku`. Mateo escribe la clave foránea contra ese nombre. |
| **C3** | *Seed* ← productos | **Eliminada** por §2.4 de este documento. |
| **C4** | *Shell* móvil ← pantallas móviles de los dos | **Eliminada como espera.** Era la costura que el documento de Karen no listaba, pese a admitir que «bloquea las pantallas móviles de los dos». Se resuelve entregándola el día 1 y del lado que tiene el dispositivo. |

`app.routes.ts` y el router de Flutter siguen con el protocolo de §5: cada uno agrega su bloque al
final de su sección, nadie reordena lo ajeno, `git pull --rebase` antes de cada push. El
`mobile/lib/core/enrutado/router.dart` lo **crea** Mateo el día 1 con las dos secciones ya
separadas y comentadas, para que Karen solo agregue las suyas.

---

## 7. Calendario recomprimido — cinco días, no ocho

El calendario de §8 arranca el día 1 el 06/09, pero el documento se escribió el 08/09. Los días 1,
2 y 3 —modelos, ambas migraciones, CU-10, CU-11, CU-13, CU-14, CU-15 y el *bootstrap*— vencieron
antes de acordarse. Quedan **cinco días** hasta el domingo **13/09 a las 23:59**.

| Día | Karen | Mateo |
|:---:|---|---|
| **1** · 09/09 | Fijar §6.4 · modelos del catálogo y del perfil · migración `0002` | Fijar §6.4 · modelos `existencia`/`movimiento`/`reserva`/`detalle` · migración `0003` · **I1 *shell* móvil + CU-01 y CU-02 móviles** |
| **2** · 10/09 | **CU-10** completo · **I2 *seed*** | **CU-13** completo · **CU-15** |
| **3** · 11/09 | **CU-11** · **CU-04** preferencias | **CU-16** · **CU-22** *backend* (con `FOR UPDATE`, riesgo R5) · **CU-04 móvil** |
| **4** · 12/09 | **CU-17** + **CU-18** web y móvil | **CU-22** + **CU-23** web y móvil · **I3 prototipo RA** · **I7 proveedor de LLM** |
| **5** · 13/09 | **CU-19** + **CU-14** (costura C1) · **I5 consolidación del `.docx`** | **CU-24** + **CU-25** · diagramas EA · CAP. 4.1 y 4.2 |

**Congelamiento de código: 13/09 a las 18:00.** Se mantiene, para dejar margen al despliegue y al
documento.

Los dos días que absorbe cada uno salen de que el *seed* y el *shell* dejaron de ser tareas sueltas
y se hacen el mismo día que el trabajo que las necesita.

---

## 8. Definición de «hecho» — dos casillas nuevas

Las ocho casillas de §9 del documento de Karen se mantienen. Se agregan dos:

- [ ] **Probado sobre el teléfono real**, no sobre el emulador, si el caso de uso tiene pantalla
      móvil.
- [ ] **Ninguna clave de API en el repositorio.** Todo lo de IA vive en variables de entorno; el
      cliente web y la app móvil nunca llaman al proveedor directamente (§6.6).

Y se corrige una: la casilla «pantalla móvil, si el actor es Cliente» solo se puede marcar a partir
del día 1, cuando el *shell* exista. Antes de eso ningún caso de uso móvil está «hecho», por
completo que esté su *backend*.

---

## 9. Lo que hay que cambiar en el repositorio si esto se acepta

| Archivo | Cambio |
|---|---|
| `docs/06-decisiones-tecnicas.md` §6.6 | Reescribir: proveedor gratuito por decidir en I7, no Claude ni `claude-opus-5` |
| `backend/.env.example` | `ANTHROPIC_API_KEY` e `IA_MODELO=claude-opus-5` → `IA_PROVEEDOR`, `IA_API_KEY`, `IA_MODELO` |
| `docs/06-decisiones-tecnicas.md` §6.11.3 | Cerrar el diferimiento: las categorías preferidas se implementan, con la autoridad de §3 |
| `mobile/README.md` | Quitar «Flutter no está instalado»; documentar el *shell* y el arranque sobre el teléfono |
| `docs/05-plan-y-cronograma.md` §5.4 | Apuntar también a este documento, junto al de Karen |
| `docs/entregas/ciclo-2/00-organizacion-por-caso-de-uso.md` | Nota al inicio remitiendo a este documento en §2.3, §5, §7 y §8 |

---

## 10. Qué hace falta de Karen para cerrar el acuerdo

Tres cosas, hoy:

1. **Aceptar o discutir los cinco movimientos de §2.** El más discutible es el 2.3 (EA); los otros
   cuatro se apoyan en dónde está el hardware o en quién es dueño de las tablas.
2. **Llenar §6.4 del documento de organización** con los nombres definitivos de `producto`,
   `variante_producto`, `imagen_producto` y de lo que agregue al perfil. Mateo necesita el nombre
   de la tabla de variantes y el de su clave primaria para escribir la clave foránea de
   `reserva_detalle` — es la costura **C2** y es lo único que lo bloquea el día 1.
3. **Confirmar que toma el *seed* (I2)** con los PNG de fondo transparente incluidos, porque de eso
   depende que el prototipo de RA del día 4 se pruebe con prendas de verdad.
