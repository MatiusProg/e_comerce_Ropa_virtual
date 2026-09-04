# 6) DECISIONES TÉCNICAS

El enunciado fija el stack principal (FastAPI, Angular, Flutter/Dart, PostgreSQL, IA vía API, RA
en móvil, pasarela de pago). Este documento registra las decisiones **que sí corresponde tomar al
equipo**: bibliotecas concretas, enfoque de la realidad aumentada, diseño de la integración de IA,
elección de pasarela y plataformas de despliegue. Cada decisión indica alternativas evaluadas y el
motivo de la elección.

---

## 6.1 Backend — FastAPI

| Aspecto | Decisión | Motivo |
|---|---|---|
| Framework | **FastAPI** (Python 3.13) | Exigido por el enunciado. Genera documentación OpenAPI automática, que sirve como contrato para Angular y Flutter (RNF07). |
| Servidor | **Uvicorn** detrás de Gunicorn en producción | Estándar ASGI; permite múltiples *workers* sin estado. |
| ORM | **SQLAlchemy 2.0** (estilo declarativo con tipado) | Control fino de las transacciones y de los bloqueos de fila, necesario para evitar la sobreventa (RNF11). |
| Migraciones | **Alembic** | Versionado del esquema en el repositorio; evita el "funciona en mi máquina" y permite reconstruir la base desde cero. |
| Validación | **Pydantic v2** (esquemas de entrada y salida separados por operación) | Validación declarativa y serialización; nunca se expone el modelo ORM directamente. |
| Autenticación | **JWT** (`python-jose`) con expiración corta + hash de contraseña con **bcrypt** (`passlib`) | RNF01. El token porta el `user_id`, el rol y, cuando corresponde, el `sucursal_id`. |
| Autorización | Dependencia de FastAPI que verifica rol y ámbito de sucursal en cada endpoint | Un Encargado no debe poder consultar ni operar sobre otra sucursal. |
| Tareas programadas | **APScheduler** dentro de la aplicación | Expiración de reservas vencidas (CU-25). Un *cron* externo sería una dependencia más de infraestructura sin beneficio en este plazo. |
| Reportes | **ReportLab** (PDF) y **openpyxl** (Excel) | CU-37. |
| Pruebas | **pytest** + `httpx.AsyncClient` sobre base de datos de prueba | Flujo de Pruebas del PUDS. |

### Organización por capas

Cada paquete de análisis (§4.1.1) se corresponde con un módulo del backend, y dentro de cada
módulo se respetan cuatro capas:

```
router (HTTP, validación, autorización)
   ↓
service (reglas de negocio, transacciones)
   ↓
repository (consultas, sin lógica de negocio)
   ↓
model (SQLAlchemy)
```

**Regla:** ningún *router* accede directamente al modelo, y ninguna regla de negocio vive en el
*router*. Esto realiza el RNF06 y hace que los diagramas de secuencia del flujo de Diseño se
correspondan literalmente con el código.

## 6.2 Base de datos — PostgreSQL

| Aspecto | Decisión |
|---|---|
| Versión | PostgreSQL 16 |
| Proveedor | **PostgreSQL gestionado por Supabase** (decisión del 02/09/2026; ver §6.9). Railway hospeda solo la API y la web |
| Claves | Enteras autoincrementales; código de negocio (SKU, número de venta) como columna única aparte |
| Índices | Sobre las columnas de filtrado del catálogo (categoría, temporada, colección, talla, color, precio) y sobre `(variante_id, sucursal_id)` en existencias |
| Búsqueda de texto | Índice **GIN** sobre `to_tsvector` del nombre y la descripción del producto (RNF02) |
| Concurrencia | `SELECT ... FOR UPDATE` sobre la fila de `existencia` dentro de la transacción de reserva y de venta (RNF11) |
| Integridad | Restricciones `CHECK` de cantidades no negativas; `UNIQUE (producto_id, talla_id, color_id)` en variantes; `UNIQUE (variante_id, sucursal_id)` en existencias |
| Datos de prueba | Script de *seed* versionado: 3 ciudades, 5 sucursales, 4 proveedores, ~60 productos con variantes, imágenes y stock distribuido |

## 6.3 Frontend web — Angular

| Aspecto | Decisión | Motivo |
|---|---|---|
| Versión | **Angular 22** con componentes *standalone* y *signals* | Menos código repetitivo que los módulos clásicos. |
| Componentes de UI | **Angular Material** | Componentes accesibles y responsivos ya resueltos; ahorra tiempo de diseño en un plazo corto (RNF05). |
| Gráficos | **Chart.js** vía `ng2-charts` | Tablero de KPIs (CU-36). |
| Estado | Servicios con *signals*; sin NgRx | NgRx no se justifica para el tamaño de este sistema y consumiría tiempo de desarrollo. |
| Autenticación | Interceptor HTTP que adjunta el JWT; guardas de ruta por rol | Cada rol accede a un área distinta (cliente, administración, sucursal, caja). |
| Comando de voz | **Web Speech API** (`SpeechRecognition`) del navegador | CU-35; no requiere biblioteca externa ni servicio adicional de transcripción. |

**Áreas de la aplicación web:** tienda pública (catálogo, ficha, carrito, pedidos), panel de
administración, panel de sucursal (reservas e inventario) y punto de venta (caja).

## 6.4 Aplicación móvil — Flutter

| Aspecto | Decisión |
|---|---|
| Versión | Flutter 3.x / Dart 3.x |
| Cliente HTTP | **Dio** con interceptor de token y manejo centralizado de errores |
| Estado | **Riverpod** |
| Cámara | Paquete **`camera`** |
| Detección de pose | **`google_mlkit_pose_detection`** (ML Kit, procesamiento en el dispositivo) |
| Alcance | Catálogo, ficha de producto, disponibilidad, **vestidor virtual**, reservas, carrito y compra, historial, recomendaciones y asistente |
| Distribución | APK firmado publicado en las *releases* del repositorio de GitHub |

## 6.5 Realidad aumentada — enfoque del vestidor virtual

**Alternativas evaluadas**

| Opción | Descripción | Evaluación |
|---|---|---|
| A | **ARCore/ARKit con modelos 3D de prendas** (`ar_flutter_plugin`) | Requiere modelar cada prenda en 3D y simular el comportamiento de la tela. Inviable en 3 semanas y sin activos 3D disponibles. **Descartada.** |
| B | **Superposición 2D guiada por detección de pose**: la cámara detecta los puntos del cuerpo (hombros, caderas) y la imagen PNG de la prenda se escala, rota y posiciona sobre el torso en tiempo real | Se ejecuta en el dispositivo, sin costo por uso, con latencia baja; los activos son las mismas imágenes de producto ya cargadas en el catálogo. **Seleccionada.** |
| C | **Prueba virtual generativa por API de imagen**: se envía la foto del usuario y la de la prenda a un servicio que genera la imagen compuesta | Resultado visualmente superior, pero con latencia de segundos, costo por imagen y dependencia de red; inadecuado para una vista "en vivo". **Reservada como mejora opcional** para generar una imagen fija de alta calidad a partir de la captura. |

**Decisión: opción B como implementación del MVP**, con la opción C como extensión si el
cronograma lo permite.

**Diseño de la funcionalidad**

1. Desde la ficha de producto, el cliente pulsa "Probar en vestidor virtual".
2. La app abre la cámara frontal y ejecuta la detección de pose sobre cada fotograma.
3. A partir de los puntos de hombro izquierdo/derecho y cadera se calculan el ancho, el alto, el
   centro y el ángulo de inclinación del torso.
4. La imagen PNG de la prenda (fondo transparente, requisito S5) se dibuja transformada sobre esos
   valores, en la capa superior de la vista de cámara.
5. El cliente cambia de color o talla desde un selector, sin salir de la vista.
6. Puede capturar la imagen resultante, guardarla o compartirla, y **agregar la prenda a la reserva
   o al carrito** directamente desde el vestidor virtual.

**Requisito de contenido.** Cada variante debe contar con una imagen PNG frontal con fondo
transparente y proporciones consistentes. Es la dependencia crítica de este módulo y debe
prepararse durante el Ciclo 2, junto con la carga del catálogo, antes de que empiece el Ciclo 3.

## 6.6 Inteligencia artificial

**Servicio elegido:** API de Claude (Anthropic), consumida desde el backend con el SDK oficial de
Python (`anthropic`). Modelo por defecto: **`claude-opus-5`**; `claude-sonnet-5` como alternativa
de menor costo para el recomendador si el consumo lo exige.

**Principio de diseño (ver D6 en §4.2.1):** la IA nunca es fuente de verdad. Toda respuesta que
involucre precios, existencias o estados se construye a partir de datos consultados en la base de
datos; el modelo redacta, ordena y explica, pero no inventa el dato.

### CU-33 · Recomendador de prendas — enfoque híbrido

1. **Filtro determinista (SQL).** Se seleccionan candidatas por: temporada vigente, disponibilidad
   real en la sucursal preferida del cliente, talla habitual del cliente y categorías con las que
   ha interactuado. Este paso garantiza que **jamás se recomiende una prenda agotada o de talla
   inexistente**.
2. **Ordenamiento por el modelo.** Las 20 a 30 candidatas se envían al modelo junto con el perfil
   del cliente (historial resumido, tallas, categorías preferidas, presupuesto habitual), que
   devuelve las 6 mejores con una justificación breve mostrada al cliente ("combina con la
   chaqueta que compraste en julio").
3. **Degradación.** Si el servicio de IA falla o se agota la cuota, se muestra el resultado del
   paso 1 ordenado por popularidad de la temporada. La funcionalidad nunca se cae; pierde
   personalización.
4. **Caché.** La recomendación por cliente se guarda con vigencia de algunas horas y se invalida
   ante una compra o un cambio de preferencias.

### CU-34 · Asistente conversacional

Se implementa con **uso de herramientas (*tool use*)**: se declaran al modelo un conjunto acotado
de funciones —`buscar_productos`, `consultar_disponibilidad`, `consultar_estado_pedido`,
`consultar_reservas_cliente`, `recomendar`— y el modelo decide cuál invocar. El backend ejecuta la
función contra la base de datos y devuelve el resultado.

**Restricción de seguridad:** el modelo **no genera SQL** y no accede a la base de datos. Solo
puede invocar las funciones declaradas, cada una con parámetros validados y con el `cliente_id`
del token inyectado por el backend, nunca tomado de la conversación. Esto impide que un cliente
consulte los pedidos de otro mediante una instrucción manipulada en el chat.

### CU-35 · Reporte generativo por comando de voz

1. El Administrador pulsa el micrófono en el panel web; la **Web Speech API** transcribe su
   solicitud ("ventas de la sucursal Centro en agosto por categoría").
2. El texto se envía al backend, que lo procesa con el mismo mecanismo de herramientas: el modelo
   selecciona el reporte y sus parámetros (`generar_reporte(tipo, sucursal, desde, hasta,
   agrupacion)`).
3. El backend ejecuta la consulta agregada real y devuelve los datos.
4. El modelo redacta la interpretación en lenguaje natural; el sistema muestra la tabla, el gráfico
   y el texto, con opción de descargar el PDF.

Nuevamente, los números provienen de la base de datos; el modelo interpreta el pedido y redacta la
lectura, no calcula los valores.

### Control de costo

- Límite de peticiones por usuario y por día.
- Caché de recomendaciones y de reportes repetidos.
- Solo se envía al modelo el contexto necesario (candidatas y perfil resumido), nunca el catálogo
  completo.
- Las claves de la API residen en variables de entorno del servidor; **el cliente web y la app
  móvil nunca llaman al servicio de IA directamente**.

## 6.7 Pasarela de pago

| Opción | Evaluación |
|---|---|
| **Stripe (modo test)** | Cuenta inmediata sin trámite comercial; `Checkout Session` alojada por Stripe (el sistema nunca ve los datos de tarjeta); webhook firmado y verificable; tarjetas de prueba documentadas; SDK de Python oficial. **Seleccionada.** |
| PayPal (sandbox) | Alternativa válida; se mantiene como plan de respaldo si Stripe presentara restricciones regionales. |
| Libélula | Pasarela de amplio uso en Bolivia (tarjetas, QR simple, transferencias). Su integración requiere convenio comercial, inviable para un proyecto académico. **Se documenta en el marco teórico** conforme al enunciado, pero no se integra. |

**Flujo de pago (CU-27 y CU-28)**

1. El cliente confirma el pedido → el backend crea la `Venta` en estado *pendiente de pago* y
   solicita a Stripe una sesión de pago.
2. El cliente es redirigido a la página de Stripe e ingresa la tarjeta de prueba.
3. Stripe notifica el resultado al backend mediante **webhook firmado**; el backend verifica la
   firma, marca la venta como pagada, registra el `Pago` y descuenta el inventario, todo en una
   transacción **idempotente** (una notificación repetida no descuenta dos veces).
4. La redirección de retorno del navegador solo sirve para mostrar el resultado al usuario; **no
   determina el estado del pedido** (ver D5).

## 6.8 Almacenamiento de imágenes

Las imágenes de productos **no** pueden guardarse en el sistema de archivos del contenedor: en
Railway ese sistema de archivos es efímero y se pierde entero en cada despliegue. Se usa un
**volumen persistente de Railway** montado en `/app/media`, y la base de datos guarda únicamente
la ruta. Es la opción que mantiene todo dentro de un mismo proveedor y sin cuentas adicionales.

*Alternativas evaluadas:* **Supabase Storage**, que ya viene con el proyecto de base de datos y
sirve las imágenes por CDN sin que pasen por la API (mejor para el RNF02), y Cloudinary. Cualquiera
de las dos queda como mejora si el catálogo crece o si los tiempos de carga resultan insuficientes
en las pruebas. Para el Ciclo 1 no aplica: todavía no hay imágenes de producto.

**Requisito del vestidor virtual:** la imagen PNG con fondo transparente de cada variante es un
activo del mismo volumen, no un archivo aparte. Sin ella el módulo de RA no funciona (supuesto S5).

## 6.9 Despliegue en la nube — Supabase y Railway

**Decisión del 02/09/2026:** la base de datos vive en **Supabase**; **Railway** hospeda la API y
la web. Antes se había previsto usar también el PostgreSQL de Railway. El cambio responde a que
Railway cobra por uso —incluida la base, que corre las 24 horas— y el crédito del plan de prueba
es finito hasta el 22/09 (riesgo R9); Supabase ofrece PostgreSQL gestionado con un plan gratuito
que cubre de sobra el volumen de este proyecto, con respaldos y un panel para inspeccionar los
datos durante la defensa.

| Componente | Dónde vive | Notas |
|---|---|---|
| Base de datos | **Supabase** — PostgreSQL 16 gestionado | Conexión por el *session pooler*; respaldos automáticos |
| `api` | **Railway** — repositorio, *root directory* `backend/`, `Dockerfile` | Healthcheck en `/health` (declarado en `backend/railway.json`); volumen persistente en `/app/media` |
| `web` | **Railway** — repositorio, *root directory* `frontend-web/`, `Dockerfile` | Compila Angular y sirve la SPA con nginx; el puerto lo inyecta Railway como `$PORT` |
| App móvil | APK firmado en las *releases* de GitHub | Instalación directa en el dispositivo de la defensa |

### Configuración inicial (una sola vez)

**Supabase**

1. Crear el proyecto, elegir la región más cercana y **guardar la contraseña de la base**: se
   muestra una sola vez.
2. Copiar la cadena de conexión del **Session pooler** en *Project Settings → Database →
   Connection string*. Tiene la forma
   `postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`.

**Railway**

3. Crear el proyecto y conectarlo al repositorio de GitHub.
4. Agregar el servicio `api` con *root directory* `backend`, y cargar en *Variables* los nombres
   de `backend/.env.example`. `DATABASE_URL` es la cadena del pooler de Supabase.
5. Generar `JWT_SECRET_KEY` con `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
6. Crear el volumen del servicio `api` con punto de montaje `/app/media`.
7. Agregar el servicio `web` con *root directory* `frontend-web`. Generar su dominio público y
   copiarlo a `CORS_ORIGINS` del servicio `api`.
8. Copiar el dominio público del `api` a `frontend-web/src/environments/environment.prod.ts`.
9. Con el `api` ya desplegado, sembrar los datos iniciales: `python -m app.db.seed` con
   `DATABASE_URL` y `ADMIN_PASSWORD` apuntando a Supabase.

### Detalles que cuestan una tarde si se pasan por alto

- **Usar el *session pooler*, no la conexión directa.** La conexión directa de Supabase
  (`db.<ref>.supabase.co`) resuelve **solo a IPv6**. Si el contenedor de Railway no tiene salida
  IPv6, la conexión falla con un error de red que no menciona IPv6 por ningún lado, y se pierde la
  tarde buscando en el lugar equivocado. El pooler responde por IPv4.
- **Puerto 5432 (session), no 6543 (transaction).** El modo *transaction* no admite sentencias
  preparadas, y psycopg 3 las usa por defecto: las consultas fallan de forma intermitente, que es
  peor que fallar siempre.
- **`DATABASE_URL` llega como `postgresql://`**, sin controlador. SQLAlchemy necesita
  `postgresql+psycopg://`. La conversión ya está resuelta en `app/db/session.py`; no hay que
  editar la variable.
- **Las migraciones corren al arrancar el contenedor** (`alembic upgrade head` en el `CMD` del
  `Dockerfile`). Si una migración falla, el servicio no levanta — y eso es deliberado: es preferible
  a quedar sirviendo tráfico contra un esquema desactualizado.
- **CORS.** Mientras el dominio del servicio `web` no esté en `CORS_ORIGINS` del `api`, la web
  compila bien, carga bien, y ninguna petición funciona. El síntoma no menciona CORS de forma
  evidente en la consola del navegador.
- **Supabase pausa los proyectos gratuitos tras una semana sin actividad.** Entre la entrega del
  20/09 y la defensa del 22/09 hay dos días: conviene entrar al panel el día previo y verificar que
  el proyecto sigue activo, no descubrirlo delante de la docente.
- **El webhook de Stripe apunta al dominio público del `api`**, no a `localhost`. Configurarlo en
  el panel de Stripe el primer día del Ciclo 3, no el último.
- **Consumo de Railway.** Sacar la base de Railway reduce bastante el gasto, pero el `api` y la
  `web` siguen consumiendo. Vigilar el crédito desde el primer día (riesgo R9).

### Reglas de despliegue

- Ningún secreto (contraseña de Supabase, cadena de conexión, clave de firma JWT, claves de API) se
  versiona en el repositorio. `backend/.env.example` documenta los **nombres** de las variables,
  nunca sus valores.
- Existen dos entornos: **desarrollo** (PostgreSQL en `docker compose`) y **producción** (Supabase
  + Railway). La demostración y la defensa se realizan siempre sobre producción (RNF13).
- Cada ciclo cierra con un despliegue verificado, no con código sin desplegar.

## 6.10 Trabajo con Git y GitHub

| Aspecto | Decisión |
|---|---|
| Estructura | **Monorepo**: backend, frontend web, app móvil y documentación en un solo repositorio |
| Ramas | `main` (estable y desplegable) · una rama por integrante y ciclo: `MateoCiclo1`, `KarenCiclo1` — ver `docs/07-estructura-repositorio.md` §7.1 |
| Integración | Mediante **Pull Request** de la rama del integrante hacia `main`, con revisión del otro. Nunca se hace *commit* directo sobre `main` |
| Mensajes de commit | Convención `tipo(alcance): descripción` — p. ej. `feat(inventario): registrar movimiento por ingreso de proveedor` |
| Etiquetas | Una etiqueta por entrega: `v0.1-presentacion1`, `v0.2-presentacion2`, `v1.0-final`, para poder mostrar el estado exacto de cada entrega |
| Frecuencia | *Commits* diarios; nadie retiene trabajo sin subir más de un día (mitiga R8) |

## 6.11 Fronteras entre casos de uso (decisiones del Ciclo 1)

Al implementar el CU-03 aparecieron dos puntos donde el límite entre casos de uso no era
evidente. Se registran aquí porque condicionan el trabajo de los ciclos siguientes.

### 6.11.1 Quién da de alta al usuario de un Encargado o un Cajero

El paso 4 del CU-03 exige que, al crear un usuario con rol Encargado o Cajero, se le asigne una
sucursal. Eso significa crear también el **empleado**, que es el objeto del CU-06.

**Decisión: el alta la realiza el CU-03.** El caso de uso crea la cuenta y el empleado asociado en
la misma transacción, porque una cuenta de Encargado sin sucursal no es un estado válido del
sistema: no podría autorizarse ninguna operación con ella. Partir el alta en dos casos de uso
dejaría al sistema en un estado inconsistente entre uno y otro.

**Consecuencia para el CU-06.** El CU-06 no incluye el alta inicial; se ocupa del resto del ciclo
de vida del empleado: editar sus datos, cambiarlo de sucursal, darlo de baja y consultar el
listado. Cuando se implemente, extiende lo que el CU-03 ya dejó creado.

### 6.11.2 Lectura de sucursales desde el módulo de organización

El formulario del CU-03 necesita un selector de sucursales. El endpoint
`GET /organizacion/sucursales` —solo lectura, devuelve identificador, nombre y ciudad de las
sucursales activas— vive en el módulo `organizacion`, que corresponde al CU-05.

**Decisión: el endpoint permanece en `organizacion`.** Duplicarlo bajo `seguridad` habría expuesto
el mismo recurso en dos rutas distintas y habría obligado a eliminarlo al implementar el CU-05. El
módulo queda con la lectura resuelta y marcada con un `TODO CU-05`; el alta, la edición y la baja
de sucursales se agregan sobre ese mismo *router* cuando llegue su turno.

**Consecuencia para el CU-05.** Quien implemente el CU-05 debe **extender** el endpoint existente,
no declarar otro con la misma ruta: FastAPI no advierte de rutas duplicadas, se queda con la
primera registrada y la segunda queda muerta sin ningún error visible.
