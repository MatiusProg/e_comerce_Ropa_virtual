param(
    # Borra el subpaquete 'Ciclo 2' de 3.3.1 y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 3 - 3.3.1 Diseno de Datos Logico. CICLO 2: el modelo de dominio con
# las ocho tablas nuevas y las nueve del Ciclo 1 a las que apuntan.
#
# EL CONTENIDO NO SE TRANSCRIBE A MANO. Las columnas, sus tipos y los
# estereotipos PK/FK salen de `information_schema` de la base construida con
# las migraciones; las genera gen-dominio-3-3-1.py en el archivo de datos que
# este script carga. Las cardinalidades salen de lo que la base OBLIGA ---
# NOT NULL y UNIQUE ---, no de la prosa.
#
# POR QUE UN SUBPAQUETE PROPIO
# ----------------------------
# Las entidades del Ciclo 1 ya existen en 3.3.1 con sus relaciones. Reusarlas
# tendria dos efectos, los dos malos (reglas 2 y 3):
#   - las relaciones NUEVAS quedarian colgadas de esos elementos y apareceria
#     una linea de mas en el diagrama del Ciclo 1, que ya esta acomodado;
#   - EA dibujaria tambien las relaciones VIEJAS entre ellas --- USUARIO-ROL,
#     SUCURSAL-CIUDAD --- que no vienen al caso aca.
# Es la misma decision que se tomo en 2.4.
#
# NO EXPORTA IMAGENES.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

. (Join-Path $PSScriptRoot 'ea-datos-3-3-1-ciclo2.datos.ps1')

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-OCrearPaqueteModelo($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    return $null
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
$pCap3 = Get-OCrearPaqueteModelo $pRaiz 'CAP. 3 - Flujo de Trabajo: Diseno'
$p331p = Get-OCrearPaqueteModelo $pCap3 '3.3.1 Diseno de Datos Logico'

if ($Rehacer) {
    for ($i = $p331p.Packages.Count - 1; $i -ge 0; $i--) {
        if ($p331p.Packages.GetAt($i).Name -eq 'Ciclo 2') {
            $p331p.Packages.DeleteAt($i, $false)
            Write-Output '  subpaquete Ciclo 2 anterior eliminado (-Rehacer)'
        }
    }
    $p331p.Packages.Refresh()
}
$p331 = Get-OCrearPaqueteModelo $p331p 'Ciclo 2'

# Regla 6: la lectura que no miente es SQL.
$yaEstan = @{}
$xml = $ea.SQLQuery("SELECT o.Object_ID AS id, o.Name AS nombre FROM t_object o WHERE o.Package_ID=$($p331.PackageID) AND o.Object_Type='Class'")
if ($xml) {
    $doc = New-Object System.Xml.XmlDocument
    $doc.LoadXml($xml)
    foreach ($fila in $doc.SelectNodes('//Row')) { $yaEstan["$($fila.nombre)"] = [int]$fila.id }
}
Write-Output "  ya habia $($yaEstan.Count) entidades en 3.3.1 / Ciclo 2"

function Get-OCrearEntidad($nombre, $notas) {
    if ($yaEstan.ContainsKey($nombre)) { return $ea.GetElementByID($yaEstan[$nombre]) }
    $e = $p331.Elements.AddNew($nombre, 'Class')
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p331.Elements.Refresh()
    $yaEstan[$nombre] = $e.ElementID
    return $e
}

# Cada columna es @{n=nombre; t=tipo; k='PK'|'FK'|'PK,FK'|$null}
function Set-Columnas($el, $lista) {
    $ya = @{}
    foreach ($a in $el.Attributes) { $ya[$a.Name] = $a }
    $i = 0
    foreach ($col in $lista) {
        if ($ya.ContainsKey($col.n)) { $at = $ya[$col.n] } else { $at = $el.Attributes.AddNew($col.n, $col.t) }
        $at.Type       = $col.t
        $at.Visibility = 'Private'
        $at.Pos        = $i
        if ($col.k) { $at.Stereotype = $col.k }
        [void]$at.Update()
        $i++
    }
    $el.Attributes.Refresh()
}

function New-Relacion($src, $dst, $verbo, $cardOrigen, $cardDestino) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq $verbo) { return }
    }
    $c = $src.Connectors.AddNew($verbo, 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update()                      # PRIMERO el conector...
    $c.ClientEnd.Cardinality = $cardOrigen # ...y despues los extremos, o EA
    $c.SupplierEnd.Cardinality = $cardDestino  # no guarda la cardinalidad
    [void]$c.ClientEnd.Update(); [void]$c.SupplierEnd.Update(); [void]$c.Update()
    $src.Connectors.Refresh()
}

# --- notas de cada entidad, que la base no tiene -------------------------
$NOTAS = @{
  'PRODUCTO'              = 'La prenda como concepto comercial. precio_base es el de referencia: el que se cobra es el de la variante.'
  'VARIANTE_PRODUCTO'     = 'La combinacion talla x color con su SKU. Es la unidad de negocio y lo unico que tiene existencia, reserva y venta (decision D1).'
  'IMAGEN_PRODUCTO'       = 'variante_id nulo = imagen del producto en general. es_transparente marca el PNG del vestidor virtual, uno por variante.'
  'EXISTENCIA'            = 'El saldo de una variante en una sucursal. Disponible y reservada van por separado: reservar TRASLADA unidades entre las dos, no las destruye (decision D3). stock_minimo es el umbral de reposicion de CU-16.'
  'MOVIMIENTO_INVENTARIO' = 'Historial INMUTABLE. El invariante D4 dice que cantidad_disponible es siempre la suma de las cantidades de sus movimientos, y de ahi sale el signo de cada tipo. usuario_id nulo = lo escribio un proceso automatico (CU-25).'
  'RESERVA'               = 'La cabecera: cliente, sucursal, franja horaria y estado. observacion es la nota de CIERRE, la escribe CU-23 al cancelar o CU-24 al atender.'
  'RESERVA_DETALLE'       = 'Una prenda apartada con su cantidad. resultado_prueba lo escribe CU-24 y es nulo mientras la reserva sigue viva.'
  'CLIENTE_CATEGORIA'     = 'Tabla puente de las categorias preferidas del cliente (CU-04). Resuelve el muchos-a-muchos: un uno-a-muchos no cabe como atributo.'
}

# --- crear todo -----------------------------------------------------------
$E = @{}
foreach ($t in $TABLAS_C2) {
    $E[$t.n] = Get-OCrearEntidad $t.n $NOTAS[$t.n]
    Set-Columnas $E[$t.n] $t.cols
}
foreach ($r in $RELACIONES_C2) {
    New-Relacion $E[$r.o] $E[$r.d] $r.v $r.co $r.cd
}
Write-Output "  $($TABLAS_C2.Count) entidades, $($RELACIONES_C2.Count) relaciones"

# --- el diagrama ----------------------------------------------------------
$nombre = '3.3.1 Modelo de Dominio - CICLO #2'
if (BuscarDiagrama $p331 $nombre) {
    Write-Output "  $nombre ya existe, no se toca"
} else {
    $d = $p331.Diagrams.AddNew($nombre, 'Logical')
    $d.Notes = 'Modelo de dominio del Ciclo 2: las ocho tablas nuevas y las del Ciclo 1 a las que apuntan sus claves foraneas.'
    [void]$d.Update(); $p331.Diagrams.Refresh()

    # Columnas agrupadas por paquete de analisis, de izquierda a derecha. Las
    # del Ciclo 1 van primero porque son a las que apuntan las demas: asi las
    # lineas cruzan en un solo sentido.
    $COLUMNAS = @(
        @{ x=40;   tablas=@('USUARIO','CLIENTE','SUCURSAL') },
        @{ x=360;  tablas=@('CATEGORIA','PROVEEDOR','TEMPORADA','COLECCION','TALLA','COLOR') },
        @{ x=680;  tablas=@('PRODUCTO','VARIANTE_PRODUCTO','IMAGEN_PRODUCTO','CLIENTE_CATEGORIA') },
        @{ x=1000; tablas=@('EXISTENCIA','MOVIMIENTO_INVENTARIO') },
        @{ x=1320; tablas=@('RESERVA','RESERVA_DETALLE') }
    )
    $ANCHO = 280

    $porNombre = @{}
    foreach ($t in $TABLAS_C2) { $porNombre[$t.n] = $t }

    $fondo = 0
    foreach ($col in $COLUMNAS) {
        $t = -40
        foreach ($n in $col.tablas) {
            # Alto por contenido: si queda corta, EA recorta la lista sin avisar.
            $alto = 60 + ($porNombre[$n].cols.Count * 18)
            Poner $d $E[$n] $col.x $t $ANCHO $alto
            $t = $t - $alto - 50
        }
        if ($t -lt $fondo) { $fondo = $t }
    }

    $nota = $p331.Elements.AddNew('', 'Note')
    $nota.Notes = @"
MODELO DE DOMINIO — CICLO 2

En blanco las ocho tablas que agrega este ciclo; a la izquierda, las del Ciclo 1 a las que apuntan sus claves foráneas —sin ellas las relaciones quedarían colgando—.

Las cardinalidades son las que la base OBLIGA, no las de la prosa: un extremo es 1 cuando la columna es NOT NULL y 0..1 cuando admite nulo; el otro es 0..1 cuando la columna es UNIQUE y 0..* cuando no.

Dos que conviene mirar en la defensa:
· EXISTENCIA lleva disponible y reservada POR SEPARADO. Reservar traslada unidades entre las dos y el total físico no cambia: la prenda sigue en la percha, solo que ya tiene dueño (decisión D3).
· MOVIMIENTO_INVENTARIO es historial inmutable, y cantidad_disponible es siempre la suma de las cantidades de sus movimientos (invariante D4). De ahí sale el signo de cada tipo: RESERVA vale −n y LIBERACION vale +n.
"@
    [void]$nota.Update()
    Poner $d $nota 40 ($fondo - 40) 900 260

    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output "  $nombre : $($d.DiagramObjects.Count) objetos, $($d.DiagramLinks.Count) relaciones"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
