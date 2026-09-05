# 1) PERFIL DEL PROYECTO

**Proyecto:** Violet Boutique — Plataforma Inteligente de Comercio Electrónico para Tienda de Ropa con Vestidores Virtuales vía Realidad Aumentada
**Materia:** Sistemas de Información II — Examen 1, S2-2026
**Docente:** MSc. Ing. Angélica Garzón Cuéllar
**Grupo (2 integrantes):**

| Integrante | Registro | Rol principal propuesto |
|---|---|---|
| Mateo Hurtado Castro | 222008687 | Backend (FastAPI + PostgreSQL), IA, despliegue |
| Karen Paola Ortega Mancilla | 222056592 | Frontend web (Angular), App móvil (Flutter), RA |

**Metodología:** Proceso Unificado de Desarrollo de Software (PUDS)
**Modelado:** UML 2.5+

---

## 1.1 Introducción

El comercio minorista de prendas de vestir atraviesa una transformación impulsada por la
convergencia entre el canal físico y el digital. Las cadenas de tiendas de ropa que operan
múltiples sucursales en distintas ciudades enfrentan hoy un doble desafío: por un lado, mantener
un control unificado y en tiempo real de un inventario que se fragmenta por producto, talla,
color, sucursal y temporada; por el otro, ofrecer una experiencia de compra que el cliente ya
espera encontrar de manera indistinta desde su teléfono, desde un navegador o dentro de la
tienda física.

La cadena de tiendas de ropa objeto de este proyecto opera actualmente con sistemas
desarticulados: cada sucursal gestiona sus existencias de forma local, el cliente no puede
conocer con antelación si la prenda que le interesa está disponible en su talla y color en la
sucursal más cercana, y la empresa carece de información consolidada para decidir compras a
proveedores, reposiciones entre sucursales o el lanzamiento de nuevas colecciones. A esto se
suma una fricción propia del rubro: el cliente necesita probarse la prenda antes de decidir, lo
que lo obliga a desplazarse a la tienda sin ninguna garantía de que la prenda le quede bien o
esté disponible al llegar.

El presente proyecto propone el desarrollo de **Violet Boutique**, una plataforma inteligente de
comercio electrónico que integra en una sola solución el catálogo multicanal (web y móvil), la
consulta de disponibilidad por sucursal, la reserva de prendas para prueba presencial, la venta
digital con pasarela de pago, la venta presencial en punto de caja, la gestión de proveedores,
temporadas y colecciones, y el control unificado de inventario. Como elementos diferenciadores,
la plataforma incorpora un **vestidor virtual mediante realidad aumentada**, que permite al
cliente visualizar sobre su propia imagen cómo luciría una prenda antes de reservarla, y
**funcionalidades de inteligencia artificial** —un asistente/recomendador de prendas y la
generación de reportes bajo demanda por comando de voz— que apoyan tanto la decisión de compra
del cliente como la toma de decisiones de la administración.

El desarrollo se conduce bajo el **Proceso Unificado de Desarrollo de Software (PUDS)**, un
proceso iterativo e incremental, dirigido por casos de uso y centrado en la arquitectura, cuyos
flujos de trabajo (Captura de Requisitos, Análisis, Diseño, Implementación y Pruebas) se recorren
en ciclos sucesivos. El modelado de todos los artefactos se realiza con **UML 2.5+**.

## 1.2 Objetivos

### 1.2.1 Objetivo General

> Desarrollar una plataforma inteligente de comercio electrónico para una cadena de tiendas de
> ropa, que integre comercio electrónico web y móvil, reservas de prendas, gestión de sucursales,
> inventario, puntos de venta, pagos electrónicos, vestidores virtuales mediante realidad
> aumentada e inteligencia artificial, utilizando el Proceso Unificado de Desarrollo y modelos
> UML.

*(Transcrito literalmente del enunciado, §2.)*

### 1.2.2 Objetivos Específicos

#### a) Objetivos específicos del enunciado

Transcritos **literalmente** del enunciado (§3). La numeración OE-01 a OE-16 respeta el orden
original. La última columna indica dónde se realiza cada uno dentro del proyecto.

| Código | Objetivo específico (textual del enunciado) | Se realiza en |
|---|---|---|
| **OE-01** | Analizar y especificar los requisitos funcionales y no funcionales del sistema. | Flujo de Captura de Requisitos (doc. 03) |
| **OE-02** | Gestionar clientes, usuarios, empleados, proveedores y sucursales. | Paquetes P1 y P2 · CU-01 a CU-07 |
| **OE-03** | Administrar el catálogo de prendas, categorías, tallas, colores, temporadas y colecciones. | Paquete P3 · CU-08 a CU-11 |
| **OE-04** | Consultar la disponibilidad de prendas por sucursal. | Paquetes P4 y P5 · CU-14, CU-19 |
| **OE-05** | Permitir al cliente reservar varias prendas para probarlas posteriormente en una tienda. | Paquete P6 · CU-22 |
| **OE-06** | Gestionar el proceso de recepción y atención de reservas. | Paquete P6 · CU-23, CU-24, CU-25 |
| **OE-07** | Incorporar vestidores virtuales utilizando realidad aumentada. | Paquete P9 · CU-21 |
| **OE-08** | Permitir compras mediante la plataforma web y aplicación móvil. | Paquete P7 · CU-26, CU-27 |
| **OE-09** | Permitir pagos presenciales en puntos de caja. | Paquete P7 · CU-30, CU-31 |
| **OE-10** | Integrar una pasarela de pago para compras digitales. | Paquete P8 · CU-27, CU-28 |
| **OE-11** | Actualizar automáticamente el inventario después de reservas, ventas, devoluciones y recepción de productos. | Paquete P4 · CU-13, CU-22, CU-28, CU-31, CU-32 |
| **OE-12** | Gestionar productos provenientes de diferentes proveedores y temporadas. | Paquetes P2 y P3 · CU-07, CU-09, CU-10, CU-13 |
| **OE-13** | Incorporar funcionalidades de inteligencia artificial para recomendación o asistencia al cliente. | Paquete P10 · CU-33, CU-34, CU-35 |
| **OE-14** | Generar reportes y dashboards para apoyar la toma de decisiones. | Paquete P11 · CU-36, CU-37 |
| **OE-15** | Aplicar UML 2.5+ para modelar los procesos, funcionalidades y arquitectura del sistema. | Todos los flujos de trabajo del PUDS (docs. 03, 04 y siguientes) |
| **OE-16** | Implementar el sistema utilizando FastAPI, Angular y Flutter/Dart. | Decisiones técnicas (doc. 06) |

#### b) Objetivos específicos adicionales del equipo

El enunciado exige en su apartado *TOMAR EN CUENTA* el despliegue en la nube, y la descripción
del problema (§1.3) expone deficiencias —la falta de trazabilidad de los movimientos de
mercadería, entre otras— que ninguno de los dieciséis objetivos anteriores cubre de forma
explícita. Se incorporan cuatro objetivos adicionales, numerados a continuación de los
originales:

| Código | Objetivo específico | Justificación |
|---|---|---|
| **OE-17** | Desplegar la solución completa en la nube —backend, base de datos y aplicación web con URL pública, y la aplicación móvil como artefacto instalable—, sin dependencia de entornos locales. | Exigencia explícita del enunciado (*"Despliegue: En la nube (no localhost)"*), no recogida en los objetivos específicos. Realiza RNF03. |
| **OE-18** | Implementar el control de acceso basado en roles (Cliente, Administrador, Encargado de Sucursal, Cajero, Proveedor) y la protección de credenciales y datos sensibles. | El OE-02 exige gestionar usuarios, pero no su seguridad. Realiza RNF01 y acota el ámbito de datos de cada rol a su sucursal. |
| **OE-19** | Garantizar la trazabilidad de las existencias registrando cada modificación de inventario como un movimiento inmutable con tipo, motivo, usuario y fecha. | Responde al registro manual y sin trazabilidad de los movimientos de mercadería descrito en §1.3. El OE-11 exige que el inventario se actualice, pero no que el cambio quede explicado. |
| **OE-20** | Asegurar la consistencia transaccional de reservas y ventas, impidiendo la sobreventa de una misma variante ante operaciones concurrentes. | Sin esta garantía, dos clientes pueden reservar o comprar la última unidad disponible. Realiza RNF11. |

## 1.3 Descripción del problema

La operación actual de la cadena de tiendas de ropa se sostiene sobre un conjunto de prácticas
manuales y sistemas aislados que producen deficiencias en toda la cadena de valor.

**Inventario fragmentado y sin visión consolidada.** Cada sucursal lleva el control de sus
existencias de manera independiente, generalmente en planillas electrónicas o en sistemas de
punto de venta que no se comunican entre sí. La consecuencia directa es que ni la administración
central ni el personal de una sucursal pueden responder con certeza a la pregunta más elemental
del negocio: *¿en qué sucursal hay esta prenda, en esta talla y en este color?*. Esto impide
detectar sobrestock en una sucursal frente a quiebre de stock en otra, y bloquea cualquier
política de transferencia entre tiendas o de reposición basada en datos.

**Ausencia de canal digital de venta.** La empresa no dispone de tienda en línea ni de aplicación
móvil. Toda venta exige la presencia física del cliente en el local, lo que limita la cobertura
al radio de desplazamiento de cada sucursal y deja fuera a los clientes que ya realizan la mayor
parte de sus compras por canales digitales. La empresa tampoco captura ningún dato de
comportamiento del cliente que pudiera usarse para personalizar la oferta.

**Fricción en la prueba de prendas.** El cliente que desea probarse una prenda debe trasladarse a
la tienda sin saber si el artículo está disponible en su talla. En la tienda debe buscar
físicamente entre las perchas y esperar disponibilidad de vestidor. Una proporción significativa
de estos desplazamientos termina sin compra por falta de talla, de color, o porque la prenda no
le sienta como esperaba. Este costo —de tiempo del cliente y de atención del personal— es hoy
invisible para la empresa porque no se registra en ningún sistema.

**Gestión manual de proveedores, temporadas y colecciones.** Los productos ingresan asociados a
proveedores y temporadas comerciales (primavera-verano, otoño-invierno, temporada escolar,
promociones, nuevas colecciones), pero esa relación no queda registrada de forma estructurada. Al
no poder medir la rotación por temporada, colección o proveedor, las decisiones de compra se
toman por intuición, produciendo tanto quiebres de stock en artículos de alta demanda como
acumulación de prendas de temporadas vencidas que terminan liquidándose bajo costo.

**Información gerencial tardía y poco confiable.** Los reportes de ventas e inventario se elaboran
manualmente consolidando planillas de cada sucursal, con días de retraso respecto al estado real.
La administración no cuenta con indicadores en tiempo real, lo que retrasa la reacción ante
situaciones anómalas: una caída de ventas en una sucursal, una talla agotada en toda la red o un
proveedor con retraso en la entrega.

**Sin personalización ni asistencia al cliente.** No existe ningún mecanismo que sugiera al
cliente prendas acordes a su historial, su talla habitual, la temporada vigente o su presupuesto.
La experiencia de navegación —cuando existe— es la de un catálogo plano e idéntico para todos.

En síntesis, el problema central es la **inexistencia de una plataforma integrada que unifique el
inventario multisucursal, habilite los canales de venta digital y presencial sobre un mismo dato,
reduzca la fricción de la prueba de prendas y convierta la información operativa en decisiones**.
Esta situación afecta simultáneamente la eficiencia operativa de la empresa, el margen erosionado
por liquidaciones evitables y la satisfacción de un cliente que percibe la experiencia de compra
como incierta y desactualizada frente a la de competidores digitalizados.

## 1.4 Alcance

### 1.4.1 Alcance positivo (lo que el sistema SÍ incluye)

**Módulo 1 — Seguridad y Usuarios.** Registro e inicio de sesión de clientes; autenticación de
usuarios internos; control de acceso basado en roles (Cliente, Administrador, Encargado de
Sucursal, Cajero, Proveedor); emisión y revocación de tokens JWT; almacenamiento de contraseñas
con hash; gestión de usuarios, roles y permisos por parte del Administrador.

**Módulo 2 — Organización y Sucursales.** Gestión de ciudades y sucursales (dirección, horarios,
capacidad de vestidores); gestión de empleados y su asignación a una sucursal; gestión de
proveedores y sus datos de contacto.

**Módulo 3 — Catálogo de Productos.** Gestión de categorías jerárquicas, tallas, colores,
temporadas y colecciones; gestión de productos con sus imágenes; generación de variantes
(SKU = producto × talla × color) con precio y código propio; asociación de productos a proveedor,
temporada y colección; publicación/despublicación de productos; gestión de promociones y
descuentos por producto, categoría o temporada.

**Módulo 4 — Inventario Multisucursal.** Existencias por variante y sucursal con cantidad
disponible y cantidad reservada; registro trazable de todo movimiento de inventario (ingreso por
compra a proveedor, reserva, liberación de reserva, venta digital, venta presencial, devolución,
transferencia entre sucursales, ajuste por inventario físico); actualización automática de
existencias ante cada operación; consulta consolidada de stock de toda la red; alertas de stock
bajo y de prendas próximas a ingresar.

**Módulo 5 — Catálogo Público y Disponibilidad.** Navegación del catálogo desde web y móvil con
búsqueda por texto y filtros (categoría, talla, color, temporada, colección, rango de precio,
sucursal); ficha de producto con galería de imágenes y selector de talla/color; consulta de
disponibilidad de una variante en todas las sucursales o en la sucursal seleccionada; lista de
favoritos.

**Módulo 6 — Reservas para Prueba en Sucursal.** Selección de múltiples prendas (variantes) para
una misma reserva; elección de sucursal y de franja horaria de atención; confirmación de la
reserva con reducción del stock disponible y aumento del stock reservado; notificación de la
reserva a la sucursal correspondiente; consulta del estado de la reserva por el cliente y su
cancelación; recepción, preparación y atención de la reserva por el Encargado de Sucursal;
expiración automática de reservas no atendidas con liberación del stock; conversión de la reserva
en venta presencial de las prendas que el cliente decide comprar.

**Módulo 7 — Vestidor Virtual con Realidad Aumentada.** Funcionalidad en la aplicación móvil que,
desde la ficha de una prenda, activa la cámara del dispositivo, detecta la posición del cuerpo
del usuario y superpone la imagen de la prenda seleccionada ajustada a esa posición, permitiendo
cambiar de color/talla sin salir de la vista, capturar una imagen del resultado y agregar la
prenda a la reserva o al carrito directamente desde el vestidor virtual.

**Módulo 8 — Compra Digital.** Carrito de compras persistente por cliente; aplicación de
promociones; selección de modalidad de entrega (retiro en sucursal o envío a domicilio con
dirección); generación del pedido; integración con pasarela de pago electrónica en **entorno de
pruebas (sandbox)** para el cobro con tarjeta; confirmación automática del pedido mediante
webhook de la pasarela; descuento automático del inventario de la sucursal que abastece el
pedido; consulta del historial de compras y del estado del pedido; emisión de comprobante digital
en PDF.

**Módulo 9 — Punto de Venta (POS) Presencial.** Apertura y cierre de caja por turno; registro de
venta presencial por el Cajero mediante búsqueda o lectura de código de la variante; carga de una
reserva atendida como base de la venta; cobro en efectivo o tarjeta; emisión del comprobante;
descuento automático del inventario de la sucursal; registro de devoluciones con reingreso al
inventario; arqueo de caja.

**Módulo 10 — Inteligencia Artificial.** Recomendador de prendas que sugiere productos
considerando historial de navegación y compra, talla habitual, temporada vigente, categoría y
disponibilidad real; asistente conversacional (chatbot) capaz de responder consultas sobre
catálogo, disponibilidad y estado de pedidos consultando el sistema; generación de reportes en
lenguaje natural bajo demanda mediante **comando de voz**, sobre datos reales del sistema.

**Módulo 11 — Reportes y Tablero de Control.** Tablero con KPIs en tiempo real (ventas del día y
del mes, ticket promedio, reservas pendientes y atendidas, tasa de conversión de reserva a venta,
productos más vendidos, stock crítico); reportes exportables a PDF y Excel de ventas por
sucursal/período/categoría, inventario consolidado, movimientos de inventario, reservas,
rendimiento por temporada y colección, y compras por proveedor.

**Módulo 12 — Despliegue en la nube.** Backend, base de datos y frontend web desplegados en
proveedores de nube con URL pública y HTTPS; aplicación móvil distribuida como artefacto
instalable (APK) apuntando al backend en la nube. **No se utilizará localhost como entorno de
demostración ni de defensa.**

### 1.4.2 Alcance negativo (lo que el sistema NO incluye)

- **Uso de frameworks de e-commerce** (PrestaShop, Shopify, Magento, WooCommerce y similares).
  Restricción explícita del enunciado; todo el sistema se desarrolla a medida.
- **Cobro real de dinero.** La pasarela de pago se integra exclusivamente en modo de pruebas
  (sandbox) con tarjetas de prueba; no se procesan transacciones reales ni se gestionan fondos.
- **Facturación tributaria oficial.** No se emiten facturas con validez fiscal ni se integra con
  el sistema de impuestos nacional; los comprobantes generados son documentos internos.
- **Módulo de logística y seguimiento de delivery propio.** El envío a domicilio se registra como
  modalidad de entrega con dirección y costo, pero no se implementa asignación de repartidores,
  cálculo de rutas ni seguimiento en tiempo real. (El funcionamiento de los deliverys se aborda
  únicamente en la fundamentación teórica exigida por el enunciado.)
- **Prueba virtual fotorrealista con reconstrucción 3D del cuerpo.** El vestidor virtual opera
  mediante superposición de la prenda sobre la imagen de cámara guiada por detección de pose; no
  incluye simulación física de tela, escaneo corporal ni medición antropométrica automática.
- **Aplicaciones móviles nativas separadas** para Android e iOS. Se desarrolla una única
  aplicación en Flutter/Dart; la distribución en la defensa se realiza sobre Android.
- **Publicación en tiendas de aplicaciones** (Google Play, App Store).
- **Portal de autogestión completo para el Proveedor.** El Proveedor accede para registrar y
  consultar la información de sus productos y su disponibilidad, pero no se implementa un flujo
  de órdenes de compra, cotizaciones ni conciliación de pagos a proveedores.
- **Integración con sistemas externos** de contabilidad, ERP, nómina o mensajería (SMS, WhatsApp).
- **Transferencia automática de stock entre sucursales.** El movimiento de transferencia se
  registra manualmente por el Administrador; no existe algoritmo de balanceo automático.
- **Aplicación de escritorio.** El punto de venta se opera desde el navegador (Angular).
- **Multi-idioma y multi-moneda.** El sistema opera en español y en una única moneda.

### 1.4.3 Supuestos y restricciones del proyecto

| # | Supuesto / restricción |
|---|---|
| S1 | El equipo está conformado por 2 integrantes y dispone de 4 semanas calendario (25/08/2026 – 22/09/2026), con entregas obligatorias el 05/09, 13/09 y 20/09 y defensa el 22/09. |
| S2 | El stack tecnológico está fijado por el enunciado y no es objeto de decisión: FastAPI (Python), Angular, Flutter/Dart, PostgreSQL, IA vía API, RA en móvil, pasarela de pago. |
| S3 | Los datos de catálogo, sucursales, proveedores y clientes se cargan mediante un *seed* de datos ficticios representativos; no se migran datos de un sistema real. |
| S4 | Los servicios de nube utilizados corresponden a planes gratuitos o de prueba, lo que impone límites de recursos (arranque en frío, cuotas de almacenamiento y de cómputo) asumidos por el equipo. |
| S5 | Las imágenes de prendas usadas por el vestidor virtual deben contar con fondo transparente (PNG con canal alfa) para poder superponerse correctamente. |
| S6 | El costo de consumo de la API de IA corre por cuenta del equipo y se controla mediante límites de uso y caché de respuestas. |
