# =========================================================================
# CAP. 2 - 2.3 Analisis de Clases. CICLO 3: los veinte diagramas de clases
# de CU-12, CU-20, CU-21 y CU-26 a CU-42.
#
# Aditivo: un diagrama que ya existe no se toca. Con -Rehacer se borran y se
# vuelven a dibujar SOLO los del Ciclo 3.
# NO EXPORTA IMAGENES. Las exporta Mateo a mano desde EA (pedido del 13/09).
#
# ---- POR QUE ESTAS CLASES SON ELEMENTOS APARTE DE LAS DE 2.2 -------------
# EA dibuja el circulo de robustez solo para los estereotipos llamados
# exactamente boundary, control y entity; con cualquier otro nombre dibuja la
# clase como tabla. 2.2 necesita el circulo y 2.3 la tabla con atributos y
# operaciones, y un mismo elemento no puede verse de las dos maneras: por eso
# estan duplicadas, con el mismo nombre en paquetes distintos. Es la misma
# decision del 04/09/2026 que ya siguio el Ciclo 2.
#
# ---- NIVEL DE DETALLE ----------------------------------------------------
#   frontera     - sin atributos; operaciones = el servicio del frontend Y el
#                  endpoint del router
#   controlador  - sin atributos; operaciones = las funciones del service
#   entidad      - atributos = LAS COLUMNAS DE LA TABLA con su tipo de la
#                  base; operaciones = las funciones del repository
#
# Los nombres son los REALES del codigo: estan en
# ea-clases-2-3-ciclo3.datos.ps1, generado por gen-ops-2-3-ciclo3.py leyendo
# los modulos con `ast`, los servicios de Angular con regex y las columnas de
# information_schema. No se inventan; cada operacion del diagrama se puede
# abrir en el repositorio.
#
# ---- LO QUE TODAVIA NO EXISTE SE DIBUJA VACIO ----------------------------
# CU-34 (asistente virtual) y CU-40 (notificaciones) no estan construidos.
# Sus clases van al diagrama sin operaciones y con una nota que lo dice. Es
# deliberado: inventarles una lista de metodos haria que el diagrama mienta
# justo donde hay que defender que falta, y dejarlos fuera escondria dos
# casos de uso del alcance.
#
# ---- LA UNION ENTRE CLASES ES SIEMPRE UNA Association --------------------
# Con nombre de rol en mayusculas y cardinalidad en los dos extremos. Nada de
# Dependency, Usage, Aggregation ni Composition: con un solo tipo de linea el
# lector compara los diagramas del capitulo entre si sin interpretar la
# semantica de cada estilo, y no queda abierta la discusion de si algo era
# agregacion o composicion.
# =========================================================================

param([switch]$Rehacer)

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\SI2\Primer_Parcial\docs\diagramas\VioletBoutique.eapx'

. (Join-Path $PSScriptRoot 'ea-clases-2-3-ciclo3.datos.ps1')

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
# el circulo de robustez ---veinte diagramas del Ciclo 3 mas los del 1 y 2---
# y el sintoma aparece recien al abrirlos. Se restauran antes de nada.
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
else              { Write-Output 'Estereotipos de 2.2: sin cambios (ya estaban en ingles)' }

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
                # EA IMPRIME EL TIPO DEL PARAMETRO, NO SU NOMBRE (guia 7.4).
                # Si se pasa nombre y tipo por separado, en el PNG sale
                # `registrar_venta(Session, VentaPresencialIn, int)` y los
                # nombres no aparecen en ningun lado. La forma que funciona es
                # armar el texto una vez y ponerlo en los DOS lados.
                $texto = if ($p.t) { "$($p.n): $($p.t)" } else { $p.n }
                $par = $o.Parameters.AddNew($texto, $texto)
                [void]$par.Update()
            }
            $o.Parameters.Refresh()
        }
        $i++
    }
    $el.Methods.Refresh()
}

# Repara los parametros que una corrida anterior dejo en la forma vieja
# ---nombre y tipo por separado, que EA dibuja mostrando SOLO el tipo---.
# `Set-Operaciones` no alcanza para esto porque saltea las operaciones que ya
# existen, y estas ya existen: lo que cambia es lo de adentro.
#
# Solo toca las clases de ESTE script. Las heredadas de los Ciclos 1 y 2
# tienen el mismo defecto, pero son de otros generadores y sus diagramas ya
# estan exportados: se avisa y se decide aparte.
function Repair-Parametros($el) {
    $el.Methods.Refresh()
    $arreglados = 0
    foreach ($o in $el.Methods) {
        $o.Parameters.Refresh()
        if ($o.Parameters.Count -eq 0) { continue }
        # Ya esta en la forma nueva si el primero lleva el tipo en el nombre.
        if ($o.Parameters.GetAt(0).Name -match ':\s') { continue }
        $viejos = @()
        foreach ($p in $o.Parameters) { $viejos += ,@($p.Name, $p.Type) }
        for ($i = $o.Parameters.Count - 1; $i -ge 0; $i--) { $o.Parameters.DeleteAt($i, $false) }
        $o.Parameters.Refresh()
        foreach ($v in $viejos) {
            $texto = if ($v[1]) { "$($v[0]): $($v[1])" } else { $v[0] }
            $par = $o.Parameters.AddNew($texto, $texto)
            [void]$par.Update()
        }
        $o.Parameters.Refresh()
        $arreglados++
    }
    return $arreglados
}

# Regla 5: borrar un diagrama no borra sus conectores. Se deduplica por par +
# tipo + nombre de rol.
function New-Asociacion($src, $dst, $rol, $cardOrigen, $cardDestino) {
    if (-not $src -or -not $dst) { throw "Asociacion '$rol' con un extremo que no existe" }
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
# la lista sin avisar --- y una entidad del Ciclo 3 como `venta` tiene
# dieciseis columnas, asi que la cuenta importa mas que en el Ciclo 2.
function Alto($nombre) {
    $na = 0; if ($ATTRS.ContainsKey($nombre)) { $na = $ATTRS[$nombre].Count }
    $no = 0
    if ($OPS.ContainsKey($nombre))   { $no = $OPS[$nombre].Count }
    if ($CTRL.ContainsKey($nombre))  { $no = $CTRL[$nombre].Count }
    if ($FRONT.ContainsKey($nombre)) { $no = $FRONT[$nombre].Count }
    return 70 + ($na * 18) + ($no * 18)
}

# ---------------- descripciones ----------------

$desc = @{
    # --- fronteras ---
    'PantallaPromociones'     = 'Frontera de CU-12. Frontend: features/admin/promociones con PromocionesService; backend: app/modules/catalogo/promociones_router.py sobre /api/v1/catalogo/promociones.'
    'PantallaFavoritos'       = 'Frontera de CU-20. Frontend: la vitrina y el panel del Cliente; backend: app/modules/catalogo_publico/favoritos_router.py sobre /api/v1/tienda/favoritos.'
    'PantallaVestidor'        = 'Frontera de CU-21, el vestidor virtual. Movil: mobile/lib/features/vestidor con la camara; backend: app/modules/vestidor_virtual/router.py y app/modules/medidas/router.py, que da el ajuste por talla.'
    'PantallaCarrito'         = 'Frontera de CU-26. Frontend: features/tienda/carrito con CarritoService; backend: app/modules/ventas/carrito_router.py sobre /api/v1/carrito.'
    'PantallaCheckout'        = 'Frontera de CU-27. Frontend: features/tienda/checkout con PedidosService; backend: app/modules/ventas/router.py sobre /api/v1/pedidos. Es quien manda al Cliente a la pasarela; NO es quien confirma el pago.'
    'WebhookPasarela'         = 'Frontera de CU-28 y la unica que no tiene pantalla: la recibe la pasarela, no una persona. app/modules/pagos/router.py. Por la decision D5 el estado del pago solo cambia desde aca, con la firma verificada.'
    'PantallaCompras'         = 'Frontera de CU-29. Frontend: features/cliente/compras con ComprasService; backend: app/modules/ventas/historial_router.py, que ademas entrega el comprobante en PDF.'
    'PantallaTurno'           = 'Frontera de CU-30. Frontend: features/caja/turno con CajaService; backend: app/modules/caja/router.py sobre /api/v1/caja.'
    'PantallaVenta'           = 'Frontera de CU-31, el mostrador. Frontend: features/caja/venta con PosService; backend: app/modules/pos/router.py sobre /api/v1/pos.'
    'PantallaDevolucion'      = 'Frontera de CU-32. Frontend: features/caja/devolucion con DevolucionesService; backend: app/modules/pos/devolucion_router.py.'
    'PantallaParaVos'         = 'Frontera de CU-33, la seccion "Para vos". Frontend y movil: la vitrina del Cliente; backend: app/modules/ia/router.py sobre /api/v1/ia/recomendaciones.'
    'PantallaAsistente'       = 'Frontera de CU-34. TODAVIA NO CONSTRUIDA: el caso de uso esta en el alcance del Ciclo 3 y aun no tiene codigo. Se dibuja vacia a proposito, para que el modelo no diga que existe algo que no existe.'
    'PantallaReportePorVoz'   = 'Frontera de CU-35. Frontend: DictadoService, que transcribe en el navegador con la Web Speech API; backend: los endpoints /voz de app/modules/reportes/reportes_router.py. El audio NO viaja al servidor: viaja el texto.'
    'PantallaTablero'         = 'Frontera de CU-36. Frontend: features/admin/tablero con TableroService; backend: app/modules/reportes/tablero_router.py.'
    'PantallaReportes'        = 'Frontera de CU-37. Frontend: features/admin/reportes con ReportesService; backend: los endpoints de catalogo y descarga de app/modules/reportes/reportes_router.py, que arma el PDF y el Excel.'
    'PantallaMisProductos'    = 'Frontera de CU-38, el panel del Proveedor. Frontend: features/proveedor con ProveedorService; backend: app/modules/catalogo/proveedor_router.py, que solo deja ver y tocar lo propio.'
    'PantallaAbastecimiento'  = 'Frontera de CU-39. Frontend: features/proveedor/abastecimiento con AbastecimientoService; backend: app/modules/abastecimiento/router.py.'
    'CanalDeAviso'            = 'Frontera de CU-40: el canal por donde sale el aviso, no una pantalla. Hoy solo esta el adaptador de correo (app/integrations/correo), que en desarrollo escribe por consola. El resto del caso de uso no esta construido.'
    'PantallaRecuperacion'    = 'Frontera de CU-41. Frontend: AuthService con el pedido y el canje; backend: los dos endpoints de recuperacion de app/modules/seguridad/router.py. Es un caso de uso del Ciclo 3 sobre un paquete del Ciclo 1.'
    'PantallaBitacora'        = 'Frontera de CU-42. Frontend: features/admin/bitacora con BitacoraService; backend: app/modules/bitacora/router.py.'

    # --- controladores ---
    'GestorPromociones'       = 'app/modules/catalogo/promociones_service.py. Elige UN descuento por prenda cuando hay varios que alcanzan: gana el porcentaje mayor y, si empatan, el mas especifico (producto > categoria > temporada). Recorre el arbol de categorias, asi que una promocion en la categoria madre alcanza a las hijas.'
    'GestorFavoritos'         = 'app/modules/catalogo_publico/service.py. Marca y desmarca, y lista solo lo ofrecible: un producto que dejo de estar a la venta no desaparece del favorito, pero tampoco se muestra como disponible.'
    'GestorVestidor'          = 'app/modules/vestidor_virtual/service.py con app/modules/medidas/service.py. Compone la prenda sobre la foto usando el PNG transparente de la variante y devuelve el ajuste segun las medidas del Cliente. Si el proveedor de IA no esta configurado responde que no esta disponible, en vez de fallar al tocarlo.'
    'GestorCarrito'           = 'app/modules/ventas/carrito_service.py. Un carrito por cliente. Resuelve el precio con GestorPromociones en cada lectura --- el precio NO se congela en el carrito --- y comprueba stock contra P4.'
    'GestorPedidos'           = 'app/modules/ventas/service.py. Arma el pedido, genera su codigo con la fecha boliviana y fija el vencimiento. Delega en GestorInventario: es P4 quien aparta, por la regla de que ninguna cantidad cambia sin su movimiento.'
    'GestorPagos'             = 'app/modules/pagos/service.py. Inicia el cobro contra el adaptador de pasarela y aplica el resultado SOLO desde la notificacion firmada (decision D5). Una notificacion repetida no descuenta el inventario dos veces.'
    'GestorHistorial'         = 'app/modules/ventas/historial_service.py. Lista las compras del Cliente y arma el comprobante en PDF con ReportLab, numerandolo la primera vez que se pide.'
    'GestorCaja'              = 'app/modules/caja/service.py. Abre y cierra el turno, y calcula el esperado sumando el efectivo cobrado y restando las devoluciones del turno. La diferencia se guarda: no se corrige.'
    'GestorMostrador'         = 'app/modules/pos/service.py. Registra la venta presencial, que segun la decision D2 es la MISMA entidad Venta que la del canal en linea. Si la venta sale de una reserva ya atendida no vuelve a descontar stock --- la prenda ya se descontro al atenderla.'
    'GestorDevoluciones'      = 'app/modules/pos/devolucion_service.py. Busca la venta devolvible y registra la devolucion dentro del turno abierto, devolviendo las unidades al inventario por GestorInventario.'
    'GestorRecomendaciones'   = 'app/modules/ia/service.py. Arma el perfil del Cliente, elige candidatas y las ordena con el adaptador de recomendacion. Guarda el resultado y lo invalida cuando el perfil cambia; sin proveedor de IA cae al orden por popularidad.'
    'GestorAsistente'         = 'Control de CU-34. TODAVIA NO CONSTRUIDO: no hay modulo que leer. Se dibuja sin operaciones a proposito.'
    'GestorReportePorVoz'     = 'app/integrations/interprete. Convierte el texto dictado en un pedido de reporte (que reporte, que periodo, que sucursal) y se lo pasa a GestorReportes. Si no hay proveedor configurado avisa que no esta disponible ANTES de ofrecer el boton.'
    'GestorTablero'           = 'app/modules/reportes/tablero_service.py. Resuelve el periodo en hora boliviana con app/core/tiempo.py y arma los indicadores de reservas, conversion, inventario y ventas.'
    'GestorReportes'          = 'app/modules/reportes/reportes_service.py. Arma los seis reportes de gestion y los exporta a PDF y Excel con app/modules/reportes/exportador.py.'
    'GestorCatalogoProveedor' = 'app/modules/catalogo/proveedor_service.py. Lo mismo que GestorProductos pero acotado a lo propio del Proveedor: por la convencion 1, un producto ajeno no da 403 sino 404.'
    'GestorAbastecimiento'    = 'app/modules/abastecimiento/service.py. El Proveedor anuncia cantidad y plazo; el Encargado ve el aviso y lo recibe, y recien ahi entra al inventario por GestorInventario.'
    'GestorNotificaciones'    = 'Control de CU-40. TODAVIA NO CONSTRUIDO. Lo unico que existe es el adaptador de correo. Se dibuja sin operaciones a proposito.'
    'GestorRecuperacion'      = 'Las dos operaciones de recuperacion de app/modules/seguridad/service.py. Guarda el HASH del token, no el token, y siempre responde lo mismo pida quien pida: decir "ese correo no existe" seria decirle a cualquiera quien tiene cuenta.'
    'GestorBitacora'          = 'app/modules/bitacora/service.py, alimentado por el middleware. Registra quien hizo que y sobre que, en hora boliviana.'

    # --- entidades ---
    'Promocion'               = 'Tabla promocion. `alcance` dice cual de los tres objetivos esta puesto (producto, categoria o temporada) y un CHECK obliga a que sea exactamente uno. `desde` y `hasta` son DATE, no instantes: la vigencia es por dia boliviano.'
    'Favorito'                = 'Tabla favorito. El par cliente-producto, unico. Marca el producto entero, no la variante: el Cliente guarda "esta prenda", no "esta prenda en talla M azul".'
    'MedidaCliente'           = 'Tabla medida_cliente. Las medidas que el Cliente carga para el vestidor virtual; de ahi sale el ajuste por talla que muestra CU-21.'
    'Carrito'                 = 'Tabla carrito. Uno por cliente, permanente. No guarda precios: el precio se resuelve en cada lectura con las promociones vigentes de ese momento.'
    'CarritoDetalle'          = 'Tabla carrito_detalle. Una variante y su cantidad. La variante, no el producto: es lo unico que tiene existencia (decision D1).'
    'Venta'                   = 'Tabla venta. UNA sola entidad para los dos canales, en linea y mostrador (decision D2); `canal` los distingue. `codigo` lleva la fecha boliviana. Los pedidos en linea nacen pendientes y vencen; los del mostrador nacen cobrados.'
    'DetalleVenta'            = 'Tabla detalle_venta. La linea vendida con su precio unitario y su descuento CONGELADOS: una promocion que cambie manana no puede cambiar lo que ya se cobro.'
    'Pago'                    = 'Tabla pago. El estado lo mueve unicamente la notificacion firmada de la pasarela (decision D5). Ninguna pantalla lo toca.'
    'TransaccionPasarela'     = 'Tabla transaccion_pasarela. El registro de lo que dijo la pasarela, con su identificador de evento. Es lo que hace que una notificacion repetida no se aplique dos veces.'
    'Comprobante'             = 'Tabla comprobante. El numero y el PDF de la venta. Se genera la primera vez que alguien lo pide y despues se reutiliza: el mismo numero para la misma venta, siempre.'
    'Caja'                    = 'Tabla caja. El puesto fisico de cobro, que pertenece a una sucursal. La migracion 0019 creo una en cada sucursal: sin caja, CU-30 no puede abrir turno y CU-31 y CU-32 quedan inservibles sin decir por que.'
    'TurnoCaja'               = 'Tabla turno_caja. La jornada de un cajero en una caja. Solo puede haber uno abierto por caja y uno por usuario a la vez, y es el ambito al que se cuelgan las ventas y las devoluciones del dia.'
    'Devolucion'              = 'Tabla devolucion. La cabecera: que venta, que turno, cuanto sale del cajon. Se registra sobre el turno abierto, y por eso el arqueo la resta.'
    'DetalleDevolucion'       = 'Tabla detalle_devolucion. La linea devuelta. No se puede devolver mas de lo vendido ni dos veces lo mismo.'
    'Recomendacion'           = 'Tabla recomendacion. El resultado guardado para un cliente, con su momento. Se invalida cuando el perfil cambia; sin eso, la seccion "Para vos" se quedaria mostrando lo de la semana pasada.'
    'Abastecimiento'          = 'Tabla abastecimiento. El anuncio del Proveedor: que variante, cuanta cantidad y para que fecha. Anunciar NO toca el inventario; recibir si.'
    'Notificacion'            = 'Entidad de CU-40. TODAVIA NO EXISTE: no hay tabla `notificacion` en la cadena de migraciones. Se dibuja sin columnas a proposito, para que el pendiente se vea en el modelo en vez de quedar escondido.'
    'Bitacora'                = 'Tabla bitacora. Quien, que, sobre que entidad y cuando, en hora boliviana. La escribe el middleware, no cada caso de uso.'
    'TokenRecuperacion'       = 'Tabla token_recuperacion. Guarda el HASH del token, no el token. Vence, se usa una sola vez, y pedir uno nuevo invalida los anteriores.'
}

$estereotipoDe = @{}
foreach ($n in @('PantallaPromociones','PantallaFavoritos','PantallaVestidor','PantallaCarrito',
                 'PantallaCheckout','WebhookPasarela','PantallaCompras','PantallaTurno',
                 'PantallaVenta','PantallaDevolucion','PantallaParaVos','PantallaAsistente',
                 'PantallaReportePorVoz','PantallaTablero','PantallaReportes','PantallaMisProductos',
                 'PantallaAbastecimiento','CanalDeAviso','PantallaRecuperacion','PantallaBitacora')) {
    $estereotipoDe[$n] = 'frontera'
}
foreach ($n in @('GestorPromociones','GestorFavoritos','GestorVestidor','GestorCarrito',
                 'GestorPedidos','GestorPagos','GestorHistorial','GestorCaja','GestorMostrador',
                 'GestorDevoluciones','GestorRecomendaciones','GestorAsistente',
                 'GestorReportePorVoz','GestorTablero','GestorReportes','GestorCatalogoProveedor',
                 'GestorAbastecimiento','GestorNotificaciones','GestorRecuperacion',
                 'GestorBitacora')) {
    $estereotipoDe[$n] = 'controlador'
}
foreach ($n in @('Promocion','Favorito','MedidaCliente','Carrito','CarritoDetalle','Venta',
                 'DetalleVenta','Pago','TransaccionPasarela','Comprobante','Caja','TurnoCaja',
                 'Devolucion','DetalleDevolucion','Recomendacion','Abastecimiento','Notificacion',
                 'Bitacora','TokenRecuperacion')) {
    $estereotipoDe[$n] = 'entidad'
}

$reparados = 0
foreach ($nombre in $estereotipoDe.Keys) {
    $el = Get-OCrearClase23 $nombre $estereotipoDe[$nombre] $desc[$nombre]
    if ($ATTRS.ContainsKey($nombre))  { Set-Atributos   $el $ATTRS[$nombre] }
    if ($OPS.ContainsKey($nombre))    { Set-Operaciones $el $OPS[$nombre] }
    if ($CTRL.ContainsKey($nombre))   { Set-Operaciones $el $CTRL[$nombre] }
    if ($FRONT.ContainsKey($nombre))  { Set-Operaciones $el $FRONT[$nombre] }
    $reparados += Repair-Parametros $el
}
if ($reparados) { Write-Output "Operaciones con parametros reescritos a la forma de la guia: $reparados" }

# ---------------- actores ----------------
# LA GUIA 7.4 LOS PIDE (correccion del 17/09/2026): la frontera existe porque
# alguien la usa, y sin el actor el diagrama no dice quien empieza el caso.
#
# La guia anota que Violet Boutique no cumplia esta regla, y da el motivo:
# aplicarla obligaba a regenerar los 23 diagramas de clases que ya estaban
# hechos. Para los veinte del Ciclo 3 ese motivo no corre ---se dibujan por
# primera vez---, asi que van con actor desde el principio.
# OJO: LA BUSQUEDA ES POR NOMBRE **Y TIPO**.
#
# El paquete 2.3 ya tiene clases `entidad` llamadas `Cliente` y `Proveedor`
# --- son las tablas `cliente` y `proveedor` del Ciclo 1 ---. Buscando solo
# por nombre, el actor Cliente resolvia a ESA CLASE: cinco diagramas quedaron
# con una entidad de base de datos puesta en la columna de actores y una
# asociacion OPERA_DESDE saliendo de ella. Se veia como un actor porque
# estaba donde va el actor.
#
# Los actores tampoco entran en `$indice23`, que esta indexado por nombre a
# secas: meterlos ahi pisaria la clase `Cliente` y `$C['Cliente']` dejaria de
# ser la entidad.
$actor23 = @{}
function Get-OCrearActor($nombre, $notas) {
    if ($actor23.ContainsKey($nombre)) { return $actor23[$nombre] }
    $p23.Elements.Refresh()
    foreach ($e in $p23.Elements) {
        if ($e.Name -eq $nombre -and $e.Type -eq 'Actor') { $actor23[$nombre] = $e; return $e }
    }
    $e = $p23.Elements.AddNew($nombre, 'Actor')
    if ($notas) { $e.Notes = $notas }
    [void]$e.Update(); $p23.Elements.Refresh()
    $actor23[$nombre] = $e
    return $e
}

# Limpieza de la corrida que ligo las entidades `Cliente` y `Proveedor` a las
# fronteras. `OPERA_DESDE` es exclusivo de la union actor--frontera, asi que
# una saliendo de una Class es siempre de aquella pasada.
$limpiados = 0
foreach ($e in $p23.Elements) {
    if ($e.Type -ne 'Class') { continue }
    $e.Connectors.Refresh()
    for ($i = $e.Connectors.Count - 1; $i -ge 0; $i--) {
        $c = $e.Connectors.GetAt($i)
        if ($c.ClientID -eq $e.ElementID -and $c.Type -eq 'Association' -and $c.Name -eq 'OPERA_DESDE') {
            $e.Connectors.DeleteAt($i, $false); $limpiados++
        }
    }
    $e.Connectors.Refresh()
}
if ($limpiados) { Write-Output "Asociaciones OPERA_DESDE que salian de una clase, borradas: $limpiados" }
foreach ($a in @(
    @{n='Cliente';                       d='Quien compra. Es el disparador de la vitrina, el carrito, el pedido, el vestidor y los favoritos.'},
    @{n='Administrador';                 d='Configura el sistema y lee los indicadores. Disparador de promociones, tablero, reportes y bitacora.'},
    @{n='Cajero';                        d='Opera el mostrador de una sucursal: turno de caja, venta presencial y devolucion.'},
    @{n='Proveedor';                     d='Empresa que abastece prendas. Solo ve y toca lo propio.'},
    @{n='Pasarela de Pago';              d='Actor externo. En CU-28 es el DISPARADOR: llama al webhook por su cuenta, sin que nadie del sistema se lo pida. En CU-27 es secundario, lo invoca GestorPagos.'},
    @{n='Servicio de IA';                d='Actor externo secundario: NUNCA dispara un caso de uso, siempre lo invoca un controlador. Por eso se une al controlador y no a la frontera.'},
    @{n='Sistema (procesos automaticos)'; d='El planificador. Dispara los casos que no los inicia una persona.'}
)) { $actor23[$a.n] = Get-OCrearActor $a.n $a.d }

# Las clases de los Ciclos 1 y 2 se REUSAN tal cual. Si alguna falta es que no
# se corrieron los generadores anteriores, y hay que parar: crearlas aca las
# dejaria sin atributos y el diagrama del Ciclo 2 mostraria una caja vacia.
$heredadas = @('GestorAutenticacion','GestorInventario','GestorVitrina','GestorProductos',
               'GestorConsolidado','GestorReservas','Producto','VarianteProducto',
               'ImagenProducto','Existencia','MovimientoInventario','Reserva','Usuario',
               'SesionToken')
$faltan = @()
foreach ($n in $heredadas) { if (-not $indice23.ContainsKey($n)) { $faltan += $n } }
if ($faltan.Count) {
    throw ("Faltan en 2.3 clases de los ciclos anteriores: {0}. Correr primero " +
           "ea-clases-2-3.ps1 y ea-clases-2-3-ciclo2.ps1") -f ($faltan -join ', ')
}

Write-Output "Clases de 2.3 del Ciclo 3 listas: $($estereotipoDe.Count) (+ $($heredadas.Count) heredadas)"

# ---------------- asociaciones ----------------

$C = $indice23
$gau = $C['GestorAutenticacion']

# --- frontera -> controlador -------------------------------------------
New-Asociacion $C['PantallaPromociones']    $C['GestorPromociones']       'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaFavoritos']      $C['GestorFavoritos']         'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaVestidor']       $C['GestorVestidor']          'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaCarrito']        $C['GestorCarrito']           'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaCheckout']       $C['GestorPedidos']           'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaCheckout']       $C['GestorPagos']             'DELEGA_EN' '1' '1'
New-Asociacion $C['WebhookPasarela']        $C['GestorPagos']             'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaCompras']        $C['GestorHistorial']         'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaTurno']          $C['GestorCaja']              'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaVenta']          $C['GestorMostrador']         'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaDevolucion']     $C['GestorDevoluciones']      'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaParaVos']        $C['GestorRecomendaciones']   'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaAsistente']      $C['GestorAsistente']         'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaReportePorVoz']  $C['GestorReportePorVoz']     'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaTablero']        $C['GestorTablero']           'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaReportes']       $C['GestorReportes']          'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaMisProductos']   $C['GestorCatalogoProveedor'] 'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaAbastecimiento'] $C['GestorAbastecimiento']    'DELEGA_EN' '1' '1'
New-Asociacion $C['CanalDeAviso']           $C['GestorNotificaciones']    'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaRecuperacion']   $C['GestorRecuperacion']      'DELEGA_EN' '1' '1'
New-Asociacion $C['PantallaBitacora']       $C['GestorBitacora']          'DELEGA_EN' '1' '1'

# --- frontera -> GestorAutenticacion -----------------------------------
# Las tres que NO van: WebhookPasarela (la llama la pasarela, no una sesion;
# lo que verifica es la FIRMA), PantallaRecuperacion (el que la usa es
# justamente quien no puede entrar) y CanalDeAviso (sale del sistema).
foreach ($f in @('PantallaPromociones','PantallaFavoritos','PantallaVestidor','PantallaCarrito',
                 'PantallaCheckout','PantallaCompras','PantallaTurno','PantallaVenta',
                 'PantallaDevolucion','PantallaParaVos','PantallaAsistente',
                 'PantallaReportePorVoz','PantallaTablero','PantallaReportes',
                 'PantallaMisProductos','PantallaAbastecimiento','PantallaBitacora')) {
    New-Asociacion $C[$f] $gau 'VERIFICA_CON' '1' '1'
}

# --- controlador -> entidad --------------------------------------------
New-Asociacion $C['GestorPromociones']       $C['Promocion']            'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorFavoritos']         $C['Favorito']             'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorVestidor']          $C['MedidaCliente']        'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorCarrito']           $C['Carrito']              'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorCarrito']           $C['CarritoDetalle']       'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorPedidos']           $C['Venta']                'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorPedidos']           $C['DetalleVenta']         'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorPagos']             $C['Pago']                 'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorPagos']             $C['TransaccionPasarela']  'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorPagos']             $C['Venta']                'ACTUALIZA'  '1' '0..*'
New-Asociacion $C['GestorHistorial']         $C['Comprobante']          'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorHistorial']         $C['Venta']                'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorCaja']              $C['Caja']                 'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorCaja']              $C['TurnoCaja']            'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorMostrador']         $C['Venta']                'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorMostrador']         $C['DetalleVenta']         'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorDevoluciones']      $C['Devolucion']           'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorDevoluciones']      $C['DetalleDevolucion']    'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorRecomendaciones']   $C['Recomendacion']        'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorAbastecimiento']    $C['Abastecimiento']       'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorNotificaciones']    $C['Notificacion']         'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorRecuperacion']      $C['TokenRecuperacion']    'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorRecuperacion']      $C['Usuario']              'ACTUALIZA'  '1' '0..*'
New-Asociacion $C['GestorBitacora']          $C['Bitacora']             'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorCatalogoProveedor'] $C['Producto']             'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorCatalogoProveedor'] $C['VarianteProducto']     'ADMINISTRA' '1' '0..*'
New-Asociacion $C['GestorTablero']           $C['Venta']                'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorTablero']           $C['Reserva']              'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorTablero']           $C['Existencia']           'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorReportes']          $C['Venta']                'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorReportes']          $C['Existencia']           'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorReportes']          $C['MovimientoInventario'] 'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorReportes']          $C['Reserva']              'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorVestidor']          $C['ImagenProducto']       'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorFavoritos']         $C['Producto']             'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorRecomendaciones']   $C['VarianteProducto']     'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorAsistente']         $C['Venta']                'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorAsistente']         $C['Reserva']              'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorBitacora']          $C['Usuario']              'CONSULTA'   '1' '0..*'
New-Asociacion $C['GestorRecuperacion']      $C['SesionToken']          'REVOCA'     '1' '0..*'

# --- las costuras: un control le PIDE el dato a otro ---------------------
# Ninguna cantidad de inventario cambia fuera de GestorInventario (P4), y
# ningun precio con descuento se calcula fuera de GestorPromociones. Estas
# lineas son la razon por la que el Ciclo 3 no reimplemento ninguna de las
# dos reglas.
New-Asociacion $C['GestorCarrito']           $C['GestorPromociones'] 'PIDE_PRECIO_A' '1' '1'
New-Asociacion $C['GestorCarrito']           $C['GestorInventario']  'CONSULTA_A'    '1' '1'
New-Asociacion $C['GestorPedidos']           $C['GestorPromociones'] 'PIDE_PRECIO_A' '1' '1'
New-Asociacion $C['GestorPedidos']           $C['GestorInventario']  'APARTA_CON'    '1' '1'
New-Asociacion $C['GestorPagos']             $C['GestorInventario']  'DESCUENTA_CON' '1' '1'
New-Asociacion $C['GestorPagos']             $C['GestorCarrito']     'VACIA_CON'     '1' '1'
New-Asociacion $C['GestorMostrador']         $C['GestorPromociones'] 'PIDE_PRECIO_A' '1' '1'
New-Asociacion $C['GestorMostrador']         $C['GestorInventario']  'DESCUENTA_CON' '1' '1'
New-Asociacion $C['GestorMostrador']         $C['GestorCaja']        'COBRA_EN'      '1' '1'
New-Asociacion $C['GestorMostrador']         $C['GestorHistorial']   'EMITE_CON'     '1' '1'
New-Asociacion $C['GestorDevoluciones']      $C['GestorInventario']  'REPONE_CON'    '1' '1'
New-Asociacion $C['GestorDevoluciones']      $C['GestorCaja']        'DESCARGA_EN'   '1' '1'
New-Asociacion $C['GestorPromociones']       $C['GestorVitrina']     'ALIMENTA_A'    '1' '1'
New-Asociacion $C['GestorFavoritos']         $C['GestorVitrina']     'CONSULTA_A'    '1' '1'
New-Asociacion $C['GestorVestidor']          $C['GestorVitrina']     'CONSULTA_A'    '1' '1'
New-Asociacion $C['GestorRecomendaciones']   $C['GestorVitrina']     'CONSULTA_A'    '1' '1'
New-Asociacion $C['GestorRecomendaciones']   $C['GestorFavoritos']   'PERFILA_CON'   '1' '1'
New-Asociacion $C['GestorAsistente']         $C['GestorVitrina']     'CONSULTA_A'    '1' '1'
New-Asociacion $C['GestorReportePorVoz']     $C['GestorReportes']    'DELEGA_EN'     '1' '1'
New-Asociacion $C['GestorCatalogoProveedor'] $C['GestorProductos']   'DELEGA_EN'     '1' '1'
New-Asociacion $C['GestorAbastecimiento']    $C['GestorConsolidado'] 'CONSULTA_A'    '1' '1'
New-Asociacion $C['GestorAbastecimiento']    $C['GestorInventario']  'RECIBE_CON'    '1' '1'
New-Asociacion $C['GestorNotificaciones']    $C['GestorReservas']    'ESCUCHA_A'     '1' '1'
New-Asociacion $C['GestorNotificaciones']    $C['GestorPagos']       'ESCUCHA_A'     '1' '1'
New-Asociacion $C['GestorNotificaciones']    $C['GestorInventario']  'ESCUCHA_A'     '1' '1'

# --- entidad -> entidad --------------------------------------------------
New-Asociacion $C['Promocion']           $C['Producto']         'APLICA_A'    '0..*' '0..1'
New-Asociacion $C['Favorito']            $C['Producto']         'MARCA_A'     '0..*' '1'
New-Asociacion $C['CarritoDetalle']      $C['Carrito']          'PERTENECE_A' '0..*' '1'
New-Asociacion $C['CarritoDetalle']      $C['VarianteProducto'] 'REFIERE_A'   '0..*' '1'
New-Asociacion $C['DetalleVenta']        $C['Venta']            'PERTENECE_A' '1..*' '1'
New-Asociacion $C['DetalleVenta']        $C['VarianteProducto'] 'VENDE'       '0..*' '1'
New-Asociacion $C['Pago']                $C['Venta']            'SALDA_A'     '0..*' '1'
New-Asociacion $C['TransaccionPasarela'] $C['Pago']             'NOTIFICA_A'  '0..*' '1'
New-Asociacion $C['Comprobante']         $C['Venta']            'ACREDITA_A'  '0..1' '1'
New-Asociacion $C['TurnoCaja']           $C['Caja']             'SE_ABRE_EN'  '0..*' '1'
New-Asociacion $C['Venta']               $C['TurnoCaja']        'SE_COBRA_EN' '0..*' '0..1'
New-Asociacion $C['Devolucion']          $C['Venta']            'REVIERTE_A'  '0..*' '1'
New-Asociacion $C['Devolucion']          $C['TurnoCaja']        'SE_PAGA_EN'  '0..*' '1'
New-Asociacion $C['DetalleDevolucion']   $C['Devolucion']       'PERTENECE_A' '1..*' '1'
New-Asociacion $C['DetalleDevolucion']   $C['DetalleVenta']     'REVIERTE_A'  '0..*' '1'
New-Asociacion $C['Recomendacion']       $C['VarianteProducto'] 'SUGIERE'     '0..*' '0..*'
New-Asociacion $C['Abastecimiento']      $C['VarianteProducto'] 'REPONE_A'    '0..*' '1'
New-Asociacion $C['MedidaCliente']       $C['Usuario']          'DESCRIBE_A'  '0..1' '1'
New-Asociacion $C['TokenRecuperacion']   $C['Usuario']          'HABILITA_A'  '0..*' '1'
New-Asociacion $C['Bitacora']            $C['Usuario']          'ATRIBUYE_A'  '0..*' '0..1'

Write-Output 'Asociaciones listas.'

# ---------------- los veinte diagramas ----------------

#   act = los actores del caso. `d` es contra QUE clase se une cada uno:
#         el disparador va contra la FRONTERA, que es lo que pide la guia;
#         un actor externo secundario ---el Servicio de IA, o la pasarela
#         cuando es el sistema el que la llama--- va contra el CONTROLADOR que
#         lo invoca, porque unirlo a la frontera diria que empieza el caso de
#         uso, y no lo empieza.
$casos = @(
  @{ n='2.3 CU-12 Gestionar promociones';              f='PantallaPromociones';   c=@('GestorPromociones','GestorAutenticacion');                                                  e=@('Promocion','Producto','VarianteProducto');
     act=@(@{a='Administrador'; d='PantallaPromociones'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-20 Gestionar favoritos';                f='PantallaFavoritos';     c=@('GestorFavoritos','GestorVitrina','GestorAutenticacion');                                    e=@('Favorito','Producto');
     act=@(@{a='Cliente'; d='PantallaFavoritos'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-21 Utilizar vestidor virtual (RA)';     f='PantallaVestidor';      c=@('GestorVestidor','GestorVitrina','GestorAutenticacion');                                     e=@('MedidaCliente','ImagenProducto','VarianteProducto');
     act=@(@{a='Cliente'; d='PantallaVestidor'; r='OPERA_DESDE'}, @{a='Servicio de IA'; d='GestorVestidor'; r='RESUELVE_PARA'}) },
  @{ n='2.3 CU-26 Gestionar carrito de compras';       f='PantallaCarrito';       c=@('GestorCarrito','GestorPromociones','GestorInventario','GestorAutenticacion');               e=@('Carrito','CarritoDetalle','VarianteProducto');
     act=@(@{a='Cliente'; d='PantallaCarrito'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-27 Realizar pedido y pagar en línea';   f='PantallaCheckout';      c=@('GestorPedidos','GestorPagos','GestorInventario','GestorPromociones','GestorAutenticacion'); e=@('Venta','DetalleVenta','Pago','Existencia');
     act=@(@{a='Cliente'; d='PantallaCheckout'; r='OPERA_DESDE'}, @{a='Pasarela de Pago'; d='GestorPagos'; r='COBRA_PARA'}) },
  @{ n='2.3 CU-28 Confirmar pago del pedido';          f='WebhookPasarela';       c=@('GestorPagos','GestorInventario','GestorCarrito');                                           e=@('Pago','TransaccionPasarela','Venta','Existencia');
     act=@(@{a='Pasarela de Pago'; d='WebhookPasarela'; r='NOTIFICA_A'}) },
  @{ n='2.3 CU-29 Consultar historial de compras';     f='PantallaCompras';       c=@('GestorHistorial','GestorAutenticacion');                                                    e=@('Venta','DetalleVenta','Comprobante');
     act=@(@{a='Cliente'; d='PantallaCompras'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-30 Abrir y cerrar caja';                f='PantallaTurno';         c=@('GestorCaja','GestorAutenticacion');                                                         e=@('Caja','TurnoCaja','Venta','Devolucion');
     act=@(@{a='Cajero'; d='PantallaTurno'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-31 Registrar venta presencial';         f='PantallaVenta';         c=@('GestorMostrador','GestorCaja','GestorInventario','GestorPromociones','GestorHistorial');    e=@('Venta','DetalleVenta','Comprobante','Existencia');
     act=@(@{a='Cajero'; d='PantallaVenta'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-32 Registrar devolución';               f='PantallaDevolucion';    c=@('GestorDevoluciones','GestorCaja','GestorInventario');                                       e=@('Devolucion','DetalleDevolucion','Venta','DetalleVenta');
     act=@(@{a='Cajero'; d='PantallaDevolucion'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-33 Recibir recomendaciones de prendas'; f='PantallaParaVos';       c=@('GestorRecomendaciones','GestorVitrina','GestorFavoritos','GestorAutenticacion');            e=@('Recomendacion','VarianteProducto','Favorito');
     act=@(@{a='Cliente'; d='PantallaParaVos'; r='OPERA_DESDE'}, @{a='Servicio de IA'; d='GestorRecomendaciones'; r='RESUELVE_PARA'}) },
  @{ n='2.3 CU-34 Conversar con el asistente virtual'; f='PantallaAsistente';     c=@('GestorAsistente','GestorVitrina','GestorAutenticacion');                                    e=@('Venta','Reserva');
     act=@(@{a='Cliente'; d='PantallaAsistente'; r='OPERA_DESDE'}, @{a='Servicio de IA'; d='GestorAsistente'; r='RESUELVE_PARA'}) },
  @{ n='2.3 CU-35 Generar reporte por comando de voz'; f='PantallaReportePorVoz'; c=@('GestorReportePorVoz','GestorReportes','GestorAutenticacion');                               e=@('Venta');
     act=@(@{a='Administrador'; d='PantallaReportePorVoz'; r='OPERA_DESDE'}, @{a='Servicio de IA'; d='GestorReportePorVoz'; r='RESUELVE_PARA'}) },
  @{ n='2.3 CU-36 Consultar tablero de indicadores';   f='PantallaTablero';       c=@('GestorTablero','GestorAutenticacion');                                                      e=@('Venta','Reserva','Existencia');
     act=@(@{a='Administrador'; d='PantallaTablero'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-37 Generar reportes de gestión';        f='PantallaReportes';      c=@('GestorReportes','GestorAutenticacion');                                                     e=@('Venta','Existencia','MovimientoInventario','Reserva');
     act=@(@{a='Administrador'; d='PantallaReportes'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-38 Registrar productos del proveedor';  f='PantallaMisProductos';  c=@('GestorCatalogoProveedor','GestorProductos','GestorAutenticacion');                          e=@('Producto','VarianteProducto');
     act=@(@{a='Proveedor'; d='PantallaMisProductos'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-39 Informar disponibilidad y plazo de abastecimiento'; f='PantallaAbastecimiento'; c=@('GestorAbastecimiento','GestorConsolidado','GestorInventario','GestorAutenticacion'); e=@('Abastecimiento','VarianteProducto','Existencia');
     act=@(@{a='Proveedor'; d='PantallaAbastecimiento'; r='OPERA_DESDE'}, @{a='Encargado de Sucursal'; d='PantallaAbastecimiento'; r='RECIBE_DESDE'}) },
  @{ n='2.3 CU-40 Notificar eventos a los usuarios';   f='CanalDeAviso';          c=@('GestorNotificaciones','GestorReservas','GestorPagos','GestorInventario');                    e=@('Notificacion');
     act=@(@{a='Sistema (procesos automaticos)'; d='CanalDeAviso'; r='DISPARA'}) },
  @{ n='2.3 CU-41 Recuperar contraseña';               f='PantallaRecuperacion';  c=@('GestorRecuperacion');                                                                       e=@('Usuario','TokenRecuperacion','SesionToken');
     act=@(@{a='Cliente'; d='PantallaRecuperacion'; r='OPERA_DESDE'}) },
  @{ n='2.3 CU-42 Consultar la bitácora del sistema';  f='PantallaBitacora';      c=@('GestorBitacora','GestorAutenticacion');                                                     e=@('Bitacora','Usuario');
     act=@(@{a='Administrador'; d='PantallaBitacora'; r='OPERA_DESDE'}, @{a='Sistema (procesos automaticos)'; d='GestorBitacora'; r='ALIMENTA_A'}) }
)

# CU-39 tiene dos disparadores, como CU-07 y CU-13 en el 2.2: el Proveedor
# que anuncia y el Encargado que recibe. La guia pide que vayan LOS DOS.
$actor23['Encargado de Sucursal'] = Get-OCrearActor 'Encargado de Sucursal' 'Recibe en su sucursal lo que el Proveedor anuncio. Es el segundo disparador de CU-39.'

# Las uniones actor -- clase, con rol en mayusculas y cardinalidad en los dos
# extremos, igual que el resto del capitulo.
foreach ($caso in $casos) {
    foreach ($u in $caso.act) {
        if (-not $actor23.ContainsKey($u.a)) { throw "Actor no declarado: $($u.a)" }
        if (-not $C.ContainsKey($u.d))       { throw "Destino inexistente para $($u.a): $($u.d)" }
        New-Asociacion $actor23[$u.a] $C[$u.d] $u.r '1' '1'
    }
}
Write-Output 'Actores unidos.'

# Cuatro columnas: actores, frontera, controladores, entidades. Las tres de
# clases son mas anchas que las del Ciclo 2 porque las firmas del Ciclo 3
# llevan mas parametros, y ahora ademas cada parametro se imprime con su
# nombre y su tipo.
$COL_ACT = @{ x=40; ancho=170 }
$COLS = @(
    @{ x=280;  ancho=460 },
    @{ x=820;  ancho=470 },
    @{ x=1370; ancho=470 }
)

$hechos = 0
foreach ($caso in $casos) {
    $ya = BuscarDiagrama $p23 $caso.n
    if ($ya) {
        if (-not $Rehacer) { Write-Output "  $($caso.n) ya existe, no se toca"; continue }
        # Borrar el diagrama NO borra los conectores (regla 5): las
        # asociaciones sobreviven y se vuelven a mostrar solas al reponer las
        # clases en el lienzo.
        #
        # El indice se busca recorriendo: las colecciones COM de EA NO tienen
        # `IndexOf` ---devuelven `System.__ComObject` y el metodo no existe---
        # y hay que ir de atras para adelante para que borrar no corra los
        # indices que faltan visitar.
        $p23.Diagrams.Refresh()
        for ($i = $p23.Diagrams.Count - 1; $i -ge 0; $i--) {
            if ($p23.Diagrams.GetAt($i).Name -eq $caso.n) { $p23.Diagrams.DeleteAt($i, $false) }
        }
        $p23.Diagrams.Refresh()
    }

    $d = $p23.Diagrams.AddNew($caso.n, 'Logical')
    [void]$d.Update(); $p23.Diagrams.Refresh()

    # Los actores primero, en su propia columna a la izquierda de la frontera.
    $t = -40
    foreach ($u in $caso.act) {
        Poner $d $actor23[$u.a] $COL_ACT.x $t $COL_ACT.ancho 90
        $t = $t - 150
    }

    $grupos = @(@($caso.f), $caso.c, $caso.e)
    for ($k = 0; $k -lt 3; $k++) {
        $t = -40
        foreach ($nombre in $grupos[$k]) {
            if (-not $C.ContainsKey($nombre)) { throw "No existe la clase '$nombre' de $($caso.n)" }
            $h = Alto $nombre
            Poner $d $C[$nombre] $COLS[$k].x $t $COLS[$k].ancho $h
            $t = $t - $h - 60   # 60 de aire entre cajas de la misma columna
        }
    }

    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    $hechos++
    Write-Output ("  {0,-58} {1} elementos, {2,2} asociaciones" -f $caso.n, $d.DiagramObjects.Count, $d.DiagramLinks.Count)
}

Write-Output "Diagramas dibujados: $hechos de $($casos.Count)"

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
