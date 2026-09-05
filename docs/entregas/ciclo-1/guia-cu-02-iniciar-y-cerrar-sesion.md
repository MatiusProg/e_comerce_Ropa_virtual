# Guía de implementación — CU-02 Iniciar y cerrar sesión

Para quien tome CU-02, que es el siguiente caso de uso del Ciclo 1. Es el que
desbloquea todo lo demás: sin sesión no hay guardas por rol, y sin guardas no se
puede construir ninguna pantalla de CU-03 en adelante.

El detalle funcional completo —flujo principal, flujo de cierre, alternativos y
excepciones— está en
[`cap-1-captura-requisitos.md`](cap-1-captura-requisitos.md) § CU-02. Esta guía
no lo repite: dice **qué falta en el código** y **con qué criterio darlo por
terminado**.

---

## Antes de empezar

```bash
git checkout main && git pull
git checkout KarenCiclo1 && git merge main
```

En `main` están los modelos, la migración y el esquema ya aplicado en Supabase.
**No hay que tocar `models.py`**: las cinco tablas de P1 ya existen.

---

## 1. Lo primero: `crear_access_token` no emite `jti`

Es la pieza que falta y el resto depende de ella.

En `app/core/security.py`, `crear_access_token()` arma el token con `sub`, `rol`,
`sucursal_id`, `iat`, `exp` y `tipo`, pero **no incluye un `jti`** (identificador
único del token). La tabla `sesion_token` tiene una columna `jti` con
restricción `UNIQUE` que hoy nadie llena.

Sin `jti` no se puede relacionar un token con su fila en `sesion_token`, y por lo
tanto **no se puede revocar**: cerrar sesión no invalidaría nada y el token
seguiría sirviendo hasta expirar solo. Eso rompe la postcondición de CU-02 y la
excepción E2 de CU-03 (desactivar una cuenta debe cortarle el acceso en el acto).

Lo que hace falta:

- Generar un `uuid4()` por token y ponerlo en el *payload* como `jti`.
- Devolverlo junto al token —o dejar que quien llame lo lea del *payload*— para
  poder guardar la fila en `sesion_token`.

---

## 2. Las tres capas

**`schemas.py`** — entrada y salida del caso de uso:

| Esquema | Contenido |
|---|---|
| `LoginIn` | `correo`, `contrasena` |
| `TokenOut` | `access_token`, `token_type` (`"bearer"`), `expira_en`, y los datos básicos del usuario: id, nombres, apellidos, rol y `sucursal_id` cuando aplica |

**`repository.py`** — solo consultas, sin reglas:

- buscar usuario por correo (con su rol cargado)
- crear la fila de `sesion_token`
- buscar una sesión por `jti`
- marcar una sesión como revocada
- revocar todas las sesiones vigentes de un usuario (lo necesita CU-03)

**`service.py`** — aquí viven las reglas del caso de uso:

- `autenticar(correo, contrasena)`: busca el usuario, **verifica que esté
  activo**, verifica el hash con `verify_password`, emite el token y registra la
  sesión con su `jti` y su `expira_en`.
- `cerrar_sesion(jti)`: marca `revocado_en = now()`.

**`router.py`** — dos endpoints bajo el prefijo `/auth` que ya existe:

| Método y ruta | Respuestas |
|---|---|
| `POST /api/v1/auth/login` | 200 con el token · **401** credenciales inválidas · **403** cuenta desactivada |
| `POST /api/v1/auth/logout` | 204 · exige token válido |

---

## 3. La verificación del token, en `dependencies.py`

No alcanza con decodificar el JWT. La dependencia que protege los endpoints
tiene que, además:

1. decodificar el token con `decodificar_token()`;
2. buscar su `jti` en `sesion_token`;
3. **rechazarlo si la sesión está revocada** (`revocado_en` no es nulo);
4. rechazarlo si el usuario fue desactivado.

El paso 3 es la razón de ser de la tabla. Si se omite, `sesion_token` queda como
adorno y el cierre de sesión no cierra nada.

---

## 4. Cuidados que ya están decididos

- **No decir cuál de los dos campos está mal.** Ante credenciales incorrectas el
  mensaje es uno solo, sin precisar si falló el correo o la contraseña
  (excepción E1). Decirlo permite averiguar qué correos están registrados.
- **Cuenta desactivada es 403, no 401.** Son situaciones distintas: una es "no
  te reconozco", la otra "te reconozco y no podés entrar" (excepción E2).
- **El token lleva `sucursal_id`.** Para Encargado y Cajero es lo que acota su
  ámbito de datos a su propia sucursal; para Cliente y Administrador va nulo.
- **La expiración sale de la configuración**, no escrita a mano:
  `settings.ACCESS_TOKEN_EXPIRE_MINUTES`.

---

## 5. En la web

- `auth.service.ts` ya existe con el registro: agregarle `login()` y `logout()`,
  y guardar el token.
- Una **guarda de ruta** que lea el rol del token y redirija al inicio de sesión
  cuando falta o expiró, **conservando la ruta destino** para volver a ella
  después de autenticarse (flujo alternativo 6a).
- Un **interceptor HTTP** que agregue `Authorization: Bearer <token>` a cada
  petición, y que ante un 401 descarte el token y redirija al login.

La pantalla de login ya está esbozada en
`frontend-web/src/app/features/auth/login/`.

---

## 6. Criterio para darlo por terminado

Sobre el **sistema desplegado**, no en local:

1. Iniciar sesión con `admin@violetboutique.bo` devuelve 200 y un token.
2. Ese token abre un endpoint protegido.
3. Una contraseña incorrecta devuelve 401, sin decir qué campo falló.
4. Cerrar sesión devuelve 204 y **el mismo token deja de servir** — éste es el
   que prueba que la revocación funciona de verdad.
5. En la web: iniciar sesión redirige al área del rol, recargar la página
   mantiene la sesión, y cerrar sesión vuelve al login.

El punto 4 es el que distingue una implementación completa de una a medias.

---

## 7. Qué queda para después

`SesionToken` es el objeto del **diagrama de estado del Ciclo 1** (sección 3.2):
*vigente → expirado / revocado*. Cuando CU-02 esté implementado conviene
contrastar el diagrama con el código y corregir el que se haya desviado; hoy el
diagrama va por delante.
