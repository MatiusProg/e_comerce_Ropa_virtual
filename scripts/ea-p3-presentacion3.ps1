# =========================================================================
# 2DO PARCIAL - 3ra presentacion (08/11): CU-21 a CU-45
#   2.5 un diagrama de casos de uso por cada caso nuevo y un diagrama general
#       nuevo con CU-01 a CU-45 (el modelo de casos de uso completo);
#   3.2 la robustez de cada caso nuevo.
#   Es el mismo generador de la 2da presentacion (ea-p2-presentacion2.ps1),
#   con otros datos y la disposicion del general en dos columnas.
#
# POR QUE NO SE USA ea-p2.ps1
#   ea-p2.ps1 genera los paquetes 2.5 y 3.2 enteros: si existen no los toca, y
#   con -Rehacer los borra. Los de la 1ra presentacion ya tienen trabajo a mano
#   (los mensajes de la robustez, ajustes de Karen), asi que borrarlos no es
#   una opcion. Este generador es aditivo POR DIAGRAMA: reusa los elementos que
#   ya estan en el paquete (por nombre) y solo crea lo que falta. Se puede
#   correr las veces que haga falta.
#
# Los datos salen de scripts/ea-p3.datos.json (scripts/p3_datos.py).
# EA_MODELO apunta a una copia para probar.
# Se corre con el PowerShell de 32 bits y EA cerrado.
# =========================================================================

param(
    # Borra SOLO los diagramas de la 3ra presentacion (los de CU-21 a CU-45 y el
    # general nuevo) y los vuelve a generar. Los elementos se reusan.
    [switch]$Rehacer
)

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if ($env:EA_MODELO) { $modelo = $env:EA_MODELO }
$datos  = Get-Content (Join-Path $PSScriptRoot 'ea-p3.datos.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$NUEVOS = @(21..45 | ForEach-Object { 'CU-{0:D2}' -f $_ })
$GENERAL = '2.5 Diagrama general de casos de uso (CU-01 a CU-45)'

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------------------------------------------------------- helpers --

function Filas($sql) {
    $xml = $ea.SQLQuery($sql)
    $out = @()
    if ($xml) {
        $doc = New-Object System.Xml.XmlDocument
        $doc.LoadXml($xml)
        foreach ($f in $doc.SelectNodes('//Row')) { $out += $f }
    }
    return $out
}

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}

function Get-Diagrama($pkg, $nombre) {
    $pkg.Diagrams.Refresh()
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

function New-Elemento($pkg, $nombre, $tipo, $estereotipo, $notas) {
    $e = $pkg.Elements.AddNew($nombre, $tipo)
    if ($estereotipo) { $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo }
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $pkg.Elements.Refresh()
    return $e
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# Regla 5: se deduplica siempre, en los dos sentidos.
function New-Conector($src, $dst, $tipo, $estereotipo) {
    foreach ($par in @(@($src, $dst), @($dst, $src))) {
        $par[0].Connectors.Refresh()
        foreach ($c in $par[0].Connectors) {
            if ($c.SupplierID -eq $par[1].ElementID -and $c.ClientID -eq $par[0].ElementID -and
                $c.Type -eq $tipo -and [string]$c.Stereotype -eq [string]$estereotipo) { return $c.ConnectorID }
        }
        if ($tipo -ne 'Association') { break }
    }
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
    return $c.ConnectorID
}

# Regla 3: se ocultan las relaciones que no son de este diagrama.
function Ocultar-Ajenos($d, $mios) {
    $d.DiagramLinks.Refresh()
    $yaTienen = @{}
    foreach ($lnk in $d.DiagramLinks) { $yaTienen[[int]$lnk.ConnectorID] = $lnk }
    $n = 0
    $enLienzo = Filas @"
SELECT c.Connector_ID AS id FROM t_connector c
WHERE c.Start_Object_ID IN (SELECT o.Object_ID  FROM t_diagramobjects o  WHERE o.Diagram_ID=$($d.DiagramID))
  AND c.End_Object_ID   IN (SELECT o2.Object_ID FROM t_diagramobjects o2 WHERE o2.Diagram_ID=$($d.DiagramID))
"@
    foreach ($f in $enLienzo) {
        $id = [int]$f.id
        if ($mios.ContainsKey($id)) { continue }
        if ($yaTienen.ContainsKey($id)) { $lnk = $yaTienen[$id] }
        else { $lnk = $d.DiagramLinks.AddNew('', ''); $lnk.ConnectorID = $id }
        $lnk.IsHidden = $true
        if (-not $lnk.Update()) { throw "no se pudo ocultar el conector $id en $($d.Name)" }
        $n++
    }
    $d.DiagramLinks.Refresh()
    return $n
}

# ------------------------------------------------------------- ubicacion --

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-Paquete $root 'Violet Boutique'
$pP2   = Get-Paquete $pRaiz 'PARCIAL 2 - ICONIX'
$p25   = Get-Paquete $pP2 '2.5 Diagrama de Casos de Uso'
$p32   = Get-Paquete $pP2 '3.2 Diagramas de Robustez'
if (-not $p25 -or -not $p32) { throw 'Faltan los paquetes 2.5 o 3.2: correr antes ea-p2.ps1' }

if ($Rehacer) {
    foreach ($pkg in @($p25, $p32)) {
        $pkg.Diagrams.Refresh()
        for ($i = $pkg.Diagrams.Count - 1; $i -ge 0; $i--) {
            $n = $pkg.Diagrams.GetAt($i).Name
            if ($n -eq $GENERAL -or ($NUEVOS | Where-Object { $n -like "* $_ *" })) {
                Write-Output "  - se borra $n"; $pkg.Diagrams.DeleteAt($i, $false)
            }
        }
        $pkg.Diagrams.Refresh()
    }
}

# =========================================================================
# 2.5 CASOS DE USO
# =========================================================================

$A = @{}; $U = @{}
$p25.Elements.Refresh()
foreach ($e in $p25.Elements) {
    if ($e.Type -eq 'Actor') { $A[$e.Name] = $e }
    elseif ($e.Type -eq 'UseCase') { $U[$e.Name.Split(' ')[0]] = $e }
}
foreach ($prop in $datos.actores.PSObject.Properties) {
    if (-not $A.ContainsKey($prop.Name)) { $A[$prop.Name] = New-Elemento $p25 $prop.Name 'Actor' $null $prop.Value.notas }
}
foreach ($c in $datos.casos) {
    if (-not $U.ContainsKey($c.id)) {
        $U[$c.id] = New-Elemento $p25 "$($c.id) $($c.n)" 'UseCase' $null $c.notas
        Write-Output "  + caso de uso $($c.id)"
    }
}

# Las relaciones de todos los casos (New-Conector no duplica).
$relaciones = @{}
foreach ($prop in $datos.actores.PSObject.Properties) {
    if ($prop.Value.padre) {
        $relaciones[[int](New-Conector $A[$prop.Name] $A[$prop.Value.padre] 'Generalization' $null)] = $true
    }
}
foreach ($c in $datos.casos) {
    foreach ($ac in $c.actores) { $relaciones[[int](New-Conector $A[$ac] $U[$c.id] 'Association' $null)] = $true }
    foreach ($inc in $c.incluye) { $relaciones[[int](New-Conector $U[$c.id] $U[$inc] 'Dependency' 'include')] = $true }
    # «extend»: la flecha va del caso que extiende al caso base.
    foreach ($ext in @($c.extiende)) { if ($ext) { $relaciones[[int](New-Conector $U[$c.id] $U[$ext] 'Dependency' 'extend')] = $true } }
}

# --- uno por caso de uso nuevo ---
foreach ($c in $datos.casos) {
    if ($NUEVOS -notcontains $c.id) { continue }
    $nombre = "2.5 $($c.id) $($c.n)"
    if (Get-Diagrama $p25 $nombre) { Write-Output "  $nombre ya existe, no se toca"; continue }
    $d = $p25.Diagrams.AddNew($nombre, 'UseCase'); [void]$d.Update(); $p25.Diagrams.Refresh()
    $propios = @{}
    $y = -60
    foreach ($ac in $c.actores) {
        Poner $d $A[$ac] 40 $y 90 110; $y -= 160
        $propios[[int](New-Conector $A[$ac] $U[$c.id] 'Association' $null)] = $true
    }
    Poner $d $U[$c.id] 300 -80 280 90
    # Los relacionados: los que incluye, a los que extiende, y los que lo extienden o lo incluyen.
    $rel = @()
    foreach ($inc in @($c.incluye)) { if ($inc) { $rel += , @($inc, [int](New-Conector $U[$c.id] $U[$inc] 'Dependency' 'include')) } }
    foreach ($ext in @($c.extiende)) { if ($ext) { $rel += , @($ext, [int](New-Conector $U[$c.id] $U[$ext] 'Dependency' 'extend')) } }
    foreach ($otro in $datos.casos) {
        if (@($otro.extiende) -contains $c.id) { $rel += , @($otro.id, [int](New-Conector $U[$otro.id] $U[$c.id] 'Dependency' 'extend')) }
        if (@($otro.incluye) -contains $c.id) { $rel += , @($otro.id, [int](New-Conector $U[$otro.id] $U[$c.id] 'Dependency' 'include')) }
    }
    $y = -60
    foreach ($r in $rel) { Poner $d $U[$r[0]] 760 $y 280 90; $propios[$r[1]] = $true; $y -= 140 }
    $d.DiagramObjects.Refresh()
    $ocultos = Ocultar-Ajenos $d $propios
    Write-Output ("  {0,-60} {1} objetos, {2} ocultos" -f $d.Name, $d.DiagramObjects.Count, $ocultos)
}

# --- el general nuevo: el modelo de casos de uso completo, CU-01 a CU-45 ---
if (Get-Diagrama $p25 $GENERAL) {
    Write-Output "  $GENERAL ya existe, no se toca"
} else {
    $d = $p25.Diagrams.AddNew($GENERAL, 'UseCase'); [void]$d.Update(); $p25.Diagrams.Refresh()
    # Cada caso va con su actor principal (el primero de la lista). Los grupos se
    # reparten en dos columnas parejas: actores | casos  ||  casos | actores, asi
    # cada actor queda pegado a los suyos. Los casos sin actor (los incluidos,
    # como el CU-05) van al pie, entre las dos columnas, y el actor abstracto
    # Usuario arriba, al medio, con las generalizaciones.
    $ORDEN = @('Administrador de la plataforma', 'Empresa interesada', 'Administrador de la empresa',
               'Proveedor', 'Encargado de sucursal', 'Cajero', 'Cliente', 'Usuario', 'Sistema')
    $grupos = [ordered]@{}
    foreach ($act in $ORDEN) { $grupos[$act] = @() }
    $sinActor = @()
    foreach ($c in $datos.casos) {
        $prim = @($c.actores | Where-Object { $_ })
        if ($prim.Count -eq 0) { $sinActor += $c.id; continue }
        if (-not $grupos.Contains($prim[0])) { $grupos[$prim[0]] = @() }
        $grupos[$prim[0]] += $c.id
    }
    $lista = @($grupos.Keys | Where-Object { $grupos[$_].Count -gt 0 -or $_ -eq 'Proveedor' })
    $total = ($lista | ForEach-Object { [Math]::Max(1, $grupos[$_].Count) } | Measure-Object -Sum).Sum
    $izq = @(); $der = @(); $cuenta = 0
    foreach ($act in $lista) {
        if ($cuenta -lt $total / 2) { $izq += $act } else { $der += $act }
        $cuenta += [Math]::Max(1, $grupos[$act].Count)
    }
    $PASO = 100
    $alto = @{}
    $minY = 0
    foreach ($lado in @(@{ actores = $izq; xA = 40; xC = 300 }, @{ actores = $der; xA = 1640; xC = 1180 })) {
        $y = -200
        foreach ($act in $lado.actores) {
            $ys = @()
            $casosA = @($grupos[$act])
            if ($casosA.Count -eq 0) { $ys += $y; $y -= $PASO }
            foreach ($cu in $casosA) { Poner $d $U[$cu] $lado.xC $y 340 70; $alto[$cu] = $y; $ys += $y; $y -= $PASO }
            if ($A.ContainsKey($act)) {
                $medio = [int](($ys | Measure-Object -Average).Average) + 20
                Poner $d $A[$act] $lado.xA $medio 90 110
            }
            $y -= 50
        }
        if ($y -lt $minY) { $minY = $y }
    }
    # Los casos sin actor (los incluidos, como el CU-05) en una columna del medio, a la altura promedio
    # de los casos que los incluyen: asi las flechas «include» son cortas y no cruzan todo el diagrama.
    foreach ($cu in $sinActor) {
        $ys = @($datos.casos | Where-Object { @($_.incluye) -contains $cu -and $alto.ContainsKey($_.id) } | ForEach-Object { $alto[$_.id] })
        $yc = if ($ys.Count) { [int](($ys | Measure-Object -Average).Average) } else { $minY - 40 }
        Poner $d $U[$cu] 760 $yc 300 80
    }
    if (-not ($lista -contains 'Usuario')) { Poner $d $A['Usuario'] 860 -20 90 110 }
    $d.DiagramObjects.Refresh()
    [void](Ocultar-Ajenos $d $relaciones)
    Write-Output "  $($d.Name): $($d.DiagramObjects.Count) objetos ($($izq -join ', ') | $($der -join ', '))"
}

# =========================================================================
# 3.2 ROBUSTEZ
# =========================================================================

$el = @{}
$p32.Elements.Refresh()
foreach ($e in $p32.Elements) {
    $clave = if ($e.Type -eq 'Actor') { "A:$($e.Name)" } else { $e.Name }
    if (-not $el.ContainsKey($clave)) { $el[$clave] = $e }
}
function Elemento($nombre, $tipo) {
    if ($el.ContainsKey($nombre)) { return $el[$nombre] }
    if ($nombre.StartsWith('A:')) {
        $e = New-Elemento $p32 $nombre.Substring(2) 'Actor' $null $null
    } else {
        $e = New-Elemento $p32 $nombre 'Class' $tipo $datos.descripcion.$nombre
    }
    $el[$nombre] = $e
    return $e
}

$porDiagrama = @()
foreach ($r in $datos.robustez) {
    if ($NUEVOS -notcontains $r.cu) { continue }
    $nombre = "3.2 $($r.cu) $($r.n)"
    if (Get-Diagrama $p32 $nombre) { Write-Output "  $nombre ya existe, no se toca"; continue }

    $actores = @($r.a | ForEach-Object { "A:$_" })
    foreach ($k in $actores) { [void](Elemento $k 'actor') }
    foreach ($k in $r.f) { [void](Elemento $k 'boundary') }
    foreach ($k in $r.c) { [void](Elemento $k 'control') }
    foreach ($k in $r.e) { [void](Elemento $k 'entity') }

    $d = $p32.Diagrams.AddNew($nombre, 'Communication')
    [void]$d.Update(); $p32.Diagrams.Refresh()
    # Los controles en columnas por NIVEL: 1 = los que hablan con una pantalla,
    # 2 = los que llaman los del nivel 1, 3 = el resto. Con todos en una sola
    # columna, el enlace del gestor a un control lejano pasaba por encima de los
    # del medio. Las entidades se ordenan por la altura del control que las usa.
    $esF = @{}; foreach ($k in $r.f) { $esF[$k] = $true }
    $esC = @{}; foreach ($k in $r.c) { $esC[$k] = $true }
    $nivel = @{}
    foreach ($p in $r.pares) {
        foreach ($par in @(@($p[0], $p[1]), @($p[1], $p[0]))) {
            if ($esF.ContainsKey($par[0]) -and $esC.ContainsKey($par[1])) { $nivel[$par[1]] = 1 }
        }
    }
    for ($n = 1; $n -le 3; $n++) {
        foreach ($p in $r.pares) {
            foreach ($par in @(@($p[0], $p[1]), @($p[1], $p[0]))) {
                if ($nivel[$par[0]] -eq $n -and $esC.ContainsKey($par[1]) -and -not $nivel.ContainsKey($par[1])) {
                    $nivel[$par[1]] = [Math]::Min($n + 1, 3)
                }
            }
        }
    }
    foreach ($k in $r.c) { if (-not $nivel.ContainsKey($k)) { $nivel[$k] = 1 } }
    $niveles = @(1, 2, 3 | Where-Object { $nv = $_; @($r.c | Where-Object { $nivel[$_] -eq $nv }).Count -gt 0 })
    $columnas = @(
        @{ lista = $actores; x = 40;  ancho = 90;  alto = 100 },
        @{ lista = @($r.f);  x = 300; ancho = 100; alto = 100 }
    )
    $x = 580
    foreach ($nv in $niveles) {
        $columnas += @{ lista = @($r.c | Where-Object { $nivel[$_] -eq $nv }); x = $x; ancho = 100; alto = 100 }
        $x += 260
    }
    $paso = 190
    $maxN = (@($columnas | ForEach-Object { $_.lista.Count }) + @($r.e.Count) | Measure-Object -Maximum).Maximum
    $centro = -60 - [int](($maxN - 1) * $paso / 2)
    $yDe = @{}
    foreach ($col in $columnas) {
        $inicio = $centro + [int](($col.lista.Count - 1) * $paso / 2)
        for ($i = 0; $i -lt $col.lista.Count; $i++) {
            $t = $inicio - $i * $paso
            Poner $d $el[$col.lista[$i]] $col.x $t $col.ancho $col.alto
            $yDe[$col.lista[$i]] = $t
        }
    }
    # Cada entidad, a la altura promedio de los controles que la usan.
    $ents = @($r.e | Sort-Object -Descending {
        $e = $_; $ys = @()
        foreach ($p in $r.pares) {
            $otro = if ($p[0] -eq $e) { $p[1] } elseif ($p[1] -eq $e) { $p[0] } else { $null }
            if ($otro -and $yDe.ContainsKey($otro)) { $ys += $yDe[$otro] }
        }
        if ($ys.Count) { ($ys | Measure-Object -Average).Average } else { $centro }
    })
    $inicio = $centro + [int](($ents.Count - 1) * $paso / 2)
    for ($i = 0; $i -lt $ents.Count; $i++) { Poner $d $el[$ents[$i]] ($x + 60) ($inicio - $i * $paso) 100 100 }
    $d.DiagramObjects.Refresh()

    $mios = @{}
    foreach ($p in $r.pares) { $mios[[int](New-Conector $el[$p[0]] $el[$p[1]] 'Association' $null)] = $true }
    $ocultos = Ocultar-Ajenos $d $mios
    $porDiagrama += , @($d, $mios)
    Write-Output ("  {0,-60} {1,2} objetos, {2,2} enlaces, {3} ocultos" -f $d.Name, $d.DiagramObjects.Count, $mios.Count, $ocultos)
}
$tarde = 0
foreach ($par in $porDiagrama) { $tarde += Ocultar-Ajenos $par[0] $par[1] }
Write-Output "  $tarde enlaces ajenos ocultos en la segunda vuelta"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
