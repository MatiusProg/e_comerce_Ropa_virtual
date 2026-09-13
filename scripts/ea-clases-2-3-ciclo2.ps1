# =========================================================================
# CAP. 2 - 2.3 Analisis de Clases. CICLO 2: los trece diagramas de clases de
# CU-10, CU-11, CU-13 a CU-19 y CU-22 a CU-25.
#
# Aditivo: un diagrama que ya existe no se toca.
# NO EXPORTA IMAGENES. Las exporta Mateo a mano desde EA (pedido del 13/09).
#
# ---- POR QUE ESTAS CLASES SON ELEMENTOS APARTE (decision del 04/09/2026) --
# Las clases de 2.2 y las de 2.3 son elementos DISTINTOS con el mismo nombre,
# en paquetes distintos. EA dibuja el circulo de robustez solo para los
# estereotipos llamados exactamente boundary, control y entity; con cualquier
# otro nombre dibuja la clase como tabla. Como 2.2 necesita el circulo y 2.3
# la tabla con atributos y operaciones, y un mismo elemento no puede verse de
# las dos maneras, estan duplicadas a proposito.
#
# ---- NIVEL DE DETALLE ----------------------------------------------------
#   frontera     - sin atributos; operaciones = el componente del frontend Y
#                  el endpoint del router
#   controlador  - sin atributos; operaciones = las funciones del service
#   entidad      - atributos = LAS COLUMNAS DE LA TABLA con su tipo de la
#                  base; operaciones = las funciones del repository
#
# Los nombres son los REALES del codigo: estan en
# ea-clases-2-3-ciclo2.datos.ps1, generado por gen-ops-2-3.py leyendo los
# modulos con `ast` y las columnas de information_schema. No se inventan.
#
# ---- LA UNION ENTRE CLASES ES SIEMPRE UNA Association --------------------
# Con nombre de rol en mayusculas y cardinalidad en los dos extremos. Nada de
# Dependency, Usage, Aggregation ni Composition: con un solo tipo de linea el
# lector compara los diagramas del capitulo entre si sin interpretar la
# semantica de cada estilo, y no queda abierta la discusion de si algo era
# agregacion o composicion.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'

. (Join-Path $PSScriptRoot 'ea-clases-2-3-ciclo2.datos.ps1')

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------- utilidades ----------------

function Get-OCrearPaqueteModelo($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}

function BuscarDiagrama($p, $n) {
    foreach ($d in $p.Diagrams) { if ($d.Name -eq $n) { return $d } }
    return $null
}

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
$pCap2 = Get-OCrearPaqueteModelo $pRaiz 'CAP. 2 - Flujo de Trabajo: Analisis'
$p22   = Get-OCrearPaqueteModelo $pCap2 '2.2 Analizar Casos de Uso'
$p22c  = Get-OCrearPaqueteModelo $p22   'Clases de Analisis'
$p23   = Get-OCrearPaqueteModelo $pCap2 '2.3 Analisis de Clases'

# PASO PREVIO OBLIGATORIO. Si una pasada anterior dejo en espanol los
# estereotipos de las clases de 2.2, los diagramas de comunicacion perdieron
# el circulo de robustez. Se restauran antes de nada.
$aIngles = @{ 'frontera' = 'boundary'; 'controlador' = 'control'; 'entidad' = 'entity' }
$restaurados = 0
foreach ($e in $p22c.Elements) {
    if ($aIngles.ContainsKey($e.Stereotype)) {
        $e.Stereotype = $aIngles[$e.Stereotype]
        $e.StereotypeEx = $e.Stereotype   # borra la aplicacion del perfil viejo
        [void]$e.Update(); $restaurados++
    }
}
if ($restaurados) { Write-Output "Estereotipos de 2.2 restaurados al ingles: $restaurados" }

# ---------------- clases de 2.3 ----------------

$indice23 = @{}
foreach ($e in $p23.Elements) { $indice23[$e.Name] = $e }

function Get-OCrearClase23($nombre, $estereotipo, $notas) {
    if ($indice23.ContainsKey($nombre)) { return $indice23[$nombre] }
    $e = $p23.Elements.AddNew($nombre, 'Class')
    $e.Stereotype = $estereotipo
    $e.StereotypeEx = $estereotipo
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p23.Elements.Refresh()
    $indice23[$nombre] = $e
    return $e
}

function Set-Atributos($el, $lista) {
    if (-not $lista) { return }
    $ya = @{}
    foreach ($a in $el.Attributes) { $ya[$a.Name] = $true }
    $i = 0
    foreach ($d in $lista) {
        if (-not $ya.ContainsKey($d.n)) {
            $a = $el.Attributes.AddNew($d.n, $d.t)
            $a.Pos = $i
            $a.Visibility = 'Private'
            [void]$a.Update()
        }
        $i++
    }
    $el.Attributes.Refresh()
}

function Set-Operaciones($el, $lista) {
    if (-not $lista) { return }
    $ya = @{}
    foreach ($o in $el.Methods) { $ya[$o.Name] = $true }
    $i = 0
    foreach ($d in $lista) {
        if (-not $ya.ContainsKey($d.n)) {
            $o = $el.Methods.AddNew($d.n, $d.r)
            $o.Pos = $i
            # Las privadas del modulo --- las que empiezan con _ --- se marcan
            # como tales: es lo que distingue un ayudante interno de la
            # operacion que otro paquete puede llamar.
            $o.Visibility = if ($d.n.StartsWith('_')) { 'Private' } else { 'Public' }
            [void]$o.Update()
            foreach ($p in $d.p) {
                if (-not $p.n) { continue }
                $par = $o.Parameters.AddNew($p.n, $p.t)
                [void]$par.Update()
            }
            $o.Parameters.Refresh()
        }
        $i++
    }
    $el.Methods.Refresh()
}

# Regla 5: borrar un diagrama no borra sus conectores. Se deduplica por par +
# tipo + nombre de rol.
function New-Asociacion($src, $dst, $rol, $cardOrigen, $cardDestino) {
    $src.Connectors.Refresh()
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq $rol) { return }
    }
    $c = $src.Connectors.AddNew($rol, 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update()                       # PRIMERO el conector...
    $c.ClientEnd.Cardinality = $cardOrigen  # ...y recien despues los extremos:
    $c.SupplierEnd.Cardinality = $cardDestino
    [void]$c.ClientEnd.Update()             # al reves, EA no guarda la cardinalidad
    [void]$c.SupplierEnd.Update()
    [void]$c.Update()
    $src.Connectors.Refresh()
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

# Alto de la caja a partir de lo que tiene adentro. Si queda corta, EA recorta
# la lista sin avisar.
function Alto($nombre) {
    $na = 0; if ($ATTRS.ContainsKey($nombre)) { $na = $ATTRS[$nombre].Count }
    $no = 0; if ($OPS.ContainsKey($nombre))   { $no = $OPS[$nombre].Count }
    return 70 + ($na * 18) + ($no * 18)
}

# ---------------- descripciones ----------------

$desc = @{
    'PantallaProductos'        = 'Frontera del caso de uso en sus dos extremos: la pantalla de administracion (frontend-web/src/app/features/admin/productos) con ProductosService, y los endpoints de /api/v1/catalogo/productos de app/modules/catalogo/router.py.'
    'PantallaImagenes'         = 'Galeria de un producto. Frontend: features/admin/productos con ProductosService; backend: app/modules/catalogo/imagenes_router.py sobre /api/v1/catalogo/productos/{id}/imagenes.'
    'PantallaInventario'       = 'Frontend: features/admin/inventario con InventarioService; backend: app/modules/inventario/router.py sobre /api/v1/inventario.'
    'PantallaConsolidado'      = 'Frontend: features/admin/consolidado con ConsolidadoService; backend: app/modules/inventario/consolidado_router.py.'
    'PantallaDisponibilidad'   = 'Panel del Encargado. Frontend: features/sucursal/disponibilidad; backend: los endpoints de alertas y umbral de app/modules/inventario/router.py.'
    'PantallaCatalogo'         = 'Vitrina publica. Frontend: features/tienda/catalogo con TiendaService; backend: app/modules/catalogo_publico/router.py sobre /api/v1/tienda. No exige token.'
    'PantallaFichaProducto'    = 'Ficha de la prenda. Frontend: features/tienda/ficha; backend: /api/v1/tienda/productos/{id} y /variantes/{id}/disponibilidad.'
    'PantallaReservas'         = 'Mis reservas del Cliente. Frontend: features/cliente/reservas; movil: mobile/lib/features/reservas; backend: app/modules/reservas/router.py sobre /api/v1/reservas.'
    'PantallaReservasSucursal' = 'Panel del Encargado. Frontend: features/sucursal/reservas; backend: el sucursal_router de app/modules/reservas/router.py sobre /api/v1/sucursal/reservas.'
    'PlanificadorTareas'       = 'Frontera del proceso automatico: el planificador que dispara la expiracion y el mantenimiento_router de app/modules/reservas/router.py, que permite dispararla a mano en la defensa.'

    'GestorProductos'          = 'app/modules/catalogo/service.py. Arma el SKU, valida que la coleccion pertenezca a la temporada y genera una variante por cada combinacion talla x color.'
    'GestorImagenes'           = 'app/modules/catalogo/imagenes_service.py. Verifica el archivo, lo guarda en el volumen y sostiene dos reglas: una sola imagen principal por producto y un solo PNG de vestidor por variante.'
    'GestorInventario'         = 'app/modules/inventario/service.py. El UNICO que escribe existencia y movimiento: ninguna cantidad cambia sin generar su movimiento. Toma el SELECT ... FOR UPDATE que mitiga el riesgo R5, y P6 lo llama para apartar y liberar stock.'
    'GestorConsolidado'        = 'app/modules/inventario/consolidado_service.py. Agrupa la existencia de toda la red por variante y calcula el estado de cada saldo.'
    'GestorVitrina'            = 'app/modules/catalogo_publico/service.py. Solo lee, y solo lo ofrecible. Es el unico control del Ciclo 2 que no exige sesion.'
    'GestorReservas'           = 'app/modules/reservas/service.py. Controla la transaccion --- apartar tres prendas es todo o nada --- y delega en GestorInventario el movimiento de stock, porque la regla de que ninguna cantidad cambia sin movimiento es de P4.'

    'Producto'                 = 'Tabla producto. La prenda como concepto comercial. precio_base es el de referencia: el que se cobra es el de la variante.'
    'VarianteProducto'         = 'Tabla variante_producto. La combinacion talla x color con su SKU. Es la unidad de negocio y lo unico que tiene existencia, reserva y venta (decision D1).'
    'ImagenProducto'           = 'Tabla imagen_producto. es_transparente marca el PNG del vestidor virtual, uno por variante.'
    'Existencia'               = 'Tabla existencia. El saldo de una variante en una sucursal. cantidad_disponible y cantidad_reservada van por separado: reservar TRASLADA unidades entre las dos, no las destruye (decision D3). stock_minimo es el umbral de reposicion que fija CU-16.'
    'MovimientoInventario'     = 'Tabla movimiento_inventario. Historial inmutable. El invariante D4 dice que cantidad_disponible es siempre la suma de las cantidades de sus movimientos, y de ahi sale el signo de cada tipo.'
    'Reserva'                  = 'Tabla reserva. La cabecera: cliente, sucursal, franja horaria y estado. observacion es la nota de CIERRE, la escribe CU-23 al cancelar o CU-24 al atender.'
    'ReservaDetalle'           = 'Tabla reserva_detalle. Una prenda apartada con su cantidad. resultado_prueba lo escribe CU-24 y es nulo mientras la reserva sigue viva.'
}

$estereotipoDe = @{}
foreach ($n in @('PantallaProductos','PantallaImagenes','PantallaInventario','PantallaConsolidado',
                 'PantallaDisponibilidad','PantallaCatalogo','PantallaFichaProducto','PantallaReservas',
                 'PantallaReservasSucursal','PlanificadorTareas')) { $estereotipoDe[$n] = 'frontera' }
foreach ($n in @('GestorProductos','GestorImagenes','GestorInventario','GestorConsolidado',
                 'GestorVitrina','GestorReservas')) { $estereotipoDe[$n] = 'controlador' }
foreach ($n in @('Producto','VarianteProducto','ImagenProducto','Existencia',
                 'MovimientoInventario','Reserva','ReservaDetalle')) { $estereotipoDe[$n] = 'entidad' }

# Se crean todas de una vez, con sus atributos y operaciones.
foreach ($nombre in $estereotipoDe.Keys) {
    $el = Get-OCrearClase23 $nombre $estereotipoDe[$nombre] $desc[$nombre]
    if ($ATTRS.ContainsKey($nombre)) { Set-Atributos   $el $ATTRS[$nombre] }
    if ($OPS.ContainsKey($nombre))   { Set-Operaciones $el $OPS[$nombre] }
}
# GestorAutenticacion ya existe desde el Ciclo 1: se reutiliza tal cual.
$gau = $indice23['GestorAutenticacion']
if (-not $gau) { throw "No se encontro GestorAutenticacion en 2.3 --- correr primero ea-clases-2-3.ps1" }

Write-Output "Clases de 2.3 listas: $($estereotipoDe.Count) nuevas + GestorAutenticacion"

# ---------------- asociaciones ----------------

$C = $indice23
New-Asociacion $C['PantallaProductos']        $C['GestorProductos']   'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaProductos']        $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PantallaImagenes']         $C['GestorImagenes']    'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaImagenes']         $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PantallaInventario']       $C['GestorInventario']  'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaInventario']       $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PantallaConsolidado']      $C['GestorConsolidado'] 'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaConsolidado']      $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PantallaDisponibilidad']   $C['GestorInventario']  'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaDisponibilidad']   $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PantallaCatalogo']         $C['GestorVitrina']     'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaFichaProducto']    $C['GestorVitrina']     'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaReservas']         $C['GestorReservas']    'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaReservas']         $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PantallaReservasSucursal'] $C['GestorReservas']    'DELEGA_EN'     '1' '1'
New-Asociacion $C['PantallaReservasSucursal'] $gau                    'VERIFICA_CON'  '1' '1'
New-Asociacion $C['PlanificadorTareas']       $C['GestorReservas']    'DELEGA_EN'     '1' '1'

New-Asociacion $C['GestorProductos']   $C['Producto']             'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorProductos']   $C['VarianteProducto']     'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorImagenes']    $C['ImagenProducto']       'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorInventario']  $C['Existencia']           'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorInventario']  $C['MovimientoInventario'] 'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorConsolidado'] $C['Existencia']           'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorVitrina']     $C['Producto']             'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorVitrina']     $C['VarianteProducto']     'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorVitrina']     $C['ImagenProducto']       'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorReservas']    $C['Reserva']              'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorReservas']    $C['ReservaDetalle']       'ADMINISTRA' '1' '0..*'

# La costura C1: P5 le PIDE el dato a P4 en vez de consultar su tabla. Y la
# mitigacion del riesgo R5 vive en P4, asi que P6 tambien pasa por el.
New-Asociacion $C['GestorVitrina']  $C['GestorInventario'] 'CONSULTA_A' '1' '1'
New-Asociacion $C['GestorReservas'] $C['GestorInventario'] 'APARTA_CON' '1' '1'

New-Asociacion $C['VarianteProducto'] $C['Producto']         'PERTENECE_A'    '0..*' '1'
New-Asociacion $C['ImagenProducto']   $C['VarianteProducto'] 'ILUSTRA_A'      '0..*' '0..1'
New-Asociacion $C['Existencia']       $C['VarianteProducto'] 'ES_DE'          '0..*' '1'
New-Asociacion $C['MovimientoInventario'] $C['Existencia']   'EXPLICA_A'      '0..*' '1'
New-Asociacion $C['ReservaDetalle']   $C['Reserva']          'PERTENECE_A'    '1..*' '1'
New-Asociacion $C['ReservaDetalle']   $C['VarianteProducto'] 'APARTA'         '0..*' '1'

Write-Output 'Asociaciones listas.'

# ---------------- los trece diagramas ----------------

$casos = @(
  @{ n='2.3 CU-10 Gestionar productos y variantes';         f='PantallaProductos';        c=@('GestorProductos','GestorAutenticacion');                e=@('Producto','VarianteProducto') },
  @{ n='2.3 CU-11 Gestionar imágenes de producto';          f='PantallaImagenes';         c=@('GestorImagenes','GestorAutenticacion');                 e=@('ImagenProducto','VarianteProducto') },
  @{ n='2.3 CU-13 Registrar ingreso de mercadería';         f='PantallaInventario';       c=@('GestorInventario','GestorAutenticacion');               e=@('Existencia','MovimientoInventario') },
  @{ n='2.3 CU-14 Consultar inventario consolidado';        f='PantallaConsolidado';      c=@('GestorConsolidado','GestorAutenticacion');              e=@('Existencia','VarianteProducto') },
  @{ n='2.3 CU-15 Registrar movimiento de inventario';      f='PantallaInventario';       c=@('GestorInventario','GestorAutenticacion');               e=@('Existencia','MovimientoInventario') },
  @{ n='2.3 CU-16 Gestionar disponibilidad de la sucursal'; f='PantallaDisponibilidad';   c=@('GestorInventario','GestorAutenticacion');               e=@('Existencia','MovimientoInventario') },
  @{ n='2.3 CU-17 Consultar catálogo';                      f='PantallaCatalogo';         c=@('GestorVitrina');                                        e=@('Producto','VarianteProducto') },
  @{ n='2.3 CU-18 Consultar ficha de producto';             f='PantallaFichaProducto';    c=@('GestorVitrina');                                        e=@('Producto','VarianteProducto','ImagenProducto') },
  @{ n='2.3 CU-19 Consultar disponibilidad por sucursal';   f='PantallaFichaProducto';    c=@('GestorVitrina','GestorInventario');                     e=@('VarianteProducto','Existencia') },
  @{ n='2.3 CU-22 Crear reserva de prendas';                f='PantallaReservas';         c=@('GestorReservas','GestorInventario','GestorAutenticacion'); e=@('Reserva','ReservaDetalle','Existencia') },
  @{ n='2.3 CU-23 Consultar y cancelar reserva';            f='PantallaReservas';         c=@('GestorReservas','GestorInventario','GestorAutenticacion'); e=@('Reserva','ReservaDetalle','Existencia') },
  @{ n='2.3 CU-24 Atender reserva en sucursal';             f='PantallaReservasSucursal'; c=@('GestorReservas','GestorInventario','GestorAutenticacion'); e=@('Reserva','ReservaDetalle','Existencia') },
  @{ n='2.3 CU-25 Expirar reservas vencidas';               f='PlanificadorTareas';       c=@('GestorReservas','GestorInventario');                    e=@('Reserva','ReservaDetalle','Existencia') }
)

# Tres columnas, como los del Ciclo 1: frontera, controladores, entidades.
$COLS = @(
    @{ x=40;   ancho=430 },
    @{ x=540;  ancho=450 },
    @{ x=1060; ancho=450 }
)

foreach ($caso in $casos) {
    if (BuscarDiagrama $p23 $caso.n) { Write-Output "  $($caso.n) ya existe, no se toca"; continue }

    $d = $p23.Diagrams.AddNew($caso.n, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()

    $grupos = @(@($caso.f), $caso.c, $caso.e)
    for ($k = 0; $k -lt 3; $k++) {
        $t = -40
        foreach ($nombre in $grupos[$k]) {
            $h = Alto $nombre
            Poner $d $C[$nombre] $COLS[$k].x $t $COLS[$k].ancho $h
            $t = $t - $h - 60   # 60 de aire entre cajas de la misma columna
        }
    }

    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    Write-Output ("  {0,-52} {1} clases, {2,2} asociaciones" -f $caso.n, $d.DiagramObjects.Count, $d.DiagramLinks.Count)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
