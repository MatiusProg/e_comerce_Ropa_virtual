# Esquema de Ventas y Pagos — la migración `0006_ciclo3_ventas`

Las **nueve tablas** que crea la migración, de los paquetes **P7 · Ventas y Punto de Venta** y
**P8 · Pagos**. Es el contrato del que cuelgan CU-27 a CU-32, y también CU-36 y CU-37.

> **Actualizado el 17/09/2026.** La versión del 15/09 proponía once tablas e incluía `carrito` e
> `item_carrito`. **Esas dos ya existen**: las creó Karen en la `0009_ciclo3_carrito` al escribir
> CU-26, con los nombres `carrito` y `carrito_detalle`. Salen de acá, y con ellas cambia la
> decisión 4 sobre el congelamiento del precio. Lo que sigue es lo que la `0006` crea de verdad.

> **Por qué este documento existe.** Para el Ciclo 2 el acuerdo de columnas estaba en la §6.4 de
> [`ciclo-2/00-organizacion-por-caso-de-uso.md`](../ciclo-2/00-organizacion-por-caso-de-uso.md), y
> eso es lo que permitió escribir dos migraciones en paralelo sin pisarse. Para el Ciclo 3 ese
> acuerdo **no existía**: el análisis nombra las clases pero no sus atributos. Esto lo llena.

---

## 1. Lo que ya está acordado y no se discute

**El identificador y la cadena.** `0006_ciclo3_ventas` es de Mateo, por la §4 de
[`ciclo-2/04-respuesta-de-karen.md`](../ciclo-2/04-respuesta-de-karen.md). **La cabeza ya no es la
`0008` sino la `0009_ciclo3_carrito`**, que entró el 15/09 con CU-26:

```python
revision      = "0006_ciclo3_ventas"
down_revision = "0009_ciclo3_carrito"
```

La cadena queda `0005 → 0008 → 0009 → 0006 → 0007`. Se lee raro y es correcta: el número del
archivo es un nombre, el orden lo da `down_revision`. **Colgarla de la `0008` dejaría el árbol con
dos cabezas y `alembic upgrade head` fallaría pidiendo cuál.**

**Las decisiones de arquitectura que esto realiza**, de `docs/04-analisis-arquitectura.md`:

| | Qué dice | Cómo se cumple acá |
|---|---|---|
| **D1** | todo referencia `variante_producto`, nunca `producto` | `detalle_venta` y `detalle_devolucion` apuntan a `variante_id`, igual que el `carrito_detalle` de CU-26 |
| **D2** | una sola `Venta` con dos canales | `venta.canal` = `DIGITAL` \| `PRESENCIAL`; no hay tabla «pedido» aparte |
| **D3** | la existencia se descompone en disponible y reservado | la venta descuenta de reservado si vino de una reserva, de disponible si no |
| **D5** | el estado del pago **solo** lo determina la pasarela | `transaccion_pasarela.evento_id` es **único**: es lo que hace idempotente el webhook |

**El estilo**, igual que en la `0003`: escrita a mano y no con `--autogenerate`; `Numeric(10, 2)`
para dinero, como `variante_producto.precio`; `String(n)` con `CheckConstraint` para los estados,
no `Enum` de PostgreSQL; y en los CHECK **va solo el sufijo** (`name="estado"`, no
`name="ck_venta_estado"`), porque la convención de `app/db/base.py` antepone el resto.

---

## 2. Las nueve tablas

### P7 · Ventas

> **`carrito` y `carrito_detalle` no se crean acá.** Ya existen desde la `0009_ciclo3_carrito`
> (CU-26, de Karen). La `0006` no las toca. Lo único que hay que saber al escribir CU-27 es que
> **`carrito_detalle` no guarda precio**: el precio se lee en vivo contra `variante_producto`, y se
> congela recién al crear la venta. La razón está en la decisión 4, más abajo.

#### `venta` — CU-27, CU-31
La tabla central. **Un solo concepto para los dos canales (D2).**

| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `codigo` | `String(20)`, único | legible para el cliente |
| `canal` | `String(12)` | `DIGITAL` \| `PRESENCIAL` |
| `estado` | `String(20)` | ver abajo |
| `cliente_id` | FK → `cliente`, **nullable** | la venta presencial puede ser anónima |
| `sucursal_id` | FK → `sucursal` | la que abastece; en presencial, donde se vendió |
| `turno_caja_id` | FK → `turno_caja`, nullable | obligatorio en `PRESENCIAL` |
| `reserva_id` | FK → `reserva`, nullable, único | **D2**: una reserva atendida se convierte en venta |
| `modalidad_entrega` | `String(10)`, nullable | `RETIRO` \| `ENVIO`; solo en `DIGITAL` |
| `direccion_id` | FK → `direccion_cliente`, nullable | obligatorio si `ENVIO` |
| `subtotal`, `descuento`, `total` | `Numeric(10,2)` | CHECK `total = subtotal - descuento` |
| `creado_en` / `actualizado_en` | mixin | |

**Estados:** `PENDIENTE_PAGO` → `PAGADA` → `ENTREGADA`, y `CANCELADA` desde cualquiera de las dos
primeras. La venta `PRESENCIAL` nace directamente en `PAGADA`: no pasa por la pasarela.

#### `detalle_venta` — CU-27, CU-31
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `venta_id` | FK → `venta`, `ON DELETE CASCADE` | |
| `variante_id` | FK → `variante_producto` | **D1** |
| `cantidad` | `Integer` | CHECK `> 0` |
| `precio_unitario`, `descuento_unitario` | `Numeric(10,2)` | congelados al vender |

**Inmutable**, como `movimiento_inventario` (D4): una corrección es una devolución, no un `UPDATE`.

#### `comprobante` — CU-27, CU-31
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `venta_id` | FK → `venta`, **único** | uno por venta |
| `tipo` | `String(10)` | `RECIBO` \| `FACTURA` |
| `numero` | `String(20)`, único | |
| `nit_ci`, `razon_social` | `String` | los datos que el cliente da al facturar |
| `emitido_en` | `DateTime(timezone=True)` | |

#### `caja` — CU-30
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `sucursal_id` | FK → `sucursal` | |
| `nombre` | `String(50)` | único por sucursal |
| `activa` | `Boolean` | |

#### `turno_caja` — CU-30
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `caja_id` | FK → `caja` | |
| `usuario_id` | FK → `usuario` | el Cajero que lo abrió |
| `abierto_en` / `cerrado_en` | `DateTime(timezone=True)`, el segundo nullable | |
| `monto_apertura`, `monto_cierre`, `monto_esperado` | `Numeric(10,2)` | el cierre y el esperado, nullable hasta cerrar |

**Índice único parcial:** un solo turno abierto por caja. Es el mismo patrón del carrito, y por la
misma razón: dos turnos abiertos hacen que el arqueo no cierre nunca.

#### `devolucion` y `detalle_devolucion` — CU-32
| `devolucion` | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `venta_id` | FK → `venta` | |
| `turno_caja_id` | FK → `turno_caja` | dónde se procesó |
| `motivo` | `String(200)` | |
| `monto` | `Numeric(10,2)` | |
| `creado_en` | | inmutable, sin `actualizado_en` |

`detalle_devolucion` es `(devolucion_id, variante_id, cantidad)`, con CHECK de cantidad positiva.
Devolver **reingresa** al inventario con un `movimiento_inventario` de tipo devolución.

### P8 · Pagos

#### `pago` — CU-27, CU-28
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `venta_id` | FK → `venta`, **único** | un pago por venta |
| `metodo` | `String(12)` | `PASARELA` \| `EFECTIVO` \| `TARJETA_POS` |
| `estado` | `String(12)` | `INICIADO` \| `APROBADO` \| `RECHAZADO` \| `REEMBOLSADO` |
| `monto` | `Numeric(10,2)` | |
| `referencia_externa` | `String(100)`, nullable, único | el id de la sesión de la pasarela |
| `creado_en` / `actualizado_en` | mixin | |

#### `transaccion_pasarela` — CU-28, **la tabla que realiza D5 y RNF09**
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `pago_id` | FK → `pago`, nullable | nullable a propósito: ver abajo |
| `evento_id` | `String(100)`, **ÚNICO** | el id del evento que manda la pasarela |
| `tipo_evento` | `String(50)` | |
| `firma_valida` | `Boolean` | |
| `carga_util` | `Text` | el JSON crudo, tal cual llegó |
| `recibido_en` | `DateTime(timezone=True)` | |

**Inmutable.** Es el registro de todo lo que la pasarela dijo, se haya aplicado o no.

> **Acá está toda la idempotencia, y es una sola restricción.** El `UNIQUE` sobre `evento_id` es lo
> que hace que una notificación repetida **no descuente el inventario dos veces**: el `INSERT`
> falla, el servicio lo trata como «ya visto» y no vuelve a tocar la venta. Sin esa restricción, la
> idempotencia habría que resolverla con lógica, y la lógica se puede equivocar cuando dos webhooks
> llegan a la vez.
>
> **`pago_id` es nullable** porque un evento puede llegar sin que sepamos aún a qué pago
> corresponde —o con firma inválida—, y esos también hay que guardarlos: son justamente los que
> uno quiere mirar cuando algo sale mal.

---

## 3. Las cuatro decisiones que quiero confirmadas

1. **No hay tabla `pedido`.** «Realizar pedido» (CU-27) crea una `venta` en `PENDIENTE_PAGO`. Es lo
   que dice D2 y evita duplicar el descuento de inventario, los comprobantes y los reportes. La
   alternativa —`pedido` y `venta` separadas— obligaría a copiar los detalles de una a otra.
2. **P8 va en la misma migración que P7.** Los identificadores reservados solo nombran `ventas` y
   `promociones`, y pagos no tiene número propio. Una venta digital sin su fila de pago está a
   medias, así que las nueve tablas nacen juntas.
3. **`venta.reserva_id` es único y nullable.** Es el puente de D2: el Encargado atiende una reserva
   (CU-24) y esa misma reserva se cobra como venta presencial, sin transformar datos.
4. **El precio se congela en dos lugares** —`detalle_venta` y `pago.monto`— y ninguno se
   recalcula después. **Corrección del 17/09: eran tres, y `item_carrito` salió.** El carrito
   **no** congela precio, y no es un descuido de CU-26 sino lo correcto:

   - **El carrito no caduca.** Es uno solo por cliente (`UNIQUE` en `cliente_id`), sin estado y sin
     vencimiento. Congelar ahí es congelar para siempre: una prenda agregada hoy se cobraría en
     diciembre al precio de hoy. La versión del 15/09 sí daba una frontera —`carrito.estado`
     `ABIERTO`/`CONVERTIDO`/`ABANDONADO`— pero esa columna no existe.
   - **Se rompe hacia el lado que cobra de más.** Si la boutique baja un precio —rebajas, fin de
     temporada, que en ropa es lo normal— el cliente con la prenda en el carrito seguiría pagando
     el precio viejo.
   - **CU-12 lo volvería un error.** Si lo que se copiara fuera el precio con la promoción ya
     aplicada, una promoción vencida se honraría indefinidamente y una que arranca hoy no
     alcanzaría lo agregado ayer. En vivo, `_armar_carrito` aplica lo vigente.
   - **El proyecto ya eligió esto antes.** `reserva_detalle` (CU-22, `0003`) no tiene ninguna
     columna de dinero. No se congela en una intención; se congela al comprometer.

   Lo que sí hay que hacer es **de CU-27, no del esquema**: si el precio cambió entre que el
   cliente miró el carrito y confirmó el pedido, CU-27 lo avisa en vez de cobrar callado.

## 4. Lo que NO entra acá

- **Promociones (CU-12)** van en la `0007_ciclo3_promociones`, que también es nuestra.
  `detalle_venta` ya tiene `descuento_unitario` y `venta` ya tiene `descuento` para recibirlas. En
  el carrito el único punto de enganche es `_armar_carrito`, en `ventas/carrito_service.py`.
- **`carrito` y `carrito_detalle` (CU-26)**, que ya existen en la `0009`.
- **CU-39** (disponibilidad y plazo de abastecimiento) toca `inventario`, no ventas.
- **CU-40** (notificaciones) se apoya en la costura de correo que ya dejó Karen.
