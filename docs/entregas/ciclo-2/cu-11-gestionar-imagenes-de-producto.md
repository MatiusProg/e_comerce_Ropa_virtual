# CU-11 · Gestionar imágenes de producto

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
> Un archivo por caso de uso, por el motivo explicado en
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-11 |
| **Nombre** | Gestionar imágenes de producto |
| **Descripción** | Permite al Administrador cargar las fotografías de un producto, asociarlas a sus variantes, elegir cuál lo representa en el catálogo y marcar la imagen con fondo transparente que consume el vestidor virtual. |
| **Propósito** | Dar al catálogo lo único que le falta para ser mostrable, y preparar el activo del que depende el módulo de realidad aumentada. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P3 · Catálogo (productos) |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF07 (la vitrina necesita imágenes), y el supuesto **S5** de §6.5 |
| **Precondiciones** | El Administrador tiene sesión iniciada y el producto existe (CU-10). |
| **Postcondiciones** | El producto tiene imagen principal para el catálogo (CU-17, CU-18) y, si corresponde, el PNG transparente por variante que el vestidor virtual necesita en el Ciclo 3 (CU-21). |

**Flujo principal**

1. El Administrador abre un producto y elige *Imágenes*.
2. El sistema muestra la galería del producto, con la imagen principal primero, indicando cuáles pertenecen a una variante y cuáles están marcadas para el vestidor virtual.
3. El Administrador elige uno o varios archivos de imagen.
4. El sistema verifica que cada archivo sea realmente una imagen de un formato admitido y de un tamaño aceptable, lo guarda en el volumen y registra su ruta. La primera imagen de un producto queda como principal.
5. El Administrador organiza la galería: asocia imágenes a variantes, elige la principal y marca las del vestidor virtual.

**Flujos alternativos**

- **3a. Asociar a una variante.** La imagen pasa a representar una combinación concreta de talla y color. Sin variante, la imagen es del producto en general.
- **3b. Cambiar la principal.** La anterior deja de serlo automáticamente: solo puede haber una por producto.
- **3c. Marcar para el vestidor virtual.** La imagen queda como el PNG transparente de su variante. Solo una por variante.
- **3d. Reordenar.** El Administrador cambia el orden en que se muestran.
- **3e. Eliminar.** La imagen se borra del catálogo y del volumen. Si era la principal, otra de la galería toma su lugar.

**Excepciones**

- **E1. Formato no admitido.** El archivo no es una imagen, o no es PNG, JPEG ni WEBP. El sistema lo rechaza sin guardar nada.
- **E2. Archivo demasiado grande.** Supera los 5 MB, o los 4000 píxeles de lado.
- **E3. Variante de otro producto.** El sistema impide asociar una imagen a una variante que no pertenece a ese producto.
- **E4. Imagen sin transparencia real.** El sistema impide marcar para el vestidor virtual una imagen cuyo archivo no tenga canal alfa con píxeles translúcidos.
- **E5. Transparente sin variante.** El sistema impide marcar para el vestidor una imagen que no pertenece a ninguna variante.

---

## Lo que no se lee en la ficha

**El formato se decide abriendo el archivo, no leyendo su nombre.** La extensión y el `content-type`
los pone quien sube, y los dos se pueden mentir. El servidor abre la imagen con Pillow y usa el
formato que ella misma declara. Es también lo que impide que un ejecutable renombrado a `.png` entre
al volumen.

**«Es un PNG» no significa «sirve para el vestidor».** El caso realista no es el archivo corrupto: es
la foto con fondo blanco guardada como PNG, que sale en modo RGBA con el canal alfa entero en 255.
Pasa cualquier control de formato y en el vestidor superpondría un rectángulo blanco sobre el torso.
Por eso el sistema mira el **mínimo real del canal alfa**, no el modo del archivo, y rechaza la
marca si no hay ningún píxel translúcido. Descubrir esto en el día 4, con el prototipo de realidad
aumentada ya andando, sería tarde.

**El nombre del archivo lo genera el servidor.** Un nombre elegido por quien sube puede traer `..`,
separadores o caracteres que el sistema de archivos interprete; y dos personas subiendo `frente.png`
se pisarían. Los archivos se agrupan por producto, de modo que borrar un producto es borrar una
carpeta.

**La base guarda la ruta, no la imagen ni su URL.** Es la §6.8: el volumen persistente de Railway
montado en `MEDIA_ROOT`. La respuesta trae además la `url` ya prefijada, para que la web y la app
móvil no tengan que saber cómo se monta el volumen.

**El orden de escritura está elegido para que la inconsistencia posible sea la barata.** No hay
transacción que abarque la base y el sistema de archivos, así que: al crear se guarda primero el
archivo y después la fila —si la fila falla, se borra el archivo—; al eliminar se borra primero la
fila y después el archivo. Lo peor que puede quedar es un archivo huérfano en el volumen, invisible
y de unos kilobytes; nunca una fila apuntando a un archivo que no existe, que sí se ve como una
imagen rota.

**Reordenar manda la lista completa, no un movimiento por petición.** De a uno quedan estados
intermedios con dos imágenes en la misma posición, y una conexión que se corta a la mitad deja el
orden a medio aplicar.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/catalogo/productos/{id}/imagenes` | 2 · galería |
| `POST` | `/catalogo/productos/{id}/imagenes` | 3-4 · subir |
| `PATCH` | `/catalogo/imagenes/{id}` | 3a · asociar a variante |
| `PATCH` | `/catalogo/imagenes/{id}/principal` | 3b |
| `PATCH` | `/catalogo/imagenes/{id}/transparente` | 3c · vestidor virtual |
| `PUT` | `/catalogo/productos/{id}/imagenes/orden` | 3d · reordenar |
| `DELETE` | `/catalogo/imagenes/{id}` | 3e |

Todos exigen rol **Administrador**. El router de CU-11 se incluye dentro del de catálogo —que ya
estaba montado desde el Ciclo 1— en lugar de montarse en `main.py`: es uno de los cinco archivos
compartidos del ciclo, y no agregar nada ahí vuelve el conflicto imposible en vez de improbable.

Los archivos en sí se sirven **sin token**, desde el volumen montado en `MEDIA_URL`. Las fotos del
catálogo son públicas —las muestran la vitrina y la app móvil— y exigir token obligaría a la app a
llevarlo en cada miniatura.
