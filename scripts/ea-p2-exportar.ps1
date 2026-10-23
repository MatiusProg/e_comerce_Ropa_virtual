# Exporta a JPG los diagramas 2.5 y 3.2 del 2do parcial (reemplaza a ea-p2-exportar-ciclo1.ps1).
# PowerShell de 32 bits, con EA ABIERTO EN PANTALLA: se exporta a través de esa instancia, porque una
# instancia sin ventana (New-Object EA.Repository) se cuelga en PutDiagramImageToFile (visto el 23/10).
$ErrorActionPreference = 'Stop'
$ea = [Runtime.InteropServices.Marshal]::GetActiveObject('EA.App').Repository
[void]$ea.OpenFile('D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx')
$base = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\2do Parcial'
$proj = $ea.GetProjectInterface()
function Paq($padre, $n) { foreach ($p in $padre.Packages) { if ($p.Name -eq $n) { return $p } }; throw "falta $n" }
$p2 = Paq (Paq $ea.Models.GetAt(0) 'Violet Boutique') 'PARCIAL 2 - ICONIX'
foreach ($par in @(@('2.5 Diagrama de Casos de Uso', 'Diagrama de casos de uso'),
                   @('3.2 Diagramas de Robustez', 'Diagrama de robustez'))) {
    $dir = Join-Path $base $par[1]
    New-Item -ItemType Directory -Force $dir | Out-Null
    foreach ($d in (Paq $p2 $par[0]).Diagrams) {
        $f = Join-Path $dir ($d.Name + '.jpg')
        [void]$proj.PutDiagramImageToFile($d.DiagramGUID, $f, 1)   # 1: formato segun la extension
        Write-Output $f
    }
}
# no se cierra: es la instancia de la persona, que queda con el modelo abierto
