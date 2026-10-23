param(
    # Borra los paquetes 2.5 y 3.2 del 2do parcial y los vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# 2DO PARCIAL (reemplaza a ea-p2-ciclo1.ps1)
#   2.5 Diagrama UML de casos de uso: uno general y uno por caso de uso.
#   3.2 Diagramas de robustez: uno por caso de uso.
#
# CORRECCIONES DE LA ING DEL 22/10 Y DECISION DE LUIS DEL 23/10
#   - los casos de uso se numeran desde el CU-01 y no hay ciclos: los paquetes
#     ya no tienen subpaquete 'Ciclo 1';
#   - la robustez se dibuja como nuestros diagramas de comunicacion del 1er
#     parcial (2.2): una pantalla, un Gestor por caso de uso y sus entidades, en
#     columnas; sin controladores alternativos en rojo;
#   - NUNCA se comunican dos entidades (lo valida scripts/p2_datos.py);
#   - el diagrama va SIN mensajes: solo los enlaces (Association) entre los que
#     se comunican. Los mensajes estan en
#     docs/diagramas/2do Parcial/3.2-robustez-mensajes.md y se cargan a mano.
#
# DE DONDE SALEN LOS DATOS
#   scripts/ea-p2.datos.json, que arma scripts/p2_datos.py. Este generador no
#   decide nada.
#
# ADITIVO: si el paquete ya existe no se toca; -Rehacer lo regenera.
# Los paquetes son autocontenidos (reglas 2 y 3 de la guia): actores y clases
# se crean aca, para que EA no rotule "(from ...)" ni dibuje relaciones ajenas.
#
# NO EXPORTA IMAGENES (eso es ea-p2-exportar.ps1). Se corre con el PowerShell
# de 32 bits, con EA abierto y el cuadro de «Aceptar» ya aceptado.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
$datos  = Get-Content (Join-Path $PSScriptRoot 'ea-p2.datos.json') -Raw -Encoding UTF8 | ConvertFrom-Json

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

function Listar-Diagramas($pkg, $sangria) {
    foreach ($d in $pkg.Diagrams) { Write-Output "$sangria$($d.Name)" }
    foreach ($sp in $pkg.Packages) { Write-Output "$sangria[$($sp.Name)]"; Listar-Diagramas $sp "$sangria  " }
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
        if ($tipo -ne 'Association') { break }   # include/generalizacion tienen sentido
    }
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
    return $c.ConnectorID
}

# Regla 3: EA dibuja toda relacion entre elementos del lienzo. Se ocultan las
# que no son de este diagrama, preguntando por SQL.
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
$pP2 = Get-OCrearPaquete $pRaiz 'PARCIAL 2 - ICONIX'
$N25 = '2.5 Diagrama de Casos de Uso'
$N32 = '3.2 Diagramas de Robustez'

if ($Rehacer) {
    foreach ($n in @($N25, $N32)) {
        $p = Get-Paquete $pP2 $n
        if ($p) { Write-Output "Se borra [$n]:"; Listar-Diagramas $p '    '; Quitar-Paquete $pP2 $n }
    }
}

# =========================================================================
# 2.5 CASOS DE USO
# =========================================================================

if (Get-Paquete $pP2 $N25) {
    Write-Output "$N25 ya existe, no se toca"
} else {
    $pkg = Get-OCrearPaquete $pP2 $N25
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
            $mios[[int](New-Conector $A[$prop.Name] $A[$prop.Value.padre] 'Generalization' $null)] = $true
        }
    }
    foreach ($c in $datos.casos) {
        foreach ($ac in $c.actores) { $mios[[int](New-Conector $A[$ac] $U[$c.id] 'Association' $null)] = $true }
        foreach ($inc in $c.incluye) { $mios[[int](New-Conector $U[$c.id] $U[$inc] 'Dependency' 'include')] = $true }
    }

    # --- el diagrama general ---
    $d = $pkg.Diagrams.AddNew('2.5 Diagrama general de casos de uso', 'UseCase'); [void]$d.Update(); $pkg.Diagrams.Refresh()
    Poner $d $A['Usuario'] 40 -560 90 110
    $hijos = @('Administrador de la plataforma', 'Empresa interesada', 'Administrador de la empresa',
               'Encargado de sucursal', 'Cajero', 'Proveedor', 'Cliente')
    $y = -60
    foreach ($h in $hijos) { Poner $d $A[$h] 260 $y 90 110; $y -= 175 }
    $y = -40
    foreach ($c in $datos.casos) {
        if ($c.id -eq 'CU-05') { continue }
        Poner $d $U[$c.id] 560 $y 280 70; $y -= 100
    }
    Poner $d $U['CU-05'] 980 -560 280 80
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
        foreach ($ac in $c.actores) { $propios[[int](New-Conector $A[$ac] $U[$c.id] 'Association' $null)] = $true }
        foreach ($inc in $c.incluye) { $propios[[int](New-Conector $U[$c.id] $U[$inc] 'Dependency' 'include')] = $true }
        $ocultos = Ocultar-Ajenos $d $propios
        Write-Output ("  {0,-52} {1} objetos, {2} ocultos" -f $d.Name, $d.DiagramObjects.Count, $ocultos)
    }
}

# =========================================================================
# 3.2 ROBUSTEZ, al estilo del diagrama de comunicacion
# =========================================================================

if (Get-Paquete $pP2 $N32) {
    Write-Output "$N32 ya existe, no se toca"
} else {
    $pkg = Get-OCrearPaquete $pP2 $N32
    $el = @{}           # 'A:Nombre' para actores; el resto por nombre
    function Elemento($nombre, $tipo) {
        if ($el.ContainsKey($nombre)) { return $el[$nombre] }
        if ($nombre.StartsWith('A:')) {
            $e = New-Elemento $pkg $nombre.Substring(2) 'Actor' $null $null
        } else {
            $e = New-Elemento $pkg $nombre 'Class' $tipo $datos.descripcion.$nombre
        }
        $el[$nombre] = $e
        return $e
    }

    $porDiagrama = @()
    foreach ($r in $datos.robustez) {
        $actores = @($r.a | ForEach-Object { "A:$_" })
        foreach ($k in $actores) { [void](Elemento $k 'actor') }
        foreach ($k in $r.f) { [void](Elemento $k 'boundary') }
        foreach ($k in $r.c) { [void](Elemento $k 'control') }
        foreach ($k in $r.e) { [void](Elemento $k 'entity') }

        # El tipo Communication es el de los 2.2 del 1er parcial: deja cargar los
        # mensajes a mano con su numeracion por grupos.
        $d = $pkg.Diagrams.AddNew("3.2 $($r.cu) $($r.n)", 'Communication')
        [void]$d.Update(); $pkg.Diagrams.Refresh()

        # actores | fronteras | controles | entidades, cada columna centrada en la
        # misma altura. Los circulos de robustez se inscriben en la caja: cuadrada.
        # Ojo, regla 7: PowerShell no distingue mayusculas; nada de $X frente a $x.
        $columnas = @(
            @{ lista = $actores; x = 40;   ancho = 90;  alto = 100 },
            @{ lista = @($r.f);  x = 320;  ancho = 100; alto = 100 },
            @{ lista = @($r.c);  x = 640;  ancho = 100; alto = 100 },
            @{ lista = @($r.e);  x = 960;  ancho = 100; alto = 100 }
        )
        $paso = 220
        $maxN = ($columnas | ForEach-Object { $_.lista.Count } | Measure-Object -Maximum).Maximum
        $centro = -60 - [int](($maxN - 1) * $paso / 2)
        foreach ($col in $columnas) {
            $inicio = $centro + [int](($col.lista.Count - 1) * $paso / 2)
            for ($i = 0; $i -lt $col.lista.Count; $i++) {
                Poner $d $el[$col.lista[$i]] $col.x ($inicio - $i * $paso) $col.ancho $col.alto
            }
        }
        $d.DiagramObjects.Refresh()

        $mios = @{}
        foreach ($p in $r.pares) {
            $id = New-Conector $el[$p[0]] $el[$p[1]] 'Association' $null
            $mios[[int]$id] = $true
        }
        $ocultos = Ocultar-Ajenos $d $mios
        $porDiagrama += , @($d, $mios)
        Write-Output ("  {0,-52} {1,2} objetos, {2,2} enlaces, {3} ocultos" -f $d.Name, $d.DiagramObjects.Count, $mios.Count, $ocultos)
    }

    # Segunda vuelta de la regla 3: un enlace creado por un diagrama posterior
    # aparece en uno anterior que tiene los dos extremos en el lienzo.
    $tarde = 0
    foreach ($par in $porDiagrama) { $tarde += Ocultar-Ajenos $par[0] $par[1] }
    Write-Output "  $tarde enlaces ajenos ocultos en la segunda vuelta"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
