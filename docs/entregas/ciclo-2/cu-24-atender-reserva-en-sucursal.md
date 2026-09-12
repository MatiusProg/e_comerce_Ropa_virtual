# CU-24 · Atender reserva en sucursal

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
>
> **Entregados el backend y la pantalla web.** No tiene pantalla móvil: el actor es el Encargado.

| Campo | Contenido |
|---|---|
| **Código** | CU-24 |
| **Nombre** | Atender reserva en sucursal |
| **Descripción** | Permite al Encargado consultar las reservas dirigidas a su sucursal, marcarlas como preparadas, confirmar la llegada del cliente, registrar el resultado de la prueba y cerrar la reserva derivándola a venta o liberando el stock. |
| **Propósito** | Cerrar el ciclo de vida de la reserva del lado de la tienda: es el momento en que el apartado se convierte en una venta o vuelve a la percha. |
| **Actores** | Encargado de Sucursal (iniciador) · Administrador (con alcance a toda la red) |
| **Paquete** | P6 · Reservas |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF10, RF11, RF12, RF22 |
| **Precondiciones** | El Encargado tiene sesión iniciada y su cuenta está vinculada a una sucursal (CU-06). La reserva es de su local y sigue en `PENDIENTE` o `PREPARADA`. |
| **Postcondiciones** | La reserva queda en `ATENDIDA` con el resultado de cada prenda. Las que el cliente **no** se lleva vuelven a `cantidad_disponible`; las que **sí**, salen del inventario. Cada prenda deja sus movimientos. |

**Flujo principal**

1. El Encargado entra al panel de reservas de su sucursal.
2. El sistema muestra las reservas dirigidas a ese local, **la franja más próxima arriba**, con el nombre del cliente, cuántas prendas tiene cada una y su estado.
3. El Encargado abre una reserva, ve las prendas con su SKU, talla y color, y las marca como preparadas cuando las junta de la percha.
4. El cliente llega y se prueba las prendas.
5. El Encargado registra, para **cada** prenda, si el cliente se la lleva o no.
6. El Encargado cierra la reserva.
7. El sistema mueve el stock de cada prenda según su resultado y deja la reserva en `ATENDIDA`, todo en una sola transacción.

**Flujos alternativos**

- **2a. Filtrar.** Por estado, o solo las que siguen vivas.
- **3a. Atender sin preparar.** `PREPARADA` es un paso útil, no obligatorio: en una tienda chica el Encargado junta las prendas y atiende al cliente en el mismo acto.
- **6a. Observación de cierre.** El Encargado deja una nota —«pidió otra talla, se la encargamos»— que queda en la reserva.
- **Administrador.** Ve y opera sobre las reservas de toda la red, no solo de un local.

**Excepciones**

- **E11. Resultados incompletos.** Si falta el resultado de alguna prenda, o viene una que no es de esa reserva, el cierre se rechaza y el mensaje dice **cuál** de las dos cosas pasa.
- **Reserva de otra sucursal.** Un Encargado no toca reservas de otro local.
- **Reserva ya cerrada.** No se prepara ni se atiende una `ATENDIDA`, `CANCELADA` o `EXPIRADA`, y el mensaje dice cuál de las tres.
- **Resultado inválido.** Solo `LLEVA` o `NO_LLEVA`.

---

## Lo que no se lee en la ficha

### Qué pasa con el stock, prenda por prenda

**`NO_LLEVA`**: una `LIBERACION` de **+n**. Las unidades vuelven al disponible y la reserva las
suelta. Es el mismo movimiento que una cancelación.

**`LLEVA`**: una `LIBERACION` de **+n** *y* una `VENTA` de **−n**. Parece un rodeo —las unidades
vuelven al disponible para salir acto seguido— y es a propósito: esas unidades **ya habían salido**
del disponible al crearse la reserva, así que una `VENTA` de −n a secas las descontaría por segunda
vez y dejaría el saldo en negativo; y un movimiento de cero lo rechaza el CHECK
`ck_movimiento_inventario_cantidad_no_nula`.

Con los dos, el neto sobre el disponible es cero, los dos son no nulos, el invariante
`disponible == suma(movimientos)` se sostiene, y el historial se lee como lo que de verdad pasó:
«volvieron del apartado y se vendieron». Es la convención que quedó fijada al escribir CU-22 y este
es el caso de uso que la estrena.

### Sobre la decisión D3 y el Ciclo 3

**D3 dice que «la venta descuenta de reservado si vino de una reserva».** Eso describe el mundo del
Ciclo 3, donde el punto de venta existe y el cobro ocurre en el mismo acto. En el Ciclo 2 no hay
entidad `Venta` todavía, y había que elegir entre dos males:

1. Dejar las unidades de `LLEVA` en `cantidad_reservada` esperando una venta que en este ciclo no
   puede ocurrir — **y que nadie liberaría después**, porque la reserva ya estaría `ATENDIDA` y
   CU-25 solo expira las vivas. Stock atrapado para siempre.
2. Descontarlas ahora, que es lo que de verdad pasó: la prenda salió de la tienda con el cliente.

**Se eligió (2).** El inventario queda diciendo la verdad y no hay stock atrapado. Cuando P7 exista,
CU-24 y el cobro pasan a ser una sola transacción y el movimiento de `VENTA` lo va a escribir la
venta, no este caso de uso; hasta entonces lo escribe acá, con el motivo que lo explica.

**Queda anotado como punto de integración del Ciclo 3**, para que al construir el POS nadie
duplique el descuento.

### Preparar es la única transición que no mueve stock

Las unidades ya estaban apartadas desde CU-22 y siguen estándolo. Lo único que cambia es que alguien
las fue a buscar a la percha. Tiene prueba de que no se genera ningún movimiento.

Y **no impide que el cliente cancele**: `PREPARADA` sigue siendo un estado vivo y el RF29 le deja
cancelar hasta que se atienda. Que el Encargado ya haya juntado las prendas no le quita al cliente
el derecho a avisar que no va.

### Cerrar a medias no se puede, y por eso E11 es importante

Si faltara el resultado de una prenda, sus unidades quedarían apartadas en una reserva ya
`ATENDIDA` — y **no las libera nadie**, porque CU-25 solo expira las vivas. Sería el mismo agujero
que la transacción de CU-22 evita del otro lado.

Por eso los resultados de **todas** las líneas viajan juntos, se comprueba que no falte ni sobre
ninguna, y el mensaje distingue las dos mitades: olvidarse de una prenda y mandar una ajena no se
arreglan igual.

### Dos routers, porque son dos colecciones

`/reservas` es del Cliente —**sus** reservas— y `/sucursal/reservas` es del Encargado —las de **su
local**—. No es el mismo recurso con dos permisos: son dos colecciones distintas que casi nunca
coinciden. La exigencia de rol se declara una vez por *router*, por la §6.11.4.

### El ámbito se resuelve leyendo la fila

Igual que en CU-16: el identificador de la URL no dice a qué sucursal pertenece una reserva. Sin ese
paso, a un Encargado le bastaría probar números para cerrar reservas de otro local.

**Y acá el rechazo es 403, no 404** — al revés que con el Cliente. El Encargado es personal de la
empresa y sabe que las otras sucursales existen: ocultárselo no protege a nadie y sí le esconde el
motivo real.

### Las dos pantallas ordenan al revés, y es correcto

El Cliente mira un **historial**: lo último que hizo va arriba. El Encargado mira una **agenda**: lo
que tiene que atender primero es lo que empieza antes. Una reserva de las 15:00 arriba de una de las
10:00 le haría trabajar en orden inverso.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/sucursal/reservas` | 2 · la agenda del local, con filtros |
| `GET` | `/sucursal/reservas/{id}` | 3 · las prendas que hay que ir a buscar |
| `PATCH` | `/sucursal/reservas/{id}/preparacion` | 3 · `PENDIENTE` → `PREPARADA` |
| `PATCH` | `/sucursal/reservas/{id}/atencion` | 5-7 · cerrar con el resultado |

Rol **Encargado o Administrador**, declarado una sola vez en `sucursal_router`.

## Pantallas

| Plataforma | Ruta | Rol |
|---|---|---|
| Web | `/sucursal/reservas` | Encargado — las de su local |
| Web | `/admin/reservas` | Administrador — toda la red, más el disparador de CU-25 |
| Móvil | — | El actor no es Cliente: es solo web (§2.2 del acuerdo) |

Es la **misma** pantalla para los dos roles, como en CU-13: el alcance lo decide
el servidor con el ámbito del token. Lo único que cambia es que el botón de
*Expirar vencidas* (CU-25) solo aparece para el Administrador, porque es
mantenimiento del sistema y no una tarea de sucursal.

**Las de hoy se destacan**, con la palabra «HOY» además del color: en un listado
plano, una reserva de dentro de tres días y una de dentro de veinte minutos se
leen igual, y solo una de las dos es urgente.

**En el diálogo de cierre, ninguna prenda viene marcada por defecto.** Poner
«NO_LLEVA» de entrada haría que cerrar sin mirar fuera un clic, y el resultado de
la prueba es justamente lo que este caso de uso existe para registrar: cada marca
mueve stock. El botón de confirmar queda deshabilitado hasta que estén todas
respondidas —que es la excepción **E11** evitada antes de enviarla—, y hay dos
atajos para el caso común: «no se llevó nada» y «se llevó todo».

## Pruebas

`backend/tests/test_cu24_atender_reserva.py` — 19 pruebas. Las que cubren lo que la base **no**
garantiza por sí sola:

- **`test_lo_que_se_lleva_sale_del_inventario`** — la que justifica la convención de los dos
  movimientos. Con solo la `VENTA` el saldo quedaría negativo; con solo la `LIBERACION`, la tienda
  seguiría creyendo que tiene una prenda que se fue caminando.
- `test_el_invariante_sobrevive_a_la_venta_desde_reserva` — **D4** sobre el ciclo completo:
  `INGRESO +10`, `RESERVA −3`, `LIBERACION +3`, `VENTA −3`.
- `test_no_se_cierra_sin_el_resultado_de_todas_las_prendas` — E11, y que al rechazarlo no toque nada.
- `test_preparar_no_mueve_stock` — que la única transición sin efecto siga sin tenerlo.
- `test_el_cliente_todavia_puede_cancelar_una_preparada` — el límite del RF29.
- `test_no_se_atiende_dos_veces` — el mismo problema que la doble cancelación de CU-23.
