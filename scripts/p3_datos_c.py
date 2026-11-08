# Datos de la 3ra presentación, grupo c: CU-31 a CU-35 (ofertas, mayoristas y traspasos).
# Sacados del código de origin/main:
#   - backend/app/modules/catalogo/ofertas_*.py y promociones_*.py (CU-31, CU-32);
#   - backend/app/core/tareas.py (la tarea automática que dispara CU-32);
#   - backend/app/modules/traspasos/*.py (CU-33, CU-34, CU-35; NO está en abastecimiento, que es del
#     proveedor, CU-39 del 1er parcial);
#   - frontend-web/src/app/features/admin/ofertas, features/admin/promociones y
#     features/sucursal/traspasos (la misma pantalla para el Encargado y el Administrador).
# Módulo autónomo: define CASOS, ROBUSTEZ, DESCRIPCION, CLASES, CUS y ESPEC con los formatos de
# scripts/p2_datos.py y scripts/p2_clases_datos.py.
# Uso: python -X utf8 scripts/p3_datos_c.py   (solo valida)

B = "backend/app/modules/"
C = "backend/app/core/"
W = "frontend-web/src/app/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."

# ------------------------------------------------------------------ 2.5 ---
CASOS = [
    # (id, nombre, actores, incluye, notas[, extiende])
    ('CU-31', 'Gestionar ofertas y precios mayoristas', ['Administrador de la empresa'], [],
     'Reemplaza al CU-12 del primer parcial. Escalones de precio mayorista por producto (desde N prendas, '
     'a Bs X cada una) y las ofertas manuales con su vigencia, que siguen siendo las promociones. '
     'RF-56, RF-58, RN-15.'),
    ('CU-32', 'Aplicar ofertas de fuera de temporada', ['Sistema', 'Administrador de la empresa'], [],
     'La tarea automática del backend crea una promoción AUTOMATICA para cada producto que cumple el factor '
     'guardado en la base (días desde el fin de la temporada y existencia sobrante) y cierra las que dejan '
     'de cumplirlo. El administrador configura el factor y puede apagar cada oferta. RF-57, RN-16.'),
    ('CU-33', 'Solicitar traspaso entre sucursales', ['Encargado de sucursal', 'Administrador de la empresa'],
     ['CU-05'],
     'Reemplaza al CU-15 del primer parcial. El encargado pide a otra sucursal y queda SOLICITADO; el '
     'administrador lo ordena sin pedido previo y nace APROBADO. Con la suscripción vencida no se registra '
     '(RN-03). RF-39, RF-40.',
     # Ordenar una sugerencia (7a de CU-35) es registrar un traspaso con desde_sugerencia.
     ['CU-35']),
    ('CU-34', 'Atender traspaso', ['Encargado de sucursal'], ['CU-05'],
     'Seguimiento y pasos del traspaso: aprobar, enviar (descuenta del origen), recibir (suma al destino) o '
     'rechazar, con su movimiento de inventario. RF-41, RN-09.'),
    ('CU-35', 'Consultar traspasos sugeridos', ['Administrador de la empresa'], ['CU-05'],
     'Calcula qué mover de dónde a dónde con las ventas del período y la existencia de cada sucursal. Lo '
     'controla la función traspasos_sugeridos del plan. RF-42.'),
]

# ------------------------------------------------------------------ 3.2 ---
AE, EN = 'A:Administrador de la empresa', 'A:Encargado de sucursal'
SI = 'A:Sistema'

ROBUSTEZ = [
    dict(cu='CU-31', n='Gestionar ofertas y precios mayoristas', a=['Administrador de la empresa'],
         f=['PantallaOfertas', 'PantallaPromociones'],
         c=['GestorOfertas', 'GestorPromociones', 'GestorAutenticacion', 'BitacoraMiddleware'],
         e=['PrecioMayorista', 'Producto', 'VarianteProducto', 'Promocion', 'AsientoBitacora'],
         grupos=['flujo principal: definir un precio mayorista',
                 'alternativo 3a: editar, apagar o encender un escalón',
                 'alternativo 6a: el escalón ya existe o el precio no es menor',
                 'alternativo 1a: oferta manual con vigencia (RF-58)'],
         m=[(1, AE, 'PantallaOfertas', 'abrirOfertas()'),
            (1, 'PantallaOfertas', 'GestorOfertas', 'listarMayoristas(busqueda, pagina, tamano)'),
            (1, 'GestorOfertas', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorOfertas', 'PrecioMayorista', 'listarMayoristas(busqueda, pagina, tamano)'),
            (1, 'GestorOfertas', 'PantallaOfertas', 'mostrarMayoristas(escalones)'),
            (1, AE, 'PantallaOfertas', 'elegirProducto(producto)'),
            (1, AE, 'PantallaOfertas', 'guardar(cantidadMinima, precioUnitario)'),
            (1, 'PantallaOfertas', 'GestorOfertas', 'crearMayorista(datos)'),
            (1, 'GestorOfertas', 'Producto', 'producto(idProducto)'),
            (1, 'GestorOfertas', 'PrecioMayorista', 'existeEscalon(idProducto, cantidadMinima)'),
            (1, 'GestorOfertas', 'VarianteProducto', 'precioMinimoDelProducto(idProducto)'),
            (1, 'GestorOfertas', 'PrecioMayorista', 'agregar(escalon)'),
            (1, 'GestorOfertas', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorOfertas', 'PantallaOfertas', 'confirmar(escalon)'),
            (2, AE, 'PantallaOfertas', 'editar(escalon)'),
            (2, 'PantallaOfertas', 'GestorOfertas', 'editarMayorista(id, datos)'),
            (2, 'GestorOfertas', 'PrecioMayorista', 'guardar(cantidadMinima, precioUnitario)'),
            (2, AE, 'PantallaOfertas', 'cambiarEstado(escalon, activo)'),
            (2, 'PantallaOfertas', 'GestorOfertas', 'cambiarEstadoMayorista(id, activo)'),
            (2, 'GestorOfertas', 'PrecioMayorista', 'cambiarEstado(activo)'),
            (3, 'GestorOfertas', 'PantallaOfertas', 'escalonRepetido(cantidadMinima)'),
            (3, 'GestorOfertas', 'PantallaOfertas', 'precioNoEsMenor(precioMinimo)'),
            (4, AE, 'PantallaPromociones', 'nueva(nombre, alcance, objetivo, porcentaje, desde, hasta)'),
            (4, 'PantallaPromociones', 'GestorPromociones', 'crear(datos)'),
            (4, 'GestorPromociones', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (4, 'GestorPromociones', 'Promocion', 'existeNombre(nombre)'),
            (4, 'GestorPromociones', 'Promocion', 'agregar(promocion)'),
            (4, 'GestorPromociones', 'BitacoraMiddleware', 'registrar(peticion)'),
            (4, 'GestorPromociones', 'PantallaPromociones', 'confirmar(promocion)')]),

    dict(cu='CU-32', n='Aplicar ofertas de fuera de temporada', a=['Sistema', 'Administrador de la empresa'],
         f=['TareaProgramada', 'PantallaOfertas'],
         c=['GestorOfertas', 'GestorAutenticacion', 'BitacoraMiddleware'],
         e=['ReglaFueraDeTemporada', 'Producto', 'Temporada', 'Existencia', 'Promocion', 'AsientoBitacora'],
         grupos=['flujo principal: la tarea automática crea y cierra las ofertas',
                 'alternativo 2a: la regla está apagada',
                 'alternativo 4a: el producto ya tiene su oferta automática',
                 'alternativo 1a: el administrador guarda el factor o aplica a mano'],
         m=[(1, SI, 'TareaProgramada', 'correrVuelta()'),
            (1, 'TareaProgramada', 'GestorOfertas', 'aplicar(empresa)'),
            (1, 'GestorOfertas', 'ReglaFueraDeTemporada', 'regla()'),
            (1, 'GestorOfertas', 'GestorOfertas', 'calcularHastaFin(hoy, diasDesdeFin)'),
            (1, 'GestorOfertas', 'Producto', 'candidatasFueraDeTemporada(hastaFin, existenciaMinima)'),
            (1, 'GestorOfertas', 'Temporada', 'fechaFin(producto)'),
            (1, 'GestorOfertas', 'Existencia', 'disponibleEnSucursalesActivas(producto)'),
            (1, 'GestorOfertas', 'Promocion', 'automaticaDe(producto)'),
            (1, 'GestorOfertas', 'Promocion', 'agregar("AUTOMATICA", producto, porcentaje, hoy)'),
            (1, 'GestorOfertas', 'Promocion', 'automaticasVigentes()'),
            (1, 'GestorOfertas', 'Promocion', 'cerrar(ayer, cerradaPorRegla)'),
            (1, 'GestorOfertas', 'TareaProgramada', 'resultado(creadas, cerradas)'),
            (2, 'GestorOfertas', 'GestorOfertas', 'omitirCreacion()'),
            (2, 'GestorOfertas', 'Promocion', 'automaticasVigentes()'),
            (2, 'GestorOfertas', 'Promocion', 'cerrar(ayer, cerradaPorRegla)'),
            (3, 'GestorOfertas', 'Promocion', 'promocion(idPromocion)'),
            (3, 'GestorOfertas', 'GestorOfertas', 'respetarSiLaApagoElAdministrador()'),
            (3, 'GestorOfertas', 'Promocion', 'reabrir(hoy, porcentaje)'),
            (4, AE, 'PantallaOfertas', 'guardarRegla(activa, diasDesdeFin, existenciaMinima, porcentaje)'),
            (4, 'PantallaOfertas', 'GestorOfertas', 'guardarRegla(datos)'),
            (4, 'GestorOfertas', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (4, 'GestorOfertas', 'ReglaFueraDeTemporada', 'guardar(regla)'),
            (4, AE, 'PantallaOfertas', 'aplicar()'),
            (4, 'PantallaOfertas', 'GestorOfertas', 'aplicar()'),
            (4, 'GestorOfertas', 'BitacoraMiddleware', 'registrar(peticion)'),
            (4, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, ruta)'),
            (4, 'GestorOfertas', 'PantallaOfertas', 'mostrarAplicacion(creadas, cerradas, candidatas)')]),

    dict(cu='CU-33', n='Solicitar traspaso entre sucursales',
         a=['Encargado de sucursal', 'Administrador de la empresa'],
         f=['PantallaTraspasos'],
         c=['GestorTraspasos', 'GestorAutenticacion', 'GestorInventario', 'GestorNotificaciones',
            'BitacoraMiddleware'],
         e=['Existencia', 'VarianteProducto', 'Sucursal', 'Traspaso', 'Usuario', 'Notificacion',
            'AsientoBitacora'],
         grupos=['flujo principal: el encargado pide a otra sucursal',
                 'alternativo 1a: el administrador ordena sin pedido previo',
                 'alternativo 5a: sucursal o prenda dada de baja',
                 'alternativos 6a y 6b: no alcanza en el origen o ya hay un traspaso abierto'],
         m=[(1, EN, 'PantallaTraspasos', 'buscarPrenda(texto)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'prendasPedibles(busqueda)'),
            (1, 'GestorTraspasos', 'GestorAutenticacion', 'autorizar("ENCARGADO")'),
            (1, 'GestorTraspasos', 'Existencia', 'prendasEnOtras(busqueda, excluir)'),
            (1, 'GestorTraspasos', 'PantallaTraspasos', 'mostrarPrendas(prendas)'),
            (1, EN, 'PantallaTraspasos', 'elegirPrenda(prenda)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'origenesPosibles(idVariante)'),
            (1, 'GestorTraspasos', 'Existencia', 'origenesPosibles(idVariante, excluir)'),
            (1, 'GestorTraspasos', 'PantallaTraspasos', 'mostrarOrigenes(origenes)'),
            (1, EN, 'PantallaTraspasos', 'pedir(origen, cantidad, motivo)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'solicitar(datos)'),
            (1, 'GestorTraspasos', 'GestorInventario', 'sucursalActiva(idOrigen, idDestino)'),
            (1, 'GestorInventario', 'Sucursal', 'obtenerSucursal(id)'),
            (1, 'GestorTraspasos', 'GestorInventario', 'variantesValidas([idVariante])'),
            (1, 'GestorInventario', 'VarianteProducto', 'obtenerVariantes(ids)'),
            (1, 'GestorTraspasos', 'Existencia', 'disponible(idVariante, idOrigen)'),
            (1, 'GestorTraspasos', 'Traspaso', 'hayAbierto(idVariante, idOrigen, idDestino)'),
            (1, 'GestorTraspasos', 'Traspaso', 'agregar("PEDIDO", "SOLICITADO", datos)'),
            (1, 'GestorTraspasos', 'GestorNotificaciones', 'avisarTraspaso(traspaso, idOrigen, titulo, cuerpo)'),
            (1, 'GestorNotificaciones', 'Usuario', 'encargadosDe(idOrigen)'),
            (1, 'GestorNotificaciones', 'Notificacion', 'crear(destinatario, "TRASPASO", titulo, cuerpo)'),
            (1, 'GestorTraspasos', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorTraspasos', 'PantallaTraspasos', 'confirmar(traspaso)'),
            (2, AE, 'PantallaTraspasos', 'ordenar(origen, destino, cantidad, motivo)'),
            (2, 'PantallaTraspasos', 'GestorTraspasos', 'solicitar(datos)'),
            (2, 'GestorTraspasos', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (2, 'GestorTraspasos', 'Traspaso', 'agregar("ORDEN", "APROBADO", aprobadoPor)'),
            (2, 'GestorTraspasos', 'GestorNotificaciones', 'avisarTraspaso(traspaso, idOrigen, titulo, cuerpo)'),
            (3, 'GestorInventario', 'GestorTraspasos', 'sucursalOPrendaInactiva()'),
            (3, 'GestorTraspasos', 'PantallaTraspasos', 'rechazarPedido(motivo)'),
            (4, 'GestorTraspasos', 'PantallaTraspasos', 'existenciaInsuficiente(disponible, pedido)'),
            (4, 'GestorTraspasos', 'PantallaTraspasos', 'traspasoAbierto(origen, destino)')]),

    dict(cu='CU-34', n='Atender traspaso', a=['Encargado de sucursal'],
         f=['PantallaTraspasos'],
         c=['GestorTraspasos', 'GestorAutenticacion', 'GestorInventario', 'GestorNotificaciones',
            'BitacoraMiddleware'],
         e=['Traspaso', 'Existencia', 'MovimientoInventario', 'Sucursal', 'Usuario', 'Notificacion',
            'AsientoBitacora'],
         grupos=['flujo principal: aprobar, enviar y recibir',
                 'alternativo 3a: rechazar o retirar el pedido',
                 'alternativo 4a: ya no alcanza en el origen',
                 'alternativo 4b: el paso le toca a la otra sucursal o el traspaso cambió',
                 'alternativo 5a: el destino se dio de baja con la mercadería en camino'],
         m=[(1, EN, 'PantallaTraspasos', 'abrirSeguimiento(bandeja, abiertos)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'listar(bandeja, estado, abiertos, pagina)'),
            (1, 'GestorTraspasos', 'GestorAutenticacion', 'autorizar("ENCARGADO")'),
            (1, 'GestorTraspasos', 'Traspaso', 'listar(sucursal, bandeja, abiertos)'),
            (1, 'GestorTraspasos', 'GestorTraspasos', 'acciones(traspaso, quien)'),
            (1, 'GestorTraspasos', 'PantallaTraspasos', 'mostrarTraspasos(traspasos)'),
            (1, EN, 'PantallaTraspasos', 'aprobar(traspaso, cantidad)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'aprobar(id, cantidad)'),
            (1, 'GestorTraspasos', 'Traspaso', 'obtener(id, bloquear)'),
            (1, 'GestorTraspasos', 'Existencia', 'disponible(idVariante, idOrigen)'),
            (1, 'GestorTraspasos', 'Traspaso', 'marcarAprobado(cantidad, usuario)'),
            (1, EN, 'PantallaTraspasos', 'enviar(traspaso)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'enviar(id)'),
            (1, 'GestorTraspasos', 'Sucursal', 'obtenerSucursal(idOrigen, idDestino)'),
            (1, 'GestorTraspasos', 'Existencia', 'obtenerExistencia(idVariante, idOrigen, bloquear)'),
            (1, 'GestorTraspasos', 'GestorInventario', 'aplicarMovimiento(existencia, "TRANSFERENCIA", -cantidad)'),
            (1, 'GestorInventario', 'Existencia', 'descontar(cantidad)'),
            (1, 'GestorInventario', 'MovimientoInventario', 'agregar("TRANSFERENCIA", -cantidad, referencia)'),
            (1, 'GestorTraspasos', 'Traspaso', 'marcarEnviado(usuario, movimientoSalida)'),
            (1, 'GestorTraspasos', 'GestorNotificaciones', 'avisarTraspaso(traspaso, idDestino, titulo, cuerpo)'),
            (1, 'GestorNotificaciones', 'Usuario', 'encargadosDe(sucursal)'),
            (1, 'GestorNotificaciones', 'Notificacion', 'crear(destinatario, "TRASPASO", titulo, cuerpo)'),
            (1, EN, 'PantallaTraspasos', 'recibir(traspaso)'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'recibir(id)'),
            (1, 'GestorTraspasos', 'GestorInventario', 'existenciaOCrearla(idVariante, idDestino)'),
            (1, 'GestorTraspasos', 'GestorInventario', 'aplicarMovimiento(existencia, "TRANSFERENCIA", cantidad)'),
            (1, 'GestorInventario', 'Existencia', 'sumar(cantidad)'),
            (1, 'GestorInventario', 'MovimientoInventario', 'agregar("TRANSFERENCIA", cantidad, referencia)'),
            (1, 'GestorTraspasos', 'Traspaso', 'marcarRecibido(usuario, movimientoEntrada)'),
            (1, 'GestorTraspasos', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorTraspasos', 'PantallaTraspasos', 'confirmar(traspaso)'),
            (2, EN, 'PantallaTraspasos', 'rechazar(traspaso, motivo)'),
            (2, 'PantallaTraspasos', 'GestorTraspasos', 'rechazar(id, motivo)'),
            (2, 'GestorTraspasos', 'Traspaso', 'marcarRechazado(usuario, motivo)'),
            (2, 'GestorTraspasos', 'GestorNotificaciones', 'avisarTraspaso(traspaso, otraSucursal, titulo, motivo)'),
            (3, 'GestorInventario', 'GestorTraspasos', 'stockInsuficiente(disponible, solicitado)'),
            (3, 'GestorTraspasos', 'GestorTraspasos', 'revertirTransaccion()'),
            (3, 'GestorTraspasos', 'PantallaTraspasos', 'existenciaInsuficiente(disponible, cantidad)'),
            (4, 'GestorTraspasos', 'PantallaTraspasos', 'pasoNoPermitido(estado)'),
            (4, 'PantallaTraspasos', 'GestorTraspasos', 'listar(bandeja, estado, abiertos, pagina)'),
            (5, EN, 'PantallaTraspasos', 'recibirDeVuelta(traspaso)'),
            (5, 'PantallaTraspasos', 'GestorTraspasos', 'devolver(id)'),
            (5, 'GestorTraspasos', 'GestorInventario', 'aplicarMovimiento(existenciaOrigen, "TRANSFERENCIA", cantidad)'),
            (5, 'GestorTraspasos', 'Traspaso', 'marcarRecibido(usuario, movimientoEntrada)')]),

    dict(cu='CU-35', n='Consultar traspasos sugeridos', a=['Administrador de la empresa'],
         f=['PantallaTraspasos'],
         c=['GestorTraspasos', 'GestorAutenticacion', 'VerificadorPlan', 'BitacoraMiddleware'],
         e=['Plan', 'Venta', 'Sucursal', 'Existencia', 'Traspaso', 'VarianteProducto', 'AsientoBitacora'],
         grupos=['flujo principal: calcular y mostrar las sugerencias',
                 'alternativo 2a: el plan no incluye la función',
                 'alternativo 3a: cambiar el período o recalcular',
                 'alternativo 7a: ordenar una sugerencia (extiende CU-33)'],
         m=[(1, AE, 'PantallaTraspasos', 'abrirSugeridos()'),
            (1, 'PantallaTraspasos', 'GestorTraspasos', 'sugeridos(dias)'),
            (1, 'GestorTraspasos', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorTraspasos', 'VerificadorPlan', 'verificarFuncion(empresa, "traspasos_sugeridos")'),
            (1, 'VerificadorPlan', 'Plan', 'incluyeFuncion("traspasos_sugeridos")'),
            (1, 'GestorTraspasos', 'Venta', 'vendidasPorSucursal(desde)'),
            (1, 'GestorTraspasos', 'Sucursal', 'sucursalesActivas()'),
            (1, 'GestorTraspasos', 'Existencia', 'existenciasDe(variantes)'),
            (1, 'GestorTraspasos', 'Traspaso', 'enTraspaso(variantes)'),
            (1, 'GestorTraspasos', 'VarianteProducto', 'variantes(ids)'),
            (1, 'GestorTraspasos', 'GestorTraspasos', 'calcularFaltaYSobra(vendidas, disponible, stockMinimo)'),
            (1, 'GestorTraspasos', 'GestorTraspasos', 'repartir(destinos, origenes)'),
            (1, 'GestorTraspasos', 'PantallaTraspasos', 'mostrarSugerencias(sugerencias)'),
            (2, 'VerificadorPlan', 'GestorTraspasos', 'rechazarPorPlan("traspasos_sugeridos")'),
            (2, 'GestorTraspasos', 'PantallaTraspasos', 'funcionNoIncluida(mensaje)'),
            (3, AE, 'PantallaTraspasos', 'cambiarDias(dias)'),
            (3, 'PantallaTraspasos', 'GestorTraspasos', 'sugeridos(dias)'),
            (4, AE, 'PantallaTraspasos', 'ordenarSugerido(sugerencia)'),
            (4, 'PantallaTraspasos', 'GestorTraspasos', 'solicitar(datos, desdeSugerencia)'),
            (4, 'GestorTraspasos', 'Traspaso', 'agregar("SUGERIDO", "APROBADO", razon)'),
            (4, 'GestorTraspasos', 'BitacoraMiddleware', 'registrar(peticion)'),
            (4, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (4, 'GestorTraspasos', 'PantallaTraspasos', 'confirmar(traspaso)')]),
]

# Solo los nombres nuevos (los demás ya están en p2_datos.py).
DESCRIPCION = {
    'PantallaOfertas': 'Pantalla «Ofertas y precios mayoristas» del administrador: escalones mayoristas y el factor de fuera de temporada.',
    'PantallaPromociones': 'Pantalla «Promociones»: las ofertas manuales con su vigencia sobre una prenda, una categoría o una temporada.',
    'PantallaTraspasos': 'Pantalla «Traspasos entre sucursales»: seguimiento, pedir u ordenar, y los sugeridos del administrador.',
    'GestorOfertas': 'Coordina CU-31 y CU-32: precios mayoristas, la regla de fuera de temporada y sus ofertas automáticas (catalogo/ofertas_service.py).',
    'GestorPromociones': 'Coordina las ofertas manuales (RF-58) y elige el único precio que se cobra: el más bajo (RN-15).',
    'GestorTraspasos': 'Coordina CU-33 a CU-35: pedir, ordenar, aprobar, enviar, recibir o rechazar traspasos, y calcular los sugeridos.',
    'GestorNotificaciones': 'Deja los avisos internos a los encargados de una sucursal (notificaciones/service.py).',
    'PrecioMayorista': 'Escalón de precio de un producto: desde una cantidad mínima de prendas, cada una a un precio (RF-56).',
    'ReglaFueraDeTemporada': 'El factor medible de RF-57, uno por empresa: días desde el fin de la temporada, existencia sobrante y porcentaje.',
    'Promocion': 'Oferta con vigencia sobre un producto, una categoría o una temporada; MANUAL o AUTOMATICA (RN-16).',
    'Producto': 'Modelo de prenda del catálogo, con su categoría, su temporada y su precio base.',
    'Temporada': 'Temporada comercial con fecha de inicio y de fin.',
    'VarianteProducto': 'Prenda vendible: producto en una talla y un color, con su SKU y su precio.',
    'Traspaso': 'Pedido de mercadería de una sucursal a otra con su seguimiento: SOLICITADO, APROBADO, ENVIADO, RECIBIDO o RECHAZADO.',
    'MovimientoInventario': 'Fila del kardex: cada cambio de saldo con su tipo, su signo, su motivo y su usuario.',
    'Notificacion': 'Aviso interno a un usuario, con su enlace a la pantalla que lo atiende.',
}

# ------------------------------------------------------------------ 3.4 ---
CLASES = {
    # ---------------- INTERFACES ----------------
    "Ofertas": {"tipo": "interfaz", "origen": W+"features/admin/ofertas/ofertas.ts",
      "nota": "Pestañas «Precios mayoristas», «Fuera de temporada» y «Ofertas manuales» (esta solo enlaza a Promociones). cargarMayoristas() y cargarRegla() son privados y los llama ngOnInit().",
      "atributos": [],
      "operaciones": ["elegirProducto(p: ProductoResumen): void", "editar(m: Mayorista): void", "cancelar(): void", "guardar(): void",
        "cambiarEstado(m: Mayorista, activo: boolean, control?: { checked: boolean }): void", "cargarCandidatas(): void",
        "guardarRegla(): void", "aplicar(): void"]},
    "Promociones": {"tipo": "interfaz", "origen": W+"features/admin/promociones/promociones.ts",
      "atributos": [],
      "operaciones": ["paginar(evento: PageEvent): void", "filtrarPorAlcance(alcance: Alcance | null): void", "alternarVigentes(): void",
        "nueva(): void", "editar(promocion: Promocion): void", "cambiarEstado(promocion: Promocion, activa: boolean): void"]},
    "Traspasos": {"tipo": "interfaz", "origen": W+"features/sucursal/traspasos/traspasos.ts",
      "nota": "La misma pantalla en /sucursal/traspasos y /admin/traspasos. Pestañas «Seguimiento» (CU-34), «Pedir» u «Ordenar» (CU-33) y «Sugeridos» (CU-35, solo administrador). ejecutar() es privado y lo llaman accionar() y confirmar().",
      "atributos": [],
      "operaciones": ["cambiarPestana(indice: number): void", "cargar(): void", "cambiarBandeja(valor: Bandeja | 'TODAS'): void",
        "cambiarAbiertos(valor: boolean): void", "irAPagina(pagina: number): void", "accionar(t: Traspaso, accion: AccionTraspaso): void",
        "confirmar(t: Traspaso): void", "etiquetaAccion(accion: AccionTraspaso): string", "iconoAccion(accion: AccionTraspaso): string",
        "elegirPrenda(p: PrendaPedible): void", "elegirOrigen(o: OrigenPosible): void", "volverABuscar(): void", "pedir(): void",
        "cambiarDias(dias: number): void", "cargarSugeridos(): void", "claveSugerido(s: TraspasoSugerido): string",
        "ordenarSugerido(s: TraspasoSugerido): void"]},

    # ---------------- CONTROLES (front) ----------------
    "OfertasService": {"tipo": "control", "origen": W+"core/services/ofertas.service.ts",
      "atributos": [],
      "operaciones": ["listarMayoristas(busqueda: string, pagina: number, tamano: number): Observable<PaginaMayoristas>",
        "crearMayorista(datos: CrearMayorista): Observable<Mayorista>", "editarMayorista(id: number, datos: EditarMayorista): Observable<Mayorista>",
        "estadoMayorista(id: number, activo: boolean): Observable<Mayorista>", "regla(): Observable<ReglaFueraDeTemporada>",
        "guardarRegla(datos: ReglaFueraDeTemporada): Observable<ReglaFueraDeTemporada>", "candidatas(): Observable<Candidata[]>",
        "aplicar(): Observable<Aplicacion>"]},
    "PromocionesService": {"tipo": "control", "origen": W+"core/services/promociones.service.ts",
      "atributos": [],
      "operaciones": ["listar(pagina: number, tamano: number, alcance?: Alcance | null, soloVigentes?: boolean): Observable<PaginaPromociones>",
        "crear(datos: CrearPromocion): Observable<Promocion>", "editar(id: number, datos: EditarPromocion): Observable<Promocion>",
        "cambiarEstado(id: number, activa: boolean): Observable<Promocion>"]},
    "TraspasosService": {"tipo": "control", "origen": W+"core/services/traspasos.service.ts",
      "atributos": [],
      "operaciones": ["listar(filtros: FiltrosTraspasos): Observable<PaginaTraspasos>", "prendas(busqueda: string): Observable<PrendaPedible[]>",
        "origenes(varianteId: number): Observable<OrigenPosible[]>", "solicitar(datos: SolicitarTraspaso): Observable<Traspaso>",
        "atender(id: number, accion: AccionTraspaso, cuerpo: object): Observable<Traspaso>", "sugeridos(dias: number): Observable<Sugerencias>"]},
    "MiPlanService": {"tipo": "control", "origen": W+"core/services/mi-plan.service.ts",
      "nota": "Solo la operación que usa CU-35: al abrir la pantalla el administrador ve el candado si el plan no incluye traspasos_sugeridos.",
      "atributos": [], "operaciones": ["incluye(codigo: string): Observable<boolean | null>"]},

    # ---------------- CONTROLES (backend) ----------------
    "ofertas_service": {"tipo": "control", "origen": B+"catalogo/ofertas_service.py",
      "nota": "Módulo de funciones. Rutas en catalogo/ofertas_router.py, todas con requiere_roles('ADMINISTRADOR'): GET/POST /ofertas/mayoristas, PATCH /ofertas/mayoristas/{id}, PATCH /ofertas/mayoristas/{id}/estado, GET/PUT /ofertas/fuera-de-temporada/regla, GET /ofertas/fuera-de-temporada/candidatas, POST /ofertas/fuera-de-temporada/aplicar.",
      "atributos": ["REGLA_POR_OMISION: ReglaOut"],
      "operaciones": ["listar_mayoristas(db, *, busqueda, pagina, tamano): tuple[int, list[MayoristaOut]]", "obtener_mayorista(db, mayorista_id): MayoristaOut",
        "_validar_precio(db, producto_id, precio): None", "crear_mayorista(db, datos: MayoristaCrearIn): MayoristaOut",
        "editar_mayorista(db, mayorista_id, datos: MayoristaEditarIn): MayoristaOut", "cambiar_estado_mayorista(db, mayorista_id, activo): MayoristaOut",
        "obtener_regla(db): ReglaOut", "guardar_regla(db, datos: ReglaIn): ReglaOut", "_cerrar(promos: list[Promocion], hoy: date): int",
        "_candidatas(db, regla: ReglaOut, hoy: date): list[CandidataOut]", "candidatas(db): list[CandidataOut]", "aplicar(db): AplicacionOut",
        "_hoy(): date"]},
    "promociones_service": {"tipo": "control", "origen": B+"catalogo/promociones_service.py",
      "nota": "Rutas en catalogo/promociones_router.py (/catalogo/promociones). descuentos_por_variante es la costura de precios que usan la caja (pos/service.py), el carrito y la vitrina: con las cantidades llama a _aplicar_mayorista.",
      "atributos": [],
      "operaciones": ["listar(db, *, pagina, tamano, alcance, solo_vigentes): tuple[int, list[PromocionOut]]", "obtener(db, promocion_id): PromocionOut",
        "crear(db, datos: PromocionCrearIn): PromocionOut", "editar(db, promocion_id, datos: PromocionEditarIn): PromocionOut",
        "cambiar_estado(db, promocion_id, datos: CambioEstadoIn): PromocionOut",
        "descuentos_por_variante(db, precios: dict[int, Decimal], cantidades: dict[int, int] | None): dict[int, Descuento]",
        "_aplicar_mayorista(db, precios, cantidades, salida): None", "_hoy(): date"]},
    "tareas": {"tipo": "control", "origen": C+"tareas.py",
      "nota": "Tarea asyncio dentro del backend (se prende con TAREAS_AUTOMATICAS=on): cada TAREAS_INTERVALO_MINUTOS toma pg_try_advisory_lock y, por cada empresa activa, fija la empresa y corre sus tareas; _fuera_de_temporada llama a ofertas_service.aplicar(db). No pasa por HTTP: el BitacoraMiddleware no la anota.",
      "atributos": ["CLAVE_DEL_BLOQUEO: int", "TAREAS_POR_EMPRESA: tuple"],
      "operaciones": ["ciclo_de_vida(_app)", "_bucle(): None", "correr_vuelta(fabrica_de_sesiones, minimo_entre_vueltas): Vuelta",
        "_toca_vuelta(conexion, minimo): bool", "_empresas_activas(db): list[int]", "_intentar(vuelta, db, nombre, tarea): None",
        "_fuera_de_temporada(db, _: int): None", "encendidas(): bool"]},
    "traspasos_service": {"tipo": "control", "origen": B+"traspasos/service.py",
      "nota": "Módulo de funciones. Rutas en traspasos/router.py con requiere_roles('ADMINISTRADOR', 'ENCARGADO'): GET /traspasos/sugeridos (además requiere_roles('ADMINISTRADOR') y requiere_funcion('traspasos_sugeridos')), GET /traspasos, GET /traspasos/prendas, GET /traspasos/origenes, GET /traspasos/{id}, POST /traspasos, POST /traspasos/{id}/aprobar|rechazar|enviar|recibir|devolver. Quien(usuario_id, rol, sucursal_id) sale del token.",
      "atributos": ["TOPE_SUGERENCIAS: int = 100"],
      "operaciones": ["listar(db, quien, *, bandeja, estado, abiertos, sucursal_id, pagina, tamano): PaginaTraspasos",
        "obtener(db, quien, traspaso_id): TraspasoOut", "prendas_pedibles(db, quien, busqueda): list[PrendaPedibleOut]",
        "origenes_posibles(db, quien, variante_id): list[OrigenPosibleOut]", "solicitar(db, quien, datos: SolicitarTraspasoIn): TraspasoOut",
        "_bloquear(db, quien, traspaso_id, accion): Traspaso", "aprobar(db, quien, traspaso_id, datos: AprobarIn): TraspasoOut",
        "rechazar(db, quien, traspaso_id, datos: RechazarIn): TraspasoOut", "enviar(db, quien, traspaso_id): TraspasoOut",
        "recibir(db, quien, traspaso_id): TraspasoOut", "devolver(db, quien, traspaso_id): TraspasoOut",
        "sugeridos(db, *, dias): SugerenciasOut", "_acciones(t, quien, *, destino_activo): list[str]",
        "_exigir(t, quien, accion, *, destino_activo): None", "_visible(t, quien): Traspaso", "_destino_activo(db, t): bool",
        "_a_salida(db, fila, quien): TraspasoOut", "_sin_stock(disponible, pedido): ErrorDeTraspaso"]},
    "inventario_service": {"tipo": "control", "origen": B+"inventario/service.py",
      "nota": "Solo las funciones que usan los traspasos. _aplicar_movimiento es la misma que usa la venta: cambia el saldo y escribe el MovimientoInventario; si quedaría negativo lanza StockInsuficiente (RN-09).",
      "atributos": [],
      "operaciones": ["_aplicar_movimiento(db, existencia, *, tipo, cantidad, reservada_delta, motivo, proveedor_id, referencia, usuario_id)",
        "_existencia_o_crearla(db, *, variante_id, sucursal_id): Existencia", "_sucursal_activa(db, sucursal_id)",
        "_variantes_validas(db, ids: list[int]): dict[int, object]", "_etiqueta_de_variante(db, variante_id): str"]},
    "notificaciones_service": {"tipo": "control", "origen": B+"notificaciones/service.py",
      "nota": "Solo lo que usan los traspasos. notificar deja la fila en la transacción en curso; el correo y el push salen después, en la tarea automática.",
      "atributos": [],
      "operaciones": ["avisar_traspaso(db, traspaso, *, sucursal_id, titulo, cuerpo): list[Notificacion]",
        "notificar(db, *, destinatario, tipo, titulo, cuerpo, enlace, entidad, entidad_id): Notificacion",
        "_encargados_de(db, sucursal_id): list[Usuario]"]},
    "verificador": {"tipo": "control", "origen": B+"plataforma/verificador.py",
      "nota": "CU-05. Lo llama la dependencia requiere_funcion('traspasos_sugeridos') de core/dependencies.py antes de la ruta; si falta la función lanza RechazoDelPlan (403 plan_limit).",
      "atributos": [],
      "operaciones": ["suscripcion_vigente(db): Suscripcion | None", "plan_vigente(db): Plan", "verificar_funcion(db, funcion: str): None"]},
    "BitacoraMiddleware": {"tipo": "control", "origen": B+"bitacora/middleware.py",
      "nota": "Anota toda peticion POST/PUT/PATCH/DELETE (y las exportaciones GET). _anotar llama a bitacora/service.py registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
      "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response", "_anotar(peticion: Request, respuesta): None"]},

    # ---------------- ENTIDADES ----------------
    "PrecioMayorista": {"tipo": "entidad", "origen": B+"catalogo/ofertas_models.py", "tabla": "precio_mayorista",
      "nota": OMIT_AUD + " UNIQUE (empresa_id, producto_id, cantidad_minima); CHECK cantidad_minima >= 2 y precio_unitario > 0.",
      "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto)", "cantidad_minima: INTEGER",
        "precio_unitario: NUMERIC(10,2)", "activo: BOOLEAN"],
      "operaciones": ["escalones_de_variantes(db, variante_ids): list[Row]  [catalogo/ofertas_repository.py]",
        "escalones_de_productos(db, producto_ids): list[PrecioMayorista]  [catalogo/ofertas_repository.py]",
        "listar_mayoristas(db, *, busqueda, pagina, tamano): tuple[int, list[Row]]  [catalogo/ofertas_repository.py]",
        "mayorista(db, mayorista_id): PrecioMayorista | None  [catalogo/ofertas_repository.py]",
        "fila_de_mayorista(db, mayorista_id): Row | None  [catalogo/ofertas_repository.py]",
        "existe_escalon(db, producto_id, cantidad_minima, *, excepto_id): bool  [catalogo/ofertas_repository.py]",
        "agregar(db, entidad): None  [catalogo/ofertas_repository.py]"]},
    "ReglaFueraDeTemporada": {"tipo": "entidad", "origen": B+"catalogo/ofertas_models.py", "tabla": "regla_fuera_de_temporada",
      "nota": OMIT_AUD + " CHECK dias_desde_fin >= 0, existencia_minima >= 1, 0 < porcentaje <= 90.",
      "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa, UNIQUE)", "activa: BOOLEAN", "dias_desde_fin: INTEGER",
        "existencia_minima: INTEGER", "porcentaje: NUMERIC(5,2)"],
      "operaciones": ["regla(db): ReglaFueraDeTemporada | None  [catalogo/ofertas_repository.py]",
        "agregar(db, entidad): None  [catalogo/ofertas_repository.py]"]},
    "Promocion": {"tipo": "entidad", "origen": B+"catalogo/promociones_models.py", "tabla": "promocion",
      "nota": OMIT_AUD + " CHECK: exactamente uno de producto_id, categoria_id, temporada_id; hasta IS NULL OR hasta >= desde. origen: MANUAL | AUTOMATICA.",
      "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "nombre: VARCHAR(80)", "alcance: VARCHAR(10)",
        "producto_id: BIGINT (FK producto)", "categoria_id: INTEGER (FK categoria)", "temporada_id: INTEGER (FK temporada)",
        "porcentaje: NUMERIC(5,2)", "desde: DATE", "hasta: DATE", "activa: BOOLEAN", "origen: VARCHAR(10)", "cerrada_por_regla: BOOLEAN"],
      "operaciones": ["descuentos_de_variantes(db, *, variante_ids, hoy): list[Row]  [catalogo/promociones_repository.py]",
        "listar(db, *, pagina, tamano, alcance, solo_vigentes, hoy): tuple[int, list[Row]]  [catalogo/promociones_repository.py]",
        "entidad(db, promocion_id): Promocion | None  [catalogo/promociones_repository.py]",
        "existe_nombre(db, nombre, *, excepto_id): bool  [catalogo/promociones_repository.py]",
        "agregar(db, promocion): Promocion  [catalogo/promociones_repository.py]",
        "automaticas_vigentes(db): list[Promocion]  [catalogo/ofertas_repository.py]",
        "promocion(db, promocion_id): Promocion | None  [catalogo/ofertas_repository.py]"]},
    "Producto": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "producto", "nota": OMIT_AUD,
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(30)", "nombre: VARCHAR(120)",
        "descripcion: VARCHAR(500)", "categoria_id: INTEGER (FK categoria)", "proveedor_id: BIGINT (FK proveedor)",
        "temporada_id: INTEGER (FK temporada)", "coleccion_id: INTEGER (FK coleccion)", "precio_base: NUMERIC(10,2)", "activo: BOOLEAN"],
      "operaciones": ["producto(db, producto_id): Producto | None  [catalogo/ofertas_repository.py]",
        "candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima): list[Row]  [catalogo/ofertas_repository.py]"]},
    "Temporada": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "temporada", "nota": OMIT_AUD,
      "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "nombre: VARCHAR(60)", "descripcion: VARCHAR(200)",
        "fecha_inicio: DATE", "fecha_fin: DATE", "activa: BOOLEAN"],
      "operaciones": ["candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima): list[Row]  [catalogo/ofertas_repository.py, JOIN temporada]"]},
    "VarianteProducto": {"tipo": "entidad", "origen": B+"catalogo/models.py", "tabla": "variante_producto", "nota": OMIT_AUD,
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto)", "talla_id: INTEGER (FK talla)",
        "color_id: INTEGER (FK color)", "sku: VARCHAR(40)", "precio: NUMERIC(10,2)", "activa: BOOLEAN"],
      "operaciones": ["precio_minimo_del_producto(db, producto_id): Decimal | None  [catalogo/ofertas_repository.py]",
        "prendas_en_otras(db, *, busqueda, excluir, limite): list[Row]  [traspasos/repository.py]",
        "variantes(db, ids): dict[int, Row]  [traspasos/repository.py]",
        "candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima): list[Row]  [catalogo/ofertas_repository.py, JOIN variante_producto]"]},
    "Existencia": {"tipo": "entidad", "origen": B+"inventario/models.py", "tabla": "existencia", "nota": OMIT_AUD,
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "variante_id: BIGINT (FK variante_producto)", "sucursal_id: INTEGER (FK sucursal)",
        "cantidad_disponible: INTEGER", "cantidad_reservada: INTEGER", "stock_minimo: INTEGER"],
      "operaciones": ["disponible(db, *, variante_id, sucursal_id): int | None  [traspasos/repository.py]",
        "origenes_posibles(db, *, variante_id, excluir): list[Row]  [traspasos/repository.py]",
        "existencias_de(db, variante_ids): list[Row]  [traspasos/repository.py]",
        "obtener_existencia(db, *, variante_id, sucursal_id, bloquear): Existencia | None  [inventario/repository.py]",
        "agregar_existencia(db, *, variante_id, sucursal_id): Existencia  [inventario/repository.py]",
        "candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima): list[Row]  [catalogo/ofertas_repository.py, SUM(cantidad_disponible)]"]},
    "Sucursal": {"tipo": "entidad", "origen": B+"organizacion/models.py", "tabla": "sucursal", "nota": OMIT_AUD,
      "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "ciudad_id: INTEGER (FK ciudad)", "nombre: VARCHAR(80)", "direccion: VARCHAR(200)",
        "telefono: VARCHAR(20)", "horario_apertura: TIME", "horario_cierre: TIME", "capacidad_vestidores: SMALLINT", "activa: BOOLEAN"],
      "operaciones": ["obtener_sucursal(db, sucursal_id): Sucursal | None  [inventario/repository.py]",
        "sucursales_activas(db): dict[int, str]  [traspasos/repository.py]"]},
    "Traspaso": {"tipo": "entidad", "origen": B+"traspasos/models.py", "tabla": "traspaso",
      "nota": OMIT_AUD + " tipo: PEDIDO | ORDEN | SUGERIDO. estado: SOLICITADO | APROBADO | ENVIADO | RECIBIDO | RECHAZADO. CHECK origen <> destino; motivo_rechazo solo si RECHAZADO; movimiento_salida_id desde ENVIADO; movimiento_entrada_id solo si RECIBIDO.",
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "tipo: VARCHAR(10)", "estado: VARCHAR(12)",
        "variante_id: BIGINT (FK variante_producto)", "sucursal_origen_id: INTEGER (FK sucursal)", "sucursal_destino_id: INTEGER (FK sucursal)",
        "cantidad: INTEGER", "cantidad_solicitada: INTEGER", "motivo: VARCHAR(200)", "solicitado_por: BIGINT (FK usuario)",
        "aprobado_por: BIGINT (FK usuario)", "aprobado_en: TIMESTAMPTZ", "enviado_por: BIGINT (FK usuario)", "enviado_en: TIMESTAMPTZ",
        "recibido_por: BIGINT (FK usuario)", "recibido_en: TIMESTAMPTZ", "rechazado_por: BIGINT (FK usuario)", "rechazado_en: TIMESTAMPTZ",
        "motivo_rechazo: VARCHAR(200)", "movimiento_salida_id: BIGINT (FK movimiento_inventario)",
        "movimiento_entrada_id: BIGINT (FK movimiento_inventario)"],
      "operaciones": ["agregar(db, **valores): Traspaso  [traspasos/repository.py]",
        "obtener(db, traspaso_id, *, bloquear): Traspaso | None  [traspasos/repository.py]",
        "hay_abierto(db, *, variante_id, origen_id, destino_id): bool  [traspasos/repository.py]",
        "listar(db, *, sucursal_id, bandeja, estado, abiertos, pagina, tamano): tuple[int, list[Row]]  [traspasos/repository.py]",
        "detalle(db, traspaso_id): Row | None  [traspasos/repository.py]",
        "en_traspaso(db, variante_ids): tuple[dict, dict]  [traspasos/repository.py]"]},
    "MovimientoInventario": {"tipo": "entidad", "origen": B+"inventario/models.py", "tabla": "movimiento_inventario",
      "nota": "No hereda Auditoria: solo creado_en. cantidad con signo (positiva entra, negativa sale). Los traspasos escriben tipo TRANSFERENCIA con referencia TRASPASO-{id}.",
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "existencia_id: BIGINT (FK existencia)", "tipo: VARCHAR(15)",
        "cantidad: INTEGER", "motivo: VARCHAR(200)", "proveedor_id: BIGINT (FK proveedor)", "referencia: VARCHAR(40)",
        "usuario_id: BIGINT (FK usuario)", "operacion_offline_id: BIGINT (FK operacion_offline)", "creado_en: TIMESTAMPTZ"],
      "operaciones": ["agregar_movimiento(db, *, existencia_id, tipo, cantidad, motivo, proveedor_id, referencia, usuario_id): MovimientoInventario  [inventario/repository.py]"]},
    "Notificacion": {"tipo": "entidad", "origen": B+"notificaciones/models.py", "tabla": "notificacion",
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "destinatario_id: BIGINT (FK usuario, ON DELETE CASCADE)",
        "tipo: VARCHAR(40)", "titulo: VARCHAR(160)", "cuerpo: TEXT", "enlace: VARCHAR(300)", "entidad: VARCHAR(60)", "entidad_id: BIGINT",
        "creada_en: TIMESTAMPTZ", "leida_en: TIMESTAMPTZ", "correo_estado: VARCHAR(20)", "correo_enviado_en: TIMESTAMPTZ",
        "correo_error: VARCHAR(300)"],
      "operaciones": ["crear(db, *, destinatario_id, tipo, titulo, cuerpo, enlace, entidad, entidad_id): Notificacion  [notificaciones/repository.py]"]},
    "Venta": {"tipo": "entidad", "origen": B+"ventas/models.py", "tabla": "venta",
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(20) (UNIQUE)", "canal: VARCHAR(12)", "estado: VARCHAR(20)",
        "cliente_id: BIGINT (FK cliente)", "sucursal_id: INTEGER (FK sucursal)", "turno_caja_id: BIGINT (FK turno_caja)", "reserva_id: BIGINT (FK reserva, UNIQUE)",
        "modalidad_entrega: VARCHAR(10)", "direccion_id: BIGINT (FK direccion_cliente)", "metodo_pago: VARCHAR(20)", "subtotal: NUMERIC(10,2)",
        "descuento: NUMERIC(10,2)", "total: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ", "actualizado_en: TIMESTAMPTZ"],
      "operaciones": ["vendidas_por_sucursal(db, *, desde): list[Row]  [traspasos/repository.py, JOIN detalle_venta]"]},
    "Plan": {"tipo": "entidad", "origen": B+"plataforma/models.py", "tabla": "plan",
      "nota": OMIT_AUD + " Tabla de la plataforma, sin empresa_id. funciones es el JSONB donde va traspasos_sugeridos.",
      "atributos": ["id: SMALLINT (PK)", "codigo: VARCHAR(20) (UNIQUE)", "nombre: VARCHAR(40) (UNIQUE)", "precio_mensual: NUMERIC(10,2)",
        "duracion_dias: SMALLINT", "max_sucursales: INTEGER", "max_empleados: INTEGER", "cupo_reportes_ia: INTEGER",
        "cupo_fotos_ia: INTEGER", "funciones: JSONB", "activo: BOOLEAN"],
      "operaciones": ["plan_vigente(db): Plan  [plataforma/verificador.py, JOIN suscripcion]"]},
    "AsientoBitacora": {"tipo": "entidad", "origen": B+"bitacora/models.py", "tabla": "bitacora",
      "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ", "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)",
        "actor: VARCHAR(160)", "rol: VARCHAR(40)", "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
        "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)", "detalle: JSONB"],
      "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int", "listar(db, limite, desplazamiento, **filtros): list[tuple]",
        "acciones(db): list[str]", "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}

# FK reales (multiplicidad: primero en el extremo ClaseA, después en ClaseB)
FK = [
    ["Producto", "PrecioMayorista", "TIENE_ESCALON", "1", "0..*"],
    ["Producto", "VarianteProducto", "TIENE", "1", "1..*"],
    ["Producto", "Promocion", "SE_OFERTA_EN", "0..1", "0..*"],
    ["Temporada", "Producto", "AGRUPA", "0..1", "0..*"],
    ["Temporada", "Promocion", "SE_OFERTA_EN", "0..1", "0..*"],
    ["VarianteProducto", "Existencia", "TIENE_SALDO_EN", "1", "0..*"],
    ["Sucursal", "Existencia", "GUARDA", "1", "0..*"],
    ["VarianteProducto", "Traspaso", "SE_TRASPASA_EN", "1", "0..*"],
    ["Sucursal", "Traspaso", "ENVIA", "1", "0..*"],
    ["Sucursal", "Traspaso", "RECIBE", "1", "0..*"],
    ["MovimientoInventario", "Traspaso", "ES_SALIDA_DE", "0..1", "0..1"],
    ["MovimientoInventario", "Traspaso", "ES_ENTRADA_DE", "0..1", "0..1"],
    ["Existencia", "MovimientoInventario", "SE_EXPLICA_EN", "1", "0..*"],
    ["Sucursal", "Venta", "VENDE", "1", "0..*"],
]


def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]


def bit(controles):
    return ([[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles]
            + [["BitacoraMiddleware", "AsientoBitacora", "REGISTRA", "1", "0..*"]])


CUS = {}

c31 = ["Ofertas", "Promociones", "OfertasService", "PromocionesService", "ofertas_service", "promociones_service",
       "BitacoraMiddleware", "AsientoBitacora", "PrecioMayorista", "Producto", "VarianteProducto", "Promocion"]
CUS["CU-31"] = {"actores": ["Administrador"], "clases": c31,
  "operaciones_en_cu": {
     "Ofertas": ["elegirProducto(p)", "editar(m)", "cancelar()", "guardar()", "cambiarEstado(m, activo, control)"],
     "OfertasService": ["listarMayoristas(busqueda, pagina, tamano)", "crearMayorista(datos)", "editarMayorista(id, datos)",
                        "estadoMayorista(id, activo)"],
     "ofertas_service": ["listar_mayoristas(db, *, busqueda, pagina, tamano)", "obtener_mayorista(db, mayorista_id)",
                         "_validar_precio(db, producto_id, precio)", "crear_mayorista(db, datos)",
                         "editar_mayorista(db, mayorista_id, datos)", "cambiar_estado_mayorista(db, mayorista_id, activo)"],
     "promociones_service": ["listar(db, *, pagina, tamano, alcance, solo_vigentes)", "crear(db, datos)",
                             "editar(db, promocion_id, datos)", "cambiar_estado(db, promocion_id, datos)",
                             "descuentos_por_variante(db, precios, cantidades)", "_aplicar_mayorista(db, precios, cantidades, salida)"],
     "Promocion": ["listar(db, *, pagina, tamano, alcance, solo_vigentes, hoy)", "entidad(db, promocion_id)",
                   "existe_nombre(db, nombre, *, excepto_id)", "agregar(db, promocion)",
                   "descuentos_de_variantes(db, *, variante_ids, hoy)"],
     "VarianteProducto": ["precio_minimo_del_producto(db, producto_id)"],
     "Producto": ["producto(db, producto_id)"]},
  "nota": "Las ofertas manuales de RF-58 son las promociones de CU-12 del primer parcial (Promociones y /catalogo/promociones); no se duplican. El mayorista se cobra en la caja, el carrito y el pedido web por promociones_service.descuentos_por_variante -> _aplicar_mayorista, que deja el precio más bajo sin sumar descuentos (RN-15); la vitrina y el mostrador lo muestran con escalones_de_productos. Omitidos los routers (ofertas_router.py, promociones_router.py) y ProductosService del buscador de productos. Ningún paso pasa por requiere_funcion: las funciones vienen en todos los planes.",
  "relaciones": [["Administrador", "Ofertas", "USA", "1", "1"], ["Administrador", "Promociones", "USA", "1", "1"],
    ["Ofertas", "OfertasService", "SOLICITA", "1", "1"], ["Promociones", "PromocionesService", "SOLICITA", "1", "1"],
    ["OfertasService", "ofertas_service", "LLAMA_A", "1", "1"], ["PromocionesService", "promociones_service", "LLAMA_A", "1", "1"],
    ["ofertas_service", "PrecioMayorista", "REGISTRA", "1", "0..*"], ["ofertas_service", "Producto", "CONSULTA", "1", "0..1"],
    ["ofertas_service", "VarianteProducto", "CONSULTA", "1", "0..*"], ["promociones_service", "Promocion", "REGISTRA", "1", "0..*"],
    ["promociones_service", "PrecioMayorista", "CONSULTA", "1", "0..*"]]
    + bit(["ofertas_service", "promociones_service"]) + fks(c31)}

c32 = ["tareas", "Ofertas", "OfertasService", "ofertas_service", "BitacoraMiddleware", "AsientoBitacora",
       "ReglaFueraDeTemporada", "Promocion", "Producto", "Temporada", "Existencia", "VarianteProducto"]
CUS["CU-32"] = {"actores": ["Sistema", "Administrador"], "clases": c32,
  "operaciones_en_cu": {
     "Ofertas": ["cargarCandidatas()", "guardarRegla()", "aplicar()"],
     "OfertasService": ["regla()", "guardarRegla(datos)", "candidatas()", "aplicar()"],
     "ofertas_service": ["obtener_regla(db)", "guardar_regla(db, datos)", "_cerrar(promos, hoy)", "_candidatas(db, regla, hoy)",
                         "candidatas(db)", "aplicar(db)", "_hoy()"],
     "Promocion": ["automaticas_vigentes(db)", "promocion(db, promocion_id)"],
     "Producto": ["candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima)"],
     "Existencia": ["candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima)"],
     "VarianteProducto": ["candidatas_fuera_de_temporada(db, *, hasta_fin, existencia_minima)"]},
  "nota": "El camino del Sistema es tareas._fuera_de_temporada -> ofertas_service.aplicar(db), sin HTTP, por eso no lo anota el BitacoraMiddleware; sí anota el PUT de la regla y el POST /ofertas/fuera-de-temporada/aplicar que dispara el administrador con «Aplicar ahora». La oferta automática no tiene tabla propia: es una Promocion con origen AUTOMATICA sobre el producto, y la caja y la vitrina la cobran sin cambios. candidatas_fuera_de_temporada es una sola consulta: JOIN producto-temporada, SUM de existencia por variante en sucursales activas (Sucursal, omitida por el tope de 12) y la última promoción automática del producto.",
  "relaciones": [["Sistema", "tareas", "DISPARA", "1", "1"], ["Administrador", "Ofertas", "USA", "1", "1"],
    ["Ofertas", "OfertasService", "SOLICITA", "1", "1"], ["OfertasService", "ofertas_service", "LLAMA_A", "1", "1"],
    ["tareas", "ofertas_service", "LLAMA_A", "1", "1"],
    ["ofertas_service", "ReglaFueraDeTemporada", "CONSULTA", "1", "0..1"], ["ofertas_service", "Promocion", "REGISTRA", "1", "0..*"],
    ["ofertas_service", "Producto", "CONSULTA", "1", "0..*"], ["ofertas_service", "Temporada", "CONSULTA", "1", "0..*"],
    ["ofertas_service", "Existencia", "CONSULTA", "1", "0..*"], ["ofertas_service", "VarianteProducto", "CONSULTA", "1", "0..*"]]
    + bit(["ofertas_service"]) + fks(c32)}

c33 = ["Traspasos", "TraspasosService", "traspasos_service", "inventario_service", "notificaciones_service",
       "BitacoraMiddleware", "AsientoBitacora", "Traspaso", "Existencia", "VarianteProducto", "Sucursal", "Notificacion"]
CUS["CU-33"] = {"actores": ["Encargado", "Administrador"], "clases": c33,
  "operaciones_en_cu": {
     "Traspasos": ["cambiarPestana(indice)", "elegirPrenda(p)", "elegirOrigen(o)", "volverABuscar()", "pedir()"],
     "TraspasosService": ["prendas(busqueda)", "origenes(varianteId)", "solicitar(datos)"],
     "traspasos_service": ["prendas_pedibles(db, quien, busqueda)", "origenes_posibles(db, quien, variante_id)",
                           "solicitar(db, quien, datos)", "_sin_stock(disponible, pedido)", "_a_salida(db, fila, quien)"],
     "inventario_service": ["_sucursal_activa(db, sucursal_id)", "_variantes_validas(db, ids)", "_etiqueta_de_variante(db, variante_id)"],
     "notificaciones_service": ["avisar_traspaso(db, traspaso, *, sucursal_id, titulo, cuerpo)",
                                "notificar(db, *, destinatario, tipo, titulo, cuerpo, enlace, entidad, entidad_id)",
                                "_encargados_de(db, sucursal_id)"],
     "Traspaso": ["agregar(db, **valores)", "hay_abierto(db, *, variante_id, origen_id, destino_id)", "detalle(db, traspaso_id)"],
     "Existencia": ["disponible(db, *, variante_id, sucursal_id)", "origenes_posibles(db, *, variante_id, excluir)"],
     "VarianteProducto": ["prendas_en_otras(db, *, busqueda, excluir, limite)"],
     "Sucursal": ["obtener_sucursal(db, sucursal_id)"]},
  "nota": "El encargado pide para SU sucursal (el destino sale del token) y queda PEDIDO/SOLICITADO; el administrador elige origen y destino y nace ORDEN/APROBADO (RF-40), o SUGERIDO si viene de CU-35. La escritura sin suscripción vigente la corta _exigir_suscripcion_para_escribir de core/dependencies.py (CU-05, 2a). Omitidos OrganizacionService (lista de destinos del administrador) y Usuario (los encargados que reciben el aviso).",
  "relaciones": [["Encargado", "Traspasos", "USA", "1", "1"], ["Administrador", "Traspasos", "USA", "1", "1"],
    ["Traspasos", "TraspasosService", "SOLICITA", "1", "1"], ["TraspasosService", "traspasos_service", "LLAMA_A", "1", "1"],
    ["traspasos_service", "inventario_service", "VALIDA_CON", "1", "1"], ["traspasos_service", "notificaciones_service", "AVISA_CON", "1", "1"],
    ["traspasos_service", "Traspaso", "REGISTRA", "1", "0..*"], ["traspasos_service", "Existencia", "CONSULTA", "1", "0..*"],
    ["traspasos_service", "VarianteProducto", "CONSULTA", "1", "0..*"], ["inventario_service", "Sucursal", "CONSULTA", "1", "0..1"],
    ["notificaciones_service", "Notificacion", "REGISTRA", "1", "0..*"]]
    + bit(["traspasos_service"]) + fks(c33)}

c34 = ["Traspasos", "TraspasosService", "traspasos_service", "inventario_service", "notificaciones_service",
       "BitacoraMiddleware", "AsientoBitacora", "Traspaso", "Existencia", "MovimientoInventario", "Sucursal", "Notificacion"]
CUS["CU-34"] = {"actores": ["Encargado"], "clases": c34,
  "operaciones_en_cu": {
     "Traspasos": ["cargar()", "cambiarBandeja(valor)", "cambiarAbiertos(valor)", "irAPagina(pagina)", "accionar(t, accion)",
                   "confirmar(t)", "etiquetaAccion(accion)", "iconoAccion(accion)"],
     "TraspasosService": ["listar(filtros)", "atender(id, accion, cuerpo)"],
     "traspasos_service": ["listar(db, quien, *, bandeja, estado, abiertos, sucursal_id, pagina, tamano)", "_bloquear(db, quien, traspaso_id, accion)",
                           "aprobar(db, quien, traspaso_id, datos)", "rechazar(db, quien, traspaso_id, datos)", "enviar(db, quien, traspaso_id)",
                           "recibir(db, quien, traspaso_id)", "devolver(db, quien, traspaso_id)", "_acciones(t, quien, *, destino_activo)",
                           "_exigir(t, quien, accion, *, destino_activo)", "_visible(t, quien)", "_destino_activo(db, t)", "_sin_stock(disponible, pedido)"],
     "inventario_service": ["_aplicar_movimiento(db, existencia, *, tipo, cantidad, ...)", "_existencia_o_crearla(db, *, variante_id, sucursal_id)",
                            "_etiqueta_de_variante(db, variante_id)"],
     "notificaciones_service": ["avisar_traspaso(db, traspaso, *, sucursal_id, titulo, cuerpo)",
                                "notificar(db, *, destinatario, tipo, titulo, cuerpo, enlace, entidad, entidad_id)"],
     "Traspaso": ["obtener(db, traspaso_id, *, bloquear)", "listar(db, *, sucursal_id, bandeja, estado, abiertos, pagina, tamano)",
                  "detalle(db, traspaso_id)"],
     "Existencia": ["disponible(db, *, variante_id, sucursal_id)", "obtener_existencia(db, *, variante_id, sucursal_id, bloquear)",
                    "agregar_existencia(db, *, variante_id, sucursal_id)"],
     "Sucursal": ["obtener_sucursal(db, sucursal_id)"]},
  "nota": "Aprobar no aparta unidades; enviar descuenta del origen con bloqueo de fila y recibir suma al destino, cada uno con su MovimientoInventario TRANSFERENCIA (RN-09). obtener(..., bloquear=True) usa FOR UPDATE: dos «Enviar» a la vez no descuentan dos veces. El administrador puede hacer cualquier paso en cualquier sucursal. Omitido Usuario (quién hizo cada paso y los encargados avisados).",
  "relaciones": [["Encargado", "Traspasos", "USA", "1", "1"], ["Traspasos", "TraspasosService", "SOLICITA", "1", "1"],
    ["TraspasosService", "traspasos_service", "LLAMA_A", "1", "1"], ["traspasos_service", "inventario_service", "MUEVE_SALDO_CON", "1", "1"],
    ["traspasos_service", "notificaciones_service", "AVISA_CON", "1", "1"], ["traspasos_service", "Traspaso", "ACTUALIZA", "1", "0..*"],
    ["traspasos_service", "Existencia", "CONSULTA", "1", "0..*"], ["traspasos_service", "Sucursal", "CONSULTA", "1", "0..2"],
    ["inventario_service", "Existencia", "ACTUALIZA", "1", "0..*"], ["inventario_service", "MovimientoInventario", "REGISTRA", "1", "0..*"],
    ["notificaciones_service", "Notificacion", "REGISTRA", "1", "0..*"]]
    + bit(["traspasos_service"]) + fks(c34)}

c35 = ["Traspasos", "TraspasosService", "MiPlanService", "traspasos_service", "verificador", "BitacoraMiddleware",
       "AsientoBitacora", "Plan", "Venta", "Existencia", "Traspaso", "VarianteProducto"]
CUS["CU-35"] = {"actores": ["Administrador"], "clases": c35,
  "operaciones_en_cu": {
     "Traspasos": ["cambiarPestana(indice)", "cambiarDias(dias)", "cargarSugeridos()", "claveSugerido(s)", "ordenarSugerido(s)"],
     "TraspasosService": ["sugeridos(dias)", "solicitar(datos)"],
     "traspasos_service": ["sugeridos(db, *, dias)", "solicitar(db, quien, datos)"],
     "verificador": ["plan_vigente(db)", "verificar_funcion(db, funcion)"],
     "Existencia": ["existencias_de(db, variante_ids)"],
     "Traspaso": ["en_traspaso(db, variante_ids)", "agregar(db, **valores)"],
     "VarianteProducto": ["variantes(db, ids)"]},
  "nota": "La consulta es un GET y no escribe; la bitácora aparece por «Ordenar N u.» (7a), que es POST /traspasos con desde_sugerencia y extiende CU-33. sugeridos(): objetivo = max(vendidas en el período, stock_minimo); falta = objetivo - disponible - en camino; sobra = disponible - prometido - objetivo; se reparte a la que más vende desde la que más le sobra; tope 100. Omitidas Sucursal (sucursales_activas) y DetalleVenta (JOIN de vendidas_por_sucursal) por el tope de 12.",
  "relaciones": [["Administrador", "Traspasos", "USA", "1", "1"], ["Traspasos", "TraspasosService", "SOLICITA", "1", "1"],
    ["Traspasos", "MiPlanService", "CONSULTA", "1", "1"], ["TraspasosService", "traspasos_service", "LLAMA_A", "1", "1"],
    ["traspasos_service", "verificador", "ES_CONTROLADO_POR", "1", "1"], ["verificador", "Plan", "CONSULTA", "1", "1"],
    ["traspasos_service", "Venta", "CONSULTA", "1", "0..*"], ["traspasos_service", "Existencia", "CONSULTA", "1", "0..*"],
    ["traspasos_service", "Traspaso", "CONSULTA", "1", "0..*"], ["traspasos_service", "VarianteProducto", "CONSULTA", "1", "0..*"]]
    + bit(["traspasos_service"]) + fks(c35)}

# ------------------------------------------------------------------ 2.6 ---
ESPEC = {
    'CU-31': dict(
        descripcion='Permite al administrador de la empresa definir precios mayoristas por producto, que se aplican '
                    'desde una cantidad mínima de prendas, y seguir creando ofertas manuales con su vigencia.',
        actores='Administrador de la empresa',
        iniciador='Administrador de la empresa',
        precondiciones='El administrador inició sesión en su empresa. El producto existe y tiene variantes activas.',
        flujo=[
            'El administrador abre «Ofertas», pestaña «Precios mayoristas».',
            'El sistema muestra los escalones de la empresa: producto, precio base, desde cuántas unidades, precio '
            'por unidad y si está activo.',
            'El administrador busca y elige el producto, indica desde cuántas unidades (2 o más) y el precio por '
            'unidad, y pulsa «Guardar».',
            'El sistema verifica que el producto exista y que no tenga ya un escalón con esa cantidad mínima.',
            'El sistema verifica que el precio mayorista sea menor que el precio más bajo de las variantes activas '
            'del producto.',
            'El sistema registra el escalón activo y lo muestra en la lista.',
            'Desde ese momento la caja, el carrito y el pedido web suman las unidades del producto, mezclando tallas '
            'y colores, y cobran el escalón más alto que se alcanza si deja el precio más bajo (RN-15).',
        ],
        alternativos=[
            '1a. Oferta manual: el administrador abre «Promociones», pulsa «Nueva» y carga el nombre, el alcance '
            '(prenda, categoría o temporada), el porcentaje y la vigencia; el sistema la registra como MANUAL.',
            '3a. Editar o apagar: el administrador pulsa «Editar» y cambia la cantidad o el precio, o usa el '
            'interruptor para apagar o encender el escalón; no se borra, porque las ventas ya lo cobraron.',
            '4a. Escalón repetido: el producto ya tiene un precio desde esa cantidad; el sistema lo rechaza y no '
            'guarda nada.',
            '5a. Precio que no gana: el precio no es menor que el más bajo del producto; el sistema lo rechaza '
            'indicando el mínimo, porque nunca se aplicaría.',
        ],
        postcondiciones='El escalón queda guardado y activo, o con el estado elegido. La caja, el carrito y la '
                        'vitrina lo muestran y lo cobran sin acumular descuentos. La petición queda en la bitácora.',
        rastreo='RF-56, RF-58 · RN-15',
    ),
    'CU-32': dict(
        descripcion='Permite al sistema poner en oferta, sin intervención de nadie, las prendas cuya temporada '
                    'terminó y que sobran, según un factor medible guardado en la base.',
        actores='Sistema, administrador de la empresa',
        iniciador='Sistema (tarea automática del backend)',
        precondiciones='Las tareas automáticas están encendidas en el servidor. La empresa guardó su regla de fuera '
                       'de temporada y la dejó activa. El producto tiene una temporada con fecha de fin.',
        flujo=[
            'La tarea automática del backend despierta cada intervalo configurado y, para cada empresa activa, '
            'ejecuta la aplicación de ofertas de fuera de temporada.',
            'El sistema lee la regla de la empresa: si está activa, los días desde el fin de la temporada, la '
            'existencia sobrante y el porcentaje.',
            'El sistema busca los productos activos cuya temporada terminó hace al menos esos días y cuya existencia '
            'disponible, sumada en las sucursales activas, llega al mínimo.',
            'A cada producto que califica y no tiene oferta automática le crea una promoción de origen AUTOMATICA '
            'sobre el producto, con el porcentaje de la regla, desde hoy y sin fecha de fin.',
            'El sistema cierra las ofertas automáticas vigentes cuyo producto ya no califica, con fecha de fin de '
            'ayer, y las marca como cerradas por la regla.',
            'El sistema confirma los cambios de la empresa y anota en el registro del servidor cuántas tareas hizo.',
            'Desde ese momento la vitrina, la caja y el carrito aplican la oferta, con el precio más bajo entre el '
            'normal, el mayorista y la oferta (RN-15).',
        ],
        alternativos=[
            '1a. A mano: el administrador abre «Ofertas», pestaña «Fuera de temporada», ajusta el factor y pulsa '
            '«Guardar regla», revisa las «Prendas que cumplen hoy el factor» y pulsa «Aplicar ahora»; esas '
            'peticiones quedan en la bitácora.',
            '2a. Regla apagada: el sistema no crea ninguna oferta y cierra las automáticas que sigan vigentes; '
            'apagar la regla desde la pantalla las cierra en el acto.',
            '4a. Ya tiene oferta automática: si está vigente se deja; si el administrador la apagó o la cerró a mano, '
            'no se vuelve a crear (RN-16); si la cerró la regla y el producto vuelve a sobrar, se reabre desde hoy.',
            '5a. Creada hoy: una automática creada hoy que deja de calificar se cierra recién al día siguiente.',
            '6a. Falla una empresa: el sistema deshace lo de esa empresa, anota el error y sigue con las demás.',
        ],
        postcondiciones='Cada producto que cumple el factor tiene una oferta automática vigente, y las que dejaron '
                        'de cumplirlo quedan cerradas en el historial. Correrla de nuevo no repite nada.',
        rastreo='RF-57 · RN-15, RN-16',
    ),
    'CU-33': dict(
        descripcion='Permite al encargado pedir a otra sucursal una cantidad de una prenda, en una talla y un color, '
                    'y al administrador ordenar un traspaso entre dos sucursales sin pedido previo.',
        actores='Encargado de sucursal, administrador de la empresa',
        iniciador='Encargado de sucursal o administrador de la empresa',
        precondiciones='El usuario inició sesión. El encargado tiene una sucursal asignada. La empresa tiene la '
                       'suscripción vigente.',
        flujo=[
            'El encargado abre «Traspasos» y elige la pestaña «Pedir».',
            'El sistema lista las prendas activas que otras sucursales tienen disponibles, filtradas por lo que '
            'escribe en el buscador.',
            'El encargado elige la prenda y el sistema muestra las sucursales que la tienen, con su disponible.',
            'El encargado elige la sucursal de origen, indica la cantidad y, si quiere, el motivo, y pulsa '
            '«Pedir a …».',
            'El sistema toma la sucursal del encargado como destino y verifica que las dos sucursales estén activas '
            'y que la prenda exista y esté activa.',
            'El sistema verifica que el origen tenga disponible la cantidad pedida y que no haya otro traspaso de esa '
            'prenda entre las mismas sucursales sin despachar.',
            'El sistema registra el traspaso de tipo PEDIDO en estado SOLICITADO y avisa a los encargados del origen.',
            'El sistema muestra el número del traspaso y abre la pestaña «Seguimiento».',
        ],
        alternativos=[
            '1a. Ordenar sin pedido: el administrador usa la pestaña «Ordenar», elige también la sucursal de destino '
            'y pulsa «Ordenar traspaso»; el traspaso nace de tipo ORDEN en estado APROBADO y se avisa al origen '
            'para que lo despache (RF-40).',
            '4a. Suscripción vencida: la empresa solo consulta y el sistema rechaza el registro (RN-03, CU-05).',
            '5a. Datos no válidos: una sucursal o la prenda están dadas de baja, el origen y el destino son la misma, '
            'o el encargado intenta pedir para otra sucursal; el sistema rechaza el pedido con el motivo.',
            '6a. No alcanza: el sistema rechaza el pedido mostrando el disponible del origen; ninguna sucursal puede '
            'quedar con existencia negativa (RN-09).',
            '6b. Traspaso abierto: ya hay uno SOLICITADO o APROBADO de esa prenda entre las dos sucursales; el '
            'sistema pide esperar a que se atienda o que lo rechacen.',
        ],
        postcondiciones='El traspaso queda registrado con su tipo, su estado, quién lo pidió y cuándo. Los '
                        'encargados del origen tienen el aviso. La existencia todavía no se mueve. La petición queda '
                        'en la bitácora.',
        rastreo='RF-39, RF-40 · RN-03, RN-09',
    ),
    'CU-34': dict(
        descripcion='Permite a los encargados seguir los traspasos de su sucursal y atender el paso que les toca: '
                    'aprobar, enviar, recibir o rechazar, con su movimiento de inventario.',
        actores='Encargado de sucursal',
        iniciador='Encargado de sucursal',
        precondiciones='El encargado inició sesión y tiene una sucursal asignada. Existe un traspaso en el que su '
                       'sucursal es el origen o el destino.',
        flujo=[
            'El encargado abre «Traspasos», pestaña «Seguimiento», y elige «Para mi sucursal», «Me piden» o '
            '«Todos», y «En curso» o «Historial».',
            'El sistema lista los traspasos de su sucursal con su estado, quién hizo cada paso y las acciones que le '
            'tocan según sea el origen o el destino.',
            'El encargado del origen pulsa «Aprobar» en un traspaso SOLICITADO; puede bajar la cantidad sin superar '
            'lo pedido.',
            'El sistema bloquea el traspaso, verifica que el origen tenga ese disponible y lo deja APROBADO, con '
            'quién y cuándo.',
            'El encargado del origen pulsa «Enviar»; el sistema descuenta la cantidad de la existencia del origen '
            'con un movimiento TRANSFERENCIA, deja el traspaso ENVIADO y avisa a los encargados del destino.',
            'El encargado del destino pulsa «Recibir»; el sistema suma la cantidad a la existencia del destino, que '
            'crea si no existía, con otro movimiento TRANSFERENCIA, y deja el traspaso RECIBIDO.',
            'El sistema confirma cada paso con un mensaje y recarga el seguimiento.',
        ],
        alternativos=[
            '3a. Rechazar: el origen rechaza un traspaso SOLICITADO o APROBADO, o el destino retira su pedido '
            'mientras siga SOLICITADO, escribiendo el motivo; el sistema lo deja RECHAZADO y avisa a la otra '
            'sucursal.',
            '4a. No alcanza: al aprobar o al enviar, si el origen ya no tiene la cantidad, el sistema rechaza el paso '
            'mostrando el disponible y no escribe nada (RN-09).',
            '4b. Paso ajeno o traspaso cambiado: el paso le toca a la otra sucursal, o alguien ya movió el traspaso; '
            'el sistema lo rechaza y la pantalla relee la lista.',
            '5a. Sucursal dada de baja: no se envía si una de las dos está de baja; si el destino se dio de baja con '
            'la mercadería en camino, el origen pulsa «Recibir de vuelta» y las unidades vuelven a su existencia.',
        ],
        postcondiciones='El traspaso avanza de estado con quién y cuándo. Al enviarse la existencia del origen baja '
                        'y al recibirse la del destino sube, con sus movimientos en el kardex; nunca queda negativa. '
                        'Cada paso queda en la bitácora.',
        rastreo='RF-41 · RN-03, RN-09',
    ),
    'CU-35': dict(
        descripcion='Permite al administrador ver qué prendas conviene mover de una sucursal a otra, según lo más '
                    'vendido en cada una y la existencia de cada una, y ordenar el traspaso.',
        actores='Administrador de la empresa',
        iniciador='Administrador de la empresa',
        precondiciones='El administrador inició sesión. El plan de la empresa incluye los traspasos sugeridos. Hay '
                       'ventas cobradas en el período.',
        flujo=[
            'El administrador abre «Traspasos» y elige la pestaña «Sugeridos».',
            'El sistema verifica que el plan incluya la función de traspasos sugeridos (CU-05).',
            'El sistema suma las unidades vendidas de cada prenda en cada sucursal en los últimos 30 días.',
            'Para cada prenda vendida, lee la existencia disponible y el stock mínimo en las sucursales activas, y lo '
            'que ya está en traspasos abiertos.',
            'El sistema calcula por sucursal el objetivo (lo vendido en el período o el stock mínimo, el mayor), lo '
            'que le falta y lo que le sobra.',
            'El sistema reparte lo que sobra hacia las sucursales que venden y les falta, primero a la que más vende '
            'y desde la que más le sobra, y arma cada sugerencia con su razón.',
            'El sistema muestra hasta 100 sugerencias: la prenda, el origen y el destino con su disponible y sus '
            'ventas, la cantidad y la razón.',
        ],
        alternativos=[
            '2a. Plan sin la función: el sistema muestra «Su plan no incluye los traspasos sugeridos» y el botón '
            '«Ver mi plan».',
            '3a. Cambiar el período: el administrador elige 7, 30, 60 o 90 días o pulsa «Recalcular», y el sistema '
            'vuelve a calcular.',
            '6a. Nada que mover: ninguna sucursal se queda corta de lo que vende mientras a otra le sobra; el sistema '
            'lo informa.',
            '7a. Ordenar una sugerencia: el administrador pulsa «Ordenar N u.»; el sistema registra un traspaso de '
            'tipo SUGERIDO en estado APROBADO con la razón como motivo (extiende CU-33) y recalcula las sugerencias.',
        ],
        postcondiciones='La consulta no modifica datos. Lo que ya está en traspaso cuenta en el cálculo, para no '
                        'sugerir dos veces lo mismo. Un traspaso ordenado desde aquí queda listo para que el origen '
                        'lo envíe.',
        rastreo='RF-42, RF-40',
    ),
}


# ------------------------------------------------------------------ validación ---
def validar():
    ids = {c[0] for c in CASOS}
    for r in ROBUSTEZ:
        assert r['cu'] in ids, r['cu']
        tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
                 **{x: 'C' for x in r['c']}, **{x: 'E' for x in r['e']}}
        grupos = sorted({g for g, *_ in r['m']})
        assert grupos == list(range(1, len(r['grupos']) + 1)), (r['cu'], grupos)
        assert 1 <= len(r['grupos']) <= 5, (r['cu'], len(r['grupos']))
        # los grupos van consecutivos en la lista de mensajes
        orden = [g for g, *_ in r['m']]
        assert orden == sorted(orden), (r['cu'], 'grupos no consecutivos')
        for g, de, a, op in r['m']:
            assert de in tipos and a in tipos, (r['cu'], de, a)
            par = {tipos[de], tipos[a]}
            # la regla de la ing: nunca entidad con entidad; tampoco frontera con frontera
            assert par in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'}), (r['cu'], de, a, op)
        usados = {p for _, de, a, _ in r['m'] for p in (de, a)}
        assert usados == set(tipos), (r['cu'], set(tipos) ^ usados)
        # F3: si hay bitácora, van los dos con sus mensajes
        if 'BitacoraMiddleware' in r['c']:
            assert 'AsientoBitacora' in r['e'], r['cu']
            assert any(op == 'registrar(peticion)' for _, _, a, op in r['m'] if a == 'BitacoraMiddleware'), r['cu']
            assert any(op.startswith('agregar(') for _, de, _, op in r['m'] if de == 'BitacoraMiddleware'), r['cu']
    actores_validos = {'Administrador de la plataforma', 'Administrador de la empresa', 'Encargado de sucursal',
                       'Cajero', 'Cliente', 'Proveedor', 'Sistema', 'Usuario', 'Empresa interesada'}
    for c in CASOS:
        assert set(c[2]) <= actores_validos, c[0]
        for x in c[3] + (c[5] if len(c) > 5 else []):
            assert x.startswith('CU-'), (c[0], x)


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


def validar_espec():
    claves = {'descripcion', 'actores', 'iniciador', 'precondiciones', 'flujo', 'alternativos',
              'postcondiciones', 'rastreo'}
    for cu, _, *_ in CASOS:
        assert cu in ESPEC, cu
        e = ESPEC[cu]
        assert set(e) == claves, (cu, set(e) ^ claves)
        assert 5 <= len(e['flujo']) <= 10, (cu, len(e['flujo']))
        assert 2 <= len(e['alternativos']) <= 5, (cu, len(e['alternativos']))
        for alt in e['alternativos']:
            pre = alt.split('.')[0]
            assert pre[:-1].isdigit() and pre[-1].isalpha(), (cu, alt[:20])
        assert 'propio' not in e['descripcion'].lower(), cu


if __name__ == '__main__':
    validar()
    validar_clases()
    validar_espec()
    nuevos = {x for r in ROBUSTEZ for x in r['f'] + r['c'] + r['e']}
    print('ok', len(CASOS), 'casos de uso,', len(ROBUSTEZ), 'robusteces,', len(CLASES), 'clases,',
          len(CUS), 'diseños de clases,', len(ESPEC), 'fichas;', len(DESCRIPCION), 'descripciones nuevas de',
          len(nuevos), 'participantes')
    for cu, d in CUS.items():
        print(' ', cu, len(d["clases"]), 'clases,', len(d["relaciones"]), 'relaciones')
