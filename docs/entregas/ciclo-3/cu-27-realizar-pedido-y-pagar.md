# CU-27 · Realizar pedido y pagar en línea

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

**Este caso de uso se hizo entre los dos**, por el acuerdo del 17/09:

| Mitad | Quién | Dónde |
|---|---|---|
| Backend y pasarela | **Mateo** | `backend/app/modules/ventas/`, `modules/pagos/`, `integrations/pasarela_pago/` |
| Web | **Karen** | `frontend-web/src/app/features/tienda/checkout/` y `.../pago/` |
| Móvil | **Mateo** | `mobile/` |

Esta ficha documenta el caso de uso entero; la mitad web con detalle, y la del
backend por referencia —es de Mateo y su razonamiento está en sus propios
archivos y en el commit `8ce1542`—.

| Campo | Contenido |
|---|---|
| **Código** | CU-27 |
| **Nombre** | Realizar pedido y pagar en línea |
| **Descripción** | Permite al Cliente confirmar el contenido del carrito, elegir la modalidad de entrega (retiro en sucursal o envío a domicilio), generar el pedido e iniciar el pago a través de la pasarela electrónica. |
| **Propósito** | Que el carrito se convierta en una compra, y que el dinero lo mueva quien tiene que moverlo. |
| **Actores** | Cliente (iniciador) · Pasarela de pago (actor externo) |
| **Paquete** | P7 · Ventas y Punto de Venta, con P8 · Pagos |
| **Prioridad** | Alta |
| **Requisitos que realiza** | **RF15**, **RF16**, **RF19** |
| **Precondiciones** | El Cliente tiene sesión iniciada y su carrito tiene algo. |
| **Postcondiciones** | Existe una `venta` en `PENDIENTE_PAGO` con su stock apartado. **El pedido no queda pagado**: eso lo hace el webhook de CU-28. |

**Flujo principal**

1. El Cliente abre su carrito (CU-26) y pulsa *Continuar al pago*.
2. El sistema muestra qué va a comprar, qué sucursales pueden abastecerlo y sus direcciones.
3. El Cliente elige **retiro en sucursal** o **envío a domicilio**, y su destino.
4. El Cliente confirma. El sistema crea la venta, aparta el stock y abre una sesión de pago.
5. El navegador va a la pasarela; el Cliente paga y vuelve.
6. La pantalla de retorno **le pregunta al servidor** en qué estado quedó el pedido y lo muestra.

**Flujos alternativos**

- **3a. Una sola sucursal puede abastecer.** Viene preseleccionada; el Cliente no tiene que elegir.
- **3b. El Cliente tiene dirección predeterminada.** Viene preseleccionada.
- **4a. El precio cambió mientras decidía.** Ver §2. No se cobra: se avisa y se vuelve a preguntar.
- **6a. El Cliente canceló en la pasarela.** Vuelve a `/pago/cancelado` y puede cancelar el pedido para soltar el stock enseguida.
- **6b. El webhook todavía no llegó.** La pantalla lo dice y muestra hasta cuándo hay plazo.

**Excepciones**

- **E1. El carrito está vacío o tiene prendas que dejaron de ofrecerse.** No se puede confirmar.
- **E2. Ninguna sucursal abastece el pedido entero.** No se puede confirmar; se dice cuál es la que más cerca está y qué le falta.
- **E3. La pasarela no responde.** 502. **No queda nada escrito** y el Cliente puede reintentar.
- **E4. El total cambió.** 409 con el total nuevo (§2).
- **E5. El pedido no es suyo.** 404, nunca 403 — convención 1 del ciclo.

---

## Lo que no se lee en la ficha

### 1. La pantalla de retorno NO decide si se pagó. Nunca

Es la decisión **D5** del análisis, y es lo único que hay que entender de este
caso de uso: *el estado del pago sólo lo determina la pasarela*, y llega por el
webhook firmado de CU-28.

La URL por la que el navegador vuelve **no prueba nada**: cualquiera puede
escribir `/pago/exito` en la barra de direcciones. Así que esa URL se usa para
dos cosas y ninguna más: saber qué pedido consultar, y con qué tono recibir a la
persona.

Todo lo que se muestra sale de `GET /tienda/pedidos/{codigo}`, o sea de la base.
**Por eso alguien que entre a `/pago/exito` a mano ve su pedido tal como está:
esperando el pago.** Eso no es un defecto de la pantalla: es la prueba de que
funciona.

### 2. La web manda el total que el cliente vio

`total_esperado` viaja en la confirmación. El carrito no congela precios —es una
intención, no un contrato, y así se decidió en CU-26—, así que entre que el
cliente miró el carrito y pulsó confirmar la tienda pudo cambiar un precio.

Sin ese campo, el sistema cobraría el precio nuevo callado y el cliente se
enteraría leyendo el comprobante. Con él, el servidor se planta y devuelve un
**409 con el total nuevo y el carrito al día**.

La web lo pinta como un aviso —el total viejo, el nuevo y «no cobramos nada»— y
**no** como un error, porque no lo es: es una pregunta que hay que volver a
hacer. Recarga el resto de la pantalla para que las sucursales y los importes
queden al día, y deja el aviso encima.

### 3. Se dice cuando el pago es de mentira

Si `pago_real` viene en `false` —que es lo que pasa con el proveedor `simulada`,
el que está configurado por omisión— la pantalla **lo declara antes de que el
cliente pulse**, con todas las letras y en color de aviso, no de error.

En la demostración el pago es simulado. Dejar que parezca real sería engañar al
tribunal, y es exactamente lo que la sección de la pasarela dice que no hay que
hacer. El aviso no va en rojo a propósito: no falló nada, es una aclaración.

### 4. De dónde saca la pantalla de retorno el código del pedido

Tres fuentes, en orden, **y hacen falta las tres**:

| | Fuente | Cuándo sirve |
|---|---|---|
| 1 | `?pedido=` en la URL | Sólo con el proveedor `simulada`, que lo agrega |
| 2 | `sessionStorage` | Lo guarda la pantalla de confirmación antes de redirigir |
| 3 | Se lo pedimos a la persona | Cuando fallan las dos |

La segunda es **la única que sirve con Stripe**: su `success_url` es
`?sesion={CHECKOUT_SESSION_ID}` y nada más, y su `cancel_url` no lleva ningún
parámetro. Es `sessionStorage` y no `localStorage` porque muere con la pestaña,
que es justo lo que dura el viaje a la pasarela y la vuelta.

La tercera existe para que **esta pantalla nunca sea un callejón sin salida**:
con Stripe y el almacenamiento bloqueado —una ventana privada— las dos primeras
fallan, y quien acaba de pagar tiene que poder llegar a su pedido igual. El
formulario normaliza lo que se escriba (sin espacios, en mayúsculas), porque el
código se lee de una pantalla o se dicta por teléfono.

> **Para Mateo, y es una línea.** La forma limpia de cerrar el caso 3 es que
> `stripe_hospedado.py` agregue `&pedido=<referencia>` a su `success_url`, como
> ya hace el proveedor simulado. No se tocó desde la web porque el backend de
> este caso de uso es suyo.

### 5. Dos detalles chicos que son decisiones

**El botón del carrito se apaga de verdad.** Con prendas que dejaron de
ofrecerse, el backend no deja confirmar, así que la web corta antes en vez de
mandar al cliente a rebotar en la pantalla siguiente. Y son **dos elementos**
—un `<a>` o un `<button disabled>`, según el caso— y no un enlace con
`aria-disabled`: un enlace deshabilitado sólo de nombre **sigue navegando** si
se lo pulsa con el teclado.

**Las sucursales que no llegan se muestran apagadas y con el motivo**, en vez de
esconderse. Un cliente que no ve su sucursal habitual necesita saber que existe y
qué le falta, no que desapareció. Y son un `<div>`, no un botón, así que el
teclado tampoco puede seleccionarlas.

### 6. Lo que la web NO hace, y por qué

**No hay «mis pedidos».** No es un olvido ni un hueco de este caso de uso: el
historial de compras es **CU-29**, que todavía no está hecho. El backend de
CU-27 expone `/opciones`, la creación, la consulta por código y la cancelación —
que es exactamente lo que este caso de uso necesita—. El listado le corresponde
a CU-29 y llegará con él.

---

## Dónde vive

**Web** (Karen)

| Archivo | Qué |
|---|---|
| `core/models/pedidos.models.ts` | espejo del contrato |
| `core/services/pedidos.service.ts` | el cliente HTTP |
| `features/tienda/checkout/` | pasos 1 a 4: confirmar |
| `features/tienda/pago/` | paso 6: el retorno, las dos salidas |

Rutas: `tienda/checkout`, `pago/exito` y `pago/cancelado`, las tres con sesión
de Cliente.

> **Los caminos de las dos últimas no son libres.** Los fija el backend con
> `PAGO_URL_EXITO` y `PAGO_URL_CANCELADO`. Cambiar uno sin cambiar el otro deja
> al cliente en un 404 justo después de pagar.

Las dos salidas son **la misma pantalla** con dos encabezados: hacen lo mismo
—preguntarle a la base en qué quedó el pedido—, y la diferencia es el tono.
`data.salida` llega al componente como entrada por `withComponentInputBinding()`.

**Backend** (Mateo) — commit `8ce1542`. Endpoints bajo `/api/v1/tienda/pedidos`:
`GET /opciones`, `POST ""`, `GET /{codigo}`, `POST /{codigo}/cancelar`, más
`POST /pedidos/expirar-vencidos` para la barrida de los que nadie pagó.

---

## Deuda que queda anotada

- **`&pedido=` en el `success_url` de Stripe** — ver §4. Una línea, de Mateo.
- **La moneda de la pasarela no es la del negocio.** Stripe no admite bolivianos
  en cuentas de prueba, así que hacia afuera se cobra en dólares
  (`PAGO_MONEDA`). La venta se guarda en su moneda; lo único que se traduce es lo
  que sale. Es limitación del *sandbox*, no del diseño.
- **Nada se miró a 390 px** de las dos pantallas nuevas. Es la misma deuda que
  quedó de CU-38, CU-41, CU-26 y CU-36.
