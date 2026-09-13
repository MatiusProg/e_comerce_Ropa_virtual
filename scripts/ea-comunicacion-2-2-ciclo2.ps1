# =========================================================================
# CAP. 2 - 2.2 Analizar Casos de Uso. CICLO 2: los trece diagramas de
# comunicacion de CU-10, CU-11, CU-13 a CU-19 y CU-22 a CU-25.
#
# Aditivo: un diagrama que ya existe no se toca. Las clases de analisis se
# comparten con el Ciclo 1 --- GestorAutenticacion es la misma --- y viven en
# 'Clases de Analisis', igual que alli.
#
# NO EXPORTA IMAGENES. Las exporta Mateo a mano desde EA (pedido del 13/09).
#
# ---- COMO SE ARMA UN MENSAJE EN EA ---------------------------------------
# 1. El ENLACE entre dos objetos es un conector 'Association', uno solo por
#    par, aunque intercambien diez mensajes. Es lo que dibuja la linea.
# 2. Cada MENSAJE es un conector 'Collaboration' y su nombre es SOLO la
#    operacion: nada de numerarlo a mano.
# 3. El NUMERO lo pone EA a partir de PDATA4, con formato <grupo>.<orden>.
#    Es el "Start New Group" de la interfaz: al cambiar de grupo EA reinicia
#    la numeracion y colorea el grupo distinto. PDATA4 es de solo lectura por
#    la API, asi que se escribe con SQL.
#
# Numerar dentro del nombre --- "1: crear()" --- se ve parecido pero es peor:
# EA no sabe que son grupos, no los colorea y amontona todas las etiquetas en
# el punto medio del enlace.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------- utilidades ----------------

function Get-OCrearPaqueteModelo($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}

$indice = @{}
function Registrar-Elementos($pkg) {
    foreach ($e in $pkg.Elements) { $indice["$($e.Type)|$($e.Stereotype)|$($e.Name)"] = $e }
    foreach ($sp in $pkg.Packages) { Registrar-Elementos $sp }
}

function Get-OCrearClase($pkg, $nombre, $estereotipo, $notas) {
    $clave = "Class|$estereotipo|$nombre"
    if ($indice.ContainsKey($clave)) { return $indice[$clave] }
    $e = $pkg.Elements.AddNew($nombre, 'Class')
    $e.Stereotype = $estereotipo
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $pkg.Elements.Refresh()
    $indice[$clave] = $e
    return $e
}

function Get-Actor($nombre) {
    $clave = "Actor||$nombre"
    if ($indice.ContainsKey($clave)) { return $indice[$clave] }
    throw "No se encontro el actor '$nombre'"
}

function Get-Diagrama($pkg, $nombre) {
    foreach ($d in $pkg.Diagrams) { if ($d.Name -eq $nombre) { return $d } }
    return $null
}

function Poner($dia, $el, $l, $t, $ancho, $alto) {
    $do = $dia.DiagramObjects.AddNew("l=$l;r=$($l+$ancho);t=$t;b=$($t-$alto);", '')
    $do.ElementID = $el.ElementID
    [void]$do.Update()
}

function New-Enlace($src, $dst) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Association') { return }
    }
    $c = $src.Connectors.AddNew('', 'Association')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update(); $src.Connectors.Refresh()
}

function New-Mensaje($src, $dst, $nombre) {
    foreach ($c in $src.Connectors) {
        if ($c.SupplierID -eq $dst.ElementID -and $c.Type -eq 'Collaboration' -and $c.Name -eq $nombre) {
            return $c.ConnectorID
        }
    }
    $c = $src.Connectors.AddNew($nombre, 'Collaboration')
    $c.SupplierID = $dst.ElementID
    [void]$c.Update(); $src.Connectors.Refresh()
    return $c.ConnectorID
}

# ---------------- estructura ----------------

$root  = $ea.Models.GetAt(0)
$pRaiz = Get-OCrearPaqueteModelo $root 'Violet Boutique'
Registrar-Elementos $pRaiz

$pCap2 = Get-OCrearPaqueteModelo $pRaiz 'CAP. 2 - Flujo de Trabajo: Analisis'
$p22   = Get-OCrearPaqueteModelo $pCap2    '2.2 Analizar Casos de Uso'
$pClas = Get-OCrearPaqueteModelo $p22      'Clases de Analisis'

# Descripciones de las clases nuevas del Ciclo 2. Las del Ciclo 1 ya estan y
# Get-OCrearClase las encuentra por nombre: no se vuelven a crear.
$desc = @{
    # --- frontera ---
    'PantallaProductos'         = 'Listado y formulario de productos y sus variantes, area del Administrador.'
    'PantallaImagenes'          = 'Galeria de un producto: carga, orden, principal y marcado para el vestidor virtual.'
    'PantallaInventario'        = 'Existencias de la red, remito de ingreso y registro de ajustes y traslados.'
    'PantallaConsolidado'       = 'Inventario consolidado de toda la red, agrupado por variante y por sucursal.'
    'PantallaDisponibilidad'    = 'Panel del Encargado: alertas de stock bajo y umbral de reposicion de su sucursal.'
    'PantallaCatalogo'          = 'Vitrina publica: busqueda, filtros, orden y paginacion. No exige sesion.'
    'PantallaFichaProducto'     = 'Ficha de una prenda: galeria, seleccion de talla y color, y disponibilidad por sucursal.'
    'PantallaReservas'          = 'Mis reservas del Cliente, en la web y en la app movil: alta, consulta y cancelacion.'
    'PantallaReservasSucursal'  = 'Panel del Encargado con las reservas dirigidas a su local, para prepararlas y cerrarlas.'
    'PlanificadorTareas'        = 'Frontera del proceso automatico: el planificador que dispara la expiracion, y el endpoint de mantenimiento que permite dispararla a mano en la defensa.'
    # --- control ---
    'GestorProductos'           = 'Coordina CU-10: valida los maestros, arma el SKU y genera las variantes talla x color.'
    'GestorImagenes'            = 'Coordina CU-11: verifica el archivo, lo guarda en el volumen y mantiene una sola principal por producto y un solo PNG de vestidor por variante.'
    'GestorInventario'          = 'Coordina CU-13, CU-15 y CU-16, y es el unico que escribe existencia y movimiento: ninguna cantidad cambia sin su movimiento. P6 lo llama para apartar y liberar stock.'
    'GestorConsolidado'         = 'Coordina CU-14: agrupa la existencia de toda la red por variante y calcula el estado de cada saldo.'
    'GestorVitrina'             = 'Coordina CU-17, CU-18 y CU-19: solo lee, y solo lo ofrecible. Es el unico control del Ciclo 2 que no exige sesion.'
    'GestorReservas'            = 'Coordina CU-22 a CU-25. Controla la transaccion --- apartar tres prendas es todo o nada --- y delega en GestorInventario el movimiento de stock.'
    # --- entidad ---
    'Producto'                  = 'Tabla producto. La prenda como concepto comercial; el precio_base es el de referencia, no el que se cobra.'
    'VarianteProducto'          = 'Tabla variante_producto. La combinacion talla x color con su SKU: es la unidad de negocio, y lo que tiene existencia, reserva y venta.'
    'ImagenProducto'            = 'Tabla imagen_producto. es_transparente marca el PNG del vestidor virtual, uno por variante.'
    'Existencia'                = 'Tabla existencia. El saldo de una variante en una sucursal: disponible y reservada por separado, mas el umbral de reposicion.'
    'MovimientoInventario'      = 'Tabla movimiento_inventario. Historial inmutable; cantidad_disponible es siempre la suma de sus movimientos.'
    'Reserva'                   = 'Tabla reserva. La cabecera: cliente, sucursal, franja horaria y estado.'
    'ReservaDetalle'            = 'Tabla reserva_detalle. Una prenda apartada, con su cantidad y el resultado de la prueba que escribe CU-24.'
}

# ---------------- los trece diagramas ----------------
#
# 'g' es el grupo del mensaje; el orden dentro del grupo lo da el orden de
# declaracion. Los actores se referencian con prefijo "A:" porque el actor
# Cliente y la entidad Cliente son elementos distintos con el mismo nombre.

$casos = @(

  @{ n='2.2 CU-10 Gestionar productos y variantes'
     actores=@('Administrador'); boundary='PantallaProductos'
     controles=@('GestorProductos','GestorAutenticacion')
     entidades=@('Producto','VarianteProducto')
     grupos='Grupo 1: alta de producto y generacion de sus variantes (pasos 3 a 7).   Grupo 2: flujo alternativo 7a, variante suelta con precio propio.   Grupo 3: flujos alternativos 3b y 7c, desactivacion.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaProductos';m='registrarProducto(datos)'},
       @{g=1;d='PantallaProductos';a='GestorProductos';m='crear_producto(datos)'},
       @{g=1;d='GestorProductos';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorProductos';a='GestorProductos';m='_validar_maestros(datos)'},
       @{g=1;d='GestorProductos';a='Producto';m='existe_codigo(codigo)'},
       @{g=1;d='GestorProductos';a='Producto';m='agregar_producto(datos)'},
       @{g=1;d='A:Administrador';a='PantallaProductos';m='generarVariantes(tallas, colores)'},
       @{g=1;d='PantallaProductos';a='GestorProductos';m='generar_variantes(producto_id, tallas, colores)'},
       @{g=1;d='GestorProductos';a='VarianteProducto';m='combinaciones_existentes(producto_id)'},
       @{g=1;d='GestorProductos';a='GestorProductos';m='armar_sku(producto, talla, color)'},
       @{g=1;d='GestorProductos';a='VarianteProducto';m='agregar_variante(datos)'},
       @{g=1;d='GestorProductos';a='PantallaProductos';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaProductos';m='crearVariante(datos)'},
       @{g=2;d='GestorProductos';a='GestorProductos';m='_precio_de(producto, precio)'},
       @{g=3;d='A:Administrador';a='PantallaProductos';m='cambiarEstado(id, activo)'},
       @{g=3;d='GestorProductos';a='Producto';m='cambiar_estado_producto(id, activo)'},
       @{g=3;d='GestorProductos';a='VarianteProducto';m='desactivar_variantes_del_producto(id)'},
       @{g=4;d='GestorProductos';a='PantallaProductos';m='codigoDuplicado()'},
       @{g=4;d='GestorProductos';a='PantallaProductos';m='coleccionAjenaALaTemporada()'}
     )},

  @{ n='2.2 CU-11 Gestionar imágenes de producto'
     actores=@('Administrador'); boundary='PantallaImagenes'
     controles=@('GestorImagenes','GestorAutenticacion')
     entidades=@('ImagenProducto','VarianteProducto')
     grupos='Grupo 1: carga de una imagen (pasos 3 y 4).   Grupo 2: flujos alternativos 3a y 3b, asociar a variante y cambiar la principal.   Grupo 3: flujo alternativo 3c, marcado para el vestidor virtual.   Grupo 4: flujo alternativo 3e, eliminacion.   Grupo 5: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaImagenes';m='subirImagen(producto_id, archivo)'},
       @{g=1;d='PantallaImagenes';a='GestorImagenes';m='subir(producto_id, archivo)'},
       @{g=1;d='GestorImagenes';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorImagenes';a='GestorImagenes';m='_asegurar_producto(producto_id)'},
       @{g=1;d='GestorImagenes';a='ImagenProducto';m='siguiente_orden(producto_id)'},
       @{g=1;d='GestorImagenes';a='ImagenProducto';m='agregar(datos)'},
       @{g=1;d='GestorImagenes';a='PantallaImagenes';m='confirmar()'},
       @{g=2;d='A:Administrador';a='PantallaImagenes';m='marcarPrincipal(id)'},
       @{g=2;d='GestorImagenes';a='VarianteProducto';m='variante_de_producto(producto_id, variante_id)'},
       @{g=2;d='GestorImagenes';a='ImagenProducto';m='principal_de(producto_id)'},
       @{g=2;d='GestorImagenes';a='ImagenProducto';m='marcar_principal(id)'},
       @{g=3;d='A:Administrador';a='PantallaImagenes';m='marcarTransparente(id)'},
       @{g=3;d='GestorImagenes';a='GestorImagenes';m='_archivo_tiene_transparencia(ruta)'},
       @{g=3;d='GestorImagenes';a='ImagenProducto';m='transparente_de_variante(variante_id)'},
       @{g=4;d='A:Administrador';a='PantallaImagenes';m='eliminarImagen(id)'},
       @{g=4;d='GestorImagenes';a='ImagenProducto';m='eliminar(imagen)'},
       @{g=5;d='GestorImagenes';a='PantallaImagenes';m='formatoNoAdmitido()'},
       @{g=5;d='GestorImagenes';a='PantallaImagenes';m='elPngNoTieneTransparencia()'}
     )},

  @{ n='2.2 CU-13 Registrar ingreso de mercadería'
     actores=@('Administrador','Encargado de Sucursal'); boundary='PantallaInventario'
     controles=@('GestorInventario','GestorAutenticacion')
     entidades=@('Existencia','MovimientoInventario')
     grupos='Grupo 1: remito completo, en una sola transaccion (pasos 5 a 7).   Grupo 2: flujo alternativo 7a, primera vez que esa variante llega al local.   Grupo 3: flujo alternativo 2a, consulta del historial.   Grupo 4: excepciones.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaInventario';m='registrarIngreso(remito)'},
       @{g=1;d='A:Encargado de Sucursal';a='PantallaInventario';m='registrarIngreso(remito)'},
       @{g=1;d='PantallaInventario';a='GestorInventario';m='registrar_ingreso(datos)'},
       @{g=1;d='GestorInventario';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR", "ENCARGADO")'},
       @{g=1;d='GestorInventario';a='GestorInventario';m='_sucursal_activa(sucursal_id)'},
       @{g=1;d='GestorInventario';a='GestorInventario';m='_variantes_validas(lineas)'},
       @{g=1;d='GestorInventario';a='Existencia';m='obtener_existencia(variante_id, sucursal_id)'},
       @{g=1;d='GestorInventario';a='GestorInventario';m='_aplicar_movimiento(existencia, INGRESO, cantidad)'},
       @{g=1;d='GestorInventario';a='MovimientoInventario';m='agregar_movimiento(datos)'},
       @{g=1;d='GestorInventario';a='PantallaInventario';m='comprobante(saldos)'},
       @{g=2;d='GestorInventario';a='GestorInventario';m='_existencia_o_crearla(variante_id, sucursal_id)'},
       @{g=2;d='GestorInventario';a='Existencia';m='agregar_existencia(variante_id, sucursal_id)'},
       @{g=3;d='A:Administrador';a='PantallaInventario';m='detalleDeIngreso(referencia)'},
       @{g=3;d='GestorInventario';a='MovimientoInventario';m='lineas_de_ingreso(referencia)'},
       @{g=4;d='GestorInventario';a='PantallaInventario';m='sucursalInactiva()'},
       @{g=4;d='GestorInventario';a='PantallaInventario';m='varianteInexistenteODesactivada()'}
     )},

  @{ n='2.2 CU-14 Consultar inventario consolidado'
     actores=@('Administrador'); boundary='PantallaConsolidado'
     controles=@('GestorConsolidado','GestorAutenticacion')
     entidades=@('Existencia','VarianteProducto')
     grupos='Grupo 1: consulta consolidada de toda la red (pasos 1 a 3).   Grupo 2: filtros y orden.   Grupo 3: sin resultados.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaConsolidado';m='consultar(filtros)'},
       @{g=1;d='PantallaConsolidado';a='GestorConsolidado';m='consultar(filtros)'},
       @{g=1;d='GestorConsolidado';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorConsolidado';a='Existencia';m='inventario_consolidado(filtros)'},
       @{g=1;d='GestorConsolidado';a='VarianteProducto';m='listar_variantes(ids)'},
       @{g=1;d='GestorConsolidado';a='GestorConsolidado';m='_agrupar(filas)'},
       @{g=1;d='GestorConsolidado';a='GestorConsolidado';m='_estado(disponible, minimo)'},
       @{g=1;d='GestorConsolidado';a='PantallaConsolidado';m='mostrarConsolidado(resultado)'},
       @{g=2;d='A:Administrador';a='PantallaConsolidado';m='filtrar(criterios)'},
       @{g=2;d='GestorConsolidado';a='GestorConsolidado';m='_ordenar(items, orden)'},
       @{g=3;d='GestorConsolidado';a='PantallaConsolidado';m='sinResultados()'}
     )},

  @{ n='2.2 CU-15 Registrar movimiento de inventario'
     actores=@('Administrador'); boundary='PantallaInventario'
     controles=@('GestorInventario','GestorAutenticacion')
     entidades=@('Existencia','MovimientoInventario')
     grupos='Grupo 1: ajuste por conteo fisico.   Grupo 2: traslado entre sucursales, que son dos movimientos en una transaccion.   Grupo 3: consulta del historial.   Grupo 4: excepciones.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaInventario';m='registrarAjuste(datos)'},
       @{g=1;d='PantallaInventario';a='GestorInventario';m='registrar_ajuste(datos)'},
       @{g=1;d='GestorInventario';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR", "ENCARGADO")'},
       @{g=1;d='GestorInventario';a='Existencia';m='obtener_existencia_por_id(existencia_id)'},
       @{g=1;d='GestorInventario';a='GestorInventario';m='_aplicar_movimiento(existencia, tipo, cantidad)'},
       @{g=1;d='GestorInventario';a='MovimientoInventario';m='agregar_movimiento(datos)'},
       @{g=1;d='GestorInventario';a='PantallaInventario';m='saldoActualizado(existencia)'},
       @{g=2;d='A:Administrador';a='PantallaInventario';m='registrarTransferencia(datos)'},
       @{g=2;d='PantallaInventario';a='GestorInventario';m='registrar_transferencia(datos)'},
       @{g=2;d='GestorInventario';a='MovimientoInventario';m='agregar_movimiento(TRASLADO_SALIDA)'},
       @{g=2;d='GestorInventario';a='MovimientoInventario';m='agregar_movimiento(TRASLADO_ENTRADA)'},
       @{g=3;d='A:Administrador';a='PantallaInventario';m='listarMovimientos(filtros)'},
       @{g=3;d='GestorInventario';a='MovimientoInventario';m='listar_movimientos(filtros)'},
       @{g=4;d='GestorInventario';a='PantallaInventario';m='saldoNegativo()'},
       @{g=4;d='GestorInventario';a='PantallaInventario';m='motivoObligatorio()'}
     )},

  @{ n='2.2 CU-16 Gestionar disponibilidad de la sucursal'
     actores=@('Encargado de Sucursal'); boundary='PantallaDisponibilidad'
     controles=@('GestorInventario','GestorAutenticacion')
     entidades=@('Existencia','MovimientoInventario')
     grupos='Grupo 1: fijar el punto de reposicion de una prenda (pasos 3 a 5).   Grupo 2: panel de alertas de stock bajo.   Grupo 3: flujo alternativo 3a, ajuste por conteo fisico acotado a su local --- es la operacion de CU-15.   Grupo 4: excepciones.'
     msj=@(
       @{g=1;d='A:Encargado de Sucursal';a='PantallaDisponibilidad';m='fijarStockMinimo(existencia_id, umbral)'},
       @{g=1;d='PantallaDisponibilidad';a='GestorInventario';m='fijar_stock_minimo(existencia_id, minimo)'},
       @{g=1;d='GestorInventario';a='GestorAutenticacion';m='autorizar("ENCARGADO")'},
       @{g=1;d='GestorInventario';a='Existencia';m='obtener_existencia_por_id(existencia_id)'},
       @{g=1;d='GestorInventario';a='Existencia';m='fijar_minimo(existencia, minimo)'},
       @{g=1;d='GestorInventario';a='PantallaDisponibilidad';m='confirmarConAviso(enAlerta)'},
       @{g=2;d='A:Encargado de Sucursal';a='PantallaDisponibilidad';m='listarAlertas()'},
       @{g=2;d='PantallaDisponibilidad';a='GestorInventario';m='alertas_de_stock(sucursal_id)'},
       @{g=2;d='GestorInventario';a='Existencia';m='listar_alertas(sucursal_id)'},
       @{g=3;d='A:Encargado de Sucursal';a='PantallaDisponibilidad';m='registrarAjuste(datos)'},
       @{g=3;d='GestorInventario';a='MovimientoInventario';m='agregar_movimiento(AJUSTE)'},
       @{g=4;d='GestorInventario';a='PantallaDisponibilidad';m='umbralNegativo()'},
       @{g=4;d='GestorInventario';a='PantallaDisponibilidad';m='existenciaDeOtraSucursal()'}
     )},

  @{ n='2.2 CU-17 Consultar catálogo'
     actores=@('Cliente'); boundary='PantallaCatalogo'
     controles=@('GestorVitrina')
     entidades=@('Producto','VarianteProducto')
     grupos='Grupo 1: consulta de la vitrina (pasos 1 y 2). NO pasa por GestorAutenticacion: el catalogo es publico.   Grupo 2: pasos 3 y 4, busqueda, filtros y orden.   Grupo 3: flujo alternativo 4a, sin resultados.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaCatalogo';m='abrirCatalogo()'},
       @{g=1;d='PantallaCatalogo';a='GestorVitrina';m='listar_productos(consulta)'},
       @{g=1;d='GestorVitrina';a='Producto';m='listar_productos(filtros)'},
       @{g=1;d='GestorVitrina';a='Producto';m='imagen_principal(ids)'},
       @{g=1;d='GestorVitrina';a='VarianteProducto';m='rango_de_precios(ids)'},
       @{g=1;d='GestorVitrina';a='VarianteProducto';m='colores_por_producto(ids)'},
       @{g=1;d='GestorVitrina';a='PantallaCatalogo';m='mostrarVitrina(pagina)'},
       @{g=2;d='A:Cliente';a='PantallaCatalogo';m='buscarYFiltrar(criterios)'},
       @{g=2;d='GestorVitrina';a='Producto';m='ids_de_categoria_y_descendientes(categoria_id)'},
       @{g=2;d='GestorVitrina';a='Producto';m='contar_productos(filtros)'},
       @{g=3;d='GestorVitrina';a='PantallaCatalogo';m='sinResultadosConFiltros()'},
       @{g=4;d='GestorVitrina';a='PantallaCatalogo';m='ordenNoReconocido()'},
       @{g=4;d='GestorVitrina';a='PantallaCatalogo';m='paginaDemasiadoGrande()'}
     )},

  @{ n='2.2 CU-18 Consultar ficha de producto'
     actores=@('Cliente'); boundary='PantallaFichaProducto'
     controles=@('GestorVitrina')
     entidades=@('Producto','VarianteProducto','ImagenProducto')
     grupos='Grupo 1: apertura de la ficha (pasos 1 y 2).   Grupo 2: pasos 3 a 6, seleccion de talla y color hasta fijar la variante.   Grupo 3: flujos alternativos 6a y 6b, foto propia de la variante y acceso al vestidor virtual.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaFichaProducto';m='abrirFicha(producto_id)'},
       @{g=1;d='PantallaFichaProducto';a='GestorVitrina';m='obtener_ficha(producto_id)'},
       @{g=1;d='GestorVitrina';a='Producto';m='obtener_producto(producto_id)'},
       @{g=1;d='GestorVitrina';a='ImagenProducto';m='imagenes_de_producto(producto_id)'},
       @{g=1;d='GestorVitrina';a='VarianteProducto';m='variante_ofrecible(producto_id)'},
       @{g=1;d='GestorVitrina';a='GestorVitrina';m='_opciones(variantes)'},
       @{g=1;d='GestorVitrina';a='PantallaFichaProducto';m='mostrarFicha(ficha)'},
       @{g=2;d='A:Cliente';a='PantallaFichaProducto';m='elegirTalla(talla_id)'},
       @{g=2;d='PantallaFichaProducto';a='PantallaFichaProducto';m='coloresDeTalla(talla_id)'},
       @{g=2;d='A:Cliente';a='PantallaFichaProducto';m='elegirColor(color_id)'},
       @{g=2;d='PantallaFichaProducto';a='PantallaFichaProducto';m='varianteDe(talla_id, color_id)'},
       @{g=3;d='GestorVitrina';a='ImagenProducto';m='rutas_de_vestidor(producto_id)'},
       @{g=3;d='PantallaFichaProducto';a='PantallaFichaProducto';m='habilitarVestidorVirtual()'},
       @{g=4;d='GestorVitrina';a='PantallaFichaProducto';m='prendaYaNoDisponible()'},
       @{g=4;d='GestorVitrina';a='PantallaFichaProducto';m='identificadorInvalido()'}
     )},

  @{ n='2.2 CU-19 Consultar disponibilidad por sucursal'
     actores=@('Cliente'); boundary='PantallaFichaProducto'
     controles=@('GestorVitrina','GestorInventario')
     entidades=@('VarianteProducto','Existencia')
     grupos='Grupo 1: consulta de disponibilidad al quedar fijada la variante (pasos 1 y 2). Es la costura C1: P5 pide el dato a P4, no consulta la tabla ajena.   Grupo 2: flujo alternativo 1a, cambio de variante.   Grupo 3: flujo alternativo 2a, sin unidades en ninguna sucursal.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaFichaProducto';m='verDisponibilidad(variante_id)'},
       @{g=1;d='PantallaFichaProducto';a='GestorVitrina';m='disponibilidad_de_variante(variante_id)'},
       @{g=1;d='GestorVitrina';a='VarianteProducto';m='variante_ofrecible(variante_id)'},
       @{g=1;d='GestorVitrina';a='GestorInventario';m='disponibilidad_por_sucursal(variante_id)'},
       @{g=1;d='GestorInventario';a='Existencia';m='disponibilidad_por_sucursal(variante_id)'},
       @{g=1;d='GestorVitrina';a='PantallaFichaProducto';m='mostrarSucursales(disponibilidad)'},
       @{g=2;d='A:Cliente';a='PantallaFichaProducto';m='cambiarVariante(variante_id)'},
       @{g=3;d='GestorVitrina';a='PantallaFichaProducto';m='sinStockPorAhora()'},
       @{g=4;d='GestorVitrina';a='PantallaFichaProducto';m='varianteYaNoDisponible()'},
       @{g=4;d='GestorVitrina';a='PantallaFichaProducto';m='servicioNoDisponible()'}
     )},

  @{ n='2.2 CU-22 Crear reserva de prendas'
     actores=@('Cliente'); boundary='PantallaReservas'
     controles=@('GestorReservas','GestorInventario','GestorAutenticacion')
     entidades=@('Reserva','ReservaDetalle','Existencia')
     grupos='Grupo 1: creacion de la reserva (pasos 5 a 7). El orden importa: primero todo lo que se rechaza SIN tocar ninguna fila, y recien al final el apartado, que es lo unico que toma bloqueos.   Grupo 2: excepciones de franja E3, E4, E5 y E8.   Grupo 3: excepcion E6, sin probadores libres.   Grupo 4: excepcion E9 y riesgo R5, sin stock suficiente.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaReservas';m='confirmarReserva(datos)'},
       @{g=1;d='PantallaReservas';a='GestorReservas';m='crear_reserva(datos)'},
       @{g=1;d='GestorReservas';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorReservas';a='GestorReservas';m='obtener_cliente_de_usuario(usuario_id)'},
       @{g=1;d='GestorReservas';a='GestorReservas';m='_validar_franja(sucursal, inicio, fin)'},
       @{g=1;d='GestorReservas';a='Reserva';m='contar_reservas_solapadas(sucursal_id, inicio, fin)'},
       @{g=1;d='GestorReservas';a='GestorInventario';m='apartar_para_reserva(variante_id, sucursal_id, cantidad)'},
       @{g=1;d='GestorInventario';a='Existencia';m='obtener_existencia(variante_id, sucursal_id)'},
       @{g=1;d='GestorInventario';a='Existencia';m='trasladar_a_reservada(existencia, cantidad)'},
       @{g=1;d='GestorReservas';a='Reserva';m='agregar_reserva(datos)'},
       @{g=1;d='GestorReservas';a='ReservaDetalle';m='agregar_detalle(reserva_id, variante_id, cantidad)'},
       @{g=1;d='GestorReservas';a='PantallaReservas';m='reservaConfirmada(reserva)'},
       @{g=2;d='GestorReservas';a='PantallaReservas';m='franjaInvalidaOFueraDeHorario()'},
       @{g=3;d='GestorReservas';a='PantallaReservas';m='sinProbadoresLibres(capacidad)'},
       @{g=4;d='GestorInventario';a='PantallaReservas';m='stockInsuficiente(disponible, solicitado)'}
     )},

  @{ n='2.2 CU-23 Consultar y cancelar reserva'
     actores=@('Cliente'); boundary='PantallaReservas'
     controles=@('GestorReservas','GestorInventario','GestorAutenticacion')
     entidades=@('Reserva','ReservaDetalle','Existencia')
     grupos='Grupo 1: consulta de mis reservas (pasos 1 a 3).   Grupo 2: cancelacion (pasos 4 y 5). El estado se comprueba DESPUES de tomar el bloqueo, no antes.   Grupo 3: flujos alternativos 2a y 2b, filtros.   Grupo 4: excepcion E10 y reserva ajena.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaReservas';m='abrirMisReservas()'},
       @{g=1;d='PantallaReservas';a='GestorReservas';m='listar_mis_reservas(usuario_id, filtros)'},
       @{g=1;d='GestorReservas';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorReservas';a='Reserva';m='listar_reservas(cliente_id, filtros)'},
       @{g=1;d='GestorReservas';a='ReservaDetalle';m='listar_detalles(reserva_id)'},
       @{g=1;d='GestorReservas';a='PantallaReservas';m='mostrarReservas(pagina)'},
       @{g=2;d='A:Cliente';a='PantallaReservas';m='cancelarReserva(id, motivo)'},
       @{g=2;d='PantallaReservas';a='GestorReservas';m='cancelar_reserva(reserva_id, datos)'},
       @{g=2;d='GestorReservas';a='Reserva';m='obtener_reserva_entidad(reserva_id, bloquear)'},
       @{g=2;d='GestorReservas';a='GestorInventario';m='liberar_de_reserva(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorInventario';a='Existencia';m='devolver_a_disponible(existencia, cantidad)'},
       @{g=2;d='GestorReservas';a='Reserva';m='marcar_cancelada(reserva, motivo)'},
       @{g=2;d='GestorReservas';a='PantallaReservas';m='reservaCancelada(reserva)'},
       @{g=3;d='A:Cliente';a='PantallaReservas';m='filtrarPorEstado(estado, vivas)'},
       @{g=4;d='GestorReservas';a='PantallaReservas';m='laReservaYaNoEstaViva(estado)'},
       @{g=4;d='GestorReservas';a='PantallaReservas';m='noEncontramosEsaReserva()'}
     )},

  @{ n='2.2 CU-24 Atender reserva en sucursal'
     actores=@('Encargado de Sucursal'); boundary='PantallaReservasSucursal'
     controles=@('GestorReservas','GestorInventario','GestorAutenticacion')
     entidades=@('Reserva','ReservaDetalle','Existencia')
     grupos='Grupo 1: agenda del local y preparacion (pasos 1 a 3).   Grupo 2: cierre con el resultado de cada prenda (pasos 5 a 7). Por cada prenda que el cliente se lleva se escriben DOS movimientos: una LIBERACION que la devuelve del apartado y una VENTA que la descuenta.   Grupo 3: flujo alternativo 3a, atender sin preparar.   Grupo 4: excepciones E10 y E11.'
     msj=@(
       @{g=1;d='A:Encargado de Sucursal';a='PantallaReservasSucursal';m='abrirPanelDeReservas()'},
       @{g=1;d='PantallaReservasSucursal';a='GestorReservas';m='listar_reservas_de_sucursal(sucursal_id, filtros)'},
       @{g=1;d='GestorReservas';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR", "ENCARGADO")'},
       @{g=1;d='GestorReservas';a='Reserva';m='listar_reservas(filtros)'},
       @{g=1;d='A:Encargado de Sucursal';a='PantallaReservasSucursal';m='prepararReserva(id)'},
       @{g=1;d='GestorReservas';a='Reserva';m='marcar_preparada(reserva)'},
       @{g=2;d='A:Encargado de Sucursal';a='PantallaReservasSucursal';m='atenderReserva(id, resultados)'},
       @{g=2;d='PantallaReservasSucursal';a='GestorReservas';m='atender_reserva(reserva_id, datos)'},
       @{g=2;d='GestorReservas';a='Reserva';m='obtener_reserva_entidad(reserva_id, bloquear)'},
       @{g=2;d='GestorReservas';a='ReservaDetalle';m='detalles_de(reserva_id)'},
       @{g=2;d='GestorReservas';a='GestorInventario';m='liberar_de_reserva(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorReservas';a='GestorInventario';m='descontar_por_venta(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorInventario';a='Existencia';m='obtener_existencia(variante_id, sucursal_id)'},
       @{g=2;d='GestorReservas';a='ReservaDetalle';m='fijar_resultado(detalle, resultado)'},
       @{g=2;d='GestorReservas';a='PantallaReservasSucursal';m='reservaAtendida(reserva)'},
       @{g=3;d='GestorReservas';a='GestorReservas';m='_reserva_de_la_sucursal(reserva, sucursal_id)'},
       @{g=4;d='GestorReservas';a='PantallaReservasSucursal';m='laReservaYaNoSePuedeAtender(estado)'},
       @{g=4;d='GestorReservas';a='PantallaReservasSucursal';m='faltaElResultadoDeAlgunaPrenda(detalles)'}
     )},

  @{ n='2.2 CU-25 Expirar reservas vencidas'
     actores=@('Sistema (procesos automáticos)'); boundary='PlanificadorTareas'
     controles=@('GestorReservas','GestorInventario')
     entidades=@('Reserva','ReservaDetalle','Existencia')
     grupos='Grupo 1: corrida de la tarea (pasos 1 a 5). No hay autorizacion porque no hay usuario: el movimiento de LIBERACION queda sin usuario_id, y eso es lo que distingue una expiracion de una cancelacion en el historial.   Grupo 2: flujo alternativo 1a, disparo manual desde el endpoint de mantenimiento.   Grupo 3: flujos alternativos 3a y 3b, nada que expirar y reserva tomada por otra transaccion.'
     msj=@(
       @{g=1;d='A:Sistema (procesos automáticos)';a='PlanificadorTareas';m='dispararTarea()'},
       @{g=1;d='PlanificadorTareas';a='GestorReservas';m='expirar_reservas_vencidas(tope)'},
       @{g=1;d='GestorReservas';a='GestorReservas';m='_ahora()'},
       @{g=1;d='GestorReservas';a='Reserva';m='listar_vencidas(corte, tope)'},
       @{g=1;d='GestorReservas';a='ReservaDetalle';m='detalles_de(reserva_id)'},
       @{g=1;d='GestorReservas';a='GestorInventario';m='liberar_de_reserva(variante_id, sucursal_id, cantidad)'},
       @{g=1;d='GestorInventario';a='Existencia';m='devolver_a_disponible(existencia, cantidad)'},
       @{g=1;d='GestorReservas';a='Reserva';m='marcar_expirada(reserva)'},
       @{g=1;d='GestorReservas';a='PlanificadorTareas';m='informe(encontradas, expiradas, unidades)'},
       @{g=2;d='PlanificadorTareas';a='PlanificadorTareas';m='expirar_reservas_vencidas()'},
       @{g=3;d='GestorReservas';a='PlanificadorTareas';m='nadaQueExpirar()'}
     )}
)

# ---------------- generacion ----------------

foreach ($caso in $casos) {
    if (Get-Diagrama $p22 $caso.n) { Write-Output "  $($caso.n) ya existe, no se toca"; continue }

    $part = @{}
    foreach ($nom in $caso.actores)   { $part["A:$nom"] = Get-Actor $nom }
    $part[$caso.boundary]             = Get-OCrearClase $pClas $caso.boundary 'boundary' $desc[$caso.boundary]
    foreach ($nom in $caso.controles) { $part[$nom] = Get-OCrearClase $pClas $nom 'control' $desc[$nom] }
    foreach ($nom in $caso.entidades) { $part[$nom] = Get-OCrearClase $pClas $nom 'entity'  $desc[$nom] }

    $d = $p22.Diagrams.AddNew($caso.n, 'Communication')
    [void]$d.Update(); $p22.Diagrams.Refresh()

    # Cuatro columnas, cada una centrada sobre el mismo eje. Las cajas son
    # cuadradas a proposito: el estereotipo de robustez se dibuja como un
    # circulo inscrito, y con una caja ancha y baja el circulo se desborda.
    $columnas = @(
        @{ lista=@($caso.actores | ForEach-Object { "A:$_" }); x=40; ancho=100; alto=90 },
        @{ lista=@($caso.boundary); x=340; ancho=100; alto=100 },
        @{ lista=$caso.controles;   x=680; ancho=100; alto=100 },
        @{ lista=$caso.entidades;   x=1020; ancho=100; alto=100 }
    )
    foreach ($col in $columnas) {
        $paso   = $col.alto + 130
        $inicio = -220 + [int]((($col.lista.Count - 1) * $paso) / 2)
        for ($i = 0; $i -lt $col.lista.Count; $i++) {
            Poner $d $part[$col.lista[$i]] $col.x ($inicio - $i * $paso) $col.ancho $col.alto
        }
    }

    $pares = @{}
    foreach ($m in $caso.msj) {
        if ($m.d -eq $m.a) { continue }
        $c1 = $part[$m.d]; $c2 = $part[$m.a]
        $k1 = "$($c1.ElementID)-$($c2.ElementID)"; $k2 = "$($c2.ElementID)-$($c1.ElementID)"
        if ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2)) { continue }
        New-Enlace $c1 $c2
        $pares[$k1] = $true
    }

    $orden = @{}
    $mios  = @{}
    foreach ($m in $caso.msj) {
        $g = $m.g
        if (-not $orden.ContainsKey($g)) { $orden[$g] = 0 }
        $orden[$g] = $orden[$g] + 1
        $id = New-Mensaje $part[$m.d] $part[$m.a] $m.m
        $ea.Execute("UPDATE t_connector SET PDATA4='$g.$($orden[$g])' WHERE Connector_ID=$id")
        $mios[$id] = $true
    }

    $nota = $pClas.Elements.AddNew('', 'Note')
    $nota.Notes = $caso.grupos
    [void]$nota.Update()
    Poner $d $nota 340 -700 800 150

    # Regla 3: las clases de analisis se comparten entre casos de uso y EA
    # dibuja TODA relacion existente entre los elementos del lienzo.
    $d.DiagramLinks.Refresh()
    $ajenos = 0
    foreach ($lnk in $d.DiagramLinks) {
        $con = $ea.GetConnectorByID($lnk.ConnectorID)
        $propio = $false
        if ($con.Type -eq 'Collaboration') {
            $propio = $mios.ContainsKey($con.ConnectorID)
        } elseif ($con.Type -eq 'Association') {
            $k1 = "$($con.ClientID)-$($con.SupplierID)"; $k2 = "$($con.SupplierID)-$($con.ClientID)"
            $propio = ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2))
        }
        if (-not $propio) { $lnk.IsHidden = $true; [void]$lnk.Update(); $ajenos++ }
    }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    $ng = ($caso.msj | ForEach-Object { $_.g } | Sort-Object -Unique).Count
    Write-Output ("  {0,-48} {1,2} objetos, {2,2} mensajes en {3} grupos, {4,2} ajenos ocultos" -f $caso.n, $d.DiagramObjects.Count, $caso.msj.Count, $ng, $ajenos)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
