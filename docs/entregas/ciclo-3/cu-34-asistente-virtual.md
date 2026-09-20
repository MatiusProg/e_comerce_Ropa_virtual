# CU-34 · Conversar con el asistente virtual

> **Escrito el 20/09/2026.** Realiza el **RF25** junto con CU-33 y CU-35. Es
> el tercero de los tres casos de uso de P10 y el que el plan dejaba caer
> primero.

---

## 1. La decisión de fondo, por tercera vez

**El modelo no consulta la base: se le consulta.** El servicio arma el
contexto con datos reales —ya filtrados por quien pregunta— y el modelo solo
redacta sobre eso.

Lo natural habría sido darle acceso a la base —herramientas, SQL generado, lo
que sea— y dejarlo buscar. Se descartó por dos razones, y cualquiera de las
dos alcanza:

1. **Un modelo con acceso a la base puede leer lo que no le toca.** La
   pregunta *«¿cuánto gastó Karen el mes pasado?»* tendría respuesta. Acotar
   eso desde el *prompt* es pedirle al modelo que se autolimite, **y eso no es
   un control de acceso.**
2. **Inventa.** Preguntado por una prenda que no existe, un modelo suelto
   describe una plausible. En una tienda eso no es un error de formato: es
   prometer algo que no se puede vender.

Acá el orden es el inverso, y **lo peor que puede hacer el modelo es explicar
mal algo cierto**. Es la misma forma de CU-33 —que ordena candidatas ya
filtradas— y de CU-35 —que elige entre reportes que existen—.

## 2. Qué ve el asistente, exactamente

| Ve | No ve |
|---|---|
| El **catálogo público**: código, nombre, categoría, precio, tallas y si hay stock | Precio base, proveedor, margen |
| **Los pedidos y las reservas de quien pregunta** | Datos de cualquier otro cliente |
| **Sus medidas**, si las cargó (CU-21) | Nada del panel de administración |
| Las sucursales, sus horarios, y la fecha de hoy | |

**El filtro por cliente va en el `WHERE`**, no en la instrucción. Hay una
prueba que lo comprueba: para un cliente sin historial, el contexto llega con
pedidos y reservas vacíos — si apareciera algo, sería de otro.

La fecha de hoy va incluida porque sin ella *«¿cuándo tengo que ir a buscar mi
reserva?»* no se puede contestar.

## 3. Una sola llamada, no dos

La alternativa era clasificar primero la pregunta —«esto es sobre pedidos»— y
recién después buscar. Son **dos viajes al modelo**, y CU-35 ya midió lo que
cuesta cada uno: entre 3 y 25 segundos.

**Cuarenta segundos para contestar «¿cuánto sale la blusa?» no es un
asistente, es una espera.** Se manda todo el contexto de una: más largo en
tokens, mucho más corto en tiempo.

Sesenta prendas son unos 1.500 tokens. Partir el catálogo obligaría a adivinar
de qué va la pregunta antes de leerla — que es justo la ida y vuelta que este
caso de uso evita.

## 4. Lo que devuelve no se cree sin comprobar

El modelo escribe los códigos de prenda entre corchetes: `[#12]`. La pantalla
los convierte en botones.

**Se validan contra el catálogo que se le pasó.** Un código inventado no llega
a la pantalla —hay prueba— y así tocar un botón nunca lleva a una ficha vacía.
Es la misma comprobación que hace CU-35 con el tipo de reporte, y por el mismo
motivo: **lo que el modelo devuelve es una propuesta, no un hecho.**

## 5. Lo que se midió contra Gemini

Seis preguntas encadenadas, con datos reales. Entre 3,0 y 3,7 segundos cada
una salvo la primera:

| Se preguntó | Contestó |
|---|---|
| «¿qué vestidos tienen?» | siete vestidos reales con su precio, enlazados |
| «¿cuánto sale el más barato de esos?» | el correcto, **usando la conversación anterior** |
| «¿ya llegó mi pedido?» | leyó sus pedidos reales y dijo que estaban cancelados, nombrando el código |
| «¿cuál es la capital de Francia?» | *«eso no es sobre la tienda»* |
| «¿tienen zapatos de fútbol Nike?» | *«no vendo zapatos de fútbol»* |

### Dos defectos que salieron de esa medición

**El código escrito con adornos no se reconocía.** Se le pide `[#12]` y a
veces escribe `[*#12*]` para resaltarlo. Con el patrón estricto, esa respuesta
se quedaba **sin prendas enlazables**: el texto nombraba la prenda y la
pantalla no la podía ofrecer. Ahora el patrón tolera lo que meta adentro del
corchete, y hay siete casos cubiertos.

**Generalizaba.** A «¿tienen algo en talla M?» contestó *«tenemos stock en
talla M para **todas** nuestras prendas»* — falso en cuanto una no lo tenga, y
quien lo lea va a venir a buscarla. Se agregó una regla explícita contra
«todas», «siempre» y «cualquiera».

## 6. Sin modelo NO se contesta igual

El recomendador de CU-33 degrada a popularidad, y está bien: una lista
ordenada por ventas sigue sirviendo. **Acá no hay equivalente.**

Un asistente que contesta «no entendí» a todo no es una versión degradada: es
un cartel que engaña. Y contestar con frases armadas sería peor — daría
respuestas que **parecen del sistema y no salen de sus datos**.

Así que el proveedor no disponible **lanza**, y las dos pantallas preguntan
antes de ofrecerlo. Es lo mismo que hace CU-35 con el micrófono.

## 7. El historial lo guarda la pantalla

**No hay tabla de conversaciones**, y es una decisión.

Lo que se ganaría es poder retomar una charla de ayer. Lo que cuesta es una
tabla que crece sin límite con texto libre de un modelo, más la pregunta de
cuánto se guarda y quién lo puede leer — justo en el caso de uso que más cerca
está de los datos personales.

La conversación vive mientras la pantalla está abierta y se reenvía con cada
pregunta. Al cerrarla se pierde, que es lo que espera cualquiera de un chat de
atención.

Se le recuerdan **seis turnos**, no todos: lo que hace falta para entender «¿y
en talla M?» son los dos o tres de antes, y una conversación larga termina
costando más el historial que la pregunta. El contrato acota a diez para que
el cuerpo de la petición no crezca sin límite.

## 8. Quién puede usarlo

**Solo el cliente.** Habla de «tus pedidos» y «tus reservas»; un administrador
tiene usuario pero no perfil de compra, y contestarle sería hablar de nadie.

## 9. Dónde vive

| Archivo | Qué |
|---|---|
| `integrations/asistente/base.py` | el contrato y el porqué |
| `integrations/asistente/gemini.py` | el proveedor, con respaldo entre dos modelos |
| `integrations/asistente/no_disponible.py` | el que lanza |
| `modules/ia/asistente_repository.py` | las consultas, compactas para el prompt |
| `modules/ia/asistente_service.py` | arma el contexto |
| `modules/ia/asistente_router.py` | `POST /asistente` y `GET /asistente/disponible` |
| `tests/test_cu34_asistente.py` | 22 pruebas |

**Sin migración**: no hay tabla nueva.

**Web**: `/tienda/asistente`, con su entrada en la barra del cliente, junto a
«Para vos». **Móvil**: `/asistente`, con su entrada en el inicio. Las dos van
al lado de CU-33 porque son la misma idea desde dos lados — una sugiere sin
que se le pida y la otra contesta lo que se le pregunta.

## 10. Límites conocidos

- **Sesenta prendas.** Si el catálogo creciera mucho habría que elegir cuáles
  entran, y eso reintroduce el paso de clasificación que se evitó.
- **No sabe de promociones.** El catálogo que ve lleva el precio de lista; los
  descuentos de CU-12 no están en el contexto.
- **No puede hacer nada**, solo contestar. No reserva, no agrega al carrito,
  no cancela. Una acción disparada por un modelo necesita una confirmación
  explícita, y eso es otro caso de uso.
- **La conversación no se guarda.** Ver §7.
