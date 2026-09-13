# =========================================================================
# CAP. 1 - 1.5 Modelo de Casos de Uso Estructurado, ACUMULADO.
#
# LA REGLA (fijada el 13/09/2026)
# ------------------------------
# El 1.5 de un ciclo muestra los casos de uso y los actores de ESE ciclo Y DE
# TODOS LOS ANTERIORES. El del Ciclo 2 lleva los 9 del Ciclo 1 mas sus 13; el
# del Ciclo 3 llevara esos 22 mas los suyos.
#
# Es lo que la seccion pide: «estructurar el modelo de casos de uso» es el
# modelo COMPLETO tal como quedo al cerrar el ciclo, no el delta. El 1.3.1 es
# el que va por caso de uso y por ciclo; el 1.5 es la foto del sistema entero.
#
# POR QUE ESTE SCRIPT Y NO -Rehacer SOBRE ea-cu-ciclo2.ps1
# --------------------------------------------------------
# Porque `-Rehacer` borra el paquete 'Ciclo 2' completo, y sus actores NO son
# solo suyos: los trece diagramas de comunicacion de 2.2 los tienen puestos en
# el lienzo. Borrarlos dejaria esos trece diagramas sin actor y con 48
# conectores de mensaje colgando. Comprobado por SQL antes de escribir esto.
#
# Asi que este script AGREGA los elementos del Ciclo 1 al paquete del Ciclo 2
# --- copias propias, como el resto del paquete --- y rehace UNICAMENTE el
# diagrama 1.5. Los trece diagramas por caso de uso no se tocan.
#
# NO EXPORTA IMAGENES.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    throw "No se encontro el paquete '$nombre'"
}
function Add-AlDiagrama($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

$root    = $ea.Models.GetAt(0)
$pRaiz   = Get-Paquete $root 'Violet Boutique'
$pCap1   = Get-Paquete $pRaiz 'CAP. 1 - Captura de Requisitos'
$pCiclo2 = Get-Paquete $pCap1 'Ciclo 2'

# Indice de lo que YA hay en el paquete, para no duplicar nada.
$yaEstan = @{}
foreach ($e in $pCiclo2.Elements) { $yaEstan["$($e.Type)|$($e.Name)"] = $e }
Write-Output "  el paquete Ciclo 2 tenia $($yaEstan.Count) elementos"

function Get-OCrear($nombre, $tipo, $notas) {
    $clave = "$tipo|$nombre"
    if ($yaEstan.ContainsKey($clave)) { return $yaEstan[$clave] }
    $e = $pCiclo2.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $pCiclo2.Elements.Refresh()
    $yaEstan[$clave] = $e
    return $e
}

# Regla 5: borrar un diagrama no borra sus conectores; se deduplica siempre.
function New-Conector($src, $dst, $tipo, $estereotipo) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq $tipo -and $c.Stereotype -eq $estereotipo) { return }
    }
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
}

# ---------------- actores que faltaban ----------------
# Cliente, Administrador, Encargado de Sucursal y Sistema ya estan.
$A = @{}
$A['cliente']   = Get-OCrear 'Cliente' 'Actor' $null
$A['admin']     = Get-OCrear 'Administrador' 'Actor' $null
$A['encargado'] = Get-OCrear 'Encargado de Sucursal' 'Actor' $null
$A['sistema']   = Get-OCrear 'Sistema (procesos automáticos)' 'Actor' $null

$A['interno'] = Get-OCrear 'Usuario interno' 'Actor' 'Actor abstracto. Personal de la empresa que se autentica con credenciales corporativas y opera dentro del ambito de datos que define su rol.'
if ($A['interno'].Abstract -ne '1') { $A['interno'].Abstract = '1'; [void]$A['interno'].Update() }
$A['cajero']    = Get-OCrear 'Cajero' 'Actor' 'Opera el punto de venta de una sucursal. Sus funciones propias llegan en el Ciclo 3.'
$A['proveedor'] = Get-OCrear 'Proveedor' 'Actor' 'Empresa que abastece prendas. Su acceso se limita a sus propios datos.'

# ---------------- casos de uso del Ciclo 1 ----------------
$U = @{}
$defC1 = @(
  @{k='cu01'; n='CU-01 Registrar cliente';                      nt='Permite a una persona crear su cuenta de cliente indicando sus datos personales, correo y contrasena, quedando habilitada para reservar y comprar.'},
  @{k='cu02'; n='CU-02 Iniciar y cerrar sesión';                 nt='Autentica al usuario con correo y contrasena y emite un token acorde a su rol; el cierre de sesion lo revoca.'},
  @{k='cu03'; n='CU-03 Gestionar usuarios y roles';              nt='Permite al Administrador crear, editar, activar o desactivar y eliminar cuentas de usuario, asignando su rol y su sucursal cuando corresponde.'},
  @{k='cu04'; n='CU-04 Gestionar perfil del cliente';            nt='Permite al Cliente consultar y modificar sus datos personales, sus tallas habituales, sus preferencias y sus direcciones de entrega.'},
  @{k='cu05'; n='CU-05 Gestionar ciudades y sucursales';         nt='Permite al Administrador registrar, editar y dar de baja ciudades y sucursales con su direccion, horario y capacidad de vestidores.'},
  @{k='cu06'; n='CU-06 Gestionar empleados';                     nt='Permite al Administrador registrar empleados y asignarlos a una sucursal, vinculandolos a su usuario del sistema.'},
  @{k='cu07'; n='CU-07 Gestionar proveedores';                   nt='Permite al Administrador registrar, editar y consultar proveedores con sus datos de contacto.'},
  @{k='cu08'; n='CU-08 Gestionar categorías, tallas y colores';  nt='Permite al Administrador mantener las categorias jerarquicas, el catalogo de tallas y el de colores.'},
  @{k='cu09'; n='CU-09 Gestionar temporadas y colecciones';      nt='Permite al Administrador registrar temporadas comerciales con su vigencia y las colecciones asociadas.'},
  @{k='verif'; n='Verificar correo electrónico';                 nt='Extension de CU-01. Solo ocurre si el registro se realizo con un correo que exige confirmacion.'},
  @{k='pass';  n='Cambiar contraseña';                           nt='Extension de CU-04. Solo ocurre si el Cliente elige modificar su contrasena.'},
  @{k='revoc'; n='Revocar sesiones activas';                     nt='Extension de CU-03 y CU-06. Solo ocurre si el usuario afectado tiene tokens vigentes.'}
)
foreach ($d in $defC1) { $U[$d.k] = Get-OCrear $d.n 'UseCase' $d.nt }

# Los del Ciclo 2, que ya existen: se recuperan por nombre.
$defC2 = @(
  @{k='cu17'; n='CU-17 Consultar catálogo'},
  @{k='cu18'; n='CU-18 Consultar ficha de producto'},
  @{k='cu19'; n='CU-19 Consultar disponibilidad por sucursal'},
  @{k='cu22'; n='CU-22 Crear reserva de prendas'},
  @{k='cu23'; n='CU-23 Consultar y cancelar reserva'},
  @{k='cu10'; n='CU-10 Gestionar productos y variantes'},
  @{k='cu11'; n='CU-11 Gestionar imágenes de producto'},
  @{k='cu13'; n='CU-13 Registrar ingreso de mercadería'},
  @{k='cu14'; n='CU-14 Consultar inventario consolidado'},
  @{k='cu15'; n='CU-15 Registrar movimiento de inventario'},
  @{k='cu16'; n='CU-16 Gestionar disponibilidad de la sucursal'},
  @{k='cu24'; n='CU-24 Atender reserva en sucursal'},
  @{k='cu25'; n='CU-25 Expirar reservas vencidas'},
  @{k='auth'; n='Autenticar usuario'}
)
foreach ($d in $defC2) {
    if (-not $yaEstan.ContainsKey("UseCase|$($d.n)")) { throw "Falta el caso de uso del Ciclo 2: $($d.n)" }
    $U[$d.k] = $yaEstan["UseCase|$($d.n)"]
}

$U['cu01'].ExtensionPoints = 'Tras crear la cuenta'; [void]$U['cu01'].Update()

# ---------------- relaciones del Ciclo 1 ----------------
foreach ($p in @(
  @('cliente','cu01'), @('cliente','cu04'), @('cliente','cu02'),
  @('interno','cu02'), @('proveedor','cu02'), @('proveedor','cu07'),
  @('admin','cu03'), @('admin','cu05'), @('admin','cu06'),
  @('admin','cu07'), @('admin','cu08'), @('admin','cu09'))) {
    New-Conector $A[$p[0]] $U[$p[1]] 'Association' $null
}
foreach ($k in @('admin','encargado','cajero')) { New-Conector $A[$k] $A['interno'] 'Generalization' $null }
foreach ($k in @('cu03','cu04','cu05','cu06','cu07','cu08','cu09')) { New-Conector $U[$k] $U['auth'] 'Dependency' 'include' }
New-Conector $U['cu06'] $U['cu03'] 'Dependency' 'include'
New-Conector $U['verif'] $U['cu01'] 'Dependency' 'extend'
New-Conector $U['cu02']  $U['cu01'] 'Dependency' 'extend'
New-Conector $U['pass']  $U['cu04'] 'Dependency' 'extend'
New-Conector $U['revoc'] $U['cu03'] 'Dependency' 'extend'
New-Conector $U['revoc'] $U['cu06'] 'Dependency' 'extend'

$pCiclo2.Elements.Refresh()
Write-Output "  ahora tiene $($pCiclo2.Elements.Count) elementos"

# =========================================================================
# El 1.5 acumulado. Se borra y se rehace SOLO este diagrama.
# =========================================================================
$nombre = '1.5 Modelo de Casos de Uso Estructurado - CICLO #2'
$pCiclo2.Diagrams.Refresh()
for ($i = $pCiclo2.Diagrams.Count - 1; $i -ge 0; $i--) {
    if ($pCiclo2.Diagrams.GetAt($i).Name -eq $nombre) {
        $pCiclo2.Diagrams.DeleteAt($i, $false)
        Write-Output '  1.5 anterior borrado (solo ese diagrama)'
    }
}
$pCiclo2.Diagrams.Refresh()

$dia = $pCiclo2.Diagrams.AddNew($nombre, 'UseCase')
$dia.Notes = 'Modelo de casos de uso al cerrar el Ciclo 2: los nueve del Ciclo 1 y los trece del Ciclo 2, con todos sus actores.'
[void]$dia.Update(); $pCiclo2.Diagrams.Refresh()

# Tres columnas: actores, Ciclo 1, Ciclo 2. La cuarta es el caso de uso de
# inclusion, que los dos ciclos comparten y por eso queda al costado.
$ACTORES = @(
  @{k='cliente';   t=-150;  w=130},
  @{k='interno';   t=-360;  w=150},
  @{k='admin';     t=-570;  w=140},
  @{k='encargado'; t=-780;  w=170},
  @{k='cajero';    t=-990;  w=130},
  @{k='proveedor'; t=-1200; w=140},
  @{k='sistema';   t=-1400; w=180}
)
foreach ($a in $ACTORES) { Add-AlDiagrama $dia $A[$a.k] 40 $a.t $a.w 80 }

$COL_C1 = @('cu01','cu02','cu03','cu04','cu05','cu06','cu07','cu08','cu09')
$COL_C1_EXT = @('verif','pass','revoc')
$COL_C2 = @('cu17','cu18','cu19','cu22','cu23','cu10','cu11','cu13','cu14','cu15','cu16','cu24','cu25')

$t = -40
foreach ($k in $COL_C1) { Add-AlDiagrama $dia $U[$k] 320 $t 250 85; $t -= 110 }
$t -= 30
foreach ($k in $COL_C1_EXT) { Add-AlDiagrama $dia $U[$k] 320 $t 250 85; $t -= 110 }

$t = -40
foreach ($k in $COL_C2) { Add-AlDiagrama $dia $U[$k] 680 $t 260 85; $t -= 110 }

Add-AlDiagrama $dia $U['auth'] 1060 -700 240 85

$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $nombre : $($dia.DiagramObjects.Count) objetos, $($dia.DiagramLinks.Count) relaciones"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
