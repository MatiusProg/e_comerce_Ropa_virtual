# CU-28 · Confirmar pago del pedido

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-28 |
| **Nombre** | Confirmar pago del pedido |
| **Descripción** | El Sistema recibe la notificación de la Pasarela de Pago, valida su autenticidad, actualiza el estado del pedido a pagado y descuenta el inventario de la sucursal que lo abastece. |
| **Propósito** | Que el dinero que entró se refleje en el sistema, una sola vez. |
| **Actores** | Pasarela de pago (iniciador, actor externo) |
| **Paquete** | P8 · Pagos |
| **Prioridad** | Alta |
| **Requisitos que realiza** | **RF19** |
| **Precondiciones** | Existe una `venta` en `PENDIENTE_PAGO` con su `pago` en `INICIADO` (CU-27). |
| **Postcondiciones** | La venta queda `PAGADA`, el inventario descontado y el carrito vacío. **O nada de eso**, si la notificación no se pudo verificar. |

**Flujo principal**

1. La Pasarela envía la notificación firmada a `POST /api/v1/pagos/webhook`.
2. El sistema **verifica la firma** sobre los bytes exactos recibidos.
3. El sistema registra la notificación en `transaccion_pasarela`.
4. El sistema marca el `pago` como aprobado y la `venta` como `PAGADA`.
5. El sistema libera lo apartado y lo descuenta como venta (dos movimientos).
6. El sistema vacía el carrito del cliente.
7. El sistema responde **200** para que la pasarela no reintente.

**Flujos alternativos**

- **1a. La notificación ya se había recibido.** Se responde 200 y no se toca nada.
- **1b. El evento no habla de un cobro.** Se registra y no se toca nada.
- **1c. La sesión no corresponde a ningún pago conocido.** Se registra y no se toca nada.
- **4a. El pago ya estaba aprobado.** No se vuelve a aplicar (segunda red, §2).
- **4b. La pasarela informa un rechazo.** El pago queda `RECHAZADO` y **el stock sigue apartado**: el pedido no fracasó, sólo no se pagó.

**Excepciones**

- **E1. La firma no se puede verificar.** **400**, y la notificación queda registrada con `firma_valida = false` y sin pago asociado.
- **E2. El cuerpo no se entiende o no trae `id_evento`.** 400.

---

## Lo que no se lee en la ficha

### 1. Toda la idempotencia es una restricción, no lógica

El `UNIQUE` sobre `transaccion_pasarela.evento_id` es lo que impide que una
notificación repetida **descuente el inventario dos veces**. El `INSERT` falla,
se trata como «ya visto» y no se vuelve a tocar la venta.

**La transacción se escribe ANTES de mover nada, y es deliberado.** Al revés
—mover primero y registrar después— dos entregas simultáneas del mismo evento
pasarían las dos por el descuento antes de que ninguna llegue al `INSERT`.
Registrar primero convierte la carrera en un choque contra la base, que es lo
único que sabe resolverla.

**Esto no es un caso de borde: Stripe reenvía hasta tres días** si no recibe un
2xx. La repetición pasa.

**Hay una segunda red**, para lo que el `UNIQUE` no puede atrapar: dos eventos
**con identificadores distintos** sobre el mismo cobro pasan la restricción sin
chocar. Lo que los frena es comprobar que el pago ya estaba aprobado antes de
volver a mover nada. Las dos redes tienen su prueba.

### 2. Por qué casi todo responde 200

Un código de error le dice a la pasarela «volvé a intentar», y eso **sólo sirve
cuando el problema es nuestro y es pasajero**.

| Situación | Respuesta | Por qué |
|---|---|---|
| Evento repetido | 200 | Reintentar no lo cambia |
| Evento de otro tipo | 200 | Una cuenta emite decenas que no interesan |
| Sesión desconocida | 200 | Reintentar no va a hacer que exista |
| Rechazo | 200 | Se recibió y se entendió |
| **Firma inválida** | **400** | Ahí sí hay algo que avisar |

Devolver error en los primeros cuatro dejaría a la pasarela golpeando durante
días por algo que nunca va a cambiar.

### 3. El endpoint no lleva token, y no es un olvido

Quien lo llama es la pasarela, que no tiene cuenta en el sistema y no puede
iniciar sesión. **Lo que lo protege es la firma**, que se verifica antes de leer
una sola clave del cuerpo.

Un token sería peor que inútil: obligaría a guardar una credencial compartida en
el panel de Stripe y **no probaría nada sobre el contenido** del mensaje — un
token robado deja publicar cualquier cosa, mientras que la firma cubre el cuerpo
exacto que viajó.

Es el único router del proyecto sin `dependencies`, y ésta es su justificación.

### 4. Verificar y traducir son una sola operación

`interpretar_webhook(cuerpo, firma)` hace las dos cosas. Separarlas dejaría
abierta la puerta a leer el contenido antes de comprobar quién lo mandó, que es
exactamente el agujero que la firma existe para tapar. Con una sola función **no
hay forma de saltearse el paso**.

El cuerpo llega **en bytes y sin tocar**: la firma se calcula sobre los bytes
exactos que viajaron, y volver a serializar un JSON ya interpretado cambia los
espacios y el orden de las claves, con lo que la verificación falla aunque el
mensaje sea legítimo. Es el error más común de esta integración, y por eso el
router lee `await request.body()` en vez de recibir un modelo de Pydantic.

### 5. Los dos movimientos de inventario, otra vez

CU-27 **apartó** el stock al crear el pedido, así que estas unidades están en
`cantidad_reservada`. Venderlas es `LIBERACION +n` seguido de `VENTA −n`:

- el neto sobre el disponible es **cero**;
- los dos movimientos son no nulos (el CHECK rechaza los de cero);
- el invariante `disponible == suma(movimientos)` se sostiene;
- y el historial se lee como lo que pasó: «volvieron del apartado y se vendieron».

Un `VENTA −n` a secas descontaría por segunda vez unidades que ya habían salido
del disponible. Con 10 unidades y un pedido de 2, el saldo quedaría en **6** en
vez de 8: cuatro prendas que la tienda cree no tener. Hay una prueba que fija
exactamente ese número.

### 6. El carrito se vacía acá, no al confirmar el pedido

Es la decisión de CU-27 y estaba escrita en su servicio esperando a que alguien
la cumpliera. Si el carrito se vaciara al confirmar, **un pago que nunca llega
dejaría al cliente sin carrito y sin compra**, y tendría que rearmarlo entero
para reintentar. Se vacía cuando el dinero entró, que es cuando dejó de ser una
intención.

### 7. El proveedor simulado también firma

Podría haber aceptado cualquier cuerpo. No lo hace, y la razón es la
demostración: si la ruta de simulación tomara un atajo que el webhook real no
tiene, **lo que se enseña en la defensa sería un flujo distinto del que se
defiende**.

`POST /pagos/simulacion` fabrica el mismo cuerpo, lo firma con el mismo secreto
y lo entrega **a la misma función**. No hay un segundo camino a `PAGADA`. La
ruta responde **404 cuando el proveedor cobra de verdad** — no 403: si el
sistema corre contra una pasarela real, esa ruta no existe.

### 8. `GET /pagos/configuracion`, para no adivinar

Dice qué proveedor está activo, si cobra de verdad, la moneda y si el webhook es
verificable. **No devuelve ninguna clave.**

Existe para poder saber, sin entrar al panel de Railway, si el despliegue quedó
con la pasarela que se creía — que es justo el error que deja al sistema
**aceptando pedidos que nadie cobra**.

---

## Dónde vive

| Archivo | Qué |
|---|---|
| `integrations/pasarela_pago/base.py` | `EventoDePago` y el método nuevo del protocolo |
| `integrations/pasarela_pago/simulada.py` | firma HMAC-SHA256 y traducción |
| `integrations/pasarela_pago/stripe_hospedado.py` | `construct_event` de Stripe |
| `modules/pagos/service.py` | `confirmar_pago`, la idempotencia y los dos movimientos |
| `modules/pagos/router.py` | los tres endpoints |
| `tests/test_cu28_webhook.py` | 16 pruebas |

**Sin migración**: las tablas `pago` y `transaccion_pasarela` ya existían desde
la `0006`, con el `UNIQUE` puesto justamente para esto.

> **P8 lo tomamos entre los dos.** El plan (§5.5) se lo asignaba a Mateo; él
> escribió `iniciar_cobro` con CU-27, y CU-28 se sumó encima mientras él pulía
> CU-21. Acordado el 18/09.

---

## Las pruebas ya no dependen del `.env` — y es un arreglo, no un detalle

`conftest.py` ahora **impone `PAGO_PROVEEDOR=simulada`** y un secreto de pruebas.

Sin eso, poner `PAGO_PROVEEDOR=stripe` para desarrollar en local hacía que las
pruebas de CU-27 y CU-28 **salieran a internet a hablar con Stripe de verdad**:
abrirían sesiones de cobro con la clave configurada, tardarían lo que tarde la
red y fallarían sin conexión — además de que la ruta de simulación responde 404
cuando la pasarela cobra en serio, y esas pruebas la usan.

Una suite que llama a un servicio de terceros no prueba el sistema: prueba el
servicio de terceros y la conexión a internet.

De paso, el secreto de pruebas hace que **la firma se verifique** en la suite.
Antes estaba vacío, el proveedor simulado no comprobaba nada, y la parte más
delicada de este caso de uso quedaba sin probar.

---

## El despliegue con Stripe

**Cuenta de prueba creada el 18/09** y webhook registrado apuntando a
`https://ecomerceropavirtual-production.up.railway.app/api/v1/pagos/webhook`,
escuchando `checkout.session.completed` y `checkout.session.expired`.

Variables en Railway (servicio **Backend**):

| Variable | Valor |
|---|---|
| `PAGO_PROVEEDOR` | `stripe` |
| `PAGO_API_KEY` | `sk_test_…` |
| `PAGO_WEBHOOK_SECRET` | `whsec_…` (el del **endpoint**, no la clave de API) |
| `PAGO_MONEDA` | `usd` |
| `PAGO_URL_EXITO` | `https://…-b192.up.railway.app/pago/exito` |
| `PAGO_URL_CANCELADO` | `https://…-b192.up.railway.app/pago/cancelado` |

> **El orden importa: primero el código, después las variables.** Aplicarlas
> sobre un despliegue que todavía no tiene el endpoint deja a Stripe recibiendo
> **404** en cada notificación, y los pedidos no pasan a pagados nunca. Es peor
> que quedarse con el simulado.

**Stripe no opera en Bolivia** — 45 países y ninguno es el nuestro. La cuenta se
abrió bajo Estados Unidos y se cobra en dólares, que es la razón por la que
`PAGO_MONEDA` existía desde CU-27. Conviene decirlo de entrada en la defensa: es
limitación del *sandbox*, no del diseño, y Libélula —de uso local— quedó en el
marco teórico porque exige convenio comercial (§6.7).

## Deuda que queda anotada

- **El desarrollo local con Stripe necesita el CLI de Stripe** (`stripe listen`)
  para reenviar el webhook a `localhost`, y ese comando imprime **otro**
  `whsec_`. Sin el CLI, en local conviene seguir con `simulada`.
- **CU-29 sigue sin existir**, así que un pedido pagado no se puede consultar
  desde una lista: sólo por su código.
