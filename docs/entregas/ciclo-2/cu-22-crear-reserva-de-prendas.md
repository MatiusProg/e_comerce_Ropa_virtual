# CU-22 · Crear reserva de prendas

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)). Un archivo por
> caso de uso, por el mismo motivo que explica
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).
>
> **Entregados el backend y la pantalla web.** La móvil queda pendiente.

| Campo | Contenido |
|---|---|
| **Código** | CU-22 |
| **Nombre** | Crear reserva de prendas |
| **Descripción** | Permite al Cliente seleccionar varias prendas (variantes), elegir la sucursal donde desea probarlas y una franja horaria, y confirmar la reserva; el sistema descuenta el stock disponible y lo registra como reservado. |
| **Propósito** | Es el caso de uso que le da sentido al vestidor virtual y a la tienda física juntos: el cliente elige en línea y se prueba en el local, con la garantía de que la prenda va a estar. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P6 · Reservas |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF09, RF10 |
| **Precondiciones** | El Cliente tiene sesión iniciada y ficha de cliente. Existe la sucursal activa y hay existencia disponible de las variantes elegidas (CU-13). |
| **Postcondiciones** | La reserva queda en estado `PENDIENTE`, las unidades pasan de `cantidad_disponible` a `cantidad_reservada`, y por cada prenda queda un `movimiento_inventario` de tipo `RESERVA`. |

**Flujo principal**

1. El Cliente navega el catálogo (CU-17) y abre la ficha de una prenda (CU-18).
2. El Cliente elige talla y color —la variante— y la agrega a su reserva, repitiendo por cada prenda que quiera probarse.
3. El Cliente elige la sucursal donde quiere probárselas y consulta su disponibilidad (CU-19).
4. El Cliente elige la franja horaria en la que va a pasar.
5. El Cliente confirma la reserva.
6. El sistema comprueba, en este orden, que la sucursal esté activa, que la franja sea válida, que las prendas sigan en el catálogo y que quede probador libre en esa franja.
7. El sistema aparta el stock de cada prenda —de disponible a reservado, con su movimiento— y registra la reserva en estado `PENDIENTE`, todo en una sola transacción. Devuelve la reserva con su detalle.

**Flujos alternativos**

- **2a. Subir la cantidad.** El Cliente pide más de una unidad de la misma variante, en lugar de agregarla dos veces.
- **5a. Consultar sus reservas.** El Cliente ve sus reservas con su estado y su franja, y puede filtrar las que siguen vivas.
- **7a. Prenda que llega de otra sucursal.** No se contempla: la reserva es por sucursal, y trasladar mercadería es CU-15.

**Excepciones**

- **E1. Prenda inexistente o desactivada.** El sistema lo impide y señala **qué** prendas, sin invalidar la reserva entera.
- **E2. Sucursal dada de baja.** No se reserva en una sucursal que no atiende.
- **E3. Franja en el pasado.** Con dos minutos de tolerancia para el desfase de reloj entre el navegador y el servidor.
- **E4. Duración inválida.** La franja tiene que durar entre 15 y 120 minutos.
- **E5. Demasiada anticipación.** No se reserva más allá de `RESERVA_ANTICIPACION_MAXIMA_HORAS` (72 h por defecto).
- **E6. Sin probadores libres.** Si las reservas vivas que se solapan con esa franja igualan la capacidad de vestidores de la sucursal, se rechaza.
- **E7. Prenda repetida en dos líneas.** Se pide subir la cantidad.
- **E8. Fuera del horario de atención.** La franja tiene que caer dentro del horario de esa sucursal.
- **E9. Sin stock suficiente.** Si una prenda no alcanza, **no se aparta ninguna**.

---

## Lo que no se lee en la ficha

### Reservar no descuenta stock: lo traslada

Es la decisión **D3** y es la que hace posible mostrar disponibilidad real sin sobrevender. Una
reserva mueve unidades de `cantidad_disponible` a `cantidad_reservada`; el **total físico no
cambia**, porque la prenda sigue colgada en la percha — lo que cambia es que ya tiene dueño. Hay
prueba de que `cantidad_fisica` se mantiene igual antes y después.

### Por qué el movimiento de RESERVA vale −n

El invariante del inventario es uno solo y se escribe así:

```
cantidad_disponible == suma(movimientos.cantidad)
```

Es lo que afirma **D4** y lo que comprueba `test_el_saldo_es_la_suma_de_sus_movimientos` desde
CU-13. Con ese invariante a la vista, el signo de cada tipo deja de ser una convención y pasa a ser
una consecuencia: `RESERVA` saca unidades del disponible, así que vale **−n**; `LIBERACION` las
devuelve, así que vale **+n**.

**El caso que obligó a pensar es la venta de una reserva atendida** (CU-24, resultado `LLEVA`). Esas
unidades ya salieron del disponible cuando se creó la reserva, así que una `VENTA` de −n las
descontaría dos veces y el saldo quedaría negativo; y un movimiento de cero lo rechaza el CHECK
`ck_movimiento_inventario_cantidad_no_nula`.

> **Queda fijada la convención para CU-24: se escriben DOS movimientos.** Una `LIBERACION` de +n
> —que devuelve las unidades al disponible y vacía la reservada— y acto seguido una `VENTA` de −n.
> El neto sobre el disponible es cero, los dos movimientos son no nulos, el invariante se sostiene, y
> el historial se lee como lo que de verdad pasó: «volvieron del apartado y se vendieron».

De ahí sale el segundo invariante, que también tiene prueba:

```
cantidad_reservada == -suma(RESERVA) - suma(LIBERACION)
```

### La mitigación del riesgo R5 vive en P4, no en P6

`apartar_para_reserva()` está en `inventario/service.py` y es quien toma el
`SELECT ... FOR UPDATE`. P6 la llama; **no escribe `existencia` ni `movimiento_inventario` por su
cuenta**. La regla «ninguna cantidad se modifica sin generar un movimiento» es de P4, y si P6 tocara
esas tablas habría dos lugares que la conocen y uno de los dos se olvidaría.

Lo que P6 sí controla es **la transacción**, porque apartar tres prendas tiene que ser todo o nada y
eso solo lo sabe P6.

### El orden de las comprobaciones no es casual

Primero va todo lo que se puede rechazar **sin tocar ninguna fila** —cliente, sucursal, franja,
prendas, capacidad— y recién al final se aparta el stock, que es lo único que toma bloqueos. Al
revés, una reserva con la franja mal escrita tendría tomadas las existencias de tres variantes
mientras se descubre el error, haciendo esperar a quien sí estaba reservando bien.

### La capacidad de vestidores por fin sirve para algo

`sucursal.capacidad_vestidores` se declaró en el Ciclo 1 y **ningún caso de uso la leía**. CU-22 la
usa para la excepción E6: si las reservas vivas que se solapan con la franja pedida igualan la
capacidad, se rechaza. Sin esto, veinte clientes reservan la misma franja en una tienda con dos
probadores y el sistema promete algo que la sucursal no puede cumplir.

**Dos franjas se solapan si `inicio_a < fin_b AND inicio_b < fin_a`**, con `<` estricto a propósito:
una reserva de 15:00 a 16:00 y otra de 16:00 a 17:00 **no** se solapan. Con `<=` no se podrían
encadenar turnos consecutivos, que es el uso normal de un probador. Tiene prueba.

### La franja se compara contra la hora de pared de la tienda

`horario_apertura` y `horario_cierre` son `TIME` sin zona: representan «abre a las nueve» en esa
tienda. La franja llega con zona, porque las columnas son `timestamptz`. **Convertir la franja a UTC
antes de compararla contra el horario haría que una sucursal que abre a las 09:00 rechazara una
reserva a las 09:30 por cuatro horas de diferencia horaria.** La prueba de E8 usa una zona real
(−04:00) y no UTC justamente para atrapar ese error.

Y la franja **tiene que traer zona horaria**: sin ella el servidor tendría que suponer cuál es, y
suponer mal significa que una reserva creada a las 23:00 expire cuatro horas antes de lo que dice la
pantalla.

### Por qué hay un tope de anticipación, y por qué es una variable de entorno

La reserva inmoviliza unidades **desde que se crea hasta que su franja vence**. Reservar para dentro
de un mes dejaría stock apartado un mes. `RESERVA_ANTICIPACION_MAXIMA_HORAS` existe para proteger el
inventario, no para incomodar al cliente, y es configurable porque es una política de negocio que una
tienda real querría ajustar.

**No se reutilizó `RESERVA_VIGENCIA_HORAS`**, que ya existía: esa es otra cosa —cuánto aguanta una
reserva *después* de que su franja terminó, antes de que CU-25 la expire, o sea la tolerancia para el
cliente que llega tarde—. Darle dos significados a una variable es cómo se rompen las configuraciones.

### Una reserva ajena devuelve 404, no 403

Un 403 confirmaría que esa reserva existe, y eso ya es información sobre otro cliente. La propiedad
se comprueba en el servicio y no en el *router* porque hace falta leer la fila para saber de quién
es: el *router* no puede autorizar lo que todavía no leyó.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `POST` | `/reservas` | 4-7 · crear la reserva completa |
| `GET` | `/reservas` | 5a · mis reservas, con filtros y paginación |
| `GET` | `/reservas/{id}` | detalle de una reserva propia |

Todos exigen rol **Cliente**, declarado una sola vez en el *router*. CU-24 es del Encargado y mira
las reservas *de su sucursal*, que es otro ámbito de datos: cuando se implemente va en un *router*
aparte, por la regla de la §6.11.4.

## Pantallas

| Plataforma | Ruta | Estado |
|---|---|---|
| Web | `/mi-cuenta/reservas` | ✔ Entregada |
| Móvil | `reservas` | **Pendiente** |

### La pantalla invierte el orden del formulario, a propósito

El servidor recibe sucursal, franja y prendas; la pantalla pide **primero las
prendas**. La pregunta del cliente es «¿dónde puedo probarme esto?», no «¿qué hay
en la sucursal Centro?».

Eligiendo primero las prendas, el selector de sucursal puede ofrecer **solo las
que tienen stock de todas ellas** —cruzando la disponibilidad de cada variante
con CU-19, que se apoya en la costura C1— en vez de dejar armar una combinación
que el servidor va a rechazar con un 409 después de que el cliente ya eligió día
y hora.

Y si se agrega una prenda que la sucursal elegida no tiene, la selección se
limpia sola en vez de quedar mostrando algo inválido.

### El detalle de la hora que no se ve

`toISOString()` **no sirve** para mandar la franja: convierte a UTC, de modo que
las 15:00 de Bolivia salen como `19:00Z`. El servidor compara esa hora contra
`sucursal.horario_apertura`, que es un `TIME` sin zona y significa «abre a las
nueve» *en esa tienda*; con la hora convertida, un local que cierra a las 18:00
rechazaría una reserva perfectamente válida.

La pantalla manda la hora de pared **más el desfase** —`2026-09-12T15:00:00-04:00`—,
que es lo que el *backend* exige y lo que `timestamptz` guarda sin ambigüedad.
Está en `conDesfase()`, con el porqué escrito al lado.

## Pruebas

`backend/tests/test_cu22_reservas.py` — 21 pruebas. Las que cubren lo que la base **no** garantiza
por sí sola:

- **`test_r5_dos_clientes_no_pueden_reservar_la_ultima_unidad`** — la prueba que el plan exige por su
  nombre (§5.6, riesgo R5). Dos hilos, **dos conexiones reales** a PostgreSQL, la misma última
  unidad. Sin el `FOR UPDATE` los dos leen «queda 1» y los dos reservan; con él, el segundo espera,
  relee «quedan 0» y falla. El resultado tiene que ser exactamente un éxito y un rechazo. Es la única
  prueba del proyecto que abre dos conexiones de verdad.
- `test_si_una_prenda_no_tiene_stock_no_se_aparta_ninguna` — la transacción, que importa más acá que
  en un ingreso: stock apartado sin reserva que lo explique no lo libera nadie.
- `test_la_reserva_aparta_el_stock_sin_destruirlo` — **D3**, comprobando que el físico no se mueva.
- `test_el_saldo_sigue_siendo_la_suma_de_sus_movimientos` — **D4** con un tipo que mueve los dos
  bolsillos. Si el signo de `RESERVA` estuviera al revés, el invariante se rompería acá.
- `test_no_se_reserva_fuera_del_horario_de_la_sucursal` — con zona real, para atrapar el error de
  convertir a UTC antes de comparar.
- `test_dos_franjas_consecutivas_no_se_solapan` — que los turnos encadenados sigan siendo posibles.
