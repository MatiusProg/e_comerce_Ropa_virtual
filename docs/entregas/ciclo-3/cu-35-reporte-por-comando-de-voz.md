# CU-35 · Generar reporte por comando de voz

> **Escrita el 20/09/2026.** Aporta al **RF25** junto con CU-33. Reutiliza
> entero CU-37: no hay ni una consulta de reportes nueva.

---

## 1. Dónde se reconoce la voz, y por qué importa

**En el cliente, no en el servidor.** El navegador trae Web Speech API y el
teléfono trae el motor del sistema; los dos son gratuitos, no consumen cuota
del modelo y no suben audio a ningún lado.

Al backend le llega **texto**. Transcribir en el servidor obligaría a un
servicio de pago y a subir megabytes por cada pedido — para obtener
exactamente la misma cadena.

## 2. Qué hace el servidor

Traduce la frase a **una elección entre opciones que ya existen**: cuál de los
seis reportes, con qué período, en qué formato y con qué filtros.

No genera nada nuevo. Es la misma decisión que en el recomendador de CU-33 —el
modelo elige entre candidatas, nunca produce el contenido— y por el mismo
motivo: **lo peor que puede hacer entonces es elegir mal**, no prometer algo
que el sistema no tiene.

Todo lo que devuelve se valida contra el catálogo: un tipo que no existe, un
formato inventado o un filtro con un valor que ese reporte no admite se
descartan.

```
POST /api/v1/reportes/voz          {"texto": "las ventas de este mes en excel"}
GET  /api/v1/reportes/voz/disponible
```

### No devuelve el archivo: devuelve qué entendió

Y la URL para bajarlo. Así la pantalla muestra *«Entendí: ventas de
septiembre, en Excel»* y recién entonces se descarga.

Entregar el archivo directo ahorraría un toque y quitaría **la única
oportunidad de notar que interpretó otra cosa**. Un reporte equivocado no se
nota hasta abrirlo, y para entonces ya se mandó por correo.

### Cuando no entiende, pide que lo repita

Con ejemplos de frases que sí funcionan. **Nunca se descarga «lo más
parecido».** Y los ejemplos viven junto a los reportes, no en la pantalla:
dependen de qué reportes existen.

## 3. Lo que se midió contra el servicio real

Seis frases, todas acertadas, entre 2,8 y 8,3 segundos:

| Lo que se dice | Lo que arma |
|---|---|
| «los movimientos de ingreso de la semana pasada» | `movimientos.xlsx?desde=…&hasta=…&tipo=INGRESO` |
| «las reservas canceladas de septiembre en pdf» | `reservas.pdf?…&estado=CANCELADA` |
| «cuánto vendimos en efectivo en agosto» | `ventas.xlsx?…&metodo_pago=EFECTIVO` |
| «hazme un pastel de chocolate» | no entendí |

**La fecha de hoy va en la instrucción.** Sin ella «este mes» no significa
nada y el modelo inventa un año.

### El arreglo que lo destrabó

En la primera medición **fallaban 3 de 7**, todas por tiempo agotado a los
30 s. La causa no era la lentitud: **un timeout no disparaba el modelo de
reserva**, porque solo lo hacían el 429 y el 503. El modelo liviano —que
contesta en 2 segundos— nunca llegaba a probarse.

Cortando a 22 s por modelo y tratando el timeout como saturación, pasó de 4/7
a 7/7.

## 4. Las dos pantallas

**Web** (`/admin/reportes`): el micrófono aparece arriba de la lista, y **solo
si el navegador y el servidor pueden**. Chrome y Edge sí; Firefox no. La lista
de reportes sigue funcionando igual — la voz es un atajo, no el único camino.

**Móvil** (`/reportes/voz`): mismo flujo. Cuando no se puede, **se dice cuál
de las dos mitades falta**: si es el permiso del micrófono se arregla en el
teléfono, y si es el servidor no hay nada que hacer desde ahí. «No disponible»
a secas no le sirve a nadie.

En los dos, el resultado parcial se muestra mientras se habla: sin eso, hablar
contra una pantalla quieta se siente roto y la gente vuelve a tocar, cortando
su propio dictado.

### Lo que hizo falta en Android

`RECORD_AUDIO`, y —lo que no es obvio— declarar el `<queries>` del
`RecognitionService`. Desde Android 11 hay que decir a qué otras aplicaciones
se les va a preguntar: sin eso `speech_to_text` **informa que no está
disponible aunque el motor esté instalado**, y el síntoma no señala la causa
por ningún lado.

## 5. Los filtros que salen de la base

Sucursal, proveedor y temporada no tienen valores fijos en el código: son
filas. Al modelo se le pasa el par **`id` → nombre**, porque lo que se dice es
«proveedor Shein» y lo que la consulta necesita es `proveedor_id=7`.

Se resuelven **en cada pedido**, así que el intérprete sigue al negocio solo:
una sucursal que abrió ayer se puede pedir hoy hablando, y una que cerró deja
de ofrecerse sin que nadie toque el código. Solo van las **activas** — ofrecer
un proveedor dado de baja sería aceptar un filtro que después no devuelve
nada.

### El error que esto corrige

Al probarlo el 20/09 se pidió *«reporte por proveedor de sucursal centro,
proveedor shein en pdf»* y **bajó las compras de todos los proveedores, sin
avisar**.

La causa era una condición de más al armar el catálogo: se salteaban los
filtros sin opciones escritas en el código. A la sucursal se la salteaba a
propósito —razonando que nadie dice «sucursal 3»—, y proveedor y temporada
caían de arrastre por venir con la tupla vacía.

El razonamiento estaba mal planteado: nadie dice «sucursal 3», pero todos
dicen «la sucursal Centro». Lo que faltaba no era ocultar el filtro, era dar
la correspondencia.

**Un filtro dicho y no aplicado es peor que uno no ofrecido**: el archivo sale
sin decir que no filtró y el número se lee como si lo estuviera.

Al encargado la sucursal se le sigue sin ofrecer, pero por otro motivo: se le
fuerza la suya, y aceptársela hablando sería prometerle una elección que
después se ignora en silencio.

## 6. Límites conocidos

- **Chrome manda el audio a Google** para transcribirlo. Es la implementación
  del navegador, no una decisión de esta aplicación, pero conviene saberlo.
  Acá solo se dictan nombres de reportes.
- **Las temporadas se ofrecen todas, incluidas las cerradas.** A diferencia
  de sucursal y proveedor, una temporada pasada es justo lo que se quiere
  pedir: «el rendimiento de la temporada de invierno» se dice en marzo.
- **En el móvil el archivo se guarda, no se abre.** En un teléfono sin lector
  de Excel, abrirlo solo termina en «no hay ninguna aplicación», que se lee
  como que la descarga falló.
