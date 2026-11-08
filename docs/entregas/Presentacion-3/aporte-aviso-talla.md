# Aporte propio · «Avísame cuando llegue mi talla»

Este documento sirve para redactar el Word y para los diagramas de EA.

## Por qué es aporte propio

El enunciado pide la tienda en línea, el inventario y las notificaciones, pero no pide esto. Lo que agrega:

- **Para el cliente:** una prenda agotada en su talla deja de ser un callejón sin salida. Pide el aviso y le llega por push, correo y la campanita apenas vuelve.
- **Para la empresa:** la **demanda insatisfecha queda medida**, es decir, cuántos clientes esperan cada talla y color. Eso orienta las reposiciones, los traspasos y las compras.

## Descripción tipo CU

**Nombre:** Pedir aviso de talla disponible (con el inciso «Atender la demanda en espera»).

**Actores:**

| Actor | Rol |
|---|---|
| Cliente | Principal |
| Encargado / Administrador | Consultan la demanda en espera |
| Sistema | Dispara el aviso cuando el inventario repone |

**Precondiciones:**
- El cliente tiene sesión.
- La variante (talla y color) es ofrecible: variante activa de un producto activo.
- La variante tiene 0 unidades disponibles en las sucursales activas.

**Flujo principal (cliente):**
1. El cliente abre la ficha de la prenda y elige la talla y el color.
2. El sistema muestra «Sin unidades disponibles por ahora en ninguna sucursal» y el botón **«Avísenme cuando llegue»**.
3. El cliente pulsa el botón.
4. El sistema registra el aviso PENDIENTE y responde «Le avisaremos…».
5. Cuando entra mercadería a esa variante y el total de la red pasa de 0 a más de 0, el sistema crea la notificación `STOCK_DISPONIBLE` y marca el aviso como AVISADO.
   - El aviso nace en la **misma transacción** que el movimiento de inventario.
   - La mercadería puede entrar por un ingreso, un traspaso recibido, una devolución o cambio, un ajuste o una reserva liberada.
6. El despachador de las tareas automáticas envía la notificación por correo y push. En la campanita se ve al instante.
7. El cliente entra desde el aviso a la ficha y compra o reserva.

**Flujos alternos:**

| Código | Situación | Respuesta del sistema |
|---|---|---|
| 3a | El cliente ya tenía un aviso pendiente de esa variante | Devuelve el mismo; no se duplica (idempotente) |
| 3b | Mientras miraba, llegaron unidades | Responde 409 «Esa talla ya tiene unidades…» y vuelve a consultar la disponibilidad |
| 3c | La variante dejó de ofrecerse | Responde 404 |
| 3d | Quien intenta pedir el aviso no es un cliente (personal) | Responde 403 |
| 5a | La reposición entra a una sucursal **inactiva** | No avisa, porque no se ofrece en la tienda |
| 5b | Ya había unidades en otra sucursal | No avisa, porque no es noticia |
| 5c | El movimiento se deshace (rollback) | El aviso tampoco queda |
| C1 | El cliente cancela desde «Mis avisos» | El aviso pendiente se borra |

**Inciso del personal, «Tallas esperadas»:**
1. El encargado o el administrador abren *Tallas esperadas*.
2. El sistema lista las variantes con avisos pendientes: prenda, talla, color, SKU, clientes esperando y desde cuándo, lo más pedido primero.
3. Cuando entra mercadería, la fila desaparece sola.

**Reglas de negocio:**

| Regla | Contenido |
|---|---|
| RN-AT1 | Un cliente tiene como máximo un aviso pendiente por variante (índice único parcial). |
| RN-AT2 | Se avisa solo al cruzar de 0 a más de 0 en el total de las sucursales activas, y una sola vez por aviso (`notificado_en`). |
| RN-AT3 | El aviso es de la variante, no del producto: avisar de otra talla sería ruido. |
| RN-AT4 | Los avisos están aislados por empresa (RLS con FORCE). La demanda es de toda la empresa, porque el cliente espera en la tienda y no en una sucursal. |

## Tablas y clases (para EA)

**Tabla nueva `aviso_talla`** (migración `0042_aviso_talla`, RLS con FORCE):

| Columna | Tipo | Nota |
|---|---|---|
| id | BIGINT PK | |
| empresa_id | BIGINT FK empresa | DEFAULT `app_empresa_actual()` |
| cliente_id | BIGINT FK cliente | ON DELETE CASCADE |
| variante_id | BIGINT FK variante_producto | ON DELETE CASCADE |
| creado_en | TIMESTAMPTZ | |
| notificado_en | TIMESTAMPTZ NULL | nulo = pendiente |
| notificacion_id | BIGINT FK notificacion NULL | ON DELETE SET NULL |

Índices:
- `uq_aviso_talla_pendiente (cliente_id, variante_id) WHERE notificado_en IS NULL`;
- `ix_aviso_talla_pendientes (variante_id) WHERE notificado_en IS NULL`.

**Cambio en `notificacion`:** el CHECK `tipo_valido` suma `STOCK_DISPONIBLE`.

**Clases (backend, módulo `app/modules/avisos_talla/`):**

| Clase | Estereotipo | Responsabilidad |
|---|---|---|
| `AvisoTalla` | «entity» | La fila de arriba |
| `servicio avisos_talla` | «control» | `suscribir`, `mis_avisos`, `variantes_esperadas`, `cancelar`, `demanda`, `avisar_si_volvio` (el gancho) |
| `cliente_router` (`/tienda/avisos-talla`) | «boundary» | GET (mis avisos), GET `/variantes`, POST, DELETE `/{id}` |
| `personal_router` (`/inventario/avisos-talla`) | «boundary» | GET (demanda); lo cubre el permiso `inventario.gestionar` |

Clases que ya existían y participan:
- `inventario.service._aplicar_movimiento`, el único lugar que cambia un saldo, que es el que llama al gancho;
- `notificaciones.service.notificar`;
- `Existencia`, `VarianteProducto` y `Notificacion`.

**Pantallas:**
- Web:
  - `Ficha`: el botón «Avísenme cuando llegue»;
  - `MisAvisos` (`/mi-cuenta/avisos`);
  - `TallasEsperadas` (`/admin/tallas-esperadas` y `/sucursal/tallas-esperadas`).
- Móvil: `PantallaFicha`, con `_BotonAvisame`, `ControlAvisosTalla` y `RepositorioAvisosTalla`.

**Secuencia del gancho, para el 3.2:**

```
Encargado → PantallaIngreso → inventario.registrar_ingreso
  → _aplicar_movimiento (suma disponible, flush)
     → avisos_talla.avisar_si_volvio(existencia, cantidad)
        → ¿hay pendientes de la variante?   [no → fin]
        → total red antes ≤ 0 < total red ahora   [no → fin]
        → loop por aviso pendiente (FOR UPDATE)
             → notificaciones.notificar(STOCK_DISPONIBLE)
             → aviso.notificado_en = ahora
  → commit (movimiento + avisos juntos)
Tarea automática → despachar_pendientes / push_service.despachar → correo y push
```
