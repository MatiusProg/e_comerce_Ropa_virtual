$ErrorActionPreference = 'Stop'
$ea = New-Object -ComObject EA.Repository
[void]$ea.OpenFile('D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx')
$base = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\parcial-2'
$proj = $ea.GetProjectInterface()
function Paq($padre, $n) { foreach ($p in $padre.Packages) { if ($p.Name -eq $n) { return $p } }; throw "falta $n" }
$p2 = Paq (Paq $ea.Models.GetAt(0) 'Violet Boutique') 'PARCIAL 2 - ICONIX'
foreach ($par in @(@('2.5 Diagrama de Casos de Uso','casos-de-uso'), @('3.2 Diagramas de Robustez','robustez'))) {
    $dir = Join-Path $base $par[1]
    New-Item -ItemType Directory -Force $dir | Out-Null
    $pkg = Paq (Paq $p2 $par[0]) 'Ciclo 1'
    foreach ($d in $pkg.Diagrams) {
        $f = Join-Path $dir ($d.Name + '.png')
        [void]$proj.PutDiagramImageToFile($d.DiagramGUID, $f, 1)
        Write-Output $f
    }
}
$ea.CloseFile(); $ea.Exit()
