# CU-17 · Consultar catálogo

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
> Un archivo por caso de uso, por el motivo explicado en
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-17 |
| **Nombre** | Consultar catálogo |
| **Descripción** | Permite al Cliente navegar el catálogo de prendas desde la web o la app móvil, buscar por texto y filtrar por categoría, talla, color, temporada, colección y precio. |
| **Propósito** | Ser la puerta de entrada del cliente al sistema: es la pantalla desde la que se llega a la ficha, a la reserva y al vestidor virtual. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P5 · Catálogo Público y Disponibilidad |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF07 · RNF02 (rendimiento del catálogo) · RNF05 (adaptable a dispositivos) |
| **Precondiciones** | Ninguna. **No exige sesión iniciada**: el catálogo es público. |
| **Postcondiciones** | El Cliente tiene a la vista un subconjunto del catálogo y puede abrir la ficha de cualquiera de sus prendas (CU-18). El sistema no cambia de estado. |

**Flujo principal**

1. El Cliente abre el catálogo desde la web o desde la app móvil.
2. El sistema muestra las prendas ofrecibles, paginadas, con su foto, su categoría, su rango de precios y los colores en que se ofrece, junto con los criterios de búsqueda y filtrado disponibles.
3. El Cliente escribe un texto de búsqueda, elige uno o más filtros, o cambia el orden.
4. El sistema vuelve a consultar y muestra el resultado desde la primera página.
5. El Cliente elige una prenda y el sistema abre su ficha (**CU-18**).

**Flujos alternativos**

- **3a. Filtrar por categoría.** El filtro alcanza a la categoría elegida **y a todas las que cuelgan de ella**: elegir *Mujer* devuelve también lo que está cargado en *Mujer > Blusas*.
- **3b. Ordenar.** Novedades, menor precio, mayor precio o nombre.
- **3c. Paginar.** El Cliente avanza o retrocede de página; el sistema conserva los filtros.
- **3d. Limpiar filtros.** Vuelve al catálogo completo en una sola consulta.
- **4a. Sin resultados.** El sistema distingue el catálogo vacío de la combinación de filtros sin resultados, y en el segundo caso ofrece limpiar los filtros.

**Excepciones**

- **E1. Orden no reconocido.** El sistema rechaza un criterio de ordenamiento que no sea uno de los cuatro previstos, nombrando los válidos.
- **E2. Página demasiado grande.** El sistema rechaza una petición que exceda el tamaño máximo de página.
- **E3. El servicio no responde.** La interfaz muestra el fallo y ofrece reintentar, sin perder los filtros puestos.

---

## Lo que no se lee en la ficha

**La vitrina es pública, y esa es la diferencia de fondo con CU-10.** El flujo principal no tiene
precondición de sesión, y en la app móvil la pantalla de catálogo se abre antes de que exista un
token. Exigir rol obligaría a registrarse para mirar una prenda, que es lo contrario de lo que pide
el RF07. Lo que se ofrece está acotado en el servidor y los esquemas públicos **no exponen
proveedor, precio base ni estado**: reutilizar el esquema del Administrador le filtraría al cliente
quién abastece cada prenda y a qué precio entró.

**Solo se ofrece lo comprable.** Producto inactivo, o sin ninguna variante activa, no aparece. Un
producto sin variantes activas no tiene precio, ni SKU, ni existencia: mostrarlo es prometer algo
que no se puede cumplir. Es una regla de negocio y por eso vive en el servicio, no en el
repositorio.

**Filtrar por categoría recorre el árbol.** `categoria` es autorreferente y los productos se cargan
en las hojas. Sin recorrer los descendientes, filtrar por una categoría raíz devolvería cero y
parecería que no hay nada de esa línea. Se resuelve con un CTE recursivo, no con una consulta por
nivel.

**Los filtros de talla, color y precio usan `EXISTS` y no `JOIN`.** Con `JOIN`, un producto con seis
variantes rojas ocuparía seis filas de la página y el `LIMIT` cortaría por la mitad de un producto.
Con `EXISTS` la fila del producto sigue siendo una sola y el total coincide con lo listado.

**El conteo y el listado filtran con la misma función, a propósito.** Si se separaran, el paginador
anunciaría páginas que no existen, y el defecto solo aparece cuando alguien pagina hasta el final.
Por el mismo motivo todo ordenamiento desempata por `id`: sin desempate, dos prendas del mismo
precio pueden salir en distinto orden entre dos páginas, y una aparecer dos veces o ninguna.

**Las opciones de los filtros son las que el catálogo realmente ofrece.** Salen de un endpoint
propio y no de los maestros de CU-08 —que además exigen rol Administrador—. Una talla que ningún
producto usa es una opción que al elegirla vacía la vitrina, y el cliente no tiene forma de saber
por qué.

**El PNG del vestidor virtual no se usa como foto de catálogo.** Es un recorte con fondo
transparente: en la vitrina se vería suelto. La tarjeta lleva en cambio una marca de que la prenda
*se puede probar*, que viaja en el listado para no tener que abrir producto por producto.

**Falta el filtro por sucursal**, que el caso de uso también enuncia. Depende de `existencia`, que
es tabla de Mateo, y entra por la **costura C1** junto con CU-19. Se dejó fuera en vez de declararlo
y no aplicarlo: un filtro que no filtra es peor que uno que todavía no está.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/tienda/productos` | 2-4 · la vitrina con búsqueda, filtros, orden y paginación |
| `GET` | `/tienda/filtros` | 2 · las opciones del panel de filtros |

Ninguno exige token. `/tienda/filtros` se declara **antes** que `/tienda/productos/{id}` en el
router: FastAPI resuelve las rutas en orden, y al revés la palabra «filtros» entraría por el detalle
y fallaría al leerse como un entero.

## Pantallas

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web | `/tienda` | `frontend-web/src/app/features/tienda/catalogo/` |
| Móvil | `/catalogo` | `mobile/lib/features/catalogo/pantalla_catalogo.dart` |

Las dos consumen los mismos endpoints. Lo que cambia es la forma: en el móvil son dos columnas de
tarjetas y los filtros van en una hoja inferior, porque en 400 px de ancho cinco selectores en fila
no entran. La paginación móvil es por botones y no por desplazamiento infinito: el infinito oculta
cuántas prendas hay y sigue pidiendo páginas mientras el dedo se mueve, sobre datos móviles.
