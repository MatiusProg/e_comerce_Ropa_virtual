param(
    # Borra los paquetes 3.1 y 3.5 del 2do parcial (solo tienen lo que genera este script) y los rehace.
    [switch]$Rehacer
)

# =========================================================================
# 2DO PARCIAL - 3.1 MODELO DE DOMINIO y 3.5 DISENO DE LA BASE DE DATOS
#
# 3.1, corto (pedido de la ing): las entidades del dominio sin atributos, con
# sus asociaciones nombradas y la multiplicidad. Las del dispositivo (PWA y
# movil) van en otro color.
#
# 3.5, completo: las 51 tablas en cuatro partes, cada una con su nombre en
# MAYUSCULAS, todas sus columnas con el tipo de la base y «PK»/«FK», y las
# relaciones con un verbo en MAYUSCULAS y la cardinalidad que obliga la base
# (la convencion del 3.3.1 del 1er parcial, seccion 7.9 de la guia). Una tabla
# de otra parte se dibuja en gris y solo con su clave primaria. Las FK a
# EMPRESA de las tablas del tenant se dibujan solo en la parte 1; en las demas
# lo dice una nota y el estereotipo «rls».
#
# Un subpaquete por parte, con sus propias copias de las tablas, para que las
# relaciones de una parte no aparezcan en otra (reglas 2 y 3 de la guia).
#
# Datos: scripts/ea-p2-bd.datos.json (scripts/p2_bd_datos.py, que los lee de
# information_schema). PowerShell de 32 bits, EA cerrado.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if ($env:EA_MODELO) { $modelo = $env:EA_MODELO }   # para probar sobre una copia
$datos = Get-Content (Join-Path $PSScriptRoot 'ea-p2-bd.datos.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$N31 = '3.1 Modelo de Dominio'
$N35 = '3.5 Diseño de la Base de Datos'
$GRIS = 0xD9D9D9; $LOCAL = 0xF5E6D7   # BGR: gris y celeste claro

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}
function Nuevo-Paquete($padre, $nombre) {
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update(); $padre.Packages.Refresh(); return $p
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}
function Asociar($a, $b, $nombre, $ca, $cb) {
    $con = $a.Connectors.AddNew($nombre, 'Association')
    $con.SupplierID = $b.ElementID
    [void]$con.Update()
    $con.ClientEnd.Cardinality = $ca; [void]$con.ClientEnd.Update()
    $con.SupplierEnd.Cardinality = $cb; [void]$con.SupplierEnd.Update()
    [void]$con.Update()
    return $con
}

$root = $ea.Models.GetAt(0)
$pP2  = Get-Paquete (Get-Paquete $root 'Violet Boutique') 'PARCIAL 2 - ICONIX'
if ($Rehacer) {
    $pP2.Packages.Refresh()
    for ($i = $pP2.Packages.Count - 1; $i -ge 0; $i--) {
        $n = $pP2.Packages.GetAt($i).Name
        if ($n -eq $N31 -or $n -eq $N35) { Write-Output "Se borra [$n]"; $pP2.Packages.DeleteAt($i, $false) }
    }
    $pP2.Packages.Refresh()
}

# ------------------------------------------------------------------ 3.1 --
if (Get-Paquete $pP2 $N31) { Write-Output "  [$N31] ya existe, no se toca" } else {
    $p31 = Nuevo-Paquete $pP2 $N31
    $el = @{}
    foreach ($q in $datos.dominio.posiciones.PSObject.Properties) {
        $c = $q.Name
        $e = $p31.Elements.AddNew($c, 'Class'); [void]$e.Update()
        if ($datos.dominio.locales -contains $c) {
            $e.Notes = 'Vive en el dispositivo: IndexedDB en la PWA, SQLite en el móvil.'
            $e.SetAppearance(1, 0, $LOCAL); [void]$e.Update()
        }
        $el[$c] = $e
    }
    $p31.Elements.Refresh()
    $d = $p31.Diagrams.AddNew('3.1 Modelo de dominio', 'Logical'); [void]$d.Update(); $p31.Diagrams.Refresh()
    $derecha = 0
    foreach ($q in $datos.dominio.posiciones.PSObject.Properties) {
        $p = $q.Value; Poner $d $el[$q.Name] $p[0] $p[1] $p[2] $p[3]
        $derecha = [Math]::Max($derecha, $p[0] + $p[2])
    }
    $nota = $p31.Elements.AddNew('', 'Note')
    $nota.Notes = 'En celeste, lo que se guarda en el dispositivo para trabajar sin conexión (CU-13 a CU-18).'
    [void]$nota.Update(); Poner $d $nota ($derecha + 60) -40 200 70
    foreach ($a in $datos.dominio.asociaciones) { [void](Asociar $el[$a[0]] $el[$a[2]] $a[1] $a[3] $a[4]) }
    Write-Output ("  {0}: {1} clases, {2} asociaciones" -f $d.Name, $el.Count, @($datos.dominio.asociaciones).Count)
}

# ------------------------------------------------------------------ 3.5 --
# Clave de cada relacion: destino|origen|columna.
$rel = @{}
foreach ($r in $datos.relaciones) { $rel["$($r.destino)|$($r.origen)|$($r.columna)"] = $r }

$p35 = Get-Paquete $pP2 $N35
if (-not $p35) { $p35 = Nuevo-Paquete $pP2 $N35 }
foreach ($parte in $datos.partes) {
    if (Get-Paquete $p35 $parte.titulo) { Write-Output "  $($parte.titulo) ya existe, no se toca"; continue }
    $pkg = Nuevo-Paquete $p35 $parte.titulo
    $el = @{}
    foreach ($q in $parte.posiciones.PSObject.Properties) {
        $t = $q.Name; $stub = $parte.propias -notcontains $t
        $def = $datos.tablas.$t
        $e = $pkg.Elements.AddNew($def.nombre, 'Class')
        if ($def.rls -and -not $stub) { $e.Stereotype = 'rls' }
        $e.Notes = if ($stub) { 'Tabla de otra parte del diseño: aquí solo su clave primaria.' } else { "Tabla $t" }
        [void]$e.Update()
        # La PK primero, despues las demas en el orden de la tabla; Pos fija ese orden.
        $orden = @($def.columnas | Where-Object { $_.k -match 'PK' }) + @($def.columnas | Where-Object { $_.k -notmatch 'PK' })
        $i = 0
        foreach ($c in $orden) {
            if ($stub -and $c.k -notmatch 'PK') { continue }
            $at = $e.Attributes.AddNew($c.n, $c.t)
            $at.Visibility = 'Private'
            if ($c.k) { $at.Stereotype = $c.k }
            $at.Pos = $i; $i++
            [void]$at.Update()
        }
        $e.Attributes.Refresh()
        if ($stub) { $e.SetAppearance(1, 0, $GRIS); [void]$e.Update() }
        $el[$t] = $e
    }
    $pkg.Elements.Refresh()

    $d = $pkg.Diagrams.AddNew($parte.titulo, 'Logical'); [void]$d.Update(); $pkg.Diagrams.Refresh()
    $derecha = 0
    foreach ($q in $parte.posiciones.PSObject.Properties) {
        $p = $q.Value; Poner $d $el[$q.Name] $p[0] $p[1] $p[2] $p[3]
        $derecha = [Math]::Max($derecha, $p[0] + $p[2])
    }
    $nota = $pkg.Elements.AddNew('', 'Note')
    $nota.Notes = "«rls»: la tabla filtra por empresa con Row Level Security; su empresa_id apunta a EMPRESA (parte 1).`r`nEn gris: tabla de otra parte, solo con su clave primaria.`r`nCardinalidad según la base: 1 si la FK es NOT NULL, 0..1 si admite nulo; 0..1 del otro lado si la FK es UNIQUE."
    [void]$nota.Update(); Poner $d $nota ($derecha + 60) -40 260 120

    # Dos FK entre las mismas tablas (usuario_id y devuelto_por; venta_id y
    # venta_cambio_id) caerian una encima de la otra: la segunda va con un
    # quiebre, corrido del centro, para que se lean los dos verbos.
    $vistos = @{}
    foreach ($k in $parte.relaciones) {
        $r = $rel["$($k[0])|$($k[1])|$($k[2])"]
        $con = Asociar $el[$r.destino] $el[$r.origen] $r.verbo $r.card_destino $r.card_origen
        $par = "$($r.destino)|$($r.origen)"
        if ($vistos.ContainsKey($par)) {
            $a = $parte.posiciones.($r.destino); $b = $parte.posiciones.($r.origen)
            $mx = [int](($a[0] + $a[2] / 2 + $b[0] + $b[2] / 2) / 2) + 90
            $my = [int](($a[1] - $a[3] / 2 + $b[1] - $b[3] / 2) / 2) + 60
            $dl = $d.DiagramLinks.AddNew('', ''); $dl.ConnectorID = $con.ConnectorID
            $dl.Path = "${mx}:${my};"; [void]$dl.Update()
        }
        $vistos[$par] = $true
    }
    Write-Output ("  {0}: {1} tablas ({2} propias), {3} relaciones" -f $d.Name, $el.Count, @($parte.propias).Count, @($parte.relaciones).Count)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
