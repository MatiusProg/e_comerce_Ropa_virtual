# CU-38 · Registrar productos del proveedor

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-38 |
| **Nombre** | Registrar productos del proveedor |
| **Descripción** | Permite al Proveedor registrar o enviar la información de los productos que abastece y asociarlos a una temporada y una colección, con alcance limitado a los suyos. |
| **Propósito** | Que el Proveedor deje de ser un actor que no inicia nada, y que la tienda reciba la información de lo que se le abastece sin cargarla a mano. |
| **Actores** | Proveedor (iniciador) · Administrador (secundario: publica) |
| **Paquete** | P2 · Organización *(los datos viven en P3)* |
| **Prioridad** | Media |
| **Requisitos que realiza** | **RF37** |
| **Precondiciones** | El Proveedor tiene sesión iniciada y su usuario está vinculado a una ficha de proveedor activa (CU-07, flujo 3c). |
| **Postcondiciones** | El producto queda registrado a nombre de ese proveedor, **sin publicar**, con sus combinaciones de talla y color declaradas. |

**Flujo principal**

1. El Proveedor abre *Mis productos* y ve lo que ya registró.
2. El sistema lista únicamente los productos de ese proveedor, paginados.
3. El Proveedor elige *Registrar producto*.
4. El Proveedor completa código, nombre, categoría, precio de referencia y —opcionalmente— temporada y colección.
5. El sistema valida, registra el producto **a nombre de quien lo envía y sin publicar**, y lo confirma.
6. El sistema ofrece declarar las tallas y colores en las que se abastece.
7. El Proveedor elige tallas y colores; el sistema genera una combinación (SKU) por cada par.
8. El Administrador revisa y publica el producto (CU-10), que entonces aparece en el catálogo.

**Flujos alternativos**

- **3a. Corregir un producto propio.** Se editan los mismos campos. El producto no puede cambiar de proveedor.
- **3b. Retirar un producto propio.** Deja de ofrecerse y sus combinaciones se desactivan. **No se borra.**
- **7a. Generar dos veces.** Las combinaciones que ya existen se omiten; la operación es idempotente.

**Excepciones**

- **E1. El código ya está registrado.** El `UNIQUE` es de toda la tabla, así que puede estar tomado por un producto que este proveedor no ve. Se rechaza **sin decir de quién es**.
- **E2. La colección no pertenece a la temporada.** Se rechaza señalando los dos campos.
- **E3. El producto no es suyo.** Se responde **igual que si no existiera**.
- **E4. El usuario tiene rol Proveedor pero ninguna ficha.** Se indica que contacte al Administrador.
- **E5. La ficha del proveedor está dada de baja.** No puede registrar ni consultar.

---

## Lo que no se lee en la ficha

**Este caso de uso existe porque el Proveedor era un actor de mentira.** El
enunciado (§4) le da tres responsabilidades y, hasta el Ciclo 2, **ninguna
estaba recogida por un requisito**: existía como ficha que el Administrador daba
de alta (CU-07) y, con acceso habilitado, podía mirar esa ficha. Un actor
principal en el diagrama de casos de uso sin una sola flecha saliendo de él.

**El código propio es casi todo ámbito; el CRUD ya era de CU-10.** No se
reimplementó nada: ni la validación de maestros, ni la coherencia entre
temporada y colección, ni el armado del SKU. Duplicarlo habría dejado dos reglas
de negocio para la misma tabla, y el día que una cambie la otra no. Lo que este
caso de uso agrega son **tres reglas**, y las tres valen su párrafo.

### 1. El `proveedor_id` sale del token, y no está en el contrato

No es que se ignore si llega: **no existe en el esquema de entrada**. Ni en el
alta ni en la edición. Y la función que lista tampoco lo recibe como parámetro,
de modo que ningún router puede pasarlo por descuido.

La diferencia importa. Aceptar el campo y comprobarlo después deja dos lugares
donde un olvido abre el mismo agujero: el que valida y el que ignora. No
aceptarlo deja uno solo.

Hay una prueba que empuja exactamente eso: registra mandando el `proveedor_id`
de la competencia y exige que el producto salga a nombre propio.

### 2. Un producto ajeno no existe: 404, nunca 403

Es la decisión menos obvia y la más importante. Un `403` diría «existe, pero no
es tuyo» — y recorrer los identificadores sería **un censo del catálogo de la
competencia**: cuántos productos tiene, con qué códigos. Un `404` no dice nada.

Es el mismo criterio que ya se había tomado dos veces en el proyecto: CU-02 no
distingue correo inexistente de contraseña incorrecta, y CU-41 no distingue un
enlace que nunca existió de uno ya usado. Acá se extiende a los datos.

La excepción E1 hereda la regla: cuando el código choca con el de otro
proveedor, el mensaje dice que está tomado y **no dice por quién**. Decirlo
reabriría por la puerta del alta lo que el 404 cierra.

> Se comprobó que esta regla se sostiene, no sólo que está escrita: con la
> comprobación de propiedad desactivada a propósito, **dos pruebas fallan**.

### 3. Lo que registra el Proveedor nace sin publicar

El RF37 dice «registrar o enviar la información de los productos que abastece».
**Registrar no es publicar.** Si el alta naciera activa, cualquier proveedor con
acceso podría poner prendas en la vitrina que ve el cliente sin que nadie las
mire.

Publicarlo es del Administrador, por CU-10. Eso da el control que daría una
aprobación **sin inventar una tabla de aprobaciones ni un estado nuevo**: el
`activo` que ya existe alcanza. Y la asimetría se sostiene hasta el final — el
Proveedor puede *retirar* lo suyo, pero no puede publicarlo, y ese intento
devuelve `403` y no `422`: el dato está bien escrito, lo que falta es el
permiso.

Hay una prueba para la otra mitad de la regla: que el Administrador **sí** pueda
publicar lo que cargó el Proveedor. Si nadie pudiera, lo registrado no llegaría
nunca a la vitrina y el caso de uso no serviría para nada.

## El bloqueo que apareció al construirlo: el Proveedor no podía leer los maestros

Su formulario necesita categorías, tallas, colores, temporadas y colecciones
para llenar los selectores. **Los cuatro routers que las exponen exigen rol
Administrador**, declarado a nivel de router — y eso es justamente lo que los
hace seguros: la dependencia se declara una vez y nadie puede olvidarla en un
endpoint.

Aflojar esa guarda habría sido lo rápido y lo peor: esos mismos routers
**crean, editan y borran** maestros. Abrirlos para llenar un selector le habría
dado al Proveedor permiso para crear categorías.

Tampoco servía `GET /tienda/filtros`, de CU-17: ése devuelve sólo lo que hoy se
ofrece —activo y con existencia—, y un alta necesita el maestro completo,
incluso una temporada que todavía no tiene un solo producto.

La salida fue `GET /catalogo/mis-productos/listas`: **su propia vista, de sólo
lectura, dentro de su propio router**, que devuelve únicamente los maestros
activos — lo único que se puede elegir al registrar algo nuevo. Dos pruebas lo
cierran: que las listas no ofrezcan un maestro dado de baja, y que el Proveedor
siga sin poder crear ni leer los de CU-08.

## Decisiones que se tomaron y conviene discutir

**`precio_base` es un precio de referencia, y el esquema no distingue costo de
precio de venta.** El campo es `NOT NULL`, así que el alta necesita uno. Se
decidió que el Proveedor cargue el suyo y que el Administrador pueda cambiarlo
por CU-10, en vez de agregar una columna nueva a una tabla que comparte con
CU-10 — lo que habría significado una migración sobre tabla ajena al caso de
uso y más alcance del que el RF37 pide. **Es una limitación conocida, no un
descuido**, y queda escrita acá para que se la pueda defender o corregir.

**El Proveedor genera variantes pero no las edita ni las borra.** Cambiar el
precio de una variante suelta o desactivarla es de CU-10 (flujos 7b y 7c): son
decisiones de venta, no de abastecimiento. El Proveedor declara qué puede traer.

**No hay borrado.** CU-10 lo tiene, con su guarda de dependencias; acá
desactivar alcanza y es más seguro: un producto retirado sigue en el inventario
y en las ventas históricas.

**No hay imágenes.** Es CU-11, otro caso de uso.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/catalogo/mis-productos/listas` | 4 · maestros para los selectores |
| `GET` | `/catalogo/mis-productos` | 2 · el listado paginado |
| `POST` | `/catalogo/mis-productos` | 5 · registrar |
| `GET` | `/catalogo/mis-productos/{id}` | detalle con variantes |
| `PATCH` | `/catalogo/mis-productos/{id}` | 3a · corregir |
| `PATCH` | `/catalogo/mis-productos/{id}/estado` | 3b · retirar |
| `POST` | `/catalogo/mis-productos/{id}/variantes` | 7 · generar combinaciones |

Los siete exigen rol **Proveedor**, declarado una sola vez a nivel de router.

**Router aparte, no endpoints dentro del de CU-10.** Aquel declara
`requiere_roles("ADMINISTRADOR")` a nivel de router; meter acá adentro rutas de
otro rol obligaría a bajar esa dependencia al endpoint, y entonces la del
Administrador pasaría a depender de que nadie se la olvide nunca más. Dos roles,
dos routers — el mismo patrón que ya usa CU-07 con `router` y `router_proveedor`.

**El prefijo lleva «mis» y ninguna ruta lleva identificador de proveedor.** Una
ruta con la forma `/catalogo/proveedores/{id}/productos` invitaría a cambiar el
número.

## Datos

**Ninguna tabla nueva. Ninguna migración.** Se reusan `producto` y
`variante_producto`, filtradas por `proveedor_id` — que ya existía en el esquema
desde la migración `0002`, con su índice.

Es lo que estaba previsto desde el acuerdo del 11/09:
[`ciclo-2/04-respuesta-de-karen.md`](../ciclo-2/04-respuesta-de-karen.md) §3 lo
anota como «Nada: reusa `producto` y `variante_producto` con filtro por
`proveedor_id`».

**Un producto con `proveedor_id` nulo no es de nadie, y por lo tanto tampoco es
suyo.** La columna es opcional y el catálogo sembrado tiene productos así. Hay
una prueba que lo fija: el listado del Proveedor no los muestra.

## Pantallas

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web · área del Proveedor | `/proveedor` | `features/proveedor/proveedor-layout/` |
| Web · listado y alta | `/proveedor/productos` | `features/proveedor/mis-productos/` |

**El área del Proveedor tiene cáscara propia, y esto no es decoración.** Antes
de CU-38, `/proveedor` era una ruta suelta que caía en la pantalla genérica de
bienvenida — la misma que usa Caja —, sin navegación. Es exactamente la trampa
que costó el PR #29 al cierre del Ciclo 2: *una pantalla montada no está
entregada si no hay cómo llegar a ella*. Acá se aplicó antes de que volviera a
pasar. Queda pendiente lo mismo para **Caja**, cuando le toque.

**La columna dice «Sin publicar», no «Inactivo».** Es la misma columna del
Administrador con otro nombre a propósito: para el Proveedor no es un estado
técnico sino una espera, y llamarla «inactiva» haría pensar que algo se rompió.

**El aviso de que la prenda nace sin publicar se muestra mientras se registra,
no después.** Un proveedor que carga una prenda y no la encuentra en la tienda
tiene que saber por qué antes de que pase.

**Tras registrar se abre solo el panel de tallas y colores.** Un producto sin
variantes no tiene SKU, y sin SKU no hay existencia, ni reserva, ni venta
(decisión D1): dejarlo para después es dejarlo a medias sin que nada lo señale.
Por lo mismo, el listado marca en rojo las prendas sin combinaciones.

**Servicio y diálogos propios, no los de CU-10.** Los del Administrador pegan en
`/catalogo/productos`; reusarlos habría hecho que la pantalla del Proveedor
pidiera rutas que su rol no puede abrir. No es duplicación: son dos contratos
distintos, y la pantalla del Proveedor no tiene que poder llamar, ni por
accidente, a un endpoint del Administrador.

**Sin pantalla móvil.** El Proveedor trabaja desde un escritorio; la app móvil
es del Cliente y del personal de sucursal.

## Lo que esto deja preparado

`proveedor_id` en `producto` deja de ser un dato que sólo carga el
Administrador. **CU-39** —informar disponibilidad y plazo de abastecimiento, de
Mateo— es el paso siguiente natural y usa el mismo ámbito: qué productos suyos
puede abastecer y en cuánto tiempo, que es lo que alimenta el estado *próximo a
ingresar* del inventario consolidado (CU-14).
