# CU-23 · Consultar y cancelar reserva

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)). Un archivo por
> caso de uso, por el mismo motivo que explica
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).
>
> **Entregado el backend.** La pantalla web y la móvil son del día 4, junto con las de CU-22.

| Campo | Contenido |
|---|---|
| **Código** | CU-23 |
| **Nombre** | Consultar y cancelar reserva |
| **Descripción** | Permite al Cliente consultar el estado y el detalle de sus reservas y cancelar aquellas aún no atendidas, liberando el stock reservado. |
| **Propósito** | Devolver al inventario lo que alguien ya no va a ir a probarse. Sin cancelación, ese stock queda retenido hasta que la franja venza y CU-25 lo libere: hasta un día entero de mercadería inmovilizada porque el cliente cambió de planes. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P6 · Reservas |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF12, **RF29** |
| **Precondiciones** | El Cliente tiene sesión iniciada y ficha de cliente. La reserva es suya y sigue en `PENDIENTE` o `PREPARADA`. |
| **Postcondiciones** | La reserva queda en `CANCELADA` con su motivo, las unidades vuelven de `cantidad_reservada` a `cantidad_disponible`, y por cada prenda queda un `movimiento_inventario` de tipo `LIBERACION`. El probador de esa franja queda libre. |

**Flujo principal**

1. El Cliente entra a *Mis reservas*.
2. El sistema muestra sus reservas de la franja más próxima a la más vieja, con su estado, su sucursal y cuántas prendas tiene cada una.
3. El Cliente abre una reserva y ve su detalle: las prendas con su SKU, talla, color y cantidad.
4. El Cliente elige cancelarla e indica, si quiere, un motivo.
5. El sistema comprueba que la reserva sea suya y que siga viva, devuelve el stock de cada prenda a disponible con su movimiento, y la deja en `CANCELADA`.

**Flujos alternativos**

- **2a. Filtrar.** El Cliente ve solo las que siguen vivas —`PENDIENTE` o `PREPARADA`— o solo las cerradas.
- **2b. Filtrar por estado.** Para un estado concreto.
- **4a. Sin motivo.** El motivo es opcional; el sistema guarda «Cancelada por el cliente».

**Excepciones**

- **E10. La reserva ya no está viva.** Si fue atendida, ya estaba cancelada o expiró, no se puede cancelar, y el mensaje dice **cuál** de las tres cosas pasó.
- **Reserva ajena o inexistente.** Las dos devuelven el mismo 404.

---

## Lo que no se lee en la ficha

### La mitad de «consultar» ya estaba

`GET /reservas` y `GET /reservas/{id}` se entregaron con CU-22, porque una reserva que se crea y no
se puede mirar no sirve de nada. Este caso de uso agrega los filtros y **la cancelación**, que es lo
que realiza el RF29 y lo único que toca stock.

### La doble cancelación es el riesgo R5 visto del otro lado

Allí era vender de más; acá es **inventar mercadería**. Si el cliente pulsa «cancelar» dos veces —o
lo hace desde la web y el teléfono a la vez—, las dos peticiones leerían la reserva en `PENDIENTE`,
las dos pasarían la comprobación de estado y las dos liberarían el stock: el saldo terminaría con 13
unidades de una prenda de la que solo hay 10.

Se resuelve con el mismo mecanismo: **`SELECT ... FOR UPDATE` sobre la fila de la reserva**. La
segunda petición espera a que la primera confirme, vuelve a leer —ahora `CANCELADA`— y se rechaza
sola con la excepción E10. Tiene prueba de concurrencia con dos conexiones reales, igual que la de
CU-22.

**El estado se comprueba DESPUÉS de tomar el bloqueo, no antes.** Comprobarlo antes sería leer un
valor que puede cambiar entre la lectura y la escritura — que es exactamente el agujero que el
bloqueo viene a cerrar.

### Cancelar no borra

Es `PATCH` sobre un sub-recurso y no `DELETE` sobre la reserva. La reserva cancelada se conserva
—con su motivo, su fecha y sus prendas— porque es historia del cliente y de la sucursal, y porque
los movimientos de `LIBERACION` que deja apuntan a ella. Una reserva borrada dejaría dos movimientos
de inventario explicando algo que ya no existe.

### Una reserva cancelada libera su probador

El control de capacidad de CU-22 solo cuenta las reservas **vivas**. Sin eso, una sucursal de un
probador se bloquearía para siempre en cuanto alguien reservara y se arrepintiera. La constante
`ESTADOS_VIVOS` se declara una sola vez en el repositorio y la usan el control de capacidad de
CU-22, la cancelación de acá y la expiración de CU-25: si cada uno la escribiera por su cuenta, el
día que se agregue un estado quedarían diciendo cosas distintas.

### `PREPARADA` todavía se cancela

El RF29 dice «mientras no haya sido atendida», y ese es el límite exacto. Que el Encargado ya haya
juntado las prendas no le quita al cliente el derecho a avisar que no va. Lo que no se puede
cancelar es una reserva `ATENDIDA`, `CANCELADA` o `EXPIRADA`.

### Una corrección sobre CU-22

Al escribir este caso de uso quedó a la vista que **`ReservaCrearIn` aceptaba una `observacion`**, y
eso rompía el modelo: `reserva.observacion` está declarada en `models.py` como la nota de **cierre**
—«lo escribe CU-23 cuando la cancela el cliente y CU-24 cuando el Encargado la cierra»—. Con las dos
cosas en la misma columna, el motivo de la cancelación pisaría la nota que el cliente dejó al
reservar, y se perdería justo el dato que explica por qué se canceló.

**Se quitó de CU-22.** Una nota del cliente al reservar es útil, pero no la pide ningún RF y necesita
columna propia; si se agrega, se agrega como `nota_cliente` con su migración, no compartiendo esta.

### El motivo es opcional, y eso es una decisión

Cancelar no es un trámite: exigir una justificación para no ir a probarse ropa solo consigue que la
gente escriba «asdf». Lo que sí se guarda siempre es **quién y cuándo** —en el movimiento de
`LIBERACION`, con el usuario y la fecha—, que es lo que de verdad le sirve a la sucursal.

Es distinto del motivo de CU-15, que **sí** es obligatorio: allí alguien está corrigiendo un saldo a
mano y el RF28 pide esa trazabilidad. Acá el sistema ya sabe todo lo que necesita.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/reservas` | 2 · mis reservas, con `estado` y `vivas` |
| `GET` | `/reservas/{id}` | 3 · detalle con las prendas |
| `PATCH` | `/reservas/{id}/cancelacion` | 4-5 · cancelar y liberar el stock |

Todos exigen rol **Cliente**. Cerrar una reserva desde la sucursal es CU-24 y es otra cosa: allí la
reserva se **atiende**, no se cancela.

## Pantallas

| Plataforma | Ruta | Estado |
|---|---|---|
| Web | `/mi-cuenta/reservas` | **Pendiente** — día 4 |
| Móvil | `reservas` | **Pendiente** — día 4 |

## Pruebas

`backend/tests/test_cu23_cancelar_reserva.py` — 13 pruebas. Las que cubren lo que la base **no**
garantiza por sí sola:

- **`test_dos_cancelaciones_simultaneas_no_inventan_mercaderia`** — dos hilos, dos conexiones
  reales, la misma reserva. Sin el `FOR UPDATE` el stock se libera dos veces y aparecen unidades que
  no existen.
- `test_cancelar_devuelve_el_stock_apartado` — exactamente lo que se apartó, ni una unidad más, y el
  físico sin moverse.
- `test_el_invariante_se_sostiene_despues_de_cancelar` — el ciclo completo ingreso → reserva →
  cancelación con **D4** comprobado. Si el signo de `RESERVA` o el de `LIBERACION` estuviera al
  revés, el saldo y la suma del historial se separarían acá.
- `test_cancelar_libera_el_probador` — que el control de capacidad de CU-22 solo cuente las vivas.
- `test_una_reserva_preparada_todavia_se_puede_cancelar` — el límite exacto del RF29.
