# 7) ESTRUCTURA DEL PROYECTO Y REPOSITORIO

## 7.1 Repositorio

| Dato | Valor |
|---|---|
| Repositorio | <https://github.com/MatiusProg/e_comerce_Ropa_virtual> |
| Estructura | Monorepo: backend, frontend web, app móvil y documentación juntos |
| Rama estable | `main` — siempre desplegable |
| Rama de integración | `develop` |
| Ramas de trabajo | `feature/<paquete>-<descripcion>` · `fix/<descripcion>` |

### Convenciones de trabajo

**Ramas.** Nunca se hace *commit* directo sobre `main`. Todo entra por Pull Request desde
`feature/*` hacia `develop`, y `develop` se integra a `main` al cerrar cada ciclo. La rama `main`
es la que Railway despliega: si se rompe, el sistema desplegado se rompe.

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
│   ├── 02-modelo-negocio.md
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

## 7.3 Estado actual

| Elemento | Estado |
|---|---|
| Enunciado analizado (`Examen1-Ecommerce-Si2-s2-26.pdf`) | ✔ |
| Documento de referencia de SI1 revisado | ✔ |
| Perfil, modelo de negocio, captura de requisitos, análisis de arquitectura | ✔ |
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
