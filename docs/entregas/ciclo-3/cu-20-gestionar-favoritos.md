# CU-20 · Gestionar favoritos

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).
> **Primera ficha del Ciclo 3.**

| Campo | Contenido |
|---|---|
| **Código** | CU-20 |
| **Nombre** | Gestionar favoritos |
| **Descripción** | Permite al Cliente marcar prendas como favoritas y consultar posteriormente su lista. |
| **Propósito** | Que el Cliente guarde lo que le interesó para volver a decidirlo, y —sobre todo— alimentar el historial de preferencias que consume el recomendador. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P5 · Catálogo Público y Disponibilidad |
| **Prioridad** | Baja |
| **Requisitos que realiza** | **RF31** · alimenta **RF25** a través del CU-33 |
| **Precondiciones** | El Cliente tiene sesión iniciada. |
| **Postcondiciones** | La prenda queda marcada o desmarcada para ese cliente. |

**Flujo principal**

1. El Cliente navega el catálogo (CU-17) o abre una ficha (CU-18).
2. El Cliente pulsa el corazón de una prenda y el sistema la marca.
3. El Cliente abre *Mis favoritos* y ve sus prendas, la última marcada primero.
4. El Cliente pulsa el corazón de una prenda marcada y el sistema la desmarca.

**Flujos alternativos**

- **2a. Marcar dos veces.** No duplica ni falla: la operación es idempotente.
- **3a. Lista vacía.** El sistema lo dice y ofrece ir al catálogo.
- **3b. Prenda que dejó de ofrecerse.** No se lista, pero **su marca no se borra**.
- **4a. Desmarcar algo que no estaba.** Tampoco falla.

**Excepciones**

- **E1. La prenda no existe o ya no se ofrece.** No se puede marcar. Las tres situaciones —inexistente, desactivada, sin variantes activas— se responden igual, por el mismo motivo que en CU-18.

---

## Lo que no se lee en la ficha

**Por qué este caso de uso se adelantó, siendo prioridad Baja.** No se eligió por prioridad sino por
lo que desbloquea. El **RF31** dice con todas las letras que los favoritos «alimentan el historial de
preferencias que necesita el recomendador del RF25». Con CU-04 preferencias entregado el mismo día,
CU-20 completa **la preferencia declarada** que consume CU-33 — que es el caso de uso que el
enunciado menciona explícitamente y el que se salva si el Ciclo 3 obliga a elegir. Hacerlo entre el
carrito y la pasarela habría sido hacerlo tarde.

Además es el único caso de uso del Ciclo 3 que es **enteramente de P5**, así que no se cruza con las
reservas, que es donde está trabajando la otra mitad del equipo.

**El favorito es del PRODUCTO, no de la variante. Es la única excepción a la decisión D1 en todo el
sistema.** Existencia, reserva y venta apuntan a la variante porque son operaciones sobre unidades
concretas. Un favorito es una **intención**, y el cliente la declara antes de elegir talla y color —
de hecho la declara justamente para volver a decidirlas después. Guardarlo por variante obligaría a
marcar «me gusta esta blusa en S negra» y perdería el favorito si esa combinación se desactiva. Y es
lo que lo vuelve útil para el RF31: lo que el recomendador necesita de acá es la **categoría**, que
es atributo del producto.

**La marca no se borra cuando la prenda se desactiva; solo se deja de mostrar.** Son dos cosas
distintas y conviene que lo sean: la fila es historial de preferencia y el CU-33 la va a leer,
mientras que listarla sería ofrecer algo que no se puede comprar. Se puede comprobar: la prenda
desaparece de la lista pero sigue apareciendo en los identificadores.

**Desmarcar no exige que la prenda siga ofreciéndose, y marcar sí.** La asimetría es deliberada: si
se exigiera para desmarcar, una prenda desactivada después de marcarla quedaría como un favorito
imposible de borrar.

**Las dos operaciones son idempotentes, y por eso el alta es `PUT` y no `POST`.** La clave primaria
compuesta de `favorito` garantiza que no se duplique, pero chocar contra ella devolvería un error de
base: el corazón de una interfaz se toca dos veces sin querer, y eso no puede ser un error. El
repositorio pregunta antes de insertar, que es lo que convierte la garantía de la base en una
promesa del endpoint.

**Los identificadores van en un endpoint aparte, y es por una restricción real.** La vitrina de
CU-17 es **pública**: no sabe quién la está mirando. Agregarle un campo `es_favorito` a la tarjeta
obligaría a que el catálogo tuviera sesión, que es exactamente lo que CU-17 decidió no tener. La
pantalla pide la lista de identificadores una sola vez al entrar, si hay sesión de Cliente, y pinta
los corazones del lado del navegador.

**La tarjeta es la misma que la de la vitrina, y hay una prueba que lo exige.** El servicio arma las
tarjetas en una única función compartida por CU-17 y CU-20. Si se duplicara, el día que se agregue
un dato nuevo la misma prenda se vería distinta en cada pantalla; la prueba compara el objeto
completo devuelto por los dos endpoints.

**El corazón se pinta antes de que responda el servidor.** Esperar la respuesta para pintarlo hace
que parezca que no funcionó. Si el servidor falla, se revierte y se avisa — que es el único caso en
que el cliente ve un salto. Y el `Set` de favoritos se reemplaza en vez de mutarse: una señal compara
por referencia, y mutar el conjunto no redibujaría nada.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `GET` | `/tienda/favoritos` | 3 · la lista paginada |
| `GET` | `/tienda/favoritos/ids` | 1-2 · para pintar los corazones del catálogo |
| `PUT` | `/tienda/favoritos/{producto_id}` | 2 · marcar |
| `DELETE` | `/tienda/favoritos/{producto_id}` | 4 · desmarcar |

Los cuatro exigen rol **Cliente**, y son los únicos de P5 que exigen sesión: el resto del paquete es
público. Por eso viven en un `favoritos_router.py` aparte, incluido dentro del router de la vitrina
—no montado en `main.py`— con el mismo patrón que CU-11 usa dentro del router de catálogo.

`/ids` se declara **antes** que `/{producto_id}`: FastAPI resuelve las rutas en orden y, al revés,
«ids» entraría por el detalle y fallaría al leerse como un entero.

## Datos

Tabla **`favorito`**, migración `0005_ciclo3_favoritos` — la **primera tabla propia de P5**. Durante
el Ciclo 2 el paquete solo leía tablas de P3 y P4, y por eso su `models.py` estuvo vacío a propósito.

```
favorito   cliente_id   BIGINT   FK cliente.id ON DELETE CASCADE
           producto_id  BIGINT   FK producto.id ON DELETE CASCADE
           creado_en    TIMESTAMPTZ  default now()
           PK compuesta (cliente_id, producto_id)
           indice (cliente_id, creado_en)
```

**Lleva `creado_en` pero no el mixin `Auditoria`.** `actualizado_en` no significa nada en una fila
que solo se crea y se borra; `creado_en` sí, porque es lo que permite mostrar la lista con lo último
marcado primero. Es la diferencia con `cliente_categoria`, que no tiene atributos y por eso se
declara con `Table(...)` y no con una clase.

**El identificador de la migración se reservó antes de escribirla**, en la §4 de
[`ciclo-2/04-respuesta-de-karen.md`](../ciclo-2/04-respuesta-de-karen.md), que es donde quedó el
acuerdo después de que apareciera una `0004` fuera del esquema original.

## Pantallas

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web · lista | `/tienda/favoritos` | `frontend-web/src/app/features/tienda/favoritos/` |
| Web · corazón | dentro de `/tienda` | `frontend-web/src/app/features/tienda/catalogo/` |

**Sin pantalla móvil todavía.** El *backend* está, así que sumarla es una pantalla y no un caso de
uso — igual que con las preferencias del CU-04.

## Lo que esto deja preparado

`favorito` es la segunda mitad de la **preferencia declarada** que consume el CU-33: la primera es
`cliente_categoria`, del CU-04. Lo que sigue faltando para el recomendador es la preferencia
**observada** —`EventoNavegacion`, el historial de qué miró el cliente—, que también es de P5 y que
se escribe cuando se construya P10: registrar cada vista de producto sin nadie que la consuma sería
una tabla que solo crece.
