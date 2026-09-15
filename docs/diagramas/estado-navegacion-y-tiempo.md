# Diagramas de Estado, Navegación y Tiempo (3.2) y su correspondencia con el código

Este documento es el hermano de [`secuencia-y-codigo.md`](secuencia-y-codigo.md), para los otros
tres diagramas de la §3.2. Explica **qué dibuja cada uno**, **de dónde sale cada caja y cada
rótulo en el código real**, y **en qué se aparta del ejemplo de cátedra y por qué**.

Sirve para dos cosas: para defenderlos mostrando la línea de código de la que sale cada elemento,
y para que cuando el código cambie se sepa qué diagrama hay que tocar.

Los tres viven en `docs/diagramas/VioletBoutique.eapx`, en tres paquetes que cuelgan de
`CAP. 3 - Flujo de Trabajo: Diseño`, al lado de `3.2 Diagramas de Secuencia`:

| Diagrama | Paquete | Tipo de EA | Generador | Cuántos |
|---|---|---|---|---|
| Estado | `3.2 Diagramas de Estado` | `Statechart` | `scripts/ea-estado-3-2.ps1` | **18** |
| Navegación | `3.2 Diagramas de Navegacion` | `Logical` | `scripts/ea-navegacion-3-2.ps1` | **7** |
| Tiempo | `3.2 Diagramas de Tiempo` | `Timing` | `scripts/ea-tiempo-3-2.ps1` | **18** |

**Los 43 están generados y verificados** (Ciclos 1 y 2, al 15/09/2026). Estado y Tiempo, uno por
cada caso de uso transaccional: CU-01 a CU-09 del Ciclo 1 y CU-10, CU-11, CU-13, CU-15, CU-16,
CU-22, CU-23, CU-24 y CU-25 del Ciclo 2. Navegación, uno por actor y por ciclo: Administrador,
Cliente, Encargado de Sucursal y Cajero en el Ciclo 1; Administrador, Cliente y Encargado en el 2.
Del Ciclo 3 no hay ninguno todavía.

---

## 1. La regla de alcance — corrección de la ingeniera, 15/09/2026

Dos reglas, y las dos cambian lo que había hecho antes:

1. **Los tres diagramas entran, en los tres ciclos.** No se difieren.
2. **Secuencia, Estado y Tiempo van solo de los casos de uso TRANSACCIONALES.** Las consultas
   puras quedan fuera. Navegación no se rige por esto: va **por actor**.

Transaccional significa que el caso de uso **escribe**: tiene un `db.commit()`. Eso deja el
reparto así:

| Ciclo | CU del ciclo | Transaccionales | Quedan fuera |
|---|---|---|---|
| **1** | 9 | **los 9** — todos escriben | — |
| **2** | 13 | **9** — CU-10, CU-11, CU-13, CU-15, CU-16, CU-22, CU-23, CU-24, CU-25 | CU-14, CU-17, CU-18, CU-19 |
| **3** | 19 | por definir | — |

Los cuatro que quedan fuera del Ciclo 2 son consultas de lectura: inventario consolidado,
catálogo, ficha de producto y disponibilidad por sucursal. Ninguno tiene `commit`.

> **Pendiente heredado.** Los diagramas de secuencia 3.2 del Ciclo 2 se hicieron **antes** de esta
> regla, así que los cuatro de las consultas ya están generados y exportados. No estorban, pero
> por la regla nueva no corresponderían. Es decisión de Mateo si se quitan.

---

## 2. Diagrama de Estado — el flujo de una transacción

### 2.1 Qué es, y qué NO es

El ejemplo de cátedra (pág. 10 de `todos los diagramas.pdf`, titulado `CU1`) **no es el ciclo de
vida de un objeto**. Es el recorrido de una transacción, de principio a fin, y va **uno por caso
de uso**:

```
Inicio → Loguear Administrador ─[correcto]→ Seleccionar opcion Usuario
                                              ├─[listar]→ Desplegar lista
                                              ├─[crear]→ Crear Usuario ─[llenar datos]→ Revisar Datos
                                              ├─[modificar]→ Modificar Usuario ─[llenar datos]↗
                                              └─[eliminar]→ ID del usuario a eliminar ─[correcto]→ Eliminar Usuario
                                   → Transaccion completada → Fin
```

Esto importa porque **había una versión anterior que estaba mal planteada**: un statechart del
objeto `Reserva`, con sus estados `PENDIENTE`/`PREPARADA`/`ATENDIDA`/`CANCELADA`/`EXPIRADA`. Ese
diagrama es correcto como máquina de estados, pero no es el que pide la cátedra y con la regla de
«uno por CU transaccional» no tiene casillero. Se eliminó.

**Los estados son ACTIVIDADES de la transacción**, no valores de una columna: autenticar,
seleccionar, capturar, validar, escribir, informar. El sumidero es siempre
`Transaccion completada` y después el estado final.

### 2.2 Cómo se lee contra el código

| Elemento del diagrama | Qué es en el código |
|---|---|
| Primer estado (`Autenticar <Actor>`) | la dependencia `requiere_roles(...)` de `backend/app/core/dependencies.py:110` |
| Guarda del primer estado | `usuario.rol not in roles` → 403, `dependencies.py:119` |
| `Seleccionar operacion` | el menú de la pantalla; cada rama es **un endpoint distinto** del `router.py` |
| Estados `Capturar ...` | el componente de formulario de Angular |
| Estado `Validar datos` | los `raise` que hay **antes** del `try` en `service.py` |
| Estado `Informar error` | la función `_traducir()` del router, que convierte cada `ErrorDeGestion` en su `HTTPException` |
| `Transaccion completada` | el `db.commit()` del bloque `try/except` |
| Guarda de cada transición | la condición literal del `if` que la produce, entre corchetes |
| `{...}` al final del rótulo | el ancla: `archivo:línea`, o el verbo y la ruta del endpoint |

### 2.3 El diagrama de CU-03, transición por transición

Es el piloto, y es el calco del `CU1` del ejemplo: mismo CRUD de usuario.

| Desde | Hasta | Guarda | Sale de |
|---|---|---|---|
| *(inicial)* | Autenticar Administrador | — | — |
| Autenticar Administrador | Seleccionar operacion | `[rol ADMINISTRADOR]` | `dependencies.py:110` |
| Autenticar Administrador | *(final de rechazo)* | `[rol distinto]` → 403 | `dependencies.py:119` |
| Seleccionar operacion | Desplegar lista de usuarios | `[listar]` | `GET /admin/usuarios` |
| Seleccionar operacion | Capturar datos del usuario | `[crear]` | `POST /admin/usuarios` |
| Seleccionar operacion | Capturar cambios | `[modificar]` | `PATCH /admin/usuarios/:id` |
| Seleccionar operacion | Confirmar cambio de estado | `[activar o desactivar]` | `PATCH /admin/usuarios/:id/estado` |
| Seleccionar operacion | Identificar usuario a eliminar | `[eliminar]` | `DELETE /admin/usuarios/:id` |
| Capturar datos / Capturar cambios | Validar datos | `[llenar datos]` | el formulario |
| Validar datos | Transaccion completada | `[correo libre y rol existente]` | `seguridad/service.py:374` y `:378` |
| Validar datos | Informar error | `[correo ya registrado]` → 409 | `seguridad/service.py:374` |
| Confirmar cambio de estado | Transaccion completada | `[no es su propia cuenta]` | `seguridad/service.py:493` |
| Confirmar cambio de estado | Informar error | `[intenta desactivarse a si mismo]` → 409 | `seguridad/service.py:493` |
| Identificar usuario a eliminar | Eliminar Usuario | `[sin operaciones asociadas]` | `seguridad/service.py:523` |
| Identificar usuario a eliminar | Informar error | `[tiene operaciones asociadas]` → 409 | `seguridad/service.py:523` |
| Informar error | Seleccionar operacion | `reintentar()` | `_traducir()`, `seguridad/router.py:160` |
| Transaccion completada | *(final)* | — | — |

El caso más claro para la defensa es el de la autodesactivación. El código **es** la guarda:

```python
# backend/app/modules/seguridad/service.py:492
# Excepcion E3.
if not activo and usuario_id == solicitante_id:
    raise AutodesactivacionProhibida(str(usuario_id))
```

### 2.4 Dos decisiones de dibujo, y por qué

**Los rechazos van a un sumidero único (`Informar error`), no vuelven por su propia flecha.** Si
cada rechazo volviera al estado que lo produjo, habría un par de flechas entre las mismas dos
cajas, y **EA escribe el rótulo de ida y el de vuelta en el mismo punto medio**: salen encimados y
no se lee ninguno de los dos. Con el sumidero, cada rechazo tiene su flecha propia y su rótulo
libre, y además es más fiel al código: los tres rechazos pasan por el mismo `_traducir()`.

**Hay dos estados finales.** El rechazo de autorización muere en el suyo, al lado de la
autenticación. Es correcto —UML 2.5 admite varios— y evita una flecha que cruce el lienzo entero
de izquierda a derecha. Además dice algo verdadero: un 403 no llega a haber transacción.

---

## 3. Diagrama de Tiempo — el viaje de una petición

### 3.1 Qué mide

El ejemplo de cátedra es una línea de vida con sus estados apilados, el evento rotulado sobre cada
escalón, la regla numérica abajo y las restricciones `{12}` y `{60}` arriba.

Acá la línea de vida principal es **la transacción**: el viaje de una petición por las capas del
backend.

```
Inactiva → Autenticando → Validando → Escribiendo → Confirmada → Inactiva
```

Ese reparto no es decorativo. Es **el mismo de los diagramas de secuencia** (frontera →
controlador → entidad) y el de las capas de 3.1.1:

| Estado | Qué es |
|---|---|
| `Autenticando` | la dependencia `requiere_roles(...)` |
| `Validando` | los `raise` previos al `try` |
| `Escribiendo` | el cuerpo del `try`: los `INSERT`/`UPDATE` |
| `Confirmada` | el `db.commit()` |

### 3.2 La regla es RELATIVA, y hay que decirlo

**Los números de la regla (0 a 100) son instantes del escenario, no milisegundos medidos.** Nadie
corrió un perfilador sobre esto. Si en la defensa preguntan por ellos, la respuesta honesta es esa.

Lo que **sí** es real son las restricciones `{...}`: cada una sale de una constante del código o de
un requisito no funcional.

| Restricción | Qué significa | De dónde sale |
|---|---|---|
| `{8 h}` | la vida de un token de acceso | `ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8`, `backend/app/core/config.py:32` |
| `{RNF11}` | la fila queda bloqueada desde el `UPDATE` hasta el `commit` | RNF11, consistencia transaccional, `docs/03-captura-requisitos.md` §3.4 |
| `{RNF02}` | el tiempo de respuesta debe ser adecuado | RNF02, rendimiento, ídem |

> Si se quisieran números medidos de verdad, habría que instrumentar el backend contra la base
> local (`localhost:5433`) y sustituir la regla relativa por milisegundos reales. No está hecho.

### 3.3 Un diagrama cuenta UN escenario

Un caso de uso transaccional tiene varias ramas; una línea de vida dibuja una sola. **Se elige la
rama donde el reloj manda**, no la más común.

Para CU-03 esa rama es **desactivar una cuenta**, no el alta. La razón es la segunda línea de
vida: `SesionToken`. Al desactivar, `revocar_sesiones_de_usuario()` corre dentro de la misma
transacción, y el token pasa de `Vigente` a `Revocado` **en el instante del commit**. Sin eso
seguiría valiendo hasta ocho horas, y la postcondición del caso de uso —«un usuario desactivado no
puede iniciar sesión»— se cumpliría solo a medias.

Eso es exactamente lo que dice la §3.2 del Ciclo 1 en `cap-2-3-analisis-y-diseno.md`, y es lo que
el diagrama hace ver de un vistazo: **las dos líneas de vida escalonan en el mismo instante.**

### 3.4 Lo que este diagrama tiene flojo, y qué contestar

De los tres es **el más discutible**, y conviene tenerlo claro antes de que lo pregunten. Se decidió
**dejarlo así** (Mateo, 15/09/2026), pero con las debilidades a la vista:

**`Transaccion` no es una clase del modelo.** UML 2.5 §17.4 dice que una línea de vida representa
la instancia de un clasificador. La de `SesionToken` lo tiene —está enganchada por `ClassifierID` a
la clase del dominio—; la de `Transaccion` **no**: es la petición en curso, no una fila de la base
ni un objeto del análisis.

> **Qué contestar si lo preguntan:** que `Transaccion` es la **petición HTTP en curso**, y que sus
> estados son las cuatro fases que atraviesa en el backend —las mismas capas del 3.1.1 y el mismo
> reparto de los diagramas de secuencia—. Que no tenga clase propia es deliberado: no es una
> entidad del dominio, es la unidad de trabajo. La alternativa sería usar la clase «controlador»
> del 2.3 (`GestorUsuarios`) como línea de vida; se evaluó y se descartó porque el controlador no
> cambia de estado, la petición sí.

**Sin números medidos, agrega poco sobre el de secuencia.** El orden frontera → controlador →
entidad ya está en 3.2. Con la regla relativa, este diagrama es ese mismo recorrido girado 90°; lo
único que suma son las restricciones. Nadie instrumentó el backend: si quisieran milisegundos
reales habría que cronometrar las cuatro fases contra la base local.

**En la mayoría de los CU no hay reloj.** Gestionar ciudades, proveedores, categorías o temporadas
no tienen ningún plazo, así que el diagrama sale igual en todos. Donde el reloj **sí** manda en
este sistema es en cuatro sitios, y son los que hay que mostrar primero si dan a elegir:

| Dónde | La constante | Casos de uso |
|---|---|---|
| vigencia del token | `ACCESS_TOKEN_EXPIRE_MINUTES` = 8 h | CU-02, CU-03, CU-06 |
| franja de la reserva | `RESERVA_VIGENCIA_HORAS` = 24 h | CU-22 a CU-25 |
| webhook del pago | confirmación asíncrona e idempotente | Ciclo 3 |
| respuesta del modelo | Gemini | Ciclo 3 |

---

## 4. Diagrama de Navegación — uno por actor

### 4.1 No es UML, y hay que decirlo

**El diagrama de navegación no existe en UML 2.5.** No es uno de los catorce de la norma. Lo que se
usa es la extensión **UWE** (*UML-based Web Engineering*): un diagrama de **clases** con un perfil
de navegación. Por eso el tipo en EA es `Logical` y los elementos son `Class`.

Si en la defensa preguntan qué diagrama UML es, la respuesta honesta es que no lo es.

### 4.2 Las tres cosas que lo definen

El ejemplo de cátedra se titula `class navegacion cliente`, y eso fija tres reglas:

1. **Va uno por actor.** El título nombra al actor y el actor está dibujado adentro. No es un mapa
   del sistema entero.
2. **Lleva los controladores**, no solo las pantallas.
3. **Los enlaces van rotulados `build` y `submit`** — se construye una vista, una vista postea.

Partir por actor no es una elección estética: **es el corte que ya hace el código**. Cada ruta de
`app.routes.ts` declara `canActivate: [sesionGuard, rolGuard('...')]`, y esa guarda es la que
decide de qué actor es cada pantalla.

### 4.3 Qué es cada caja

| Estereotipo | Qué es | Cómo se llama |
|---|---|---|
| `«menu»` | la pantalla eje del actor, la que deja el login | `admin-layout.ts` |
| `«navigationClass»` | una vista de lista. Sus atributos son **los filtros reales** del endpoint de listado | `usuarios.ts` |
| `«formClass»` | un formulario. Sus atributos son **los campos reales** | `usuario-formulario.ts` |
| `«controller»` | el router. Sus operaciones son **las funciones**, una por una | `seguridad/router.py` |

**Los nombres son los nombres exactos de los archivos y las funciones** —regla de oro 10 de
[`GUIA-DIAGRAMAS-EA.md`](../../GUIA-DIAGRAMAS-EA.md), del 15/09/2026—. Nada de `UsuariosController`
ni `Formulario de usuario`: si el diagrama no se puede comparar renglón a renglón contra el
repositorio, no sirve de nada.

Eso trae una consecuencia que hay que aceptar: **si dos áreas comparten archivo, comparten caja.**
Ciudades y sucursales las atiende las dos `organizacion/router.py`, así que en el diagrama hay
**una sola caja** con las diez funciones de ambas, y le llegan los `submit` de las cuatro vistas.
Tener dos cajas separadas era más cómodo de mirar y era falso.

El atributo `ruta` de cada vista es su ruta literal de `app.routes.ts`. Eso es lo que hace el
diagrama verificable: se abre el archivo y se comparan una por una.

### 4.4 El salto que no se dibuja

Entre la vista y el controlador del servidor hay un salto más: el servicio de Angular
(`core/services/*.service.ts`), que es quien hace el HTTP. **No se dibuja como clase** para no
duplicar cada fila —serían siete cajas que no deciden nada— pero está nombrado en la nota de cada
controlador.

### 4.5 La cadena, no las idas y vueltas

Los enlaces van en cadena, como en el ejemplo:

```
Actor ─[sesion + ROL]→ Tablero ─build→ Vista ─build→ Formulario ─submit→ Controlador
                                          └─submit→ Controlador
```

No hay flecha de vuelta del controlador a la vista, por dos razones. La primera es de dibujo: con
la ida y la vuelta entre las mismas dos cajas, **EA encima los dos rótulos** y sale `sbuild:` en
lugar de `submit` y `build`. La segunda es que la vuelta ya está contada — `Tablero ─build→ Vista`
es el mismo `build` que hace el controlador al devolver la página.

### 4.6 Lo que este diagrama deja ver

| Actor | Ciclo | Elementos | Qué muestra |
|---|---|---|---|
| Administrador | #1 | 22 | usuarios, ciudades, sucursales, empleados, proveedores, maestros y temporadas |
| Cliente | #1 | 7 | el acceso público (`/login`, `/registro`) y el perfil con sus dos formularios |
| Encargado de Sucursal | #1 | 2 | solo la bienvenida: sus funciones llegan en el Ciclo 2 |
| Cajero | #1 | 2 | ídem; el punto de venta es del Ciclo 3 |
| Administrador | #2 | 35 | las siete del Ciclo 1 más productos, imágenes, inventario, consolidado y reservas |
| Cliente | #2 | 13 | lo del Ciclo 1 más la vitrina, los favoritos y las reservas |
| Encargado de Sucursal | #2 | 10 | reservas de la sucursal, disponibilidad e inventario |

**Son ACUMULATIVOS**, como el 1.5: el del Ciclo 2 lleva también lo del Ciclo 1, porque un mapa de
navegación es la foto de todo lo que el actor puede alcanzar, no solo de lo nuevo. Por eso el del
Administrador del Ciclo 2 es el más grande del capítulo —35 elementos— y para el `.docx`
probablemente haya que apretarlo o partirlo.

Faltan los del **móvil**, y los del **Proveedor**, cuyo portal sigue siendo una pantalla vacía.

> **El del Cliente dibuja el problema del catálogo.** `/tienda` y `/tienda/producto/:id` cuelgan
> del **actor**, no del eje del rol, porque no declaran `canActivate`; y de la zona con sesión no
> sale ninguna flecha de vuelta a `/tienda`. Eso es exactamente el defecto detectado el 13/09. Está
> dicho en la nota del diagrama, sin una nota gráfica que lo señale: es decisión de Mateo si se
> muestra o se tapa.

---

## 5. Lo que EA hace mal con estos tres

Cinco tropiezos, todos encontrados generando el piloto. Los cinco están resueltos en los
generadores; esto es para que no se vuelvan a pisar.

### 5.1 «view» y «form» son estereotipos reservados

Si a una clase se le pone `«view»` o `«form»`, EA cambia la forma de la caja por la de su perfil de
interfaz de usuario, no escribe el `«...»` y —lo grave— **deja de dibujar los atributos**: el
formulario sale como una caja vacía, sin sus campos, que es justo lo que había que mostrar.

Por eso se usan `«navigationClass»` y `«formClass»`, que EA no toca. Es el mismo tropiezo del
`«FORM»` del 4.3, que EA pasa a minúscula.

### 5.2 El alto de una caja es un mínimo, no una medida

Si la clase tiene más atributos u operaciones de los que entran, **EA agranda la caja hacia abajo
sin avisar** y se come la fila siguiente. El caso peor del diagrama del Administrador es el
formulario de usuario, con seis campos, y el controlador de empleados, con siete operaciones:
necesitan 150 px. Con los 85 de la primera versión se solapaban.

### 5.3 Dos flechas entre las mismas dos cajas = dos rótulos en el mismo punto

Vale para los tres diagramas. EA pone el rótulo en el punto medio del conector, y si hay ida y
vuelta entre los mismos dos elementos, los dos puntos medios coinciden. El resultado es ilegible y
**no da ningún error**: hay que mirarlo.

La solución es de modelado, no de dibujo: un sumidero de errores en el de estado, una cadena en el
de navegación.

### 5.4 En el de tiempo, el rótulo se dibuja hacia la derecha y no se corta

EA escribe el evento a la derecha del instante, y la restricción pegada al final del evento, sin
envolver ni recortar. Con la línea de vida angosta los rótulos consecutivos se pisan y el último se
sale del marco. Por eso `$ANCHO = 1400` —unos 14 px por unidad de la regla— y los rótulos van
cortos.

### 5.5 La restricción va SIN llaves

Las pone EA al dibujar. Si se escriben en el dato, salen dobles: `{{8 h}}`.

### 5.6 El rótulo de una flecha cae en el punto medio, y el punto medio choca

Esto apareció al pasar de un caso de uso a dieciocho, y es lo que más tiempo costó. EA dibuja el
rótulo de cada transición **a media altura entre origen y destino**. Con varias flechas saliendo
del mismo menú, dos de ellas terminan a la misma altura y en la misma x, y los rótulos quedan
encimados —se llegó a leer `[a[intenta desactivarse a si mismo] {409 service.py:493}o}`—.

La solución fue dejar de escribir coordenadas y declarar **columna + fila**, admitiendo **medias
filas**. Un medio punto mueve el rótulo 90 px y eso alcanza:

- `Informar error` va en la fila **3.5**, no en la 3: en la 3 su vuelta al menú comparte punto medio
  con la rama `menú → operación 3`.
- `Transaccion completada` va en la **2.5**, no en la 2: en la 2 el conector `operación 3 → cierre`
  comparte punto medio con el `Validar → Informar error`, que es vertical y cae en la misma x.
- Y hay una regla más general: **el punto medio de la flecha de vuelta tiene que caer en el HUECO
  entre dos operaciones, nunca sobre una.** En CU-11, CU-13, CU-22 y CU-24 hubo que correr el
  sumidero medio punto por eso.

### 5.7 Un elemento no puede estar dos veces en el mismo lienzo

Pero sí en dos diagramas distintos. Como los controladores se nombran por archivo y un archivo
atiende a varios actores, `seguridad/router.py` aparece en el diagrama del Administrador y en el
del Cliente: es **el mismo elemento**, y el generador lo reutiliza buscándolo por nombre. Cuando lo
reutiliza le **agrega las operaciones que falten**, porque cada diagrama declara el subconjunto que
le toca y la caja tiene que terminar con la unión de todas.

Dentro de un mismo diagrama, en cambio, la caja compartida se dibuja **una sola vez**, en la
primera banda que la usa, y las demás le tiran la flecha.

---

## 6. Cómo se regeneran

```powershell
# aditivo: solo crea los diagramas que faltan
powershell -ExecutionPolicy Bypass -File scripts\ea-estado-3-2.ps1
powershell -ExecutionPolicy Bypass -File scripts\ea-tiempo-3-2.ps1
powershell -ExecutionPolicy Bypass -File scripts\ea-navegacion-3-2.ps1

# uno solo, por caso de uso o por actor
powershell -ExecutionPolicy Bypass -File scripts\ea-estado-3-2.ps1 -CU CU-03
powershell -ExecutionPolicy Bypass -File scripts\ea-navegacion-3-2.ps1 -Actor Administrador

# borra el paquete entero y lo rehace
powershell -ExecutionPolicy Bypass -File scripts\ea-estado-3-2.ps1 -Rehacer

# sobre una copia, sin tocar el modelo bueno. Es como se afinaron los tres.
powershell -ExecutionPolicy Bypass -File scripts\ea-estado-3-2.ps1 -Modelo C:\ruta\Prueba.eapx
```

**Enterprise Architect tiene que estar cerrado.** El script abre el modelo por COM; con EA abierto,
su copia en memoria pisa lo escrito.

**Los tres generadores NO exportan imágenes.** Las saca Mateo a mano desde EA, que es el pedido del
13/09.

### Agregar un caso de uso o un actor

Los datos están al principio de cada script, en tablas declarativas:

- `ea-estado-3-2.ps1` → `$CASOS`: un bloque por CU, con su lista de `estados` (nombre, posición,
  nota) y su lista de `transiciones` (desde, hasta, rótulo).
- `ea-tiempo-3-2.ps1` → `$CASOS`: un bloque por CU, con sus `lineas` de vida y, en cada una, los
  `estados` del eje Y y las `marcas` (instante, estado, evento, restricción).
- `ea-navegacion-3-2.ps1` → `$ACTORES`: un bloque por actor, con su `menu` y una `areas` por zona
  funcional (vista, formulario y controlador).

Agregar un caso de uso es agregar un bloque. No hay que tocar el código de abajo.
