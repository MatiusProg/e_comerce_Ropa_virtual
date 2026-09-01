# 5) PLAN DE TRABAJO Y CRONOGRAMA

## 5.1 Fechas obligatorias (fijadas por el enunciado)

| Hito | Fecha | Hora límite |
|---|---|---|
| Inicio del examen | Martes **25/08/2026** | — |
| **Presentación #1** | Sábado **05/09/2026** | 23:59 |
| **Presentación #2** | Domingo **13/09/2026** | 23:59 |
| **Presentación final** | Domingo **20/09/2026** | 23:59 |
| **Defensa del software** | Martes **22/09/2026** | — |

> Las tres presentaciones son **obligatorias** para estar habilitados a la defensa.

**Situación al 01/09/2026:** ya transcurrió la primera semana del plazo (25/08 – 31/08). Restan
**4 días** para la Presentación #1 y **19 días** para la defensa. El cronograma parte de esta
fecha, no de la de inicio del examen.

## 5.2 Estructura de ciclos (PUDS)

El proyecto se organiza en **tres ciclos de desarrollo, uno por cada presentación**. Cada ciclo
recorre los cinco flujos de trabajo del PUDS (Captura de Requisitos, Análisis, Diseño,
Implementación y Pruebas) sobre su propio subconjunto de casos de uso, y cierra con **software
funcionando y desplegado**, no con software a medias.

| Ciclo | Fase PUDS | Período | Días | Casos de uso | Entrega |
|---|---|---|:---:|:---:|---|
| **Ciclo 1 — Fundamentos** | Inicio | 01/09 – 05/09 | 4 | 9 (CU-01 a CU-09) | Presentación #1 |
| **Ciclo 2 — Núcleo del negocio** | Elaboración | 06/09 – 13/09 | 8 | 13 (CU-10, 11, 13-19, 22-25) | Presentación #2 |
| **Ciclo 3 — Comercio e inteligencia** | Construcción | 14/09 – 20/09 | 7 | 15 (CU-12, 20, 21, 26-37) | Presentación final |
| **Cierre** | Transición | 21/09 – 22/09 | 2 | — | Defensa |

El **Ciclo 1 es deliberadamente el más corto**: son cuatro días y su contenido es CRUD y
autenticación, sin reglas de negocio complejas. Es lo que cabe en el tiempo disponible sin
comprometer la calidad de los otros dos.

## 5.3 Ciclo 1 — Fundamentos (01/09 al 05/09)

**Objetivo:** entregar la documentación de Perfil, Fundamentación Teórica, Modelo del Negocio y
Captura de Requisitos, y dejar el proyecto arrancado, con seguridad y organización funcionando y
**desplegado en Railway**.

### Alcance funcional — paquetes P1, P2 y P3 (maestros)

| Paquete | Casos de uso | Alcance |
|---|---|---|
| P1 Seguridad | CU-01 a CU-04 | Registro de cliente, login/logout con JWT, gestión de usuarios y roles, perfil del cliente |
| P2 Organización | CU-05 a CU-07 | CRUD de ciudades, sucursales, empleados y proveedores |
| P3 Catálogo (maestros) | CU-08, CU-09 | CRUD de categorías, tallas, colores, temporadas y colecciones |

### Documentación (entregable principal de la Presentación #1)

| # | Tarea | Responsable | Estado |
|---|---|---|---|
| 1 | Perfil: introducción, objetivos, descripción del problema, alcance | Mateo | ✔ |
| 2 | Modelo del negocio: problemas, depuración, propietarios, cuantificación, alternativas, Ishikawa | Mateo | ✔ |
| 3 | Captura de requisitos: actores, casos de uso, priorización, trazabilidad RF/RNF | Mateo | ✔ |
| 4 | **Parte I · E-commerce**: conceptos y características; como usuario en Amazon, Alibaba y Shopify; como desarrollador en Magento, PrestaShop y WooCommerce | Karen | pendiente |
| 5 | **Parte I · Pasarelas de pago**: formas de pago en línea (débito, crédito, QR, transferencias); **Libélula**; **PayPal** y **Stripe** | Karen | pendiente |
| 6 | **Parte I · Deliverys**: funcionamiento (Yaigo / Yummy) y cálculo del costo de entrega (distancia, peso, frecuencia, tamaño) | Karen | pendiente |
| 7 | **Parte I · PUDS**: fases, flujos de trabajo, carácter iterativo e incremental | Mateo | pendiente |
| 8 | **Parte I · UML 2.5+**: diagramas estructurales y de comportamiento; los que se usan en este proyecto | Mateo | pendiente |
| 9 | Diagrama de Ishikawa (dibujado) | Karen | pendiente |
| 10 | **Diagrama de Casos de Uso UML** (general y del Ciclo 1) | Karen | pendiente |
| 11 | **Detalle de los 9 casos de uso del Ciclo 1** con plantilla completa: descripción, propósito, actores, iniciador, precondiciones, flujo principal, postcondiciones y excepciones | Ambos | pendiente |
| 12 | **Prototipos de interfaz** del Ciclo 1 (login, gestión de usuarios, sucursales, maestros) | Karen | pendiente |
| 13 | Consolidación en Word con índice automático, portada y bibliografía | Karen | pendiente |

### Técnico

| # | Tarea | Responsable | Estado |
|---|---|---|---|
| 14 | Repositorio en GitHub, ramas y estructura del monorepo | Mateo | ✔ |
| 15 | Esqueleto del backend FastAPI por paquetes, configuración por entorno, `/health` | Mateo | ✔ |
| 16 | Proyecto Angular 22 y esqueleto de la app Flutter | Karen | ✔ (generados) |
| 17 | Servicio **PostgreSQL en Railway** creado y conectado | Mateo | pendiente |
| 18 | Modelos y migración de P1, P2 y P3 (maestros) + *seed* de usuarios | Mateo | pendiente |
| 19 | Endpoints de P1, P2 y P3 (maestros) | Mateo | pendiente |
| 20 | Login, guardas por rol y ABM de organización y maestros en Angular | Karen | pendiente |
| 21 | **Despliegue del backend y de la web en Railway con URL pública** | Mateo · Karen | pendiente |

> **Criterio de cierre del Ciclo 1:** el documento está entregado en la plataforma **y** existe una
> URL pública en Railway donde se puede iniciar sesión como Administrador y dar de alta una
> sucursal. El despliegue es un requisito del enunciado; dejarlo para el final es el error más
> costoso posible en un plazo de tres semanas.

## 5.4 Ciclo 2 — Núcleo del negocio (06/09 al 13/09)

**Objetivo:** el corazón del sistema funcionando en la nube — catálogo con variantes, inventario
multisucursal y reservas.

### Alcance funcional — paquetes P3 (productos), P4, P5 y P6

| Paquete | Casos de uso | Alcance | Responsable |
|---|---|---|---|
| P3 Catálogo | CU-10, CU-11 | Productos, generación de **variantes (SKU)** e imágenes | Mateo (API) · Karen (UI) |
| P4 Inventario | CU-13 a CU-16 | Existencias por (variante, sucursal), movimientos trazables, ingreso de mercadería, consulta consolidada, alertas de stock bajo | Mateo |
| P5 Catálogo público | CU-17 a CU-19 | Búsqueda, filtros, paginación, ficha de producto y disponibilidad por sucursal — **web y móvil** | Karen |
| P6 Reservas | CU-22 a CU-25 | Reserva múltiple con sucursal y horario, consulta y cancelación, atención en sucursal, expiración automática | Mateo (API) · Karen (UI web y móvil) |
| — | — | *Seed* completo: 3 ciudades, 5 sucursales, 4 proveedores, ~60 productos con variantes, imágenes y stock distribuido | Mateo |
| — | — | **Prototipo aislado del vestidor virtual** (cámara + detección de pose, sin integrar) | Karen |

### Documentación

- **Flujo de Análisis:** identificación de paquetes, relación paquete–caso de uso, vista de
  paquetes, **diagramas de comunicación** de los casos de uso de los Ciclos 1 y 2, análisis de
  clases (entidad, control, interfaz) y análisis de paquetes.
- **Flujo de Diseño:** diagrama de despliegue (físico), diagrama de paquetes (lógico), **diagramas
  de secuencia**, **diagrama de clases de diseño**, diseño lógico de datos (modelo
  entidad-relación) y diseño físico (migraciones y tabla de volúmenes).
- **Detalle de los 13 casos de uso del Ciclo 2** y prototipos de sus interfaces.

> **Criterio de cierre del Ciclo 2:** un cliente puede registrarse desde la app, navegar el
> catálogo, filtrar por talla y color, ver en qué sucursal hay stock, crear una reserva de varias
> prendas, y el Encargado puede verla, prepararla y atenderla — todo sobre el sistema desplegado
> en Railway.

> **El prototipo del vestidor virtual se construye en este ciclo, no en el siguiente.** Es el
> riesgo técnico más alto del proyecto (R3) y no puede descubrirse que no funciona el 15/09.

## 5.5 Ciclo 3 — Comercio e inteligencia (14/09 al 20/09)

**Objetivo:** los diferenciadores del enunciado funcionando, documento final consolidado y sistema
listo para la defensa.

### Alcance funcional — paquetes P7, P8, P9, P10, P11 y lo que resta de P3 y P5

| Paquete | Casos de uso | Alcance | Responsable |
|---|---|---|---|
| P9 Vestidor Virtual | CU-21 | Integración del prototipo con el catálogo: cambio de variante en vivo, captura y derivación a reserva o carrito | **Karen** |
| P7 Ventas y POS | CU-26, 27, 29-32 | Carrito, generación de pedido, historial; apertura/cierre de caja, venta presencial, comprobante y devolución | Mateo (API) · Karen (UI) |
| P8 Pagos | CU-27, CU-28 | Stripe en sandbox, webhook verificado e idempotente, confirmación del pedido y descuento de inventario | Mateo |
| P10 Inteligencia Artificial | CU-33 a CU-35 | Recomendador híbrido, asistente conversacional y reporte generativo por comando de voz | Mateo (backend) · Karen (voz en el navegador) |
| P11 Reportes y Tablero | CU-36, CU-37 | KPIs en tiempo real y exportación a PDF y Excel | Mateo (API) · Karen (UI y gráficos) |
| P3 (resto) | CU-12 | Promociones y descuentos | Mateo |
| P5 (resto) | CU-20 | Favoritos | Karen |

### Documentación

- Diseño del Ciclo 3 (secuencia, clases, datos) y actualización de los modelos de los ciclos
  anteriores que hayan cambiado durante la implementación.
- **Flujo de Pruebas:** casos de prueba por caso de uso con resultado esperado y obtenido, y
  evidencia (capturas) tomada del sistema desplegado.
- Manual de usuario breve por rol y manual de despliegue en Railway.
- Bibliografía, anexos y consolidación final del documento.

> **Criterio de cierre del Ciclo 3:** el flujo se puede demostrar de punta a punta sobre el sistema
> desplegado: catálogo → vestidor virtual → reserva → atención en sucursal → venta en caja; y en
> paralelo catálogo → carrito → pago con tarjeta de prueba → inventario descontado → reporte.

> **Este ciclo es el más cargado y el más incierto.** Si el plazo aprieta, el orden de sacrificio
> está decidido de antemano: primero CU-20 (Favoritos) y CU-32 (Devoluciones), ambas de prioridad
> Baja; después CU-34 (asistente conversacional), conservando CU-33 y CU-35, que ya cubren el RF25.
> No se sacrifica nunca el vestidor virtual ni el pago: son exigencias explícitas del enunciado.

## 5.6 Cierre — 21/09 y 22/09 (Defensa)

- **Congelamiento de código** el 20/09 tras la entrega. A partir de ahí solo se corrigen defectos
  bloqueantes; no se agregan funcionalidades.
- **Datos de demostración** preparados: un cliente, un administrador, un encargado y un cajero con
  credenciales listas; una reserva en curso; un pedido pagado; stock en varias sucursales.
- **Guion de la defensa** (≈15 minutos): problema → arquitectura → flujo del cliente (catálogo,
  vestidor virtual, reserva) → flujo de sucursal (atención, POS) → pago en línea → IA
  (recomendación y reporte por voz) → tablero de KPIs.
- **Plan de contingencia:** vídeo de respaldo grabado el 20/09, APK preinstalado en el dispositivo
  de la defensa y en un segundo dispositivo.
- Ensayo completo cronometrado, con **ambos integrantes capaces de explicar cualquier módulo**.

## 5.7 Distribución de responsabilidades

| Ámbito | Mateo Hurtado (222008687) | Karen Ortega (222056592) |
|---|---|---|
| **Backend FastAPI** | Responsable principal | Apoyo en endpoints de su módulo |
| **Base de datos PostgreSQL** | Responsable principal | — |
| **Frontend web Angular** | Apoyo | Responsable principal |
| **App móvil Flutter** | Apoyo | Responsable principal |
| **Realidad aumentada** | — | Responsable principal |
| **Inteligencia artificial** | Responsable principal (backend) | Comando de voz en el navegador |
| **Pasarela de pago** | Responsable principal | — |
| **Despliegue en Railway** | Responsable principal | Servicio del frontend web |
| **Documentación PUDS** | Perfil, modelo de negocio, requisitos, análisis, diseño de datos | Marco teórico, diagramas UML, prototipos, consolidación |
| **Diagramas UML** | Revisión y validación | Elaboración |

**Regla de trabajo acordada.** Ninguno de los dos es el único que entiende un módulo: al cierre de
cada ciclo, cada integrante le explica al otro lo que implementó. En la defensa cualquiera de los
dos puede ser interrogado sobre cualquier parte del sistema.

## 5.8 Riesgos del proyecto

| # | Riesgo | Prob. | Impacto | Mitigación |
|---|---|:---:|:---:|---|
| R1 | **Plazo insuficiente**: ya se perdió la primera semana y el alcance del enunciado es amplio | Alta | Alto | Tres ciclos con alcance cerrado; orden de sacrificio decidido de antemano (§5.5); cada ciclo cierra con software funcionando, no a medias |
| R2 | **El despliegue se posterga** y falla en la última semana | Alta | Alto | Desplegar en Railway durante el Ciclo 1, con un `/health`, antes de tener funcionalidad; cada ciclo cierra desplegando |
| R3 | **La realidad aumentada consume más tiempo del previsto** o no funciona en el dispositivo de la defensa | Media | Alto | Superposición 2D guiada por pose, no reconstrucción 3D; **prototipo aislado durante el Ciclo 2**; probar en el dispositivo real de la defensa con antelación |
| R4 | **El webhook de la pasarela no llega** al backend desplegado | Media | Alto | Modo sandbox, que no requiere aprobación comercial; probar el webhook contra la URL pública de Railway desde el primer día del Ciclo 3; registrar toda notificación recibida |
| R5 | **Sobreventa por concurrencia**: dos clientes reservan la última unidad | Media | Medio | Transacción con `SELECT ... FOR UPDATE` sobre la existencia; prueba explícita de concurrencia en el Ciclo 2 |
| R6 | **Costo o límite de la API de IA** agotado durante la defensa | Baja | Medio | Caché de respuestas; tope de peticiones por usuario; degradación a recomendación por reglas si el servicio falla (D6) |
| R7 | **Conflictos de integración** entre backend y frontend al trabajar en paralelo | Media | Medio | Contrato de API definido antes de implementar (OpenAPI); ramas por funcionalidad e integración por Pull Request; sin *commits* directos sobre `main` |
| R8 | **Indisponibilidad de un integrante** en un grupo de dos | Baja | Alto | Decisiones documentadas en el repositorio; *commits* diarios; ningún módulo con conocimiento exclusivo de una persona |
| R9 | **Límite del plan de Railway** (horas de ejecución o crédito agotado) justo antes de la defensa | Media | Alto | Vigilar el consumo desde el primer día; los tres servicios en un mismo proyecto; vídeo de respaldo y APK preinstalado |
| R10 | **Cambio o aclaración de requisitos** por parte de la docente | Media | Medio | Consultar dudas en las presentaciones #1 y #2, cuando aún hay margen para corregir |
