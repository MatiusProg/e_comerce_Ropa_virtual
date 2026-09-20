# CU-30 · Abrir y cerrar caja

Guía de lo que se construyó y por qué cada decisión es como es.

> **Escrita el 19/09/2026.** Es la **puerta de CU-31**: la base exige
> `turno_caja_id` en toda venta presencial, así que sin un turno abierto no se
> puede cobrar en el mostrador.

---

## 1. Lo que aporta, que no es abrir una fila

Abrir un turno es escribir un registro. Lo que este caso de uso aporta es el
**arqueo**: al cerrar, el sistema dice cuánto **debería** haber en el cajón y
la persona dice cuánto **hay**.

Los dos números se guardan, y la diferencia se calcula al leer.

**Se guardan los dos y no el resultado.** Un descuadre sin los dos números no
se puede auditar: saber que faltaron 50 Bs no dice si se contó mal, si se
cobró de menos o si falta plata.

```
monto_esperado = monto_apertura + efectivo cobrado − devoluciones
diferencia     = monto_cierre (contado) − monto_esperado
```

## 2. Por qué hizo falta una migración

`venta` no guardaba **cómo** se cobró. Sin eso el arqueo no se puede hacer:

| Si se suma… | Pasa que… |
|---|---|
| todo lo cobrado | cada pago con tarjeta descuadra el turno |
| nada | el esperado es siempre el monto de apertura, y el arqueo no compara nada |

Las dos son peores que no tener la función, porque **un arqueo que siempre
descuadra enseña a ignorarlo**.

La `0014_ciclo3_metodo_pago` agrega `venta.metodo_pago` con los mismos dos
CHECK que el resto de la tabla: obligatorio en las presenciales, nulo en las
digitales —esas las cobra la pasarela y el método lo sabe Stripe—.

**`QR` es un método aparte y no «efectivo».** En Bolivia el pago con código QR
bancario es corriente y **no entra al cajón**: meterlo dentro de EFECTIVO
descuadraría el turno por cada uno.

## 3. Las reglas que el código impone

| Regla | Por qué |
|---|---|
| **Una caja, un turno abierto** | Dos a la vez hacen que el arqueo no cierre nunca: no se sabría a cuál imputar lo cobrado. Lo garantiza el índice único parcial `ix_turno_caja_abierto`. |
| **Una persona, un turno** | Se comprueba antes de bloquear la caja: si el cajero ya tiene otro turno, el problema no es la caja que pidió. |
| **Cierra quien abrió** | El arqueo le atribuye un descuadre a una persona. Que otro lo cierre significa anotarle el faltante a quien no estuvo ahí. |
| **El descuadre no se rechaza** | Es justamente lo que hay que registrar. Una validación que exija que cuadre impide anotar el problema. |
| **Una venta cancelada no suma** | No se cobró, aunque quede colgada del turno. |

### El bloqueo, que parece redundante y no lo es

`bloquear_caja` toma `SELECT … FOR UPDATE` sobre la caja antes de insertar el
turno. El índice único parcial ya impide el dato malo, así que **la base nunca
queda mal**. Lo que el bloqueo evita es el *síntoma*: sin él, dos aperturas
simultáneas llegan las dos a la inserción y una revienta con un error de
integridad —que el cajero ve como «error del sistema» cuando lo correcto es
decirle «esa caja ya está abierta»—.

Se bloquea la **caja** y no el turno porque el turno que estorba todavía no
existe: no se puede bloquear una fila que la otra petición está por insertar.

## 4. Los endpoints

```
GET  /api/v1/caja/cajas                    las cajas de mi sucursal, y cuál está ocupada
GET  /api/v1/caja/turnos/mio               mi turno abierto, o null
POST /api/v1/caja/turnos                   abrir  {caja_id, monto_apertura}
POST /api/v1/caja/turnos/{id}/cierre       cerrar {monto_cierre} → devuelve el arqueo
```

**CAJERO y ENCARGADO.** El encargado atiende el mostrador en sucursales chicas
—que es el caso de esta tienda— y dejarlo afuera obligaría a tener un usuario
Cajero de mentira. El **administrador no**: no está en una sucursal, y un
turno que nadie abrió físicamente no tiene arqueo posible.

`GET /turnos/mio` devuelve `null` y no 404: **no tener turno abierto es el
estado normal** al empezar el día, y con 404 la pantalla trataría lo corriente
por el camino de los fallos.

La caja ocupada **se informa, no se esconde**: el cajero necesita saber que
existe y que alguien la tiene tomada, no que desapareció.

## 5. Una caja por sucursal, sembrada

`seed_catalogo._cajas` crea una `Caja 1` en cada sucursal.

**No hay API para dar de alta cajas** —eso sería del administrador y no está
en el alcance del ciclo—. Sin el sembrado, un despliegue limpio deja a todos
los cajeros sin ninguna caja donde abrir turno: CU-30 y CU-31 construidos e
**imposibles de usar**, con la lista vacía y ningún error que lo explique.

## 6. Lo que queda pendiente

- **La pantalla.** Según el reparto del plan, CU-30 y CU-31 son «Mateo (API) ·
  Karen (UI)». En la web, `features/caja/` sigue siendo un archivo de una
  línea.
- **Las devoluciones (CU-32)** hoy suman cero, porque el caso de uso no
  existe. La consulta ya está escrita y se ejecuta igual: cuando la devolución
  exista, el arqueo la cuenta **sin que nadie tenga que acordarse de volver
  acá**.
- **Cerrar un turno olvidado.** Hoy solo puede cerrarlo quien lo abrió. Un
  encargado que necesite cerrar el turno de alguien que se fue necesita otra
  operación, con su propio registro de quién lo hizo y por qué.
