# 4) FLUJO DE TRABAJO: ANÁLISIS

Segundo flujo de trabajo del PUDS. Se define la arquitectura en términos de paquetes de análisis,
se relacionan los paquetes con los casos de uso, se identifica el modelo de dominio preliminar y
se establece la arquitectura física de despliegue. Los diagramas de comunicación por caso de uso y
el análisis de clases detallado se desarrollan por ciclo en el documento de entrega.

---

## 4.1 Análisis de la arquitectura

### 4.1.1 Identificar paquetes

Se identifican **once paquetes de análisis**, derivados de los módulos del alcance y agrupados
por cohesión funcional. La numeración refleja el orden de dependencia: un paquete solo puede
depender de paquetes de número menor o igual, salvo las excepciones indicadas.

**P1 · Seguridad y Usuarios.**
Gestiona la identidad y el acceso: registro de clientes, autenticación por credenciales, emisión y
validación de tokens, y control de acceso basado en roles (Cliente, Administrador, Encargado de
Sucursal, Cajero, Proveedor). Es el paquete más transversal del sistema: todos los demás dependen
de él para validar quién ejecuta cada operación y sobre qué ámbito de datos (por ejemplo, un
Encargado solo opera sobre su propia sucursal). No depende de ningún otro paquete.

**P2 · Organización.**
Gestiona la estructura de la empresa: ciudades, sucursales con su dirección, horario y capacidad
de vestidores, empleados asignados a una sucursal, y proveedores. Provee a los demás paquetes la
noción de *sucursal*, que es el eje sobre el que se particionan el inventario, las reservas y las
ventas. Depende de P1 para vincular empleados y proveedores con sus usuarios.

**P3 · Catálogo.**
Gestiona la definición comercial del producto: categorías jerárquicas, tallas, colores,
temporadas, colecciones, productos, sus imágenes y sus **variantes (SKU = producto × talla ×
color)**, además de las promociones. Es el paquete que define *qué se vende*. Depende de P1 y de
P2 (proveedor del producto). Es la base de datos maestra sobre la que operan los paquetes P4, P5,
P6, P7 y P9.

**P4 · Inventario.**
Gestiona *cuánto hay y dónde*: las existencias por combinación (variante, sucursal) con su
cantidad disponible y reservada, y el registro trazable de todo movimiento (ingreso de proveedor,
reserva, liberación, venta, devolución, transferencia, ajuste). Concentra la regla de negocio más
crítica del sistema: **ninguna cantidad se modifica sin generar un movimiento**. Depende de P2
(sucursal) y P3 (variante), y es utilizado por P5, P6, P7 y P8.

**P5 · Catálogo Público y Disponibilidad.**
Expone al cliente la vista de solo lectura del catálogo: búsqueda, filtros, paginación, ficha de
producto, consulta de disponibilidad de una variante por sucursal y lista de favoritos. Es la
fachada de consulta optimizada para web y móvil; separa las necesidades de lectura del cliente de
las operaciones de mantenimiento del Administrador. Depende de P3 y P4.

**P6 · Reservas.**
Gestiona el ciclo de vida completo de la reserva de prendas para prueba presencial: creación con
múltiples variantes, sucursal y franja horaria; notificación a la sucursal; preparación y atención
por el Encargado; cancelación por el cliente; expiración automática; y derivación a venta
presencial. Cada transición de estado produce un movimiento en P4. Depende de P1, P2, P3 y P4.

**P7 · Ventas y Punto de Venta.**
Gestiona la venta en sus dos canales sobre una misma entidad: el carrito y el pedido digital
(web/móvil) y la venta presencial en caja (POS), incluidas la apertura y cierre de caja, la
emisión de comprobantes y las devoluciones. Es el paquete que unifica ambos canales de venta
sobre el mismo inventario. Depende de P1, P2, P3, P4 y P6 (una reserva atendida puede convertirse
en venta).

**P8 · Pagos.**
Gestiona el cobro: la iniciación del pago electrónico contra la pasarela, la recepción y
verificación de su notificación (*webhook*), la confirmación del pedido, y el registro del cobro
presencial en efectivo o tarjeta. Aísla la integración con el servicio externo del resto del
sistema, de modo que cambiar de pasarela no afecte a P7. Depende de P7 y del actor externo
Pasarela de Pago.

**P9 · Vestidor Virtual (Realidad Aumentada).**
Reside principalmente en la aplicación móvil. Gestiona la sesión de prueba virtual: obtención de
la imagen de cámara, detección de la pose corporal, superposición de la imagen de la prenda
seleccionada ajustada al cuerpo, cambio de variante en vivo, captura del resultado y derivación a
reserva o carrito. Depende de P3 (imagen y variante de la prenda) y del actor externo Servicio de
Realidad Aumentada; se comunica con P5, P6 y P7.

**P10 · Inteligencia Artificial.**
Gestiona las funcionalidades inteligentes: el recomendador de prendas, el asistente conversacional
y la generación de reportes bajo demanda por comando de voz. Consume los datos de los demás
paquetes y delega el razonamiento en el actor externo Servicio de Inteligencia Artificial. No es
consultado por ningún otro paquete: es un consumidor, nunca un proveedor de datos, lo que permite
desactivarlo sin afectar la operación del sistema.

**P11 · Reportes y Tablero.**
Gestiona la consolidación de información para la toma de decisiones: cálculo de los KPIs en tiempo
real y generación de reportes exportables a PDF y Excel. Depende de todos los paquetes
transaccionales (P4, P6, P7, P8) en modo de solo lectura.

> **Nota sobre P8 y P11.** Podrían haberse absorbido dentro de P7 (Ventas) y del resto de los
> paquetes transaccionales. Se documentan como paquetes propios porque tienen naturalezas
> distintas: P8 concentra todo el acoplamiento con un servicio externo, y P11 es de solo lectura.
> Aislarlos permite sustituir la pasarela de pago o agregar reportes sin tocar la lógica de venta.

### 4.1.2 Relacionar paquetes y casos de uso

| Paquete | Casos de uso que realiza |
|---|---|
| **P1 · Seguridad y Usuarios** | CU-01, CU-02, CU-03, CU-04 |
| **P2 · Organización** | CU-05, CU-06, CU-07 |
| **P3 · Catálogo** | CU-08, CU-09, CU-10, CU-11, CU-12 |
| **P4 · Inventario** | CU-13, CU-14, CU-15, CU-16 |
| **P5 · Catálogo Público y Disponibilidad** | CU-17, CU-18, CU-19, CU-20 |
| **P6 · Reservas** | CU-22, CU-23, CU-24, CU-25 |
| **P7 · Ventas y Punto de Venta** | CU-26, CU-27, CU-29, CU-30, CU-31, CU-32 |
| **P8 · Pagos** | CU-27 (parcial), CU-28 |
| **P9 · Vestidor Virtual (RA)** | CU-21 |
| **P10 · Inteligencia Artificial** | CU-33, CU-34, CU-35 |
| **P11 · Reportes y Tablero** | CU-36, CU-37 |

### 4.1.3 Vista de paquetes (dependencias)

```
                        ┌──────────────────────┐
                        │  P1 Seguridad y      │  ◄──── (todos dependen de P1)
                        │     Usuarios         │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │  P2 Organización     │
                        │  (ciudad, sucursal,  │
                        │   empleado, prov.)   │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │  P3 Catálogo         │
                        │  (producto, variante,│
                        │   temporada, colec.) │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │  P4 Inventario       │
                        │  (existencia,        │
                        │   movimiento)        │
                        └───┬──────┬───────┬───┘
                            │      │       │
              ┌─────────────▼─┐ ┌──▼─────┐ │
              │ P5 Catálogo   │ │ P6     │ │
              │    Público    │ │Reservas│ │
              └───┬───────────┘ └───┬────┘ │
                  │                 │      │
                  │        ┌────────▼──────▼────┐
                  │        │ P7 Ventas y POS    │
                  │        └─────────┬──────────┘
                  │                  │
                  │        ┌─────────▼──────────┐      ┌─────────────────┐
                  │        │ P8 Pagos           │─────►│ «externo»       │
                  │        └────────────────────┘      │ Pasarela de Pago│
                  │                                    └─────────────────┘
        ┌─────────▼──────────┐                         ┌─────────────────┐
        │ P9 Vestidor Virtual│────────────────────────►│ «externo»       │
        │      (RA, móvil)   │                         │ Servicio de RA  │
        └────────────────────┘                         └─────────────────┘

        ┌────────────────────┐                         ┌─────────────────┐
        │ P10 Inteligencia   │────────────────────────►│ «externo»       │
        │      Artificial    │  (lee P3,P4,P5,P6,P7)   │ Servicio de IA  │
        └────────────────────┘                         └─────────────────┘

        ┌────────────────────┐
        │ P11 Reportes y     │  (solo lectura sobre P4, P6, P7, P8)
        │      Tablero       │
        └────────────────────┘
```

**Regla arquitectónica.** Las dependencias son unidireccionales y descendentes. Un paquete nunca
depende de otro de nivel superior; la comunicación en sentido inverso se realiza mediante eventos
o consultas de solo lectura. Esta regla es la que permite desarrollar el Ciclo 1 (P1–P3) sin que
los paquetes de los Ciclos 2 y 3 existan todavía, y el Ciclo 2 (P4–P6) sin los del Ciclo 3.

### 4.1.4 Paquetes por ciclo

| Ciclo | Entrega | Paquetes | Alcance |
|---|---|---|---|
| **1** | 05/09 | P1 · P2 · P3 (maestros) | Seguridad, organización y la taxonomía del catálogo (categorías, tallas, colores, temporadas, colecciones) |
| **2** | 13/09 | P3 (productos) · P4 · P5 · P6 | Productos y variantes, inventario, catálogo público y reservas |
| **3** | 20/09 | P3 (promociones) · P5 (favoritos) · P7 · P8 · P9 · P10 · P11 | Ventas, pagos, POS, vestidor virtual, IA y reportes |

P3 (Catálogo) es el único paquete que se construye en los tres ciclos: primero sus maestros
—necesarios para que exista una variante—, después los productos y sus variantes, y por último las
promociones. P5 aporta el catálogo público en el Ciclo 2 y los favoritos en el Ciclo 3.

## 4.2 Modelo de dominio preliminar

Clases de entidad identificadas en el análisis. Los atributos se detallan en el flujo de Diseño.

| Paquete | Clases de entidad |
|---|---|
| P1 | `Usuario`, `Rol`, `Permiso`, `Cliente`, `SesionToken` |
| P2 | `Ciudad`, `Sucursal`, `Empleado`, `Proveedor` |
| P3 | `Categoria`, `Talla`, `Color`, `Temporada`, `Coleccion`, `Producto`, `VarianteProducto`, `ImagenProducto`, `Promocion` |
| P4 | `Existencia`, `MovimientoInventario`, `TipoMovimiento` |
| P5 | `Favorito`, `EventoNavegacion` |
| P6 | `Reserva`, `DetalleReserva`, `EstadoReserva` |
| P7 | `Carrito`, `ItemCarrito`, `Venta`, `DetalleVenta`, `Comprobante`, `Caja`, `TurnoCaja`, `Devolucion` |
| P8 | `Pago`, `TransaccionPasarela` |
| P9 | `SesionVestidorVirtual` |
| P10 | `Recomendacion`, `ConversacionAsistente`, `SolicitudReporteIA` |

### 4.2.1 Decisiones de análisis relevantes

**D1 — La variante (SKU) es la unidad de negocio, no el producto.**
`Producto` describe la prenda ("Camisa Oxford manga larga"); `VarianteProducto` representa la
combinación concreta talla × color, que es la que tiene código propio, precio, existencia, reserva
y venta. Todo el inventario, las reservas y las ventas referencian **variante**, nunca producto.
Sin esta separación es imposible cumplir RF05, RF08 y RF21.

**D2 — Un solo concepto de venta con dos canales.**
La venta digital y la venta presencial se modelan sobre la misma clase `Venta`, diferenciadas por
el atributo `canal` (`DIGITAL` | `PRESENCIAL`) y por la forma de pago asociada. Esto evita
duplicar la lógica de descuento de inventario, la emisión de comprobantes y los reportes, y
permite que una reserva atendida se convierta en venta presencial sin transformación de datos.

**D3 — La existencia se descompone en disponible y reservado.**
`Existencia` mantiene `cantidad_disponible` y `cantidad_reservada` por (variante, sucursal). Una
reserva no descuenta el stock: lo traslada de disponible a reservado. La venta descuenta de
reservado (si vino de una reserva) o de disponible (si es venta directa). La expiración de una
reserva devuelve la cantidad de reservado a disponible. Este modelo es el que hace posible mostrar
disponibilidad real al cliente y evitar la sobreventa.

**D4 — Todo cambio de existencia genera un `MovimientoInventario` inmutable.**
Los movimientos nunca se editan ni se eliminan; una corrección se registra como un nuevo
movimiento de ajuste. `Existencia` es, conceptualmente, el saldo de sus movimientos. Realiza el
RNF10 y es lo que vuelve auditable un inventario que hoy se lleva a mano y sin rastro.

**D5 — El estado del pago solo lo determina la pasarela.**
El pedido pasa a *pagado* únicamente al recibir y verificar la notificación (webhook) firmada por
la pasarela, nunca por la redirección del navegador del cliente, que es manipulable. El
procesamiento de la notificación es idempotente: una notificación repetida no descuenta el
inventario dos veces. Realiza el RNF09.

**D6 — El paquete de IA es un consumidor, nunca una fuente de verdad.**
El recomendador y el asistente leen datos del sistema y producen sugerencias o texto; ninguna
decisión de negocio (precio, existencia, estado de pedido) depende de su respuesta. Ante la caída
o el error del servicio externo, el sistema degrada a un comportamiento por defecto (por ejemplo,
recomendaciones basadas en reglas: más vendidos de la temporada vigente en la talla del cliente)
sin interrumpir la operación.

## 4.3 Arquitectura física preliminar (vista de despliegue)

```
┌────────────────────────┐        ┌──────────────────────────┐
│ «dispositivo»          │        │ «dispositivo»            │
│ Teléfono Android       │        │ PC / Navegador           │
│ ┌────────────────────┐ │        │ ┌──────────────────────┐ │
│ │ App FashionStore   │ │        │ │ SPA Angular          │ │
│ │ (Flutter/Dart)     │ │        │ │ (cliente / admin /   │ │
│ │  + Vestidor Virtual│ │        │ │  encargado / cajero) │ │
│ └────────────────────┘ │        │ └──────────────────────┘ │
└───────────┬────────────┘        └────────────┬─────────────┘
            │  HTTPS / JSON                    │  HTTPS / JSON
            └───────────────┬──────────────────┘
                            │
              ┌─────────────▼───────────────────┐
              │ «nodo de ejecución» (nube)      │
              │  Servidor de Aplicación         │
              │  ┌───────────────────────────┐  │
              │  │ API REST FastAPI (Uvicorn)│  │
              │  │  P1..P8, P10, P11         │  │
              │  └───────────────────────────┘  │
              └───┬─────────┬──────────┬────────┘
                  │ SQL/TLS │ HTTPS    │ HTTPS
     ┌────────────▼──┐  ┌───▼────────┐ │  ┌──────────────────┐
     │ «nodo» (nube) │  │ «externo»  │ └─►│ «externo»        │
     │ PostgreSQL    │  │ Pasarela   │    │ Servicio de IA   │
     │ (gestionado)  │  │ de Pago    │    │ (API)            │
     └───────────────┘  └────────────┘    └──────────────────┘
                  ┌──────────────────────┐
                  │ «nodo» Almacenamiento│  ◄── imágenes de productos
                  │ de objetos / CDN     │      (servidas al cliente)
                  └──────────────────────┘
```

**Características de la arquitectura física**

- **Backend sin estado.** El servidor de aplicación no guarda sesión en memoria; la identidad
  viaja en el token JWT. Esto permite replicar el nodo horizontalmente y realiza el RNF04.
- **Una única API para dos clientes.** Angular y Flutter consumen exactamente el mismo contrato
  REST, sin lógica de negocio duplicada en el cliente. Realiza RNF07 y RNF08.
- **Base de datos gestionada.** PostgreSQL como servicio, con respaldos automáticos, fuera del
  nodo de aplicación. Realiza RNF03.
- **Imágenes fuera de la aplicación.** Las imágenes de productos se sirven desde almacenamiento de
  objetos, no desde el servidor FastAPI, lo que descarga la API y mejora los tiempos de respuesta
  del catálogo. Realiza RNF02.
- **Servicios externos aislados tras adaptadores.** La pasarela de pago y el servicio de IA se
  consumen a través de un adaptador propio en el backend; ninguna capa de negocio conoce sus
  detalles. Permite sustituirlos sin propagar cambios.
- **Sin localhost.** Los tres nodos propios (aplicación, base de datos, frontend web) y el
  almacenamiento de imágenes residen en la nube con URL pública y HTTPS, conforme a RNF13.
