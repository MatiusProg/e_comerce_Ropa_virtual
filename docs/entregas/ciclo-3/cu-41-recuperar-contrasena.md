# CU-41 · Recuperar contraseña

> Ficha del caso de uso, en el mismo formato que las del Ciclo 1
> ([`ciclo-1/cap-1-captura-requisitos.md`](../ciclo-1/cap-1-captura-requisitos.md)).

| Campo | Contenido |
|---|---|
| **Código** | CU-41 |
| **Nombre** | Recuperar contraseña |
| **Descripción** | Permite a cualquier usuario recuperar el acceso a su cuenta mediante un enlace de un solo uso enviado a su correo, sin intervención del Administrador. |
| **Propósito** | Que olvidar la contraseña no deje a nadie fuera del sistema ni obligue al Administrador a elegir una contraseña que entonces conocería. |
| **Actores** | Usuario sin sesión (iniciador) · Servicio de correo (secundario) |
| **Paquete** | P1 · Seguridad y Usuarios |
| **Prioridad** | Media |
| **Requisitos que realiza** | **RF39** |
| **Precondiciones** | Ninguna. Es el único caso de uso del sistema, junto con CU-01, CU-02 y la vitrina, que no exige sesión. |
| **Postcondiciones** | La contraseña de la cuenta quedó reemplazada y todas sus sesiones abiertas, revocadas. |

**Flujo principal**

1. El Usuario abre *¿Olvidaste tu contraseña?* desde la pantalla de inicio de sesión.
2. El Usuario escribe el correo de su cuenta y confirma.
3. El sistema invalida los enlaces pendientes de esa cuenta y emite uno nuevo, de un solo uso.
4. El sistema envía el enlace al correo del Usuario.
5. El sistema informa que, **si el correo corresponde a una cuenta**, el enlace fue enviado.
6. El Usuario abre el enlace y escribe la contraseña nueva dos veces.
7. El sistema canjea el enlace, que deja de servir.
8. El sistema reemplaza la contraseña y revoca todas las sesiones abiertas de la cuenta.
9. El sistema confirma y ofrece iniciar sesión.

**Flujos alternativos**

- **2a. El correo no corresponde a ninguna cuenta.** El sistema **responde exactamente lo mismo** y no envía nada. Ver más abajo.
- **2b. La cuenta está desactivada.** Tampoco se envía enlace, y tampoco se dice.
- **2c. El Usuario pide el enlace de nuevo.** El anterior deja de servir en el acto; vale el último.
- **6a. La contraseña no cumple las reglas, o las dos no coinciden.** El sistema lo señala y **el enlace no se gasta**.

**Excepciones**

- **E1. El enlace no es válido, ya se usó o venció.** El sistema lo rechaza y ofrece pedir uno nuevo. Las **tres** situaciones se responden igual, por el mismo motivo que en CU-02.
- **E2. La cuenta se desactivó después de pedir el enlace.** El sistema lo rechaza indicando que contacte al Administrador, y **deshace el canje**: el enlace queda sin usar.

---

## Lo que no se lee en la ficha

**Todo este caso de uso gira alrededor de una sola idea: el enlace ES la credencial de la cuenta
mientras vive.** Quien lo tenga puede cambiar la contraseña sin saber la anterior. De ahí salen
cuatro decisiones, y ninguna es un extra:

| Decisión | Dónde vive | Qué pasaría sin ella |
|---|---|---|
| Se guarda el **SHA-256** del token, nunca el token | modelo `TokenRecuperacion` | Una lectura de la tabla entregaría el acceso a todas las cuentas con un enlace pendiente |
| Vale **una sola vez**, y lo decide la base | `canjear_token_de_recuperacion` | Los enlaces quedan en el historial del correo y servirían cada vez que alguien los abriera |
| Vale **poco tiempo** — 30 minutos | `RECUPERACION_VIGENCIA_MINUTOS` | Un correo abierto en una máquina compartida sería una llave permanente |
| Canjearlo **revoca todas las sesiones** | `confirmar_recuperacion` | Quien recupera una cuenta que le tomaron no recuperaría el control: el intruso seguiría adentro hasta que su token venciera solo |

**La respuesta es idéntica exista o no la cuenta, y eso no es un descuido de diseño: es el diseño.**
El endpoint es público y sin token. Si distinguiera «te enviamos el enlace» de «ese correo no
existe», sería una forma de averiguar qué direcciones están registradas en la tienda, probándolas de
a una y sin límite. Es exactamente la misma decisión que ya se había tomado en CU-02, donde correo
inexistente y contraseña incorrecta comparten un único mensaje. Por eso el acuse dice «**si** el
correo corresponde a una cuenta», en condicional, y por eso el esquema de salida tiene un solo
campo: para que no pueda volverse distinto por descuido en una de las dos ramas.

**El de un solo uso lo resuelve la base, no el servicio.** La comprobación y la marca viajan en la
misma sentencia: `UPDATE ... WHERE hash_token = ? AND usado_en IS NULL AND expira_en > ? RETURNING
usuario_id`. Si en cambio se leyera la fila, se decidiera en Python y después se escribiera, dos
peticiones simultáneas con el mismo token pasarían las dos la comprobación antes de que ninguna
escribiera, y las dos cambiarían la contraseña. Con la condición dentro del `UPDATE`, la segunda no
encuentra fila que actualizar y el `RETURNING` vuelve vacío.

**SHA-256 y no bcrypt, que es lo que usan las contraseñas.** Son dos problemas distintos. Una
contraseña es una palabra que alguien puede adivinar, y bcrypt encarece el cálculo para frenar los
diccionarios; el token son 32 bytes aleatorios y no hay diccionario posible. Además el hash tiene
que poder **buscarse por igualdad**, que es justo lo que bcrypt —con su sal por fila— no permite.

**El token llega por la URL y se devuelve por el cuerpo.** Por la URL no hay alternativa: es un
enlace. Pero mandarlo de vuelta en la cadena de consulta lo escribiría en el registro de accesos del
servidor, además del historial del navegador donde ya está. Va por `POST`.

**El correo sale después del `commit`, no antes.** Al revés, una transacción que fallara dejaría
circulando un enlace que no existe en la base.

**E2 deshace el canje.** Si la cuenta se dio de baja entre que se pidió el enlace y que se abrió, no
tiene sentido quemarlo: una baja puede revertirse, y el enlace todavía no sirvió para nada.

**La contraseña nueva cumple las mismas reglas que el registro.** Recuperar el acceso no puede ser
una puerta de atrás para poner una clave más débil de la que CU-01 habría aceptado.

## La costura de correo

**CU-41 es el primer caso de uso del sistema que manda un correo**, así que estrena
`app/integrations/correo/`. Pero cuando se escribió, el proyecto **no tenía servicio de correo
contratado** y dos casos de uso lo estrenaban: éste y el CU-40 de Mateo.

Lo decidido el 13/09 fue **la costura primero y el proveedor después**: un contrato mínimo
(`Mensaje` + `enviar`) y un proveedor `consola` que en vez de enviar escribe el correo entero en el
*log*. Con eso CU-41 se construye y se prueba completo —token, dos endpoints, dos pantallas— sin
proveedor, y elegirlo pasa a ser agregar un módulo hermano y cambiar **una** variable en Railway.

```
CORREO_PROVEEDOR   consola | (el que se elija)
CORREO_API_KEY
CORREO_REMITENTE
CORREO_REMITENTE_NOMBRE
```

**Los nombres no llevan la marca adentro.** Es la lección que ya había dejado la IA: se acordó que
las variables fueran `IA_PROVEEDOR`/`IA_API_KEY`/`IA_MODELO` y se implementó atada a una marca, de
modo que cambiar de proveedor obligaba a tocar el despliegue además del código. *(Esa inconsistencia
se corrigió en `config.py` junto con este caso de uso.)*

**Dos cosas ya sabidas para cuando se elija proveedor:**

- **API HTTP, no SMTP.** Muchas plataformas bloquean los puertos de correo de salida y eso se
  descubre tarde; no se verificó si Railway lo hace. Un `POST` no corre ese riesgo: el contenedor ya
  sale a internet para Supabase.
- **La trampa es el remitente.** Los servicios transaccionales no dejan enviar desde cualquier
  dirección: o se verifica un dominio propio —no lo tenemos— o se usa el dominio de prueba del
  proveedor, que en varios **solo permite enviar a la casilla verificada de la cuenta**. Si en la
  defensa se piensa mandar un correo a alguien del tribunal, hay que averiguarlo antes.

**Un `CORREO_PROVEEDOR` desconocido no degrada en silencio a `consola`: falla.** Degradar sería peor
que fallar — el sistema parecería mandar correos que nadie recibe, y acá eso deja usuarios sin poder
entrar sin que nada avise. Y el proveedor `consola` corriendo en producción escribe un `WARNING`,
porque el cuerpo que vuelca al *log* lleva el enlace adentro.

## Endpoints

| Método | Ruta | Paso | Respuesta |
|---|---|---|---|
| `POST` | `/auth/recuperacion` | 2-5 | `202` siempre |
| `POST` | `/auth/recuperacion/confirmar` | 6-9 | `204` · `400` E1 · `403` E2 |

Los dos son **públicos**, y van en el mismo router que `/registro` y `/login` por el mismo motivo
que ellos: el actor de CU-41 es alguien que justamente no puede iniciar sesión. Exigir token sería
pedirle lo único que no tiene.

**`202` y no `200`**: la solicitud se aceptó. Que el correo llegue depende del proveedor y de la
casilla del destinatario, y esa respuesta no lo afirma.

**`400` y no `404` en E1**: un `404` confirmaría que ese enlace nunca existió, que es justamente lo
que el caso de uso evita.

## Datos

Tabla **`token_recuperacion`**, migración `0008_ciclo3_recuperacion`.

```
token_recuperacion   id             BIGSERIAL  PK
                     usuario_id     BIGINT     FK usuario.id ON DELETE CASCADE
                     hash_token     VARCHAR(64)  UNIQUE   -- SHA-256 hexadecimal
                     solicitado_en  TIMESTAMPTZ  default now()
                     expira_en      TIMESTAMPTZ
                     usado_en       TIMESTAMPTZ  NULL
                     CHECK (expira_en > solicitado_en)
                     indice parcial (usuario_id) WHERE usado_en IS NULL
```

**Una tabla y no dos columnas en `usuario`.** El hash del token y su vencimiento como columnas
alcanzarían para el flujo principal y fallarían en todo lo demás: no habría historia de quién pidió
recuperar ni cuándo, no se podría caducar un enlace sin escribir sobre la fila del usuario, y cada
petición ensuciaría una tabla que se lee en **cada** autenticación. Es el mismo razonamiento por el
que `sesion_token` existe: credenciales de vida corta con su propio ciclo de vida.

**El índice es parcial.** La única consulta que filtra por `usuario_id` es la que invalida los
pendientes; los canjeados solo se conservan. Así el índice no crece con la historia.

**Invalidar marca `usado_en`, no borra la fila.** La tabla conserva quién pidió recuperar y cuándo,
que es lo único que queda si después hay que entender un acceso raro.

### Sobre el número de la migración — leer antes de escribir la `0006`

Los identificadores se reservaron en la §4 de
[`ciclo-2/04-respuesta-de-karen.md`](../ciclo-2/04-respuesta-de-karen.md): `0006_ciclo3_ventas` y
`0007_ciclo3_promociones` son de Mateo, y de ahí en adelante de Karen. Por eso ésta es la `0008`.

**Pero reservar el nombre no ordena la cadena.** Alembic no mira el número del archivo: mira
`down_revision`. Al 15/09 la `0006` y la `0007` no estaban escritas y la cabeza seguía siendo la
`0005`, así que ésta cuelga de la `0005` — apuntar a una revisión inexistente rompe el comando
entero.

> **Consecuencia para Mateo:** la cabeza ya no es la `0005` sino la `0008`. Su
> `0006_ciclo3_ventas` tiene que declarar `down_revision = "0008_ciclo3_recuperacion"`. La cadena
> queda `0005 → 0008 → 0006 → 0007`, que se lee raro y es correcta: el número del archivo es un
> nombre, el orden es la cadena. Dos revisiones con el mismo `down_revision` dejarían el árbol con
> dos cabezas y `alembic upgrade head` fallaría pidiendo cuál.

Verificada como manda la §: aplicada contra la base de pruebas, `alembic check` sin operaciones
pendientes para esta tabla, y `downgrade` probado —no solo el `upgrade`—.

## Pantallas

| Plataforma | Ruta | Archivo |
|---|---|---|
| Web · pedir el enlace | `/olvide-contrasena` | `frontend-web/src/app/features/auth/olvide/` |
| Web · contraseña nueva | `/recuperar/:token` | `frontend-web/src/app/features/auth/restablecer/` |

El camino `/recuperar/:token` lo arma el *backend* al enviar el correo, como
`${WEB_BASE_URL}/recuperar/{token}`. **Si cambia en un lado, cambia en el otro.**

Se agregó además el enlace *¿Olvidaste tu contraseña?* en la pantalla de inicio de sesión — sin eso,
las dos pantallas existirían y nadie podría llegar a ellas, que es la lección que dejó el CU-16 al
cierre del Ciclo 2.

**`WEB_BASE_URL` apuntando a `localhost` en producción es un fallo silencioso**: el correo sale
igual y el enlace no le sirve a nadie.

**Sin pantalla móvil.** La app puede abrir la web para esto; una pantalla propia exigiría además un
esquema de enlace profundo para que el correo la abra, que es más de lo que el caso de uso pide.

## Lo que esto deja preparado

La costura de correo queda escrita y probada, así que **CU-40 (notificaciones, de Mateo) ya no está
bloqueado por el proveedor**: puede construirse contra `enviar` y quedar funcionando con `consola`.
Su degradación acordada —aviso dentro de la aplicación, sin correo— pasa de ser el plan a ser el
respaldo.
