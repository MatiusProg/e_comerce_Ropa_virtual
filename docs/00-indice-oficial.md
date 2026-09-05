# 0) ÍNDICE OFICIAL DE LA INGENIERA — MAPEO Y ANÁLISIS

Documento de control. Registra el **índice actualizado que entregó la ingeniera**, tal como está
plasmado en el documento de entrega (`SI2 Ex1 Grupo 16.docx`, editado en OneDrive), lo mapea
contra los documentos de este repositorio y deja constancia de lo que falta y de lo que ya no va.

> **Regla de oro:** el índice de la ingeniera manda. Los archivos de `docs/` son la *fuente* del
> contenido; el `.docx` es el *entregable*. Cuando la numeración de un archivo de `docs/` no
> coincida con la del índice oficial, gana el índice oficial.

---

## 0.1 El índice oficial

Cada capítulo de la Parte II se subdivide por ciclo (`CICLO #1`, `CICLO #2`, `CICLO #3`) en las
secciones que dependen de los casos de uso. Esos encabezados se van agregando a medida que cada
ciclo tiene contenido; por eso hoy solo existe `CICLO #1`.

```
1.1  Introducción
1.2  Objetivo General
1.3  Objetivos Específicos
1.4  Descripción del problema
1.5  Alcance
     1.5.1  Alcance Positivo
     1.5.2  Alcance Negativo

Parte I – Fundamentación Teórica
     a) E-commerce            · a. Como usuario  · b. Como desarrollador
     b) Pasarelas de pago     · a. Formas de pago online  · b. LIBÉLULA  · c. PayPal, STRIPE
     c) Deliverys             · a. Cómo funcionan  · b. Cómo calculan los pagos
     d) PUDS
     e) UML

Parte II – Proceso de desarrollo

CAP. 1  FLUJO DE TRABAJO: CAPTURA DE REQUISITOS
     1.1  Identificar Casos de Uso y Actores
          1.1.1  Actores
          1.1.2  Casos de Uso
          1.1.3  Requisitos Funcionales
          1.1.4  Requisitos No Funcionales
     1.2  Priorización de Casos de Uso          → CICLO #1 · #2 · #3
     1.3  Detallar Casos de Uso
          1.3.1  Elaborar la tabla Detalle      → por ciclo
          1.3.2  Diseñar Casos de Uso           → por ciclo
     1.4  Prototipar Interfaz De Usuario        → por ciclo
     1.5  Estructurar Modelo de Casos de Uso    → por ciclo

CAP. 2  FLUJO DE TRABAJO: ANÁLISIS
     2.1  Análisis de Arquitectura
          2.1.1  Identificar Paquetes
          2.1.2  Relacionar Paquetes y Casos de Uso
          2.1.3  Vista de Paquetes
     2.2  Analizar Casos de Uso                 → por ciclo
     2.3  Análisis de Clases                    → por ciclo
     2.4  Análisis de Paquetes                  → por ciclo

CAP. 3  FLUJO DE TRABAJO: DISEÑO
     3.1  Diseño de Arquitectura
          3.1.1  Diseño lógico                  → por ciclo
          3.1.2  Diseño Físico                  → por ciclo
     3.2  Diseño de Casos de Uso
          Diagrama de Secuencia                 → por ciclo
          Diagrama de Tiempo                    → no pedido todavía
          Diagrama de Estado                    → por ciclo
          Diagrama de Navegación                → por ciclo
     3.3  Diseño de Datos
          3.3.1  Diseño de datos lógico         → por ciclo
          3.3.2  Diseño de datos físico         → por ciclo

CAP. 4  FLUJO DE TRABAJO: IMPLEMENTACIÓN          (Ciclo 2)
     4.1  Selección de plataforma de Software
          4.1.1 Lenguaje · 4.1.2 Base de Datos · 4.1.3 Sistemas Operativos
          4.1.4 Frameworks y Librerías Adicionales
     4.2  Implementación Arquitectura Sistema Principal
     4.3  Implementación de Arquitectura Subsistemas (paquetes)

CAP. 5  FLUJO DE TRABAJO: PRUEBAS                 (Ciclo 3)

BIBLIOGRAFÍA                                      (Ciclo 2)
ANEXOS                                            (Ciclo 2)
     GITHUB · PLATAFORMA · DESCARGAR APP
```

---

## 0.2 Reglas de alcance

**Qué va completo desde la primera entrega**, sin subdividir por ciclo:

- 1.1.1 Actores — los nueve (A1 a A9)
- 1.1.2 Casos de Uso — los treinta y siete (CU-01 a CU-37)
- 1.1.3 Requisitos Funcionales — RF01 a RF36
- 1.1.4 Requisitos No Funcionales — RNF01 a RNF13
- 2.1 Análisis de Arquitectura — los once paquetes, la matriz paquete–caso de uso y la vista de
  paquetes

**Qué se desarrolla solo para el ciclo en curso.** Todo lo que depende de los casos de uso: 1.3,
1.4, 1.5, 2.2, 2.3, 2.4 y todo el CAP. 3. En esta entrega, los **nueve casos de uso del Ciclo 1**
(CU-01 a CU-09) y los paquetes **P1, P2 y P3-maestros**.

**Hasta dónde llega esta primera entrega.** Hasta el **CAP. 3**. El CAP. 4 (Implementación) y el
CAP. 5 (Pruebas) se estrenan en los ciclos 2 y 3 respectivamente, igual que la Bibliografía y los
Anexos.

**Qué no se hace en este proyecto.** El **Modelado del Negocio** y el **diagrama de Ishikawa** no
forman parte del índice y no se realizan. `02-modelo-negocio.md` queda en el repositorio como
contexto interno —de ahí salieron el alcance, varios objetivos y varios requisitos—, pero **no se
vuelca al `.docx`** y ninguna sección entregada cita sus códigos de problema (P1, P2, …). Esas
referencias ya se reescribieron en `01-perfil.md`, `03-captura-requisitos.md`,
`04-analisis-arquitectura.md` y `marco-teorico/01-ecommerce.md` para que el texto entregado se
sostenga solo.

**Qué no se pidió todavía.** El **Diagrama de Tiempo** de 3.2. Queda sin `CICLO #1` hasta que la
docente lo solicite.

**Todo lo demás va dibujado.** Donde el índice pide un diagrama, va un diagrama —no una tabla, no
un resumen en prosa—. Esto afecta sobre todo a 1.3.2, 2.1.3, 2.2, 2.3, 3.1.1, 3.1.2, 3.2 y 3.3:
son **doce diagramas** para el Ciclo 1, contando los nueve de secuencia como uno por caso de uso.

**Numeración.** El Perfil usa 1.1–1.5 y `CAP. 1` vuelve a usar 1.1–1.5. Es ambiguo, pero es el
índice oficial y se respeta tal cual. Nuestros archivos `03-captura-requisitos.md` (§3.x) y
`04-analisis-arquitectura.md` (§4.x) ya no coinciden con la numeración del entregable; la tabla de
§0.3 resuelve la correspondencia.

---

## 0.3 Mapeo índice oficial → repositorio

| Sección del índice oficial | Fuente en `docs/` | Estado |
|---|---|---|
| 1.1 Introducción | `01-perfil.md` §1.1 | ✔ |
| 1.2 Objetivo General | `01-perfil.md` §1.2.1 | ✔ |
| 1.3 Objetivos Específicos | `01-perfil.md` §1.2.2 | ✔ |
| 1.4 Descripción del problema | `01-perfil.md` §1.3 | ✔ |
| 1.5.1 / 1.5.2 Alcance | `01-perfil.md` §1.4.1 y §1.4.2 | ✔ |
| — (sin sección) | `01-perfil.md` §1.4.3 Supuestos y restricciones | queda fuera del índice; llevar a 1.5 o descartar |
| Parte I · a) a e) | `marco-teorico/01` a `05` | ✔ (corregir en el `.docx` dos referencias rotas, ver §0.7) |
| **1.1.1 Actores** | `03-captura-requisitos.md` §3.1.1 | ✔ los 9 |
| **1.1.2 Casos de Uso** | `03-captura-requisitos.md` §3.1.2 | ✔ los 37 |
| **1.1.3 Requisitos Funcionales** | `03-captura-requisitos.md` §3.3 | ✔ RF01–RF36 con trazabilidad a CU |
| **1.1.4 Requisitos No Funcionales** | `03-captura-requisitos.md` §3.4 | ✔ RNF01–RNF13 |
| **1.2 Priorización** (los tres ciclos) | `03-captura-requisitos.md` §3.2 | ✔ redactado · falta volcarlo al `.docx` |
| **1.3.1 Tabla Detalle** · Ciclo 1 | `entregas/ciclo-1/cap-1-captura-requisitos.md` | ✔ las 9 tablas, listas para volcar |
| **1.3.2 Diseñar Casos de Uso** · Ciclo 1 | `diagramas/VioletBoutique.eapx` · PNG en `diagramas/casos-de-uso/` | ✔ los 9 diagramas, uno por caso de uso |
| **1.4 Prototipar Interfaz** · Ciclo 1 | `prototipos/` (vacío) | ✘ **falta** — ~12 pantallas |
| **1.5 Estructurar Modelo de CU** · Ciclo 1 | `entregas/ciclo-1/cap-1-captura-requisitos.md` · `diagramas/VioletBoutique.eapx` | ✔ texto y diagrama |
| 2.1.1 Identificar Paquetes | `04-analisis-arquitectura.md` §4.1.1 | ✔ los 11 |
| 2.1.2 Relacionar Paquetes y CU | `04-analisis-arquitectura.md` §4.1.2 | ✔ |
| 2.1.3 Vista de Paquetes | `04-analisis-arquitectura.md` §4.1.3 | ◐ texto ✔ · **falta el diagrama** |
| **2.2 Analizar Casos de Uso** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ clases y mensajes de los 9 especificados · **faltan los 9 diagramas** |
| **2.3 Análisis de Clases** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ las 14 clases con atributos y relaciones · **falta el diagrama** |
| **2.4 Análisis de Paquetes** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ✔ contenido y dependencias de P1, P2 y P3-maestros |
| **3.1.1 Diseño lógico** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ las cuatro capas y su correspondencia con los estereotipos · **falta el diagrama** |
| **3.1.2 Diseño Físico** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ los cuatro nodos especificados · **falta el diagrama** y cerrar el proveedor de nube |
| **Diagrama de Secuencia** · Ciclo 1 | — | ✘ **falta** — 9, uno por caso de uso |
| Diagrama de Tiempo | — | — no pedido todavía |
| **Diagrama de Estado** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ estados y transiciones de `SesionToken` · **falta el diagrama** |
| **Diagrama de Navegación** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ mapa de pantallas por rol · **falta el diagrama** |
| **3.3.1 Diseño de datos lógico** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ◐ entidades, claves y cardinalidades · **falta el diagrama entidad-relación** |
| **3.3.2 Diseño de datos físico** · Ciclo 1 | `entregas/ciclo-1/cap-2-3-analisis-y-diseno.md` | ✔ esquema PostgreSQL completo con tipos, claves, índices y restricciones |
| CAP. 4 · Implementación | `06-decisiones-tecnicas.md` + `entorno/versiones.md` + `07-estructura-repositorio.md` | Ciclo 2 — el material ya está escrito, hay que reordenarlo en 4.1.1–4.1.4, 4.2 y 4.3 |
| CAP. 5 · Pruebas | `pruebas/` (vacío) | Ciclo 3 |
| BIBLIOGRAFÍA | bibliografías por sección en `marco-teorico/` | Ciclo 2 — hay que consolidarlas |
| ANEXOS · GITHUB / PLATAFORMA / DESCARGAR APP | `07-estructura-repositorio.md` §7.1 | Ciclo 2 — URL del repositorio, URL pública del sistema desplegado y enlace al APK |
| — (sin sección) | `05-plan-y-cronograma.md` | no tiene lugar en el índice; queda como documento interno |
| — (no se realiza) | `02-modelo-negocio.md` | fuera del alcance del entregable |

Leyenda: ✔ hecho · ◐ hay material, falta el diagrama · ✘ falta

---

## 0.4 Lo que falta para esta entrega

El **texto** de todas las secciones del Ciclo 1 está escrito y listo para volcar al `.docx`:

- `CAP. 1` → [`entregas/ciclo-1/cap-1-captura-requisitos.md`](entregas/ciclo-1/cap-1-captura-requisitos.md)
  — las nueve tablas de detalle (1.3.1) y el modelo estructurado con `include`, `extend` y
  generalización (1.5).
- `CAP. 2` y `CAP. 3` → [`entregas/ciclo-1/cap-2-3-analisis-y-diseno.md`](entregas/ciclo-1/cap-2-3-analisis-y-diseno.md)
  — clases de análisis y mensajes por caso de uso (2.2), las catorce clases (2.3), los tres
  paquetes (2.4), las cuatro capas (3.1.1), los cuatro nodos de despliegue (3.1.2), los estados de
  la sesión y el mapa de navegación (3.2), y el modelo de datos lógico y físico (3.3).

**Lo que falta son los artefactos gráficos y el volcado.** Todo lo de abajo se dibuja a partir de
los dos documentos anteriores:

| # | Artefacto | Sección | Cantidad |
|---|---|---|:---:|
| 1 | Diagrama de casos de uso general y del Ciclo 1 | 1.3.2 | 2 |
| 2 | Prototipos de interfaz | 1.4 | ~12 |
| 3 | Diagrama del modelo estructurado (include / extend / generalización) | 1.5 | 1 |
| 4 | Diagrama de la vista de paquetes | 2.1.3 | 1 |
| 5 | Diagramas de comunicación | 2.2 | 9 |
| 6 | Diagrama de clases de análisis | 2.3 | 1 |
| 7 | Diagrama de capas y paquetes de diseño | 3.1.1 | 1 |
| 8 | Diagrama de despliegue | 3.1.2 | 1 |
| 9 | Diagramas de secuencia | 3.2 | 9 |
| 10 | Diagrama de estado de `SesionToken` | 3.2 | 1 |
| 11 | Diagrama de navegación | 3.2 | 1 |
| 12 | Diagrama entidad-relación | 3.3.1 | 1 |

Más dos tareas de documento: **volcar todo al `.docx`** y **actualizar el índice con F9**.

Los diagramas de secuencia (9) son los únicos que conviene esperar a tener el código, porque el
orden exacto de llamadas se fija al implementar. Los once artefactos restantes pueden dibujarse ya.

El detalle con responsables y estado está en `05-plan-y-cronograma.md` §5.3.

---

## 0.5 La cuestión de los 30 casos de uso

**Estado: no confirmado.** Varios compañeros afirman que la ingeniera pidió 30 casos de uso. Se
consulta el 04/09/2026.

Con la estructura por ciclo el riesgo bajó bastante:

- **1.1.2 y 1.2 van completos**, o sea que se entregan **37 casos de uso identificados y
  priorizados** — por encima de 30 en la lectura más común.
- La única lectura que todavía muerde es "30 **con tabla de detalle**". Ahí la subdivisión por
  ciclo juega a favor: detallar solo los del ciclo en curso es ortodoxia PUDS y se defiende sola.
- **Cobertura barata:** la tabla de detalle es el único artefacto que no depende de ningún otro.
  Si al terminar las nueve del Ciclo 1 se sigue de corrido con las de prioridad Alta del Ciclo 2,
  se llega a veintitantas sin tocar el camino crítico. Si mañana la respuesta es "30 detallados",
  se está cerca; si es "los del ciclo", el trabajo adelantado va igual en la entrega siguiente.
- **No confundir con implementación.** Detallar es trabajo documental. El Ciclo 1 sigue
  implementando CU-01 a CU-09.

---

## 0.6 Revisión del `.docx` — estado de los encabezados por ciclo

Revisado sobre la versión del 03/09/2026. Los encabezados `CICLO #1` ya están puestos en 1.2
(con `#2` y `#3`), 1.3.2, 1.4, 1.5, 2.2, 2.3, 3.1.1, 3.1.2, Diagrama de Secuencia, 3.3.1 y 3.3.2.
Correctamente **no** los llevan 1.1.1 a 1.1.4, 2.1.1 a 2.1.3 ni el Diagrama de Tiempo.

**Faltan cuatro:**

| Sección | Por qué lleva ciclo |
|---|---|
| **1.3.1 Elaborar la tabla Detalle** | Es la que más claramente va por ciclo — nueve tablas ahora, trece en el Ciclo 2. Hoy 1.3.2 tiene `CICLO #1` y 1.3.1 no. |
| **2.4 Análisis de Paquetes** | En este ciclo se analizan P1, P2 y P3-maestros; en el siguiente, P3, P4, P5 y P6. |
| **Diagrama de Estado** (3.2) | `SesionToken` en el Ciclo 1; `Reserva` en el 2 y `Pedido` en el 3. |
| **Diagrama de Navegación** (3.2) | El mapa de pantallas crece con cada ciclo. |

**Otras observaciones sobre el documento:**

- **El índice automático está desactualizado.** Es un campo `TOC \o "1-3"`, o sea que solo muestra
  tres niveles. `CICLO #1` usa el estilo `Titulo3`, que está basado en *Título 4* y por lo tanto
  **no debería aparecer** en el índice — sin embargo hoy aparece una vez, suelta, debajo de 1.2.
  Es residuo de un refresco anterior. **Al actualizar con F9 esa línea desaparece** y el índice
  queda limpio, con los `CICLO #N` visibles solo en el cuerpo. Es el comportamiento deseado; no
  hay que cambiar el estilo.
- **1.1.4 dice "Requisitos No funcionales"** — conviene unificar la mayúscula con el resto de los
  títulos: *Requisitos No Funcionales*.
- Los subtítulos de 3.2 (Secuencia, Tiempo, Estado, Navegación) están **sin numerar**, igual que
  en el índice que dio la ingeniera. Se deja así.
- **`CAP. 5`, `BIBLIOGRAFÍA` y `ANEXOS` ya existen como encabezados** aunque su contenido sea de
  los ciclos siguientes. Está bien que estén: el índice queda armado desde ahora.
- El anexo **PLATAFORMA** es donde va la URL pública del sistema desplegado. Aunque el anexo se
  llene en el Ciclo 2, **el despliegue es exigencia del enunciado desde esta entrega**, así que la
  URL debería existir el 05/09 aunque todavía no esté escrita ahí.

---

## 0.7 Errata pendiente en el `.docx`

Al volcar la Parte I al documento se perdieron dos referencias cruzadas que en el Markdown eran
enlaces. En el `.docx` las frases quedaron incompletas, dentro de **Parte I · d) PUDS**:

| Dice (roto) | Debe decir |
|---|---|
| «los 37 casos de uso **de** son el eje» | «los 37 casos de uso del **CAP. 1 § 1.1.2** son el eje» |
| «los once paquetes de análisis **de** , su regla de dependencias…» | «los once paquetes de análisis del **CAP. 2 § 2.1.1**, su regla de dependencias…» |

El origen ya está corregido en `marco-teorico/04-puds.md`; **la corrección en el `.docx` hay que
hacerla a mano.**
