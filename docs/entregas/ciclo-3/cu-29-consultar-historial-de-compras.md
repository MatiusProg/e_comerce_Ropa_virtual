# CU-29 · Consultar historial de compras

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-29 |
| **Nombre** | Consultar historial de compras |
| **Descripción** | Permite al Cliente consultar sus pedidos anteriores, su estado actual y descargar el comprobante digital de cada uno. |
| **Propósito** | Que el cliente pueda encontrar lo que compró sin depender de haberse guardado un enlace. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P7 · Ventas y Punto de Venta |
| **Prioridad** | Media |
| **Requisitos que realiza** | **RF15**, **RF16** |
| **Precondiciones** | El Cliente tiene sesión iniciada. |
| **Postcondiciones** | Ninguna sobre la compra. La primera descarga **emite** el comprobante si todavía no existía. |

**Flujo principal**

1. El Cliente abre *Mis compras* desde su barra.
2. El sistema lista sus compras, de la más nueva a la más vieja.
3. El Cliente despliega una y ve sus prendas, el total y adónde iba.
4. El Cliente descarga el recibo en PDF.

**Flujos alternativos**

- **2a. Sin compras.** Se dice que no hay ninguna y se ofrece el catálogo.
- **2b. Muchas compras.** Se pagina; por omisión diez por página.
- **4a. La compra todavía no se pagó.** No hay recibo, y se explica por qué.

**Excepciones**

- **E1. La compra es de otro cliente.** **404**, nunca 403.
- **E2. La compra no se pagó.** **409**, que no es lo mismo que no existir.

---

## Lo que no se lee en la ficha

### 1. El hueco que cierra

Hasta que esto existió, **alguien compraba y no tenía dónde ver lo que compró.**
La única forma de volver a su pedido era conservar el código que quedaba en la
URL después de pagar. Cerrar la pestaña equivalía a perderlo.

El backend de CU-27 expone la consulta *por código* —que es lo que su pantalla
de retorno necesita— pero no un listado, y con razón: listar el historial no es
parte de realizar un pedido. Es este caso de uso.

### 2. Van TODAS las compras, no sólo las pagadas

Es la decisión de fondo. Un historial que escondiera las canceladas y las que
esperan pago dejaría al cliente **sin forma de encontrar el pedido que acaba de
hacer** —que es justo el que va a buscar— ni de entender por qué un cobro que
recuerda no aparece.

**El estado se muestra; la fila no se esconde.** Y «esperando pago» no se pinta
en rojo: no falló nada, sólo no terminó.

### 3. El comprobante se emite una vez y se reimprime siempre

`comprobante.venta_id` es `UNIQUE`, y el modelo lo dice con todas las letras:
*«reimprimir no es reemitir»*.

La emisión crea la fila con su número y su fecha; **todas las descargas
posteriores generan el PDF a partir de esa misma fila**. Si el PDF se armara sin
fila, cada descarga sería un comprobante distinto para la misma compra — y un
comprobante que cambia de número cada vez que se lo mira no sirve como
comprobante de nada. Hay una prueba dedicada.

#### Se emite al confirmarse el pago, y también al descargar

`asegurar_comprobante` la llama **CU-28**, dentro de la transacción del cobro,
para que el recibo exista desde el instante en que el dinero entró — que es
cuando corresponde emitirlo, no cuando alguien se acuerda de descargarlo.

Pero **la misma función la llama la descarga**, y no es redundante: las ventas
que se pagaron *antes* de que CU-29 existiera no tienen comprobante, y sin esa
segunda llamada su botón fallaría para siempre. El `UNIQUE` hace que llamarla
dos veces sea inofensivo.

#### El número

`R-00000042`, derivado del identificador de la venta. Es único porque el
identificador lo es, y además **estable**: reintentar la emisión produce el mismo
número, así que el choque contra el `UNIQUE` se resuelve leyendo la fila que ya
estaba en vez de generando otra.

> **Lo que esto no es.** Una numeración fiscal de verdad es correlativa y sin
> huecos, lo que exige una secuencia dedicada y una conversación sobre
> facturación que este ciclo no tuvo. El PDF lo dice al pie: *«Documento sin
> validez fiscal»*. Un recibo sin datos fiscales que no lo aclare se puede
> confundir con una factura, y no lo es.

### 4. Es un RECIBO, no una FACTURA

El CHECK `factura_con_datos` exige NIT y razón social en una `FACTURA`. Pedirle
esos datos al cliente es otra conversación —y otra pantalla— que no entra en el
alcance. Se emite `RECIBO`, con los dos campos nulos, que es exactamente lo que
el esquema previó.

### 5. 409 y no 404 cuando la compra no se pagó

La compra existe; lo que falta es el pago. El cliente tiene que poder distinguir
**«no encontramos esa compra»** de **«esa compra todavía no se pagó»**, porque lo
que hace después es distinto: en un caso busca en otro lado, en el otro espera o
vuelve a pagar.

Y en la pantalla se dice por qué no hay recibo en vez de esconder el botón: un
botón que falta no explica nada, y el cliente se queda preguntándose si lo perdió.

### 6. El PDF se dibuja con ReportLab, no con HTML

Agregar un motor de HTML a PDF traería dependencias del sistema —un navegador
sin cabeza, o librerías de C— que habría que instalar también en el contenedor
de Railway. `reportlab` ya estaba en `requirements.txt` y es Python puro.

El texto se dibuja por coordenadas, que es tosco pero predecible: un recibo de
una página no justifica un motor de maquetado.

### 7. La descarga no es un `<a href>`

Aunque sería más simple. El endpoint exige el token, y **un enlace del navegador
no pasa por el interceptor que lo adjunta**: devolvería 401. Se descarga con
`HttpClient` y se guarda desde memoria, revocando el `objectURL` enseguida —si
no, cada recibo descargado queda en memoria hasta cerrar la pestaña.

La cabecera es `attachment` y no `inline`: el enunciado pide **descargar** el
comprobante. Con `inline` el navegador lo abre en una pestaña y guardarlo pasa a
ser un paso más que el cliente tiene que descubrir solo.

---

## Dónde vive

**Backend** — archivos propios dentro de P7, con el mismo patrón que `carrito_*`.
CU-27 es de Mateo y CU-29 de Karen; separarlos evita que las dos ramas toquen las
mismas líneas.

| Archivo | Qué |
|---|---|
| `ventas/historial_schemas.py` | la página; **reusa `PedidoOut`** de CU-27 |
| `ventas/historial_repository.py` | el listado; **reusa `_seleccion_pedido`** |
| `ventas/historial_service.py` | emisión del comprobante y el PDF |
| `ventas/historial_router.py` | `GET /tienda/compras` y `.../{codigo}/comprobante` |
| `tests/test_cu29_historial.py` | 13 pruebas |

**Sin migración**: `comprobante` existe desde la `0006`, con el `UNIQUE` puesto
justamente para esto.

> **El prefijo es `/tienda/compras` y no `/tienda/pedidos`**, aunque por debajo
> sean la misma tabla. Un «pedido» es el flujo de comprar y vive mientras eso
> ocurre; una «compra» es lo que quedó después. Para el cliente son dos momentos
> distintos y los busca en lugares distintos.

**Web**

| Archivo | Qué |
|---|---|
| `core/services/compras.service.ts` | el cliente HTTP |
| `features/cliente/compras/` | la pantalla |

Ruta `mi-cuenta/compras` —bajo `/mi-cuenta` y no bajo `/tienda`, por la misma
distinción— y su enlace en la barra del Cliente.

**Móvil** — *agregado el 20/09/2026.*

Hasta esa fecha **el caso de uso no existía en el teléfono**: se veía el pedido
recién pagado —porque la pantalla de CU-27 vuelve a él— y nada más. **Comprar y
después no poder volver a ver la compra es lo primero que alguien intenta**, y
en una demostración se nota enseguida.

Es la cuarta vez en el Ciclo 3 que aparece el mismo agujero —pasó con CU-33,
con CU-37 y con los datos de CU-39—: **un caso de uso sin forma de llegar no
está hecho.**

| Archivo | Qué |
|---|---|
| `data/modelos/compra.dart` | `PaginaDeCompras`; **reusa `Pedido`**, que ya existía para CU-27 |
| `data/repositorios/repositorio_compra.dart` | `misCompras()` |
| `features/compra/estado_compra.dart` | `misComprasProvider` |
| `features/compra/pantalla_mis_compras.dart` | la pantalla |

Ruta `/compras`, **suelta y no anidada bajo `/carrito`** aunque el detalle del
pedido sí lo esté: el carrito es *lo que estoy por comprar* y esto es *lo que
ya compré*. Colgarla de ahí haría que el botón de volver del teléfono llevara
al carrito, que no es de donde se vino. Con su entrada en la pantalla de
inicio, justo debajo de «Mi carrito».

Tres decisiones de la pantalla:

- **El provider se invalida cuando cambia el carrito.** Confirmar un pedido lo
  vacía y agrega una compra; sin eso, al volver del pago la lista traería una
  compra menos.
- **El estado se distingue por color Y por icono.** Quien no distingue rojo y
  verde tiene que poder ver igual si su pedido se pagó.
- **La fila lleva el total y el estado, no las prendas.** El pedido ya viene
  con sus líneas y dibujarlas sería gratis, pero una lista donde cada fila
  mide media pantalla deja de ser una lista. Acá se busca *cuál* compra; el
  detalle está a un toque.

**El comprobante en PDF no se descarga desde el móvil**, solo desde la web. En
un teléfono sin lector de PDF, abrirlo termina en «no hay ninguna aplicación»,
que se lee como que la descarga falló — el mismo criterio que ya se tomó en
CU-35 con los reportes.

## Deuda que queda anotada

- **La numeración no es fiscal.** Ver §3.
- **No hay FACTURA**, sólo RECIBO. Ver §4.
- **Nada se miró a 390 px**, como el resto de las pantallas del ciclo.
- **El móvil no descarga el comprobante.** Ver arriba.
- **El móvil no pagina**: trae las diez primeras compras. Con el volumen de la
  demostración alcanza, y agregar el desplazamiento infinito sin tener con qué
  probarlo sería código que nadie ejercitó.
