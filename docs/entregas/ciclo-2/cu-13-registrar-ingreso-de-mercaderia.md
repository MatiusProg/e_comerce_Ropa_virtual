# CU-13 · Registrar ingreso de mercadería

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)) y que las de
> CU-10 y CU-11. Un archivo por caso de uso, por el mismo motivo que explica
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-13 |
| **Nombre** | Registrar ingreso de mercadería |
| **Descripción** | Permite al Administrador o al Encargado registrar la recepción de prendas enviadas por un proveedor a una sucursal, generando el movimiento de inventario de tipo ingreso. |
| **Propósito** | Es la única puerta por la que entra stock al sistema. Sin ella no hay existencias, y sin existencias no hay vitrina, ni disponibilidad, ni reserva. |
| **Actores** | Administrador (iniciador) · Encargado de Sucursal (iniciador, solo sobre su sucursal) |
| **Paquete** | P4 · Inventario |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF22, RF27 (y RF06 en la parte de procedencia) |
| **Precondiciones** | El usuario tiene sesión iniciada. Existen la sucursal activa que recibe, el proveedor activo que envía y al menos una variante activa (CU-05, CU-07, CU-10). |
| **Postcondiciones** | La existencia de cada variante en esa sucursal queda aumentada, y por cada línea queda un `movimiento_inventario` de tipo `INGRESO` con su proveedor, su remito, su usuario y su fecha. |

**Flujo principal**

1. El usuario ingresa a *Inventario*.
2. El sistema muestra las existencias con su cantidad disponible, reservada y física, y el historial de ingresos ya registrados, del más reciente al más viejo.
3. El usuario elige registrar un ingreso.
4. El sistema presenta el formulario del remito: proveedor, sucursal que recibe, número de remito y observación.
5. El usuario busca cada producto por código o nombre, elige la combinación de talla y color, indica cuántas unidades llegaron y la agrega al remito. Repite por cada prenda del envío.
6. El usuario confirma el ingreso.
7. El sistema valida el remito completo, aumenta la cantidad disponible de cada variante en esa sucursal y registra un movimiento de tipo `INGRESO` por cada línea, todo en una sola transacción. Devuelve el comprobante con el saldo que quedó en cada prenda.

**Flujos alternativos**

- **2a. Consultar un ingreso del historial.** El usuario despliega una fila y el sistema muestra las líneas de ese ingreso.
- **4a. Encargado.** La sucursal no se elige: es la suya y el sistema la impone.
- **5a. Quitar una línea.** El usuario retira del remito una prenda que había agregado, antes de confirmar.
- **7a. Prenda nueva en esa sucursal.** Si es la primera vez que esa variante llega a ese local, el sistema crea su existencia en cero y el ingreso la sube.

**Excepciones**

- **E1. Prenda inexistente o desactivada.** El sistema impide el ingreso y señala **qué líneas** del remito son las que fallan, sin invalidar el resto.
- **E2. Sucursal dada de baja.** No entra mercadería a una sucursal inactiva.
- **E3. Proveedor dado de baja.** Un proveedor inactivo no puede enviar mercadería.
- **E4. Prenda repetida en dos líneas.** El sistema lo impide y pide unificarlas en una sola con la cantidad total.
- **E9. Fallo a mitad del remito.** Si una línea falla, no queda registrada ninguna.
- **Ámbito.** Un Encargado que intente cargar mercadería en una sucursal que no es la suya recibe un rechazo y no se escribe nada.

---

## Lo que no se lee en la ficha

**No hay tabla `ingreso`, y es una decisión, no un olvido.** Un remito es una cabecera con varias
líneas, y la primera intención es modelarlo con dos tablas. La §3 del acuerdo del ciclo congeló el
Ciclo 2 en ocho tablas nuevas, y una cabecera de ingreso sería la novena — con dos personas
discutiendo el mismo esquema a mitad de ciclo. En su lugar el ingreso **se reconstruye** desde sus
propios movimientos: las líneas comparten `proveedor_id`, `referencia`, `usuario_id` y `creado_en`,
y ese último las agrupa sin ambigüedad aunque no se haya cargado un remito, porque `now()` en
PostgreSQL devuelve el instante de la **transacción** y no el de cada fila.

El precio es que no se puede anular «el ingreso» de un tiro, solo corregirlo con un `AJUSTE` — que
es como se corrige cualquier otra cosa en esa tabla, por la decisión **D4**. Si en el Ciclo 3 la
recepción crece —estados, recepción parcial, costo por línea—, ahí sí merece su cabecera.

**`movimiento_inventario` estrenó dos columnas: `proveedor_id` y `referencia`.** Son aditivas y
sobre una tabla propia, así que la §6.4 no exige avisar; se anotan igual acá porque cambian lo que
el modelo puede responder. Sin ellas, la procedencia de un lote viviría solo en el texto del motivo,
y `producto.proveedor_id` —que es de quien provee el **modelo**— no sirve para saber de dónde vino
**este** envío: un mismo producto puede llegar de dos proveedores distintos.

**El remito viaja entero, en una sola petición.** Aceptar las líneas de a una simplificaría el
formulario y rompería la excepción E9: si se corta la conexión en la línea catorce, el depósito no
tendría cómo saber por dónde iba. Con una transacción, se vuelve a intentar entero.

**La existencia se toma con `SELECT ... FOR UPDATE`.** Es el mismo bloqueo del riesgo **R5**,
aplicado en chico: dos personas registrando ingresos de la misma prenda al mismo tiempo leerían el
mismo saldo, sumarían cada una lo suyo, y la segunda pisaría a la primera —10 + 5 + 5 daría 15 en
vez de 20—.

**El servidor devuelve *qué* variantes rechazó, no solo que hubo un error.** Es lo que permite que
la pantalla marque las dos líneas malas de un remito de diecisiete en vez de obligar a cargarlo
entero de nuevo. Por eso ese 422 lleva un objeto y no un texto.

## Endpoints

| Método | Ruta | Paso |
|---|---|---|
| `POST` | `/inventario/ingresos` | 4-7 · registrar el remito completo |
| `GET` | `/inventario/ingresos` | 2 · historial agrupado, paginado |
| `GET` | `/inventario/ingresos/detalle` | 2a · líneas de un ingreso |
| `GET` | `/inventario/existencias` | 2 · saldos con la prenda y la sucursal resueltas |

Todos exigen rol **Administrador o Encargado**, declarado una sola vez en `operacion_router`. El
ámbito de sucursal del Encargado no lo resuelve el rol sino `verificar_ambito_sucursal`, porque la
sucursal viaja dentro del token y no en el cuerpo de la petición.

## Pantallas

| Plataforma | Ruta | Rol |
|---|---|---|
| Web | `/admin/inventario` | Administrador |
| Web | `/sucursal/inventario` | Encargado |
| Móvil | — | El actor no es Cliente: es solo web (§2.2 del acuerdo) |

Es la **misma** pantalla para los dos roles. El alcance no lo decide la ruta sino el servidor, y las
acciones de CU-15 se ocultan para el Encargado: ofrecer un botón que devuelve 403 es una promesa que
la interfaz no puede cumplir.

## Pruebas

`backend/tests/test_cu13_ingresos.py` — 17 pruebas. Las que cubren lo que la base **no** garantiza
por sí sola:

- `test_excepcion_e9_si_una_linea_falla_no_queda_cargada_ninguna` — la transacción, que no la impone
  ninguna restricción de PostgreSQL sino un único `commit` al final.
- `test_el_saldo_es_la_suma_de_sus_movimientos` — la decisión **D4**, comprobada literalmente. Es lo
  que garantiza que la existencia desnormalizada no se despegue del historial.
- `test_el_encargado_no_carga_mercaderia_en_otra_sucursal` — el ámbito viaja en el token, no en el
  JSON.
- `test_las_lineas_de_un_ingreso_se_agrupan_en_una_sola_fila` — que la reconstrucción del ingreso sin
  tabla propia separe dos ingresos distintos y una las líneas de uno solo.
