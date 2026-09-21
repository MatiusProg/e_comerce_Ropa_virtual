# Ciclo 3 · Qué caso de uso lleva cada diagrama

> **Escrito el 20/09/2026.** Decide sobre qué casos de uso se hacen los tres
> diagramas nuevos —estado, navegación y tiempo— y el de secuencia que los
> acompaña. El auxiliar fue explícito en que **no se hacen de todos los CU**.

---

## 1. El criterio

De la explicación del auxiliar:

- **Tiempo:** «solo los de procesos como catálogo, venta, compra, pagos, ia,
  probador». Pocos.
- **Estado:** «suele mostrar o representar los mismos cus que el de tiempo».
- **Navegación:** «se puede hacer por rol o por cu…, **la ing pide por cu**».
- **Secuencia:** tampoco se espera de todos.

Con eso, el conjunto son los CU que (a) caen en uno de esos seis procesos y
(b) tienen una máquina de estados de verdad, no un alta-baja-modificación.

## 2. Los seis elegidos del Ciclo 3

| CU | Proceso del auxiliar | Por qué entra |
|---|---|---|
| **CU-27** Realizar pedido y pagar | venta · compra · pagos | El más rico: aparta stock, espera un actor externo y puede expirar solo |
| **CU-28** Confirmar pago | pagos | La otra mitad de CU-27; el estado final lo fija un webhook firmado |
| **CU-31** Registrar venta presencial | venta | Depende del turno de caja y descuenta inventario |
| **CU-34** Asistente virtual | ia | El ejemplo que el propio auxiliar usó para el diagrama de tiempo |
| **CU-33** Recomendar prendas | ia | Segundo de IA, con validación contra catálogo |
| **CU-21** Vestidor virtual | probador | Es literalmente «el probador» de su lista |

**Cuatro diagramas por cada uno** —estado, navegación, tiempo y secuencia—
dan 24. Los de secuencia de los Ciclos 1 y 2 ya están todos.

## 3. Lo que hay en el modelo hoy

**Los 43 diagramas viejos se borraron** —18 de estado, 18 de tiempo y 7 de
navegación, de los Ciclos 1 y 2— y en su lugar están estos **17**, todos del
Ciclo 3:

| CU | Estado | Tiempo | Navegación |
|---|:---:|:---:|:---:|
| CU-21 Vestidor virtual | ✔ | ✔ | ✔ |
| CU-27 Pedido y pago | ✔ | ✔ | ✔ |
| CU-28 Confirmar pago | ✔ | ✔ | — |
| CU-31 Venta presencial | ✔ | ✔ | ✔ |
| CU-33 Recomendaciones | ✔ | ✔ | ✔ |
| CU-34 Asistente virtual | ✔ | ✔ | ✔ |
| | **6** | **6** | **5** |

### Por qué CU-28 no tiene diagrama de navegación

**Porque no tiene pantallas.** Lo inicia la pasarela llamando a un webhook;
no hay página, ni formulario, ni nadie navegando. Lo único con interfaz es la
pantalla de retorno del pago, y esa ya está dibujada en el de CU-27, que es
donde el cliente la alcanza.

Dibujarle una navegación sería inventar un recorrido que no existe.

### Lo que cambió en los generadores para poder hacerlos

1. **`-CU` en el de navegación.** Estaba organizado por actor; pedir el de
   CU-27 por su actor arrastraba de vuelta los mapas acumulativos del Cliente.
   Ahora un bloque declara de qué CU es y se pide de a uno. Sin `-CU` los
   bloques por caso de uso no se dibujan.
2. **`nombre` por bloque.** Para que un diagrama de un solo CU no se llame
   como su actor y se pise con el mapa del ciclo.
3. **`base` por bloque.** CU-21 vive **solo en el teléfono**: sus carpetas son
   `mobile/lib`, no `frontend-web/src/app`. Decir lo contrario sería mentir
   sobre dónde está el código, que es la regla de oro 10 de la guía.

### Verificación tras generar

| | |
|---|---|
| Diagramas en el modelo | 175 |
| **Conectores rotos** | **0** |
| Comunicación / Secuencia / Casos de uso | 42 / 22 / 56, intactos |

Se hizo respaldo del `.eapx` antes de borrar nada, y el borrado alcanzó solo a
los paquetes 35, 36 y 37 —los tres del capítulo—, que no comparten elementos
con ningún otro diagrama.

## 4. El piloto, y por qué CU-27

Antes de escribir los 24 se hizo **uno de cada** sobre **CU-27**, para
revisar que el patrón sirve. Es el mejor candidato de los seis:

- **Estado:** cubre lo que ningún CU de gestión tiene —el commit **no** es el
  estado final—.
- **Tiempo:** es el único donde una entidad cambia de estado **sin que nadie
  la toque**, cuando la barrida expira el pedido.
- **Navegación:** es el único recorrido con las cuatro clases de enlace que
  describe el auxiliar: `link`, `build`, `submit` y `redirect`.

Los tres bloques están en `scripts/ea-estado-3-2.ps1`,
`scripts/ea-navegacion-3-2.ps1` y `scripts/ea-tiempo-3-2.ps1`, marcados
`# ================= CICLO 3 =================`.

## 5. Lo que queda por decidir

**El de navegación cambia de forma.** Los de los Ciclos 1 y 2 se hicieron
**por actor** —un mapa acumulativo por rol y por ciclo—, y el auxiliar pide
**por caso de uso**. El bloque nuevo es por CU y se dibuja aparte, con su
propio nombre; para eso se agregó el campo `nombre` al generador.

Eso deja una pregunta abierta que es del equipo, no del generador: **si los
de navegación de los Ciclos 1 y 2 hay que rehacerlos por CU**, o si se
entregan como están y solo el Ciclo 3 va por caso de uso.

## 6. Los Ciclos 1 y 2 quedaron sin estos tres diagramas

Los que había se borraron por estar mal, así que **hoy los Ciclos 1 y 2 no
tienen ninguno de estos tres**. Rehacerlos con el patrón nuevo es el trabajo
que sigue, si se decide que van.

Las carpetas `docs/diagramas/Estado/`, `Navegacion/` y `Tiempo/` siguen
vacías: **la exportación de los JPG la hace Mateo**, no el generador.
