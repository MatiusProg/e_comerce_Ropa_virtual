# Los fragmentos `loop` que faltan en los diagramas de secuencia 3.2

> **Escrito el 24/09/2026, a pedido de Mateo.** Es un documento de **análisis**:
> no toca ningún diagrama ni el `.eapx`. Dice **dónde va cada `loop`, qué
> mensajes encierra, qué guarda lleva y de qué línea de código sale**, para
> poder dibujarlos a mano en EA.
>
> Cubre los **seis diagramas del Ciclo 3** ya generados —CU-21, CU-27, CU-28,
> CU-31, CU-33 y CU-34— más el **CU-32**, cuyo guion ya está escrito en
> `scripts/ea-secuencia-3-2.ps1` pero todavía no se generó.
>
> Los `loop` del Ciclo 1 ya están analizados en la sección 4.4 de
> [`secuencia-y-codigo.md`](secuencia-y-codigo.md); este archivo no los repite.

---

## 1. La regla: el `loop` va en el controlador y en la tabla, no en la pantalla

Un `loop` que envuelve mensajes de una línea de vida de pantalla
—`:PantallaVenta`, `:PantallaCheckout`— está mal puesto. **La repetición es del
controlador recorriendo una colección**, y de la tabla recibiendo esa operación
una vez por elemento. La vista recibe la lista ya armada y la pinta una sola
vez: por eso su mensaje es uno, no N.

### 1.1 Un `SELECT` que devuelve N filas NO es un `loop`

Es el error simétrico y conviene decirlo antes de empezar a dibujar cajas.

```
1.5a: SELECT v.* FROM existencia e JOIN variante_producto v ...
1.5a.1: list[VarianteProducto]          ← esto NO lleva loop
```

Es **un** mensaje con **un** conjunto de resultados. No hay repetición que
marcar. Si se le pusiera un `loop`, habría que ponérselo a cada consulta del
proyecto y el operador dejaría de significar nada.

El `loop` aparece cuando:

1. el **controlador recorre** lo que recibió (`for`, `while`, una comprensión), y
   en cada vuelta **vuelve a hablar** con una entidad o con otro gestor; o
2. la **base misma itera**, que en este proyecto es sólo la CTE recursiva de
   CU-08 (ya documentada en la 4.4 de `secuencia-y-codigo.md`).

### 1.2 La excepción, que hay una

**CU-21 tiene un `loop` legítimo sobre una pantalla.** No es un descuido de la
regla: es el único lugar del sistema donde la pantalla **es** el bucle. Ver
§2.1.

---

## 2. Diagrama por diagrama

### 2.1 CU-21 · Utilizar vestidor virtual (RA) — **2 `loop`**

#### `loop` A — el de los fotogramas *(la excepción)*

| | |
|---|---|
| **Encierra** | `1.5: detectarPose(fotograma)` y `1.6: dibujarPrenda(hombros, cadera)` |
| **Cruza** | sólo `:PantallaVestidor` (los dos son auto-mensajes) |
| **Guarda** | `[por cada fotograma de la cámara]` |
| **Sale de** | `mobile/lib/features/vestidor/pantalla_vestidor.dart` — el `ImageStream` de la cámara |

**Por qué éste sí va sobre una pantalla.** No se está pintando una lista que
llegó del servidor: se está procesando el vídeo en vivo, unas 30 veces por
segundo, **dentro del teléfono**. La prueba de que el bucle existe está en la
propia interfaz: la pantalla muestra los **fotogramas por segundo** que está
procesando (punto 7 de `cu-21-alcance-real-para-los-diagramas.md`). Un contador
de FPS sólo tiene sentido si hay un bucle detrás.

Es además el `loop` más defendible del proyecto entero, porque **no hay ni una
llamada al servidor adentro**: el ciclo completo —detectar pose, escalar la
prenda, dibujarla— ocurre en el dispositivo. Vale la pena que en la defensa se
diga con esas palabras.

#### `loop` B — la tabla de tallas

| | |
|---|---|
| **Encierra** | `2.4a: compararConMedidaTalla(medidas)` |
| **Cruza** | sólo `:GestorVestidor` (auto-mensaje) |
| **Guarda** | `[por cada talla de la tabla]` |
| **Sale de** | `backend/app/modules/medidas/service.py:71` (arma un `AjusteDeTalla` por talla) y `:101` (segunda pasada, para el factor de largo) |

Son **dos** recorridos sobre la misma tabla, y el segundo no se puede fusionar
con el primero: el factor de largo se mide **contra la talla recomendada**, que
no se sabe cuál es hasta terminar el primero. Si se quiere ser fiel, son dos
`loop` consecutivos sobre el mismo auto-mensaje; con uno solo y la guarda
`[por cada talla de la tabla]` alcanza para el nivel de detalle del examen.

---

### 2.2 CU-27 · Realizar pedido y pagar en línea — **3 `loop`**

#### `loop` A — elegir sucursal *(el que más se pasa por alto)*

| | |
|---|---|
| **Encierra** | `1.3: SELECT sucursal_id, SUM(...) ... GROUP BY sucursal_id` y `1.3.1` |
| **Cruza** | `:GestorPedidos` → `:Existencia` |
| **Guarda** | `[por cada sucursal activa]` |
| **Sale de** | `backend/app/modules/ventas/service.py:220` |

El `GROUP BY` lo hace la base **una vez**; lo que se repite es lo de después:
Python recorre las sucursales activas y, para cada una, arma la lista de lo que
le falta. El mensaje es uno y el `loop` marca que la evaluación es N.

#### `loop` B — apartar el stock *(el importante)*

| | |
|---|---|
| **Encierra** | de `2.6a: apartar_para_reserva(...)` hasta `2.8a.1: confirmación` |
| **Cruza** | `:GestorPedidos` → `:GestorInventario` → `:Existencia` |
| **Guarda** | `[por cada línea del carrito]` |
| **Sale de** | `ventas/service.py:532` — `for linea in lineas:` |

Es donde vive la mitigación de **R5**: el `SELECT … FOR UPDATE` de `2.7a` se
toma **una vez por línea**, no una vez por pedido. Dibujar el `loop` acá es lo
que hace visible que el bloqueo es por prenda.

#### `loop` C — las líneas del pedido

| | |
|---|---|
| **Encierra** | `2.10a: INSERT INTO detalle_venta (precio_unitario CONGELADO)` |
| **Cruza** | `:GestorPedidos` → `:DetalleVenta` |
| **Guarda** | `[por cada línea del carrito]` |
| **Sale de** | `ventas/service.py:545` — mismo `for` que el `loop` B |

> ⚠ **Ojo con éste: el diagrama y el código no van en el mismo orden.**
>
> En el código hay **un solo `for`** que hace el apartado *y* el `INSERT` del
> detalle. En el diagrama, el apartado (`2.6a`–`2.8a.1`) va **antes** del
> `INSERT INTO venta` (`2.9a`), y el detalle (`2.10a`) va después. Con ese
> orden, una sola caja que los cubra a los dos se tragaría también el
> `INSERT INTO venta`, **que ocurre una vez y no N**.
>
> Dos salidas:
> - **Mínima (la que recomiendo):** dos cajas separadas, la B y la C, con la
>   misma guarda. Es correcto y no obliga a tocar mensajes.
> - **Fiel:** mover `2.9a` para que quede antes del apartado —que es el orden
>   real del código— y entonces una sola caja cubre `2.6a`–`2.10a`. Es más
>   exacto, pero renumera.

#### `loop` D — cancelar

| | |
|---|---|
| **Encierra** | `3.3: liberar(variantes, sucursal)` y `3.4: UPDATE existencia SET reservada = …` |
| **Cruza** | `:GestorPedidos` → `:GestorInventario` → `:Existencia` |
| **Guarda** | `[por cada línea del pedido]` |
| **Sale de** | `ventas/service.py:646` — `for detalle in repository.detalles_de(...)` |

---

### 2.3 CU-28 · Confirmar pago del pedido — **1 `loop`**

| | |
|---|---|
| **Encierra** | de `1.8a: confirmar_salida(venta)` hasta `1.10a.1: confirmación` |
| **Cruza** | `:GestorPagos` → `:GestorInventario` → `:Existencia` |
| **Guarda** | `[por cada línea del pedido]` |
| **Sale de** | `backend/app/modules/pagos/service.py:343` |

Cada vuelta hace **dos** movimientos de inventario, no uno: `liberar_de_reserva`
—que deshace el apartado de CU-27— y `descontar_por_venta`. Por eso la caja
tiene que cubrir también el `1.10a: registrarMovimiento(SALIDA, referencia)`.

**Lo que queda fuera, a propósito:** `1.4`, `1.5a`, `1.6a` y `1.7a`. La
verificación de firma, el asiento de idempotencia, el `UPDATE pago` y el
`UPDATE venta` ocurren **una sola vez por aviso**, sin importar cuántas líneas
tenga el pedido. Que se vea que sólo el tramo de inventario es N es parte de lo
que el diagrama tiene que contar.

---

### 2.4 CU-31 · Registrar venta presencial — **1 `loop`**

| | |
|---|---|
| **Encierra** | de `1.9a: descontar(variantes, sucursal)` hasta `1.11a.1: confirmación` |
| **Cruza** | `:GestorMostrador` → `:GestorInventario` → `:Existencia` |
| **Guarda** | `[por cada prenda del ticket]` |
| **Sale de** | `backend/app/modules/pos/service.py:424` — el `for` de `_descontar` |

**Lo que NO va adentro, y es el detalle que vale la pena defender:**

```
1.8a: descuentos_por_variante(precios)     ← UNA sola consulta para todo el ticket
```

`catalogo/promociones_service.py:163` recibe el diccionario de precios **entero**
y resuelve todos los descuentos de una vez. Dejarlo fuera de la caja no es un
descuido: es lo que muestra que las promociones **no** se consultan prenda por
prenda. Si estuviera adentro, el diagrama estaría documentando un problema de
rendimiento que el código no tiene.

**Lo que falta para ser completo:** el `INSERT INTO detalle_venta` también corre
una vez por línea (`pos/service.py:509`), pero **el diagrama no tiene línea de
vida `:DetalleVenta`**, así que hoy no hay nada que encerrar. Si alguna vez se
agrega esa línea, ese `INSERT` lleva su propio `loop`.

---

### 2.5 CU-33 · Recibir recomendaciones de prendas — **2 `loop`**

#### `loop` A — armar las candidatas

| | |
|---|---|
| **Encierra** | `1.5: armarContexto(senal, catalogo)  {id -> nombre}` |
| **Cruza** | sólo `:GestorRecomendaciones` (auto-mensaje) |
| **Guarda** | `[por cada producto candidato]` |
| **Sale de** | `backend/app/modules/ia/service.py:163` — comprensión que arma una `Candidata` por fila |

#### `loop` B — validar lo que contestó el modelo *(el que cuenta la historia)*

| | |
|---|---|
| **Encierra** | `1.8: validarContraCatalogo(sugerencias)` |
| **Cruza** | sólo `:GestorRecomendaciones` (auto-mensaje) |
| **Guarda** | `[por cada sugerencia del modelo]` |
| **Sale de** | `ia/service.py:282` — `for sugerencia in sugerencias:` |

Este es el que conviene señalar en la defensa: el bucle **descarta una por una**
las prendas que el modelo sugirió y que ya no se pueden comprar —borradas,
desactivadas, sin variante activa o agotadas—. Es la prueba visible de que *el
modelo ordena pero no decide*.

**Lo que queda fuera:** `1.6: generar(prompt)` es **una** llamada al modelo, y
`1.7: productos_con_stock(ids)` es **una** consulta en bloque —la costura C1—.
Ninguno de los dos se repite.

---

### 2.6 CU-34 · Conversar con el asistente virtual — **1 `loop`**

| | |
|---|---|
| **Encierra** | `1.9: armarContexto(catalogo, ofertas, tallas, pedidos, medidas)` |
| **Cruza** | sólo `:GestorAsistente` (auto-mensaje) |
| **Guarda** | `[por cada fila del contexto]` |
| **Sale de** | `backend/app/modules/ia/asistente_service.py:121, 151, 156, 164 y 172` |

Son **cinco** recorridos dentro del mismo auto-mensaje: catálogo, pedidos,
reservas, sucursales y tabla de tallas. Se los puede dejar en una sola caja —el
mensaje es uno— o partir `1.9` en cinco mensajes y poner una caja a cada uno.
Para el nivel del examen, una caja alcanza.

**Lo que queda fuera:** `1.10: responder(...)`, que el propio mensaje ya rotula
`{UNA sola llamada}`. Meterlo en un `loop` diría exactamente lo contrario de lo
que el diagrama quiere probar.

---

### 2.7 CU-32 · Registrar devolución o cambio — **4 `loop`**

> **El guion ya está escrito** en `scripts/ea-secuencia-3-2.ps1`, así que acá
> van los **números de mensaje reales**. Los cuatro se dibujan a mano después de
> generar el diagrama.

#### FLUJO 1 · Devolver — 1 caja

| | |
|---|---|
| **Encierra** | de `1.12a: INSERT INTO detalle_devolucion` hasta `1.14a.1: MovimientoInventario (DEVOLUCION)` |
| **Cruza** | `:GestorDevoluciones` → `:GestorInventario` → `:Existencia` |
| **Guarda** | `[por cada prenda que vuelve]` |
| **Sale de** | el `for` de `registrar` en `pos/devolucion_service.py` |

Queda **fuera** `1.11a: INSERT INTO devolucion`: la cabecera se escribe una vez.
Y queda fuera `1.10a`, el `FOR UPDATE`, que se toma **una sola vez sobre la
venta** —no por línea— porque lo que serializa es la venta entera.

#### FLUJO 2 · Cambiar — 3 cajas, y el orden entre ellas es el punto

| | caja A | caja B | caja C |
|---|---|---|---|
| **Encierra** | `2.10a: INSERT INTO detalle_venta` | `2.12a` → `2.14a` | `2.15a` → `2.17a.1` |
| **Cruza** | `:GestorDevoluciones` → `:Venta` | `:GestorDevoluciones` → `:Devolucion` → `:GestorInventario` → `:Existencia` | `:GestorDevoluciones` → `:GestorInventario` → `:Existencia` |
| **Guarda** | `[por cada prenda que se lleva]` | `[por cada prenda que vuelve]` | `[por cada prenda que se lleva]` |

**Las cajas B y C van una después de la otra, y en ese orden.** No es
cosmético: es el orden del mostrador —el cliente entrega y después recibe— y es
lo único que permite cambiar una prenda fallada por **otra igual** cuando era la
última. Al revés, el descuento no encontraría stock de una prenda que el cliente
tiene en la mano. Los mensajes `2.13a` y `2.15a` ya llevan el rótulo `[1ro ENTRA
lo viejo]` y `[2do SALE lo nuevo]` justamente para que se lea sin explicación.

Quedan **fuera** de las tres, y conviene que se note:

```
2.7:  descuentos_por_variante(precios)   ← UNA sola para todo el cambio
2.9a: INSERT INTO venta                  ← la cabecera, una vez
2.8:  diferencia = total_llevado - ...   ← una cuenta, no un recorrido
```

Si la caja A se dibuja pegada a la C —las dos tienen la misma guarda— hay que
cuidar que **no se trague `2.11a`**, que es la cabecera de la devolución y
ocurre una sola vez. Por eso van separadas.
---

## 3. Resumen

| Diagrama | ¿Lleva `loop`? | Cuántos | Dónde |
|---|---|---|---|
| CU-21 Vestidor virtual | **Sí** | 2 | fotogramas *(sobre la pantalla: la excepción)* · tabla de tallas |
| CU-27 Pedido y pago | **Sí** | 3–4 | sucursales · apartado · detalle · cancelación |
| CU-28 Confirmar pago | **Sí** | 1 | líneas del pedido |
| CU-31 Venta presencial | **Sí** | 1 | prendas del ticket |
| CU-33 Recomendaciones | **Sí** | 2 | candidatas · validación de sugerencias |
| CU-34 Asistente virtual | **Sí** | 1 | armado del contexto |
| CU-32 Devolución o cambio | **Sí** | 4 | lo que vuelve (×2) · lo que sale (×2) |

**Los seis del Ciclo 3 llevan `loop`, y ninguno lo tiene dibujado hoy.**

---

## 4. Cómo se dibuja uno a mano en EA

El generador sólo crea fragmentos `alt`, porque es el único operador cuyo código
interno está verificado contra el archivo de cátedra. Para poner un `loop` a
mano, la sección 5 de [`secuencia-y-codigo.md`](secuencia-y-codigo.md) tiene el
procedimiento; en resumen es cambiar el operador del fragmento y escribir la
guarda del operando.

⚠ **Y la trampa de siempre:** EA **remaqueta el diagrama de secuencia entero
cada vez que lo abre**, pero **conserva la caja del fragmento**. Después de
agregar un `loop`, conviene cerrar y volver a abrir el diagrama y **verificar
que la caja siga envolviendo los mismos mensajes**: si se corrió, hay que
reajustarla a mano antes de exportar el JPG.
