# CU-18 · Consultar ficha de producto

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
> Un archivo por caso de uso, por el motivo explicado en
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-18 |
| **Nombre** | Consultar ficha de producto |
| **Descripción** | Permite al Cliente ver el detalle de una prenda con su galería de imágenes, su descripción y su precio, y seleccionar la talla y el color deseados. |
| **Propósito** | Fijar la **variante** —la combinación talla × color, que es la unidad de negocio— para que el Cliente pueda reservarla, comprarla o probarla en el vestidor virtual. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P5 · Catálogo Público y Disponibilidad |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF07 · RF05 (tallas y colores) · RNF05 |
| **Precondiciones** | Ninguna. **No exige sesión iniciada.** El producto se alcanza desde el catálogo (CU-17) o por su enlace directo. |
| **Postcondiciones** | El Cliente tiene identificada una variante concreta, con su precio y su SKU, en condiciones de reservarla (CU-22), agregarla al carrito (CU-26) o probarla en el vestidor virtual (CU-21). El sistema no cambia de estado. |

**Flujo principal**

1. El Cliente elige una prenda desde el catálogo.
2. El sistema muestra la ficha: galería de imágenes, categoría, nombre, descripción, rango de precios, y las tallas y los colores en los que se ofrece.
3. El Cliente elige una talla.
4. El sistema restringe los colores a los que existen en esa talla.
5. El Cliente elige un color.
6. El sistema muestra la variante resultante con su precio propio y su SKU.

**Flujos alternativos**

- **3a. Elegir primero el color.** Simétrico: el sistema restringe las tallas a las que existen en ese color.
- **3b. Soltar la selección.** Volver a tocar la talla o el color elegido lo deselecciona y devuelve todas las opciones.
- **4a. La combinación anterior deja de existir.** Si el color ya elegido no se ofrece en la talla nueva, el sistema suelta el color en lugar de mostrar una combinación inexistente.
- **6a. La variante tiene foto propia.** La galería salta a la imagen de esa combinación de talla y color.
- **6b. La variante se puede probar.** Si tiene su PNG con fondo transparente, el sistema habilita el acceso al vestidor virtual (**CU-21**, Ciclo 3).

**Excepciones**

- **E1. La prenda ya no está disponible.** Cubre tres situaciones que se responden igual: el producto no existe, está desactivado, o no le queda ninguna variante activa. El sistema informa que la prenda dejó de ofrecerse.
- **E2. Identificador inválido.** La app devuelve al catálogo en vez de fallar: la ruta la puede escribir cualquiera.
- **E3. El servicio no responde.** La interfaz muestra el fallo y ofrece volver al catálogo.

---

## Lo que no se lee en la ficha

**La E1 responde 404 y no 403, a propósito.** Distinguir «no existe» de «existe pero está oculto»
convertiría la ficha en un detector de productos ocultos: bastaría recorrer identificadores para
saber cuáles hay desactivados y cuántos son. Las tres situaciones dan la misma respuesta y el mismo
mensaje.

**La selección se resuelve en dos pasos que se restringen entre sí, y no en uno.** No toda
combinación talla × color existe: puede haber una blusa en S negra y en M roja, y ninguna en S roja.
Si las dos listas fueran independientes, la pantalla dejaría armar una combinación que no se puede
comprar y el error aparecería recién al reservar —cuando el cliente ya decidió—. Por eso elegir la
talla acota los colores, y al revés.

**Lo que no se ofrece se apaga, no desaparece.** Si el color no disponible se fuera de la fila, los
que quedan saltarían de lugar justo cuando el cliente está por tocar uno. Se deshabilita en el sitio
y el rótulo dice por qué.

**La ficha entrega el precio de la variante, no el del producto.** Es la decisión **D1**: la
variante es la unidad de negocio y es la que tiene precio, existencia, reserva y venta.
`producto.precio_base` es solo el sugerido con el que nacen las variantes. Mientras no haya variante
elegida se muestra el rango; en cuanto la hay, su precio propio.

**Cada variante viaja con la URL de su PNG transparente. Es la costura C5.** El activo del vestidor
virtual es **por variante** —el índice parcial `uq_imagen_transparente_variante` garantiza uno solo
por cada una—, así que entregarlo en la ficha significa que la pantalla de realidad aumentada recibe
todo lo que necesita al navegar: no vuelve a consultar la API ni conoce la tabla de imágenes. Sin
esto, CU-21 tendría que aprenderse el catálogo para dibujar una prenda.

**El PNG transparente no entra en la galería.** Viaja dentro de su variante. Mezclado entre las
fotos del producto se vería como un recorte suelto sobre el fondo de la pantalla.

**El bloque de disponibilidad por sucursal se anuncia en vez de dibujarse vacío.** Es **CU-19** y
llega con la **costura C1**, cuando el servicio de inventario exponga
`disponibilidad_por_sucursal(db, variante_id)`. Un bloque vacío se lee como un defecto; un aviso, no.

**El botón del vestidor virtual está en la ficha de las dos plataformas, pero solo funciona en el
móvil.** La cámara y la detección de pose corren en el dispositivo: es el RF13 —«la aplicación móvil
deberá permitir utilizar el vestidor virtual»—. En la web el botón anuncia la funcionalidad y remite
a la app; en el móvil queda listo del lado del dato y avisa que la pantalla llega en el Ciclo 3, en
vez de navegar a una ruta que todavía no existe.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/tienda/productos/{producto_id}` | 2-6 · la ficha completa |

No exige token, igual que el resto de P5. La respuesta trae la galería con las URL ya prefijadas por
el servidor, para que la web y la app móvil no tengan que saber cómo se monta el volumen (§6.8).

## Pantallas

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web | `/tienda/producto/:id` | `frontend-web/src/app/features/tienda/ficha/` |
| Móvil | `/catalogo/:id` | `mobile/lib/features/catalogo/pantalla_ficha.dart` |

En el móvil la ruta va **anidada** bajo la del catálogo: así el botón de volver del teléfono lleva de
la ficha a la vitrina y no a la pantalla de inicio.
