# CU-10 · Gestionar productos y variantes

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
>
> **Un archivo por caso de uso, y no un capítulo compartido.** El acuerdo del ciclo dice que cada
> uno redacta la documentación de sus propios casos de uso, pero su §5 solo lista cinco archivos
> compartidos y ninguno es de documentación: si los dos escribiéramos en un mismo
> `cap-1-captura-requisitos.md` del Ciclo 2, tendríamos un sexto archivo compartido que nadie
> previó, y encima el más largo. Con un archivo por caso de uso el conflicto es imposible, y la
> consolidación del `.docx` (I5) los une en el orden del índice.

| Campo | Contenido |
|---|---|
| **Código** | CU-10 |
| **Nombre** | Gestionar productos y variantes |
| **Descripción** | Permite al Administrador registrar las prendas del catálogo y generar sus variantes —la combinación concreta de talla y color— con su SKU y su precio. |
| **Propósito** | Crear la unidad sobre la que se apoya todo el resto del sistema: la variante es lo que tiene existencia, reserva y venta. Sin ella no hay inventario, ni reserva, ni vitrina. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P3 · Catálogo (productos) |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF05 |
| **Precondiciones** | El Administrador tiene sesión iniciada. Existen al menos una categoría, una talla y un color (CU-08). |
| **Postcondiciones** | El producto y sus variantes quedan disponibles para el ingreso de mercadería (CU-13), la vitrina (CU-17, CU-18) y la reserva (CU-22). |

**Flujo principal**

1. El Administrador ingresa a *Productos* dentro del catálogo.
2. El sistema muestra los productos paginados, con su código, nombre, categoría, precio base, estado y cuántas variantes tiene cada uno, y ofrece filtrar por categoría, temporada, colección, proveedor y estado, o buscar por código o nombre.
3. El Administrador elige registrar un producto.
4. El sistema presenta el formulario: código, nombre, descripción, categoría, proveedor, temporada, colección, precio base y estado.
5. El Administrador completa los datos y confirma.
6. El sistema valida que el código no se repita y que la colección elegida pertenezca a la temporada indicada, y registra el producto.
7. El Administrador elige las tallas y los colores que ese producto va a tener, y el sistema genera una variante por cada combinación, con su SKU y con el precio base del producto.

**Flujos alternativos**

- **3a. Editar.** El Administrador modifica un producto existente y confirma. Cambiar el precio base **no** altera el precio de las variantes que ya existen.
- **3b. Desactivar.** El producto deja de ofrecerse y sus variantes se desactivan con él, pero se conserva en las existencias, reservas y ventas que ya lo referencian.
- **7a. Variante suelta.** El Administrador agrega una sola combinación talla × color, con un precio propio si corresponde, sin generar el resto.
- **7b. Editar variante.** El Administrador cambia el precio de una variante. La talla y el color no se editan: cambiarlos la convertiría en otra variante distinta, con existencias y reservas ya apuntando a ella.
- **7c. Desactivar variante.** La variante deja de ofrecerse y se conserva en el historial.

**Excepciones**

- **E1. Código o SKU duplicado.** El sistema lo impide y señala el campo. La comparación del código no distingue mayúsculas.
- **E2. Colección ajena a la temporada.** El sistema impide guardar un producto cuya colección pertenezca a una temporada distinta de la indicada. Si solo se indica la colección, la temporada se completa a partir de ella.
- **E3. Eliminación con dependencias.** El sistema impide eliminar un producto o una variante que ya tenga existencias o reservas, y ofrece desactivarlo.

---

## Lo que no se lee en la ficha

**El SKU es legible y determinista: `CODIGO-TALLA-COLOR`.** Determinista importa porque el paso 7 se
puede repetir —al agregar una talla nueva— y tiene que producir exactamente los mismos SKU para las
combinaciones que ya existían. Si no entra en los 40 caracteres del campo, **no se trunca**: se avisa
y se pide acortar el código del producto. Truncar haría que «Verde militar» y «Verde menta» generaran
el mismo SKU para dos variantes distintas, que es justo lo que un SKU no puede hacer.

**Volver a generar variantes omite las que ya existen en vez de fallar.** La restricción
`uq_variante_producto_talla_color` garantiza que no se dupliquen; el servicio las cuenta aparte y la
interfaz dice cuántas creó y cuántas omitió.

**El precio de la variante es una copia, no una referencia.** Nace igual al precio base del producto
y después se mueve solo. Es la decisión 1 de la §6.4 del acuerdo: si el precio base repropagara,
cambiaría el precio de variantes ya vendidas.

**La coherencia entre temporada y colección la sostiene el servicio, no la base.** Es el precio de la
única redundancia aceptada del esquema —decisión 2 de la §6.4— y por eso tiene prueba propia.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/catalogo/productos` | 2 · listado con filtros y paginación |
| `POST` | `/catalogo/productos` | 4-6 · alta |
| `GET` | `/catalogo/productos/{id}` | detalle con variantes |
| `PATCH` | `/catalogo/productos/{id}` | 3a · editar |
| `PATCH` | `/catalogo/productos/{id}/estado` | 3b · desactivar |
| `DELETE` | `/catalogo/productos/{id}` | E3 si tiene dependencias |
| `POST` | `/catalogo/productos/{id}/variantes/generar` | 7 · generación talla × color |
| `POST` | `/catalogo/productos/{id}/variantes` | 7a · variante suelta |
| `PATCH` | `/catalogo/variantes/{id}` | 7b, 7c · precio y estado |
| `DELETE` | `/catalogo/variantes/{id}` | E3 a nivel de variante |

Todos exigen rol **Administrador**, declarado una sola vez en el router. La vitrina del cliente
—CU-17, CU-18 y CU-19— no se sirve desde aquí: vive en el paquete P5 y no exige rol.
