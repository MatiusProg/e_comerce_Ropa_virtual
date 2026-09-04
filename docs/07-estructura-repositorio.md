# 7) ESTRUCTURA DEL PROYECTO Y REPOSITORIO

## 7.1 Repositorio

| Dato | Valor |
|---|---|
| Repositorio | <https://github.com/MatiusProg/e_comerce_Ropa_virtual> |
| Estructura | Monorepo: backend, frontend web, app móvil y documentación juntos |
| Rama estable | `main` — siempre desplegable; es la que se entrega y la que se despliega |
| Ramas de trabajo | Una por integrante y por ciclo: `<Nombre>Ciclo<N>` — `MateoCiclo1`, `KarenCiclo1` |
| Rama `develop` | En desuso desde el 03/09/2026; se conserva por historial |

### Convenciones de trabajo

**Ramas — decisión del 03/09/2026.** Se abandona el esquema `feature/*` → `develop` → `main` y se
adopta **una rama por integrante y por ciclo**, con el formato `<Nombre>Ciclo<N>`:

```
main
 ├── MateoCiclo1
 └── KarenCiclo1
```

Cada rama **se crea desde `main`** y vuelve a `main` por Pull Request. `develop` queda sin uso; se
conserva solo por historial. Al empezar el Ciclo 2 se abren `MateoCiclo2` y `KarenCiclo2` desde
`main`, y así sucesivamente.

**Por qué se cambió.** Somos dos y trabajamos sobre partes distintas del monorepo —backend y
documentación por un lado, frontend y diagramas por el otro—. Con `feature/*` + `develop` cada
cambio pasaba por dos integraciones antes de llegar a la rama que se entrega; con una rama por
persona y ciclo, cada uno tiene un espacio propio, estable durante todo el ciclo, y `main` refleja
en todo momento lo que hay entregado.

**Sigue en pie:** nunca se hace *commit* directo sobre `main`. La rama `main` es la que se
despliega: si se rompe, el sistema desplegado se rompe.

**Antes de empezar el día:** `git checkout main && git pull` y luego `git merge main` sobre tu
rama, para no acumular divergencia.

**Mensajes de commit.** Convención `tipo(alcance): descripción`, en español y en imperativo:

```
feat(inventario): registrar movimiento por ingreso de proveedor
fix(reservas): liberar stock al expirar una reserva no atendida
docs(analisis): agregar diagrama de comunicacion de CU-22
```

Tipos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.

**Etiquetas.** Una por entrega, para poder mostrar el estado exacto de cada presentación:
`v0.1-ciclo1` (05/09) · `v0.2-ciclo2` (13/09) · `v1.0-final` (20/09).

**Frecuencia.** *Commits* diarios. Nadie retiene trabajo sin subir más de un día — es la
mitigación del riesgo R8 (indisponibilidad de un integrante en un grupo de dos).

## 7.2 Estructura del monorepo

```
PRIMER_PARCIAL/                        raíz del repositorio
│
├── README.md                          Punto de entrada del proyecto
├── .gitignore                         Python · Node/Angular · Flutter · secretos
├── docker-compose.yml                 PostgreSQL local para desarrollo
│
├── docs/                              DOCUMENTACIÓN PUDS
│   ├── 01-perfil.md
│   ├── 00-indice-oficial.md
│   ├── 02-modelo-negocio.md          (contexto interno; no se entrega)
│   ├── 03-captura-requisitos.md
│   ├── 04-analisis-arquitectura.md
│   ├── 05-plan-y-cronograma.md
│   ├── 06-decisiones-tecnicas.md
│   ├── 07-estructura-repositorio.md
│   ├── marco-teorico/                 Parte I: e-commerce, pasarelas, deliverys, PUDS, UML
│   ├── casos-de-uso/                  Detalle de CU por ciclo
│   ├── diagramas/                     Fuentes editables (.drawio, .puml) y PNG exportados
│   │   ├── casos-de-uso/  comunicacion/  secuencia/
│   │   ├── clases/        paquetes/      despliegue/
│   │   └── entidad-relacion/
│   ├── prototipos/                    Mockups de interfaz web y móvil
│   ├── pruebas/                       Casos de prueba y evidencias
│   └── entregas/                      Documento Word/PDF de cada presentación
│
├── backend/                           API REST — FastAPI + PostgreSQL
│   ├── app/
│   │   ├── main.py                    Monta un router por paquete, por ciclo
│   │   ├── core/                      config · security · dependencies
│   │   ├── db/                        base · session · seed
│   │   ├── modules/                   UN SUBPAQUETE POR PAQUETE DE ANÁLISIS
│   │   │   ├── seguridad/             P1  · CU-01 a CU-04        · ciclo 1
│   │   │   ├── organizacion/          P2  · CU-05 a CU-07        · ciclo 1
│   │   │   ├── catalogo/              P3  · CU-08 a CU-12        · ciclos 1-3
│   │   │   ├── inventario/            P4  · CU-13 a CU-16        · ciclo 2
│   │   │   ├── catalogo_publico/      P5  · CU-17 a CU-20        · ciclos 2-3
│   │   │   ├── reservas/              P6  · CU-22 a CU-25        · ciclo 2
│   │   │   ├── ventas/                P7  · CU-26,27,29-32       · ciclo 3
│   │   │   ├── pagos/                 P8  · CU-27, CU-28         · ciclo 3
│   │   │   ├── vestidor_virtual/      P9  · CU-21                · ciclo 3
│   │   │   ├── ia/                    P10 · CU-33 a CU-35        · ciclo 3
│   │   │   └── reportes/              P11 · CU-36, CU-37         · ciclo 3
│   │   │        cada módulo: router · service · repository · models · schemas
│   │   └── integrations/              Adaptadores de Stripe y de la API de IA
│   ├── alembic/                       Migraciones versionadas
│   ├── tests/                         pytest
│   ├── requirements.txt · Dockerfile · railway.json · .env.example
│
├── frontend-web/                      Aplicación web — Angular 22
│   ├── src/app/
│   │   ├── core/                      Interceptor JWT, guardas por rol, servicios de API
│   │   ├── shared/                    Componentes y utilidades comunes
│   │   └── features/
│   │       ├── auth/         Registro e inicio de sesión           · ciclo 1
│   │       ├── admin/        Organización, catálogo, inventario    · ciclos 1-3
│   │       ├── tienda/       Catálogo, ficha, carrito, pedidos     · ciclos 2-3
│   │       ├── sucursal/     Reservas e inventario (Encargado)     · ciclo 2
│   │       ├── caja/         Punto de venta (Cajero)               · ciclo 3
│   │       ├── reportes/     Tablero de KPIs y exportación         · ciclo 3
│   │       └── asistente/    Chat con IA y comando de voz          · ciclo 3
│   ├── src/environments/              URL de la API por entorno
│   └── Dockerfile · nginx.conf · railway.json
│
├── mobile/                            Aplicación móvil — Flutter
│   ├── lib/
│   │   ├── core/                      Cliente HTTP (Dio), tema, enrutado
│   │   ├── data/                      Modelos del contrato y repositorios
│   │   └── features/
│   │       ├── auth/               · ciclo 1
│   │       ├── catalogo/           · ciclos 2-3
│   │       ├── reservas/           · ciclo 2
│   │       ├── vestidor_virtual/   P9 · cámara + pose + superposición · ciclo 3
│   │       ├── compra/             · ciclo 3
│   │       └── asistente/          · ciclo 3
│   └── pubspec.yaml
│
└── scripts/                           Utilidades de desarrollo y despliegue
```

### El principio que ordena todo

**El código replica los paquetes de análisis.** `backend/app/modules/` contiene exactamente un
subpaquete por cada paquete identificado en §4.1.1, con el mismo nombre. Tres consecuencias
buscadas:

1. El **diagrama de paquetes** del flujo de Diseño se corresponde literalmente con el árbol de
   carpetas. En la defensa no hay que explicar una traducción entre el documento y el código.
2. La **división del trabajo** entre los dos integrantes se hace por paquete, lo que minimiza los
   conflictos de fusión en Git.
3. La **trazabilidad** caso de uso → paquete → carpeta → endpoint es directa y verificable.

Lo mismo vale para las cuatro capas dentro de cada módulo (`router → service → repository →
models`): son las mismas que aparecen en los diagramas de secuencia.

## 7.3 Arranque de un integrante

Pasos para incorporarse al desarrollo. Están escritos en orden y **el orden importa**: cada paso
supone el anterior.

### 1. Bajar el proyecto y leer

```bash
git clone https://github.com/MatiusProg/e_comerce_Ropa_virtual.git
cd e_comerce_Ropa_virtual
```

Tres documentos, en este orden:

1. [`README.md`](../README.md) — qué es el proyecto y cómo está organizado.
2. [`docs/00-indice-oficial.md`](00-indice-oficial.md) — el índice de la ingeniera, qué va
   completo, qué va por ciclo y qué falta.
3. [`docs/05-plan-y-cronograma.md`](05-plan-y-cronograma.md) §5.3 — las tareas del Ciclo 1 con
   responsable y estado.

### 2. Instalar el entorno

Las versiones exactas y el orden de instalación están en
[`docs/entorno/versiones.md`](entorno/versiones.md). Para el Ciclo 1 hace falta:

| Herramienta | Versión | Necesaria en el Ciclo 1 |
|---|---|---|
| Python | 3.13.15 — **no 3.14** | Sí, para el backend |
| Node.js y npm | 24.19.0 / 11.17.0 | Sí, para Angular |
| Docker Desktop + PostgreSQL | imagen `postgres:16-alpine` | Sí, base de datos local |
| Git | 2.55.0 | Sí |
| **Flutter** | 3.47.2 | **Aplazado** |
| **Android Studio** | 2026.1.4.7 | **Aplazado** |

> **Sobre Flutter y Android Studio.** Son los dos más pesados del conjunto —Android Studio con el
> SDK y un emulador pide mucha RAM y bastante disco— y **la aplicación móvil no se toca en el
> Ciclo 1**: los nueve casos de uso son de seguridad, organización y maestros del catálogo, y se
> demuestran desde la web. Por eso su instalación se aplaza.
>
> **Verificá esta decisión con tu propio Claude antes de aplicarla**, contándole las
> características reales de tu equipo (RAM, disco libre, procesador). Si tu máquina los aguanta
> sin problema, instalalos igual y te ahorrás el trabajo en el Ciclo 3; si no, aplazalos y
> seguí con el resto. Lo que **no** conviene es instalarlos a ciegas y quedarte sin espacio a
> mitad del ciclo.

Al terminar, verificá el entorno con la sección *Verificación del entorno* de
`docs/entorno/versiones.md`. Si aplazaste Flutter, `flutter doctor` no aplica todavía.

### 3. Crear tu rama

```bash
git checkout main
git pull
git checkout -b KarenCiclo1
git push -u origin KarenCiclo1
```

### 4. Tomar un caso de uso pendiente

Los casos de uso del Ciclo 1 son **CU-01 a CU-09**, y su detalle completo —flujo principal,
alternativos, excepciones— está en
[`docs/entregas/ciclo-1/cap-1-captura-requisitos.md`](entregas/ciclo-1/cap-1-captura-requisitos.md).
El diseño de datos y la arquitectura por capas están en
[`cap-2-3-analisis-y-diseno.md`](entregas/ciclo-1/cap-2-3-analisis-y-diseno.md).

**Antes de empezar, avisá cuál tomás**, para no trabajar los dos sobre lo mismo. El reparto
previsto está en `05-plan-y-cronograma.md` §5.3 y §5.7: el backend y la base de datos son de
Mateo; el frontend web, los diagramas UML y los prototipos son de Karen. Dentro de eso, elegí y
avisá.

### 5. Commitear y pushear a medida que avanzás

No se retiene trabajo sin subir. La regla es **al menos un push por día de trabajo**, y mejor uno
por cada pieza que quede funcionando. Mensajes con la convención `tipo(alcance): descripción` de
§7.1.

```bash
git add -A
git commit -m "feat(seguridad): pantalla de inicio de sesion con guarda por rol"
git push
```

Cuando algo esté terminado y probado, Pull Request de tu rama hacia `main`.

**Por qué esta frecuencia.** Es la mitigación del riesgo R8 —somos dos, y si uno no puede
trabajar un día el otro tiene que poder continuar desde lo último subido—. Y es lo que nos permite
avanzar en paralelo: mientras uno desarrolla los casos de uso, el otro modela los diagramas sobre
lo que ya está en `main`.

## 7.4 Estado actual

| Elemento | Estado |
|---|---|
| Enunciado analizado (`Examen1-Ecommerce-Si2-s2-26.pdf`) | ✔ |
| Documento de referencia de SI1 revisado | ✔ |
| Perfil, captura de requisitos y análisis de arquitectura | ✔ |
| Índice oficial de la ingeniera mapeado (`docs/00-indice-oficial.md`) | ✔ |
| Plan, cronograma en 3 ciclos y decisiones técnicas | ✔ |
| Repositorio Git conectado a GitHub | ✔ |
| Estructura del monorepo | ✔ |
| Esqueleto del backend (core, db, 11 módulos, Alembic, Docker, Railway) | ✔ |
| Proyecto Angular 22 generado con la estructura de áreas | ✔ |
| Esqueleto de la app Flutter (`pubspec.yaml` + `lib/`) | ✔ parcial — falta `flutter create` |
| Modelos, migraciones y endpoints del Ciclo 1 | ✖ pendiente |
| Servicios de Railway creados y desplegados | ✖ pendiente |
| Guía e índice del marco teórico (`docs/marco-teorico/00-indice-y-guia.md`) | ✔ |
| Marco teórico redactado (Parte I del enunciado) | ✖ pendiente — Karen (a–c) y Mateo (d–e) |
| Diagramas UML | ✖ pendientes |
| Detalle de los 9 casos de uso del Ciclo 1 | ✖ pendiente |
| Prototipos de interfaz | ✖ pendientes |
