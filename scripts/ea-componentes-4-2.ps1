param(
    # Borra el paquete 4.2 entero y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 4 - 4.2 Diagrama de Componentes del Sistema.
#
# ---- DE DONDE SALE ESTE FORMATO ----
# De los ejemplos de catedra 'CICLO 4.eapx' y 'CICLO 4 PROY_GRUP.eapx'. Los
# dos, siendo de proyectos distintos, usan la misma plantilla:
#   - izquierda : los paquetes funcionales del analisis 2.1, como elementos
#                 Package;
#   - centro    : un hub del que salen todas las dependencias;
#   - derecha   : las capas tecnicas, componentes con estereotipo «Frontend»
#                 y «Backend»;
#   - abajo     : un paquete "Base de Datos" con el motor como componente
#                 «database» y las tablas como elementos Object;
#   - sueltos   : los servicios externos.
# Todas las relaciones son Dependency.
#
# ---- TRES COSAS EN LAS QUE ESTE DIAGRAMA SE APARTA DEL EJEMPLO ----
#
# 1. DOS HUBS EN VEZ DE UNO. En los ejemplos, un unico App.tsx depende de
#    todo, incluida la base de datos. Eso no es cierto en ninguna
#    arquitectura de dos capas. Aqui el centro tiene los dos puntos de
#    composicion REALES del proyecto: app.routes.ts, que arma la SPA de
#    Angular, y main.py, que monta los routers de FastAPI y abre la sesion
#    contra PostgreSQL. Entre ellos hay una sola dependencia, la llamada HTTP.
#
# 2. LA CONTENCION ES DE VERDAD. En los ejemplos las tablas solo estan
#    DIBUJADAS encima del paquete "Base de Datos": ParentID = 0 en todos, asi
#    que al mover el paquete los hijos se quedan. Aqui las 16 tablas cuelgan
#    del elemento por ParentID.
#
# 3. EL COLOR DICE EN QUE ESTADO ESTA CADA PAQUETE. Verde, implementado y
#    montado en main.py; gris, pendiente. Es lo que pidio Mateo: que el
#    diagrama muestre el sistema COMO ESTA HOY, no como va a quedar.
#
# ADITIVO: abre el modelo y solo agrega lo que falta.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$NOMBRE_DIA = '4.2 Diagrama de Componentes del Sistema'

# Colores de fondo, en el entero BGR que guarda EA en ObjectStyle (BCol).
$VERDE = 14086358   # RGB 214,240,214 - implementado en el Ciclo 1
$GRIS  = 15132390   # RGB 230,230,230 - pendiente

# =========================================================================
# LOS PAQUETES FUNCIONALES DEL 2.1
# 'hecho' = tiene router montado en backend/app/main.py hoy.
# =========================================================================
$PAQUETES = @(
    @{ n = 'P1 · Seguridad y Usuarios';               hecho = $true;  nota = 'CU-01 a CU-04. backend/app/modules/seguridad. Montado: /auth, /usuarios, /perfil.' },
    @{ n = 'P2 · Organización';                       hecho = $true;  nota = 'CU-05 a CU-07. backend/app/modules/organizacion. Montado: /organizacion, /organizacion/empleados, /organizacion/proveedores.' },
    @{ n = 'P3 · Catálogo';                           hecho = $true;  nota = 'CU-08 y CU-09. backend/app/modules/catalogo. Montado: /catalogo, /catalogo/maestros, /catalogo/temporadas.' },
    @{ n = 'P4 · Inventario';                         hecho = $false; nota = 'Ciclo 2. El modulo existe en backend/app/modules/inventario pero su router esta comentado en main.py.' },
    @{ n = 'P5 · Catálogo Público y Disponibilidad';  hecho = $false; nota = 'Ciclo 2. Router comentado en main.py.' },
    @{ n = 'P6 · Reservas';                           hecho = $false; nota = 'Ciclo 2. Router comentado en main.py.' },
    @{ n = 'P7 · Ventas y Punto de Venta';            hecho = $false; nota = 'Ciclo 3. Router comentado en main.py.' },
    @{ n = 'P8 · Pagos';                              hecho = $false; nota = 'Ciclo 3. Router comentado en main.py. Depende de la pasarela de pago.' },
    @{ n = 'P9 · Vestidor Virtual (RA)';              hecho = $false; nota = 'Ciclo 3. Router comentado en main.py.' },
    @{ n = 'P10 · Inteligencia Artificial';           hecho = $false; nota = 'Ciclo 3. Router comentado en main.py. Por decision del 04/09/2026 el modelo tiene que ser gratuito.' },
    @{ n = 'P11 · Reportes y Tablero';                hecho = $false; nota = 'Ciclo 3. Router comentado en main.py.' }
)

# =========================================================================
# LAS CAPAS TECNICAS, TAL COMO ESTAN HOY EN EL REPOSITORIO
# =========================================================================
$FRONTEND = @(
    @{ n = 'Features';      nota = 'frontend-web/src/app/features: admin, auth, cliente, tienda, caja, sucursal, reportes, asistente, inicio.' },
    @{ n = 'Services';      nota = 'frontend-web/src/app/core/services: auth, usuarios, perfil, organizacion, empleados, proveedores, maestros, temporadas. Cada uno envuelve HttpClient.' },
    @{ n = 'Models';        nota = 'frontend-web/src/app/core/models: los tipos de entrada y salida de la API, uno por modulo.' },
    @{ n = 'Guards';        nota = 'frontend-web/src/app/core/guards/auth.guard.ts: corta la navegacion si no hay sesion o el rol no alcanza.' },
    @{ n = 'Interceptors';  nota = 'frontend-web/src/app/core/interceptors/auth.interceptor.ts: agrega el Bearer a cada peticion.' },
    @{ n = 'Shared';        nota = 'frontend-web/src/app/shared: bienvenida y confirmacion.' }
)

$BACKEND = @(
    @{ n = 'Routers';       nota = 'router.py de cada modulo. Declara los endpoints, las dependencias de seguridad y traduce los errores del servicio a HTTPException.' },
    @{ n = 'Services';      nota = 'service.py de cada modulo. Es el «controlador» de los diagramas de analisis: coordina el caso de uso y delimita la transaccion.' },
    @{ n = 'Repositories';  nota = 'repository.py de cada modulo. Lo unico que arma consultas; ningun otro archivo toca la sesion.' },
    @{ n = 'Schemas';       nota = 'schemas.py de cada modulo. Modelos Pydantic de entrada y salida.' },
    @{ n = 'Models (ORM)';  nota = 'models.py de cada modulo. Las 16 tablas mapeadas con SQLAlchemy 2.0.' },
    @{ n = 'Core';          nota = 'backend/app/core: config.py (settings), security.py (hash y JWT), dependencies.py (get_usuario_actual, requiere_roles).' },
    @{ n = 'DB';            nota = 'backend/app/db: session.py (engine y get_db), base.py (Base y el mixin Auditoria), seed.py (roles y permisos iniciales).' }
)

# =========================================================================
# LAS 16 TABLAS QUE EXISTEN HOY
# =========================================================================
$TABLAS = @(
    'rol', 'permiso', 'rol_permiso', 'usuario',
    'cliente', 'direccion_cliente', 'sesion_token', 'ciudad',
    'sucursal', 'empleado', 'proveedor', 'categoria',
    'talla', 'color', 'temporada', 'coleccion'
)

# =========================================================================
# SERVICIOS EXTERNOS
# =========================================================================
$EXTERNOS = @(
    @{ n = 'Supabase · session pooler'; hecho = $true;  nota = 'La base de produccion, en Supabase desde el 04/09/2026. Se conecta por el session pooler, no por la conexion directa.' },
    @{ n = 'PostgreSQL local :5433';    hecho = $true;  nota = 'La base de pruebas, en localhost puerto 5433. No es 5432 y no se sustituye por SQLite.' },
    @{ n = 'Pasarela de Pago';          hecho = $false; nota = 'Ciclo 3, P8. backend/app/integrations/pasarela_pago esta creado pero vacio.' },
    @{ n = 'Servicio de IA (gratuito)'; hecho = $false; nota = 'Ciclo 3, P10. backend/app/integrations/ia esta creado pero vacio. El modelo tiene que ser gratuito.' }
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
$pRaiz = BuscarPaquete $root 'Violet Boutique'
if (-not $pRaiz) { throw 'No se encontro el paquete Violet Boutique' }

$pCap4 = Get-OCrearPaquete $pRaiz 'CAP. 4 - Flujo de Trabajo: Implementacion'

if ($Rehacer) {
    for ($i = $pCap4.Packages.Count - 1; $i -ge 0; $i--) {
        if ($pCap4.Packages.GetAt($i).Name -eq '4.2 Componentes del Sistema') {
            $pCap4.Packages.DeleteAt($i, $false)
            Write-Output '  paquete 4.2 anterior eliminado (-Rehacer)'
        }
    }
    $pCap4.Packages.Refresh()
}

$p42 = Get-OCrearPaquete $pCap4 '4.2 Componentes del Sistema'

if (BuscarDiagrama $p42 $NOMBRE_DIA) {
    Write-Output "  $NOMBRE_DIA ya existe, no se toca"
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    exit 0
}

$dia = $p42.Diagrams.AddNew($NOMBRE_DIA, 'Component')
[void]$dia.Update(); $p42.Diagrams.Refresh()

$estilos = @()   # para pintar el fondo en la segunda pasada

function New-Elemento($nombre, $tipo, $estereotipo, $nota) {
    $e = $p42.Elements.AddNew($nombre, $tipo)
    if ($estereotipo) { $e.Stereotype = $estereotipo; $e.StereotypeEx = $estereotipo }
    if ($nota) { $e.Notes = $nota }
    [void]$e.Update()
    return $e
}
function Poner($el, $l, $t, $ancho, $alto, $color) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l + $ancho);t=$t;b=$($t - $alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
    if ($color) { $script:estilos += [pscustomobject]@{ id = $el.ElementID; col = $color } }
}
function New-Dependencia($src, $dst, $nombre) {
    $c = $src.Connectors.AddNew($nombre, 'Dependency')
    $c.SupplierID = $dst.ElementID
    $c.Direction = 'Source -> Destination'
    [void]$c.Update()
    $src.Connectors.Refresh()
}

# ---- Columna izquierda: los paquetes funcionales del 2.1 ----
$elPaq = @()
$y = -60
foreach ($p in $PAQUETES) {
    $e = New-Elemento $p.n 'Package' $null $p.nota
    Poner $e 40 $y 300 68 $(if ($p.hecho) { $VERDE } else { $GRIS })
    $elPaq += $e
    $y -= 92
}

# ---- Centro: los dos puntos de composicion reales ----
$elRoutes = New-Elemento 'app.routes.ts' 'Component' 'App' 'frontend-web/src/app/app.routes.ts. Punto de composicion de la SPA: declara las rutas por feature y les cuelga el auth.guard.'
Poner $elRoutes 440 -170 250 95 $VERDE

$elMain = New-Elemento 'main.py' 'Component' 'App' 'backend/app/main.py. Punto de composicion de la API: crea la aplicacion FastAPI 0.141, configura CORS y monta los routers. Hoy monta 11 y deja 8 comentados.'
Poner $elMain 440 -620 250 95 $VERDE

# ---- Derecha: las capas tecnicas ----
$elFront = @()
$y = -50
foreach ($c in $FRONTEND) {
    $e = New-Elemento $c.n 'Component' 'Frontend' $c.nota
    Poner $e 830 $y 260 68 $VERDE
    $elFront += $e
    $y -= 90
}

$elBack = @()
$y = -610
foreach ($c in $BACKEND) {
    $e = New-Elemento $c.n 'Component' 'Backend' $c.nota
    Poner $e 830 $y 260 68 $VERDE
    $elBack += $e
    $y -= 90
}

# ---- Abajo: la base de datos ----
$elBD = New-Elemento 'Base de Datos' 'Package' $null 'PostgreSQL 17. El esquema de 3.3.1: 16 tablas, todas creadas. Las de los Ciclos 2 y 3 todavia no existen.'
Poner $elBD 400 -1300 940 445 $null

$elMotor = New-Elemento 'PostgreSQL 17' 'Component' 'database' 'Motor de la base. En produccion corre en Supabase; para pruebas, en localhost:5433.'
Poner $elMotor 440 -1345 260 60 $null

$elTablas = @()
$col = 0; $fila = 0
foreach ($t in $TABLAS) {
    $lx = 440 + ($col * 215)
    $ly = -1440 - ($fila * 58)
    $e = New-Elemento $t 'Object' $null "Tabla $t."
    Poner $e $lx $ly 190 46 $null
    $elTablas += $e
    $col++
    if ($col -eq 4) { $col = 0; $fila++ }
}

# ---- Servicios externos ----
$elExt = @()
$y = -620
foreach ($x in $EXTERNOS) {
    $e = New-Elemento $x.n 'Component' 'externo' $x.nota
    Poner $e 1180 $y 250 68 $(if ($x.hecho) { $VERDE } else { $GRIS })
    $elExt += $e
    $y -= 92
}

# ---- Leyenda ----
$leyenda = New-Elemento '' 'Note' $null (
    "ESTADO AL 05/09/2026`n`n" +
    "Verde: implementado y montado en main.py.`n" +
    "Gris: modulo creado, router comentado.`n`n" +
    "11 routers montados (Ciclo 1: P1, P2, P3).`n" +
    "3 comentados del Ciclo 2, 5 del Ciclo 3.`n" +
    "16 de las 16 tablas del Ciclo 1, creadas."
)
Poner $leyenda 40 -1090 300 190 $null

# ---- Dependencias ----
foreach ($e in $elPaq)   { New-Dependencia $elRoutes $e '' }
foreach ($e in $elFront) { New-Dependencia $elRoutes $e '' }
New-Dependencia $elRoutes $elMain 'HTTP /api/v1'

foreach ($e in $elBack) { New-Dependencia $elMain $e '' }
New-Dependencia $elMain $elBD ''
foreach ($e in $elExt)  { New-Dependencia $elMain $e '' }

$elBD_dep = New-Dependencia $elBD $elMotor ''

$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $NOMBRE_DIA : $($dia.DiagramObjects.Count) elementos, $($dia.DiagramLinks.Count) dependencias"

$guids = $estilos | ForEach-Object { [pscustomobject]@{ id = $_.id; col = $_.col } }
$idBD = $elBD.ElementID
$idsTablas = ($elTablas | ForEach-Object { $_.ElementID }) -join ','

# Orden de dibujo: primero el motor, despues las tablas. El paquete va al
# final para que quede POR DETRAS. Ver la nota de la PARTE 2.
$zOrden = @($elMotor.ElementID) + ($elTablas | ForEach-Object { $_.ElementID })

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
[GC]::Collect(); [GC]::WaitForPendingFinalizers()
Start-Sleep -Milliseconds 1500

# =========================================================================
# PARTE 2 - Dos cosas que la API COM no deja hacer:
#
#   a) El color de fondo, que vive concatenado en
#      t_diagramobjects.ObjectStyle como 'BCol=<BGR>;'.
#
#   b) La contencion real de las tablas dentro del paquete "Base de Datos".
#      Asignar Element.ParentID por COM lanza NullReferenceException en
#      EA 15, asi que se escribe t_object.ParentID directo. Sin esto, las
#      tablas quedarian solo DIBUJADAS encima del paquete --- que es el
#      defecto que tienen los dos archivos de catedra.
# =========================================================================

$cn = New-Object System.Data.OleDb.OleDbConnection("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$modelo;")
$cn.Open()
$c = $cn.CreateCommand()
$c.CommandText = "SELECT Diagram_ID FROM t_diagram WHERE Name = '$NOMBRE_DIA'"
$did = [int]$c.ExecuteScalar()

foreach ($g in $guids) {
    $q = $cn.CreateCommand()
    $q.CommandText = "SELECT ObjectStyle FROM t_diagramobjects WHERE Diagram_ID = $did AND Object_ID = $($g.id)"
    $st = "$($q.ExecuteScalar())"
    if ($st -notmatch 'BCol=') {
        $st = $st + "BCol=$($g.col);"
        $u = $cn.CreateCommand()
        $u.CommandText = "UPDATE t_diagramobjects SET ObjectStyle = ? WHERE Diagram_ID = $did AND Object_ID = $($g.id)"
        [void]$u.Parameters.AddWithValue('s', $st)
        [void]$u.ExecuteNonQuery()
    }
}
$np = $cn.CreateCommand()
$np.CommandText = "UPDATE t_object SET ParentID = $idBD WHERE Object_ID IN ($idsTablas)"
$filas = $np.ExecuteNonQuery()

# ---- Orden Z ----
# En t_diagramobjects, Sequence MAS BAJO = se dibuja ENCIMA. Sin tocarlo, el
# paquete "Base de Datos" queda con una secuencia menor que la de casi todas
# las tablas y las tapa. Se le da la secuencia mas alta para mandarlo al
# fondo, y a lo que va adentro, las mas bajas.
$z = 2
foreach ($oid in $zOrden) {
    $u = $cn.CreateCommand()
    $u.CommandText = "UPDATE t_diagramobjects SET Sequence = $z WHERE Diagram_ID = $did AND Object_ID = $oid"
    [void]$u.ExecuteNonQuery()
    $z++
}
$uz = $cn.CreateCommand()
$uz.CommandText = "UPDATE t_diagramobjects SET Sequence = 100 WHERE Diagram_ID = $did AND Object_ID = $idBD"
[void]$uz.ExecuteNonQuery()

$cn.Close()
Write-Output "  color de fondo aplicado a $($guids.Count) elementos"
Write-Output "  $filas tablas colgadas del paquete Base de Datos por ParentID"
Write-Output "  orden Z: paquete al fondo, $($zOrden.Count) elementos adelante"
Write-Output 'OK'
