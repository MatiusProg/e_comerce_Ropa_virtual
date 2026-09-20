# CU-38 + CU-39 · El abastecimiento tiene final

> **Escrita el 20/09/2026.** No es un caso de uso nuevo: es el final que le
> faltaba al flujo que CU-38 y CU-39 empiezan.

---

## 1. El hueco, en una frase

Una vez que una prenda aparecía como **«próxima a ingresar», no había forma de
recibirla.**

Lo único que existía era el ingreso directo de CU-13, que no sabe nada del
anuncio. Así que la mercadería llegaba, entraba al saldo, y el consolidado la
seguía prometiendo como en camino: **la contaba dos veces**.

Y el proveedor, del otro lado, anunciaba y **no se enteraba de nada**: su aviso
quedaba «Informado» para siempre aunque el lote hubiera llegado hacía semanas.

La migración **0015 lo había dejado anotado**, con estas palabras:

> *No se cierra solo al llegar la mercadería. […] Atarlo al ingreso exige
> decidir qué pasa si llega la mitad, o si llega de otro proveedor, y esas son
> reglas de negocio que nadie definió.*

Este documento es esas reglas.

## 2. Las cuatro reglas

| Lo que pasa | Qué hace el sistema |
|---|---|
| Llega **todo** | El aviso pasa a `RECIBIDO` y deja de sumar al «próximo a ingresar». |
| Llega **menos** | Sigue `ANUNCIADO` **por el resto**. Cerrarlo haría desaparecer mercadería que el proveedor todavía debe. |
| Llega **más** | Entra todo al inventario y el aviso se cierra. El sobrante es un dato del remito, no un error: la mercadería ya está físicamente en la tienda, y rechazar el ingreso dejaría el depósito con cajas que el sistema dice que no existen. |
| **No hay aviso** | El ingreso funciona igual que siempre. CU-13 existe desde el Ciclo 1 y cubre la compra que nadie anunció; exigir el aviso lo rompería. |

### Por qué hace falta `cantidad_recibida` y no alcanza con el estado

Sin ella, una entrega parcial no se puede representar: o el aviso está abierto
por el total —y el consolidado promete de más— o está cerrado —y promete de
menos—. Con el acumulado, **lo que sigue en camino es `cantidad -
cantidad_recibida`**, que es exactamente lo que falta.

Es un acumulado y no un reemplazo: una entrega puede venir en tres camiones.

## 3. Lo que cambia en la pantalla de ingreso

Los avisos pendientes aparecen **arriba, antes del buscador de prendas**.

Quien recibe un camión casi siempre está recibiendo algo anunciado, y hacerle
buscar la variante a mano es pedirle que reconstruya un dato que el sistema ya
tiene. Peor todavía: **así es como el aviso terminaba sin cerrarse nunca** — el
camino corto no existía, y el largo no cerraba nada.

- Tocar un aviso agrega la línea con la **cantidad pendiente ya puesta y
  editable**: lo más común es que llegue todo, y lo segundo más común es que
  llegue parte.
- Están ordenados **por plazo**, no por fecha de anuncio: lo que le sirve a
  quien recibe es «esto tendría que estar llegando».
- **El primer aviso que se toma fija el proveedor del remito.** Un remito es de
  un solo proveedor; mezclar dos haría que el servidor rechace el segundo
  *después* de que la persona lo agregó.
- Si se pone menos de lo pendiente, la línea dice **«quedan 15»**. Una entrega
  parcial que no lo dice se lee como completa y el encargado deja de esperar el
  resto.

```
GET  /api/v1/inventario/ingresos/avisos
POST /api/v1/inventario/ingresos   → lineas[].abastecimiento_id (opcional)
```

## 4. Lo que cambia para el proveedor

Su pantalla ahora tiene **tres estados y no dos**:

| | |
|---|---|
| **Informado** | Anunciado, todavía en camino. |
| **Entregado** | Llegó. Con la fecha en el tooltip. |
| **Retirado** | Lo canceló él. |

Y en la cantidad se lee **«entraron 30 · faltan 15»**.

«Entregado» y «Retirado» se distinguen con color propio porque son cosas
opuestas —uno entregó, el otro se arrepintió— y hasta ahora los dos caían en
la misma pastilla gris.

Los `RECIBIDO` **se muestran siempre**, aunque no se pidan los cancelados:
ocultarlos dejaría su pantalla igual que antes —solo lo que todavía no llegó—
y el lote entregado desaparecería sin decir que se entregó.

## 5. Lo que no se puede hacer

- **Cerrar el aviso de otra prenda.** Sin esa comprobación, recibir una blusa
  cerraría el aviso de un pantalón y las dos cuentas quedarían mal a la vez.
- **Cerrar el aviso de otro proveedor.** Llegaría la mercadería de uno y el
  sistema descontaría la deuda del otro.
- **Recibir dos veces el mismo aviso.**

Los tres se comprueban **antes de tocar ningún saldo**, para que un aviso
inválido corte el ingreso entero (excepción E9) en vez de dejar medio remito
cargado y la deuda del proveedor descontada a medias. Hay una prueba
justamente de eso.

## 6. Detalles que costaron

- **El bloqueo.** `para_recibir` usa `with_for_update`: dos recepciones
  simultáneas del mismo aviso leerían el mismo `cantidad_recibida` y la
  segunda pisaría a la primera. Es el mismo bloqueo que ya usa la existencia
  (RNF11).
- **El índice único parcial no cambia.** Sigue siendo sobre `ANUNCIADO`, así
  que un aviso recibido ya no bloquea uno nuevo del mismo proveedor para la
  misma variante — que es justo lo que se quiere: el proveedor vuelve a
  anunciar el lote siguiente.
- **La bajada no devuelve los `RECIBIDO` a `ANUNCIADO`**, los pasa a
  `CANCELADO`. Devolverlos haría que el consolidado prometa otra vez
  mercadería que ya está en el saldo — el defecto que esta migración vino a
  arreglar, reintroducido por el `downgrade`.
- **El identificador de la revisión no puede pasar de 32 caracteres.**
  `alembic_version.version_num` es `varchar(32)`, y
  `0018_ciclo3_recepcion_de_anuncios` son 33: la migración aplica el DDL y
  revienta al anotar la versión. Quedó como `0018_ciclo3_recepcion`.
- **`op.drop_constraint` aplica la convención de nombres.** Pasarle
  `"ck_abastecimiento_estado"` busca
  `ck_abastecimiento_ck_abastecimiento_estado`. Hay que envolverlo en
  `op.f(...)`. Es la misma trampa que ya nos costó una migración de arreglo.

## 7. Límites conocidos

- **El aviso no dice a qué sucursal llega.** El proveedor anuncia contra la
  red y quien recibe lo mete en la suya. Poner sucursal en el anuncio exigiría
  que el proveedor sepa el reparto interno de la tienda, que no es asunto suyo.
- **No hay aviso automático al proveedor cuando su lote entra.** Lo ve al
  entrar a su pantalla. Mandarle un correo es CU-40, que no está construido.
- **No hay pantalla en el móvil.** El ingreso lo hace el encargado desde la
  web.
