# CICLO 2 · Organización del trabajo por caso de uso

> **Documento de acuerdo entre los dos integrantes.** Fija quién hace qué, quién es dueño de qué
> tabla y en qué orden se ataca el ciclo. Reemplaza el reparto por capas de la tabla de
> responsabilidades de [`docs/05-plan-y-cronograma.md`](../../05-plan-y-cronograma.md) §5.4 para
> lo que dure el Ciclo 2.
>
> **Rama de trabajo:** `Ciclo2`. Entrega: Presentación #2.
>
> ---
>
> **Este documento ya no se lee solo.** Mateo respondió con una contrapropuesta —
> [`01-contrapropuesta-de-mateo.md`](01-contrapropuesta-de-mateo.md) — que Karen **acató el
> 09/09/2026**. Acepta el fondo de este documento (§1, §2, §3, §4, §5 y §6) y **sustituye** cuatro
> partes suyas:
>
> | Sección de acá | Qué la reemplaza |
> |---|---|
> | **§2.3** Balance | §4.1 y §4.3 de la contrapropuesta — casos de uso 7 a 7; **CU-14 pasa a Karen** |
> | **§5**, última línea (`seed.py` de Mateo) | §2.4 — el *seed* es de **Karen**, y con eso la costura **C3 desaparece** |
> | **§7** Trabajo que no es un caso de uso | §4.2 — **I1, I3 e I4 son de Mateo**; I2 e I5 de Karen |
> | **§8** Orden de arranque | §7 — calendario recomprimido a **cinco días: 09/09 – 13/09/2026** |
>
> Todo lo demás de este documento sigue vigente tal cual, incluida la **§6.4**, que es la única
> sección que se llenó después: los nombres de las tablas quedaron fijados el 09/09.

---

## 1. Qué cambia respecto del Ciclo 1

En el Ciclo 1 el trabajo se dividió **por capa**: Mateo la API, Karen la web. Funcionó para nueve
CRUD, pero tuvo un costo visible en el propio historial del repositorio: cada caso de uso necesitó
dos commits de dos personas distintas (`feat(seguridad): ... en la API` / `... en la web`), y entre
uno y otro hubo una espera. Con trece casos de uso, reglas de negocio reales y una aplicación móvil
que todavía no existe, esa espera ya no cabe en el cronograma.

**Regla nueva del Ciclo 2: el caso de uso es la unidad de trabajo, y es vertical.**

Quien toma un caso de uso lo entrega **completo y funcionando**:

| Capa | Qué incluye |
|---|---|
| **Datos** | Modelo SQLAlchemy y migración Alembic de las tablas que el caso de uso estrena |
| **Backend** | `schemas.py`, `repository.py`, `service.py`, `router.py` y el montaje en `main.py` |
| **Pruebas** | Al menos una prueba por flujo alternativo del caso de uso, en `backend/tests/` |
| **Web** | Componentes Angular, servicio HTTP, modelos TypeScript y ruta con su guarda de rol |
| **Móvil** | Pantalla Flutter, si el caso de uso tiene actor Cliente (los de Administrador y Encargado son solo web) |
| **Documento** | Detalle 1.3.1, diagrama 1.3.2, comunicación 2.2, secuencia 3.2 y prototipo 1.4 de **ese** caso de uso |

**Corolario — cada uno es dueño de sus tablas.** El que estrena una tabla escribe su modelo, su
migración y es el único que la modifica durante el ciclo. Nadie hace `autogenerate` sobre tablas
ajenas ni edita el `models.py` de un módulo que no le toca. Es la misma regla que el Ciclo 1 aplicó
sobre `models.py`, ahora repartida en vez de centralizada.

---

## 2. Reparto de los trece casos de uso

**Criterio del corte:** no se repartieron casos de uso sueltos, sino **bloques cerrados por tabla**.
Un bloque agrupa todos los casos de uso que escriben sobre las mismas tablas, para que ninguna tabla
tenga dos dueños. De ahí salen dos mitades con sentido propio: **Karen es dueña del producto y de su
vitrina**; **Mateo es dueño del stock y de la reserva**.

### 2.1 Karen — Catálogo y vitrina (P3 productos + P5)

| CU | Nombre | Paq. | Tablas propias | Web | Móvil |
|---|---|:---:|---|:---:|:---:|
| **CU-10** | Gestionar productos y variantes | P3 | `producto`, `variante_producto` | ✔ Admin | — |
| **CU-11** | Gestionar imágenes de producto | P3 | `imagen_producto` | ✔ Admin | — |
| **CU-17** | Consultar catálogo | P5 | — (solo lectura) | ✔ Cliente | ✔ |
| **CU-18** | Consultar ficha de producto | P5 | — (solo lectura) | ✔ Cliente | ✔ |
| **CU-19** | Consultar disponibilidad por sucursal | P5 | — (lee `existencia`) | ✔ Cliente | ✔ |
| **CU-04** *(resto)* | Categorías preferidas del perfil | P1 | `cliente_categoria` | ✔ Cliente | — |

**Por qué este bloque es coherente:** es la cadena completa `producto → variante → imagen → vitrina
→ ficha`. Karen crea las tres tablas del catálogo y después es la única que las consume desde el
lado del cliente; no hay ida y vuelta con nadie. Además `imagen_producto` incluye la imagen con
fondo transparente que necesita el vestidor virtual, que también es suyo.

### 2.2 Mateo — Stock y reservas (P4 + P6)

| CU | Nombre | Paq. | Tablas propias | Web | Móvil |
|---|---|:---:|---|:---:|:---:|
| **CU-13** | Registrar ingreso de mercadería | P4 | `existencia`, `movimiento_inventario` | ✔ Admin/Enc. | — |
| **CU-14** | Consultar inventario consolidado | P4 | — | ✔ Admin | — |
| **CU-15** | Registrar movimiento de inventario | P4 | — | ✔ Admin | — |
| **CU-16** | Gestionar disponibilidad de la sucursal | P4 | — | ✔ Encargado | — |
| **CU-22** | Crear reserva de prendas | P6 | `reserva`, `reserva_detalle` | ✔ Cliente | ✔ |
| **CU-23** | Consultar y cancelar reserva | P6 | — | ✔ Cliente | ✔ |
| **CU-24** | Atender reserva en sucursal | P6 | — | ✔ Encargado | — |
| **CU-25** | Expirar reservas vencidas | P6 | — | — (tarea programada) | — |

**Por qué este bloque es coherente:** cada transición de una reserva produce un movimiento de
inventario (§4.1.1, P6). Reserva y existencia son la misma regla de negocio vista dos veces
—incluido el `SELECT ... FOR UPDATE` del riesgo R5— y separarlas entre dos personas sería repartir
una transacción en dos cabezas.

### 2.3 Balance

| | Casos de uso | Trabajo adicional |
|---|:---:|---|
| **Karen** | 6 | Bootstrap de la app Flutter · Prototipo del vestidor virtual (R3) · Diagramas en EA · Consolidación del `.docx` |
| **Mateo** | 8 | *Seed* completo (3 ciudades, 5 sucursales, 4 proveedores, ~60 productos con variantes, imágenes y stock) |

Mateo lleva dos casos de uso más porque Karen carga con las dos piezas de infraestructura del ciclo
—la app móvil, que hoy está en cero, y el prototipo de realidad aumentada, que es el riesgo técnico
más alto del proyecto— más la consolidación del documento.

---

## 3. Propiedad de las tablas

Ocho tablas nuevas. Ninguna tiene dos dueños.

| Tabla | La estrena | Dueño | Migración |
|---|:---:|:---:|:---:|
| `producto` | CU-10 | **Karen** | `0002` |
| `variante_producto` | CU-10 | **Karen** | `0002` |
| `imagen_producto` | CU-11 | **Karen** | `0002` |
| `cliente_categoria` | CU-04 | **Karen** | `0002` |
| `existencia` | CU-13 | **Mateo** | `0003` |
| `movimiento_inventario` | CU-13 | **Mateo** | `0003` |
| `reserva` | CU-22 | **Mateo** | `0003` |
| `reserva_detalle` | CU-22 | **Mateo** | `0003` |

Las catorce tablas del Ciclo 1 quedan **congeladas**: si un caso de uso del Ciclo 2 necesita una
columna nueva en una tabla del Ciclo 1, se acuerda entre los dos antes de tocarla y se registra en
`docs/06-decisiones-tecnicas.md`.

### 3.1 Archivos de modelo — sin colisión

Cada módulo ya tiene su propio `models.py`, así que las dos personas escriben en archivos distintos:

```
Karen                                     Mateo
  app/modules/catalogo/models.py            app/modules/inventario/models.py
  app/modules/seguridad/models.py           app/modules/reservas/models.py
```

`app/modules/catalogo_publico/models.py` **queda vacío**: P5 no tiene entidades propias, solo lee
las de P3 y P4.

---

## 4. Migraciones — cadena y acuerdo previo

Alembic es lineal: `0003` declara `down_revision = "0002_ciclo2_catalogo"`. Eso haría que Mateo
tuviera que esperar a que la migración de Karen esté en la rama antes de escribir la suya.

**Se evita acordando los identificadores de revisión el primer día, antes de escribir nada:**

| Archivo | `revision` | `down_revision` | Autor |
|---|---|---|:---:|
| `0002_ciclo2_catalogo.py` | `0002_ciclo2_catalogo` | `0001_ciclo1` | Karen |
| `0003_ciclo2_inventario_reservas.py` | `0003_ciclo2_inv_res` | `0002_ciclo2_catalogo` | Mateo |

Con los identificadores fijados, **las dos migraciones se escriben en paralelo desde el día 1** y se
integran en ese orden. Mateo puede declarar la clave foránea `existencia.variante_id →
variante_producto.id` sin que la tabla exista todavía en su copia, porque el nombre está acordado en
§6.4.

**Regla:** las migraciones del Ciclo 2 se escriben **a mano**, no con `--autogenerate`. Autogenerar
con los modelos del otro a medio escribir produce migraciones que borran tablas ajenas.

---

## 5. Archivos compartidos y protocolo para no chocar

Hay cinco archivos que las dos personas tocan. Cuatro ya vienen preparados con las líneas escritas y
comentadas desde el Ciclo 1, así que cada uno **descomenta solo su línea** y el conflicto es nulo:

| Archivo | Karen descomenta | Mateo descomenta |
|---|---|---|
| `backend/alembic/env.py` | línea 28 (`catalogo_publico`) | líneas 27 y 29 (`inventario`, `reservas`) |
| `backend/app/main.py` — imports | línea 30 (`catalogo_publico_router`) | líneas 29 y 31 (`inventario`, `reservas`) |
| `backend/app/main.py` — `include_router` | línea 108 | líneas 107 y 109 |
| `frontend-web/src/app/app.routes.ts` | rutas `tienda/**` y `mi-cuenta/**` | rutas `admin/inventario`, `sucursal/**`, `mi-cuenta/reservas` |
| `mobile/lib/core/enrutado/router.dart` | rutas de catálogo | rutas de reservas |

Los dos únicos con riesgo real son `app.routes.ts` y el router de Flutter. Protocolo: **cada uno
agrega su bloque de rutas al final de su sección y nunca reordena las ajenas**; `git pull --rebase`
antes de cada push.

`backend/app/db/seed.py` es **exclusivo de Mateo** durante este ciclo.

---

## 6. Las costuras — los tres puntos donde uno depende del otro

Solo hay tres. Cada uno se resuelve con un contrato acordado el día 1, no con una espera.

### C1 · `existencia` ← CU-19 (Karen consume de Mateo)

CU-19 muestra al cliente en qué sucursales hay stock de una variante. La tabla es de Mateo.

**Contrato:** Mateo expone en `app/modules/inventario/service.py` una función de consulta que Karen
importa desde `catalogo_publico/service.py` — no una llamada HTTP interna, no un `SELECT` de Karen
sobre una tabla ajena:

```python
def disponibilidad_por_sucursal(db: Session, variante_id: int) -> list[DisponibilidadSucursal]
# -> [{sucursal_id, sucursal_nombre, ciudad_nombre, cantidad_disponible}]
```

Mientras no exista, Karen maqueta CU-19 contra un *stub* que devuelve esa forma.

### C2 · `variante_producto` ← CU-22 (Mateo consume de Karen)

La reserva referencia variantes. **Contrato:** Karen fija y publica el nombre de la tabla, el de su
clave primaria y el del campo `sku` **el día 1**, en §6.4, antes de escribir el modelo. Mateo
escribe su clave foránea contra ese nombre.

### C3 · *Seed* ← productos (Mateo consume de Karen)

El *seed* de ~60 productos con variantes es de Mateo, pero siembra tablas de Karen. **Contrato:** el
*seed* se escribe **después** de que la migración `0002` esté integrada en `Ciclo2` (día 2), y Karen
no cambia la forma de esas tablas después de ese punto sin avisar.

### 6.4 Nombres acordados — fijados el 09/09/2026

> **Vinculante para los dos.** Karen fija acá las cuatro tablas del catálogo y del perfil; las
> cuatro de Mateo quedan como estaban. Lo que Mateo necesita para desbloquear la costura **C2** es
> la primera línea de la segunda tabla: **`variante_producto`, clave primaria `id` (`BIGINT`)**, y
> el campo **`sku VARCHAR(40)`**. A partir de acá, cambiar un nombre de esta sección se avisa;
> agregar columnas nuevas, no.

**Convenciones heredadas del Ciclo 1**, que estas tablas respetan:

- Nombres de tabla en **singular y minúscula**; la clave primaria siempre se llama `id`.
- **`BIGINT`** en las entidades que crecen con el uso (`usuario`, `cliente`, `empleado`,
  `proveedor`); **`INTEGER`** en los catálogos chicos (`categoria`, `talla`, `color`, `ciudad`,
  `sucursal`). Producto, variante e imagen son de las primeras.
- Mixin `Auditoria` (`creado_en`, `actualizado_en`) en todo lo que se edita.
- Los nombres de índices y restricciones los genera la convención de `app/db/base.py`; las que
  llevan nombre propio se declaran en `__table_args__`.

#### Tablas de Karen — migración `0002_ciclo2_catalogo`

```
producto              id              BIGINT        PK
                      codigo          VARCHAR(30)   UNIQUE, codigo interno de la prenda
                      nombre          VARCHAR(120)
                      descripcion     VARCHAR(500)  NULL
                      categoria_id    INTEGER       FK categoria.id, indexado
                      proveedor_id    BIGINT        FK proveedor.id, NULL, indexado
                      temporada_id    INTEGER       FK temporada.id, NULL, indexado
                      coleccion_id    INTEGER       FK coleccion.id, NULL, indexado
                      precio_base     NUMERIC(10,2) precio sugerido de las variantes
                      activo          BOOLEAN       default true
                      + creado_en, actualizado_en

variante_producto     id              BIGINT        PK        <-- lo que pide la costura C2
                      producto_id     BIGINT        FK producto.id ON DELETE CASCADE, indexado
                      talla_id        INTEGER       FK talla.id, indexado
                      color_id        INTEGER       FK color.id, indexado
                      sku             VARCHAR(40)   UNIQUE     <-- codigo propio de la variante
                      precio          NUMERIC(10,2) NOT NULL
                      activa          BOOLEAN       default true
                      + creado_en, actualizado_en
                      UNIQUE (producto_id, talla_id, color_id)

imagen_producto       id              BIGINT        PK
                      producto_id     BIGINT        FK producto.id ON DELETE CASCADE, indexado
                      variante_id     BIGINT        FK variante_producto.id ON DELETE CASCADE,
                                                    NULL, indexado
                      ruta            VARCHAR(255)  ruta en el volumen, no la imagen (§6.8)
                      es_principal    BOOLEAN       default false
                      es_transparente BOOLEAN       default false  <-- PNG del vestidor (S5)
                      orden           SMALLINT      default 0
                      + creado_en, actualizado_en
                      indice parcial UNIQUE (producto_id) WHERE es_principal
                      indice parcial UNIQUE (variante_id) WHERE es_transparente

cliente_categoria     cliente_id      BIGINT        FK cliente.id ON DELETE CASCADE
                      categoria_id    INTEGER       FK categoria.id ON DELETE CASCADE
                      PK compuesta (cliente_id, categoria_id), sin columnas propias
```

#### Tablas de Mateo — migración `0003_ciclo2_inv_res`

Sin cambios; se repiten para que esta sección sea el único lugar que hay que mirar.

```
existencia            (id, variante_id, sucursal_id, cantidad_disponible,
                       cantidad_reservada, ...)
movimiento_inventario (id, existencia_id, tipo, cantidad, motivo, usuario_id, creado_en)
reserva               (id, cliente_id, sucursal_id, franja_inicio, franja_fin, estado, ...)
reserva_detalle       (id, reserva_id, variante_id, cantidad, resultado_prueba?)
```

`existencia.variante_id` y `reserva_detalle.variante_id` son **`BIGINT`** y apuntan a
`variante_producto.id`.

#### Las cinco decisiones que no se leen en la tabla

1. **La variante lleva `precio` obligatorio, y `producto.precio_base` es solo el sugerido.** Lo pide
   la decisión **D1** de §4.2.1: la variante es la unidad de negocio y es la que tiene precio,
   existencia, reserva y venta. Al generar las variantes de un producto, el servicio copia
   `precio_base` en cada una; después cada variante se mueve sola. Cambiar `precio_base` no
   repropaga hacia atrás, a propósito: si lo hiciera, cambiaría el precio de variantes ya vendidas.

2. **`producto` guarda `temporada_id` y `coleccion_id` a la vez, y las dos admiten nulo.** Es
   redundante —una colección ya pertenece a una temporada— pero un producto puede estar en una
   temporada sin pertenecer a ninguna colección, y la rotación por temporada es lo que justifica
   `temporada` en el modelo. **Se evaluó derivar la temporada de la colección y se decidió
   conservar la redundancia** (Karen, 09/09/2026): derivarla obligaría a crear una colección
   ficticia para cada producto suelto, o a dejar sin temporada a los productos que no pertenecen a
   ninguna colección, y son justamente los que el reporte de rotación no puede perder.

   El precio de conservarla es que las dos columnas pueden contradecirse, así que la coherencia se
   vuelve responsabilidad explícita del servicio de CU-10: **si vienen las dos,
   `coleccion.temporada_id` tiene que coincidir con `producto.temporada_id`**, y si viene solo la
   colección, la temporada se completa a partir de ella en vez de quedar nula. No se declara como
   restricción en la base porque exigiría una clave foránea compuesta sobre `coleccion` y un
   `trigger` para cada cambio de la colección; con dos columnas y una regla de servicio se resuelve
   igual y se lee mejor. Es el único punto del esquema donde se aceptó una redundancia, y queda
   anotado para que no parezca un descuido.

3. **`imagen_producto.variante_id` admite nulo, y eso distingue los dos tipos de imagen.** Con nulo,
   la imagen es del producto en general y sirve para el listado del catálogo; con valor, es de una
   combinación talla × color concreta. El índice parcial sobre `es_transparente` garantiza **como
   máximo un PNG transparente por variante**, que es el activo del que depende el vestidor virtual
   (§6.5, supuesto S5): si el prototipo de RA no encuentra imagen, es un dato que falta y no un
   error de código. Los dos índices parciales copian el patrón que el Ciclo 1 ya usa en
   `uq_direccion_predeterminada`.

4. **La imagen guarda `ruta`, no `url`.** §6.8 decidió el volumen persistente de Railway montado en
   `/app/media`, con la base guardando únicamente la ruta. Poner `url` invitaría a escribir el
   dominio en la base y ataría los datos al despliegue actual; si algún día se pasa a Supabase
   Storage o a Cloudinary, se cambia quién sirve el archivo y no todas las filas.

5. **`cliente_categoria` no lleva mixin de auditoría ni `id` propio.** Es una tabla puente sin
   atributos, igual que `rol_permiso` del Ciclo 1, y se declara con `Table(...)` y no con una
   clase. Cierra el diferimiento de §6.11.3 de las decisiones técnicas, que dejó las categorías
   preferidas para este ciclo porque en el Ciclo 1 todavía no existían categorías que elegir.

#### Lo que la autoridad de §3 de la contrapropuesta **no** hace falta usar todavía

El perfil del cliente no necesita más tablas que `cliente_categoria`. Los otros tres bloques que
promete el flujo principal del CU-04 —datos personales, tallas habituales y direcciones— ya están
modelados en `cliente` y `direccion_cliente` desde el Ciclo 1, y Mateo los cubrió en la pantalla
móvil. Si al implementar aparece algo más, se agrega a la `0002` sin consultar y se anota acá.

**Una arruga conocida, que no se toca en este ciclo:** `cliente.talla_superior`, `talla_inferior` y
`talla_calzado` son `VARCHAR(10)` de texto libre, de cuando `talla` todavía no era una entidad.
Ahora lo es, y el recomendador del CU-33 va a querer cruzarlas con `talla.id`. Convertirlas en
claves foráneas **no es un cambio aditivo**, así que queda fuera del alcance del Ciclo 2 y se
decide entre los dos antes del Ciclo 3.

---

## 7. Trabajo que no es un caso de uso

| # | Tarea | Responsable | Fecha límite | Por qué importa |
|---|---|:---:|:---:|---|
| I1 | **Bootstrap de la app Flutter**: `flutter create`, cliente Dio con interceptor de JWT, `go_router`, `flutter_secure_storage`, y **login + registro contra la API ya desplegada** | Karen | **día 3 (08/09)** | `mobile/lib/` hoy solo tiene `.gitkeep`. Bloquea las pantallas móviles de **los dos** (CU-17/18/19 de Karen y CU-22/23 de Mateo) |
| I2 | *Seed* completo con ~60 productos, variantes, imágenes y stock distribuido | Mateo | día 4 (09/09) | Sin datos no hay catálogo demostrable ni reserva que probar |
| I3 | **Prototipo aislado del vestidor virtual** (cámara + detección de pose, sin integrar) | Karen | día 7 (12/09) | Riesgo **R3**. El cronograma es explícito: se construye en el Ciclo 2, no en el 3 |
| I4 | Diagramas UML del ciclo en Enterprise Architect (`scripts/ea-*.ps1`) | Karen | continuo | — |
| I5 | Consolidación del `.docx`, índice con F9, portada | Karen | día 8 (13/09) | — |
| I6 | Redespliegue en Railway al cierre de cada bloque | Ambos | continuo | Riesgo **R2** |

**Documentación: cada uno redacta la de sus propios casos de uso**, el mismo día que cierra el caso
de uso — no al final. Karen dibuja en EA y consolida; Mateo revisa y valida, como en el Ciclo 1.
El CAP. 4 (Implementación), la Bibliografía y los Anexos, que se estrenan en este ciclo, se
reparten: 4.1 Selección de plataforma y 4.2 Arquitectura principal para Mateo; 4.3 Arquitectura de
subsistemas y los Anexos para Karen.

---

## 8. Orden de arranque

| Día | Karen | Mateo |
|:---:|---|---|
| **1** · 06/09 | Acordar §6.4 · modelos `producto`/`variante`/`imagen`/`cliente_categoria` · migración `0002` | Acordar §6.4 · modelos `existencia`/`movimiento`/`reserva`/`detalle` · migración `0003` |
| **2** · 07/09 | **CU-10** backend + web | **CU-13** backend + web (ingreso de mercadería) |
| **3** · 08/09 | **CU-11** backend + web · **I1 bootstrap Flutter** | **CU-15** + **CU-14** backend + web |
| **4** · 09/09 | **CU-17** + **CU-18** backend (`/tienda`) | **I2 seed** · **CU-16** backend + web |
| **5** · 10/09 | **CU-17** + **CU-18** web y móvil | **CU-22** backend (con `FOR UPDATE`, riesgo R5) |
| **6** · 11/09 | **CU-19** (costura C1) · **CU-04** categorías preferidas | **CU-22** + **CU-23** web y móvil |
| **7** · 12/09 | **I3 prototipo del vestidor virtual** | **CU-24** + **CU-25** backend + web |
| **8** · 13/09 | Diagramas, consolidación del `.docx`, despliegue | CAP. 4, revisión, despliegue |

**Congelamiento de código: 13/09 a las 18:00**, para dejar margen al despliegue y al documento.

---

## 9. Definición de «hecho» de un caso de uso

Un caso de uso no se declara terminado hasta que las ocho casillas están marcadas:

- [ ] Migración escrita a mano y aplicada sin error, con su `downgrade`
- [ ] `schemas` · `repository` · `service` · `router`, montado en `main.py`
- [ ] Exigencia de rol declarada en el *router* (y `consulta_router` aparte si otro rol necesita leer — ver §6.11.4 de decisiones técnicas)
- [ ] Pruebas del flujo principal y de los alternativos en `backend/tests/`
- [ ] Pantalla web con su ruta y su guarda de rol
- [ ] Pantalla móvil, si el actor es Cliente
- [ ] Sección del documento redactada y diagramas generados
- [ ] Desplegado en Railway y probado sobre la URL pública

**Un commit por caso de uso completo**, con el mismo formato del Ciclo 1:
`feat(<paquete>): <nombre del caso de uso> (CU-NN)`.

---

## 10. Si el reparto no convence — el corte alternativo

El punto discutible es **CU-19**, que es de Karen pero lee la tabla de Mateo (costura C1). Si esa
dependencia molesta, se mueve CU-19 a Mateo: desaparece la única costura de lectura cruzada, pero el
reparto queda 5 contra 9 y la ficha de producto (CU-18, Karen) y su bloque de disponibilidad
(CU-19, Mateo) pasan a ser dos personas en la misma pantalla — una costura de UI, que es más cara de
integrar que una de datos. **Por eso se eligió dejar CU-19 con Karen.**

El otro ajuste posible, si el día 5 Karen va retrasada por el bootstrap de Flutter, es pasarle
**CU-11** (imágenes) a Mateo: es el caso de uso más aislado de los seis y el único que no forma
parte de la cadena de la vitrina.
