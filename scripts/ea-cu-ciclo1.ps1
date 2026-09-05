param(
    # Confirma que se quiere DESTRUIR el modelo y volver a crearlo desde cero.
    [switch]$Recrear
)

# =========================================================================
# CAP. 1 - 1.5 Modelo de Casos de Uso Estructurado y 1.3.2 un diagrama por
# caso de uso.
#
# ESTE ES EL UNICO GENERADOR QUE NO ES ADITIVO: crea el modelo desde la
# plantilla vacia de EA. Los otros diez esperan que el .eapx ya exista y solo
# le agregan lo que falta.
#
# Por eso exige el modificador -Recrear: se invoca igual que los demas, y sin
# la barrera un tipeo distraido borraria TODOS los diagramas de los cuatro
# capitulos --- incluidos los acomodados a mano, que no se recuperan.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
$base   = 'C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.eapx'

if ((Test-Path $modelo) -and -not $Recrear) {
    throw ("$modelo ya existe y este script lo BORRA para rehacerlo desde cero. " +
           "Si es lo que querés, volvé a correrlo con -Recrear. " +
           "Los diagramas del resto de los capitulos NO se recuperan.")
}

if (Test-Path $modelo) { Remove-Item $modelo -Force }
Copy-Item $base $modelo

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function New-Paquete($padre, $nombre) {
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update(); $padre.Packages.Refresh(); return $p
}
function New-Elemento($pkg, $nombre, $tipo, $notas) {
    $e = $pkg.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); return $e
}
function Add-AlDiagrama($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}
function New-Conector($src, $dst, $tipo, $estereotipo) {
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
}

$root     = $ea.Models.GetAt(0)
$pRaiz = New-Paquete $root     'Violet Boutique'
$pCap1    = New-Paquete $pRaiz 'CAP. 1 - Captura de Requisitos'
$pCiclo1  = New-Paquete $pCap1    'Ciclo 1'

$dia = $pCiclo1.Diagrams.AddNew('1.5 Modelo de Casos de Uso Estructurado - CICLO #1', 'UseCase')
[void]$dia.Update(); $pCiclo1.Diagrams.Refresh()

# ---------------- actores ----------------
$A = @{}
$defA = @(
  @{k='cliente';   n='Cliente';               t=-110; nt='Persona que se registra, consulta y mantiene su perfil. Se autorregistra en el sistema.'},
  @{k='interno';   n='Usuario interno';       t=-350; nt='Actor abstracto. Personal de la empresa que se autentica con credenciales corporativas y opera dentro del ambito de datos que define su rol.'},
  @{k='admin';     n='Administrador';         t=-500; nt='Acceso completo: usuarios y roles, organizacion y maestros del catalogo.'},
  @{k='encargado'; n='Encargado de Sucursal'; t=-640; nt='Responsable operativo de una sucursal. Sus funciones propias llegan en el Ciclo 2.'},
  @{k='cajero';    n='Cajero';                t=-780; nt='Opera el punto de venta de una sucursal. Sus funciones propias llegan en el Ciclo 3.'},
  @{k='proveedor'; n='Proveedor';             t=-930; nt='Empresa que abastece prendas. Su acceso se limita a sus propios datos.'}
)
foreach ($def in $defA) {
    $e = New-Elemento $pCiclo1 $def.n 'Actor' $def.nt
    if ($def.k -eq 'interno') { $e.Abstract = '1'; [void]$e.Update() }
    Add-AlDiagrama $dia $e 40 $def.t 100 80
    $A[$def.k] = $e
}

# ---------------- casos de uso ----------------
$U = @{}
$defU = @(
  @{k='cu01';  n='CU-01 Registrar cliente';                      l=300; t=-40; h=120;   nt='Permite a una persona crear su cuenta de cliente indicando sus datos personales, correo y contrasena, quedando habilitada para reservar y comprar.'},
  @{k='cu04';  n='CU-04 Gestionar perfil del cliente';           l=300; t=-185; h=85;  nt='Permite al Cliente consultar y modificar sus datos personales, sus tallas habituales, sus preferencias y sus direcciones de entrega.'},
  @{k='cu02';  n='CU-02 Iniciar y cerrar sesión';                l=300; t=-295; h=85;  nt='Autentica al usuario con correo y contrasena y emite un token acorde a su rol; el cierre de sesion lo revoca.'},
  @{k='cu03';  n='CU-03 Gestionar usuarios y roles';             l=300; t=-405; h=85;  nt='Permite al Administrador crear, editar, activar o desactivar y eliminar cuentas de usuario, asignando su rol y su sucursal cuando corresponde.'},
  @{k='cu05';  n='CU-05 Gestionar ciudades y sucursales';        l=300; t=-515; h=85;  nt='Permite al Administrador registrar, editar y dar de baja ciudades y sucursales con su direccion, horario y capacidad de vestidores.'},
  @{k='cu06';  n='CU-06 Gestionar empleados';                    l=300; t=-625; h=85;  nt='Permite al Administrador registrar empleados y asignarlos a una sucursal, vinculandolos a su usuario del sistema.'},
  @{k='cu07';  n='CU-07 Gestionar proveedores';                  l=300; t=-735; h=85;  nt='Permite al Administrador registrar, editar y consultar proveedores con sus datos de contacto.'},
  @{k='cu08';  n='CU-08 Gestionar categorías, tallas y colores'; l=300; t=-845; h=85;  nt='Permite al Administrador mantener las categorias jerarquicas, el catalogo de tallas y el de colores.'},
  @{k='cu09';  n='CU-09 Gestionar temporadas y colecciones';     l=300; t=-955; h=85;  nt='Permite al Administrador registrar temporadas comerciales con su vigencia y las colecciones asociadas.'},
  @{k='verif'; n='Verificar correo electrónico';                 l=680; t=-40; h=85;   nt='Extension de CU-01. Solo ocurre si el registro se realizo con un correo que exige confirmacion.'},
  @{k='pass';  n='Cambiar contraseña';                           l=680; t=-185; h=85;  nt='Extension de CU-04. Solo ocurre si el Cliente elige modificar su contrasena.'},
  @{k='revoc'; n='Revocar sesiones activas';                     l=680; t=-405; h=85;  nt='Extension de CU-03 y CU-06. Solo ocurre si el usuario afectado tiene tokens vigentes.'},
  @{k='auth';  n='Autenticar usuario';                           l=680; t=-1120; h=85; nt='Caso de uso de inclusion. Verifica el token y el rol antes del primer paso de toda operacion interna. No es uno de los 37 numerados: no produce por si mismo un resultado de valor para un actor.'}
)
foreach ($def in $defU) {
    $e = New-Elemento $pCiclo1 $def.n 'UseCase' $def.nt
    Add-AlDiagrama $dia $e $def.l $def.t 220 $def.h
    $U[$def.k] = $e
}

if ($A.Count -ne 6 -or $U.Count -ne 13) { throw "Faltan elementos: actores=$($A.Count) casos=$($U.Count)" }

# ---------------- asociaciones actor - caso de uso ----------------
foreach ($p in @(
  @('cliente','cu01'), @('cliente','cu04'), @('cliente','cu02'),
  @('interno','cu02'), @('proveedor','cu02'), @('proveedor','cu07'),
  @('admin','cu03'), @('admin','cu05'), @('admin','cu06'),
  @('admin','cu07'), @('admin','cu08'), @('admin','cu09'))) {
    New-Conector $A[$p[0]] $U[$p[1]] 'Association' $null
}

# ---------------- generalizacion de actores ----------------
foreach ($k in @('admin','encargado','cajero')) { New-Conector $A[$k] $A['interno'] 'Generalization' $null }

# ---------------- include ----------------
foreach ($k in @('cu03','cu04','cu05','cu06','cu07','cu08','cu09')) {
    New-Conector $U[$k] $U['auth'] 'Dependency' 'include'
}
New-Conector $U['cu06'] $U['cu03'] 'Dependency' 'include'

# ---------------- extend ----------------
New-Conector $U['verif'] $U['cu01'] 'Dependency' 'extend'
New-Conector $U['cu02']  $U['cu01'] 'Dependency' 'extend'
New-Conector $U['pass']  $U['cu04'] 'Dependency' 'extend'
New-Conector $U['revoc'] $U['cu03'] 'Dependency' 'extend'
New-Conector $U['revoc'] $U['cu06'] 'Dependency' 'extend'

$pCiclo1.Elements.Refresh(); $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "1.5  -> elementos: $($pCiclo1.Elements.Count) | objetos: $($dia.DiagramObjects.Count) | conectores: $($dia.DiagramLinks.Count)"

# =========================================================================
# 1.3.2 Disenar Casos de Uso: un diagrama por cada caso de uso.
# Los diagramas viven en el mismo paquete que los elementos: si estuvieran en un
# subpaquete, EA rotula cada elemento con "(from Ciclo 1)" y ensucia el dibujo.
# =========================================================================
function New-DiagramaDeCasoDeUso($paquete, $nombre, $puestos, $ocultar) {
    $d = $paquete.Diagrams.AddNew($nombre, 'UseCase')
    [void]$d.Update(); $paquete.Diagrams.Refresh()
    foreach ($x in $puestos) { Add-AlDiagrama $d $x.el $x.l $x.t $x.w $x.h }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()

    # Oculta las relaciones que existen entre elementos presentes pero que no son
    # objeto de este diagrama (p. ej. Cliente-CU-02 en el diagrama de CU-01).
    if ($ocultar) {
        foreach ($lnk in $d.DiagramLinks) {
            $con = $ea.GetConnectorByID($lnk.ConnectorID)
            foreach ($par in $ocultar) {
                if ($con.ClientID -eq $par[0].ElementID -and $con.SupplierID -eq $par[1].ElementID) {
                    $lnk.IsHidden = $true; [void]$lnk.Update()
                }
            }
        }
        $d.DiagramLinks.Refresh()
    }
    return $d
}

# --- CU-01 Registrar cliente ---
$U['cu01'].ExtensionPoints = 'Tras crear la cuenta'
[void]$U['cu01'].Update()

$dCu01 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-01 Registrar cliente' @(
    @{ el=$A['cliente']; l=40;  t=-150; w=100; h=80 },
    @{ el=$U['cu01'];    l=290; t=-120; w=250; h=115 },
    @{ el=$U['verif'];   l=700; t=-40;  w=230; h=80 },
    @{ el=$U['cu02'];    l=700; t=-210; w=230; h=80 }
) @( ,@($A['cliente'], $U['cu02']) )

# --- CU-02 Iniciar y cerrar sesion ---
# Los cinco actores humanos usan este caso de uso. Cliente y Proveedor se asocian
# directamente; Administrador, Encargado y Cajero lo heredan de Usuario interno.
# Se dibujan igual los tres concretos --- sin linea propia al caso de uso --- para
# que el diagrama se entienda sin tener al lado el 1.5.
$dCu02 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-02 Iniciar y cerrar sesión' @(
    @{ el=$A['cliente'];   l=40;  t=-40;  w=110; h=80 },
    @{ el=$A['interno'];   l=40;  t=-200; w=110; h=80 },
    @{ el=$A['admin'];     l=40;  t=-330; w=110; h=80 },
    @{ el=$A['encargado']; l=40;  t=-450; w=140; h=80 },
    @{ el=$A['cajero'];    l=40;  t=-570; w=110; h=80 },
    @{ el=$A['proveedor']; l=40;  t=-700; w=110; h=80 },
    @{ el=$U['cu02'];      l=340; t=-280; w=250; h=85 },
    @{ el=$U['cu01'];      l=750; t=-265; w=230; h=115 }
) @( ,@($A['cliente'], $U['cu01']) )

# --- CU-03 Gestionar usuarios y roles ---
$dCu03 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-03 Gestionar usuarios y roles' @(
    @{ el=$A['admin']; l=40;  t=-120; w=100; h=80 },
    @{ el=$U['cu03'];  l=290; t=-110; w=250; h=85 },
    @{ el=$U['auth'];  l=700; t=-40;  w=230; h=85 },
    @{ el=$U['revoc']; l=700; t=-180; w=230; h=85 }
) $null

# --- CU-04 Gestionar perfil del cliente ---
$dCu04 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-04 Gestionar perfil del cliente' @(
    @{ el=$A['cliente']; l=40;  t=-120; w=100; h=80 },
    @{ el=$U['cu04'];    l=290; t=-110; w=250; h=85 },
    @{ el=$U['auth'];    l=700; t=-40;  w=230; h=85 },
    @{ el=$U['pass'];    l=700; t=-180; w=230; h=85 }
) $null

# --- CU-05 Gestionar ciudades y sucursales ---
$dCu05 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-05 Gestionar ciudades y sucursales' @(
    @{ el=$A['admin']; l=40;  t=-80; w=100; h=80 },
    @{ el=$U['cu05'];  l=290; t=-70; w=250; h=85 },
    @{ el=$U['auth'];  l=700; t=-70; w=230; h=85 }
) $null

# --- CU-06 Gestionar empleados ---
$dCu06 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-06 Gestionar empleados' @(
    @{ el=$A['admin']; l=40;  t=-160; w=100; h=80 },
    @{ el=$U['cu06'];  l=290; t=-150; w=250; h=85 },
    @{ el=$U['cu03'];  l=700; t=-40;  w=230; h=85 },
    @{ el=$U['auth'];  l=700; t=-160; w=230; h=85 },
    @{ el=$U['revoc']; l=700; t=-280; w=230; h=85 }
) @( @($A['admin'], $U['cu03']), @($U['cu03'], $U['auth']), @($U['revoc'], $U['cu03']) )

# --- CU-07 Gestionar proveedores ---
$dCu07 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-07 Gestionar proveedores' @(
    @{ el=$A['admin'];     l=40;  t=-60;  w=100; h=80 },
    @{ el=$A['proveedor']; l=40;  t=-180; w=100; h=80 },
    @{ el=$U['cu07'];      l=290; t=-110; w=250; h=85 },
    @{ el=$U['auth'];      l=700; t=-110; w=230; h=85 }
) $null

# --- CU-08 Gestionar categorias, tallas y colores ---
$dCu08 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-08 Gestionar categorías, tallas y colores' @(
    @{ el=$A['admin']; l=40;  t=-80; w=100; h=80 },
    @{ el=$U['cu08'];  l=290; t=-70; w=250; h=85 },
    @{ el=$U['auth'];  l=700; t=-70; w=230; h=85 }
) $null

# --- CU-09 Gestionar temporadas y colecciones ---
$dCu09 = New-DiagramaDeCasoDeUso $pCiclo1 'CU-09 Gestionar temporadas y colecciones' @(
    @{ el=$A['admin']; l=40;  t=-80; w=100; h=80 },
    @{ el=$U['cu09'];  l=290; t=-70; w=250; h=85 },
    @{ el=$U['auth'];  l=700; t=-70; w=230; h=85 }
) $null

# --- exportacion -------------------------------------------------------------
$prj = $ea.GetProjectInterface()
$dirPng = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\casos-de-uso\'

$salidas = @(
    @{ d=$dia;   f='1.5-modelo-estructurado-ciclo-1.png';               n='1.5  ' },
    @{ d=$dCu01; f='1.3.2-cu-01-registrar-cliente.png';                 n='CU-01' },
    @{ d=$dCu02; f='1.3.2-cu-02-iniciar-y-cerrar-sesion.png';           n='CU-02' },
    @{ d=$dCu03; f='1.3.2-cu-03-gestionar-usuarios-y-roles.png';        n='CU-03' },
    @{ d=$dCu04; f='1.3.2-cu-04-gestionar-perfil-del-cliente.png';      n='CU-04' },
    @{ d=$dCu05; f='1.3.2-cu-05-gestionar-ciudades-y-sucursales.png';   n='CU-05' },
    @{ d=$dCu06; f='1.3.2-cu-06-gestionar-empleados.png';               n='CU-06' },
    @{ d=$dCu07; f='1.3.2-cu-07-gestionar-proveedores.png';             n='CU-07' },
    @{ d=$dCu08; f='1.3.2-cu-08-gestionar-categorias-tallas-colores.png'; n='CU-08' },
    @{ d=$dCu09; f='1.3.2-cu-09-gestionar-temporadas-y-colecciones.png'; n='CU-09' }
)
foreach ($s in $salidas) {
    $visibles = ($s.d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
    $exp = $prj.PutDiagramImageToFile($s.d.DiagramGUID, $dirPng + $s.f, 1)
    Write-Output ("{0} -> objetos: {1,2} | relaciones visibles: {2,2} | export: {3}" -f $s.n, $s.d.DiagramObjects.Count, $visibles, $exp)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
