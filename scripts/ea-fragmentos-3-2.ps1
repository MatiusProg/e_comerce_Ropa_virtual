# =========================================================================
# CAP. 3 - 3.2: reubica las cajas 'alt' y 'loop' y las notas de flujo de
# los diagramas de secuencia que YA existen, para que cada caja encierre
# exactamente los mensajes que le da el guion de ea-secuencia-3-2.ps1.
#
# ---- COMO DIBUJA EA UN DIAGRAMA DE SECUENCIA (medido el 29/09) ----
# Se exporto la imagen de los diagramas por COM y se comparo con lo guardado:
#   1. EA NO usa la altura guardada de los mensajes. Los apila por SeqNo de
#      35 en 35 arrancando en -135, y solo agrega espacio cuando un mensaje
#      caeria sobre la cabecera de una caja (la empuja ~27 por debajo del
#      borde de arriba).
#   2. Las cajas y las notas SI quedan donde estan guardadas.
#   Por eso el generador anterior, que dejaba huecos para las notas, veia
#   sus cajas corridas: EA cierra los huecos y las cajas quedan quietas.
#   Y por eso en EA mover una nota o una caja "mueve todo": se recalculan
#   los mensajes y las cajas de abajo ya no encierran lo mismo.
#   3. Los operandos de un 'alt' (t_xref 'Partitions') se leen de ABAJO
#      hacia ARRIBA: el ultimo @PAR es el operando de arriba.
#
# Este script simula esa regla: calcula donde va a poner EA cada mensaje y
# pone las cajas alrededor. Tambien escribe esa altura en los mensajes, para
# que lo guardado coincida con lo dibujado.
#
# Las notas van en una columna a la izquierda (x 5..120), fuera de todas las
# cajas: si una nota cae dentro de una caja, EA la trata como contenida y la
# arrastra con ella.
#
# Solo toca geometria de cajas, notas, mensajes y lineas de vida, y el texto
# de los operandos. No crea ni borra elementos. Si un diagrama no coincide
# con su guion (otra cantidad de cajas o mensajes con otro nombre) lo salta
# y lo dice.
#
#   .\ea-fragmentos-3-2.ps1 -Modelo <copia.eapx>            # todos
#   .\ea-fragmentos-3-2.ps1 -Modelo <copia.eapx> -Solo 'CU-01','CU-21'
#
# EA tiene que estar CERRADO sobre ese archivo.
# =========================================================================

param(
    [Parameter(Mandatory)] [string]$Modelo,
    [string[]]$Solo
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Modelo)) { throw "No existe $Modelo" }
$Modelo = (Resolve-Path $Modelo).Path

# ---- El guion sale del generador, sin ejecutarlo ----
$fuente = Get-Content (Join-Path $PSScriptRoot 'ea-secuencia-3-2.ps1') -Raw -Encoding UTF8
$ast = [System.Management.Automation.Language.Parser]::ParseInput($fuente, [ref]$null, [ref]$null)
$asg = $ast.Find({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$CASOS' }, $true)
$CASOS = Invoke-Expression $asg.Right.Extent.Text

# ---- Constantes medidas sobre lo que dibuja EA ----
$Y_PRIMERO = -135   # primer mensaje
$PASO      = 35     # separacion entre mensajes
$CABECERA  = 27     # lo que ocupa la cabecera de una caja ('alt', 'loop' + guarda)
$ETIQUETA  = 22     # lo que ocupa la guarda de un operando bajo la linea divisoria
$AUTO      = 15     # lo que baja la flecha de un auto-mensaje
$NOTA_L = 5; $NOTA_R = 120; $NOTA_ALTO = 50

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.12.0;Data Source=$Modelo;")
$cn.Open()
function Tabla($sql) { $a = New-Object System.Data.OleDb.OleDbDataAdapter($sql, $cn); $t = New-Object System.Data.DataTable; [void]$a.Fill($t); return $t.Rows }
function Exec($sql, $params) {
    $c = $cn.CreateCommand(); $c.CommandText = $sql
    if ($params) { foreach ($p in $params) { [void]$c.Parameters.AddWithValue('p', $p) } }
    return $c.ExecuteNonQuery()
}

$saltados = @()

foreach ($cu in $CASOS) {
    if ($Solo) {
        $cod = ($cu.nombre -split ' ')[1]
        if ($Solo -notcontains $cod) { continue }
    }
    # El nombre trae acentos que no pasan bien por SQL concatenado: se busca en memoria.
    $todos = Tabla "SELECT Diagram_ID, Name FROM t_diagram WHERE Diagram_Type = 'Sequence'"
    $filaDia = @($todos | Where-Object { $_.Name -eq $cu.nombre })
    if ($filaDia.Count -ne 1) { $saltados += "$($cu.nombre): hay $($filaDia.Count) diagramas con ese nombre"; continue }
    $dia = [int]$filaDia[0].Diagram_ID

    # ---- Lo que hay en el diagrama ----
    $msgsEA = @(Tabla "SELECT Connector_ID, SeqNo, Name, Start_Object_ID, End_Object_ID FROM t_connector WHERE DiagramID = $dia AND Connector_Type = 'Sequence' ORDER BY SeqNo")
    $objs = @(Tabla "SELECT do.Object_ID, o.Object_Type, o.NType, o.ea_guid, o.Name, o.Classifier, do.RectTop, do.RectLeft, do.RectRight, do.RectBottom FROM t_diagramobjects do INNER JOIN t_object o ON do.Object_ID = o.Object_ID WHERE do.Diagram_ID = $dia")
    $guionMsgs = @($cu.guion | Where-Object { $_.t -eq 'msg' })

    $mal = $null
    if ($msgsEA.Count -ne $guionMsgs.Count) { $mal = "$($msgsEA.Count) mensajes en EA y $($guionMsgs.Count) en el guion" }
    else {
        for ($i = 0; $i -lt $msgsEA.Count; $i++) {
            if ($msgsEA[$i].Name -ne $guionMsgs[$i].n) { $mal = "el mensaje $($i + 1) es '$($msgsEA[$i].Name)' y el guion dice '$($guionMsgs[$i].n)'"; break }
        }
    }
    $cajasEA = @{ 0 = @($objs | Where-Object { $_.Object_Type -eq 'InteractionFragment' -and $_.NType -eq 0 } | Sort-Object RectTop -Descending)
                  4 = @($objs | Where-Object { $_.Object_Type -eq 'InteractionFragment' -and $_.NType -eq 4 } | Sort-Object RectTop -Descending) }
    $notasEA = @($objs | Where-Object { $_.Object_Type -eq 'Note' } | Sort-Object RectTop -Descending)
    $nAlt = @($cu.guion | Where-Object { $_.t -eq 'alt' }).Count
    $nLoop = @($cu.guion | Where-Object { $_.t -eq 'loop' }).Count
    $nNota = @($cu.guion | Where-Object { $_.t -eq 'nota' }).Count
    if (-not $mal -and $cajasEA[0].Count -ne $nAlt) { $mal = "$($cajasEA[0].Count) 'alt' en EA y $nAlt en el guion" }
    if (-not $mal -and $cajasEA[4].Count -ne $nLoop) { $mal = "$($cajasEA[4].Count) 'loop' en EA y $nLoop en el guion" }
    if (-not $mal -and $notasEA.Count -ne $nNota) { $mal = "$($notasEA.Count) notas en EA y $nNota en el guion" }
    if ($mal) { $saltados += "$($cu.nombre): $mal"; continue }

    # ---- Lineas de vida: posicion horizontal por clave del guion ----
    # Se reconocen por los extremos de los mensajes que el guion les atribuye.
    $objDe = @{}
    for ($i = 0; $i -lt $msgsEA.Count; $i++) {
        $objDe[$guionMsgs[$i].o] = [int]$msgsEA[$i].Start_Object_ID
        $objDe[$guionMsgs[$i].d] = [int]$msgsEA[$i].End_Object_ID
    }
    $rect = @{}; foreach ($o in $objs) { $rect[[int]$o.Object_ID] = $o }
    $derecha = 0; $x0 = [int]::MaxValue
    foreach ($o in $objs | Where-Object { $_.Object_Type -in 'Actor', 'Sequence' }) {
        $derecha = [math]::Max($derecha, [int]$o.RectRight); $x0 = [math]::Min($x0, [int]$o.RectLeft)
    }

    # ---- Simulacion ----
    $y = @(); $piso = $Y_PRIMERO + $PASO   # altura del "mensaje anterior" virtual
    $fondo = $piso                          # lo mas bajo ocupado por el anterior
    $limite = 0                             # nada puede ir por encima de esto (cabeceras, etiquetas)
    $pendienteNota = $false; $notas = @()
    $pila = New-Object System.Collections.ArrayList
    $frames = @()
    $ultimoTopAbierto = $null               # tope de la caja abierta despues del ultimo mensaje
    $k = 0
    foreach ($p in $cu.guion) {
        switch ($p.t) {
            'nota' { $pendienteNota = $true; $notaTxt = $p.txt }
            'msg' {
                $yy = $piso - $PASO
                if ($limite -lt 0 -and $yy -gt $limite) { $yy = $limite }
                $y += $yy
                $auto = ($p.o -eq $p.d)
                $piso = $yy; $fondo = $yy - $(if ($auto) { $AUTO } else { 0 })
                if ($pendienteNota) { $notas += $yy; $pendienteNota = $false }
                foreach ($f in $pila) { $f.lv[$p.o] = $true; $f.lv[$p.d] = $true }
                $limite = 0; $ultimoTopAbierto = $null; $k++
            }
            { $_ -in 'alt', 'loop' } {
                if ($null -ne $ultimoTopAbierto) { $top = $ultimoTopAbierto - 6 }   # anidada: justo adentro
                elseif ($limite -lt 0) { $top = $limite - 4 }                        # justo bajo una guarda
                else { $top = $fondo - 8 }
                $ultimoTopAbierto = $top
                $limite = $top - $CABECERA
                $tipo = if ($p.t -eq 'alt') { 0 } else { 4 }
                $ops = New-Object System.Collections.ArrayList; if ($tipo -eq 4) { [void]$ops.Add($p.g) }
                [void]$pila.Add(@{ tipo = $tipo; top = $top; hondo = $pila.Count; cortes = @(); ops = $ops; lv = @{}; desde = $k })
            }
            'op' {
                $f = $pila[$pila.Count - 1]
                if ($f.ops.Count -gt 0) {
                    $corte = $fondo - 10
                    $f.cortes += $corte
                    $limite = $corte - $ETIQUETA
                }
                [void]$f.ops.Add($p.g)
            }
            'fin' {
                $f = $pila[$pila.Count - 1]; $pila.RemoveAt($pila.Count - 1)
                if ($k -eq $f.desde) { throw "$($cu.nombre): fragmento vacio" }
                $bot = $fondo - 12
                # Si otra caja cerro justo antes (anidada), esta cierra un poco mas abajo.
                if ($script:ultimoBot -and $script:ultimoBotK -eq $k) { $bot = [math]::Min($bot, $script:ultimoBot - 6) }
                $script:ultimoBot = $bot; $script:ultimoBotK = $k
                $f.bot = $bot
                $fondo = $bot; $piso = [math]::Min($piso, $bot + 20)   # el siguiente mensaje queda >= 15 bajo el borde
                $frames += $f
            }
        }
    }
    $script:ultimoBot = $null

    # ---- Horizontal y operandos ----
    foreach ($f in $frames) {
        if ($f.tipo -eq 0) {
            $f.l = $x0 - 60 + 8 * $f.hondo
            $f.r = $derecha + 40 - 8 * $f.hondo
        } else {
            $izq = [int]::MaxValue; $der = 0
            foreach ($key in $f.lv.Keys) { $r = $rect[$objDe[$key]]; $izq = [math]::Min($izq, [int]$r.RectLeft); $der = [math]::Max($der, [int]$r.RectRight) }
            if ($f.lv.Count -eq 1) { $der += 60 }
            $f.l = $izq - 15; $f.r = $der + 15
        }
        if ($f.ops.Count -ne $f.cortes.Count + 1) { throw "$($cu.nombre): operandos y cortes no cuadran" }
        $limites = @($f.top) + $f.cortes + @($f.bot)
        $partes = @()
        for ($i = 0; $i -lt $f.ops.Count; $i++) {
            $partes += @{ n = $f.ops[$i]; s = $limites[$i] - $limites[$i + 1] }
        }
        $f.partes = $partes
    }

    # ---- Escribir ----
    $frOrden = @{ 0 = @($frames | Where-Object { $_.tipo -eq 0 } | Sort-Object { $_.top } -Descending)
                  4 = @($frames | Where-Object { $_.tipo -eq 4 } | Sort-Object { $_.top } -Descending) }
    foreach ($t in 0, 4) {
        for ($i = 0; $i -lt $frOrden[$t].Count; $i++) {
            $f = $frOrden[$t][$i]; $o = $cajasEA[$t][$i]
            [void](Exec "UPDATE t_diagramobjects SET RectTop = $($f.top), RectBottom = $($f.bot), RectLeft = $($f.l), RectRight = $($f.r) WHERE Diagram_ID = $dia AND Object_ID = $($o.Object_ID)")
            # Se conservan los GUID de operando que ya tenia; EA lee de abajo hacia arriba.
            $viejo = [string]@(Tabla "SELECT Description FROM t_xref WHERE Client = '$($o.ea_guid)' AND Name = 'Partitions'")[0].Description
            $guids = @([regex]::Matches($viejo, 'GUID=(\{[^}]+\})') | ForEach-Object { $_.Groups[1].Value })
            $txt = ''
            for ($j = $f.partes.Count - 1; $j -ge 0; $j--) {
                $g = if ($j -lt $guids.Count) { $guids[$j] } else { '{' + [guid]::NewGuid().ToString().ToUpper() + '}' }
                $txt += "@PAR;Name=$($f.partes[$j].n);Size=$($f.partes[$j].s);GUID=$g;@ENDPAR;"
            }
            [void](Exec "UPDATE t_xref SET Description = ? WHERE Client = '$($o.ea_guid)' AND Name = 'Partitions'" @($txt))
        }
    }
    for ($i = 0; $i -lt $notasEA.Count; $i++) {
        $top = $notas[$i] + 12
        [void](Exec "UPDATE t_diagramobjects SET RectTop = $top, RectBottom = $($top - $NOTA_ALTO), RectLeft = $NOTA_L, RectRight = $NOTA_R WHERE Diagram_ID = $dia AND Object_ID = $($notasEA[$i].Object_ID)")
    }
    for ($i = 0; $i -lt $msgsEA.Count; $i++) {
        $yy = $y[$i]; $ye = if ($guionMsgs[$i].o -eq $guionMsgs[$i].d) { $yy - $AUTO } else { $yy }
        [void](Exec "UPDATE t_connector SET PtStartY = $yy, PtEndY = $ye WHERE Connector_ID = $($msgsEA[$i].Connector_ID)")
    }
    $bajo = ($y | Measure-Object -Minimum).Minimum - 60
    $bajo = [math]::Min($bajo, (($frames | ForEach-Object { $_.bot }) + 0 | Measure-Object -Minimum).Minimum - 30)
    foreach ($o in $objs | Where-Object { $_.Object_Type -in 'Actor', 'Sequence' }) {
        [void](Exec "UPDATE t_diagramobjects SET RectBottom = $bajo WHERE Diagram_ID = $dia AND Object_ID = $($o.Object_ID)")
    }
    Write-Output ("  {0}: {1} mensajes, {2} alt, {3} loop, {4} notas" -f $cu.nombre, $msgsEA.Count, $nAlt, $nLoop, $notasEA.Count)
}

$cn.Close()
if ($saltados.Count) { Write-Output ''; Write-Output 'SALTADOS (no coinciden con su guion, no se tocaron):'; $saltados | ForEach-Object { Write-Output "  $_" } }
Write-Output 'OK'
