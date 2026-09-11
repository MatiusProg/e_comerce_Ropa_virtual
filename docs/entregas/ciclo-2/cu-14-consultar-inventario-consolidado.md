# CU-14 · Consultar inventario consolidado

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-14 |
| **Nombre** | Consultar inventario consolidado |
| **Descripción** | Permite al Administrador consultar las existencias de toda la red por producto, variante y sucursal, con su estado (disponible, reservada, agotada, próxima a ingresar). |
| **Propósito** | Ver cómo está repartido el stock entre tiendas, que es lo que permite detectar el desbalance entre sucursales y decidir una transferencia. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P4 · Inventario |
| **Prioridad** | Alta |
| **Requisitos que realiza** | **RF21** (control de existencias por sucursal) · RF24 (consulta de reportes de inventario) |
| **Precondiciones** | El Administrador tiene sesión iniciada. |
| **Postcondiciones** | Ninguna: es de solo lectura. |

**Flujo principal**

1. El Administrador abre el inventario consolidado.
2. El sistema muestra una fila **por variante** con su saldo sumado en toda la red, su estado y en cuántas sucursales hay unidades, más un resumen de totales.
3. El Administrador despliega una fila y ve el reparto: cuánto hay en cada sucursal, disponible y reservado.

**Flujos alternativos**

- **2a. Filtrar por sucursal.** Los totales pasan a ser de esa tienda, y la pantalla lo advierte para que no se lean como de la red.
- **2b. Filtrar por estado.** Disponible, reservada o agotada.
- **2c. Buscar.** Por SKU, por nombre de prenda o por color.
- **2d. Ordenar.** Por prenda, por más o menos stock, o por menos sucursales —que es el orden que pone arriba lo que está concentrado en una sola tienda—.
- **3a. Prenda concentrada.** Si todo el stock de una variante está en una sola sucursal habiendo varias, el sistema lo señala.

**Excepciones**

- **E1. Sin existencias registradas.** El sistema lo informa e indica que se cargan con un ingreso de mercadería. No es un error: `existencia` solo tiene filas donde alguna vez entró algo.
- **E2. Usuario sin permiso.** Solo el Administrador. El Encargado tiene su ámbito acotado a su sucursal y su caso de uso es CU-16.

---

## Lo que no se lee en la ficha

**Agrupa por variante, y ahí está la diferencia con la pantalla de inventario de CU-13 y CU-15.**
Aquélla lista el par `(variante, sucursal)` porque un ingreso o un ajuste se hacen sobre una tienda
concreta: responde «sobre qué fila opero». Ésta responde «cómo está repartida la prenda en la red».
Una prenda en tres tiendas ocupa una fila con el reparto adentro, no tres filas que hay que
reconstruir a ojo. Sin esa diferencia, CU-14 sería la misma pantalla con otro nombre.

**«Agotada» gana sobre «reservada».** Una variante con 0 disponibles y 3 apartadas está agotada para
quien quiera comprarla hoy. Decir «reservada» haría creer que hay algo que ofrecer, que es
exactamente lo contrario de lo que el número significa.

**El estado «próxima a ingresar» está en el contrato y hoy no lo devuelve ninguna fila.** El
enunciado lo pide y la descripción del caso de uso lo promete, pero **ningún caso de uso lo
produce**: CU-13 registra la mercadería cuando ya llegó, y nada anuncia lo que está en camino. Es el
agujero **H1** del [análisis de alcance del 10/09](02-analisis-de-alcance-y-vestidor-virtual.md), y
lo cerraría el **CU-39** propuesto allí —el Proveedor informa disponibilidad y plazo—. Se declara el
valor para no tener que cambiar el contrato después, el filtro existe y devuelve vacío, y hay una
prueba que lo deja escrito. No es un olvido: es una dependencia que falta, y está anotada como tal.

**El filtro por sucursal se aplica antes de agrupar, no después.** Preguntar «qué hay en la Centro»
tiene que devolver los saldos de la Centro. Aplicarlo después daría las variantes que están en la
Centro, pero con su reparto en toda la red: una vista de red disfrazada de vista de tienda. Se
resuelve pasando el filtro a la costura, no filtrando el resultado.

**El resumen suma todo lo filtrado y se calcula antes de paginar.** Un resumen que solo suma las
veinte filas visibles no es un resumen.

**Los datos salen de la costura C1, no de una consulta propia.** `existencia` es de Mateo y la regla
del ciclo es que nadie consulte la tabla del otro: `inventario/service.py` expone
`inventario_consolidado(db, ...)` justamente para esto. El precio es que la agrupación, el filtrado
fino, el orden y la paginación se resuelven en memoria en vez de en SQL. Al tamaño de este catálogo
no es un problema —`existencia` solo tiene filas donde hubo un ingreso, y el orden de magnitud son
centenares—. Si creciera a decenas de miles, **lo correcto no sería empezar a consultar la tabla
desde acá** —eso rompe el acuerdo y deja la tabla con dos dueños— sino pedir que la costura acepte
paginación. Queda anotado para que la decisión, si llega, se tome a propósito.

**El aviso de concentración es el motivo de existir de la pantalla.** Sesenta unidades en una
sucursal y cero en las otras cuatro no es lo mismo que sesenta repartidas, y el total solo no lo
dice. Por eso viaja `sucursales_con_saldo` calculado y por eso hay un orden que lo usa.

**La sucursal en cero se muestra apagada, no se esconde.** Es al revés que en CU-19: al cliente le
sobra saber dónde no hay, y al Administrador es justamente lo que necesita para decidir la
transferencia.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/inventario/consolidado` | 2-3 · listado agrupado y resumen |

Exige rol **Administrador**. Devuelve el listado y el resumen en una sola respuesta: la pantalla los
muestra siempre juntos y se calculan del mismo filtrado, así que separarlos serían dos consultas que
recorren lo mismo y abriría la posibilidad de que la cabecera y la tabla queden desfasadas.

## Dónde vive el código

CU-14 es de Karen por la §4.1 de la contrapropuesta —el único caso de uso de inventario que no
escribe ninguna tabla—, pero pertenece al paquete de Mateo. Para que ninguna de las dos personas
edite los archivos de la otra, vive en archivos propios dentro del mismo paquete, con el patrón que
`catalogo/` ya usa para `imagenes_*` y `temporadas_*`:

```
backend/app/modules/inventario/consolidado_schemas.py
backend/app/modules/inventario/consolidado_service.py
backend/app/modules/inventario/consolidado_router.py
```

Ningún archivo de CU-13 ni de CU-15 se tocó. Lo único compartido es la línea de montaje en
`main.py` y una línea en `MODULOS_CON_ROUTER`.

## Pantalla

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web | `/admin/consolidado` | `frontend-web/src/app/features/admin/consolidado/` |

Sin pantalla móvil: el actor es el Administrador, y la app es del Cliente.
