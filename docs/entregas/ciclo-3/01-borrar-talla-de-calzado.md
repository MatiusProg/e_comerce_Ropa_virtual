# La tienda no vende zapatos: fuera `cliente.talla_calzado`

> Cambio de esquema del Ciclo 3, hecho el **17/09/2026**. No realiza ningún caso
> de uso: corrige uno que arrastraba desde el Ciclo 1.

## Qué pasaba

`cliente.talla_calzado` existe desde la migración `0001` y **nunca apuntó a
nada**:

- no hay un solo tipo `CALZADO` en la tabla `talla`;
- no hay un solo producto de calzado en el catálogo, ni sembrado ni en producción;
- ningún caso de uso lee el campo para recomendar, filtrar ni vender.

La consecuencia es que **el perfil del cliente pedía una talla de calzado para
una tienda sin zapatos**: un selector del 35 al 44 que no se cruza con nada.

Aclarado el 13/09: el negocio es principalmente **ropa femenina**. Puede haber
una categoría de varón a futuro; calzado no está en el alcance.

## Se pierden datos, y es a propósito

En producción hay **501 clientes con un valor escrito** en esa columna. Son
números que el formulario les hizo elegir y que el sistema nunca usó. Al quitar
la columna se van.

El `downgrade` **no los devuelve**: vuelve a crear la columna vacía. Recuperarlos
exigiría haberlos copiado a otro lado antes, y copiar un dato que se decidió no
usar es quedarse con el problema con otro nombre.

> Si alguna vez la tienda vende zapatos, la talla de calzado va a ser **una fila
> de `talla` con tipo `CALZADO`** —como todas las demás— y no una columna suelta
> en `cliente`. Es la forma que el resto del catálogo ya usa.

## La cadena de Alembic se movió otra vez — para Mateo

Es la **tercera** vez en este ciclo, así que otra vez: *Alembic no mira el número
del archivo, mira `down_revision`.*

Cuando este borrado se anotó, la migración iba a ser la `0009`. Ya no: la `0009`
la tomó el carrito. El `0007` sigue reservado para las promociones (CU-12), así
que a ésta le tocó el **`0010`**, colgando de la `0006` de ventas.

```python
# 0007_ciclo3_promociones
down_revision = "0010_ciclo3_sin_calzado"
```

La cadena queda `0005 → 0008 → 0009 → 0006 → 0010 → 0007`. Se lee raro y es
correcta.

## No era aditivo: ocho puntas

Medido el 17/09.

| | Punta | Estado |
|---|---|---|
| 1 | Migración `0010_ciclo3_sin_calzado` | hecha |
| 2 | Modelo `Cliente` (`seguridad/models.py`) | hecha |
| 3 | Los dos esquemas de CU-04 y su validador (`seguridad/schemas.py`) | hecha |
| 4 | El servicio de perfil, salida y campos borrables (`seguridad/service.py`) | hecha |
| 5 | El sembrado, constante y uso (`db/seed_operacion.py`) | hecha |
| 6 | La prueba de CU-04 (`tests/test_cu04_perfil.py`) | hecha |
| 7 | La web: modelo, formulario y selector | hecha |
| 8 | Los tres scripts de EA (`ea-datos-3-3-1`, `ea-datos-3-3-1-ciclo2.datos`, `ea-clases-2-3`) | hechas |
| 9 | **El móvil** | **pendiente — es de Mateo** |

### Por qué el móvil queda pendiente y no rompe nada

Toca `mobile/lib/data/modelos/perfil.dart`,
`features/perfil/pantalla_perfil.dart` y `features/perfil/formularios_perfil.dart`
—los tres de CU-04 móvil, que es de Mateo, y **los está tocando ahora** con la
parte móvil de CU-27—. Editarlos desde acá sería un conflicto seguro.

**Mientras tanto no se rompe**, y conviene saber por qué: Pydantic **ignora los
campos que sobran**. Un móvil que siga mandando `talla_calzado` en el `PATCH`
recibe un 200 y el campo se descarta en silencio. Lo único que se ve es una fila
vacía en su pantalla de perfil, donde antes decía «Calzado».

Lo que hay que quitar allá:

- `perfil.dart`: el campo `tallaCalzado` del modelo, su lectura del JSON, su
  escritura, y el `required this.tallaCalzado` de `PerfilActualizar`.
- `pantalla_perfil.dart:229`: la fila `_Dato(rotulo: 'Calzado', ...)`.
- `formularios_perfil.dart`: el controlador `_calzado` y su envío.

### Tres documentos viejos siguen nombrando la columna

No se tocaron, y es deliberado: **son el registro de lo que se entregó en su
momento**, y reescribirlos sería falsear lo que aquellos ciclos presentaron.

| Documento | Dónde |
|---|---|
| `ciclo-1/cap-2-3-analisis-y-diseno.md` | línea 338, en el DDL de `cliente` |
| `ciclo-2/00-organizacion-por-caso-de-uso.md` | línea 345 |
| `ciclo-2/cu-04-categorias-preferidas.md` | línea 106 |

**Para quien arme el documento consolidado del 20/09:** si esos fragmentos se
copian tal cual, el documento va a mostrar una columna que ya no existe. O se
citan como historia —diciendo que el Ciclo 3 la quitó— o se actualizan junto con
los diagramas reexportados. Conviene decidirlo antes de la defensa y no durante.

### Los diagramas hay que reexportarlos

Los tres scripts de EA ya no declaran la columna, pero **los PNG y JPG del
repositorio siguen mostrándola**: se generan corriendo los scripts contra
Enterprise Architect, y eso se hace en la máquina de Mateo.

Afecta al diagrama de datos (3.3.1, ciclos 1 y 2) y al de clases (2.3). Es lo que
había que coordinar antes de borrar, y por eso se esperó a que cerrara sus
diagramas.

## Verificación

- `alembic heads` → **una sola cabeza**, `0010_ciclo3_sin_calzado`.
- `upgrade head` sobre una base limpia: la cadena entera aplica.
- `alembic check` → **«No new upgrade operations detected»**: los modelos y las
  migraciones coinciden.
- `downgrade -1` devuelve la columna nullable y vacía; `upgrade` la vuelve a
  quitar. Ida y vuelta comprobadas contra PostgreSQL.
- `test_cu04_perfil.py` y `test_cu04_preferencias.py`: **34 pasan**. La prueba de
  las tallas ahora afirma que `talla_calzado` **no está** en la respuesta.
- La web compila limpia.
