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

## 3. El piloto, y por qué CU-27

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

## 4. Lo que hay que mirar al revisar el piloto

**El de navegación cambia de forma.** Los de los Ciclos 1 y 2 se hicieron
**por actor** —un mapa acumulativo por rol y por ciclo—, y el auxiliar pide
**por caso de uso**. El bloque nuevo es por CU y se dibuja aparte, con su
propio nombre; para eso se agregó el campo `nombre` al generador.

Eso deja una pregunta abierta que es del equipo, no del generador: **si los
de navegación de los Ciclos 1 y 2 hay que rehacerlos por CU**, o si se
entregan como están y solo el Ciclo 3 va por caso de uso.

## 5. Estado de los Ciclos 1 y 2

Los de estado, navegación y tiempo de los Ciclos 1 y 2 **ya están generados
dentro del `.eapx`**. Lo que falta es **exportar los JPG**: las carpetas
`docs/diagramas/Estado/`, `Navegacion/` y `Tiempo/` están vacías.
