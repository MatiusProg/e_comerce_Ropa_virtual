# a) E-commerce

> **Pendiente de Karen:** este documento cubre los conceptos y el análisis de cada plataforma. El
> enunciado pide además *experimentar* como usuario, así que hay que **crear una cuenta en Amazon,
> Alibaba y Shopify, recorrer el flujo de compra y agregar capturas propias** en los puntos
> marcados con 📷. Sin esas capturas la sección está incompleta.

---

## 1. Conceptos generales y características

El **comercio electrónico** (e-commerce) es la compra y venta de bienes o servicios a través de
redes electrónicas, junto con los procesos que la sostienen: publicación del catálogo, captación
del pedido, cobro, entrega y postventa. No se reduce a "tener una página para vender": lo que
define a un e-commerce es que el **ciclo comercial completo queda registrado y automatizado**, de
modo que cada pedido genera datos de inventario, de cobro y de comportamiento del cliente.

### Modelos de negocio

| Modelo | Descripción | Ejemplo |
|---|---|---|
| **B2C** (Business to Consumer) | La empresa vende directamente al consumidor final | Tienda propia de una marca de ropa |
| **B2B** (Business to Business) | Venta entre empresas, con precios por volumen y condiciones negociadas | Alibaba |
| **C2C** (Consumer to Consumer) | Particulares venden a particulares; la plataforma solo intermedia | MercadoLibre, eBay |
| **Marketplace** | La plataforma no vende: aloja a múltiples vendedores y cobra comisión | Amazon (parte de su operación) |
| **D2C** (Direct to Consumer) | El fabricante salta al intermediario y vende directo | Marcas que abren su propia tienda |

### Componentes de una tienda en línea

1. **Catálogo** — productos, categorías, atributos y **variantes**. En indumentaria la variante
   (talla × color) es la unidad real de venta, no el producto.
2. **Buscador y filtros** — sin ellos un catálogo de miles de artículos es inutilizable.
3. **Carrito** — persistente, asociado al cliente.
4. **Checkout** — datos de entrega, modalidad de envío y confirmación del pedido.
5. **Pasarela de pago** — procesa el cobro fuera del dominio de la tienda (ver documento b).
6. **Gestión de inventario** — descuenta existencias y evita la sobreventa.
7. **Logística** — envío, retiro en tienda o entrega por un tercero (ver documento c).
8. **Postventa** — seguimiento, comprobantes, devoluciones y atención.

### Tienda propia frente a marketplace

Vender en un marketplace da tráfico inmediato pero cuesta una comisión por venta, impone las
reglas de la plataforma y —lo más importante— **el cliente es del marketplace, no de la marca**:
sus datos de comportamiento no quedan en poder del vendedor. Una tienda propia exige generar el
tráfico, pero conserva el margen, la identidad y los datos.

### Dónde se ubica Violet Boutique

Violet Boutique es un **B2C de tienda propia con un componente físico central**: el cliente puede
comprar en línea, pero también reservar prendas para **probárselas en una sucursal** y comprarlas
allí. No es un e-commerce puro ni una tienda física digitalizada, sino un modelo híbrido en el
que el inventario de las sucursales es el mismo que se muestra en línea.

Esa característica —**inventario multisucursal con reserva para prueba física, más punto de venta
en tienda**— es la que ninguna plataforma de e-commerce resuelve de fábrica, y es el argumento
técnico que justifica el desarrollo a medida (ver §3 de este documento).

---

## 2. Como usuario: Amazon, Alibaba y Shopify

### 2.1 Amazon

**Qué es.** El mayor minorista en línea del mundo, con un modelo **doble**: vende inventario
propio (Amazon retail) y a la vez opera como **marketplace** para vendedores terceros. En una
misma ficha de producto pueden competir varios vendedores por la "Buy Box", el botón de compra
por defecto.

**Recorrido de compra.**

1. **Búsqueda y filtros** — buscador con autocompletado y filtros laterales por categoría, marca,
   precio, valoración y, en indumentaria, **talla y color**.
2. **Ficha de producto** — galería de imágenes, selector de variante, precio, disponibilidad,
   fecha estimada de entrega, vendedor, reseñas y preguntas de otros compradores.
3. **Carrito y checkout** — dirección guardada, opciones de envío por velocidad, y **compra en un
   clic** para usuarios con datos guardados.
4. **Pago** — tarjeta, saldo en cuenta, financiación.
5. **Seguimiento** — estados del pedido y trazabilidad del envío.
6. **Devoluciones** — política de devolución autogestionada, con etiqueta de retorno generada
   desde la propia cuenta.

**Cómo resuelve la talla** — el problema central de este proyecto:
- Guía de tallas por marca dentro de la ficha.
- Reseñas etiquetadas por los compradores como "queda chico / justo / grande".
- Recomendación de talla basada en compras anteriores del mismo usuario.
- Programas de prueba antes de pagar en algunos mercados, que reconocen exactamente el problema
  que Violet Boutique ataca con el vestidor virtual y la reserva.

**Recomendaciones.** Amazon personaliza a partir de historial de navegación, historial de compra,
productos vistos juntos y valoraciones. Es el referente del filtrado colaborativo aplicado a
escala.

📷 *Capturas: búsqueda con filtros de talla, ficha de producto con selector de variante,
checkout y seguimiento de pedido.*

### 2.2 Alibaba

**Qué es.** Plataforma **B2B mayorista** que conecta compradores de todo el mundo con fabricantes
y distribuidores, principalmente chinos. No es una tienda: es un directorio transaccional de
proveedores. Su equivalente minorista es AliExpress.

**Diferencias clave frente a un B2C.**

- **Cantidad mínima de pedido (MOQ)** — no se compra una unidad, sino lotes.
- **Precios por escala** — el precio unitario baja según el volumen.
- **Negociación** — el flujo típico no es "agregar al carrito" sino **solicitar cotización (RFQ)**
  y conversar con el proveedor.
- **Verificación del proveedor** — sellos como *Verified Supplier* y *Gold Supplier*, años de
  antigüedad, tasa de respuesta y volumen histórico. La confianza es el producto que vende la
  plataforma.
- **Trade Assurance** — retención del pago hasta que el comprador confirma que recibió lo
  acordado; es un mecanismo de custodia (*escrow*).
- **Muestras** — se compran unidades de muestra antes del pedido grande.

**Relevancia para Violet Boutique.** Alibaba es el modelo del **lado proveedor** del sistema: una
cadena de tiendas de ropa se abastece exactamente así, comprando por lote a distintos
proveedores según temporada. El actor *Proveedor* (A5) y el caso de uso *Registrar ingreso de
mercadería* (CU-13) reproducen la punta final de este proceso.

📷 *Capturas: ficha de un producto con MOQ y precios por escala, perfil de un proveedor
verificado, formulario de solicitud de cotización.*

### 2.3 Shopify

**Qué es.** Una diferencia que conviene marcar desde el inicio: **Shopify no es un marketplace**.
Es una plataforma **SaaS** que le permite a cualquier persona **crear su propia tienda en línea**
sin programar ni administrar servidores. El comprador final no "compra en Shopify": compra en la
tienda de una marca, que por debajo funciona con Shopify.

**Como usuario comprador** — la experiencia es la de la tienda de cada marca: catálogo, ficha con
variantes, carrito y **Shopify Checkout**, un proceso de pago estandarizado y reconocible, con
*Shop Pay* para acelerar la compra recurrente.

**Como comerciante** — panel de administración con productos y variantes, inventario,
pedidos, clientes, descuentos e informes; temas para el diseño; y una tienda de aplicaciones para
extender funciones. El modelo de negocio es de **suscripción mensual más comisión por
transacción**, menor si se usa Shopify Payments.

**Ventajas y límites.** Rapidez de puesta en marcha y cero mantenimiento de infraestructura, a
cambio de costo recurrente, personalización limitada por el modelo de datos de la plataforma, y
dependencia total del proveedor: la tienda no es portable.

> ⚠️ **Shopify aparece dos veces en el enunciado**: acá, como plataforma a conocer *como usuario*,
> y en la lista de frameworks **prohibidos** para desarrollar este proyecto. Estudiarlo sí,
> usarlo no.

📷 *Capturas: una tienda pública hecha con Shopify, el checkout, y el panel de administración de
una tienda de prueba.*

---

## 3. Como desarrollador: Magento, PrestaShop y WooCommerce

El enunciado pide conocer **para qué sirven, qué beneficios aportan y cómo se usan** para crear
tiendas en línea.

### 3.1 Magento / Adobe Commerce

**Qué es.** Plataforma de e-commerce escrita en PHP, hoy propiedad de Adobe. Existe en dos
versiones: **Magento Open Source**, gratuita y autoalojada, y **Adobe Commerce**, la versión
comercial con funciones adicionales y soporte.

**Para qué sirve.** Catálogos grandes y complejos, operaciones **multi-tienda** y multi-idioma, y
funciones B2B avanzadas de serie. Es la plataforma de referencia para comercios de gran volumen.

**Cómo se usa.** Se instala en un servidor propio (PHP, MySQL/MariaDB, Elasticsearch/OpenSearch,
Redis), se configura desde el panel de administración y se extiende con **módulos** y **temas**;
su ecosistema supera las 4.000 extensiones.

**Costo.** Magento Open Source tiene licencia de **$0**, pero exige infraestructura y personal
técnico. Adobe Commerce se licencia por volumen de ventas: los niveles publicados para 2026 van
desde alrededor de **$22.000/año** para comercios de $1–5 millones de GMV hasta **$125.000+/año**
para $25M+, y el costo total de propiedad —hosting, desarrollo, extensiones y mantenimiento—
suele ser dos o tres veces la licencia.

**Ventajas:** escalabilidad muy alta, catálogo y variantes potentes, multi-tienda nativo.
**Desventajas:** curva de aprendizaje pronunciada, alto consumo de recursos, costo de
implementación elevado. Es una plataforma pensada para equipos, no para una persona.

### 3.2 PrestaShop

**Qué es.** Plataforma de e-commerce en PHP, de código abierto y autoalojada, de origen francés y
amplia adopción en Europa y Latinoamérica.

**Para qué sirve.** Tiendas pequeñas y medianas que quieren control del código sin la complejidad
de Magento.

**Cómo se usa.** Instalación en un hosting PHP/MySQL, panel de administración propio, y extensión
mediante **módulos** y **hooks** —puntos de enganche donde un módulo inyecta comportamiento sin
tocar el núcleo—. Tiene su propio marketplace de módulos y temas.

**Costo.** Licencia **$0**; el gasto está en hosting (del orden de $1 a $200 mensuales según
escala) y en módulos de pago, que son la fuente de ingresos del ecosistema.

**Ventajas:** más liviano que Magento, comunidad amplia, buen equilibrio entre control y
simplicidad. **Desventajas:** escalabilidad media, y las actualizaciones mayores suelen romper
módulos de terceros.

### 3.3 WooCommerce

**Qué es.** No es una plataforma independiente: es un **plugin de WordPress** que convierte un
sitio de WordPress en una tienda en línea. Es la opción de e-commerce más difundida del mundo,
por herencia directa de la difusión de WordPress.

**Para qué sirve.** Negocios que ya tienen un sitio en WordPress, o proyectos pequeños donde el
contenido (blog, marca) pesa tanto como el catálogo.

**Cómo se usa.** Se instala como plugin, se configura con un asistente, y se extiende con otros
plugins y temas. La curva de aprendizaje es la más baja de las tres.

**Costo.** El plugin es **gratuito**; el gasto está en hosting, tema y —sobre todo— en los plugins
de pago que hacen falta para funciones serias.

**Ventajas:** simplicidad, comunidad enorme, integración natural con contenido y SEO.
**Desventajas:** escalabilidad baja —el rendimiento se degrada con catálogos grandes—, y la
dependencia de muchos plugins de terceros vuelve frágil el mantenimiento y amplía la superficie
de seguridad.

### 3.4 Cuadro comparativo

| | **Magento Open Source** | **PrestaShop** | **WooCommerce** |
|---|---|---|---|
| Tipo | Plataforma autoalojada | Plataforma autoalojada | Plugin de WordPress |
| Lenguaje | PHP | PHP | PHP |
| Licencia | $0 (Adobe Commerce: desde ~$22.000/año) | $0 | $0 |
| Escalabilidad | Muy alta | Media | Baja |
| Complejidad | Alta | Media | Baja |
| Multi-tienda | Nativo | Con módulos | Con plugins |
| Ideal para | Gran volumen, B2B | Pymes | Tiendas pequeñas y sitios de contenido |

### 3.5 Por qué Violet Boutique no usa ninguna de estas plataformas

El enunciado las prohíbe expresamente. Pero más allá de la restricción académica, el análisis
muestra que **ninguna resuelve de fábrica la combinación que exige este problema**:

| Necesidad de Violet Boutique | Qué ofrecen estas plataformas |
|---|---|
| **Inventario por variante y por sucursal**, con disponibilidad consultable por el cliente antes de ir a la tienda | Manejan stock por variante, pero el stock multi-almacén con consulta pública por sucursal exige extensiones de pago o desarrollo propio |
| **Reserva de varias prendas para probárselas en una sucursal**, con franja horaria, preparación por el encargado y expiración automática | No existe. Es un flujo propio de este negocio, no del comercio electrónico genérico |
| **Punto de venta presencial** integrado al mismo inventario | Existe como producto aparte y de pago |
| **Vestidor virtual con realidad aumentada** en app móvil propia | No existe |
| **IA propia**: recomendador, asistente y reportes por comando de voz | No existe; solo módulos de terceros de alcance limitado |
| **Movimientos de inventario inmutables y trazables** (RNF10) | El modelo de datos no es del equipo, así que la trazabilidad depende de lo que exponga la plataforma |

A esto se suma que el proyecto debe aplicar **PUDS y UML** sobre una arquitectura propia: adoptar
una plataforma existente dejaría sin objeto los flujos de Análisis y Diseño, que son el núcleo de
la materia.

Este razonamiento es el que sustenta el descarte de la alternativa de adoptar una plataforma de
e-commerce existente y limitarse a configurarla.

---

## Bibliografía de esta sección

- MGT Commerce. *Magento vs WooCommerce vs Shopify vs OpenCart vs PrestaShop*.
  <https://www.mgt-commerce.com/blog/magento-vs-woocommerce-vs-shopify-vs-opencart-vs-prestashop/>
- IWD Agency. *Magento Open Source vs. Adobe Commerce: A Complete 2026 Comparison*.
  <https://www.iwdagency.com/blogs/news/magento-open-source-vs-magento-commerce-a-complete-comparison/>
- Keliam. *Mejor plataforma ecommerce 2026: PrestaShop vs WooCommerce vs Magento*.
  <https://www.keliam.com/comparativa-prestashop-woocommerce-magento/>
- Litextension. *PrestaShop vs Magento: 10 Aspects Comparison (2026)*.
  <https://litextension.com/blog/prestashop-vs-magento/>
- Sitios oficiales: <https://business.adobe.com/products/magento/> · <https://www.prestashop.com/>
  · <https://woocommerce.com/> · <https://www.shopify.com/> · <https://www.amazon.com/> ·
  <https://www.alibaba.com/>

*Consultado el 02/09/2026.*
