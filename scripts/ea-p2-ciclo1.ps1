param(
    # Borra los paquetes 'Ciclo 1' de 2.5 y de 3.2 del 2do parcial y los vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# 2DO PARCIAL - CICLO 1 (CU-43 a CU-54)
#   2.5 Diagrama UML de casos de uso: uno del ciclo completo y uno por caso de uso.
#   3.2 Diagramas de robustez ICONIX: uno por caso de uso.
#
# DE DONDE SALEN LOS DATOS
#   scripts/ea-p2-ciclo1.datos.json, que arma scripts/p2_ciclo1_datos.py a
#   partir de las fichas del 2.6 del Word. El .py valida las reglas de
#   conexion de ICONIX antes de escribir el JSON: este generador no decide nada.
#
# POR QUE LA ROBUSTEZ NO ES COMO LOS 2.2 DEL 1ER PARCIAL
#   Ver docs/diagramas/iconix-robustez-vs-comunicacion.md. En resumen:
#   - sin mensajes numerados ni operaciones: solo enlaces (Association), a lo
#     sumo con una etiqueta corta con la accion del usuario o la condicion;
#   - un controlador por VERBO de la ficha, no un GestorX por caso de uso;
#   - una nota a la izquierda con el flujo normal y los alternativos;
#   - los controladores de los flujos alternativos en ROJO, en el mismo
#     diagrama, como en el ejemplo del PDF de la materia.
#   Sin mensajes, tampoco existe el problema de la punta de flecha (guia, 7.3).
#
# ADITIVO: si el paquete del ciclo ya existe no se toca; -Rehacer lo regenera.
# Los paquetes son autocontenidos (reglas 2 y 3 de la guia): actores y clases
# se crean aca, para que EA no rotule "(from ...)" ni dibuje relaciones ajenas.
#
# NO EXPORTA IMAGENES. EA tiene que estar cerrado, salvo la instancia vacia
# que se abre para poder conectarse por COM (ver memoria ea-trial-expirado).
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
$datos  = Get-Content (Join-Path $PSScriptRoot 'ea-p2-ciclo1.datos.json') -Raw -Encoding UTF8 | ConvertFrom-Json

$ROJO = 60 * 65536 + 60 * 256 + 230      # BGR de (230, 60, 60)

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

function Get-OCrearPaquete($padre, $nombre) {
    $p = Get-Paquete $padre $nombre
    if ($p) { return $p }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update(); $padre.Packages.Refresh(); return $p
}

function Quitar-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    for ($i = $padre.Packages.Count - 1; $i -ge 0; $i--) {
        if ($padre.Packages.GetAt($i).Name -eq $nombre) { $padre.Packages.DeleteAt($i, $false) }
    }
    $padre.Packages.Refresh()
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
function New-Conector($src, $dst, $tipo, $estereotipo, $nombre) {
    foreach ($par in @(@($src, $dst), @($dst, $src))) {
        $par[0].Connectors.Refresh()
        foreach ($c in $par[0].Connectors) {
            if ($c.SupplierID -eq $par[1].ElementID -and $c.ClientID -eq $par[0].ElementID -and
                $c.Type -eq $tipo -and [string]$c.Stereotype -eq [string]$estereotipo) { return $c.ConnectorID }
        }
        if ($tipo -ne 'Association') { break }   # include/generalizacion tienen sentido
    }
    $c = $src.Connectors.AddNew([string]$nombre, $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
    return $c.ConnectorID
}

# Regla 3: EA dibuja toda relacion entre elementos del lienzo. Se ocultan las
# que no son de este diagrama, preguntando por SQL (DiagramLinks no trae las
# que EA todavia no materializo).
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
if (-not $pRaiz) { throw "No se encontro el paquete 'Violet Boutique'." }
$pP2  = Get-OCrearPaquete $pRaiz 'PARCIAL 2 - ICONIX'
$p25  = Get-OCrearPaquete $pP2 '2.5 Diagrama de Casos de Uso'
$p32  = Get-OCrearPaquete $pP2 '3.2 Diagramas de Robustez'

if ($Rehacer) {
    Quitar-Paquete $p25 'Ciclo 1'
    Quitar-Paquete $p32 'Ciclo 1'
    Write-Output 'Paquetes Ciclo 1 de 2.5 y 3.2 borrados (-Rehacer).'
}

# =========================================================================
# 2.5 CASOS DE USO
# =========================================================================

if (Get-Paquete $p25 'Ciclo 1') {
    Write-Output '2.5 Ciclo 1 ya existe, no se toca'
} else {
    $pkg = Get-OCrearPaquete $p25 'Ciclo 1'
    $A = @{}
    foreach ($prop in $datos.actores.PSObject.Properties) {
        $e = New-Elemento $pkg $prop.Name 'Actor' $null $prop.Value.notas
        if ($prop.Value.abstracto) { $e.Abstract = '1'; [void]$e.Update() }
        $A[$prop.Name] = $e
    }
    $U = @{}
    foreach ($c in $datos.casos) { $U[$c.id] = New-Elemento $pkg "$($c.id) $($c.n)" 'UseCase' $null $c.notas }

    $mios = @{}
    foreach ($prop in $datos.actores.PSObject.Properties) {
        if ($prop.Value.padre) {
            $id = New-Conector $A[$prop.Name] $A[$prop.Value.padre] 'Generalization' $null $null
            $mios[[int]$id] = $true
        }
    }
    foreach ($c in $datos.casos) {
        foreach ($ac in $c.actores) { $mios[[int](New-Conector $A[$ac] $U[$c.id] 'Association' $null $null)] = $true }
        foreach ($inc in $c.incluye) { $mios[[int](New-Conector $U[$c.id] $U[$inc] 'Dependency' 'include' $null)] = $true }
    }

    # --- el modelo del ciclo completo ---
    $d = $pkg.Diagrams.AddNew('2.5 Ciclo 1 - Plataforma SaaS', 'UseCase'); [void]$d.Update(); $pkg.Diagrams.Refresh()
    Poner $d $A['Usuario'] 40 -560 90 110
    $hijos = @('Administrador de la plataforma', 'Empresa interesada', 'Administrador de la empresa',
               'Encargado de sucursal', 'Cajero', 'Proveedor', 'Cliente')
    $y = -60
    foreach ($h in $hijos) { Poner $d $A[$h] 260 $y 90 110; $y -= 175 }
    $y = -40
    foreach ($c in $datos.casos) {
        if ($c.id -eq 'CU-47') { continue }
        Poner $d $U[$c.id] 560 $y 280 70; $y -= 100
    }
    Poner $d $U['CU-47'] 980 -560 280 80
    $d.DiagramObjects.Refresh()
    [void](Ocultar-Ajenos $d $mios)
    Write-Output "  $($d.Name): $($d.DiagramObjects.Count) objetos"

    # --- uno por caso de uso ---
    foreach ($c in $datos.casos) {
        $d = $pkg.Diagrams.AddNew("2.5 $($c.id) $($c.n)", 'UseCase'); [void]$d.Update(); $pkg.Diagrams.Refresh()
        $y = -60
        foreach ($ac in $c.actores) { Poner $d $A[$ac] 40 $y 90 110; $y -= 160 }
        Poner $d $U[$c.id] 290 -80 260 90
        $y = -80
        foreach ($inc in $c.incluye) { Poner $d $U[$inc] 680 $y 260 90; $y -= 140 }
        $d.DiagramObjects.Refresh()
        $propios = @{}
        foreach ($ac in $c.actores) { $propios[[int](New-Conector $A[$ac] $U[$c.id] 'Association' $null $null)] = $true }
        foreach ($inc in $c.incluye) { $propios[[int](New-Conector $U[$c.id] $U[$inc] 'Dependency' 'include' $null)] = $true }
        $ocultos = Ocultar-Ajenos $d $propios
        Write-Output ("  {0,-52} {1} objetos, {2} ocultos" -f $d.Name, $d.DiagramObjects.Count, $ocultos)
    }
}

# =========================================================================
# 3.2 ROBUSTEZ
# =========================================================================

if (Get-Paquete $p32 'Ciclo 1') {
    Write-Output '3.2 Ciclo 1 ya existe, no se toca'
} else {
    $pkg = Get-OCrearPaquete $p32 'Ciclo 1'
    $el = @{}           # 'A:Nombre' para actores; el resto por nombre
    function Elemento($nombre, $tipo) {
        if ($el.ContainsKey($nombre)) { return $el[$nombre] }
        if ($nombre.StartsWith('A:')) {
            $e = New-Elemento $pkg $nombre.Substring(2) 'Actor' $null $null
        } else {
            $desc = $datos.descripcion.$nombre
            $e = New-Elemento $pkg $nombre 'Class' $tipo $desc
        }
        $el[$nombre] = $e
        return $e
    }

    $rojos = @()
    $porDiagrama = @()
    foreach ($r in $datos.robustez) {
        $tipoDe = @{}
        foreach ($x in $r.a)  { $tipoDe["A:$x"] = 'actor' }
        foreach ($x in $r.f)  { $tipoDe[$x] = 'boundary' }
        foreach ($x in $r.c)  { $tipoDe[$x] = 'control' }
        foreach ($x in $r.ca) { $tipoDe[$x] = 'control' }
        foreach ($x in $r.e)  { $tipoDe[$x] = 'entity' }
        foreach ($k in @($tipoDe.Keys)) { [void](Elemento $k $tipoDe[$k]) }

        $enlaces = @($r.l | ForEach-Object { , ($_ -split '\|') })
        $vecinos = @{}
        foreach ($p in $enlaces) {
            if (-not $vecinos.ContainsKey($p[0])) { $vecinos[$p[0]] = @() }
            if (-not $vecinos.ContainsKey($p[1])) { $vecinos[$p[1]] = @() }
            $vecinos[$p[0]] += $p[1]; $vecinos[$p[1]] += $p[0]
        }

        # --- disposicion: columnas y filas en medios pasos de 75 px ---
        # Ojo, regla 7: PowerShell no distingue mayusculas. Las columnas se
        # llamaban $X y los bucles 'foreach ($x ...)' las pisaban.
        # nota | actores | fronteras | alternativos (rojo) | flujo normal | entidades
        $colX = @{ actor = 360; boundary = 560; alt = 800; control = 1060; entity = 1320 }
        $fila = @{}
        $ocupado = @{ actor = @(); boundary = @(); alt = @(); control = @(); entity = @() }
        function Reservar($col, $deseada) {
            $s = [Math]::Max(0, $deseada)
            while ($true) {
                $libre = $true
                foreach ($o in $ocupado[$col]) { if ([Math]::Abs($o - $s) -lt 2) { $libre = $false; break } }
                if ($libre) { $ocupado[$col] += $s; return $s }
                $s++
            }
        }
        function FilaDeVecino($nombre, $preferidos) {
            foreach ($v in $vecinos[$nombre]) { if ($preferidos -contains $v -and $fila.ContainsKey($v)) { return $fila[$v] } }
            foreach ($v in $vecinos[$nombre]) { if ($fila.ContainsKey($v)) { return $fila[$v] } }
            return 0
        }
        for ($i = 0; $i -lt $r.c.Count; $i++) { $fila[$r.c[$i]] = Reservar 'control' (2 * $i) }
        foreach ($x in $r.ca) { $fila[$x] = Reservar 'alt' ((FilaDeVecino $x $r.c) + 1) }
        foreach ($x in $r.e)  { $fila[$x] = Reservar 'entity' (FilaDeVecino $x ($r.c + $r.ca)) }
        foreach ($x in $r.f)  { $fila[$x] = Reservar 'boundary' (FilaDeVecino $x $r.c) }
        foreach ($x in $r.a)  { $fila["A:$x"] = Reservar 'actor' (FilaDeVecino "A:$x" $r.f) }

        $d = $pkg.Diagrams.AddNew("3.2 $($r.cu) $($r.n)", 'Analysis')
        [void]$d.Update(); $pkg.Diagrams.Refresh()

        $nota = $pkg.Elements.AddNew('', 'Note')
        $nota.Notes = "$($r.cu) $($r.n)`r`n`r`n" + ($r.nota -replace "`n", "`r`n")
        [void]$nota.Update()
        $lineas = ($r.nota -split "`n").Count + 3
        Poner $d $nota 20 -40 300 ([Math]::Max(300, $lineas * 17 + 40))

        foreach ($k in $tipoDe.Keys) {
            $col = $tipoDe[$k]
            if ($r.ca -contains $k) { $col = 'alt' }
            $alto = 90; $ancho = 90
            if ($col -eq 'actor') { $ancho = 70 }
            Poner $d $el[$k] $colX[$col] (-60 - 75 * $fila[$k]) $ancho $alto
        }
        $d.DiagramObjects.Refresh()

        $mios = @{}
        foreach ($p in $enlaces) {
            $etq = if ($p.Count -gt 2) { $p[2] } else { $null }
            $id = New-Conector $el[$p[0]] $el[$p[1]] 'Association' $null $etq
            $mios[[int]$id] = $true
        }
        $ocultos = Ocultar-Ajenos $d $mios
        $porDiagrama += , @($d, $mios)
        foreach ($x in $r.ca) { $rojos += , @($d.DiagramID, $el[$x].ElementID) }
        Write-Output ("  {0,-52} {1,2} objetos, {2,2} enlaces, {3} ocultos" -f $d.Name, $d.DiagramObjects.Count, $mios.Count, $ocultos)
    }

    # Segunda vuelta de la regla 3: un enlace creado por un diagrama posterior
    # (CU-53 une 'Crear empresa con su suscripcion' con 'Usuario') aparece en
    # uno anterior que tiene los dos extremos en el lienzo (CU-43).
    $tarde = 0
    foreach ($par in $porDiagrama) { $tarde += Ocultar-Ajenos $par[0] $par[1] }
    Write-Output "  $tarde enlaces ajenos ocultos en la segunda vuelta"

    # Color de los alternativos: vive en t_diagramobjects.ObjectStyle (guia, 6.1).
    foreach ($par in $rojos) {
        $st = ''
        $f = Filas "SELECT ObjectStyle AS s FROM t_diagramobjects WHERE Diagram_ID=$($par[0]) AND Object_ID=$($par[1])"
        if ($f.Count -gt 0 -and $f[0].s) { $st = [string]$f[0].s }
        if ($st -notmatch 'BCol=') {
            $ea.Execute("UPDATE t_diagramobjects SET ObjectStyle='$st" + "BCol=$ROJO;' WHERE Diagram_ID=$($par[0]) AND Object_ID=$($par[1])")
        }
    }
    Write-Output "  $($rojos.Count) controladores alternativos en rojo"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
