# 2) MODELO DEL NEGOCIO

> **FUERA DEL ALCANCE DEL ENTREGABLE.** El índice oficial de la ingeniera no incluye el Modelado
> del Negocio ni el diagrama de Ishikawa, y se confirmó que **no se realizan en este proyecto**.
> Este documento **no se vuelca al `.docx`** y ninguna sección entregada debe citar sus códigos
> de problema (P1, P2, …). Se conserva en el repositorio como contexto interno: es el análisis
> del que salieron el alcance, los objetivos adicionales y varios requisitos, y sirve para
> responder en la defensa por qué el sistema hace lo que hace. Ver
> [`docs/00-indice-oficial.md`](00-indice-oficial.md).

Este capítulo corresponde al modelado del negocio previo a la captura de requisitos del PUDS.
Se identifica y depura el problema, se determinan sus propietarios, se cuantifica su impacto, se
evalúan alternativas de cambio y se construye el diagrama causa-efecto (Ishikawa).

---

## 2.1 Identificar el problema

### 2.1.1 Lista inicial de problemas

| Código | Descripción del problema |
|---|---|
| P1 | Inventario gestionado de forma independiente en cada sucursal, sin consolidación central |
| P2 | Imposibilidad de conocer la disponibilidad de una prenda por talla, color y sucursal antes de acudir a la tienda |
| P3 | Inexistencia de canal de venta digital (web y móvil); toda venta requiere presencia física |
| P4 | Alta tasa de visitas a tienda que terminan sin compra por falta de talla, color o por desajuste de la prenda |
| P5 | Registro manual de movimientos de mercadería (ingresos, ventas, devoluciones) en planillas, sin trazabilidad |
| P6 | Gestión no estructurada de proveedores, temporadas y colecciones, que impide medir rotación |
| P7 | Acumulación de prendas de temporadas vencidas que deben liquidarse por debajo del costo |
| P8 | Quiebres de stock en artículos de alta demanda mientras existe sobrestock del mismo artículo en otra sucursal |
| P9 | Reportes de ventas e inventario elaborados manualmente y con días de retraso |
| P10 | Ausencia de indicadores en tiempo real para la toma de decisiones de la administración |
| P11 | Nula personalización de la oferta: el catálogo es idéntico para todos los clientes |
| P12 | La empresa no captura datos de comportamiento del cliente (navegación, preferencias, historial) |
| P13 | Ausencia de un mecanismo de reserva anticipada de prendas para prueba en sucursal |
| P14 | Congestión de vestidores físicos en horarios pico y demora en la atención |
| P15 | Falta de un canal de pago electrónico; solo se cobra en efectivo o tarjeta en caja física |
| P16 | Retrasos e incumplimientos de entrega por parte de proveedores sin registro formal |

### 2.1.2 Depuración de problemas

Se depuran los problemas que quedan fuera del alcance del sistema o que resultan absorbidos por
otros ya listados:

- **P7 (acumulación de temporadas vencidas)** es una **consecuencia** de P6 (gestión no
  estructurada de temporadas) y de P9/P10 (falta de información oportuna), no un problema
  independiente. *Se fusiona con P6.*
- **P10 (ausencia de indicadores en tiempo real)** describe la misma carencia que **P9** desde la
  perspectiva de la gerencia. *Se fusiona con P9.*
- **P12 (no se capturan datos de comportamiento)** es la **causa habilitante** de **P11** (nula
  personalización): sin datos no hay personalización posible. *Se fusiona con P11.*
- **P14 (congestión de vestidores físicos)** corresponde a la gestión operativa del espacio físico
  de la tienda (cantidad de vestidores, turnos de personal), que excede el alcance de un sistema
  de información. El sistema lo mitiga parcialmente mediante la reserva con franja horaria (P13),
  pero no lo resuelve. *Se descarta.*
- **P16 (incumplimiento de proveedores)** pertenece al proceso de compras y gestión contractual
  con proveedores. El alcance definido incluye el registro de proveedores y el ingreso de
  mercadería, pero no el ciclo de órdenes de compra ni la evaluación de cumplimiento. *Se
  descarta.*

### 2.1.3 Lista final de problemas

| Código | Descripción del problema (depurada) |
|---|---|
| **P1** | Inventario fragmentado por sucursal, sin consolidación ni visión unificada de la red |
| **P2** | El cliente no puede conocer la disponibilidad de una prenda por talla, color y sucursal antes de acudir a la tienda |
| **P3** | Inexistencia de canal de venta digital (web y móvil) y de pago electrónico |
| **P4** | Alta tasa de visitas a tienda sin compra por falta de talla/color o por desajuste de la prenda al probársela |
| **P5** | Registro manual y sin trazabilidad de los movimientos de mercadería |
| **P6** | Gestión no estructurada de proveedores, temporadas y colecciones, que impide medir rotación y produce liquidaciones bajo costo |
| **P8** | Desbalance de stock entre sucursales: quiebre en una y sobrestock del mismo artículo en otra |
| **P9** | Reportes e indicadores elaborados manualmente y con días de retraso respecto al estado real |
| **P11** | Nula personalización de la oferta y ausencia de captura de datos de comportamiento del cliente |
| **P13** | Ausencia de un mecanismo de reserva anticipada de prendas para prueba en sucursal |

### 2.1.4 Propietarios de los problemas

Se identifica qué actores del negocio padecen cada problema (✓ = afectado directamente).

| Código | Problema (resumido) | Cliente | Administrador | Encargado de Sucursal | Cajero | Proveedor |
|---|---|:---:|:---:|:---:|:---:|:---:|
| P1 | Inventario fragmentado | ✓ | ✓ | ✓ | ✓ | |
| P2 | Sin consulta de disponibilidad previa | ✓ | | ✓ | ✓ | |
| P3 | Sin canal digital ni pago electrónico | ✓ | ✓ | | ✓ | |
| P4 | Visitas sin compra | ✓ | ✓ | ✓ | | |
| P5 | Movimientos sin trazabilidad | | ✓ | ✓ | ✓ | |
| P6 | Proveedores/temporadas sin estructura | | ✓ | ✓ | | ✓ |
| P8 | Desbalance de stock entre sucursales | ✓ | ✓ | ✓ | | |
| P9 | Reportes tardíos | | ✓ | ✓ | | |
| P11 | Sin personalización de la oferta | ✓ | ✓ | | | |
| P13 | Sin reserva anticipada | ✓ | | ✓ | | |

### 2.1.5 Análisis del problema

**P1 — Inventario fragmentado.** Cada sucursal opera su propio registro de existencias. No existe
una entidad única que represente "el stock de la variante X en la sucursal Y", por lo que
cualquier consulta que cruce sucursales debe resolverse por teléfono o correo entre encargados.
Esta fragmentación es la causa raíz de P2, P8 y buena parte de P9: sin un dato único no hay
consulta pública, ni balanceo, ni reportes confiables.

**P2 — Sin consulta de disponibilidad previa.** El cliente carece de cualquier vía para saber si
la prenda está disponible en su talla y color antes de desplazarse. El costo se traslada
íntegramente al cliente en forma de tiempo y transporte, y a la empresa en forma de atención de
consultas que no se convierten en venta.

**P3 — Sin canal digital ni pago electrónico.** La empresa está ausente del canal donde ocurre una
porción creciente del consumo. Además de perder esas ventas, pierde el registro digital de la
transacción, que es la materia prima de cualquier análisis de comportamiento posterior.

**P4 — Visitas sin compra.** El acto de probarse la prenda es insustituible en el rubro, pero hoy
ocurre al final del recorrido del cliente (después del desplazamiento y la búsqueda física). Si
la prenda no está o no le sienta, todo el esfuerzo previo se pierde. Adelantar una aproximación
visual de la prenda al momento de la navegación —vestidor virtual— y garantizar la disponibilidad
—reserva— ataca directamente este problema.

**P5 — Movimientos sin trazabilidad.** Los ingresos, ventas y devoluciones se anotan en planillas
que se sobrescriben. Cuando el conteo físico no coincide con el registrado no hay forma de
reconstruir qué ocurrió ni cuándo, de modo que las diferencias se ajustan sin explicación y el
error se vuelve estructural.

**P6 — Proveedores, temporadas y colecciones sin estructura.** La relación producto → proveedor →
temporada → colección no se registra formalmente. Sin ella no puede calcularse la rotación por
temporada ni el rendimiento por proveedor, y las compras se deciden por intuición. El resultado
visible es la acumulación de prendas fuera de temporada que se liquidan por debajo del costo.

**P8 — Desbalance de stock entre sucursales.** Es una consecuencia directa de P1 combinada con la
ausencia de reportes: la empresa pierde ventas en una sucursal por un artículo que sobra en otra,
sin enterarse. El sistema no resuelve automáticamente el balanceo (fuera de alcance), pero al
hacer visible el desbalance y registrar el movimiento de transferencia, habilita la corrección.

**P9 — Reportes tardíos.** La consolidación manual de planillas introduce un desfase de días entre
el hecho y su reporte. La administración decide sobre una fotografía vencida del negocio, lo que
anula su capacidad de reaccionar ante caídas de venta, agotamientos o promociones fallidas.

**P11 — Sin personalización.** Todos los clientes ven el mismo catálogo en el mismo orden. La
empresa no distingue al cliente recurrente del ocasional, ni conoce su talla habitual o sus
categorías preferidas, desaprovechando la oportunidad más barata de aumentar el ticket promedio:
mostrar lo correcto a la persona correcta.

**P13 — Sin reserva anticipada.** No hay forma de que el cliente asegure las prendas que desea
probar. La sucursal tampoco puede anticipar la demanda de sus vestidores ni preparar las prendas
con antelación, de modo que la atención se resuelve íntegramente en el momento, con el cliente
esperando.

### 2.1.6 Estimación y cuantificación del problema

Las magnitudes indicadas son estimaciones de trabajo elaboradas a partir del relevamiento del
proceso actual; su función es dimensionar el impacto relativo de cada problema y priorizar, no
constituir una medición contable.

| Código | Problema | Impacto estimado | Justificación |
|---|---|---|---|
| P1 | Inventario fragmentado | **Alto** | Cada consulta entre sucursales consume entre 10 y 30 minutos de dos empleados. Es la causa raíz de P2, P8 y P9. |
| P2 | Sin disponibilidad previa | **Alto** | Se estima que 3 de cada 10 visitas se originan en una consulta que pudo resolverse en línea. |
| P3 | Sin canal digital | **Alto** | La totalidad de la demanda digital potencial queda sin atender; competidores del rubro ya operan en línea. |
| P4 | Visitas sin compra | **Alto** | Estimado en torno al 50 % de las visitas; representa costo de atención sin ingreso asociado. |
| P5 | Movimientos sin trazabilidad | **Medio-Alto** | Las diferencias de inventario detectadas en los conteos físicos no son atribuibles ni corregibles en origen. |
| P6 | Proveedores/temporadas sin estructura | **Medio-Alto** | Las liquidaciones de fin de temporada por debajo del costo erosionan directamente el margen anual. |
| P8 | Desbalance entre sucursales | **Medio-Alto** | Cada quiebre de stock evitable es una venta perdida con producto existente en la red. |
| P9 | Reportes tardíos | **Medio** | Entre 4 y 8 horas mensuales de trabajo administrativo y decisiones tomadas sobre datos vencidos. |
| P11 | Sin personalización | **Medio** | Costo de oportunidad sobre el ticket promedio y sobre la recompra del cliente recurrente. |
| P13 | Sin reserva anticipada | **Medio** | Prolonga los tiempos de atención en tienda y no permite anticipar la demanda de vestidores. |

### 2.1.7 Alternativas de cambio

| # | Alternativa | Ventajas | Desventajas | Decisión |
|---|---|---|---|---|
| A1 | **Mantener la operación actual** (planillas y sistemas locales por sucursal) | Costo cero inmediato; sin curva de aprendizaje | No resuelve ningún problema identificado; el deterioro competitivo se acentúa | **Descartada** |
| A2 | **Adoptar una plataforma de e-commerce comercial** (Shopify, PrestaShop, Magento, WooCommerce) | Puesta en marcha rápida; funcionalidades de tienda ya resueltas | **Prohibida explícitamente por el enunciado del examen**; además no cubre inventario multisucursal con reserva para prueba física, POS de sucursal, vestidor virtual con RA ni la IA requerida; dependencia y costo recurrente por licencia | **Descartada** |
| A3 | **Digitalizar solo el inventario** (sistema interno sin canal de venta) | Menor esfuerzo de desarrollo; resuelve P1, P5, P8, P9 | Deja sin resolver P2, P3, P4, P11 y P13, que son los que afectan directamente al cliente; no cumple los objetivos del proyecto | **Descartada** |
| A4 | **Desarrollar una plataforma integral a medida** (web + móvil + POS + inventario + RA + IA), desplegada en la nube | Resuelve la totalidad de la lista final de problemas sobre un dato único; cumple las restricciones tecnológicas y metodológicas del enunciado; el equipo conserva el control del código y la evolución | Mayor esfuerzo de desarrollo; exige priorización estricta por el plazo de 4 semanas; requiere resolver la integración de RA, IA y pasarela de pago | **Seleccionada** |

### 2.1.8 Conclusiones y recomendaciones

**Conclusiones.** El diagnóstico muestra que los diez problemas de la lista final no son
independientes: se organizan en torno a una carencia estructural única —la inexistencia de un
dato de inventario y de catálogo compartido por toda la red— de la que se derivan la
imposibilidad de consulta previa (P2), el desbalance entre sucursales (P8), la falta de reportes
confiables (P9) y, en última instancia, la imposibilidad de abrir un canal digital (P3). Atacar
la causa raíz con una plataforma integrada resuelve simultáneamente la mayor parte del árbol de
problemas.

**Recomendaciones.**

1. Construir primero el **núcleo de datos** —usuarios y roles, sucursales, catálogo con variantes
   e inventario por sucursal— porque de él dependen todos los demás módulos. Este núcleo se
   reparte entre los Ciclos 1 y 2 del PUDS.
2. Priorizar, dentro de lo que ve el cliente, la **consulta de disponibilidad y la reserva**
   (P2, P4, P13) antes que la venta digital, ya que son las funcionalidades que resuelven la
   fricción específica del rubro y las que diferencian esta plataforma de una tienda en línea
   genérica.
3. Registrar **todo cambio de existencias como un movimiento de inventario inmutable** (P5),
   nunca como una simple actualización de un contador. La trazabilidad debe ser una propiedad de
   la arquitectura, no un módulo agregado al final.
4. Tratar la **realidad aumentada y la inteligencia artificial** como incrementos del Ciclo 3,
   apoyados sobre el catálogo ya estable. Ambos son diferenciadores exigidos por el enunciado,
   pero carecen de sustento si el catálogo y el inventario no funcionan primero.
5. Desplegar en la nube **desde el primer ciclo**, no al final. El despliegue es un requisito
   explícito y su postergación es el riesgo más frecuente en proyectos de este plazo.

## 2.2 Diagrama de Ishikawa (causa–efecto)

**Efecto (problema central):** *Pérdida de ventas e ineficiencia operativa por la ausencia de una
plataforma integrada de comercio electrónico y control de inventario multisucursal.*

### 2.2.1 Identificar las principales categorías

Se adoptan las categorías del modelo 6M adaptadas al contexto de una cadena de tiendas de ropa:

| Categoría | Interpretación en este negocio |
|---|---|
| **Métodos (procesos)** | Cómo se ejecutan hoy la venta, la reposición, el conteo de inventario y la atención al cliente |
| **Maquinaria (tecnología)** | Sistemas, equipos y software con que cuenta la empresa |
| **Mano de obra (personal)** | Capacidades, carga y dependencia del personal de sucursal y de administración |
| **Materiales (productos e información)** | Estado de la información de productos, proveedores, temporadas y colecciones |
| **Medición (control)** | Indicadores, reportes y capacidad de detectar desvíos |
| **Medio (entorno y cliente)** | Condiciones del mercado y expectativas del cliente |

### 2.2.2 Identificar las causas

**Métodos (procesos)**
- Registro de movimientos de mercadería en planillas, sobrescribiendo el estado anterior.
- Reposición decidida por criterio individual del encargado, sin regla ni umbral definido.
- Atención de la prueba de prendas resuelta íntegramente en el momento, sin preparación previa.
- Consulta de stock de otra sucursal resuelta por teléfono, sin registro.

**Maquinaria (tecnología)**
- Sistemas de punto de venta aislados y sin comunicación entre sucursales.
- Ausencia de aplicación web y móvil de cara al cliente.
- Ausencia de integración con pasarelas de pago electrónico.
- Ausencia de infraestructura en la nube; todo dato reside en equipos locales de cada tienda.

**Mano de obra (personal)**
- Tiempo del personal consumido en tareas de consolidación manual de planillas.
- Conocimiento del stock y de la ubicación de la mercadería concentrado en personas concretas.
- Dependencia de la disponibilidad de un empleado para responder cualquier consulta de stock.
- Ausencia de capacitación en herramientas digitales de gestión.

**Materiales (productos e información)**
- Catálogo sin estructura de variantes: producto, talla y color no se modelan como un SKU único.
- Relación producto → proveedor → temporada → colección no registrada formalmente.
- Fichas de producto sin imágenes normalizadas ni atributos consistentes.
- Datos de clientes dispersos o inexistentes.

**Medición (control)**
- Inexistencia de indicadores de venta, rotación y conversión.
- Reportes producidos manualmente y con días de retraso.
- Imposibilidad de medir la rotación por temporada, colección o proveedor.
- Diferencias de inventario detectadas pero no atribuibles a una causa.

**Medio (entorno y cliente)**
- Competencia del rubro ya operando con canales digitales y despacho a domicilio.
- Cliente que espera consultar disponibilidad, comprar y pagar desde el teléfono.
- Cliente que exige probarse la prenda antes de decidir la compra.
- Estacionalidad marcada de la demanda por temporadas comerciales.

### 2.2.3 Analizar y discutir el diagrama

El análisis del diagrama muestra que las causas de mayor peso se concentran en dos categorías:
**Maquinaria (tecnología)** y **Materiales (información)**. Las causas agrupadas bajo *Métodos*,
*Mano de obra* y *Medición* no son en su mayoría causas primarias, sino **respuestas adaptativas**
a la carencia tecnológica: se consulta por teléfono porque no hay sistema que responda; se
consolida a mano porque no hay dato único que consultar; el conocimiento se concentra en personas
porque no está registrado en ningún sistema.

De ello se desprende una conclusión operativa para el diseño: **la intervención sobre las
categorías Maquinaria y Materiales desactiva la mayoría de las causas de las otras tres
categorías**. Concretamente, modelar correctamente el catálogo con variantes (SKU = producto ×
talla × color) y las existencias por sucursal —causas de la categoría Materiales— es condición
previa e indispensable para que las funcionalidades tecnológicas tengan sobre qué operar. Por eso
los dos primeros ciclos del proyecto se definen alrededor de ese núcleo de datos.

La categoría **Medio** contiene causas externas, no eliminables por el sistema (la competencia, la
estacionalidad, la necesidad de probarse la prenda). El sistema no las suprime: las **absorbe**
mediante el vestidor virtual con RA y la reserva para prueba en sucursal, que reducen el costo
que esas condiciones imponen al cliente.

Finalmente, la categoría **Medición** deja de ser un problema una vez que las operaciones quedan
registradas: los reportes y KPIs no son un desarrollo adicional independiente, sino la
consecuencia natural de haber registrado cada venta, reserva y movimiento de inventario como un
hecho trazable en la base de datos.
