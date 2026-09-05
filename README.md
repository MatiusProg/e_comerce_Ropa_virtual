# Violet Boutique

Plataforma inteligente de comercio electrónico para una cadena de tiendas de
ropa, con **vestidores virtuales vía realidad aumentada**, reservas para prueba
en sucursal, inventario multisucursal, punto de venta e inteligencia artificial.

Proyecto académico — Examen 1, Sistemas de Información II, S2-2026.
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

## Tecnologías

| Capa | Herramienta | Versión |
|---|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic | FastAPI **0.141** · SQLAlchemy **2.0** |
| Lenguaje del backend | Python | **3.13** — ver la advertencia de abajo |
| Base de datos | PostgreSQL | **16** |
| Controlador de base de datos | psycopg | **3.3** (no psycopg2) |
| Frontend web | Angular + Angular Material | Angular **22** |
| Móvil | Flutter / Dart | Flutter **3.x** |
| Realidad aumentada | `camera` + ML Kit Pose Detection | procesamiento en el dispositivo |
| Inteligencia artificial | API de Claude (`anthropic`) | `claude-opus-5` |
| Pasarela de pago | Stripe | **modo de pruebas** |
| Base de datos gestionada | Supabase | PostgreSQL 16, por *session pooler* |
| Hospedaje | Railway | API y web, en un solo proyecto |
| Metodología | PUDS + UML 2.5+ | 3 ciclos |

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

Requisitos: Docker, **Python 3.13**, Node 20+, Flutter (solo para la app móvil).

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
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

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
cd backend && pytest
```

Documentación interactiva de la API: <http://localhost:8000/docs>

---

## Las cuatro reglas que sostienen el sistema

Salen del flujo de Análisis y están justificadas en
[docs/04-analisis-arquitectura.md](docs/04-analisis-arquitectura.md) §4.2.1.
Romper cualquiera de ellas produce datos incorrectos **sin generar ningún
error visible**.

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

---

## Los tres ciclos

Uno por cada presentación obligatoria. El Ciclo 1 es deliberadamente el más
corto: son cuatro días y su contenido es CRUD y autenticación.

| Ciclo | Entrega | Días | CU | Contenido |
|---|---|:---:|:---:|---|
| **1 · Fundamentos** | 05/09 | 4 | 9 | Seguridad y roles · Ciudades, sucursales, empleados, proveedores · Maestros del catálogo (categorías, tallas, colores, temporadas, colecciones) |
| **2 · Núcleo del negocio** | 13/09 | 8 | 13 | Productos y **variantes** · **Inventario multisucursal** con movimientos trazables · Catálogo público y disponibilidad · **Reservas** para prueba en sucursal |
| **3 · Comercio e inteligencia** | 20/09 | 7 | 15 | **Vestidor virtual (RA)** · Carrito y **pago en línea** · **Punto de venta** · **IA**: recomendador, asistente y reportes por voz · Tablero de KPIs |

Defensa: **martes 22/09**. Cada ciclo cierra con software **desplegado en la
nube**, no con código sin desplegar.

---

## Estructura

```
backend/
  app/core/         config, seguridad (JWT + bcrypt), dependencias de autorización
  app/db/           base declarativa, sesión, seed
  app/modules/      UN SUBPAQUETE POR PAQUETE DE ANÁLISIS
                    seguridad · organizacion · catalogo · inventario ·
                    catalogo_publico · reservas · ventas · pagos ·
                    vestidor_virtual · ia · reportes
  app/integrations/ adaptadores de Stripe y de la API de IA
  alembic/          migraciones versionadas
  tests/            pytest
frontend-web/
  src/app/core/     interceptor JWT, guardas por rol, servicios de API
  src/app/shared/   componentes reutilizables
  src/app/features/ auth · admin · tienda · sucursal · caja · reportes · asistente
mobile/
  lib/core/         cliente HTTP (Dio), tema, enrutado
  lib/data/         modelos del contrato y repositorios
  lib/features/     auth · catalogo · reservas · vestidor_virtual · compra · asistente
docs/
  00                índice oficial de la ingeniera y mapeo del entregable
  01 a 07           documentación PUDS
  entregas/         el contenido de cada ciclo, listo para volcar al documento
  diagramas/        fuentes UML y exportados
  casos-de-uso/     detalle por ciclo
  entregas/         el documento de cada presentación
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
Cada integrante trabaja en **una rama por ciclo** —`MateoCiclo1`, `KarenCiclo1`—
creada desde `main`, y todo entra por Pull Request hacia `main` con revisión del
otro.

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
| Backend · Base de datos · IA · Despliegue | Mateo Hurtado Castro | 222008687 |
| Frontend web · App móvil · Realidad aumentada | Karen Paola Ortega Mancilla | 222056592 |

Ninguno de los dos es el único que entiende un módulo: al cierre de cada ciclo,
cada integrante le explica al otro lo que implementó. En la defensa cualquiera
puede ser interrogado sobre cualquier parte del sistema.

## Licencia

MIT — ver [LICENSE](LICENSE).
