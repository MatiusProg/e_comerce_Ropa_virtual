# 0) ÍNDICE OFICIAL DE LA INGENIERA — MAPEO Y ANÁLISIS

Documento de control. Registra el **índice actualizado que entregó la ingeniera**, tal como está
plasmado en el documento de entrega (`SI2 Ex1 Grupo 16.docx`, editado en OneDrive), lo mapea
contra los documentos de este repositorio y deja constancia de lo que falta, lo que sobra y lo
que hay que preguntar.

> **Regla de oro:** el índice de la ingeniera manda. Los archivos de `docs/` son la *fuente* del
> contenido; el `.docx` es el *entregable*. Cuando la numeración de un archivo de `docs/` no
> coincida con la del índice oficial, gana el índice oficial.

---

## 0.1 El índice oficial (transcripción literal)

```
1.1  Introducción
1.2  Objetivo General
1.3  Objetivos Específicos
1.4  Descripción del problema
1.5  Alcance
     1.5.1  Alcance Positivo
     1.5.2  Alcance Negativo

Parte I – Fundamentación Teórica
     a) E-commerce
        a. Como usuario
        b. Como desarrollador
     b) Pasarelas de pago
        a. Describir cómo funcionan las distintas formas de pago online
        b. Indagar sobre LIBÉLULA una pasarela que se usa con frecuencia en nuestro medio
        c. Indagar sobre PayPal, STRIPE una opción de pasarela de pago internacional
     c) Deliverys
        a. Describir cómo funcionan los deliverys
        b. Como calculan los pagos para una entrega
     d) PUDS
     e) UML

Parte II – Proceso de desarrollo

CAP. 1  FLUJO DE TRABAJO: CAPTURA DE REQUISITOS
     1.1  Identificar Casos de Uso y Actores
          1.1.1  Actores
          1.1.2  Casos de Uso
     1.2  Priorización de Casos de Uso
     1.3  Detallar Casos de Uso
          1.3.1  Elaborar la tabla Detalle
          1.3.2  Diseñar Casos de Uso
     1.4  Prototipar Interfaz De Usuario
     1.5  Estructurar Modelo de Casos de Uso

CAP. 2  FLUJO DE TRABAJO: ANÁLISIS
     2.1  Análisis de Arquitectura
          2.1.1  Identificar Paquetes
          2.1.2  Relacionar Paquetes y Casos de Uso
          2.1.3  Vista de Paquetes
     2.2  Analizar Casos de Uso
     2.3  Análisis de Clases
     2.4  Análisis de Paquetes

CAP. 3  FLUJO DE TRABAJO: DISEÑO
     3.1  Diseño de Arquitectura
          3.1.1  Diseño lógico
          3.1.2  Diseño Físico
     3.2  Diseño de Casos de Uso
          Diagrama de Secuencia
          Diagrama de Tiempo
          Diagrama de Estado
          Diagrama de Navegación
     3.3  Diseño de Datos
          3.3.1  Diseño de datos lógico
          3.3.2  Diseño de datos físico

CAP. 4  FLUJO DE TRABAJO: IMPLEMENTACIÓN
     4.1  Selección de plataforma de Software
          4.1.1  Lenguaje de Programación
          4.1.2  Base de Datos
          4.1.3  Sistemas Operativos
          4.1.4  Frameworks y Librerías Adicionales
     4.2  Implementación Arquitectura Sistema Principal
     4.3  Implementación de Arquitectura Subsistemas (paquetes)

CAP. 5  FLUJO DE TRABAJO: PRUEBAS
```

---

## 0.2 Qué cambió respecto de nuestra estructura

1. **La numeración se reinicia en la Parte II.** El Perfil usa 1.1–1.5 y `CAP. 1` vuelve a usar
   1.1–1.5. Es ambiguo, pero es el índice oficial: se respeta tal cual. Nuestros archivos
   `03-captura-requisitos.md` (§3.x) y `04-analisis-arquitectura.md` (§4.x) **ya no coinciden**
   con la numeración del entregable; ver la tabla de mapeo de §0.3.

2. **El documento ya no se organiza por ciclo, sino por flujo de trabajo.** No hay
   "CAP. 1 del Ciclo 1", "CAP. 1 del Ciclo 2": hay **un solo** capítulo de Captura de Requisitos.
   La consecuencia es directa: `CAP. 1` debe quedar **completo**, con todos los actores, todos
   los casos de uso, todos detallados y prototipados — no solo los nueve del Ciclo 1. Esto es lo
   que hace verosímil el rumor de los 30 CU (ver §0.5).

3. **Desaparece el capítulo de Modelo del Negocio.** Nuestro `02-modelo-negocio.md` (lista y
   depuración de problemas, propietarios, cuantificación, alternativas, Ishikawa) **no tiene
   sección propia en el índice oficial**. Opciones, en orden de preferencia:
   - fundirlo dentro de **1.4 Descripción del problema** — es donde encaja de forma natural, el
     Ishikawa es el análisis causal del problema que ahí se describe;
   - dejarlo como **anexo** al final del documento.

   No conviene descartarlo: es trabajo hecho, es parte del PUDS (flujo de Modelado del Negocio) y
   el Ishikawa fue pedido explícitamente. **Preguntar a la ingeniera.**

4. **Desaparecen las secciones de Requisitos Funcionales y No Funcionales.** El índice no tiene
   ningún apartado para RF01–RF36 ni RNF01–RNF13, que hoy viven en `03-captura-requisitos.md`
   §3.3 y §3.4 y que el enunciado exige (§5 y §6). El lugar natural es **dentro de `CAP. 1`**,
   antes de 1.1 o como sub-apartado de 1.1. **Preguntar a la ingeniera** — es el hueco más grande
   del índice.

5. **El cronograma, las decisiones técnicas y la estructura del repositorio tampoco tienen
   sección propia.** `05-plan-y-cronograma.md`, `06-decisiones-tecnicas.md` y
   `07-estructura-repositorio.md` se reparten así: la plataforma de software va a **4.1**, el
   despliegue a **3.1.2 / 4.2**, la organización del código a **4.3**, y el cronograma queda sin
   lugar (anexo).

6. **`CAP. 5 FLUJO DE TRABAJO: PRUEBAS` aparece en el índice (pág. 32) pero no existe en el
   cuerpo del documento.** Hay que crear el encabezado; hoy el `.docx` termina en 4.3.

---

## 0.3 Mapeo índice oficial → repositorio

| Sección del índice oficial | Fuente en `docs/` | Estado |
|---|---|---|
| 1.1 Introducción | `01-perfil.md` §1.1 | ✔ redactado y volcado al `.docx` |
| 1.2 Objetivo General | `01-perfil.md` §1.2.1 | ✔ |
| 1.3 Objetivos Específicos | `01-perfil.md` §1.2.2 | ✔ |
| 1.4 Descripción del problema | `01-perfil.md` §1.3 (+ `02-modelo-negocio.md`) | ✔ el texto; **falta** decidir dónde entra el Modelo del Negocio y el Ishikawa |
| 1.5.1 Alcance Positivo | `01-perfil.md` §1.4.1 | ✔ |
| 1.5.2 Alcance Negativo | `01-perfil.md` §1.4.2 | ✔ |
| — (sin sección) | `01-perfil.md` §1.4.3 Supuestos y restricciones | queda fuera del índice; llevar a 1.5 o a anexo |
| Parte I · a) E-commerce | `marco-teorico/01-ecommerce.md` | ✔ |
| Parte I · b) Pasarelas de pago | `marco-teorico/02-pasarelas-de-pago.md` | ✔ |
| Parte I · c) Deliverys | `marco-teorico/03-deliverys.md` | ✔ |
| Parte I · d) PUDS | `marco-teorico/04-puds.md` | ✔ (corregir en el `.docx` dos referencias rotas, ver §0.6) |
| Parte I · e) UML | `marco-teorico/05-uml.md` | ✔ |
| **1.1.1 Actores** | `03-captura-requisitos.md` §3.1.1 | ✔ 9 actores (A1–A9) |
| **1.1.2 Casos de Uso** | `03-captura-requisitos.md` §3.1.2 | ✔ 37 CU (CU-01 a CU-37) |
| **1.2 Priorización de Casos de Uso** | `03-captura-requisitos.md` §3.2 | ✔ prioridad, ciclo y paquete por CU |
| **1.3.1 Elaborar la tabla Detalle** | — | ✘ **falta** — 0 de 37 tablas de detalle |
| **1.3.2 Diseñar Casos de Uso** | — | ✘ **falta** — diagrama UML de casos de uso (general y por paquete) |
| **1.4 Prototipar Interfaz De Usuario** | `prototipos/` (vacío) | ✘ **falta** |
| **1.5 Estructurar Modelo de Casos de Uso** | — | ✘ **falta** — `include`, `extend`, generalización y agrupación por paquete |
| 2.1.1 Identificar Paquetes | `04-analisis-arquitectura.md` §4.1.1 | ✔ 11 paquetes |
| 2.1.2 Relacionar Paquetes y Casos de Uso | `04-analisis-arquitectura.md` §4.1.2 | ✔ |
| 2.1.3 Vista de Paquetes | `04-analisis-arquitectura.md` §4.1.3 | ✔ el texto; **falta** el diagrama dibujado |
| 2.2 Analizar Casos de Uso | — | ✘ **falta** — clases «boundary» / «control» / «entity» y diagramas de comunicación |
| 2.3 Análisis de Clases | `04-analisis-arquitectura.md` §4.2 (parcial) | ◐ hay modelo de dominio preliminar; falta el diagrama de clases de análisis |
| 2.4 Análisis de Paquetes | `04-analisis-arquitectura.md` §4.1.3 (parcial) | ◐ |
| 3.1.1 Diseño lógico | `06-decisiones-tecnicas.md` (parcial) | ◐ |
| 3.1.2 Diseño Físico | `04-analisis-arquitectura.md` §4.3 + `06-decisiones-tecnicas.md` §6.9 | ◐ despliegue descrito; falta el diagrama |
| 3.2 Diseño de Casos de Uso (secuencia, tiempo, estado, navegación) | — | ✘ **falta** (Ciclo 2) |
| 3.3 Diseño de Datos (lógico y físico) | — | ✘ **falta** — modelo E-R y esquema físico (Ciclo 2) |
| 4.1 Selección de plataforma de Software | `06-decisiones-tecnicas.md` + `entorno/versiones.md` | ✔ contenido listo; hay que reordenarlo en 4.1.1–4.1.4 |
| 4.2 Implementación Arquitectura Sistema Principal | `07-estructura-repositorio.md` §7.2 | ◐ |
| 4.3 Implementación de Arquitectura Subsistemas | `07-estructura-repositorio.md` §7.2 | ◐ |
| CAP. 5 Pruebas | `pruebas/` (vacío) | ✘ **falta** — la sección ni siquiera existe en el `.docx` |

Leyenda: ✔ hecho · ◐ hay material, hay que reorganizarlo · ✘ falta

---

## 0.4 Lo que falta, en orden

Todo lo de `CAP. 1` es bloqueante si se confirma que el capítulo va completo:

1. **Tablas de detalle de casos de uso** (1.3.1) — plantilla: nombre, código, descripción,
   propósito, actores, iniciador, precondiciones, flujo principal, flujos alternativos,
   postcondiciones y excepciones. Es el trabajo más voluminoso que queda.
2. **Diagrama UML de casos de uso** (1.3.2) — uno general y uno por paquete, legibles.
3. **Prototipos de interfaz** (1.4) — al menos los del Ciclo 1: login, gestión de usuarios,
   sucursales y maestros del catálogo.
4. **Modelo de casos de uso estructurado** (1.5) — relaciones `include`, `extend` y
   generalización, y agrupación de los CU por paquete.
5. **Diagrama de paquetes dibujado** (2.1.3) — el texto ya está.
6. **Ubicar RF/RNF, Modelo del Negocio e Ishikawa** una vez que la ingeniera responda.
7. **Crear el encabezado de `CAP. 5`** en el `.docx`.

---

## 0.5 La cuestión de los 30 casos de uso

**Estado: no confirmado.** Varios compañeros afirman que la ingeniera pidió 30 casos de uso para
esta primera presentación. Se consulta el 04/09/2026. Hasta entonces se sigue trabajando con lo
planificado.

Lo que ya se puede afirmar sin esperar la respuesta:

- **Identificados tenemos 37**, así que por número estamos por encima de 30 en cualquier lectura.
  El riesgo no está en *identificar*, está en *detallar*.
- **La lectura peligrosa** es "30 casos de uso **detallados**" (índice 1.3.1) para el 05/09. Hoy
  hay **0 tablas de detalle** escritas, y el plan (`05-plan-y-cronograma.md`, tarea 11) solo
  contempla detallar los **9 del Ciclo 1**. La diferencia es de **21 a 28 tablas adicionales**.
- **La estructura del propio índice apoya esa lectura**: `CAP. 1` es único, no se repite por
  ciclo, así que el capítulo se entrega completo o no se entrega.
- **Lo que NO cambia es el alcance de implementación.** Detallar un caso de uso es trabajo
  documental. El Ciclo 1 sigue implementando CU-01 a CU-09. No hay que confundir "30 CU
  documentados" con "30 CU programados para el 05/09": eso último no cabe en cuatro días y no es
  lo que pide el índice.

**Plan de contingencia si se confirma:** detallar los 37 en una sola pasada con la misma
plantilla, empezando por los 9 del Ciclo 1 (que además llevan prototipo) y siguiendo por
prioridad Alta → Media → Baja. Es trabajo repetitivo y paralelizable entre los dos.

**Qué preguntar el 04/09:**

1. ¿Los 30 CU son *identificados* o *detallados con tabla*?
2. ¿`CAP. 1` va completo en esta entrega, o solo la parte correspondiente al Ciclo 1?
3. ¿Dónde entran los Requisitos Funcionales y No Funcionales del enunciado?
4. ¿Dónde entra el Modelo del Negocio y el diagrama de Ishikawa?
5. ¿`CAP. 5 Pruebas` se entrega vacío o todavía no se incluye?

---

## 0.6 Errata detectada en el `.docx`

Al volcar la Parte I al documento se perdieron dos referencias cruzadas que en el Markdown eran
enlaces. En el `.docx` las frases quedaron incompletas, dentro de **Parte I · d) PUDS**:

| Dice (roto) | Debe decir |
|---|---|
| «los 37 casos de uso **de** son el eje» | «los 37 casos de uso del **CAP. 1 § 1.1.2** son el eje» |
| «los once paquetes de análisis **de** , su regla de dependencias…» | «los once paquetes de análisis del **CAP. 2 § 2.1.1**, su regla de dependencias…» |

Ya se corrigió el origen en `marco-teorico/04-puds.md` para que un próximo copiado no arrastre el
error; **la corrección en el `.docx` hay que hacerla a mano.**
