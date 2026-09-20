# CU-12 · Gestionar promociones

Guía de lo que se construyó y por qué cada decisión es como es.

> **Escrita el 20/09/2026.**
>
> **Sobre el reparto.** El plan asigna CU-12 a Mateo
> (`docs/05-plan-y-cronograma.md`, «P3 (resto)»). Estaba sin empezar y él venía
> de cerrar CU-37 y CU-39, así que se tomó de este lado. Es la misma decisión
> que con CU-28, CU-31 y CU-32.

---

## 1. Lo que resuelve, y lo que hubo que agregarle

El RF35 lo dice en una línea:

> Permite al Administrador definir descuentos con vigencia aplicables a un
> producto, una categoría o una temporada.

El caso de uso, leído al pie, es **definir**. Pero una promoción que no rebaja
nada no es una función: es una tabla. Así que CU-12 también las **aplica**, en
los cinco lugares donde un precio se muestra o se cobra.

## 2. La regla del módulo: cuando dos se cruzan, gana la mayor

Es lo único verdaderamente difícil de este caso de uso.

Una prenda puede quedar alcanzada por una promoción de su producto **y** otra
de su categoría a la vez. Eso es legítimo y no hay forma razonable de
prohibirlo: obligaría al Administrador a revisar todo el catálogo cada vez que
carga una.

Había tres salidas:

| | Qué pasa | Por qué no / sí |
|---|---|---|
| **Sumarlas** | 20 % + 15 % = 35 % | Dos promociones pensadas por separado terminan regalando la prenda sin que nadie lo haya decidido. |
| **Gana la más específica** | producto > categoría > temporada | Suena ordenado y falla en el caso corriente: si una camisa tiene 10 % propio y después se lanza «toda la categoría al 20 %», el cliente vería 10 % — menos de lo que la vitrina anuncia. |
| **Gana la mayor** ✅ | se aplica una sola, la más grande | El cliente paga el mejor precio que la tienda anunció. A igual porcentaje gana la más específica, que es la que alguien puso mirando esa prenda. |

**No se acumulan nunca.** Y la respuesta lleva el **nombre** de la que ganó, no
solo el porcentaje: quien ve «−20 %» sin saber de qué se pregunta si es un
error, y el cajero que tiene que explicarlo en el mostrador necesita poder
leerlo.

La regla está escrita **en la pantalla**, no en una ayuda escondida: quien
carga la segunda promoción sobre la misma categoría tiene que saberlo antes de
guardar, no después de que un cliente reclame.

## 3. Tres decisiones de esquema

### El descuento es un porcentaje, no un monto fijo

1. **El alcance es amplio.** «Bs 50» sobre una categoría cuyas prendas van de
   Bs 80 a Bs 900 regala la primera y no mueve la última.
2. **No puede dejar el precio en negativo.** Acotado a (0, 100], el descuento
   nunca supera el precio — que es justo lo que exige el CHECK
   `ck_detalle_venta_descuento_acotado` al congelar la venta.
3. **Sobrevive a un cambio de precio.** Si la tienda sube una prenda, el
   porcentaje sigue significando lo mismo.

Agregar el monto fijo después es una columna más y un discriminador; no obliga
a reescribir lo guardado, porque cada promoción diría de qué tipo es.

### La vigencia son fechas, no marcas de tiempo

Quien carga una promoción piensa «del 1 al 15 de octubre», no «del 1 a las
00:00:00−04:00». Guardar `timestamptz` obligaría a inventar una hora de corte
que el Administrador nunca eligió.

**El precio de esa decisión es que hay que preguntar qué día es en Bolivia.**
Railway corre en UTC y ahí el día cambia a las 20:00 hora boliviana: con
`date.today()`, una promoción que termina «el 30» dejaría de aplicar con cuatro
horas de tienda abierta y clientes adentro. Lo resuelve `_hoy()`.

El mismo cuidado va del lado de la web: las fechas **no pasan por
`toISOString()`**, que convierte a UTC y le restaría un día a la fecha elegida
—el 1 de octubre se guardaría como el 30 de septiembre—.

### Tres claves foráneas nulables, no una `objetivo_id` genérica

La genérica es más corta y **no puede tener clave foránea**: nada impediría
apuntar a una categoría borrada, y esa promoción no se aplicaría nunca sin que
nadie entendiera por qué. Con tres FK, la base garantiza que el objetivo existe
y un CHECK garantiza que hay **exactamente uno**, coherente con el alcance
declarado.

### No guarda a qué variantes alcanza

Guarda el alcance —«la categoría 4»— y no la lista de variantes que hoy caen
dentro. Materializarla obligaría a recalcularla cada vez que entra un producto a
la categoría, y el día que alguien se olvidara, la promoción dejaría afuera
prendas que el cartel de la vitrina promete.

Con el alcance guardado, un producto que entra a una categoría en promoción
entra ya con el descuento puesto, sin que nadie haga nada.

## 4. Dónde se aplica

`descuentos_por_variante` y `descuentos_por_producto` son la costura. La
consumen:

| Quién | Qué muestra |
|---|---|
| Vitrina y ficha (P5) | El precio de lista tachado y el rebajado al lado |
| Carrito (CU-26) | Lo mismo, por línea, y el total ya con descuento |
| Pedido (CU-27) | Congela precio y descuento; la pasarela cobra el rebajado |
| Mostrador (CU-31) | Igual, y el cajero ve de cuánto era |

**Una consulta por pantalla, no una por prenda.**

`carrito_service._armar_carrito` venía anunciando desde el Ciclo 3 temprano que
ese era el punto de enganche. Lo es, y es el único: el total del carrito sale de
ahí y de ningún otro lado.

### El precio y el descuento viajan separados

Nunca un solo número ya rebajado. Una tarjeta que solo muestra «Bs 200» no es
una oferta, es un precio; lo que vende es ver «Bs 250» tachado.

### El descuento se congela junto con el precio

En `detalle_venta.descuento_unitario`. Si mañana la promoción se apaga, el
pedido sigue explicando por qué se cobró lo que se cobró — y `venta.descuento`
es lo que deja que CU-36 pueda decir cuánto se rebajó.

Las dos columnas existen desde la `0006_ciclo3_ventas`, en cero, con el CHECK
`total = subtotal − descuento` ya atado. Se pusieron entonces a propósito:
agregarlas ahora obligaría a decidir qué descuento tenían las ventas ya hechas,
y la respuesta correcta —ninguno— se pierde si la columna no estaba.

## 5. Un error que casi entra

El mostrador arma su total desde el precio de lista y lo manda como
`total_esperado`. Con descuento, ese total **no coincidiría con el del
servidor** y CU-31 rechazaría con 409 *toda* venta de una prenda en promoción.

Por eso `PrendaEnMostradorOut` y `LineaDeReservaOut` llevan el descuento, y
`totalCentavos` de la pantalla usa `precio_final`.

## 6. Los endpoints

```
GET   /api/v1/catalogo/promociones                  lista, con cuáles descuentan hoy
POST  /api/v1/catalogo/promociones                  crear → 201
GET   /api/v1/catalogo/promociones/{id}             una
PATCH /api/v1/catalogo/promociones/{id}             nombre, porcentaje, vigencia
PATCH /api/v1/catalogo/promociones/{id}/estado      encender o apagar
```

Solo **ADMINISTRADOR**: un descuento cambia lo que la tienda cobra en todas sus
sucursales a la vez, no es una decisión de mostrador.

**No hay borrado.** Una promoción se apaga: las ventas ya cobradas con ella la
nombran en su historial, y volver a encenderla la temporada que viene es lo
normal.

**El alcance y el objetivo no se editan.** Cambiarle el alcance a una promoción
viva es otra promoción: la que estaba corriendo alcanzaba otras prendas, y los
pedidos ya cobrados con ella quedarían explicados por una regla que ya no dice
lo mismo. Para eso se apaga ésta y se crea otra, que además deja rastro de las
dos.

### `activa` y `vigente` no son lo mismo

Y confundirlas es la forma más fácil de creer que el sistema está roto:

- `activa` — el interruptor, lo que el Administrador controla.
- `vigente` — si **hoy** está descontando.

Una promoción activa que empieza el mes que viene no descuenta nada. La
pantalla muestra las dos, y cuando no descuenta el tooltip dice cuál de los dos
motivos es.

## 7. Sobre el número de la migración

Es la **0016** y cuelga de la `0015_ciclo3_abastecimiento` de Mateo.

Nació siendo la 0015 —la `0014` había dejado anotado que «la de Karen es la
0015»— y **estaba mal**: entre medio Mateo escribió la suya para CU-39 y ya
estaba en `main`. Dos 0015 hermanas dejan el árbol de Alembic con dos cabezas y
`alembic upgrade head` falla sin decir cuál es el problema. Lo atrapó el propio
`upgrade` contra la base de pruebas.

**La lección: antes de numerar una migración hay que traer `main`.** No alcanza
con mirar el head de la rama propia.

Los docs del Ciclo 3 temprano prometían `0007_ciclo3_promociones`. Ese número
se reservó y la cadena le pasó por encima; un archivo `0007` que corre después
de la 0015 sería una trampa para quien lea la carpeta.

## 8. Lo que queda pendiente

- **No hay monto fijo**, solo porcentaje (sección 3).
- **No hay promoción «sobre todo el catálogo».** No está pedida, y se arma con
  una por categoría — que además deja rastro de cuál se aplicó.
- **No se avisa del solapamiento al cargar.** CU-09 sí lo hace con las
  temporadas, porque ahí dos vigentes compiten por ser *la* temporada. Acá el
  cruce es legítimo y la regla lo resuelve sola; avisar en cada alta sería ruido
  sobre algo que no es un problema.
- **El desplegable de productos no pagina**: pide los primeros 200. Una tienda
  con miles necesitaría un buscador ahí.
- **`venta.descuento` no se muestra todavía en el tablero de CU-36.** El dato
  está guardado desde ahora; mostrarlo es una consulta más en P11.
