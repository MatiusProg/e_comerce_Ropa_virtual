# Violet Boutique — API REST (FastAPI)

Backend de la plataforma. Sirve al mismo tiempo a la aplicación web (Angular) y
a la aplicación móvil (Flutter): **un solo contrato, ninguna regla de negocio
duplicada en el cliente** (RNF07, RNF08).

## Arranque local

Requisitos: **Python 3.13** y Docker (solo para la base de datos).

```bash
# 1. La base de datos
docker compose up -d                     # desde la raíz del repositorio

# 2. El entorno virtual
cd backend
py -3.13 -m venv .venv                   # Windows
python3.13 -m venv .venv                 # macOS / Linux
.venv\Scripts\activate                   # Windows
source .venv/bin/activate                # macOS / Linux

pip install -r requirements.txt

# 3. La configuración
cp .env.example .env                     # y completar los valores

# 4. El esquema y los datos de prueba
alembic upgrade head
python -m app.db.seed

# 5. A correr
uvicorn app.main:app --reload
```

### El dataset de demostración

`seed.py` deja el sistema **vacío**: los roles para entrar y el catálogo para
mirar. Para verlo **en uso** —con existencias, movimientos, clientes, favoritos
y reservas— hay un segundo seed:

```bash
python -m app.db.seed_operacion
```

Necesita `DEMO_PASSWORD` en el `.env` y tarda unos minutos. **Corre contra una
base local**: escribe miles de filas y se niega a arrancar si `DATABASE_URL`
apunta a Supabase o a Railway, que es la base desplegada. Los volúmenes se
ajustan en el diccionario `VOLUMEN`, al principio del archivo.

Con los valores de fábrica deja ~515 personas, ~2.400 existencias, ~5.600
movimientos repartidos en seis meses, ~2.100 favoritos y 300 reservas en los
cinco estados.

### Las dos taxonomías del catálogo

El árbol de categorías existe en dos versiones y **el seed elige la que la base
ya tiene**, no la que prefiere:

| Perfil | Árbol | Cuándo se usa |
|---|---|---|
| `PERFIL_PUBLICO` | Mujer / Hombre / Accesorios | base vacía (máquina recién clonada) |
| `PERFIL_PRENDA` | Prendas Superiores / Inferiores / Ropa Íntima… | la base ya tiene esas categorías (es el caso de Supabase) |

El motivo es que el seed reconoce las categorías **por nombre**: sembrar un árbol
sobre el otro no reemplaza nada, lo agrega al lado, y la vitrina termina
ofreciendo `Mujer > Blusas` y `Prendas Superiores > Blusas y Camisas` como si
fueran ramas distintas. La elección se hace mirando la base —`_perfil_de()`— y
no con una variable de entorno: una variable mal puesta en Railway siembra la
taxonomía equivocada en la base de todo el equipo, y deshacerlo es borrar
productos a mano.

Al agregar una categoría a Supabase hay que copiarla **letra por letra** al
perfil correspondiente. Si difiere en un acento o en una mayúscula, el seed no
la reconoce y crea una gemela.

### Cargar el dataset en Supabase y verlo en el despliegue

**El seed escribe en dos lugares a la vez**: las filas van a la base y las
imágenes —que se dibujan con Pillow, no están versionadas— van al disco de la
máquina que lo ejecuta. Correrlo desde una laptop apuntando a Supabase deja las
filas en Supabase y los archivos en la laptop: la API desplegada sirve `/media`
desde el volumen de Railway, así que **todas las fotos responderían 404**.

Y no se arregla repitiéndolo: el seed salta el producto cuyo código ya existe,
así que la segunda corrida ni siquiera llega a generar las imágenes. Habría que
borrar los productos primero.

Por eso **el seed se ejecuta dentro del contenedor de Railway**, donde
`MEDIA_ROOT` es el volumen persistente y `DATABASE_URL` es Supabase. `railway
run` **no** sirve: ejecuta el comando en tu máquina con las variables del
servicio inyectadas, que es exactamente el caso roto.

#### Se corre desde la Console del servicio

Railway da una terminal dentro del contenedor en la pestaña **Console** del
servicio. Es la forma correcta: no hay que tocar el comando de arranque, no hay
`healthcheck` que pueda fallar y no se puede dejar el servicio caído.

```sh
python -m app.db.seed             # catálogo: productos, variantes e imágenes
python -m app.db.seed_operacion   # personas, inventario, favoritos y reservas
```

> **Antes se documentaba aquí un cambio temporal del comando de arranque**, con
> el seed en segundo plano para que el `healthcheckTimeout` de 120 s no diera el
> despliegue por fallido. Funcionaba, pero arriesgaba dejar el servicio abajo si
> el comando quedaba mal escrito. La Console lo vuelve innecesario.

#### Requisitos

| | |
|---|---|
| Volumen montado en `/app/media` | **imprescindible antes de sembrar** |
| `MEDIA_ROOT=/app/media` y `MEDIA_URL` | para servir las imágenes |
| `ADMIN_PASSWORD` | lo pide `app.db.seed` |
| `DEMO_PASSWORD` y `SEMBRAR_EN_DESPLEGADA=1` | **solo** los pide `app.db.seed_operacion` |

`app.db.seed` **no necesita** las dos últimas: se puede sembrar el catálogo sin
definir ninguna credencial nueva.

`SEMBRAR_EN_DESPLEGADA=1` desarma a propósito la guarda que impide sembrar
contra una base desplegada. Sin ella, `seed_operacion` se niega a arrancar.

#### Verificación

```bash
API=https://ecomerceropavirtual-production.up.railway.app
curl -s "$API/api/v1/tienda/productos?pagina=1&tamano=1"                          # total > 0
curl -s -o /dev/null -w "%{http_code}\n" "$API/media/productos/1/principal.jpg"   # 200
```

Y en la salida del seed, la línea `taxonomia:` tiene que nombrar el perfil que
corresponde a esa base. Si dice el equivocado, **parar**: significa que no
reconoció las categorías y va a crear un árbol gemelo.

#### Estado del despliegue al 13/09/2026

El **catálogo ya está cargado**: 52 productos, 798 variantes y 111 imágenes —59
de ellas los PNG transparentes del vestidor, verificados con canal alfa real—.
Se sembró con el perfil *por tipo de prenda* y las 12 categorías que ya existían
quedaron intactas, sin gemelas.

El volumen `backend-volume` está montado en `/app/media` del servicio Backend,
región `us-east4-eqdc4a`, y las imágenes se sirven desde ahí.

**Falta `app.db.seed_operacion`** —las personas, el inventario, los favoritos y
las reservas—, que además necesita las dos variables de la tabla de arriba.

## Organización del código

`app/modules/` contiene **un subpaquete por cada paquete de análisis** de
[`docs/04-analisis-arquitectura.md`](../docs/04-analisis-arquitectura.md), con
el mismo nombre. El diagrama de paquetes del documento y el árbol de carpetas
son la misma cosa; no hay que traducir entre uno y otro en la defensa.

```
app/
├── main.py               Monta un router por paquete. Los ciclos 2 y 3 están
│                         comentados: se descomentan al implementarlos.
├── core/
│   ├── config.py         Toda la configuración, por variables de entorno
│   ├── security.py       Hash bcrypt y emisión/validación de JWT
│   └── dependencies.py   Sesión de BD, usuario actual, exigencia de rol
├── db/
│   ├── base.py           Base declarativa + convención de nombres
│   ├── session.py        Motor y sesión (una por petición)
│   ├── seed.py           Roles, ciudades y administrador (ciclo 1)
│   ├── seed_catalogo.py  Sucursales, maestros y ~60 productos (ciclo 2)
│   └── seed_operacion.py Personas, inventario, favoritos y reservas
├── modules/
│   ├── seguridad/          P1  · CU-01 a CU-04            · ciclo 1
│   ├── organizacion/       P2  · CU-05 a CU-07            · ciclo 1
│   ├── catalogo/           P3  · CU-08 a CU-12            · ciclos 1-3
│   ├── inventario/         P4  · CU-13 a CU-16            · ciclo 2
│   ├── catalogo_publico/   P5  · CU-17 a CU-20            · ciclos 2-3
│   ├── reservas/           P6  · CU-22 a CU-25            · ciclo 2
│   ├── ventas/             P7  · CU-26, 27, 29 a 32       · ciclo 3
│   ├── pagos/              P8  · CU-27, CU-28             · ciclo 3
│   ├── vestidor_virtual/   P9  · CU-21                    · ciclo 3
│   ├── ia/                 P10 · CU-33 a CU-35            · ciclo 3
│   └── reportes/           P11 · CU-36, CU-37             · ciclo 3
└── integrations/         Adaptadores de Stripe y de la API de IA
```

### Las cuatro capas — la regla que no se rompe

Dentro de cada módulo:

```
router.py       HTTP: valida la entrada, resuelve la autorización, delega
    ↓
service.py      Reglas de negocio y control de la transacción
    ↓
repository.py   Consultas. Nada más.
    ↓
models.py       SQLAlchemy
```

Ningún `router` toca `models` directamente, y ninguna regla de negocio vive en
un `router`. Esto no es formalismo: es lo que hace que los **diagramas de
secuencia** del flujo de Diseño se correspondan literalmente con el código, y
lo que permite que dos personas trabajen en paralelo sin pisarse.

## Migraciones (Alembic)

```bash
alembic revision --autogenerate -m "crear tablas de seguridad"
alembic upgrade head
alembic downgrade -1                     # deshacer la última
alembic history                          # ver el historial
```

> **La trampa más común:** si el modelo nuevo no está importado en
> `alembic/env.py`, Alembic no lo ve y genera una migración **vacía** sin
> avisar. Al agregar un módulo con tablas, descomentar su import ahí.

## Pruebas

```bash
pytest                                   # todas
pytest tests/test_health.py -v           # una
pytest --cov=app                         # con cobertura
```

## Reglas de negocio que no se negocian

Estas cuatro salen del análisis y sostienen la integridad del sistema. Están
justificadas en [`docs/04-analisis-arquitectura.md`](../docs/04-analisis-arquitectura.md) §4.2.1.

**1. La variante (SKU), no el producto, es la unidad de negocio.**
`Producto` describe la prenda; `VarianteProducto` es la combinación talla ×
color, y es la que tiene precio, existencia, reserva y venta. Inventario,
reservas y ventas referencian **variante**, nunca producto.

**2. Ninguna cantidad cambia sin generar un `MovimientoInventario`.**
Los movimientos son inmutables: una corrección es un movimiento nuevo de tipo
ajuste, jamás una edición. `Existencia` es el saldo de sus movimientos.

**3. La reserva no descuenta stock: lo traslada.**
`Existencia` lleva `cantidad_disponible` y `cantidad_reservada`. Reservar mueve
de disponible a reservado; vender descuenta de reservado (si vino de una
reserva) o de disponible; expirar devuelve a disponible. Toda la operación va
en **una transacción con `SELECT ... FOR UPDATE`** sobre la fila de existencia —
sin eso, dos clientes compran la misma última unidad.

**4. El estado del pago lo determina el webhook, nunca el navegador.**
La redirección de vuelta desde la pasarela solo sirve para mostrarle algo al
usuario. El pedido pasa a pagado al recibir el webhook **con la firma
verificada**, y ese procesamiento es **idempotente**: si la pasarela reenvía la
notificación, el inventario no se descuenta dos veces.
