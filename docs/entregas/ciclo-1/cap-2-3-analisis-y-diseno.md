# CAP. 2 y CAP. 3 · CICLO #1 — Análisis y Diseño

Contenido listo para volcar al `.docx`, en el orden del índice oficial. Cubre las secciones de
`CAP. 2` y `CAP. 3` que dependen de los casos de uso del Ciclo 1.

Las secciones **2.1.1 a 2.1.3** van completas y su fuente es
[`docs/04-analisis-arquitectura.md`](../../04-analisis-arquitectura.md) §4.1.

Este documento aporta el **texto y la especificación** de cada artefacto. Los diagramas se
dibujan a partir de él y se guardan en `docs/diagramas/`.

---

## 2.2 Analizar Casos de Uso — CICLO #1

Cada caso de uso se realiza con clases de análisis de tres estereotipos: «boundary» (comunicación
con el actor), «control» (coordinación y reglas del caso de uso) y «entity» (información
persistente). Esta tabla es la especificación de los nueve **diagramas de comunicación** del
Ciclo 1: cada fila indica qué objetos aparecen en el diagrama y en qué orden se envían los
mensajes.

| CU | «boundary» | «control» | «entity» | Mensajes principales |
|---|---|---|---|---|
| **CU-01** Registrar cliente | `FormularioRegistro` | `GestorRegistro` | `Usuario`, `Rol`, `Cliente` | 1 enviarDatos → 2 validar → 3 verificarCorreoDisponible → 4 hashearContraseña → 5 crearUsuario → 6 crearCliente → 7 confirmar |
| **CU-02** Iniciar y cerrar sesión | `FormularioLogin` | `GestorAutenticacion` | `Usuario`, `Rol`, `SesionToken` | 1 enviarCredenciales → 2 buscarPorCorreo → 3 verificarActivo → 4 verificarHash → 5 emitirToken → 6 registrarSesion → 7 devolverToken |
| **CU-03** Gestionar usuarios y roles | `PantallaUsuarios` | `GestorUsuarios` | `Usuario`, `Rol`, `SesionToken` | 1 listar/crear/editar → 2 autorizarAdministrador → 3 validar → 4 verificarUnicidad → 5 persistir → 6 revocarSesiones (al desactivar) |
| **CU-04** Gestionar perfil del cliente | `PantallaPerfil` | `GestorPerfil` | `Cliente`, `Usuario`, `DireccionCliente` | 1 solicitarPerfil → 2 autorizarPropietario → 3 obtenerDatos → 4 modificar → 5 validar → 6 persistir |
| **CU-05** Gestionar ciudades y sucursales | `PantallaSucursales` | `GestorOrganizacion` | `Ciudad`, `Sucursal` | 1 listar/crear/editar → 2 autorizarAdministrador → 3 validar → 4 verificarNombreUnicoEnCiudad → 5 persistir |
| **CU-06** Gestionar empleados | `PantallaEmpleados` | `GestorEmpleados` | `Empleado`, `Usuario`, `Rol`, `Sucursal` | 1 crear → 2 autorizarAdministrador → 3 validar → 4 verificarSucursalActiva → 5 crearUsuario → 6 crearEmpleado → 7 confirmar (transacción única) |
| **CU-07** Gestionar proveedores | `PantallaProveedores` | `GestorProveedores` | `Proveedor`, `Usuario` | 1 listar/crear/editar → 2 autorizarAdministrador → 3 validar → 4 verificarIdentificacionUnica → 5 persistir |
| **CU-08** Gestionar categorías, tallas y colores | `PantallaMaestrosCatalogo` | `GestorTaxonomia` | `Categoria`, `Talla`, `Color` | 1 listar/crear/editar → 2 autorizarAdministrador → 3 validar → 4 verificarUnicidadEntreHermanas → 5 verificarSinCiclo → 6 persistir |
| **CU-09** Gestionar temporadas y colecciones | `PantallaTemporadas` | `GestorTemporadas` | `Temporada`, `Coleccion` | 1 listar/crear/editar → 2 autorizarAdministrador → 3 validar → 4 verificarRangoDeFechas → 5 advertirSolapamiento → 6 persistir |

**Dos observaciones sobre estos diagramas.**

La clase de control `GestorAutenticacion` aparece en los nueve, porque los ocho casos de uso
internos incluyen *Autenticar usuario*. Para no repetirla nueve veces, en los diagramas de CU-03
a CU-09 se representa como un único mensaje `autorizar()` dirigido a ella, y su detalle se ve una
sola vez en el diagrama de CU-02.

CU-06 es el único con **dos entidades creadas en la misma transacción** (`Usuario` y `Empleado`).
Su diagrama de comunicación es el más interesante del ciclo, porque muestra que la coordinación
vive en el control y no en las entidades.

---

## 2.3 Análisis de Clases — CICLO #1

Catorce clases de análisis, agrupadas por paquete. Los atributos se listan a nivel de análisis:
la definición de tipos y restricciones corresponde a 3.3.

### P1 · Seguridad y Usuarios

| Clase | Estereotipo | Responsabilidad | Atributos |
|---|---|---|---|
| `Usuario` | «entity» | Representa a cualquier persona que accede al sistema, con su credencial y su rol | correo, hash de contraseña, nombres, apellidos, estado, fecha de alta |
| `Rol` | «entity» | Define el conjunto de permisos de un tipo de usuario | nombre, descripción |
| `Permiso` | «entity» | Acción concreta que un rol puede ejecutar | código, descripción |
| `Cliente` | «entity» | Datos comerciales de un usuario con rol Cliente | documento, teléfono, tallas habituales, categorías preferidas |
| `SesionToken` | «entity» | Registro de una sesión emitida, para poder revocarla | identificador del token, fecha de emisión, fecha de expiración, fecha de revocación |

**Relaciones.** `Usuario` → `Rol` (muchos a uno). `Rol` ↔ `Permiso` (muchos a muchos).
`Cliente` → `Usuario` (uno a uno). `SesionToken` → `Usuario` (muchos a uno).

### P2 · Organización

| Clase | Estereotipo | Responsabilidad | Atributos |
|---|---|---|---|
| `Ciudad` | «entity» | Agrupa las sucursales de una misma plaza | nombre, departamento |
| `Sucursal` | «entity» | Tienda física; es el eje de partición del inventario, las reservas y las ventas | nombre, dirección, teléfono, horario, capacidad de vestidores, estado |
| `Empleado` | «entity» | Persona que trabaja en una sucursal, con su cargo | documento, teléfono, cargo, fecha de ingreso, fecha de baja |
| `Proveedor` | «entity» | Empresa que abastece prendas | razón social, identificación tributaria, contacto, teléfono, correo, dirección, estado |

**Relaciones.** `Sucursal` → `Ciudad` (muchos a uno). `Empleado` → `Sucursal` (muchos a uno).
`Empleado` → `Usuario` (uno a uno). `Proveedor` → `Usuario` (uno a uno, opcional).

### P3 · Catálogo (maestros)

| Clase | Estereotipo | Responsabilidad | Atributos |
|---|---|---|---|
| `Categoria` | «entity» | Clasificación jerárquica de las prendas | nombre, orden, estado |
| `Talla` | «entity» | Medida de una prenda; junto al color define la variante | código, tipo de prenda, orden |
| `Color` | «entity» | Color de una prenda; junto a la talla define la variante | nombre, valor hexadecimal |
| `Temporada` | «entity» | Ventana comercial a la que pertenecen los productos | nombre, descripción, fecha de inicio, fecha de fin, estado |
| `Coleccion` | «entity» | Conjunto de productos lanzado dentro de una temporada | nombre, descripción |

**Relaciones.** `Categoria` → `Categoria` (autorreferencia, categoría padre opcional).
`Coleccion` → `Temporada` (muchos a uno).

> **Nota de análisis.** `Talla` y `Color` no son atributos de texto del producto sino entidades
> propias, porque en el Ciclo 2 la variante (SKU) se define como producto × talla × color y
> necesita referenciarlas. Modelarlas como texto libre haría imposible filtrar el catálogo por
> talla, que es el RF07.

---

## 2.4 Análisis de Paquetes — CICLO #1

Tres de los once paquetes se construyen en este ciclo.

| Paquete | Clases que contiene | Casos de uso que realiza | Depende de |
|---|---|---|---|
| **P1 · Seguridad y Usuarios** | `Usuario`, `Rol`, `Permiso`, `Cliente`, `SesionToken` | CU-01, CU-02, CU-03, CU-04 | — (no depende de ninguno) |
| **P2 · Organización** | `Ciudad`, `Sucursal`, `Empleado`, `Proveedor` | CU-05, CU-06, CU-07 | P1 |
| **P3 · Catálogo (maestros)** | `Categoria`, `Talla`, `Color`, `Temporada`, `Coleccion` | CU-08, CU-09 | P1 |

**Regla de dependencias.** Las flechas van en un solo sentido: P2 → P1 y P3 → P1. P1 no conoce a
ninguno de los otros dos, y P2 y P3 no se conocen entre sí en este ciclo. Esto es lo que permite
que P1 sea el paquete más transversal del sistema —los ocho paquetes restantes lo usarán para
autorizar— sin acoplarse a nada.

**Por qué estos tres y no otros.** Son los paquetes sin los cuales ningún otro puede existir: sin
usuarios con rol no hay autorización, sin sucursal no hay dónde particionar el inventario, y sin
talla ni color no puede definirse una variante, que es la unidad real de venta. Los ocho paquetes
restantes dependen directa o indirectamente de estos tres.

---

## 3.1.1 Diseño lógico — CICLO #1

La arquitectura lógica del backend es de **cuatro capas**, y cada paquete de análisis se
implementa como un módulo que las repite completas:

| Capa | Archivo | Responsabilidad | Estereotipo de análisis que realiza |
|---|---|---|---|
| Router | `router.py` | Expone los endpoints REST, valida la entrada con esquemas y traduce errores a códigos HTTP | «boundary» |
| Service | `service.py` | Contiene las reglas del caso de uso, coordina repositorios y delimita la transacción | «control» |
| Repository | `repository.py` | Traduce entre objetos y base de datos; es el único que emite consultas | — |
| Model | `models.py` | Define las entidades persistentes | «entity» |

**Reglas que no se rompen.** El router nunca consulta la base de datos directamente; el service
nunca conoce HTTP; el repository nunca contiene reglas de negocio. La transacción se abre y se
cierra en el service, que es donde vive el caso de uso.

**Módulos del Ciclo 1.** `seguridad/` (P1), `organizacion/` (P2) y `catalogo/` (P3), cada uno con
sus cuatro archivos. El árbol de carpetas y el diagrama de paquetes son la misma cosa.

**Frontend web.** Angular organizado por *features* que corresponden a las áreas por rol:
`auth/` para CU-01 y CU-02, y `admin/` para CU-03, CU-05 a CU-09, con guardas de ruta que leen el
rol del token.

## 3.1.2 Diseño Físico — CICLO #1

Especificación del **diagrama de despliegue**: cuatro nodos y las vías de comunicación entre
ellos.

| Nodo | Artefacto desplegado | Tecnología | Comunicación |
|---|---|---|---|
| Dispositivo del cliente | Navegador con la aplicación Angular | Chrome / Edge | HTTPS hacia el nodo de aplicación |
| Dispositivo móvil | Aplicación Flutter instalada (APK) | Android | HTTPS hacia el nodo de aplicación |
| Nodo de aplicación | Contenedor con la API FastAPI | Linux · Python 3.13 · Uvicorn | Protocolo de PostgreSQL hacia el nodo de datos |
| Nodo de datos | Base de datos PostgreSQL gestionada | PostgreSQL 16 | — |

**Notas del despliegue del Ciclo 1.** La API expone `/health` para verificación externa; el
frontend web se sirve como artefacto estático desde el mismo proveedor; la aplicación móvil no se
despliega en tienda sino que se distribuye como APK. Todos los secretos —cadena de conexión,
clave de firma del token— se inyectan como variables de entorno, nunca versionados.

> **Pendiente de decisión.** El proveedor del nodo de datos y del nodo de aplicación está sin
> cerrar. El diagrama de despliegue debe nombrarlo, así que esta decisión bloquea 3.1.2.

---

## 3.2 Diagrama de Estado — CICLO #1

El único objeto con ciclo de vida propio en el Ciclo 1 es la sesión. `Reserva` y `Pedido`, que son
los ricos, pertenecen a los ciclos 2 y 3.

**Objeto:** `SesionToken`

| Estado | Significado |
|---|---|
| *(inicial)* | — |
| **Vigente** | El token fue emitido y es aceptado en cada petición |
| **Expirado** | Se cumplió la fecha de expiración sin renovación |
| **Revocado** | El usuario cerró sesión, o el Administrador desactivó la cuenta |
| *(final)* | — |

| Transición | Evento | Condición |
|---|---|---|
| inicial → Vigente | `emitir()` | Credenciales verificadas en CU-02 |
| Vigente → Vigente | `renovar()` | La renovación llega antes de la expiración |
| Vigente → Expirado | `vencerPlazo()` | Se alcanza la fecha de expiración |
| Vigente → Revocado | `cerrarSesion()` | El usuario cierra sesión (CU-02) |
| Vigente → Revocado | `desactivarUsuario()` | El Administrador desactiva la cuenta (CU-03) o da de baja al empleado (CU-06) |
| Expirado → final | `purgar()` | Limpieza periódica de sesiones vencidas |
| Revocado → final | `purgar()` | Ídem |

**Por qué importa.** Es lo que hace que desactivar un usuario tenga efecto inmediato: sin el
registro de sesiones, un token ya emitido seguiría siendo válido hasta vencer, y una cuenta
desactivada podría seguir operando.

## 3.2 Diagrama de Navegación — CICLO #1

Mapa de pantallas de la aplicación web, por rol. Es la especificación del diagrama de navegación
y, a la vez, la lista de prototipos de 1.4.

**Público (sin sesión)**

```
Inicio de sesión ──► Registro de cliente
       │                    │
       └────────────────────┴──► (según rol del token)
```

**Cliente**

```
Inicio ──► Mi perfil ──► Mis direcciones
                    └──► Cambiar contraseña
```

**Administrador**

```
Tablero
  ├─ Usuarios ─────────► Detalle / alta / edición de usuario
  ├─ Organización
  │    ├─ Ciudades ────► Alta / edición de ciudad
  │    ├─ Sucursales ──► Alta / edición de sucursal
  │    ├─ Empleados ───► Alta / edición de empleado
  │    └─ Proveedores ─► Alta / edición de proveedor
  └─ Catálogo (maestros)
       ├─ Categorías ──► Árbol y alta / edición
       ├─ Tallas ──────► Alta / edición
       ├─ Colores ─────► Alta / edición
       ├─ Temporadas ──► Alta / edición
       └─ Colecciones ─► Alta / edición
```

**Encargado de Sucursal y Cajero.** En el Ciclo 1 su navegación se reduce al inicio de sesión y a
una pantalla de bienvenida con el nombre de su sucursal: sus funciones propias llegan con las
reservas (Ciclo 2) y el punto de venta (Ciclo 3). Se incluye igual en el diagrama para mostrar que
la guarda por rol ya está operando.

**Regla de navegación.** Toda ruta distinta de inicio de sesión y registro exige token vigente; si
el token falta o expiró, la aplicación redirige a inicio de sesión conservando la ruta destino
para volver a ella después de autenticarse.

---

## 3.3.1 Diseño de datos lógico — CICLO #1

Modelo entidad-relación de las catorce clases de análisis. El diseño incorpora **dos elementos
que el análisis no tenía**, y conviene decirlo en el documento porque es exactamente lo que aporta
el flujo de Diseño:

- **`direccion_cliente`** — CU-04 permite al Cliente mantener *varias* direcciones de entrega.
  Una relación uno-a-muchos exige una entidad propia; como atributo de `Cliente` sería
  irrepresentable.
- **`rol_permiso`** — la relación muchos-a-muchos entre `Rol` y `Permiso` se resuelve con una
  tabla intermedia.

### Entidades y relaciones

| Entidad | Clave primaria | Claves foráneas | Restricciones de unicidad |
|---|---|---|---|
| `rol` | id | — | nombre |
| `permiso` | id | — | codigo |
| `rol_permiso` | (rol_id, permiso_id) | rol_id → rol · permiso_id → permiso | — |
| `usuario` | id | rol_id → rol | correo |
| `cliente` | id | usuario_id → usuario | usuario_id · documento |
| `direccion_cliente` | id | cliente_id → cliente · ciudad_id → ciudad | — |
| `sesion_token` | id | usuario_id → usuario | jti |
| `ciudad` | id | — | nombre |
| `sucursal` | id | ciudad_id → ciudad | (ciudad_id, nombre) |
| `empleado` | id | usuario_id → usuario · sucursal_id → sucursal | usuario_id · documento |
| `proveedor` | id | usuario_id → usuario (opcional) | identificacion_tributaria |
| `categoria` | id | categoria_padre_id → categoria | (categoria_padre_id, nombre) |
| `talla` | id | — | (tipo_prenda, codigo) |
| `color` | id | — | nombre |
| `temporada` | id | — | nombre |
| `coleccion` | id | temporada_id → temporada | (temporada_id, nombre) |

### Cardinalidades

```
rol      1 ──── N  usuario
rol      N ──── N  permiso            (vía rol_permiso)
usuario  1 ──── 1  cliente
usuario  1 ──── 1  empleado
usuario  1 ──── 0..1 proveedor
usuario  1 ──── N  sesion_token
cliente  1 ──── N  direccion_cliente
ciudad   1 ──── N  sucursal
ciudad   1 ──── N  direccion_cliente
sucursal 1 ──── N  empleado
categoria 1 ─── N  categoria          (jerarquía; padre opcional)
temporada 1 ─── N  coleccion
```

## 3.3.2 Diseño de datos físico — CICLO #1

Esquema PostgreSQL 16. Se implementa con migraciones versionadas; el orden de creación respeta las
dependencias de claves foráneas.

```sql
-- ============ P1 · Seguridad y Usuarios ============

CREATE TABLE rol (
    id          SMALLSERIAL PRIMARY KEY,
    nombre      VARCHAR(30)  NOT NULL UNIQUE,
    descripcion VARCHAR(150)
);

CREATE TABLE permiso (
    id          SMALLSERIAL PRIMARY KEY,
    codigo      VARCHAR(60)  NOT NULL UNIQUE,
    descripcion VARCHAR(150)
);

CREATE TABLE rol_permiso (
    rol_id     SMALLINT NOT NULL REFERENCES rol(id)     ON DELETE CASCADE,
    permiso_id SMALLINT NOT NULL REFERENCES permiso(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

CREATE TABLE usuario (
    id               BIGSERIAL PRIMARY KEY,
    correo           VARCHAR(120) NOT NULL UNIQUE,
    hash_contrasena  VARCHAR(255) NOT NULL,
    nombres          VARCHAR(80)  NOT NULL,
    apellidos        VARCHAR(80)  NOT NULL,
    rol_id           SMALLINT     NOT NULL REFERENCES rol(id),
    activo           BOOLEAN      NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    actualizado_en   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_usuario_rol ON usuario(rol_id);

CREATE TABLE cliente (
    id                 BIGSERIAL PRIMARY KEY,
    usuario_id         BIGINT      NOT NULL UNIQUE REFERENCES usuario(id) ON DELETE CASCADE,
    documento          VARCHAR(20) UNIQUE,
    telefono           VARCHAR(20),
    talla_superior     VARCHAR(10),
    talla_inferior     VARCHAR(10),
    talla_calzado      VARCHAR(10),
    creado_en          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sesion_token (
    id            BIGSERIAL PRIMARY KEY,
    usuario_id    BIGINT      NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    jti           UUID        NOT NULL UNIQUE,
    emitido_en    TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_en     TIMESTAMPTZ NOT NULL,
    revocado_en   TIMESTAMPTZ,
    CONSTRAINT ck_sesion_vigencia CHECK (expira_en > emitido_en)
);
CREATE INDEX idx_sesion_usuario_activa ON sesion_token(usuario_id) WHERE revocado_en IS NULL;

-- ============ P2 · Organización ============

CREATE TABLE ciudad (
    id           SERIAL PRIMARY KEY,
    nombre       VARCHAR(60) NOT NULL UNIQUE,
    departamento VARCHAR(60) NOT NULL
);

CREATE TABLE sucursal (
    id                     SERIAL PRIMARY KEY,
    ciudad_id              INTEGER      NOT NULL REFERENCES ciudad(id),
    nombre                 VARCHAR(80)  NOT NULL,
    direccion              VARCHAR(200) NOT NULL,
    telefono               VARCHAR(20),
    horario_apertura       TIME         NOT NULL,
    horario_cierre         TIME         NOT NULL,
    capacidad_vestidores   SMALLINT     NOT NULL DEFAULT 1,
    activa                 BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_sucursal_ciudad_nombre UNIQUE (ciudad_id, nombre),
    CONSTRAINT ck_sucursal_horario   CHECK (horario_cierre > horario_apertura),
    CONSTRAINT ck_sucursal_capacidad CHECK (capacidad_vestidores > 0)
);
CREATE INDEX idx_sucursal_ciudad ON sucursal(ciudad_id);

CREATE TABLE direccion_cliente (
    id             BIGSERIAL PRIMARY KEY,
    cliente_id     BIGINT       NOT NULL REFERENCES cliente(id) ON DELETE CASCADE,
    ciudad_id      INTEGER      NOT NULL REFERENCES ciudad(id),
    alias          VARCHAR(40)  NOT NULL,
    direccion      VARCHAR(200) NOT NULL,
    referencia     VARCHAR(200),
    predeterminada BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE UNIQUE INDEX uq_direccion_predeterminada
    ON direccion_cliente(cliente_id) WHERE predeterminada;

CREATE TABLE empleado (
    id            BIGSERIAL PRIMARY KEY,
    usuario_id    BIGINT      NOT NULL UNIQUE REFERENCES usuario(id),
    sucursal_id   INTEGER     NOT NULL REFERENCES sucursal(id),
    documento     VARCHAR(20) NOT NULL UNIQUE,
    telefono      VARCHAR(20),
    cargo         VARCHAR(30) NOT NULL,
    fecha_ingreso DATE        NOT NULL,
    fecha_baja    DATE,
    CONSTRAINT ck_empleado_cargo CHECK (cargo IN ('ENCARGADO', 'CAJERO')),
    CONSTRAINT ck_empleado_fechas CHECK (fecha_baja IS NULL OR fecha_baja >= fecha_ingreso)
);
CREATE INDEX idx_empleado_sucursal ON empleado(sucursal_id);

CREATE TABLE proveedor (
    id                        BIGSERIAL PRIMARY KEY,
    usuario_id                BIGINT       UNIQUE REFERENCES usuario(id),
    razon_social              VARCHAR(120) NOT NULL,
    identificacion_tributaria VARCHAR(30)  NOT NULL UNIQUE,
    contacto                  VARCHAR(80),
    telefono                  VARCHAR(20),
    correo                    VARCHAR(120),
    direccion                 VARCHAR(200),
    activo                    BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ============ P3 · Catálogo (maestros) ============

CREATE TABLE categoria (
    id                 SERIAL PRIMARY KEY,
    categoria_padre_id INTEGER REFERENCES categoria(id),
    nombre             VARCHAR(60) NOT NULL,
    orden              SMALLINT    NOT NULL DEFAULT 0,
    activa             BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_categoria_padre_nombre UNIQUE (categoria_padre_id, nombre),
    CONSTRAINT ck_categoria_no_autopadre CHECK (categoria_padre_id IS DISTINCT FROM id)
);
CREATE INDEX idx_categoria_padre ON categoria(categoria_padre_id);

CREATE TABLE talla (
    id          SERIAL PRIMARY KEY,
    tipo_prenda VARCHAR(30) NOT NULL,
    codigo      VARCHAR(10) NOT NULL,
    orden       SMALLINT    NOT NULL DEFAULT 0,
    activa      BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_talla_tipo_codigo UNIQUE (tipo_prenda, codigo)
);

CREATE TABLE color (
    id            SERIAL PRIMARY KEY,
    nombre        VARCHAR(40) NOT NULL UNIQUE,
    hexadecimal   CHAR(7)     NOT NULL,
    activo        BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_color_hex CHECK (hexadecimal ~ '^#[0-9A-Fa-f]{6}$')
);

CREATE TABLE temporada (
    id             SERIAL PRIMARY KEY,
    nombre         VARCHAR(60) NOT NULL UNIQUE,
    descripcion    VARCHAR(200),
    fecha_inicio   DATE        NOT NULL,
    fecha_fin      DATE        NOT NULL,
    activa         BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT ck_temporada_rango CHECK (fecha_fin > fecha_inicio)
);

CREATE TABLE coleccion (
    id           SERIAL PRIMARY KEY,
    temporada_id INTEGER     NOT NULL REFERENCES temporada(id),
    nombre       VARCHAR(60) NOT NULL,
    descripcion  VARCHAR(200),
    activa       BOOLEAN     NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_coleccion_temporada_nombre UNIQUE (temporada_id, nombre)
);
CREATE INDEX idx_coleccion_temporada ON coleccion(temporada_id);
```

### Decisiones del diseño físico

| Decisión | Motivo |
|---|---|
| Claves numéricas autoincrementales | Índices más compactos y uniones más baratas que con claves de texto |
| `TIMESTAMPTZ` en vez de `TIMESTAMP` | El sistema se despliega en la nube; sin zona horaria las fechas se vuelven ambiguas |
| Baja lógica (`activo`) en lugar de borrado | Un maestro referenciado por operaciones históricas no puede eliminarse sin romper la trazabilidad |
| Índice parcial en `sesion_token` | Solo interesan las sesiones no revocadas; el índice se mantiene pequeño aunque la tabla crezca |
| Índice único parcial en `direccion_cliente` | Garantiza a nivel de base de datos que cada cliente tenga a lo sumo una dirección predeterminada |
| `CHECK` sobre el color hexadecimal | Evita que un valor mal formado llegue a la interfaz y rompa la muestra de color |
| Unicidad compuesta en `sucursal`, `categoria`, `coleccion` y `talla` | Las reglas de unicidad de los casos de uso se aplican en la base, no solo en el servicio: son la última línea de defensa ante concurrencia |

> **Nota.** La restricción `ck_categoria_no_autopadre` impide que una categoría sea su propio
> padre, pero **no** detecta ciclos más largos (A → B → A). Esa validación vive en el servicio,
> tal como se describe en la excepción E2 de CU-08.
