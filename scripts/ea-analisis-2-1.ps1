# =========================================================================
# CAP. 2 - 2.1 Analisis de Arquitectura, en Enterprise Architect.
#
#   2.1.1  Identificar Paquetes      un diagrama con los once paquetes
#   2.1.2  Relacionar Paquetes y CU  trazas de cada paquete a sus casos de uso
#   2.1.3  Vista de Paquetes         un diagrama por paquete, con sus casos de
#                                    uso y los actores que intervienen
#
# ADITIVO A PROPOSITO: abre el modelo existente y solo agrega lo que falta.
# No recrea el archivo ni toca los diagramas ya hechos, porque a esta altura
# hay diagramas acomodados a mano y volver a generarlos borraria ese trabajo.
# Se puede ejecutar las veces que haga falta: los elementos y diagramas que ya
# existen se reutilizan.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\FashionStore.eapx'

if (-not (Test-Path $modelo)) { throw "No existe $modelo" }

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------- utilidades ----------------

function Get-OCrearPaqueteModelo($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}

# Busca un elemento por nombre en todo el modelo; si no esta, lo crea.
$indice = @{}
function Registrar-Elementos($pkg) {
    foreach ($e in $pkg.Elements) { $indice["$($e.Type)|$($e.Name)"] = $e }
    foreach ($sp in $pkg.Packages) { Registrar-Elementos $sp }
}

function Get-OCrearElemento($pkg, $nombre, $tipo, $notas) {
    $clave = "$tipo|$nombre"
    if ($indice.ContainsKey($clave)) { return $indice[$clave] }
    $e = $pkg.Elements.AddNew($nombre, $tipo)
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $pkg.Elements.Refresh()
    $indice[$clave] = $e
    return $e
}

function Ensure-Conector($src, $dst, $tipo, $estereotipo) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq $tipo) { return }
    }
    $c = $src.Connectors.AddNew('', $tipo)
    $c.SupplierID = $dst.ElementID
    if ($estereotipo) { $c.Stereotype = $estereotipo }
    [void]$c.Update(); $src.Connectors.Refresh()
}

function Get-Diagrama($pkg, $nombre) {
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

function New-Diagrama($pkg, $nombre, $tipo) {
    $d = $pkg.Diagrams.AddNew($nombre, $tipo); [void]$d.Update(); $pkg.Diagrams.Refresh(); return $d
}

function Ordenar-Z($dia) {
    $i = 1
    foreach ($o in $dia.DiagramObjects) {
        $el = $ea.GetElementByID($o.ElementID)
        if ($el.Type -eq 'Package') { $o.Sequence = 100 } else { $o.Sequence = $i; $i++ }
        [void]$o.Update()
    }
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# ---------------- estructura del modelo ----------------

$root     = $ea.Models.GetAt(0)
$pFashion = Get-OCrearPaqueteModelo $root     'FashionStore'
Registrar-Elementos $pFashion
Write-Output "elementos ya existentes en el modelo: $($indice.Count)"

$pCap1 = Get-OCrearPaqueteModelo $pFashion 'CAP. 1 - Captura de Requisitos'
$pCU   = Get-OCrearPaqueteModelo $pCap1    'Modelo de Casos de Uso'
$pCap2 = Get-OCrearPaqueteModelo $pFashion 'CAP. 2 - Flujo de Trabajo: Analisis'
$p21   = Get-OCrearPaqueteModelo $pCap2    '2.1 Analisis de Arquitectura'
$p213  = Get-OCrearPaqueteModelo $p21      '2.1.3 Vista de Paquetes'

# ---------------- actores ----------------

$defActores = @(
  @{k='cliente';   n='Cliente';                          nt='A1. Consulta el catalogo, reserva, compra y usa el vestidor virtual. Se autorregistra.'},
  @{k='admin';     n='Administrador';                    nt='A2. Acceso completo: usuarios, organizacion, catalogo, inventario, promociones y reportes.'},
  @{k='encargado'; n='Encargado de Sucursal';            nt='A3. Responsable operativo de una sucursal. Su ambito de datos se limita a su tienda.'},
  @{k='cajero';    n='Cajero';                           nt='A4. Opera el punto de venta: caja, ventas presenciales y devoluciones.'},
  @{k='proveedor'; n='Proveedor';                        nt='A5. Abastece prendas. Acceso limitado a sus propios productos.'},
  @{k='sistema';   n='Sistema (procesos automaticos)';   nt='A6. Lo que el sistema ejecuta sin intervencion humana: expiracion de reservas, confirmacion de pago, KPIs y alertas.'},
  @{k='pasarela';  n='Pasarela de Pago';                 nt='A7. Servicio externo que procesa los pagos electronicos en modo de pruebas y notifica por webhook.'},
  @{k='ia';        n='Servicio de Inteligencia Artificial'; nt='A8. Servicio externo que genera recomendaciones, sostiene el asistente y produce los reportes por voz.'},
  @{k='ra';        n='Servicio de Realidad Aumentada';   nt='A9. Componente del dispositivo movil que provee camara y deteccion de pose corporal.'}
)
$A = @{}
foreach ($def in $defActores) { $A[$def.k] = Get-OCrearElemento $pCU $def.n 'Actor' $def.nt }

# ---------------- los 37 casos de uso ----------------

$defCU = @(
  @{k='cu01'; n='CU-01 Registrar cliente'},
  @{k='cu02'; n='CU-02 Iniciar y cerrar sesión'},
  @{k='cu03'; n='CU-03 Gestionar usuarios y roles'},
  @{k='cu04'; n='CU-04 Gestionar perfil del cliente'},
  @{k='cu05'; n='CU-05 Gestionar ciudades y sucursales'},
  @{k='cu06'; n='CU-06 Gestionar empleados'},
  @{k='cu07'; n='CU-07 Gestionar proveedores'},
  @{k='cu08'; n='CU-08 Gestionar categorías, tallas y colores'},
  @{k='cu09'; n='CU-09 Gestionar temporadas y colecciones'},
  @{k='cu10'; n='CU-10 Gestionar productos y variantes'},
  @{k='cu11'; n='CU-11 Gestionar imágenes de producto'},
  @{k='cu12'; n='CU-12 Gestionar promociones'},
  @{k='cu13'; n='CU-13 Registrar ingreso de mercadería'},
  @{k='cu14'; n='CU-14 Consultar inventario consolidado'},
  @{k='cu15'; n='CU-15 Registrar movimiento de inventario'},
  @{k='cu16'; n='CU-16 Gestionar disponibilidad de la sucursal'},
  @{k='cu17'; n='CU-17 Consultar catálogo'},
  @{k='cu18'; n='CU-18 Consultar ficha de producto'},
  @{k='cu19'; n='CU-19 Consultar disponibilidad por sucursal'},
  @{k='cu20'; n='CU-20 Gestionar favoritos'},
  @{k='cu21'; n='CU-21 Utilizar vestidor virtual (RA)'},
  @{k='cu22'; n='CU-22 Crear reserva de prendas'},
  @{k='cu23'; n='CU-23 Consultar y cancelar reserva'},
  @{k='cu24'; n='CU-24 Atender reserva en sucursal'},
  @{k='cu25'; n='CU-25 Expirar reservas vencidas'},
  @{k='cu26'; n='CU-26 Gestionar carrito de compras'},
  @{k='cu27'; n='CU-27 Realizar pedido y pagar en línea'},
  @{k='cu28'; n='CU-28 Confirmar pago del pedido'},
  @{k='cu29'; n='CU-29 Consultar historial de compras'},
  @{k='cu30'; n='CU-30 Abrir y cerrar caja'},
  @{k='cu31'; n='CU-31 Registrar venta presencial'},
  @{k='cu32'; n='CU-32 Registrar devolución'},
  @{k='cu33'; n='CU-33 Recibir recomendaciones de prendas'},
  @{k='cu34'; n='CU-34 Conversar con el asistente virtual'},
  @{k='cu35'; n='CU-35 Generar reporte por comando de voz'},
  @{k='cu36'; n='CU-36 Consultar tablero de indicadores'},
  @{k='cu37'; n='CU-37 Generar reportes de gestión'}
)
$U = @{}
foreach ($def in $defCU) { $U[$def.k] = Get-OCrearElemento $pCU $def.n 'UseCase' $null }
Write-Output "actores: $($A.Count) | casos de uso: $($U.Count)"

# ---------------- los once paquetes de analisis ----------------

$defPaq = @(
  @{k='p1';  n='P1 · Seguridad y Usuarios';               cus=@('cu01','cu02','cu03','cu04');
     nt='Identidad y acceso: registro, autenticacion, emision de tokens y control por roles. Es el mas transversal del sistema y no depende de ningun otro.'},
  @{k='p2';  n='P2 · Organización';                       cus=@('cu05','cu06','cu07');
     nt='Estructura de la empresa: ciudades, sucursales, empleados y proveedores. Aporta la nocion de sucursal, eje sobre el que se particiona todo lo demas.'},
  @{k='p3';  n='P3 · Catálogo';                           cus=@('cu08','cu09','cu10','cu11','cu12');
     nt='Definicion comercial del producto: taxonomia, temporadas, productos, variantes (SKU) y promociones. Define que se vende.'},
  @{k='p4';  n='P4 · Inventario';                         cus=@('cu13','cu14','cu15','cu16');
     nt='Cuanto hay y donde: existencias por variante y sucursal, y registro trazable de todo movimiento. Ninguna cantidad cambia sin generar un movimiento.'},
  @{k='p5';  n='P5 · Catálogo Público y Disponibilidad';  cus=@('cu17','cu18','cu19','cu20');
     nt='Vista de solo lectura para el cliente: busqueda, filtros, ficha de producto, disponibilidad por sucursal y favoritos.'},
  @{k='p6';  n='P6 · Reservas';                           cus=@('cu22','cu23','cu24','cu25');
     nt='Ciclo de vida de la reserva para prueba presencial: creacion, notificacion, atencion, cancelacion y expiracion automatica.'},
  @{k='p7';  n='P7 · Ventas y Punto de Venta';            cus=@('cu26','cu27','cu29','cu30','cu31','cu32');
     nt='La venta en sus dos canales sobre una misma entidad: pedido digital y caja presencial, con comprobantes y devoluciones.'},
  @{k='p8';  n='P8 · Pagos';                              cus=@('cu27','cu28');
     nt='Cobro electronico y presencial. Aisla la integracion con la pasarela externa, de modo que cambiarla no afecte a P7.'},
  @{k='p9';  n='P9 · Vestidor Virtual (RA)';              cus=@('cu21');
     nt='Prueba virtual en la aplicacion movil: camara, deteccion de pose y superposicion de la prenda ajustada al cuerpo.'},
  @{k='p10'; n='P10 · Inteligencia Artificial';           cus=@('cu33','cu34','cu35');
     nt='Recomendador, asistente conversacional y reportes por comando de voz. Es consumidor de datos, nunca fuente de verdad: se puede desactivar sin frenar la operacion.'},
  @{k='p11'; n='P11 · Reportes y Tablero';                cus=@('cu36','cu37');
     nt='KPIs en tiempo real y reportes exportables a PDF y Excel. Solo lectura sobre los paquetes transaccionales.'}
)
$P = @{}
foreach ($def in $defPaq) { $P[$def.k] = Get-OCrearElemento $p21 $def.n 'Package' $def.nt }

# =========================================================================
# 2.1.1  Identificar Paquetes
# =========================================================================
if (Get-Diagrama $p21 '2.1.1 Identificar Paquetes') {
    Write-Output '2.1.1 ya existe, no se toca'
} else {
    $d = New-Diagrama $p21 '2.1.1 Identificar Paquetes' 'Package'
    $col = 0; $fila = 0
    foreach ($def in $defPaq) {
        $l = 40 + $col * 340
        $t = -40 - $fila * 200
        Poner $d $P[$def.k] $l $t 240 70
        # La descripcion corta va como nota visible, ademas de en las notas del
        # propio paquete: en el diagrama impreso las notas del elemento no se ven.
        $nota = $p21.Elements.AddNew('', 'Note')
        $nota.Notes = $def.nt
        [void]$nota.Update()
        Poner $d $nota $l ($t - 80) 240 100
        Ensure-Conector $nota $P[$def.k] 'NoteLink' $null
        $col++; if ($col -ge 3) { $col = 0; $fila++ }
    }
    $d.DiagramObjects.Refresh()
    Write-Output "2.1.1 creado con $($d.DiagramObjects.Count) objetos"
}

# =========================================================================
# 2.1.2  Relacionar Paquetes y Casos de Uso  (trazas)
# =========================================================================
if (Get-Diagrama $p21 '2.1.2 Relacionar Paquetes y Casos de Uso') {
    Write-Output '2.1.2 ya existe, no se toca'
} else {
    $d = New-Diagrama $p21 '2.1.2 Relacionar Paquetes y Casos de Uso' 'Package'
    $t = -40
    foreach ($def in $defPaq) {
        $altoBloque = $def.cus.Count * 90
        # El paquete se centra verticalmente contra su bloque de casos de uso.
        $tPaq = $t - [int](($altoBloque - 70) / 2)
        Poner $d $P[$def.k] 40 $tPaq 260 70
        $tCU = $t
        foreach ($k in $def.cus) {
            Poner $d $U[$k] 420 $tCU 300 70
            Ensure-Conector $P[$def.k] $U[$k] 'Abstraction' 'trace'
            $tCU -= 90
        }
        $t -= ($altoBloque + 40)
    }
    # EA dibuja toda relacion existente entre elementos presentes, asi que aqui
    # se colaban los include y extend entre casos de uso. Este diagrama es solo
    # de trazas: el resto se oculta, sin tocarlas en el modelo.
    $d.DiagramLinks.Refresh()
    $ocultos = 0
    foreach ($lnk in $d.DiagramLinks) {
        $con = $ea.GetConnectorByID($lnk.ConnectorID)
        if ($con.Stereotype -ne 'trace') { $lnk.IsHidden = $true; [void]$lnk.Update(); $ocultos++ }
    }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    $visibles = ($d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
    Write-Output "2.1.2 creado con $($d.DiagramObjects.Count) objetos, $visibles trazas y $ocultos relaciones ajenas ocultas"
}

# =========================================================================
# 2.1.3  Vista de Paquetes: un diagrama por paquete
#
# Un diagrama por paquete y no uno solo, porque un actor participa en varios
# paquetes y en EA un elemento solo puede aparecer una vez por diagrama: en un
# unico lienzo, Cliente tendria que estar dentro de P1, P5, P6, P7, P9 y P10 a
# la vez, y no se puede.
# =========================================================================

# Que actores intervienen en cada caso de uso.
$actoresPorCU = @{
  cu01=@('cliente'); cu02=@('cliente','admin','encargado','cajero','proveedor')
  cu03=@('admin'); cu04=@('cliente'); cu05=@('admin'); cu06=@('admin')
  cu07=@('admin','proveedor'); cu08=@('admin'); cu09=@('admin'); cu10=@('admin')
  cu11=@('admin'); cu12=@('admin'); cu13=@('admin','encargado'); cu14=@('admin')
  cu15=@('admin'); cu16=@('encargado'); cu17=@('cliente'); cu18=@('cliente')
  cu19=@('cliente'); cu20=@('cliente'); cu21=@('cliente','ra'); cu22=@('cliente')
  cu23=@('cliente'); cu24=@('encargado'); cu25=@('sistema'); cu26=@('cliente')
  cu27=@('cliente','pasarela'); cu28=@('sistema','pasarela'); cu29=@('cliente')
  cu30=@('cajero'); cu31=@('cajero'); cu32=@('cajero'); cu33=@('cliente','ia')
  cu34=@('cliente','ia'); cu35=@('admin','ia'); cu36=@('admin')
  cu37=@('admin','encargado')
}

foreach ($def in $defPaq) {
    $nombre = "2.1.3 $($def.n)"
    if (Get-Diagrama $p213 $nombre) { Write-Output "  $nombre ya existe, no se toca"; continue }
    $d = New-Diagrama $p213 $nombre 'UseCase'

    # Actores que intervienen en este paquete, sin repetir.
    $suyos = @()
    # Ojo: la variable del bucle no puede llamarse $a --- PowerShell no distingue
    # mayusculas y pisaria $A, la tabla de actores.
    foreach ($act in $def.cus) { foreach ($nom in $actoresPorCU[$act]) { if ($suyos -notcontains $nom) { $suyos += $nom } } }

    $altoPaq = [Math]::Max($def.cus.Count * 100 + 80, $suyos.Count * 120 + 80)

    # El paquete como contenedor; los casos de uso van dentro de sus limites.
    Poner $d $P[$def.k] 300 -40 460 $altoPaq

    $t = -110
    foreach ($k in $def.cus) {
        Poner $d $U[$k] 340 $t 380 70
        $t -= 100
    }
    $ta = -60
    foreach ($nom in $suyos) {
        Poner $d $A[$nom] 40 $ta 120 90
        $ta -= 120
    }
    foreach ($k in $def.cus) {
        foreach ($nom in $actoresPorCU[$k]) { Ensure-Conector $A[$nom] $U[$k] 'Association' $null }
    }
    # La traza paquete -> caso de uso sobra aqui: los casos de uso ya estan
    # dibujados DENTRO del paquete, que es la misma informacion. Se oculta solo
    # en este diagrama. Los include y extend entre casos de uso del mismo
    # paquete si se conservan: ahi si aportan.
    $d.DiagramLinks.Refresh()
    foreach ($lnk in $d.DiagramLinks) {
        $con = $ea.GetConnectorByID($lnk.ConnectorID)
        if ($con.Stereotype -eq 'trace') { $lnk.IsHidden = $true; [void]$lnk.Update() }
    }
    # Orden Z. EA deja la secuencia sin definir (999999) y entonces el paquete,
    # que es un rectangulo relleno, tapa los casos de uso que tiene dentro. Con
    # numero mas bajo el objeto va al frente: el paquete al fondo, el resto
    # adelante.
    Ordenar-Z $d
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    $vis = ($d.DiagramLinks | Where-Object { -not $_.IsHidden }).Count
    Write-Output "  $nombre : $($d.DiagramObjects.Count) objetos, $vis relaciones"
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
