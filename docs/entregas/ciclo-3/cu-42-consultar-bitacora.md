# CU-42 · Consultar la bitácora del sistema

> **Escrita el 20/09/2026.** Realiza el **RNF14**, agregado al documento de
> requisitos junto con este caso de uso.

---

## 1. Qué hueco cierra, y por qué el RNF10 no lo cerraba

El **RNF10** ya exigía trazabilidad — pero **solo de existencias**: cada
modificación de inventario queda como un `movimiento_inventario` inmutable.
Eso cubre la mercadería y nada más.

No había ningún registro de:

- quién inició sesión, ni quién lo **intentó** sin conseguirlo;
- quién cambió un precio;
- quién desactivó un producto o dio de baja a un empleado;
- quién abrió o cerró una caja.

En un sistema con cinco roles y operaciones sobre dinero eso es un agujero:
**cuando algo aparece cambiado, no hay forma de saber quién lo cambió.**

El catálogo iba de CU-01 a CU-41 sin ninguna bitácora. Este es el CU-42.

## 2. Es una tabla, no un archivo de log

El log de la aplicación se pierde en cada despliegue —Railway reinicia el
contenedor— y no se puede consultar desde la aplicación. **Una bitácora que
el Administrador no puede leer no sirve para lo único que se le pide.**

## 3. La decisión de fondo: lo escribe un middleware

La alternativa era sembrar `bitacora.registrar(...)` por los servicios, en
cada operación que valga la pena anotar. Se descartó por una razón:

> **Se puede olvidar.** Una ruta nueva que nadie instrumenta no deja rastro, y
> el agujero no se nota nunca — la bitácora no se queja de lo que le falta.
> Justo la operación que alguien quiera esconder es la que va a estar sin
> anotar.

Desde el middleware la cobertura es automática y completa: **toda petición que
cambia algo queda registrada aunque el caso de uso sea de la semana que
viene.**

### Solo lo que cambia algo

Se anotan `POST`, `PUT`, `PATCH` y `DELETE`. Los `GET` no: serían miles de
filas por día —cada pantalla del catálogo son varias— y volverían inservible
justo la pantalla que existe para buscar entre ellas.

Quedan fuera además el **webhook de la pasarela** (llega miles de veces con
reintentos, no lo hace una persona, y tiene su propio rastro en `pago`) y **la
bitácora misma**, que si no agregaría una fila a lo que se está consultando.

### Llevarse datos también deja rastro — agregado el 20/09

La primera versión solo anotaba lo que **cambia** algo. Al mirar producción,
el resultado fue elocuente: **de 28 asientos, 24 eran entrar y salir.**

La regla estaba bien planteada pero incompleta: **«leer» y «llevarse» no son
lo mismo.** Bajar el reporte de ventas de un mes es sacar información a un
archivo que después vive fuera, se manda por correo y ya no se controla. Es
justamente lo que una auditoría quiere saber, y no dejaba rastro alguno.

Ahora también se anotan, como acción **`EXPORTAR`**:

| Ruta | Queda como |
|---|---|
| `GET /reportes/{tipo}.{pdf\|xlsx}` | entidad «reporte de ventas», id «xlsx» |
| `GET .../{codigo}/comprobante` | entidad «comprobante», id el código |

**El tablero no entra**, y es deliberado: se mira en pantalla, no genera
archivo, y en el teléfono se refresca tirando hacia abajo. Anotarlo llenaría
la bitácora de ruido que nadie pidió.

### Los fallos son lo que más interesa

Un `401` o un `403` **sí** se anotan, como `CREAR_RECHAZADO`: son los intentos
de hacer algo sin permiso. Un barrido de rutas se ve como una hilera de ellos.

### Lo que el middleware no podía saber

En un **inicio de sesión fallido** no hay usuario que resolver, y el
middleware no puede leer el correo del cuerpo sin consumir el flujo de la
petición. Sin eso, el asiento diría que alguien intentó entrar **sin decir con
qué cuenta** — que es el único dato que importa de un intento fallido.

Lo resuelve la ruta de login dejando el correo en `request.state`, y el
middleware lo recoge. Es la única excepción a «el middleware se arregla solo».

### El detalle: los parámetros, no el cuerpo

La columna `detalle` existía desde el principio, ya filtraba credenciales y
**estaba vacía en todo salvo el login**. Ahora guarda los **parámetros de la
consulta**, que en una exportación son justo lo interesante: con qué período
y con qué filtros salió el reporte que alguien se llevó.

Se guardan los parámetros y **no el cuerpo de la petición**, y es una
decisión. Leer el cuerpo en el middleware obliga a consumir el flujo antes de
que lo lea la ruta, y `BaseHTTPMiddleware` no lo devuelve intacto: habría que
reinyectarlo a mano, y **un error ahí rompe todas las peticiones del
sistema**, no solo la bitácora. No vale el riesgo por un dato de auditoría.

Una ruta que quiera guardar más lo deja en `request.state.bitacora_detalle`,
que es lo que ya hace el login con el correo intentado.

### Dos defectos que aparecieron al revisarlo

- **`POST /pagos/webhook` se estaba anotando** pese a estar excluido: la lista
  decía `/webhooks/` y la ruta real es `/pagos/webhook`. En producción se
  coló un asiento antes de que se notara.
- **El pedido por voz salía como `CREAR`**, que miente: no crea nada, le pide
  a un modelo que interprete una frase. Ahora es `PEDIR_REPORTE_POR_VOZ`.
  Quedó un mapa de rutas donde el verbo HTTP no dice la verdad.

### El inicio de sesión ahora lleva su rol

Se anotaba **sin rol y sin usuario**: en ese momento todavía no hay token que
resolver, así que el middleware no sabe quién es. Dos consecuencias, y la
segunda es de fondo:

1. la fila se veía distinta de todas las demás;
2. **filtrar por «solo empleados» dejaba fuera sus entradas al sistema** —
   que es de lo primero que se quiere auditar.

Lo resuelve la ruta de login, que sí sabe quién es apenas valida las
credenciales. Un **intento fallido sigue sin rol**, y está bien: ahí no hay
usuario, solo el correo intentado.

> **Y no, un inicio de sesión no deja dos asientos.** Se revisó porque lo
> parecía: deja uno solo, verificado contra producción con una ventana de
> ±3 s y sin un solo duplicado en la tabla. Lo que se ve son **dos acciones
> distintas y las dos reales** —cerrar la sesión anterior y abrir una nueva—
> que al cambiar de cuenta quedan una al lado de la otra.

## 4. Inmutable, como el movimiento de inventario

Misma decisión **D4**. No hay `actualizado_en`, y la API **no expone ni un
`POST`, ni un `PATCH`, ni un `DELETE`** sobre esta tabla — hay una prueba que
lee el contrato de OpenAPI y falla si aparece alguno.

**Una bitácora que se puede corregir no prueba nada**, y justamente quien
tendría motivo para alterarla es quien tiene el rol para leerla.

## 5. Por qué se duplican el correo y el rol

`usuario_id` es nulo y la clave foránea es `ON DELETE SET NULL`: borrar una
cuenta **no puede** borrar el rastro de lo que hizo. Por eso el asiento guarda
además:

- **`actor`**: el correo tal como estaba en ese momento;
- **`rol`**: el rol con el que se actuó entonces, porque los roles se
  reasignan.

Duplican datos que ya están en `usuario`, y está bien que lo hagan: **una
bitácora que se reescribe sola cuando cambian los datos maestros no es un
registro histórico.**

## 6. Ninguna credencial llega a la bitácora

El detalle se filtra **en profundidad** antes de guardarse: cualquier clave que
contenga `contrasena`, `password`, `token`, `clave`, `secret`, `hash`,
`tarjeta` o `cvv` se reemplaza por `«omitido»`.

En profundidad y no solo en el primer nivel, porque `{"acceso": {"contrasena":
...}}` es exactamente la forma que tiene el alta de un proveedor con acceso.

La bitácora se lee desde una pantalla y se puede exportar: **una clave ahí
dentro es una filtración con fecha y nombre.**

## 7. Que la bitácora falle no puede impedir vender

Todo el registro está dentro de un `try` que traga la excepción y la manda al
log. Si la tabla no existe, si la base no responde:

> Una tienda que no puede vender porque no puede anotar que vendió está peor
> que una que vende sin anotar.

El asiento se escribe además en **su propia sesión**, no en la de la petición:
si compartieran, una petición que termina en error haría `rollback` y se
llevaría puesto el asiento — justo el de la operación fallida.

### El detalle que casi mete datos de prueba en producción

El middleware pide su sesión **a través de la dependencia `get_db`**, no
llamando a `SessionLocal()`. Parece un rodeo y no lo es: las pruebas sustituyen
`get_db` para apuntar a la base de pruebas, pero **no tocan `SessionLocal`**,
que sigue leyendo `DATABASE_URL` del `.env` — o sea, Supabase. Con la llamada
directa, correr la batería de pruebas habría escrito asientos en producción.

## 8. Quién la puede leer

**Solo el Administrador**, y es una decisión, no una omisión. La bitácora dice
a qué hora entra cada empleado, desde qué dirección y qué toca: en manos de un
Encargado eso es vigilancia de sus compañeros, no auditoría. El Encargado ya
tiene el reporte de movimientos de su sucursal, que es lo que necesita para su
trabajo.

## 9. La pantalla

`/admin/bitacora`, **con su entrada en el menú al lado de Reportes**. Es la
tercera vez en este ciclo que un caso de uso se construye sin forma de llegar
—pasó con CU-33, con CU-37 y con los datos de CU-39—, así que la entrada se
puso junto con la ruta.

- Lista densa: lo que se hace acá es barrer muchas líneas buscando una.
- **El fallo se distingue por color y por icono**, no solo por color: quien no
  distingue rojo y verde no vería justo la diferencia que más importa.
- Dice **«Solo lectura»** en la cabecera. Que no se pueda editar es una
  propiedad del registro, y quien lo lee tiene que saberlo para poder confiar
  en él.
- Los filtros de acción y recurso se piden a `/bitacora/opciones`, que los lee
  de la tabla: con una lista escrita en el front, el desplegable ofrecería
  acciones sin resultados y escondería las que sí hay.

```
GET /api/v1/bitacora?desde=&hasta=&usuario_id=&accion=&entidad=&exito=&busqueda=&pagina=&tamano=
GET /api/v1/bitacora/opciones
```

## 10. La hora

Los asientos se guardan en `TIMESTAMPTZ` y **el servidor los devuelve ya
convertidos a hora boliviana**. La pantalla los formata con la zona fijada
explícitamente (`-0400`) en vez de dejar que `DatePipe` use la del navegador:
una computadora con la hora mal puesta mostraría una bitácora distinta a la de
la máquina de al lado, sobre un registro cuyo único valor es que **todos vean
lo mismo**.

Ver `hora-boliviana.md`, que se escribió en la misma tanda.

## 11. Límites conocidos

- **No se guarda el cuerpo de la petición**, solo los parámetros de la
  consulta. Ver arriba: el motivo es técnico y no de alcance.
- **No dice qué cambió, solo que se cambió.** Un «antes y después» exigiría
  leer la fila antes de cada modificación, que es una consulta más por
  operación en todo el sistema.
- **No hay purga.** La tabla crece sin límite. Con el volumen de una tienda y
  la duración de este proyecto no es un problema, pero en producción real haría
  falta archivar lo viejo.
- **No hay pantalla en el móvil.** La bitácora es del Administrador, que
  trabaja en la web.
