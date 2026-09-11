# CU-16 · Gestionar disponibilidad de la sucursal

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)). Un archivo por
> caso de uso, por el mismo motivo que explica
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-16 |
| **Nombre** | Gestionar disponibilidad de la sucursal |
| **Descripción** | Permite al Encargado consultar y ajustar la disponibilidad de las prendas de su propia sucursal y consultar sus alertas de stock bajo. |
| **Propósito** | Darle al responsable de un local las tres cosas que necesita sobre su stock: saber qué tiene, corregirlo cuando no coincide con la realidad, y enterarse de lo que hay que reponer **antes** de que se acabe. |
| **Actores** | Encargado de Sucursal (iniciador) · Administrador (con alcance a toda la red) |
| **Paquete** | P4 · Inventario |
| **Prioridad** | Media |
| **Requisitos que realiza** | RF21, RF22 |
| **Precondiciones** | El Encargado tiene sesión iniciada y su cuenta está vinculada a una sucursal (CU-06). |
| **Postcondiciones** | El umbral de reposición de la prenda queda fijado, y cada corrección de saldo deja su `movimiento_inventario` de tipo `AJUSTE`. |

**Flujo principal**

1. El Encargado ingresa a *Disponibilidad*.
2. El sistema muestra, arriba y separadas, las prendas que llegaron a su punto de reposición —de la más urgente a la menos— y, abajo, el listado completo de su sucursal con la cantidad disponible, la reservada, la que hay en el local y el umbral de cada una.
3. El Encargado elige una prenda y fija cuándo quiere que le avise.
4. El sistema muestra cuántas unidades disponibles hay hoy y le advierte si el umbral elegido deja la prenda en alerta desde ese mismo momento.
5. El Encargado confirma y el sistema guarda el umbral. La prenda entra o sale del panel de alertas según corresponda.

**Flujos alternativos**

- **2a. Buscar.** El Encargado filtra el listado por SKU, prenda, talla o color.
- **2b. Ver también las agotadas.** Por defecto se muestran todas; el filtro permite quedarse solo con las que tienen saldo.
- **3a. Ajustar por conteo físico.** El Encargado corrige el saldo de una prenda de su sucursal. Es la misma operación de CU-15, acotada a su local.
- **3b. Dejar de vigilar una prenda.** Un umbral de cero apaga la alerta y la prenda desaparece del panel.
- **5a. Reposición.** Cuando un ingreso (CU-13) sube el saldo por encima del umbral, la alerta se apaga sola.

**Excepciones**

- **E1. Sucursal ajena.** Un Encargado que intente ajustar o fijar el umbral de una prenda de otra sucursal recibe un rechazo, y nada se escribe.
- **E2. Umbral negativo.** No se acepta: cero ya significa «sin alerta».
- **E3. Existencia inexistente.** Fijar el umbral de una existencia que no existe devuelve 404.
- Las excepciones **E7** (conteo sin diferencia) y **E8** (conteo menor que lo reservado) de CU-15 aplican igual, porque el ajuste es el mismo.

---

## Lo que no se lee en la ficha

**El umbral no existía y hubo que crearlo.** `existencia` estrena `stock_minimo` en la migración
`0004`. Sin él, la promesa de «alertas de stock bajo» que traen la descripción del caso de uso y la
§5 del plan no tenía contra qué compararse: no había ningún número en el sistema que dijera cuándo
una prenda está por acabarse.

**Va por existencia y no como una constante del sistema.** El punto de reposición no es una
propiedad del sistema sino del par (prenda, sucursal): de una camiseta negra básica la sucursal del
centro necesita veinte, y de un vestido de fiesta, dos. Un umbral único llenaría la pantalla de
alertas falsas sobre los vestidos y no avisaría nunca de las camisetas — que es exactamente al
revés de para lo que sirve una alerta.

**Cero significa «sin alerta», y es el valor por defecto a propósito.** Una existencia recién creada
por un ingreso no debería empezar a avisar sola con un número que nadie eligió. Tiene el costo de
que una prenda sin umbral no se vigila, y por eso la interfaz la muestra con un guion atenuado y no
en blanco: *sin vigilar* y *bien* son dos cosas distintas.

**La alerta se compara contra el disponible, no contra el físico.** Lo reservado sigue en la percha,
pero ya tiene dueño y no sirve para atender al próximo cliente que entre — que es justamente lo que
la alerta quiere evitar que pase. Con 10 unidades de las que 8 están reservadas quedan 2 para
vender, y con umbral 5 tiene que avisar aunque el físico diga 10. Tiene prueba propia.

**Se usa `<=` y no `<`.** Estar exactamente en el mínimo ya es estar en el punto de reposición: ese
es el sentido de la palabra.

**Las alertas se ordenan por distancia al umbral, no por cantidad.** Una prenda en cero con mínimo
diez urge más que una en nueve con el mismo mínimo. Quien abre la pantalla a primera hora viene a
hacer una sola pregunta —qué pido hoy— y la respuesta tiene que estar arriba.

**El umbral es la única escritura del paquete que no genera movimiento**, y no es una excepción a la
regla. Lo que no se toca sin dejar rastro es una *cantidad de mercadería*; el umbral no lo es, es
una preferencia de quien administra el local. No hay nada que auditar porque no cambió el stock,
solo cuándo avisar sobre él. Además, un movimiento de cero unidades lo rechazaría el CHECK
`ck_movimiento_inventario_cantidad_no_nula`.

**El ámbito se comprueba resolviendo la existencia primero.** El identificador de la URL no dice a
qué sucursal pertenece, así que el *router* la busca antes de autorizar. Sin ese paso, a un
Encargado le bastaría probar números para cambiarle el umbral a cualquier prenda de la red.

## Una corrección sobre CU-15

El 10/09, al implementar CU-15, se declaró que **el ajuste era solo del Administrador**, leyendo la
fila de CU-15 de la §2.2 del acuerdo de organización, que dice «web: ✔ Admin». Estaba incompleto:
**CU-16 es ese mismo ajuste visto desde el Encargado**, acotado a su sucursal, y es justamente por
eso que CU-15 figura como de Administrador — la mitad del Encargado tiene caso de uso propio.

Se corrigió: `POST /inventario/movimientos/ajuste` pasó al *router* de operación, que admite los dos
roles, con `verificar_ambito_sucursal` adentro. **Un endpoint con dos alcances, no dos endpoints**:
duplicarlo expondría el mismo recurso en dos rutas —lo que la §6.11.2 decidió no hacer— y dejaría
dos copias de la regla del conteo físico esperando a divergir.

La **transferencia** no se movió: cruza dos sucursales y el Encargado responde por una sola.

## Un defecto de la `0003` que apareció al escribir la `0004`

Los ocho CHECK que creó la migración `0003` quedaron con el prefijo duplicado
—`ck_existencia_ck_existencia_disponible_no_negativa`— y uno de ellos se pasó del límite de 63
caracteres de PostgreSQL y terminó truncado con un *hash*. La causa es que la convención de
`app/db/base.py` antepone la tabla sola, así que a `name=` hay que pasarle **solo el sufijo**; la
`0003` lo dice en su propia cabecera y después hace lo contrario.

No era solo feo: `Base.metadata.create_all()` —con lo que las pruebas arman el esquema— sí aplica
bien la convención, así que **la base de pruebas y la base migrada tenían nombres distintos para la
misma restricción**. Cualquier código que distinga una violación por el nombre de su restricción,
que es lo que hace el ayudante `_viola()` de varios servicios del Ciclo 1, pasaría en las pruebas y
fallaría en producción.

La `0004` los renombra, comprobando antes que existan: una base creada con `create_all` ya los tiene
cortos, y un `ALTER` a ciegas fallaría ahí.

## Endpoints

| Método | Ruta | Paso | Rol |
|---|---|---|---|
| `GET` | `/inventario/alertas` | 2 · prendas en punto de reposición | Administrador y Encargado |
| `PATCH` | `/inventario/existencias/{id}/stock-minimo` | 3-5 · fijar el umbral | Administrador y Encargado |
| `GET` | `/inventario/existencias` | 2 · listado de la sucursal | Administrador y Encargado |
| `POST` | `/inventario/movimientos/ajuste` | 3a · conteo físico | Administrador y Encargado |

El Encargado ve y toca solo su sucursal; el Administrador, toda la red. La diferencia no está en el
rol declarado sino en `verificar_ambito_sucursal`, porque la sucursal viaja dentro del token.

## Pantallas

| Plataforma | Ruta | Rol |
|---|---|---|
| Web | `/sucursal/disponibilidad` | Encargado |
| Web | `/admin/inventario` | Administrador — la columna *Mínimo* y la acción de fijarlo |
| Móvil | — | El actor no es Cliente: es solo web (§2.2 del acuerdo) |

La pantalla del Encargado **no** es la misma que la del Administrador, a diferencia de CU-13. Esta
está organizada alrededor del saldo de un local —alertas arriba, listado abajo—; la del
Administrador, alrededor del movimiento. Comparten los diálogos y el servicio, que es donde vive lo
que de verdad se repite.

## Pruebas

`backend/tests/test_cu16_disponibilidad.py` — 16 pruebas. Las que cubren lo que la base **no**
garantiza por sí sola:

- `test_la_alerta_mira_el_disponible_y_no_el_fisico` — la más importante del caso de uso.
- `test_el_encargado_ajusta_su_propia_sucursal` y `test_el_encargado_no_ajusta_la_sucursal_ajena` —
  el ámbito en las dos direcciones, y que el rechazo sea **antes** de escribir.
- `test_el_encargado_no_toca_el_umbral_de_otra_sucursal` — que el identificador de la URL no alcance.
- `test_el_umbral_no_genera_movimiento` — la única escritura del paquete que no deja rastro, a
  propósito.
- `test_las_alertas_salen_de_la_mas_urgente_a_la_menos` y
  `test_reponer_por_un_ingreso_apaga_la_alerta` — que la alerta se calcule contra el saldo actual y
  no se guarde como un estado que alguien tenga que acordarse de apagar.
