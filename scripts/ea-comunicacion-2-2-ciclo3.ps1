# =========================================================================
# CAP. 2 - 2.2 Analizar Casos de Uso. CICLO 3: los VEINTE diagramas de
# comunicacion de CU-12, CU-20, CU-21 y CU-26 a CU-42.
#
# Aditivo: un diagrama que ya existe no se toca. Las clases de analisis se
# comparten con los Ciclos 1 y 2 --- GestorAutenticacion es la misma, y
# GestorInventario es el mismo que estreno CU-13 --- y viven en
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
# ---- LOS NOMBRES DE LOS MENSAJES SON LOS DEL CODIGO ----------------------
# No se inventan. `crear_pedido(datos)`, `confirmar_pago(cuerpo, firma)`,
# `descontar_por_venta(...)` son las funciones que existen. Un diagrama de
# analisis con operaciones imaginarias se lee bien y no sirve para nada:
# quien lo use para entender el sistema no va a encontrar nada de eso.
#
# Las CLASES si son conceptuales --- `GestorMostrador` no es un archivo ---
# porque el modelo de analisis es anterior al diseno. Cada una dice en sus
# notas a que modulo corresponde.
# =========================================================================

$ErrorActionPreference = 'Stop'
$modelo = 'D:\UNI\Si2\PRIMER_PARCIAL\docs\diagramas\VioletBoutique.eapx'

$ea = New-Object -ComObject EA.Repository
if (-not $ea.OpenFile($modelo)) { throw "No se pudo abrir $modelo" }

# ---------------- utilidades ----------------
# Las mismas que el generador del Ciclo 2, por el mismo motivo: cada generador
# se corre solo y un archivo compartido obligaria a dot-sourcing relativo.

$indice = @{}

function Filas($sql) {
    $xml = $ea.SQLQuery($sql)
    $out = @()
    if ($xml) {
        $doc = New-Object System.Xml.XmlDocument
        $doc.LoadXml($xml)
        foreach ($f in $doc.SelectNodes('//Row')) { $out += $f }
    }
    return $out
}

function Get-OCrearPaqueteModelo($padre, $nombre) {
    foreach ($p in $padre.Packages) { if ($p.Name -eq $nombre) { return $p } }
    $p = $padre.Packages.AddNew($nombre, 'Package'); [void]$p.Update()
    $padre.Packages.Refresh(); return $p
}

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
    throw "No se encontro el actor '$nombre'. Corre antes ea-cu-ciclo3.ps1: los actores nuevos de este ciclo --- Cajero, Proveedor, Pasarela de Pago, Servicio de IA --- los crea ese generador."
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

# Descripciones de las clases NUEVAS del Ciclo 3. Las de los ciclos anteriores
# ya estan y Get-OCrearClase las encuentra por nombre: no se vuelven a crear.
$desc = @{
    # --- frontera ---
    'PantallaPromociones'    = 'Area del Administrador: alta, edicion y encendido de promociones. Distingue "activa" de "vigente", que no es lo mismo.'
    'PantallaFavoritos'      = 'Lista de favoritos del Cliente, y el corazon que se pulsa desde la vitrina y la ficha.'
    'PantallaVestidor'       = 'Pantalla movil del vestidor virtual: camara, deteccion de pose y superposicion de la prenda. En la web solo anuncia y remite a la app.'
    'PantallaCarrito'        = 'El carrito del Cliente: lineas, cantidades y total ya con las promociones aplicadas.'
    'PantallaCheckout'       = 'Confirmacion del pedido: modalidad de entrega, destino y salida hacia la pasarela.'
    'WebhookPasarela'        = 'Frontera SIN persona: el endpoint que recibe la notificacion firmada de la pasarela. No exige token --- lo que autoriza es la firma.'
    'PantallaCompras'        = 'Historial del Cliente y descarga del comprobante en PDF.'
    'PantallaTurno'          = 'Una sola pantalla con dos caras: abrir la caja o cerrarla con el arqueo. El Cajero nunca esta en las dos a la vez.'
    'PantallaVenta'          = 'Punto de venta: busqueda de prendas, ticket, metodo de cobro y vuelto. Tambien carga una reserva ya atendida.'
    'PantallaDevolucion'     = 'Busqueda de la venta y marcado de lo que vuelve, con el aviso de si el dinero sale del cajon.'
    'PantallaParaVos'        = 'Las prendas que el sistema sugiere al Cliente.'
    'PantallaAsistente'      = 'SIN CONSTRUIR. Conversacion en lenguaje natural sobre el catalogo, los pedidos y las reservas.'
    'PantallaReportePorVoz'  = 'Dictado del pedido de un reporte, con la confirmacion de lo que el sistema entendio ANTES de generar.'
    'PantallaTablero'        = 'Los siete indicadores del negocio, con sus graficos.'
    'PantallaReportes'       = 'Los seis reportes de gestion, sus filtros y la descarga en PDF y Excel.'
    'PantallaMisProductos'   = 'Area del Proveedor: los productos que abastece, acotados a los suyos.'
    'PantallaAbastecimiento' = 'Area del Proveedor: que puede traer y en que plazo.'
    'CanalDeAviso'           = 'SIN CONSTRUIR. Frontera de salida de CU-40: el correo y la bandeja dentro del sistema. No la abre una persona --- es el sistema el que escribe en ella.'
    'PantallaRecuperacion'   = 'Pedir el enlace y fijar la contrasena nueva. Se usa SIN sesion, que es su razon de ser.'
    'PantallaBitacora'       = 'Consulta de la bitacora del sistema, con sus filtros.'
    # --- control ---
    'GestorPromociones'      = 'Coordina CU-12. Cuando dos promociones alcanzan la misma prenda decide cual gana: la MAYOR, y a igualdad la mas especifica. Nunca las suma. Es la costura que consumen la vitrina, el carrito, el pedido y el mostrador.'
    'GestorFavoritos'        = 'Coordina CU-20. Marcar no aparta inventario ni compromete una compra.'
    'GestorVestidor'         = 'Coordina CU-21. El probado asistido por IA es opcional: sin clave configurada la superposicion directa sigue funcionando.'
    'GestorCarrito'          = 'Coordina CU-26. El carrito NO guarda precios ni descuentos: los lee en vivo, porque es una intencion y no un compromiso.'
    'GestorPedidos'          = 'Coordina CU-27. Pide la sesion de pago ANTES de bloquear inventario, para no sostener bloqueos durante una llamada de red a un tercero.'
    'GestorPagos'            = 'Coordina CU-27 y CU-28. El estado del pago lo determina UNICAMENTE la notificacion firmada (decision D5): la vuelta del navegador no prueba nada.'
    'GestorHistorial'        = 'Coordina CU-29. Emite el comprobante la primera vez que alguien lo pide, de forma idempotente.'
    'GestorCaja'             = 'Coordina CU-30. Guarda los DOS numeros del arqueo --- lo esperado y lo contado --- porque un descuadre sin los dos no se puede auditar.'
    'GestorMostrador'        = 'Coordina CU-31. La venta nace PAGADA. Si viene de una reserva NO descuenta inventario: CU-24 ya lo desconto cuando el cliente se llevo la prenda del probador.'
    'GestorDevoluciones'     = 'Coordina CU-32. El monto que registra es lo que sale del CAJON, no lo que vale la prenda: con tarjeta va en cero, porque esa plata nunca entro.'
    'GestorRecomendaciones'  = 'Coordina CU-33. Sin el Servicio de IA recomienda por popularidad: la pantalla nunca queda vacia por un tercero.'
    'GestorAsistente'        = 'SIN CONSTRUIR. Coordinaria CU-34: interpreta la consulta y la responde con los datos reales, acotados al propio cliente.'
    'GestorReportePorVoz'    = 'Coordina CU-35. Interpreta el dictado y DELEGA la generacion en GestorReportes: no hay dos generadores de reportes.'
    'GestorTablero'          = 'Coordina CU-36. "Vendido hoy" es siempre hoy, con el corte a la medianoche boliviana, aunque se consulte otro periodo.'
    'GestorReportes'         = 'Coordina CU-37. Cada reporte admite sus propios filtros, que no son los mismos para todos.'
    'GestorCatalogoProveedor'= 'Coordina CU-38. Acota al proveedor de la sesion: lo que no es suyo no existe.'
    'GestorAbastecimiento'   = 'Coordina CU-39. Lo anunciado NO suma existencia: alimenta el estado "proximo a ingresar" y nada mas.'
    'GestorNotificaciones'   = 'SIN CONSTRUIR. Coordinaria CU-40: decide a quien le corresponde enterarse y registra el aviso. Perder el correo no puede significar perder el aviso.'
    'GestorRecuperacion'     = 'Coordina CU-41. El enlace es de un solo uso y al usarlo revoca las sesiones abiertas.'
    'GestorBitacora'         = 'Coordina CU-42. Escribe cada asiento y nunca lo edita: la bitacora es inmutable.'
    # --- entidad ---
    'Promocion'              = 'Tabla promocion. Guarda el ALCANCE --- un producto, una categoria o una temporada --- y no la lista de variantes que hoy caen dentro: asi un producto nuevo entra ya con el descuento puesto.'
    'Favorito'               = 'Tabla favorito. Un cliente y un producto. No aparta nada.'
    'MedidaCliente'          = 'Tabla medida_cliente. Las medidas que el Cliente cargo, para ajustar la escala de la prenda en el vestidor.'
    'Carrito'                = 'Tabla carrito. Uno por cliente, sobrevive a cerrar el navegador.'
    'CarritoDetalle'         = 'Tabla carrito_detalle. Una variante y su cantidad. NO guarda precio: el carrito es una intencion.'
    'Venta'                  = 'Tabla venta. UN concepto para los dos canales (decision D2): el pedido web nace PENDIENTE_PAGO y la venta de mostrador nace PAGADA. No hay tabla pedido aparte.'
    'DetalleVenta'           = 'Tabla detalle_venta. Inmutable, con el precio Y el descuento CONGELADOS: una venta de marzo tiene que seguir sumando lo que sumo en marzo.'
    'Pago'                   = 'Tabla pago. El intento de cobro y su estado, que solo mueve la notificacion firmada.'
    'TransaccionPasarela'    = 'Tabla transaccion_pasarela. Cada notificacion recibida, con su identificador unico: es lo que hace que un reintento de la pasarela no cobre dos veces.'
    'Comprobante'            = 'Tabla comprobante. Uno por venta, y no se edita: reimprimir no es reemitir.'
    'Caja'                   = 'Tabla caja. Un punto de cobro fisico de una sucursal. Se da de alta una vez y se desactiva; no se borra, porque los turnos viejos la siguen nombrando.'
    'TurnoCaja'              = 'Tabla turno_caja. Una jornada de cobro. Guarda el monto esperado y el contado por separado: la diferencia ES el arqueo.'
    'Devolucion'             = 'Tabla devolucion. Cuelga de un turno porque el dinero sale de una caja concreta, y sin eso el arqueo no cerraria.'
    'DetalleDevolucion'      = 'Tabla detalle_devolucion. Que variante vuelve y cuantas unidades.'
    'Recomendacion'          = 'Tabla recomendacion. Lo que el sistema sugirio y cuando, para no recalcularlo en cada visita.'
    'Abastecimiento'         = 'Tabla abastecimiento. Lo que un proveedor anuncia que puede traer y en que plazo.'
    'Bitacora'               = 'Tabla bitacora. Asiento inmutable: usuario, rol, accion, recurso, fecha y resultado. Tambien los intentos de acceso fallidos.'
    'TokenRecuperacion'      = 'Tabla token_recuperacion. De un solo uso y con vencimiento.'
    'Notificacion'           = 'SIN CONSTRUIR. Guardaria el aviso con su destinatario, su hecho y si se entrego.'
}

# ---------------- los veinte diagramas ----------------
#
# 'g' es el grupo del mensaje; el orden dentro del grupo lo da el orden de
# declaracion. Los actores se referencian con prefijo "A:" porque el actor
# Cliente y la entidad Cliente son elementos distintos con el mismo nombre.

$casos = @(

  @{ n='2.2 CU-12 Gestionar promociones'
     actores=@('Administrador'); boundary='PantallaPromociones'
     controles=@('GestorPromociones','GestorCarrito','GestorAutenticacion')
     entidades=@('Promocion','Producto','VarianteProducto')
     grupos='Grupo 1: alta de una promocion (pasos 1 a 6).   Grupo 2: aplicarla --- es lo que la vuelve una funcion y no una tabla ---; cuando dos alcanzan la misma prenda gana la MAYOR, nunca se suman.   Grupo 3: flujo alternativo 8a, apagarla; deja de descontar en el acto y no se borra.   Grupo 4: excepciones E1 a E4.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaPromociones';m='crearPromocion(datos)'},
       @{g=1;d='PantallaPromociones';a='GestorPromociones';m='crear(datos)'},
       @{g=1;d='GestorPromociones';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorPromociones';a='Promocion';m='existe_nombre(nombre)'},
       @{g=1;d='GestorPromociones';a='Producto';m='producto_existe(objetivo_id)'},
       @{g=1;d='GestorPromociones';a='Promocion';m='agregar(promocion)'},
       @{g=1;d='GestorPromociones';a='PantallaPromociones';m='obtener(promocion_id)'},
       @{g=2;d='GestorCarrito';a='GestorPromociones';m='descuentos_por_variante(precios)'},
       @{g=2;d='GestorPromociones';a='GestorPromociones';m='_hoy()'},
       @{g=2;d='GestorPromociones';a='Promocion';m='descuentos_de_variantes(variante_ids, hoy)'},
       @{g=2;d='GestorPromociones';a='VarianteProducto';m='linaje_de_categorias()'},
       @{g=2;d='GestorPromociones';a='GestorPromociones';m='_elegir(candidatas)'},
       @{g=2;d='GestorPromociones';a='GestorPromociones';m='_redondear(monto)'},
       @{g=3;d='A:Administrador';a='PantallaPromociones';m='cambiarEstado(id, activa)'},
       @{g=3;d='PantallaPromociones';a='GestorPromociones';m='cambiar_estado(promocion_id, datos)'},
       @{g=4;d='GestorPromociones';a='PantallaPromociones';m='NombreDuplicado(nombre)'},
       @{g=4;d='GestorPromociones';a='PantallaPromociones';m='ObjetivoInexistente(alcance, id)'},
       @{g=4;d='GestorPromociones';a='PantallaPromociones';m='VigenciaInvalida()'}
     )}

  @{ n='2.2 CU-20 Gestionar favoritos'
     actores=@('Cliente'); boundary='PantallaFavoritos'
     controles=@('GestorFavoritos','GestorVitrina','GestorAutenticacion')
     entidades=@('Favorito','Producto')
     grupos='Grupo 1: marcar y ver la lista (pasos 1 a 4).   Grupo 2: flujo alternativo 2a, el mismo boton desmarca.   Grupo 3: flujos alternativos 4a y 4b, lista vacia y prenda que dejo de ofrecerse.   Grupo 4: excepciones E1 y E2.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaFavoritos';m='marcarFavorito(producto_id)'},
       @{g=1;d='PantallaFavoritos';a='GestorFavoritos';m='marcar(usuario_id, producto_id)'},
       @{g=1;d='GestorFavoritos';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorFavoritos';a='Producto';m='es_ofrecible(producto_id)'},
       @{g=1;d='GestorFavoritos';a='Favorito';m='agregar(cliente_id, producto_id)'},
       @{g=1;d='A:Cliente';a='PantallaFavoritos';m='verFavoritos()'},
       @{g=1;d='PantallaFavoritos';a='GestorFavoritos';m='listar(usuario_id)'},
       @{g=1;d='GestorFavoritos';a='GestorVitrina';m='_tarjetas(productos)'},
       @{g=2;d='PantallaFavoritos';a='GestorFavoritos';m='desmarcar(usuario_id, producto_id)'},
       @{g=3;d='GestorFavoritos';a='PantallaFavoritos';m='listaVacia()'},
       @{g=4;d='GestorFavoritos';a='PantallaFavoritos';m='PrendaNoOfrecible()'}
     )}

  @{ n='2.2 CU-21 Utilizar vestidor virtual (RA)'
     actores=@('Cliente','Servicio de IA'); boundary='PantallaVestidor'
     controles=@('GestorVestidor','GestorVitrina','GestorAutenticacion')
     entidades=@('VarianteProducto','ImagenProducto','MedidaCliente')
     grupos='Grupo 1: superposicion directa en el telefono (pasos 1 a 5). NO depende de ningun tercero.   Grupo 2: flujo alternativo 4a, probado asistido por IA --- es OPCIONAL.   Grupo 3: flujo alternativo 5a, ajuste de escala con las medidas del Cliente.   Grupo 4: excepciones E1 a E3; la E3 vuelve a la superposicion directa.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaVestidor';m='probarPrenda(variante_id)'},
       @{g=1;d='PantallaVestidor';a='GestorVitrina';m='ficha_de_producto(producto_id)'},
       @{g=1;d='GestorVitrina';a='ImagenProducto';m='rutas_de_vestidor(producto_id)'},
       @{g=1;d='PantallaVestidor';a='PantallaVestidor';m='abrirCamara()'},
       @{g=1;d='PantallaVestidor';a='PantallaVestidor';m='detectarPose()'},
       @{g=1;d='PantallaVestidor';a='PantallaVestidor';m='superponerPrenda()'},
       @{g=2;d='A:Cliente';a='PantallaVestidor';m='pedirProbadoAsistido(foto)'},
       @{g=2;d='PantallaVestidor';a='GestorVestidor';m='probar(foto, variante_id)'},
       @{g=2;d='GestorVestidor';a='GestorVestidor';m='estado()'},
       @{g=2;d='GestorVestidor';a='A:Servicio de IA';m='generarProbado(foto, prenda)'},
       @{g=3;d='GestorVestidor';a='MedidaCliente';m='medidas_de(cliente_id)'},
       @{g=4;d='GestorVestidor';a='PantallaVestidor';m='ProbadorNoConfigurado()'},
       @{g=4;d='GestorVitrina';a='PantallaVestidor';m='sinImagenDeVestidor()'}
     )}

  @{ n='2.2 CU-26 Gestionar carrito de compras'
     actores=@('Cliente'); boundary='PantallaCarrito'
     controles=@('GestorCarrito','GestorPromociones','GestorAutenticacion')
     entidades=@('Carrito','CarritoDetalle','VarianteProducto','Existencia')
     grupos='Grupo 1: agregar y ver el carrito (pasos 1 a 4). El precio y el descuento se leen EN VIVO: el carrito no guarda ninguno de los dos.   Grupo 2: cambiar cantidad y quitar.   Grupo 3: flujo alternativo, prenda que dejo de ofrecerse --- se muestra apagada y no se borra sola.   Grupo 4: excepciones.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaCarrito';m='agregarAlCarrito(variante_id, cantidad)'},
       @{g=1;d='PantallaCarrito';a='GestorCarrito';m='agregar(usuario_id, datos)'},
       @{g=1;d='GestorCarrito';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorCarrito';a='Carrito';m='obtener_carrito(cliente_id)'},
       @{g=1;d='GestorCarrito';a='CarritoDetalle';m='agregar_linea(carrito_id, variante_id, cantidad)'},
       @{g=1;d='A:Cliente';a='PantallaCarrito';m='verCarrito()'},
       @{g=1;d='PantallaCarrito';a='GestorCarrito';m='ver_carrito(usuario_id)'},
       @{g=1;d='GestorCarrito';a='CarritoDetalle';m='lineas_resueltas(carrito_id)'},
       @{g=1;d='GestorCarrito';a='GestorPromociones';m='descuentos_por_variante(precios)'},
       @{g=1;d='GestorCarrito';a='Existencia';m='stock_de_variantes(variante_ids)'},
       @{g=1;d='GestorCarrito';a='PantallaCarrito';m='_armar_carrito(carrito_id)'},
       @{g=2;d='PantallaCarrito';a='GestorCarrito';m='cambiar_cantidad(usuario_id, variante_id, datos)'},
       @{g=2;d='PantallaCarrito';a='GestorCarrito';m='quitar(usuario_id, variante_id)'},
       @{g=3;d='GestorCarrito';a='PantallaCarrito';m='lineaNoDisponible()'},
       @{g=4;d='GestorCarrito';a='PantallaCarrito';m='CantidadFueraDeRango()'}
     )}

  @{ n='2.2 CU-27 Realizar pedido y pagar en línea'
     actores=@('Cliente','Pasarela de Pago'); boundary='PantallaCheckout'
     controles=@('GestorPedidos','GestorPagos','GestorInventario','GestorPromociones','GestorAutenticacion')
     entidades=@('Venta','DetalleVenta','Pago','Existencia')
     grupos='Grupo 1: confirmar el pedido (pasos 2 a 5). La sesion de pago se pide ANTES de bloquear inventario: al reves, dos clientes comprando la misma prenda se serializarian detras del tiempo de respuesta de Stripe.   Grupo 2: el precio y el descuento se CONGELAN aca.   Grupo 3: flujos alternativos, retiro contra envio.   Grupo 4: excepciones --- carrito vacio, stock insuficiente y precio cambiado.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaCheckout';m='confirmarPedido(modalidad, destino, total_esperado)'},
       @{g=1;d='PantallaCheckout';a='GestorPedidos';m='crear_pedido(usuario_id, datos)'},
       @{g=1;d='GestorPedidos';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorPedidos';a='Venta';m='bloquear_cliente(cliente_id)'},
       @{g=1;d='GestorPedidos';a='GestorPromociones';m='descuentos_por_variante(precios)'},
       @{g=1;d='GestorPedidos';a='GestorPedidos';m='_cobertura(lineas)'},
       @{g=1;d='GestorPedidos';a='GestorPagos';m='iniciar_cobro(venta_id, referencia, total, lineas)'},
       @{g=1;d='GestorPagos';a='A:Pasarela de Pago';m='crear_sesion(solicitud)'},
       @{g=1;d='GestorPagos';a='Pago';m='agregar_pago(venta_id, INICIADO)'},
       @{g=1;d='GestorPedidos';a='Venta';m='agregar_venta(codigo, PENDIENTE_PAGO)'},
       @{g=2;d='GestorPedidos';a='DetalleVenta';m='agregar_detalle(precio_unitario, descuento_unitario)'},
       @{g=2;d='GestorPedidos';a='GestorInventario';m='apartar_para_reserva(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorInventario';a='Existencia';m='mover_a_reservada(existencia, cantidad)'},
       @{g=3;d='GestorPedidos';a='GestorPedidos';m='_elegir_sucursal_de_envio(completas, ciudad_destino)'},
       @{g=4;d='GestorPedidos';a='PantallaCheckout';m='PrecioCambiado(esperado, actual)'},
       @{g=4;d='GestorPedidos';a='PantallaCheckout';m='YaTienePedidoPendiente(codigo)'},
       @{g=4;d='GestorInventario';a='PantallaCheckout';m='StockInsuficiente(disponible, solicitado)'}
     )}

  @{ n='2.2 CU-28 Confirmar pago del pedido'
     actores=@('Pasarela de Pago'); boundary='WebhookPasarela'
     controles=@('GestorPagos','GestorInventario','GestorCarrito')
     entidades=@('Pago','Venta','TransaccionPasarela','Existencia')
     grupos='Grupo 1: notificacion valida y aprobada (pasos 1 a 6). NO hay autorizacion por token: lo que autoriza es la FIRMA, y ese es el punto de la decision D5.   Grupo 2: el descuento de inventario, con los DOS movimientos --- LIBERACION y VENTA --- porque el stock ya estaba apartado desde CU-27.   Grupo 3: flujo alternativo, notificacion repetida; la pasarela reintenta y el sistema responde "repetido" sin cobrar dos veces.   Grupo 4: excepciones --- firma invalida y pago rechazado.'
     msj=@(
       @{g=1;d='A:Pasarela de Pago';a='WebhookPasarela';m='notificar(cuerpo, firma)'},
       @{g=1;d='WebhookPasarela';a='GestorPagos';m='confirmar_pago(cuerpo, firma)'},
       @{g=1;d='GestorPagos';a='GestorPagos';m='interpretar_webhook(cuerpo, firma)'},
       @{g=1;d='GestorPagos';a='TransaccionPasarela';m='ya_procesada(identificador)'},
       @{g=1;d='GestorPagos';a='Pago';m='obtener_por_referencia(referencia)'},
       @{g=1;d='GestorPagos';a='GestorPagos';m='_aplicar_cobro(pago, evento)'},
       @{g=1;d='GestorPagos';a='Pago';m='marcar_aprobado(pago)'},
       @{g=1;d='GestorPagos';a='Venta';m='marcar_pagada(venta)'},
       @{g=2;d='GestorPagos';a='GestorInventario';m='liberar_de_reserva(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorPagos';a='GestorInventario';m='descontar_por_venta(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorInventario';a='Existencia';m='_aplicar_movimiento(existencia, VENTA, -cantidad)'},
       @{g=2;d='GestorPagos';a='GestorCarrito';m='vaciar_carrito(cliente_id)'},
       @{g=3;d='GestorPagos';a='WebhookPasarela';m='resultado("repetido")'},
       @{g=4;d='GestorPagos';a='WebhookPasarela';m='FirmaInvalida()'},
       @{g=4;d='GestorPagos';a='WebhookPasarela';m='resultado("rechazado")'}
     )}

  @{ n='2.2 CU-29 Consultar historial de compras'
     actores=@('Cliente'); boundary='PantallaCompras'
     controles=@('GestorHistorial','GestorAutenticacion')
     entidades=@('Venta','DetalleVenta','Comprobante')
     grupos='Grupo 1: ver el historial (pasos 1 a 3).   Grupo 2: descargar el comprobante. La PRIMERA descarga lo EMITE, de forma idempotente por el UNIQUE sobre venta_id.   Grupo 3: excepciones --- compra ajena (404, nunca 403) y compra sin comprobante posible.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaCompras';m='verCompras(pagina)'},
       @{g=1;d='PantallaCompras';a='GestorHistorial';m='listar_compras(usuario_id, pagina, tamano)'},
       @{g=1;d='GestorHistorial';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorHistorial';a='Venta';m='pagina_de_compras(cliente_id, pagina)'},
       @{g=1;d='GestorHistorial';a='DetalleVenta';m='lineas_de_pedido(venta_id)'},
       @{g=2;d='A:Cliente';a='PantallaCompras';m='descargarComprobante(codigo)'},
       @{g=2;d='PantallaCompras';a='GestorHistorial';m='comprobante_en_pdf(usuario_id, codigo)'},
       @{g=2;d='GestorHistorial';a='Comprobante';m='obtener_comprobante(venta_id)'},
       @{g=2;d='GestorHistorial';a='Comprobante';m='asegurar_comprobante(venta)'},
       @{g=2;d='GestorHistorial';a='GestorHistorial';m='_dibujar_pdf(comprobante, pedido)'},
       @{g=3;d='GestorHistorial';a='PantallaCompras';m='PedidoInexistente(codigo)'},
       @{g=3;d='GestorHistorial';a='PantallaCompras';m='SinComprobante(estado)'}
     )}

  @{ n='2.2 CU-30 Abrir y cerrar caja'
     actores=@('Cajero'); boundary='PantallaTurno'
     controles=@('GestorCaja','GestorAutenticacion')
     entidades=@('Caja','TurnoCaja','Venta','Devolucion')
     grupos='Grupo 1: abrir el turno (pasos 1 a 4). El bloqueo de la CAJA serializa las aperturas: sin el, dos simultaneas revientan con un error de integridad que el cajero lee como "error del sistema".   Grupo 2: el arqueo al cerrar (pasos 6 a 8). Se guardan los DOS numeros.   Grupo 3: flujo alternativo 8a, cierre con descuadre --- NO se rechaza: es justamente lo que hay que registrar.   Grupo 4: excepciones E1 a E3.'
     msj=@(
       @{g=1;d='A:Cajero';a='PantallaTurno';m='abrirTurno(caja_id, monto_apertura)'},
       @{g=1;d='PantallaTurno';a='GestorCaja';m='mi_turno(usuario_id)'},
       @{g=1;d='PantallaTurno';a='GestorCaja';m='cajas_disponibles(sucursal_id)'},
       @{g=1;d='GestorCaja';a='GestorAutenticacion';m='autorizar("CAJERO","ENCARGADO")'},
       @{g=1;d='GestorCaja';a='Caja';m='bloquear_caja(caja_id)'},
       @{g=1;d='GestorCaja';a='TurnoCaja';m='turno_abierto_de_caja(caja_id)'},
       @{g=1;d='GestorCaja';a='TurnoCaja';m='abrir(caja_id, usuario_id, monto_apertura)'},
       @{g=2;d='A:Cajero';a='PantallaTurno';m='cerrarTurno(turno_id, monto_cierre)'},
       @{g=2;d='PantallaTurno';a='GestorCaja';m='cerrar(turno_id, usuario_id, monto_cierre)'},
       @{g=2;d='GestorCaja';a='Venta';m='efectivo_cobrado(turno_id)'},
       @{g=2;d='GestorCaja';a='Devolucion';m='devoluciones_del_turno(turno_id)'},
       @{g=2;d='GestorCaja';a='GestorCaja';m='_esperado(turno)'},
       @{g=2;d='GestorCaja';a='TurnoCaja';m='guardar_arqueo(esperado, contado)'},
       @{g=3;d='GestorCaja';a='PantallaTurno';m='arqueoConDiferencia(diferencia)'},
       @{g=4;d='GestorCaja';a='PantallaTurno';m='ErrorDeCaja("esa caja ya esta abierta")'},
       @{g=4;d='GestorCaja';a='PantallaTurno';m='ErrorDeCaja("cierra quien abrio")'}
     )}

  @{ n='2.2 CU-31 Registrar venta presencial'
     actores=@('Cajero'); boundary='PantallaVenta'
     controles=@('GestorMostrador','GestorCaja','GestorInventario','GestorPromociones','GestorHistorial')
     entidades=@('Venta','DetalleVenta','Comprobante','Existencia')
     grupos='Grupo 1: cobrar buscando las prendas (pasos 1 a 8). La venta nace PAGADA y todo ocurre en UNA transaccion: venta, lineas, descuento e comprobante.   Grupo 2: flujo alternativo 2a, cobrar una reserva ya atendida --- el puente de la decision D2.   Grupo 3: flujo alternativo 7a, la venta viene de una reserva y NO se toca el inventario: CU-24 ya lo descontó.   Grupo 4: excepciones E1 a E6.'
     msj=@(
       @{g=1;d='A:Cajero';a='PantallaVenta';m='buscarPrendas(busqueda)'},
       @{g=1;d='PantallaVenta';a='GestorMostrador';m='buscar_prendas(usuario_id, busqueda)'},
       @{g=1;d='GestorMostrador';a='GestorCaja';m='turno_abierto_de_usuario(usuario_id)'},
       @{g=1;d='GestorMostrador';a='Existencia';m='prendas_vendibles(sucursal_id, busqueda)'},
       @{g=1;d='GestorMostrador';a='GestorPromociones';m='descuentos_por_variante(precios)'},
       @{g=1;d='A:Cajero';a='PantallaVenta';m='cobrar(metodo_pago, lineas, total_esperado)'},
       @{g=1;d='PantallaVenta';a='GestorMostrador';m='registrar_venta(usuario_id, datos)'},
       @{g=1;d='GestorMostrador';a='Venta';m='agregar_venta_presencial(codigo, PAGADA, turno_caja_id)'},
       @{g=1;d='GestorMostrador';a='DetalleVenta';m='agregar_detalle(precio_unitario, descuento_unitario)'},
       @{g=1;d='GestorMostrador';a='GestorInventario';m='descontar_por_venta(variante_id, sucursal_id, cantidad)'},
       @{g=1;d='GestorInventario';a='Existencia';m='_aplicar_movimiento(existencia, VENTA, -cantidad)'},
       @{g=1;d='GestorMostrador';a='GestorHistorial';m='asegurar_comprobante(venta)'},
       @{g=1;d='GestorHistorial';a='Comprobante';m='agregar_comprobante(venta_id, RECIBO)'},
       @{g=2;d='PantallaVenta';a='GestorMostrador';m='reservas_por_cobrar(usuario_id)'},
       @{g=2;d='GestorMostrador';a='Venta';m='reserva_cobrable(reserva_id, sucursal_id)'},
       @{g=3;d='GestorMostrador';a='GestorMostrador';m='_descontar(desde_reserva=True) -> no hace nada'},
       @{g=4;d='GestorMostrador';a='PantallaVenta';m='SinTurnoAbierto()'},
       @{g=4;d='GestorMostrador';a='PantallaVenta';m='SinStock(prenda, disponible, solicitado)'},
       @{g=4;d='GestorMostrador';a='PantallaVenta';m='ConflictoDePrecio(esperado, actual)'}
     )}

  @{ n='2.2 CU-32 Registrar devolución'
     actores=@('Cajero'); boundary='PantallaDevolucion'
     controles=@('GestorDevoluciones','GestorCaja','GestorInventario')
     entidades=@('Venta','DetalleVenta','Devolucion','DetalleDevolucion','Existencia')
     grupos='Grupo 1: buscar la venta y ver lo que QUEDA por devolver (pasos 1 y 2).   Grupo 2: registrarla (pasos 3 a 7). El bloqueo de la VENTA serializa: sin el, dos devoluciones simultaneas devuelven las dos la ultima unidad.   Grupo 3: flujo alternativo 2a, cobrada con tarjeta --- la prenda vuelve igual pero el monto va en CERO, porque esa plata nunca entro al cajon.   Grupo 4: excepciones E1 a E5.'
     msj=@(
       @{g=1;d='A:Cajero';a='PantallaDevolucion';m='buscarVenta(codigo)'},
       @{g=1;d='PantallaDevolucion';a='GestorDevoluciones';m='buscar_venta(usuario_id, codigo)'},
       @{g=1;d='GestorDevoluciones';a='GestorCaja';m='turno_abierto_de_usuario(usuario_id)'},
       @{g=1;d='GestorDevoluciones';a='Venta';m='venta_devolvible(codigo, sucursal_id)'},
       @{g=1;d='GestorDevoluciones';a='DetalleVenta';m='lineas_vendidas(venta_id)'},
       @{g=1;d='GestorDevoluciones';a='DetalleDevolucion';m='ya_devuelto(venta_id)'},
       @{g=2;d='A:Cajero';a='PantallaDevolucion';m='registrarDevolucion(motivo, lineas)'},
       @{g=2;d='PantallaDevolucion';a='GestorDevoluciones';m='registrar(usuario_id, datos)'},
       @{g=2;d='GestorDevoluciones';a='Venta';m='bloquear_venta(venta_id)'},
       @{g=2;d='GestorDevoluciones';a='Devolucion';m='agregar_devolucion(venta_id, turno_caja_id, motivo, monto)'},
       @{g=2;d='GestorDevoluciones';a='DetalleDevolucion';m='agregar_detalle(devolucion_id, variante_id, cantidad)'},
       @{g=2;d='GestorDevoluciones';a='GestorInventario';m='reingresar_por_devolucion(variante_id, sucursal_id, cantidad)'},
       @{g=2;d='GestorInventario';a='Existencia';m='_aplicar_movimiento(existencia, DEVOLUCION, +cantidad)'},
       @{g=3;d='GestorDevoluciones';a='GestorDevoluciones';m='_sale_del_cajon(venta) -> False'},
       @{g=4;d='GestorDevoluciones';a='PantallaDevolucion';m='VentaNoDevolvible(codigo)'},
       @{g=4;d='GestorDevoluciones';a='PantallaDevolucion';m='DevuelveDeMas(prenda, devolvibles, solicitado)'}
     )}

  @{ n='2.2 CU-33 Recibir recomendaciones de prendas'
     actores=@('Cliente','Servicio de IA'); boundary='PantallaParaVos'
     controles=@('GestorRecomendaciones','GestorVitrina','GestorFavoritos','GestorAutenticacion')
     entidades=@('Recomendacion','VarianteProducto','Existencia')
     grupos='Grupo 1: generar la recomendacion (pasos 1 a 5). Las candidatas se filtran por disponibilidad REAL antes de pedirle nada al modelo.   Grupo 2: flujo alternativo 5a, recomendacion vigente --- se reutiliza en vez de volver a llamar.   Grupo 3: flujo alternativo 5b, comprar o marcar un favorito la invalida.   Grupo 4: excepciones --- sin Servicio de IA recomienda por popularidad; la pantalla NUNCA queda vacia por un tercero.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaParaVos';m='verRecomendaciones()'},
       @{g=1;d='PantallaParaVos';a='GestorRecomendaciones';m='recomendaciones(usuario_id)'},
       @{g=1;d='GestorRecomendaciones';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorRecomendaciones';a='GestorRecomendaciones';m='_perfil(cliente)'},
       @{g=1;d='GestorRecomendaciones';a='Existencia';m='_candidatas(cliente, categoria_ids)'},
       @{g=1;d='GestorRecomendaciones';a='A:Servicio de IA';m='ordenar(candidatas, perfil)'},
       @{g=1;d='GestorRecomendaciones';a='Recomendacion';m='guardar(cliente_id, prendas, generada_en)'},
       @{g=1;d='GestorRecomendaciones';a='GestorVitrina';m='_tarjetas(productos)'},
       @{g=2;d='GestorRecomendaciones';a='GestorRecomendaciones';m='_vencida(generada_en)'},
       @{g=3;d='GestorFavoritos';a='GestorRecomendaciones';m='invalidar(cliente_id)'},
       @{g=4;d='GestorRecomendaciones';a='GestorRecomendaciones';m='_por_popularidad(candidatas)'}
     )}

  @{ n='2.2 CU-34 Conversar con el asistente virtual'
     actores=@('Cliente','Servicio de IA'); boundary='PantallaAsistente'
     controles=@('GestorAsistente','GestorVitrina','GestorAutenticacion')
     entidades=@('Venta','Reserva')
     grupos='SIN CONSTRUIR: este diagrama describe lo acordado, no lo que existe.   Grupo 1: consulta y respuesta (pasos 1 a 5). Los datos se consultan ACOTADOS al propio cliente.   Grupo 2: flujo alternativo 4a, la respuesta remite a la pantalla que lo resuelve mejor.   Grupo 3: excepciones --- sin Servicio de IA remite a las pantallas de consulta, y NO inventa una respuesta.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaAsistente';m='preguntar(texto)'},
       @{g=1;d='PantallaAsistente';a='GestorAsistente';m='responder(usuario_id, texto)'},
       @{g=1;d='GestorAsistente';a='GestorAutenticacion';m='autorizar("CLIENTE")'},
       @{g=1;d='GestorAsistente';a='A:Servicio de IA';m='interpretar(texto, catalogo)'},
       @{g=1;d='GestorAsistente';a='Venta';m='mis_pedidos(cliente_id)'},
       @{g=1;d='GestorAsistente';a='Reserva';m='mis_reservas(cliente_id)'},
       @{g=1;d='GestorAsistente';a='GestorVitrina';m='buscar(filtros)'},
       @{g=1;d='GestorAsistente';a='PantallaAsistente';m='respuesta(texto, enlaces)'},
       @{g=2;d='GestorAsistente';a='PantallaAsistente';m='remitirAPantalla(ruta)'},
       @{g=3;d='GestorAsistente';a='PantallaAsistente';m='AsistenteNoConfigurado()'}
     )}

  @{ n='2.2 CU-35 Generar reporte por comando de voz'
     actores=@('Administrador','Servicio de IA'); boundary='PantallaReportePorVoz'
     controles=@('GestorReportePorVoz','GestorReportes','GestorAutenticacion')
     entidades=@('Venta','Existencia')
     grupos='Grupo 1: dictar y generar (pasos 1 a 6). Se MUESTRA lo que el sistema entendio ANTES de generar, no despues.   Grupo 2: la generacion se DELEGA en CU-37 --- no hay dos generadores de reportes.   Grupo 3: flujos alternativos 2a y 5a, escribir en vez de dictar y corregir los filtros a mano.   Grupo 4: excepciones E1 a E3.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaReportePorVoz';m='dictar()'},
       @{g=1;d='PantallaReportePorVoz';a='PantallaReportePorVoz';m='transcribir()'},
       @{g=1;d='PantallaReportePorVoz';a='GestorReportePorVoz';m='interpretar(texto)'},
       @{g=1;d='GestorReportePorVoz';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=1;d='GestorReportePorVoz';a='GestorReportes';m='catalogo_para_el_interprete(es_admin)'},
       @{g=1;d='GestorReportePorVoz';a='A:Servicio de IA';m='interpretar(texto, conocidos, hoy())'},
       @{g=1;d='GestorReportePorVoz';a='PantallaReportePorVoz';m='PedidoEntendidoOut(tipo, filtros)'},
       @{g=2;d='A:Administrador';a='PantallaReportePorVoz';m='confirmarYGenerar()'},
       @{g=2;d='PantallaReportePorVoz';a='GestorReportes';m='generar(tipo, filtros)'},
       @{g=2;d='GestorReportes';a='Venta';m='consultar(periodo, sucursal_id)'},
       @{g=3;d='PantallaReportePorVoz';a='GestorReportePorVoz';m='interpretar(texto_escrito)'},
       @{g=4;d='GestorReportePorVoz';a='PantallaReportePorVoz';m='InterpreteNoConfigurado()'},
       @{g=4;d='GestorReportePorVoz';a='PantallaReportePorVoz';m='noSeEntendio()'}
     )}

  @{ n='2.2 CU-36 Consultar tablero de indicadores'
     actores=@('Administrador'); boundary='PantallaTablero'
     controles=@('GestorTablero','GestorAutenticacion')
     entidades=@('Venta','Reserva','Existencia')
     grupos='Grupo 1: los siete indicadores (pasos 1 a 3).   Grupo 2: flujo alternativo 2a, "vendido hoy" es SIEMPRE hoy con el corte a la medianoche boliviana, aunque se consulte otro periodo.   Grupo 3: flujo alternativo 3a, el Encargado lo ve acotado a su sucursal.   Grupo 4: excepcion E1, periodo invertido.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaTablero';m='verTablero(periodo, sucursal_id)'},
       @{g=1;d='PantallaTablero';a='GestorTablero';m='tablero(desde, hasta, sucursal_id)'},
       @{g=1;d='GestorTablero';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR","ENCARGADO")'},
       @{g=1;d='GestorTablero';a='Venta';m='resumen_de_ventas(desde, hasta, sucursal_id)'},
       @{g=1;d='GestorTablero';a='Venta';m='top_variantes_vendidas(desde, hasta, limite)'},
       @{g=1;d='GestorTablero';a='Reserva';m='resumen_de_reservas(desde, hasta, sucursal_id)'},
       @{g=1;d='GestorTablero';a='Existencia';m='stock_critico(sucursal_id)'},
       @{g=1;d='GestorTablero';a='GestorTablero';m='_dinero(valor)'},
       @{g=2;d='GestorTablero';a='Venta';m='monto_vendido_hoy(sucursal_id)'},
       @{g=2;d='GestorTablero';a='GestorTablero';m='inicio_del_dia()'},
       @{g=3;d='GestorTablero';a='GestorTablero';m='_acotar_a_sucursal(usuario)'},
       @{g=4;d='GestorTablero';a='PantallaTablero';m='ErrorDeReporte("periodo invertido")'}
     )}

  @{ n='2.2 CU-37 Generar reportes de gestión'
     actores=@('Administrador'); boundary='PantallaReportes'
     controles=@('GestorReportes','GestorAutenticacion')
     entidades=@('Venta','Existencia','MovimientoInventario','Reserva')
     grupos='Grupo 1: elegir, filtrar y ver (pasos 1 a 4). Cada reporte admite SUS filtros, que no son los mismos para todos.   Grupo 2: la descarga en PDF y en Excel.   Grupo 3: flujos alternativos 3a y 3b, periodo por omision en dias BOLIVIANOS y acotado a la sucursal del Encargado.   Grupo 4: excepciones E1 y E2; un reporte sin filas se genera igual, porque un archivo vacio y un error se confunden.'
     msj=@(
       @{g=1;d='A:Administrador';a='PantallaReportes';m='elegirReporte(tipo)'},
       @{g=1;d='PantallaReportes';a='GestorReportes';m='opciones_de(filtro)'},
       @{g=1;d='A:Administrador';a='PantallaReportes';m='generar(tipo, filtros)'},
       @{g=1;d='PantallaReportes';a='GestorReportes';m='generar(tipo, filtros)'},
       @{g=1;d='GestorReportes';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR","ENCARGADO")'},
       @{g=1;d='GestorReportes';a='Venta';m='consultar(periodo, sucursal_id)'},
       @{g=1;d='GestorReportes';a='MovimientoInventario';m='consultar(periodo, tipo)'},
       @{g=1;d='GestorReportes';a='GestorReportes';m='_totales(definicion, filas)'},
       @{g=2;d='A:Administrador';a='PantallaReportes';m='descargar(formato)'},
       @{g=2;d='PantallaReportes';a='GestorReportes';m='exportar(reporte, formato)'},
       @{g=2;d='GestorReportes';a='GestorReportes';m='formatear(valor) en hora boliviana'},
       @{g=3;d='GestorReportes';a='GestorReportes';m='_rango(desde, hasta) con hoy() boliviano'},
       @{g=4;d='GestorReportes';a='PantallaReportes';m='ErrorDeReporte("periodo invertido")'}
     )}

  @{ n='2.2 CU-38 Registrar productos del proveedor'
     actores=@('Proveedor'); boundary='PantallaMisProductos'
     controles=@('GestorCatalogoProveedor','GestorProductos','GestorAutenticacion')
     entidades=@('Producto','VarianteProducto')
     grupos='Grupo 1: registrar un producto propio (pasos 1 a 5). NO se publica solo: el Administrador lo revisa antes de que llegue a la vitrina.   Grupo 2: asociarlo a una temporada y una coleccion.   Grupo 3: excepciones --- lo que no es suyo no existe (404, nunca 403).'
     msj=@(
       @{g=1;d='A:Proveedor';a='PantallaMisProductos';m='registrarProducto(datos)'},
       @{g=1;d='PantallaMisProductos';a='GestorCatalogoProveedor';m='crear(usuario_id, datos)'},
       @{g=1;d='GestorCatalogoProveedor';a='GestorAutenticacion';m='autorizar("PROVEEDOR")'},
       @{g=1;d='GestorCatalogoProveedor';a='GestorCatalogoProveedor';m='_proveedor_del_usuario(usuario_id)'},
       @{g=1;d='GestorCatalogoProveedor';a='GestorProductos';m='crear_producto(datos, proveedor_id)'},
       @{g=1;d='GestorProductos';a='Producto';m='agregar_producto(datos)'},
       @{g=2;d='PantallaMisProductos';a='GestorCatalogoProveedor';m='generar_variantes(producto_id, tallas, colores)'},
       @{g=2;d='GestorCatalogoProveedor';a='VarianteProducto';m='agregar_variante(datos)'},
       @{g=3;d='GestorCatalogoProveedor';a='PantallaMisProductos';m='ProductoInexistente()'}
     )}

  @{ n='2.2 CU-39 Informar disponibilidad y plazo de abastecimiento'
     actores=@('Proveedor'); boundary='PantallaAbastecimiento'
     controles=@('GestorAbastecimiento','GestorConsolidado','GestorAutenticacion')
     entidades=@('Abastecimiento','VarianteProducto','Existencia')
     grupos='Grupo 1: anunciar (pasos 1 a 4). Lo anunciado NO suma existencia: alimenta el estado "proximo a ingresar" y nada mas.   Grupo 2: lo anunciado se VE en el inventario consolidado, que es lo que le da sentido.   Grupo 3: flujo alternativo, cancelar un anuncio.   Grupo 4: excepciones --- una variante que no es suya no existe.'
     msj=@(
       @{g=1;d='A:Proveedor';a='PantallaAbastecimiento';m='anunciar(variante_id, cantidad, plazo)'},
       @{g=1;d='PantallaAbastecimiento';a='GestorAbastecimiento';m='anunciar(usuario_id, datos)'},
       @{g=1;d='GestorAbastecimiento';a='GestorAutenticacion';m='autorizar("PROVEEDOR")'},
       @{g=1;d='GestorAbastecimiento';a='VarianteProducto';m='mis_variantes(proveedor_id)'},
       @{g=1;d='GestorAbastecimiento';a='Abastecimiento';m='agregar(variante_id, cantidad, plazo)'},
       @{g=2;d='GestorConsolidado';a='GestorAbastecimiento';m='avisos_de_ingreso(variante_ids)'},
       @{g=2;d='GestorConsolidado';a='Existencia';m='inventario_consolidado(filtros)'},
       @{g=3;d='PantallaAbastecimiento';a='GestorAbastecimiento';m='cancelar(usuario_id, anuncio_id)'},
       @{g=4;d='GestorAbastecimiento';a='PantallaAbastecimiento';m='VarianteAjena()'}
     )}

  @{ n='2.2 CU-40 Notificar eventos a los usuarios'
     actores=@('Sistema (procesos automáticos)'); boundary='CanalDeAviso'
     controles=@('GestorNotificaciones','GestorReservas','GestorPagos','GestorInventario')
     entidades=@('Notificacion','Reserva','Venta','Existencia')
     grupos='SIN CONSTRUIR: este diagrama describe lo acordado, no lo que existe.   Grupo 1: los cuatro disparadores. NO hay autorizacion porque no hay usuario: es el sistema el que avisa.   Grupo 2: registrar y entregar.   Grupo 3: flujo alternativo 3a, varios destinatarios --- una notificacion por cada uno.   Grupo 4: excepcion E1 --- si el correo falla la notificacion QUEDA REGISTRADA igual: perder el correo no puede significar perder el aviso.'
     msj=@(
       @{g=1;d='GestorReservas';a='GestorNotificaciones';m='avisar("reserva creada", reserva)'},
       @{g=1;d='GestorReservas';a='GestorNotificaciones';m='avisar("reserva preparada", reserva)'},
       @{g=1;d='GestorPagos';a='GestorNotificaciones';m='avisar("pedido pagado", venta)'},
       @{g=1;d='GestorInventario';a='GestorNotificaciones';m='avisar("stock bajo", existencia)'},
       @{g=2;d='GestorNotificaciones';a='GestorNotificaciones';m='_destinatarios(hecho)'},
       @{g=2;d='GestorNotificaciones';a='Notificacion';m='registrar(destinatario, hecho)'},
       @{g=2;d='GestorNotificaciones';a='CanalDeAviso';m='enviar(mensaje)'},
       @{g=2;d='A:Sistema (procesos automáticos)';a='CanalDeAviso';m='entregar()'},
       @{g=3;d='GestorNotificaciones';a='Notificacion';m='registrar(otro_destinatario, hecho)'},
       @{g=4;d='CanalDeAviso';a='GestorNotificaciones';m='envioFallido()'},
       @{g=4;d='GestorNotificaciones';a='Notificacion';m='marcar_no_entregada()'}
     )}

  @{ n='2.2 CU-41 Recuperar contraseña'
     actores=@('Cliente'); boundary='PantallaRecuperacion'
     controles=@('GestorRecuperacion','GestorAutenticacion')
     entidades=@('Usuario','TokenRecuperacion','SesionToken')
     grupos='Grupo 1: pedir el enlace (pasos 1 a 3). NO hay autorizacion: se usa SIN sesion, y esa es su razon de ser.   Grupo 2: fijar la contrasena nueva. El enlace es de UN SOLO USO y revoca las sesiones abiertas.   Grupo 3: flujo alternativo, correo inexistente --- se responde IGUAL que si existiera, para no revelar quien tiene cuenta.   Grupo 4: excepciones --- enlace vencido o ya usado.'
     msj=@(
       @{g=1;d='A:Cliente';a='PantallaRecuperacion';m='pedirEnlace(correo)'},
       @{g=1;d='PantallaRecuperacion';a='GestorRecuperacion';m='solicitar_recuperacion(datos)'},
       @{g=1;d='GestorRecuperacion';a='Usuario';m='por_correo(correo)'},
       @{g=1;d='GestorRecuperacion';a='TokenRecuperacion';m='agregar(usuario_id, hash, vence_en)'},
       @{g=1;d='GestorRecuperacion';a='GestorRecuperacion';m='_armar_correo_de_recuperacion(usuario, token)'},
       @{g=2;d='A:Cliente';a='PantallaRecuperacion';m='fijarContrasena(token, nueva)'},
       @{g=2;d='PantallaRecuperacion';a='GestorRecuperacion';m='confirmar_recuperacion(datos)'},
       @{g=2;d='GestorRecuperacion';a='TokenRecuperacion';m='vigente(hash)'},
       @{g=2;d='GestorRecuperacion';a='Usuario';m='cambiar_contrasena(usuario, hash_nuevo)'},
       @{g=2;d='GestorRecuperacion';a='TokenRecuperacion';m='marcar_usado(token)'},
       @{g=2;d='GestorRecuperacion';a='SesionToken';m='revocar_todas(usuario_id)'},
       @{g=3;d='GestorRecuperacion';a='PantallaRecuperacion';m='respuestaIndistinta()'},
       @{g=4;d='GestorRecuperacion';a='PantallaRecuperacion';m='TokenInvalido()'}
     )}

  @{ n='2.2 CU-42 Consultar la bitácora del sistema'
     actores=@('Administrador','Sistema (procesos automáticos)'); boundary='PantallaBitacora'
     controles=@('GestorBitacora','GestorAutenticacion')
     entidades=@('Bitacora','Usuario')
     grupos='Grupo 1: el sistema ESCRIBE cada asiento, en toda operacion que modifica el estado. Nadie lo pide: ocurre solo.   Grupo 2: el Administrador consulta y filtra.   Grupo 3: los intentos de acceso FALLIDOS tambien se registran --- son los que mas importan.   Grupo 4: la bitacora es INMUTABLE: no hay operacion de edicion ni de borrado, y eso es lo que el diagrama tiene que dejar ver.'
     msj=@(
       @{g=1;d='A:Sistema (procesos automáticos)';a='GestorBitacora';m='registrar(usuario, rol, accion, recurso, resultado)'},
       @{g=1;d='GestorBitacora';a='GestorBitacora';m='limpiar(detalle)'},
       @{g=1;d='GestorBitacora';a='Bitacora';m='agregar(asiento)'},
       @{g=2;d='A:Administrador';a='PantallaBitacora';m='consultar(filtros)'},
       @{g=2;d='PantallaBitacora';a='GestorBitacora';m='listar(filtros, pagina)'},
       @{g=2;d='GestorBitacora';a='GestorAutenticacion';m='autorizar("ADMINISTRADOR")'},
       @{g=2;d='GestorBitacora';a='Bitacora';m='pagina_de_asientos(filtros)'},
       @{g=2;d='GestorBitacora';a='Usuario';m='nombres_de(usuario_ids)'},
       @{g=2;d='PantallaBitacora';a='GestorBitacora';m='opciones()'},
       @{g=3;d='GestorAutenticacion';a='GestorBitacora';m='registrar("ACCESO_FALLIDO", correo)'},
       @{g=4;d='GestorBitacora';a='GestorBitacora';m='en_bolivia(momento)'}
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

    # Un mensaje puede nombrar un control que no esta en la lista de este caso
    # --- CU-12 lo recibe de GestorCarrito, CU-40 de cuatro gestores ajenos ---.
    # Se crean igual: sin esto, $part[...] devuelve nulo y el mensaje revienta.
    foreach ($m in $caso.msj) {
        foreach ($nom in @($m.d, $m.a)) {
            if ($part.ContainsKey($nom)) { continue }
            if ($nom.StartsWith('A:')) { $part[$nom] = Get-Actor $nom.Substring(2); continue }
            $part[$nom] = Get-OCrearClase $pClas $nom 'control' $desc[$nom]
        }
    }

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
    #
    # No sirve recorrer $d.DiagramLinks a secas: esa coleccion solo trae los
    # enlaces que EA ya materializo, y un conector creado por OTRO generador
    # despues de este lienzo todavia no tiene fila. Esos se dibujan con los
    # valores por defecto --- o sea visibles --- y el bucle nunca los veia. Se
    # pregunta por SQL cuales tienen los dos extremos en el lienzo, y al que no
    # sea de este caso de uso se le crea la fila oculta si le falta.
    $d.DiagramLinks.Refresh()
    $yaTienen = @{}
    foreach ($lnk in $d.DiagramLinks) { $yaTienen[[int]$lnk.ConnectorID] = $lnk }

    $ajenos = 0
    $enLienzo = Filas @"
SELECT c.Connector_ID AS id, c.Connector_Type AS t,
       c.Start_Object_ID AS a, c.End_Object_ID AS b
FROM t_connector c
WHERE c.Start_Object_ID IN (SELECT o.Object_ID  FROM t_diagramobjects o  WHERE o.Diagram_ID=$($d.DiagramID))
  AND c.End_Object_ID   IN (SELECT o2.Object_ID FROM t_diagramobjects o2 WHERE o2.Diagram_ID=$($d.DiagramID))
"@
    foreach ($f in $enLienzo) {
        $id = [int]$f.id
        $propio = $false
        if ($f.t -eq 'Collaboration') {
            $propio = $mios.ContainsKey($id)
        } elseif ($f.t -eq 'Association') {
            $k1 = "$($f.a)-$($f.b)"; $k2 = "$($f.b)-$($f.a)"
            $propio = ($pares.ContainsKey($k1) -or $pares.ContainsKey($k2))
        }
        if ($propio) { continue }

        if ($yaTienen.ContainsKey($id)) {
            $lnk = $yaTienen[$id]
        } else {
            $lnk = $d.DiagramLinks.AddNew('', '')
            $lnk.ConnectorID = $id
        }
        $lnk.IsHidden = $true
        if (-not $lnk.Update()) { throw "no se pudo ocultar el conector $id en $($caso.n)" }
        $ajenos++
    }
    $d.DiagramObjects.Refresh(); $d.DiagramLinks.Refresh()
    $ng = @($caso.msj | ForEach-Object { $_.g } | Sort-Object -Unique).Count
    Write-Output ("  {0,-52} {1,2} objetos, {2,2} mensajes en {3} grupos, {4,2} ajenos ocultos" -f $caso.n, $d.DiagramObjects.Count, $caso.msj.Count, $ng, $ajenos)
}

$ea.CloseFile(); $ea.Exit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($ea) | Out-Null
Write-Output 'OK'
