# e) UML 2.5+

---

## 1. Qué es UML

**UML** (*Unified Modeling Language*, Lenguaje Unificado de Modelado) es un lenguaje **gráfico**
estandarizado para especificar, visualizar, construir y documentar los artefactos de un sistema
de software.

Tres precisiones que suelen confundirse:

- **UML no es una metodología.** No dice cómo desarrollar; dice cómo **representar**. El proceso
  lo aporta el PUDS.
- **UML no es un lenguaje de programación.** No se ejecuta. Aunque existen herramientas que
  generan código a partir de modelos, el propósito es comunicar.
- **UML no obliga a dibujar los catorce diagramas.** Se usan los que aportan información; dibujar
  un diagrama que nadie va a leer es trabajo perdido.

**Historia.** Nace de la unificación de los métodos de **Booch**, **OMT** (Rumbaugh) y
**OOSE/Objectory** (Jacobson) —los "tres amigos"— a mediados de los noventa. En 1997 el **OMG**
(*Object Management Group*) lo adopta como estándar, y desde entonces lo mantiene.

**UML 2.5**, publicado en 2015, es una revisión que **no agrega diagramas nuevos**: reorganiza y
simplifica la especificación, que se había vuelto difícil de leer. Reemplaza la separación entre
infraestructura y superestructura por un documento único, aclara la semántica y elimina
ambigüedades. Por eso, en la práctica, un modelo "UML 2.5+" se ve igual que uno de UML 2.x bien
hecho: lo que cambió es la especificación, no la notación.

## 2. Los catorce diagramas

UML 2.5 define catorce tipos de diagrama, en dos grandes familias.

```
                            Diagrama UML
                                 │
             ┌───────────────────┴────────────────────┐
             │                                        │
      ESTRUCTURALES (7)                     DE COMPORTAMIENTO (7)
      qué hay en el sistema                 qué hace el sistema
             │                                        │
   ┌─────────┼──────────┐              ┌──────────────┼──────────────┐
   │ Clases              │             │ Casos de uso                │
   │ Objetos             │             │ Actividad                   │
   │ Componentes         │             │ Estados (máquina de estados)│
   │ Despliegue          │             │                             │
   │ Paquetes            │             │   ── de INTERACCIÓN (4) ──  │
   │ Perfiles            │             │   Secuencia                 │
   │ Estructura compuesta│             │   Comunicación              │
   └─────────────────────┘             │   Tiempos                   │
                                       │   Visión general            │
                                       └─────────────────────────────┘
```

### 2.1 Diagramas estructurales

Describen la **estructura estática**: qué elementos existen y cómo se relacionan.

| Diagrama | Qué muestra |
|---|---|
| **Clases** | Clases del sistema, sus atributos, operaciones y relaciones (asociación, agregación, composición, herencia, dependencia) |
| **Objetos** | Una "fotografía" del sistema en un instante: instancias concretas con valores |
| **Componentes** | Las partes reemplazables del sistema y las interfaces que ofrecen y requieren |
| **Despliegue** | La topología física: nodos de hardware, artefactos desplegados y vías de comunicación |
| **Paquetes** | Agrupación lógica de elementos y las dependencias entre grupos |
| **Perfiles** | Extensiones de UML para un dominio específico, mediante estereotipos |
| **Estructura compuesta** | La estructura interna de una clase: sus partes, puertos y conectores |

### 2.2 Diagramas de comportamiento

Describen la **dinámica**: qué ocurre y en qué orden.

| Diagrama | Qué muestra |
|---|---|
| **Casos de uso** | Funcionalidad desde la perspectiva de los actores, y las relaciones `include`, `extend` y generalización |
| **Actividad** | Flujo de trabajo paso a paso, con decisiones, bifurcaciones y concurrencia |
| **Estados** | Los estados por los que pasa un objeto y qué eventos provocan cada transición |
| **Secuencia** | Interacción entre objetos **ordenada en el tiempo**, con líneas de vida y mensajes |
| **Comunicación** | La misma interacción, pero destacando **quién habla con quién**; los mensajes van numerados |
| **Tiempos** | Cambios de estado en relación con el tiempo; se usa en sistemas de tiempo real |
| **Visión general de interacción** | Un diagrama de actividad cuyos nodos son otras interacciones |

**Secuencia frente a comunicación** — son la misma información con distinto énfasis: el de
secuencia resalta el **orden temporal** (el tiempo baja por el eje vertical); el de comunicación
resalta la **topología de las relaciones**. El PUDS usa comunicación en Análisis, donde importa
quién colabora con quién, y secuencia en Diseño, donde importa el orden exacto de las llamadas.

## 3. Elementos de los diagramas que usa este proyecto

### 3.1 Casos de uso

- **Actor** — monigote. Un rol externo, no una persona concreta. Puede ser un sistema.
- **Caso de uso** — elipse. Una funcionalidad completa con valor para el actor.
- **Asociación** — línea entre actor y caso de uso.
- **`«include»`** — flecha discontinua. El caso base **siempre** ejecuta al incluido. Sirve para
  factorizar comportamiento repetido (por ejemplo, *Verificar disponibilidad*).
- **`«extend»`** — flecha discontinua en sentido inverso. El caso extendido se ejecuta **solo bajo
  cierta condición**.
- **Generalización** — un actor o caso de uso especializa a otro.
- **Límite del sistema** — el rectángulo que separa lo interno de los actores.

> Confusión frecuente: `include` apunta **del caso base al incluido**; `extend` apunta **del
> extendido al base**. Las flechas van en sentidos opuestos y es un error común en la defensa.

### 3.2 Clases

- **Clase** — rectángulo de tres compartimentos: nombre, atributos, operaciones.
- **Visibilidad** — `+` público, `-` privado, `#` protegido, `~` de paquete.
- **Multiplicidad** — `1`, `0..1`, `1..*`, `*` en los extremos de la asociación.
- **Relaciones:**
  - **Asociación** — línea simple; una clase conoce a otra.
  - **Agregación** — rombo vacío; "tiene un", con vida independiente.
  - **Composición** — rombo relleno; "es parte de", y si se elimina el todo se elimina la parte.
  - **Herencia** — triángulo vacío; "es un".
  - **Dependencia** — flecha discontinua; uso puntual.

> En este proyecto: `Reserva` ◆— `DetalleReserva` es **composición** (un detalle no existe sin su
> reserva); `Producto` ◇— `Proveedor` es **asociación** (el proveedor existe por su cuenta).

### 3.3 Secuencia

Línea de vida, barra de activación, mensaje síncrono (flecha rellena), mensaje de retorno (flecha
discontinua), mensaje asíncrono (flecha abierta), y **fragmentos combinados**: `alt`
(alternativa), `opt` (opcional), `loop` (repetición), `par` (paralelo).

### 3.4 Despliegue

- **Nodo** — cubo tridimensional: un dispositivo o un entorno de ejecución.
- **Artefacto** — el elemento físico desplegado (un contenedor, un ejecutable, un APK).
- **Vía de comunicación** — línea entre nodos, etiquetada con el protocolo (`HTTPS`, `TLS`).

## 4. Relación entre UML y los flujos del PUDS

| Flujo de trabajo | Diagramas UML | Pregunta que responden |
|---|---|---|
| **Modelado del negocio** | Actividad · Casos de uso del negocio | ¿Cómo trabaja hoy la organización? |
| **Requisitos** | **Casos de uso** | ¿Qué debe hacer el sistema, y para quién? |
| **Análisis** | **Comunicación** · Clases de análisis · **Paquetes** | ¿Qué objetos colaboran para lograrlo? |
| **Diseño** | **Secuencia** · **Clases de diseño** · **Despliegue** · Paquetes · Estados | ¿Cómo lo hacen, técnicamente? |
| **Implementación** | Componentes | ¿En qué partes se materializa? |
| **Pruebas** | Actividad (escenarios) | ¿Cómo se verifica? |

## 5. Los diagramas que se elaboran en Violet Boutique

| # | Diagrama | Dónde | Ciclo |
|---|---|---|---|
| 1 | **Casos de uso** general y por paquete | Requisitos | 1, 2 y 3 |
| 2 | **Paquetes** (vista de análisis) | Análisis | 1 |
| 3 | **Comunicación** por caso de uso | Análisis | 1, 2 y 3 |
| 4 | **Clases de análisis** («boundary», «control», «entity») | Análisis | 1 |
| 5 | **Secuencia** por caso de uso | Diseño | 1, 2 y 3 |
| 6 | **Clases de diseño** | Diseño | 1, 2 y 3 |
| 7 | **Despliegue** (nodos en Railway, app móvil, servicios externos) | Diseño | 1 |
| 8 | **Estados** de `Reserva` y de `Venta` | Diseño | 2 y 3 |
| 9 | **Entidad-relación** (modelo físico de datos) | Diseño de datos | 1, 2 y 3 |

**Sobre el diagrama entidad-relación:** estrictamente **no es UML** —es notación de modelado de
datos, de Chen o de pata de gallo—. Se incluye porque el PUDS lo contempla dentro del diseño de
datos y porque es lo que se traduce a las tablas de PostgreSQL. Va acompañado del **diagrama de
clases de diseño**, que sí es UML y representa el mismo dominio en términos de objetos.

**El diagrama de estados merece atención especial en este proyecto.** `Reserva` tiene un ciclo de
vida con transiciones que son reglas de negocio duras, y cada una mueve inventario:

```
                    crear
    ○ ──────────────────────────────► [PENDIENTE]
                                          │
              ┌───────────────────────────┼──────────────────────────┐
              │ preparar                  │ cancelar        vencer   │
              ▼                           ▼                          ▼
        [PREPARADA]                  [CANCELADA] ●             [EXPIRADA] ●
              │
              │ confirmar llegada
              ▼
        [ATENDIDA]
              │
              │ el cliente compra          │ el cliente no compra
              ▼                            ▼
        [CONVERTIDA] ●               [CERRADA] ●
```

Cada transición hacia un estado final —cancelada, expirada, cerrada— **devuelve el stock
reservado a disponible**; la transición a *convertida* lo descuenta definitivamente. Modelar esto
como máquina de estados antes de programarlo evita el error más caro del sistema: perder o
duplicar existencias en una transición no contemplada.

## 6. Herramientas

| Herramienta | Notas |
|---|---|
| **draw.io / diagrams.net** | Gratuita, con plantillas UML. Guarda en `.drawio`, versionable en Git |
| **PlantUML** | Diagramas escritos como **texto** y renderizados a imagen. Ideal para versionar: el diff de un cambio se lee |
| **StarUML** | Escritorio, orientado a UML, con generación de código |
| **Enterprise Architect** | Profesional y completa; licencia paga |
| **Visual Paradigm** | Edición comunitaria gratuita para uso no comercial |

**Decisión del proyecto.** Los diagramas se elaboran en **draw.io** y se versionan en
`docs/diagramas/` junto con su exportación a PNG, de modo que el documento use la imagen y el
repositorio conserve la fuente editable. Para los diagramas que cambian seguido conviene
**PlantUML**, porque un cambio se ve en el `git diff` y no obliga a comparar dos imágenes.

---

## Bibliografía de esta sección

- Object Management Group (2015). *OMG Unified Modeling Language (OMG UML), Version 2.5*.
  <https://www.omg.org/spec/UML/2.5/>
- Booch, G., Rumbaugh, J. y Jacobson, I. (2006). *El Lenguaje Unificado de Modelado* (2.ª ed.).
  Addison-Wesley.
- Fowler, M. (2003). *UML Distilled: A Brief Guide to the Standard Object Modeling Language*
  (3.ª ed.). Addison-Wesley.
- Larman, C. (2004). *UML y Patrones: una introducción al análisis y diseño orientado a objetos y
  al proceso unificado* (2.ª ed.). Prentice Hall.
- Sitio de UML del OMG. <https://www.uml.org/>
