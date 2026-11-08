# Exporta a JPG los diagramas de la 3ra presentacion (2.5, 3.2 y 3.4 de CU-21 a CU-45 y el general).
# Siempre sobre una COPIA del .eapx (guia, anexo 01/11, G): asi sale sin marca de agua y no se pisa con un
# EA abierto. Repositorio sin ventana; PowerShell de 32 bits. Los diagramas se buscan por SQL (recorrer
# las colecciones de paquetes por COM se colgaba sin escribir nada).
param(
    [Parameter(Mandatory)] [string]$Modelo,
    [Parameter(Mandatory)] [string]$Salida
)
$ErrorActionPreference = 'Stop'
# 08/11: sin ventana, PutDiagramImageToFile se colgo en los 2.5 y 3.4 (y despues en todos). Con un EA
# visible lanzado desde este mismo proceso (truco de la memoria ea-trial-expirado) funciona.
Get-Process EA -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process 'C:\Program Files (x86)\Sparx Systems\EA Trial\EA.exe'
$ea = $null
for ($i = 0; $i -lt 60 -and -not $ea; $i++) {
    Start-Sleep -Milliseconds 1000
    try { $ea = [Runtime.InteropServices.Marshal]::GetActiveObject('EA.App').Repository } catch { }
}
if (-not $ea) { throw 'EA no arranco' }
Write-Output 'EA abierto'
if (-not $ea.OpenFile($Modelo)) { throw "No se pudo abrir $Modelo" }
Write-Output 'modelo abierto'
$proj = $ea.GetProjectInterface()
$xml = [xml]$ea.SQLQuery("SELECT ea_guid, Name FROM t_diagram")
$CARPETA = @{ '2.5' = 'Diagrama de casos de uso'; '3.2' = 'Diagrama de robustez'; '3.4' = 'Diagrama de clases'; '3.3' = 'Diagrama de secuencia'; '3.1' = 'Modelo de dominio'; '3.5' = 'Base de datos' }
$n = 0
foreach ($f in $xml.SelectNodes('//Row')) {
    $nombre = $f.Name; $guid = $f.ea_guid
    $esP3 = ($nombre -match '^(2\.5|3\.2|3\.3|3\.4) CU-(\d+) ' -and [int]$Matches[2] -ge 21) -or $nombre -like '*(CU-01 a CU-46)'
    if (-not $esP3) { continue }
    $dir = Join-Path $Salida $CARPETA[$nombre.Substring(0, 3)]
    New-Item -ItemType Directory -Force $dir | Out-Null
    $archivo = Join-Path $dir ($nombre + '.jpg')
    [void]$proj.PutDiagramImageToFile($guid, $archivo, 1)
    $n++; Write-Output "  $n  $nombre"
}
$ea.CloseFile(); $ea.Exit()
Get-Process EA -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Output "OK: $n diagramas"
