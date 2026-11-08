# =========================================================================
# 2DO PARCIAL - 3.3 Diagramas de Secuencia de la 3ra presentacion (CU-21 a CU-45).
# Copia de ea-secuencia-p2.ps1 (el de Karen): mismo dibujo, otros guiones, y SIN -Rehacer.
#
# ---- DE DONDE SALE ESTE FORMATO ----
# ICONIX: la secuencia sale de la robustez. Por eso:
#   - las lineas de vida son los mismos participantes del 3.2 del mismo CU
#     (paquete 'PARCIAL 2 - ICONIX > 3.2 Diagramas de Robustez'), ni uno mas;
#   - los mensajes son los que Mateo cargo en la robustez, con SU numeracion
#     de EA (1, 1.1, 1.2... 2, 2.1...), para seguir el mismo mensaje en los
#     dos diagramas;
#   - los retornos, que la robustez no tiene, van como sub-nivel del mensaje
#     que los provoca (1.3 -> 1.3.1) y se dibujan punteados.
#
# ---- LOS FRAGMENTOS COMBINADOS ----
# Cada uno sale de una estructura de control del codigo (ver
# docs/diagramas/secuencia-y-codigo.md, seccion 3):
#   alt      if / elif / else; raise excluyentes          (NType 0)
#   opt      if sin else                                    (NType 1)
#   break    raise temprano que abandona el resto           (NType 2)
#   loop     for, o el UPDATE que recorre varias filas      (NType 4)
#   critical try: ... commit / except: rollback             (NType 5)
# El guion los abre con t='alt'|'opt'|'break'|'loop'|'critical', los alt
# separan operandos con t='op', y todos cierran con t='fin'. Se anidan.
#
# ---- COMO SE MAQUETA ----
# Con la regla medida el 29/09 (scripts/ea-fragmentos-3-2.ps1): EA apila los
# mensajes por SeqNo de 35 en 35 desde -135 e ignora su altura guardada; solo
# baja un mensaje si caeria sobre la cabecera de una caja o la guarda de un
# operando. Las cajas y las notas quedan donde se guardan. Este script simula
# esa regla y pone cada caja alrededor de lo que le toca. NO SE ARRASTRA NADA
# A MANO EN EA: mover una caja corre todos los mensajes de abajo.
#
# Las lineas de vida van enlazadas por ClassifierID a las clases del 3.2; los
# actores se crean en el paquete 3.3 (regla 2 de la guia).
#
# ADITIVO: solo crea los diagramas que faltan. -Rehacer borra el paquete 3.3
# entero; -Solo 'CU-01','CU-05' limita a esos casos de uso.
#
# Se corre con el PowerShell de 64 bits (el proveedor ACE 16.0 solo esta ahi),
# con EA abierto SIN este archivo y su cuadro de inicio aceptado: el script
# usa ese EA, y la segunda pasada escribe directo en el .eapx. Primero sobre una copia (-Modelo copia.eapx) y mirar las imagenes.
# =========================================================================

param(
    [string]$Modelo = (Join-Path $PSScriptRoot '..\docs\diagramas\VioletBoutique.eapx'),
    [switch]$Rehacer,
    [string[]]$Solo,
    # Exporta un PNG por diagrama creado a esta carpeta, para revisarlos.
    [string]$Imagenes
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }
$Modelo = (Resolve-Path $Modelo).Path

# ---- Constantes de dibujo (medidas sobre lo que dibuja EA) ----
$X0        = 190    # borde izquierdo de la primera linea de vida
$GAP       = 45     # separacion horizontal entre lineas de vida
$TOP_LV    = -50    # borde superior de las lineas de vida
$Y_PRIMERO = -135   # primer mensaje
$PASO      = 35     # separacion entre mensajes
$AUTO      = 15     # lo que baja la flecha de vuelta de un auto-mensaje
$NOTA_L = 5; $NOTA_R = 120; $NOTA_ALTO = 50
$NTYPE = @{ alt = 0; opt = 1; break = 2; loop = 4; critical = 5 }

# =========================================================================
# GUION DE CADA CASO DE USO
#
# lineas : de izquierda a derecha. 'actor' crea (o reusa) el actor en el
#          paquete 3.3; 'clase' enlaza con la clase del 3.2.
# guion  : de arriba hacia abajo. t='nota' separa flujos; t='msg' con o/d
#          (claves de linea), n (texto) y ret=$true si es retorno.
# =========================================================================

# Los guiones de CU-21 a CU-45 estan en ea-secuencia-p3-<a..e>.datos.ps1 (los armaron agentes leyendo
# la robustez de scripts/p3_datos_<g>.py y el codigo). Cada archivo define $CASOS_P3.
$CASOS = @()
foreach ($g in 'a', 'b', 'c', 'd', 'e') {
    $f = Join-Path $PSScriptRoot "ea-secuencia-p3-$g.datos.ps1"
    if (Test-Path $f) { $CASOS_P3 = @(); . $f; $CASOS += $CASOS_P3 }
}

# =========================================================================
# MAQUETADO: donde va a dibujar EA cada mensaje, y las cajas alrededor.
#
# Medido el 25/10 exportando estos diagramas: EA apila los mensajes por SeqNo
# de 35 en 35 desde -135 y NO baja ninguno, ni por la cabecera de una caja ni
# por la guarda de un operando ni por un borde. (La regla del 29/09, que si
# bajaba algunos, dejaba aca los operandos corridos.) Asi que los mensajes
# quedan fijos y cada borde ---el de arriba de una caja, una divisoria entre
# operandos o el de abajo--- se pone en el HUECO entre dos mensajes seguidos.
# Si en un hueco caen varios bordes, se reparten parejo en el orden del guion.
# $pos: clave de linea -> @{ l; r } (bordes horizontales).
# =========================================================================
function Maquetar($cu, $pos) {
    $y = @(); $esAuto = @(); $notas = @(); $pendienteNota = $null
    $pila = New-Object System.Collections.ArrayList
    $frames = @(); $eventos = @(); $k = 0
    foreach ($p in $cu.guion) {
        switch ($p.t) {
            'nota' { $pendienteNota = $p.txt }
            'msg' {
                $yy = $Y_PRIMERO - $PASO * $k
                $y += $yy; $esAuto += ($p.o -eq $p.d)
                if ($pendienteNota) { $notas += @{ y = $yy; txt = $pendienteNota }; $pendienteNota = $null }
                foreach ($f in $pila) { $f.lv[$p.o] = $true; $f.lv[$p.d] = $true }
                $k++
            }
            { $_ -in 'alt', 'opt', 'break', 'loop', 'critical' } {
                $ops = New-Object System.Collections.ArrayList
                if ($p.t -ne 'alt') { [void]$ops.Add([string]$p.g) }
                $f = @{ tipo = $NTYPE[$p.t]; hondo = $pila.Count; cortes = New-Object System.Collections.ArrayList; ops = $ops; lv = @{}; desde = $k }
                [void]$pila.Add($f)
                $eventos += @{ hueco = $k; f = $f; que = 'top' }
            }
            'op' {
                $f = $pila[$pila.Count - 1]
                if ($f.ops.Count -gt 0) { $eventos += @{ hueco = $k; f = $f; que = 'corte' } }
                [void]$f.ops.Add($p.g)
            }
            'fin' {
                $f = $pila[$pila.Count - 1]; $pila.RemoveAt($pila.Count - 1)
                if ($k -eq $f.desde) { throw "$($cu.nombre): fragmento vacio" }
                $eventos += @{ hueco = $k; f = $f; que = 'bot' }
                $frames += $f
            }
        }
    }
    $n = $k
    # Cada hueco va desde la flecha del mensaje anterior (la de vuelta, si es
    # un auto-mensaje) hasta un poco arriba de la flecha del siguiente.
    foreach ($grupo in ($eventos | Group-Object { $_.hueco })) {
        $h = [int]$grupo.Name
        $arriba = if ($h -eq 0) { $y[0] + 40 } else { $y[$h - 1] - $(if ($esAuto[$h - 1]) { $AUTO } else { 0 }) - 3 }
        $abajo  = if ($h -lt $n) { $y[$h] + 5 } else { $arriba - 8 * ($grupo.Count + 1) }
        $i = 0
        foreach ($e in $grupo.Group) {
            $i++
            $pos_y = [int]($arriba - $i * ($arriba - $abajo) / ($grupo.Count + 1))
            switch ($e.que) { 'top' { $e.f.top = $pos_y } 'corte' { [void]$e.f.cortes.Add($pos_y) } 'bot' { $e.f.bot = $pos_y } }
        }
    }
    if ($pila.Count) { throw "$($cu.nombre): falta un 'fin'" }

    $x0 = [int]::MaxValue; $derecha = 0
    foreach ($key in $pos.Keys) { $x0 = [math]::Min($x0, $pos[$key].l); $derecha = [math]::Max($derecha, $pos[$key].r) }
    foreach ($f in $frames) {
        if ($f.tipo -eq 0) {
            # El 'alt' cruza el diagrama entero.
            $f.l = $x0 - 60 + 8 * $f.hondo
            $f.r = $derecha + 40 - 8 * $f.hondo
        } else {
            # Los demas abarcan solo las lineas de vida que tocan sus mensajes.
            $izq = [int]::MaxValue; $der = 0
            foreach ($key in $f.lv.Keys) { $izq = [math]::Min($izq, $pos[$key].l); $der = [math]::Max($der, $pos[$key].r) }
            if ($f.lv.Count -eq 1) { $der += 60 }
            $f.l = $izq - 15; $f.r = $der + 15
        }
        if ($f.ops.Count -ne $f.cortes.Count + 1) { throw "$($cu.nombre): operandos y cortes no cuadran" }
        $limites = @($f.top) + $f.cortes + @($f.bot)
        # EA lee los operandos de ABAJO hacia ARRIBA: se escriben al reves.
        $txt = ''
        for ($j = $f.ops.Count - 1; $j -ge 0; $j--) {
            $g = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
            $txt += "@PAR;Name=$($f.ops[$j]);Size=$($limites[$j] - $limites[$j + 1]);GUID=$g;@ENDPAR;"
        }
        $f.par = $txt
    }
    $bajo = ($y | Measure-Object -Minimum).Minimum - 60
    foreach ($f in $frames) { $bajo = [math]::Min($bajo, $f.bot - 30) }
    return @{ y = $y; notas = $notas; frames = $frames; bajo = $bajo }
}

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}
function Poner($dia, $el, $l, $r, $t, $b) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$r;t=$t;b=$b;", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# Con la version de prueba, un EA nuevo por COM falla (CO_E_SERVER_EXEC_FAILURE)
# hasta que se acepta su cuadro de inicio, y solo una vez. Si ya hay un EA
# abierto se usa ese: se le abre el modelo y al final se cierra el archivo,
# no EA.
function Abrir-EA {
    try { return @{ ea = [Runtime.InteropServices.Marshal]::GetActiveObject('EA.App').Repository; propio = $false } }
    catch { return @{ ea = (New-Object -ComObject EA.Repository); propio = $true } }
}
function Cerrar-EA($h) {
    $h.ea.CloseFile()
    if ($h.propio) { $h.ea.Exit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($h.ea) | Out-Null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}

$h = Abrir-EA; $ea = $h.ea
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
try {
    $root  = $ea.Models.GetAt(0)
    $pRaiz = Get-Paquete $root 'Violet Boutique'
    if (-not $pRaiz) { throw "No se encontro el paquete 'Violet Boutique'" }
    $pP2 = Get-Paquete $pRaiz 'PARCIAL 2 - ICONIX'
    if (-not $pP2) { throw "No se encontro 'PARCIAL 2 - ICONIX'" }
    $p32 = Get-Paquete $pP2 '3.2 Diagramas de Robustez'
    if (-not $p32) { throw "No se encontro el 3.2 de robustez del 2do parcial" }

    # Las clases del 3.2, por nombre y SOLO las de tipo Class: 'Usuario' y
    # 'Cliente' son tambien actores en ese paquete (trampa 4).
    $clase = @{}
    foreach ($e in $p32.Elements) { if ($e.Type -eq 'Class') { $clase[$e.Name] = $e } }

    $N33 = '3.3 Diagramas de Secuencia'
    if ($Rehacer) { throw 'Aca no hay -Rehacer: borraria la secuencia de CU-01 a CU-20. Borrar a mano.' }
    if ($false) {
        $pP2.Packages.Refresh()
        for ($i = $pP2.Packages.Count - 1; $i -ge 0; $i--) {
            if ($pP2.Packages.GetAt($i).Name -eq $N33) { $pP2.Packages.DeleteAt($i, $false); Write-Output "  [$N33] borrado (-Rehacer)" }
        }
        $pP2.Packages.Refresh()
    }
    $p33 = Get-Paquete $pP2 $N33
    if (-not $p33) { $p33 = $pP2.Packages.AddNew($N33, 'Package'); [void]$p33.Update(); $pP2.Packages.Refresh() }

    $actor = @{}
    foreach ($e in $p33.Elements) { if ($e.Type -eq 'Actor') { $actor[$e.Name] = $e } }

    $pendientes = @()
    foreach ($cu in $CASOS) {
        if ($Solo -and $Solo -notcontains $cu.cu) { continue }
        $ya = $null
        foreach ($d in $p33.Diagrams) { if ($d.Name -eq $cu.nombre) { $ya = $d } }
        if ($ya) { Write-Output "  $($cu.nombre) ya existe, no se toca"; continue }

        # ---- Lineas de vida y su posicion horizontal ----
        $lv = @{}; $pos = @{}; $x = $X0
        foreach ($def in $cu.lineas) {
            if ($def.ContainsKey('actor')) {
                if (-not $actor.ContainsKey($def.actor)) {
                    $a = $p33.Elements.AddNew($def.actor, 'Actor'); [void]$a.Update(); $p33.Elements.Refresh()
                    $actor[$def.actor] = $a
                }
                $el = $actor[$def.actor]; $ancho = 110
            } else {
                if (-not $clase.ContainsKey($def.clase)) { throw "$($cu.cu): falta la clase '$($def.clase)' en el 3.2" }
                $el = $p33.Elements.AddNew('', 'Sequence')
                $el.Name = ''
                $el.ClassifierID = $clase[$def.clase].ElementID
                [void]$el.Update()
                $ancho = [math]::Max(120, 8 * $def.clase.Length + 30)
            }
            $lv[$def.k] = $el
            $pos[$def.k] = @{ l = $x; r = $x + $ancho }
            $x += $ancho + $GAP
        }
        $p33.Elements.Refresh()

        $m = Maquetar $cu $pos

        $dia = $p33.Diagrams.AddNew($cu.nombre, 'Sequence'); [void]$dia.Update(); $p33.Diagrams.Refresh()
        foreach ($def in $cu.lineas) { Poner $dia $lv[$def.k] $pos[$def.k].l $pos[$def.k].r $TOP_LV $m.bajo }
        foreach ($n in $m.notas) {
            $nota = $p33.Elements.AddNew('', 'Note'); $nota.Notes = $n.txt; [void]$nota.Update()
            Poner $dia $nota $NOTA_L $NOTA_R ($n.y + 12) ($n.y + 12 - $NOTA_ALTO)
        }
        $frags = @()
        foreach ($f in $m.frames) {
            $fr = $p33.Elements.AddNew('', 'InteractionFragment'); [void]$fr.Update()
            Poner $dia $fr $f.l $f.r $f.top $f.bot
            $frags += @{ g = $fr.ElementGUID; tipo = $f.tipo; par = $f.par }
        }
        $p33.Elements.Refresh()

        # ---- Los mensajes ----
        $geo = @(); $seq = 1; $i = 0
        foreach ($p in $cu.guion) {
            if ($p.t -ne 'msg') { continue }
            $src = $lv[$p.o]; $dst = $lv[$p.d]
            $c = $src.Connectors.AddNew($p.n, 'Sequence')
            $c.SupplierID = $dst.ElementID
            $c.Direction = 'Source -> Destination'
            $c.DiagramID = $dia.DiagramID
            $c.SequenceNo = $seq
            [void]$c.Update(); $src.Connectors.Refresh()
            $ret = $p.ContainsKey('ret') -and $p.ret
            $ye = if ($p.o -eq $p.d) { $m.y[$i] - $AUTO } else { $m.y[$i] }
            $geo += @{ g = $c.ConnectorGUID; seq = $seq; y = $m.y[$i]; ye = $ye; ret = $ret }
            $seq++; $i++
        }
        $pendientes += @{ cu = $cu; diaId = $dia.DiagramID; guid = $dia.DiagramGUID; geo = $geo; frags = $frags }
        Write-Output ("  {0}: {1} lineas, {2} mensajes, {3} fragmentos" -f $cu.nombre, $cu.lineas.Count, $geo.Count, $frags.Count)
    }
} finally {
    Cerrar-EA $h
}
Start-Sleep -Milliseconds 1500
if ($pendientes.Count -eq 0) { Write-Output 'Nada nuevo'; Write-Output 'OK'; exit 0 }

# =========================================================================
# PARTE 2 - Lo que la API COM no expone, directo sobre el .eapx (EA cerrado)
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Modelo;")
$cn.Open()
function Exec($sql, $params) {
    $c = $cn.CreateCommand(); $c.CommandText = $sql
    if ($params) { foreach ($v in $params) { [void]$c.Parameters.AddWithValue('p', $v) } }
    return $c.ExecuteNonQuery()
}
function Scalar($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteScalar() }

foreach ($pend in $pendientes) {
    $cx = @{}
    $c = $cn.CreateCommand()
    $c.CommandText = "SELECT Object_ID, (RectLeft + RectRight) / 2 FROM t_diagramobjects WHERE Diagram_ID = $($pend.diaId)"
    $r = $c.ExecuteReader(); while ($r.Read()) { $cx[[int]$r[0]] = [int]$r[1] }; $r.Close()

    foreach ($x in $pend.geo) {
        $donde = "ea_guid = '$($x.g)'"
        $sx = $cx[[int](Scalar "SELECT Start_Object_ID FROM t_connector WHERE $donde")]
        $ex = $cx[[int](Scalar "SELECT End_Object_ID FROM t_connector WHERE $donde")]
        $tipo = if ($x.ret) { 'Return' } else { 'Call' }
        $flags = if ($x.seq -eq 1) { 'Activation=0;Initiate=1;ForceActivation=0;ExtendActivationUp=0;' } else { 'Activation=0;' }
        [void](Exec "UPDATE t_connector SET SeqNo = $($x.seq), PtStartX = $sx, PtStartY = $($x.y), PtEndX = $ex, PtEndY = $($x.ye), PDATA1 = 'Synchronous', PDATA2 = 'retval=void;', PDATA3 = '$tipo', StateFlags = '$flags' WHERE $donde")
    }
    foreach ($f in $pend.frags) {
        [void](Exec "UPDATE t_object SET NType = $($f.tipo), PDATA1 = '6' WHERE ea_guid = '$($f.g)'")
        # Un 'critical' no lleva guarda: sin la fila, EA no dibuja '[]'.
        if ($f.par -match 'Name=;' -and $f.par -notmatch 'Name=[^;]') { continue }
        # Los acentos por parametro (regla 9).
        $gx = '{' + [guid]::NewGuid().ToString().ToUpper() + '}'
        [void](Exec "INSERT INTO t_xref (XrefID, Name, Type, Visibility, Client, Description) VALUES ('$gx', 'Partitions', 'element property', 'Public', '$($f.g)', ?)" @($f.par))
    }

    # El estilo de los 3.2 del 1er parcial: Times New Roman en negrita, los
    # controles en naranja y las entidades en marron; fronteras, actores y
    # notas con el color de EA.
    $c = $cn.CreateCommand()
    # Las cajas quedan con la letra de EA: en negrita grande, la guarda de una
    # caja de un solo mensaje se pisa con el borde de abajo.
    $c.CommandText = "SELECT do.Object_ID, c.Stereotype FROM (t_diagramobjects do INNER JOIN t_object o ON o.Object_ID = do.Object_ID) LEFT JOIN t_object c ON c.Object_ID = o.Classifier WHERE do.Diagram_ID = $($pend.diaId) AND o.Object_Type <> 'InteractionFragment'"
    $r = $c.ExecuteReader(); $estilos = @{}
    while ($r.Read()) { $estilos[[int]$r[0]] = if ($r.IsDBNull(1)) { '' } else { [string]$r[1] } }
    $r.Close()
    foreach ($id in $estilos.Keys) {
        $bcol = switch ($estilos[$id]) { 'control' { 'BCol=13495295;' } 'entity' { 'BCol=8894686;' } default { '' } }
        $duid = ([guid]::NewGuid().ToString('N').Substring(0, 8)).ToUpper()
        [void](Exec "UPDATE t_diagramobjects SET ObjectStyle = 'DUID=$duid;${bcol}font=Times New Roman;bold=1;black=0;italic=0;ul=0;charset=0;pitch=18;fontsz=100;' WHERE Diagram_ID = $($pend.diaId) AND Object_ID = $id")
    }
    Write-Output "  $($pend.cu.nombre): geometria, retornos y operandos escritos"
}
$cn.Close()

# ---- Imagenes para revisar (opcional) ----
if ($Imagenes) {
    New-Item -ItemType Directory -Force $Imagenes | Out-Null
    $h = Abrir-EA; $ea = $h.ea
    [void]$ea.OpenFile($Modelo)
    $pi = $ea.GetProjectInterface()
    foreach ($pend in $pendientes) {
        $png = Join-Path $Imagenes "$($pend.cu.cu).png"
        [void]$pi.PutDiagramImageToFile($pend.guid, $png, 1)
    }
    Cerrar-EA $h
    Write-Output "  imagenes en $Imagenes"
}
Write-Output 'OK'
