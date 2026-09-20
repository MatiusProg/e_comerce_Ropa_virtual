# =========================================================================
# CAP. 1 - 1.5 Modelo de Casos de Uso Estructurado, ACUMULADO. CICLO 3.
#
# LA REGLA (fijada el 13/09/2026)
# ------------------------------
# El 1.5 de un ciclo muestra los casos de uso y los actores de ESE ciclo Y DE
# TODOS LOS ANTERIORES. El del Ciclo 2 lleva los 9 del Ciclo 1 mas sus 13; el
# del Ciclo 3 lleva esos 22 mas sus 20.
#
# Es lo que la seccion pide: «estructurar el modelo de casos de uso» es el
# modelo COMPLETO tal como quedo al cerrar el ciclo, no el delta. El 1.3.1 es
# el que va por caso de uso y por ciclo; el 1.5 es la foto del sistema entero.
#
# Lo reporto Karen el 20/09: el 1.5 del Ciclo 3 tenia sus 20 casos de uso y
# nada mas. La regla ya estaba escrita y aplicada al Ciclo 2 --- lo que falto
# fue el script equivalente para el 3. Este es ese script.
#
# POR QUE ESTE SCRIPT Y NO -Rehacer SOBRE ea-cu-ciclo3.ps1
# --------------------------------------------------------
# Porque `-Rehacer` borra el paquete 'Ciclo 3' completo, y sus actores NO son
# solo suyos: los veinte diagramas de comunicacion de 2.2 los tienen puestos
# en el lienzo. Borrarlos dejaria esos veinte diagramas sin actor y con los
# mensajes colgando. Es la misma razon por la que el Ciclo 2 tuvo su script
# aparte.
#
# Asi que este script AGREGA al paquete del Ciclo 3 los elementos de los
# Ciclos 1 y 2 --- copias propias, como el resto del paquete --- y rehace
# UNICAMENTE el diagrama 1.5. Los veinte diagramas por caso de uso no se
# tocan.
#
# NO EXPORTA IMAGENES.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\SI2\Primer_Parcial\docs\diagramas\VioletBoutique.eapx'
if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    throw "No se encontro el paquete '$nombre'"
}

# OJO: recibe el ID del elemento, no el elemento. Es la correccion del 13/09:
# `Elements.Refresh()` invalida las referencias COM ya guardadas y
# `.ElementID` empieza a devolver 0 --- EA dibuja igual los recuadros, pero
# ninguno queda ligado a un elemento y el diagrama sale sin una sola relacion,
# sin dar error en ningun lado.
function Add-AlDiagrama($dia, $idElemento, $l, $t, $ancho, $alto) {
    if (-not $idElemento) { throw 'Add-AlDiagrama recibio un id vacio' }
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $idElemento
    [void]$do.Update()
}

$root    = $ea.Models.GetAt(0)
$pRaiz   = Get-Paquete $root 'Violet Boutique'
$pCap1   = Get-Paquete $pRaiz 'CAP. 1 - Captura de Requisitos'
$pCiclo3 = Get-Paquete $pCap1 'Ciclo 3'

# ---------------------------------------------------------------------
# PASO PREVIO: el nombre roto de CU-27.
#
# En el modelo quedo guardado como 'CU-27 Realizar pedido y pagar en lÃ­nea':
# los dos bytes UTF-8 de la `i` acentuada (C3 AD) entraron como dos
# caracteres sueltos. El culpable es que `ea-cu-ciclo3.ps1` no tiene BOM ---
# PowerShell 5.1 lee un archivo sin BOM como cp1252, no como UTF-8 --- y eso
# se ve en el 1.3.2 exportado y ahora se veria tambien en el 1.5.
#
# Se repara aca, que es la proxima vez que alguien abre el paquete, y no se
# repite porque al generador ya se le puso el BOM.
# ---------------------------------------------------------------------
$roto = "CU-27 Realizar pedido y pagar en l$([char]0x00C3)$([char]0x00AD)nea"
$sano = "CU-27 Realizar pedido y pagar en l$([char]0x00ED)nea"
foreach ($e in $pCiclo3.Elements) {
    if ($e.Name -eq $roto) {
        $e.Name = $sano; [void]$e.Update()
        Write-Output '  CU-27: nombre reparado (estaba doblemente codificado)'
    }
}
$pCiclo3.Elements.Refresh()

# Indice de lo que YA hay en el paquete, para no duplicar nada.
$yaEstan = @{}
foreach ($e in $pCiclo3.Elements) { $yaEstan["$($e.Type)|$($e.Name)"] = $e }
Write-Output "  el paquete Ciclo 3 tenia $($yaEstan.Count) elementos"

function Get-OCrear($nombre, $tipo, $notas) {
    $clave = "$tipo|$nombre"
    if ($yaEstan.ContainsKey($clave)) { return $yaEstan[$clave] }
    $e = $pCiclo3.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $pCiclo3.Elements.Refresh()
    $yaEstan[$clave] = $e
    return $e
}

# Regla 5: borrar un diagrama no borra sus conectores; se deduplica siempre.
function New-Conector($src, $dst, $tipo, $estereotipo) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        # `[string]` en los dos lados a proposito: para una Association el
        # estereotipo del conector es cadena vacia y el parametro llega como
        # $null, y en PowerShell `'' -eq $null` es FALSO. Sin el casteo, la
        # deduplicacion no reconoce el conector que ya existe y lo vuelve a
        # crear en cada corrida: asi aparecieron 30 duplicados el 13/09.
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq $tipo -and
            [string]$c.Stereotype -eq [string]$estereotipo) { return }
    }
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
}

# ---------------- actores ----------------
# Los siete del paquete ya existen. OJO con el nombre del actor de procesos
# automaticos: en el paquete del Ciclo 3 esta SIN acento, distinto de como se
# llama en los paquetes de los Ciclos 1 y 2. Se usa EL QUE HAY, porque
# `Get-OCrear` busca por nombre: pedirlo con acento no lo encontraria y
# crearia un segundo actor, y el 1.5 saldria con dos cajas para el mismo
# actor y las relaciones repartidas entre las dos.
$A = @{}
$A['cliente']   = Get-OCrear 'Cliente' 'Actor' $null
$A['admin']     = Get-OCrear 'Administrador' 'Actor' $null
$A['encargado'] = Get-OCrear 'Encargado de Sucursal' 'Actor' $null
$A['cajero']    = Get-OCrear 'Cajero' 'Actor' $null
$A['proveedor'] = Get-OCrear 'Proveedor' 'Actor' $null
$A['sistema']   = Get-OCrear 'Sistema (procesos automaticos)' 'Actor' $null

# El unico que falta: el actor abstracto del que heredan los internos.
$A['interno'] = Get-OCrear 'Usuario interno' 'Actor' 'Actor abstracto. Personal de la empresa que se autentica con credenciales corporativas y opera dentro del ambito de datos que define su rol.'
if ($A['interno'].Abstract -ne '1') { $A['interno'].Abstract = '1'; [void]$A['interno'].Update() }

# ---------------- casos de uso del Ciclo 1 ----------------
$U = @{}
$defC1 = @(
  @{k='cu01'; n='CU-01 Registrar cliente';                      nt='Permite a una persona crear su cuenta de cliente indicando sus datos personales, correo y contrasena, quedando habilitada para reservar y comprar.'},
  @{k='cu02'; n='CU-02 Iniciar y cerrar sesión';                nt='Autentica al usuario con correo y contrasena y emite un token acorde a su rol; el cierre de sesion lo revoca.'},
  @{k='cu03'; n='CU-03 Gestionar usuarios y roles';             nt='Permite al Administrador crear, editar, activar o desactivar y eliminar cuentas de usuario, asignando su rol y su sucursal cuando corresponde.'},
  @{k='cu04'; n='CU-04 Gestionar perfil del cliente';           nt='Permite al Cliente consultar y modificar sus datos personales, sus tallas habituales, sus preferencias y sus direcciones de entrega.'},
  @{k='cu05'; n='CU-05 Gestionar ciudades y sucursales';        nt='Permite al Administrador registrar, editar y dar de baja ciudades y sucursales con su direccion, horario y capacidad de vestidores.'},
  @{k='cu06'; n='CU-06 Gestionar empleados';                    nt='Permite al Administrador registrar empleados y asignarlos a una sucursal, vinculandolos a su usuario del sistema.'},
  @{k='cu07'; n='CU-07 Gestionar proveedores';                  nt='Permite al Administrador registrar, editar y consultar proveedores con sus datos de contacto.'},
  @{k='cu08'; n='CU-08 Gestionar categorías, tallas y colores'; nt='Permite al Administrador mantener las categorias jerarquicas, el catalogo de tallas y el de colores.'},
  @{k='cu09'; n='CU-09 Gestionar temporadas y colecciones';     nt='Permite al Administrador registrar temporadas comerciales con su vigencia y las colecciones asociadas.'},
  @{k='verif'; n='Verificar correo electrónico';                nt='Extension de CU-01. Solo ocurre si el registro se realizo con un correo que exige confirmacion.'},
  @{k='pass';  n='Cambiar contraseña';                          nt='Extension de CU-04. Solo ocurre si el Cliente elige modificar su contrasena.'},
  @{k='revoc'; n='Revocar sesiones activas';                    nt='Extension de CU-03 y CU-06. Solo ocurre si el usuario afectado tiene tokens vigentes.'}
)
foreach ($d in $defC1) { $U[$d.k] = Get-OCrear $d.n 'UseCase' $d.nt }

# ---------------- casos de uso del Ciclo 2 ----------------
$defC2 = @(
  @{k='cu10'; n='CU-10 Gestionar productos y variantes';        nt='Permite al Administrador dar de alta y mantener prendas y generar sus variantes talla x color con su SKU.'},
  @{k='cu11'; n='CU-11 Gestionar imágenes de producto';         nt='Permite cargar y ordenar las imagenes de una prenda, marcar la principal y el PNG transparente del vestidor virtual.'},
  @{k='cu13'; n='CU-13 Registrar ingreso de mercadería';        nt='Registra la entrada de unidades a una sucursal generando su movimiento de inventario.'},
  @{k='cu14'; n='CU-14 Consultar inventario consolidado';       nt='Muestra el saldo de cada variante en toda la red de sucursales.'},
  @{k='cu15'; n='CU-15 Registrar movimiento de inventario';     nt='Registra ajustes, traspasos y mermas; ninguna cantidad cambia sin generar su movimiento.'},
  @{k='cu16'; n='CU-16 Gestionar disponibilidad de la sucursal'; nt='Permite al Encargado fijar el stock minimo y ver las alertas de reposicion de su sucursal.'},
  @{k='cu17'; n='CU-17 Consultar catálogo';                     nt='Vitrina publica: permite navegar y filtrar las prendas ofrecibles sin necesidad de sesion.'},
  @{k='cu18'; n='CU-18 Consultar ficha de producto';            nt='Muestra el detalle de una prenda con sus imagenes, sus variantes y su precio.'},
  @{k='cu19'; n='CU-19 Consultar disponibilidad por sucursal';  nt='Indica en que sucursales hay unidades de una variante.'},
  @{k='cu22'; n='CU-22 Crear reserva de prendas';               nt='Permite al Cliente apartar prendas en una sucursal para probarselas en una franja horaria.'},
  @{k='cu23'; n='CU-23 Consultar y cancelar reserva';           nt='Permite al Cliente ver sus reservas y cancelarlas, liberando las unidades apartadas.'},
  @{k='cu24'; n='CU-24 Atender reserva en sucursal';            nt='Permite al Encargado registrar el resultado de la prueba de cada prenda de una reserva.'},
  @{k='cu25'; n='CU-25 Expirar reservas vencidas';              nt='Proceso automatico que libera las unidades de las reservas que pasaron su franja sin ser atendidas.'}
)
foreach ($d in $defC2) { $U[$d.k] = Get-OCrear $d.n 'UseCase' $d.nt }

# El caso de uso de inclusion ya esta en el paquete desde el Ciclo 3.
if (-not $yaEstan.ContainsKey('UseCase|Autenticar usuario')) { throw 'Falta "Autenticar usuario" en el paquete Ciclo 3' }
$U['auth'] = $yaEstan['UseCase|Autenticar usuario']

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

# ---------------- relaciones del Ciclo 2 ----------------
foreach ($p in @(
  @('cliente','cu17'), @('cliente','cu18'), @('cliente','cu19'),
  @('cliente','cu22'), @('cliente','cu23'),
  @('admin','cu10'), @('admin','cu11'), @('admin','cu13'),
  @('admin','cu14'), @('admin','cu15'), @('admin','cu16'), @('admin','cu24'),
  @('encargado','cu13'), @('encargado','cu16'), @('encargado','cu24'),
  @('sistema','cu25'))) {
    New-Conector $A[$p[0]] $U[$p[1]] 'Association' $null
}
foreach ($k in @('cu10','cu11','cu13','cu14','cu15','cu16','cu22','cu23','cu24')) {
    New-Conector $U[$k] $U['auth'] 'Dependency' 'include'
}
New-Conector $U['cu22'] $U['cu19'] 'Dependency' 'include'
New-Conector $U['cu18'] $U['cu17'] 'Dependency' 'extend'
New-Conector $U['cu19'] $U['cu18'] 'Dependency' 'extend'
New-Conector $U['cu15'] $U['cu16'] 'Dependency' 'extend'

$pCiclo3.Elements.Refresh()
Write-Output "  ahora tiene $($pCiclo3.Elements.Count) elementos"

# =========================================================================
# El 1.5 acumulado. Se borra y se rehace SOLO este diagrama.
# =========================================================================
$nombre = '1.5 Modelo de Casos de Uso Estructurado - CICLO #3'
$pCiclo3.Diagrams.Refresh()
for ($i = $pCiclo3.Diagrams.Count - 1; $i -ge 0; $i--) {
    if ($pCiclo3.Diagrams.GetAt($i).Name -eq $nombre) {
        $pCiclo3.Diagrams.DeleteAt($i, $false)
        Write-Output '  1.5 anterior borrado (solo ese diagrama)'
    }
}
$pCiclo3.Diagrams.Refresh()

# Se releen los identificadores del paquete, ya sin referencias viejas dando
# vueltas: es la unica lectura que no puede estar invalidada.
$idDe = @{}
$pCiclo3.Elements.Refresh()
foreach ($e in $pCiclo3.Elements) { $idDe["$($e.Type)|$($e.Name)"] = $e.ElementID }

# La clave sale de las DEFINICIONES, no de la referencia COM: despues de un
# `Elements.Refresh()` esas referencias no sirven ni para leerles el nombre.
$nombreDe = @{
  'cliente'   = 'Actor|Cliente'
  'admin'     = 'Actor|Administrador'
  'encargado' = 'Actor|Encargado de Sucursal'
  'cajero'    = 'Actor|Cajero'
  'proveedor' = 'Actor|Proveedor'
  'sistema'   = 'Actor|Sistema (procesos automaticos)'
  'interno'   = 'Actor|Usuario interno'
  'pasarela'  = 'Actor|Pasarela de Pago'
  'ia'        = 'Actor|Servicio de IA'
  'auth'      = 'UseCase|Autenticar usuario'
}
foreach ($d in $defC1) { $nombreDe[$d.k] = "UseCase|$($d.n)" }
foreach ($d in $defC2) { $nombreDe[$d.k] = "UseCase|$($d.n)" }

# Los del Ciclo 3 se nombran COMO ESTAN EN EL MODELO, no como los escribe el
# generador del 1.3.2: varios quedaron sin tilde alli (devolucion, gestion,
# bitacora) y buscarlos con tilde no los encuentra.
$defC3 = @(
  'CU-12 Gestionar promociones',
  'CU-20 Gestionar favoritos',
  'CU-21 Utilizar vestidor virtual (RA)',
  'CU-26 Gestionar carrito de compras',
  "CU-27 Realizar pedido y pagar en l$([char]0x00ED)nea",
  'CU-28 Confirmar pago del pedido',
  'CU-29 Consultar historial de compras',
  'CU-30 Abrir y cerrar caja',
  'CU-31 Registrar venta presencial',
  'CU-32 Registrar devolucion',
  'CU-33 Recibir recomendaciones de prendas',
  'CU-34 Conversar con el asistente virtual',
  'CU-35 Generar reporte por comando de voz',
  'CU-36 Consultar tablero de indicadores',
  'CU-37 Generar reportes de gestion',
  'CU-38 Registrar productos del proveedor',
  'CU-39 Informar disponibilidad y plazo',
  'CU-40 Notificar eventos a los usuarios',
  "CU-41 Recuperar contrase$([char]0x00F1)a",
  'CU-42 Consultar la bitacora del sistema'
)
foreach ($n in $defC3) { $nombreDe["c3:$n"] = "UseCase|$n" }

function Id($clave) {
    $k = $nombreDe[$clave]
    if (-not $k -or -not $idDe.ContainsKey($k)) { throw "No se encontro el id de '$clave'" }
    return $idDe[$k]
}

$dia = $pCiclo3.Diagrams.AddNew($nombre, 'UseCase')
$dia.Notes = 'Modelo de casos de uso al cerrar el Ciclo 3: los nueve del Ciclo 1, los trece del Ciclo 2 y los veinte del Ciclo 3, con todos sus actores.'
[void]$dia.Update(); $pCiclo3.Diagrams.Refresh()

# Cuatro columnas: actores, Ciclo 1, Ciclo 2, Ciclo 3. La quinta es el caso de
# uso de inclusion, que los tres ciclos comparten y por eso queda al costado.
$ACTORES = @(
  @{k='cliente';   t=-150;  w=130},
  @{k='interno';   t=-360;  w=150},
  @{k='admin';     t=-570;  w=140},
  @{k='encargado'; t=-780;  w=170},
  @{k='cajero';    t=-990;  w=130},
  @{k='proveedor'; t=-1200; w=140},
  @{k='sistema';   t=-1410; w=180},
  @{k='pasarela';  t=-1620; w=150},
  @{k='ia';        t=-1830; w=150}
)
foreach ($a in $ACTORES) { Add-AlDiagrama $dia (Id $a.k) 40 $a.t $a.w 80 }

$COL_C1     = @('cu01','cu02','cu03','cu04','cu05','cu06','cu07','cu08','cu09')
$COL_C1_EXT = @('verif','pass','revoc')
$COL_C2     = @('cu10','cu11','cu13','cu14','cu15','cu16','cu17','cu18','cu19','cu22','cu23','cu24','cu25')

$t = -40
foreach ($k in $COL_C1) { Add-AlDiagrama $dia (Id $k) 320 $t 250 85; $t -= 110 }
$t -= 30
foreach ($k in $COL_C1_EXT) { Add-AlDiagrama $dia (Id $k) 320 $t 250 85; $t -= 110 }

$t = -40
foreach ($k in $COL_C2) { Add-AlDiagrama $dia (Id $k) 680 $t 260 85; $t -= 110 }

$t = -40
foreach ($n in $defC3) { Add-AlDiagrama $dia (Id "c3:$n") 1040 $t 280 85; $t -= 110 }

Add-AlDiagrama $dia (Id 'auth') 1420 -1000 240 85

$dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "  $nombre : $($dia.DiagramObjects.Count) objetos, $($dia.DiagramLinks.Count) relaciones"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
