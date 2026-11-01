param(
    # Borra el paquete 3.4 entero (solo tiene lo que genera este script) y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# 2DO PARCIAL - 3.4 DISENO DE CLASES (CU-13 a CU-20)
#
# Lo que pide la ing (22/10 y 01/11):
#   - interfaz: todas las acciones de la pantalla;
#   - control: todos los metodos que usa el caso de uso (los del backend y,
#     sin conexion, los del controlador del dispositivo);
#   - entidad: sus columnas con el tipo de la base y sus metodos (las funciones
#     del repository.py); entre entidades, las FK reales;
#   - F3: un control visible y la referencia a la bitacora.
#
# Un SUBPAQUETE POR CASO DE USO, con sus propias copias de las clases: asi cada
# diagrama muestra solo las operaciones que usa ese caso (operaciones_en_cu) y
# las relaciones de un caso no aparecen en otro (reglas 2 y 3 de la guia).
#
# Estereotipos en castellano (interfaz, controlador, entidad): los de robustez
# en ingles harian que EA dibuje circulos en vez de la tabla con atributos y
# operaciones (seccion 5.9 de la guia).
#
# Datos: scripts/ea-p2-clases.datos.json (scripts/p2_clases_datos.py).
# PowerShell de 32 bits, EA cerrado.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
$datos  = Get-Content (Join-Path $PSScriptRoot 'ea-p2-clases.datos.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$casos  = (Get-Content (Join-Path $PSScriptRoot 'ea-p2.datos.json') -Raw -Encoding UTF8 | ConvertFrom-Json).casos
$N34 = '3.4 Diagramas de Clases'
$ESTEREOTIPO = @{ 'interfaz' = 'interfaz'; 'control' = 'controlador'; 'entidad' = 'entidad' }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}

# Parte "a, b<c, d>, e" por las comas de primer nivel.
function Partir($texto) {
    $out = @(); $nivel = 0; $actual = ''
    foreach ($ch in $texto.ToCharArray()) {
        if ($ch -in '<', '(', '[', '{') { $nivel++ }
        if ($ch -in '>', ')', ']', '}') { $nivel-- }
        if ($ch -eq ',' -and $nivel -eq 0) { $out += $actual.Trim(); $actual = '' } else { $actual += $ch }
    }
    if ($actual.Trim()) { $out += $actual.Trim() }
    return $out
}

function Nueva-Clase($pkg, $nombre, $def, $ops) {
    $e = $pkg.Elements.AddNew($nombre, 'Class')
    $st = $ESTEREOTIPO[$def.tipo]
    $e.Stereotype = $st; $e.StereotypeEx = $st
    $notas = "Origen: $($def.origen)"
    if ($def.tabla) { $notas += "`r`nTabla: $($def.tabla)" }
    if ($def.nota) { $notas += "`r`n$($def.nota)" }
    $e.Notes = $notas
    [void]$e.Update()
    foreach ($a in @($def.atributos)) {
        if (-not $a) { continue }
        $i = $a.IndexOf(':')
        if ($i -gt 0) { $n = $a.Substring(0, $i).Trim(); $t = $a.Substring($i + 1).Trim() } else { $n = $a; $t = '' }
        $at = $e.Attributes.AddNew($n, $t); [void]$at.Update()
    }
    foreach ($o in @($ops)) {
        if (-not $o) { continue }
        $o = ($o -replace '\s*\[[^\]]*\]\s*$', '')          # el [archivo] va solo en los datos
        $abre = $o.IndexOf('('); $cierra = $o.LastIndexOf(')')
        $n = $o.Substring(0, $abre).Trim()
        $params = $o.Substring($abre + 1, $cierra - $abre - 1)
        $resto = $o.Substring($cierra + 1).Trim()
        $ret = if ($resto.StartsWith(':')) { $resto.Substring(1).Trim() } else { '' }
        $m = $e.Methods.AddNew($n, $ret); [void]$m.Update()
        foreach ($p in (Partir $params)) {
            if (-not $p) { continue }
            $par = $m.Parameters.AddNew($p, $p); [void]$par.Update()   # EA imprime el tipo: va el texto entero
        }
        $m.Parameters.Refresh()
    }
    $e.Attributes.Refresh(); $e.Methods.Refresh()
    return $e
}

function Ancho($nombre, $def, $ops) {
    $largo = $nombre.Length + 14
    foreach ($a in @($def.atributos)) { if ($a -and $a.Length + 4 -gt $largo) { $largo = $a.Length + 4 } }
    foreach ($o in @($ops)) { if ($o) { $l = ($o -replace '\s*\[[^\]]*\]\s*$', '').Length + 4; if ($l -gt $largo) { $largo = $l } } }
    return [Math]::Max(170, [Math]::Min(560, [int]($largo * 6.4)))
}

function Alto($def, $ops) {
    return 56 + (@($def.atributos | Where-Object { $_ }).Count + @($ops | Where-Object { $_ }).Count) * 15
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# ------------------------------------------------------------- ubicacion --

$root  = $ea.Models.GetAt(0)
$pP2   = Get-Paquete (Get-Paquete $root 'Violet Boutique') 'PARCIAL 2 - ICONIX'
if ($Rehacer -and (Get-Paquete $pP2 $N34)) {
    $pP2.Packages.Refresh()
    for ($i = $pP2.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pP2.Packages.GetAt($i).Name -eq $N34) { Write-Output "Se borra [$N34]"; $pP2.Packages.DeleteAt($i, $false) }
    }
    $pP2.Packages.Refresh()
}
$p34 = Get-Paquete $pP2 $N34
if (-not $p34) { $p34 = $pP2.Packages.AddNew($N34, 'Package'); [void]$p34.Update(); $pP2.Packages.Refresh() }

foreach ($prop in $datos.cus.PSObject.Properties) {
    $cu = $prop.Name; $def = $prop.Value
    $nombreCu = ($casos | Where-Object { $_.id -eq $cu }).n
    $nombrePkg = "$cu $nombreCu"
    if (Get-Paquete $p34 $nombrePkg) { Write-Output "  $nombrePkg ya existe, no se toca"; continue }
    $pkg = $p34.Packages.AddNew($nombrePkg, 'Package'); [void]$pkg.Update(); $p34.Packages.Refresh()

    $el = @{}; $tam = @{}
    foreach ($ac in @($def.actores)) {
        $a = $pkg.Elements.AddNew($ac, 'Actor'); [void]$a.Update(); $el[$ac] = $a; $tam[$ac] = @(90, 110)
    }
    $usadas = @{}
    if ($def.operaciones_en_cu) { foreach ($q in $def.operaciones_en_cu.PSObject.Properties) { $usadas[$q.Name] = @($q.Value) } }
    foreach ($c in @($def.clases)) {
        $cd = $datos.clases.$c
        $ops = if ($usadas.ContainsKey($c)) { $usadas[$c] } else { @($cd.operaciones) }
        $el[$c] = Nueva-Clase $pkg $c $cd $ops
        $tam[$c] = @((Ancho $c $cd $ops), (Alto $cd $ops))
    }
    $pkg.Elements.Refresh()

    $d = $pkg.Diagrams.AddNew("3.4 $cu $nombreCu", 'Logical')
    if ($def.nota) { $d.Notes = $def.nota }
    [void]$d.Update(); $pkg.Diagrams.Refresh()

    # Columnas: actores | interfaces | controles | entidades (en dos columnas si son muchas).
    $porTipo = @{ 'interfaz' = @(); 'control' = @(); 'entidad' = @() }
    foreach ($c in @($def.clases)) { $porTipo[$datos.clases.$c.tipo] += $c }
    $columnas = @(, @($def.actores)) + @(, $porTipo['interfaz']) + @(, $porTipo['control'])
    $ents = $porTipo['entidad']
    if ($ents.Count -gt 4) {
        $mitad = [int][Math]::Ceiling($ents.Count / 2)
        $columnas += @(, $ents[0..($mitad - 1)]); $columnas += @(, $ents[$mitad..($ents.Count - 1)])
    } elseif ($ents.Count) { $columnas += @(, $ents) }

    $x = 30
    foreach ($col in $columnas) {
        if (-not $col -or $col.Count -eq 0) { continue }
        $ancho = ($col | ForEach-Object { $tam[$_][0] } | Measure-Object -Maximum).Maximum
        $y = -40
        foreach ($c in $col) { Poner $d $el[$c] $x $y $tam[$c][0] $tam[$c][1]; $y -= $tam[$c][1] + 50 }
        $x += $ancho + 110
    }
    $d.DiagramObjects.Refresh()

    foreach ($r in @($def.relaciones)) {
        $con = $el[$r[0]].Connectors.AddNew($r[2], 'Association')
        $con.SupplierID = $el[$r[1]].ElementID
        [void]$con.Update()
        $con.ClientEnd.Cardinality = $r[3]; [void]$con.ClientEnd.Update()
        $con.SupplierEnd.Cardinality = $r[4]; [void]$con.SupplierEnd.Update()
        [void]$con.Update()
    }
    Write-Output ("  {0,-60} {1,2} clases, {2,2} relaciones" -f $d.Name, @($def.clases).Count, @($def.relaciones).Count)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
