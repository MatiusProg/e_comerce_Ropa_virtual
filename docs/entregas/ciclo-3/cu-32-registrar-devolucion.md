# CU-32 · Registrar devolución

Guía de lo que se construyó y por qué cada decisión es como es.

> **Escrita el 20/09/2026.** Cierra el área de Caja: CU-30 abre el turno, CU-31
> cobra y CU-32 recibe de vuelta. Las tres cuelgan del mismo turno y las tres
> terminan en el mismo arqueo.

---

## 1. Lo que resuelve

> Permite al Cajero registrar la devolución de una prenda vendida,
> **reingresándola al inventario de la sucursal con su movimiento
> correspondiente**.

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

## 7. Lo que queda pendiente

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
