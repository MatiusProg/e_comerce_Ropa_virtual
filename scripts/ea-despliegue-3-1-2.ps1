param(
    [switch]$Rehacer
)

# =========================================================================
# CAP. 3 - 3.1.2 Diagrama de Despliegue.
#
# ---- POR QUE ESTE DIAGRAMA SUELE SALIR MAL ----
# Porque se dibuja como un diagrama de componentes con iconos de computadora.
# Los cinco errores tipicos, y como se evitan aqui:
#
#   1. Usar Package o Component para los servidores. En UML un servidor es un
#      NODE --- la caja en 3D ---, y se distingue «device» (el hardware) de
#      «executionEnvironment» (el runtime que corre DENTRO de ese hardware).
#      Aqui son elementos Device y ExecutionEnvironment de verdad.
#
#   2. Meter COMPONENTES dentro de los nodos. Eso es UML 1.x. Desde UML 2.0
#      lo que se despliega en un nodo es un ARTEFACTO --- el archivo: la
#      imagen Docker, el bundle compilado, el .apk --- y ese artefacto
#      MANIFIESTA («manifest») al componente.
#
#   3. Unir los nodos con Dependency. La conexion entre dos nodos es un
#      CommunicationPath: una linea SOLIDA, sin punta de flecha, rotulada con
#      el protocolo. EA lo tiene como tipo propio, no hace falta simularlo.
#
#   4. Olvidar la multiplicidad de los clientes. Hay muchas computadoras y
#      muchos celulares, no uno de cada uno: por eso llevan [*].
#
#   5. Repetir el mismo artefacto en cada nodo. El bundle de Angular es UNO
#      solo desplegado en cuatro sitios; se dibuja una vez y se le sacan
#      cuatro flechas «deploy». En cambio los artefactos que viven en un solo
#      nodo van dibujados DENTRO de el, que tambien es notacion valida.
#
# ---- LAS DOS NOTACIONES DE DESPLIEGUE, Y CUANDO USAR CADA UNA ----
#   - Artefacto DENTRO del nodo: cuando ese artefacto vive solo ahi.
#     (la imagen de la API, el esquema de la base, nginx.conf)
#   - Artefacto FUERA con flecha «deploy»: cuando el mismo artefacto se
#     despliega en varios nodos. (el bundle de Angular)
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '3.1.2 Diagrama de Despliegue'

# =========================================================================
# PARTE 1 - Enterprise Architect por COM
# =========================================================================

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-OCrearPaquete($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}
function BuscarPaquete($p, $n) {
    foreach ($s in $p.Packages) { if ($s.Name -eq $n) { return $s }; $r = BuscarPaquete $s $n; if ($r) { return $r } }
    return $null
}
function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    foreach ($s in $p.Packages) { $r = BuscarDiagrama $s $n; if ($r) { return $r } }
    return $null
}

$root = $ea.Models.GetAt(0)
$pCap3 = BuscarPaquete $root 'CAP. 3 - Flujo de Trabajo: Diseno'
if (-not $pCap3) { throw 'No se encontro el paquete CAP. 3' }
$p31 = Get-OCrearPaquete $pCap3 '3.1 Diseno de la Arquitectura'

if ($Rehacer) {
    for ($i = $p31.Diagrams.Count - 1; $i -ge 0; $i--) {
        if ($p31.Diagrams.GetAt($i).Name -eq $NOMBRE_DIA) {
            $p31.Diagrams.DeleteAt($i, $false); Write-Output '  diagrama anterior eliminado (-Rehacer)'
        }
    }
    $p31.Diagrams.Refresh()
    for ($i = $p31.Elements.Count - 1; $i -ge 0; $i--) {
        $t = $p31.Elements.GetAt($i).Type
        if ($t -in @('Device','ExecutionEnvironment','Artifact','Node')) { $p31.Elements.DeleteAt($i, $false) }
    }
    $p31.Elements.Refresh()
}

if (BuscarDiagrama $p31 $NOMBRE_DIA) {
    Write-Output "  $NOMBRE_DIA ya existe, no se toca"
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    exit 0
}

$dia = $p31.Diagrams.AddNew($NOMBRE_DIA, 'Deployment')
[void]$dia.Update(); $p31.Diagrams.Refresh()

$zHijos = @()   # artefactos y runtimes: se dibujan ENCIMA
$zMedio = @()   # execution environments
$zCajas = @()   # devices: al fondo
$multip = @()   # nodos que llevan [*]
$padres = @()   # contencion real por ParentID

function New-El($nombre, $tipo, $estereotipo, $nota) {
    $e = $p31.Elements.AddNew($nombre, $tipo)
    if ($estereotipo) { $e.Stereotype = $estereotipo }
    if ($nota) { $e.Notes = $nota }
    [void]$e.Update()
    return $e
}
function Poner($el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}
function New-Rel($src, $dst, $tipo, $estereotipo, $nombre) {
    $c = $src.Connectors.AddNew($nombre, $tipo)
    $c.SupplierID = $dst.ElementID
    $c.Direction = 'Source -> Destination'
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update()
    $src.Connectors.Refresh()
}

# =========================================================================
# CLIENTES. Son «device»: hardware. Dentro de cada uno, el runtime que
# ejecuta nuestro software. Llevan [*] porque hay muchos, no uno.
# =========================================================================
$dPC = New-El 'Computadora / Laptop' 'Device' 'device' 'Puesto de trabajo del administrador, el encargado de sucursal y el cajero. Tambien es por donde entra el cliente desde la web.'
Poner $dPC 60 -60 400 200
$zCajas += $dPC.ElementID; $multip += $dPC.ElementID

$eePC = New-El 'Navegador web' 'ExecutionEnvironment' 'executionEnvironment' 'Chrome, Edge o Firefox. Ejecuta la SPA de Angular y guarda el token de sesion.'
Poner $eePC 90 -120 340 110
$zMedio += $eePC.ElementID; $padres += @{ h = $eePC.ElementID; p = $dPC.ElementID }

$dTab = New-El 'Tablet' 'Device' 'device' 'Uso en piso de venta y en el probador. Entra por la misma web, sin aplicacion instalada.'
Poner $dTab 520 -60 400 200
$zCajas += $dTab.ElementID; $multip += $dTab.ElementID

$eeTab = New-El 'Navegador web ' 'ExecutionEnvironment' 'executionEnvironment' 'El mismo bundle de Angular que en la computadora; la interfaz es responsiva.'
Poner $eeTab 550 -120 340 110
$zMedio += $eeTab.ElementID; $padres += @{ h = $eeTab.ElementID; p = $dTab.ElementID }

$dCel = New-El 'Smartphone Android' 'Device' 'device' 'El unico cliente con dos caminos: hoy entra por el navegador, y en el Ciclo 3 tendra la aplicacion Flutter instalada.'
Poner $dCel 980 -60 440 200
$zCajas += $dCel.ElementID; $multip += $dCel.ElementID

$eeCelWeb = New-El 'Navegador móvil' 'ExecutionEnvironment' 'executionEnvironment' 'Chrome para Android. Es como se usa el sistema hoy desde el telefono.'
Poner $eeCelWeb 1010 -105 380 55
$zMedio += $eeCelWeb.ElementID; $padres += @{ h = $eeCelWeb.ElementID; p = $dCel.ElementID }

$eeCelApp = New-El 'Android Runtime' 'ExecutionEnvironment' 'executionEnvironment' 'La maquina virtual de Android. Aqui correra la aplicacion Flutter del Ciclo 3, con el vestidor virtual en realidad aumentada.'
Poner $eeCelApp 1010 -180 380 55
$zMedio += $eeCelApp.ElementID; $padres += @{ h = $eeCelApp.ElementID; p = $dCel.ElementID }

# =========================================================================
# SERVIDORES. Railway hospeda dos contenedores; Supabase, la base.
# =========================================================================
$dRW = New-El 'Servidor Railway' 'Device' 'device' 'Plataforma que hospeda la API y la web, cada una como un servicio con su propia imagen Docker. Inyecta la variable PORT en el arranque.'
Poner $dRW 60 -480 800 340
$zCajas += $dRW.ElementID

$eeNginx = New-El 'Contenedor · nginx:alpine' 'ExecutionEnvironment' 'executionEnvironment' 'Segunda etapa del frontend-web/Dockerfile. Sirve los estaticos compilados y sustituye $PORT en la plantilla de nginx al arrancar.'
Poner $eeNginx 90 -530 350 270
$zMedio += $eeNginx.ElementID; $padres += @{ h = $eeNginx.ElementID; p = $dRW.ElementID }

$eeUvi = New-El 'Contenedor · Python 3.13 + Uvicorn' 'ExecutionEnvironment' 'executionEnvironment' 'backend/Dockerfile. El puerto que expone y el que usa el servidor tienen que ser el mismo: Railway enruta mirando el EXPOSE.'
Poner $eeUvi 470 -530 370 270
$zMedio += $eeUvi.ElementID; $padres += @{ h = $eeUvi.ElementID; p = $dRW.ElementID }

$dSB = New-El 'Servidor Supabase · AWS us-east-1' 'Device' 'device' 'Hospeda la base de produccion. En produccion desde el 04/09/2026.'
Poner $dSB 920 -480 620 340
$zCajas += $dSB.ElementID

$eePool = New-El 'PgBouncer · session pooler' 'ExecutionEnvironment' 'executionEnvironment' 'aws-0-us-east-1.pooler.supabase.com. Se conecta por AQUI, no por la conexion directa: el pooler es el que aguanta que Railway abra y cierre conexiones en cada despliegue.'
Poner $eePool 950 -530 560 70
$zMedio += $eePool.ElementID; $padres += @{ h = $eePool.ElementID; p = $dSB.ElementID }

$eePG = New-El 'PostgreSQL 17' 'ExecutionEnvironment' 'executionEnvironment' 'El motor. En desarrollo se reemplaza por el contenedor postgres:16-alpine de docker-compose.yml.'
Poner $eePG 950 -620 560 180
$zMedio += $eePG.ElementID; $padres += @{ h = $eePG.ElementID; p = $dSB.ElementID }

# =========================================================================
# ARTEFACTOS QUE VIVEN EN UN SOLO NODO -> se dibujan DENTRO de el.
# =========================================================================
$aNginxConf = New-El 'nginx.conf' 'Artifact' 'artifact' 'frontend-web/nginx.conf. Plantilla que resuelve $PORT y reenvia todas las rutas al index.html, para que funcione el enrutado de Angular.'
Poner $aNginxConf 110 -600 310 55
$zHijos += $aNginxConf.ElementID; $padres += @{ h = $aNginxConf.ElementID; p = $eeNginx.ElementID }

$aApiImg = New-El 'violetboutique-api:latest' 'Artifact' 'artifact' 'Imagen Docker construida desde backend/Dockerfile sobre python:3.13-slim.'
Poner $aApiImg 490 -600 330 55
$zHijos += $aApiImg.ElementID; $padres += @{ h = $aApiImg.ElementID; p = $eeUvi.ElementID }

$aMedia = New-El 'volumen media/' 'Artifact' 'artifact' 'Volumen persistente montado en /app/media. El sistema de archivos del contenedor es efimero: lo que no este aqui se pierde en cada despliegue.'
Poner $aMedia 490 -670 330 55
$zHijos += $aMedia.ElementID; $padres += @{ h = $aMedia.ElementID; p = $eeUvi.ElementID }

$aEsquema = New-El 'esquema violetboutique · 16 tablas' 'Artifact' 'artifact' 'El esquema de 3.3.1 aplicado: rol, permiso, rol_permiso, usuario, cliente, direccion_cliente, sesion_token, ciudad, sucursal, empleado, proveedor, categoria, talla, color, temporada, coleccion.'
Poner $aEsquema 970 -670 520 55
$zHijos += $aEsquema.ElementID; $padres += @{ h = $aEsquema.ElementID; p = $eePG.ElementID }

# =========================================================================
# ARTEFACTOS DESPLEGADOS EN VARIOS NODOS -> se dibujan UNA VEZ, fuera, y
# se les saca una flecha «deploy» por cada nodo destino.
# =========================================================================
$aBundle = New-El 'violetboutique-web · bundle Angular' 'Artifact' 'artifact' 'dist/frontend-web/browser: el index.html y los .js compilados con ng build --configuration production. nginx los sirve y cada navegador los ejecuta.'
Poner $aBundle 1620 -80 380 64
$zHijos += $aBundle.ElementID

$aApk = New-El 'violetboutique.apk · Ciclo 3' 'Artifact' 'artifact' 'El paquete de la aplicacion Flutter. Todavia no existe: mobile/ tiene el arbol de carpetas y el pubspec.yaml, pero ni un archivo Dart.'
Poner $aApk 1620 -180 380 64
$zHijos += $aApk.ElementID

# =========================================================================
# COMPONENTES. Lo que cada artefacto MANIFIESTA.
# =========================================================================
$cBE = New-El 'Backend · FastAPI' 'Component' $null 'backend/. Los once modulos de app/modules/.'
Poner $cBE 1620 -480 380 70
$cFE = New-El 'Frontend · Angular' 'Component' $null 'frontend-web/. La SPA.'
Poner $cFE 1620 -580 380 70
$cMO = New-El 'Móvil · Flutter' 'Component' $null 'mobile/. Andamiaje del Ciclo 3.'
Poner $cMO 1620 -680 380 70

# =========================================================================
# RELACIONES
# =========================================================================

# «deploy»: del artefacto al nodo donde se despliega.
New-Rel $aBundle $eePC     'Deployment' 'deploy' ''
New-Rel $aBundle $eeTab    'Deployment' 'deploy' ''
New-Rel $aBundle $eeCelWeb 'Deployment' 'deploy' ''
New-Rel $aBundle $eeNginx  'Deployment' 'deploy' ''
New-Rel $aApk    $eeCelApp 'Deployment' 'deploy' ''

# «manifest»: del artefacto al componente que implementa.
New-Rel $aApiImg $cBE 'Manifest' 'manifest' ''
New-Rel $aBundle $cFE 'Manifest' 'manifest' ''
New-Rel $aApk    $cMO 'Manifest' 'manifest' ''

# CommunicationPath: linea solida entre NODOS, rotulada con el protocolo.
New-Rel $dPC  $dRW 'CommunicationPath' $null 'HTTPS'
New-Rel $dTab $dRW 'CommunicationPath' $null 'HTTPS'
New-Rel $dCel $dRW 'CommunicationPath' $null 'HTTPS'
New-Rel $dRW  $dSB 'CommunicationPath' $null 'TCP 5432 · session pooler'

# ---- Leyenda ----
$leyenda = New-El '' 'Note' $null (
    "CÓMO SE LEE`n`n" +
    "«device»                hardware`n" +
    "«executionEnvironment»  runtime que corre dentro`n" +
    "«artifact»              el archivo que se despliega`n`n" +
    "— línea sólida  = CommunicationPath (protocolo)`n" +
    "- - «deploy»    = el artefacto corre en ese nodo`n" +
    "- - «manifest»  = el artefacto implementa ese componente`n`n" +
    "[*] en los clientes: hay muchos, no uno de cada uno.`n`n" +
    "El bundle de Angular se dibuja UNA vez con cuatro flechas`n" +
    "«deploy» porque es el mismo artefacto en cuatro nodos.`n" +
    "Los que viven en un solo nodo van dentro de él."
)
Poner $leyenda 60 -880 800 260

$p31.Elements.Refresh()
$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $($dia.DiagramLinks.Count) relaciones"

$didCom = $dia.DiagramID
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Lo que la API COM no deja hacer:
#   a) ParentID, para que la contencion sea real y no solo dibujada.
#   b) La multiplicidad [*] de los nodos cliente.
#   c) El orden Z. Sequence MAS BAJO = se dibuja ENCIMA, asi que los
#      artefactos van con el numero mas bajo y los «device» con el mas alto.
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }

foreach ($r in $padres) { [void](Exec "UPDATE t_object SET ParentID = $($r.p) WHERE Object_ID = $($r.h)") }
[void](Exec "UPDATE t_object SET Multiplicity = '*' WHERE Object_ID IN ($($multip -join ','))")

$z = 2
foreach ($id in $zHijos) { [void](Exec "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID = $didCom AND Object_ID = $id"); $z++ }
foreach ($id in $zMedio) { [void](Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $didCom AND Object_ID = $id") }
foreach ($id in $zCajas) { [void](Exec "UPDATE t_diagramobjects SET Sequence = 200 WHERE Diagram_ID = $didCom AND Object_ID = $id") }

$cn.Close()
Write-Output "  $($padres.Count) contenciones, $($multip.Count) multiplicidades y el orden Z escritos"
Write-Output 'OK'
