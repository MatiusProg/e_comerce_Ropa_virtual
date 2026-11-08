# Datos de la 3ra presentación, grupo «e»: CU-42, CU-43, CU-44 (aporte) y CU-45 (aporte).
# Sacados del código de origin/main (08/11):
#   CU-42  backend/app/modules/notificaciones/push_service.py, integrations/push/, core/tareas.py,
#          frontend-web core/services/push-web.service.ts + shared/campanita, mobile core/push/servicio_push.dart
#   CU-43  backend/app/modules/offline/service.py (_devolver_automaticamente, _avisar_resultado, _avisar_lote)
#   CU-44  backend/app/modules/avisos_talla/ + inventario/service.py (_aplicar_movimiento llama al gancho)
#   CU-45  backend/app/modules/analitica/anomalias.py, service.py, repository.py + anomalias-panel.ts
# Módulo autónomo: define CASOS, ROBUSTEZ, DESCRIPCION, CLASES, CUS y ESPEC.
# Uso: python -X utf8 scripts/p3_datos_e.py   (solo valida; no escribe nada)

# ------------------------------------------------------------------ 2.5 ---
CASOS = [
    # (id, nombre, actores, incluye, notas[, extiende])
    ('CU-42', 'Enviar avisos push de las operaciones sin conexión', ['Sistema', 'Usuario'], [],
     'El usuario registra su dispositivo (Web Push con VAPID en la PWA, FCM en el móvil) y el Sistema le manda '
     'por push los avisos: al instante los del lote de la sincronización y en la tarea automática los demás. '
     'RF-65.',
     # La sincronización despacha al terminar el lote, si hay avisos y dispositivos.
     ['CU-17']),
    ('CU-43', 'Devolver automáticamente el pago de una operación rechazada', ['Sistema'], [],
     'Al rechazar una operación cobrada, el QR se reintegra solo (simulado) y el efectivo queda por devolver en '
     'la sucursal (CU-19); se avisa al cliente y a los encargados. RF-66, RF-55, RN-21.',
     ['CU-17']),
    ('CU-44', 'Pedir aviso de talla disponible',
     ['Cliente', 'Encargado de sucursal', 'Administrador de la empresa', 'Sistema'], [],
     'Aporte propio. El cliente pide el aviso de una talla y color agotados; el inventario avisa al pasar la red '
     'de 0 a más de 0 y el personal consulta las tallas esperadas. RF-67, RN-24.'),
    ('CU-45', 'Detectar anomalías en caja y devoluciones', ['Administrador de la empresa'], ['CU-05'],
     'Aporte propio. Isolation Forest sobre los turnos de caja cerrados y las devoluciones, con la explicación de '
     'cada caso por mediana y MAD. Pide la función analitica_ml del plan. RF-68.'),
]

# ------------------------------------------------------------------ 3.2 ---
AE, EN, CL, US, SI = ('A:Administrador de la empresa', 'A:Encargado de sucursal', 'A:Cliente', 'A:Usuario',
                      'A:Sistema')

ROBUSTEZ = [
    dict(cu='CU-42', n='Enviar avisos push de las operaciones sin conexión', a=['Sistema', 'Usuario'],
         f=['PantallaAvisos', 'PantallaInicioSesion', 'TareaProgramada', 'EventoDeConexion', 'CanalPush'],
         c=['GestorPush', 'ControlPush', 'GestorNotificaciones', 'GestorOffline', 'ControlOffline',
            'GestorAutenticacion', 'BitacoraMiddleware'],
         e=['SuscripcionPush', 'Notificacion', 'AsientoBitacora'],
         grupos=['flujo principal: el usuario activa los avisos en la PWA',
                 'flujo principal, pasos 4, 6 a 8: la tarea automática despacha los pendientes',
                 'flujo principal, paso 5: la sincronización despacha al instante',
                 'flujo principal, paso 2 en el móvil: el token de FCM al iniciar sesión',
                 'alternativos 3a y 7a: dispositivo de otra cuenta o que ya no existe'],
         m=[(1, US, 'PantallaAvisos', 'abrirCampanita()'),
            (1, 'PantallaAvisos', 'ControlPush', 'iniciar()'),
            (1, 'ControlPush', 'GestorPush', 'configuracion()'),
            (1, 'GestorPush', 'GestorAutenticacion', 'autorizar(usuario)'),
            (1, 'GestorPush', 'ControlPush', 'clavePublicaVapid(clave)'),
            (1, US, 'PantallaAvisos', 'recibirAvisosEnEsteDispositivo()'),
            (1, 'PantallaAvisos', 'ControlPush', 'activar()'),
            (1, 'ControlPush', 'ControlPush', 'pedirSuscripcion(clavePublica)'),
            (1, 'ControlPush', 'GestorPush', 'registrar("WEBPUSH", direccion, p256dh, auth, dispositivo)'),
            (1, 'GestorPush', 'SuscripcionPush', 'porDireccion(direccion, bloquear)'),
            (1, 'GestorPush', 'SuscripcionPush', 'guardar(usuario, canal, claves, dispositivo)'),
            (1, 'GestorPush', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorPush', 'ControlPush', 'dispositivoRegistrado(suscripcion)'),
            (1, 'ControlPush', 'PantallaAvisos', 'mostrarAvisosActivos()'),
            (2, 'GestorNotificaciones', 'GestorPush', 'tieneDispositivos(destinatario)'),
            (2, 'GestorPush', 'SuscripcionPush', 'existeDe(usuario)'),
            (2, 'GestorNotificaciones', 'Notificacion', 'crear(aviso, push="PENDIENTE")'),
            (2, SI, 'TareaProgramada', 'ejecutarVuelta()'),
            (2, 'TareaProgramada', 'GestorPush', 'despachar()'),
            (2, 'GestorPush', 'Notificacion', 'tomarPendientePush()'),
            (2, 'GestorPush', 'SuscripcionPush', 'dispositivosDe(destinatario)'),
            (2, 'GestorPush', 'CanalPush', 'enviar(destino, aviso)'),
            (2, 'GestorPush', 'SuscripcionPush', 'marcarUsada(ahora)'),
            (2, 'GestorPush', 'Notificacion', 'marcarPush("ENVIADO", ahora)'),
            (2, 'GestorPush', 'TareaProgramada', 'resumen(intentadas, enviadas, fallidas)'),
            (3, SI, 'EventoDeConexion', 'conexionRecuperada()'),
            (3, 'EventoDeConexion', 'ControlOffline', 'sincronizar()'),
            (3, 'ControlOffline', 'GestorOffline', 'sincronizar(lote)'),
            (3, 'GestorOffline', 'GestorNotificaciones', 'avisarA(destinatarios, "OPERACION_OFFLINE")'),
            (3, 'GestorOffline', 'GestorPush', 'despacharSinFallar(idsDelLote)'),
            (3, 'GestorPush', 'CanalPush', 'enviar(destino, aviso)'),
            (4, US, 'PantallaInicioSesion', 'iniciarSesion(slug, correo, contrasena)'),
            (4, 'PantallaInicioSesion', 'ControlPush', 'registrar(dio)'),
            (4, 'ControlPush', 'ControlPush', 'obtenerTokenFcm()'),
            (4, 'ControlPush', 'GestorPush', 'registrar("FCM", token, "App Android")'),
            (4, 'GestorPush', 'SuscripcionPush', 'guardar(usuario, canal, token)'),
            (5, 'GestorPush', 'ControlPush', 'dispositivoAjeno()'),
            (5, 'CanalPush', 'GestorPush', 'errorDePush(invalida)'),
            (5, 'GestorPush', 'SuscripcionPush', 'borrar()'),
            (5, 'GestorPush', 'Notificacion', 'marcarPush("FALLIDO", motivo)')]),

    dict(cu='CU-43', n='Devolver automáticamente el pago de una operación rechazada', a=['Sistema'],
         f=['EventoDeConexion', 'CanalPush'],
         c=['GestorOffline', 'ControlOffline', 'GestorInventario', 'GestorNotificaciones', 'GestorPush',
            'BitacoraMiddleware'],
         e=['OperacionOffline', 'OperacionLocal', 'Cliente', 'Usuario', 'Sucursal', 'Notificacion',
            'AsientoBitacora'],
         grupos=['flujo principal: rechazada y cobrada por QR, se reintegra sola',
                 'alternativo 2a: no se había cobrado, solo se avisa el rechazo',
                 'alternativo 4a: cobrada en efectivo, queda por devolver en la sucursal',
                 'alternativo 6a: venta anónima, el aviso va en el resumen del lote'],
         m=[(1, SI, 'EventoDeConexion', 'conexionRecuperada()'),
            (1, 'EventoDeConexion', 'ControlOffline', 'sincronizar()'),
            (1, 'ControlOffline', 'OperacionLocal', 'pendientes()'),
            (1, 'ControlOffline', 'GestorOffline', 'sincronizar(lote)'),
            (1, 'GestorOffline', 'OperacionOffline', 'operacionPorUuid(uuid)'),
            (1, 'GestorOffline', 'GestorInventario', 'descontar(sucursal, lineas)'),
            (1, 'GestorInventario', 'GestorOffline', 'existenciaInsuficiente()'),
            (1, 'GestorOffline', 'GestorOffline', 'limitarAlTotal(montoCobrado, total)'),
            (1, 'GestorOffline', 'GestorOffline', 'reintegrarQr(operacion)'),
            (1, 'GestorOffline', 'OperacionOffline',
             'guardar(operacion, "RECHAZADA", motivo, devolucionAutomatica, referencia)'),
            (1, 'GestorOffline', 'GestorNotificaciones', 'usuarioDelCliente(cliente)'),
            (1, 'GestorNotificaciones', 'Cliente', 'obtener(cliente)'),
            (1, 'GestorNotificaciones', 'Usuario', 'activo(usuario)'),
            (1, 'GestorOffline', 'GestorNotificaciones', 'avisarA([cliente], "DEVOLUCION_PAGO")'),
            (1, 'GestorNotificaciones', 'Notificacion', 'crear(aviso)'),
            (1, 'GestorOffline', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorOffline', 'GestorPush', 'despacharSinFallar(ids)'),
            (1, 'GestorPush', 'Notificacion', 'tomarPendientePush()'),
            (1, 'GestorPush', 'CanalPush', 'enviar(destino, aviso)'),
            (1, 'GestorOffline', 'ControlOffline', 'resultados(lote)'),
            (1, 'ControlOffline', 'OperacionLocal', 'actualizar(uuid, "rechazada", reintegroQr)'),
            (2, 'GestorOffline', 'OperacionOffline', 'guardar(operacion, "RECHAZADA", motivo)'),
            (2, 'GestorOffline', 'GestorNotificaciones', 'avisarA([cliente], "OPERACION_OFFLINE")'),
            (3, 'GestorOffline', 'Sucursal', 'sucursal(id)'),
            (3, 'GestorOffline', 'GestorNotificaciones', 'encargadosDe(sucursal)'),
            (3, 'GestorNotificaciones', 'Usuario', 'encargadosActivos(sucursal)'),
            (3, 'GestorOffline', 'GestorNotificaciones', 'avisarA(encargados, "DEVOLUCION_PAGO")'),
            (3, 'GestorOffline', 'GestorNotificaciones', 'avisarA([cliente], "DEVOLUCION_PAGO")'),
            (3, 'GestorOffline', 'ControlOffline', 'rechazada(uuid, motivo, requiereDevolucion)'),
            (4, 'GestorOffline', 'GestorNotificaciones', 'avisarA([cajero], resumenDelLote)'),
            (4, 'GestorNotificaciones', 'Notificacion', 'crear(aviso)')]),

    dict(cu='CU-44', n='Pedir aviso de talla disponible',
         a=['Cliente', 'Encargado de sucursal', 'Administrador de la empresa', 'Sistema'],
         f=['PantallaFicha', 'PantallaMisAvisos', 'PantallaTallasEsperadas', 'PantallaInventario',
            'TareaProgramada', 'CanalPush'],
         c=['GestorAvisosTalla', 'GestorAutenticacion', 'GestorInventario', 'GestorNotificaciones', 'GestorPush',
            'BitacoraMiddleware'],
         e=['AvisoTalla', 'VarianteProducto', 'Existencia', 'Sucursal', 'Cliente', 'Notificacion',
            'AsientoBitacora'],
         grupos=['flujo principal: el cliente pide el aviso',
                 'flujo principal, pasos 6 y 7: vuelve la talla y se avisa',
                 'alternativos 4a y 4b: ya lo había pedido o llegaron unidades',
                 'alternativo 8a: cancelar desde «Mis avisos»',
                 'alternativo 8b: el personal consulta las tallas esperadas'],
         m=[(1, CL, 'PantallaFicha', 'elegirTalla(talla)'),
            (1, CL, 'PantallaFicha', 'elegirColor(color)'),
            (1, CL, 'PantallaFicha', 'pedirAviso()'),
            (1, 'PantallaFicha', 'GestorAvisosTalla', 'suscribir(variante)'),
            (1, 'GestorAvisosTalla', 'GestorAutenticacion', 'autorizar("CLIENTE")'),
            (1, 'GestorAvisosTalla', 'Cliente', 'clienteDeUsuario(usuario)'),
            (1, 'GestorAvisosTalla', 'VarianteProducto', 'varianteOfrecible(variante)'),
            (1, 'GestorAvisosTalla', 'AvisoTalla', 'pendienteDe(cliente, variante)'),
            (1, 'GestorAvisosTalla', 'Existencia', 'totalDisponible(variante)'),
            (1, 'GestorAvisosTalla', 'AvisoTalla', 'crear(cliente, variante)'),
            (1, 'GestorAvisosTalla', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorAvisosTalla', 'PantallaFicha', 'avisoRegistrado(aviso)'),
            (2, EN, 'PantallaInventario', 'registrarIngreso(datos)'),
            (2, 'PantallaInventario', 'GestorInventario', 'registrarIngreso(datos)'),
            (2, 'GestorInventario', 'Existencia', 'sumarDisponible(cantidad)'),
            (2, 'GestorInventario', 'GestorAvisosTalla', 'avisarSiVolvio(existencia, cantidad)'),
            (2, 'GestorAvisosTalla', 'AvisoTalla', 'hayPendientes(variante)'),
            (2, 'GestorAvisosTalla', 'Sucursal', 'estaActiva(sucursal)'),
            (2, 'GestorAvisosTalla', 'Existencia', 'totalDisponible(variante)'),
            (2, 'GestorAvisosTalla', 'AvisoTalla', 'pendientesParaActualizar(variante)'),
            (2, 'GestorAvisosTalla', 'GestorNotificaciones', 'notificar(cliente, "STOCK_DISPONIBLE")'),
            (2, 'GestorNotificaciones', 'Notificacion', 'crear(aviso)'),
            (2, 'GestorAvisosTalla', 'AvisoTalla', 'marcarNotificado(ahora, notificacion)'),
            (2, SI, 'TareaProgramada', 'ejecutarVuelta()'),
            (2, 'TareaProgramada', 'GestorPush', 'despachar()'),
            (2, 'GestorPush', 'Notificacion', 'tomarPendientePush()'),
            (2, 'GestorPush', 'CanalPush', 'enviar(destino, aviso)'),
            (3, 'GestorAvisosTalla', 'PantallaFicha', 'avisoRegistrado(avisoExistente)'),
            (3, 'GestorAvisosTalla', 'PantallaFicha', 'yaHayUnidades()'),
            (4, CL, 'PantallaMisAvisos', 'cancelar(aviso)'),
            (4, 'PantallaMisAvisos', 'GestorAvisosTalla', 'cancelar(aviso)'),
            (4, 'GestorAvisosTalla', 'AvisoTalla', 'pendientePropio(aviso, cliente)'),
            (4, 'GestorAvisosTalla', 'AvisoTalla', 'borrar()'),
            (4, 'GestorAvisosTalla', 'PantallaMisAvisos', 'avisoCancelado()'),
            (5, EN, 'PantallaTallasEsperadas', 'abrirTallasEsperadas()'),
            (5, AE, 'PantallaTallasEsperadas', 'abrirTallasEsperadas()'),
            (5, 'PantallaTallasEsperadas', 'GestorAvisosTalla', 'demanda()'),
            (5, 'GestorAvisosTalla', 'GestorAutenticacion', 'autorizar("ENCARGADO", "ADMINISTRADOR")'),
            (5, 'GestorAvisosTalla', 'AvisoTalla', 'pendientesPorVariante()'),
            (5, 'GestorAvisosTalla', 'VarianteProducto', 'detalleDeVariantes(ids)'),
            (5, 'GestorAvisosTalla', 'PantallaTallasEsperadas', 'mostrarDemanda(filas)')]),

    dict(cu='CU-45', n='Detectar anomalías en caja y devoluciones', a=['Administrador de la empresa'],
         f=['PantallaAnomalias'],
         c=['GestorAnalitica', 'DetectorAnomalias', 'GestorAutenticacion', 'VerificadorPlan',
            'BitacoraMiddleware'],
         e=['TurnoCaja', 'Venta', 'Devolucion', 'Usuario', 'ModeloAnalitica', 'AsientoBitacora'],
         grupos=['flujo principal: buscar anomalías',
                 'flujo principal, paso 9: marcar una anomalía como revisada',
                 'alternativo 2a: el plan no incluye la función',
                 'alternativo 3a: menos de 20 turnos cerrados',
                 'alternativo 5a: menos de 15 devoluciones'],
         m=[(1, AE, 'PantallaAnomalias', 'buscarAnomalias()'),
            (1, 'PantallaAnomalias', 'GestorAnalitica', 'entrenarAnomalias(semilla)'),
            (1, 'GestorAnalitica', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorAnalitica', 'VerificadorPlan', 'verificar(empresa, "analitica_ml")'),
            (1, 'GestorAnalitica', 'TurnoCaja', 'turnosCerrados(desde)'),
            (1, 'GestorAnalitica', 'ModeloAnalitica', 'ultimo("ANOMALIAS")'),
            (1, 'GestorAnalitica', 'DetectorAnomalias', 'detectar(matrizTurnos, variablesTurno, semilla)'),
            (1, 'DetectorAnomalias', 'DetectorAnomalias', 'explicar(fila, matriz, variables)'),
            (1, 'GestorAnalitica', 'Devolucion', 'devolucionesRecientes(desde)'),
            (1, 'GestorAnalitica', 'Venta', 'ventasPorCajero(desde)'),
            (1, 'GestorAnalitica', 'DetectorAnomalias',
             'detectar(matrizDevoluciones, variablesDevolucion, semilla)'),
            (1, 'GestorAnalitica', 'ModeloAnalitica', 'guardar(modelo, "ANOMALIAS")'),
            (1, 'GestorAnalitica', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, entidad)'),
            (1, 'GestorAnalitica', 'PantallaAnomalias', 'mostrarAnomalias(turnos, devoluciones)'),
            (2, AE, 'PantallaAnomalias', 'marcarRevisada(grupo, anomalia)'),
            (2, 'PantallaAnomalias', 'GestorAnalitica', 'marcarRevisada(grupo, id)'),
            (2, 'GestorAnalitica', 'ModeloAnalitica', 'ultimo("ANOMALIAS")'),
            (2, 'GestorAnalitica', 'Usuario', 'nombreDe(usuario)'),
            (2, 'GestorAnalitica', 'ModeloAnalitica', 'actualizarResultado(revision)'),
            (2, 'GestorAnalitica', 'BitacoraMiddleware', 'registrar(peticion)'),
            (2, 'GestorAnalitica', 'PantallaAnomalias', 'mostrarAnomalias(turnos, devoluciones)'),
            (3, 'VerificadorPlan', 'GestorAnalitica', 'rechazarPorPlan("plan_limit")'),
            (3, 'GestorAnalitica', 'PantallaAnomalias', 'mostrarCandado()'),
            (4, 'GestorAnalitica', 'PantallaAnomalias', 'faltanTurnos(minimo, hay)'),
            (5, 'GestorAnalitica', 'PantallaAnomalias', 'faltanDevoluciones(minimo, hay)')]),
]

# Solo los nombres NUEVOS de la robustez (los demás ya están en p2_datos.py).
DESCRIPCION = {
    'PantallaAvisos': 'Menú de la campanita (web): los avisos y el botón «Recibir avisos en este dispositivo».',
    'CanalPush': 'Frontera de salida: Firebase Cloud Messaging para la app y Web Push con VAPID para la PWA.',
    'ControlPush': 'Control del dispositivo: PushWebService en la PWA y ServicioPush en el móvil. Suscribe el '
                   'dispositivo y abre la pantalla del aviso al tocarlo.',
    'GestorPush': 'Control del backend de CU-42 (notificaciones/push_service.py): registra dispositivos y despacha '
                  'los avisos pendientes por push.',
    'GestorNotificaciones': 'Crea el aviso en la transacción del hecho (notificaciones/service.py); lo deja con el '
                            'push PENDIENTE si la persona tiene dispositivos.',
    'SuscripcionPush': 'Un dispositivo que acepta avisos push de una persona: token de FCM o suscripción Web Push.',
    'Notificacion': 'Aviso a una persona por un hecho ya ocurrido; guarda el estado del correo y del push.',
    'GestorAvisosTalla': 'Control del backend de CU-44 (avisos_talla/service.py): pedidos de aviso, demanda y el '
                         'gancho que avisa cuando vuelve la talla.',
    'PantallaFicha': 'Ficha de la prenda en la tienda: elegir talla y color y el botón «Avísenme cuando llegue».',
    'PantallaMisAvisos': '«Mis avisos» del cliente: las tallas que espera y las que ya llegaron.',
    'PantallaTallasEsperadas': '«Tallas esperadas» del encargado y del administrador: la demanda en espera.',
    'PantallaInventario': 'Inventario de la sucursal, donde se registra el ingreso de mercadería (CU-21).',
    'AvisoTalla': 'Pedido de un cliente de que le avisen cuando vuelva una variante; pendiente mientras '
                  'notificado_en es nulo.',
    'VarianteProducto': 'Una talla y un color de un producto, con su SKU y su precio.',
    'PantallaAnomalias': 'Panel «Anomalías» dentro de «Analítica inteligente», con las pestañas de turnos y '
                         'devoluciones.',
    'GestorAnalitica': 'Control del backend de la analítica (analitica/service.py): entrena, consulta y marca '
                       'revisadas las anomalías.',
    'DetectorAnomalias': 'Isolation Forest de 200 árboles y la explicación por mediana y MAD (analitica/anomalias.py).',
    'ModeloAnalitica': 'Un entrenamiento guardado; el de tipo ANOMALIAS lleva los casos marcados en resultado.',
}

# ------------------------------------------------------------------ 3.4 ---
B = "backend/app/modules/"
W = "frontend-web/src/app/"
M = "mobile/lib/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."

CLASES = {
    # ---------------- INTERFACES ----------------
    "Campanita": {"tipo": "interfaz", "origen": W + "shared/campanita/campanita.ts",
        "nota": "El botón «Recibir avisos en este dispositivo» solo aparece si push.disponible() (service worker "
                "registrado, es decir build de producción, y clave VAPID configurada).",
        "atributos": [], "operaciones": ["ngOnInit(): void", "alternarPush(): void", "abrir(): void",
                                         "entrar(aviso: Notificacion): void", "marcarTodas(): void"]},
    "Pendientes": {"tipo": "interfaz", "origen": W + "features/caja/pendientes/pendientes.ts",
        "nota": "Muestra «reintegrado por QR (ref. …)» cuando la operación trae reintegro_qr (CU-43).",
        "atributos": [], "operaciones": ["preparar(): Promise<void>", "sincronizar(): Promise<void>", "limpiar(): void"]},
    "Rechazadas": {"tipo": "interfaz", "origen": W + "features/sucursal/rechazadas/rechazadas.ts",
        "nota": "Muestra la marca de devolución automática (fila.devolucion_automatica).",
        "atributos": [], "operaciones": ["cambiarVista(vista: 'por-devolver' | 'todas'): void",
                                         "abrir(fila: OperacionDeSucursal): void", "devolver(fila: OperacionDeSucursal): void"]},
    "Ficha": {"tipo": "interfaz", "origen": W + "features/tienda/ficha/ficha.ts",
        "atributos": [], "operaciones": ["ngOnInit(): void", "pedirAviso(): void", "elegirTalla(tallaId: number): void",
                                         "elegirColor(colorId: number): void", "verFoto(indice: number): void",
                                         "urlDe(url: string | null): string | null", "agregarAlCarrito(): void",
                                         "reservar(): void"]},
    "MisAvisos": {"tipo": "interfaz", "origen": W + "features/cliente/avisos/avisos.ts",
        "atributos": [], "operaciones": ["ngOnInit(): void", "foto(a: AvisoTalla): string | null",
                                         "cancelar(a: AvisoTalla): void"]},
    "TallasEsperadas": {"tipo": "interfaz", "origen": W + "features/sucursal/tallas-esperadas/tallas-esperadas.ts",
        "nota": "La misma pantalla en /admin/tallas-esperadas y /sucursal/tallas-esperadas.",
        "atributos": [], "operaciones": ["ngOnInit(): void", "cargar(): void"]},
    "AnomaliasPanel": {"tipo": "interfaz", "origen": W + "features/reportes/analitica/anomalias/anomalias-panel.ts",
        "atributos": [], "operaciones": ["ngOnInit(): void", "buscar(): void",
                                         "revisar(grupo: GrupoAnomalia, a: Anomalia): void",
                                         "nivel(puntaje: number): 'alto' | 'medio'"]},

    # ---------------- CONTROLES (dispositivo) ----------------
    "PushWebService": {"tipo": "control", "origen": W + "core/services/push-web.service.ts",
        "nota": "Usa SwPush de @angular/service-worker. registrar(), olvidar() y nombreDelDispositivo() son privados.",
        "atributos": ["activo: Signal<boolean>", "ocupado: Signal<boolean>", "disponible: Signal<boolean>",
                      "permisoDenegado: Signal<boolean>"],
        "operaciones": ["iniciar(): Promise<void>", "activar(): Promise<void>", "desactivar(): Promise<void>",
                        "registrar(sub: PushSubscription): Promise<void>", "olvidar(): void",
                        "nombreDelDispositivo(): string"]},
    "ServicioPush": {"tipo": "control", "origen": M + "core/push/servicio_push.dart",
        "nota": "Singleton (ServicioPush.instancia). estado_sesion.dart llama a registrar() al iniciar sesión y a "
                "darDeBaja() antes del logout. Sin google-services.json queda disponible = false.",
        "atributos": ["_disponible: bool", "_tokenRegistrado: String?", "alTocar: void Function(String)?"],
        "operaciones": ["inicializar(): Future<void>", "_abrir(mensaje: RemoteMessage): void",
                        "registrar(dio: Dio): Future<void>", "_enviar(dio: Dio, token: String): Future<void>",
                        "darDeBaja(dio: Dio): Future<void>"]},
    "OfflineService": {"tipo": "control", "origen": W + "core/services/offline.service.ts",
        "atributos": ["enLinea: Signal<boolean>", "operaciones: Signal<OperacionGuardada[]>",
                      "pendientes: Signal<OperacionGuardada[]>"],
        "operaciones": ["sincronizar(): Promise<{confirmadas, rechazadas} | null>",
                        "enviar(lote, cuenta): Promise<'seguir' | 'parar'>", "actualizar(uuid, cambios): Promise<void>",
                        "deSucursal(porDevolver): Observable<OperacionDeSucursal[]>",
                        "registrarDevolucion(uuid, datos): Observable<OperacionDeSucursal>"]},
    "AvisosTallaService": {"tipo": "control", "origen": W + "core/services/avisos-talla.service.ts",
        "atributos": [],
        "operaciones": ["misAvisos(): Observable<AvisoTalla[]>", "variantesEsperadas(): Observable<number[]>",
                        "pedir(varianteId: number): Observable<AvisoTalla>", "cancelar(avisoId: number): Observable<void>",
                        "demanda(): Observable<DemandaTalla[]>", "urlDeImagen(url: string | null): string | null"]},
    "AnaliticaService": {"tipo": "control", "origen": W + "core/services/analitica.service.ts",
        "atributos": [],
        "operaciones": ["resumen(): Observable<ResumenAnalitica>", "entrenar(semilla?: number): Observable<ResumenAnalitica>",
                        "clientes(): Observable<ClienteSegmento[]>", "reporte(formato: 'pdf' | 'xlsx'): Observable<Blob>",
                        "anomalias(): Observable<ResultadoAnomalias>", "buscarAnomalias(): Observable<ResultadoAnomalias>",
                        "marcarRevisada(grupo: GrupoAnomalia, id: number): Observable<ResultadoAnomalias>"]},

    # ---------------- CONTROLES (backend) ----------------
    "push_service": {"tipo": "control", "origen": B + "notificaciones/push_service.py",
        "nota": "Módulo de funciones. Rutas en notificaciones/router.py: GET /notificaciones/push/configuracion, "
                "GET y POST /notificaciones/push/dispositivos, POST /notificaciones/push/dispositivos/baja y "
                "POST /mantenimiento/notificaciones/despacho-push. despachar() toma de a una con FOR UPDATE SKIP LOCKED "
                "y confirma por aviso.",
        "atributos": ["TOPE_POR_DESPACHO: int = 100"],
        "operaciones": ["configuracion(): ConfiguracionPushOut", "tiene_dispositivos(db, usuario_id): bool",
                        "registrar(db, usuario_id, datos): SuscripcionPushOut",
                        "_puede_quedarselo(fila, datos): bool", "dar_de_baja(db, usuario_id, direccion): bool",
                        "mis_dispositivos(db, usuario_id): list[SuscripcionPushOut]", "_aviso_de(n): AvisoPush",
                        "_entregar(db, n): tuple[bool, str | None]", "despachar(db, ids, limite): DespachoOut",
                        "despachar_sin_fallar(db, ids): None"]},
    "push_integracion": {"tipo": "control", "origen": "backend/app/integrations/push/__init__.py",
        "nota": "La costura hacia el push. Con PUSH_PROVEEDOR=real usa ProveedorFcm (fcm.py: API HTTP v1 con un JWT "
                "RS256 de la cuenta de servicio) y ProveedorWebPush (webpush.py: pywebpush con VAPID); con simulado, "
                "ProveedorSimulado. Un 404/410 o UNREGISTERED levanta ErrorDePush(invalida=True).",
        "atributos": [],
        "operaciones": ["enviar(destino: Destino, aviso: AvisoPush): None", "proveedor_de(canal: str): ProveedorPush",
                        "_proveedores(): dict[str, ProveedorPush]"]},
    "notificaciones_service": {"tipo": "control", "origen": B + "notificaciones/service.py",
        "atributos": [],
        "operaciones": ["notificar(db, destinatario, tipo, titulo, cuerpo, enlace, entidad, entidad_id): Notificacion",
                        "avisar_a(db, destinatarios, tipo, titulo, cuerpo, enlace, entidad, entidad_id): list[Notificacion]",
                        "usuario_del_cliente(db, cliente_id): Usuario | None",
                        "encargados_de(db, sucursal_id): list[Usuario]",
                        "despachar_pendientes(db, limite): DespachoOut"]},
    "tareas": {"tipo": "control", "origen": "backend/app/core/tareas.py",
        "nota": "Tarea asyncio dentro del backend (TAREAS_AUTOMATICAS=on), cada TAREAS_INTERVALO_MINUTOS; un "
                "pg_try_advisory_lock evita que los dos workers corran la misma vuelta.",
        "atributos": ["CLAVE_DEL_BLOQUEO: int", "ESPERA_INICIAL_SEGUNDOS: int = 60"],
        "operaciones": ["correr_vuelta(fabrica_de_sesiones, minimo_entre_vueltas): Vuelta", "_push(db, empresa_id): None",
                        "_correos(db, empresa_id): None", "_intentar(vuelta, db, nombre, tarea): None",
                        "_bucle(): None", "ciclo_de_vida(app)"]},
    "offline_service": {"tipo": "control", "origen": B + "offline/service.py",
        "nota": "Módulo de funciones. Ruta POST /offline/sincronizar (CU-17) y POST /offline/operaciones/{uuid}/devolucion "
                "(CU-19).",
        "atributos": [],
        "operaciones": ["sincronizar(db, usuario_id, rol, sucursal_del_usuario, lote): LoteOut",
                        "_sincronizar_una(db, op, usuario_id, rol, sucursal_del_usuario, dispositivo, avisos): ResultadoOut",
                        "_resultado(db, fila, repetida): ResultadoOut", "_por_devolver(fila): bool",
                        "_reintegrar_qr(fila): str", "_devolver_automaticamente(fila): None",
                        "_que_es(fila): str", "_avisar_resultado(db, fila): list",
                        "_avisar_lote(db, resultados, usuario_id, rol): list[int]",
                        "registrar_devolucion(db, uuid, datos, usuario_id, sucursal_id): OperacionOut"]},
    "avisos_talla_service": {"tipo": "control", "origen": B + "avisos_talla/service.py",
        "nota": "Rutas en avisos_talla/router.py: /tienda/avisos-talla (GET, GET /variantes, POST, DELETE /{id}; rol "
                "CLIENTE) e /inventario/avisos-talla (GET; ENCARGADO y ADMINISTRADOR).",
        "atributos": ["VIGENCIA_DE_LOS_AVISADOS: timedelta = 30 días"],
        "operaciones": ["total_disponible(db, variante_id): int",
                        "_variante_ofrecible(db, variante_id): VarianteProducto | None",
                        "_detalle_de_variantes(db, ids): dict[int, dict]",
                        "suscribir(db, usuario_id, variante_id): AvisoOut", "mis_avisos(db, usuario_id): list[AvisoOut]",
                        "variantes_esperadas(db, usuario_id): list[int]", "cancelar(db, usuario_id, aviso_id): None",
                        "_a_salida(db, avisos): list[AvisoOut]", "demanda(db): list[DemandaOut]",
                        "avisar_si_volvio(db, existencia, cantidad): int"]},
    "inventario_service": {"tipo": "control", "origen": B + "inventario/service.py",
        "nota": "Solo lo que toca CU-44: _aplicar_movimiento es el único lugar que cambia un saldo y llama al gancho "
                "avisar_si_volvio cuando la cantidad es positiva.",
        "atributos": [],
        "operaciones": ["_aplicar_movimiento(db, existencia, tipo, cantidad, reservada_delta, motivo, proveedor_id, "
                        "referencia, usuario_id): MovimientoInventario",
                        "registrar_ingreso(db, datos, usuario_id, confirmar, movimientos): IngresoOut"]},
    "analitica_service": {"tipo": "control", "origen": B + "analitica/service.py",
        "nota": "Rutas en analitica/router.py (ADMINISTRADOR + requiere_funcion('analitica_ml')): GET y POST "
                "/analitica/anomalias, POST /analitica/anomalias/{grupo}/{item_id}/revisada.",
        "atributos": ["DIAS_ANOMALIAS: int = 365"],
        "operaciones": ["entrenar_anomalias(db, usuario_id, semilla): dict", "consultar_anomalias(db): dict",
                        "marcar_revisada(db, grupo, item_id, usuario_id): dict",
                        "_matriz_turnos(filas): np.ndarray", "_matriz_devoluciones(filas, ventas_cajero): np.ndarray",
                        "_revisadas_previas(db): dict[str, dict]", "_items(filas, d, armar, grupo, revisadas): list[dict]",
                        "_turno(f): dict", "_devolucion(f): dict", "_grupo(filas, d, armar, grupo, revisadas): dict",
                        "_guardar(db, tipo, e, inicio, usuario_id): ModeloAnalitica"]},
    "anomalias": {"tipo": "control", "origen": B + "analitica/anomalias.py",
        "nota": "Es el DetectorAnomalias del .md del aporte. Usa sklearn.ensemble.IsolationForest.",
        "atributos": ["CONTAMINACION: float = 0.05", "PARAMETROS_IF: dict = {n_estimators: 200}",
                      "MIN_TURNOS: int = 20", "MIN_DEVOLUCIONES: int = 15", "VARIABLES_TURNO: tuple[Variable]",
                      "VARIABLES_DEVOLUCION: tuple[Variable]"],
        "operaciones": ["detectar(matriz, variables, semilla): Detectado",
                        "explicar(x, matriz, variables): str", "_frase(v, x, mediana): str",
                        "_formatear(valor, unidad): str", "serializar(modelos): bytes"]},
    "verificador": {"tipo": "control", "origen": B + "plataforma/verificador.py",
        "nota": "CU-05. requiere_funcion('analitica_ml') de core/dependencies.py llama a verificar_funcion.",
        "atributos": [],
        "operaciones": ["verificar_funcion(db, funcion): None", "incluye(db, funcion): bool"]},
    "BitacoraMiddleware": {"tipo": "control", "origen": B + "bitacora/middleware.py",
        "nota": "Anota toda peticion POST/PUT/PATCH/DELETE (y las exportaciones GET). _anotar llama a bitacora/service.py "
                "registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, "
                "agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
        "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response",
                                         "_anotar(peticion: Request, respuesta): None"]},

    # ---------------- ENTIDADES ----------------
    "SuscripcionPush": {"tipo": "entidad", "origen": B + "notificaciones/models.py", "tabla": "suscripcion_push",
        "nota": "UNIQUE (empresa_id, direccion). CHECK canal IN ('FCM','WEBPUSH') y WEBPUSH con sus dos claves. "
                "No hay repository: las consultas están en push_service.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "usuario_id: BIGINT (FK usuario, ON DELETE CASCADE)",
                      "canal: VARCHAR(10)", "direccion: TEXT", "clave_p256dh: VARCHAR(200)", "clave_auth: VARCHAR(100)",
                      "dispositivo: VARCHAR(120)", "creada_en: TIMESTAMPTZ", "usada_en: TIMESTAMPTZ"],
        "operaciones": ["tiene_dispositivos(db, usuario_id): bool  [notificaciones/push_service.py]",
                        "registrar(db, usuario_id, datos): SuscripcionPushOut  [notificaciones/push_service.py, FOR UPDATE]",
                        "dar_de_baja(db, usuario_id, direccion): bool  [notificaciones/push_service.py]",
                        "mis_dispositivos(db, usuario_id): list[SuscripcionPushOut]  [notificaciones/push_service.py]",
                        "_entregar(db, n): tuple[bool, str | None]  [notificaciones/push_service.py]"]},
    "Notificacion": {"tipo": "entidad", "origen": B + "notificaciones/models.py", "tabla": "notificacion",
        "nota": "tipo incluye OPERACION_OFFLINE, DEVOLUCION_PAGO y STOCK_DISPONIBLE. push_estado: OMITIDO | PENDIENTE | "
                "ENVIADO | FALLIDO; ENVIADO si y solo si push_enviado_en no es nulo.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "destinatario_id: BIGINT (FK usuario, ON DELETE CASCADE)",
                      "tipo: VARCHAR(40)", "titulo: VARCHAR(160)", "cuerpo: TEXT", "enlace: VARCHAR(300)",
                      "entidad: VARCHAR(60)", "entidad_id: BIGINT", "creada_en: TIMESTAMPTZ", "leida_en: TIMESTAMPTZ",
                      "correo_estado: VARCHAR(20)", "correo_enviado_en: TIMESTAMPTZ", "correo_error: VARCHAR(300)",
                      "push_estado: VARCHAR(20)", "push_enviado_en: TIMESTAMPTZ", "push_error: VARCHAR(300)"],
        "operaciones": ["crear(db, destinatario_id, tipo, titulo, cuerpo, enlace, entidad, entidad_id, correo_estado, "
                        "correo_error, push_estado): Notificacion  [notificaciones/repository.py]",
                        "contar_de(db, destinatario_id, solo_no_leidas): int  [notificaciones/repository.py]",
                        "listar_de(db, destinatario_id, ...): list[Notificacion]  [notificaciones/repository.py]",
                        "marcar_leidas(db, ...): int  [notificaciones/repository.py]",
                        "tomar_pendiente_de_correo(db): Notificacion | None  [notificaciones/repository.py]",
                        "despachar(db, ids, limite): DespachoOut  [notificaciones/push_service.py, FOR UPDATE SKIP LOCKED]"]},
    "OperacionOffline": {"tipo": "entidad", "origen": B + "offline/models.py", "tabla": "operacion_offline",
        "nota": "CHECK devolucion_con_responsable: devuelto_en IS NULL OR devolucion_automatica OR devuelto_por IS NOT NULL.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "uuid: UUID (UNIQUE)", "tipo: VARCHAR(10)",
                      "estado: VARCHAR(12)", "sucursal_id: INTEGER (FK sucursal)", "usuario_id: BIGINT (FK usuario)",
                      "dispositivo: VARCHAR(80)", "creada_en_cliente: TIMESTAMPTZ", "recibida_en: TIMESTAMPTZ",
                      "intentos: SMALLINT", "metodo_pago: VARCHAR(10)", "monto_cobrado: NUMERIC(12,2)",
                      "referencia_pago: VARCHAR(60)", "carga: JSONB", "venta_id: BIGINT (FK venta, UNIQUE)",
                      "reserva_id: BIGINT (FK reserva, UNIQUE)", "motivo_rechazo: VARCHAR(300)", "devuelto_en: TIMESTAMPTZ",
                      "devuelto_por: BIGINT (FK usuario)", "metodo_devolucion: VARCHAR(10)",
                      "referencia_devolucion: VARCHAR(60)", "observacion_devolucion: VARCHAR(300)",
                      "cliente_id: BIGINT (FK cliente)", "devolucion_automatica: BOOLEAN"],
        "operaciones": ["operacion_por_uuid(db, uuid, bloquear): OperacionOffline | None  [offline/repository.py]",
                        "operaciones(db, sucursal_id, usuario_id, estado, por_devolver, limite): list[tuple[OperacionOffline, Usuario]]  [offline/repository.py]",
                        "efectivo_por_devolver(db, turno_id): tuple[int, Decimal]  [caja/repository.py]"]},
    "Cliente": {"tipo": "entidad", "origen": B + "seguridad/models.py", "tabla": "cliente", "nota": OMIT_AUD +
                " Sin empresa_id: la cuenta del cliente es única en la plataforma (RN-13).",
        "atributos": ["id: BIGINT (PK)", "usuario_id: BIGINT (FK usuario, UNIQUE)", "documento: VARCHAR(20) (UNIQUE)",
                      "telefono: VARCHAR(20)", "talla_superior: VARCHAR(10)", "talla_inferior: VARCHAR(10)"],
        "operaciones": ["_usuario_del_cliente(db, cliente_id): Usuario | None  [notificaciones/service.py]",
                        "cliente_id_de_usuario(db, usuario_id): int  [seguridad/service.py]"]},
    "Usuario": {"tipo": "entidad", "origen": B + "seguridad/models.py", "tabla": "usuario", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "correo: VARCHAR(120)", "hash_contrasena: VARCHAR(255)", "nombres: VARCHAR(80)",
                      "apellidos: VARCHAR(80)", "rol_id: SMALLINT (FK rol)", "activo: BOOLEAN", "empresa_id: BIGINT (FK empresa)"],
        "operaciones": ["_usuario_activo(db, usuario_id): Usuario | None  [notificaciones/service.py]",
                        "_encargados_de(db, sucursal_id): list[Usuario]  [notificaciones/service.py, JOIN empleado]"]},
    "AvisoTalla": {"tipo": "entidad", "origen": B + "avisos_talla/models.py", "tabla": "aviso_talla",
        "nota": "Migración 0042, RLS con FORCE. Índice único parcial uq_aviso_talla_pendiente (cliente_id, variante_id) "
                "WHERE notificado_en IS NULL (RN-24). No hay repository: las consultas están en avisos_talla/service.py.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "cliente_id: BIGINT (FK cliente, ON DELETE CASCADE)",
                      "variante_id: BIGINT (FK variante_producto, ON DELETE CASCADE)", "creado_en: TIMESTAMPTZ",
                      "notificado_en: TIMESTAMPTZ", "notificacion_id: BIGINT (FK notificacion, ON DELETE SET NULL)"],
        "operaciones": ["suscribir(db, usuario_id, variante_id): AvisoOut  [avisos_talla/service.py]",
                        "mis_avisos(db, usuario_id): list[AvisoOut]  [avisos_talla/service.py]",
                        "cancelar(db, usuario_id, aviso_id): None  [avisos_talla/service.py]",
                        "demanda(db): list[DemandaOut]  [avisos_talla/service.py, GROUP BY variante_id]",
                        "avisar_si_volvio(db, existencia, cantidad): int  [avisos_talla/service.py, FOR UPDATE]"]},
    "VarianteProducto": {"tipo": "entidad", "origen": B + "catalogo/models.py", "tabla": "variante_producto", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "producto_id: BIGINT (FK producto)",
                      "talla_id: INTEGER (FK talla)", "color_id: INTEGER (FK color)", "sku: VARCHAR(40)",
                      "precio: NUMERIC(10,2)", "activa: BOOLEAN"],
        "operaciones": ["_variante_ofrecible(db, variante_id): VarianteProducto | None  [avisos_talla/service.py]",
                        "_detalle_de_variantes(db, ids): dict[int, dict]  [avisos_talla/service.py]"]},
    "Existencia": {"tipo": "entidad", "origen": B + "inventario/models.py", "tabla": "existencia", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "variante_id: BIGINT (FK variante_producto)",
                      "sucursal_id: INTEGER (FK sucursal)", "cantidad_disponible: INTEGER", "cantidad_reservada: INTEGER",
                      "stock_minimo: INTEGER"],
        "operaciones": ["obtener_existencia(db, variante_id, sucursal_id, bloquear): Existencia | None  [inventario/repository.py]",
                        "agregar_movimiento(db, existencia_id, tipo, cantidad, ...): MovimientoInventario  [inventario/repository.py]",
                        "total_disponible(db, variante_id): int  [avisos_talla/service.py, JOIN sucursal activa]"]},
    "ModeloAnalitica": {"tipo": "entidad", "origen": B + "analitica/models.py", "tabla": "modelo_analitica",
        "nota": "Migración 0040; la 0043 amplía el CHECK del tipo a ('DEMANDA', 'SEGMENTOS', 'ANOMALIAS'). En resultado "
                "quedan turnos y devoluciones con {suficientes, muestras, mensaje, medianas, marcadas[]}.",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "tipo: VARCHAR(12)", "parametros: JSONB",
                      "metricas: JSONB", "resultado: JSONB", "filas_entrenamiento: INTEGER", "filas_reales: INTEGER",
                      "filas_sinteticas: INTEGER", "duracion_ms: INTEGER", "modelo: BYTEA",
                      "entrenado_por: BIGINT (FK usuario, ON DELETE SET NULL)", "entrenado_en: TIMESTAMPTZ"],
        "operaciones": ["guardar(db, modelo): ModeloAnalitica  [analitica/repository.py]",
                        "ultimo(db, tipo): ModeloAnalitica | None  [analitica/repository.py]",
                        "historial(db): list[Row]  [analitica/repository.py]"]},
    "TurnoCaja": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "turno_caja",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "caja_id: INTEGER (FK caja)",
                      "usuario_id: BIGINT (FK usuario)", "abierto_en: TIMESTAMPTZ", "cerrado_en: TIMESTAMPTZ",
                      "monto_apertura: NUMERIC(10,2)", "monto_cierre: NUMERIC(10,2)", "monto_esperado: NUMERIC(10,2)"],
        "operaciones": ["turnos_cerrados(db, desde): list[Row]  [analitica/repository.py, JOIN caja, sucursal, usuario, venta, devolucion]",
                        "turno_por_id(db, turno_id): TurnoCaja | None  [caja/repository.py]"]},
    "Devolucion": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "devolucion",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta)",
                      "turno_caja_id: BIGINT (FK turno_caja)", "origen: VARCHAR(6)", "recibida_por: BIGINT (FK usuario)",
                      "reembolso_referencia: VARCHAR(100)", "reembolso_monto: NUMERIC(10,2)", "tipo: VARCHAR(12)",
                      "venta_cambio_id: BIGINT (FK venta, UNIQUE)", "motivo: VARCHAR(200)", "monto: NUMERIC(10,2)",
                      "diferencia: NUMERIC(10,2)", "metodo_diferencia: VARCHAR(20)", "creado_en: TIMESTAMPTZ",
                      "estado: VARCHAR(10)", "conforme: BOOLEAN", "observacion_cliente: VARCHAR(300)"],
        "operaciones": ["devoluciones_recientes(db, desde): list[Row]  [analitica/repository.py, JOIN detalle_devolucion, detalle_venta]",
                        "devoluciones_del_turno(db, turno_id): Decimal  [caja/repository.py]"]},
    "Venta": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "venta",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(20) (UNIQUE)", "canal: VARCHAR(12)",
                      "estado: VARCHAR(20)", "cliente_id: BIGINT (FK cliente)", "sucursal_id: INTEGER (FK sucursal)",
                      "turno_caja_id: BIGINT (FK turno_caja)", "metodo_pago: VARCHAR(20)", "subtotal: NUMERIC(10,2)",
                      "descuento: NUMERIC(10,2)", "total: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ"],
        "nota": "Solo las columnas que lee el análisis; el resto, en el 3.4 de la P2.",
        "operaciones": ["ventas_por_cajero(db, desde): dict[int, int]  [analitica/repository.py]",
                        "efectivo_cobrado(db, turno_id): Decimal  [caja/repository.py]"]},
    "AsientoBitacora": {"tipo": "entidad", "origen": B + "bitacora/models.py", "tabla": "bitacora",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ",
                      "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)", "actor: VARCHAR(160)", "rol: VARCHAR(40)",
                      "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
                      "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)",
                      "detalle: JSONB"],
        "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int",
                        "listar(db, limite, desplazamiento, **filtros): list[tuple]", "acciones(db): list[str]",
                        "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}

# FK reales (multiplicidad: primero en el extremo ClaseA, después en ClaseB)
FK = [
    ["Usuario", "SuscripcionPush", "TIENE", "1", "0..*"],
    ["Usuario", "Notificacion", "RECIBE", "1", "0..*"],
    ["Usuario", "OperacionOffline", "REGISTRA", "1", "0..*"],
    ["Usuario", "OperacionOffline", "DEVUELVE", "0..1", "0..*"],
    ["Cliente", "OperacionOffline", "ES_CLIENTE_DE", "0..1", "0..*"],
    ["Usuario", "Cliente", "ES", "1", "0..1"],
    ["Cliente", "AvisoTalla", "PIDE", "1", "0..*"],
    ["VarianteProducto", "AvisoTalla", "ES_ESPERADA_EN", "1", "0..*"],
    ["Notificacion", "AvisoTalla", "AVISA", "0..1", "0..1"],
    ["VarianteProducto", "Existencia", "TIENE_SALDO_EN", "1", "0..*"],
    ["Usuario", "ModeloAnalitica", "ENTRENA", "0..1", "0..*"],
    ["Usuario", "TurnoCaja", "ABRE", "1", "0..*"],
    ["TurnoCaja", "Venta", "AGRUPA", "0..1", "0..*"],
    ["TurnoCaja", "Devolucion", "PROCESA", "0..1", "0..*"],
    ["Venta", "Devolucion", "SE_DEVUELVE_EN", "1", "0..*"],
    ["Venta", "Devolucion", "SE_CAMBIA_POR", "0..1", "0..1"],
    ["Usuario", "Devolucion", "RECIBE", "0..1", "0..*"],
    ["Usuario", "AsientoBitacora", "DEJA_RASTRO_EN", "0..1", "0..*"],
]


def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]


def bit(controles):
    return ([[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles]
            + [["BitacoraMiddleware", "AsientoBitacora", "REGISTRA", "1", "0..*"]])


CUS = {}

c42 = ["Campanita", "PushWebService", "ServicioPush", "push_service", "push_integracion", "notificaciones_service",
       "offline_service", "tareas", "BitacoraMiddleware", "AsientoBitacora", "SuscripcionPush", "Notificacion"]
CUS["CU-42"] = {"actores": ["Sistema", "Cliente", "Cajero"], "clases": c42,
    "operaciones_en_cu": {"offline_service": ["sincronizar(db, usuario_id, rol, sucursal_del_usuario, lote)",
                                              "_avisar_resultado(db, fila)", "_avisar_lote(db, resultados, usuario_id, rol)"],
                          "notificaciones_service": ["notificar(...)", "avisar_a(...)"],
                          "tareas": ["correr_vuelta(fabrica_de_sesiones, minimo_entre_vueltas)", "_push(db, empresa_id)",
                                     "_bucle()"],
                          "Campanita": ["ngOnInit()", "alternarPush()"]},
    "nota": "El registro del dispositivo (POST /notificaciones/push/dispositivos) es lo que anota la bitácora; el "
            "despacho de la tarea automática no pasa por HTTP y no deja asiento. sincronizar() llama a "
            "push_service.despachar_sin_fallar(db, ids) con los avisos del lote. Omitida por el tope la entidad "
            "Usuario (FK de suscripcion_push.usuario_id y notificacion.destinatario_id). En el móvil, "
            "estado_sesion.dart llama a ServicioPush.registrar() al iniciar sesión (no hay botón).",
    "relaciones": [["Cliente", "Campanita", "USA", "1", "1"], ["Cajero", "Campanita", "USA", "1", "1"],
                   ["Cliente", "ServicioPush", "RECIBE_AVISOS_EN", "1", "1"],
                   ["Campanita", "PushWebService", "SOLICITA", "1", "1"],
                   ["PushWebService", "push_service", "REGISTRA_DISPOSITIVO_EN", "1", "1"],
                   ["ServicioPush", "push_service", "REGISTRA_DISPOSITIVO_EN", "1", "1"],
                   ["push_service", "SuscripcionPush", "REGISTRA", "1", "0..*"],
                   ["push_service", "Notificacion", "ACTUALIZA", "1", "0..*"],
                   ["push_service", "push_integracion", "LLAMA_A", "1", "1"],
                   ["notificaciones_service", "push_service", "CONSULTA", "1", "1"],
                   ["notificaciones_service", "Notificacion", "REGISTRA", "1", "0..*"],
                   ["offline_service", "notificaciones_service", "LLAMA_A", "1", "1"],
                   ["offline_service", "push_service", "LLAMA_A", "1", "1"],
                   ["Sistema", "tareas", "EJECUTA", "1", "1"],
                   ["tareas", "push_service", "LLAMA_A", "1", "1"]] + bit(["push_service", "offline_service"]) + fks(c42)}

c43 = ["Pendientes", "Rechazadas", "OfflineService", "offline_service", "notificaciones_service", "push_service",
       "BitacoraMiddleware", "AsientoBitacora", "OperacionOffline", "Cliente", "Usuario", "Notificacion"]
CUS["CU-43"] = {"actores": ["Sistema", "Cajero", "Encargado"], "clases": c43,
    "operaciones_en_cu": {"offline_service": ["sincronizar(...)", "_sincronizar_una(...)", "_resultado(db, fila, repetida)",
                                              "_por_devolver(fila)", "_reintegrar_qr(fila)", "_devolver_automaticamente(fila)",
                                              "_que_es(fila)", "_avisar_resultado(db, fila)",
                                              "_avisar_lote(db, resultados, usuario_id, rol)",
                                              "registrar_devolucion(db, uuid, datos, usuario_id, sucursal_id)"],
                          "OfflineService": ["sincronizar()", "enviar(lote, cuenta)", "actualizar(uuid, cambios)",
                                             "deSucursal(porDevolver)"],
                          "notificaciones_service": ["avisar_a(...)", "usuario_del_cliente(db, cliente_id)",
                                                     "encargados_de(db, sucursal_id)"],
                          "push_service": ["despachar_sin_fallar(db, ids)", "despachar(db, ids, limite)"],
                          "Pendientes": ["sincronizar()"], "Rechazadas": ["cambiarVista(vista)"]},
    "nota": "El actor del caso de uso es el Sistema: la devolución ocurre dentro de POST /offline/sincronizar, que "
            "dispara el dispositivo solo (evento 'online' y cada 60 s); el Cajero y el Encargado solo ven el resultado. "
            "El reintegro del QR es simulado (_reintegrar_qr devuelve 'REINT-QR-' + 10 hex del uuid). El efectivo no "
            "se devuelve solo: queda en CU-19 y caja/repository.py efectivo_por_devolver lo suma al arqueo. "
            "registrar_devolucion responde 409 si devolucion_automatica ya es verdadero. Omitida Sucursal por el tope.",
    "relaciones": [["Sistema", "OfflineService", "DISPARA_SINCRONIZACION", "1", "1"],
                   ["Cajero", "Pendientes", "USA", "1", "1"], ["Encargado", "Rechazadas", "USA", "1", "1"],
                   ["Pendientes", "OfflineService", "CONSULTA", "1", "1"], ["Rechazadas", "OfflineService", "CONSULTA", "1", "1"],
                   ["OfflineService", "offline_service", "ENVIA_LOTE_A", "1", "1"],
                   ["offline_service", "OperacionOffline", "ACTUALIZA", "1", "0..*"],
                   ["offline_service", "notificaciones_service", "LLAMA_A", "1", "1"],
                   ["offline_service", "push_service", "LLAMA_A", "1", "1"],
                   ["notificaciones_service", "Cliente", "CONSULTA", "1", "0..1"],
                   ["notificaciones_service", "Usuario", "CONSULTA", "1", "0..*"],
                   ["notificaciones_service", "Notificacion", "REGISTRA", "1", "0..*"],
                   ["push_service", "Notificacion", "ACTUALIZA", "1", "0..*"]] + bit(["offline_service"]) + fks(c43)}

c44 = ["Ficha", "MisAvisos", "TallasEsperadas", "AvisosTallaService", "avisos_talla_service", "inventario_service",
       "notificaciones_service", "BitacoraMiddleware", "AsientoBitacora", "AvisoTalla", "VarianteProducto", "Existencia"]
CUS["CU-44"] = {"actores": ["Cliente", "Encargado", "Administrador"], "clases": c44,
    "operaciones_en_cu": {"Ficha": ["ngOnInit()", "pedirAviso()", "elegirTalla(tallaId)", "elegirColor(colorId)"],
                          "notificaciones_service": ["notificar(...)", "usuario_del_cliente(db, cliente_id)"]},
    "nota": "El cliente se resuelve con seguridad/service.py cliente_id_de_usuario. Omitidas por el tope: Cliente y "
            "Notificacion (FK de aviso_talla), push_service y tareas (el despacho es el de CU-42) y el móvil "
            "(pantalla_ficha.dart _BotonAvisame, estado_avisos_talla.dart ControlAvisosTalla y "
            "repositorio_avisos_talla.dart RepositorioAvisosTalla, que solo piden el aviso). La ficha decide mostrar "
            "el botón con la disponibilidad del catálogo público.",
    "relaciones": [["Cliente", "Ficha", "USA", "1", "1"], ["Cliente", "MisAvisos", "USA", "1", "1"],
                   ["Encargado", "TallasEsperadas", "USA", "1", "1"], ["Administrador", "TallasEsperadas", "USA", "1", "1"],
                   ["Ficha", "AvisosTallaService", "SOLICITA", "1", "1"], ["MisAvisos", "AvisosTallaService", "SOLICITA", "1", "1"],
                   ["TallasEsperadas", "AvisosTallaService", "CONSULTA", "1", "1"],
                   ["AvisosTallaService", "avisos_talla_service", "LLAMA_A", "1", "1"],
                   ["avisos_talla_service", "AvisoTalla", "REGISTRA", "1", "0..*"],
                   ["avisos_talla_service", "VarianteProducto", "CONSULTA", "1", "0..*"],
                   ["avisos_talla_service", "Existencia", "CONSULTA", "1", "0..*"],
                   ["inventario_service", "Existencia", "ACTUALIZA", "1", "0..*"],
                   ["inventario_service", "avisos_talla_service", "AVISA_A", "1", "1"],
                   ["avisos_talla_service", "notificaciones_service", "LLAMA_A", "1", "1"]]
                  + bit(["avisos_talla_service", "inventario_service"]) + fks(c44)}

c45 = ["AnomaliasPanel", "AnaliticaService", "analitica_service", "anomalias", "verificador", "BitacoraMiddleware",
       "AsientoBitacora", "ModeloAnalitica", "TurnoCaja", "Devolucion", "Venta", "Usuario"]
CUS["CU-45"] = {"actores": ["Administrador"], "clases": c45,
    "operaciones_en_cu": {"AnaliticaService": ["anomalias()", "buscarAnomalias()", "marcarRevisada(grupo, id)"]},
    "nota": "Solo datos reales, sin sintéticos (filas_sinteticas = 0). turnos_cerrados lee además caja y sucursal; "
            "devoluciones_recientes lee detalle_devolucion y detalle_venta para el valor devuelto (omitidas por el tope). "
            "repository.guardar borra los análisis viejos y conserva los últimos 5 (CONSERVAR). La revisión queda dentro "
            "del JSONB resultado como {por, en}.",
    "relaciones": [["Administrador", "AnomaliasPanel", "USA", "1", "1"],
                   ["AnomaliasPanel", "AnaliticaService", "SOLICITA", "1", "1"],
                   ["AnaliticaService", "analitica_service", "LLAMA_A", "1", "1"],
                   ["analitica_service", "verificador", "VERIFICA_CON", "1", "1"],
                   ["analitica_service", "anomalias", "ENTRENA_CON", "1", "1"],
                   ["analitica_service", "ModeloAnalitica", "REGISTRA", "1", "0..*"],
                   ["analitica_service", "TurnoCaja", "CONSULTA", "1", "0..*"],
                   ["analitica_service", "Devolucion", "CONSULTA", "1", "0..*"],
                   ["analitica_service", "Venta", "CONSULTA", "1", "0..*"],
                   ["analitica_service", "Usuario", "CONSULTA", "1", "0..1"]] + bit(["analitica_service"]) + fks(c45)}

# ------------------------------------------------------------------ 2.6 ---
ESPEC = {
    'CU-42': {
        'descripcion': 'Envía al cliente, al cajero y al encargado, en el teléfono o en el navegador y aunque la '
                       'aplicación esté cerrada, el aviso de lo que pasó con sus operaciones sin conexión.',
        'actores': 'Sistema, usuario (cliente, cajero o encargado)',
        'iniciador': 'Sistema',
        'precondiciones': 'El usuario inició sesión y aceptó los avisos en su dispositivo. El servidor tiene '
                          'configurado Web Push (claves VAPID) o FCM; si no, usa el canal simulado.',
        'flujo': [
            'El usuario abre la campanita y pulsa «Recibir avisos en este dispositivo».',
            'El sistema entrega la clave pública VAPID; el navegador crea la suscripción y la envía con sus claves. '
            'En el móvil, la aplicación envía su token de FCM sola al iniciar sesión.',
            'El sistema guarda el dispositivo a nombre del usuario; si ya existía, lo renueva sin duplicarlo.',
            'Cuando nace un aviso para una persona con algún dispositivo, el sistema lo deja con el push pendiente.',
            'Al terminar el lote de la sincronización (CU-17), el sistema despacha al instante los push de los avisos '
            'que nacieron en ese lote.',
            'En cada vuelta, la tarea automática despacha los push pendientes de los demás casos de uso.',
            'El sistema envía cada aviso a todos los dispositivos de la persona: por FCM a la aplicación y por Web Push '
            'a la PWA.',
            'El sistema marca el push como enviado, con su fecha, si llegó al menos a un dispositivo.',
            'El usuario toca la notificación y la aplicación lo lleva a la pantalla del aviso.',
        ],
        'alternativos': [
            '1a. Apagar los avisos: el usuario pulsa «Apagar los avisos en este dispositivo» o cierra sesión, y el '
            'sistema da de baja ese dispositivo.',
            '1b. Permiso denegado: si el navegador bloqueó los avisos, la campanita muestra «El navegador bloqueó los '
            'avisos» y no ofrece activarlos.',
            '3a. Dispositivo de otra cuenta: si el dispositivo está a nombre de otra persona de la tienda y la petición '
            'no trae sus mismas claves, el sistema responde «Este dispositivo recibe los avisos de otra cuenta».',
            '7a. Dispositivo que ya no existe: si FCM o el navegador responden que la suscripción venció, el sistema '
            'borra el dispositivo y el push queda fallido con el motivo; el aviso sigue en la campanita.',
            '7b. Sin dispositivos: si la persona ya no tiene ningún dispositivo, el push queda omitido.',
        ],
        'postcondiciones': 'El aviso llegó al dispositivo o quedó registrado por qué no. Un push que falla no '
                           'deshace la operación ni borra el aviso de la campanita.',
        'rastreo': 'RF-65, RF-23 · RN-06',
    },
    'CU-43': {
        'descripcion': 'Devuelve por el mismo medio el pago de una operación sin conexión que el servidor rechazó al '
                       'sincronizar: el QR se reintegra solo y el efectivo queda registrado para entregarse en la '
                       'sucursal.',
        'actores': 'Sistema',
        'iniciador': 'Sistema',
        'precondiciones': 'Una venta o una reserva hecha sin conexión se cobró (CU-16) y llega al servidor en la '
                          'sincronización (CU-17).',
        'flujo': [
            'El dispositivo envía el lote de operaciones pendientes al recuperar la conexión.',
            'El sistema intenta confirmar la operación, no alcanza la existencia y la deja rechazada con su motivo.',
            'El sistema limita lo que hay que devolver al total de la operación: lo que el cliente dio de más ya se le '
            'entregó como vuelto.',
            'Como se cobró con QR, el sistema reintegra el monto (simulado) y genera la referencia «REINT-QR-…».',
            'El sistema marca la operación como devuelta automáticamente, con la fecha, el medio «QR», la referencia y '
            'una observación, sin un responsable humano.',
            'El sistema deja al cliente el aviso «Le devolvimos Bs … por QR» con la referencia, y al cajero el resumen '
            'del lote.',
            'El sistema confirma la operación y despacha los avisos por push (CU-42).',
            'El dispositivo muestra la operación rechazada y reintegrada por QR, con su referencia, en la pantalla '
            '«Sin conexión».',
        ],
        'alternativos': [
            '2a. Sin cobro: si la operación no se había cobrado, no hay nada que devolver y solo se avisa el rechazo.',
            '4a. Cobrada en efectivo: el sistema no puede sacar billetes del cajón. La operación queda por devolver en '
            'la lista de la sucursal (CU-19); a los encargados les llega «Hay Bs … en efectivo para devolver» y al '
            'cliente, «Su dinero lo espera en …». El arqueo cuenta ese efectivo hasta que se entregue.',
            '6a. Venta anónima: si la venta no tenía cliente, nadie recibe el aviso de la devolución; el cajero la ve '
            'en el resumen del lote.',
            '8a. Ya devuelta: si el encargado intenta registrarla a mano en CU-19, el sistema responde «El sistema ya '
            'la reintegró por QR».',
        ],
        'postcondiciones': 'El pago de la operación rechazada se devolvió una sola vez, por el mismo medio, y quedó '
                           'registrado cuándo y cómo. El cliente fue avisado.',
        'rastreo': 'RF-66, RF-55 · RN-06, RN-21',
    },
    'CU-44': {
        'descripcion': 'Permite al cliente pedir que le avisen cuando vuelva a haber unidades de una talla y un color '
                       'agotados, y a la empresa ver cuántos clientes esperan cada talla.',
        'actores': 'Cliente, encargado de sucursal, administrador de la empresa, Sistema',
        'iniciador': 'Cliente',
        'precondiciones': 'El cliente inició sesión. La talla y el color están activos, su producto también, y no '
                          'tienen unidades disponibles en ninguna sucursal activa.',
        'flujo': [
            'El cliente abre la ficha de la prenda y elige la talla y el color.',
            'El sistema muestra que no hay unidades en ninguna sucursal y ofrece el botón «Avísenme cuando llegue».',
            'El cliente pulsa el botón.',
            'El sistema verifica que la variante se siga ofreciendo y que siga sin unidades, y registra el aviso '
            'pendiente.',
            'El sistema responde «Listo. Le avisaremos por la campanita, el correo y el teléfono cuando llegue».',
            'Cuando entra mercadería a esa variante y el total de las sucursales activas pasa de 0 a más de 0, el '
            'sistema crea el aviso «Volvió su talla» y marca el pedido como avisado, en la misma transacción del '
            'movimiento de inventario.',
            'La tarea automática envía el aviso por correo y por push (CU-42); en la campanita se ve al instante.',
            'El cliente entra desde el aviso a la ficha y compra o reserva.',
        ],
        'alternativos': [
            '4a. Ya lo había pedido: el sistema devuelve el aviso pendiente que ya existía; no lo duplica.',
            '4b. Llegaron unidades: si mientras miraba entró mercadería, el sistema responde «Esa talla ya tiene '
            'unidades: puede comprarla o reservarla ahora» y la ficha vuelve a consultar la disponibilidad.',
            '6a. No es noticia: si la mercadería entra a una sucursal inactiva o ya había unidades en otra sucursal, '
            'el sistema no avisa.',
            '8a. Cancelar: en «Mis avisos», el cliente cancela un aviso pendiente y el sistema lo borra.',
            '8b. Tallas esperadas: el encargado o el administrador abren «Tallas esperadas» y el sistema lista cada '
            'talla y color con los clientes que esperan y desde cuándo, lo más pedido primero.',
        ],
        'postcondiciones': 'El pedido queda pendiente hasta que vuelve la talla; entonces se avisa una sola vez. La '
                           'empresa conoce la demanda que espera.',
        'rastreo': 'RF-67 · RN-24',
    },
    'CU-45': {
        'descripcion': 'Marca con aprendizaje no supervisado (Isolation Forest) los turnos de caja y las devoluciones '
                       'que se apartan de lo habitual, y explica el motivo de cada caso.',
        'actores': 'Administrador de la empresa',
        'iniciador': 'Administrador de la empresa',
        'precondiciones': 'El administrador inició sesión. El plan de la empresa incluye la analítica con aprendizaje '
                          'automático. Hay al menos 20 turnos de caja cerrados en el último año.',
        'flujo': [
            'El administrador abre «Analítica inteligente» y pulsa «Buscar anomalías».',
            'El sistema verifica el rol y que el plan incluya la función (incluye CU-05).',
            'El sistema junta los turnos cerrados del último año con la diferencia de arqueo, las devoluciones y su '
            'monto, el descuento, la parte cobrada en efectivo, las ventas y la duración.',
            'El sistema entrena un Isolation Forest de 200 árboles y marca alrededor del 5 % más aislado.',
            'Como hay al menos 15 devoluciones, hace lo mismo con su valor, las horas desde la venta, la tasa de '
            'devoluciones de quien la atendió, si la prenda venía de un cambio, si es un cambio y la hora.',
            'Para cada caso marcado, el sistema nombra las variables que más se apartan de la mediana, por ejemplo '
            '«diferencia de arqueo 8× la habitual».',
            'El sistema guarda el análisis, conserva las revisiones anteriores y deja solo los últimos cinco análisis.',
            'El sistema muestra las pestañas «Turnos de caja» y «Devoluciones» con el puntaje, la fecha, el cajero, la '
            'sucursal, el detalle y el motivo.',
            'El administrador pulsa «Marcar revisada» en cada caso y el sistema registra quién y cuándo.',
        ],
        'alternativos': [
            '2a. Plan sin la función: el sistema responde «plan_limit» y la pantalla muestra el candado con «Ver mi '
            'plan».',
            '3a. Pocos turnos: con menos de 20 turnos cerrados, el sistema responde «Hacen falta al menos 20 turnos de '
            'caja cerrados para buscar anomalías» y no guarda nada.',
            '5a. Pocas devoluciones: el sistema analiza solo los turnos y la pestaña «Devoluciones» dice cuántas '
            'faltan.',
            '9a. Volver a buscar: el administrador pulsa «Volver a buscar» y el sistema entrena de nuevo con los datos '
            'de hoy, sin perder las revisiones de los mismos casos.',
        ],
        'postcondiciones': 'Queda guardado un análisis de tipo «ANOMALIAS» con los casos marcados, su puntaje, su '
                           'explicación y su revisión. Una anomalía es una alerta para revisar, no una prueba de fraude.',
        'rastreo': 'RF-68, RF-09',
    },
}


# ------------------------------------------------------------- validación ---
ACTORES_VALIDOS = {'Administrador de la plataforma', 'Administrador de la empresa', 'Encargado de sucursal', 'Cajero',
                   'Cliente', 'Proveedor', 'Sistema', 'Usuario', 'Empresa interesada'}
NOMBRES_2_5 = {'CU-42': 'Enviar avisos push de las operaciones sin conexión',
               'CU-43': 'Devolver automáticamente el pago de una operación rechazada',
               'CU-44': 'Pedir aviso de talla disponible',
               'CU-45': 'Detectar anomalías en caja y devoluciones'}


def validar():
    ids = {c[0] for c in CASOS}
    for c in CASOS:
        assert c[1] == NOMBRES_2_5[c[0]], c[0]
        assert set(c[2]) <= ACTORES_VALIDOS, c
        for ref in list(c[3]) + (list(c[5]) if len(c) > 5 else []):
            assert ref.startswith('CU-') and len(ref) == 5, (c[0], ref)
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
            ops = {(de, a, op.split('(')[0]) for _, de, a, op in r['m']}
            assert any(a == 'BitacoraMiddleware' and o == 'registrar' for de, a, o in ops), r['cu']
            assert ('BitacoraMiddleware', 'AsientoBitacora', 'agregar') in ops, r['cu']
    nombres = {p for r in ROBUSTEZ for p in r['f'] + r['c'] + r['e']}
    for k in DESCRIPCION:
        assert k in nombres, ('DESCRIPCION sin uso', k)


def validar_cus():
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
    for k, v in CLASES.items():
        assert v["tipo"] in ("interfaz", "control", "entidad"), k


def validar_espec():
    claves = {'descripcion', 'actores', 'iniciador', 'precondiciones', 'flujo', 'alternativos', 'postcondiciones',
              'rastreo'}
    for c in CASOS:
        e = ESPEC[c[0]]
        assert set(e) == claves, (c[0], claves ^ set(e))
        assert 5 <= len(e['flujo']) <= 10, (c[0], len(e['flujo']))
        assert 2 <= len(e['alternativos']) <= 5, (c[0], len(e['alternativos']))
        for alt in e['alternativos']:
            assert alt[0].isdigit() and '. ' in alt and ':' in alt, (c[0], alt)


if __name__ == '__main__':
    validar()
    validar_cus()
    validar_espec()
    print('ok:', len(CASOS), 'casos de uso,', len(ROBUSTEZ), 'robusteces,', len(CLASES), 'clases,',
          len(CUS), 'diseños de clases')
    for cu, d in CUS.items():
        print(' ', cu, len(d['clases']), 'clases,', len(d['relaciones']), 'relaciones')
