param(
    # Borra el paquete 'Ciclo 2' del CAP. 1 y lo vuelve a generar.
    [switch]$Rehacer
)

# =========================================================================
# CAP. 1 - 1.5 Modelo de Casos de Uso Estructurado y 1.3.1 Disenar CU,
# un diagrama por caso de uso. CICLO 2: los trece casos de uso del nucleo
# del negocio (CU-10, CU-11, CU-13 a CU-19, CU-22 a CU-25).
#
# ESTE GENERADOR SI ES ADITIVO --- al reves que ea-cu-ciclo1.ps1, que crea el
# modelo desde la plantilla vacia y por eso exige -Recrear. Este abre el
# .eapx existente y solo le agrega el paquete 'Ciclo 2' con sus catorce
# diagramas. Si el paquete ya esta, no lo toca; para rehacerlo, -Rehacer.
#
# POR QUE EL PAQUETE 'Ciclo 2' ES AUTOCONTENIDO
# ---------------------------------------------
# Los actores y el caso de uso de inclusion se crean de nuevo aca en vez de
# reutilizar los del paquete 'Ciclo 1', y es a proposito. Son las reglas 2 y 3
# del manual:
#
#   - Regla 2: si el diagrama y sus elementos viven en paquetes distintos, EA
#     rotula cada elemento con "(from Ciclo 1)" debajo del nombre y ensucia
#     los catorce dibujos.
#   - Regla 3: EA dibuja TODA relacion que exista entre los elementos que estan
#     en el lienzo. Compartiendo el actor Administrador, el diagrama de CU-10
#     dibujaria tambien sus lineas a CU-03, CU-05, CU-06, CU-07, CU-08 y CU-09
#     --- seis relaciones ajenas que habria que ocultar una por una en cada
#     diagrama del ciclo.
#
# Cada paquete de ciclo es una vista del modelo en un momento del proyecto, y
# es la misma decision que ya tomo el generador del Ciclo 1.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'
$dirPng = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\casos-de-uso\'

if (-not (Test-Path $modelo)) {
    throw "No existe $modelo. Este generador es aditivo: el modelo tiene que existir."
}

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------------------------------------------------------- helpers --

function Get-Paquete($padre, $nombre) {
    $padre.Packages.Refresh()
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    return $null
}

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

# Regla 5: borrar un diagrama NO borra sus conectores. Se deduplica siempre,
# o una segunda corrida deja el modelo con las relaciones por duplicado.
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

function New-DiagramaDeCasoDeUso($paquete, $nombre, $puestos, $ocultar) {
    $d = $paquete.Diagrams.AddNew($nombre, 'UseCase')
    [void]$d.Update(); $paquete.Diagrams.Refresh()
    foreach ($x in $puestos) { Add-AlDiagrama $d $x.el $x.l $x.t $x.w $x.h }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()

    # Regla 3: oculta las relaciones que existen entre elementos presentes en
    # el lienzo pero que no son objeto de ESTE diagrama.
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

# ------------------------------------------------------------ ubicacion ----

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-Paquete $root 'Violet Boutique'
if (-not $pRaiz) { throw "No se encontro el paquete 'Violet Boutique' en el modelo." }
$pCap1 = Get-Paquete $pRaiz 'CAP. 1 - Captura de Requisitos'
if (-not $pCap1) { throw "No se encontro 'CAP. 1 - Captura de Requisitos'." }

$pCiclo2 = Get-Paquete $pCap1 'Ciclo 2'
if ($pCiclo2 -and -not $Rehacer) {
    Write-Output "El paquete 'Ciclo 2' ya existe y este generador es aditivo: no se toca."
    Write-Output "Para rehacerlo desde cero, volve a correrlo con -Rehacer."
    $ea.CloseFile(); $ea.Exit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
    return
}
if ($pCiclo2 -and $Rehacer) {
    for ($i = 0; $i -lt $pCap1.Packages.Count; $i++) {
        if ($pCap1.Packages.GetAt($i).Name -eq 'Ciclo 2') { $pCap1.Packages.DeleteAt($i, $false); break }
    }
    $pCap1.Packages.Refresh()
    Write-Output "Paquete 'Ciclo 2' borrado (-Rehacer)."
}
$pCiclo2 = New-Paquete $pCap1 'Ciclo 2'

# =========================================================================
# 1.5  Modelo de Casos de Uso Estructurado - CICLO #2
# =========================================================================

$dia = $pCiclo2.Diagrams.AddNew('1.5 Modelo de Casos de Uso Estructurado - CICLO #2', 'UseCase')
[void]$dia.Update(); $pCiclo2.Diagrams.Refresh()

# ---------------- actores ----------------
# Cuatro, no nueve: solo los que inician algun caso de uso de este ciclo. El
# Cajero, el Proveedor, la Pasarela de Pago y los dos servicios externos no
# aparecen porque ningun CU del Ciclo 2 los tiene como iniciador.
$A = @{}
$defA = @(
  @{k='cliente';   n='Cliente';                        t=-250;  h=80;  nt='Persona que consulta el catalogo, mira la ficha de una prenda, averigua donde hay existencia y reserva para probarse en una sucursal.'},
  @{k='admin';     n='Administrador';                  t=-800;  h=80;  nt='Acceso completo. En este ciclo mantiene el catalogo de productos y sus variantes, y opera el inventario de toda la red.'},
  @{k='encargado'; n='Encargado de Sucursal';          t=-1000; h=80;  nt='Responsable operativo de una sucursal. Su ambito de datos esta restringido a su local: registra ingresos, vigila la disponibilidad y atiende las reservas dirigidas a su tienda.'},
  @{k='sistema';   n='Sistema (procesos automáticos)'; t=-1420; h=80;  nt='A6. Procesos que el sistema ejecuta sin intervencion humana. En este ciclo, la expiracion de las reservas vencidas con liberacion del stock apartado.'}
)
foreach ($def in $defA) {
    $e = New-Elemento $pCiclo2 $def.n 'Actor' $def.nt
    Add-AlDiagrama $dia $e 40 $def.t 130 $def.h
    $A[$def.k] = $e
}

# ---------------- casos de uso ----------------
# En una columna, agrupados por paquete de analisis: primero los del Cliente
# (P5 y P6), despues los internos (P3 y P4), y al final el proceso automatico.
$U = @{}
$defU = @(
  @{k='cu17'; n='CU-17 Consultar catálogo';                       l=340; t=-40;   h=85;  nt='Permite al Cliente recorrer las prendas ofrecibles con busqueda, filtros, orden y paginacion, viendo foto, categoria, rango de precios y colores.'},
  @{k='cu18'; n='CU-18 Consultar ficha de producto';              l=340; t=-150;  h=85;  nt='Permite al Cliente ver el detalle de una prenda y elegir talla y color hasta fijar una variante con su precio propio y su SKU.'},
  @{k='cu19'; n='CU-19 Consultar disponibilidad por sucursal';    l=340; t=-260;  h=85;  nt='Permite al Cliente saber en que sucursales hay unidades disponibles de la variante elegida, con su ciudad y su cantidad.'},
  @{k='cu22'; n='CU-22 Crear reserva de prendas';                 l=340; t=-390;  h=85;  nt='Permite al Cliente apartar varias prendas en una sucursal y una franja horaria para probarselas. El stock pasa de disponible a reservado en una sola transaccion.'},
  @{k='cu23'; n='CU-23 Consultar y cancelar reserva';             l=340; t=-500;  h=85;  nt='Permite al Cliente ver el estado y el detalle de sus reservas y cancelar las que todavia no fueron atendidas, liberando el stock apartado.'},
  @{k='cu10'; n='CU-10 Gestionar productos y variantes';          l=340; t=-660;  h=85;  nt='Permite al Administrador registrar, editar y desactivar productos, y generar sus variantes talla x color con su SKU y su precio.'},
  @{k='cu11'; n='CU-11 Gestionar imágenes de producto';           l=340; t=-770;  h=85;  nt='Permite al Administrador cargar y organizar la galeria de un producto: imagen principal, imagenes por variante y las marcadas para el vestidor virtual.'},
  @{k='cu13'; n='CU-13 Registrar ingreso de mercadería';          l=340; t=-880;  h=85;  nt='Permite registrar el remito de un envio que llego a una sucursal, subiendo la existencia de cada variante y dejando un movimiento de INGRESO por linea.'},
  @{k='cu14'; n='CU-14 Consultar inventario consolidado';         l=340; t=-990;  h=85;  nt='Permite al Administrador ver la existencia de toda la red por variante y por sucursal, con lo disponible, lo reservado y lo fisico.'},
  @{k='cu15'; n='CU-15 Registrar movimiento de inventario';       l=340; t=-1100; h=85;  nt='Permite corregir el saldo de una variante en una sucursal por conteo fisico, merma o traslado, dejando siempre el movimiento que lo explica.'},
  @{k='cu16'; n='CU-16 Gestionar disponibilidad de la sucursal';  l=340; t=-1210; h=85;  nt='Permite al Encargado ver la existencia de su local, fijar el punto de reposicion de cada prenda y trabajar sobre el panel de alertas de stock bajo.'},
  @{k='cu24'; n='CU-24 Atender reserva en sucursal';              l=340; t=-1320; h=85;  nt='Permite al Encargado preparar las prendas de una reserva y cerrarla registrando, por cada prenda, si el cliente se la llevo o no.'},
  @{k='cu25'; n='CU-25 Expirar reservas vencidas';                l=340; t=-1440; h=85;  nt='Proceso automatico. Cierra las reservas cuya franja venció sin ser atendidas y devuelve al disponible el stock que tenian apartado.'},
  @{k='auth'; n='Autenticar usuario';                             l=760; t=-1000; h=85;  nt='Caso de uso de inclusion, ya presente en el Ciclo 1. Verifica el token y el rol antes del primer paso de toda operacion que exige sesion. No es uno de los casos de uso numerados: no produce por si mismo un resultado de valor para un actor.'}
)
foreach ($def in $defU) {
    $e = New-Elemento $pCiclo2 $def.n 'UseCase' $def.nt
    Add-AlDiagrama $dia $e $def.l $def.t 260 $def.h
    $U[$def.k] = $e
}

if ($A.Count -ne 4 -or $U.Count -ne 14) { throw "Faltan elementos: actores=$($A.Count) casos=$($U.Count)" }

# ---------------- puntos de extension ----------------
$U['cu17'].ExtensionPoints = 'Al elegir una prenda';            [void]$U['cu17'].Update()
$U['cu18'].ExtensionPoints = 'Al quedar fijada la variante';    [void]$U['cu18'].Update()
$U['cu16'].ExtensionPoints = 'Al elegir una prenda del listado'; [void]$U['cu16'].Update()

# ---------------- asociaciones actor - caso de uso ----------------
foreach ($p in @(
  # El Cliente: la vitrina publica y sus reservas.
  @('cliente','cu17'), @('cliente','cu18'), @('cliente','cu19'),
  @('cliente','cu22'), @('cliente','cu23'),
  # El Administrador: el catalogo y el inventario de toda la red.
  @('admin','cu10'), @('admin','cu11'), @('admin','cu13'),
  @('admin','cu14'), @('admin','cu15'), @('admin','cu16'), @('admin','cu24'),
  # El Encargado: solo su sucursal.
  @('encargado','cu13'), @('encargado','cu16'), @('encargado','cu24'),
  # A6.
  @('sistema','cu25'))) {
    New-Conector $A[$p[0]] $U[$p[1]] 'Association' $null
}

# ---------------- include ----------------
# Toda operacion con sesion incluye la autenticacion. CU-17, CU-18 y CU-19 NO:
# la vitrina es publica --- su router no exige token --- y esa es justamente la
# diferencia que el diagrama tiene que dejar ver.
foreach ($k in @('cu10','cu11','cu13','cu14','cu15','cu16','cu22','cu23','cu24')) {
    New-Conector $U[$k] $U['auth'] 'Dependency' 'include'
}
# CU-22 cruza la disponibilidad de cada variante para ofrecer solo las
# sucursales que tienen TODAS las prendas: no es opcional, pasa siempre.
New-Conector $U['cu22'] $U['cu19'] 'Dependency' 'include'

# ---------------- extend ----------------
# CU-18 extiende CU-17 en 'Al elegir una prenda': recorrer el catalogo se
# completa sin abrir ninguna ficha.
New-Conector $U['cu18'] $U['cu17'] 'Dependency' 'extend'
# CU-19 extiende CU-18: la ficha esta completa sin la disponibilidad --- la
# propia ficha dice que es un dato de apoyo y que perderlo no rompe la pantalla.
New-Conector $U['cu19'] $U['cu18'] 'Dependency' 'extend'
# CU-15 extiende CU-16: el flujo alternativo 3a de CU-16 es la misma operacion
# de ajuste de CU-15, acotada al local del Encargado.
New-Conector $U['cu15'] $U['cu16'] 'Dependency' 'extend'

$pCiclo2.Elements.Refresh(); $dia.DiagramObjects.Refresh(); $dia.DiagramLinks.Refresh()
Write-Output "1.5  -> elementos: $($pCiclo2.Elements.Count) | objetos: $($dia.DiagramObjects.Count) | conectores: $($dia.DiagramLinks.Count)"

# =========================================================================
# 1.3.1 Disenar Casos de Uso: un diagrama por caso de uso.
# En el MISMO paquete que los elementos (regla 2).
# =========================================================================

# --- CU-10 ---
$dCu10 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-10 Gestionar productos y variantes' @(
    @{ el=$A['admin']; l=40;  t=-80; w=130; h=80 },
    @{ el=$U['cu10'];  l=320; t=-70; w=260; h=85 },
    @{ el=$U['auth'];  l=740; t=-70; w=240; h=85 }
) $null

# --- CU-11 ---
$dCu11 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-11 Gestionar imágenes de producto' @(
    @{ el=$A['admin']; l=40;  t=-80; w=130; h=80 },
    @{ el=$U['cu11'];  l=320; t=-70; w=260; h=85 },
    @{ el=$U['auth'];  l=740; t=-70; w=240; h=85 }
) $null

# --- CU-13 --- dos iniciadores: el Administrador sobre toda la red y el
# Encargado solo sobre su sucursal, que el sistema le impone.
$dCu13 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-13 Registrar ingreso de mercadería' @(
    @{ el=$A['admin'];     l=40;  t=-60;  w=130; h=80 },
    @{ el=$A['encargado']; l=40;  t=-200; w=160; h=80 },
    @{ el=$U['cu13'];      l=320; t=-110; w=260; h=85 },
    @{ el=$U['auth'];      l=740; t=-110; w=240; h=85 }
) $null

# --- CU-14 ---
$dCu14 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-14 Consultar inventario consolidado' @(
    @{ el=$A['admin']; l=40;  t=-80; w=130; h=80 },
    @{ el=$U['cu14'];  l=320; t=-70; w=260; h=85 },
    @{ el=$U['auth'];  l=740; t=-70; w=240; h=85 }
) $null

# --- CU-15 --- se muestra CU-16 porque el ajuste del Encargado llega por ahi.
# Hay que ocultar las relaciones propias de CU-16 que EA dibujaria igual.
$dCu15 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-15 Registrar movimiento de inventario' @(
    @{ el=$A['admin']; l=40;  t=-120; w=130; h=80 },
    @{ el=$U['cu15'];  l=320; t=-110; w=260; h=85 },
    @{ el=$U['auth'];  l=740; t=-40;  w=240; h=85 },
    @{ el=$U['cu16'];  l=740; t=-190; w=260; h=85 }
) @( @($A['admin'], $U['cu16']), @($U['cu16'], $U['auth']) )

# --- CU-16 --- el Encargado es el iniciador; el Administrador entra con
# alcance a toda la red.
$dCu16 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-16 Gestionar disponibilidad de la sucursal' @(
    @{ el=$A['encargado']; l=40;  t=-60;  w=160; h=80 },
    @{ el=$A['admin'];     l=40;  t=-200; w=130; h=80 },
    @{ el=$U['cu16'];      l=320; t=-110; w=260; h=85 },
    @{ el=$U['auth'];      l=740; t=-40;  w=240; h=85 },
    @{ el=$U['cu15'];      l=740; t=-190; w=260; h=85 }
) @( @($A['admin'], $U['cu15']), @($U['cu15'], $U['auth']) )

# --- CU-17 --- sin 'Autenticar usuario': la vitrina es publica.
$dCu17 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-17 Consultar catálogo' @(
    @{ el=$A['cliente']; l=40;  t=-80; w=130; h=80 },
    @{ el=$U['cu17'];    l=320; t=-70; w=260; h=85 },
    @{ el=$U['cu18'];    l=740; t=-70; w=260; h=85 }
) @( ,@($A['cliente'], $U['cu18']) )

# --- CU-18 ---
$dCu18 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-18 Consultar ficha de producto' @(
    @{ el=$A['cliente']; l=40;  t=-120; w=130; h=80 },
    @{ el=$U['cu18'];    l=320; t=-110; w=260; h=85 },
    @{ el=$U['cu17'];    l=740; t=-40;  w=260; h=85 },
    @{ el=$U['cu19'];    l=740; t=-190; w=260; h=85 }
) @( @($A['cliente'], $U['cu17']), @($A['cliente'], $U['cu19']) )

# --- CU-19 --- se muestra CU-22 porque de aca sale la reserva, y esa flecha
# --- CU-22 include CU-19 --- si viene al caso.
$dCu19 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-19 Consultar disponibilidad por sucursal' @(
    @{ el=$A['cliente']; l=40;  t=-120; w=130; h=80 },
    @{ el=$U['cu19'];    l=320; t=-110; w=260; h=85 },
    @{ el=$U['cu18'];    l=740; t=-40;  w=260; h=85 },
    @{ el=$U['cu22'];    l=740; t=-190; w=260; h=85 }
) @( @($A['cliente'], $U['cu18']), @($A['cliente'], $U['cu22']) )

# --- CU-22 ---
$dCu22 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-22 Crear reserva de prendas' @(
    @{ el=$A['cliente']; l=40;  t=-120; w=130; h=80 },
    @{ el=$U['cu22'];    l=320; t=-110; w=260; h=85 },
    @{ el=$U['cu19'];    l=740; t=-40;  w=260; h=85 },
    @{ el=$U['auth'];    l=740; t=-190; w=240; h=85 }
) @( ,@($A['cliente'], $U['cu19']) )

# --- CU-23 ---
$dCu23 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-23 Consultar y cancelar reserva' @(
    @{ el=$A['cliente']; l=40;  t=-80; w=130; h=80 },
    @{ el=$U['cu23'];    l=320; t=-70; w=260; h=85 },
    @{ el=$U['auth'];    l=740; t=-70; w=240; h=85 }
) $null

# --- CU-24 ---
$dCu24 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-24 Atender reserva en sucursal' @(
    @{ el=$A['encargado']; l=40;  t=-60;  w=160; h=80 },
    @{ el=$A['admin'];     l=40;  t=-200; w=130; h=80 },
    @{ el=$U['cu24'];      l=320; t=-110; w=260; h=85 },
    @{ el=$U['auth'];      l=740; t=-110; w=240; h=85 }
) $null

# --- CU-25 --- sin autenticacion: no hay usuario, lo dispara el planificador.
$dCu25 = New-DiagramaDeCasoDeUso $pCiclo2 'CU-25 Expirar reservas vencidas' @(
    @{ el=$A['sistema']; l=40;  t=-80; w=170; h=80 },
    @{ el=$U['cu25'];    l=340; t=-70; w=260; h=85 }
) $null

# --- exportacion -------------------------------------------------------------
$prj = $ea.GetProjectInterface()

$salidas = @(
    @{ d=$dia;   f='1.5-modelo-estructurado-ciclo-2.png';                    n='1.5  ' },
    @{ d=$dCu10; f='1.3.1-cu-10-gestionar-productos-y-variantes.png';        n='CU-10' },
    @{ d=$dCu11; f='1.3.1-cu-11-gestionar-imagenes-de-producto.png';         n='CU-11' },
    @{ d=$dCu13; f='1.3.1-cu-13-registrar-ingreso-de-mercaderia.png';        n='CU-13' },
    @{ d=$dCu14; f='1.3.1-cu-14-consultar-inventario-consolidado.png';       n='CU-14' },
    @{ d=$dCu15; f='1.3.1-cu-15-registrar-movimiento-de-inventario.png';     n='CU-15' },
    @{ d=$dCu16; f='1.3.1-cu-16-gestionar-disponibilidad-de-la-sucursal.png'; n='CU-16' },
    @{ d=$dCu17; f='1.3.1-cu-17-consultar-catalogo.png';                     n='CU-17' },
    @{ d=$dCu18; f='1.3.1-cu-18-consultar-ficha-de-producto.png';            n='CU-18' },
    @{ d=$dCu19; f='1.3.1-cu-19-consultar-disponibilidad-por-sucursal.png';  n='CU-19' },
    @{ d=$dCu22; f='1.3.1-cu-22-crear-reserva-de-prendas.png';               n='CU-22' },
    @{ d=$dCu23; f='1.3.1-cu-23-consultar-y-cancelar-reserva.png';           n='CU-23' },
    @{ d=$dCu24; f='1.3.1-cu-24-atender-reserva-en-sucursal.png';            n='CU-24' },
    @{ d=$dCu25; f='1.3.1-cu-25-expirar-reservas-vencidas.png';              n='CU-25' }
)
foreach ($s in $salidas) {
    $visibles = ($s.d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
    $exp = $prj.PutDiagramImageToFile($s.d.DiagramGUID, $dirPng + $s.f, 1)
    Write-Output ("{0} -> objetos: {1,2} | relaciones visibles: {2,2} | export: {3}" -f $s.n, $s.d.DiagramObjects.Count, $visibles, $exp)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
