# Respuesta de Mateo sobre la paginación de existencias — 13/09/2026

Respuesta al aviso de Karen sobre `GET /api/v1/inventario/existencias`.

**Resumen: tenías razón en los cuatro puntos, está arreglado en este PR, y el
orden es al revés del que proponías — primero el arreglo, después el dataset.**

---

## 1. El orden: arreglar primero

Proponías cargar el dataset antes para tener las 3.424 filas reales, porque «con
la base vacía no podés verificarlo». Eso ya no es cierto: **corrí
`seed_operacion` en local** al revisar el PR anterior, así que tengo 2.351
existencias y 5.689 movimientos para probar sin tocar Supabase.

Y hay un motivo para no invertirlo: el dataset es justamente lo que vuelve la
pantalla inservible. Cargarlo primero sería romper a propósito la base que el
tribunal puede estar mirando, y después correr contra el reloj para arreglarla,
con el congelamiento hoy a las 18:00. Sembrar producción es el último paso,
cuando el código que tiene que sobrevivirlo ya está puesto.

---

## 2. Lo que encontré al mirarlo

Los cuatro puntos que señalaste son exactos:

| | |
|---|---|
| `listar_existencias` no acepta `pagina` ni `tamano` | Cierto: devolvía `list[ExistenciaOut]` |
| La tabla pinta la lista entera | Cierto: `<table [dataSource]="existencias()">` |
| El patrón ya está al lado | Cierto: `/ingresos` y `/movimientos` ya paginan igual |
| El selector de origen de la transferencia se alimenta de esa lista | Cierto: `transferir()` le pasa `this.existencias()` |

Y el aviso sobre `inventario_consolidado` estaba bien puesto: CU-14 calcula su
resumen sobre **todo lo filtrado antes de paginar**, así que paginar la costura
le daría el resumen de la página. **No la toqué.**

**Apareció un quinto punto que no estaba en tu lista:** el panel de CU-16
—`features/sucursal/disponibilidad`— llama al mismo endpoint y también dibujaba
todo. Son ~470 filas por sucursal, no 3.424, pero es el mismo problema un orden
de magnitud más abajo. Su filtro por texto además se resolvía en el cliente, con
un comentario que lo justificaba diciendo que «una sucursal maneja decenas o
pocos cientos de existencias, ya vienen todas». Con el listado paginado eso
dejaba de valer: filtrar en el cliente buscaría dentro de veinte filas y diría
que no hay nada. **El filtro pasó al servidor.**

---

## 3. Lo que hace este PR

**Backend.** `GET /inventario/existencias` pagina con `pagina` y `tamano`, igual
que sus dos vecinos, y devuelve `PaginaExistencias` con `total`. Se agregó
`busqueda`, que alcanza al SKU y al nombre de la prenda: con miles de filas,
llegar a una concreta paginando de a veinte no es viable.

La paginación va en una **función de servicio nueva**, `listar_existencias`, no
en `inventario_consolidado`. En el repositorio, `limite` y `desplazamiento` son
opcionales y por omisión no se aplican, así que la costura C1 sigue devolviendo
el conjunto completo. El conteo y el listado comparten los filtros en
`_filtrar_existencias`: si contaran distinto, el paginador mostraría un total que
no se corresponde con lo que se ve.

**Frontend.** Las dos pantallas paginan y buscan contra el servidor. El diálogo
de transferencia **tiene ahora su propio buscador**: cuando se abre desde el
botón general —sin fila de partida— ya no depende de la página que el usuario
estuviera mirando. Cuando se abre desde una fila, el origen sigue viniendo
fijado y el buscador no aparece.

---

## 4. Lo que verifiqué, y lo que no

**Verificado:**

- **333 pruebas en verde.** El cambio de contrato rompió 42: ocho archivos de
  prueba leían la respuesta como lista. Están adaptadas —leen `["items"]` y piden
  `tamano` suficiente para que ningún escenario se quede corto con el tamaño de
  fábrica, que es 20—.
- **La web compila** (`ng build`), con los cuatro archivos de pantalla tocados.

**No verificado:** no lo vi funcionando en un navegador. De este lado tampoco hay
uno. Lo que puedo afirmar es el contrato y que compila; que 3.424 filas ya no
llegan al navegador se sigue de que el endpoint devuelve veinte.

---

## 5. Entonces, el orden

1. **Merge de este PR.**
2. **Sembrar la desplegada**, con el `git pull` previo por el arreglo del
   retrofechado del PR anterior, y en una ventana en la que nadie esté usando la
   aplicación.
3. **Mirar las dos pantallas con los datos reales.** Ahí sí hace falta el
   navegador, y ahí se ve si veinte filas por página es el número correcto.

**Sobre la RA:** gracias, la pruebo contra el despliegue en cuanto cierre los
diagramas. Que los 59 PNG tengan canal alfa real y vengan por variante en
`imagen_vestidor_url` es exactamente lo que el prototipo necesita para no tener
que adivinar nada.
