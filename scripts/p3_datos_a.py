# Datos de la P3, grupo «a»: CU-21 a CU-25 (inventario de la sucursal y devoluciones en caja y por la web).
# Sale del código de origin/main (08/11). Mismo formato que scripts/p2_datos.py (2.5 y 3.2) y
# scripts/p2_clases_datos.py (3.4); ESPEC es la ficha del 2.6.
# Uso: python -X utf8 scripts/p3_datos_a.py   (solo valida; no escribe nada)
import re

B = "backend/app/modules/"
W = "frontend-web/src/app/"
M = "mobile/lib/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."

# ------------------------------------------------------------------ 2.5 ---
CASOS = [
    # (id, nombre, actores, incluye, notas[, extiende])
    ('CU-21', 'Gestionar el inventario de la sucursal', ['Encargado de sucursal', 'Administrador de la empresa'],
     ['CU-17'],
     'Reemplaza a CU-13, CU-15 y CU-16 del primer parcial. Existencias, ingresos, ajustes por conteo y kardex; '
     'el encargado registra ingresos y conteos también sin conexión y se confirman al sincronizar. RF-52, RF-53.'),
    ('CU-22', 'Registrar cambio o devolución en caja', ['Cajero'], [],
     'Reemplaza al CU-32 del primer parcial. Devolución o cambio con la diferencia de precio, nota de devolución '
     'y conformidad del cliente; mueve el inventario y el arqueo. También lo usa el encargado. RF-24, RF-37, RF-59.'),
    ('CU-23', 'Configurar la ventana de devolución', ['Administrador de la empresa'], [],
     'Horas desde la compra o la entrega (1 a 720) en que se aceptan cambios y devoluciones; no depende del plan. '
     'RF-35, RN-08.'),
    ('CU-24', 'Solicitar cambio o devolución por la web', ['Cliente'], ['CU-26'],
     'El cliente pide desde «Mis compras» el cambio o la devolución de un pedido entregado, dentro de la ventana. '
     'RF-34, RF-59.'),
    ('CU-25', 'Atender solicitud de devolución', ['Encargado de sucursal', 'Cliente'], ['CU-26'],
     'El encargado aprueba o rechaza con su motivo; al recibir la prenda nace la nota y se reembolsa por la '
     'pasarela; el cliente da la conformidad. RF-36, RF-37.'),
]

# ------------------------------------------------------------------ 3.2 ---
AE, CJ, CL, EN = 'A:Administrador de la empresa', 'A:Cajero', 'A:Cliente', 'A:Encargado de sucursal'

ROBUSTEZ = [
    dict(cu='CU-21', n='Gestionar el inventario de la sucursal', a=['Encargado de sucursal'],
         f=['PantallaInventario'],
         c=['GestorInventario', 'ControlOffline', 'GestorOffline', 'GestorAutenticacion', 'BitacoraMiddleware'],
         e=['Existencia', 'MovimientoInventario', 'VarianteProducto', 'Proveedor', 'PaqueteLocal', 'OperacionLocal',
            'OperacionOffline', 'AsientoBitacora'],
         grupos=['flujo principal: ajuste por conteo físico en línea',
                 'alternativo 3a: registrar un ingreso de mercadería',
                 'alternativo 3b: ver el kardex de la prenda',
                 'alternativo 4a: sin conexión, se guarda en el dispositivo y se sincroniza después',
                 'alternativo 5a: el conteo coincide o no cubre lo reservado'],
         m=[(1, EN, 'PantallaInventario', 'abrirInventario()'),
            (1, 'PantallaInventario', 'GestorInventario', 'listarExistencias(sucursal, busqueda, pagina)'),
            (1, 'GestorInventario', 'GestorAutenticacion', 'autorizar("ENCARGADO", sucursal)'),
            (1, 'GestorInventario', 'Existencia', 'listarExistencias(sucursal, filtros)'),
            (1, 'GestorInventario', 'PantallaInventario', 'mostrarExistencias(pagina)'),
            (1, EN, 'PantallaInventario', 'ajustar(prenda, contado, motivo)'),
            (1, 'PantallaInventario', 'GestorInventario', 'registrarAjuste(sucursal, variante, contado, motivo)'),
            (1, 'GestorInventario', 'VarianteProducto', 'variantesValidas(ids)'),
            (1, 'GestorInventario', 'Existencia', 'obtenerExistencia(variante, sucursal, bloquear)'),
            (1, 'GestorInventario', 'GestorInventario', 'calcularDiferencia(contado, disponible + reservada)'),
            (1, 'GestorInventario', 'Existencia', 'aplicarCantidad(diferencia)'),
            (1, 'GestorInventario', 'MovimientoInventario', 'agregar("AJUSTE", diferencia, motivo, usuario)'),
            (1, 'GestorInventario', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorInventario', 'PantallaInventario', 'mostrarAjuste(movimiento, existencia)'),
            (2, EN, 'PantallaInventario', 'registrarIngreso(proveedor, remito, lineas)'),
            (2, 'PantallaInventario', 'GestorInventario', 'registrarIngreso(sucursal, proveedor, referencia, lineas)'),
            (2, 'GestorInventario', 'Proveedor', 'obtenerProveedor(id)'),
            (2, 'GestorInventario', 'VarianteProducto', 'variantesValidas(ids)'),
            (2, 'GestorInventario', 'Existencia', 'obtenerOCrear(variante, sucursal)'),
            (2, 'GestorInventario', 'MovimientoInventario', 'agregar("INGRESO", cantidad, proveedor, referencia)'),
            (2, 'GestorInventario', 'PantallaInventario', 'mostrarIngreso(ingreso)'),
            (3, EN, 'PantallaInventario', 'verKardex(prenda)'),
            (3, 'PantallaInventario', 'GestorInventario', 'kardex(variante, sucursal, pagina)'),
            (3, 'GestorInventario', 'Existencia', 'obtenerExistencia(variante, sucursal)'),
            (3, 'GestorInventario', 'MovimientoInventario', 'kardex(existencia, pagina)'),
            (3, 'GestorInventario', 'PantallaInventario', 'mostrarKardex(movimientos, saldo, sinConexion)'),
            (4, EN, 'PantallaInventario', 'prepararSinConexion()'),
            (4, 'PantallaInventario', 'ControlOffline', 'prepararInventario()'),
            (4, 'ControlOffline', 'GestorOffline', 'paqueteDeInventario(usuario, sucursal)'),
            (4, 'GestorOffline', 'GestorAutenticacion', 'autorizar("ENCARGADO")'),
            (4, 'GestorOffline', 'Existencia', 'prendasParaInventario(sucursal)'),
            (4, 'GestorOffline', 'Proveedor', 'proveedoresActivos()'),
            (4, 'GestorOffline', 'ControlOffline', 'paquete(prendas, proveedores, vigencia)'),
            (4, 'ControlOffline', 'PaqueteLocal', 'guardarPaqueteInventario(paquete)'),
            (4, EN, 'PantallaInventario', 'contar(prenda, contado, motivo)'),
            (4, 'PantallaInventario', 'ControlOffline', 'registrarConteo(prenda, contado, motivo)'),
            (4, 'ControlOffline', 'ControlOffline', 'generarUuid()'),
            (4, 'ControlOffline', 'OperacionLocal', 'guardar(operacion, "local")'),
            (4, 'ControlOffline', 'PaqueteLocal', 'aplicarAInventario(delta)'),
            (4, 'ControlOffline', 'GestorOffline', 'sincronizar(lote)'),
            (4, 'GestorOffline', 'OperacionOffline', 'operacionPorUuid(uuid)'),
            (4, 'GestorOffline', 'MovimientoInventario', 'fisicoAlMomento(variante, sucursal, creadaEn)'),
            (4, 'GestorOffline', 'GestorInventario', 'ajustarPorDiferencia(variante, sucursal, diferencia, motivo)'),
            (4, 'GestorOffline', 'OperacionOffline', 'guardar(operacion, "CONFIRMADA")'),
            (4, 'GestorOffline', 'BitacoraMiddleware', 'registrar(peticion)'),
            (4, 'GestorOffline', 'ControlOffline', 'resultados(lote)'),
            (4, 'ControlOffline', 'OperacionLocal', 'actualizar(uuid, estado, motivo)'),
            (4, 'ControlOffline', 'PantallaInventario', 'mostrarCola(pendientes)'),
            (5, 'GestorInventario', 'PantallaInventario', 'conteoSinDiferencia()'),
            (5, 'GestorInventario', 'PantallaInventario', 'conteoMenorQueLoReservado(reservada)'),
            (5, 'GestorInventario', 'GestorOffline', 'stockInsuficiente(disponible)'),
            (5, 'GestorOffline', 'OperacionOffline', 'guardar(operacion, "RECHAZADA", motivo)'),
            (5, 'GestorOffline', 'ControlOffline', 'rechazada(uuid, motivo)')]),

    dict(cu='CU-22', n='Registrar cambio o devolución en caja', a=['Cajero'],
         f=['PantallaDevolucion', 'DialogoNotaDevolucion'],
         c=['GestorDevoluciones', 'GestorCaja', 'GestorInventario', 'GestorPromociones', 'GestorAutenticacion',
            'BitacoraMiddleware'],
         e=['TurnoCaja', 'Venta', 'DetalleVenta', 'Devolucion', 'DetalleDevolucion', 'Empresa', 'SolicitudDevolucion',
            'Existencia', 'MovimientoInventario', 'AsientoBitacora'],
         grupos=['flujo principal: devolución con la nota y la conformidad',
                 'alternativo 3a: cambio por otra prenda o talla, con la diferencia',
                 'alternativos 6a a 6c: fuera de la ventana, solo cambio o devuelve de más',
                 'alternativo 8a: ver e imprimir la nota'],
         m=[(1, CJ, 'PantallaDevolucion', 'buscarVenta(codigo)'),
            (1, 'PantallaDevolucion', 'GestorDevoluciones', 'buscarVenta(codigo)'),
            (1, 'GestorDevoluciones', 'GestorAutenticacion', 'autorizar("CAJERO")'),
            (1, 'GestorDevoluciones', 'GestorCaja', 'mostradorDe(usuario)'),
            (1, 'GestorCaja', 'TurnoCaja', 'turnoAbiertoDe(usuario)'),
            (1, 'GestorDevoluciones', 'Venta', 'ventaDevolvible(codigo, sucursal)'),
            (1, 'GestorDevoluciones', 'DetalleVenta', 'lineasVendidas(venta)'),
            (1, 'GestorDevoluciones', 'DetalleDevolucion', 'yaDevuelto(venta)'),
            (1, 'GestorDevoluciones', 'Empresa', 'ventanaDevolucionHoras()'),
            (1, 'GestorDevoluciones', 'SolicitudDevolucion', 'cambioAprobado(venta)'),
            (1, 'GestorDevoluciones', 'PantallaDevolucion', 'mostrarDevolvibles(lineas, venceEn)'),
            (1, CJ, 'PantallaDevolucion', 'registrar(lineas, motivo, conformidad)'),
            (1, 'PantallaDevolucion', 'GestorDevoluciones', 'registrar(codigo, motivo, lineas, conformidad)'),
            (1, 'GestorDevoluciones', 'GestorDevoluciones', 'exigirPlazo(venta, horas)'),
            (1, 'GestorDevoluciones', 'Venta', 'bloquearVenta(venta)'),
            (1, 'GestorDevoluciones', 'Devolucion', 'agregar(venta, turno, motivo, monto, observacionCliente)'),
            (1, 'GestorDevoluciones', 'DetalleDevolucion', 'agregar(devolucion, variante, cantidad)'),
            (1, 'GestorDevoluciones', 'GestorInventario', 'reingresarPorDevolucion(variante, sucursal, cantidad)'),
            (1, 'GestorInventario', 'Existencia', 'sumarDisponible(cantidad)'),
            (1, 'GestorInventario', 'MovimientoInventario', 'agregar("DEVOLUCION", cantidad, motivo)'),
            (1, 'GestorDevoluciones', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorDevoluciones', 'PantallaDevolucion', 'mostrarComprobante(numeroNota, monto, saleDelCajon)'),
            (2, CJ, 'PantallaDevolucion', 'elegirModo("CAMBIO")'),
            (2, CJ, 'PantallaDevolucion', 'agregar(prendaNueva)'),
            (2, 'PantallaDevolucion', 'GestorDevoluciones',
             'registrarCambio(codigo, devueltas, llevadas, metodoDiferencia, conformidad)'),
            (2, 'GestorDevoluciones', 'GestorPromociones', 'descuentosPorVariante(precios)'),
            (2, 'GestorDevoluciones', 'GestorDevoluciones', 'calcularDiferencia(totalLlevado, valorDevuelto)'),
            (2, 'GestorDevoluciones', 'Venta', 'agregarVentaPresencial(codigo, "CAMBIO", total)'),
            (2, 'GestorDevoluciones', 'DetalleVenta', 'agregar(ventaNueva, variante, precio, descuento)'),
            (2, 'GestorDevoluciones', 'Devolucion', 'agregar("CAMBIO", ventaNueva, diferencia, metodoDiferencia)'),
            (2, 'GestorDevoluciones', 'GestorInventario', 'descontarPorVenta(variante, sucursal, cantidad)'),
            (2, 'GestorInventario', 'Existencia', 'bloquearYDescontar(variante, cantidad)'),
            (2, 'GestorDevoluciones', 'SolicitudDevolucion', 'completarCon(devolucion)'),
            (2, 'GestorDevoluciones', 'PantallaDevolucion', 'mostrarCambio(ventaNueva, diferencia, aFavorDe)'),
            (3, 'GestorDevoluciones', 'PantallaDevolucion', 'fueraDePlazo(venceEn, horas)'),
            (3, 'GestorDevoluciones', 'PantallaDevolucion', 'soloCambio(motivo)'),
            (3, 'GestorDevoluciones', 'PantallaDevolucion', 'devuelveDeMas(devolvibles)'),
            (4, CJ, 'DialogoNotaDevolucion', 'verNota(idDevolucion)'),
            (4, 'DialogoNotaDevolucion', 'GestorDevoluciones', 'nota(idDevolucion, sucursal)'),
            (4, 'GestorDevoluciones', 'Devolucion', 'devolucionConVenta(idDevolucion)'),
            (4, 'GestorDevoluciones', 'DetalleDevolucion', 'detallesDe(devolucion)'),
            (4, 'GestorDevoluciones', 'DialogoNotaDevolucion', 'mostrarNota(nota)'),
            (4, CJ, 'DialogoNotaDevolucion', 'imprimir()')]),

    dict(cu='CU-23', n='Configurar la ventana de devolución', a=['Administrador de la empresa'],
         f=['PanelVentanaDevolucion'],
         c=['GestorVentanaDevolucion', 'GestorAutenticacion', 'BitacoraMiddleware', 'GestorDevoluciones'],
         e=['Empresa', 'AsientoBitacora'],
         grupos=['flujo principal: ver y guardar la ventana', 'alternativo 3a: elegir un atajo de 24, 48 o 72 horas',
                 'alternativo 6a: horas fuera de 1 a 720',
                 'alternativo 7a: la caja y la web aplican la ventana vigente (RN-08)'],
         m=[(1, AE, 'PanelVentanaDevolucion', 'abrirMiTienda()'),
            (1, 'PanelVentanaDevolucion', 'GestorVentanaDevolucion', 'obtenerVentana()'),
            (1, 'GestorVentanaDevolucion', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorVentanaDevolucion', 'Empresa', 'obtener(empresa)'),
            (1, 'GestorVentanaDevolucion', 'PanelVentanaDevolucion', 'mostrarVentana(horas)'),
            (1, AE, 'PanelVentanaDevolucion', 'ingresarHoras(horas)'),
            (1, AE, 'PanelVentanaDevolucion', 'guardar()'),
            (1, 'PanelVentanaDevolucion', 'GestorVentanaDevolucion', 'guardarVentana(horas)'),
            (1, 'GestorVentanaDevolucion', 'Empresa', 'guardarVentana(horas)'),
            (1, 'GestorVentanaDevolucion', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorVentanaDevolucion', 'PanelVentanaDevolucion', 'confirmar(horas)'),
            (2, AE, 'PanelVentanaDevolucion', 'elegirAtajo(horas)'),
            (3, 'GestorVentanaDevolucion', 'PanelVentanaDevolucion', 'horasInvalidas(1, 720)'),
            (4, 'GestorDevoluciones', 'Empresa', 'ventanaDevolucionHoras()'),
            (4, 'GestorDevoluciones', 'GestorDevoluciones', 'calcularVencimiento(compraOEntrega, horas)')]),

    dict(cu='CU-24', n='Solicitar cambio o devolución por la web', a=['Cliente'],
         f=['PantallaSolicitarDevolucion', 'PantallaMisSolicitudes'],
         c=['GestorDevolucionesWeb', 'GestorDevoluciones', 'GestorNotificaciones', 'GestorAutenticacion',
            'BitacoraMiddleware'],
         e=['Venta', 'DetalleVenta', 'DetalleDevolucion', 'SolicitudDevolucion', 'LineaSolicitudDevolucion',
            'VarianteProducto', 'Empresa', 'Notificacion', 'AsientoBitacora'],
         grupos=['flujo principal: pedir la devolución de un pedido entregado',
                 'alternativo 3a: pedir un cambio por otra talla o color',
                 'alternativos 5a y 5b: fuera de la ventana o pedido no entregado',
                 'alternativo 5c: pide más de lo que queda o un cambio inválido',
                 'alternativo 8a: seguir la solicitud en «Mis solicitudes»'],
         m=[(1, CL, 'PantallaSolicitarDevolucion', 'pedirDevolucion(codigo)'),
            (1, 'PantallaSolicitarDevolucion', 'GestorDevolucionesWeb', 'pedidoDevolvible(codigo)'),
            (1, 'GestorDevolucionesWeb', 'GestorAutenticacion', 'autorizar("CLIENTE")'),
            (1, 'GestorDevolucionesWeb', 'Venta', 'ventaDigital(codigo)'),
            (1, 'GestorDevolucionesWeb', 'GestorDevoluciones', 'ventanaEnHoras()'),
            (1, 'GestorDevoluciones', 'Empresa', 'ventanaDevolucionHoras()'),
            (1, 'GestorDevolucionesWeb', 'DetalleVenta', 'lineasVendidas(venta)'),
            (1, 'GestorDevolucionesWeb', 'DetalleDevolucion', 'yaDevuelto(venta)'),
            (1, 'GestorDevolucionesWeb', 'LineaSolicitudDevolucion', 'pedidoEnSolicitudesAbiertas(venta)'),
            (1, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'mostrarDevolvibles(lineas, venceEn)'),
            (1, CL, 'PantallaSolicitarDevolucion', 'elegirPrendas(cantidades, motivo)'),
            (1, CL, 'PantallaSolicitarDevolucion', 'enviar()'),
            (1, 'PantallaSolicitarDevolucion', 'GestorDevolucionesWeb', 'solicitar(codigo, tipo, motivo, lineas)'),
            (1, 'GestorDevolucionesWeb', 'Venta', 'bloquear(venta)'),
            (1, 'GestorDevolucionesWeb', 'GestorDevolucionesWeb', 'validarPlazoYCantidades(lineas)'),
            (1, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'crear(venta, cliente, sucursal, tipo, motivo)'),
            (1, 'GestorDevolucionesWeb', 'LineaSolicitudDevolucion', 'crear(variante, cantidad, varianteNueva)'),
            (1, 'GestorDevolucionesWeb', 'GestorNotificaciones', 'avisarDevolucionSolicitada(solicitud)'),
            (1, 'GestorNotificaciones', 'Notificacion', 'crear(encargado, titulo, cuerpo)'),
            (1, 'GestorDevolucionesWeb', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'confirmarSolicitud(solicitud)'),
            (2, CL, 'PantallaSolicitarDevolucion', 'cambiarTipo("CAMBIO")'),
            (2, 'GestorDevolucionesWeb', 'VarianteProducto', 'opcionesDeCambio(variante, sucursal)'),
            (2, CL, 'PantallaSolicitarDevolucion', 'elegirNueva(linea, variante)'),
            (2, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'mostrarDiferencia(valorNuevo, valorDevuelto)'),
            (3, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'fueraDePlazo(horas, venceEn)'),
            (3, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'pedidoNoEntregado()'),
            (4, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'puedePedirHasta(libres)'),
            (4, 'GestorDevolucionesWeb', 'PantallaSolicitarDevolucion', 'cambioNoValido()'),
            (5, CL, 'PantallaMisSolicitudes', 'abrirMisSolicitudes()'),
            (5, 'PantallaMisSolicitudes', 'GestorDevolucionesWeb', 'misSolicitudes()'),
            (5, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'idsDeSolicitudes(cliente)'),
            (5, 'GestorDevolucionesWeb', 'PantallaMisSolicitudes', 'mostrarSolicitudes(estado, respuesta)')]),

    dict(cu='CU-25', n='Atender solicitud de devolución', a=['Encargado de sucursal', 'Cliente'],
         f=['PantallaPedidosWeb', 'PantallaMisSolicitudes', 'PasarelaDePago'],
         c=['GestorDevolucionesWeb', 'GestorInventario', 'GestorNotificaciones', 'GestorAutenticacion',
            'BitacoraMiddleware'],
         e=['SolicitudDevolucion', 'Venta', 'Devolucion', 'DetalleDevolucion', 'Pago', 'Existencia',
            'MovimientoInventario', 'Notificacion', 'AsientoBitacora'],
         grupos=['flujo principal: aprobar, recibir la prenda y reembolsar por la pasarela',
                 'alternativo 2a: rechazar con el motivo',
                 'alternativo 4a: un cambio aprobado se retira en caja (CU-22)',
                 'alternativo 6a: la pasarela no puede reembolsar',
                 'paso 8 y alternativo 8a: el cliente da o niega la conformidad'],
         m=[(1, EN, 'PantallaPedidosWeb', 'abrirPedidosWeb()'),
            (1, 'PantallaPedidosWeb', 'GestorDevolucionesWeb', 'solicitudesDeSucursal(estado)'),
            (1, 'GestorDevolucionesWeb', 'GestorAutenticacion', 'autorizar("ENCARGADO")'),
            (1, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'idsDeSolicitudes(sucursal, estado)'),
            (1, 'GestorDevolucionesWeb', 'PantallaPedidosWeb', 'mostrarSolicitudes(solicitudes)'),
            (1, EN, 'PantallaPedidosWeb', 'aprobar(solicitud, respuesta)'),
            (1, 'PantallaPedidosWeb', 'GestorDevolucionesWeb', 'aprobar(id, respuesta)'),
            (1, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'solicitud(id, bloquear)'),
            (1, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'marcar("APROBADA", respuesta, usuario)'),
            (1, 'GestorDevolucionesWeb', 'GestorNotificaciones', 'avisarDevolucionResuelta(solicitud)'),
            (1, 'GestorNotificaciones', 'Notificacion', 'crear(cliente, titulo, cuerpo)'),
            (1, 'GestorDevolucionesWeb', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, EN, 'PantallaPedidosWeb', 'recibir(solicitud)'),
            (1, 'PantallaPedidosWeb', 'GestorDevolucionesWeb', 'recibir(id)'),
            (1, 'GestorDevolucionesWeb', 'Venta', 'ventaPorId(venta, bloquear)'),
            (1, 'GestorDevolucionesWeb', 'DetalleDevolucion', 'yaDevuelto(venta)'),
            (1, 'GestorDevolucionesWeb', 'Devolucion', 'crear("WEB", "ABIERTA", recibidaPor)'),
            (1, 'GestorDevolucionesWeb', 'DetalleDevolucion', 'crear(devolucion, variante, cantidad)'),
            (1, 'GestorDevolucionesWeb', 'GestorInventario', 'reingresarPorDevolucion(variante, sucursal, cantidad)'),
            (1, 'GestorInventario', 'Existencia', 'sumarDisponible(cantidad)'),
            (1, 'GestorInventario', 'MovimientoInventario', 'agregar("DEVOLUCION", cantidad, motivo)'),
            (1, 'GestorDevolucionesWeb', 'Pago', 'pagoDeVenta(venta)'),
            (1, 'GestorDevolucionesWeb', 'PasarelaDePago', 'reembolsar(referenciaExterna, monto, clave)'),
            (1, 'GestorDevolucionesWeb', 'Devolucion', 'guardarReembolso(referencia, monto)'),
            (1, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'marcar("COMPLETADA", devolucion)'),
            (1, 'GestorDevolucionesWeb', 'PantallaPedidosWeb', 'mostrarNota(numeroNota, reembolso)'),
            (2, EN, 'PantallaPedidosWeb', 'rechazar(solicitud, motivo)'),
            (2, 'PantallaPedidosWeb', 'GestorDevolucionesWeb', 'rechazar(id, respuesta)'),
            (2, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'marcar("RECHAZADA", respuesta, usuario)'),
            (2, 'GestorDevolucionesWeb', 'GestorNotificaciones', 'avisarDevolucionResuelta(solicitud)'),
            (2, 'GestorDevolucionesWeb', 'PantallaPedidosWeb', 'motivoObligatorio()'),
            (3, 'GestorDevolucionesWeb', 'PantallaPedidosWeb', 'cambioSeRetiraEnCaja()'),
            (4, 'PasarelaDePago', 'GestorDevolucionesWeb', 'errorDePasarela(detalle)'),
            (4, 'GestorDevolucionesWeb', 'GestorDevolucionesWeb', 'revertirTransaccion()'),
            (4, 'GestorDevolucionesWeb', 'PantallaPedidosWeb', 'reembolsoFallido(detalle)'),
            (5, CL, 'PantallaMisSolicitudes', 'darConformidad(conforme, observacion)'),
            (5, 'PantallaMisSolicitudes', 'GestorDevolucionesWeb', 'conformidad(id, conforme, observacion)'),
            (5, 'GestorDevolucionesWeb', 'SolicitudDevolucion', 'solicitud(id, bloquear)'),
            (5, 'GestorDevolucionesWeb', 'Devolucion', 'cerrarConConformidad(conforme, observacion)'),
            (5, 'GestorDevolucionesWeb', 'PantallaMisSolicitudes', 'mostrarSolicitudes(estado)')]),
]

# Solo los nombres nuevos (los de la P2 ya tienen su descripción en p2_datos.py).
DESCRIPCION = {
    'PantallaInventario': 'Pantalla «Inventario»: existencias, ingresos, ajustes y kardex; en la web y en el móvil, también sin conexión.',
    'GestorInventario': 'Control del backend de inventario (inventario/service.py): ingresos, ajustes, kardex, reingresos y descuentos con bloqueo de fila.',
    'MovimientoInventario': 'Movimiento inmutable de una existencia, con signo, tipo, motivo, usuario y la operación offline que lo originó.',
    'VarianteProducto': 'La prenda vendible: producto en una talla y un color, con su SKU y su precio.',
    'Proveedor': 'Quien manda la mercadería de un ingreso.',
    'PantallaDevolucion': 'Pantalla «Devoluciones y cambios» de la caja.',
    'DialogoNotaDevolucion': 'Diálogo que muestra e imprime la nota de devolución (ND-…).',
    'GestorDevoluciones': 'Control del backend de CU-22 (pos/devolucion_service.py): devolución, cambio, nota y la ventana vigente.',
    'GestorPromociones': 'Calcula el descuento vigente de cada prenda (RN-15) para el precio del cambio.',
    'DetalleVenta': 'Línea de una venta, con el precio y el descuento congelados.',
    'DetalleDevolucion': 'Prenda y cantidad que volvieron en una devolución o un cambio.',
    'SolicitudDevolucion': 'Pedido web de cambio o devolución: PENDIENTE, APROBADA, RECHAZADA o COMPLETADA.',
    'LineaSolicitudDevolucion': 'Prenda que el cliente pide devolver y, en un cambio, la que quiere a cambio.',
    'PanelVentanaDevolucion': 'Tarjeta «Ventana de devolución» dentro de «Mi tienda».',
    'GestorVentanaDevolucion': 'Control de CU-23 (plataforma/mi_tienda/service.py): lee y guarda la ventana de la empresa.',
    'PantallaSolicitarDevolucion': 'Diálogo «Cambio o devolución» de un pedido en «Mis compras».',
    'PantallaMisSolicitudes': 'Lista «Mis cambios y devoluciones» del cliente, con la nota y la conformidad.',
    'GestorDevolucionesWeb': 'Control del backend de CU-24 y CU-25 (devoluciones_web/service.py).',
    'GestorNotificaciones': 'Deja el aviso en la campanita y en la cola de correo y push (notificaciones/service.py).',
    'Notificacion': 'Aviso a un usuario, con su estado de correo y de push.',
    'PantallaPedidosWeb': 'Pantalla «Pedidos web» de la sucursal: entregas y solicitudes de devolución.',
    'PasarelaDePago': 'Frontera de salida: el proveedor de pagos (Stripe o el simulado) que hace el reembolso.',
    'Pago': 'Cobro de un pedido web por la pasarela, con la referencia externa de la sesión.',
}

# ------------------------------------------------------------------ 3.4 ---
CLASES = {
    # ---------------- INTERFACES ----------------
    "Inventario": {"tipo": "interfaz", "origen": W + "features/admin/inventario/inventario.ts",
        "nota": "La usan el Administrador (/admin/inventario) y el Encargado (/sucursal/inventario). Los diálogos que abre (IngresoFormulario, AjusteFormulario, MinimoFormulario, TransferenciaFormulario, KardexDialogo) llaman a InventarioService.",
        "atributos": [],
        "operaciones": ["ngOnInit(): void", "refrescarTodo(): void", "paginarExistencias(evento: PageEvent): void",
            "buscarExistencias(): void", "paginarIngresos(evento: PageEvent): void", "paginarMovimientos(evento: PageEvent): void",
            "alternarDetalle(ingreso: IngresoResumen): void", "estaAbierto(ingreso: IngresoResumen): boolean",
            "registrarIngreso(): void", "ajustar(existencia: Existencia): void", "fijarMinimo(existencia: Existencia): void",
            "transferir(existencia: Existencia | null): void", "verKardex(existencia: Existencia): void",
            "conSigno(cantidad: number): string", "claseDeTipo(tipo: TipoMovimiento): string"]},
    "PantallaInventario": {"tipo": "interfaz", "origen": M + "features/inventario/pantalla_inventario.dart",
        "nota": "Los métodos viven en _PantallaInventarioState. En el mismo archivo están PantallaIngresoSinRed (_guardar(paquete) llama a ControlOffline.registrarIngreso) y PantallaKardex (initState pide RepositorioOffline.kardex).",
        "atributos": [],
        "operaciones": ["initState(): void", "_preparar({bool silencioso}): Future<void>",
            "_abrirPrenda(context, p: PrendaInventario, enLinea: bool): void", "_contar(context, p: PrendaInventario): Future<void>"]},
    "Devolucion_PWA": {"tipo": "interfaz", "origen": W + "features/caja/devolucion/devolucion.ts",
        "nota": "En el código la clase se llama `Devolucion`; se renombra para no chocar con la entidad Devolucion. registrarCambio(venta) es privado y lo llama registrar() en modo CAMBIO.",
        "atributos": [],
        "operaciones": ["ngOnInit(): void", "elegirModo(modo: Modo): void", "agregar(prenda: PrendaEnMostrador): void",
            "cantidadLlevada(prenda: PrendaQueSeLleva, cantidad: number): void", "quitar(prenda: PrendaQueSeLleva): void",
            "buscar(): void", "cambiar(fila: LineaEnDevolucion, cantidad: number): void", "todo(): void", "registrar(): void",
            "verNota(id: number): void", "plazoTexto(horas: number): string", "otra(): void",
            "subtotalLlevado(prenda: PrendaQueSeLleva): number", "subtotalDe(fila: LineaEnDevolucion): number"]},
    "NotaDevolucionDialogo": {"tipo": "interfaz", "origen": W + "features/caja/devolucion/nota-devolucion.ts",
        "nota": "Pide GET /pos/notas-devolucion/{id} con HttpClient (o la URL /tienda/devoluciones/{id}/nota, desde «Mis solicitudes»).",
        "atributos": [],
        "operaciones": ["ngOnInit(): void", "sinSigno(monto: string): string", "esCero(monto: string): boolean", "imprimir(): void"]},
    "VentanaDevolucion": {"tipo": "interfaz", "origen": W + "features/admin/mi-tienda/ventana-devolucion.ts",
        "nota": "Tarjeta dentro de MiTienda. Llama con HttpClient a GET y PUT /plataforma/mi-tienda/devoluciones (no hay service del front). Los atajos de 24, 48 y 72 h son horas.setValue(atajo) en la plantilla.",
        "atributos": ["atajos: number[]", "horas: FormControl<number>", "guardadas: Signal<number | null>"],
        "operaciones": ["ngOnInit(): void", "comoTexto(): string", "guardar(): void"]},
    "Compras": {"tipo": "interfaz", "origen": W + "features/cliente/compras/compras.ts",
        "atributos": [],
        "operaciones": ["ngOnInit(): void", "paginar(evento: PageEvent): void", "pedirDevolucion(compra: Pedido): void",
            "tieneComprobante(compra: Pedido): boolean", "descargar(compra: Pedido): void", "rotulo(estado: EstadoPedido): string"]},
    "SolicitarDevolucion": {"tipo": "interfaz", "origen": W + "features/cliente/compras/solicitar-devolucion.ts",
        "nota": "Diálogo. Llama con HttpClient a GET /tienda/devoluciones/pedidos/{codigo} y POST /tienda/devoluciones.",
        "atributos": [],
        "operaciones": ["ngOnInit(): void", "enTexto(monto: number): string", "cambiarTipo(tipo: TipoSolicitud): void",
            "mover(e: Eleccion, paso: number): void", "elegirNueva(e: Eleccion, variante: number): void", "enviar(): void"]},
    "MisSolicitudes": {"tipo": "interfaz", "origen": W + "features/cliente/compras/mis-solicitudes.ts",
        "nota": "Llama con HttpClient a GET /tienda/devoluciones y POST /tienda/devoluciones/{id}/conformidad.",
        "atributos": [],
        "operaciones": ["ngOnInit(): void", "recargar(): void", "verNota(s: Solicitud): void",
            "conformidad(s: Solicitud, conforme: boolean, observacion: string): void", "rotulo(estado: EstadoSolicitud): string"]},
    "PedidosWeb": {"tipo": "interfaz", "origen": W + "features/sucursal/pedidos-web/pedidos-web.ts",
        "nota": "Llama con HttpClient a /sucursal/pedidos y /sucursal/solicitudes-devolucion/{id}/{aprobar|rechazar|recibir}.",
        "atributos": [],
        "operaciones": ["pendientes(): number", "ngOnInit(): void", "entregar(p: PedidoDeSucursal): void",
            "atender(s: Solicitud, accion: 'aprobar' | 'rechazar' | 'recibir', respuesta: string): void",
            "verNota(id: number): void", "rotulo(estado: EstadoSolicitud): string"]},

    # ---------------- CONTROLES (front) ----------------
    "InventarioService": {"tipo": "control", "origen": W + "core/services/inventario.service.ts",
        "atributos": [],
        "operaciones": ["avisosDeIngreso(): Observable<AvisoDeIngreso[]>", "registrarIngreso(datos: IngresoCrear): Observable<IngresoRegistrado>",
            "listarIngresos(filtros: FiltrosIngresos): Observable<PaginaIngresos>", "detalleDeIngreso(ingreso: IngresoResumen): Observable<Movimiento[]>",
            "listarExistencias(filtros: FiltrosExistencias): Observable<PaginaExistencias>",
            "kardex(variante_id: number, sucursal_id: number, pagina: number, tamano: number): Observable<Kardex>",
            "listarMovimientos(filtros: FiltrosMovimientos): Observable<PaginaMovimientos>", "tiposManuales(): Observable<TipoManual[]>",
            "listarAlertas(sucursal_id?: number): Observable<Existencia[]>", "fijarStockMinimo(existencia_id, stock_minimo): Observable<Existencia>",
            "registrarAjuste(datos: AjusteCrear): Observable<AjusteRegistrado>", "registrarTransferencia(datos): Observable<TransferenciaRegistrada>",
            "traducir(error: HttpErrorResponse): ErrorInventario"]},
    "ControlOffline": {"tipo": "control", "origen": M + "features/offline/estado_offline.dart",
        "nota": "Notifier<EstadoOffline> (offlineProvider). Baja el paquete por RepositorioOffline.descargarPaqueteInventario() (GET /offline/paquete-inventario) y guarda en SQLite por BaseLocal (guardarPaqueteInventario, leerPaqueteInventario, aplicarAInventario).",
        "atributos": ["state: EstadoOffline", "_base: BaseLocal"],
        "operaciones": ["prepararInventario(): Future<PaqueteInventario>",
            "registrarIngreso({proveedor: ProveedorLocal, remito: String?, prendas: Map<PrendaInventario, int>}): Future<OperacionGuardada>",
            "registrarConteo({prenda: PrendaInventario, contado: int, motivo: String}): Future<OperacionGuardada>",
            "_guardarDeInventario({resumen: String, cuerpo: Map<String, dynamic>}): Future<OperacionGuardada>",
            "_efecto(cuerpo: Map<String, dynamic>): Map<int, int>", "sincronizar(): Future<({int confirmadas, int rechazadas})?>"]},
    "DevolucionesService": {"tipo": "control", "origen": W + "core/services/devoluciones.service.ts",
        "atributos": [],
        "operaciones": ["buscarVenta(codigo: string): Observable<VentaDevolvible>", "registrar(datos: Devolucion): Observable<ComprobanteDevolucion>",
            "registrarCambio(datos: Cambio): Observable<ComprobanteCambio>", "traducir(error: HttpErrorResponse): ErrorDevolucion"]},

    # ---------------- CONTROLES (backend) ----------------
    "inventario_service": {"tipo": "control", "origen": B + "inventario/service.py",
        "nota": "Módulo de funciones. Rutas en inventario/router.py: GET /inventario/existencias, POST /inventario/ingresos, POST /inventario/movimientos/ajuste, GET /inventario/kardex, PATCH /inventario/existencias/{id}/stock-minimo (Administrador y Encargado, este limitado a su sucursal por verificar_ambito_sucursal); POST /inventario/movimientos/transferencia solo el Administrador.",
        "atributos": [],
        "operaciones": ["listar_existencias(db, pagina, tamano, sucursal_id, producto_id, solo_con_saldo, busqueda): PaginaExistencias",
            "registrar_ingreso(db, datos: IngresoIn, usuario_id, confirmar, movimientos): IngresoOut",
            "registrar_ajuste(db, datos: AjusteIn, usuario_id): AjusteOut",
            "ajustar_por_diferencia(db, variante_id, sucursal_id, diferencia, motivo, usuario_id): MovimientoInventario | None",
            "kardex(db, variante_id, sucursal_id, pagina, tamano): KardexOut",
            "registrar_transferencia(db, datos: TransferenciaIn, usuario_id): TransferenciaOut",
            "fijar_stock_minimo(db, existencia_id, stock_minimo): ExistenciaOut",
            "reingresar_por_devolucion(db, variante_id, sucursal_id, cantidad, usuario_id, motivo): Existencia",
            "descontar_por_venta(db, variante_id, sucursal_id, cantidad, usuario_id, motivo, movimientos): Existencia",
            "_aplicar_movimiento(db, existencia, tipo, cantidad, reservada_delta, motivo, proveedor_id, referencia, usuario_id): MovimientoInventario",
            "_existencia_o_crearla(db, variante_id, sucursal_id): Existencia", "_variantes_validas(db, ids): dict[int, Row]"]},
    "offline_service": {"tipo": "control", "origen": B + "offline/service.py",
        "nota": "Módulo de funciones. GET /offline/paquete-inventario (solo ENCARGADO) y POST /offline/sincronizar. _sincronizar_una marca cada movimiento escrito con operacion_offline_id.",
        "atributos": [],
        "operaciones": ["paquete_de_inventario(db, usuario_id, sucursal_id): PaqueteDeInventarioOut",
            "sincronizar(db, usuario_id, rol, sucursal_del_usuario, lote): LoteOut",
            "_sincronizar_una(db, op, usuario_id, rol, sucursal_del_usuario, dispositivo): ResultadoOut",
            "_confirmar_inventario(db, op, usuario_id, rol, sucursal_del_usuario, movimientos): int",
            "_resultado(db, fila, repetida): ResultadoOut"]},
    "devolucion_service": {"tipo": "control", "origen": B + "pos/devolucion_service.py",
        "nota": "Módulo de funciones. Rutas en pos/devolucion_router.py: GET /pos/devoluciones/ventas/{codigo}, POST /pos/devoluciones, POST /pos/devoluciones/cambios (CAJERO y ENCARGADO) y GET /pos/notas-devolucion/{id} (también ADMINISTRADOR). El turno sale de pos/service.py mostrador_de; los precios del cambio, de promociones.descuentos_por_variante.",
        "atributos": [],
        "operaciones": ["ventana_en_horas(db): int", "_vence_en(venta, horas): datetime", "_exigir_plazo(db, venta, cambio_aprobado): None",
            "_por_que_solo_cambio(venta): str | None", "_aprobada_cubre(aprobada, pedidas): bool", "_sale_del_cajon(venta): bool",
            "_lineas_que_vuelven(db, venta, pedidas, en_la_web): tuple[list, dict]",
            "buscar_venta(db, usuario_id, codigo): VentaDevolvibleOut", "registrar(db, usuario_id, datos: DevolucionIn): DevolucionOut",
            "registrar_cambio(db, usuario_id, datos: CambioIn): CambioOut", "_a_favor_de(diferencia): str",
            "nota(db, devolucion_id, sucursal_id): NotaDevolucionOut"]},
    "mi_tienda_router": {"tipo": "control", "origen": B + "plataforma/mi_tienda/router.py",
        "nota": "Router /plataforma/mi-tienda, solo ADMINISTRADOR. La ventana no depende del plan (las rutas de la marca sí, con requiere_funcion).",
        "atributos": [],
        "operaciones": ["obtener_ventana(db, usuario): VentanaDevolucionOut", "guardar_ventana(datos: VentanaDevolucionIn, db, usuario): VentanaDevolucionOut"]},
    "mi_tienda_service": {"tipo": "control", "origen": B + "plataforma/mi_tienda/service.py",
        "atributos": [],
        "operaciones": ["_empresa(db, empresa_id): Empresa", "obtener_ventana(db, empresa_id): VentanaDevolucionOut",
            "guardar_ventana(db, empresa_id, datos: VentanaDevolucionIn): VentanaDevolucionOut"]},
    "devoluciones_web_service": {"tipo": "control", "origen": B + "devoluciones_web/service.py",
        "nota": "Módulo de funciones. Rutas en devoluciones_web/router.py: /tienda/devoluciones (CLIENTE) y /sucursal/solicitudes-devolucion (ENCARGADO de su sucursal y ADMINISTRADOR de todas).",
        "atributos": [],
        "operaciones": ["_cliente_id(db, usuario_id): int", "_venta_del_cliente(db, codigo, cliente_id): Venta",
            "_plazo(db, venta): tuple[int, datetime, bool]", "_comprometidas(db, venta_id): dict[int, int]",
            "pedido_devolvible(db, usuario_id, codigo): PedidoDevolvibleOut", "solicitar(db, usuario_id, datos: SolicitudIn): SolicitudOut",
            "solicitud_out(db, solicitud_id): SolicitudOut", "mis_solicitudes(db, usuario_id): list[SolicitudOut]",
            "solicitudes_de_sucursal(db, sucursal_id, estado): list[SolicitudOut]",
            "_solicitud_de_sucursal(db, solicitud_id, sucursal_id): SolicitudDevolucion",
            "aprobar(db, solicitud_id, usuario_id, sucursal_id, respuesta): SolicitudOut",
            "rechazar(db, solicitud_id, usuario_id, sucursal_id, respuesta): SolicitudOut",
            "recibir(db, solicitud_id, usuario_id, sucursal_id): SolicitudOut",
            "cambio_aprobado_de(db, venta_id): SolicitudDevolucion | None", "completar_con(db, solicitud, devolucion_id): None",
            "conformidad(db, usuario_id, solicitud_id, conforme, observacion): SolicitudOut",
            "nota_del_cliente(db, usuario_id, solicitud_id): NotaDevolucionOut"]},
    "notificaciones_service": {"tipo": "control", "origen": B + "notificaciones/service.py",
        "nota": "notificar() deja el aviso en la transacción, con el correo PENDIENTE u OMITIDO según el plan (verificador.incluye 'correo'); lo manda después despachar_pendientes (CU-26).",
        "atributos": [],
        "operaciones": ["notificar(db, destinatario, tipo, titulo, cuerpo, enlace, entidad, entidad_id): Notificacion",
            "avisar_devolucion_solicitada(db, solicitud): list[Notificacion]",
            "avisar_devolucion_resuelta(db, solicitud): Notificacion | None"]},
    "pasarela_pago": {"tipo": "control", "origen": "backend/app/integrations/pasarela_pago/__init__.py",
        "nota": "Fachada del proveedor configurado (simulada.py o stripe_hospedado.py). reembolsar es idempotente por la clave devolucion-web-{id}; si falla levanta ErrorDePasarela y recibir() hace rollback.",
        "atributos": [],
        "operaciones": ["obtener_proveedor(): ProveedorPasarela", "reembolsar(referencia_sesion: str, monto, clave: str): str"]},
    "BitacoraMiddleware": {"tipo": "control", "origen": B + "bitacora/middleware.py",
        "nota": "Anota toda petición POST/PUT/PATCH/DELETE (y las exportaciones GET). _anotar llama a bitacora/service.py registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
        "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response", "_anotar(peticion: Request, respuesta): None"]},

    # ---------------- ENTIDADES (almacén local) ----------------
    "prenda_inventario": {"tipo": "entidad", "origen": M + "core/almacenamiento/base_local.dart",
        "nota": "SQLite violet_offline.db (versión 3). Junto a ella está proveedor_local (id, razon_social), omitida por el tope.",
        "atributos": ["variante_id: INTEGER (PK)", "sku: TEXT", "producto: TEXT", "talla: TEXT", "color: TEXT",
            "disponible: INTEGER", "reservada: INTEGER", "stock_minimo: INTEGER"],
        "operaciones": ["guardarPaqueteInventario(paquete: PaqueteInventario): Future<void>",
            "leerPaqueteInventario(): Future<PaqueteInventario?>", "aplicarAInventario(delta: Map<int, int>): Future<void>"]},

    # ---------------- ENTIDADES (PostgreSQL) ----------------
    "Existencia": {"tipo": "entidad", "origen": B + "inventario/models.py", "tabla": "existencia", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "variante_id: BIGINT (FK variante_producto)",
            "sucursal_id: INTEGER (FK sucursal)", "cantidad_disponible: INTEGER", "cantidad_reservada: INTEGER", "stock_minimo: INTEGER"],
        "operaciones": ["obtener_existencia(db, variante_id, sucursal_id, bloquear): Existencia | None  [inventario/repository.py]",
            "obtener_existencia_con_detalle(db, existencia_id): Row | None  [inventario/repository.py]",
            "agregar_existencia(db, variante_id, sucursal_id): Existencia  [inventario/repository.py]",
            "contar_existencias(db, ...): int  [inventario/repository.py]",
            "obtener_existencia_por_id(db, existencia_id): Existencia | None  [inventario/repository.py]",
            "listar_alertas(db, sucursal_id): list[Row]  [inventario/repository.py]",
            "prendas_para_inventario(db, sucursal_id): list[Row]  [offline/repository.py]"]},
    "MovimientoInventario": {"tipo": "entidad", "origen": B + "inventario/models.py", "tabla": "movimiento_inventario",
        "nota": "Inmutable: sin actualizado_en. tipo IN (INGRESO, RESERVA, LIBERACION, VENTA, DEVOLUCION, TRANSFERENCIA, AJUSTE); cantidad con signo y <> 0.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "existencia_id: BIGINT (FK existencia)", "tipo: VARCHAR(15)",
            "cantidad: INTEGER", "motivo: VARCHAR(200)", "proveedor_id: BIGINT (FK proveedor)", "referencia: VARCHAR(40)",
            "usuario_id: BIGINT (FK usuario)", "operacion_offline_id: BIGINT (FK operacion_offline)", "creado_en: TIMESTAMPTZ"],
        "operaciones": ["agregar_movimiento(db, existencia_id, tipo, cantidad, motivo, proveedor_id, referencia, usuario_id): MovimientoInventario  [inventario/repository.py]",
            "obtener_movimiento(db, movimiento_id): Row | None  [inventario/repository.py]",
            "listar_movimientos(db, ...): list[Row]  [inventario/repository.py]",
            "kardex(db, existencia_id, pagina, tamano): tuple[int, list[Row]]  [inventario/repository.py]",
            "fisico_al_momento(db, variante_id, sucursal_id, momento): int  [offline/repository.py]",
            "unidades_de_operacion(db, operacion_id): int  [offline/repository.py]"]},
    "OperacionOffline": {"tipo": "entidad", "origen": B + "offline/models.py", "tabla": "operacion_offline",
        "nota": "tipo IN (VENTA, RESERVA, INGRESO, AJUSTE); INGRESO y AJUSTE (CU-21) van sin pago. Omitidas por espacio las columnas de devolución (devuelto_en, devuelto_por, metodo_devolucion, referencia_devolucion, observacion_devolucion, devolucion_automatica) y cliente_id.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "uuid: UUID (UNIQUE)", "tipo: VARCHAR(10)", "estado: VARCHAR(12)",
            "sucursal_id: INTEGER (FK sucursal)", "usuario_id: BIGINT (FK usuario)", "dispositivo: VARCHAR(80)", "creada_en_cliente: TIMESTAMPTZ",
            "recibida_en: TIMESTAMPTZ", "intentos: SMALLINT", "carga: JSONB", "motivo_rechazo: VARCHAR(300)"],
        "operaciones": ["operacion_por_uuid(db, uuid, bloquear): OperacionOffline | None  [offline/repository.py]"]},
    "Venta": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "venta",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(20) (UNIQUE)", "canal: VARCHAR(12)", "estado: VARCHAR(20)",
            "cliente_id: BIGINT (FK cliente)", "sucursal_id: INTEGER (FK sucursal)", "turno_caja_id: BIGINT (FK turno_caja)", "reserva_id: BIGINT (FK reserva, UNIQUE)",
            "modalidad_entrega: VARCHAR(10)", "direccion_id: BIGINT (FK direccion_cliente)", "metodo_pago: VARCHAR(20)", "subtotal: NUMERIC(10,2)",
            "descuento: NUMERIC(10,2)", "total: NUMERIC(10,2)", "entregado_en: TIMESTAMPTZ", "creado_en: TIMESTAMPTZ", "actualizado_en: TIMESTAMPTZ"],
        "operaciones": ["venta_devolvible(db, codigo, sucursal_id): Venta | None  [pos/devolucion_repository.py]",
            "bloquear_venta(db, venta_id): Venta | None  [pos/devolucion_repository.py]",
            "codigo_de_venta(db, venta_id): str | None  [pos/devolucion_repository.py]",
            "agregar_venta_presencial(db, codigo, cliente_id, sucursal_id, turno_caja_id, reserva_id, metodo_pago, subtotal, descuento, total): Venta  [pos/repository.py]",
            "venta_digital(db, codigo, bloquear): Venta | None  [devoluciones_web/repository.py]",
            "venta_por_id(db, venta_id, bloquear): Venta | None  [devoluciones_web/repository.py]"]},
    "DetalleVenta": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "detalle_venta",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta, ON DELETE CASCADE)", "variante_id: BIGINT (FK variante_producto)",
            "cantidad: INTEGER", "precio_unitario: NUMERIC(10,2)", "descuento_unitario: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ"],
        "operaciones": ["lineas_vendidas(db, venta_id): list[Row]  [pos/devolucion_repository.py]",
            "agregar_detalle(db, venta_id, variante_id, cantidad, precio_unitario, descuento_unitario): DetalleVenta  [pos/repository.py]"]},
    "TurnoCaja": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "turno_caja",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "caja_id: INTEGER (FK caja)", "usuario_id: BIGINT (FK usuario)", "abierto_en: TIMESTAMPTZ",
            "cerrado_en: TIMESTAMPTZ", "monto_apertura: NUMERIC(10,2)", "monto_cierre: NUMERIC(10,2)", "monto_esperado: NUMERIC(10,2)"],
        "operaciones": ["turno_abierto_de_usuario(db, usuario_id): TurnoCaja | None  [caja/repository.py]",
            "contexto_de_turno(db, turno_caja_id): Row  [pos/devolucion_repository.py]"]},
    "Devolucion": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "devolucion",
        "nota": "La nota de devolución (numero_nota = ND-{id:06d}, propiedad). origen CAJA exige turno; WEB va sin turno, con recibida_por y monto 0. estado ABIERTA o CERRADA; CERRADA exige conforme distinto de false (RN-20).",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta)", "turno_caja_id: BIGINT (FK turno_caja)",
            "origen: VARCHAR(6)", "recibida_por: BIGINT (FK usuario)", "reembolso_referencia: VARCHAR(100)", "reembolso_monto: NUMERIC(10,2)",
            "tipo: VARCHAR(12)", "venta_cambio_id: BIGINT (FK venta, UNIQUE)", "motivo: VARCHAR(200)", "monto: NUMERIC(10,2)",
            "diferencia: NUMERIC(10,2)", "metodo_diferencia: VARCHAR(20)", "creado_en: TIMESTAMPTZ", "estado: VARCHAR(10)",
            "conforme: BOOLEAN", "observacion_cliente: VARCHAR(300)"],
        "operaciones": ["agregar_devolucion(db, venta_id, turno_caja_id, motivo, monto, tipo, venta_cambio_id, diferencia, metodo_diferencia, observacion_cliente): Devolucion  [pos/devolucion_repository.py]",
            "devolucion_con_venta(db, devolucion_id): tuple[Devolucion | None, Venta | None]  [pos/devolucion_repository.py]",
            "Devolucion(origen='WEB', estado='ABIERTA', ...) + db.add  [devoluciones_web/service.py recibir]",
            "db.get(Devolucion, id) y cierre con conforme  [devoluciones_web/service.py conformidad]"]},
    "DetalleDevolucion": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "detalle_devolucion",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "devolucion_id: BIGINT (FK devolucion, ON DELETE CASCADE)",
            "variante_id: BIGINT (FK variante_producto)", "cantidad: INTEGER", "creado_en: TIMESTAMPTZ"],
        "operaciones": ["agregar_detalle(db, devolucion_id, variante_id, cantidad): DetalleDevolucion  [pos/devolucion_repository.py]",
            "ya_devuelto(db, venta_id): dict[int, int]  [pos/devolucion_repository.py]",
            "detalles_de(db, devolucion_id): list[DetalleDevolucion]  [pos/devolucion_repository.py]"]},
    "Empresa": {"tipo": "entidad", "origen": B + "plataforma/models.py", "tabla": "empresa", "nota": OMIT_AUD + " CHECK ventana_devolucion_horas BETWEEN 1 AND 720.",
        "atributos": ["id: BIGINT (PK)", "nombre: VARCHAR(120)", "razon_social: VARCHAR(160)", "nit: VARCHAR(30)", "slug: VARCHAR(40) (UNIQUE)",
            "correo_contacto: VARCHAR(120)", "estado: VARCHAR(10)", "logo: VARCHAR(255)", "color_principal: VARCHAR(7)",
            "color_secundario: VARCHAR(7)", "ventana_devolucion_horas: SMALLINT"],
        "operaciones": ["db.get(Empresa, empresa_id)  [plataforma/mi_tienda/service.py _empresa]",
            "db.get(Empresa, empresa_actual(db))  [pos/devolucion_service.py ventana_en_horas]"]},
    "SolicitudDevolucion": {"tipo": "entidad", "origen": B + "devoluciones_web/models.py", "tabla": "solicitud_devolucion",
        "nota": "tipo IN (DEVOLUCION, CAMBIO); estado IN (PENDIENTE, APROBADA, RECHAZADA, COMPLETADA); RECHAZADA exige respuesta.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta)", "cliente_id: BIGINT (FK cliente)",
            "sucursal_id: INTEGER (FK sucursal)", "tipo: VARCHAR(12)", "estado: VARCHAR(12)", "motivo: VARCHAR(300)", "respuesta: VARCHAR(300)",
            "atendida_por: BIGINT (FK usuario)", "atendida_en: TIMESTAMPTZ", "devolucion_id: BIGINT (FK devolucion, UNIQUE)", "creado_en: TIMESTAMPTZ"],
        "operaciones": ["solicitud(db, solicitud_id, bloquear): SolicitudDevolucion | None  [devoluciones_web/repository.py]",
            "cabecera_de_solicitud(db, solicitud_id): Row  [devoluciones_web/repository.py]",
            "ids_de_solicitudes(db, cliente_id, sucursal_id, estado): list[int]  [devoluciones_web/repository.py]",
            "cambio_aprobado(db, venta_id): SolicitudDevolucion | None  [devoluciones_web/repository.py]"]},
    "LineaSolicitudDevolucion": {"tipo": "entidad", "origen": B + "devoluciones_web/models.py", "tabla": "linea_solicitud_devolucion",
        "nota": "UNIQUE (solicitud_id, variante_id); variante_nueva_id distinta de variante_id.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "solicitud_id: BIGINT (FK solicitud_devolucion, ON DELETE CASCADE)",
            "variante_id: BIGINT (FK variante_producto)", "cantidad: INTEGER", "variante_nueva_id: BIGINT (FK variante_producto)"],
        "operaciones": ["pedido_en_solicitudes_abiertas(db, venta_id): dict[int, int]  [devoluciones_web/repository.py]",
            "lineas_de_solicitud(db, solicitud_id): list[Row]  [devoluciones_web/repository.py]",
            "opciones_de_cambio(db, variante_id, sucursal_id): list[Row]  [devoluciones_web/repository.py]"]},
    "Pago": {"tipo": "entidad", "origen": B + "pagos/models.py", "tabla": "pago",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta, UNIQUE)", "metodo: VARCHAR(12)",
            "estado: VARCHAR(12)", "monto: NUMERIC(10,2)", "referencia_externa: VARCHAR(100) (UNIQUE)", "creado_en: TIMESTAMPTZ",
            "actualizado_en: TIMESTAMPTZ"],
        "operaciones": ["db.query(Pago).filter(Pago.venta_id == venta.id).one_or_none()  [devoluciones_web/service.py recibir]"]},
    "AsientoBitacora": {"tipo": "entidad", "origen": B + "bitacora/models.py", "tabla": "bitacora",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ", "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)",
            "actor: VARCHAR(160)", "rol: VARCHAR(40)", "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
            "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)", "detalle: JSONB"],
        "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int", "listar(db, limite, desplazamiento, **filtros): list[tuple]",
            "acciones(db): list[str]", "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}

# FK reales (multiplicidad: primero en el extremo ClaseA, después en ClaseB)
FK = [
    ["Existencia", "MovimientoInventario", "SE_MUEVE_EN", "1", "0..*"],
    ["OperacionOffline", "MovimientoInventario", "ORIGINA", "0..1", "0..*"],
    ["Venta", "DetalleVenta", "CONTIENE", "1", "0..*"],
    ["TurnoCaja", "Venta", "AGRUPA", "0..1", "0..*"],
    ["TurnoCaja", "Devolucion", "PROCESA", "0..1", "0..*"],
    ["Venta", "Devolucion", "SE_DEVUELVE_EN", "1", "0..*"],
    ["Venta", "Devolucion", "SE_CAMBIA_POR", "0..1", "0..1"],
    ["Devolucion", "DetalleDevolucion", "CONTIENE", "1", "0..*"],
    ["Venta", "SolicitudDevolucion", "SE_PIDE_EN", "1", "0..*"],
    ["Devolucion", "SolicitudDevolucion", "CIERRA", "0..1", "0..1"],
    ["SolicitudDevolucion", "LineaSolicitudDevolucion", "CONTIENE", "1", "0..*"],
    ["Venta", "Pago", "SE_COBRA_CON", "1", "0..1"],
]


def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]


def bit(controles):
    return [[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles] + [["BitacoraMiddleware", "AsientoBitacora", "REGISTRA", "1", "0..*"]]


CUS = {}

c21 = ["Inventario", "PantallaInventario", "InventarioService", "ControlOffline", "inventario_service", "offline_service",
       "BitacoraMiddleware", "AsientoBitacora", "Existencia", "MovimientoInventario", "OperacionOffline", "prenda_inventario"]
CUS["CU-21"] = {"actores": ["Encargado", "Administrador"], "clases": c21,
    "operaciones_en_cu": {
        "InventarioService": ["listarExistencias(filtros)", "registrarIngreso(datos)", "registrarAjuste(datos)", "kardex(variante_id, sucursal_id, pagina, tamano)",
                              "listarMovimientos(filtros)", "fijarStockMinimo(existencia_id, stock_minimo)"],
        "ControlOffline": ["prepararInventario()", "registrarIngreso({proveedor, remito, prendas})", "registrarConteo({prenda, contado, motivo})",
                           "_guardarDeInventario({resumen, cuerpo})", "_efecto(cuerpo)", "sincronizar()"],
        "inventario_service": ["listar_existencias(...)", "registrar_ingreso(db, datos, usuario_id, confirmar, movimientos)", "registrar_ajuste(db, datos, usuario_id)",
                               "ajustar_por_diferencia(db, variante_id, sucursal_id, diferencia, motivo, usuario_id)", "kardex(db, variante_id, sucursal_id, pagina, tamano)",
                               "fijar_stock_minimo(db, existencia_id, stock_minimo)", "_aplicar_movimiento(...)", "_existencia_o_crearla(db, variante_id, sucursal_id)"],
        "offline_service": ["paquete_de_inventario(db, usuario_id, sucursal_id)", "sincronizar(...)", "_sincronizar_una(...)", "_confirmar_inventario(...)"]},
    "nota": "El mismo panel sin conexión existe en la web (InventarioOffline en inventario-offline.ts, con OfflineService.prepararInventario/registrarIngresoOffline/registrarConteoOffline y el object store 'operaciones' de IndexedDB); se omite por el tope de 12 porque repite al móvil. Omitidas también PantallaIngresoSinRed y PantallaKardex (mismo .dart), operacion_pendiente (la cola de CU-17), VarianteProducto y Proveedor. El conteo offline aplica la diferencia contra repository.fisico_al_momento, no contra el saldo del paquete.",
    "relaciones": [["Encargado", "Inventario", "USA", "1", "1"], ["Administrador", "Inventario", "USA", "1", "1"], ["Encargado", "PantallaInventario", "USA", "1", "1"],
        ["Inventario", "InventarioService", "SOLICITA", "1", "1"], ["PantallaInventario", "ControlOffline", "SOLICITA", "1", "1"],
        ["InventarioService", "inventario_service", "LLAMA_A", "1", "1"], ["ControlOffline", "offline_service", "SINCRONIZA_CON", "1", "1"],
        ["ControlOffline", "prenda_inventario", "ACTUALIZA", "1", "0..*"], ["offline_service", "inventario_service", "DELEGA_EN", "1", "1"],
        ["offline_service", "OperacionOffline", "REGISTRA", "1", "0..*"], ["offline_service", "Existencia", "CONSULTA", "1", "0..*"],
        ["inventario_service", "Existencia", "ACTUALIZA", "1", "0..*"], ["inventario_service", "MovimientoInventario", "REGISTRA", "1", "0..*"]]
        + bit(["inventario_service", "offline_service"]) + fks(c21)}

c22 = ["Devolucion_PWA", "NotaDevolucionDialogo", "DevolucionesService", "devolucion_service", "inventario_service", "BitacoraMiddleware",
       "AsientoBitacora", "Devolucion", "DetalleDevolucion", "Venta", "DetalleVenta", "TurnoCaja"]
CUS["CU-22"] = {"actores": ["Cajero"], "clases": c22,
    "operaciones_en_cu": {
        "devolucion_service": ["ventana_en_horas(db)", "_vence_en(venta, horas)", "_exigir_plazo(db, venta, cambio_aprobado)", "_por_que_solo_cambio(venta)",
                               "_aprobada_cubre(aprobada, pedidas)", "_sale_del_cajon(venta)", "_lineas_que_vuelven(...)", "buscar_venta(db, usuario_id, codigo)",
                               "registrar(db, usuario_id, datos)", "registrar_cambio(db, usuario_id, datos)", "_a_favor_de(diferencia)", "nota(db, devolucion_id, sucursal_id)"],
        "inventario_service": ["reingresar_por_devolucion(db, variante_id, sucursal_id, cantidad, usuario_id, motivo)",
                               "descontar_por_venta(db, variante_id, sucursal_id, cantidad, usuario_id, motivo, movimientos)"],
        "Venta": ["venta_devolvible(db, codigo, sucursal_id)", "bloquear_venta(db, venta_id)", "codigo_de_venta(db, venta_id)", "agregar_venta_presencial(...)"],
        "Devolucion": ["agregar_devolucion(...)", "devolucion_con_venta(db, devolucion_id)"]},
    "nota": "El turno lo resuelve pos/service.py mostrador_de (TurnoCaja vía caja/repository.py); los precios del cambio, promociones.descuentos_por_variante; la ventana, Empresa.ventana_devolucion_horas (CU-23); el cambio aprobado por la web, devoluciones_web (SolicitudDevolucion, completar_con). Omitidos por el tope: Empresa, SolicitudDevolucion, MovimientoInventario, Existencia, CajaService y PosService (Devolucion_PWA busca la prenda nueva con PosService.prendas). La conformidad viaja en DevolucionIn/CambioIn y la nota nace CERRADA y conforme.",
    "relaciones": [["Cajero", "Devolucion_PWA", "USA", "1", "1"], ["Cajero", "NotaDevolucionDialogo", "USA", "1", "1"],
        ["Devolucion_PWA", "DevolucionesService", "SOLICITA", "1", "1"], ["Devolucion_PWA", "NotaDevolucionDialogo", "ABRE", "1", "0..1"],
        ["DevolucionesService", "devolucion_service", "LLAMA_A", "1", "1"], ["NotaDevolucionDialogo", "devolucion_service", "CONSULTA", "1", "1"],
        ["devolucion_service", "inventario_service", "LLAMA_A", "1", "1"],
        ["devolucion_service", "Venta", "REGISTRA", "1", "0..*"], ["devolucion_service", "DetalleVenta", "REGISTRA", "1", "0..*"],
        ["devolucion_service", "Devolucion", "REGISTRA", "1", "0..*"], ["devolucion_service", "DetalleDevolucion", "REGISTRA", "1", "0..*"],
        ["devolucion_service", "TurnoCaja", "CONSULTA", "1", "0..1"]]
        + bit(["devolucion_service"]) + fks(c22)}

c23 = ["VentanaDevolucion", "mi_tienda_router", "mi_tienda_service", "devolucion_service", "devoluciones_web_service",
       "BitacoraMiddleware", "AsientoBitacora", "Empresa"]
CUS["CU-23"] = {"actores": ["Administrador"], "clases": c23,
    "operaciones_en_cu": {"devolucion_service": ["ventana_en_horas(db)", "_vence_en(venta, horas)", "_exigir_plazo(db, venta, cambio_aprobado)"],
                          "devoluciones_web_service": ["_plazo(db, venta)"]},
    "nota": "VentanaDevolucion habla con el backend por HttpClient, sin service del front. La ventana vale desde que se guarda, también para ventas anteriores: devolucion_service.ventana_en_horas la lee en cada pedido (si la empresa no la tiene, usa DEVOLUCION_PLAZO_DIAS * 24) y devoluciones_web_service._plazo la cuenta desde entregado_en.",
    "relaciones": [["Administrador", "VentanaDevolucion", "USA", "1", "1"], ["VentanaDevolucion", "mi_tienda_router", "SOLICITA", "1", "1"],
        ["mi_tienda_router", "mi_tienda_service", "LLAMA_A", "1", "1"], ["mi_tienda_service", "Empresa", "ACTUALIZA", "1", "1"],
        ["devolucion_service", "Empresa", "CONSULTA", "1", "1"], ["devoluciones_web_service", "devolucion_service", "LLAMA_A", "1", "1"]]
        + bit(["mi_tienda_service"]) + fks(c23)}

c24 = ["Compras", "SolicitarDevolucion", "MisSolicitudes", "devoluciones_web_service", "devolucion_service", "notificaciones_service",
       "BitacoraMiddleware", "AsientoBitacora", "SolicitudDevolucion", "LineaSolicitudDevolucion", "Venta", "DetalleVenta"]
CUS["CU-24"] = {"actores": ["Cliente"], "clases": c24,
    "operaciones_en_cu": {
        "devoluciones_web_service": ["_cliente_id(db, usuario_id)", "_venta_del_cliente(db, codigo, cliente_id)", "_plazo(db, venta)", "_comprometidas(db, venta_id)",
                                     "pedido_devolvible(db, usuario_id, codigo)", "solicitar(db, usuario_id, datos)", "solicitud_out(db, solicitud_id)",
                                     "mis_solicitudes(db, usuario_id)"],
        "devolucion_service": ["ventana_en_horas(db)"],
        "notificaciones_service": ["notificar(...)", "avisar_devolucion_solicitada(db, solicitud)"],
        "MisSolicitudes": ["ngOnInit()", "recargar()", "rotulo(estado)"],
        "Venta": ["venta_digital(db, codigo, bloquear)"],
        "DetalleVenta": ["lineas_vendidas(db, venta_id)"]},
    "nota": "Las tres interfaces llaman al backend con HttpClient (no hay service del front para devoluciones web). Lo ya devuelto sale de pos/devolucion_repository.py ya_devuelto (DetalleDevolucion, omitida por el tope); Notificacion y Empresa también omitidas. El correo al encargado lo manda después CU-26.",
    "relaciones": [["Cliente", "Compras", "USA", "1", "1"], ["Compras", "SolicitarDevolucion", "ABRE", "1", "0..1"], ["Cliente", "MisSolicitudes", "USA", "1", "1"],
        ["Compras", "MisSolicitudes", "CONTIENE", "1", "1"],
        ["SolicitarDevolucion", "devoluciones_web_service", "SOLICITA", "1", "1"], ["MisSolicitudes", "devoluciones_web_service", "CONSULTA", "1", "1"],
        ["devoluciones_web_service", "devolucion_service", "LLAMA_A", "1", "1"], ["devoluciones_web_service", "notificaciones_service", "LLAMA_A", "1", "1"],
        ["devoluciones_web_service", "Venta", "CONSULTA", "1", "0..1"], ["devoluciones_web_service", "DetalleVenta", "CONSULTA", "1", "0..*"],
        ["devoluciones_web_service", "SolicitudDevolucion", "REGISTRA", "1", "0..*"], ["devoluciones_web_service", "LineaSolicitudDevolucion", "REGISTRA", "1", "0..*"]]
        + bit(["devoluciones_web_service"]) + fks(c24)}

c25 = ["PedidosWeb", "MisSolicitudes", "devoluciones_web_service", "inventario_service", "pasarela_pago", "notificaciones_service",
       "BitacoraMiddleware", "AsientoBitacora", "SolicitudDevolucion", "Devolucion", "DetalleDevolucion", "Pago"]
CUS["CU-25"] = {"actores": ["Encargado", "Cliente"], "clases": c25,
    "operaciones_en_cu": {
        "devoluciones_web_service": ["solicitudes_de_sucursal(db, sucursal_id, estado)", "_solicitud_de_sucursal(db, solicitud_id, sucursal_id)",
                                     "aprobar(db, solicitud_id, usuario_id, sucursal_id, respuesta)", "rechazar(db, solicitud_id, usuario_id, sucursal_id, respuesta)",
                                     "recibir(db, solicitud_id, usuario_id, sucursal_id)", "conformidad(db, usuario_id, solicitud_id, conforme, observacion)",
                                     "nota_del_cliente(db, usuario_id, solicitud_id)", "solicitud_out(db, solicitud_id)"],
        "inventario_service": ["reingresar_por_devolucion(db, variante_id, sucursal_id, cantidad, usuario_id, motivo)"],
        "notificaciones_service": ["notificar(...)", "avisar_devolucion_resuelta(db, solicitud)"],
        "MisSolicitudes": ["verNota(s)", "conformidad(s, conforme, observacion)"],
        "pasarela_pago": ["reembolsar(referencia_sesion, monto, clave)"]},
    "nota": "recibir() hace todo en una transacción: nota ABIERTA de origen WEB sin turno, sus líneas, el reingreso (MovimientoInventario DEVOLUCION) y el reembolso; si la pasarela falla, rollback. Un CAMBIO aprobado no se recibe acá: lo completa la caja (CU-22, completar_con). Omitidas por el tope: Venta (venta_por_id con bloqueo), Existencia, MovimientoInventario, Notificacion y NotaDevolucionDialogo.",
    "relaciones": [["Encargado", "PedidosWeb", "USA", "1", "1"], ["Cliente", "MisSolicitudes", "USA", "1", "1"],
        ["PedidosWeb", "devoluciones_web_service", "SOLICITA", "1", "1"], ["MisSolicitudes", "devoluciones_web_service", "SOLICITA", "1", "1"],
        ["devoluciones_web_service", "inventario_service", "LLAMA_A", "1", "1"], ["devoluciones_web_service", "pasarela_pago", "LLAMA_A", "1", "1"],
        ["devoluciones_web_service", "notificaciones_service", "LLAMA_A", "1", "1"],
        ["devoluciones_web_service", "SolicitudDevolucion", "ACTUALIZA", "1", "0..*"], ["devoluciones_web_service", "Devolucion", "REGISTRA", "1", "0..*"],
        ["devoluciones_web_service", "DetalleDevolucion", "REGISTRA", "1", "0..*"], ["devoluciones_web_service", "Pago", "CONSULTA", "1", "0..1"]]
        + bit(["devoluciones_web_service"]) + fks(c25)}

# ------------------------------------------------------------------ 2.6 ---
ESPEC = {
    'CU-21': {
        'descripcion': 'Permite al encargado consultar la existencia de su sucursal, registrar ingresos de mercadería y ajustes por '
                       'conteo físico, también sin conexión, y ver el kardex de cada prenda.',
        'actores': 'Encargado de sucursal, administrador de la empresa',
        'iniciador': 'Encargado de sucursal',
        'precondiciones': 'El encargado inició sesión y su cuenta está asignada a una sucursal. Para trabajar sin conexión, antes '
                          'pulsó «Preparar sin conexión» con red.',
        'flujo': [
            'El encargado abre la pantalla «Inventario».',
            'El sistema muestra las existencias de su sucursal, paginadas, con lo disponible, lo reservado, lo que hay en el local y el mínimo.',
            'El encargado elige una prenda y pulsa «Ajustar por conteo físico» (en el móvil, «Contar»).',
            'El encargado ingresa las unidades contadas, reservadas incluidas, y el motivo.',
            'El sistema compara lo contado con lo que hay en el local (disponible más reservado) y calcula la diferencia.',
            'El sistema aplica la diferencia al disponible y registra un movimiento AJUSTE con el motivo, el usuario y la fecha, en una sola transacción.',
            'El sistema anota la operación en la bitácora y muestra el saldo nuevo.',
        ],
        'alternativos': [
            '3a. Registrar ingreso: el encargado pulsa «Registrar ingreso», elige el proveedor, el remito y las prendas con su cantidad; el sistema '
            'sube los saldos y deja un movimiento INGRESO por prenda.',
            '3b. Ver el kardex: el encargado pulsa «Ver el kardex»; el sistema muestra cada movimiento de la prenda (ingresos, ventas, reservas, '
            'traspasos, devoluciones y ajustes) con el saldo que dejó y la marca «Registrado sin conexión» cuando corresponde.',
            '4a. Sin conexión: el conteo o el ingreso se guarda en el dispositivo con su UUID y corrige el saldo local; al volver la red se '
            'sincroniza (incluye CU-17) y el servidor aplica solo la diferencia contra lo que había en el local a la hora del conteo.',
            '5a. Conteo sin diferencia o menor que lo reservado: el sistema rechaza el ajuste y no escribe nada; sin conexión, la operación '
            'queda rechazada con su motivo.',
        ],
        'postcondiciones': 'El saldo de la prenda es la suma de sus movimientos y cada cambio queda con su motivo, su usuario y su fecha. '
                           'Lo registrado sin conexión queda confirmado o rechazado en la cola del dispositivo.',
        'rastreo': 'RF-52, RF-53 · RN-07',
    },
    'CU-22': {
        'descripcion': 'Permite al cajero recibir en caja una prenda vendida, devolviendo el dinero o cambiándola por otra prenda o talla '
                       'con la diferencia de precio, y emitir la nota de devolución con la conformidad del cliente.',
        'actores': 'Cajero, encargado de sucursal',
        'iniciador': 'Cajero',
        'precondiciones': 'El cajero tiene un turno de caja abierto. La venta es de su sucursal y está pagada o entregada.',
        'flujo': [
            'El cajero abre «Devoluciones y cambios» e ingresa el código de la venta.',
            'El sistema muestra lo vendido, lo que ya volvió, lo que se puede devolver, el precio pagado y hasta cuándo rige la ventana de la empresa.',
            'El cajero elige las prendas y cantidades que vuelven y escribe el motivo.',
            'El cliente da su conformidad; el cajero la marca y anota su observación.',
            'El cajero pulsa «Registrar devolución».',
            'El sistema verifica la ventana, bloquea la venta y registra la devolución con su detalle; el dinero sale del cajón solo si la venta se cobró en efectivo.',
            'El sistema reingresa cada prenda al inventario con un movimiento DEVOLUCION y anota la operación en la bitácora.',
            'El sistema muestra el comprobante con el número de nota (ND-…), que se puede ver e imprimir.',
        ],
        'alternativos': [
            '3a. Cambio de prenda: el cajero elige «Cambiar por otra» y agrega lo que el cliente se lleva; el sistema calcula la diferencia con '
            'los precios y ofertas vigentes, la cobra o la devuelve por el método elegido y crea una venta nueva pagada con «CAMBIO» (RN-17).',
            '6a. Fuera de la ventana: el sistema rechaza e informa cuándo venció (RN-08), salvo un cambio ya aprobado por la web (CU-25).',
            '6b. Solo cambio: si la venta salió de un cambio (RN-23) o es un pedido web, el sistema no devuelve dinero y solo admite el cambio.',
            '6c. Devuelve de más: si otra caja devolvió parte en el medio, el sistema rechaza y vuelve a cargar la venta.',
        ],
        'postcondiciones': 'La nota queda cerrada con la conformidad del cliente (RN-20). El inventario y el arqueo del turno quedan '
                           'coherentes con lo que entró y salió.',
        'rastreo': 'RF-24, RF-37, RF-59 · RN-08, RN-17, RN-20, RN-23',
    },
    'CU-23': {
        'descripcion': 'Permite al administrador de la empresa fijar cuántas horas después de la compra o de la entrega se aceptan '
                       'cambios y devoluciones, en caja y por la web.',
        'actores': 'Administrador de la empresa',
        'iniciador': 'Administrador de la empresa',
        'precondiciones': 'El administrador inició sesión en su empresa. La función no depende del plan.',
        'flujo': [
            'El administrador abre «Mi tienda».',
            'El sistema muestra la tarjeta «Ventana de devolución» con las horas vigentes (48 si nunca se cambió).',
            'El administrador escribe las horas.',
            'El sistema muestra el plazo en días cuando es exacto.',
            'El administrador pulsa «Guardar».',
            'El sistema verifica que sea un entero entre 1 y 720 horas y lo guarda en la empresa.',
            'El sistema anota el cambio en la bitácora y confirma la ventana nueva.',
        ],
        'alternativos': [
            '3a. Atajo: el administrador pulsa «24 h», «48 h» o «72 h» y el campo toma ese valor.',
            '6a. Valor fuera de rango: la pantalla no habilita «Guardar» y, si llega al servidor, este lo rechaza con el rango permitido.',
            '7a. Efecto inmediato: la ventana rige desde ya, también para las ventas anteriores, porque la caja (CU-22) y la web (CU-24) '
            'calculan el plazo al momento del pedido.',
        ],
        'postcondiciones': 'La empresa queda con su ventana de devolución; fuera de ella, los cambios y devoluciones se rechazan (RN-08).',
        'rastreo': 'RF-35 · RN-08',
    },
    'CU-24': {
        'descripcion': 'Permite al cliente pedir desde la tienda en línea el cambio o la devolución de prendas de un pedido ya '
                       'entregado, dentro de la ventana de la empresa.',
        'actores': 'Cliente',
        'iniciador': 'Cliente',
        'precondiciones': 'El cliente inició sesión. El pedido es suyo, se compró por la web y está entregado.',
        'flujo': [
            'El cliente abre «Mis compras» y pulsa «Cambio o devolución» en un pedido.',
            'El sistema muestra, por prenda, lo comprado, lo ya comprometido, lo que se puede pedir, el precio pagado y hasta cuándo rige la ventana desde la entrega.',
            'El cliente elige «Devolver», las prendas y cantidades, y escribe el motivo.',
            'El cliente pulsa «Enviar solicitud».',
            'El sistema bloquea el pedido y verifica la ventana y que las cantidades no superen lo que queda.',
            'El sistema registra la solicitud pendiente con sus líneas.',
            'El sistema avisa a los encargados de la sucursal (incluye CU-26) y anota la operación en la bitácora.',
            'El cliente ve la solicitud en «Mis cambios y devoluciones».',
        ],
        'alternativos': [
            '3a. Cambio: el cliente elige «Cambiar talla o color» y, por prenda, otra talla o color del mismo producto con saldo en la '
            'sucursal; el sistema muestra la diferencia que se cobrará o devolverá (RF-59).',
            '5a. Fuera de plazo: el sistema rechaza e informa la fecha y la hora en que venció la ventana (RN-08).',
            '5b. Pedido no entregado: el sistema no deja pedir nada hasta que la sucursal lo marque como entregado.',
            '5c. Cantidad de más o cambio inválido: el sistema rechaza si pide más de lo que queda, o si la prenda elegida no es del mismo '
            'producto o no hay en la sucursal.',
        ],
        'postcondiciones': 'La solicitud queda pendiente. Mientras esté abierta, esas unidades no se pueden volver a pedir ni traer a caja.',
        'rastreo': 'RF-34, RF-59 · RN-08',
    },
    'CU-25': {
        'descripcion': 'Permite al encargado aprobar o rechazar con su motivo las solicitudes web de su sucursal y, al recibir la prenda '
                       'de una devolución, registrar la nota, reingresar la prenda y reembolsar por la pasarela.',
        'actores': 'Encargado de sucursal, cliente',
        'iniciador': 'Encargado de sucursal',
        'precondiciones': 'Hay una solicitud pendiente en la sucursal del encargado (CU-24).',
        'flujo': [
            'El encargado abre «Pedidos web» y ve las solicitudes con sus prendas, el motivo y la diferencia.',
            'El encargado escribe una respuesta opcional y pulsa «Aprobar».',
            'El sistema deja la solicitud aprobada con quién y cuándo, avisa al cliente (incluye CU-26) y anota en la bitácora.',
            'Cuando la prenda llega, el encargado pulsa «Prenda recibida: reembolsar».',
            'El sistema registra la nota de devolución abierta, de origen web y sin turno de caja, con su detalle, y reingresa cada prenda al inventario.',
            'El sistema reembolsa lo pagado por la pasarela, por el mismo medio, y guarda la referencia del reembolso.',
            'El sistema marca la solicitud como completada y avisa al cliente.',
            'El cliente revisa la nota en «Mis cambios y devoluciones» y pulsa «Estoy conforme»; el sistema cierra la nota (RN-20).',
        ],
        'alternativos': [
            '2a. Rechazar: el encargado escribe el motivo (al menos 5 letras) y pulsa «Rechazar»; la solicitud queda rechazada y el cliente ve el motivo.',
            '4a. Cambio aprobado: no se recibe acá; el cliente lo retira en caja, donde se salda la diferencia y la solicitud se completa (CU-22).',
            '6a. Falla la pasarela: el sistema deshace todo (ni nota ni reingreso) e informa el detalle.',
            '8a. No conforme: el cliente pulsa «No estoy conforme»; la nota queda abierta con su observación, a la vista del encargado.',
        ],
        'postcondiciones': 'La solicitud queda rechazada o completada. Si se completó, la prenda volvió al inventario, el reembolso quedó '
                           'registrado y la nota se cierra solo con la conformidad del cliente.',
        'rastreo': 'RF-36, RF-37 · RN-20',
    },
}


# ------------------------------------------------------------- validación ---
ACTORES_VALIDOS = {'Administrador de la plataforma', 'Administrador de la empresa', 'Encargado de sucursal', 'Cajero', 'Cliente',
                   'Proveedor', 'Sistema', 'Usuario', 'Empresa interesada'}
NOMBRES_2_5 = {
    'CU-21': 'Gestionar el inventario de la sucursal', 'CU-22': 'Registrar cambio o devolución en caja',
    'CU-23': 'Configurar la ventana de devolución', 'CU-24': 'Solicitar cambio o devolución por la web',
    'CU-25': 'Atender solicitud de devolución',
}


def validar():
    ids = {c[0] for c in CASOS}
    for c in CASOS:
        assert c[1] == NOMBRES_2_5[c[0]], (c[0], c[1])
        assert set(c[2]) <= ACTORES_VALIDOS, (c[0], c[2])
        for x in c[3] + (c[5] if len(c) > 5 else []):
            assert re.fullmatch(r'CU-\d\d', x), (c[0], x)
    for r in ROBUSTEZ:
        assert r['cu'] in ids, r['cu']
        assert r['n'] == NOMBRES_2_5[r['cu']], r['cu']
        assert 1 <= len(r['grupos']) <= 5, r['cu']
        assert r['c'][0].startswith('Gestor'), r['cu']
        tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
                 **{x: 'C' for x in r['c']}, **{x: 'E' for x in r['e']}}
        grupos = sorted({g for g, *_ in r['m']})
        assert grupos == list(range(1, len(r['grupos']) + 1)), (r['cu'], grupos)
        for g, de, a, op in r['m']:
            assert de in tipos and a in tipos, (r['cu'], de, a)
            par = {tipos[de], tipos[a]}
            # la regla de la ing: nunca entidad con entidad; tampoco frontera con frontera
            assert par in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'}), (r['cu'], de, a, op)
        usados = {p for _, de, a, _ in r['m'] for p in (de, a)}
        assert usados == set(tipos), (r['cu'], set(tipos) - usados)
        # F3: si hay bitácora, con sus dos mensajes
        if 'BitacoraMiddleware' in r['c']:
            ops = [(de, a, op) for _, de, a, op in r['m']]
            assert any(a == 'BitacoraMiddleware' and op.startswith('registrar(') for de, a, op in ops), r['cu']
            assert any(de == 'BitacoraMiddleware' and a == 'AsientoBitacora' and op.startswith('agregar(') for de, a, op in ops), r['cu']
    # DESCRIPCION: solo nombres que aparecen en alguna robustez
    todos = {x for r in ROBUSTEZ for x in r['f'] + r['c'] + r['e']}
    assert set(DESCRIPCION) <= todos, set(DESCRIPCION) - todos


def validar_clases():
    for cu, d in CUS.items():
        assert 6 <= len(d["clases"]) <= 12, (cu, len(d["clases"]))
        for c in d["clases"]:
            assert c in CLASES, (cu, c)
        for r in d["relaciones"]:
            for x in r[:2]:
                assert x in d["clases"] or x in d["actores"], (cu, r)
        for c in d.get("operaciones_en_cu", {}):
            assert c in d["clases"], (cu, c)
        if "BitacoraMiddleware" in d["clases"]:
            assert "AsientoBitacora" in d["clases"], cu
            assert any(r[2] == "ES_ANOTADO_POR" for r in d["relaciones"]), cu
    for n, c in CLASES.items():
        assert c["tipo"] in ("interfaz", "control", "entidad"), n
        if c["tipo"] == "entidad" and c["origen"].endswith(".py") and "bitacora" not in c["origen"]:
            assert c["atributos"][0].startswith("id: ") and "(PK)" in c["atributos"][0], n


def validar_espec():
    claves = {'descripcion', 'actores', 'iniciador', 'precondiciones', 'flujo', 'alternativos', 'postcondiciones', 'rastreo'}
    assert set(ESPEC) == {c[0] for c in CASOS}, set(ESPEC)
    for cu, f in ESPEC.items():
        assert set(f) == claves, (cu, claves ^ set(f))
        assert 5 <= len(f['flujo']) <= 10, (cu, len(f['flujo']))
        assert 2 <= len(f['alternativos']) <= 5, (cu, len(f['alternativos']))
        for a in f['alternativos']:
            assert re.match(r'^\d+[a-z]\. [^:]+: ', a), (cu, a)
        assert re.fullmatch(r'RF-\d\d(, RF-\d\d)*( · RN-\d\d(, RN-\d\d)*)?', f['rastreo']), (cu, f['rastreo'])


if __name__ == '__main__':
    validar()
    validar_clases()
    validar_espec()
    for cu, d in CUS.items():
        print(cu, len(d["clases"]), 'clases,', len(d["relaciones"]), 'relaciones')
    print('ok:', len(CASOS), 'casos,', len(ROBUSTEZ), 'robusteces,', len(CLASES), 'clases,', len(DESCRIPCION), 'descripciones nuevas')
