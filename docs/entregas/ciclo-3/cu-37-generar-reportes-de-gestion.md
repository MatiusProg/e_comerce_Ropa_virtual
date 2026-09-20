# CU-37 · Generar reportes de gestión

> **Escrita el 19/09/2026.** Realiza el **RF36** —«exportar los reportes en
> formato PDF y Excel»—, que hasta hoy no lo cubría nadie: CU-36 muestra los
> indicadores en pantalla y ahí terminaba.

---

## 1. Los seis reportes

| Tipo | Qué lista | Período |
|---|---|---|
| `ventas` | Cada venta consumada, con canal, estado, método de pago y total | sí |
| `inventario` | Saldos por variante y sucursal | **no** |
| `movimientos` | Cada entrada y salida de inventario, con quién la hizo | sí |
| `reservas` | Reservas por franja, estado y cliente | sí |
| `rendimiento` | Ventas, unidades e importe por temporada y colección | sí |
| `compras` | Ingresos de mercadería agrupados por proveedor | sí |

**El inventario no lleva período a propósito.** Un inventario es una *foto de
ahora*, no un acumulado: los saldos se mantienen desnormalizados y solo tienen
el valor actual. Pedirle fechas sería prometer un saldo histórico que la tabla
no guarda.

## 2. Un exportador, no doce funciones

Seis reportes por dos formatos son doce funciones que dibujan tablas si se
escriben por separado — y las doce terminan viéndose distinto: una pone el
total en negrita y otra no, una escribe la fecha de una forma y otra de otra.
Peor: arreglar el ancho de una columna hay que hacerlo doce veces.

`exportador.py` tiene **dos** funciones. Cada reporte solo declara qué filas
tiene y cómo se llaman sus columnas; el resto es común.

### Lo que el formato cambia, y por qué

| | PDF | Excel |
|---|---|---|
| Orientación | **apaisado** — estos reportes tienen entre 5 y 8 columnas, y en A4 vertical el texto se parte | — |
| Encabezado | se **repite en cada página** (`repeatRows=1`); sin eso, desde la hoja 2 no se sabe qué es cada columna | congelado, con filtros puestos |
| Números | texto formateado | **números de verdad** |

Lo último es la razón de ser del Excel: quien lo pide lo pide para sumar,
filtrar y hacer una tabla dinámica. Si los importes fueran texto —«1.234,56»—
no se podría hacer nada de eso, y el archivo sería un PDF con otra extensión.

## 3. Decisiones que no se ven pero se notan

**El alcance siempre se imprime.** Bajo el título van el período y la
sucursal. Un PDF de ventas sin eso es un papel que no se puede archivar:
dentro de un mes nadie sabe de cuándo es ni de dónde.

**El último día del período entra entero.** `hasta` es inclusivo para quien
pide, y por dentro se convierte en «< el día siguiente». Comparar `<= hasta`
contra marcas de tiempo deja fuera todo lo que pasó ese día después de
medianoche — es el defecto clásico de los reportes por fecha, y hay una prueba
que lo fija.

**Solo cuentan las ventas consumadas** (`PAGADA` y `ENTREGADA`). Una
`PENDIENTE_PAGO` todavía no vendió nada y una `CANCELADA` no vendió nunca.
Es el mismo criterio que usa el tablero de CU-36: con criterios distintos, los
dos números se contradirían y nadie sabría cuál creer.

**Un reporte vacío no es un error.** En un período sin movimiento no pasó
nada, y el archivo lo dice con todas las letras en vez de entregar una hoja
con encabezados sueltos que se lee como que algo falló.

**La extensión va en la ruta** (`/reportes/ventas.pdf`, no
`?formato=pdf`): así el navegador y el sistema operativo saben qué es sin
mirar las cabeceras, y al guardarlo el archivo ya se llama como debe.

## 4. Quién puede, y sobre qué

```
GET /api/v1/reportes/catalogo          qué reportes hay y qué columnas trae cada uno
GET /api/v1/reportes/{tipo}.{pdf|xlsx}?desde=&hasta=&sucursal_id=
```

**ADMINISTRADOR y ENCARGADO.** Pero al encargado **se le fuerza su sucursal**
en vez de confiar en el parámetro: sin eso, quitar `?sucursal_id=` de la URL
le daría los números de toda la red, y un reporte de ventas es exactamente el
dato que no corresponde que vea de las demás. Hay dos pruebas sobre esto, una
de ellas mandando el parámetro a mano.

`/catalogo` existe para que la pantalla no tenga la lista escrita a mano: si
se agrega un reporte, aparece solo. Sin eso, agregar el séptimo obliga a tocar
el backend y la web, y alguien se olvida de la segunda mitad.

## 5. Lo que queda pendiente

- **La pantalla.** Por el reparto del plan, CU-37 es «Mateo (API) · Karen (UI
  y gráficos)».
- **Agrupar con subtotales** —por ejemplo ventas por sucursal con un subtotal
  cada una— se resuelve armando las filas ya agrupadas. El exportador no lo
  hace: meter agrupación ahí lo convertiría en un motor de informes, que es
  mucho más de lo que el caso de uso pide.

## 6. Dos defectos que aparecieron escribiéndolo

Las consultas tienen entre tres y siete JOIN, y un nombre de columna
equivocado no se nota hasta que alguien pide *ese* reporte. Aparecieron dos al
ejecutarlas contra el modelo:

- **`Reserva` no tiene columna `codigo`** —se identifica por id— y su
  `cliente_id` apunta a `cliente`, no a `usuario`: el correo está un salto más
  allá.
- **`DetalleVenta` no guarda `subtotal`**: tiene cantidad, precio unitario y
  descuento unitario. El subtotal es dato derivado, y guardarlo permitiría que
  contradijera a los tres de los que sale.

Por eso las 22 pruebas ejecutan **las doce combinaciones** de reporte y
formato: es lo que impide que un reporte roto llegue a una defensa.
