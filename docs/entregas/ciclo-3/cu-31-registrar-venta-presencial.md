# CU-31 · Registrar venta presencial

Guía de lo que se construyó y por qué cada decisión es como es.

> **Escrita el 20/09/2026.** Se apoya en CU-30, que es su puerta: la base exige
> `turno_caja_id` en toda venta presencial, así que sin un turno abierto no se
> puede cobrar.
>
> **Sobre el reparto.** El plan del ciclo decía «Mateo (API) · Karen (UI)» para
> CU-30 y CU-31. CU-30 salió así. En CU-31 Mateo siguió con CU-20, CU-21 y
> CU-33, y el caso de uso se tomó **entero de este lado**, API incluida, para
> que no quedara a mitad de camino en la entrega. Es la misma decisión que se
> tomó con CU-28.

---

## 1. Lo que este caso de uso resuelve

La ficha de requisitos lo dice en una línea:

> Permite al Cajero registrar una venta en sucursal **buscando las variantes o
> cargando una reserva ya atendida**, cobrar en efectivo o tarjeta, emitir el
> comprobante y descontar el inventario.

Son **dos caminos de entrada** y un solo resultado: una `Venta` de canal
`PRESENCIAL` que nace `PAGADA`, colgada de un turno abierto, con su comprobante
emitido.

## 2. La decisión que sostiene todo: los dos caminos no descuentan lo mismo

Es lo único verdaderamente difícil de CU-31, y es un agujero que se abre solo
si no se piensa.

**Camino A — el cajero busca las prendas.** Las unidades están en el
disponible y nadie las apartó. Se escribe **un** movimiento: `VENTA −n`, por la
costura `inventario.descontar_por_venta`.

**Camino B — se cobra una reserva ya atendida.** Las unidades **ya salieron del
inventario**. CU-24, al cerrar la reserva, escribió `LIBERACION +n` y
`VENTA −n` por cada prenda con resultado `LLEVA`: el cliente se la llevó puesta
del probador, y el inventario tenía que decir la verdad en ese momento aunque
el cobro todavía no existiera. Su propio código lo dejó anotado:

> «Cuando P7 exista, CU-24 y el cobro pasan a ser una sola transacción y el
> movimiento de VENTA lo va a escribir la venta, no este caso de uso; hasta
> entonces lo escribe acá, con el motivo que lo explica.»

P7 ya existe. **Y aun así CU-24 sigue descontando, a propósito.**

Un segundo `VENTA −n` sobre las mismas unidades las contaría dos veces. El
disponible quedaría mintiendo **sin que nada reventara**, que es la peor forma
de un error de inventario: no hay excepción, no hay log, solo un número que
dejó de ser verdad.

| | Camino A | Camino B |
|---|---|---|
| Quién apartó el stock | nadie | la reserva, en CU-22 |
| Quién lo liberó | — | CU-24, al atender |
| Quién escribió `VENTA −n` | **CU-31** | **CU-24**, al atender |
| Qué hace CU-31 con el inventario | descuenta | **nada** |

Lo único que separa las dos historias en el código es una línea:

```python
def _descontar(db, *, lineas, mostrador, usuario_id, codigo, desde_reserva):
    if desde_reserva:
        return
    ...
```

Y lo único que impide que alguien la borre por parecerle de más es la prueba
`test_cobrar_una_reserva_no_vuelve_a_descontar`, que compara el disponible
antes y después de cobrar.

### Por qué no se movió el descuento a CU-31 — decidido el 20/09

Al principio esto quedó anotado como deuda: «cuando CU-24 deje de descontar, el
camino B tiene que empezar a hacerlo». Al ir a saldarla apareció que **moverla
empeora las cosas**, y se cerró como decisión.

El docstring de `atender_reserva` tiene la clave: «CU-24 y el cobro pasan a ser
**una sola transacción**». El plan no era mover una línea de un archivo a otro:
era que atender y cobrar fueran **un solo acto**.

Separados como están hoy —el Encargado atiende en el probador, el cajero cobra
en el mostrador— mover el `VENTA −n` a CU-31 abre una ventana real: entre los
dos momentos las unidades vuelven a estar **disponibles**, y otro cliente puede
comprarlas mientras el primero camina del probador a la caja con la prenda en
la mano.

| | Se gana | Se pierde |
|---|---|---|
| **Como está** | el inventario dice la verdad desde que la prenda sale del probador; no hay ventana de sobreventa | que el camino B de CU-31 no mueva inventario se lee raro —y está escrito— |
| **Moviéndolo** | «el que vende, descuenta»: más prolijo en el diagrama | la garantía de que no se venda dos veces la misma prenda |

Se eligió lo primero. **Fusionar los dos actos en una sola pantalla sería la
solución completa**, y es un rediseño de CU-24 y CU-31 juntos, no un arreglo:
queda como trabajo futuro con su motivo, no como deuda.

## 3. Un paquete propio, `app/modules/pos/`

CU-30 estrenó `app/modules/caja/` como paquete aparte en vez de meterse en
`ventas/`. CU-31 sigue esa línea.

Es el grado más fuerte de la convención de no pisarse: **ni siquiera archivos
propios dentro del paquete ajeno, sino un paquete propio al lado**. `ventas/`
—que es de CU-27— no se toca en ninguna línea.

```
app/modules/pos/
├── schemas.py       el contrato
├── repository.py    consultas y las dos escrituras
├── service.py       las reglas
└── router.py        los seis endpoints
```

Lo único que se reutiliza de `ventas/` son **lecturas y costuras**, no
escrituras:

| Se reutiliza | De dónde | Por qué |
|---|---|---|
| `historial_service.asegurar_comprobante` | CU-29 | Idempotente por el UNIQUE; ya resuelve la carrera |
| `historial_service._dibujar_pdf` | CU-29 | Dos funciones que dibujan el mismo recibo terminan divergiendo |
| `inventario.descontar_por_venta` | CU-13 | El bloqueo de fila y el invariante viven ahí |
| `caja_repository.turno_abierto_de_usuario` | CU-30 | La regla «un turno por caja» sigue siendo suya |

### Por qué `agregar_venta_presencial` es propia y no la de Mateo

`ventas.repository.agregar_venta` **no acepta `metodo_pago`** —no lo necesita,
porque CU-27 solo crea ventas digitales y ahí el CHECK exige que sea NULL—.
Agregarle el parámetro sería editar un archivo suyo a un día de la entrega.

Además, la versión propia **no puede armar una venta presencial inválida**: el
turno es obligatorio, y la modalidad y la dirección ni siquiera son
parámetros. Los tres CHECK quedan satisfechos **por construcción** y no por
disciplina de quien la llama.

## 4. Las reglas que el código impone

| Regla | Por qué |
|---|---|
| **Sin turno abierto no se cobra** | Lo exige el CHECK `ck_venta_turno_segun_canal`. El servicio lo dice con palabras en vez de dejar que la base lo rechace con un error de integridad. |
| **La sucursal sale del turno, nunca del cuerpo** | Convención 2. Aceptarla dejaría a un cajero de Centro imputando una venta a la caja de Norte, y esa otra caja cerraría con un sobrante inexplicable. |
| **La venta nace PAGADA** | El dinero se recibe en el acto. Es lo contrario de CU-27, donde nace `PENDIENTE_PAGO` y solo el webhook firmado de CU-28 la mueve (D5). |
| **La venta presencial puede ser anónima** | «Quien entra, paga y se va no tiene por qué dejar sus datos». El cliente solo aparece cuando la venta viene de una reserva. |
| **Una reserva no se cobra dos veces** | `venta.reserva_id` es UNIQUE. El servicio lo dice antes de llegar ahí, y la reserva deja de ofrecerse. |
| **El precio se congela al vender** | `detalle_venta.precio_unitario` es copia, no lectura. Un comprobante impreso tiene que seguir coincidiendo con el sistema. |
| **Si el total cambió, se avisa** | 409 con los dos números. Entregar un ticket por un importe distinto del que se le dijo al cliente es lo que no puede pasar en un mostrador. |
| **Solo el efectivo da vuelto** | Con tarjeta o QR se cobra el importe exacto: ofrecer vuelto ahí sería sacar plata del cajón por un cobro que no entró. |
| **Si falta stock no queda nada a medias** | Una sola transacción: venta, líneas, descuento y comprobante. |

### Lo que no se cobra de una reserva

Solo las líneas con `resultado_prueba = 'LLEVA'`. Lo que el cliente devolvió a
la percha ya volvió al disponible en CU-24, y cobrarlo sería cobrarle una
prenda que no se llevó. Una reserva donde no se llevó nada **no se ofrece**:
está atendida y cerrada, y no hay nada que cobrar.

## 5. Los endpoints

```
GET  /api/v1/pos/prendas                       lo que hay para vender acá, con precio y saldo
GET  /api/v1/pos/reservas                      reservas atendidas sin cobrar
GET  /api/v1/pos/reservas/{id}                 el detalle de una, con los precios de hoy
POST /api/v1/pos/ventas                        cobrar → 201 con el ticket
GET  /api/v1/pos/ventas/{codigo}               releer, para reimprimir
GET  /api/v1/pos/ventas/{codigo}/comprobante   el PDF
```

**CAJERO y ENCARGADO**, los mismos que CU-30 y por el mismo motivo. El
administrador no: no está en una sucursal ni tiene turno.

**Ninguno recibe `sucursal_id`.** Todos lo sacan del turno abierto de quien
pide.

El cuerpo del cobro:

```jsonc
{
  "metodo_pago": "EFECTIVO",            // o TARJETA, o QR
  "lineas": [{"variante_id": 12, "cantidad": 2}],   // camino A
  "reserva_id": null,                   // camino B — excluyente con lineas
  "total_esperado": "500.00",           // opcional; si no coincide, 409
  "monto_recibido": "1000.00"           // opcional; solo para el vuelto
}
```

`monto_recibido` **no se guarda**: no hay columna donde ponerlo, e inventarla
para un número que sirve treinta segundos en el mostrador sería cargar el
esquema. Viaja de vuelta en el ticket junto con el vuelto y ahí termina.

### Por qué el código es `VP-` y no `VB-`

Las ventas de mostrador y los pedidos web comparten la misma columna única. El
prefijo distinto deja saber de un vistazo —en el arqueo, en el tablero, cuando
alguien lee un número por teléfono— de cuál de los dos canales vino cada una,
sin ir a mirar la fila.

## 6. Lo que el arqueo de CU-30 ve

Es la comprobación que hace que los dos casos de uso sirvan juntos:

| Método | Se registra | Suma al esperado | Aparece en el detalle |
|---|---|---|---|
| EFECTIVO | sí | **sí** | sí |
| TARJETA | sí | no | sí |
| QR | sí | no | sí |

Tarjeta y QR no entran al cajón. Sumarlos haría que todo turno con un pago con
tarjeta apareciera descuadrado, **y un arqueo que siempre descuadra enseña a
ignorarlo**. Pero sí se listan aparte: el cajero tiene que poder conciliar el
voucher del POS contra el sistema.

## 7. La pantalla

`/caja/vender`, dentro de la cáscara del Cajero que estrenó CU-30.

Tres cosas que hace a propósito:

1. **No deja cobrar sin turno, y lo dice al entrar.** El servidor lo rechaza
   igual, pero enterarse recién al pulsar «Cobrar», con el cliente esperando y
   el ticket armado, es la peor manera de saberlo.
2. **Calcula el total y lo manda como `total_esperado`.** No para que el
   servidor confíe en él —recalcula y manda—, sino para que el cobro se
   detenga si el precio cambió en el medio.
3. **Muestra el vuelto mientras se escribe.** Un cajero con billetes en la mano
   no puede estar esperando a que el servidor le diga cuánto devolver.

**El dinero no se convierte a `number` para sumarlo.** Se suma en centavos
enteros y se vuelve a texto con dos decimales: `250.00 + 0.1 + 0.2` en coma
flotante da `250.30000000000001`, y ese es exactamente el centavo que el
arqueo encuentra al cierre del turno.

La lista de prendas **solo muestra las que tienen saldo**. El inventario deja
ver las que están en cero porque al depositero le importa; en el mostrador no:
ofrecer una prenda agotada lleva al cajero a armar un ticket que va a fallar
con el cliente delante.

## 8. Lo que queda pendiente

- **Fusionar atender y cobrar en un solo acto.** Es lo que cerraría de verdad
  el puente de D2 —ver la sección 2—. No es una deuda de CU-31: es un rediseño
  de los dos casos de uso juntos, y hoy lo que hay funciona sin ventana de
  sobreventa.
- **No hay búsqueda de clientes.** Una venta de mostrador es anónima salvo que
  venga de una reserva. Identificar al cliente que compra sin reserva —para
  que la compra le aparezca en CU-29— necesita un buscador que no entró en el
  ciclo.
- **El comprobante es un RECIBO, no una factura.** `nit_ci` y `razon_social`
  quedan nulos. Emitir factura exige una numeración fiscal correlativa y una
  conversación sobre facturación que este ciclo no tuvo; el PDF lo dice al pie.
- **CU-12 (promociones) no existe**, así que el descuento viaja en cero. Las
  tres columnas ya están atadas por el CHECK `total = subtotal − descuento`:
  cuando exista, no hay que volver acá.
