# =========================================================================
# Verificacion de los diagramas 2.2 del Ciclo 3. SOLO LECTURA.
#
# Busca dos cosas que un generador puede dejar mal sin que nada falle:
#
#   1. ELEMENTOS HUERFANOS: puestos en el lienzo y sin un solo mensaje. Se ven
#      como una caja suelta al costado, sin ninguna linea. Lo reporto Karen
#      sobre CU-37 el 20/09.
#   2. ENLACES SIN NOMBRE: la seccion 7.3 de la guia pide que los enlaces
#      `Association` de un diagrama de comunicacion se llamen `L1..Ln`. El
#      generador del Ciclo 2 no los nombra, y el del Ciclo 3 lo heredo.
#
# POR QUE NO USA SQL CON `JOIN`
# ------------------------------
# El primer intento consultaba `t_diagramlinks` con un `JOIN` y EA respondio
# «error de sintaxis en la clausula FROM»: el motor Jet del .eapx no lo
# acepta como uno espera, y encima el dialogo de error queda abierto y hay que
# cerrar EA a mano. El generador del Ciclo 2 ---que si funciona--- usa solo
# subconsultas con `IN`. Aca se va mas lejos y se usa el modelo de objetos,
# que es lo unico probado para leer `DiagramLinks`.
# =========================================================================

$ErrorActionPreference = 'Stop'
$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile('D:\UNI\SI2\Primer_Parcial\docs\diagramas\VioletBoutique.eapx')) {
    throw 'No se pudo abrir el modelo'
}

try {
    $root  = $ea.Models.GetAt(0)
    $pRaiz = $null
    foreach ($p in $root.Packages) { if ($p.Name -eq 'Violet Boutique') { $pRaiz = $p } }
    $pCap2 = $null
    foreach ($p in $pRaiz.Packages) { if ($p.Name -eq 'CAP. 2 - Flujo de Trabajo: Analisis') { $pCap2 = $p } }
    $p22 = $null
    foreach ($p in $pCap2.Packages) { if ($p.Name -eq '2.2 Analizar Casos de Uso') { $p22 = $p } }
    if (-not $p22) { throw "No se encontro el paquete '2.2 Analizar Casos de Uso'" }

    $delCiclo3 = @()
    foreach ($d in $p22.Diagrams) {
        if ($d.Name -match '2\.2 CU-(12|20|21|2[6-9]|3[0-9]|4[0-2]) ') { $delCiclo3 += $d }
    }

    Write-Output "Revisando $($delCiclo3.Count) diagramas del Ciclo 3"
    Write-Output ''

    $totalHuerfanos = 0
    $totalEnlaces   = 0
    $sinNombre      = 0

    foreach ($d in $delCiclo3) {
        $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()

        # Quien participa en algun mensaje de ESTE lienzo.
        $participan = @{}
        $enLienzo    = @{}
        foreach ($do in $d.DiagramObjects) { $enLienzo[[int]$do.ElementID] = $true }

        foreach ($lnk in $d.DiagramLinks) {
            $con = $ea.GetConnectorByID($lnk.ConnectorID)
            if ($lnk.IsHidden) { continue }
            if ($con.Type -eq 'Collaboration') {
                $participan[[int]$con.ClientID]   = $true
                $participan[[int]$con.SupplierID] = $true
            }
            elseif ($con.Type -eq 'Association') {
                $totalEnlaces++
                if (-not $con.Name) { $sinNombre++ }
            }
        }

        $huerfanos = @()
        foreach ($do in $d.DiagramObjects) {
            $el = $ea.GetElementByID($do.ElementID)
            if ($el.Type -eq 'Note') { continue }
            if (-not $participan.ContainsKey([int]$do.ElementID)) {
                $huerfanos += "$($el.Name) <<$($el.Stereotype)>>"
            }
        }

        if ($huerfanos.Count -gt 0) {
            $totalHuerfanos += $huerfanos.Count
            Write-Output $d.Name
            foreach ($h in $huerfanos) { Write-Output "    HUERFANO  $h" }
        }
    }

    Write-Output ''
    Write-Output "Huerfanos en total : $totalHuerfanos"
    Write-Output "Enlaces visibles   : $totalEnlaces"
    Write-Output "  sin nombre (la guia 7.3 pide L1..Ln): $sinNombre"
}
finally {
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
}
