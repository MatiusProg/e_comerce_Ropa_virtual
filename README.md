# Violet Boutique

Plataforma inteligente de comercio electrónico para tiendas de ropa, con
**vestidores virtuales vía realidad aumentada**, reservas para prueba en
sucursal, inventario multisucursal, punto de venta e inteligencia artificial.

Desde el 2do parcial es un **SaaS multitenant**: cada boutique es una
**empresa** con su propio catálogo, sus sucursales y su plan (Básico,
Profesional o Empresarial). Además, la caja, las reservas y el inventario
**funcionan sin conexión** y se sincronizan cuando vuelve la red.

Proyecto académico de Sistemas de Información II, S2-2026, **Grupo 15**.
Examen 1 (1er parcial) y **Examen 2 (2do parcial, metodología ICONIX)**.
Docente: MSc. Ing. Angélica Garzón Cuéllar.

> **Datos ficticios.** No se cargan datos de personas ni de empresas reales en
> ningún entorno: ni en el *seed*, ni en capturas, ni en la demostración. Los
> pagos se procesan **exclusivamente en el modo de pruebas** de la pasarela.

---

## Sistema desplegado

Todo lo demostrable corre en la nube; no se usa `localhost` para la defensa
(RNF13).

| | |
|---|---|
| **Web** | <https://ecomerceropavirtual-production-b192.up.railway.app> |
| **API** | <https://ecomerceropavirtual-production.up.railway.app> |
| **Documentación interactiva** | <https://ecomerceropavirtual-production.up.railway.app/docs> |
| **Sonda de salud** | <https://ecomerceropavirtual-production.up.railway.app/health> |

La base de datos es **Supabase**; **Railway** hospeda la API y la web. Las
migraciones corren solas al arrancar el contenedor, así que un despliegue nunca
queda sirviendo contra un esquema viejo. Detalle en
[docs/06-decisiones-tecnicas.md](docs/06-decisiones-tecnicas.md) §6.9.

**La vitrina no exige sesión.** `/tienda` y la ficha de cada prenda son públicas
a propósito: el RF07 pide que el cliente consulte el catálogo desde la web y el
móvil, y exigir una cuenta para mirar una prenda lo contradice. Lo que se ofrece
está acotado en el servidor —solo producto activo con variantes activas— y los
esquemas públicos no exponen proveedor ni precio base.

### La app móvil

| | |
|---|---|
| **APK (3ra presentación)** | <https://github.com/MatiusProg/e_comerce_Ropa_virtual/releases/tag/p3-apk> — archivo `violet-boutique-p3.apk` |
| **Siempre el último** | <https://github.com/MatiusProg/e_comerce_Ropa_virtual/releases/latest> (hoy apunta al de arriba) |

El APK de la 3ra presentación suma dos cosas al de la 2da:

- **El inventario offline del encargado (CU-21):** consulta las existencias de
  su sucursal y registra conteos y ajustes sin red; se sincronizan con el mismo
  contrato que la caja.
- **Los avisos push (CU-42)** con **Firebase Cloud Messaging**: el teléfono se
  entera cuando una operación hecha sin conexión se confirma o se rechaza, sin
  tener que abrir la app.

**Para compilarlo con push hace falta `mobile/android/app/google-services.json`**,
el archivo del proyecto de Firebase. No se versiona (está en el `.gitignore`):
lo pasa el equipo. Del lado del backend, el push se configura con
`PUSH_PROVEEDOR`, `PUSH_FCM_CREDENCIALES` y las claves VAPID de la web (ver
[Variables de producción](#variables-de-producción-nuevas-del-2do-parcial)).

Apunta a la **API desplegada**, no a `localhost`: la URL de producción es el
valor por omisión en el código, y el APK se compila **sin** `--dart-define`.
Se verifica en el binario antes de publicarlo, no en el comando --- una vez
se subió uno que apuntaba al equipo de desarrollo y el error tardó en verse.

No va dentro del repositorio porque **pesa 107 MB y Git corta en 100 MB**; un
*release* admite hasta 2 GB.

**Sigue firmado con la clave de depuración**, que es el `TODO` que deja la
plantilla de Flutter. Android lo instala igual pidiendo permiso para orígenes
desconocidos. Una firma propia es el paso que falta para publicarlo en serio.

**Sin minificar, y es a propósito.** Desde AGP 9 la minificación viene
encendida por omisión en `release`, y eso rompía el arranque: ML Kit ---el
detector de pose del vestidor--- arrastra WorkManager, que usa Room, que carga
su clase generada por reflexión. R8 la renombraba y la aplicación moría antes
del primer cuadro. Ver la nota en `mobile/android/app/build.gradle.kts`.

### Variables de producción nuevas del 2do parcial

Se cargan en Railway, en el servicio de la API. Acá van **solo los nombres**:
ningún valor ni clave se escribe en el repositorio. Están definidas, con su
valor por omisión, en `backend/app/core/config.py`.

| Variable | Para qué sirve |
|---|---|
| `TAREAS_AUTOMATICAS` | `on` prende las tareas que corren dentro del backend: copias automáticas, ofertas de fuera de temporada, expiración de reservas y pedidos, despacho de correos y de push. Apagada (`off`) en local y en las pruebas. La acompaña `TAREAS_INTERVALO_MINUTOS` |
| `PAGO_PROVEEDOR` | la pasarela: `simulada` aprueba al instante sin cobrar; en producción, Stripe en modo de pruebas |
| `PAGO_API_KEY` · `PAGO_WEBHOOK_SECRET` | la clave de la pasarela y el secreto con que se verifica la firma del webhook |
| `PAGO_URL_EXITO` · `PAGO_URL_CANCELADO` | adónde vuelve el navegador después de pagar o de cancelar |
| `PAGO_MONEDA` | la moneda con que se le habla a la pasarela (el *sandbox* de Stripe no admite bolivianos) |
| `PUSH_PROVEEDOR` | `simulado` solo deja el aviso en el log; `real` envía por FCM (app) y por Web Push (web instalada) |
| `PUSH_FCM_CREDENCIALES` | la cuenta de servicio de Firebase, en JSON o en base64 |
| `PUSH_VAPID_PUBLICA` · `PUSH_VAPID_PRIVADA` · `PUSH_VAPID_CONTACTO` | las claves VAPID de Web Push y el contacto que exige el estándar |
| `PROBADOR_IA_PROVEEDOR` | la foto realista del probador (CU-38): `simulado` compone la vista en el servidor sin llamar a nadie, `gemini` usa el modelo, `no_disponible` la apaga |

## Tecnologías

| Capa | Herramienta | Versión |
|---|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic | FastAPI **0.141** · SQLAlchemy **2.0** |
| Lenguaje del backend | Python | **3.13** — ver la advertencia de abajo |
| Base de datos | PostgreSQL | **16** en local · **17** en Supabase |
| Controlador de base de datos | psycopg | **3.3** (no psycopg2) |
| Frontend web | Angular + Angular Material | Angular **22** |
| Móvil | Flutter / Dart | Flutter **3.47** · Dart **3.13** |
| Realidad aumentada | `camera` + ML Kit Pose Detection | procesamiento en el dispositivo |
| Inteligencia artificial | Gemini | **modelo gratuito** · el SDK se fija al construir P10 |
| Analítica con ML | scikit-learn | **1.9** · GradientBoosting, KMeans e Isolation Forest |
| Avisos push | Firebase Cloud Messaging (app) + Web Push con VAPID (web) | `pywebpush` **2.5** |
| Pasarela de pago | Stripe | **modo de pruebas** |
| Correo | Brevo (API HTTP) | el SMTP de Gmail no sale de Railway; en local, `CORREO_PROVEEDOR=consola` |
| Multitenant | PostgreSQL RLS con `FORCE` + `SET ROLE violet_app` | una sola base, aislada por `empresa_id` |
| Sin conexión (web) | PWA (`@angular/service-worker`) + IndexedDB | caja, reservas e inventario |
| Sin conexión (móvil) | SQLite (`sqflite`) | reservas del cliente e inventario del encargado |
| Base de datos gestionada | Supabase | PostgreSQL **17**, por *session pooler* |
| Hospedaje | Railway | API y web, en un solo proyecto |
| Metodología | PUDS (1er parcial) · **ICONIX** (2do parcial) | UML 2.5+ en Enterprise Architect |

### ⚠️ Python 3.13, no 3.14

**Los dos usamos exactamente Python 3.13.** No es preferencia, es una
restricción: `passlib` 1.7.4 —la biblioteca que hashea las contraseñas de todo
el sistema— no recibe mantenimiento desde 2020 y no declara soporte para 3.14.
Por la misma razón **bcrypt está fijado en 4.3.0 y no debe subir a 5.x**:
passlib lee un atributo interno de bcrypt que la versión 5 eliminó.

Si ya tenés Python 3.14, no hace falta desinstalarlo: conviven. El entorno
virtual fija cuál se usa.

```powershell
winget install --id Python.Python.3.13 -e     # Windows
py -3.13 -m venv .venv                        # el venv fija la versión
```

Las versiones exactas están fijadas en `backend/requirements.txt`, verificadas
contra PyPI.

---

## Arranque rápido

Requisitos: Docker, **Python 3.13**, Node 22+, Flutter 3.47+ (solo para la app móvil).

```bash
git clone https://github.com/MatiusProg/e_comerce_Ropa_virtual.git
cd e_comerce_Ropa_virtual

docker compose up -d                     # levanta PostgreSQL 16 en el 5432

cd backend
cp .env.example .env                     # completar los valores
py -3.13 -m venv .venv                   # Windows
python3.13 -m venv .venv                 # macOS / Linux
.venv\Scripts\activate                   # Windows
source .venv/bin/activate                # macOS / Linux

pip install -r requirements.txt
alembic upgrade head                     # crea también el rol violet_app y los planes
python -m app.db.seed                    # roles, ciudades y administrador
python -m app.db.seed_catalogo           # sucursales, maestros y ~60 productos
python -m app.db.seed_operacion          # personas, inventario y reservas
python -m app.db.seed_plataforma         # el administrador de la plataforma (CU-01)
uvicorn app.main:app --reload
```

**`APP_DB_ROLE=violet_app` tiene que estar en el `.env`.** Sin él, la API se
conecta como dueña de las tablas, la RLS no se aplica y **no hay aislamiento
entre empresas**: todo parece andar y una empresa ve los datos de otra. Las
migraciones sí corren sin ese rol.

**Para iniciar sesión, el login pide el *slug* de la empresa** (por ejemplo,
`violet-boutique`). Solo el administrador de la plataforma entra sin slug.

En otra terminal:

```bash
cd frontend-web
npm install
npm start                                # http://localhost:4200
```

Verificación de que el entorno quedó bien:

```bash
# 1. La versión del intérprete del entorno virtual.
python --version                         # debe decir 3.13.x

# 2. La API responde.
curl http://localhost:8000/health        # {"status":"ok",...}

# 3. Las pruebas pasan.
cd backend && pytest                     # 1303 pruebas, todas pasan
```

Documentación interactiva de la API: <http://localhost:8000/docs>

---

## Las reglas que sostienen el sistema

Las cuatro primeras salen del flujo de Análisis del 1er parcial y están
justificadas en [docs/04-analisis-arquitectura.md](docs/04-analisis-arquitectura.md)
§4.2.1. Las dos últimas son del 2do parcial. Romper cualquiera de ellas
produce datos incorrectos **sin generar ningún error visible**.

**1. La variante (SKU), no el producto, es la unidad de negocio.**
`Producto` describe la prenda ("Camisa Oxford manga larga"). `VarianteProducto`
es la combinación talla × color, y es la que tiene código, precio, existencia,
reserva y venta. Inventario, reservas y ventas referencian **variante**, jamás
producto. Sin esta separación no se pueden cumplir RF05, RF08 ni RF21.

**2. Ninguna cantidad cambia sin generar un `MovimientoInventario`.**
Los movimientos son **inmutables**: una corrección es un movimiento nuevo de
tipo ajuste, nunca una edición del anterior. `Existencia` es el saldo de sus
movimientos. Hoy las diferencias de inventario no son atribuibles a nada
porque las planillas se sobrescriben; con esto, cada cambio queda explicado.

**3. La reserva no descuenta stock: lo traslada.**
`Existencia` lleva `cantidad_disponible` y `cantidad_reservada`.

```
reservar   →  disponible −N   reservado +N
vender     →  reservado −N    (si vino de reserva)  |  disponible −N (venta directa)
expirar    →  reservado −N    disponible +N
cancelar   →  reservado −N    disponible +N
```

Toda la operación va en **una transacción con `SELECT ... FOR UPDATE`** sobre
la fila de existencia. Sin ese bloqueo, dos clientes reservan la misma última
unidad y el sistema vende algo que no tiene.

**4. El estado del pago lo determina el webhook, nunca el navegador.**
La redirección de vuelta desde la pasarela solo sirve para mostrarle algo al
usuario — es una URL, y una URL la puede escribir cualquiera. El pedido pasa a
pagado al recibir el webhook **con la firma verificada**, y ese procesamiento
es **idempotente**: si la pasarela reenvía la notificación, el inventario no se
descuenta dos veces.

**5. El aislamiento entre empresas lo hace la base, no el código.**
Cada tabla de empresa lleva `empresa_id` con un `DEFAULT` que sale del contexto
de la petición, y una política RLS con `FORCE`. Por eso las consultas **no
filtran por empresa a mano**: si una se olvidara de filtrar, igual no vería
datos ajenos. El contexto lo fija `app/core/tenencia.py` a partir del JWT.

**6. Lo hecho sin conexión lo confirma el servidor, una sola vez.**
El dispositivo crea el UUID de cada operación, y el servidor es idempotente
por ese UUID: un reintento devuelve lo que ya se decidió. Cobrar o registrar
sin red **no confirma nada**. Si dos operaciones compiten por la misma unidad,
gana la que llega primero al servidor; la otra queda **rechazada** con su
motivo, y el dinero cobrado se marca para devolver. Un conteo físico hecho sin
red se aplica como **diferencia** contra lo que el equipo veía, así no pisa las
ventas que llegaron mientras tanto.

---

## 2do parcial: presentaciones

Los casos de uso se renumeraron desde CU-01 para el 2do parcial. El detalle
está en el Word de la entrega, `SI2 Ex2 Grupo 15.docx`.

| Presentación | Fecha | CU | Contenido | Estado |
|---|---|---|---|---|
| **1** | dom 25/10 | CU-01 a CU-12 | Empresas, planes y suscripciones · login por empresa · cuenta única del cliente · usuarios y empleados por empresa · contratar un plan · personalizar la tienda | ✅ |
| **2** | dom 01/11 | CU-13 a CU-20 | Preparar el dispositivo · venta, reserva y pago sin conexión · sincronizar · operaciones pendientes y rechazadas · caja con ventas sin conexión | ✅ |
| **3** | dom 08/11 | CU-21 a CU-45 | Inventario de la sucursal · cambios y devoluciones (en caja y por la web) · avisos por correo según el plan · reportes con IA y voz · analítica con ML · ofertas · traspasos · probador por talla · exportación y copias de seguridad · roles · avisos push · **dos aportes propios** | ✅ |

**Defensa: martes 10/11/2026, 7:00.** El reparto de la 3ra presentación es por
bloques: devoluciones, IA, ML, probador y avisos van por un lado; traspasos,
ofertas, roles, exportación y copias de seguridad, por el otro.

### Qué trae la 3ra presentación

Los 23 casos de uso que pide el enunciado (CU-21 a CU-43) y **dos aportes
propios** que no pide: en total, **45 CU** en el 2do parcial. El material de la
entrega está en [docs/entregas/Presentacion-3/](docs/entregas/Presentacion-3/).

| Módulo | CU | Qué hace |
|---|---|---|
| **Inventario y devoluciones** | CU-21 a CU-26, CU-28 | Inventario de la sucursal, también sin conexión · cambio o devolución en caja con nota y conformidad · ventana de devolución por empresa · solicitud por la web y su atención con reembolso por la pasarela · avisos por correo según el plan · reportes de gestión con devoluciones |
| **IA y analítica** | CU-27, CU-29, CU-30, CU-45 | Reporte con IA **por texto o por voz** · demanda por producto con **GradientBoosting** · segmentos de clientes con **KMeans** · dashboard analítico · **anomalías** en caja y devoluciones (aporte) |
| **Ofertas y traspasos** | CU-31 a CU-35 | Precios mayoristas · ofertas de fuera de temporada que se aplican solas · traspaso entre sucursales, su atención y los traspasos sugeridos |
| **Probador con talla real** | CU-36 a CU-38 | La prenda se dibuja con los centímetros de la talla elegida sobre la foto del cliente, y la foto realista con IA parte de esa composición ([detalle](docs/entregas/Presentacion-3/cu-36-38-probador.md)) |
| **Exportación, copias y roles** | CU-39 a CU-41 | Exportar los datos de la empresa · copias de seguridad propias de cada empresa · roles y permisos que define cada empresa |
| **Push y devolución automática** | CU-42, CU-43 | Avisos push (FCM y Web Push) de lo hecho sin conexión · devolución automática del pago de una operación rechazada |
| **Aviso de talla** | CU-44 | «Avísame cuando llegue mi talla» (aporte) |

Los dos aportes propios:

- **CU-44 · «Avísame cuando llegue mi talla».** Si la talla y el color están
  agotados, el cliente pide el aviso y le llega por push, correo y la campanita
  apenas el inventario repone. La empresa, además, ve cuántos clientes esperan
  cada variante. [Detalle](docs/entregas/Presentacion-3/aporte-aviso-talla.md).
- **CU-45 · «Detectar anomalías en caja y devoluciones».** Un **Isolation
  Forest** marca los turnos de caja y las devoluciones que se apartan de lo
  habitual (descuadres de arqueo, devoluciones en serie o fuera de hora) y
  explica por qué. Pide el plan Empresarial.
  [Detalle](docs/entregas/Presentacion-3/aporte-anomalias.md).

### Cómo probar el multitenant

Además de Violet Boutique, la plataforma tiene **cuatro organizaciones de
demostración**, una por cada combinación de plan que vale la pena mostrar.
Todo el detalle —cuentas, qué datos tiene cada una y ejemplos para la
defensa— está en
[docs/entregas/Presentacion-3/organizaciones-demo.md](docs/entregas/Presentacion-3/organizaciones-demo.md).

| Slug | Plan | Qué muestra |
|---|---|---|
| `alpaca` | Empresarial | todo, con analítica ML e IA; tiene un turno con un faltante marcado como anomalía |
| `chiquitana` | Empresarial | todo, con analítica ML e IA |
| `illimani` | Profesional | la IA anda, la analítica con ML **no** (responde 403) |
| `awayu` | Básico | **sin** IA ni analítica, y no deja crear una tercera sucursal |

En el login se escribe el slug y una de estas cuentas:

| Rol | Correo |
|---|---|
| Administrador | `admin@<slug>.test` |
| Encargado | `encargado1@<slug>.test` (uno por sucursal) |
| Cajero | `cajero1@<slug>.test` |
| Cliente | `cliente1@<slug>.test` (hasta `cliente20`) |
| Proveedor | `proveedor1@<slug>.test` |

**La contraseña de las cuentas de demostración la entrega el equipo.**

Tres cosas para ver en la defensa: el administrador de `alpaca` ve solo sus
productos `ALP-..` y el de `awayu` solo los `AWY-..`; `admin@awayu.test` con el
slug `alpaca` no entra; y `cliente1@alpaca.test` entra también con el slug
`violet-boutique`, porque la cuenta del cliente es una sola en la plataforma
(RN-13).

---

## 1er parcial: los tres ciclos

Uno por cada presentación obligatoria. El Ciclo 1 es deliberadamente el más
corto: son cuatro días y su contenido es CRUD y autenticación.

| Ciclo | Entrega | Días | CU | Contenido |
|---|---|:---:|:---:|---|
| **1 · Fundamentos** | 05/09 | 4 | 9 | Seguridad y roles · Ciudades, sucursales, empleados, proveedores · Maestros del catálogo (categorías, tallas, colores, temporadas, colecciones) |
| **2 · Núcleo del negocio** | 13/09 | 8 | 13 | Productos y **variantes** · **Inventario multisucursal** con movimientos trazables · Catálogo público y disponibilidad · **Reservas** para prueba en sucursal |
| **3 · Comercio e inteligencia** | 20/09 | 7 | 19 | **Vestidor virtual (RA)** · Carrito y **pago en línea** · **Punto de venta** · **IA**: recomendador, asistente y reportes por voz · Tablero de KPIs · Los cuatro del refinamiento (CU-38 a CU-41) |

Defensa del 1er parcial: **martes 29/09** (se aplazó desde el 22/09). Cada ciclo
cierra con software **desplegado en la nube**, no con código sin desplegar.

---

## Estructura

```
backend/
  app/core/         config, seguridad (JWT + bcrypt), dependencias de autorización
  app/db/           base declarativa, sesión, seed
  app/core/tenencia.py  el contexto de empresa (multitenant) que lee la RLS
  app/modules/      UN SUBPAQUETE POR PAQUETE DE ANÁLISIS
                    seguridad · organizacion · catalogo · inventario ·
                    catalogo_publico · reservas · ventas · pos · caja ·
                    pagos · abastecimiento · medidas · vestidor_virtual ·
                    ia · reportes · notificaciones · bitacora
                    2do parcial: plataforma (empresas, planes, suscripciones)
                    · offline (paquetes y sincronización)
                    3ra presentación: devoluciones_web · analitica ·
                    traspasos · roles · datos (exportación y copias) ·
                    avisos_talla
  app/integrations/ adaptadores de Stripe y de la API de IA
  alembic/          migraciones versionadas (0022 en adelante: 2do parcial; 0043 la última)
  tests/            pytest; los del 2do parcial empiezan con test_p2_ o test_p3_
frontend-web/
  src/app/core/     interceptor JWT, guardas por rol, servicios de API,
                    y la cola offline (offline.service.ts + IndexedDB)
  src/app/shared/   componentes reutilizables
  src/app/features/ auth · admin · tienda · sucursal · caja · reportes ·
                    asistente · plataforma · contratar · proveedor · cliente ·
                    avisos · seguridad
mobile/
  lib/core/         cliente HTTP (Dio), tema, enrutado, SQLite (base_local.dart)
  lib/data/         modelos del contrato y repositorios
  lib/features/     auth · inicio · catalogo · perfil · reservas · vestidor ·
                    compra · asistente · gestion · reportes · offline ·
                    inventario
scripts/            generadores de los diagramas UML sobre el .eapx
                    (ea-p2-*.ps1 y ea-p3-*.ps1 para el 2do parcial) y del
                    Word (word-p2/, word-p3/)
docs/
  00                índice oficial de la ingeniera y mapeo del entregable
  01 a 07           documentación PUDS
  entregas/         el contenido de cada ciclo, listo para volcar al documento
  diagramas/        fuentes UML (VioletBoutique.eapx) y exportados
  casos-de-uso/     detalle por ciclo
  marco-teorico/    la Parte I del documento
```

**El código replica los paquetes de análisis, con el mismo nombre.** El
diagrama de paquetes del documento y el árbol de carpetas son la misma cosa: en
la defensa no hay que traducir entre uno y otro.

### Dónde mirar antes de escribir código

| Si vas a… | Leé primero |
|---|---|
| **incorporarte al desarrollo** | **[docs/07-estructura-repositorio.md](docs/07-estructura-repositorio.md) §7.3** — entorno, rama propia, qué tomar y con qué frecuencia subir |
| **armar el documento de entrega** | **[docs/00-indice-oficial.md](docs/00-indice-oficial.md)** — el índice que dio la ingeniera, qué sección sale de qué archivo y qué falta |
| **desarrollar un caso de uso del Ciclo 1** | **[docs/entregas/ciclo-1/](docs/entregas/ciclo-1/)** — las 9 tablas de detalle, el análisis y el diseño de datos |
| **desarrollar un caso de uso del Ciclo 2** | **[docs/entregas/ciclo-2/](docs/entregas/ciclo-2/)** — una ficha por caso de uso con el «por qué» de cada decisión, y los seis documentos del acuerdo del ciclo |
| **generar o tocar un diagrama UML** | **[GUIA-DIAGRAMAS-EA.md](GUIA-DIAGRAMAS-EA.md)** — el manual completo: los catorce tipos, las nueve reglas, el catálogo de errores y el anexo del 2do parcial con ICONIX. Leerlo **antes** de correr cualquier `scripts/ea-*.ps1`. El `.eapx` es binario: lo toca **una sola persona a la vez** |
| **trabajar sin conexión** (web o móvil) | `backend/app/modules/offline/` — el contrato de sincronización (CU-17) es el mismo para la web y el móvil, y el módulo explica la idempotencia y quién gana una unidad en disputa |
| **implementar CU-02 (login)** | **[docs/entregas/ciclo-1/guia-cu-02-iniciar-y-cerrar-sesion.md](docs/entregas/ciclo-1/guia-cu-02-iniciar-y-cerrar-sesion.md)** — qué falta en el código y cómo saber que está terminado |
| **montar tu entorno por primera vez** | **[docs/entorno/versiones.md](docs/entorno/versiones.md)** — qué instalar, en qué orden, con las versiones exactas |
| **levantar el backend** | **[backend/README.md](backend/README.md)** — de cero a `/health` respondiendo |
| **escribir código del backend** | **[backend/README.md](backend/README.md)** — las cuatro capas y las reglas que no se rompen |
| **escribir código del frontend web** | [frontend-web/README.md](frontend-web/README.md) — áreas por rol y configuración de la API |
| **tocar el vestidor virtual** | **[mobile/README.md](mobile/README.md)** — cómo funciona la superposición y qué necesita de las imágenes |
| entender qué construye cada ciclo | [docs/05-plan-y-cronograma.md](docs/05-plan-y-cronograma.md) |
| saber por qué se eligió cada tecnología | [docs/06-decisiones-tecnicas.md](docs/06-decisiones-tecnicas.md) |
| **desplegar en Railway** | [docs/06-decisiones-tecnicas.md](docs/06-decisiones-tecnicas.md) §6.9 — servicios, variables y las confusiones que cuestan una tarde |
| agregar un caso de uso o un paquete | [docs/03-captura-requisitos.md](docs/03-captura-requisitos.md) y [docs/04-analisis-arquitectura.md](docs/04-analisis-arquitectura.md) |
| entender el problema que se resuelve | [docs/01-perfil.md](docs/01-perfil.md) §1.3 — y, como contexto interno que no se entrega, [docs/02-modelo-negocio.md](docs/02-modelo-negocio.md) |
| trabajar con el repositorio | [docs/07-estructura-repositorio.md](docs/07-estructura-repositorio.md) — ramas, commits y etiquetas |
| **redactar el marco teórico** | **[docs/marco-teorico/00-indice-y-guia.md](docs/marco-teorico/00-indice-y-guia.md)** — el índice que exige el enunciado y qué responder en cada punto |

---

## Cómo contribuir

Nunca se hace *commit* directo sobre `main`: es la rama que Railway despliega.
Cada caso de uso va en **su propia rama** —`feat/cu21-inventario-offline`;
en el 1er parcial eran ramas por ciclo, como `MateoCiclo2`—
creada desde `main`, y todo entra por Pull Request hacia `main` con revisión del
otro. Un arreglo puntual que no es de un caso de uso va en su propia rama corta
—`fix/…`— y se mergea aparte.

Mensajes de commit en español, en imperativo, con la convención
`tipo(alcance): descripción`:

```
feat(inventario): registrar movimiento por ingreso de proveedor
fix(reservas): liberar stock al expirar una reserva no atendida
```

Detalle completo en
[docs/07-estructura-repositorio.md](docs/07-estructura-repositorio.md) §7.1.

## Equipo

| Rol | Integrante | Registro |
|---|---|---|
| Full stack | Mateo Hurtado Castro | 222008687 |
| Full stack | Karen Paola Ortega Mancilla | 222056592 |

**Los dos somos full stack, y no es una formalidad: es cómo se reparte el
trabajo.** Desde el Ciclo 2 el reparto es **por caso de uso completo** —quien lo
toma escribe su migración, su backend, su pantalla web y su pantalla móvil— y no
por capa. Así nadie espera a que el otro termine para poder seguir, y ninguna
parte del sistema tiene un solo dueño.

En la defensa cualquiera puede ser interrogado sobre cualquier parte.

## Licencia

MIT — ver [LICENSE](LICENSE).
