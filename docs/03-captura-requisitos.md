# 3) FLUJO DE TRABAJO: CAPTURA DE REQUISITOS

Primer flujo de trabajo del PUDS. Se identifican los actores del sistema, se enuncian los casos de
uso, se priorizan y se distribuyen en los ciclos de desarrollo. El detalle completo de cada caso
de uso (descripción, propósito, actores, precondiciones, flujo principal, postcondiciones y
excepciones) se desarrolla por ciclo en el documento de entrega.

---

## 3.1 Encontrar actores y casos de uso

### 3.1.1 Actores

| Código | Actor | Tipo | Descripción |
|---|---|---|---|
| **A1** | **Cliente** | Humano, primario | Persona que consulta el catálogo, utiliza el vestidor virtual, reserva prendas para probarlas en una sucursal, compra desde la web o la app móvil y paga electrónicamente. Se autorregistra en el sistema. Es el actor con mayor volumen de interacción y el destinatario de las funcionalidades de IA. |
| **A2** | **Administrador** | Humano, primario | Usuario con acceso completo. Gestiona usuarios y roles, ciudades y sucursales, empleados, proveedores, el catálogo completo (productos, variantes, categorías, tallas, colores, temporadas, colecciones), las promociones, el inventario consolidado de toda la red y los reportes e indicadores empresariales. |
| **A3** | **Encargado de Sucursal** | Humano, primario | Responsable operativo de una sucursal. Recibe y consulta las reservas dirigidas a su sucursal, prepara las prendas reservadas, confirma la llegada del cliente y la atención de la reserva, gestiona la disponibilidad de prendas de su tienda, registra ingresos y movimientos de inventario y consulta las ventas de su sucursal. Su ámbito de datos está restringido a su sucursal. |
| **A4** | **Cajero** | Humano, primario | Opera el punto de venta de una sucursal. Abre y cierra su caja, consulta productos, registra ventas presenciales —incluidas las originadas en una reserva atendida—, procesa el cobro en efectivo o tarjeta, emite comprobantes y registra devoluciones. |
| **A5** | **Proveedor** | Humano, secundario | Empresa que abastece prendas. Registra o envía la información de los productos que provee, informa su disponibilidad y asocia sus productos a temporadas y colecciones. Su acceso es de alcance limitado a sus propios productos. |
| **A6** | **Sistema (procesos automáticos)** | No humano, interno | Representa los procesos que el sistema ejecuta sin intervención humana: actualización automática de existencias tras cada operación, expiración de reservas vencidas con liberación de stock, confirmación del pedido al recibir la notificación de pago, cálculo de KPIs y generación de alertas de stock bajo. |
| **A7** | **Pasarela de Pago** | No humano, externo | Servicio externo que procesa los pagos electrónicos en entorno de pruebas. Recibe la solicitud de cobro, procesa la transacción, la aprueba o rechaza y notifica el resultado al sistema mediante *webhook*. |
| **A8** | **Servicio de Inteligencia Artificial** | No humano, externo | Servicio de IA consumido vía API. Analiza preferencias y genera recomendaciones de prendas, sostiene la conversación del asistente virtual y produce los reportes generativos bajo demanda solicitados por comando de voz. |
| **A9** | **Servicio de Realidad Aumentada** | No humano, externo | Componente del dispositivo móvil (cámara, detección de pose corporal) sobre el que se construye el vestidor virtual. Provee al sistema la posición del cuerpo del usuario para superponer la prenda seleccionada. |

**Correspondencia con el enunciado.** Los actores **A1 a A5, A7 y A8** son los siete actores
principales listados en el enunciado (§4): Cliente, Administrador, Encargado de sucursal, Cajero,
Proveedor, Sistema de pagos y Servicio de inteligencia artificial. Se conservan con esos nombres
y esas responsabilidades. El equipo incorpora dos actores adicionales:

- **A6 · Sistema (procesos automáticos).** El enunciado exige comportamientos que ocurren sin
  intervención humana —la actualización automática del inventario (RF20) y la confirmación del
  pago— pero no los atribuye a ningún actor. Modelarlos como actor permite que los casos de uso
  CU-25 y CU-28 tengan un iniciador explícito.
- **A9 · Servicio de Realidad Aumentada.** El enunciado exige el vestidor virtual (RF13) sin
  nombrar el componente que provee la detección de pose corporal. Se modela como actor externo
  por simetría con A7 y A8, que también son servicios consumidos por el sistema.

**Nota sobre A5 (Proveedor).** El enunciado lo lista como actor principal. En este proyecto su
participación se modela con alcance acotado (registro y consulta de sus productos y su
disponibilidad); el ciclo de órdenes de compra queda fuera del alcance —ver §1.4.2.

### 3.1.2 Casos de uso

| ID | Nombre | Descripción |
|---|---|---|
| CU-01 | Registrar cliente | Permite a una persona crear su cuenta de cliente indicando sus datos personales, correo y contraseña, quedando habilitada para reservar y comprar. |
| CU-02 | Iniciar y cerrar sesión | Permite a cualquier usuario autenticarse con correo y contraseña obteniendo un token de acceso acorde a su rol; el cierre de sesión invalida el token. |
| CU-03 | Gestionar usuarios y roles | Permite al Administrador crear, editar, activar/desactivar y eliminar cuentas de usuario, asignando su rol y, cuando corresponde, su sucursal. |
| CU-04 | Gestionar perfil del cliente | Permite al Cliente consultar y modificar sus datos personales, sus tallas habituales, sus preferencias y sus direcciones de entrega. |
| CU-05 | Gestionar ciudades y sucursales | Permite al Administrador registrar, editar y dar de baja ciudades y sucursales, con su dirección, horario de atención y capacidad de vestidores. |
| CU-06 | Gestionar empleados | Permite al Administrador registrar empleados (encargados y cajeros) y asignarlos a una sucursal, vinculándolos a su usuario del sistema. |
| CU-07 | Gestionar proveedores | Permite al Administrador registrar, editar y consultar proveedores con sus datos de contacto y los productos que abastecen. |
| CU-08 | Gestionar categorías, tallas y colores | Permite al Administrador mantener las categorías jerárquicas de prendas, el catálogo de tallas y el catálogo de colores utilizados en las variantes. |
| CU-09 | Gestionar temporadas y colecciones | Permite al Administrador registrar temporadas comerciales (primavera-verano, otoño-invierno, escolar, promociones, nuevas colecciones) con su vigencia, y las colecciones asociadas. |
| CU-10 | Gestionar productos y variantes | Permite al Administrador registrar un producto con su descripción, categoría, proveedor, temporada y colección, y generar sus variantes (SKU) por combinación de talla y color, cada una con su precio y código. |
| CU-11 | Gestionar imágenes de producto | Permite al Administrador cargar, ordenar y eliminar las imágenes de un producto, incluyendo la imagen con fondo transparente que utiliza el vestidor virtual. |
| CU-12 | Gestionar promociones | Permite al Administrador definir descuentos con vigencia aplicables a un producto, una categoría o una temporada. |
| CU-13 | Registrar ingreso de mercadería | Permite al Administrador o al Encargado registrar la recepción de prendas enviadas por un proveedor a una sucursal, generando el movimiento de inventario de tipo ingreso. |
| CU-14 | Consultar inventario consolidado | Permite al Administrador consultar las existencias de toda la red por producto, variante y sucursal, con su estado (disponible, reservado, agotado, próximo a ingresar). |
| CU-15 | Registrar movimiento de inventario | Permite registrar ajustes por conteo físico y transferencias de mercadería entre sucursales, dejando trazabilidad del motivo, el usuario y la fecha. |
| CU-16 | Gestionar disponibilidad de la sucursal | Permite al Encargado consultar y ajustar la disponibilidad de las prendas de su propia sucursal y consultar sus alertas de stock bajo. |
| CU-17 | Consultar catálogo | Permite al Cliente navegar el catálogo desde la web o la app móvil, buscar por texto y filtrar por categoría, talla, color, temporada, colección, precio y sucursal. |
| CU-18 | Consultar ficha de producto | Permite al Cliente ver el detalle de una prenda con su galería de imágenes, descripción y precio, y seleccionar la talla y el color deseados. |
| CU-19 | Consultar disponibilidad por sucursal | Permite al Cliente conocer en qué sucursales está disponible la variante seleccionada y en qué cantidad. |
| CU-20 | Gestionar favoritos | Permite al Cliente marcar prendas como favoritas y consultar posteriormente su lista. |
| CU-21 | Utilizar vestidor virtual (RA) | Permite al Cliente, desde la app móvil, activar la cámara y visualizar sobre su propia imagen la prenda seleccionada, cambiar talla y color, capturar el resultado y agregar la prenda a la reserva o al carrito. |
| CU-22 | Crear reserva de prendas | Permite al Cliente seleccionar varias prendas (variantes), elegir la sucursal donde desea probarlas y una franja horaria, y confirmar la reserva; el sistema descuenta el stock disponible y lo registra como reservado. |
| CU-23 | Consultar y cancelar reserva | Permite al Cliente consultar el estado y el detalle de sus reservas y cancelar aquellas aún no atendidas, liberando el stock reservado. |
| CU-24 | Atender reserva en sucursal | Permite al Encargado consultar las reservas dirigidas a su sucursal, marcarlas como preparadas, confirmar la llegada del cliente, registrar el resultado de la prueba y cerrar la reserva derivándola a venta o liberando el stock. |
| CU-25 | Expirar reservas vencidas | El Sistema detecta las reservas cuya franja horaria venció sin atención, las marca como expiradas y devuelve el stock reservado a disponible. |
| CU-26 | Gestionar carrito de compras | Permite al Cliente agregar variantes al carrito, modificar cantidades, eliminar ítems y ver el total con las promociones aplicadas. |
| CU-27 | Realizar pedido y pagar en línea | Permite al Cliente confirmar el contenido del carrito, elegir la modalidad de entrega (retiro en sucursal o envío a domicilio), generar el pedido e iniciar el pago a través de la pasarela electrónica. |
| CU-28 | Confirmar pago del pedido | El Sistema recibe la notificación de la Pasarela de Pago, valida su autenticidad, actualiza el estado del pedido a pagado y descuenta el inventario de la sucursal que lo abastece. |
| CU-29 | Consultar historial de compras | Permite al Cliente consultar sus pedidos anteriores, su estado actual y descargar el comprobante digital de cada uno. |
| CU-30 | Abrir y cerrar caja | Permite al Cajero abrir su turno con un monto inicial y cerrarlo registrando el arqueo, obteniendo el resumen de las ventas del turno. |
| CU-31 | Registrar venta presencial | Permite al Cajero registrar una venta en sucursal buscando las variantes o cargando una reserva ya atendida, cobrar en efectivo o tarjeta, emitir el comprobante y descontar el inventario. |
| CU-32 | Registrar devolución | Permite al Cajero registrar la devolución de una prenda vendida, reingresándola al inventario de la sucursal con su movimiento correspondiente. |
| CU-33 | Recibir recomendaciones de prendas | El Sistema, apoyado en el Servicio de IA, sugiere al Cliente prendas acordes a su historial de navegación y compra, su talla habitual, la temporada vigente, la categoría consultada y la disponibilidad real. |
| CU-34 | Conversar con el asistente virtual | Permite al Cliente formular consultas en lenguaje natural sobre el catálogo, la disponibilidad y el estado de sus pedidos y reservas; el asistente responde consultando los datos reales del sistema. |
| CU-35 | Generar reporte por comando de voz | Permite al Administrador solicitar un reporte en lenguaje natural mediante comando de voz; el sistema interpreta la solicitud, consulta los datos y devuelve el reporte generado, con opción de descarga. |
| CU-36 | Consultar tablero de indicadores | Permite al Administrador visualizar los KPIs del negocio en tiempo real: ventas del día y del mes, ticket promedio, reservas pendientes y atendidas, conversión de reserva a venta, productos más vendidos y stock crítico. |
| CU-37 | Generar reportes de gestión | Permite al Administrador y al Encargado generar y descargar en PDF y Excel los reportes de ventas, inventario, movimientos, reservas, rendimiento por temporada/colección y compras por proveedor. |

## 3.2 Priorizar los casos de uso

Criterio de priorización aplicado: **Alta** = indispensable para el MVP y bloqueante de otros
casos de uso; **Media** = necesaria para completar la funcionalidad exigida pero no bloqueante;
**Baja** = complementaria, se implementa si el plazo lo permite.

| ID | Nombre | Prioridad | Ciclo | Paquete |
|---|---|---|---|---|
| CU-01 | Registrar cliente | Alta | 1 | Seguridad |
| CU-02 | Iniciar y cerrar sesión | Alta | 1 | Seguridad |
| CU-03 | Gestionar usuarios y roles | Alta | 1 | Seguridad |
| CU-04 | Gestionar perfil del cliente | Media | 1 | Seguridad |
| CU-05 | Gestionar ciudades y sucursales | Alta | 1 | Organización |
| CU-06 | Gestionar empleados | Media | 1 | Organización |
| CU-07 | Gestionar proveedores | Media | 1 | Organización |
| CU-08 | Gestionar categorías, tallas y colores | Alta | 1 | Catálogo |
| CU-09 | Gestionar temporadas y colecciones | Alta | 1 | Catálogo |
| CU-10 | Gestionar productos y variantes | Alta | 2 | Catálogo |
| CU-11 | Gestionar imágenes de producto | Alta | 2 | Catálogo |
| CU-12 | Gestionar promociones | Media | 3 | Catálogo |
| CU-13 | Registrar ingreso de mercadería | Alta | 2 | Inventario |
| CU-14 | Consultar inventario consolidado | Alta | 2 | Inventario |
| CU-15 | Registrar movimiento de inventario | Media | 2 | Inventario |
| CU-16 | Gestionar disponibilidad de la sucursal | Media | 2 | Inventario |
| CU-17 | Consultar catálogo | Alta | 2 | Catálogo Público |
| CU-18 | Consultar ficha de producto | Alta | 2 | Catálogo Público |
| CU-19 | Consultar disponibilidad por sucursal | Alta | 2 | Catálogo Público |
| CU-20 | Gestionar favoritos | Baja | 3 | Catálogo Público |
| CU-21 | Utilizar vestidor virtual (RA) | Alta | 3 | Vestidor Virtual |
| CU-22 | Crear reserva de prendas | Alta | 2 | Reservas |
| CU-23 | Consultar y cancelar reserva | Alta | 2 | Reservas |
| CU-24 | Atender reserva en sucursal | Alta | 2 | Reservas |
| CU-25 | Expirar reservas vencidas | Media | 2 | Reservas |
| CU-26 | Gestionar carrito de compras | Alta | 3 | Ventas |
| CU-27 | Realizar pedido y pagar en línea | Alta | 3 | Ventas / Pagos |
| CU-28 | Confirmar pago del pedido | Alta | 3 | Pagos |
| CU-29 | Consultar historial de compras | Media | 3 | Ventas |
| CU-30 | Abrir y cerrar caja | Media | 3 | Punto de Venta |
| CU-31 | Registrar venta presencial | Alta | 3 | Punto de Venta |
| CU-32 | Registrar devolución | Baja | 3 | Punto de Venta |
| CU-33 | Recibir recomendaciones de prendas | Alta | 3 | Inteligencia Artificial |
| CU-34 | Conversar con el asistente virtual | Media | 3 | Inteligencia Artificial |
| CU-35 | Generar reporte por comando de voz | Media | 3 | Inteligencia Artificial |
| CU-36 | Consultar tablero de indicadores | Alta | 3 | Reportes |
| CU-37 | Generar reportes de gestión | Alta | 3 | Reportes |

### Distribución por ciclos

El proyecto se organiza en **tres ciclos**, uno por cada presentación obligatoria. El Ciclo 1 es
deliberadamente **el más corto**: arranca el 01/09 y cierra el 05/09, cuatro días.

**CICLO 1 — Fundamentos (9 casos de uso: CU-01 a CU-09).** Presentación #1, 05/09.
Seguridad e identidad (registro, autenticación, roles y perfil), estructura organizacional
(ciudades, sucursales, empleados, proveedores) y los **maestros del catálogo** (categorías,
tallas, colores, temporadas y colecciones). Es el cimiento sobre el que se apoya todo lo demás:
sin usuarios con rol, sin sucursales y sin la taxonomía de tallas y colores no puede existir una
variante de producto, y sin variante no hay inventario, ni reserva, ni venta. Nueve casos de uso
de CRUD y autenticación, sin reglas de negocio complejas — es lo que cabe en cuatro días.

**CICLO 2 — Núcleo del negocio (13 casos de uso: CU-10, CU-11, CU-13 a CU-19, CU-22 a CU-25).**
Presentación #2, 13/09.
Productos y sus **variantes (SKU)** con imágenes, el **inventario multisucursal** con movimientos
trazables, el **catálogo público** con búsqueda, filtros y consulta de disponibilidad por
sucursal, y el ciclo completo de **reservas** para prueba presencial. Es el núcleo arquitectónico
y el que concentra las reglas de negocio duras del sistema (traslado disponible ↔ reservado,
movimientos inmutables, expiración automática). Resuelve los problemas P1, P2, P5, P8 y P13.

**CICLO 3 — Comercio, experiencia e inteligencia (15 casos de uso: CU-12, CU-20, CU-21, CU-26 a
CU-37).** Presentación final, 20/09.
Promociones, favoritos, **vestidor virtual con realidad aumentada**, carrito y **venta digital con
pasarela de pago**, **punto de venta presencial**, **inteligencia artificial** (recomendador,
asistente conversacional y reportes por comando de voz) y el **tablero de indicadores** con los
reportes exportables. Completa el ciclo de vida comercial y resuelve los problemas P3, P4, P6, P9
y P11.

| Ciclo | Entrega | Días | Casos de uso | Carácter |
|---|---|:---:|:---:|---|
| 1 | 05/09 | 4 | 9 | Fundamentos — CRUD y autenticación |
| 2 | 13/09 | 8 | 13 | Núcleo — reglas de negocio del inventario y las reservas |
| 3 | 20/09 | 7 | 15 | Diferenciadores — RA, IA, pagos, POS y reportes |

> **Advertencia sobre el Ciclo 3.** Es el más cargado y contiene lo técnicamente más incierto
> (realidad aumentada, integración de pagos, IA). Dos mitigaciones están previstas en el plan: los
> casos de uso de prioridad **Baja** (CU-20 Favoritos y CU-32 Devoluciones) son los primeros en
> sacrificarse si el plazo aprieta, y el **prototipo aislado del vestidor virtual** se construye
> durante el Ciclo 2, en paralelo, no cuando empieza el Ciclo 3.

## 3.3 Requisitos funcionales

### 3.3.1 Requisitos funcionales del enunciado

Transcritos **literalmente** del enunciado (§5). La numeración RF01 a RF25 respeta el orden
original. La última columna traza cada requisito con los casos de uso que lo realizan.

| RF | Requisito funcional (textual del enunciado) | Casos de uso |
|---|---|---|
| **RF01** | El sistema deberá permitir registrar clientes. | CU-01, CU-04 |
| **RF02** | El sistema deberá permitir gestionar usuarios y roles. | CU-02, CU-03 |
| **RF03** | El sistema deberá administrar múltiples ciudades y sucursales. | CU-05 |
| **RF04** | El sistema deberá permitir gestionar productos de ropa. | CU-10, CU-11 |
| **RF05** | El sistema deberá gestionar tallas, colores, categorías y temporadas. | CU-08, CU-09, CU-10 |
| **RF06** | El sistema deberá gestionar proveedores. | CU-07, CU-13 |
| **RF07** | El cliente deberá poder consultar el catálogo desde web y móvil. | CU-17, CU-18 |
| **RF08** | El cliente deberá poder consultar disponibilidad por sucursal. | CU-19 |
| **RF09** | El cliente deberá poder seleccionar múltiples prendas para una reserva. | CU-22 |
| **RF10** | El sistema deberá registrar y gestionar reservas. | CU-22, CU-23, CU-24, CU-25 |
| **RF11** | El sistema deberá notificar las reservas a la sucursal correspondiente. | CU-22, CU-24 |
| **RF12** | El sistema deberá permitir consultar el estado de una reserva. | CU-23, CU-24 |
| **RF13** | La aplicación móvil deberá permitir utilizar el vestidor virtual. | CU-21 |
| **RF14** | El cliente deberá poder agregar productos al carrito. | CU-26 |
| **RF15** | El cliente deberá poder comprar mediante la plataforma web. | CU-26, CU-27, CU-28 |
| **RF16** | El cliente deberá poder comprar mediante la aplicación móvil. | CU-26, CU-27, CU-28 |
| **RF17** | El cajero deberá poder registrar ventas presenciales. | CU-31 |
| **RF18** | El sistema deberá permitir pagos en punto de caja. | CU-30, CU-31 |
| **RF19** | El sistema deberá integrar una pasarela de pago para compras digitales. | CU-27, CU-28 |
| **RF20** | El sistema deberá actualizar automáticamente el inventario después de una venta. | CU-28, CU-31, CU-32 |
| **RF21** | El sistema deberá controlar las existencias por sucursal. | CU-14, CU-16, CU-19 |
| **RF22** | El sistema deberá registrar movimientos de inventario. | CU-13, CU-15, CU-25, CU-28, CU-31, CU-32 |
| **RF23** | El sistema deberá gestionar temporadas y colecciones. | CU-09 |
| **RF24** | El sistema deberá permitir consultar reportes de ventas e inventario. | CU-36, CU-37 |
| **RF25** | El sistema deberá proporcionar al menos una funcionalidad basada en inteligencia artificial. | CU-33, CU-34, CU-35 |

**Cobertura:** los veinticinco requisitos funcionales del enunciado quedan cubiertos por al menos
un caso de uso.

### 3.3.2 Requisitos funcionales adicionales del equipo

Al detallar los casos de uso aparecieron operaciones necesarias para cerrar el ciclo de vida de
los procesos exigidos, que el enunciado no enuncia como requisito. Se formulan como requisitos
adicionales numerados a continuación de los originales.

| RF | Requisito funcional adicional | Casos de uso | Por qué se agrega |
|---|---|---|---|
| **RF26** | El sistema deberá permitir registrar empleados y asignarlos a una sucursal. | CU-06 | El RF03 administra sucursales y el RF02 usuarios, pero nadie vincula a la persona con su tienda. Sin esto no puede acotarse el ámbito de datos de un Encargado o un Cajero. |
| **RF27** | El sistema deberá permitir registrar el ingreso de mercadería enviada por un proveedor a una sucursal. | CU-13 | El OE-11 exige actualizar el inventario tras la *recepción de productos*, pero ningún RF define esa operación. |
| **RF28** | El sistema deberá permitir registrar transferencias de mercadería entre sucursales y ajustes por conteo físico. | CU-15 | El RF22 exige registrar movimientos; estos dos tipos son los que permiten corregir el desbalance entre sucursales (problema P8). |
| **RF29** | El cliente deberá poder cancelar una reserva mientras no haya sido atendida. | CU-23 | El RF10 gestiona reservas y el RF12 consulta su estado, pero sin cancelación el stock queda retenido hasta expirar. |
| **RF30** | El sistema deberá liberar automáticamente el stock de las reservas que venzan sin ser atendidas. | CU-25 | Sin expiración, cada reserva no atendida inmoviliza inventario de forma indefinida. |
| **RF31** | El cliente deberá poder marcar prendas como favoritas y consultar su lista. | CU-20 | Alimenta el historial de preferencias que necesita el recomendador del RF25. |
| **RF32** | El cliente deberá poder consultar el historial y el estado de sus pedidos y descargar su comprobante. | CU-29 | Los RF15 y RF16 permiten comprar, pero nada permite al cliente saber después qué pasó con su pedido. |
| **RF33** | El cajero deberá poder abrir y cerrar su caja por turno, registrando el arqueo. | CU-30 | El RF18 permite cobrar en caja; sin apertura y cierre de turno el dinero cobrado no es atribuible ni cuadrable. |
| **RF34** | El cajero deberá poder registrar devoluciones de prendas vendidas, reingresándolas al inventario. | CU-32 | El OE-11 exige actualizar el inventario tras *devoluciones*, operación que ningún RF define. |
| **RF35** | El sistema deberá permitir gestionar promociones y descuentos con vigencia, aplicables a un producto, una categoría o una temporada. | CU-12 | El enunciado incluye "gestionar promociones" entre las funciones del Administrador (§4), pero no lo formula como RF. |
| **RF36** | El sistema deberá permitir exportar los reportes en formato PDF y Excel. | CU-37 | El RF24 exige consultar reportes; la exportación es lo que los vuelve utilizables fuera del sistema. |

## 3.4 Requisitos no funcionales

### 3.4.1 Requisitos no funcionales del enunciado

Transcritos **literalmente** del enunciado (§6).

| RNF | Requisito no funcional (textual del enunciado) | Cómo se realiza en la arquitectura |
|---|---|---|
| **RNF01** | **Seguridad:** las contraseñas y datos sensibles deberán protegerse adecuadamente. | Hash de contraseñas con bcrypt; autenticación por token JWT con expiración; autorización por rol verificada en cada endpoint; secretos gestionados por variables de entorno, nunca en el repositorio; HTTPS obligatorio en todos los entornos desplegados. |
| **RNF02** | **Rendimiento:** las consultas del catálogo deberán responder en tiempos adecuados. | Índices sobre las columnas de filtrado y búsqueda; paginación obligatoria en todo listado; carga diferida de relaciones; caché de las consultas de catálogo más frecuentes; imágenes servidas desde almacenamiento de objetos, no desde la aplicación. |
| **RNF03** | **Disponibilidad:** el sistema deberá estar disponible para usuarios web y móviles. | Despliegue en la nube con URL pública y HTTPS; una única API REST que atiende indistintamente a la web y a la app móvil; base de datos gestionada con respaldos automáticos. |
| **RNF04** | **Escalabilidad:** la arquitectura deberá permitir incorporar nuevas sucursales y ciudades. | Ciudad y sucursal son entidades de datos, no configuración del código; el inventario se modela por (variante, sucursal), de modo que agregar una sucursal es una operación de datos; backend sin estado, replicable horizontalmente. |
| **RNF05** | **Usabilidad:** las interfaces deberán ser intuitivas y adaptables a diferentes dispositivos. | Diseño responsivo en Angular; navegación por rol; validación en formulario con mensajes claros; app Flutter con navegación nativa; consistencia visual entre web y móvil. |
| **RNF06** | **Mantenibilidad:** el código deberá organizarse en módulos y seguir buenas prácticas. | Organización del backend por paquetes correspondientes a los paquetes de análisis; separación en capas (router → servicio → repositorio → modelo); esquemas Pydantic para validación de entrada y salida; control de versiones con Git y revisión por Pull Request. |
| **RNF07** | **Integración:** FastAPI deberá proporcionar servicios mediante API REST. | API REST versionada (`/api/v1`) con documentación OpenAPI generada automáticamente; contratos JSON estables consumidos por Angular y Flutter. |
| **RNF08** | **Compatibilidad:** la aplicación móvil deberá desarrollarse utilizando Flutter/Dart. | Único código fuente Flutter para Android; cliente HTTP compartido y modelos de datos derivados del contrato de la API. |
| **RNF09** | **Seguridad transaccional:** las operaciones de pago deberán utilizar mecanismos seguros y, para el proyecto académico, entornos de prueba. | Pasarela integrada en modo sandbox; el sistema nunca almacena datos de tarjeta —el cobro ocurre en el dominio de la pasarela—; el estado del pedido se confirma exclusivamente por webhook firmado y verificado, nunca por la redirección del navegador; idempotencia en el procesamiento de la notificación de pago. |

### 3.4.2 Requisitos no funcionales adicionales del equipo

| RNF | Requisito no funcional adicional | Justificación |
|---|---|---|
| **RNF10** | **Trazabilidad:** toda modificación de existencias deberá quedar registrada como un movimiento inmutable con tipo, motivo, usuario y fecha. | Deriva del problema P5 del modelo de negocio; sin él no hay auditoría ni explicación posible de las diferencias de inventario. |
| **RNF11** | **Consistencia transaccional:** la reserva, la venta y la confirmación de pago deberán ejecutarse en una transacción con bloqueo de la fila de existencia. | Evita la sobreventa cuando dos clientes compiten por la última unidad de una variante. |
| **RNF12** | **Restricción tecnológica:** no deberán utilizarse frameworks de tipo e-commerce (PrestaShop, Shopify, Magento, WooCommerce y similares). | Exigencia explícita del enunciado (*TOMAR EN CUENTA*). |
| **RNF13** | **Despliegue:** el sistema deberá desplegarse en la nube; la demostración y la defensa se realizarán sobre el sistema desplegado, no sobre localhost. | Exigencia explícita del enunciado (*TOMAR EN CUENTA*). |
