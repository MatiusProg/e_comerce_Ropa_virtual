# =========================================================================
# ARREGLO PUNTUAL - 2.4 Analisis de Paquetes, CICLO 2: le faltan las notas.
#
# El diagrama quedo con sus seis paquetes y SIN las dos notas de cohesion y
# acoplamiento, que es literalmente de lo que trata el punto 2.4. Su propio
# generador las agrega al final, pero el diagrama ya existia cuando esa
# parte se escribio y el guardia «si ya existe, no se toca» impide que una
# nueva corrida las ponga.
#
# Encontrado el 20/09/2026 al generar el del Ciclo 3, comparando cuantos
# objetos tenia cada uno: 3, 6 y 16.
#
# Es aditivo y solo toca ese diagrama. No exporta imagenes.
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

$yaTiene = 0
foreach ($o in $d.DiagramObjects) {
    if ($ea.GetElementByID($o.ElementID).Type -eq 'Note') { $yaTiene++ }
}
if ($yaTiene -ge 2) {
    Write-Output "  ya tiene $yaTiene notas, no se toca"
} else {
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
    # La fila mas baja de los paquetes, para colgar las notas debajo.
    $masBajo = 0
    foreach ($o in $d.DiagramObjects) { if ($o.bottom -lt $masBajo) { $masBajo = $o.bottom } }
    $t = $masBajo - 40

    foreach ($par in @(@(40, $cohesion), @(520, $acoplamiento))) {
        $n = $pkg.Elements.AddNew('', 'Note'); $n.Notes = $par[1]; [void]$n.Update()
        $do = $d.DiagramObjects.AddNew("l=$($par[0]);r=$($par[0]+440);t=$t;b=$($t-300);", '')
        $do.ElementID = $n.ElementID; [void]$do.Update()
    }
    $pkg.Elements.Refresh(); $d.DiagramObjects.Refresh()
    Write-Output "  notas agregadas: $($d.DiagramObjects.Count) objetos en total"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
