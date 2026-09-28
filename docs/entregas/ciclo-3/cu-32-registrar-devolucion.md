# CU-32 · Registrar devolución

Guía de lo que se construyó y por qué cada decisión es como es.

> **Escrita el 20/09/2026.** Cierra el área de Caja: CU-30 abre el turno, CU-31
> cobra y CU-32 recibe de vuelta. Las tres cuelgan del mismo turno y las tres
> terminan en el mismo arqueo.
>
> **Ampliada el 24/09/2026 con el segundo flujo, el cambio de prenda**
> (migración `0020`). Las secciones 1 a 6 describen el flujo de devolución tal
> como se entregó; la **sección 7** describe el cambio, y la 8 lo que sigue
> pendiente después de él.

---

## 1. Lo que resuelve

> Permite al Cajero registrar la devolución de una prenda vendida,
> **reingresándola al inventario de la sucursal con su movimiento
> correspondiente**, o **cambiarla por otra** dentro del plazo que fija la
> tienda.

**Son dos flujos de un mismo caso de uso y no dos casos de uso.** El cliente
elige entre devolver y cambiar **con la prenda ya sobre el mostrador**, después
de que el cajero buscó la venta: la decisión es parte del mismo trámite.
Comparten el actor, la precondición —una venta cobrada en esta sucursal, dentro
del plazo— y la mitad del recorrido, porque lo que vuelve se valida igual en los
dos. Se separan recién en el último paso, que es **a dónde va el valor de lo
devuelto**: al cajón, o contra una prenda nueva.

Dos efectos, y conviene no mezclarlos:

1. **La prenda vuelve al inventario.** Siempre. Lo que volvió al local está en
   el local, y eso no depende de cómo se haya pagado.
2. **La plata sale del cajón.** Solo a veces. Y ahí está lo interesante.

## 2. La decisión que sostiene el arqueo

`devolucion.monto` **no es «el valor de lo devuelto»: es lo que sale del
cajón**. Lo fija CU-30, que lo resta del monto esperado del turno:

```
monto_esperado = monto_apertura + efectivo cobrado − devoluciones
```

Si una venta cobrada **con tarjeta** se devolviera y su monto sumara ahí, el
turno cerraría con un faltante que nadie puede explicar: esa plata **nunca
entró al cajón**, así que tampoco puede salir de él. Y el faltante se le
anotaría al cajero, que no hizo nada mal.

Por eso:

| La venta se cobró con | La prenda vuelve al inventario | `monto` | El reintegro |
|---|---|---|---|
| EFECTIVO | sí | el valor devuelto | billetes, del cajón |
| TARJETA | sí | **0.00** | vuelve por la tarjeta |
| QR | sí | **0.00** | vuelve por el QR |
| (pedido web) | sí | **0.00** | vuelve por la pasarela |

El contrato saca **los dos números por separado**, porque la pantalla necesita
decir dos cosas distintas:

```jsonc
{
  "valor_devuelto": "250.00",   // lo que valen las prendas que volvieron
  "monto": "0.00",              // lo que sale del cajón
  "sale_del_cajon": false
}
```

«Son Bs 250» y «no los saque del cajón» son dos frases, y las dos hacen falta.
Mostrar solo la primera llevaría al cajero a abrir el cajón y entregarlos.

## 3. Una devolución no corrige la venta: es un hecho nuevo

No se edita la `Venta`, no se borra el `DetalleVenta`, no se toca el movimiento
de `VENTA`.

Los movimientos de inventario son **inmutables** (D4), y la venta lo es por el
mismo motivo: si se editara, el historial diría que la prenda nunca se vendió
—y el reporte de rotación, el ticket promedio de CU-36 y el arqueo del turno en
que se cobró **cambiarían solos, hacia atrás**—.

Lo que la devolución escribe es una fila `Devolucion`, sus `DetalleDevolucion`
y un movimiento `DEVOLUCION +n` por prenda. La venta sigue diciendo lo que dijo
el día que ocurrió.

### La costura nueva en P4

`inventario.reingresar_por_devolucion` es la inversa exacta de
`descontar_por_venta`: un `DEVOLUCION +n` y nada más. No hay que liberar nada
antes, porque la prenda devuelta no estaba apartada: salió de la tienda y
volvió.

Usa `_existencia_o_crearla` y no `obtener_existencia`: una prenda puede
devolverse en la sucursal aunque su fila de existencia se haya borrado —o
aunque la venta fuera un pedido web abastecido desde otra—, y negarse a
reingresarla dejaría la prenda **físicamente en el local y fuera del sistema**.

`DEVOLUCION` ya estaba en `TIPOS_MOVIMIENTO` desde la `0003`, y el docstring de
`_aplicar_movimiento` ya lo listaba con signo `+n`. **No hizo falta migración.**

## 4. Las reglas que el código impone

| Regla | Por qué |
|---|---|
| **Sin turno abierto no se devuelve** | La devolución sale de un cajón y cuelga de un turno: `devolucion.turno_caja_id` es NOT NULL. |
| **Solo ventas PAGADA o ENTREGADA** | Una `PENDIENTE_PAGO` no se cobró y una `CANCELADA` ya se deshizo. Devolver cualquiera de las dos sería sacar mercadería y plata contra una venta que no ocurrió. |
| **Solo de esta sucursal** | Convención 1: una venta de otra sucursal no existe para este cajero. 404, nunca 403. |
| **No más de lo que queda por devolver** | `vendidas − ya devueltas`. No hay restricción en la base que lo impida —dos devoluciones parciales son legítimas—, así que la cuenta la hace el servicio. |
| **El precio es el CONGELADO de la venta** | Se reintegra lo que el cliente pagó, no lo que la prenda cuesta hoy. Si la tienda subió el precio, devolverle el nuevo sería regalarle la diferencia. |
| **El motivo es obligatorio** | Una devolución sin motivo es mercadería y plata que nadie puede auditar después. Dejarlo opcional garantiza que quede vacío siempre. |
| **Una prenda que no estaba en la venta, no vuelve** | 422. Sería reingresar stock contra una venta que no la incluía. |

### El bloqueo sobre la venta

`bloquear_venta` toma `SELECT … FOR UPDATE` sobre la venta **antes** de leer lo
ya devuelto. Sin él, dos devoluciones simultáneas de la misma venta leen el
mismo saldo, las dos concluyen que queda una unidad y **las dos la devuelven**:
la tienda reingresa dos prendas que nunca salieron y paga dos veces.

No hay CHECK que lo atrape, porque la regla cruza dos tablas.

## 5. Los endpoints

```
GET  /api/v1/pos/devoluciones/ventas/{codigo}   la venta y lo que queda por devolver
POST /api/v1/pos/devoluciones                   registrarla → 201
```

**CAJERO y ENCARGADO**, los mismos que CU-30 y CU-31. Ninguno recibe
`sucursal_id`: sale del turno abierto de quien pide.

```jsonc
{
  "venta_codigo": "VP-20260920-A3F2",
  "motivo": "No le quedó bien",
  "lineas": [{"variante_id": 12, "cantidad": 1}]
}
```

La ficha de la venta no lista lo vendido a secas: lista **lo que todavía queda
por devolver**. Ofrecer las unidades que ya volvieron llevaría a reingresarlas
dos veces.

## 6. La pantalla

`/caja/devoluciones`, la tercera sección de la cáscara del Cajero —que con esto
**queda completa**: ya no hay ninguna entrada apagada en su barra—.

Tres decisiones:

- **Arranca en cero, no en «todo».** Devolver la venta entera es una decisión,
  no el valor por omisión. Con todo marcado, un descuido reingresa mercadería
  que el cliente no trajo. Hay un botón «devolver todo lo que queda» para
  cuando sí es eso.
- **La marca «no sale del cajón» va arriba, junto al código de la venta.** El
  cajero tiene que verla **antes** de contar los billetes, no después de
  entregarlos.
- **La línea ya devuelta se apaga, no se esconde.** Necesita saber que esa
  prenda estaba en la venta y que ya volvió, no que desapareció.

El dinero se suma en centavos enteros, igual que en CU-31.

## 7. El segundo flujo: el cambio de prenda

### 7.1 Un cambio es una devolución que además vende

Lo que vuelve ya lo sabe expresar `devolucion` con sus `detalle_devolucion`; lo
que sale ya lo sabe expresar `venta` con sus `detalle_venta`. Una tabla nueva
tendría que volver a modelar una de las dos y quedaría con la mitad de las
reglas duplicadas —el precio congelado, el descuento de CU-12, el comprobante—.

Así que **el cambio es una fila de `devolucion` que apunta a una `venta`**, y
la migración `0020` agrega cuatro columnas:

| columna | en una DEVOLUCIÓN | en un CAMBIO |
|---|---|---|
| `tipo` | `DEVOLUCION` | `CAMBIO` |
| `venta_cambio_id` | NULL | la venta nueva, UNIQUE |
| `monto` | el reintegro, si se pagó en efectivo | **siempre 0** |
| `diferencia` | siempre 0 | total nuevo − valor devuelto, **CON SIGNO** |
| `metodo_diferencia` | NULL | cómo se salda, si hay algo que saldar |

Seis CHECK hacen imposible una combinación incoherente: un cambio sin venta
nueva, una devolución con diferencia, un método de pago contra una diferencia de
cero, o un cambio que saque plata del cajón por la prenda vieja.

### 7.2 `monto` y `diferencia` no son lo mismo, y por eso son dos columnas

`devolucion.monto` significa, desde CU-30, **lo que sale del cajón**. En un
cambio no sale nada por la prenda devuelta: su valor se **acredita** contra la
prenda nueva. Lo único que se mueve en el cajón es la diferencia.

`diferencia` es **la única columna con signo de todo P7**, y lo es a propósito:
positiva paga el cliente, negativa devuelve la tienda. Partirla en dos columnas
no negativas obligaría a un CHECK que impida que las dos tengan valor a la vez,
y a que cada consulta se acuerde de restar una y sumar la otra.

### 7.3 Lo que esto obligó a cambiar en el arqueo de CU-30

La venta nueva vale **la prenda que sale** —Bs 250—, no lo que entró al cajón
—Bs 50—. Si contara como efectivo, el turno cerraría con un sobrante de 200 que
el cajero no puede explicar ni contando bien.

Se podía excluirla con un `NOT EXISTS` en cada consulta del arqueo. Se prefirió
**darle su propio método de pago**:

```
venta.metodo_pago = 'CAMBIO'
```

Con eso, el filtro que ya existía —`metodo_pago = 'EFECTIVO'`— la deja fuera sin
ninguna condición nueva, **ninguna consulta futura puede olvidarse de
excluirla**, y el desglose del cierre la muestra en su propia línea en vez de
esconderla: la mercadería sí se movió, y el cajero lo sabe.

`CAMBIO` **no es una forma de cobrar**: no se puede elegir en la pantalla de
venta y no vale para `metodo_diferencia`. Por eso el modelo tiene dos tuplas,
`METODOS_PAGO` y `METODOS_VENTA`, y sólo la segunda lo incluye.

La fórmula del arqueo queda:

```
monto_esperado = monto_apertura
               + efectivo cobrado
               − devoluciones
               ± diferencias de cambios saldadas en efectivo
```

El último término **suma** aunque represente una salida de plata, porque ya
viene con signo. Restarlo invertiría el caso más común —el cliente se lleva algo
más caro y pone la diferencia— y el error no se vería hasta que un turno con
cambios cerrara al revés.

### 7.4 El orden: primero entra lo viejo, después sale lo nuevo

Es el orden del mostrador —el cliente entrega y después recibe— y además es el
único que resuelve el caso más común de todos: **cambiar una prenda fallada por
otra igual**. Si se descontara primero, la última unidad no estaría disponible
todavía y el cambio se rechazaría por falta de stock de una prenda que el
cliente tiene en la mano.

### 7.5 El plazo

`DEVOLUCION_PLAZO_DIAS`, por defecto **2 días**, y vale igual para devolver que
para cambiar. Si el cambio durara más, cambiar por algo y devolver eso sería la
forma de devolver fuera de plazo.

**Se cuenta en horas desde el cobro, no en fechas de calendario.** Con fechas,
quien compra un lunes a las 23:50 tendría casi tres días y quien compra ese
mismo lunes a las 08:00 tendría poco más de dos. El plazo es el mismo para los
dos o no es un plazo.

**Es una configuración y no una constante** porque es una decisión de la tienda
—la temporada de fin de año suele estirarlo—, y **no se guarda en cada
devolución**: guardarlo congelaría en cada fila una política comercial que va a
cambiar, y además no se puede reconstruir hacia atrás, porque las devoluciones
ya escritas se registraron sin plazo ninguno.

El plazo se **informa** al buscar la venta y se **exige** al registrar. Una venta
vencida se busca y se encuentra igual, con `dentro_de_plazo` en falso: el cajero
necesita poder abrirla para explicarle al cliente por qué no se puede y desde
cuándo. Un plazo que sólo se descubre al confirmar hace perder el trabajo hecho
y deja al cajero discutiendo sin un número que mostrar.

### 7.6 Por qué es un endpoint y no dos llamadas desde la pantalla

```
POST /api/v1/pos/devoluciones/cambios   → 201
```

El cambio podría armarse llamando a `POST /devoluciones` y después a
`POST /pos/ventas`, sin una sola línea de backend nueva. No se hace, por tres
motivos que el mostrador nota:

1. **No sería atómico.** Entre las dos llamadas se puede caer la red o agotarse
   el stock de la prenda nueva, y el cliente queda sin la vieja —ya
   reingresada— y sin la nueva.
2. **El cajón quedaría mal.** La devolución sacaría Bs 200 y la venta metería
   Bs 250, cuando lo que pasó sobre el mostrador fue que el cliente puso 50. El
   arqueo daría el mismo total, pero el desglose mentiría, y el cajero contaría
   billetes que nunca movió.
3. **Se perdería el vínculo.** Nada diría que esa venta salió de ese cambio, y
   ni el tablero ni la bitácora podrían reconstruirlo después.

```jsonc
{
  "venta_codigo": "VP-20260920-A3F2",
  "motivo": "Le quedó grande",
  "devueltas": [{"variante_id": 12, "cantidad": 1}],
  "llevadas":  [{"variante_id": 15, "cantidad": 1}],
  "metodo_diferencia": "EFECTIVO",
  "diferencia_esperada": "50.00"
}
```

**`metodo_diferencia` es opcional en el contrato y obligatorio cuando hay
diferencia.** La asimetría es a propósito: el precio final lo fija el servidor
—las promociones de CU-12 se leen al cobrar, no antes— así que la pantalla no
puede saber con certeza si va a haber diferencia. Exigirlo siempre obligaría a
mandar un método inventado en los cambios que salen parejos, y ese método
terminaría en la base diciendo que se movió plata que no se movió.

**`diferencia_esperada` es una guarda**, igual que `total_esperado` en CU-31: si
la pantalla calculó una diferencia y el servidor calculó otra —una promoción que
empezó en el medio—, se rechaza con 409 y se muestra el número nuevo, en vez de
cobrarle al cliente algo que no vio en pantalla.

### 7.7 La pantalla

La misma, `/caja/devoluciones`. Dos pantallas obligarían a elegir antes de tener
la información y a volver atrás cuando el cliente cambia de idea.

- **La elección va después de marcar qué vuelve.** Es el orden del mostrador.
- **La diferencia se dice en palabras además del número.** «Cobre Bs 50» y
  «Entregue Bs 50» son frases distintas; un signo menos se lee mal con el
  cliente esperando. El servidor manda `a_favor_de` —CLIENTE, TIENDA o NADIE—
  justamente para que la pantalla no tenga que interpretarlo.
- **El método de la diferencia no tiene valor por omisión.** Uno por defecto
  haría que la mitad de los cambios quedaran como efectivo sin que nadie lo
  decidiera, y el arqueo diría que entró plata que no entró.

### 7.8 Lo que verifican las pruebas

`tests/test_cu32_cambios.py`, 22 pruebas. Las que importan:

| Prueba | Qué protege |
|---|---|
| `el_arqueo_cuenta_la_diferencia_y_no_la_venta_entera` | El riesgo central: apertura 100 + venta 250 + diferencia 50 = **400**, no 700. |
| `una_diferencia_a_favor_de_la_tienda_baja_el_esperado` | Que el signo no esté invertido. |
| `una_diferencia_con_tarjeta_no_toca_el_cajon` | Que el filtro sea por cómo se salda hoy, no por cómo se pagó aquel día. |
| `cambiar_una_prenda_fallada_por_otra_identica_siendo_la_ultima` | El orden reingreso → descuento. |
| `sin_stock_de_la_nueva_no_queda_la_vieja_reingresada` | La atomicidad que dos llamadas no pueden dar. |
| `un_cambio_gasta_el_saldo_devolvible_de_la_venta` | Que cambiar y devolver salgan del mismo saldo. |

## 8. El agujero que esto destapó: el dinero devuelto no se veía

> **Encontrado el 24/09/2026 probando el flujo, y arreglado el mismo día.**

Al probar un cambio apareció que **la plata devuelta no figuraba en ningún
reporte ni en el tablero**. Buscando `devolucion` en todo el módulo `reportes`
no aparecía una sola vez.

Lo único rastreable era la **mercadería**, en el reporte de movimientos
filtrado por `DEVOLUCION`, y en **unidades**: nadie podía decir cuánto valía lo
que volvió, qué prenda vuelve más, ni en qué caja.

### 8.1 El cambio de prenda lo hizo más visible, y conviene decirlo así

El tablero suma `venta.total` sin restar nada, así que informaba como vendido
algo que estaba de vuelta en la percha. Eso ya pasaba con las devoluciones
puras. **El cambio agrega un caso más:** la venta original se sigue contando
*y además* nace una venta nueva por la prenda que sale.

```
vender un cinturón de 250  →  el tablero dice 250
cambiarlo por uno de 300   →  el tablero dice 550
lo que de verdad quedó vendido:  300
```

Sobra **exactamente el valor de lo devuelto**. El cambio no introdujo el error;
lo hizo imposible de ignorar.

### 8.2 Lo que se agregó

**Un séptimo reporte, `devoluciones`.** Una fila por línea devuelta —no por
devolución— porque es lo que permite las dos lecturas que hacen falta: **por
producto**, que es donde se ve una talla mal rotulada o una falla de
confección, y **por cajero**, que es quien la recibió. Agrupar por devolución
daría el flujo de caja y perdería las dos.

| Fecha | Sucursal | Tipo | Venta | Cajero | Prenda | Talla | Color | Cantidad | **Valor devuelto** |

**El tablero, neto.** Tres cifras nuevas: `devuelto_periodo`, `neto_periodo` y
sus equivalentes del día.

**`monto_periodo` NO cambió de significado**, y es deliberado: sigue siendo lo
vendido en bruto. Un tablero donde el mismo campo pasa a querer decir otra cosa
rompe en silencio a quien ya lo estaba leyendo. Y hacen falta los dos números,
no sólo el neto: «vendimos 10.000 y devolvieron 200» y «vendimos 10.000 y
devolvieron 4.000» dan el mismo neto y no son la misma situación.

**El ticket promedio sigue saliendo del bruto**, también a propósito: es cuánto
gasta quien compra, y una devolución posterior no cambia lo que esa persona
gastó ese día.

### 8.3 El valor devuelto no es una columna, y no debe serlo

`devolucion.monto` **no sirve** para esto: es lo que sale del cajón, y vale
cero con tarjeta, con QR y en **todo** cambio.

El valor real se reconstruye cruzando `detalle_devolucion` con `detalle_venta`
por **(venta, variante)**, para recuperar el precio congelado. Es un `join` por
dos columnas y no por una: la misma variante en otra venta se pagó otro precio.

Guardarlo como columna sería un dato derivado que puede contradecir a los tres
de los que sale —la misma razón por la que `detalle_venta` no guarda su
subtotal—. Y leer `variante_producto.precio` sería peor: un cambio de lista
reescribiría hacia atrás cuánto se devolvió el mes pasado.

## 9. Lo que queda pendiente

- **La devolución la inicia SIEMPRE el Cajero, nunca el cliente.** Anotado por
  Mateo el 24/09/2026 y **deliberadamente fuera de alcance**: lo natural es que
  quien compró por la web pueda *solicitar* la devolución desde su historial de
  compras (CU-29), y que el mostrador la reciba o la rechace. Eso es un caso de
  uso nuevo —con su estado «solicitada», su actor Cliente y su notificación—,
  no un flujo más de éste. Lo que existe hoy supone que la persona y la prenda
  están sobre el mostrador.
- **No hay comprobante de devolución en PDF.** El de la venta sí existe
  (CU-29 / CU-31). Un papel de devolución exige decidir qué dice respecto de la
  factura original, y eso es la misma conversación sobre facturación que este
  ciclo no tuvo.
- **La devolución no cancela la venta ni la marca.** Una venta devuelta entera
  sigue figurando como PAGADA, y es lo correcto: se cobró. Si el negocio
  quisiera un estado `DEVUELTA`, sería un estado más en `ESTADOS_VENTA` y una
  migración.
- **El reintegro por tarjeta o QR es una gestión fuera del mostrador.** El
  sistema registra que corresponde y cuánto; devolverlo por la pasarela sería
  otro caso de uso, con su propia conciliación.
- **No se puede deshacer una devolución mal cargada.** Como los movimientos son
  inmutables, la corrección sería un ajuste de inventario (CU-15) y una nota, y
  hoy hay que hacerlos a mano.
