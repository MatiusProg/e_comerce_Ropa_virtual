$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\FashionStore.eapx'
$base   = 'C:\Program Files (x86)\Sparx Systems\EA Trial\EABase.eapx'

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
$pFashion = New-Paquete $root     'FashionStore'
$pCap1    = New-Paquete $pFashion 'CAP. 1 - Captura de Requisitos'
$pCiclo1  = New-Paquete $pCap1    'Ciclo 1'

$dia = $pCiclo1.Diagrams.AddNew('1.3.2 Diagrama de Casos de Uso - CICLO #1', 'UseCase')
[void]$dia.Update(); $pCiclo1.Diagrams.Refresh()

# ---------------- actores ----------------
$A = @{}
$defA = @(
  @{k='cliente';   n='Cliente';               t=-100; nt='Persona que se registra, consulta y mantiene su perfil. Se autorregistra en el sistema.'},
  @{k='interno';   n='Usuario interno';       t=-330; nt='Actor abstracto. Personal de la empresa que se autentica con credenciales corporativas y opera dentro del ambito de datos que define su rol.'},
  @{k='admin';     n='Administrador';         t=-470; nt='Acceso completo: usuarios y roles, organizacion y maestros del catalogo.'},
  @{k='encargado'; n='Encargado de Sucursal'; t=-600; nt='Responsable operativo de una sucursal. Sus funciones propias llegan en el Ciclo 2.'},
  @{k='cajero';    n='Cajero';                t=-730; nt='Opera el punto de venta de una sucursal. Sus funciones propias llegan en el Ciclo 3.'},
  @{k='proveedor'; n='Proveedor';             t=-880; nt='Empresa que abastece prendas. Su acceso se limita a sus propios datos.'}
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
  @{k='cu01';  n='CU-01 Registrar cliente';                      l=300; t=-40;   nt='Permite a una persona crear su cuenta de cliente indicando sus datos personales, correo y contrasena, quedando habilitada para reservar y comprar.'},
  @{k='cu04';  n='CU-04 Gestionar perfil del cliente';           l=300; t=-150;  nt='Permite al Cliente consultar y modificar sus datos personales, sus tallas habituales, sus preferencias y sus direcciones de entrega.'},
  @{k='cu02';  n='CU-02 Iniciar y cerrar sesión';                l=300; t=-260;  nt='Autentica al usuario con correo y contrasena y emite un token acorde a su rol; el cierre de sesion lo revoca.'},
  @{k='cu03';  n='CU-03 Gestionar usuarios y roles';             l=300; t=-370;  nt='Permite al Administrador crear, editar, activar o desactivar y eliminar cuentas de usuario, asignando su rol y su sucursal cuando corresponde.'},
  @{k='cu05';  n='CU-05 Gestionar ciudades y sucursales';        l=300; t=-480;  nt='Permite al Administrador registrar, editar y dar de baja ciudades y sucursales con su direccion, horario y capacidad de vestidores.'},
  @{k='cu06';  n='CU-06 Gestionar empleados';                    l=300; t=-590;  nt='Permite al Administrador registrar empleados y asignarlos a una sucursal, vinculandolos a su usuario del sistema.'},
  @{k='cu07';  n='CU-07 Gestionar proveedores';                  l=300; t=-700;  nt='Permite al Administrador registrar, editar y consultar proveedores con sus datos de contacto.'},
  @{k='cu08';  n='CU-08 Gestionar categorías, tallas y colores'; l=300; t=-810;  nt='Permite al Administrador mantener las categorias jerarquicas, el catalogo de tallas y el de colores.'},
  @{k='cu09';  n='CU-09 Gestionar temporadas y colecciones';     l=300; t=-920;  nt='Permite al Administrador registrar temporadas comerciales con su vigencia y las colecciones asociadas.'},
  @{k='verif'; n='Verificar correo electrónico';                 l=680; t=-40;   nt='Extension de CU-01. Solo ocurre si el registro se realizo con un correo que exige confirmacion.'},
  @{k='pass';  n='Cambiar contraseña';                           l=680; t=-150;  nt='Extension de CU-04. Solo ocurre si el Cliente elige modificar su contrasena.'},
  @{k='revoc'; n='Revocar sesiones activas';                     l=680; t=-370;  nt='Extension de CU-03 y CU-06. Solo ocurre si el usuario afectado tiene tokens vigentes.'},
  @{k='auth';  n='Autenticar usuario';                           l=680; t=-1060; nt='Caso de uso de inclusion. Verifica el token y el rol antes del primer paso de toda operacion interna. No es uno de los 37 numerados: no produce por si mismo un resultado de valor para un actor.'}
)
foreach ($def in $defU) {
    $e = New-Elemento $pCiclo1 $def.n 'UseCase' $def.nt
    Add-AlDiagrama $dia $e $def.l $def.t 220 75
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
Write-Output "elementos: $($pCiclo1.Elements.Count) | objetos: $($dia.DiagramObjects.Count) | conectores: $($dia.DiagramLinks.Count)"

$prj = $ea.GetProjectInterface()
$png = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\casos-de-uso\1.3.2-casos-de-uso-ciclo-1.png'
Write-Output "export => $($prj.PutDiagramImageToFile($dia.DiagramGUID, $png, 1))"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
