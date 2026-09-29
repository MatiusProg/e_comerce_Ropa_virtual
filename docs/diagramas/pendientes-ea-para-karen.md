# Lo que queda por hacer en EA — para Karen

> **Actualización del 29/09: los puntos 1 y 2 ya están resueltos por script.**
> `scripts/ea-fragmentos-3-2.ps1` reubicó las cajas `alt` y `loop` y las notas
> de los 3.2 y dio vuelta las guardas. Se verificó exportando la imagen de
> CU-01, CU-02, CU-21, CU-27 y CU-32. **No arrastrar cajas ni mensajes en EA**:
> EA reparte los mensajes de 35 en 35 sin mirar la altura guardada, y deja
> fijas las cajas y las notas. Mover cualquier cosa corre los mensajes y
> desarma las cajas de abajo. **Los 29 diagramas 3.2 de los tres ciclos** se
> revisaron; 28 quedaron corregidos. **CU-17** se deja como está: su guion
> tiene un `alt` que el modelo no tiene, y se decidió no agregarlo. El punto 3
> también está hecho: se borraron los duplicados 351 y 452 de CU-32.
>
> **Lo que queda es de Mateo: exportar y pasar al documento (punto 4).** Hay
> que reexportar **todos los 3.2**, porque cambiaron todos. Además van el 3.2
> de CU-32, el 2.2 de CU-21, y **el 2.2 y el 2.3 de CU-32 «o cambio»**, que
> tampoco están exportados. Los JPG `2.2 CU-32 Registrar devolución.jpg` y
> `2.3 CU-32 Registrar devolución.jpg` son de los diagramas borrados: hay que
> quitarlos de `comunicacion/`, de `clases/` y del documento.

> **Escrito el 28/09/2026**, la víspera de la defensa. Es la lista de lo que
> hay que **acomodar a mano en Enterprise Architect** sobre
> `VioletBoutique.eapx`. El código ya está; esto es sólo dibujo y exportación.
>
> ⚠ **Trabajar sobre el `.eapx` de la rama `KarenCU12`**, que es el más nuevo
> (ya trae los `loop` de `46c06f0`, el 3.3.1 acomodado y CU-40). El archivo es
> binario y **no se fusiona**: mientras lo tengas vos, nadie más lo toca.

---

## 1. Los 15 `loop` del Ciclo 3 — ya existen, falta acomodar las cajas

El generador (`scripts/ea-secuencia-3-2.ps1 -Fragmentos`) ya **creó** los
fragmentos con su tipo `loop` y su guarda escrita. Lo que salió mal es la
**posición**: las cajas cayeron corridas y no envuelven los mensajes que les
corresponden. Hay que **arrastrar cada caja** hasta que encierre exactamente
lo que dice la tabla.

El detalle completo —qué mensajes, qué líneas de vida, de qué línea de código
sale cada uno y **qué tiene que quedar afuera**— está en
[`loops-3-2.md`](loops-3-2.md). Este es el resumen para ir tachando:

| Diagrama 3.2 | Cajas | Encierra | Guarda |
|---|---|---|---|
| **CU-21** Vestidor virtual (RA) | A | `1.5` y `1.6` (auto-mensajes de `:PantallaVestidor`) | `[por cada fotograma de la cámara]` |
| | B | `2.4a` (auto-mensaje de `:GestorVestidor`) | `[por cada talla de la tabla]` |
| **CU-27** Pedido y pago en línea | A | `1.3` y `1.3.1` | `[por cada sucursal activa]` |
| | B | `2.6a` → `2.8a.1` | `[por cada línea del carrito]` |
| | C | `2.10a` — **sin tragarse `2.9a`** | `[por cada línea del carrito]` |
| | D | `3.3` y `3.4` | `[por cada línea del pedido]` |
| **CU-28** Confirmar pago | 1 | `1.8a` → `1.10a.1` | `[por cada línea del pedido]` |
| **CU-31** Venta presencial | 1 | `1.9a` → `1.11a.1` — **`1.8a` queda afuera** | `[por cada prenda del ticket]` |
| **CU-32** Devolución o cambio | F1 | `1.12a` → `1.14a.1` — **`1.11a` afuera** | `[por cada prenda que vuelve]` |
| | F2-A | `2.10a` | `[por cada prenda que se lleva]` |
| | F2-B | `2.12a` → `2.14a` | `[por cada prenda que vuelve]` |
| | F2-C | `2.15a` → `2.17a.1` — **B antes que C** | `[por cada prenda que se lleva]` |
| **CU-33** Recomendaciones | A | `1.5` | `[por cada producto candidato]` |
| | B | `1.8` | `[por cada sugerencia del modelo]` |
| **CU-34** Asistente virtual | 1 | `1.9` — **`1.10` queda afuera** | `[por cada fila del contexto]` |

**La regla para no equivocarse:** el `loop` va sobre el **controlador y la
tabla**, nunca sobre la pantalla (la única excepción es la caja A de CU-21).
Y un `SELECT` que devuelve muchas filas **no** lleva `loop`.

---

## 2. Los `alt` de TODOS los 3.2 — corridos y con las guardas al revés

Esto afecta **también a los diagramas del Ciclo 1 y 2**, no sólo a los nuevos.

**Por qué pasa:** EA ubica el mensaje k en `-135 - 35·(k-1)` sin dejar huecos,
y lee los operandos de un `alt` **de abajo hacia arriba**. El generador los
escribía pensando lo contrario. Resultado:

1. La caja del `alt` no coincide con sus mensajes → **arrastrarla**.
2. La guarda del primer operando aparece en el segundo y viceversa (p. ej.
   `[credenciales válidas]` sobre el tramo del error) → **intercambiar el
   texto de las guardas** de los dos operandos.
3. Revisar que la **línea divisoria** entre operandos quede entre el último
   mensaje del caso feliz y el primero del alternativo.

Diagramas a revisar: los 3.2 de CU-01 a CU-11, CU-13 a CU-19, CU-21 a CU-25,
CU-27, CU-28, CU-31, **CU-32**, CU-33 y CU-34.

---

## 3. CU-32: lo que le falta

- **Borrar los duplicados 351 y 452**: son el 2.2 y el 2.3 con el nombre viejo
  «CU-32 Registrar devolución» (sin «o cambio»). Quedarse con los que dicen
  «Registrar devolución **o cambio**».
- El **3.2 de CU-32 no está exportado** (no hay JPG en `secuencia/`).
- Ya tiene los retornos punteados y los operandos de sus `alt`; revisar igual
  el punto 2.

---

## 4. Exportar los JPG

Después de acomodar cada diagrama:

1. **Cerrarlo y volver a abrirlo** — EA remaqueta el diagrama de secuencia al
   abrirlo pero **conserva las cajas**, así que se pueden volver a correr.
   Si se corrieron, reacomodar.
2. Recién entonces exportar a `docs/diagramas/secuencia/` con el nombre de
   siempre: `3.2 CU-XX Nombre del caso de uso.jpg`, reemplazando el anterior.

Lo que falta o hay que reexportar:

- **Todos los 3.2** que se toquen por los puntos 1 y 2.
- **3.2 CU-32** (nuevo).
- **2.2 CU-21** Vestidor virtual: no está en `comunicacion/`.

---

## 5. Al terminar

~~Commit en `KarenCU12`~~ → **commit en `KarenDiagramas`** (actualizado el
29/09) con los JPG, y avisar para que nadie abra el `.eapx` viejo mientras
tanto.

`KarenDiagramas` es `main` + los diagramas de `KarenCU12`, **sin** el backend
de CU-40. Ahí está el `.eapx` más nuevo: el de `KarenCU12` quedó atrás, porque
todavía tiene los duplicados de CU-32 y las cajas corridas.

---

## 6. Después de la defensa: todo esto sube a `main`

**Instrucción de Karen (29/09): después de la defensa, todos estos cambios se
suben a `main`.** El orden importa, por el `.eapx`:

1. **Primero `KarenDiagramas` → `main`**, con un PR, incluidos los JPG que
   exporte Mateo. Trae el `.eapx` bueno, el script `ea-fragmentos-3-2.ps1` y
   la guía al día. No toca backend ni web, así que no tiene riesgo para
   producción.
2. **Después, CU-40 (`KarenCU12`, PR #70)**, cuando se decida subirlo. Al
   mergear, el `.eapx` va a dar conflicto: **hay que quedarse con el de
   `main`**. `KarenCU12` trae una versión más vieja y pisaría todo lo de
   arriba:

       git checkout --ours docs/diagramas/VioletBoutique.eapx   # (parado en main o en la rama que recibe)

   Antes de resolver, medir qué tiene cada lado, como dice la guía
   (`GUIA-DIAGRAMAS-EA.md`): por ejemplo, que `main` **no** tenga los
   diagramas 351 y 452.
3. CU-40 trae la migración `0021`. Al desplegarlo hay que correr Alembic en
   Railway y poner las variables de correo (SMTP). El puerto 587 en Railway
   nunca se probó.

> **Ojo:** el PR #70 (`KarenCU12`) también trae el **código de CU-40** con la
> migración `0021`. Se acordó **no subir CU-40 a producción** antes de la
> defensa, así que ese PR **no se mergea tal cual**: los diagramas y el
> `.eapx` tienen que pasar a `main` sin el backend de CU-40.
