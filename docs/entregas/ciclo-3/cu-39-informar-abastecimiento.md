# CU-39 · Informar disponibilidad y plazo de abastecimiento

> **Escrita el 20/09/2026.** Realiza el **RF38** y cierra el **agujero H1** del
> análisis de alcance del 10/09.

---

## 1. Qué agujero cierra

El enunciado pide que el inventario consolidado distinga cinco estados, entre
ellos **«próxima a ingresar»**. `EstadoExistencia.PROXIMA_A_INGRESAR` estaba
declarado desde el Ciclo 2 y **ninguna fila lo devolvía**.

No era un olvido: lo decía el propio comentario del enum. CU-13 registra la
mercadería **cuando ya llegó**, y nada en el sistema anunciaba lo que estaba
por llegar. El estado era inalcanzable.

Este caso de uso es lo que faltaba. El proveedor declara qué puede abastecer,
cuánto y en cuántos días; el consolidado lo lee y recién entonces ese estado
existe.

## 2. Las decisiones del modelo

**Cuelga de la variante, no del producto.** El consolidado es por variante
(decisión D1): «hay 3 de la blusa» no significa nada sin talla ni color. Un
anuncio a nivel producto habría que repartirlo entre variantes al mostrarlo, y
ese reparto sería inventado.

**El plazo va en días, no en fecha.** El proveedor piensa en «te lo tengo en
una semana», no en «el 27 de septiembre». Guardar la fecha obligaría a
recalcularla en cada edición y a decidir qué hacer con una que ya pasó —
problema que con días no se plantea.

**Un anuncio vigente por proveedor y variante**, con índice único *parcial*
sobre los `ANUNCIADO`. Parcial y no UNIQUE normal por lo mismo que en
`turno_caja`: los cancelados son muchos y legítimos, y prohibirlos impediría
volver a anunciar algo que se retiró.

Dos anuncios vigentes del mismo proveedor para la misma variante no es un dato
útil sino una duda: el consolidado tendría que decidir si suma o si toma el
último, y cualquiera de las dos sorprende a alguien.

**Cancelar marca, no borra.** El compromiso existió, y el inventario que lo
mostró durante una semana tiene que poder explicarse después.

## 3. Cómo entra en el inventario consolidado

```
si hay disponible        → DISPONIBLE
si hay reservado         → RESERVADA
si hay anunciado         → PROXIMA_A_INGRESAR      ← lo nuevo
si no                    → AGOTADA
```

**«Próxima a ingresar» va al final, y es deliberado.** Una variante con 5
disponibles y 20 anunciadas está DISPONIBLE: se puede vender hoy, y decir
«próxima a ingresar» haría creer lo contrario. Solo cuando no hay nada ni
disponible ni apartado, lo anunciado es la información útil: *no hay, pero
viene*.

Se suma **entre proveedores** y se toma el plazo **menor**: si dos anuncian la
misma variante van a llegar las dos cantidades, y lo que le importa a quien
mira el inventario es cuándo llega la primera.

La consulta va **en bloque** para toda la página. Preguntar variante por
variante serían decenas de viajes para pintar una columna.

## 4. Quién puede

```
GET    /api/v1/proveedor/abastecimiento/variantes    las combinaciones de MIS productos
GET    /api/v1/proveedor/abastecimiento              lo que informé
POST   /api/v1/proveedor/abastecimiento              informar
DELETE /api/v1/proveedor/abastecimiento/{id}         retirar el aviso
```

**Solo el PROVEEDOR**, y **solo sobre sus propios productos**. Un «próxima a
ingresar» respaldado por quien no abastece esa prenda promete algo que nadie
se comprometió a traer. El administrador tampoco: es el proveedor quien se
compromete, no la tienda por él.

Y **cada proveedor cancela el suyo**: sin eso, uno borra el compromiso de otro
y el inventario pierde información sin que su dueño se entere.

## 5. La pantalla

`/proveedor/abastecimiento`, en el menú del proveedor.

El encabezado dice **para qué sirve**: «lo que informes acá aparece en el
inventario de la tienda como próxima a ingresar». Sin eso parece un cuaderno
privado y nadie lo llena; lo que le da sentido a cargarlo es que la tienda lo
ve.

Detalles menores que se notan al usarla: el selector solo ofrece las
combinaciones propias —el servidor ya filtra, pero además no se muestran—, y
al informar se limpia la prenda **pero no el plazo**, porque quien informa
varias seguidas suele darles el mismo.

## 6. Límites conocidos

**Una variante que nunca tuvo stock en ninguna sucursal no aparece.** El
consolidado se arma sobre las filas de `existencia`, que se crean con el
primer ingreso; una variante sin esa fila no está en el listado y por lo tanto
no puede mostrarse como próxima a ingresar.

Cubre el caso que importa —«se agotó y vuelve»—. El otro, anunciar algo que la
tienda nunca tuvo, exigiría que el consolidado saliera también de
`abastecimiento`, y eso es cambiar de dónde salen sus filas. Se deja anotado
en vez de resolverse a medias.

**El aviso no se cierra solo al llegar la mercadería.** Cuando el ingreso de
CU-13 registra lo que llegó, el anuncio sigue vigente hasta que alguien lo
retira. Atarlo al ingreso exige decidir qué pasa si llega la mitad, o si llega
de otro proveedor, y esas son reglas de negocio que nadie definió. Adivinarlas
sería peor que dejar el cierre a mano.
