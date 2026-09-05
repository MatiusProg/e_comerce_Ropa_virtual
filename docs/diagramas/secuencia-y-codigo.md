# Diagramas de secuencia (3.2) y su correspondencia con el código

Este documento explica **cómo se lee un diagrama de secuencia de Violet Boutique contra el
código real**, y **de dónde sale cada fragmento de interacción** (`alt`, `loop`, `critical`,
`opt`, `break`, …).

Sirve para dos cosas: para defender los diagramas mostrando la línea de código de la que
sale cada mensaje, y para que cuando el código cambie se sepa qué diagrama hay que tocar.

Los diagramas están en `docs/diagramas/VioletBoutique.eapx`, paquete
`CAP. 3 - Flujo de Trabajo: Diseño > 3.2 Diagramas de Secuencia`, y los genera
`scripts/ea-secuencia-3-2.ps1`.

---

## 1. Las líneas de vida: qué archivo es cada una

Cada línea de vida está **enlazada por `ClassifierID`** a su clase del capítulo 2.3, así que
EA la rotula `: NombreDeClase` y el vínculo es real, no texto suelto. Y cada clase de 2.3
corresponde a un lugar concreto del repositorio:

| Línea de vida | Estereotipo en 2.3 | Dónde vive en el código |
|---|---|---|
| `: Formulario…` / `: Pantalla…` | `frontera` | `frontend-web/src/app/features/…` + su `core/services/*.service.ts`, y el `router.py` del módulo |
| `: Gestor…` | `controlador` | `backend/app/modules/<módulo>/service.py` |
| `: GestorAutenticacion` | `controlador` | `backend/app/core/dependencies.py` y `backend/app/core/security.py` |
| `: Usuario`, `: Cliente`, `: Sucursal`, … | `entidad` | la tabla en `models.py` y las funciones de `repository.py` que la consultan |

El **actor** es el mismo elemento del CAP. 1, no una copia: si se renombra allá, se renombra
en los nueve diagramas.

---

## 2. Los mensajes: cómo se escribe cada tipo

| Tramo | Qué se escribe en el mensaje | Ejemplo |
|---|---|---|
| Actor → frontera | la acción del usuario en la pantalla | `1.1: enviarCredenciales(correo, contrasena)` |
| Frontera → controlador | la función real de `service.py`, con su firma | `1.2: autenticar(db, datos)` |
| Controlador → controlador | la función auxiliar o privada | `1.5: verify_password(contrasena, hash_contrasena)` |
| Controlador → entidad | **el SQL literal** que emite `repository.py` | `1.7: INSERT INTO usuario (correo, hash_contrasena, rol_id)` |
| Entidad → controlador | **el tipo del resultado**, marcado como retorno | `1.7.1: Usuario (id)` |
| Controlador → frontera (error) | el nombre del error y su código HTTP | `4.1: correoYaRegistrado() -> 409` |

Los mensajes de vuelta se marcan como **`Return`** en EA, por eso se dibujan con línea
punteada. El código HTTP sale de la función `_traducir` del router correspondiente
(por ejemplo `backend/app/modules/seguridad/router.py:159`).

### La numeración

Se hereda **tal cual** del diagrama de comunicación 2.2 del mismo caso de uso: `1.1`, `1.2`,
… para el flujo básico, `2.x` y `3.x` para los alternos, `4.x` para los errores. Así el mismo
mensaje se sigue en los dos capítulos.

Los **retornos** que el 2.2 no tiene se numeran como sub-nivel del mensaje que los provoca
(`1.7` → `1.7.1`), para no desplazar la numeración original.

---

## 3. Los fragmentos de interacción: el catálogo

Un fragmento combinado marca en el diagrama lo que en el código es una **estructura de
control**. Esta es la correspondencia completa:

| Operador UML | Construcción en el código | Cuándo corresponde |
|---|---|---|
| **`alt`** | `if / elif / else`; varios `raise` excluyentes; ramas de un `except` | dos o más caminos mutuamente excluyentes, cada uno con su guarda |
| **`opt`** | `if` **sin** `else` | un tramo que puede ejecutarse o no; equivale a un `alt` de un solo operando |
| **`loop`** | `for`, `while`, una comprensión, o una consulta recursiva que itera en la base | repetición de un tramo |
| **`break`** | `raise` o `return` temprano que **abandona** el resto de la interacción | salida anticipada; lo que sigue no se ejecuta |
| **`critical`** | bloque transaccional `try: … db.commit() / except: db.rollback()` | región que no admite interrupción ni intercalado |
| **`par`** | `asyncio.gather`, hilos, tareas concurrentes | dos tramos que corren en paralelo |
| **`ref`** | una llamada a otra interacción ya diagramada | reutilizar un caso de uso dentro de otro |
| **`seq` / `strict`** | orden débil / orden estricto entre líneas de vida | rara vez necesario |
| **`neg`** | — | documentar un escenario **prohibido** |
| **`assert`** | una invariante que debe cumplirse | la única continuación válida |
| **`ignore` / `consider`** | — | decir qué mensajes se omiten o se tienen en cuenta |

> **Regla práctica:** el fragmento se dibuja alrededor de los mensajes afectados, y la guarda
> del operando se escribe **en español, entre corchetes**, con la misma condición que evalúa
> el `if` del código.

---

## 4. Dónde está cada fragmento en Violet Boutique

### 4.1 Los `alt` que están dibujados

Los nueve diagramas suman **12 fragmentos `alt`**. Cada uno sale de una decisión real:

| Diagrama | Operandos | Sale de |
|---|---|---|
| CU-01 | `datos válidos` / `correo o documento ya registrado` | `seguridad/service.py:89` |
| CU-02 | `credenciales válidas y cuenta activa` / `credenciales inválidas` / `cuenta desactivada` | `seguridad/service.py:192` y `:195` |
| CU-03 (1) | `correo libre y rol existente` / `correo ya registrado` | `seguridad/service.py:371` |
| CU-03 (2) | `no es su propia cuenta` / `intenta desactivarse a sí mismo` | `seguridad/service.py:517` |
| CU-04 | `contraseña actual correcta` / `contraseña actual incorrecta` | `seguridad/service.py` → `cambiar_contrasena` |
| CU-05 (1) | `nombre libre en la ciudad` / `nombre duplicado en la ciudad` | `organizacion/service.py` → `crear_sucursal` |
| CU-05 (2) | `la ciudad no tiene sucursales` / `la ciudad tiene sucursales activas` | `organizacion/service.py:156` → `eliminar_ciudad` |
| CU-06 | `vincula un usuario existente` / `crea una cuenta nueva` | `organizacion/empleados/service.py:180` y `:193` |
| CU-07 | `identificación tributaria libre` / `identificación duplicada` | `organizacion/proveedores_service.py:127` |
| CU-08 (1) | `nombre libre entre hermanas y sin ciclo` / `el padre elegido es descendiente` | `catalogo/maestros/service.py:181` |
| CU-08 (2) | `sin subcategorías` / `tiene subcategorías` | `catalogo/maestros/service.py:235` |
| CU-09 | `nombre libre y sin solapamiento` / `fechas incoherentes` / `se cruza con otra temporada activa` | `catalogo/temporadas_service.py:133` y `:146` |

El caso más claro es **CU-06**. El código es literalmente el fragmento:

```python
# backend/app/modules/organizacion/empleados/service.py:180
if datos.usuario_id is not None:          # operando 1: vincula un usuario existente
    usuario = repository.obtener_usuario_vinculable(db, datos.usuario_id)
    usuario.rol_id = rol.id
    repositorio_seguridad.revocar_sesiones_de_usuario(db, usuario.id)
else:                                     # operando 2: crea una cuenta nueva
    usuario = repository.agregar_usuario(db, correo=..., rol_id=rol.id)
```

### 4.2 Los `critical` que **no** están dibujados

Cada alta y cada baja del sistema ocurre dentro de una transacción. En UML eso es un
fragmento **`critical`** que envuelve desde el primer `INSERT`/`UPDATE` hasta el retorno:

```python
try:
    repository.agregar_usuario(...)
    repository.agregar_empleado(...)
    db.commit()          # <- fin del critical
except IntegrityError as exc:
    db.rollback()        # <- lo que el critical protege
    raise CorreoYaRegistrado(...) from exc
```

Están en:

| Módulo | Líneas del bloque transaccional |
|---|---|
| `seguridad/service.py` | `:120` (registrar cliente), `:211` (autenticar), `:257` (cerrar sesión), `:402` (crear usuario), `:462` (editar usuario), `:497` (cambiar estado), `:525` (eliminar usuario), `:649` (agregar dirección), `:699` (marcar predeterminada) |
| `organizacion/empleados/service.py` | `:215` (crear empleado), `:302` (editar), `:341` (dar de baja) |
| `catalogo/maestros/service.py` | los `try/commit` de cada `crear_*` y `editar_*` |
| `catalogo/temporadas_service.py` | ídem |

En los diagramas esto se representó como el mensaje `revertirTransaccion()` sobre la propia
línea del gestor (CU-01 `2.2`, CU-06 `3.2`), que es lo que hace el 2.2 correspondiente. Si se
quiere el fragmento `critical` explícito, va alrededor de los `INSERT`/`UPDATE` del operando
de éxito.

### 4.3 Los `opt` que **no** están dibujados

Son los `if` sin `else`. En los diagramas se resolvieron escribiendo **la guarda dentro del
nombre del mensaje** (`2.1a: [si queda predeterminada] UPDATE …`), que se lee igual y no
agrega una caja más:

| Dónde | Código | En qué diagrama |
|---|---|---|
| Crear usuario con rol que exige sucursal | `seguridad/service.py:393` — `if exige_empleado:` crea también la ficha de empleado | CU-03 |
| Primera dirección de un cliente | `seguridad/service.py:688` — `if predeterminada:` desmarca la anterior | CU-04, mensaje `2.1a` |
| Temporada que no queda activa | `temporadas_service.py:146` — `if datos.activa:` solo entonces comprueba solapamiento | CU-09 |

### 4.4 Los `loop` que **no** están dibujados

| Dónde | Código | Qué itera |
|---|---|---|
| Armar el árbol de categorías | `catalogo/maestros/service.py:94` y `:98` — dos `for` sobre la lista plana | una pasada por categoría |
| Buscar descendientes de una categoría | `catalogo/maestros/repository.py:73` — CTE `recursive=True` | la **base de datos** itera la jerarquía; en el diagrama es el mensaje `1.6: WITH RECURSIVE descendientes AS (…)` de CU-08 |
| Convertir las direcciones a salida | `seguridad/service.py:577` — comprensión sobre las filas | una por dirección |

El de la CTE recursiva es el más interesante para la defensa: **el bucle no está en Python,
está en el motor**. Por eso el mensaje al `: Categoria` lleva el SQL recursivo literal.

### 4.5 Los `break`

`raise` tempranos que abandonan el caso de uso sin llegar al `commit`:

| Dónde | Código |
|---|---|
| Nadie puede desactivarse a sí mismo | `seguridad/service.py:517` |
| Usuario con operaciones asociadas no se borra | `seguridad/service.py:520` |
| Documento de empleado ya registrado | `organizacion/empleados/service.py:172` |

En los diagramas cada uno es el segundo operando de un `alt`, que es equivalente y más
legible que un `break` suelto.

### 4.6 Los que este proyecto no usa

- **`par`**: el backend es **síncrono**. Los endpoints son `def`, no `async def`, y
  SQLAlchemy usa `Session` bloqueante. No hay nada concurrente que dibujar. Si en el Ciclo 3
  la integración con la IA o la pasarela de pago se hace en paralelo, ahí sí correspondería.
- **`ref`**: candidato claro para el Ciclo 2. Los siete casos de uso de administración
  arrancan con `1.3: requiere_roles("ADMINISTRADOR")`, que es exactamente la validación de
  token de CU-02. En vez de repetirla, se podría poner un `ref` al diagrama de CU-02.
- **`neg`**, **`assert`**, **`ignore`**, **`consider`**, **`seq`**, **`strict`**: no se usan;
  ninguno aporta al nivel de detalle que pide el examen.

---

## 5. Cómo cambiar el operador de un fragmento en EA

El script solo genera fragmentos **`alt`**, porque es el único operador cuyo código interno
está verificado contra el archivo de cátedra (`t_object.NType = 0`). Para convertir uno en
`loop`, `opt` o `critical`:

1. Doble clic sobre el fragmento en el diagrama.
2. En el cuadro de propiedades, desplegable **Interaction Operator**.
3. Elegir el operador. Si tiene guarda, se escribe en el operando.

Los operandos (las bandas con la guarda) se agregan con clic derecho sobre el fragmento →
**Combined Fragment → Add Operand**.

---

## 6. Dos cosas que hay que saber de EA

### 6.1 EA remaqueta el diagrama cada vez que lo abre

No respeta las alturas que uno escriba por script: **reordena los mensajes por `SeqNo`** y
los reparte con su propio paso —35 px arrancando en −135—, dejando un hueco extra en cada
borde de fragmento. Lo que sí conserva es la caja del fragmento combinado.

La consecuencia es traicionera: si los mensajes se escriben con otra escala, al abrir el
diagrama se comprimen, la caja se queda donde estaba y **el `alt` termina envolviendo
mensajes que no son**. Por eso `scripts/ea-secuencia-3-2.ps1` usa exactamente la escala de
EA, y por eso conviene **verificar la cobertura de cada operando después de abrir el modelo**.

### 6.2 Los operandos no se pueden crear por la API COM

El operador del fragmento y sus operandos viven en `t_object.NType` y en una fila
`Partitions` de `t_xref`, con este formato:

```
@PAR;Name=<guarda>;Size=<alto en px>;GUID={…};@ENDPAR;@PAR;…@ENDPAR;
```

**La suma de los `Size` tiene que ser exactamente el alto de la caja**, o EA reparte mal las
bandas. El script los escribe por OLEDB en una segunda pasada, después de cerrar EA.

---

## 7. Cómo se regenera

```powershell
# aditivo: solo crea los diagramas que faltan
powershell -ExecutionPolicy Bypass -File scripts\ea-secuencia-3-2.ps1

# borra el paquete 3.2 entero y lo rehace
powershell -ExecutionPolicy Bypass -File scripts\ea-secuencia-3-2.ps1 -Rehacer
```

**Enterprise Architect tiene que estar cerrado.** El script abre el modelo por COM y después
escribe directo sobre el `.eapx`; con EA abierto, su copia en memoria pisa lo escrito.

El guion de cada caso de uso está al principio del script, en la variable `$CASOS`: una lista
de líneas de vida y una lista de pasos (`nota`, `msg`, `alt`, `op`, `fin`) que se lee de
arriba hacia abajo y es el orden vertical del diagrama. Agregar un mensaje es agregar una
línea ahí.
