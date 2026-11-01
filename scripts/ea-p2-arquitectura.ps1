param(
    # Borra el paquete 4.2 del 2do parcial (solo tiene lo que genera este script) y lo rehace.
    [switch]$Rehacer
)

# =========================================================================
# 2DO PARCIAL - 4.2 DISENO DE LA ARQUITECTURA DEL SISTEMA
#
#   4.2.1 Diagrama de despliegue
#   4.2.2 Diagrama de capas
#
# Siguen el patron del 1er parcial (scripts/ea-despliegue-3-1-2.ps1 y
# scripts/ea-capas-3-1-1.ps1, y las secciones de la guia), con las
# correcciones de la ing para esta presentacion:
#   - en el de capas, la capa 3 se llama «Capa intermedia» y la capa 4
#     «Capa de software»;
#   - lo de cada nodo se tiene que poder rastrear: cada elemento de las capas
#     3 y 4 lleva como estereotipo el nodo del despliegue donde corre, el
#     mismo color que ese nodo, y una relacion «trace» hacia el en el modelo
#     (EA la muestra en la ventana de trazabilidad);
#   - el despliegue muestra Docker: Railway construye la API y la web desde
#     sus Dockerfile (railway.json, builder DOCKERFILE) y corre cada una en un
#     contenedor; en desarrollo, docker-compose levanta postgres:16-alpine.
#
# Despliegue, las reglas de siempre (patron-despliegue): Device para el
# hardware, ExecutionEnvironment para lo que corre adentro, Artifact para lo
# que se despliega, CommunicationPath con el protocolo entre nodos, [*] en
# los clientes, y el artefacto que va a varios nodos se dibuja una vez con
# flechas «deploy».
#
# Capas: «realiza» va de la capa 1 a la 2 a proposito (pedido de la catedra,
# patron-capas); no corregirlo.
#
# PowerShell de 64 bits (la segunda pasada usa ACE.OLEDB.16.0), EA cerrado.
# EA_MODELO apunta a una copia para probar.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if ($env:EA_MODELO) { $modelo = $env:EA_MODELO }
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }
$N42 = '4.2 Diseño de la Arquitectura'
$DESPLIEGUE = '4.2.1 Diagrama de despliegue'
$CAPAS = '4.2.2 Diagrama de capas'

# Un color por nodo (BGR), el mismo en los dos diagramas: asi se rastrea.
$COLOR = @{
    CLI = 0xF7E4D2   # clientes con navegador (celeste)
    CEL = 0xD8F0D8   # smartphone (verde)
    API = 0xCCE5FF   # Railway, contenedor de la API (naranja)
    WEB = 0xCCF5FF   # Railway, contenedor de la web (amarillo)
    SB  = 0xF2DCEC   # Supabase (lila)
    DEV = 0xE6E6E6   # PC de desarrollo (gris)
    EXT = 0xFFFFFF   # servicios externos
}

# =========================================================================
# 4.2.1 DESPLIEGUE. Cada nodo: k, nombre, tipo, estereotipo, padre, caja
# (l, t, ancho, alto), color, nota. El orden importa: el padre antes que el hijo.
# =========================================================================
$NODOS = @(
    # ---- Clientes ----
    @{ k='dCLI'; n='Computadora / Laptop / Tablet'; tipo='Device'; st='device'; c='CLI'; mult=$true
       box=@(40, -40, 560, 300); nota='Puesto del administrador de la plataforma, del administrador de la empresa, del encargado y del cajero; tambien el cliente que compra desde la web.' },
    @{ k='eNAV'; n='Navegador web (Chrome / Edge)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dCLI'; c='CLI'
       box=@(70, -90, 500, 220); nota='Ejecuta la PWA de Angular. Con el Service Worker instalado, la aplicacion abre sin conexion.' },
    @{ k='aSW'; n='ngsw-worker.js · Service Worker'; tipo='Artifact'; st='artifact'; p='eNAV'
       box=@(100, -140, 440, 50); nota='Generado por ng build a partir de ngsw-config.json. Guarda en cache la aplicacion (CU-13).' },
    @{ k='aIDB'; n='IndexedDB · paquete y cola sin conexión'; tipo='Artifact'; st='artifact'; p='eNAV'
       box=@(100, -210, 440, 50); nota='core/services/offline.service.ts: el paquete de mostrador (prendas, clientes, turno) y las operaciones guardadas hasta sincronizar (CU-13 a CU-18).' },

    @{ k='dCEL'; n='Smartphone Android'; tipo='Device'; st='device'; c='CEL'; mult=$true
       box=@(660, -40, 520, 300); nota='El cliente con la aplicacion Flutter: reserva sin conexion (CU-15). Probado en un Xiaomi con HyperOS.' },
    @{ k='eAND'; n='Android Runtime · Flutter'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dCEL'; c='CEL'
       box=@(690, -90, 460, 220); nota='La aplicacion Flutter compilada para Android.' },
    @{ k='aAPK'; n='app-release.apk'; tipo='Artifact'; st='artifact'; p='eAND'
       box=@(720, -140, 400, 50); nota='flutter build apk, con API_URL por --dart-define. No se publica en Google Play.' },
    @{ k='aSQL'; n='SQLite · violetboutique.db'; tipo='Artifact'; st='artifact'; p='eAND'
       box=@(720, -210, 400, 50); nota='mobile/lib/core/almacenamiento/base_local.dart: el paquete del cliente, las fotos y la cola de reservas (CU-13, CU-15, CU-17, CU-18).' },

    # ---- Railway ----
    @{ k='dRW'; n='Servidor Railway'; tipo='Device'; st='device'; c='API'
       box=@(40, -420, 1140, 400); nota='Construye cada servicio desde su Dockerfile (railway.json: builder DOCKERFILE) y lo corre en un contenedor. Inyecta PORT.' },
    @{ k='eDKW'; n='Docker · contenedor violetboutique-web (nginx:alpine)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dRW'; c='WEB'
       box=@(70, -470, 480, 310); nota='frontend-web/Dockerfile en dos etapas: node:22-alpine compila (ng build) y nginx:alpine sirve lo compilado.' },
    @{ k='aNGX'; n='nginx.conf'; tipo='Artifact'; st='artifact'; p='eDKW'
       box=@(100, -530, 420, 50); nota='Plantilla que resuelve $PORT y reenvia las rutas al index.html.' },
    @{ k='eDKA'; n='Docker · contenedor violetboutique-api (python:3.13-slim)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dRW'; c='API'
       box=@(590, -470, 560, 310); nota='backend/Dockerfile. Al arrancar corre alembic upgrade head y despues el servidor.' },
    @{ k='eGUN'; n='Gunicorn + workers Uvicorn (ASGI)'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='eDKA'; c='API'
       box=@(620, -520, 500, 230); nota='gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 2.' },
    @{ k='aIMG'; n='violetboutique-api:latest'; tipo='Artifact'; st='artifact'; p='eGUN'
       box=@(650, -570, 440, 50); nota='La imagen Docker de la API: FastAPI, los modulos de app/modules y las migraciones.' },
    @{ k='aMED'; n='volumen media/'; tipo='Artifact'; st='artifact'; p='eGUN'
       box=@(650, -640, 440, 50); nota='Volumen persistente en /app/media: logos de las empresas (CU-12) e imagenes del catalogo.' },

    # ---- Supabase ----
    @{ k='dSB'; n='Servidor Supabase · AWS us-east-1'; tipo='Device'; st='device'; c='SB'
       box=@(1240, -420, 600, 400); nota='La base de produccion.' },
    @{ k='ePOOL'; n='PgBouncer · session pooler'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dSB'; c='SB'
       box=@(1270, -470, 540, 70); nota='La API se conecta por el pooler, no por la conexion directa.' },
    @{ k='ePG'; n='PostgreSQL 17'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dSB'; c='SB'
       box=@(1270, -570, 540, 210); nota='Con Row Level Security por empresa (rol violet_app).' },
    @{ k='aESQ'; n='esquema violetboutique · 51 tablas · RLS'; tipo='Artifact'; st='artifact'; p='ePG'
       box=@(1300, -630, 480, 50); nota='Migraciones Alembic hasta 0028_cu17_operacion_offline. 38 tablas del tenant con RLS.' },

    # ---- Desarrollo ----
    @{ k='dDEV'; n='PC de desarrollo'; tipo='Device'; st='device'; c='DEV'
       box=@(40, -880, 700, 300); nota='La maquina de cada integrante.' },
    @{ k='eDCK'; n='Docker Desktop · docker-compose'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='dDEV'; c='DEV'
       box=@(70, -930, 640, 220); nota='docker-compose.yml: el servicio db siempre; el servicio api solo con el perfil api (normalmente la API corre fuera, con uvicorn --reload).' },
    @{ k='eCPG'; n='contenedor postgres:16-alpine · :5432'; tipo='ExecutionEnvironment'; st='executionEnvironment'; p='eDCK'; c='DEV'
       box=@(100, -980, 580, 140); nota='violetboutique_db, con healthcheck pg_isready.' },
    @{ k='aPGD'; n='volumen pgdata'; tipo='Artifact'; st='artifact'; p='eCPG'
       box=@(130, -1030, 520, 50); nota='Los datos de la base local, que sobreviven al contenedor.' },

    @{ k='dGH'; n='GitHub · MatiusProg/e_comerce_Ropa_virtual'; tipo='Device'; st='device'; c='DEV'
       box=@(800, -880, 380, 160); nota='El origen desde el que Railway construye las imagenes: no es un destino de despliegue.' },
    @{ k='aDKF'; n='Dockerfile + railway.json'; tipo='Artifact'; st='artifact'; p='dGH'
       box=@(830, -940, 320, 50); nota='Uno por servicio, en backend/ y en frontend-web/.' },

    # ---- Servicios externos ----
    @{ k='xBRE'; n='Brevo · API de correo'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(1900, -420, 280, 90); nota='Envia el acceso del administrador al dar de alta una empresa (CU-01, CU-11).' },
    @{ k='xGEM'; n='Google Gemini'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(1900, -560, 280, 90); nota='La IA del 1er parcial (recomendaciones, asistente, probador).' },
    @{ k='xSTR'; n='Stripe'; tipo='Node'; st='servicio externo'; c='EXT'
       box=@(1900, -700, 280, 90); nota='La pasarela de pago en linea del 1er parcial. Sin conexion no se usa (CU-16).' }
)

# El bundle de Angular es uno solo desplegado en dos nodos: va afuera, con «deploy».
$AFUERA = @(
    @{ k='aBND'; n='violetboutique-web · bundle Angular (PWA)'; box=@(1240, -40, 600, 60)
       nota='dist/frontend-web/browser: index.html, los .js, manifest.webmanifest y ngsw-worker.js. nginx lo sirve y cada navegador lo ejecuta.' }
)
$COMPONENTES = @(
    @{ k='cBE'; n='Backend · FastAPI'; box=@(1240, -140, 290, 60) },
    @{ k='cFE'; n='Frontend · Angular (PWA)'; box=@(1550, -140, 290, 60) },
    @{ k='cMO'; n='Móvil · Flutter'; box=@(1240, -230, 290, 60) }
)
$DEPLOY   = @(@('aBND','eNAV'), @('aBND','eDKW'))
$MANIFEST = @(@('aIMG','cBE'), @('aBND','cFE'), @('aAPK','cMO'))
$CAMINOS  = @(
    @('dCLI','dRW','HTTPS 443 · PWA y API REST'),
    @('dCEL','dRW','HTTPS 443 · API REST y sincronización'),
    @('dRW','dSB','TCP 5432 · TLS · session pooler'),
    @('dRW','xBRE','HTTPS 443'),
    @('dRW','xGEM','HTTPS 443'),
    @('dRW','xSTR','HTTPS 443 · webhook'),
    @('dGH','dRW','git push → build del Dockerfile'),
    @('dDEV','dGH','git push')
)

# =========================================================================
# 4.2.2 CAPAS
# =========================================================================
$CAPA1 = @(
    @{ k='M1';  n='Módulo 1 · Plataforma SaaS';             cu='CU-01, CU-11' },
    @{ k='M2';  n='Módulo 2 · Planes y suscripciones';      cu='CU-02 a CU-05' },
    @{ k='M3';  n='Módulo 3 · Aislamiento multitenant';     cu='CU-06 a CU-10, CU-12' },
    @{ k='M4';  n='Módulo 4 · PWA offline';                 cu='CU-13, CU-14, CU-18' },
    @{ k='M5';  n='Módulo 5 · Móvil offline';               cu='CU-13, CU-15, CU-18' },
    @{ k='M6';  n='Módulo 6 · Sincronización';              cu='CU-17' },
    @{ k='M7';  n='Módulo 7 · Ventas offline y caja';       cu='CU-19, CU-20' },
    @{ k='M12'; n='Módulo 12 · Pago sin conexión';          cu='CU-16' }
)
$CAPA2 = @(
    @{ k='FE'; n='Frontend · Angular (PWA)'; x=400; w=720; cols=2
       nota='frontend-web/. La SPA instalable como PWA.'
       arts=@('features/plataforma/', 'features/caja/', 'features/sucursal/', 'core/services/offline.service.ts', 'ngsw-config.json', 'public/manifest.webmanifest', 'nginx.conf', 'Dockerfile')
       realiza=@('M1','M2','M3','M4','M6','M7','M12') },
    @{ k='MO'; n='Móvil · Flutter'; x=1160; w=480; cols=1
       nota='mobile/. La aplicacion del cliente.'
       arts=@('lib/features/offline/', 'lib/core/almacenamiento/base_local.dart', 'lib/data/repositorios/repositorio_offline.dart', 'pubspec.yaml')
       realiza=@('M5','M6') },
    @{ k='BE'; n='Backend · FastAPI'; x=1680; w=720; cols=2
       nota='backend/. Python 3.13, FastAPI, SQLAlchemy 2 y psycopg 3.'
       arts=@('modules/plataforma/', 'modules/plataforma/contratacion/', 'modules/offline/', 'modules/caja/', 'modules/bitacora/', 'core/tenencia.py', 'core/dependencies.py', 'alembic/versions/', 'Dockerfile', 'railway.json')
       realiza=@('M1','M2','M3','M6','M7') }
)
# nodo: el del despliegue donde corre (estereotipo, color y «trace»).
$CAPA3 = @(
    @{ k='SW';  n='Service Worker + IndexedDB';          nodo='eNAV'; c='CLI'; st='nodo: navegador';      de=@('FE') },
    @{ k='NGX'; n='nginx';                               nodo='eDKW'; c='WEB'; st='nodo: Railway · web';  de=@('FE') },
    @{ k='FLU'; n='Flutter + sqflite (SQLite)';          nodo='eAND'; c='CEL'; st='nodo: smartphone';     de=@('MO') },
    @{ k='GUN'; n='Gunicorn + Uvicorn (ASGI)';           nodo='eGUN'; c='API'; st='nodo: Railway · API';  de=@('BE') },
    @{ k='PGL'; n='PostgreSQL 16 (postgres:16-alpine)';  nodo='eCPG'; c='DEV'; st='nodo: PC de desarrollo'; de=@() },
    @{ k='ORM'; n='SQLAlchemy 2 + psycopg 3 + Alembic';  nodo='eDKA'; c='API'; st='nodo: Railway · API';  de=@('BE') },
    @{ k='POOL'; n='PgBouncer · session pooler';         nodo='ePOOL'; c='SB'; st='nodo: Supabase';       de=@() },
    @{ k='PG';  n='PostgreSQL 17 + RLS';                 nodo='ePG';  c='SB';  st='nodo: Supabase';       de=@() }
)
# Dentro de la capa intermedia: quien usa a quien.
$INTERMEDIA = @(@('ORM','POOL','se conecta a'), @('POOL','PG','reparte conexiones a'), @('ORM','PGL','en desarrollo, se conecta a'))
$CAPA4 = @(
    @{ k='OSC'; n='Windows / Android + navegador';            nodo='dCLI'; c='CLI'; st='nodo: computadora o tablet'; sobre=@('SW') },
    @{ k='AND'; n='Android 14 (HyperOS)';                     nodo='dCEL'; c='CEL'; st='nodo: smartphone'; sobre=@('FLU') },
    @{ k='LNX'; n='Docker · Linux (contenedores de Railway)'; nodo='dRW';  c='API'; st='nodo: Servidor Railway'; sobre=@('GUN','ORM','NGX') },
    @{ k='WIN'; n='Docker Desktop · Windows 11';              nodo='dDEV'; c='DEV'; st='nodo: PC de desarrollo'; sobre=@('PGL') },
    @{ k='AWS'; n='Supabase · Linux en AWS us-east-1';        nodo='dSB';  c='SB';  st='nodo: Servidor Supabase'; sobre=@('POOL','PG') }
)

# =========================================================================
# EA por COM
# =========================================================================
$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}
function Poner($dia, $el, $l, $t, $ancho, $alto) {
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

$root = $ea.Models.GetAt(0)
$pP2 = Get-Paquete (Get-Paquete $root 'Violet Boutique') 'PARCIAL 2 - ICONIX'
if ($Rehacer) {
    for ($i = $pP2.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pP2.Packages.GetAt($i).Name -eq $N42) { Write-Output "Se borra [$N42]"; $pP2.Packages.DeleteAt($i, $false) }
    }
    $pP2.Packages.Refresh()
}
if (Get-Paquete $pP2 $N42) {
    Write-Output "  [$N42] ya existe, no se toca (usar -Rehacer)"
    $ea.CloseFile(); $ea.Exit(); exit 0
}
$p42 = $pP2.Packages.AddNew($N42, 'Package'); [void]$p42.Update(); $pP2.Packages.Refresh()
$pDes = $p42.Packages.AddNew('4.2.1 Despliegue', 'Package'); [void]$pDes.Update()
$pCap = $p42.Packages.AddNew('4.2.2 Capas', 'Package'); [void]$pCap.Update()
$p42.Packages.Refresh()

# ---------------------------------------------------------- despliegue --
$dDes = $pDes.Diagrams.AddNew($DESPLIEGUE, 'Deployment'); [void]$dDes.Update(); $pDes.Diagrams.Refresh()
$el = @{}; $padres = @(); $multip = @(); $nivel = @{}
foreach ($n in $NODOS) {
    $e = $pDes.Elements.AddNew($n.n, $n.tipo)
    $e.Stereotype = $n.st; $e.Notes = $n.nota; [void]$e.Update()
    if ($n.c) { $e.SetAppearance(1, 0, $COLOR[$n.c]); [void]$e.Update() }
    $el[$n.k] = $e
    $nivel[$n.k] = if ($n.p) { $nivel[$n.p] + 1 } else { 0 }
    if ($n.p) { $padres += @{ h = $e.ElementID; p = $el[$n.p].ElementID } }
    if ($n.mult) { $multip += $e.ElementID }
    Poner $dDes $e $n.box[0] $n.box[1] $n.box[2] $n.box[3]
}
foreach ($a in $AFUERA) {
    $e = $pDes.Elements.AddNew($a.n, 'Artifact'); $e.Stereotype = 'artifact'; $e.Notes = $a.nota; [void]$e.Update()
    $el[$a.k] = $e; $nivel[$a.k] = 9
    Poner $dDes $e $a.box[0] $a.box[1] $a.box[2] $a.box[3]
}
foreach ($c in $COMPONENTES) {
    $e = $pDes.Elements.AddNew($c.n, 'Component'); [void]$e.Update()
    $el[$c.k] = $e; $nivel[$c.k] = 9
    Poner $dDes $e $c.box[0] $c.box[1] $c.box[2] $c.box[3]
}
foreach ($r in $DEPLOY)   { New-Rel $el[$r[0]] $el[$r[1]] 'Deployment' 'deploy' '' }
foreach ($r in $MANIFEST) { New-Rel $el[$r[0]] $el[$r[1]] 'Manifest' 'manifest' '' }
foreach ($r in $CAMINOS)  { New-Rel $el[$r[0]] $el[$r[1]] 'CommunicationPath' $null $r[2] }
$ley = $pDes.Elements.AddNew('', 'Note')
$ley.Notes = "CÓMO SE LEE`r`n«device» hardware · «executionEnvironment» lo que corre adentro (Docker, Gunicorn, el navegador) · «artifact» el archivo que se despliega.`r`nLínea sólida: CommunicationPath con su protocolo. «deploy»: el artefacto corre en ese nodo. «manifest»: el artefacto implementa ese componente. [*]: hay muchos clientes.`r`nCada color es un nodo: el diagrama de capas (4.2.2) usa los mismos colores."
[void]$ley.Update(); Poner $dDes $ley 1240 -880 600 120
Write-Output "  $DESPLIEGUE : $($NODOS.Count + $AFUERA.Count + $COMPONENTES.Count) elementos"

# --------------------------------------------------------------- capas --
$dCap = $pCap.Diagrams.AddNew($CAPAS, 'Component'); [void]$dCap.Update(); $pCap.Diagrams.Refresh()
function New-ElCap($nombre, $tipo, $st, $nota) {
    $e = $pCap.Elements.AddNew($nombre, $tipo)
    if ($st) { $e.Stereotype = $st }
    if ($nota) { $e.Notes = $nota }
    [void]$e.Update(); return $e
}
$Y = @{ 1 = -60; 2 = -260; 3 = -700; 4 = -940 }
$rotulos = @("CAPA 1`r`nVista de análisis", "CAPA 2`r`nBackend + Frontend + Móvil", "CAPA 3`r`nCapa intermedia", "CAPA 4`r`nCapa de software")
for ($i = 1; $i -le 4; $i++) { $nt = New-ElCap '' 'Note' $null $rotulos[$i - 1]; Poner $dCap $nt 20 $Y[$i] 330 80 }

$c1 = @{}; $x = 400
foreach ($m in $CAPA1) {
    $e = New-ElCap $m.n 'Package' $null "Modulo del alcance (1.5.1). Casos de uso: $($m.cu)."
    Poner $dCap $e $x $Y[1] 230 76; $c1[$m.k] = $e; $x += 250
}
$c2 = @{}; $hijos = @{}
foreach ($b in $CAPA2) {
    $caja = New-ElCap $b.n 'Package' $null $b.nota
    $filas = [math]::Ceiling($b.arts.Count / $b.cols)
    $alto = 70 + $filas * 55
    Poner $dCap $caja $b.x $Y[2] $b.w $alto
    $c2[$b.k] = $caja; $hijos[$caja.ElementID] = @()
    $anchoArt = if ($b.cols -eq 1) { $b.w - 40 } else { [int](($b.w - 60) / 2) }
    for ($i = 0; $i -lt $b.arts.Count; $i++) {
        $col = $i % $b.cols; $fila = [math]::Floor($i / $b.cols)
        $a = New-ElCap $b.arts[$i] 'Artifact' $null "Archivo o carpeta de $($b.n)."
        Poner $dCap $a ($b.x + 20 + $col * ($anchoArt + 20)) ($Y[2] - 50 - $fila * 55) $anchoArt 45
        $hijos[$caja.ElementID] += $a.ElementID
    }
}
$c3 = @{}; $x = 400
foreach ($s in $CAPA3) {
    $e = New-ElCap $s.n 'Package' $s.st "Corre en el nodo '$($el[$s.nodo].Name)' del diagrama de despliegue (4.2.1)."
    $e.SetAppearance(1, 0, $COLOR[$s.c]); [void]$e.Update()
    Poner $dCap $e $x $Y[3] 260 90; $c3[$s.k] = $e; $x += 285
}
$c4 = @{}; $x = 400
foreach ($s in $CAPA4) {
    $e = New-ElCap $s.n 'Package' $s.st "Es el nodo '$($el[$s.nodo].Name)' del diagrama de despliegue (4.2.1)."
    $e.SetAppearance(1, 0, $COLOR[$s.c]); [void]$e.Update()
    Poner $dCap $e $x $Y[4] 400 90; $c4[$s.k] = $e; $x += 456
}
$n = @{ r = 0; e = 0; s = 0; t = 0 }
foreach ($b in $CAPA2) { foreach ($k in $b.realiza) { New-Rel $c1[$k] $c2[$b.k] 'Realisation' 'realiza' ''; $n.r++ } }
foreach ($s in $CAPA3) { foreach ($k in $s.de) { New-Rel $c2[$k] $c3[$s.k] 'Dependency' 'se ejecuta en' ''; $n.e++ } }
foreach ($r in $INTERMEDIA) { New-Rel $c3[$r[0]] $c3[$r[1]] 'Dependency' $r[2] ''; $n.e++ }
foreach ($s in $CAPA4) { foreach ($k in $s.sobre) { New-Rel $c3[$k] $c4[$s.k] 'Dependency' 'corre sobre' ''; $n.s++ } }
# «trace» de cada elemento de las capas 3 y 4 a su nodo del despliegue: queda
# en el modelo (ventana de trazabilidad) y no se dibuja, porque el nodo no
# esta en este diagrama.
foreach ($s in $CAPA3) { New-Rel $c3[$s.k] $el[$s.nodo] 'Abstraction' 'trace' ''; $n.t++ }
foreach ($s in $CAPA4) { New-Rel $c4[$s.k] $el[$s.nodo] 'Abstraction' 'trace' ''; $n.t++ }
$ley = New-ElCap '' 'Note' $null "Cada elemento de las capas 3 y 4 dice en su estereotipo en qué nodo del diagrama de despliegue (4.2.1) corre, tiene el mismo color que ese nodo y está unido a él con una relación «trace» en el modelo."
Poner $dCap $ley 20 -1080 600 70
Write-Output ("  {0} : «realiza» {1}, «se ejecuta en» {2}, «corre sobre» {3}, «trace» {4}" -f $CAPAS, $n.r, $n.e, $n.s, $n.t)

$didDes = $dDes.DiagramID; $didCap = $dCap.DiagramID
# Los ID, antes de cerrar EA: despues los objetos COM ya no responden.
$idEl = @{}; foreach ($k in $el.Keys) { $idEl[$k] = $el[$k].ElementID }
$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# Segunda pasada por OLEDB (EA cerrado): lo que la API COM no deja hacer.
#   a) ParentID: la contencion real, no solo dibujada.
#   b) Multiplicity '*' de los clientes.
#   c) Orden Z: Sequence mas bajo = se dibuja encima. Cuanto mas adentro, mas arriba.
# =========================================================================
$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
function Exec($sql) { $c = $cn.CreateCommand(); $c.CommandText = $sql; return $c.ExecuteNonQuery() }
foreach ($r in $padres) { [void](Exec "UPDATE t_object SET ParentID = $($r.p) WHERE Object_ID = $($r.h)") }
if ($multip.Count) { [void](Exec "UPDATE t_object SET Multiplicity = '*' WHERE Object_ID IN ($($multip -join ','))") }
foreach ($k in $el.Keys) {
    $seq = 200 - 40 * [math]::Min($nivel[$k], 4)
    [void](Exec "UPDATE t_diagramobjects SET Sequence = $seq WHERE Diagram_ID = $didDes AND Object_ID = $($idEl[$k])")
}
foreach ($caja in $hijos.Keys) {
    [void](Exec "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $didCap AND Object_ID = $caja")
    foreach ($h in $hijos[$caja]) {
        [void](Exec "UPDATE t_object SET ParentID = $caja WHERE Object_ID = $h")
        [void](Exec "UPDATE t_diagramobjects SET Sequence = 2 WHERE Diagram_ID = $didCap AND Object_ID = $h")
    }
}
$cn.Close()
Write-Output "  $($padres.Count) contenciones, $($multip.Count) multiplicidades y el orden Z escritos"
Write-Output 'OK'
