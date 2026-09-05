# Parte I — Fundamentación Teórica · índice y guía

**Estado: redactado.** Este archivo es el índice y la guía; el contenido está en los cinco
documentos que se listan abajo. Sirve para verificar que ninguna exigencia del enunciado se pasó
por alto.

> **Lo único que falta son las capturas propias.** El enunciado pide *experimentar* con Amazon,
> Alibaba y Shopify como usuario. El documento `01-ecommerce.md` marca con 📷 los seis puntos
> donde van esas capturas. Sin ellas la sección a.a queda incompleta, por bien redactada que
> esté.

El enunciado pide expresamente *"revisar en libros o sitios en internet especializados en la
temática"*. Cada afirmación con dato duro (comisiones, plazos, porcentajes) debe llevar su fuente
en la bibliografía; los datos inventados o desactualizados son lo primero que se nota en una
defensa.

---

## Estructura exigida (literal del enunciado)

```
Parte I – Fundamentación Teórica
  a) E-commerce
       a. Como usuario:      Amazon · Alibaba · Shopify
       b. Como desarrollador: Magento · PrestaShop · WooCommerce
  b) Pasarelas de pago
       a. Formas de pago online (débito, crédito, QR, transferencias)
       b. LIBÉLULA
       c. PayPal · STRIPE
  c) Deliverys
       a. Cómo funcionan (ejemplo Yaigo – Yummy)
       b. Cómo calculan el pago de una entrega
  d) PUDS
  e) UML
```

## Archivos

| # | Archivo | Contenido | Estado |
|---|---|---|---|
| a | [`01-ecommerce.md`](01-ecommerce.md) | Conceptos y características; Amazon, Alibaba y Shopify como usuario; Magento, PrestaShop y WooCommerce como desarrollador; por qué no se usa ninguno | ✔ redactado · faltan las capturas 📷 |
| b | [`02-pasarelas-de-pago.md`](02-pasarelas-de-pago.md) | Actores y etapas de un cobro; débito, crédito, QR y transferencias; **Libélula**; **PayPal**; **Stripe** | ✔ redactado |
| c | [`03-deliverys.md`](03-deliverys.md) | Ciclo de un pedido; Yaigo, Yummy y el mercado boliviano; cálculo de la tarifa de entrega | ✔ redactado |
| d | [`04-puds.md`](04-puds.md) | Origen, las tres características, fases, flujos de trabajo y aplicación al proyecto | ✔ redactado |
| e | [`05-uml.md`](05-uml.md) | Qué es UML, los catorce diagramas, notación y los que usa este proyecto | ✔ redactado |

---

## a) E-commerce

### Conceptos generales y características

Definición de comercio electrónico; modelos de negocio (B2C, B2B, C2C, marketplace); elementos
que componen una tienda en línea (catálogo, carrito, checkout, pasarela, logística, postventa);
diferencias entre tienda propia y marketplace.

**Conectar con el proyecto:** Violet Boutique es un B2C de tienda propia con retiro y prueba en
sucursal — un modelo híbrido físico-digital que no es el de un e-commerce puro. Conviene decirlo
explícitamente, porque justifica por qué no se usa un framework de e-commerce.

### a.a) Como usuario — Amazon, Alibaba, Shopify

El enunciado pide *conocer detalladamente cómo funciona*, es decir **usarlos**, no describirlos
desde afuera. Crear una cuenta en cada uno y recorrer el flujo completo, documentando con
capturas propias.

Por cada plataforma, responder:

- Qué es y a qué modelo de negocio responde (Amazon: marketplace + retail propio; Alibaba: B2B
  mayorista; Shopify: plataforma para crear tu propia tienda — **no** es un marketplace).
- Recorrido de compra completo: búsqueda → filtros → ficha de producto → carrito → checkout →
  métodos de pago → seguimiento del pedido → devoluciones.
- Cómo resuelven la **talla y la variante** en indumentaria (es el problema central de este
  proyecto): guías de talla, reseñas con talle, recomendación de talla.
- Qué hacen con las **recomendaciones** y en qué se basan.
- Qué elementos de su experiencia **se replican en Violet Boutique** y cuáles no, y por qué.

> Shopify aparece acá como usuario y también en la lista de frameworks **prohibidos** por el
> enunciado (junto con PrestaShop, Magento y WooCommerce). Estudiarlo sí; usarlo no.

### a.b) Como desarrollador — Magento, PrestaShop, WooCommerce

Por cada uno: para qué sirve, qué beneficios aporta y cómo se usa para crear un sitio de tienda
en línea.

- Qué es y sobre qué corre (Magento/Adobe Commerce: PHP, orientado a gran escala; PrestaShop:
  PHP, autoalojado; WooCommerce: plugin de WordPress).
- Licencia, costo y modelo de negocio de cada uno.
- Qué trae resuelto de fábrica: catálogo, variantes, inventario, checkout, pasarelas,
  multi-tienda, roles.
- Cómo se instala y se extiende (módulos, temas, hooks).
- Ventajas y desventajas frente a un desarrollo a medida.

**Cierre obligatorio de la sección.** El enunciado prohíbe usarlos. Hay que explicar por qué el
desarrollo a medida es la opción correcta para este caso — y el argumento no es "porque lo pide
el examen", sino que ninguno resuelve de fábrica la combinación que exige el problema: inventario
multisucursal con reserva para prueba física, POS de sucursal, vestidor virtual con RA e IA
integrada. Es el razonamiento que sustenta descartar la alternativa de adoptar una plataforma
de e-commerce existente y limitarse a configurarla.

---

## b) Pasarelas de pago

### b.a) Formas de pago en línea

Describir **cómo funcionan**, no solo enumerarlas. Para cada una: quiénes intervienen (comercio,
pasarela, adquirente, marca, emisor), qué viaja en cada paso y cuánto tarda en acreditarse.

| Forma de pago | Qué explicar |
|---|---|
| Tarjeta de **débito** | Debita del saldo en el momento; autorización y captura; menor riesgo de contracargo |
| Tarjeta de **crédito** | Línea de crédito del emisor; autorización, captura y liquidación diferida; contracargos |
| **QR** | QR estático vs. dinámico; interoperabilidad; en Bolivia, el QR del BCB; acreditación inmediata |
| **Transferencias** | Bancarias y de billeteras; conciliación manual y por qué es el método más difícil de automatizar |

Conviene explicar acá el concepto de **sandbox** o entorno de pruebas, porque es el que usa este
proyecto (RNF09).

### b.b) LIBÉLULA

Pasarela boliviana. Investigar: qué es y quién la opera, qué métodos de cobro ofrece (tarjetas,
QR, pago en efectivo en entidades), cómo se integra (API, checkout alojado, plugins), qué
requisitos comerciales pide para habilitar una cuenta, y su esquema de comisiones.

**Relevancia para el proyecto:** es la opción realista para un comercio boliviano en producción,
y **es también el motivo por el que no se integra acá** — exige convenio comercial, inviable en un
proyecto académico. Eso hay que decirlo (ver `docs/06-decisiones-tecnicas.md` §6.7).

### b.c) PayPal y Stripe

Por cada una: cobertura geográfica, métodos que acepta, modelo de comisiones, cómo se integra
(SDK, checkout alojado, webhooks) y qué ofrece su entorno de pruebas.

**Stripe merece más profundidad**: es la pasarela que integra este proyecto. Explicar el flujo
`Checkout Session` → redirección → **webhook firmado** → confirmación, y por qué el estado del
pago lo determina el webhook y nunca la redirección del navegador (decisión D5 del análisis).

---

## c) Deliverys

### c.a) Cómo funcionan

Tomar **Yaigo** y **Yummy** como casos. Describir: los tres actores (cliente, comercio,
repartidor) y cómo la plataforma los coordina; el ciclo de un pedido desde que se confirma hasta
que se entrega; cómo se asigna el repartidor; el seguimiento en tiempo real; y el modelo de
ingresos de la plataforma (comisión al comercio, tarifa al cliente, publicidad).

### c.b) Cómo calculan el pago de una entrega

El enunciado nombra los factores: **distancia, peso, frecuencia y tamaño de la entrega**.
Explicar cómo influye cada uno y cómo se combinan en una tarifa:

- **Tarifa base** + costo por kilómetro; distancia en ruta real, no en línea recta.
- **Peso y volumen**: el *peso volumétrico* y por qué un paquete liviano pero grande cuesta como
  uno pesado.
- **Frecuencia y demanda**: tarifa dinámica en horas pico, clima o escasez de repartidores.
- **Tamaño**: si entra en una mochila, si exige vehículo, si permite agrupar varias entregas.
- Otros: tiempo de espera en el comercio, zona, propina.

**Cierre.** El delivery propio está **fuera del alcance** de Violet Boutique
(`docs/01-perfil.md` §1.4.2): el sistema registra el envío a domicilio como modalidad de entrega
con dirección y costo, pero no asigna repartidores ni calcula rutas. Decirlo explícitamente
evita que la docente asuma que se prometió algo que no está.

---

## d) PUDS — Proceso Unificado de Desarrollo de Software

- Origen y autores (Jacobson, Booch, Rumbaugh).
- Las tres características que lo definen: **dirigido por casos de uso**, **centrado en la
  arquitectura**, **iterativo e incremental**. Explicar qué significa cada una, no solo
  nombrarlas.
- Las cuatro **fases**: Inicio, Elaboración, Construcción, Transición, y el objetivo de cada una.
- Los **flujos de trabajo**: Modelado del Negocio, Requisitos, Análisis, Diseño, Implementación y
  Pruebas — y cómo cada iteración los recorre todos, en distinta proporción.
- El diagrama de las "jorobas" (esfuerzo de cada flujo a lo largo de las fases).
- Artefactos que produce cada flujo.
- Comparación breve con un método ágil, y por qué para este proyecto se usa PUDS.

**Conectar con el proyecto:** los tres ciclos de Violet Boutique (`docs/05-plan-y-cronograma.md`
§5.2) son iteraciones del PUDS, una por presentación. Mostrar la tabla de ciclos como aplicación
concreta de la teoría.

## e) UML 2.5+

- Qué es UML, quién lo mantiene (OMG) y qué aporta la versión 2.5.
- Los **catorce diagramas**, clasificados en **estructurales** (clases, objetos, componentes,
  despliegue, paquetes, perfiles, estructura compuesta) y **de comportamiento** (casos de uso,
  actividad, estados, secuencia, comunicación, tiempos, visión general de interacción).
- Elementos y notación de cada diagrama que se usa en el proyecto.
- Relación entre diagramas y flujos de trabajo del PUDS.

**Los que efectivamente se usan en este proyecto** — conviene presentarlos así, porque es lo que
la docente va a buscar en el documento:

| Flujo de trabajo | Diagrama UML |
|---|---|
| Requisitos | Casos de uso |
| Análisis | Comunicación · Clases de análisis · Paquetes |
| Diseño | Secuencia · Clases de diseño · Paquetes · Despliegue |
| Diseño de datos | Entidad-relación (no es UML estricto; se acompaña del diagrama de clases) |

---

## Bibliografía

Llevar la lista desde el inicio, no reconstruirla al final. Formato APA. Para cada fuente:
autor/organización, título, año, URL y fecha de consulta. Las páginas oficiales de Amazon,
Alibaba, Shopify, Magento, PrestaShop, WooCommerce, Libélula, PayPal, Stripe, Yaigo y Yummy son
fuentes válidas y preferibles a artículos de terceros para datos de comisiones y funcionalidades.
