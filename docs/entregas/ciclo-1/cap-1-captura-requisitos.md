# CAP. 1 · CICLO #1 — Captura de Requisitos

Contenido listo para volcar al `.docx`, en el orden del índice oficial. Cubre las secciones de
`CAP. 1` que dependen de los casos de uso del Ciclo 1: **1.3.1 Elaborar la tabla Detalle** y
**1.5 Estructurar Modelo de Casos de Uso**.

Las secciones **1.1.1 a 1.1.4** y **1.2** van completas y su fuente es
[`docs/03-captura-requisitos.md`](../../03-captura-requisitos.md). Las secciones **1.3.2**
(diagrama de casos de uso) y **1.4** (prototipos) son artefactos gráficos y se elaboran aparte.

**Casos de uso del Ciclo 1:** CU-01 a CU-09 · paquetes P1 Seguridad, P2 Organización y
P3 Catálogo (maestros).

---

## 1.3.1 Elaborar la tabla Detalle — CICLO #1

### CU-01 · Registrar cliente

| Campo | Contenido |
|---|---|
| **Código** | CU-01 |
| **Nombre** | Registrar cliente |
| **Descripción** | Permite a una persona crear su cuenta de cliente indicando sus datos personales, correo y contraseña, quedando habilitada para reservar y comprar. |
| **Propósito** | Incorporar al visitante como cliente identificado del sistema, de modo que sus reservas, compras y preferencias puedan asociarse a él. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P1 · Seguridad y Usuarios |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF01, RNF01 |
| **Precondiciones** | El correo electrónico no está registrado en el sistema. |
| **Postcondiciones** | Existe un usuario con rol *Cliente* y su ficha de cliente asociada; la contraseña queda almacenada como hash; el cliente puede iniciar sesión. |

**Flujo principal**

1. El Cliente solicita el formulario de registro desde la web o la app móvil.
2. El sistema presenta el formulario: nombres, apellidos, documento de identidad, teléfono, correo electrónico y contraseña.
3. El Cliente completa los datos y confirma.
4. El sistema valida el formato del correo, la fortaleza de la contraseña y que todos los campos obligatorios estén presentes.
5. El sistema verifica que el correo no corresponda a un usuario ya registrado.
6. El sistema calcula el hash de la contraseña.
7. El sistema crea el usuario con rol *Cliente* y su ficha de cliente asociada.
8. El sistema informa que el registro fue exitoso e invita a iniciar sesión.

**Flujos alternativos**

- **4a. Datos inválidos.** El sistema señala cada campo con error y devuelve el control al paso 3 sin perder lo ya escrito.
- **8a. Registro desde el flujo de reserva o compra.** Si el registro se inició al intentar una operación que exige identificación, el sistema inicia la sesión automáticamente y devuelve al Cliente al punto donde estaba.

**Excepciones**

- **E1. Correo ya registrado.** El sistema informa que ese correo ya tiene cuenta y ofrece iniciar sesión o recuperar la contraseña. El caso de uso termina sin crear nada.
- **E2. Error al persistir.** La operación se ejecuta en una transacción: si falla la creación del usuario o de la ficha de cliente, no se crea ninguno de los dos y el sistema informa el error.

---

### CU-02 · Iniciar y cerrar sesión

| Campo | Contenido |
|---|---|
| **Código** | CU-02 |
| **Nombre** | Iniciar y cerrar sesión |
| **Descripción** | Permite a cualquier usuario autenticarse con correo y contraseña obteniendo un token de acceso acorde a su rol; el cierre de sesión invalida el token. |
| **Propósito** | Establecer la identidad y el rol del usuario para toda operación posterior, y permitir terminar esa identificación de forma segura. |
| **Actores** | Cliente, Administrador, Encargado de Sucursal, Cajero, Proveedor (cualquiera de ellos inicia) |
| **Paquete** | P1 · Seguridad y Usuarios |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF02, RNF01 |
| **Precondiciones** | El usuario existe y su cuenta está activa. |
| **Postcondiciones** | El usuario posee un token de acceso vigente con su rol y, si corresponde, su sucursal. Al cerrar sesión el token queda revocado y deja de ser aceptado. |

**Flujo principal**

1. El usuario solicita la pantalla de inicio de sesión.
2. El sistema presenta el formulario de correo y contraseña.
3. El usuario ingresa sus credenciales y confirma.
4. El sistema busca el usuario por su correo y verifica que la cuenta esté activa.
5. El sistema compara la contraseña recibida contra el hash almacenado.
6. El sistema emite un token de acceso que contiene el identificador del usuario, su rol y su sucursal cuando la tiene, con una vigencia definida.
7. El sistema registra la sesión y devuelve el token junto con los datos básicos del usuario.
8. La aplicación redirige al usuario al área que corresponde a su rol.

**Flujo de cierre de sesión**

1. El usuario solicita cerrar sesión.
2. El sistema revoca el token vigente y registra la fecha de cierre.
3. La aplicación descarta el token almacenado y vuelve a la pantalla de inicio de sesión.

**Flujos alternativos**

- **6a. Token vencido durante el uso.** Al recibir una petición con un token expirado, el sistema la rechaza y la aplicación redirige al inicio de sesión conservando la ruta destino.

**Excepciones**

- **E1. Credenciales incorrectas.** El sistema informa que el correo o la contraseña no son válidos, **sin precisar cuál de los dos**, y devuelve el control al paso 3.
- **E2. Cuenta desactivada.** El sistema informa que la cuenta no está habilitada e indica contactar al Administrador. No se emite token.
- **E3. Intentos fallidos reiterados.** Tras varios intentos fallidos consecutivos el sistema demora la respuesta para dificultar el ataque por fuerza bruta.

---

### CU-03 · Gestionar usuarios y roles

| Campo | Contenido |
|---|---|
| **Código** | CU-03 |
| **Nombre** | Gestionar usuarios y roles |
| **Descripción** | Permite al Administrador crear, editar, activar/desactivar y eliminar cuentas de usuario, asignando su rol y, cuando corresponde, su sucursal. |
| **Propósito** | Controlar quién accede al sistema y con qué alcance, que es la base del control de acceso por roles. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P1 · Seguridad y Usuarios |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF02, RNF01 |
| **Precondiciones** | El Administrador tiene sesión iniciada con su rol. |
| **Postcondiciones** | El conjunto de usuarios y sus roles refleja los cambios; un usuario desactivado no puede iniciar sesión. |

**Flujo principal**

1. El Administrador ingresa a la gestión de usuarios.
2. El sistema lista los usuarios paginados, con su correo, nombre, rol, sucursal y estado, y ofrece búsqueda por nombre o correo y filtro por rol y por estado.
3. El Administrador elige crear un usuario.
4. El sistema presenta el formulario: nombres, apellidos, correo, contraseña inicial, rol y —si el rol es Encargado de Sucursal o Cajero— la sucursal.
5. El Administrador completa los datos y confirma.
6. El sistema valida los datos y que el correo no esté en uso.
7. El sistema crea el usuario con la contraseña almacenada como hash y lo muestra en la lista.

**Flujos alternativos**

- **3a. Editar.** El Administrador selecciona un usuario, el sistema presenta sus datos, el Administrador los modifica y confirma. La contraseña solo se modifica si se ingresa una nueva.
- **3b. Activar o desactivar.** El Administrador cambia el estado de la cuenta. El sistema pide confirmación y, al desactivar, revoca los tokens vigentes de ese usuario.
- **3c. Eliminar.** El sistema solo permite eliminar usuarios sin operaciones asociadas; en caso contrario ofrece desactivar en su lugar.

**Excepciones**

- **E1. Correo ya registrado.** El sistema lo informa y devuelve el control al paso 5.
- **E2. Rol que exige sucursal sin sucursal indicada.** El sistema impide guardar y señala el campo.
- **E3. Autodesactivación.** El sistema impide que el Administrador desactive o elimine su propia cuenta.

---

### CU-04 · Gestionar perfil del cliente

| Campo | Contenido |
|---|---|
| **Código** | CU-04 |
| **Nombre** | Gestionar perfil del cliente |
| **Descripción** | Permite al Cliente consultar y modificar sus datos personales, sus tallas habituales, sus preferencias y sus direcciones de entrega. |
| **Propósito** | Mantener actualizada la información con la que el sistema personaliza la oferta y ejecuta las entregas. |
| **Actores** | Cliente (iniciador) |
| **Paquete** | P1 · Seguridad y Usuarios |
| **Prioridad** | Media |
| **Requisitos que realiza** | RF01 |
| **Precondiciones** | El Cliente tiene sesión iniciada. |
| **Postcondiciones** | Los datos del cliente quedan actualizados; sus tallas habituales quedan disponibles para el recomendador del Ciclo 3. |

**Flujo principal**

1. El Cliente ingresa a su perfil.
2. El sistema muestra sus datos personales, sus tallas habituales por tipo de prenda, sus categorías preferidas y sus direcciones de entrega registradas.
3. El Cliente modifica los datos que desea y confirma.
4. El sistema valida los datos y los guarda.
5. El sistema confirma la actualización.

**Flujos alternativos**

- **3a. Agregar dirección.** El Cliente registra una nueva dirección con su alias, ciudad, referencia y, opcionalmente, la marca como predeterminada.
- **3b. Eliminar dirección.** El sistema pide confirmación y elimina la dirección; si era la predeterminada, deja sin predeterminada al cliente.
- **3c. Cambiar contraseña.** El Cliente ingresa la contraseña actual y la nueva dos veces; el sistema verifica la actual antes de reemplazar el hash.

**Excepciones**

- **E1. Contraseña actual incorrecta.** El sistema rechaza el cambio y devuelve el control al paso 3c.
- **E2. Correo en uso.** Si el Cliente intenta cambiar su correo por uno ya registrado, el sistema lo impide.

**Nota de alcance (Ciclo 1).** Las *categorías preferidas* del paso 2 se difieren al Ciclo 2, donde
se implementan junto con el CU-08, que es el que da de alta las categorías. Ver §6.11.3 de
`docs/06-decisiones-tecnicas.md`. El resto del flujo se realiza completo en el Ciclo 1.

---

### CU-05 · Gestionar ciudades y sucursales

| Campo | Contenido |
|---|---|
| **Código** | CU-05 |
| **Nombre** | Gestionar ciudades y sucursales |
| **Descripción** | Permite al Administrador registrar, editar y dar de baja ciudades y sucursales, con su dirección, horario de atención y capacidad de vestidores. |
| **Propósito** | Establecer la estructura física de la cadena, que es el eje sobre el que se particionan el inventario, las reservas y las ventas. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P2 · Organización |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF03, RNF04 |
| **Precondiciones** | El Administrador tiene sesión iniciada. |
| **Postcondiciones** | La red de ciudades y sucursales queda actualizada y disponible para el resto del sistema. |

**Flujo principal**

1. El Administrador ingresa a la gestión de sucursales.
2. El sistema lista las ciudades con sus sucursales, indicando dirección, horario, capacidad de vestidores y estado.
3. El Administrador elige registrar una sucursal.
4. El sistema presenta el formulario: nombre, ciudad, dirección, teléfono, horario de atención, capacidad de vestidores y estado.
5. El Administrador completa los datos y confirma.
6. El sistema valida los datos y verifica que el nombre no se repita dentro de la misma ciudad.
7. El sistema registra la sucursal y la muestra en la lista.

**Flujos alternativos**

- **3a. Gestionar ciudades.** El Administrador registra o edita una ciudad con su nombre y departamento.
- **3b. Editar sucursal.** El sistema presenta los datos actuales, el Administrador los modifica y confirma.
- **3c. Dar de baja.** El sistema marca la sucursal como inactiva; deja de ofrecerse para reservas y compras, pero se conserva para la trazabilidad histórica.

**Excepciones**

- **E1. Nombre de sucursal duplicado en la ciudad.** El sistema lo impide y señala el campo.
- **E2. Baja de ciudad con sucursales activas.** El sistema impide dar de baja la ciudad e indica que primero deben darse de baja sus sucursales.
- **E3. Capacidad de vestidores no positiva.** El sistema rechaza el valor.

---

### CU-06 · Gestionar empleados

| Campo | Contenido |
|---|---|
| **Código** | CU-06 |
| **Nombre** | Gestionar empleados |
| **Descripción** | Permite al Administrador registrar empleados (encargados y cajeros) y asignarlos a una sucursal, vinculándolos a su usuario del sistema. |
| **Propósito** | Vincular a la persona con su tienda, que es lo que permite acotar el ámbito de datos de un Encargado o un Cajero a su propia sucursal. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P2 · Organización |
| **Prioridad** | Media |
| **Requisitos que realiza** | RF26, RNF01 |
| **Precondiciones** | El Administrador tiene sesión iniciada y existe al menos una sucursal activa. |
| **Postcondiciones** | El empleado queda registrado, asignado a una sucursal y vinculado a un usuario con el rol correspondiente. |

**Flujo principal**

1. El Administrador ingresa a la gestión de empleados.
2. El sistema lista los empleados con su nombre, cargo, sucursal y estado, con filtro por sucursal y por cargo.
3. El Administrador elige registrar un empleado.
4. El sistema presenta el formulario: nombres, apellidos, documento, teléfono, cargo (Encargado de Sucursal o Cajero), sucursal, fecha de ingreso y los datos de su usuario.
5. El Administrador completa los datos y confirma.
6. El sistema valida los datos, verifica que el documento no esté registrado y que la sucursal esté activa.
7. El sistema crea el usuario con el rol correspondiente al cargo y la sucursal indicada, y lo vincula a la ficha del empleado, todo en una única transacción.

**Flujos alternativos**

- **3a. Editar.** El Administrador modifica los datos del empleado o lo reasigna a otra sucursal; el sistema actualiza también la sucursal del usuario vinculado.
- **3b. Dar de baja.** El sistema registra la fecha de baja del empleado y desactiva su usuario, revocando sus tokens vigentes.
- **3c. Vincular a un usuario existente.** En lugar de crear un usuario nuevo, el Administrador selecciona uno ya existente sin empleado asociado.

**Excepciones**

- **E1. Documento ya registrado.** El sistema lo informa y devuelve el control al paso 5.
- **E2. Sucursal inactiva.** El sistema impide asignar un empleado a una sucursal dada de baja.
- **E3. Fallo parcial.** Si falla la creación del usuario o de la ficha, la transacción se revierte por completo.

---

### CU-07 · Gestionar proveedores

| Campo | Contenido |
|---|---|
| **Código** | CU-07 |
| **Nombre** | Gestionar proveedores |
| **Descripción** | Permite al Administrador registrar, editar y consultar proveedores con sus datos de contacto y los productos que abastecen. |
| **Propósito** | Estructurar la relación con los proveedores para poder asociarles productos y, más adelante, medir su rotación. |
| **Actores** | Administrador (iniciador) · Proveedor (consulta sus propios datos) |
| **Paquete** | P2 · Organización |
| **Prioridad** | Media |
| **Requisitos que realiza** | RF06 |
| **Precondiciones** | El Administrador tiene sesión iniciada. |
| **Postcondiciones** | El proveedor queda registrado y disponible para asociarse a productos en el Ciclo 2. |

**Flujo principal**

1. El Administrador ingresa a la gestión de proveedores.
2. El sistema lista los proveedores con su razón social, identificación tributaria, contacto y estado.
3. El Administrador elige registrar un proveedor.
4. El sistema presenta el formulario: razón social, identificación tributaria, persona de contacto, teléfono, correo, dirección y estado.
5. El Administrador completa los datos y confirma.
6. El sistema valida los datos y verifica que la identificación tributaria no esté registrada.
7. El sistema registra el proveedor y lo muestra en la lista.

**Flujos alternativos**

- **3a. Editar.** El Administrador modifica los datos del proveedor y confirma.
- **3b. Dar de baja.** El sistema marca el proveedor como inactivo; sus productos históricos se conservan.
- **3c. Habilitar acceso al Proveedor.** El Administrador crea un usuario con rol *Proveedor* vinculado a la ficha, con alcance limitado a sus propios productos.

**Excepciones**

- **E1. Identificación tributaria duplicada.** El sistema lo impide y señala el campo.
- **E2. Correo con formato inválido.** El sistema rechaza el valor.

---

### CU-08 · Gestionar categorías, tallas y colores

| Campo | Contenido |
|---|---|
| **Código** | CU-08 |
| **Nombre** | Gestionar categorías, tallas y colores |
| **Descripción** | Permite al Administrador mantener las categorías jerárquicas de prendas, el catálogo de tallas y el catálogo de colores utilizados en las variantes. |
| **Propósito** | Construir la taxonomía sin la cual no puede existir una variante de producto, y por lo tanto ni inventario, ni reserva, ni venta. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P3 · Catálogo (maestros) |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF05 |
| **Precondiciones** | El Administrador tiene sesión iniciada. |
| **Postcondiciones** | Las categorías, tallas y colores quedan disponibles para definir productos y variantes en el Ciclo 2. |

**Flujo principal**

1. El Administrador ingresa a los maestros del catálogo y elige *Categorías*.
2. El sistema muestra las categorías en forma de árbol, con su categoría padre, orden y estado.
3. El Administrador elige registrar una categoría.
4. El sistema presenta el formulario: nombre, categoría padre (opcional), orden de presentación y estado.
5. El Administrador completa los datos y confirma.
6. El sistema valida que el nombre no se repita entre las categorías hermanas y que la jerarquía no forme un ciclo.
7. El sistema registra la categoría y la muestra en el árbol.

**Flujos alternativos**

- **1a. Tallas.** El Administrador gestiona las tallas indicando su código (XS, S, M, L, XL, 38, 40…), su tipo de prenda y su orden, que es el que define cómo se muestran en la ficha de producto.
- **1b. Colores.** El Administrador gestiona los colores indicando su nombre y su valor hexadecimal, que la interfaz usa para mostrar la muestra de color.
- **3a. Editar.** El Administrador modifica un elemento existente y confirma.
- **3b. Desactivar.** El elemento deja de ofrecerse para nuevas variantes, pero se conserva en las existentes.

**Excepciones**

- **E1. Nombre o código duplicado.** El sistema lo impide y señala el campo.
- **E2. Ciclo en la jerarquía.** El sistema impide asignar como padre a una categoría descendiente de la que se está editando.
- **E3. Eliminación con dependencias.** El sistema impide eliminar una categoría con subcategorías o con productos asociados, y ofrece desactivarla.

---

### CU-09 · Gestionar temporadas y colecciones

| Campo | Contenido |
|---|---|
| **Código** | CU-09 |
| **Nombre** | Gestionar temporadas y colecciones |
| **Descripción** | Permite al Administrador registrar temporadas comerciales (primavera-verano, otoño-invierno, escolar, promociones, nuevas colecciones) con su vigencia, y las colecciones asociadas. |
| **Propósito** | Estructurar la dimensión temporal y comercial del catálogo, que es la que permite medir rotación por temporada y colección. |
| **Actores** | Administrador (iniciador) |
| **Paquete** | P3 · Catálogo (maestros) |
| **Prioridad** | Alta |
| **Requisitos que realiza** | RF05, RF23 |
| **Precondiciones** | El Administrador tiene sesión iniciada. |
| **Postcondiciones** | Las temporadas y colecciones quedan disponibles para asociarse a productos en el Ciclo 2; a lo sumo una temporada queda marcada como vigente. |

**Flujo principal**

1. El Administrador ingresa a los maestros del catálogo y elige *Temporadas*.
2. El sistema lista las temporadas con su nombre, fecha de inicio, fecha de fin, estado y si es la vigente.
3. El Administrador elige registrar una temporada.
4. El sistema presenta el formulario: nombre, descripción, fecha de inicio, fecha de fin y estado.
5. El Administrador completa los datos y confirma.
6. El sistema valida que la fecha de fin sea posterior a la de inicio y que el nombre no se repita.
7. El sistema registra la temporada y la muestra en la lista.

**Flujos alternativos**

- **1a. Colecciones.** El Administrador registra una colección indicando su nombre, su descripción y la temporada a la que pertenece.
- **3a. Editar.** El Administrador modifica una temporada o colección existente y confirma.
- **3b. Cerrar temporada.** El Administrador marca una temporada como cerrada; sus productos siguen siendo consultables pero dejan de considerarse de temporada vigente.

**Excepciones**

- **E1. Fechas incoherentes.** El sistema rechaza una fecha de fin anterior o igual a la de inicio.
- **E2. Solapamiento de temporadas vigentes.** Si el rango se superpone con otra temporada activa, el sistema advierte y pide confirmación explícita antes de guardar.
- **E3. Eliminación con dependencias.** El sistema impide eliminar una temporada con colecciones o productos asociados, y ofrece cerrarla.

---

## 1.5 Estructurar Modelo de Casos de Uso — CICLO #1

Estructurar el modelo consiste en identificar el comportamiento que se repite entre casos de uso
y extraerlo, de modo que cada conducta quede descrita una sola vez. Sobre los nueve casos de uso
del Ciclo 1 se aplican las tres relaciones de UML.

### Relaciones «include»

Un `include` indica que el caso de uso base **siempre** ejecuta al incluido; el incluido es
obligatorio y no tiene sentido por sí solo dentro de ese flujo.

| Caso de uso base | «include» | Justificación |
|---|---|---|
| CU-03 Gestionar usuarios y roles | **Autenticar usuario** | Toda operación administrativa exige identidad y rol verificados antes del primer paso. |
| CU-04 Gestionar perfil del cliente | **Autenticar usuario** | El perfil solo existe en el contexto de un cliente identificado. |
| CU-05 Gestionar ciudades y sucursales | **Autenticar usuario** | Ídem. |
| CU-06 Gestionar empleados | **Autenticar usuario** | Ídem. |
| CU-07 Gestionar proveedores | **Autenticar usuario** | Ídem. |
| CU-08 Gestionar categorías, tallas y colores | **Autenticar usuario** | Ídem. |
| CU-09 Gestionar temporadas y colecciones | **Autenticar usuario** | Ídem. |
| CU-06 Gestionar empleados | **CU-03 Gestionar usuarios y roles** | Registrar un empleado crea siempre su usuario con el rol correspondiente al cargo; es el mismo comportamiento, no una copia. |

> **Sobre *Autenticar usuario*.** Es un caso de uso de inclusión, no uno de los treinta y siete
> numerados: no produce por sí mismo un resultado de valor para un actor, sino que es la
> verificación del token que comparten todos los casos de uso internos. Se extrae precisamente
> para no repetir el mismo paso en cada tabla de detalle. CU-02 sí es un caso de uso completo,
> porque su resultado de valor —obtener y descartar la sesión— es visible para el actor.

### Relaciones «extend»

Un `extend` indica comportamiento **opcional**, que ocurre solo bajo cierta condición y en un
punto de extensión definido del caso de uso base.

| Caso de uso base | Punto de extensión | «extend» | Condición |
|---|---|---|---|
| CU-01 Registrar cliente | Tras crear la cuenta (paso 8) | **Verificar correo electrónico** | Solo si el registro se realizó con un correo que exige confirmación. |
| CU-01 Registrar cliente | Tras crear la cuenta (paso 8) | **CU-02 Iniciar sesión** | Solo si el registro se inició desde un flujo de reserva o compra que exigía identificación. |
| CU-04 Gestionar perfil del cliente | Durante la edición (paso 3) | **Cambiar contraseña** | Solo si el Cliente elige modificar su contraseña. |
| CU-03 Gestionar usuarios y roles | Al desactivar una cuenta | **Revocar sesiones activas** | Solo si el usuario desactivado tiene tokens vigentes. |
| CU-06 Gestionar empleados | Al dar de baja al empleado | **Revocar sesiones activas** | Ídem. |

### Generalización

**De actores.** Administrador, Encargado de Sucursal y Cajero comparten el hecho de ser personal
interno que se autentica con credenciales corporativas y opera dentro de un ámbito de datos
definido por su rol. Se modela un actor abstracto **Usuario interno** del que los tres heredan.
Cliente y Proveedor no heredan de él: el Cliente se autorregistra y el Proveedor tiene acceso
restringido a sus propios datos.

**Qué gana el modelo con esto.** CU-02 lo usan los **cinco** actores humanos. Sin la
generalización harían falta cinco asociaciones; con ella bastan dos —Cliente y Proveedor— más la
de *Usuario interno*, porque Administrador, Encargado y Cajero heredan las asociaciones de su
actor padre. El diagrama de CU-02 dibuja igual a los tres concretos con su relación de herencia,
para que se entienda sin tener al lado el modelo estructurado, pero **ninguno lleva línea propia
al caso de uso**: sería redundante.

```
        Usuario interno  (abstracto)
              △
    ┌─────────┼─────────┐
Administrador  Encargado  Cajero
             de Sucursal
```

**De casos de uso.** Los siete casos de uso de mantenimiento del Ciclo 1 —CU-03, CU-05, CU-06,
CU-07, CU-08 y CU-09— comparten la misma estructura: listar con filtros, crear, editar y
desactivar una entidad maestra, con validación de unicidad y control de dependencias antes de
eliminar. Se modela un caso de uso abstracto **Gestionar entidad maestra** del que todos
heredan, y cada uno especializa las validaciones propias de su entidad. Esta generalización es la
que justifica que en el diseño exista un servicio y un repositorio genéricos reutilizados por los
seis, en lugar de seis implementaciones equivalentes.

### Agrupación por paquete

| Paquete | Casos de uso del Ciclo 1 |
|---|---|
| **P1 · Seguridad y Usuarios** | CU-01, CU-02, CU-03, CU-04 · más *Autenticar usuario* como caso de uso de inclusión |
| **P2 · Organización** | CU-05, CU-06, CU-07 |
| **P3 · Catálogo (maestros)** | CU-08, CU-09 |

La dirección de las dependencias es **P3 → P2 → P1**, nunca a la inversa: P2 depende de P1 para
vincular empleados y proveedores con sus usuarios, y P3 no depende de ninguno de los dos en sus
maestros —solo de P1 para la autorización—. Esta es la misma regla que ordena el árbol de
carpetas del backend.
