# d) PUDS — Proceso Unificado de Desarrollo de Software

---

## 1. Qué es y de dónde viene

El **Proceso Unificado de Desarrollo de Software** (PUDS, o *Unified Process*) es un marco de
proceso para el desarrollo de software orientado a objetos, publicado en 1999 por **Ivar
Jacobson, Grady Booch y James Rumbaugh** en *El Proceso Unificado de Desarrollo de Software*.

Los tres autores son también los creadores de UML, y eso no es casualidad: **UML es el lenguaje y
el PUDS es el proceso que dice cuándo y para qué usar cada diagrama**. Cada uno resuelve la mitad
del problema.

Se lo llama "unificado" porque integra las mejores prácticas de los métodos que lo precedieron
—Objectory de Jacobson, el método de Booch y OMT de Rumbaugh— en un único marco coherente. No es
una metodología rígida: es un **marco adaptable**, del que cada organización toma lo que su
proyecto necesita. RUP (*Rational Unified Process*) es su versión comercial más conocida.

## 2. Las tres características que lo definen

El PUDS se resume en tres rasgos. No son eslóganes: cada uno tiene consecuencias concretas sobre
cómo se trabaja.

### 2.1 Dirigido por casos de uso

Un **caso de uso** describe una interacción completa entre un actor y el sistema que produce un
resultado de valor para ese actor.

En el PUDS los casos de uso **no son solo un artefacto de requisitos**: son el hilo conductor de
todo el proceso. Cada caso de uso se captura, luego se analiza, luego se diseña, luego se
implementa y finalmente se prueba. La trazabilidad es completa: se puede seguir un mismo caso de
uso desde el enunciado del cliente hasta la prueba que lo verifica.

La consecuencia práctica es que **el sistema se construye por funcionalidades completas y
verificables**, no por capas técnicas. No se hace "toda la base de datos" y luego "todos los
formularios": se hace *Crear reserva* de punta a punta.

> **En este proyecto:** los 37 casos de uso del **CAP. 1 § 1.1.2**
> ([`docs/03-captura-requisitos.md`](../03-captura-requisitos.md)) son el eje. La tabla de
> trazabilidad RF → CU y la organización del código por paquetes son la aplicación directa de
> este principio.

### 2.2 Centrado en la arquitectura

La **arquitectura** es el conjunto de decisiones estructurales importantes: cómo se divide el
sistema, cómo se comunican sus partes y qué tecnologías lo sostienen. Son las decisiones caras de
revertir.

El PUDS sostiene que la arquitectura debe establecerse **temprano**, en las primeras iteraciones,
y validarse construyendo los casos de uso arquitectónicamente significativos —aquellos que
atraviesan la mayor cantidad de partes del sistema—. La arquitectura y los casos de uso se
moldean mutuamente: los casos de uso dicen qué debe hacer el sistema; la arquitectura dice cómo
puede hacerlo de forma sostenible.

> **En este proyecto:** los once paquetes de análisis del **CAP. 2 § 2.1.1**
> ([`docs/04-analisis-arquitectura.md`](../04-analisis-arquitectura.md)), su regla de dependencias
> unidireccionales y las cuatro capas del backend (router → service → repository → model). El
> código replica los paquetes con el mismo nombre, de modo que el diagrama de paquetes y el árbol
> de carpetas son la misma cosa.

### 2.3 Iterativo e incremental

El desarrollo se organiza en **iteraciones**: mini-proyectos de duración acotada que recorren
todos los flujos de trabajo y terminan en un **incremento** —una versión ejecutable y probada del
sistema, con más funcionalidad que la anterior—.

- **Iterativo** — se repite el ciclo completo varias veces, refinando lo hecho.
- **Incremental** — cada vuelta agrega funcionalidad al producto.

Los beneficios son concretos: los riesgos se atacan temprano en lugar de descubrirse al final;
hay retroalimentación real sobre software que funciona, no sobre documentos; y los cambios de
requisitos se absorben en la iteración siguiente en lugar de romper el plan.

> **En este proyecto:** tres ciclos, uno por presentación, cada uno cerrando con software
> **desplegado y funcionando** — ver [`docs/05-plan-y-cronograma.md`](../05-plan-y-cronograma.md).

## 3. Las cuatro fases

El ciclo de vida se divide en cuatro fases. Cada una termina en un **hito** que decide si el
proyecto continúa.

| Fase | Pregunta que responde | Hito de cierre |
|---|---|---|
| **Inicio** *(Inception)* | ¿Vale la pena hacerlo? | **Objetivos del ciclo de vida** — alcance, actores, casos de uso principales, riesgos y viabilidad |
| **Elaboración** *(Elaboration)* | ¿Cómo se va a construir? | **Arquitectura del ciclo de vida** — arquitectura estable y validada, mayoría de los casos de uso detallados, riesgos técnicos resueltos |
| **Construcción** *(Construction)* | Construirlo | **Capacidad operativa inicial** — producto completo, probado y listo para entregar |
| **Transición** *(Transition)* | Entregarlo | **Entrega del producto** — sistema en manos del usuario, defectos corregidos, capacitación hecha |

El **esfuerzo no se reparte por igual**: Inicio y Transición son cortas; Elaboración y
Construcción concentran la mayor parte del trabajo. Y una fase puede contener varias iteraciones.

## 4. Los flujos de trabajo

Cada iteración recorre **todos** los flujos, pero en distinta proporción según la fase. Ésa es la
idea que representa el célebre **diagrama de las jorobas** (*humps chart*): cada flujo es una
curva cuyo pico está en la fase donde más pesa, pero ninguna curva es cero en las demás.

| Flujo de trabajo | Qué produce |
|---|---|
| **Modelado del negocio** | Comprensión del contexto y los procesos de la organización: problemas, causas, actores del negocio |
| **Requisitos** | Modelo de casos de uso, actores, especificaciones y prototipos de interfaz |
| **Análisis** | Estructura lógica independiente de la tecnología: paquetes, clases de análisis, diagramas de comunicación |
| **Diseño** | Solución técnica concreta: diagramas de secuencia, clases de diseño, modelo de datos, despliegue |
| **Implementación** | Código fuente, componentes, ejecutables |
| **Pruebas** | Casos de prueba, resultados y defectos |

A éstos se suman los **flujos de apoyo**: gestión del proyecto, gestión de la configuración y del
cambio, y gestión del entorno.

```
                 INICIO   ELABORACIÓN   CONSTRUCCIÓN   TRANSICIÓN
Modelado negocio  ███▄       ▄▄            ▁              ▁
Requisitos        ▄████     ████▄          ▄▄             ▁
Análisis           ▄▄▄     ██████▄         ▄▄▄            ▁
Diseño              ▁▄     ▄██████        ████▄           ▄
Implementación      ▁       ▄▄███        ███████▄        ▄▄
Pruebas             ▁        ▄▄▄          ▄█████         ████
```

*Cada flujo alcanza su pico en una fase distinta, pero ninguno desaparece del todo.*

### Clases de análisis

Dentro del flujo de Análisis, el PUDS clasifica las clases en tres estereotipos, y es una
distinción que ordena mucho el diseño posterior:

| Estereotipo | Responsabilidad | Equivalente en este proyecto |
|---|---|---|
| **«boundary»** (interfaz) | Comunicación con actores externos | Componentes de Angular / Flutter · `router.py` |
| **«control»** (control) | Coordinación y reglas del caso de uso | `service.py` |
| **«entity»** (entidad) | Información persistente del dominio | `models.py` |

## 5. Comparación con métodos ágiles

| | **PUDS** | **Scrum / ágil** |
|---|---|---|
| Unidad de trabajo | Iteración dentro de una fase | Sprint |
| Documentación | Extensa y formal, con artefactos definidos | La mínima necesaria |
| Modelado | Central, con UML | Opcional |
| Requisitos | Casos de uso detallados | Historias de usuario |
| Roles | Muchos y especializados | Tres (PO, SM, Equipo) |
| Prescripción | Alto: define artefactos y flujos | Bajo: define un marco de eventos |

Ambos son iterativos e incrementales — no es la diferencia. La diferencia real está en **cuánto
se modela y se documenta antes de codificar**.

### Por qué PUDS en este proyecto

1. **Lo exige el enunciado**, junto con UML 2.5+.
2. **El dominio se presta**: los requisitos están fijados de antemano en el enunciado y no van a
   cambiar durante las tres semanas. El principal valor de lo ágil —absorber requisitos
   cambiantes— no aplica acá.
3. **El producto evaluable incluye el modelado.** En un proyecto comercial la documentación
   compite con el código por el tiempo disponible; en éste, la documentación **es** parte de la
   entrega.
4. **Ordena el trabajo de un equipo de dos**: los paquetes de análisis definen quién toca qué y
   minimizan los conflictos de integración.

## 6. Aplicación concreta en FashionStore

| Ciclo | Fase PUDS | Período | Casos de uso | Flujos predominantes |
|---|---|---|---|---|
| **1 · Fundamentos** | Inicio | 01/09 – 05/09 | 9 (CU-01 a CU-09) | Modelado del negocio, Requisitos |
| **2 · Núcleo del negocio** | Elaboración | 06/09 – 13/09 | 13 | Análisis, Diseño, Implementación |
| **3 · Comercio e inteligencia** | Construcción | 14/09 – 20/09 | 15 | Diseño, Implementación, Pruebas |
| **Cierre** | Transición | 21/09 – 22/09 | — | Pruebas de aceptación, defensa |

**Cada ciclo recorre los cinco flujos** sobre su propio subconjunto de casos de uso y cierra con
software desplegado. El Ciclo 1 es deliberadamente el más corto y el que más peso pone en
Requisitos; el Ciclo 3 concentra Implementación y Pruebas.

**Trazabilidad de un caso de uso a través del proceso** — tomando CU-22 *Crear reserva de
prendas*:

```
Modelado del negocio  →  P13: no existe mecanismo de reserva anticipada  (doc. 02)
Requisitos            →  RF09, RF10 · CU-22 detallado con flujos y excepciones  (doc. 03)
Análisis              →  Paquete P6 · diagrama de comunicación · clases de análisis  (doc. 04)
Diseño                →  Diagrama de secuencia · clases de diseño · tablas reserva y detalle
Implementación        →  backend/app/modules/reservas/  (router → service → repository → models)
Pruebas               →  Caso de prueba: reservar la última unidad desde dos sesiones a la vez
```

---

## Bibliografía de esta sección

- Jacobson, I., Booch, G. y Rumbaugh, J. (2000). *El Proceso Unificado de Desarrollo de Software*.
  Addison-Wesley.
- Kruchten, P. (2003). *The Rational Unified Process: An Introduction* (3.ª ed.). Addison-Wesley.
- Pressman, R. S. (2010). *Ingeniería del Software: un enfoque práctico* (7.ª ed.). McGraw-Hill.
  — capítulo sobre modelos de proceso prescriptivos.
- Sommerville, I. (2011). *Ingeniería de Software* (9.ª ed.). Pearson.
