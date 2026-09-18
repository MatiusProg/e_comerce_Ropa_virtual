# CU-21 · Cómo se carga una prenda del vestidor virtual

Guía operativa, no de diseño. Es lo que hay que hacer para que una prenda del
catálogo se pueda probar en el vestidor, y por qué cada paso es como es.

> **Escrita el 17/09/2026**, al descubrir que las prendas que el vestidor
> mostraba eran siluetas planas generadas por el *seed*, y que 10 de las 32
> prendas probables no aparecían nunca en la pantalla.

---

## 1. La regla que no se deduce mirando el PNG

`mobile/lib/features/vestidor/pantalla_vestidor.dart` coloca la prenda así:

```dart
ancho = distancia entre hombros * 2.1      // _anchoRespectoAHombros
top   = centro de hombros - ancho * 0.18   // _subida
```

De ahí salen **tres condiciones que el archivo tiene que cumplir**, y ninguna
se ve abriendo la imagen:

| | Por qué |
|---|---|
| **La línea de los hombros va a `0.18 × ancho del PNG` desde el borde superior** | Si está más abajo, la prenda cuelga del cuello. Con 600 px de ancho, la línea va en `y = 108`. |
| **La prenda ocupa todo el ancho del PNG y está centrada** | El alto se ajusta con `BoxFit.contain`. Si el archivo tiene márgenes laterales, la prenda sale más chica que el cuerpo. |
| **El alfa tiene borde suave**, no escalonado | En la cámara, un borde dentado se lee como un recorte mal hecho. Se consigue dibujando o exportando al doble o cuádruple de tamaño y reduciendo. |

**El alto es libre.** Lo que fija la escala es el ancho.

---

## 2. Los tres pasos, y qué valida cada uno

Todo pasa por la API de **CU-11**, que ya existía. No hace falta tocar el disco
ni la base a mano.

### Paso 1 · Subir el archivo, asociado a la variante

```
POST /api/v1/catalogo/productos/{producto_id}/imagenes?variante_id={variante_id}
      multipart/form-data, campo `archivo`
      rol: ADMINISTRADOR
```

**`variante_id` no es opcional acá.** El PNG del vestidor es de una *variante*
—talla y color concretos— por la decisión **D1**. Una silueta «del producto»,
sin talla ni color, es una figura que no existe: el vestidor no sabría qué
color pintar.

Valida: **máximo 5 MB** y **máximo 4000 px de lado** (`imagenes_almacen.py`).

> Al subir, la imagen queda registrada con `es_transparente = false` **aunque el
> archivo tenga alfa**. La transparencia no se declara: se marca después, en el
> paso 2. Es deliberado — una foto de catálogo con fondo recortado no es lo
> mismo que un activo de realidad aumentada.

### Paso 2 · Marcarla como la prenda del vestidor

```
PATCH /api/v1/catalogo/imagenes/{imagen_id}/transparente
      {"es_transparente": true}
      rol: ADMINISTRADOR
```

**Esto no es una formalidad: el backend relee el archivo del disco y comprueba
que tenga transparencia de verdad.** Un JPG, o un PNG sin canal alfa, se
rechaza. Está bien que así sea: un PNG opaco en el vestidor se ve como un
rectángulo tapando a la persona.

**Una variante tiene un solo PNG de vestidor.** Lo garantiza el índice parcial
`uq_imagen_transparente_variante`, y marcar uno nuevo desmarca el anterior
solo. Así que **volver a cargar una prenda es simplemente repetir los dos
pasos**: no hay que borrar nada.

### Paso 3 · Comprobar que aparece

```
GET /api/v1/tienda/productos?solo_vestidor=true
```

Devuelve exactamente las prendas probables. Si la recién cargada no está, algo
falló en el paso 2.

---

## 3. El filtro `solo_vestidor`, y el defecto que arregla

Se agregó el 17/09 y **es de CU-21, no de la vitrina**.

Antes no existía, así que el vestidor pedía la primera página de 48 productos y
filtraba por `tiene_vestidor` en el teléfono. Medido contra el dataset de
demostración:

| | |
|---|---|
| Prendas probables | **32** |
| Que el prototipo veía | 22 |
| Que **no aparecían nunca** | **10** — las de identificadores 1 a 10 |

Con el orden por novedades (`id` descendente), las diez más viejas caen fuera
de la primera página. Y **cuáles caen ahí cambia cada vez que se agrega un
producto**, así que el defecto aparecía y desaparecía solo.

El filtro es **opt-in**: sin declararlo, la vitrina devuelve todo. Hay una
prueba dedicada a eso, porque se agregó a una consulta que ya estaba en uso y
si por omisión recortara, la vitrina entera se vaciaría el día que nadie haya
cargado PNG transparentes.

---

## 4. De dónde salen las prendas hoy, y qué habría que mejorar

### Lo que siembra el *seed*

`seed_catalogo._png_transparente_de_variante(color_hex)` dibuja **un rectángulo
de color liso con hombros rectos**. Cumple el supuesto **S5** —«hay un PNG con
alfa»— y nada más. En la cámara se ve como un cartel pegado encima del cuerpo,
y es la razón por la que el vestidor «se ve chafa» aunque la realidad aumentada
funcione bien.

### Lo que se cargó el 17/09

Dos prendas dibujadas con volumen —silueta curva, escote recortado, mangas con
puño, sombreado lateral, costuras y borde suave—, en el color real de su
variante:

| Producto | Variante | Prenda |
|---|---|---|
| 1 · Blusa de seda manga larga | 4 · S · Rojo vino | manga larga, `#722F37` |
| 4 · Blusa de gasa | 36 · M · Malva | manga corta, `#8E6C88` |

Se cargaron **por la API**, con los tres pasos de arriba. Las demás variantes
de esos mismos productos conservan la silueta vieja **a propósito**: sirve para
comparar las dos en la defensa.

El generador está en el *scratchpad* de la sesión y **no se versionó**: es una
herramienta de relleno, no parte del sistema.

### Lo que sigue siendo deuda

**Siguen siendo dibujos, no fotos de ropa.** Para la defensa, lo que mejor se
ve es una **foto real del producto recortada con fondo transparente**:

1. Foto de la prenda **de frente y estirada** (no sobre percha, que deforma los
   hombros).
2. Recortar el fondo. Cualquier herramienta de quitar fondo sirve; lo que
   importa es que el resultado tenga **alfa de verdad**, no un blanco.
3. Encuadrar respetando la §1: hombros al 18 % del ancho, prenda centrada y a
   todo lo ancho.
4. Exportar **PNG** (no JPG: no tiene canal alfa).
5. Subirla con los tres pasos de la §2.

> ⚠️ **Ojo con el origen de las imágenes.** Si se usan fotos de catálogos
> ajenos, hay que poder justificarlas. Lo más limpio para un trabajo académico
> es fotografiar prendas propias, o usar bancos con licencia explícita y
> citarlos en los anexos.

---

## 5. Lo que falta en Railway, y es urgente

**En local está completo**: las 79 siluetas del *seed* más las 2 prendas nuevas
existen y se sirven.

**En Railway falta la mayoría.** De 10 rutas probadas el 17/09, **8 devolvieron
404**: el volumen persistente quedó a medio llenar. Si la defensa corre contra
Railway, el vestidor va a mostrar prendas vacías casi siempre.

Se arregla **volviendo a correr el *seed* de catálogo contra Railway**, o
subiendo las imágenes por la API apuntando a ese entorno. Es independiente de
escribir CU-21 y conviene hacerlo antes.

---

## 6. Qué NO bloquea a CU-21

- **CU-20 (favoritos)** no lo toca. La ficha de CU-21 dice «agregar la prenda a
  la **reserva o al carrito**», y las dos costuras ya existen: CU-22 desde el
  Ciclo 2 y CU-26 desde el 17/09.
- **La tabla `SesionVestidorVirtual`** que declara la §4.2 de la arquitectura
  **tampoco bloquea**: registra la sesión de prueba, no la habilita. Se dejó
  sin escribir el 17/09 a propósito, para no abrir una migración mientras otra
  persona estaba trabajando en el backend —dos migraciones simultáneas dejan el
  árbol con dos cabezas—. Queda pendiente y es lo único de P9 que falta del
  lado del servidor.
