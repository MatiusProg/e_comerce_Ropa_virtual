# Esquema de Ventas y Pagos — la migración `0006_ciclo3_ventas`

Propuesta de las **diez tablas** de los paquetes **P7 · Ventas y Punto de Venta** y **P8 · Pagos**.
Es el contrato del que cuelgan CU-26 a CU-32, y también CU-29, CU-36 y CU-37, así que conviene
cerrarlo antes de escribir código encima.

> **Por qué este documento existe.** Para el Ciclo 2 el acuerdo de columnas estaba en la §6.4 de
> [`ciclo-2/00-organizacion-por-caso-de-uso.md`](../ciclo-2/00-organizacion-por-caso-de-uso.md), y
> eso es lo que permitió escribir dos migraciones en paralelo sin pisarse. Para el Ciclo 3 ese
> acuerdo **no existía**: el análisis nombra las clases pero no sus atributos. Esto lo llena.

---

## 1. Lo que ya está acordado y no se discute

**El identificador y la cadena.** `0006_ciclo3_ventas` es de Mateo, por la §4 de
[`ciclo-2/04-respuesta-de-karen.md`](../ciclo-2/04-respuesta-de-karen.md). Y por la nota que Karen
dejó en [`cu-41-recuperar-contrasena.md`](cu-41-recuperar-contrasena.md), **la cabeza ya no es la
`0005` sino la `0008`**:

```python
revision      = "0006_ciclo3_ventas"
down_revision = "0008_ciclo3_recuperacion"
```

La cadena queda `0005 → 0008 → 0006 → 0007`. Se lee raro y es correcta: el número del archivo es
un nombre, el orden lo da `down_revision`.

**Las decisiones de arquitectura que esto realiza**, de `docs/04-analisis-arquitectura.md`:

| | Qué dice | Cómo se cumple acá |
|---|---|---|
| **D1** | todo referencia `variante_producto`, nunca `producto` | `item_carrito`, `detalle_venta` y `detalle_devolucion` apuntan a `variante_id` |
| **D2** | una sola `Venta` con dos canales | `venta.canal` = `DIGITAL` \| `PRESENCIAL`; no hay tabla «pedido» aparte |
| **D3** | la existencia se descompone en disponible y reservado | la venta descuenta de reservado si vino de una reserva, de disponible si no |
| **D5** | el estado del pago **solo** lo determina la pasarela | `transaccion_pasarela.evento_id` es **único**: es lo que hace idempotente el webhook |

**El estilo**, igual que en la `0003`: escrita a mano y no con `--autogenerate`; `Numeric(10, 2)`
para dinero, como `variante_producto.precio`; `String(n)` con `CheckConstraint` para los estados,
no `Enum` de PostgreSQL; y en los CHECK **va solo el sufijo** (`name="estado"`, no
`name="ck_venta_estado"`), porque la convención de `app/db/base.py` antepone el resto.

---

## 2. Las diez tablas

### P7 · Ventas

#### `carrito` — CU-26
Un carrito **abierto** por cliente. Se cierra al convertirse en venta.

| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `cliente_id` | FK → `cliente` | |
| `estado` | `String(10)` | `ABIERTO` \| `CONVERTIDO` \| `ABANDONADO` |
| `creado_en` / `actualizado_en` | mixin `Auditoria` | |

**Índice único parcial:** un solo carrito `ABIERTO` por cliente. Es lo que evita que dos pestañas
del navegador creen dos carritos y el total salga partido.

#### `item_carrito` — CU-26
| Columna | Tipo | Notas |
|---|---|---|
| `id` | PK | |
| `carrito_id` | FK → `carrito`, `ON DELETE CASCADE` | |
| `variante_id` | FK → `variante_producto` | **D1** |
| `cantidad` | `Integer` | CHECK `> 0` |
| `precio_unitario` | `Numeric(10,2)` | **se copia al agregar**, no se lee en vivo |

**Único** `(carrito_id, variante_id)`: agregar dos veces la misma variante suma cantidad, no crea
una fila más.

> **Por qué el precio se copia.** Es la misma razón por la que `variante_producto.precio` no
> repropaga desde `producto.precio_base`: si el precio se leyera en vivo, el total del carrito
> cambiaría solo mientras el cliente decide. Lo que se copia es el precio **con la promoción ya
> aplicada** (CU-12, migración `0007`).

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
   medias, así que las diez tablas nacen juntas.
3. **`venta.reserva_id` es único y nullable.** Es el puente de D2: el Encargado atiende una reserva
   (CU-24) y esa misma reserva se cobra como venta presencial, sin transformar datos.
4. **El precio se congela en tres lugares** —`item_carrito`, `detalle_venta` y `pago.monto`— y
   ninguno se recalcula después. Es la misma regla que ya rige en `variante_producto.precio`.

## 4. Lo que NO entra acá

- **Promociones (CU-12)** van en la `0007_ciclo3_promociones`, que también es nuestra. `item_carrito`
  y `detalle_venta` ya tienen la columna de descuento para recibirlas.
- **CU-39** (disponibilidad y plazo de abastecimiento) toca `inventario`, no ventas.
- **CU-40** (notificaciones) se apoya en la costura de correo que ya dejó Karen.
