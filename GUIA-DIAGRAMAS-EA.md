# Cómo generar los diagramas UML de Enterprise Architect por automatización

**Guía completa y autocontenida.** Está escrita para que otra sesión de Claude —o cualquier
persona, en este proyecto o en otro— pueda reproducir los **catorce tipos de diagrama** que se
generaron para Violet Boutique sin volver a averiguar nada de lo que costó averiguar.

No es un resumen: es el manual. Todo lo que dice está verificado contra Enterprise Architect 15
Trial en Windows, escribiendo sobre archivos `.eapx` reales.

> **Contexto de origen.** Proyecto *Violet Boutique* (antes *FashionStore*), materia SI2,
> Examen 1, semestre 2-2026. Modelo único en `docs/diagramas/VioletBoutique.eapx`, generadores en
> `scripts/ea-*.ps1`. Nada de lo que sigue depende de ese proyecto en particular salvo los ejemplos.

---

## Índice

1. [Qué hace falta antes de empezar](#1-qué-hace-falta-antes-de-empezar)
2. [La forma de la solución: dos pasadas](#2-la-forma-de-la-solución-dos-pasadas)
3. [Las diez reglas de oro](#3-las-diez-reglas-de-oro)
4. [Plantilla de un generador](#4-plantilla-de-un-generador)
5. [Recetario de la API COM](#5-recetario-de-la-api-com)
6. [Recetario de la segunda pasada (OLEDB)](#6-recetario-de-la-segunda-pasada-oledb)
7. [Receta por diagrama](#7-receta-por-diagrama)
   - [7.1 Casos de uso 1.3.2 y 1.5](#71-casos-de-uso-132-y-15)
   - [7.2 Análisis de arquitectura 2.1.1 / 2.1.2 / 2.1.3](#72-análisis-de-arquitectura-211--212--213)
   - [7.3 Comunicación 2.2](#73-comunicación-22)
   - [7.4 Clases de análisis 2.3](#74-clases-de-análisis-23)
   - [7.5 Análisis de paquetes 2.4](#75-análisis-de-paquetes-24)
   - [7.6 Capas 3.1.1](#76-capas-311)
   - [7.7 Despliegue 3.1.2](#77-despliegue-312)
   - [7.8 Secuencia 3.2](#78-secuencia-32)
   - [7.9 Modelo de dominio 3.3.1](#79-modelo-de-dominio-331)
   - [7.10 Componentes del sistema 4.2](#710-componentes-del-sistema-42)
   - [7.11 Componentes por subsistema 4.3](#711-componentes-por-subsistema-43)
   - [7.12 Estado 3.2](#712-estado-32)
   - [7.13 Navegación 3.2](#713-navegación-32)
   - [7.14 Tiempo 3.2](#714-tiempo-32)
8. [Exportar a PNG](#8-exportar-a-png)
9. [Catálogo de errores: síntoma → causa → arreglo](#9-catálogo-de-errores-síntoma--causa--arreglo)
10. [Lo que no se puede automatizar](#10-lo-que-no-se-puede-automatizar)
11. [Checklist de verificación](#11-checklist-de-verificación)
12. [Cómo llevar esto a otro proyecto](#12-cómo-llevar-esto-a-otro-proyecto)

---

## 1. Qué hace falta antes de empezar

| Requisito | Detalle |
|---|---|
| **Enterprise Architect** | Versión 15 (sirve la Trial). Instalado, con su servidor COM registrado. |
| **Plantilla vacía** | `C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.eapx`. Es el modelo en blanco que se copia para crear uno nuevo. En una instalación con licencia la ruta es `...\Sparx Systems\EA\EABase.eapx`. |
| **Proveedor OLEDB** | `Microsoft.ACE.OLEDB.16.0`. Un `.eapx` **es una base de Access renombrada**; la segunda pasada la abre directo. Viene con Office de 64 bits o con el *Access Database Engine* redistribuible. |
| **PowerShell** | El de Windows (`powershell.exe`, 5.1) alcanza. La arquitectura de PowerShell (32/64 bits) tiene que coincidir con la de EA y con la del proveedor ACE. |
| **EA cerrado** | **Innegociable.** Si EA está abierto, su copia en memoria pisa lo que escriba el script y se pierde todo el trabajo, sin error. |

Ejecución típica:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\ea-secuencia-3-2.ps1
powershell -ExecutionPolicy Bypass -File scripts\ea-secuencia-3-2.ps1 -Rehacer
```

> **`ea-cu-ciclo1.ps1` es la excepción: no es aditivo.** Crea el modelo desde la plantilla
> vacía, o sea que **borra el `.eapx` existente con todos los diagramas de los cuatro
> capítulos**. Por eso exige `-Recrear`; sin ese modificador se niega a correr. Los otros diez
> generadores esperan que el modelo ya exista.

---

## 2. La forma de la solución: dos pasadas

Cada generador tiene la misma estructura, y la razón es que **la API COM de EA no expone todo**.

```
PARTE 1 — API COM  (EA.Repository)
    crear paquetes, elementos, atributos, operaciones, conectores,
    diagramas y la posición de cada objeto en el lienzo
        ↓
    $ea.CloseFile(); $ea.Exit(); ReleaseComObject; GC; Start-Sleep 1500ms
        ↓
PARTE 2 — OLEDB directo sobre el .eapx
    lo que la API no deja tocar: color de fondo, orden Z, ParentID,
    multiplicidad, geometría de los mensajes de secuencia, tipo de
    mensaje, operandos de un fragmento combinado, estereotipos
    conflictivos
```

**El `Start-Sleep` no es supersticioso.** Sin él, EA todavía tiene el archivo abierto y el
`OleDbConnection.Open()` falla o —peor— escribe sobre un archivo que EA vuelve a guardar después.
1500 ms alcanza; menos es apostar.

Hay una excepción cómoda: con el repositorio **abierto por COM** se puede ejecutar SQL de
modificación sin cerrar nada, con `$ea.Execute("UPDATE ...")`. Sirve para retoques puntuales
(por ejemplo `PDATA4` de los mensajes de comunicación). Para escrituras masivas o para tablas que
EA cachea, la segunda pasada por OLEDB es más segura.

---

## 3. Las diez reglas de oro

### 1. Los generadores son **aditivos**

Abren el modelo existente y **solo agregan lo que falta**. Un diagrama que ya existe no se toca.

```powershell
if (BuscarDiagrama $paquete $nombre) { Write-Output "  $nombre ya existe, no se toca"; continue }
```

Por qué: apenas hay un diagrama acomodado a mano, un generador que rehaga el archivo borra ese
trabajo. Siendo aditivos, se pueden correr las veces que haga falta. Para rehacer algo a propósito
está el modificador `-Rehacer`, que borra ese paquete y lo vuelve a generar.

### 2. Un diagrama y los elementos que muestra viven en el **mismo paquete**

Si no, EA rotula cada elemento con `(from OtroPaquete)` debajo del nombre y el dibujo se ensucia.
Es opción de visualización, pero se arrastra en cada exportación.

### 3. EA dibuja **toda** relación que exista entre los elementos presentes en el lienzo

Si dos clases se comparten entre casos de uso, el diagrama de CU-06 muestra también los mensajes de
CU-02. No se borra nada del modelo: se **oculta por diagrama**.

```powershell
$d.DiagramLinks.Refresh()
foreach ($lnk in $d.DiagramLinks) {
    $con = $ea.GetConnectorByID($lnk.ConnectorID)
    if (-not $esMio) { $lnk.IsHidden = $true; [void]$lnk.Update() }
}
```

### 4. El orden Z viene **sin definir** y hay que fijarlo

`DiagramObject.Sequence` arranca en 999999. **Número más bajo = se dibuja más al frente.**
Un `Package` es un rectángulo relleno: sin tocar la secuencia tapa a los elementos que contiene y
se ve una caja vacía con líneas entrando a la nada.

```powershell
# contenedores al fondo, contenido adelante
foreach ($o in $dia.DiagramObjects) {
    $el = $ea.GetElementByID($o.ElementID)
    if ($el.Type -eq 'Package') { $o.Sequence = 100 } else { $o.Sequence = $i; $i++ }
    [void]$o.Update()
}
```

> **Trampa:** `$dia.DiagramObjects` conserva la copia que tenía **al crearse el diagrama** —vacía—.
> Sin un `$dia.DiagramObjects.Refresh()` antes, el bucle no encuentra nada que ordenar, **no da
> error**, y los paquetes quedan tapando a sus hijos.

### 5. Borrar un diagrama **no** borra sus conectores

Regenerar sin deduplicar dejó **471 conectores de mensaje duplicados** en el modelo. Todo
`New-*` de conector busca primero si ya existe uno entre el mismo par, del mismo tipo y con el
mismo nombre.

```powershell
function New-Asociacion($src, $dst, $rol, $cardOrigen, $cardDestino) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq $rol) { return }
    }
    ...
}
```

### 6. `Package.Elements` **no devuelve los elementos de tipo `Package`**

La API los esconde. Un «buscar-o-crear» que recorra `Elements` **nunca** encuentra un paquete ya
creado y lo vuelve a crear en cada pasada. Así fue como los once paquetes del 2.1 terminaron
**triplicados**, y cada diagrama apuntando a una copia distinta.

La lectura que no miente es SQL:

```powershell
$yaEstan = @{}
$xml = $ea.SQLQuery("SELECT o.Object_ID AS id, o.Name AS nombre, o.Object_Type AS tipo
                     FROM t_object o WHERE o.Package_ID=$($pkg.PackageID)")
if ($xml) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.LoadXml($xml)
    foreach ($fila in $doc.SelectNodes('//Row')) { $yaEstan["$($fila.tipo)|$($fila.nombre)"] = [int]$fila.id }
}
```

`SQLQuery` devuelve **XML**, no filas. Se parsea con `XmlDocument` y `//Row`.

### 7. PowerShell **no distingue mayúsculas** en los nombres de variable

`$a` y `$A` son la misma variable. Un `foreach ($a in ...)` pisa el mapa `$A` de actores y el
script falla mucho más adelante, con un error que no menciona nada de esto. **Los mapas nunca se
llaman con una sola letra**, y la variable de un bucle nunca se llama como un mapa vivo.

### 8. Las **notas del elemento no se ven** en el PNG exportado

Lo que se lee en el dibujo es un elemento de tipo `Note` puesto en el lienzo. Si la explicación
tiene que salir en la entrega, va como `Note`, no como `Element.Notes`. (Se pueden poner las dos:
`Notes` para quien abra el modelo, `Note` para quien lea el PDF.)

Para atarla a un elemento: conector `NoteLink`.

### 9. Los acentos por **parámetro**, nunca interpolados en el SQL

Concatenando, el proveedor ACE manda la cadena en la codificación ANSI del sistema y los acentos
llegan rotos.

```powershell
$ins.CommandText = "UPDATE t_xref SET Description = ? WHERE Client = '$guid'"
[void]$ins.Parameters.AddWithValue('d', $textoConAcentos)
```

### 10. El nombre de un elemento es el **nombre exacto** de lo que representa en el código

**Regla del 15/09/2026, para todo lo que se genere de acá en adelante.** Un elemento con nombre de
prosa obliga a traducir mentalmente en la defensa, y esa traducción no está escrita en ningún lado.
Si el diagrama dice `FormularioRegistro` y el archivo se llama `registro.html`, nadie puede
comprobar que uno corresponda al otro.

| Estereotipo | Qué nombre lleva | Por qué |
|---|---|---|
| **frontera** | el **archivo** de la vista, tal cual: `registro.html`, `usuarios.ts` | hay uno por pantalla, así que el archivo identifica sin ambigüedad |
| **control** | el **nombre exacto de la función**: `registrar_cliente`, `cambiar_estado` | el archivo **no** sirve: todos los módulos tienen su `service.py` y se llamarían igual |
| **entidad** | el **nombre exacto de la tabla**: `usuario`, `sesion_token`, `direccion_cliente` | minúsculas y guion bajo, como en la base; sin traducir a PascalCase |

**Cuando el control es una clase con varias operaciones** —el caso del diagrama de navegación 3.2—
el nombre de la clase es el **archivo del módulo** (`catalogo/maestros/router.py`) y **cada
operación es el nombre exacto de su función** (`listar_categorias`, `cambiar_estado_talla`). Ahí el
archivo sí identifica, porque se nombra completo con su ruta.

Consecuencia que hay que aceptar: **si dos áreas comparten un archivo, comparten el elemento.**
Ciudades y sucursales son las dos `organizacion/router.py`, así que en el diagrama son **una sola
caja** con las operaciones de las dos. Es incómodo de dibujar y es verdad; la caja separada era la
mentira.

En Angular la vista son dos archivos (`usuarios.ts` y `usuarios.html`). **Se nombra con el `.ts`**,
que es el que importa `app.routes.ts` y donde vive la clase, y el `.html` va en la nota.

> **Lo que ya está hecho no se renombra** —decisión de Mateo del 15/09—, así que en el modelo
> conviven los nombres viejos (`FormularioRegistro`, `GestorRegistro`, `Usuario`) con los nuevos.
> Si algún día se quisiera unificar, **renombrar en EA es barato**: los diagramas referencian los
> elementos por `Object_ID`, así que un renombre se propaga solo a todos los diagramas donde
> aparezca, sin regenerar ninguno.

---

## 4. Plantilla de un generador

Copiar esto y llenarlo. Es el esqueleto exacto que usan los once scripts.

```powershell
param(
    # Borra el paquete de este capítulo y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# <CAPÍTULO> - <NÚMERO> <NOMBRE DEL DIAGRAMA>
#
# ---- DE DÓNDE SALE ESTE FORMATO ----
#   (el ejemplo de cátedra, la referencia, la norma que se sigue)
#
# ---- EN QUÉ SE APARTA DEL EJEMPLO, Y POR QUÉ ----
#   1. ...
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\ruta\al\Modelo.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '<nombre exacto del diagrama>'

# ---- Constantes de dibujo (todas juntas, arriba) ----
$X0 = 40; $Y0 = -60; $ANCHO = 300; $ALTO = 70; $PASO = 90

# ---- Los datos: qué se dibuja. Tablas declarativas, no código. ----
$DATOS = @( ... )

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarPaquete($p, $n) {
    foreach ($s in $p.Packages) { if ($s.Name -eq $n) { return $s }; $r = BuscarPaquete $s $n; if ($r) { return $r } }
    return $null
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
    return $do
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaquete $root 'Violet Boutique'
$pCap  = Get-OCrearPaquete $pRaiz 'CAP. N - ...'

if ($Rehacer) {
    for ($i = $pCap.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap.Packages.GetAt($i).Name -eq '<paquete>') {
            $pCap.Packages.DeleteAt($i, $false)
            Write-Output '  paquete anterior eliminado (-Rehacer)'
        }
    }
    $pCap.Packages.Refresh()
}

$pkg = Get-OCrearPaquete $pCap '<paquete>'

if (BuscarDiagrama $pkg $NOMBRE_DIA) {
    Write-Output "  $NOMBRE_DIA ya existe, no se toca"
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    exit 0
}

$dia = $pkg.Diagrams.AddNew($NOMBRE_DIA, '<TipoDeDiagrama>')
[void]$dia.Update(); $pkg.Diagrams.Refresh()

#   ... crear elementos, ponerlos, conectarlos ...

$pkg.Elements.Refresh()
$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $($dia.DiagramLinks.Count) relaciones"

# Guardar los IDs que la PARTE 2 va a necesitar ANTES de cerrar.
$didCom = $dia.DiagramID

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Lo que la API COM no deja hacer
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql)   { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }
function Scalar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteScalar() }

#   ... UPDATEs ...

$cn.Close()
Write-Output 'OK'
```

**Cada script imprime al final cuántos objetos y cuántas relaciones dejó.** Es la única forma
barata de darse cuenta de que algo se duplicó o de que faltó un conector.

---

## 5. Recetario de la API COM

### 5.1 Abrir y cerrar

```powershell
$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }
$root = $ea.Models.GetAt(0)          # el paquete "Model", raíz de todo

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
```

### 5.2 Crear un modelo desde cero

```powershell
$base = 'C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.eapx'
if (Test-Path $modelo) { Remove-Item $modelo -Force }
Copy-Item $base $modelo
```

### 5.3 Paquetes

```powershell
$p = $padre.Packages.AddNew('Nombre', 'Package'); [void]$p.Update(); $padre.Packages.Refresh()
$padre.Packages.DeleteAt($i, $false)      # borrar (el $false es "no refrescar")
```

### 5.4 Elementos

```powershell
$e = $pkg.Elements.AddNew('Nombre', 'Class')
$e.Stereotype   = 'entidad'
$e.StereotypeEx = 'entidad'      # SIEMPRE los dos, ver 5.9
$e.Notes        = 'Descripción para quien abra el modelo.'
$e.Abstract     = '1'            # actor abstracto, clase abstracta
$e.ExtensionPoints = 'Tras crear la cuenta'   # solo UseCase
[void]$e.Update(); $pkg.Elements.Refresh()
```

Tipos usados en este proyecto: `Actor`, `UseCase`, `Package`, `Class`, `Component`, `Object`,
`Artifact`, `Device`, `ExecutionEnvironment`, `Node`, `Note`, `Sequence` (línea de vida),
`InteractionFragment`.

### 5.5 Poner un elemento en el lienzo

```powershell
$do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
$do.ElementID = $el.ElementID
[void]$do.Update()
```

**Sistema de coordenadas, que es lo que más confunde:**

- `l` (left) y `r` (right) son positivos y crecen **hacia la derecha**. `r = l + ancho`.
- `t` (top) y `b` (bottom) son **negativos** y **crecen hacia abajo**: `t = -40` está arriba,
  `t = -900` está mucho más abajo. `b = t - alto`.
- O sea: **más negativo = más abajo**. Un `$y -= 90` en un bucle baja una fila.

### 5.6 Conectores

```powershell
$c = $src.Connectors.AddNew('nombre', 'Association')
$c.SupplierID = $dst.ElementID
$c.Stereotype = 'trace'
$c.Direction  = 'Source -> Destination'
[void]$c.Update()
$c.ClientEnd.Cardinality   = '1'
$c.SupplierEnd.Cardinality = '0..*'
[void]$c.ClientEnd.Update(); [void]$c.SupplierEnd.Update(); [void]$c.Update()
$src.Connectors.Refresh()
```

El conector **sale de `$src`** (`Client`) y **llega a `$dst`** (`Supplier`). Los `Update()` de los
extremos van **después** del primer `Update()` del conector: antes, el conector todavía no existe
y las cardinalidades se pierden en silencio.

Tipos por caso:

| Quiero dibujar | Tipo de conector | Estereotipo |
|---|---|---|
| Actor ↔ caso de uso | `Association` | — |
| Herencia de actores | `Generalization` | — |
| `include` / `extend` | `Dependency` | `include` / `extend` |
| Traza paquete → caso de uso | `Abstraction` | `trace` |
| Dependencia entre paquetes | `Dependency` | sin estereotipo · `Direction = 'Source -> Destination'` · ver §7.5 |
| Relación entre clases | `Association` (**siempre**) | — |
| Enlace de comunicación | `Association` | — |
| Mensaje de comunicación | `Collaboration` | — |
| Mensaje de secuencia | `Sequence` | — |
| Capa realiza capa | `Realisation` | `realiza` |
| Ensamblado componente↔componente | `Assembly` | — |
| Nodo ↔ nodo | `CommunicationPath` | — |
| Artefacto → nodo | `Deployment` | `deploy` |
| Artefacto → componente | `Manifest` | `manifest` |
| Nota → elemento | `NoteLink` | — |

> Un conector `Sequence` en un diagrama de comunicación **se crea sin error y no dibuja nada**.
> Y al revés: un `Collaboration` en un diagrama de secuencia tampoco.

### 5.7 Atributos y operaciones

```powershell
$at = $el.Attributes.AddNew('correo', 'VARCHAR(120)')
$at.Type       = 'VARCHAR(120)'
$at.Visibility = 'Private'
$at.Pos        = 0                 # el orden de arriba hacia abajo
$at.Stereotype = 'PK'              # «PK» / «FK» en el modelo de datos
[void]$at.Update()
$el.Attributes.Refresh()

$m = $el.Methods.AddNew('crear_temporada', 'TemporadaOut')   # (nombre, tipo de retorno)
$m.Visibility = 'Public'           # 'Private' si empieza con _
$m.Pos = 0
[void]$m.Update()
$pa = $m.Parameters.AddNew('db', 'Session'); $pa.Position = 0; [void]$pa.Update()
$m.Parameters.Refresh()
$el.Methods.Refresh()
```

> **`Pos` no garantiza el orden visible.** Si en las preferencias de EA está activa *ordenar
> características alfabéticamente*, los muestra alfabéticos igual. Se desactiva a mano; no hay
> forma de forzarlo por script.

### 5.8 Ocultar una relación en un diagrama

```powershell
$d.DiagramLinks.Refresh()
foreach ($lnk in $d.DiagramLinks) {
    $con = $ea.GetConnectorByID($lnk.ConnectorID)
    if ($con.Stereotype -ne 'trace') { $lnk.IsHidden = $true; [void]$lnk.Update() }
}
$d.DiagramLinks.Refresh()
$visibles = ($d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
```

### 5.9 Estereotipos: `Stereotype` **y** `StereotypeEx`

EA guarda dos cosas: el texto del estereotipo (`t_object.Stereotype`) y la **aplicación del perfil**
(una fila `Stereotypes` en `t_xref`, que es lo que lee y escribe `StereotypeEx`).

Si se cambia solo `Stereotype`, el elemento queda con `StereotypeEx = "entidad,entity"`: **el viejo
sigue activo por debajo** y el ícono no desaparece. Hay que asignar los dos.

```powershell
$e.Stereotype = 'entidad'; $e.StereotypeEx = 'entidad'
```

**Los estereotipos de robustez son un caso aparte.** EA dibuja el **ícono redondo** solo para los
estereotipos que se llaman exactamente `boundary`, `control` y `entity`. Con cualquier otro nombre
—`frontera`, `controlador`, `entidad`— dibuja la clase como **tabla**, con atributos y operaciones.

**No hay forma de desactivar el ícono por diagrama.** Se probaron `StereoIcon`, `UseStereoIcon`,
`ShowIcon`, `UCRect`, `SPT`, `NoIcon`, `ShapeScript` e `IsIcon` en `DiagramObject.Style`, y ninguna
surte efecto.

Como el diagrama de comunicación necesita el formato redondo y el de clases el de tabla, y un mismo
elemento no puede verse de las dos maneras, **la solución es tener dos juegos de elementos con el
mismo nombre en paquetes distintos**: los de comunicación con los estereotipos en inglés, los de
clases con los estereotipos en español. El lector ve `Usuario` en los dos capítulos; el modelo tiene
dos elementos.

**El estereotipo `form` es otro caso especial.** EA trae uno propio llamado `form` y, al asignarlo
por la API, lo empareja **sin distinguir mayúsculas**: guarda `form` en minúscula y encima le cuelga
la aplicación del perfil. `CLASS` y `TABLA` no chocan con nada y quedan bien. Se arregla en la
segunda pasada; ver [6.5](#65-desligar-un-estereotipo-del-perfil-el-caso-form).

### 5.10 SQL con el repositorio abierto

```powershell
$ea.Execute("UPDATE t_connector SET PDATA4='1.3' WHERE Connector_ID=$id")   # escribe
$xml = $ea.SQLQuery("SELECT Object_ID AS id FROM t_object WHERE Package_ID=$pid")  # lee, devuelve XML
```

---

## 6. Recetario de la segunda pasada (OLEDB)

```powershell
$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql)   { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }
function Scalar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteScalar() }
```

Las tablas que interesan:

| Tabla | Para qué |
|---|---|
| `t_package` | paquetes (`Package_ID`, `Name`, `Parent_ID`, `ea_guid`) |
| `t_object` | elementos (`Object_ID`, `Name`, `Object_Type`, `Stereotype`, `ParentID`, `Multiplicity`, `NType`, `PDATA1`, `Note`, `ea_guid`) |
| `t_diagram` | diagramas (`Diagram_ID`, `Name`, `Notes`) |
| `t_diagramobjects` | **la posición de un elemento en un diagrama** (`Diagram_ID`, `Object_ID`, `RectLeft/Right/Top/Bottom`, `Sequence`, `ObjectStyle`) |
| `t_connector` | conectores (`Connector_ID`, `Name`, `Start_Object_ID`, `End_Object_ID`, `SeqNo`, `PtStartX/Y`, `PtEndX/Y`, `PDATA1..4`, `StateFlags`, `ea_guid`) |
| `t_xref` | perfiles aplicados y particiones de fragmento (`Client` = GUID del elemento, `Name` = `'Stereotypes'` o `'Partitions'`, `Description` = el contenido) |

> Un mismo paquete aparece **dos veces**: como fila en `t_package` y como fila en `t_object` con
> `Object_Type = 'Package'` y el mismo `ea_guid`. **Renombrar un paquete es actualizar las dos.**

### 6.1 Color de fondo

Vive **concatenado** en `t_diagramobjects.ObjectStyle`, con la forma `BCol=<entero BGR>;`.
Es por diagrama, no por elemento.

```powershell
$st = "$(Scalar "SELECT ObjectStyle FROM t_diagramobjects WHERE Diagram_ID=$did AND Object_ID=$oid")"
if ($st -notmatch 'BCol=') {
    $u = $cn.CreateCommand()
    $u.CommandText = "UPDATE t_diagramobjects SET ObjectStyle = ? WHERE Diagram_ID=$did AND Object_ID=$oid"
    [void]$u.Parameters.AddWithValue('s', ($st + "BCol=$color;"))
    [void]$u.ExecuteNonQuery()
}
```

El entero es **BGR**, no RGB. Los que se usaron:

| Color | RGB | Entero BGR | Significado en este proyecto |
|---|---|---|---|
| Verde claro | 214,240,214 | `14086358` | implementado |
| Gris | 230,230,230 | `15132390` | pendiente |
| Azul claro | 214,230,250 | `16443094` | pertenece a otro subsistema |

Cálculo: `BGR = azul*65536 + verde*256 + rojo`.

### 6.2 Contención real: `ParentID`

Que un elemento esté **dibujado** encima de un paquete no significa que le pertenezca: al mover el
contenedor, los hijos se quedan. La contención de verdad es `t_object.ParentID`.

```powershell
Exec "UPDATE t_object SET ParentID = $idPadre WHERE Object_ID IN ($idsHijos)"
```

> **Asignar `Element.ParentID` por COM lanza `NullReferenceException` en EA 15.** Por eso va acá.

### 6.3 Orden Z desde SQL

```powershell
$z = 2
foreach ($id in $hijos) { Exec "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID=$did AND Object_ID=$id"; $z++ }
Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID=$did AND Object_ID=$idContenedor"
```

Recordar: **más bajo = más al frente**.

### 6.4 Multiplicidad de un nodo

```powershell
Exec "UPDATE t_object SET Multiplicity = '*' WHERE Object_ID IN ($ids)"
```

### 6.5 Desligar un estereotipo del perfil (el caso `form`)

```powershell
$pk = "(SELECT Package_ID FROM t_package WHERE Name = '4.3 Componentes de Subsistemas')"
Exec "DELETE FROM t_xref WHERE Name='Stereotypes' AND Client IN
        (SELECT ea_guid FROM t_object WHERE Stereotype='form' AND Package_ID=$pk)"
Exec "UPDATE t_object SET Stereotype='FORM' WHERE Stereotype='form' AND Package_ID=$pk"
```

`StereotypeEx` **no es una columna de `t_object`**: es justamente la fila de `t_xref` que se acaba
de borrar.

### 6.6 Renombrar el modelo entero

Si el proyecto cambia de nombre:

```powershell
$g = Scalar "SELECT ea_guid FROM t_package WHERE Package_ID = 2"   # el paquete raíz
$u = $cn.CreateCommand(); $u.CommandText = "UPDATE t_package SET Name = ? WHERE Package_ID = 2"
[void]$u.Parameters.AddWithValue('n','Nombre Nuevo'); [void]$u.ExecuteNonQuery()
$u2 = $cn.CreateCommand(); $u2.CommandText = "UPDATE t_object SET Name = ? WHERE ea_guid = '$g'"
[void]$u2.Parameters.AddWithValue('n','Nombre Nuevo'); [void]$u2.ExecuteNonQuery()
```

Y para encontrar lo que quedó con el nombre viejo:

```sql
SELECT Object_ID, Name FROM t_object   WHERE Name  LIKE '%viejo%';
SELECT Object_ID, Note FROM t_object   WHERE Note  LIKE '%viejo%';
SELECT Diagram_ID, Name FROM t_diagram WHERE Name  LIKE '%viejo%';
SELECT Connector_ID, Name FROM t_connector WHERE Name LIKE '%viejo%';
SELECT Package_ID, Notes FROM t_package WHERE Notes LIKE '%viejo%';
```

**Hacer una copia del `.eapx` antes de tocarlo.** Es un archivo binario: no hay `git diff` que
salve.

---

## 7. Receta por diagrama

Para cada uno: **tipo de diagrama en EA**, elementos, conectores, disposición y las trampas propias.

### 7.1 Casos de uso 1.3.2 y 1.5

**Tipo de diagrama:** `UseCase` · **Script:** `ea-cu-ciclo1.ps1`

| Qué | Cómo |
|---|---|
| Actores | `Actor`. El abstracto (p. ej. «Usuario interno») con `$e.Abstract = '1'` |
| Casos de uso | `UseCase`, con `Notes` describiendo el objetivo |
| Actor ↔ CU | `Association` |
| Herencia de actores | `Generalization`, del concreto al abstracto |
| `include` | `Dependency` con estereotipo `include`, **del que incluye al incluido** |
| `extend` | `Dependency` con estereotipo `extend`, **de la extensión al caso base** |
| Punto de extensión | `$cu.ExtensionPoints = 'Tras crear la cuenta'` |

**1.5 (modelo estructurado)** es un solo diagrama con todo: actores en una columna a la izquierda,
casos de uso en dos columnas a la derecha (los numerados y las extensiones).

> ⚠️ **El 1.5 es ACUMULATIVO. Regla fijada el 13/09/2026.** El de un ciclo muestra los casos de uso
> y los actores de **ese ciclo y de todos los anteriores**: el del Ciclo 2 lleva los 9 del Ciclo 1
> más sus 13, y el del Ciclo 3 llevará esos 22 más los suyos. Es lo que la sección pide —
> «estructurar el modelo de casos de uso» es el modelo **completo tal como quedó al cerrar el
> ciclo**, no el delta—. El que va por ciclo y por caso de uso es el **1.3.1**; el 1.5 es la foto
> del sistema entero.
>
> **Cuidado al rehacerlo:** los actores del paquete de un ciclo no son solo suyos. En Violet
> Boutique los trece diagramas de comunicación de **2.2** tienen puestos en el lienzo los actores
> del paquete `Ciclo 2`, así que un `-Rehacer` que borre ese paquete los deja sin actor y con 48
> conectores de mensaje colgando. Se comprueba antes, por SQL:
>
> ```sql
> SELECT d.Name, o.Name FROM (t_diagramobjects dobj
>   INNER JOIN t_object o ON o.Object_ID = dobj.Object_ID)
>   INNER JOIN t_diagram d ON d.Diagram_ID = dobj.Diagram_ID
> WHERE o.Package_ID = <el paquete> AND d.Package_ID <> <el paquete>
> ```
>
> Si devuelve filas, hay que **agregar sin borrar** y rehacer solo el diagrama 1.5, que es lo que
> hace `ea-cu-1-5-acumulado.ps1`.
>
> **Y un detalle del conteo:** al crear el diagrama sobre conectores que YA existían, EA no
> materializa las `DiagramLinks` hasta que alguien lo abre —el script reporta 0 relaciones y el
> dibujo sale bien igual—. Lo que se verifica entonces es cuántos conectores hay **entre los
> elementos del paquete**, que es lo que EA va a dibujar (regla 3).

**1.3.2** es **un diagrama por caso de uso**, en el **mismo paquete** que el 1.5 (regla 2). Cada uno
muestra su CU, los actores que lo inician y los CU relacionados por `include`/`extend`.

**La trampa:** como todos los elementos se comparten, al poner en el lienzo de CU-01 al actor
`Cliente` y al caso `CU-02`, EA dibuja también la asociación Cliente–CU-02, que no viene al caso.
Se pasa la lista de pares a ocultar:

```powershell
$dCu01 = New-DiagramaDeCasoDeUso $pkg 'CU-01 Registrar cliente' @(
    @{ el=$A['cliente']; l=40;  t=-150; w=100; h=80 },
    @{ el=$U['cu01'];    l=290; t=-120; w=250; h=115 }
) @( ,@($A['cliente'], $U['cu02']) )      # <- la coma inicial fuerza array de arrays
```

> El `,@(...)` con coma delante no es un error de tipeo: en PowerShell, un array de un solo elemento
> que a su vez es array se aplana. La coma lo impide.

**Otro detalle:** si el diagrama y el actor están en paquetes distintos aparece el rótulo
`(from Ciclo 1)` debajo del actor. Es opción de visualización de EA, se apaga a mano.

---

### 7.2 Análisis de arquitectura 2.1.1 / 2.1.2 / 2.1.3

**Tipo:** `Package` (2.1.1 y 2.1.2) y `UseCase` (2.1.3) · **Script:** `ea-analisis-2-1.ps1`

- **2.1.1 Identificar paquetes.** Los paquetes como elementos `Package` en una grilla de 3
  columnas. Debajo de cada uno, un `Note` con su descripción, atado con `NoteLink` (regla 8).
- **2.1.2 Relacionar paquetes y casos de uso.** El paquete a la izquierda, sus casos de uso
  apilados a la derecha, unidos con `Abstraction` estereotipo `trace`. El paquete se **centra
  verticalmente** contra su bloque:

  ```powershell
  $tPaq = $t - [int](($def.cus.Count * 90 - 70) / 2)
  ```

  Después se ocultan todas las relaciones que no sean `trace`: si no, se cuelan los `include` y
  `extend` entre casos de uso y el diagrama deja de ser de trazas.

- **2.1.3 Vista de paquetes.** **Un diagrama por paquete**, no uno solo. La razón es dura: en EA
  **un elemento solo puede aparecer una vez por diagrama**, y un actor participa en varios
  paquetes. En un único lienzo, `Cliente` tendría que estar dentro de P1, P5, P6, P7, P9 y P10 a la
  vez.

  El paquete se dibuja como **contenedor grande** y los casos de uso van **dentro de sus límites**:

  ```powershell
  $altoPaq = [Math]::Max($def.cus.Count * 100 + 80, $suyos.Count * 120 + 80)
  Poner $d $P[$def.k] 300 -40 460 $altoPaq
  ```

  Acá es **obligatorio** ordenar el Z (regla 4) o el paquete tapa a sus casos de uso. Y se ocultan
  las trazas: los CU ya están dibujados dentro del paquete, que es la misma información.

#### Agregar un caso de uso al 2.1.2 y al 2.1.3 sin rehacerlos

Pasa en cada ciclo: aparecen casos de uso nuevos y los dos diagramas ya están acomodados a mano.
**No se regeneran.** Script de referencia: `ea-analisis-2-1-refinamiento.ps1`.

| Diagrama | Qué hacer |
|---|---|
| **2.1.2** | Es una columna: paquetes a la izquierda, casos de uso a la derecha, agrupados por paquete. Se inserta el caso de uso en el bloque de **su** paquete y se **empuja hacia abajo** todo lo que queda debajo del umbral. Las inserciones se aplican de **abajo hacia arriba**, o cada desplazamiento mueve el punto de inserción de las que faltan. |
| **2.1.3** | Ahí el `Package` **sí es un marco contenedor**: los actores y los casos de uso se dibujan dentro de sus límites. Hay que **bajar `Bottom` del marco antes** de meter nada, o el elemento nuevo queda fuera de la caja. Si el actor iniciador no estaba en esa vista, se agrega también. |

**La traza va del PAQUETE al CASO DE USO** —`Abstraction` «trace», `Source` = paquete— y cada caso
de uso lleva **dos**: una desde la copia del paquete que usa el 2.1.2 y otra desde la que usa el
2.1.3. Un caso de uso que pertenece a dos paquetes lleva cuatro, y aparece **una sola vez** en el
2.1.2.

> ⚠️ **Los once paquetes están triplicados en el modelo** (ids 59-69 para 2.1.1, 81-91 para 2.1.2 y
> 92-102 para 2.1.3). Es el resultado de la regla 6 —`Package.Elements` no devuelve los elementos de
> tipo `Package`, así que el buscar-o-crear no los encontraba y los recreaba en cada corrida—. **No
> se arregla**: cada diagrama apunta a su copia y unificarlos ahora significa rehacer los trece
> dibujos a mano. Lo que sí hay que hacer es **colgar cada traza de la copia correcta**.

**Comprobación obligatoria después de mover cosas.** Un choque de cajas no da error y no se ve hasta
que alguien abre el diagrama. Se verifica por SQL, sin exportar nada:

```sql
SELECT d.RectLeft, d.RectRight, d.RectTop, d.RectBottom, o.Name
FROM t_diagramobjects d INNER JOIN t_object o ON o.Object_ID = d.Object_ID
WHERE d.Diagram_ID = <id>
```

y se cruzan todos los pares buscando solapamiento, más que cada elemento caiga dentro del marco.
La primera corrida de este script dejó al actor `Sistema (procesos automáticos)` encima de
`CU-30 Abrir y cerrar caja` en la vista de P7; se detectó así y no abriendo EA.

---

### 7.3 Comunicación 2.2

**Tipo:** `Communication` · **Script:** `ea-comunicacion-2-2.ps1`

Esto costó averiguarlo y no está documentado con claridad en ningún lado:

1. **El enlace** entre dos objetos es un conector **`Association`**. Es lo que dibuja la línea, y va
   **uno solo por par**, aunque intercambien diez mensajes.
2. **Cada mensaje** es un conector **`Collaboration`**. Su nombre es **solo la operación**;
   **nada de numerarlo a mano**.
3. **El número lo pone EA**, y sale del campo **`PDATA4`** del conector, con el formato
   `<grupo>.<orden>`. Ese campo es el ***Start New Group*** de la interfaz: al cambiar de grupo, EA
   reinicia la numeración y dibuja el grupo nuevo **en otro color**.

`PDATA4` es de **solo lectura** por la API (`MiscData(3)`), así que se escribe con SQL:

```powershell
$id = New-Mensaje $part[$m.d] $part[$m.a] $m.m
$ea.Execute("UPDATE t_connector SET PDATA4='$grupo.$orden' WHERE Connector_ID=$id")
```

> Numerar a mano dentro del nombre —`"1: enviarDatos()"`— se ve parecido pero es peor: EA no sabe
> que son grupos, no los colorea, y **amontona todas las etiquetas en el punto medio del enlace**.
> Con `PDATA4` las apila ordenadas.

**Disposición:** cuatro columnas —actores, `«boundary»`, `«control»`, `«entity»`— cada una centrada
verticalmente sobre el mismo eje:

```powershell
$paso   = $col.alto + 130
$inicio = -220 + [int]((($col.lista.Count - 1) * $paso) / 2)
```

**Las cajas tienen que ser cuadradas.** El estereotipo de robustez se dibuja como un **círculo
inscrito en la caja**; con una caja ancha y baja el círculo se desborda y tapa a los vecinos. Y la
separación entre elementos tiene que ser **mayor que el alto** de la caja.

**La numeración de los grupos** sigue las etiquetas de la tabla de detalle del caso de uso: grupo 1
el flujo principal, los siguientes los alternativos y las excepciones. Cada diagrama lleva un `Note`
al pie explicando qué es cada grupo.

Como las clases de análisis se comparten entre casos de uso, hay que ocultar todo lo que no se creó
para este diagrama (regla 3), tanto los `Collaboration` ajenos como los `Association` ajenos.

---

### 7.4 Clases de análisis 2.3

**Tipo:** `Logical` · **Script:** `ea-clases-2-3.ps1`

Un diagrama de clases **por caso de uso**, con las mismas clases que el 2.2 del mismo caso pero
**como elementos distintos** (ver [5.9](#59-estereotipos-stereotype-y-stereotypeex)): estereotipos
`frontera`, `controlador`, `entidad`, que EA dibuja **como tabla**.

**Nivel de detalle:**

| Estereotipo | Atributos | Operaciones |
|---|---|---|
| `frontera` | — | el componente del frontend **y** el endpoint del router |
| `controlador` | — | las funciones del `service.py` / del módulo de seguridad |
| `entidad` | **las columnas de la tabla**, con su tipo de la base | las funciones del `repository.py` que consultan esa tabla |

Los nombres son **los reales del código**, no inventados. Es lo que permite defender el diagrama:
cada operación se puede abrir en el repositorio.

**La unión entre dos clases es siempre una `Association`**, con **nombre de rol en mayúsculas**
(`DELEGA_EN`, `ADMINISTRA`, `PERTENECE_A`) y **cardinalidad en los dos extremos**. Nada de
`Dependency`, `Usage`, `Aggregation` ni `Composition`. El motivo es de lectura: con un solo tipo de
línea el lector compara los diagramas del capítulo entre sí sin interpretar la semántica de cada
estilo, y no queda abierta la discusión de si algo era agregación o composición.

**Paso previo obligatorio.** Si una pasada anterior dejó los estereotipos del 2.2 en español, los
diagramas de comunicación perdieron el ícono redondo. El script los restaura antes de nada:

```powershell
$aIngles = @{ 'frontera'='boundary'; 'controlador'='control'; 'entidad'='entity' }
foreach ($e in $p22Clases.Elements) {
    if ($aIngles.ContainsKey($e.Stereotype)) {
        $e.Stereotype = $aIngles[$e.Stereotype]
        $e.StereotypeEx = $e.Stereotype     # borra la aplicación del perfil viejo
        [void]$e.Update()
    }
}
```

**Alto de la caja:** ~`60 + nAtributos*18 + nOperaciones*18`. Si queda corta, EA recorta la lista sin
avisar.

---

### 7.5 Análisis de paquetes 2.4

**Tipo de diagrama:** `Package` · **Script:** `ea-paquetes-2-4-ciclo2.ps1`

> **Esta receta cambió el 13/09/2026.** La primera versión —la que produjo el diagrama del
> Ciclo 1— dibujaba las clases **contenidas** dentro de cada paquete y unía los paquetes con
> `Usage`. Se reemplazó por la forma del diagrama **3.10a** de otro proyecto
> (`PROYECTO_MEDICOS/docs/diagramas/PlataformaMedica.eapx`), que está mejor resuelto. Abajo va el
> porqué del cambio y lo que queda de la versión vieja.

| Qué | Cómo |
|---|---|
| Paquetes | elementos de tipo `Package`, **280 × 80** |
| Dependencias | conector **`Dependency`**, sin estereotipo, `Direction = 'Source -> Destination'` |
| Disposición | pirámide por capas, **paso de fila 150**, columnas cada 320 (`40 · 360 · 680` y `200 · 520`) |
| Orden Z | **no hace falta tocarlo**: sin clases adentro, ningún rectángulo tapa a nadie |

**Lo que cambió, y por qué.**

1. **Los paquetes van solos, sin las clases adentro.** Con tres paquetes y catorce clases el
   dibujo del Ciclo 1 todavía se leía; con los seis paquetes y la veintena de clases del Ciclo 2
   se vuelve ilegible. El diagrama del capítulo tiene que contestar «quién depende de quién», y
   eso se ve mejor sin el relleno.
2. **`Dependency` en vez de `Usage`.** Es lo que usa el 3.10a y es la flecha que UML asocia a la
   dependencia entre paquetes. `Usage` («use») es un refinamiento de `Dependency` que promete más
   de lo que el diagrama afirma.
3. **La disposición es una pirámide, no dos filas.** La base —el paquete del que todos dependen—
   abajo y centrada; cada capa encima depende hacia abajo. Con la regla de las dos filas, un
   sistema de seis paquetes deja una fila de cinco y no se entiende qué depende de qué.

**La cohesión no se pierde: se baja a las notas.** El 3.10a no lleva notas, pero la sección 2.4
del índice pide las dos mitades —cohesión y acoplamiento—, así que van dos `Note` al pie, y la de
cohesión **nombra las clases de cada paquete**. Es la misma información que antes estaba dibujada,
en un espacio que no compite con las flechas.

**La grilla, para copiarla tal cual:**

```powershell
$ANCHO = 280; $ALTO = 80; $PASO_FILA = 150
$COLUMNAS = @{ 1 = @(360); 2 = @(200, 520); 3 = @(40, 360, 680) }   # por cantidad de la fila
$t = -60
foreach ($fila in $capas) {
    $xs = $COLUMNAS[$fila.Count]
    for ($i = 0; $i -lt $fila.Count; $i++) { Poner $d $P[$fila[$i]] $xs[$i] $t $ANCHO $ALTO }
    $t -= $PASO_FILA
}
```

**Lo que sigue valiendo de la versión vieja:**

- Los elementos se **duplican** a propósito: no se reusan los paquetes del 2.1. Colgarles las
  dependencias los haría aparecer en 2.1.1 y 2.1.2, que ya están acomodados a mano (regla 3).
- El diagrama y sus elementos viven en el **mismo paquete** (regla 2).
- `Package.Elements` **no devuelve los elementos de tipo `Package`**: el «buscar-o-crear» tiene
  que indexar por SQL sobre `t_object`, o cada corrida los duplica (regla 6).

**El diagrama del Ciclo 1 no se rehízo.** Quedó con las clases adentro y con `Usage`; el del
Ciclo 2 en adelante usa esta receta. Si se quieren uniformes, hay que rehacer el del Ciclo 1 a
mano o borrarlo y volver a generarlo.

**Sobre el nombre.** En el proyecto médico el diagrama se llama `3.10a Diagrama de Paquetes` y es
**uno solo** para todo el sistema. Acá la sección es `2.4 Análisis de Paquetes` y va **por ciclo**,
porque así lo pide el índice de la ingeniera; el nombre del diagrama conserva el sufijo
`- CICLO #N`.

---

### 7.6 Capas 3.1.1

**Tipo:** `Component` · **Script:** `ea-capas-3-1-1.ps1`

Cuatro filas imaginarias, de arriba hacia abajo, con un `Note` a la izquierda rotulando cada una:

| Capa | Contenido | Forma |
|---|---|---|
| 1 · Vista de análisis | los paquetes del 2.1, alineados y **sin relaciones entre sí** | `Package` |
| 2 · Backend + Frontend + Móvil | una caja por aplicación, con sus **archivos más característicos** adentro | `Package` + `Artifact` |
| 3 · Servidores locales | el entorno de desarrollo de cada máquina | `Package` |
| 4 · Servidores en la nube | dónde vive el sistema publicado | `Package` |

Y tres relaciones, una por salto:

```
capa 1 --«realiza»------> capa 2      Realisation
capa 2 --«ejecuta en»---> capa 3      Dependency
capa 3 --«despliega en»-> capa 4      Dependency
```

**Sobre la dirección de «realiza»:** en UML la realización apunta del que **implementa** hacia lo
realizado, o sea capa 2 → capa 1. Acá se dibuja **al revés**, de capa 1 a capa 2, porque así lo pidió
la cátedra y así se lee de arriba hacia abajo junto con las otras dos. **Queda anotado para que
nadie lo "corrija" por error.**

**Sobre las formas:** las capas 3 y 4 usan `Package` —la carpeta— porque así lo pide la cátedra
*para este diagrama*. En el **diagrama de despliegue** que viene después esos mismos servidores
tienen que ser `Node` con `«device»` y `«executionEnvironment»`; ahí la carpeta no vale.

En la segunda pasada: `ParentID` para que los archivos cuelguen de verdad de su caja, y el orden Z
para que la caja no los tape.

---

### 7.7 Despliegue 3.1.2

**Tipo:** `Deployment` · **Script:** `ea-despliegue-3-1-2.ps1`

Este diagrama sale mal casi siempre porque se dibuja como un diagrama de componentes con íconos de
computadora. **Los cinco errores típicos:**

1. **Usar `Package` o `Component` para los servidores.** En UML un servidor es un **`Node`** —la
   caja en 3D— y se distingue `«device»` (el hardware) de `«executionEnvironment»` (el runtime que
   corre **dentro** de ese hardware). EA tiene los tipos `Device` y `ExecutionEnvironment` de
   verdad: usarlos.
2. **Meter componentes dentro de los nodos.** Eso es UML 1.x. Desde UML 2.0 lo que se despliega en
   un nodo es un **artefacto** —el archivo: la imagen Docker, el bundle compilado, el `.apk`— y ese
   artefacto **manifiesta** (`«manifest»`) al componente.
3. **Unir los nodos con `Dependency`.** La conexión entre dos nodos es un **`CommunicationPath`**:
   línea **sólida, sin punta de flecha**, rotulada con el protocolo. EA lo tiene como tipo propio.
4. **Olvidar la multiplicidad de los clientes.** Hay muchas computadoras y muchos celulares, no uno
   de cada uno: llevan `[*]` (`t_object.Multiplicity = '*'`, en la segunda pasada).
5. **Repetir el mismo artefacto en cada nodo.** El bundle de Angular es **uno solo** desplegado en
   cuatro sitios: se dibuja una vez y se le sacan cuatro flechas `«deploy»`.

**Las dos notaciones de despliegue, y cuándo usar cada una:**

- **Artefacto DENTRO del nodo** — cuando ese artefacto vive solo ahí (la imagen de la API, el
  esquema de la base, `nginx.conf`).
- **Artefacto FUERA con flecha `«deploy»`** — cuando el mismo artefacto se despliega en varios
  nodos.

Las dos son notación válida; mezclarlas con criterio es lo correcto.

Conectores: `Deployment` («deploy») artefacto→nodo, `Manifest` («manifest») artefacto→componente,
`CommunicationPath` nodo↔nodo con el protocolo como **nombre** del conector.

Segunda pasada: `ParentID` (contención real), `Multiplicity` y orden Z en tres niveles —artefactos y
runtimes adelante (`Sequence` 2, 3, 4…), execution environments en el medio (100), devices al fondo
(200)—.

Y un `Note` de leyenda explicando qué significa cada estereotipo y cada tipo de línea. En un
diagrama de despliegue vale la pena: es el que más gente lee mal.

---

### 7.8 Secuencia 3.2

**Tipo:** `Sequence` · **Script:** `ea-secuencia-3-2.ps1`

El más difícil de los catorce. Tiene tres problemas propios.

#### a) Las líneas de vida

No son elementos `Class` puestos en el lienzo: son elementos de tipo **`Sequence`**, **sin nombre**,
con **`ClassifierID`** apuntando a la clase del 2.3.

```powershell
$el = $pkg.Elements.AddNew('', 'Sequence')
$el.Name = ''
$el.ClassifierID = $clase['Usuario'].ElementID
[void]$el.Update()
```

Así EA lo rotula `: Usuario` y **el vínculo queda vivo**: si se renombra la clase, se renombra la
línea de vida. Si se pone el nombre a mano es texto suelto y se desincroniza.

El **actor** es el mismo elemento del capítulo 1, no una copia.

#### b) EA **remaqueta el diagrama entero cada vez que lo abre**

No respeta las alturas que uno escriba: **reordena los mensajes por `SeqNo`** y los reparte con
**su** paso —**35 px arrancando en −135**—, dejando un hueco extra en cada borde de fragmento. Lo
que **sí** conserva es la caja del fragmento combinado.

La consecuencia es traicionera: si los mensajes se escriben con otra escala, al abrir el diagrama se
comprimen, **la caja se queda donde estaba** y el `alt` termina envolviendo mensajes que no son.

**Por eso las constantes del script replican exactamente la escala de EA:**

```powershell
$X0        = 190    # borde izquierdo de la primera línea de vida
$GAP       = 70     # separación horizontal entre líneas de vida
$TOP_LV    = -50    # borde superior de las líneas de vida
$Y_PRIMERO = -135   # altura del primer mensaje  (la que usa EA)
$PASO      = 35     # separación vertical         (la que usa EA)
$ALTO_NOTA = 55     # lo que consume una nota separadora de flujo
$ALTO_ALT  = 22     # lo que consume la cabecera de un fragmento
$ALTO_OP   = 20     # lo que consume la etiqueta de un operando
```

Con esa escala la remaquetación es prácticamente la identidad. Aun así: **verificar la cobertura de
cada operando después de abrir el modelo.**

#### c) Ni el tipo de mensaje ni los operandos se pueden escribir por COM

Los mensajes son conectores `Sequence`, pero su geometría y su tipo viven en `t_connector`:

```powershell
$c = $src.Connectors.AddNew($nombre, 'Sequence')
$c.SupplierID = $dst.ElementID
$c.Direction  = 'Source -> Destination'
$c.DiagramID  = $dia.DiagramID
$c.SequenceNo = $seq
[void]$c.Update()
```

Y en la segunda pasada, con `$sx`/`$ex` = centro horizontal de cada línea de vida
(`(RectLeft + RectRight) / 2` de `t_diagramobjects`):

```sql
UPDATE t_connector SET
    SeqNo = <n>, PtStartX = <sx>, PtStartY = <y>, PtEndX = <ex>, PtEndY = <y>,
    PDATA1 = 'Synchronous', PDATA2 = 'retval=void;',
    PDATA3 = 'Call',            -- 'Return' para los de vuelta (línea punteada)
    StateFlags = 'Activation=0;'
WHERE ea_guid = '<guid>'
```

El **primer** mensaje del diagrama lleva
`StateFlags = 'Activation=0;Initiate=1;ForceActivation=0;ExtendActivationUp=0;'`.

**Fragmentos combinados.** El elemento es un `InteractionFragment`. El operador y sus operandos
viven en `t_object.NType` y en una fila `Partitions` de `t_xref`:

```sql
UPDATE t_object SET NType = 0, PDATA1 = '6' WHERE ea_guid = '<guid>'   -- NType 0 = alt
```

```
@PAR;Name=<guarda>;Size=<alto en px>;GUID={…};@ENDPAR;@PAR;…@ENDPAR;
```

**La suma de los `Size` tiene que ser exactamente el alto de la caja**, o EA reparte mal las bandas.
Se calcula a partir de los cortes entre operandos:

```powershell
$limites = @($f.top) + $f.cortes + @($f.bot)
for ($i = 0; $i -lt $f.ops.Count; $i++) {
    $tam = $limites[$i] - $limites[$i + 1]
    $g = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
    $partes += "@PAR;Name=$($f.ops[$i]);Size=$tam;GUID=$g;@ENDPAR;"
}
```

Y se inserta **por parámetro**, por los acentos de las guardas (regla 9).

#### d) Solo se genera `alt`

Es el único operador cuyo código interno está verificado (`NType = 0`). Para los demás, el mensaje
lleva la guarda en el nombre —`2.1a: [si queda predeterminada] UPDATE …`— y se documenta cuál
operador correspondería. **Cambiarlo a mano es trivial:** doble clic sobre el fragmento →
desplegable **Interaction Operator**. Los operandos se agregan con clic derecho → **Combined
Fragment → Add Operand**.

#### e) El guion

Cada caso de uso se declara como una lista de líneas de vida y una lista de pasos que **se lee de
arriba hacia abajo y es el orden vertical del diagrama**:

```powershell
guion = @(
  @{ t='nota'; txt = "FLUJO 1`nAlta de temporada" },
  @{ t='msg'; o='act'; d='pte'; n='1.1: registrarTemporada(datos)' },
  @{ t='msg'; o='pte'; d='gte'; n='1.2: crear_temporada(db, datos)' },
  @{ t='msg'; o='tem'; d='gte'; n='1.5.1: Temporada | None'; ret=$true },
  @{ t='alt' },
  @{ t='op';  g='nombre libre y sin solapamiento' },
  @{ t='msg'; o='gte'; d='tem'; n='1.7: INSERT INTO temporada (...)' },
  @{ t='op';  g='fechas incoherentes' },
  @{ t='msg'; o='gte'; d='pte'; n='4.1: fechasIncoherentes() -> 422' },
  @{ t='fin' }
)
```

`nota` = separador de flujo · `msg` = mensaje (`ret=$true` lo marca como retorno) · `alt` abre
fragmento · `op` operando con su guarda · `fin` lo cierra. **Agregar un mensaje es agregar una
línea.**

#### f) Convención de contenido de los mensajes

| Tramo | Qué se escribe | Ejemplo |
|---|---|---|
| Actor → frontera | la acción del usuario | `1.1: enviarCredenciales(correo, contrasena)` |
| Frontera → controlador | la función real, con su firma | `1.2: autenticar(db, datos)` |
| Controlador → controlador | la función auxiliar | `1.5: verify_password(contrasena, hash)` |
| Controlador → entidad | **el SQL literal** | `1.7: INSERT INTO usuario (correo, ...)` |
| Entidad → controlador | **el tipo del resultado**, como `Return` | `1.7.1: Usuario (id)` |
| Controlador → frontera (error) | el error y su código HTTP | `4.1: correoYaRegistrado() -> 409` |

**La numeración se hereda tal cual del diagrama de comunicación 2.2** del mismo caso de uso, para
que el mismo mensaje se siga en los dos capítulos. Los **retornos**, que el 2.2 no tiene, se numeran
como sub-nivel del mensaje que los provoca (`1.7` → `1.7.1`), para no desplazar la numeración
original.

---

### 7.9 Modelo de dominio 3.3.1

**Tipo:** `Logical` · **Script:** `ea-datos-3-3-1.ps1`

Convenciones (tomadas del modelo de referencia de cátedra):

- **una clase por tabla**, con el **nombre de la entidad en MAYÚSCULAS**;
- **sin operaciones**: es un modelo de datos, no de comportamiento;
- **atributos privados**, la clave primaria **primero**;
- relaciones como **`Association`** con un **verbo en MAYÚSCULAS** por nombre (`TIENE`, `ALBERGA`,
  `SE_ASIGNA_EN`) y **cardinalidad en los dos extremos**;
- **nombres de columna en minúsculas**, como en el código.

Dos agregados sobre la referencia, que valen la pena:

1. **el tipo de cada columna**, para que el modelo lógico y el esquema físico digan lo mismo;
2. **el estereotipo `«PK»` / `«FK»`** en cada columna que lo sea (`'PK,FK'` para una clave compuesta
   que además es foránea). Sin eso hay que adivinar qué columna cierra cada relación.

**El contenido no se transcribe a mano.** Sale de los modelos del ORM compilados con el dialecto de
la base real, y se **verifica columna por columna** contra ellos después de generar.

**Las cardinalidades salen de lo que la base realmente obliga, no de la prosa.** Si
`cliente.usuario_id` es `UNIQUE NOT NULL`, un usuario tiene **0 o 1** ficha de cliente —nunca
"exactamente 1", porque un administrador no es cliente—.

> ⚠️ **El UNIQUE compuesto no hace único a cada una de sus columnas.** Al derivar las
> cardinalidades de `information_schema`, un `JOIN` contra `key_column_usage` devuelve **una fila
> por columna** de la restricción. `variante_producto` tiene `UNIQUE(producto_id, talla_id,
> color_id)`: leído así, `producto_id` parece único y el modelo termina diciendo que **un producto
> tiene a lo sumo una variante** —exactamente al revés de lo que afirma la decisión D1—. Hay que
> agrupar por `constraint_name` y quedarse solo con las restricciones de **una** columna:
>
> ```sql
> SELECT tc.table_name, MIN(kcu.column_name), COUNT(kcu.column_name)
> FROM information_schema.table_constraints tc
> JOIN information_schema.key_column_usage kcu ON kcu.constraint_name = tc.constraint_name
> WHERE tc.constraint_type = 'UNIQUE'
> GROUP BY tc.table_name, tc.constraint_name
> -- y descartar las que devuelven COUNT > 1
> ```
>
> No da error y el diagrama se ve bien: se detecta leyendo las cardinalidades una por una.

**Disposición:** columnas agrupadas por paquete de análisis, de izquierda a derecha. Las
autorreferencias (una categoría que es subcategoría de otra) necesitan **aire a la derecha**.
Alto de cada caja: `60 + nColumnas * 18`.

---

### 7.10 Componentes del sistema 4.2

**Tipo:** `Component` · **Script:** `ea-componentes-4-2.ps1`

Plantilla (de los ejemplos de cátedra):

```
izquierda : los paquetes funcionales del 2.1, como elementos Package
centro    : el/los hub del que salen las dependencias
derecha   : las capas técnicas, Component con estereotipo «Frontend» y «Backend»
abajo     : un paquete "Base de Datos" con el motor como Component «database»
            y las tablas como elementos Object
sueltos   : los servicios externos, Component «externo»
```

**Todas las relaciones son `Dependency`.**

Tres cosas en las que conviene apartarse del ejemplo:

1. **Dos hubs en vez de uno.** En los ejemplos un único `App.tsx` depende de todo, incluida la base
   de datos. Eso no es cierto en ninguna arquitectura de dos capas. Los hubs reales son los **dos
   puntos de composición** del proyecto: el archivo de rutas del frontend y el `main.py` que monta
   los routers. Entre ellos, **una sola dependencia**: la llamada HTTP.
2. **La contención tiene que ser de verdad.** En los ejemplos las tablas solo están **dibujadas**
   encima del paquete: `ParentID = 0` en todos, así que al mover el paquete los hijos se quedan.
   Ver [6.2](#62-contención-real-parentid).
3. **El color dice en qué estado está cada cosa.** Verde, implementado; gris, pendiente. Un
   `Note` de leyenda con la fecha del corte. Así el diagrama muestra el sistema **como está hoy**,
   no como va a quedar.

---

### 7.11 Componentes por subsistema 4.3

**Tipo:** `Component` · **Script:** `ea-componentes-4-3.ps1`

Uno por paquete, con el nombre codificando la trazabilidad: *Subsistema N = paquete PN del análisis
2.1*. Tres bandas horizontales, **todas de elementos `Component`**, diferenciadas solo por el
estereotipo:

```
«FORM»    pantallas del frontend
   │      Assembly   (el conector de ensamblado de UML 2.x)
«CLASS»   endpoints del backend
   │      Dependency
«TABLA»   tablas de la base
```

Tres decisiones que mejoran el ejemplo de cátedra:

1. **Los estereotipos son de verdad.** En el archivo de cátedra están tecleados a mano como texto
   —`<CLASS>`, y `< FORM>` con un espacio de sobra—. Acá se asignan por `Stereotype` y
   `StereotypeEx`, así que EA los dibuja entre guillemets. Ver el caso especial de `form` en
   [6.5](#65-desligar-un-estereotipo-del-perfil-el-caso-form).
2. **La banda `«CLASS»` va en dos filas, alternando.** Con 27 endpoints en una sola fila el diagrama
   pasa de los 4000 px y el texto no se lee al exportarlo. Cada grupo ocupa `ceil(n/2)` columnas y
   los endpoints se alternan entre la fila de arriba y la de abajo.
3. **Cada `«CLASS»` queda debajo de su `«FORM»`.** Los endpoints se agrupan por la pantalla que los
   llama y la pantalla se **centra sobre su grupo**: así las líneas de `Assembly` son cortas y
   verticales, y no se cruzan.

```powershell
$cols   = [math]::Ceiling($n / 2)
$anchoF = ($cols * $COL_STEP) - ($COL_STEP - $COL_W)   # la pantalla cubre su grupo
$cx     = $x0 + ([math]::Floor($i / 2) * $COL_STEP)
$cy     = if ($i % 2 -eq 0) { $Y_CLS_A } else { $Y_CLS_B }
```

Color: verde, implementado; azul, tabla que pertenece a **otro** subsistema. Y una validación que
vale oro:

```powershell
if (-not $elTabla.ContainsKey($t)) {
    throw "En '$($sub.nombre)' el endpoint $k apunta a la tabla $t, que no está en la banda"
}
```

### 7.12 Estado 3.2

**Tipo:** `Statechart` · **Script:** `ea-estado-3-2.ps1`

El más fácil de los que faltaban. Tres piezas y nada más:

| Pieza | Cómo se crea |
|---|---|
| Estado | `$pkg.Elements.AddNew('PENDIENTE', 'State')` |
| Pseudoestado inicial | `AddNew('', 'StateNode')` + `$el.Subtype = 100` |
| Estado final | `AddNew('', 'StateNode')` + `$el.Subtype = 101` |
| Transición | `$src.Connectors.AddNew($rotulo, 'StateFlow')` |

**Los `Subtype` del `StateNode` están sin documentar y se averiguaron probando.** Los que EA 15
dibuja son exactamente tres; del 103 en adelante **no dibuja nada** —el elemento queda en el árbol
y el lienzo sale vacío en ese punto, sin ningún error—:

| `Subtype` | Qué dibuja |
|---|---|
| `100` | círculo negro relleno — **inicial** |
| `101` | círculo negro con anillo — **final** |
| `102` | círculo con una X — punto de salida |
| `103`…`108` | **nada** |

El rótulo de la transición es el **nombre del conector**, con la notación de UML
`evento [guarda] / acción`. Acá la guarda es la **condición literal del `if` que la produce** y
entre llaves va el ancla al código (`[correo ya registrado]  {409 service.py:374}`), que es lo que
hace defendible el diagrama.

**QUÉ SE DIBUJA — corrección del 15/09/2026.** Este diagrama **no es el ciclo de vida de un
objeto**. Es el **flujo de una transacción**, y va **uno por caso de uso transaccional**, como el
`CU1` del ejemplo de cátedra: `Inicio → Autenticar → Seleccionar operacion → [ramas] →
Transaccion completada → Fin`. Hubo una primera versión que dibujaba la máquina de estados de
`Reserva`; estaba bien como statechart y mal como entregable. Se eliminó. El detalle está en
[`docs/diagramas/estado-navegacion-y-tiempo.md`](docs/diagramas/estado-navegacion-y-tiempo.md).

**La maqueta son cinco columnas**, no un abanico: autenticación · menú · operaciones · validación ·
cierre. Las operaciones se apilan en la columna del medio con **180 px entre una y otra**, y el
hueco entre la columna del menú y la de las operaciones tiene que ser **ancho** (600 px): por ahí
salen las cinco flechas del menú y ahí se dibujan sus rótulos, que son largos.

**NO SE ESCRIBEN COORDENADAS.** Cada estado declara su **columna y su fila**, y el generador calcula
`l` y `t`. Con dieciocho casos de uso, poner `l` y `t` a mano una por una era garantía de error, y
además impedía lo que resultó ser la herramienta clave: **las medias filas**.

> **El rótulo cae en el punto medio, y el punto medio choca.** EA dibuja el rótulo de cada
> transición a media altura entre origen y destino. Con cinco flechas saliendo del mismo menú, dos
> terminan a la misma altura y en la misma x, y los rótulos salen encimados —se llegó a leer
> `[a[intenta desactivarse a si mismo] {409 service.py:493}o}`— **sin ningún error**. Un medio punto
> de fila mueve el rótulo 90 px y alcanza. Tres reglas que salieron de esto:
>
> - el sumidero de errores va en la fila **3.5**, no en la 3;
> - el estado de cierre va en la **2.5**, no en la 2;
> - y en general, **el punto medio de la flecha de vuelta tiene que caer en el HUECO entre dos
>   operaciones, nunca sobre una**.

**Dos hallazgos que valen para cualquier statechart:**

- **Nunca dos flechas entre las mismas dos cajas.** EA pone el rótulo en el punto medio del
  conector; con ida y vuelta los dos puntos medios coinciden y los rótulos salen encimados —se leyó
  `[a[intenta desactivarse a si mismo] {409 service.py:493}o}`— **sin dar ningún error**. La
  solución es de modelado: todos los rechazos van a **un sumidero único** (`Informar error`, que es
  el `_traducir()` del router) y de ahí sale **una sola** flecha de vuelta al menú.
- **Se pueden poner varios estados finales, y conviene.** El rechazo de autorización muere en un
  final propio, dibujado al lado de la autenticación. Es UML válido, dice algo verdadero —un 403 no
  llega a haber transacción— y evita una flecha que cruce el lienzo entero.

El pseudoestado inicial va **lejos** del primer estado: el rótulo de esa transición se dibuja en el
punto medio, y con la flecha corta queda encima del círculo.

---

### 7.13 Navegación 3.2

**Tipo:** `Logical` (diagrama de clases) · **Script:** `ea-navegacion-3-2.ps1`

**Esto no es UML.** El diagrama de navegación no existe en la especificación 2.5 y **hay que
decirlo en la defensa**: es la extensión de *UML-based Web Engineering* (UWE), o sea un diagrama de
clases con un perfil encima. Por eso el tipo de diagrama es `Logical` y los elementos son `Class`:
no hay tipo nativo al que corresponda.

**VA UNO POR ACTOR — corrección del 15/09/2026.** El ejemplo de cátedra se titula
`class navegacion cliente`: nombra al actor, lo dibuja adentro, e incluye **los controladores** con
sus operaciones, no solo las pantallas. La primera versión de este generador hacía **uno solo para
todo el sistema**, con pantallas y rutas nada más; se rehízo. Ver
[`docs/diagramas/estado-navegacion-y-tiempo.md`](docs/diagramas/estado-navegacion-y-tiempo.md).

| Pieza | Cómo se crea |
|---|---|
| Vista de lista | `Class` con `Stereotype` **y** `StereotypeEx` = `navigationClass` (ver §5.9) |
| Formulario | lo mismo, con `formClass`. Sus atributos son **los campos reales** |
| Controlador | lo mismo, con `controller`. Sus operaciones son **los endpoints** |
| Menú / eje por rol | lo mismo, con `menu` |
| Actor | **se reutiliza** el del CAP. 1, buscándolo por SQL; no se copia |
| Salto | `Association` con `Direction = 'Source -> Destination'` |

> **`view` y `form` son estereotipos RESERVADOS de EA.** Si se usan, EA cambia la forma de la caja
> por la de su perfil de interfaz de usuario, no escribe el `«...»` y —lo grave— **deja de dibujar
> los atributos**: el formulario sale como una caja vacía, sin sus campos, que es justo lo que había
> que mostrar. Por eso `navigationClass` y `formClass`. Es el mismo tropiezo del `«FORM»` del 4.3.

> **El rótulo del enlace va en el NOMBRE y sin estereotipo.** Con los dos puestos EA escribe `build`
> y debajo `«build»`, que es lo mismo dos veces. El estereotipo se reserva para `navigationLink`,
> el enlace del actor al menú, donde el nombre lo ocupa la guarda.

**Los nombres son los exactos del código** (regla de oro 10): `usuarios.ts`, `usuario-formulario.ts`,
`seguridad/router.py`, y las operaciones `listar_usuarios`, `crear_usuario`… Por eso el generador
crea **un controlador por archivo, no por área**, y el `$ids[...|ctrl]` de dos áreas que comparten
`router.py` apunta al mismo elemento. Un elemento **no puede estar dos veces en el mismo lienzo**,
así que la caja compartida se dibuja en la primera banda que la usa y las demás le tiran la flecha.

**El alto de cada caja se calcula del contenido**, no es constante: `AltoCaja` suma cabecera + una
fila por atributo y por operación. El caso peor es `catalogo/maestros/router.py`, con dieciséis
funciones; con un alto fijo se comía la banda siguiente.

**Un elemento no puede estar dos veces en el mismo lienzo, pero sí en dos diagramas.** Como el
nombre es el archivo y un archivo atiende a varios actores, `seguridad/router.py` sale en el
diagrama del Administrador y en el del Cliente: **es el mismo elemento**. El generador lo busca por
nombre antes de crearlo y, al reutilizarlo, **le agrega las operaciones que falten** —cada diagrama
declara el subconjunto que le toca y la caja tiene que terminar con la unión—. Ojo con el tipo:
`Methods.Count` llega como un tipo COM que `Pos` no acepta, y el error («La conversión especificada
no es válida») no dice de dónde sale; hay que forzar `[int]`.

**Un área puede venir sin vista o sin formulario, y una pantalla puede ser pública.** El perfil del
Cliente es una sola pantalla con dos formularios encima, sin lista propia; y `/login`, `/registro` y
`/tienda` no declaran `canActivate`, así que cuelgan **del actor** y no del eje del rol. Dibujarlas
colgando del menú sería mentir sobre la guarda.

**La ruta va como atributo, no en el nombre.** `$el.Attributes.AddNew('ruta', '/tienda')` con
`Type` = la ruta: el nodo se lee «Catálogo» y debajo `+ ruta: /tienda`. Si se mete el path en el
nombre, el diagrama deja de leerse como un mapa de pantallas y pasa a ser una lista de URLs.

**La guarda va en el nombre del enlace**, entre corchetes: `[sesion + ADMINISTRADOR]`. Sale de
`canActivate` de la ruta de destino, o sea de `sesionGuard` + `rolGuard(...)`.

**La fuente es `frontend-web/src/app/app.routes.ts`, ruta por ruta.** El diagrama es el espejo de
ese archivo; si se agrega una ruta, se agrega un nodo. Eso es lo que lo hace defendible.

Cuatro cosas de maqueta, cada una encontrada rompiéndose:

- **Una banda por área funcional**: la vista arriba, su formulario debajo y el controlador a la
  derecha, centrado entre los dos. Así ninguna flecha cruza una caja.
- **El alto que se pide es un MÍNIMO, no una medida.** Si la clase tiene más atributos u
  operaciones de los que entran, **EA agranda la caja hacia abajo sin avisar** y se come la banda
  siguiente. El caso peor del Administrador —seis campos en el formulario de usuario, siete
  operaciones en el controlador de empleados— necesita 150 px de alto y 380 px de banda. Con 85 y
  230 se solapaban.
- **El corredor entre el menú y la columna de vistas tiene que ser ancho** —680 px—. Por ahí se
  abren en abanico las siete flechas `build` del tablero; si es angosto cruzan por encima de los
  formularios que quedan en el camino.
- **Nada de enlaces de vuelta: la navegación se dibuja en CADENA.** `Tablero –build→ Vista –build→
  Formulario –submit→ Controlador`. Si la vista apunta al controlador y el controlador de vuelta a
  la vista, EA escribe los dos rótulos en el mismo punto medio y sale `sbuild:` encima de `submit`.
  Y la vuelta ya está contada: `Tablero –build→ Vista` es el mismo `build` que hace el controlador
  al devolver la página.

---

### 7.14 Tiempo 3.2

**Tipo:** `Timing` · **Script:** `ea-tiempo-3-2.ps1`

**VA UNO POR CASO DE USO TRANSACCIONAL — corrección del 15/09/2026.** La línea de vida principal es
**la transacción** (`Inactiva → Autenticando → Validando → Escribiendo → Confirmada`), que es el
mismo reparto de los diagramas de secuencia y de las capas de 3.1.1. Un diagrama cuenta **un solo
escenario**: se elige la rama donde el reloj manda, no la más común. Ver
[`docs/diagramas/estado-navegacion-y-tiempo.md`](docs/diagramas/estado-navegacion-y-tiempo.md).

La línea de vida es un elemento **`TimeLine`**. `AddNew('...', 'StateLifeline')` y
`AddNew('...', 'ValueLifeline')` **fallan** con *«Referencia a objeto no establecida»*: esos dos
nombres no existen en la API, hay un solo tipo.

```powershell
$el = $pkg.Elements.AddNew('', 'TimeLine')
$el.ClassifierID = $idDeLaClase      # EA la rotula ": Reserva" y el vínculo queda vivo
$el.Name = ''                        # con clasificador puesto, si no lo escribe DOS veces
[void]$el.Update()
```

Las dos colecciones que hacen el dibujo **no aparecen en ninguna receta de Sparx** y se encontraron
mirando `$el | Get-Member`:

```powershell
# Las franjas del eje Y, de arriba hacia abajo, en el orden en que se agregan.
foreach ($nom in @('PENDIENTE','PREPARADA','ATENDIDA','EXPIRADA')) {
    $part = $el.Partitions.AddNew($nom, '')
    $part.Name = $nom
    $part.Size = 34
}
[void]$el.Update()

# Los escalones: a qué estado salta y en qué instante.
$tr = $el.StateTransitions.AddNew('PREPARADA', '')
$tr.TxState = 'PREPARADA'
$tr.TxTime  = 30
$tr.Event   = 'prepararReserva()  {CU-24}'
$tr.TimeConstraint = '{franja_fin + RESERVA_VIGENCIA_HORAS}'   # opcional
[void]$el.Update()
```

`Transition` también tiene `DurationConstraint` y `Note`. `Partition` tiene además `Operator`.

**Tres trampas, las tres silenciosas:**

1. **Ni `Partition` ni `Transition` tienen `Update()` propio.** Llamarlo tira
   *«no contiene ningún método llamado 'Update'»*. Se asignan las propiedades y se guarda con el
   `Update()` del **elemento**.
2. **`AddNew` persiste solo, y la colección vuelve a leerse en `0`.** `$el.Partitions.Count` da `0`
   aunque las franjas estén escritas y se dibujen. No sirve para verificar, y **correr el generador
   dos veces sobre el mismo elemento DUPLICA las franjas** —se ven los cuatro estados, y abajo los
   cuatro otra vez—. Por eso el elemento se crea nuevo en cada corrida y el paquete se rehace
   entero. Lo que sí se puede mirar es la fila de `t_xref` con `Name='Partitions'`, que guarda
   `@PAR;Name=...;Size=...;@ENDPAR;` por franja.
3. **La regla horizontal es fija, de 0 a 100**, estirada al ancho del elemento. `TxTime` va en esa
   escala, así que los números **son relativos** y no significan horas: hay que decirlo en la nota
   del diagrama.

**Y tres más, de la vuelta del 15/09:**

4. **La restricción va SIN llaves.** Las pone EA al dibujar; si se escriben en el dato salen
   dobles: `{{8 h}}`.
5. **El rótulo se dibuja hacia la derecha y EA no lo corta ni lo envuelve**, y pega la restricción
   al final del evento sin separación. Con la línea de vida angosta los rótulos consecutivos se
   pisan y el último se sale del marco. La receta que funciona: **`$ANCHO = 1400`** —unos 14 px por
   unidad de la regla—, rótulos **cortos**, restricciones de una o dos palabras, y la última marca
   en 84 como mucho. Lo que significa cada `{...}` va en la **nota del diagrama**, no en el rótulo.
6. **Las restricciones son lo único medible del diagrama, así que tienen que salir del código.**
   `{8 h}` es `ACCESS_TOKEN_EXPIRE_MINUTES` de `core/config.py:32`; `{RNF11}` y `{RNF02}` son
   requisitos no funcionales. Inventar milisegundos es peor que dejar la regla relativa y decirlo.

---

## 8. Exportar a PNG

```powershell
$prj = $ea.GetProjectInterface()
$ok  = $prj.PutDiagramImageToFile($dia.DiagramGUID, 'D:\...\salida.png', 1)
```

El tercer parámetro es el formato (`1` = PNG). Se pasa el **`DiagramGUID`**, no el `DiagramID`.

> **Marca de agua.** Con EA 15 **Trial**, algunas exportaciones salen con
> *"EA 15.0 Unregistered Trial Version"* y otras no, **sin patrón claro**. **Revisar cada PNG antes
> de pegarlo en el documento.** Si sale con marca, exportar de nuevo desde la interfaz
> (*Diagram → Save Image to File*) suele salir limpio.

Conviene imprimir, junto al resultado, cuántos objetos y cuántas relaciones **visibles** tenía el
diagrama:

```powershell
$visibles = ($d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
```

---

## 9. Catálogo de errores: síntoma → causa → arreglo

| Síntoma | Causa | Arreglo |
|---|---|---|
| Se ejecuta sin error pero **el modelo no cambió** | EA estaba abierto: su copia en memoria pisó lo escrito | Cerrar EA y volver a correr |
| Un **rectángulo relleno tapa** lo que tiene dentro; se ven líneas entrando a la nada | orden Z sin definir (999999) | `Sequence` alta al contenedor, baja al contenido |
| El orden Z **no cambia nada** y no hay error | `$dia.DiagramObjects` tiene la copia vacía de cuando se creó el diagrama | `$dia.DiagramObjects.Refresh()` **antes** del bucle |
| Aparecen **relaciones que no corresponden** al diagrama | EA dibuja toda relación entre elementos presentes | `DiagramLink.IsHidden = $true` |
| Quedan **relaciones ajenas visibles** aunque el generador las oculte | `Diagram.DiagramLinks` solo trae los enlaces que EA ya materializó: un conector creado por otro generador **después** del lienzo todavía no tiene fila, y sin fila se dibuja visible | listar por SQL los conectores con ambos extremos en el lienzo y, al que falte, crearle la fila con `DiagramLinks.AddNew('','')` + `ConnectorID` + `IsHidden` |
| Un diagrama recién generado muestra **0 enlaces visibles** en `t_diagramlinks` | falsa alarma: EA materializa las filas al abrir el diagrama, y **un conector sin fila se dibuja visible**; las filas que sí existen son justo las ocultas | contar `visibles = conectores en el lienzo − filas con `Hidden=True``, no las filas con `Hidden=False` |
| Elementos **duplicados o triplicados** tras varias corridas | `Package.Elements` no devuelve los `Package` | indexar por `t_object` con `$ea.SQLQuery` |
| Cientos de **conectores duplicados** | borrar un diagrama no borra sus conectores | deduplicar por par + tipo + nombre antes de crear |
| Cada elemento con **`(from OtroPaquete)`** debajo | el diagrama y el elemento están en paquetes distintos | mover el diagrama, o apagar la opción en EA |
| El **ícono redondo no desaparece** al cambiar el estereotipo | quedó `StereotypeEx = "entidad,entity"` | asignar `Stereotype` **y** `StereotypeEx` |
| El estereotipo `FORM` aparece **en minúscula** | EA lo empareja con su `form` propio, sin distinguir mayúsculas | borrar la fila `Stereotypes` de `t_xref` y forzar `Stereotype` |
| Las **cardinalidades no se guardan** | se llamó a `ClientEnd.Update()` antes del primer `Update()` del conector | `Update()` del conector → cardinalidades → `Update()` de cada extremo |
| Los **atributos salen alfabéticos** pese a fijar `Pos` | opción *ordenar características alfabéticamente* de EA | desactivarla en las preferencias |
| Los mensajes de comunicación se **amontonan en el punto medio** | se numeró a mano dentro del nombre | numerar con `PDATA4` |
| El fragmento `alt` **envuelve mensajes que no son** | EA remaquetó el diagrama al abrirlo con otra escala | usar `$Y_PRIMERO = -135` y `$PASO = 35` |
| Las **guardas salen con acentos rotos** | el SQL se armó por concatenación y ACE lo mandó en ANSI | pasar el texto por `Parameters.AddWithValue` |
| Los **operandos del fragmento** se reparten mal | la suma de los `Size` no da el alto de la caja | recalcular a partir de los cortes |
| `NullReferenceException` al asignar `Element.ParentID` | la API COM de EA 15 no lo soporta | escribir `t_object.ParentID` por OLEDB |
| El script falla **mucho después** del error real, sin sentido | una variable de bucle pisó un mapa (`$a` vs `$A`) | nombres de más de una letra para los mapas |
| `OleDbConnection.Open()` falla justo después de cerrar EA | el proceso todavía tiene el archivo | `ReleaseComObject` + `GC::Collect` + `Start-Sleep 1500` |
| Un array de un solo par se **aplana** | PowerShell aplana arrays de un elemento | `@( ,@($a, $b) )` con coma delante |
| El diagrama sale con **las cajas sueltas**: los elementos se ven pero **ninguna relación** | los `DiagramObject` quedaron con `Object_ID = 0`. Pasa cuando se guarda la referencia COM de un elemento y después se llama a `Elements.Refresh()`: la referencia se invalida y `.ElementID` devuelve 0 —y `.Name` y `.Type`, cadena vacía— | guardar el **identificador**, no el elemento, y releerlo del paquete justo antes de dibujar. No da error en ningún lado: se detecta con `SELECT COUNT(*) FROM t_diagramobjects WHERE Diagram_ID=<n> AND Object_ID=0` |
| Cada corrida **duplica** las asociaciones, pero no los `include` ni los `extend` | la deduplicación compara `$c.Stereotype -eq $estereotipo`. Para una `Association` el estereotipo del conector es **cadena vacía** y el parámetro llega como `$null`, y en PowerShell `'' -eq $null` es **falso** | castear los dos lados: `[string]$c.Stereotype -eq [string]$estereotipo` |
| Los **acentos de los nombres** salen como `automÃ¡ticos` en el diagrama exportado | el `.ps1` se guardó **sin BOM** y PowerShell 5.1 lo lee como ANSI (Windows-1252), no como UTF-8 | guardar el script en **UTF-8 con BOM** y volver a generar con `-Rehacer`. Es invisible al leer el archivo: se comprueba con `open(p,'rb').read(3) == b'ï»¿'` |
| `AddNew('...', 'StateLifeline')` o `'ValueLifeline'` tira **«Referencia a objeto no establecida»** | esos dos nombres no existen en la API: la línea de vida de un diagrama de tiempo es de tipo **`TimeLine`**, uno solo para las dos | `AddNew('', 'TimeLine')` y el clasificador aparte |
| Un `StateNode` **no se dibuja** y el lienzo queda con un hueco, sin ningún error | `Subtype` fuera del rango que EA 15 conoce: solo dibuja `100` (inicial), `101` (final) y `102` (punto de salida) | usar uno de esos tres |
| Las franjas del diagrama de tiempo **salen duplicadas** —los cuatro estados, y abajo los cuatro otra vez— | `Partitions.AddNew` persiste solo y `Partitions.Count` **vuelve a leerse en 0**, así que la deduplicación por conteo no ve nada | crear la línea de vida nueva en cada corrida y rehacer el paquete entero; para mirar lo escrito, `t_xref` con `Name='Partitions'` |
| `Update()` sobre una `Partition` o una `Transition` tira **«no contiene ningún método llamado 'Update'»** | no lo tienen: se guardan con el `Update()` del elemento que las contiene | asignar las propiedades y llamar a `$el.Update()` |
| La línea de vida del diagrama de tiempo se rotula **«Reserva: Reserva»** | se le puso `Name` **y** `ClassifierID`, y EA concatena los dos | dejar `Name = ''` cuando hay clasificador |

---

## 10. Lo que no se puede automatizar

Ninguna de estas se resuelve por script. Hay que hacerlas en EA, a mano:

- **Separar las etiquetas de mensajes que comparten enlace.** Con dos, EA las apila bien; con tres
  o cuatro se superponen. Un arrastre por etiqueta y quedan fijas. Se probó fijar la posición con
  `DiagramLink.Geometry` y EA la recalcula; `LayoutDiagramEx` **empeora** el diagrama.
- **El orden de los atributos**, si está activa la opción de ordenar alfabéticamente.
- **El rótulo `(from …)`** bajo los elementos, cuando el diagrama y el elemento están en paquetes
  distintos.
- **Cambiar el operador de un fragmento** de `alt` a `loop`, `opt` o `critical`.
- **La distribución del diagrama de navegación.** El mapa es un árbol con un nodo que dispara once
  flechas; el generador lo deja legible y sin cajas pisadas, pero apretarlo para que entre en una
  página del documento es a mano.
- **Acomodar y exportar.** Los generadores dejan una distribución razonable, no definitiva.

---

## 11. Checklist de verificación

Después de correr un generador, **antes** de exportar:

- [ ] El script imprimió el conteo de objetos y relaciones, y los números tienen sentido.
- [ ] Abrir el modelo en EA y mirar el diagrama **entero**, no la miniatura.
- [ ] Ningún contenedor tapa a sus hijos.
- [ ] No hay relaciones ajenas visibles.
- [ ] No hay elementos duplicados en el árbol del proyecto.
- [ ] En los de secuencia: **cada operando del `alt` envuelve exactamente los mensajes que le
      tocan**, después de que EA remaquetó al abrir.
- [ ] En los de comunicación: los grupos están numerados y coloreados por EA, no a mano.
- [ ] Los estereotipos se ven entre guillemets, y en el caso correcto.
- [ ] Las cardinalidades están en los dos extremos de cada asociación.
- [ ] El PNG exportado **no tiene la marca de agua** de la versión Trial.
- [ ] Cerrar EA antes de volver a correr cualquier script.

---

## 12. Cómo llevar esto a otro proyecto

1. **Copiar `scripts/ea-*.ps1`** al proyecto nuevo.
2. **Cambiar dos cosas en cada uno:** la variable `$modelo` (la ruta del `.eapx`) y el nombre del
   paquete raíz (`Get-OCrearPaquete $root 'Violet Boutique'`).
3. **Crear el modelo vacío** con `ea-cu-ciclo1.ps1 -Recrear`, que es el único que copia
   `EABase.eapx`. Los otros diez esperan que el modelo ya exista. **Ese `-Recrear` es una
   barrera a propósito:** el script destruye el `.eapx` completo, y sin la barrera se invoca
   igual que los aditivos.
4. **Reemplazar las tablas de datos.** Cada script tiene sus datos **declarados arriba**, separados
   de la lógica de dibujo: la lista de actores y casos de uso, la de paquetes, el guion de cada
   diagrama de secuencia, las entidades con sus columnas. Es lo único específico del proyecto.
5. **Correr en orden.** Hay dependencias reales entre generadores:

   ```
   ea-cu-ciclo1.ps1 -Recrear   crea el modelo, los actores y los casos de uso (DESTRUCTIVO)
        ↓
   ea-analisis-2-1.ps1     necesita los actores y los casos de uso
        ↓
   ea-comunicacion-2-2.ps1 necesita los actores; crea las clases «boundary/control/entity»
        ↓
   ea-clases-2-3.ps1       crea las clases «frontera/controlador/entidad»
        ↓
   ea-paquetes-2-4.ps1     independiente (crea sus propios elementos)
   ea-datos-3-3-1.ps1      independiente
   ea-capas-3-1-1.ps1      independiente
   ea-despliegue-3-1-2.ps1 independiente
        ↓
   ea-secuencia-3-2.ps1    NECESITA las clases de 2.3 (las enlaza por ClassifierID)
        ↓
   ea-componentes-4-2.ps1  independiente
   ea-componentes-4-3.ps1  independiente
   ```

6. **Respetar las diez reglas de oro.** Son las que costaron el tiempo.

---

## Apéndice · Ficha rápida

```
Modelo               docs/diagramas/VioletBoutique.eapx
Generadores          scripts/ea-*.ps1
Plantilla vacía      C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.eapx
Proveedor OLEDB      Microsoft.ACE.OLEDB.16.0
Correr               powershell -ExecutionPolicy Bypass -File scripts\ea-<x>.ps1 [-Rehacer]
Requisito absoluto   Enterprise Architect CERRADO

Coordenadas          l/r positivos hacia la derecha · t/b NEGATIVOS, más negativo = más abajo
                     r = l + ancho    ·    b = t - alto
Orden Z              Sequence más BAJO = más al FRENTE (sin definir vale 999999)
Color                t_diagramobjects.ObjectStyle += "BCol=<entero BGR>;"
                     BGR = azul*65536 + verde*256 + rojo
Contención           t_object.ParentID   (por COM lanza NullReferenceException)
Mensaje comunicación conector Collaboration + t_connector.PDATA4 = '<grupo>.<orden>'
Mensaje secuencia    conector Sequence + PtStartY/PtEndY + PDATA3 = 'Call' | 'Return'
Escala de secuencia  primer mensaje en -135, paso de 35 px  (la que EA impone al remaquetar)
Fragmento alt        InteractionFragment + t_object.NType = 0, PDATA1 = '6'
                     operandos en t_xref 'Partitions': @PAR;Name=…;Size=…;GUID={…};@ENDPAR;
                     la suma de los Size = alto exacto de la caja
Exportar             $ea.GetProjectInterface().PutDiagramImageToFile($dia.DiagramGUID, $ruta, 1)
```

---

*Última actualización: 13/09/2026. Verificado contra Enterprise Architect 15 Trial en Windows 11.*
