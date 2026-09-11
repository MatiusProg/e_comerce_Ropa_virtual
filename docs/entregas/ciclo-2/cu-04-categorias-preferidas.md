# CU-04 · Gestionar perfil del cliente — categorías preferidas

> **Addendum del Ciclo 2 a un caso de uso del Ciclo 1.** La ficha completa del CU-04 está en
> [`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md); acá va **solo el
> bloque que quedó diferido**, para que se lea qué entró en cada ciclo y por qué.
>
> Cierra la §6.11.3 de [`docs/06-decisiones-tecnicas.md`](../../06-decisiones-tecnicas.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-04 (flujo alternativo 3d) |
| **Nombre** | Gestionar categorías preferidas |
| **Descripción** | Permite al Cliente elegir las categorías de prenda que le interesan, para que el sistema le recomiende en función de ellas. |
| **Propósito** | Alimentar el recomendador del CU-33 con una preferencia declarada por el propio cliente, además de la que se deduce de su historial. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P1 · Seguridad |
| **Prioridad** | Media |
| **Requisitos que realiza** | RF01 (registro y datos del cliente) · alimenta **RF25** (funcionalidad de IA) |
| **Precondiciones** | El Cliente tiene sesión iniciada. Existen categorías activas con prendas publicadas (CU-08 y CU-10). |
| **Postcondiciones** | Las preferidas del Cliente quedan siendo exactamente las enviadas. |

**Flujo principal (3d)**

1. El Cliente abre su perfil y ve el bloque de categorías, con las que ya tenía marcadas.
2. El Cliente marca y desmarca categorías, hasta el tope.
3. El Cliente guarda.
4. El sistema valida las categorías, reemplaza la selección anterior y devuelve el perfil actualizado.

**Flujos alternativos**

- **2a. Tope alcanzado.** Las no elegidas se deshabilitan y el sistema explica que hay que sacar una para agregar otra.
- **2b. Descartar.** La selección vuelve a lo último guardado sin tocar el servidor.
- **3a. Lista vacía.** Es válida y significa «ninguna».
- **4a. Sin categorías que ofrecer.** Si el catálogo no publicó ninguna, el bloque lo dice en vez de mostrarse vacío.

**Excepciones**

- **E3. Categoría inexistente o desactivada.** El sistema rechaza la operación **entera** y nombra los identificadores que sobran.

---

## Lo que no se lee en la ficha

**Por qué estaba diferido, en una línea.** El paso 2 del CU-04 prometía «datos personales, tallas
habituales, **preferencias** y direcciones» desde el Ciclo 1, pero las categorías las crea el CU-08:
construirlo entonces habría dejado un selector permanentemente vacío. Ahora existen, y el cambio fue
aditivo como se había previsto — no hubo que rehacer nada del CU-04 del Ciclo 1.

**Se guarda la selección completa, no altas y bajas.** Es el mismo razonamiento que el
reordenamiento de imágenes de CU-11: marcar de a una deja estados intermedios y una conexión cortada
a la mitad guarda medias preferencias. Mandar la lista entera hace que la operación sea idempotente
—repetirla no cambia nada— y que no exista un «a medio aplicar». Por eso es `PUT` y no `POST` ni
`PATCH`: reemplaza el recurso.

**El rechazo es total, no parcial.** Si una de cinco categorías ya no existe, no se guardan las
cuatro buenas. Media selección guardada sería peor que ninguna: el cliente creería que quedó lo que
eligió.

**El error nombra las que sobran.** La pantalla puede tener el árbol cargado desde antes de que el
Administrador desactivara una rama. Decir solo «hay un error» deja al cliente sin saber cuál
desmarcar.

**Las opciones salen de `/tienda/filtros` y no del maestro de CU-08.** Aquel exige rol
Administrador —un Cliente recibiría 403— y además devolvería categorías sin una sola prenda: una
preferencia que no puede recomendar nada. El endpoint público de la vitrina ya devuelve exactamente
el conjunto elegible. Es, además, la primera vez que una pantalla de P1 consume P5.

**El tope de doce es del caso de uso, no de la base.** La tabla puente admite las que sean. Pero el
recomendador del CU-33 usa las preferencias para **acotar** candidatas, y un cliente que marca las
treinta categorías no acota nada: una preferencia que abarca todo el catálogo no es una preferencia.
De paso ataja una petición con diez mil identificadores.

**Los duplicados se descartan en silencio.** La clave primaria compuesta de `cliente_categoria` los
rechazaría con un error de base. Mandar la misma categoría dos veces es algo que una interfaz puede
hacer sin querer; no es algo de lo que haya que avisarle al cliente.

**El cliente nunca envía su identificador.** El servidor lo resuelve desde el token, igual que en el
resto del CU-04: la pantalla no tiene forma de escribir las preferencias de otro.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/perfil` | 1 · el perfil, ahora con `categorias_preferidas` |
| `PUT` | `/perfil/categorias` | 3-4 · reemplaza la selección |

Los dos exigen rol **Cliente**. El `PUT` devuelve el perfil completo para que la pantalla se
refresque con una sola respuesta.

## Pantalla

| Plataforma | Dónde | Archivo |
|---|---|---|
| Web | Bloque «Lo que te interesa» del perfil | `frontend-web/src/app/features/cliente/perfil/` |

**Sin pantalla móvil en este ciclo**, y es deliberado: lo fijó la §2.1 de la contrapropuesta. La
pantalla móvil del CU-04 la construyó Mateo sin este bloque, y lo suma después si hay tiempo. El
*backend* ya está, así que agregarlo es una pantalla, no un caso de uso.

## Lo que esto deja preparado

`cliente_categoria` es la mitad declarada del perfil de preferencias que consume el **CU-33**. La
otra mitad —el historial de navegación y de compra— llega con el Ciclo 3.

Queda pendiente la arruga ya conocida y anotada en la §6.4: `cliente.talla_superior`,
`talla_inferior` y `talla_calzado` son `VARCHAR(10)` de texto libre, de cuando `talla` todavía no
era una entidad. El recomendador va a querer cruzarlas con `talla.id`, y convertirlas en claves
foráneas **no es un cambio aditivo**. Sigue fuera del alcance del Ciclo 2 y se decide entre los dos
antes del Ciclo 3.
