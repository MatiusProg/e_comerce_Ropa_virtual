# CU-40 · Notificar eventos a los usuarios

**Realiza el RF11.** Entregado el 28/09/2026. Paquete **P13 · Notificaciones**.

Hasta hoy CU-40 era el único caso de uso del Ciclo 3 que seguía sin construir, y
los diagramas lo dibujaban **vacío a propósito**: `Notificacion` sin columnas y
sus clases sin operaciones, porque inventarle métodos habría hecho que el modelo
mintiera justo donde había que defender que faltaba. Ya no falta.

## Qué hueco cierra, exactamente

El **RF11** dice: *«el sistema deberá notificar las reservas a la sucursal
correspondiente»*. Hasta el refinamiento del Ciclo 2 ese requisito estaba trazado
a **CU-22** y **CU-24**, que es donde la reserva **aparece en la lista** del
Encargado cuando él entra a mirarla.

Eso es **consulta, no notificación**: nada salía a buscar al destinatario. Si el
Encargado no abría la pantalla, no se enteraba. CU-40 es el que lo realiza de
verdad.

## Los cuatro hechos

Los fija la ficha de `docs/03-captura-requisitos.md` §3.1 y no hay un quinto:

| Tipo | Cuándo | A quién | Desde dónde |
|---|---|---|---|
| `RESERVA_EN_SUCURSAL` | se crea una reserva dirigida a un local | Encargado(s) de esa sucursal | `reservas.service.crear_reserva` (CU-22) |
| `RESERVA_PREPARADA` | el Encargado la marca lista | el Cliente que reservó | `reservas.service.preparar_reserva` (CU-24) |
| `PEDIDO_PAGADO` | la pasarela confirma el cobro | el Cliente que compró | `pagos.service._aplicar_cobro` (CU-28) |
| `STOCK_BAJO` | una prenda cruza su punto de reposición | Encargado(s) de esa sucursal | `inventario.service._aplicar_movimiento` (CU-13/15/22/24/28/31) |

La lista está cerrada por un `CHECK` en la base. Un tipo nuevo es una decisión de
alcance, no un valor que alguien pueda inventar desde el código que llama.

## Las tres decisiones que valen la defensa

### 1. El aviso se guarda DENTRO de la transacción; el correo sale FUERA

Son dos exigencias opuestas y por eso se separan.

El **aviso** tiene que nacer **con** el hecho. Si la reserva se crea y después
algo falla y la transacción se deshace, el aviso tiene que deshacerse también.
Por eso las cuatro funciones `avisar_*` **no confirman nada**: se apoyan en el
`commit` de quien las llamó.

El **correo** tiene que salir **después** del `commit`. Mandarlo antes significa
avisarle al Encargado de una reserva que todavía puede no existir — y un correo
no se puede deshacer. Por eso el envío es un paso aparte.

### 2. El aviso en la aplicación es el piso, no el techo

El 13/09 se acordó que si no había proveedor de correo, CU-40 degradaba a *aviso
dentro de la aplicación*. Ahora hay proveedor, y esa degradación pasó a ser **la
base**: el aviso aparece en la campanita **en el mismo instante** en que ocurre
el hecho, y el correo es lo que además sale a buscar a la persona.

La consecuencia práctica es que **un proveedor de correo caído no rompe nada**.
Es la misma lección de CU-41: el proveedor puede estar caído, la dirección puede
ser inválida, la clave puede haber vencido. Nada de eso puede hacer que una venta
falle. El despachador atrapa el fallo por notificación, la marca `FALLIDO` con el
motivo y sigue con la siguiente.

### 3. El stock bajo avisa AL CRUZAR, no cada vez que está bajo

Una prenda en alerta recibe decenas de movimientos mientras sigue baja —se vende
de a una, se reserva, se libera— y avisar en cada uno llenaría la campanita del
Encargado con el mismo aviso repetido hasta volverla inservible.

Mirando el **cruce**, el aviso sale una vez: la que el saldo bajó del umbral.
Vuelve a salir cuando se repone y se cae otra vez, que es justo cuando vuelve a
ser noticia.

    def cruzo_el_umbral(*, antes, ahora, stock_minimo) -> bool:
        if stock_minimo <= 0:
            return False
        return antes > stock_minimo >= ahora

`stock_minimo == 0` significa «sin alerta» —lo fija el modelo de `Existencia`— y
nunca cruza. Sin esa condición, toda existencia que llegue a cero avisaría,
incluidas las que nadie pidió vigilar.

Está aparte del movimiento y es pública **para poder probarla sola**: es una
decisión de tres enteros, y comprobarla montando un producto, una variante, una
sucursal y un ingreso probaría sobre todo el armado.

## El despachador es el mismo arreglo que CU-25

`POST /api/v1/mantenimiento/notificaciones/despacho` está pensado para un
planificador —una tarea de Railway, un cron—, igual que la expiración de reservas
de CU-25, y por las mismas dos razones:

- **Es idempotente.** Solo mira las `PENDIENTE`, y cada una que sale pasa a
  `ENVIADO`. Correrlo dos veces seguidas no manda nada dos veces, que es el único
  error que el usuario nota.
- **Se puede disparar a mano en la defensa** para mostrar el correo llegando. Hay
  un botón en `/avisos` que solo ve el Administrador.

Confirma **una por una** a propósito: si confirmara al final, un fallo a la mitad
dejaría correos ya entregados marcados como pendientes, y la corrida siguiente
los mandaría de nuevo.

El reintento es un paso **aparte** (`/mantenimiento/notificaciones/reintento`).
Si el despachador reintentara solo, un proveedor caído lo dejaría girando sobre
las mismas filas dentro de la misma corrida. Reintentar es una decisión de quien
opera —después de arreglar la clave o el remitente—, no del despachador.

## El proveedor de correo real

`app/integrations/correo/smtp.py`, elegido con `CORREO_PROVEEDOR=smtp`. La
costura ya existía desde CU-41; esto es un módulo hermano de `consola.py` y
**ningún caso de uso cambió**.

### Por qué SMTP si `base.py` prefiere una API HTTP

`base.py` dice, con razón, que un proveedor debería hablar por HTTP: muchas
plataformas de hospedaje bloquean los puertos de correo de salida. Esa sigue
siendo la preferencia. Se eligió SMTP por una razón concreta:

**es el único camino que no depende de dar de alta una cuenta en un servicio de
terceros.** La cuenta de Google ya existe, la contraseña de aplicación se genera
en dos minutos, y desde ahí se le puede escribir a **cualquier dirección**. Los
servicios transaccionales gratuitos, en cambio, o piden verificar un dominio
—que el proyecto no tiene— o solo dejan escribirle a la casilla verificada de la
cuenta, que es justo lo que arruinaría una demostración frente al tribunal.

### El riesgo, escrito para que no sorprenda

**No se verificó si Railway deja salir por el puerto 587.** Si lo bloquea, el
envío falla con un tiempo de espera agotado y el sistema **no se rompe**: el
aviso en la aplicación ya está guardado y la notificación queda `FALLIDO` con el
motivo, visible desde la pantalla. Comprobarlo es disparar el despacho **una vez
en producción** y mirar el resultado.

Si resultara bloqueado, la salida es un módulo hermano que hable HTTP. Es una
entrada más en `_PROVEEDORES` y una variable distinta en Railway.

### Cómo se configura

1. La cuenta de Google necesita la verificación en dos pasos activada.
2. Se genera una **contraseña de aplicación** de 16 caracteres.
3. En Railway:

       CORREO_PROVEEDOR    = smtp
       CORREO_SMTP_USUARIO = la dirección de Gmail
       CORREO_API_KEY      = la contraseña de aplicación, sin espacios
       CORREO_REMITENTE    = la misma dirección de Gmail
       WEB_BASE_URL        = la URL pública de la web

**El remitente tiene que ser la misma cuenta que se autentica.** Gmail reescribe
el `From` al de la cuenta, así que poner `no-responder@violetboutique.bo` —un
dominio que no es de nadie— no lo hace aparecer: lo único que consigue es que el
correo llegue con otro remitente del que dice el código. El módulo avisa por el
log cuando los dos no coinciden.

**`WEB_BASE_URL` apuntando a localhost en producción es un fallo silencioso:** el
correo sale igual y el enlace no le sirve a nadie.

## Endpoints

| Método y ruta | Quién | Qué hace |
|---|---|---|
| `GET /api/v1/notificaciones` | cualquiera con sesión | Los suyos, paginados, con filtro `solo_no_leidas` |
| `GET /api/v1/notificaciones/resumen` | cualquiera con sesión | Cuántos sin leer (la campanita) |
| `POST /api/v1/notificaciones/{id}/leer` | cualquiera con sesión | Marca uno |
| `POST /api/v1/notificaciones/leer-todas` | cualquiera con sesión | Deja la campanita en cero |
| `POST /api/v1/mantenimiento/notificaciones/despacho` | Administrador | Manda los correos pendientes |
| `POST /api/v1/mantenimiento/notificaciones/reintento` | Administrador | Devuelve los fallidos a la cola |

**El router de los avisos no lleva `requiere_roles`, y no es un olvido.** Los
cuatro hechos le llegan a roles distintos —Encargado y Cliente— y exigir un rol
dejaría a la mitad de los destinatarios sin poder leer lo suyo. El ámbito lo pone
el `usuario.id` en el `WHERE`, no el rol.

**No existe `POST /notificaciones`.** El actor de CU-40 es el **Sistema**. Un
endpoint para crear avisos convertiría a cualquier usuario con sesión en el
iniciador del caso de uso, y le permitiría mandarle avisos a otro.

**Un aviso ajeno responde 404 y no 403**, la convención del proyecto: un 403
confirmaría que ese número corresponde a un aviso real de otra persona, y
recorrer números se volvería un censo.

## Datos

Migración **`0021_ciclo3_notificaciones`**, que cuelga de la
`0020_ciclo3_cambio_prenda`. **Una sola tabla**, `notificacion`.

Las tres clases que el 2.3 de CU-40 dibuja **no son tres tablas**:
`GestorNotificaciones` es el servicio y **`CanalDeAviso` es la costura**
`app/integrations/correo`, que existe desde CU-41 y no se persiste — los canales
no se dan de alta desde la aplicación, se eligen con `CORREO_PROVEEDOR`. Una
tabla de dos filas fijas sería un maestro que nadie mantiene.

El estado del correo vive en las mismas columnas y no en una tabla aparte: con un
solo canal además del de la aplicación, una tabla `envio` tendría exactamente una
fila por notificación. Cuando entre un segundo —SMS, push del móvil— ahí sí
corresponde separarla.

Tres restricciones que vale la pena mirar:

- `tipo IN (...)` y `correo_estado IN (...)`, las dos listas cerradas.
- `(correo_estado = 'ENVIADO') = (correo_enviado_en IS NOT NULL)`. Sin esto una
  fila puede decir `PENDIENTE` y traer fecha, y el despachador no sabría a cuál
  creerle.

Y `ondelete=CASCADE`, **al revés que la bitácora**: allá el usuario se pone en
`NULL` porque un asiento sin actor sigue siendo un registro histórico. Un aviso
no: es **para** alguien. Sin destinatario no queda historia, queda una fila que
nadie puede leer y que nadie va a borrar.

`OMITIDO` no es lo mismo que `FALLIDO`: es el aviso que nace sin dirección a la
cual mandarlo. Mezclarlos haría que el reintento persiguiera para siempre correos
que nunca hubo que mandar.

## Pantallas

- **La campanita** (`shared/campanita`) va en las cáscaras del Cliente, del
  Encargado y de la administración. **Abrir el menú no marca nada como leído**:
  leer es una acción de la persona, no un efecto de pasar el mouse.
- **`/avisos`**, una sola pantalla para todos los roles. El contenido es idéntico
  y el ámbito no lo decide la pantalla. Lleva `sesionGuard` y ningún `rolGuard`.
- **El bloque de despacho solo lo ve el Administrador.** Esconderlo no es la
  seguridad —el servidor exige el rol en los dos endpoints—: es no ofrecer un
  botón que va a responder 403.

**El contador vive en el servicio, no en la campanita.** Hay una campanita por
cáscara y tres contadores independientes mostrarían números distintos en la misma
sesión. Es la misma decisión que tomó el carrito en CU-26.

## Los enlaces apuntan al listado y no a la ficha

`/sucursal/reservas` y no `/sucursal/reservas/12`, porque **la web no tiene rutas
de detalle**: ni de reservas, ni de compras, ni de existencias. Inventarlas
dejaría correos con enlaces que caen en «no encontrado», que es peor que un
enlace al listado. El identificador igual viaja en `entidad_id`, así que el día
que esas rutas existan es cambiar una línea.

Se guardan **relativos**: el dominio cambia entre local y Railway, y un enlace
guardado con el de desarrollo no sirve en producción. El correo lo completa con
`WEB_BASE_URL` al momento de enviar.

## Lo que hay que revisar antes de la defensa

1. **Disparar el despacho una vez en producción** y mirar si el 587 sale. Es el
   único supuesto sin verificar de toda la entrega.
2. **Cargar los Encargados de las sucursales.** Una sucursal sin Encargado activo
   no rompe nada —la reserva se crea igual y queda un `WARNING` en el log— pero
   tampoco notifica a nadie. Es un dato maestro, no un defecto.
3. **El `3.3.1` y el `2.3` de CU-40 quedaron viejos**: el modelo de datos ahora
   tiene 44 tablas y `Notificacion` tiene columnas. Hay que regenerarlos.
