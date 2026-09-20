# CU-26 · Gestionar carrito de compras

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-26 |
| **Nombre** | Gestionar carrito de compras |
| **Descripción** | Permite al Cliente agregar variantes al carrito, modificar cantidades, eliminar ítems y ver el total con las promociones aplicadas. |
| **Propósito** | Que el Cliente arme su compra antes de confirmarla, y que esa compra sobreviva a cerrar el navegador. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P7 · Ventas y Punto de Venta |
| **Prioridad** | Alta |
| **Requisitos que realiza** | **RF14** |
| **Precondiciones** | El Cliente tiene sesión iniciada. |
| **Postcondiciones** | El carrito refleja lo que el Cliente eligió. **No se apartó ninguna unidad del inventario.** |

**Flujo principal**

1. El Cliente abre una ficha de producto (CU-18) y elige talla y color, lo que fija la **variante**.
2. El Cliente pulsa *Agregar al carrito*; el sistema suma una unidad de esa variante.
3. El Cliente abre *Mi carrito* y ve sus prendas, el precio de cada una y el total.
4. El Cliente ajusta cantidades, quita prendas o vacía el carrito.

**Flujos alternativos**

- **2a. Agregar algo que ya estaba.** Se **suma** a la cantidad existente; no se crea una segunda línea.
- **3a. Cambiar la cantidad.** El selector **fija** la cantidad, no la suma.
- **3b. Quitar una prenda.** Sale del carrito. Funciona aunque la prenda ya no se ofrezca.
- **3c. Vaciar el carrito.** Es idempotente: vaciar algo ya vacío no falla.
- **3d. Una prenda dejó de ofrecerse.** Sigue en la lista, marcada, y **no suma al total**.

**Excepciones**

- **E1. La prenda no existe o ya no se ofrece.** No se puede agregar. Los tres casos —inexistente, variante desactivada, producto desactivado— se responden igual, con el mismo criterio que CU-18.
- **E2. Se superaría el tope por prenda.** Se rechaza **sin recortar en silencio**.
- **E3. La prenda no está en el carrito.** Cambiar su cantidad o quitarla falla.

---

## Lo que no se lee en la ficha

Casi todo lo de acá sale de **dos decisiones**, y conviene que queden escritas
porque son las que alguien podría deshacer sin darse cuenta.

### 1. El carrito no guarda precios

No hay columna de precio en `carrito_detalle`. El total se calcula al leer,
contra `variante_producto`.

**Un carrito es una intención, no un contrato.** El precio se fija cuando se
genera el pedido (CU-27), no cuando se agrega la prenda. Guardar una foto del
precio dejaría al carrito cotizando un valor que la tienda ya no sostiene, y el
cliente lo descubriría al pagar — que es el peor momento posible.

Es la misma familia de razonamiento que `favorito`, que tampoco guarda nada del
producto: lo que se guarda es la elección, no sus atributos.

> Hay una prueba que cambia el precio de una variante con el carrito armado y
> exige que el total cambie.

### 2. El carrito no inmoviliza inventario

Agregar al carrito no descuenta ni aparta nada. **Eso lo hace una reserva
(CU-22)**, que sí aparta unidades desde que se crea hasta que su franja vence,
porque el cliente va a ir a buscarlas.

Un carrito que apartara stock dejaría inventario congelado por cada cliente que
abandona la compra — que son casi todos. Y el proyecto ya tiene el mecanismo
para cuando de verdad hace falta apartar: el `SELECT ... FOR UPDATE` sobre la
existencia, que resuelve el riesgo R5 y vive en CU-22.

De ahí se sigue algo que parece un descuido y no lo es: **se puede agregar al
carrito una prenda agotada.** Impedirlo sólo le quitaría al cliente la
posibilidad de dejarla anotada mientras la tienda repone. La línea viaja con
`stock_total` para que la pantalla lo diga.

La disponibilidad se **informa** acá y se **valida** en CU-27, contra el bloqueo
de la existencia, que es donde importa.

### Agregar SUMA; cambiar cantidad FIJA

Son dos operaciones distintas y van por dos verbos distintos —`POST /items` y
`PATCH /items/{variante_id}`—. Confundirlas es el defecto clásico del carrito:
quien pulsa «Agregar» dos veces desde la ficha espera llevar dos, y quien
escribe «2» en el selector espera llevar dos, no cuatro.

Un mismo endpoint que a veces suma y a veces fija sería imposible de usar sin
mirar el código.

### Una prenda que se cae sigue en la lista

Si desapareciera, el cliente vería bajar el total sin entender por qué. Se queda
marcada, sin sumar, para que pueda sacarla él o preguntar. Y **se puede quitar
aunque ya no se ofrezca**: exigirlo dejaría líneas imposibles de borrar — la
misma decisión que tomó CU-20 al desmarcar un favorito.

Las **unidades** sí la siguen contando, aunque el total no: es lo que el cliente
metió en el carrito, y la burbuja del ícono no puede cambiar sola porque la
tienda desactivó una prenda.

### Quitar una línea falla si no está; vaciar no

La asimetría es deliberada. Un corazón de favorito se toca dos veces sin querer,
y por eso desmarcar es idempotente. Este botón está junto a una línea concreta:
que no exista significa que **la pantalla está vieja**, y decirlo hace que se
recargue. Vaciar, en cambio, no habla de ninguna línea — pedir «que quede vacío»
sobre algo ya vacío es una petición cumplida.

### Leer el carrito no lo crea

La mayoría de quienes abren la pantalla nunca agregan nada. Crear una fila por
visita sería escribir por mirar. El carrito se crea en el primer `agregar`, y
**la comprobación de E1 va antes**: probar con un identificador inventado no
deja un carrito vacío de rastro. Hay una prueba que mira la tabla, no la
respuesta — un carrito vacío y uno inexistente se ven igual desde afuera.

## Las promociones — CERRADO el 20/09

> **Al 15/09 esta sección decía que las promociones no existían**, que eran de
> Mateo y que estrenaban la `0007_ciclo3_promociones`. Las tres cosas cambiaron
> y se corrigen acá en vez de dejarlas como estaban: una ficha que describe un
> comportamiento que ya no es el que el código tiene es peor que no tenerla.

La descripción dice «ver el total con las promociones aplicadas», y ya se
aplican. **CU-12** existe desde el 20/09; la tabla la estrena la
`0016_ciclo3_promociones` —no la `0007`, que se reservó temprano y la cadena le
pasó por encima— y se tomó de este lado, no del de Mateo.

El punto donde se aplican es `_armar_carrito`, tal como esta ficha anunciaba, y
es **el único**: el total del carrito sale de ahí y de ningún otro lado.

Cada línea lleva el precio de lista y el descuento **por separado**, no un solo
número ya rebajado: el cliente tiene que ver de cuánto era y cuánto paga, que es
lo que vuelve creíble la oferta.

El carrito sigue sin guardar el descuento, por el mismo motivo por el que no
guarda el precio: si lo guardara, una promoción vencida se honraría
indefinidamente y una que arranca hoy no alcanzaría lo que el cliente agregó
ayer.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/tienda/carrito` | 3 · el carrito con precios y disponibilidad al día |
| `POST` | `/tienda/carrito/items` | 2 · agregar (**suma**) |
| `PATCH` | `/tienda/carrito/items/{variante_id}` | 3a · fijar la cantidad |
| `DELETE` | `/tienda/carrito/items/{variante_id}` | 3b · quitar |
| `DELETE` | `/tienda/carrito` | 3c · vaciar |

Los cinco exigen rol **Cliente**, declarado una sola vez a nivel de router.

**Los cinco devuelven el carrito entero**, no sólo la línea tocada: la pantalla
necesita el total y la burbuja del ícono, y pedirlos aparte serían dos viajes
por cada «Agregar».

**Ninguna ruta lleva identificador de carrito.** Se resuelve desde el token,
igual que la ficha del Proveedor en CU-38 y el perfil en CU-04. Una ruta con la
forma `/carritos/{id}` invitaría a cambiar el número.

**El prefijo es `/tienda` pero el código es de P7.** La ruta vive ahí porque es
donde el cliente la usa —viene de la vitrina y va al pago— pero el paquete es
Ventas. Por eso se monta en `main.py` en vez de colgarse del router de la
vitrina como sí hace CU-20: los favoritos **son** de P5, y colgar un router de
P7 dentro de uno de P5 crearía una dependencia al revés de la que declara la
arquitectura.

## Datos

Migración `0009_ciclo3_carrito`. **Las dos primeras tablas propias de P7.**

```
carrito           id              BIGSERIAL  PK
                  cliente_id      BIGINT     FK cliente.id ON DELETE CASCADE, UNIQUE
                  creado_en       TIMESTAMPTZ
                  actualizado_en  TIMESTAMPTZ

carrito_detalle   id              BIGSERIAL  PK
                  carrito_id      BIGINT     FK carrito.id ON DELETE CASCADE
                  variante_id     BIGINT     FK variante_producto.id   (sin CASCADE)
                  cantidad        INTEGER    CHECK (cantidad > 0)
                  creado_en / actualizado_en
                  UNIQUE (carrito_id, variante_id)
```

**`UNIQUE` en `cliente_id`: un cliente, un carrito.** No hay carritos guardados
ni listas múltiples —eso sería otro caso de uso— y el `UNIQUE` es lo que vuelve
imposible que dos peticiones simultáneas creen dos carritos y la compra quede
partida en dos.

**`UNIQUE (carrito_id, variante_id)`:** una variante aparece una vez. Es lo que
convierte «agregar de nuevo» en «sumar cantidad» en vez de en una segunda línea
que el cliente no sabría cuál editar.

**`variante_id` sin `ON DELETE CASCADE`, a diferencia de `carrito_id`.** Una
variante que está en algún carrito no se borra, se desactiva. Si se borrara, la
línea desaparecería sin que el cliente entienda por qué le falta algo.

**Apunta a la variante y no al producto** —decisión D1—: un carrito con «una
blusa» sin talla ni color no se puede convertir en pedido. Es la diferencia con
`favorito`, que apunta al producto porque es una intención anterior a elegir.

**Cantidad cero no es una línea**: es una línea borrada, y el `CHECK` lo
garantiza en la base. Para dejarla en cero está `DELETE`.

### Sobre el número, otra vez

La cadena queda `0005 → 0008 → 0009 → 0006 → 0007`.

Alembic **no mira el número del archivo, mira `down_revision`**. Al escribir
esto la cabeza era la `0008`, así que ésta cuelga de ahí.

> **Para Mateo:** la cabeza ya no es la `0008` sino la `0009`. Su
> `0006_ciclo3_ventas` tiene que declarar
> `down_revision = "0009_ciclo3_carrito"` — corrige el aviso del PR #31, que
> decía `0008`.

`pedido`, `venta`, `caja` y sus detalles **siguen reservados** para esa `0006`.
El carrito es separable: existe antes del pedido y sobrevive a que el cliente no
compre. Estrenar sólo lo que CU-26 necesita respeta la reserva.

### Un defecto que atrapó `alembic check`

Los modelos de CU-26 viven en `ventas/carrito_models.py`, no en `models.py`, y
**`alembic/env.py` no los importaba**. El resultado: `check` veía `carrito` y
`carrito_detalle` como tablas sobrantes, y un futuro `--autogenerate` habría
escrito una migración que **las borra**. Se agregó la importación.

Es el precio del patrón «archivos propios dentro del paquete ajeno», y vale
recordarlo: **cada vez que se usa, hay que sumar el modelo a `env.py`.**

## Pantallas

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web · el carrito | `/tienda/carrito` | `features/tienda/carrito/` |
| Web · agregar | dentro de `/tienda/producto/:id` | `features/tienda/ficha/` |
| Web · la burbuja | dentro de `/tienda` | `features/tienda/catalogo/` |

**El botón de agregar está en la ficha, no en la tarjeta del catálogo.** El
carrito guarda variantes: desde el listado no hay talla ni color elegidos, y un
botón ahí tendría que abrir un selector o adivinar. La ficha ya resuelve esa
elección.

**La burbuja sale de una señal compartida en el servicio, no de una consulta de
cada pantalla.** Si cada una lo pidiera por su cuenta se desincronizarían en
cuanto el cliente agregara algo desde una ficha. Todos los endpoints devuelven
el carrito entero justamente para que actualizarla sea una línea.

**Agregar no navega al carrito.** Quien está mirando una ficha suele querer
seguir mirando; llevarlo de golpe le corta el recorrido. El aviso le ofrece ir.

**El botón de pagar está deshabilitado y dice por qué.** CU-27 es el caso de uso
siguiente. Un botón que no lleva a ninguna parte es peor que uno que explica que
todavía no se puede.

**Sin pantalla móvil.** El carrito móvil llega con CU-27, que es cuando la
compra se puede completar.

## Lo que esto deja preparado

`carrito` y `carrito_detalle` son la entrada del criterio de cierre del Ciclo 3:
**catálogo → carrito → pago → inventario descontado → reporte**. **CU-27**
—realizar pedido y pagar— lee este carrito, fija los precios en el pedido y ahí
sí valida la disponibilidad contra el bloqueo de la existencia.
