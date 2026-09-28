# =========================================================================
# ARREGLO PUNTUAL - 2.4 Analisis de Paquetes, CICLO 2: sus dos notas.
#
# ---- PRIMER PROBLEMA (20/09): NO ESTABAN ----
# El diagrama quedo con sus seis paquetes y SIN las dos notas de cohesion y
# acoplamiento, que es literalmente de lo que trata el punto 2.4. Su propio
# generador las agrega al final, pero el diagrama ya existia cuando esa
# parte se escribio y el guardia «si ya existe, no se toca» impide que una
# nueva corrida las ponga.
#
# Encontrado el 20/09/2026 al generar el del Ciclo 3, comparando cuantos
# objetos tenia cada uno: 3, 6 y 16.
#
# ---- SEGUNDO PROBLEMA (21/09): SALIERON CON LOS ACENTOS ROTOS ----
# `COHESIA"N a€" quA©` en vez de `COHESION - que`. Este archivo se habia
# guardado SIN BOM, y PowerShell 5.1 lee un .ps1 sin BOM como ANSI
# (Windows-1252), no como UTF-8: cada acento entro al modelo como los dos
# bytes de su UTF-8 leidos por separado. No da ningun error --- el script
# corre y escribe basura --- y se ve recien al abrir el diagrama.
# El mismo defecto tenia ea-paquetes-2-4-ciclo3.ps1.
# ESTE ARCHIVO TIENE QUE QUEDAR GUARDADO EN UTF-8 CON BOM.
#
# Por eso ahora el script es IDEMPOTENTE en vez de aditivo: si las notas ya
# estan, les REESCRIBE el texto en lugar de saltearlas. Asi una sola corrida
# arregla los acentos, y correrlo de nuevo no cambia nada.
#
# Solo toca ese diagrama. No exporta imagenes.
# =========================================================================
$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

$xml = $ea.SQLQuery("SELECT Diagram_ID AS id, Package_ID AS pkg FROM t_diagram WHERE Name='2.4 Analisis de Paquetes - CICLO #2'")
$doc = New-Object System.Xml.XmlDocument; $doc.LoadXml($xml)
$fila = $doc.SelectSingleNode('//Row')
if (-not $fila) { throw 'No se encontro el diagrama del Ciclo 2' }
$d   = $ea.GetDiagramByID([int]$fila.id)
$pkg = $ea.GetPackageByID([int]$fila.pkg)

$cohesion = @"
COHESIÓN — qué agrupa a cada paquete.

P3 reúne todo lo que define una prenda: producto, variante (SKU), imagen, y los maestros del Ciclo 1 —categoría, talla, color, temporada, colección—.

P4 reúne lo que dice cuánto hay y dónde: existencia y movimiento de inventario.

P5 no tiene tabla propia en este ciclo: es una fachada de lectura sobre P3 y P4, y esa es su razón de ser.

P6 reúne la reserva y su detalle, con los cinco estados de su ciclo de vida.

Ninguna clase encaja en dos paquetes a la vez, y sacar cualquiera deja a su paquete incompleto: eso es alta cohesión.
"@

$acoplamiento = @"
ACOPLAMIENTO — qué sabe cada paquete del otro.

Las dependencias van en un solo sentido y siempre hacia abajo: nunca hay un ciclo. P1 no conoce a ninguno; P5 y P6, que están arriba, no se conocen entre sí.

Las dos que importan en este ciclo:

· P5 → P4 es la costura C1. CU-19 le PIDE la disponibilidad a P4 en vez de consultar la tabla existencia, que es ajena.

· P6 → P4 es la mitigación del riesgo R5. P6 controla la transacción —apartar tres prendas es todo o nada— pero el movimiento de stock lo escribe P4, porque la regla «ninguna cantidad cambia sin movimiento» es de P4 y no puede estar en dos lugares.
"@

# Las notas que ya esten en el lienzo, de izquierda a derecha: la primera es
# la de cohesion y la segunda la de acoplamiento, que es el orden en que se
# colocaron.
$notas = @()
foreach ($o in $d.DiagramObjects) {
    $el = $ea.GetElementByID($o.ElementID)
    if ($el.Type -eq 'Note') { $notas += [pscustomobject]@{ el = $el; x = $o.left } }
}
$notas = @($notas | Sort-Object x)

if ($notas.Count -ge 2) {
    # Reescritura: el caso de los acentos rotos.
    $notas[0].el.Notes = $cohesion;     [void]$notas[0].el.Update()
    $notas[1].el.Notes = $acoplamiento; [void]$notas[1].el.Update()
    Write-Output "  ya tenia $($notas.Count) notas: texto reescrito con los acentos correctos"
} else {
    # Alta: el caso del 20/09, cuando no habia ninguna.
    # La fila mas baja de los paquetes, para colgar las notas debajo.
    $masBajo = 0
    foreach ($o in $d.DiagramObjects) { if ($o.bottom -lt $masBajo) { $masBajo = $o.bottom } }
    $t = $masBajo - 40

    foreach ($par in @(@(40, $cohesion), @(520, $acoplamiento))) {
        $n = $pkg.Elements.AddNew('', 'Note'); $n.Notes = $par[1]; [void]$n.Update()
        $do = $d.DiagramObjects.AddNew("l=$($par[0]);r=$($par[0]+440);t=$t;b=$($t-360);", '')
        $do.ElementID = $n.ElementID; [void]$do.Update()
    }
    $pkg.Elements.Refresh(); $d.DiagramObjects.Refresh()
    Write-Output "  notas agregadas: $($d.DiagramObjects.Count) objetos en total"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
