param(
    # Borra el paquete 3.1 entero y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 3 - 3.1.1 Diagrama de Capas.
#
# Cuatro filas imaginarias, de arriba hacia abajo:
#
#   CAPA 1  Vista de analisis .... los 11 paquetes del 2.1, alineados y SIN
#                                  relaciones entre si.
#   CAPA 2  Backend + Frontend ... un rectangulo por aplicacion, con sus
#           + Movil                archivos mas caracteristicos adentro.
#   CAPA 3  Servidores locales ... el entorno de desarrollo de cada maquina.
#   CAPA 4  Servidores en la nube  donde vive el sistema publicado.
#
# Y tres relaciones, una por salto entre capas:
#
#   capa 1 --«realiza»------> capa 2   Realisation
#   capa 2 --«ejecuta en»---> capa 3   Dependency
#   capa 3 --«despliega en»-> capa 4   Dependency
#
# ---- SOBRE LA DIRECCION DE «realiza» ----
# En UML la realizacion apunta del que IMPLEMENTA hacia lo realizado, o sea
# que lo correcto seria capa 2 -> capa 1. Mateo decidio el 05/09/2026
# dibujarla al reves, de capa 1 a capa 2, porque asi la pidio la catedra y
# asi se lee de arriba hacia abajo junto con las otras dos. Queda anotado
# aqui para que nadie lo "corrija" por error mas adelante.
#
# ---- SOBRE LAS FORMAS ----
# Las capas 3 y 4 usan elementos Package --- la carpeta --- porque asi lo
# pide la catedra para este diagrama. En el diagrama de DESPLIEGUE que viene
# despues, esos mismos servidores tienen que ser Node, con «device» y
# «executionEnvironment»; ahi la carpeta no vale.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '3.1.1 Diagrama de Capas'

# ---- Constantes de dibujo ----
$X_ROT   = 20;   $W_ROT  = 340          # la etiqueta de cada capa, a la izquierda
$X0      = 400                          # donde arranca el contenido
$Y_C1    = -60;  $H_C1   = 76;  $W_C1 = 200; $S_C1 = 215
$Y_C2    = -280; $H_C2   = 300
$Y_C3    = -700; $H_C34  = 90;  $W_C34 = 340; $S_C34 = 380
$Y_C4    = -900
$W_ART   = 280;  $H_ART  = 45;  $S_ART = 300; $S_FILA = 55

# =========================================================================
# CAPA 1 - los 11 paquetes del analisis 2.1
# =========================================================================
$CAPA1 = @(
    @{ k = 'P1';  n = 'P1 · Seguridad y Usuarios' },
    @{ k = 'P2';  n = 'P2 · Organización' },
    @{ k = 'P3';  n = 'P3 · Catálogo' },
    @{ k = 'P4';  n = 'P4 · Inventario' },
    @{ k = 'P5';  n = 'P5 · Catálogo Público y Disponibilidad' },
    @{ k = 'P6';  n = 'P6 · Reservas' },
    @{ k = 'P7';  n = 'P7 · Ventas y Punto de Venta' },
    @{ k = 'P8';  n = 'P8 · Pagos' },
    @{ k = 'P9';  n = 'P9 · Vestidor Virtual (RA)' },
    @{ k = 'P10'; n = 'P10 · Inteligencia Artificial' },
    @{ k = 'P11'; n = 'P11 · Reportes y Tablero' }
)

# =========================================================================
# CAPA 2 - una caja por aplicacion, con sus archivos mas caracteristicos.
# 'realiza' lista los paquetes de la capa 1 que se implementan ahi, segun las
# carpetas que existen HOY en el repositorio.
# =========================================================================
$CAPA2 = @(
    @{
        k = 'BE'; n = 'Backend · FastAPI'; x = 560; w = 620; cols = 2
        nota = 'backend/. FastAPI 0.141 sobre Python 3.13, SQLAlchemy 2.0 y psycopg 3. Los once modulos de app/modules/ son los once paquetes del analisis.'
        arts = @('main.py', 'core/config.py', 'core/security.py', 'core/dependencies.py', 'db/session.py', 'requirements.txt', 'Dockerfile')
        realiza = @('P1','P2','P3','P4','P5','P6','P7','P8','P9','P10','P11')
    },
    @{
        k = 'FE'; n = 'Frontend · Angular'; x = 1260; w = 620; cols = 2
        nota = 'frontend-web/. SPA en Angular servida por nginx. Hoy tienen componentes admin, auth, cliente e inicio; el resto de features son carpetas creadas para los ciclos 2 y 3.'
        arts = @('app.routes.ts', 'app.config.ts', 'core/services/', 'core/guards/', 'core/interceptors/', 'package.json', 'Dockerfile')
        realiza = @('P1','P2','P3','P4','P5','P7','P10','P11')
    },
    @{
        k = 'MO'; n = 'Móvil · Flutter'; x = 1960; w = 460; cols = 1
        nota = 'mobile/. Andamiaje de la aplicacion movil: pubspec.yaml y el arbol de carpetas de lib/features. Todavia sin codigo Dart.'
        arts = @('pubspec.yaml', 'lib/core/', 'lib/data/', 'lib/features/')
        realiza = @('P1','P5','P6','P7','P9','P10')
    }
)

# =========================================================================
# CAPA 3 - el entorno de desarrollo de cada maquina.
# 'ejecuta' dice que cajas de la capa 2 corren ahi.
# =========================================================================
$CAPA3 = @(
    @{ k = 'PG';  n = 'Docker · PostgreSQL 16 · :5432'; ejecuta = @('BE')
       nota = 'docker-compose.yml, servicio db. Imagen postgres:16-alpine con volumen pgdata, para que cada integrante levante la base sin instalarla.' },
    @{ k = 'UVI'; n = 'Uvicorn · :8000';                ejecuta = @('BE')
       nota = 'El servidor ASGI de desarrollo. Se levanta fuera de Docker con --reload para tener recarga en caliente; el perfil api del compose lo mete en un contenedor.' },
    @{ k = 'NG';  n = 'ng serve · :4200';               ejecuta = @('FE')
       nota = 'El servidor de desarrollo de Angular. Su origen esta en CORS_ORIGINS del backend.' },
    @{ k = 'EMU'; n = 'Emulador Android · Flutter';     ejecuta = @('MO')
       nota = 'flutter run sobre el emulador o un dispositivo fisico. El puerto 8100 tambien esta habilitado en CORS_ORIGINS.' }
)

# =========================================================================
# CAPA 4 - donde vive el sistema publicado.
# 'despliega' dice que entornos de la capa 3 se publican ahi.
# =========================================================================
$CAPA4 = @(
    @{ k = 'RW';  n = 'Railway · API + Web';   despliega = @('UVI','NG')
       nota = 'Hospeda la API y la web, cada una como un servicio con su propia imagen Docker. Inyecta la variable PORT y monta un volumen persistente en /app/media.' },
    @{ k = 'SB';  n = 'Supabase · PostgreSQL'; despliega = @('PG')
       nota = 'La base de produccion. Se conecta por el SESSION POOLER, no por la conexion directa. En produccion desde el 04/09/2026.' },
    @{ k = 'GH';  n = 'GitHub · repositorio';  despliega = @()
       nota = 'MatiusProg/e_comerce_Ropa_virtual. No recibe flecha porque no es un destino de despliegue: es el ORIGEN desde el que Railway construye las imagenes.' },
    @{ k = 'GP';  n = 'Google Play · Ciclo 3'; despliega = @('EMU')
       nota = 'Destino previsto de la aplicacion movil. Todavia no hay nada publicado.' }
)

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

if ($Rehacer) {
    for ($i = $pCap3.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap3.Packages.GetAt($i).Name -eq '3.1 Diseno de la Arquitectura') {
            $pCap3.Packages.DeleteAt($i, $false)
            Write-Output '  paquete 3.1 anterior eliminado (-Rehacer)'
        }
    }
    $pCap3.Packages.Refresh()
}

$p31 = Get-OCrearPaquete $pCap3 '3.1 Diseno de la Arquitectura'

if (BuscarDiagrama $p31 $NOMBRE_DIA) {
    Write-Output "  $NOMBRE_DIA ya existe, no se toca"
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    exit 0
}

$dia = $p31.Diagrams.AddNew($NOMBRE_DIA, 'Component')
[void]$dia.Update(); $p31.Diagrams.Refresh()

function New-Elem($nombre, $tipo, $estereotipo, $nota) {
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
function New-Rel($src, $dst, $tipo, $estereotipo) {
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    $c.Direction = 'Source -> Destination'
    $c.Stereotype = $estereotipo
    [void]$c.Update()
    $src.Connectors.Refresh()
}

# ---- Etiquetas de las cuatro capas ----
$rotulos = @(
    @{ t = $Y_C1; txt = "CAPA 1`nVista de Análisis" },
    @{ t = $Y_C2; txt = "CAPA 2`nBackend + Frontend + Móvil" },
    @{ t = $Y_C3; txt = "CAPA 3`nServidores locales" },
    @{ t = $Y_C4; txt = "CAPA 4`nServidores en la nube" }
)
foreach ($r in $rotulos) {
    $e = New-Elem '' 'Note' $null $r.txt
    Poner $e $X_ROT $r.t $W_ROT 80
}

# ---- CAPA 1 ----
$el1 = @{}
for ($i = 0; $i -lt $CAPA1.Count; $i++) {
    $p = $CAPA1[$i]
    $e = New-Elem $p.n 'Package' $null "Paquete del analisis 2.1. Su modulo de backend es backend/app/modules/."
    Poner $e ($X0 + $i * $S_C1) $Y_C1 $W_C1 $H_C1
    $el1[$p.k] = $e
}

# ---- CAPA 2: la caja y sus archivos ----
$el2 = @{}
$artIds = @{}
foreach ($c in $CAPA2) {
    $caja = New-Elem $c.n 'Package' $null $c.nota
    Poner $caja $c.x $Y_C2 $c.w $H_C2
    $el2[$c.k] = $caja

    $hijos = @()
    for ($i = 0; $i -lt $c.arts.Count; $i++) {
        $col = $i % $c.cols
        $fila = [math]::Floor($i / $c.cols)
        $ax = $c.x + 20 + ($col * $S_ART)
        $ay = $Y_C2 - 50 - ($fila * $S_FILA)
        $ancho = if ($c.cols -eq 1) { $c.w - 40 } else { $W_ART }
        $a = New-Elem $c.arts[$i] 'Artifact' $null "Archivo de $($c.n)."
        Poner $a $ax $ay $ancho $H_ART
        $hijos += $a.ElementID
    }
    $artIds[$caja.ElementID] = $hijos
}

# ---- CAPA 3 y CAPA 4 ----
$anchoC34 = ($CAPA3.Count * $S_C34) - ($S_C34 - $W_C34)
$x34 = $X0 + [int]((($CAPA1.Count * $S_C1 - ($S_C1 - $W_C1)) - $anchoC34) / 2)

$el3 = @{}
for ($i = 0; $i -lt $CAPA3.Count; $i++) {
    $s = $CAPA3[$i]
    $e = New-Elem $s.n 'Package' $null $s.nota
    Poner $e ($x34 + $i * $S_C34) $Y_C3 $W_C34 $H_C34
    $el3[$s.k] = $e
}

$el4 = @{}
for ($i = 0; $i -lt $CAPA4.Count; $i++) {
    $s = $CAPA4[$i]
    $e = New-Elem $s.n 'Package' $null $s.nota
    Poner $e ($x34 + $i * $S_C34) $Y_C4 $W_C34 $H_C34
    $el4[$s.k] = $e
}

# ---- Relaciones ----
$n1 = 0; $n2 = 0; $n3 = 0
foreach ($c in $CAPA2) {
    foreach ($k in $c.realiza) { New-Rel $el1[$k] $el2[$c.k] 'Realisation' 'realiza'; $n1++ }
}
foreach ($s in $CAPA3) {
    foreach ($k in $s.ejecuta) { New-Rel $el2[$k] $el3[$s.k] 'Dependency' 'ejecuta en'; $n2++ }
}
foreach ($s in $CAPA4) {
    foreach ($k in $s.despliega) { New-Rel $el3[$k] $el4[$s.k] 'Dependency' 'despliega en'; $n3++ }
}

$p31.Elements.Refresh()
$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos"
Write-Output "     «realiza» $n1   «ejecuta en» $n2   «despliega en» $n3"

$idsCajas = ($el2.Values | ForEach-Object { $_.ElementID })
$mapaArt = $artIds

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Lo que la API COM no deja hacer:
#   a) ParentID, para que los archivos cuelguen DE VERDAD de su caja.
#   b) El orden Z. En t_diagramobjects, Sequence MAS BAJO = se dibuja ENCIMA;
#      sin tocarlo la caja tapa a sus propios archivos.
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
$c = $cn.CreateCommand()
$c.CommandText = "SELECT Diagram_ID FROM t_diagram WHERE Name = '$NOMBRE_DIA'"
$did = [int]$c.ExecuteScalar()

$z = 2
foreach ($caja in $idsCajas) {
    $hijos = $mapaArt[$caja]
    $ids = $hijos -join ','
    $u = $cn.CreateCommand()
    $u.CommandText = "UPDATE t_object SET ParentID = $caja WHERE Object_ID IN ($ids)"
    [void]$u.ExecuteNonQuery()
    foreach ($h in $hijos) {
        $uz = $cn.CreateCommand()
        $uz.CommandText = "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID = $did AND Object_ID = $h"
        [void]$uz.ExecuteNonQuery()
        $z++
    }
    $uc = $cn.CreateCommand()
    $uc.CommandText = "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $did AND Object_ID = $caja"
    [void]$uc.ExecuteNonQuery()
}
$cn.Close()
Write-Output "  archivos colgados de su caja y orden Z corregido"
Write-Output 'OK'
