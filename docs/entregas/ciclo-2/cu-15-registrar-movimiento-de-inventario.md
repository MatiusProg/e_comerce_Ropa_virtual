# CU-15 · Registrar movimiento de inventario

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)). Un archivo por
> caso de uso, por el mismo motivo que explica
> [`cu-10-gestionar-productos-y-variantes.md`](cu-10-gestionar-productos-y-variantes.md).

| Campo | Contenido |
|---|---|
| **Código** | CU-15 |
| **Nombre** | Registrar movimiento de inventario |
| **Descripción** | Permite registrar ajustes por conteo físico y transferencias de mercadería entre sucursales, dejando trazabilidad del motivo, el usuario y la fecha. |
| **Propósito** | Cerrar la brecha entre lo que el sistema dice que hay y lo que hay de verdad, y repartir el stock entre locales, **sin** que ninguna cantidad cambie sin dejar el movimiento que la explica. |
| **Actores** | Administrador (iniciador). El ajuste lo comparte con el Encargado por **CU-16**, acotado a su sucursal |
| **Paquete** | P4 · Inventario |
| **Prioridad** | Media |
| **Requisitos que realiza** | RF22, RF28 |
| **Precondiciones** | El Administrador tiene sesión iniciada. Para transferir, existe saldo disponible de esa prenda en la sucursal de origen. |
| **Postcondiciones** | La cantidad disponible queda corregida y por cada cambio existe un `movimiento_inventario` con su tipo, su cantidad con signo, su motivo, su usuario y su fecha. Una transferencia deja **dos** movimientos. |

**Flujo principal — ajuste por conteo físico**

1. El Administrador ingresa a *Inventario* y ve las existencias con su cantidad disponible, reservada y física.
2. El Administrador elige ajustar una existencia.
3. El sistema muestra los tres saldos y pide las **unidades contadas** en el local, reservadas incluidas, más el motivo.
4. El Administrador escribe lo que contó y el sistema muestra en vivo la diferencia que se va a registrar.
5. El Administrador confirma.
6. El sistema calcula la diferencia contra el total físico, la aplica a la cantidad disponible y registra un movimiento de tipo `AJUSTE` con esa diferencia con signo.

**Flujos alternativos**

- **3a. Transferencia entre sucursales.** El Administrador elige una prenda con saldo, una sucursal de destino, la cantidad y el motivo. El sistema descuenta del origen, suma al destino y registra **dos** movimientos de tipo `TRANSFERENCIA`: uno negativo y otro positivo.
- **1a. Consultar el historial.** El Administrador filtra los movimientos por sucursal y por tipo, y ve qué se movió, cuánto, por qué, quién y cuándo. El Encargado también puede leerlo, acotado a su sucursal.
- **6a. Prenda no registrada en esa sucursal.** Si apareció mercadería que el sistema no tenía, se crea su existencia en cero y el ajuste la sube.

**Excepciones**

- **E5. Origen y destino iguales.** No se transfiere una sucursal a sí misma.
- **E6. Stock insuficiente.** No se transfiere más de lo disponible en el origen. El mensaje dice cuánto hay.
- **E7. Conteo sin diferencia.** Si lo contado coincide con lo registrado no se genera movimiento, y el sistema lo dice como confirmación y no como error.
- **E8. Conteo menor que lo reservado.** Si hay 4 unidades apartadas para reservas y el conteo dice 3, el ajuste dejaría una reserva sin respaldo físico. Se frena y se pide cancelar la reserva primero (CU-23).
- **Prenda que nunca estuvo en el origen.** Se distingue de E6: una es «no alcanzan», la otra «nunca estuvo acá».

---

## Lo que no se lee en la ficha

**Lo que se cuenta es el total físico, no lo disponible.** Es la regla más importante de este caso de
uso y la más fácil de equivocar. Quien recorre la percha cuenta prendas, y una prenda apartada para
una reserva **sigue estando en la percha**. Si el ajuste comparara lo contado contra la cantidad
disponible, cada reserva viva parecería un faltante y el ajuste «corregiría» un descuadre que no
existe — robándole las unidades a la reserva. Por eso se compara contra `disponible + reservada`, y
por eso la pantalla muestra los tres números y dice explícitamente cuál hay que igualar.

La diferencia, en cambio, se aplica **solo a la cantidad disponible**: lo reservado lo mueven CU-22,
CU-23 y CU-25, y este caso de uso no los pisa.

**Se envía lo contado, no la diferencia.** Nadie cuenta «menos tres camisas»: cuenta «hay
diecisiete». La resta la hace el servidor, que es quien sabe cuál era el saldo en ese instante — si
la mandara la interfaz, dos personas ajustando a la vez calcularían su diferencia contra el mismo
saldo viejo.

**Una transferencia son dos filas, no una.** Una salida negativa en el origen y una entrada positiva
en el destino, las dos de tipo `TRANSFERENCIA`, con el mismo motivo, el mismo usuario y el mismo
instante. Es lo que hace que el saldo de cada sucursal se pueda reconstruir mirando **solo sus
propios movimientos**, que es la promesa de la decisión **D4**. Una sola fila con dos sucursales
obligaría a que cada consulta de saldo supiera interpretar el signo según de qué lado se la mire.

**Los dos bloqueos se toman en orden ascendente de sucursal.** Si cada transferencia bloqueara
«primero el origen, después el destino», dos transferencias cruzadas —de la 1 a la 2 y de la 2 a la
1, a la vez— tomarían los mismos dos bloqueos en orden inverso y se esperarían mutuamente:
un interbloqueo. PostgreSQL lo detecta y mata a una, pero la que muere es una transferencia legítima
que alguien tuvo que volver a cargar. Ordenar por identificador lo vuelve imposible.

**El signo va en la cantidad y no se deduce del tipo.** Hay dos tipos que van en las dos
direcciones: un `AJUSTE` por conteo puede sumar o restar, y una `TRANSFERENCIA` es salida en un local
y entrada en otro. Con el signo en la cantidad, la afirmación de **D4** —el saldo de una existencia
es la **suma** de sus movimientos— se vuelve literal y verificable, y hay una prueba que la comprueba.

**Solo tres de los siete tipos se cargan a mano.** `RESERVA`, `LIBERACION`, `VENTA` y `DEVOLUCION`
las genera el sistema desde CU-22, CU-23, CU-25 y las ventas del Ciclo 3. Ofrecerlas en el selector
dejaría descuadrar un saldo contra la reserva o la venta que lo justifica. El selector se pide al
servidor en vez de escribirlo en la interfaz, por el mismo motivo que los cargos de CU-06.

**La transferencia es solo del Administrador; el ajuste, no.** *(Corregido el 11/09 al implementar
CU-16.)* Esta ficha decía que el Encargado no ajustaba, leyendo solo la fila de CU-15 de la §2.2 del
acuerdo. Estaba incompleto: **CU-16 es ese mismo ajuste visto desde el Encargado** —«consultar y
**ajustar** la disponibilidad de las prendas de su propia sucursal»—, y es justamente por eso que
CU-15 figura como de Administrador: la mitad del Encargado tiene caso de uso propio.

Así que `POST /inventario/movimientos/ajuste` vive en el *router* de operación, que admite los dos
roles, con `verificar_ambito_sucursal` adentro. **Un endpoint con dos alcances, no dos endpoints**:
duplicarlo expondría el mismo recurso en dos rutas —lo que la §6.11.2 decidió no hacer— y dejaría
dos copias de la regla del conteo físico esperando a divergir.

La **transferencia** sí se queda solo con el Administrador: cruza dos sucursales y el Encargado
responde por una sola. Como son dos ámbitos de rol distintos sobre el mismo paquete, hay **dos
routers** y la exigencia se declara una vez en cada uno — la regla de la §6.11.4 de
`docs/06-decisiones-tecnicas.md`: bajarla al nivel de cada endpoint reintroduce el agujero de
olvidarla en uno solo.

## Endpoints

| Método | Ruta | Paso | Rol |
|---|---|---|---|
| `POST` | `/inventario/movimientos/ajuste` | 3-6 · conteo físico | Administrador y Encargado (CU-16) |
| `POST` | `/inventario/movimientos/transferencia` | 3a · traslado | Administrador |
| `GET` | `/inventario/movimientos` | 1a · historial con filtros, paginado | Administrador y Encargado |
| `GET` | `/inventario/tipos-movimiento` | selector del formulario | Administrador y Encargado |

## Pantallas

| Plataforma | Ruta | Rol |
|---|---|---|
| Web | `/admin/inventario` | Administrador |
| Web | `/sucursal/inventario` | Encargado — historial e ingresos, sin transferencia |
| Web | `/sucursal/disponibilidad` | Encargado — el ajuste de su sucursal, que es **CU-16** |
| Móvil | — | El actor no es Cliente: es solo web (§2.2 del acuerdo) |

## Pruebas

`backend/tests/test_cu15_movimientos.py` — 16 pruebas. Las que cubren lo que la base **no** garantiza
por sí sola:

- `test_el_conteo_se_compara_contra_el_total_fisico_no_contra_el_disponible` — la prueba más
  importante del caso de uso. Con 10 unidades y 4 reservadas, un conteo de 10 no genera movimiento;
  si se comparara contra el disponible, inventaría cuatro prendas.
- `test_excepcion_e8_el_conteo_no_puede_ser_menor_que_lo_reservado` — y que al rechazarlo no toque
  nada.
- `test_la_transferencia_deja_dos_movimientos_y_mueve_los_dos_saldos` — incluida la comprobación de
  que cada sucursal reconstruye su saldo con sus propias filas.
- `test_el_encargado_no_transfiere_entre_sucursales` — pero sí ajusta lo suyo (CU-16) y sí lee el
  historial.

## Costura C1 — lo que este paquete le debe a Karen

Junto con estos dos casos de uso quedan expuestas las dos funciones que CU-19 y CU-14 consumen, con
las firmas acordadas en la §6 del documento de organización, en
`backend/app/modules/inventario/service.py`:

```python
disponibilidad_por_sucursal(db, variante_id)   # CU-19
inventario_consolidado(db, sucursal_id=..., producto_id=..., solo_con_saldo=...)  # CU-14 y CU-16
```

Devuelven esquemas de este paquete y no filas de SQLAlchemy: si devolvieran `Row`, el contrato sería
la forma de una consulta y cambiarla de este lado rompería la pantalla del otro sin que nada avisara.
El *stub* contra el que Karen estaba maquetando ya se puede reemplazar por la función real.
