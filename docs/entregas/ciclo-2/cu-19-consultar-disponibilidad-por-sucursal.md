# CU-19 · Consultar disponibilidad por sucursal

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-19 |
| **Nombre** | Consultar disponibilidad por sucursal |
| **Descripción** | Permite al Cliente conocer en qué sucursales está disponible la variante seleccionada y en qué cantidad. |
| **Propósito** | Cerrar la decisión de compra: el cliente ya eligió la prenda, la talla y el color, y lo único que le falta saber es a qué tienda ir. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P5 · Catálogo Público y Disponibilidad |
| **Prioridad** | Alta |
| **Requisitos que realiza** | **RF08** · RF21 (control de existencias por sucursal, visto desde el cliente) |
| **Precondiciones** | Ninguna. **No exige sesión iniciada.** El Cliente llega desde la ficha (CU-18) con una variante ya elegida. |
| **Postcondiciones** | El Cliente sabe en qué sucursales hay unidades y cuántas. El sistema no cambia de estado. |

**Flujo principal**

1. El Cliente elige talla y color en la ficha de producto, con lo que queda fijada una variante.
2. El sistema consulta el inventario y muestra las sucursales donde hay unidades disponibles, con su ciudad y su cantidad, más el total de la red.
3. El Cliente identifica la sucursal a la que quiere ir y puede reservar la prenda allí (**CU-22**).

**Flujos alternativos**

- **1a. Cambiar de variante.** Al cambiar la talla o el color, el sistema vuelve a consultar: la existencia es por variante y el resultado anterior ya no aplica.
- **2a. Sin unidades en ninguna sucursal.** El sistema informa que no hay stock por ahora, sin tratarlo como error: la prenda existe y se sigue ofreciendo.
- **2b. Sucursales sin unidades.** No se listan. Para el inventario un saldo en cero es un dato legítimo —es lo que hace falta para reponer—; para la vitrina es ruido.

**Excepciones**

- **E1. La variante ya no está disponible.** No existe, está desactivada, o su producto lo está. Las tres se responden igual, por el mismo motivo que en CU-18.
- **E2. El servicio no responde.** La ficha muestra el aviso y conserva la prenda y su precio: la disponibilidad es un dato de apoyo y perderla no puede romper la pantalla.

---

## Lo que no se lee en la ficha

**Este es el caso de uso que cruza la costura C1, y es el único de P5 que lee una tabla ajena.**
`existencia` es de Mateo. P5 **no la consulta**: importa
`inventario.service.disponibilidad_por_sucursal(db, variante_id)`, que es la función acordada en la
§6 del documento de organización. No es un `SELECT` sobre una tabla de otro paquete ni una llamada
HTTP interna, que eran las dos formas descartadas en el acuerdo.

La prueba `test_la_costura_devuelve_lo_mismo_que_el_inventario` existe justamente para eso: compara
lo que ve el cliente contra el endpoint de existencias del propio paquete de Mateo, que lee la misma
tabla por otro camino. Si las dos mitades se desincronizaran, el síntoma sería un cliente viajando a
una tienda donde no hay nada, y no un error en pantalla.

**Cuelga de la variante y no del producto.** La existencia se modela por `(variante, sucursal)`:
preguntar «dónde hay esta blusa» no tiene respuesta útil si no se dice en qué talla y en qué color.
Es la decisión **D1** vista desde el cliente.

**Se consulta al completar la selección, no al abrir la ficha.** Una prenda con cuatro tallas y tres
colores tiene doce variantes; pedir la disponibilidad de todas al entrar serían doce consultas de
las que el cliente mira una. La contrapartida es una espera corta al elegir, que es cuando el dato
recién importa.

**En la web se descarta la respuesta que llega tarde.** Si el cliente cambia de talla mientras la
consulta anterior está en vuelo, la respuesta vieja puede llegar después: sin comprobar que el
`variante_id` de la respuesta sea el de la variante elegida, la pantalla mostraría el stock de una
talla junto al SKU de otra. En el móvil el problema no existe, porque cada variante tiene su propio
proveedor `family` y Riverpod resuelve el emparejamiento.

**No se publica lo reservado.** `existencia` lleva `cantidad_disponible` y `cantidad_reservada`; el
esquema público solo transporta la primera. Al cliente le sirve saber cuánto puede llevarse, no
cuánto tienen apartado otros, y publicar lo segundo dejaría deducir el movimiento comercial de cada
tienda a cualquiera que mire la API.

**La comprobación de que la variante sea ofrecible va primero, y es de P3.** Sin ella, la
disponibilidad sería una puerta trasera: una variante retirada del catálogo seguiría informando
dónde hay stock de ella, contando por un endpoint lo que CU-17 y CU-18 ocultan.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/tienda/variantes/{variante_id}/disponibilidad` | 2 · sucursales con stock |

Público, como el resto de P5.

## Pantallas

| Plataforma | Dónde | Archivo |
|---|---|---|
| Web | Bloque «Dónde encontrarla» de la ficha | `frontend-web/src/app/features/tienda/ficha/` |
| Móvil | Mismo bloque, al pie de la ficha | `mobile/lib/features/catalogo/pantalla_ficha.dart` |

## Lo que este caso de uso deja preparado

El **filtro por sucursal de CU-17** quedó fuera de la vitrina porque dependía de esta misma costura.
Ahora que existe, es un filtro más sobre `existencia`; se evalúa junto con CU-22, que es quien
convierte esta consulta en una reserva.
