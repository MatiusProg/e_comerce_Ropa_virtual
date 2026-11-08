# Datos de la 3ra presentación, grupo b: CU-26 a CU-30 (correo, reportes con IA, reportes de gestión con
# devoluciones y la analítica con ML). Sacados del código de origin/main al 08/11.
#   - CASOS       -> 2.5 (mismo formato que CASOS de p2_datos.py)
#   - ROBUSTEZ    -> 3.2 (mismo formato que ROBUSTEZ de p2_datos.py)
#   - DESCRIPCION -> notas de los nombres nuevos de la robustez
#   - CLASES, CUS -> 3.4 diseño de clases (mismo formato que clases/cus de p2_clases_datos.py)
#   - ESPEC       -> ficha del 2.6
# Uso: python -X utf8 scripts/p3_datos_b.py   (solo valida; no escribe nada)

B = "backend/app/modules/"
W = "frontend-web/src/app/"
OMIT_AUD = "Omitidas las heredadas de Auditoria: creado_en TIMESTAMPTZ, actualizado_en TIMESTAMPTZ."

# ------------------------------------------------------------------ 2.5 ---
CASOS = [
    ('CU-26', 'Notificar eventos por correo según el plan', ['Sistema'], ['CU-05'],
     'Reemplaza al CU-40 del primer parcial. El aviso nace con el hecho y la tarea automática lo manda por Brevo '
     'cada 15 minutos, solo si el plan incluye la función «correo». RF-49.'),
    ('CU-27', 'Generar reporte con IA por texto o voz', ['Administrador de la empresa', 'Encargado de sucursal'],
     ['CU-05'],
     'Reemplaza al CU-35 del primer parcial. Gemini traduce el pedido a una especificación que el backend valida '
     'contra una lista blanca y ejecuta dentro del tenant; gasta el cupo reportes_ia. RF-25 a RF-30, RN-10, RN-11.'),
    ('CU-28', 'Generar reportes de gestión con devoluciones', ['Administrador de la empresa', 'Encargado de sucursal'],
     [],
     'Reemplaza al CU-37 del primer parcial. Los reportes fijos en PDF y Excel, con el de devoluciones y cambios '
     'por prenda y su valor al precio de la venta. RF-28, RF-38.'),
    ('CU-29', 'Entrenar los modelos de analítica', ['Administrador de la empresa'], ['CU-05'],
     'GradientBoosting para la demanda semanal y KMeans sobre RFM para los segmentos, con datos reales completados '
     'con sintéticos; se guarda en modelo_analitica. Función analitica_ml. RF-31.'),
    ('CU-30', 'Consultar el dashboard analítico', ['Administrador de la empresa'], ['CU-05'],
     'Métricas, demanda prevista, segmentos y los clientes de hoy clasificados con el modelo guardado; reporte '
     'inteligente en PDF y Excel. Función analitica_ml. RF-32, RF-33.'),
]

# ------------------------------------------------------------------ 3.2 ---
AE, EN, SI = 'A:Administrador de la empresa', 'A:Encargado de sucursal', 'A:Sistema'

ROBUSTEZ = [
    dict(cu='CU-26', n='Notificar eventos por correo según el plan', a=['Sistema'],
         # La tarea no pasa por HTTP: el middleware de la bitácora no la ve (ver la nota del 3.4).
         f=['TareaProgramada', 'CanalDeCorreo'],
         c=['GestorNotificaciones', 'GestorTareas', 'VerificadorPlan', 'GestorReservas'],
         e=['Notificacion', 'Usuario', 'Suscripcion', 'Plan', 'TareaAutomatica', 'Empresa'],
         grupos=['flujo principal: el aviso nace con el hecho y sale por correo',
                 'alternativo 3a: el plan no incluye el correo',
                 'alternativo 4a: el otro worker ya hizo la vuelta',
                 'alternativo 7a: Brevo rechaza o no responde'],
         m=[(1, 'GestorReservas', 'GestorNotificaciones', 'avisarReservaEnSucursal(reserva)'),
            (1, 'GestorNotificaciones', 'Usuario', 'encargadosDe(sucursal)'),
            (1, 'GestorNotificaciones', 'VerificadorPlan', 'incluye("correo")'),
            (1, 'VerificadorPlan', 'Suscripcion', 'vigenteDe(empresa)'),
            (1, 'VerificadorPlan', 'Plan', 'incluyeFuncion("correo")'),
            (1, 'GestorNotificaciones', 'Notificacion', 'crear(destinatario, tipo, titulo, cuerpo, "PENDIENTE")'),
            (1, SI, 'TareaProgramada', 'despertarCada15Minutos()'),
            (1, 'TareaProgramada', 'GestorTareas', 'correrVuelta()'),
            (1, 'GestorTareas', 'GestorTareas', 'tomarBloqueoAdvisory()'),
            (1, 'GestorTareas', 'TareaAutomatica', 'tocaVuelta(minimo)'),
            (1, 'GestorTareas', 'Empresa', 'empresasActivas()'),
            (1, 'GestorTareas', 'GestorNotificaciones', 'despacharPendientes(empresa)'),
            (1, 'GestorNotificaciones', 'Notificacion', 'tomarPendienteDeCorreo()'),
            (1, 'GestorNotificaciones', 'Usuario', 'obtener(destinatario)'),
            (1, 'GestorNotificaciones', 'GestorNotificaciones', 'armarMensaje(notificacion, enlace)'),
            (1, 'GestorNotificaciones', 'CanalDeCorreo', 'enviar(mensaje)'),
            (1, 'GestorNotificaciones', 'Notificacion', 'marcar("ENVIADO", enviadoEn)'),
            (2, 'VerificadorPlan', 'GestorNotificaciones', 'noIncluye()'),
            (2, 'GestorNotificaciones', 'Notificacion', 'crear(destinatario, tipo, titulo, cuerpo, "OMITIDO", motivo)'),
            (3, 'GestorTareas', 'TareaAutomatica', 'ultimaVuelta()'),
            (3, 'GestorTareas', 'GestorTareas', 'saltearVuelta()'),
            (4, 'CanalDeCorreo', 'GestorNotificaciones', 'errorDeEnvio(motivo)'),
            (4, 'GestorNotificaciones', 'Notificacion', 'marcar("FALLIDO", motivo)'),
            (4, 'GestorNotificaciones', 'GestorNotificaciones', 'seguirConLaSiguiente()')]),

    dict(cu='CU-27', n='Generar reporte con IA por texto o voz',
         a=['Administrador de la empresa', 'Encargado de sucursal'],
         f=['PantallaReportesIA', 'ProveedorIA'],
         c=['GestorReportesIA', 'GestorAutenticacion', 'VerificadorPlan', 'BitacoraMiddleware'],
         e=['Plan', 'ConsumoCupo', 'Sucursal', 'Venta', 'Devolucion', 'Existencia', 'Reserva', 'AsientoBitacora'],
         grupos=['flujo principal: el pedido se entiende y se arma el reporte',
                 'alternativo 3a: el plan no lo incluye o se agotó el cupo',
                 'alternativo 5a: sin IA, entra el intérprete por reglas',
                 'alternativo 6a: pedido ambiguo o no soportado',
                 'alternativo 8a: exportar a PDF o Excel'],
         m=[(1, AE, 'PantallaReportesIA', 'escribirODictar(pedido)'),
            (1, EN, 'PantallaReportesIA', 'escribirODictar(pedido)'),
            (1, 'PantallaReportesIA', 'GestorReportesIA', 'consultar(texto)'),
            (1, 'GestorReportesIA', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR", "ENCARGADO")'),
            (1, 'GestorReportesIA', 'VerificadorPlan', 'verificar("reportes_ia", cupo)'),
            (1, 'VerificadorPlan', 'Plan', 'incluyeFuncion("reportes_ia")'),
            (1, 'VerificadorPlan', 'ConsumoCupo', 'usoDelMes("reportes_ia")'),
            (1, 'GestorReportesIA', 'Sucursal', 'paresIdNombre(sucursalForzada)'),
            (1, 'GestorReportesIA', 'ProveedorIA', 'interpretarConsulta(texto, vocabulario, hoy)'),
            (1, 'ProveedorIA', 'GestorReportesIA', 'especificacion(json)'),
            (1, 'GestorReportesIA', 'GestorReportesIA', 'validar(especificacion)'),
            (1, 'GestorReportesIA', 'Venta', 'sumarPor(dimensiones, filtros, periodo)'),
            (1, 'GestorReportesIA', 'Devolucion', 'sumarPor(dimensiones, filtros, periodo)'),
            (1, 'GestorReportesIA', 'Existencia', 'sumarPor(dimensiones, filtros)'),
            (1, 'GestorReportesIA', 'Reserva', 'contarPor(dimensiones, filtros, periodo)'),
            (1, 'GestorReportesIA', 'GestorReportesIA', 'armarGraficoYLectura(filas)'),
            (1, 'GestorReportesIA', 'VerificadorPlan', 'consumirCupo("reportes_ia")'),
            (1, 'VerificadorPlan', 'ConsumoCupo', 'sumarUno(recurso, periodo)'),
            (1, 'GestorReportesIA', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, ip)'),
            (1, 'GestorReportesIA', 'PantallaReportesIA', 'mostrarReporte(entendido, tabla, grafico, lectura)'),
            (2, 'VerificadorPlan', 'GestorReportesIA', 'rechazarPorPlan("plan_limit", limite, uso)'),
            (2, 'GestorReportesIA', 'PantallaReportesIA', 'avisarPlan(mensaje)'),
            (3, 'ProveedorIA', 'GestorReportesIA', 'errorDelInterprete()'),
            (3, 'GestorReportesIA', 'GestorReportesIA', 'interpretarPorReglas(texto, vocabulario, hoy)'),
            (4, 'GestorReportesIA', 'PantallaReportesIA', 'noEntendido(motivo, ejemplos)'),
            (5, AE, 'PantallaReportesIA', 'exportar(formato)'),
            (5, 'PantallaReportesIA', 'GestorReportesIA', 'exportar(especificacion, formato)'),
            (5, 'GestorReportesIA', 'GestorReportesIA', 'validarYEjecutar(especificacion)'),
            (5, 'GestorReportesIA', 'PantallaReportesIA', 'entregarArchivo(pdfOXlsx)')]),

    dict(cu='CU-28', n='Generar reportes de gestión con devoluciones',
         a=['Administrador de la empresa', 'Encargado de sucursal'],
         f=['PantallaReportes', 'ProveedorIA'],
         c=['GestorReportes', 'GestorAutenticacion', 'VerificadorPlan', 'BitacoraMiddleware'],
         e=['Devolucion', 'DetalleDevolucion', 'DetalleVenta', 'Sucursal', 'AsientoBitacora'],
         grupos=['flujo principal: bajar el reporte de devoluciones y cambios',
                 'alternativo 3a: pedir el reporte hablando',
                 'alternativo 5a: el encargado solo ve su sucursal'],
         m=[(1, AE, 'PantallaReportes', 'abrirReportes()'),
            (1, EN, 'PantallaReportes', 'abrirReportes()'),
            (1, 'PantallaReportes', 'GestorReportes', 'catalogo()'),
            (1, 'GestorReportes', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR", "ENCARGADO")'),
            (1, 'GestorReportes', 'Sucursal', 'opcionesDeSucursal()'),
            (1, 'GestorReportes', 'PantallaReportes', 'mostrarCatalogo(reportes, filtros)'),
            (1, AE, 'PantallaReportes', 'descargar("devoluciones", formato, periodo, filtros)'),
            (1, EN, 'PantallaReportes', 'descargar("devoluciones", formato, periodo, filtros)'),
            (1, 'PantallaReportes', 'GestorReportes', 'descargar(tipo, formato, desde, hasta, filtros)'),
            (1, 'GestorReportes', 'Devolucion', 'devoluciones(desde, hasta, sucursal, tipo)'),
            (1, 'GestorReportes', 'DetalleDevolucion', 'lineasDevueltas(devolucion)'),
            (1, 'GestorReportes', 'DetalleVenta', 'precioCongelado(venta, variante)'),
            (1, 'GestorReportes', 'GestorReportes', 'totales(cantidad, valor)'),
            (1, 'GestorReportes', 'GestorReportes', 'aPdfOExcel(tabla)'),
            (1, 'GestorReportes', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar("EXPORTAR", usuario, ip)'),
            (1, 'GestorReportes', 'PantallaReportes', 'entregarArchivo(nombre)'),
            (2, AE, 'PantallaReportes', 'hablar()'),
            (2, 'PantallaReportes', 'GestorReportes', 'interpretarVoz(texto)'),
            (2, 'GestorReportes', 'VerificadorPlan', 'verificar("reportes_ia", cupo)'),
            (2, 'GestorReportes', 'ProveedorIA', 'interpretar(texto, reportes, hoy)'),
            (2, 'GestorReportes', 'PantallaReportes', 'mostrarLoEntendido(resumen, url)'),
            (3, 'GestorReportes', 'GestorReportes', 'forzarSucursal(usuario.sucursal)'),
            (3, 'GestorReportes', 'PantallaReportes', 'sinSucursalAsignada()')]),

    dict(cu='CU-29', n='Entrenar los modelos de analítica', a=['Administrador de la empresa'],
         f=['PantallaAnalitica'],
         c=['GestorAnalitica', 'GestorAutenticacion', 'VerificadorPlan', 'BitacoraMiddleware'],
         e=['Plan', 'Producto', 'Venta', 'ModeloAnalitica', 'AsientoBitacora'],
         grupos=['flujo principal: entrenar los dos modelos',
                 'alternativo 2a: el plan no incluye la analítica',
                 'alternativo 3a: la empresa casi no tiene ventas'],
         m=[(1, AE, 'PantallaAnalitica', 'entrenar()'),
            (1, 'PantallaAnalitica', 'GestorAnalitica', 'entrenar(semilla)'),
            (1, 'GestorAnalitica', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorAnalitica', 'VerificadorPlan', 'verificarFuncion("analitica_ml")'),
            (1, 'VerificadorPlan', 'Plan', 'incluyeFuncion("analitica_ml")'),
            (1, 'GestorAnalitica', 'Producto', 'productosActivos()'),
            (1, 'GestorAnalitica', 'Venta', 'ventasSemanales(desde)'),
            (1, 'GestorAnalitica', 'GestorAnalitica', 'demandaSintetica(productos, semanas, semilla)'),
            (1, 'GestorAnalitica', 'GestorAnalitica', 'entrenarDemanda(GradientBoosting, corteTemporal)'),
            (1, 'GestorAnalitica', 'Venta', 'rfmDeClientes()'),
            (1, 'GestorAnalitica', 'GestorAnalitica', 'entrenarSegmentos(KMeans, k 2 a 6, silueta)'),
            (1, 'GestorAnalitica', 'ModeloAnalitica', 'guardar(entrenamiento)'),
            (1, 'GestorAnalitica', 'ModeloAnalitica', 'borrarViejos(tipo, conservar 5)'),
            (1, 'GestorAnalitica', 'BitacoraMiddleware', 'registrar(peticion)'),
            (1, 'BitacoraMiddleware', 'AsientoBitacora', 'agregar(accion, usuario, ip)'),
            (1, 'GestorAnalitica', 'PantallaAnalitica', 'mostrarDashboard(resumen)'),
            (2, 'VerificadorPlan', 'GestorAnalitica', 'rechazarPorPlan("plan_limit")'),
            (2, 'GestorAnalitica', 'PantallaAnalitica', 'mostrarCandado(mensaje)'),
            (3, 'GestorAnalitica', 'GestorAnalitica', 'completarConSinteticos(filasReales)')]),

    dict(cu='CU-30', n='Consultar el dashboard analítico', a=['Administrador de la empresa'],
         f=['PantallaAnalitica'],
         c=['GestorAnalitica', 'GestorAutenticacion', 'VerificadorPlan'],
         e=['Plan', 'ModeloAnalitica', 'Venta'],
         grupos=['flujo principal: ver el dashboard',
                 'alternativo 2a: el plan no incluye la analítica',
                 'alternativo 3a: todavía no se entrenó',
                 'alternativo 7a: descargar el reporte inteligente'],
         m=[(1, AE, 'PantallaAnalitica', 'abrirAnalitica()'),
            (1, 'PantallaAnalitica', 'GestorAnalitica', 'resumen()'),
            (1, 'GestorAnalitica', 'GestorAutenticacion', 'autorizar("ADMINISTRADOR")'),
            (1, 'GestorAnalitica', 'VerificadorPlan', 'verificarFuncion("analitica_ml")'),
            (1, 'VerificadorPlan', 'Plan', 'incluyeFuncion("analitica_ml")'),
            (1, 'GestorAnalitica', 'ModeloAnalitica', 'ultimo("DEMANDA")'),
            (1, 'GestorAnalitica', 'ModeloAnalitica', 'ultimo("SEGMENTOS")'),
            (1, 'GestorAnalitica', 'PantallaAnalitica', 'mostrarMetricasPrediccionesYSegmentos(resumen)'),
            (1, 'PantallaAnalitica', 'GestorAnalitica', 'clientesPorSegmento()'),
            (1, 'GestorAnalitica', 'Venta', 'rfmDeClientes()'),
            (1, 'GestorAnalitica', 'GestorAnalitica', 'clasificar(modeloGuardado, rfm)'),
            (1, 'GestorAnalitica', 'PantallaAnalitica', 'mostrarClientes(segmentos)'),
            (2, 'VerificadorPlan', 'GestorAnalitica', 'rechazarPorPlan("plan_limit")'),
            (2, 'GestorAnalitica', 'PantallaAnalitica', 'mostrarCandado(mensaje)'),
            (3, 'GestorAnalitica', 'PantallaAnalitica', 'invitarAEntrenar()'),
            (4, AE, 'PantallaAnalitica', 'descargar(formato)'),
            (4, 'PantallaAnalitica', 'GestorAnalitica', 'reporte(formato)'),
            (4, 'GestorAnalitica', 'GestorAnalitica', 'aPdfOExcel(tabla)'),
            (4, 'GestorAnalitica', 'PantallaAnalitica', 'entregarArchivo(nombre)')]),
]

DESCRIPCION = {
    'GestorNotificaciones': 'Coordina CU-26: deja el aviso con el hecho y despacha los correos pendientes (notificaciones/service.py).',
    'GestorTareas': 'Control de las tareas automáticas (core/tareas.py): una vuelta cada 15 minutos por empresa activa, con advisory lock.',
    'GestorReservas': 'Crea la reserva; al hacerlo le pide a GestorNotificaciones el aviso al encargado (uno de los hechos que avisan).',
    'Notificacion': 'Aviso a una persona por un hecho: campanita, estado del correo (OMITIDO, PENDIENTE, ENVIADO, FALLIDO) y del push.',
    'TareaAutomatica': 'Marca de la plataforma con la hora de la última vuelta; evita que el otro worker la repita.',
    'PantallaReportesIA': 'Pantalla «Reportes con IA»: pedido escrito o dictado, ejemplos, tabla, gráfico y exportación.',
    'ProveedorIA': 'Frontera de salida: Gemini, que traduce la frase a una especificación en JSON. No escribe SQL.',
    'GestorReportesIA': 'Coordina CU-27: vocabulario, interpretación, validación contra la lista blanca y ejecución (reportes/dinamico*.py).',
    'PantallaReportes': 'Pantalla «Reportes de gestión»: catálogo de reportes fijos con filtros y descarga en PDF o Excel.',
    'GestorReportes': 'Coordina CU-28: genera el reporte fijo pedido y lo convierte a PDF o Excel (reportes/reportes_*.py).',
    'DetalleDevolucion': 'Prenda devuelta en una devolución o un cambio, con su cantidad.',
    'DetalleVenta': 'Línea de una venta con el precio y el descuento congelados.',
    'PantallaAnalitica': 'Pantalla «Analítica inteligente»: entrenar, métricas, demanda prevista, segmentos y reporte.',
    'GestorAnalitica': 'Coordina CU-29 y CU-30: arma los datos, entrena GradientBoosting y KMeans y arma el dashboard (analitica/service.py).',
    'ModeloAnalitica': 'Un entrenamiento guardado: tipo, parámetros, métricas, resultado, filas reales y sintéticas y el modelo serializado.',
    'Producto': 'Prenda del catálogo con su categoría, temporada y precio base.',
}

# ------------------------------------------------------------------ 3.4 ---
CLASES = {
    # ---------------- INTERFACES ----------------
    "ConsultaIa": {"tipo": "interfaz", "origen": W + "features/reportes/consulta-ia/consulta-ia.ts",
        "nota": "Ruta /admin/reportes-ia y la del encargado. El micrófono usa DictadoService (Web Speech API): al servidor llega texto, no audio.",
        "atributos": [], "operaciones": ["usarEjemplo(frase: string): void", "hablar(): void", "consultar(): void",
            "exportar(formato: 'pdf' | 'xlsx'): void", "formatear(valor: string | number, columna: number): string"]},
    "Exportar": {"tipo": "interfaz", "origen": W + "features/reportes/exportar/exportar.ts",
        "nota": "Ruta /admin/reportes. interpretar(frase) es privado: lo llama hablar() al terminar el dictado.",
        "atributos": [], "operaciones": ["ngOnInit(): void", "hablar(): void", "descargarLoEntendido(): void",
            "valorDe(tipo: string, campo: string): string", "elegir(tipo: string, campo: string, valor: string): void",
            "limpiar(tipo: string): void", "cuantosFiltros(tipo: string): number",
            "descargar(reporte: ReporteDisponible, formato: 'pdf' | 'xlsx'): void", "estaBajando(tipo: string, formato: string): boolean"]},
    "Analitica": {"tipo": "interfaz", "origen": W + "features/reportes/analitica/analitica.ts",
        "nota": "Ruta /admin/analitica. cargarClientes() es privado: lo llaman cargar() y entrenar(). Debajo va <app-anomalias-panel> (aporte propio, no es de estos CU).",
        "atributos": [], "operaciones": ["ngOnInit(): void", "cargar(): void", "entrenar(): void", "descargar(formato: 'pdf' | 'xlsx'): void",
            "tendencia(t: string): {icono, texto}", "fechaCorta(iso: string): string", "fechaLarga(iso: string): string"]},
    "ProveedorBrevo": {"tipo": "interfaz", "origen": "backend/app/integrations/correo/brevo.py",
        "nota": "Frontera de salida CanalDeCorreo. Se elige con CORREO_PROVEEDOR=brevo (por omisión 'consola'); POST https://api.brevo.com/v3/smtp/email. Lo llama integrations/correo/__init__.py enviar(mensaje).",
        "atributos": ["nombre: str = 'brevo'"], "operaciones": ["enviar(mensaje: Mensaje): None"]},
    "InterpreteGemini": {"tipo": "interfaz", "origen": "backend/app/integrations/interprete/gemini.py",
        "nota": "Frontera de salida ProveedorIA. Lo elige integrations/interprete/__init__.py obtener_proveedor() con IA_PROVEEDOR=gemini; sin clave queda InterpreteNoDisponible, que levanta ErrorDelInterprete.",
        "atributos": ["nombre: str = 'gemini'", "disponible: bool"],
        "operaciones": ["interpretar(texto, reportes: list[ReporteConocido], hoy: date): Pedido | None",
            "interpretar_consulta(texto: str, vocabulario: dict, hoy: date): dict | None", "_pedir_json(modelo: str, instruccion: str): dict | None"]},

    # ---------------- CONTROLES (web) ----------------
    "ReportesService": {"tipo": "control", "origen": W + "core/services/reportes.service.ts",
        "atributos": [],
        "operaciones": ["catalogo(): Observable<ReporteDisponible[]>", "descargar(tipo, formato, filtros): Observable<{archivo, nombre}>",
            "hayVoz(): Observable<boolean>", "interpretarVoz(texto: string): Observable<PedidoEntendido>",
            "consultarIa(texto: string): Observable<ResultadoReporteIa>",
            "exportarIa(especificacion, formato): Observable<{archivo, nombre}>",
            "traducirIa(error): ErrorReportes", "nombreDe(disposicion, tipo, formato): string", "traducir(error): ErrorReportes"]},
    "DictadoService": {"tipo": "control", "origen": W + "core/services/dictado.service.ts",
        "atributos": ["soportado: Signal<boolean>", "escuchando: Signal<boolean>", "texto: Signal<string>", "error: Signal<string | null>"],
        "operaciones": ["escuchar(alTerminar: (frase: string) => void): void", "detener(): void"]},
    "AnaliticaService": {"tipo": "control", "origen": W + "core/services/analitica.service.ts",
        "nota": "anomalias(), buscarAnomalias() y marcarRevisada() son del aporte propio (CU-45), fuera de estos CU.",
        "atributos": [],
        "operaciones": ["resumen(): Observable<ResumenAnalitica>", "entrenar(semilla?: number): Observable<ResumenAnalitica>",
            "clientes(): Observable<ClienteSegmento[]>", "reporte(formato: 'pdf' | 'xlsx'): Observable<Blob>", "traducir(error): ErrorAnalitica"]},

    # ---------------- CONTROLES (backend) ----------------
    "tareas": {"tipo": "control", "origen": "backend/app/core/tareas.py",
        "nota": "Modulo de funciones; la frontera TareaProgramada es _bucle(), una tarea asyncio que arranca ciclo_de_vida (lifespan de FastAPI) si TAREAS_AUTOMATICAS=on, cada TAREAS_INTERVALO_MINUTOS (15). Advisory lock pg_try_advisory_lock para los 2 workers de gunicorn. _correos llama a notificaciones/service.py despachar_pendientes. No pasa por HTTP: el middleware de la bitacora no la anota.",
        "atributos": ["CLAVE_DEL_BLOQUEO = 0x56494F4C4554", "ESPERA_INICIAL_SEGUNDOS = 60", "TAREAS_POR_EMPRESA: tuple"],
        "operaciones": ["ciclo_de_vida(_app)", "encendidas(): bool", "_bucle(): None", "correr_vuelta(fabrica_de_sesiones, minimo_entre_vueltas): Vuelta",
            "_toca_vuelta(conexion, minimo): bool", "_empresas_activas(db): list[int]", "_intentar(vuelta, db, nombre, tarea): None",
            "_correos(db, empresa_id): None", "_push(db, empresa_id): None"]},
    "notificaciones_service": {"tipo": "control", "origen": B + "notificaciones/service.py",
        "nota": "Modulo de funciones. Los avisar_* los llaman otros paquetes (reservas, pagos, inventario, traspasos, devoluciones web, offline) dentro de su transaccion. Endpoint manual: POST /mantenimiento/notificaciones/despacho y /reintento (ADMINISTRADOR).",
        "atributos": ["TOPE_POR_DESPACHO = 50"],
        "operaciones": ["notificar(db, *, destinatario, tipo, titulo, cuerpo, enlace, entidad, entidad_id): Notificacion",
            "avisar_reserva_en_sucursal(db, reserva): list[Notificacion]", "avisar_pedido_pagado(db, venta): Notificacion | None",
            "avisar_stock_bajo(db, existencia, *, etiqueta): list[Notificacion]", "avisar_devolucion_solicitada(db, solicitud): list[Notificacion]",
            "avisar_devolucion_resuelta(db, solicitud): Notificacion | None", "_encargados_de(db, sucursal_id): list[Usuario]",
            "_cuerpo_html(notificacion, url): str", "_mensaje_de(db, notificacion): Mensaje | None",
            "despachar_pendientes(db, *, limite): DespachoOut", "reintentar_fallidas(db, *, limite): int"]},
    "verificador": {"tipo": "control", "origen": B + "plataforma/verificador.py",
        "nota": "VerificadorPlan (CU-05). Los routers no lo llaman a mano: declaran requiere_funcion / requiere_cupo de core/dependencies.py, que responden 403 plan_limit.",
        "atributos": ["FUNCIONES: dict[str, str]", "CUPOS: dict[str, tuple]"],
        "operaciones": ["suscripcion_vigente(db): Suscripcion | None", "plan_vigente(db): Plan", "incluye(db, funcion): bool",
            "verificar_funcion(db, funcion): None", "uso_del_mes(db, cupo): int", "verificar_cupo(db, cupo): None", "consumir_cupo(db, cupo): int"]},
    "dinamico_router": {"tipo": "control", "origen": B + "reportes/dinamico_router.py",
        "nota": "Rutas POST /reportes/ia/consulta y POST /reportes/ia/exportar.{pdf|xlsx}. Dependencias del router: requiere_roles(ADMINISTRADOR, ENCARGADO), requiere_funcion('reportes_ia'); la consulta ademas requiere_cupo('reportes_ia').",
        "atributos": ["EJEMPLOS: list[str]"],
        "operaciones": ["consultar(datos: ConsultaIn, db, usuario): ResultadoOut", "exportar(formato, datos: EspecificacionIn, db, usuario): Response",
            "_sucursal_forzada(usuario): int | None", "_no_entendido(motivo, interprete): ResultadoOut"]},
    "dinamico": {"tipo": "control", "origen": B + "reportes/dinamico.py",
        "nota": "8 medidas (ventas_monto, unidades_vendidas, cantidad_ventas, ticket_promedio, devoluciones_monto, unidades_devueltas, existencias, reservas) y 13 dimensiones. La consulta la arma SIEMPRE este codigo con SQLAlchemy; el RLS aisla la empresa.",
        "atributos": ["MEDIDAS: dict[str, Medida]", "DIMENSIONES: dict[str, Dimension]", "LIMITE_MAXIMO = 200"],
        "operaciones": ["vocabulario(db, *, sucursal_forzada): dict", "validar(db, crudo: dict): Especificacion",
            "ejecutar(db, espec, *, sucursal_forzada): Resultado", "_describir_filtros(db, espec, forzada): list[str]",
            "_grafico(espec, filas, medida): dict", "_narrar(espec, filas, medida): str"]},
    "interprete_reglas": {"tipo": "control", "origen": B + "reportes/interprete_reglas.py",
        "nota": "El respaldo sin IA: lo usa consultar() cuando el proveedor levanta ErrorDelInterprete; la pantalla muestra «sin IA».",
        "atributos": [], "operaciones": ["interpretar(texto: str, vocabulario: dict, hoy: date): dict | None", "_periodo(t, hoy): tuple[date | None, date | None]"]},
    "reportes_router": {"tipo": "control", "origen": B + "reportes/reportes_router.py",
        "nota": "Rutas GET /reportes/catalogo, GET /reportes/{tipo}.{formato}, GET /reportes/voz/disponible y POST /reportes/voz (este con requiere_funcion y requiere_cupo 'reportes_ia'). requiere_roles(ADMINISTRADOR, ENCARGADO).",
        "atributos": [],
        "operaciones": ["catalogo_de_reportes(db, usuario): list[dict]", "descargar(tipo, formato, db, usuario, desde, hasta, sucursal_id, ...): Response",
            "hay_pedido_por_voz(db): dict", "pedir_por_voz(datos: PedidoPorVozIn, db, usuario): PedidoEntendidoOut"]},
    "reportes_service": {"tipo": "control", "origen": B + "reportes/reportes_service.py",
        "atributos": ["REPORTES: dict[str, Definicion]"],
        "operaciones": ["generar(db, *, tipo, desde, hasta, sucursal_id, extras): Tabla", "opciones_de(db, filtro): list[dict]",
            "_rango(desde, hasta): tuple[datetime, datetime]", "_totales(definicion, filas): list | None",
            "catalogo_para_el_interprete(db, es_admin): list"]},
    "exportador": {"tipo": "control", "origen": B + "reportes/exportador.py",
        "atributos": ["FORMATOS: dict"], "operaciones": ["a_pdf(tabla: Tabla): bytes", "a_excel(tabla: Tabla): bytes"]},
    "analitica_router": {"tipo": "control", "origen": B + "analitica/router.py",
        "nota": "Dependencias: requiere_roles('ADMINISTRADOR') y requiere_funcion('analitica_ml'). Las rutas /anomalias son del aporte propio.",
        "atributos": [],
        "operaciones": ["entrenar(db, usuario, datos: EntrenarIn | None): ResumenOut", "historial(db): list[HistorialOut]",
            "resumen(db): ResumenOut", "clientes(db): list[ClienteSegmentoOut]", "reporte_pdf(db): Response", "reporte_excel(db): Response"]},
    "analitica_service": {"tipo": "control", "origen": B + "analitica/service.py",
        "atributos": [],
        "operaciones": ["entrenar(db, usuario_id, semilla): dict", "_productos(db): list[ProductoBase]",
            "_matriz_real(db, productos, lunes): ndarray", "_rfm_real(db): tuple[list, ndarray]",
            "_guardar(db, tipo, e: Entrenado, inicio, usuario_id): ModeloAnalitica", "resumen(db): dict", "historial(db): list[dict]",
            "clientes_por_segmento(db): list[dict]", "reporte(db): Tabla"]},
    "modelos": {"tipo": "control", "origen": B + "analitica/modelos.py",
        "nota": "Funciones puras con scikit-learn: no tocan la base. GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.9), validacion con corte temporal de 12 semanas; KMeans con k de 2 a 6 elegido por silueta.",
        "atributos": ["SEMANAS_DE_PRUEBA = 12", "PARAMETROS_GB: dict", "K_CANDIDATOS = range(2, 7)"],
        "operaciones": ["entrenar_demanda(productos, sinteticas, reales, lunes, semilla): Entrenado",
            "entrenar_segmentos(sinteticos, reales, semilla): Entrenado", "clasificar(modelo: bytes, rfm): list[str]",
            "_preprocesar(rfm): ndarray", "_nombrar(centros): dict[int, str]"]},
    "sinteticos": {"tipo": "control", "origen": B + "analitica/sinteticos.py",
        "atributos": ["SEMILLA = 2026", "SEMANAS = 104", "CLIENTES_SINTETICOS = 240"],
        "operaciones": ["productos_de_relleno(cantidad): list[ProductoBase]", "demanda_semanal(productos, semana_iso, semilla): ndarray",
            "clientes_rfm(cantidad, semilla): ndarray"]},
    "BitacoraMiddleware": {"tipo": "control", "origen": B + "bitacora/middleware.py",
        "nota": "Anota toda peticion POST/PUT/PATCH/DELETE (y las exportaciones GET /reportes/{tipo}.pdf|xlsx). _anotar llama a bitacora/service.py registrar(db, accion, metodo, ruta, estado_http, exito, usuario_id, actor, rol, entidad, entidad_id, ip, agente, detalle), que inserta con bitacora/repository.py agregar(db, **campos). Los GET no se anotan.",
        "atributos": [], "operaciones": ["dispatch(peticion: Request, siguiente): Response", "_anotar(peticion: Request, respuesta): None"]},

    # ---------------- ENTIDADES ----------------
    "Notificacion": {"tipo": "entidad", "origen": B + "notificaciones/models.py", "tabla": "notificacion",
        "nota": "tipo IN (RESERVA_EN_SUCURSAL, RESERVA_PREPARADA, PEDIDO_PAGADO, STOCK_BAJO, TRASPASO, DEVOLUCION, OPERACION_OFFLINE, DEVOLUCION_PAGO, STOCK_DISPONIBLE); correo_estado IN (OMITIDO, PENDIENTE, ENVIADO, FALLIDO).",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "destinatario_id: BIGINT (FK usuario, ON DELETE CASCADE)",
            "tipo: VARCHAR(40)", "titulo: VARCHAR(160)", "cuerpo: TEXT", "enlace: VARCHAR(300)", "entidad: VARCHAR(60)", "entidad_id: BIGINT",
            "creada_en: TIMESTAMPTZ", "leida_en: TIMESTAMPTZ", "correo_estado: VARCHAR(20)", "correo_enviado_en: TIMESTAMPTZ",
            "correo_error: VARCHAR(300)", "push_estado: VARCHAR(20)", "push_enviado_en: TIMESTAMPTZ", "push_error: VARCHAR(300)"],
        "operaciones": ["crear(db, *, destinatario_id, tipo, titulo, cuerpo, enlace, entidad, entidad_id, correo_estado, correo_error, push_estado): Notificacion  [notificaciones/repository.py]",
            "tomar_pendiente_de_correo(db): Notificacion | None  [notificaciones/repository.py]",
            "listar_de(db, destinatario_id, ...): list[Notificacion]  [notificaciones/repository.py]",
            "contar_de(db, destinatario_id, *, solo_no_leidas): int  [notificaciones/repository.py]",
            "marcar_leidas(db, destinatario_id, notificacion_id): int  [notificaciones/repository.py]"]},
    "TareaAutomatica": {"tipo": "entidad", "origen": B + "plataforma/models.py", "tabla": "tarea_automatica",
        "nota": "De la plataforma: sin empresa ni RLS (migracion 0035). Una sola fila, clave 'vuelta'.",
        "atributos": ["clave: VARCHAR(40) (PK)", "ultima_vuelta: TIMESTAMPTZ"],
        "operaciones": ["_toca_vuelta(conexion, minimo): bool  [core/tareas.py, SQL directo: SELECT y INSERT ... ON CONFLICT]"]},
    "Empresa": {"tipo": "entidad", "origen": B + "plataforma/models.py", "tabla": "empresa", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "nombre: VARCHAR(120)", "razon_social: VARCHAR(160)", "nit: VARCHAR(30)", "slug: VARCHAR(40) (UNIQUE)",
            "correo_contacto: VARCHAR(120)", "estado: VARCHAR(10)", "logo: VARCHAR(255)", "color_principal: VARCHAR(7)",
            "color_secundario: VARCHAR(7)", "ventana_devolucion_horas: SMALLINT"],
        "operaciones": ["_empresas_activas(db): list[int]  [core/tareas.py, estado != BAJA]"]},
    "Plan": {"tipo": "entidad", "origen": B + "plataforma/models.py", "tabla": "plan", "nota": OMIT_AUD,
        "atributos": ["id: SMALLINT (PK)", "codigo: VARCHAR(20) (UNIQUE)", "nombre: VARCHAR(40) (UNIQUE)", "precio_mensual: NUMERIC(10,2)",
            "duracion_dias: SMALLINT", "max_sucursales: INTEGER", "max_empleados: INTEGER", "cupo_reportes_ia: INTEGER",
            "cupo_fotos_ia: INTEGER", "funciones: JSONB", "activo: BOOLEAN"],
        "operaciones": ["plan_vigente(db): Plan  [plataforma/verificador.py]", "incluye(db, funcion): bool  [plataforma/verificador.py]"]},
    "Suscripcion": {"tipo": "entidad", "origen": B + "plataforma/models.py", "tabla": "suscripcion", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "plan_id: SMALLINT (FK plan)", "inicio: DATE", "vencimiento: DATE",
            "estado: VARCHAR(12)"],
        "operaciones": ["suscripcion_vigente(db): Suscripcion | None  [plataforma/verificador.py]"]},
    "ConsumoCupo": {"tipo": "entidad", "origen": B + "plataforma/models.py", "tabla": "consumo_cupo",
        "nota": "PK compuesta (empresa_id, recurso, periodo). periodo = primer dia del mes en hora de Bolivia.",
        "atributos": ["empresa_id: BIGINT (PK, FK empresa)", "recurso: VARCHAR(20) (PK)", "periodo: DATE (PK)", "usados: INTEGER"],
        "operaciones": ["uso_del_mes(db, cupo): int  [plataforma/verificador.py]",
            "consumir_cupo(db, cupo): int  [plataforma/verificador.py, INSERT ... ON CONFLICT DO UPDATE]"]},
    "Usuario": {"tipo": "entidad", "origen": B + "seguridad/models.py", "tabla": "usuario", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "correo: VARCHAR(120)", "hash_contrasena: VARCHAR(255)", "nombres: VARCHAR(80)", "apellidos: VARCHAR(80)",
            "rol_id: SMALLINT (FK rol)", "activo: BOOLEAN", "empresa_id: BIGINT (FK empresa)"],
        "operaciones": ["_encargados_de(db, sucursal_id): list[Usuario]  [notificaciones/service.py]",
            "db.get(Usuario, destinatario_id)  [notificaciones/service.py _mensaje_de]"]},
    "Sucursal": {"tipo": "entidad", "origen": B + "organizacion/models.py", "tabla": "sucursal", "nota": OMIT_AUD,
        "atributos": ["id: INTEGER (PK)", "empresa_id: BIGINT (FK empresa)", "ciudad_id: INTEGER (FK ciudad)", "nombre: VARCHAR(80)", "direccion: VARCHAR(200)",
            "telefono: VARCHAR(20)", "horario_apertura: TIME", "horario_cierre: TIME", "capacidad_vestidores: SMALLINT", "activa: BOOLEAN"],
        "operaciones": ["opciones_de_sucursal(db): list[tuple[str, str]]  [reportes/reportes_repository.py]",
            "nombre_de_sucursal(db, sucursal_id): str | None  [reportes/reportes_repository.py]",
            "vocabulario(db, *, sucursal_forzada): dict  [reportes/dinamico.py, pares id -> nombre]"]},
    "Venta": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "venta",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(20) (UNIQUE)", "canal: VARCHAR(12)", "estado: VARCHAR(20)",
            "cliente_id: BIGINT (FK cliente)", "sucursal_id: INTEGER (FK sucursal)", "turno_caja_id: BIGINT (FK turno_caja)", "reserva_id: BIGINT (FK reserva, UNIQUE)",
            "modalidad_entrega: VARCHAR(10)", "direccion_id: BIGINT (FK direccion_cliente)", "metodo_pago: VARCHAR(20)", "subtotal: NUMERIC(10,2)",
            "descuento: NUMERIC(10,2)", "total: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ", "actualizado_en: TIMESTAMPTZ"],
        "operaciones": ["ventas_semanales(db, desde): list[Row]  [analitica/repository.py, JOIN detalle_venta]",
            "rfm_de_clientes(db): list[Row]  [analitica/repository.py, JOIN cliente y usuario]",
            "ejecutar(db, espec, *, sucursal_forzada): Resultado  [reportes/dinamico.py, hecho 'venta']"]},
    "DetalleVenta": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "detalle_venta",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta, ON DELETE CASCADE)", "variante_id: BIGINT (FK variante_producto)",
            "cantidad: INTEGER", "precio_unitario: NUMERIC(10,2)", "descuento_unitario: NUMERIC(10,2)", "creado_en: TIMESTAMPTZ"],
        "operaciones": ["devoluciones(db, *, desde, hasta, sucursal_id, tipo): list[tuple]  [reportes/reportes_repository.py, JOIN por (venta, variante)]"]},
    "Devolucion": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "devolucion",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "venta_id: BIGINT (FK venta)", "turno_caja_id: BIGINT (FK turno_caja)",
            "origen: VARCHAR(6)", "recibida_por: BIGINT (FK usuario)", "reembolso_referencia: VARCHAR(100)", "reembolso_monto: NUMERIC(10,2)",
            "tipo: VARCHAR(12)", "venta_cambio_id: BIGINT (FK venta, UNIQUE)", "motivo: VARCHAR(200)", "monto: NUMERIC(10,2)",
            "diferencia: NUMERIC(10,2)", "metodo_diferencia: VARCHAR(20)", "creado_en: TIMESTAMPTZ", "estado: VARCHAR(10)",
            "conforme: BOOLEAN", "observacion_cliente: VARCHAR(300)"],
        "operaciones": ["devoluciones(db, *, desde, hasta, sucursal_id, tipo): list[tuple]  [reportes/reportes_repository.py]",
            "ejecutar(db, espec, *, sucursal_forzada): Resultado  [reportes/dinamico.py, hecho 'devolucion']"]},
    "DetalleDevolucion": {"tipo": "entidad", "origen": B + "ventas/models.py", "tabla": "detalle_devolucion",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "devolucion_id: BIGINT (FK devolucion, ON DELETE CASCADE)",
            "variante_id: BIGINT (FK variante_producto)", "cantidad: INTEGER", "creado_en: TIMESTAMPTZ"],
        "operaciones": ["devoluciones(db, *, desde, hasta, sucursal_id, tipo): list[tuple]  [reportes/reportes_repository.py, una fila por linea devuelta]"]},
    "Producto": {"tipo": "entidad", "origen": B + "catalogo/models.py", "tabla": "producto", "nota": OMIT_AUD,
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "codigo: VARCHAR(30)", "nombre: VARCHAR(120)", "descripcion: VARCHAR(500)",
            "categoria_id: INTEGER (FK categoria)", "proveedor_id: BIGINT (FK proveedor)", "temporada_id: INTEGER (FK temporada)",
            "coleccion_id: INTEGER (FK coleccion)", "precio_base: NUMERIC(10,2)", "activo: BOOLEAN"],
        "operaciones": ["productos_activos(db): list[Row]  [analitica/repository.py]"]},
    "ModeloAnalitica": {"tipo": "entidad", "origen": B + "analitica/models.py", "tabla": "modelo_analitica",
        "nota": "tipo IN (DEMANDA, SEGMENTOS, ANOMALIAS); se conservan los ultimos 5 de cada tipo (CONSERVAR).",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "tipo: VARCHAR(12)", "parametros: JSONB", "metricas: JSONB", "resultado: JSONB",
            "filas_entrenamiento: INTEGER", "filas_reales: INTEGER", "filas_sinteticas: INTEGER", "duracion_ms: INTEGER", "modelo: BYTEA",
            "entrenado_por: BIGINT (FK usuario, ON DELETE SET NULL)", "entrenado_en: TIMESTAMPTZ"],
        "operaciones": ["guardar(db, modelo): ModeloAnalitica  [analitica/repository.py]", "ultimo(db, tipo): ModeloAnalitica | None  [analitica/repository.py]",
            "historial(db): list[Row]  [analitica/repository.py]"]},
    "AsientoBitacora": {"tipo": "entidad", "origen": B + "bitacora/models.py", "tabla": "bitacora",
        "atributos": ["id: BIGINT (PK)", "empresa_id: BIGINT (FK empresa)", "ocurrido_en: TIMESTAMPTZ", "usuario_id: BIGINT (FK usuario, ON DELETE SET NULL)",
            "actor: VARCHAR(160)", "rol: VARCHAR(40)", "accion: VARCHAR(40)", "entidad: VARCHAR(60)", "entidad_id: VARCHAR(60)", "metodo: VARCHAR(10)",
            "ruta: VARCHAR(300)", "estado_http: INTEGER", "exito: BOOLEAN", "ip: VARCHAR(60)", "agente: VARCHAR(200)", "detalle: JSONB"],
        "operaciones": ["agregar(db, **campos): AsientoBitacora", "contar(db, **filtros): int", "listar(db, limite, desplazamiento, **filtros): list[tuple]",
            "acciones(db): list[str]", "roles(db): list[str]", "entidades(db): list[str]", "ultimo(db): AsientoBitacora | None"]},
}

# FK reales (multiplicidad: primero en el extremo ClaseA, despues en ClaseB)
FK = [
    ["Usuario", "Notificacion", "RECIBE", "1", "0..*"],
    ["Empresa", "Notificacion", "TIENE", "1", "0..*"],
    ["Empresa", "Suscripcion", "CONTRATA", "1", "0..*"],
    ["Plan", "Suscripcion", "RIGE", "1", "0..*"],
    ["Venta", "Devolucion", "SE_DEVUELVE_EN", "1", "0..*"],
    ["Venta", "DetalleVenta", "CONTIENE", "1", "0..*"],
    ["Devolucion", "DetalleDevolucion", "CONTIENE", "1", "0..*"],
    ["Sucursal", "Venta", "VENDE", "1", "0..*"],
    ["Usuario", "ModeloAnalitica", "ENTRENA", "0..1", "0..*"],
    ["Usuario", "AsientoBitacora", "DEJA_RASTRO_EN", "0..1", "0..*"],
]


def fks(cls):
    s = set(cls)
    return [list(v) for v in FK if v[0] in s and v[1] in s]


def bit(controles):
    return [[c, "BitacoraMiddleware", "ES_ANOTADO_POR", "1", "1"] for c in controles] + \
           [["BitacoraMiddleware", "AsientoBitacora", "REGISTRA", "1", "0..*"]]


CUS = {}

c26 = ["tareas", "notificaciones_service", "verificador", "ProveedorBrevo", "Notificacion", "Usuario", "Suscripcion", "Plan",
       "TareaAutomatica", "Empresa"]
CUS["CU-26"] = {"actores": ["Sistema"], "clases": c26,
    "operaciones_en_cu": {"tareas": ["_bucle()", "correr_vuelta(fabrica_de_sesiones, minimo_entre_vueltas)", "_toca_vuelta(conexion, minimo)",
            "_empresas_activas(db)", "_intentar(vuelta, db, nombre, tarea)", "_correos(db, empresa_id)"],
        "notificaciones_service": ["notificar(...)", "avisar_reserva_en_sucursal(db, reserva)", "_encargados_de(db, sucursal_id)",
            "_mensaje_de(db, notificacion)", "_cuerpo_html(notificacion, url)", "despachar_pendientes(db, *, limite)"],
        "verificador": ["incluye(db, funcion)", "plan_vigente(db)", "suscripcion_vigente(db)"],
        "Notificacion": ["crear(...)", "tomar_pendiente_de_correo(db)"]},
    "nota": "Sin BitacoraMiddleware: la tarea automatica no es una peticion HTTP y el middleware no la ve (solo el boton manual POST /mantenimiento/notificaciones/despacho deja asiento). El plan se mira al CREAR el aviso (notificar -> verificador.incluye('correo')): sin la funcion nace OMITIDO con motivo y queda solo en la campanita. La vuelta corre con fijar_empresa (RLS) por cada empresa activa. Omitidos por el tope: push_service (CU-42, despacha el push en la misma vuelta) y los modulos que llaman a avisar_* (reservas, pagos, inventario, traspasos, devoluciones web, offline).",
    "relaciones": [["Sistema", "tareas", "DISPARA", "1", "1"], ["tareas", "notificaciones_service", "LLAMA_A", "1", "1"],
        ["tareas", "TareaAutomatica", "ACTUALIZA", "1", "1"], ["tareas", "Empresa", "CONSULTA", "1", "0..*"],
        ["notificaciones_service", "verificador", "USA", "1", "1"], ["verificador", "Suscripcion", "CONSULTA", "1", "0..1"],
        ["verificador", "Plan", "CONSULTA", "1", "1"], ["notificaciones_service", "Usuario", "CONSULTA", "1", "0..*"],
        ["notificaciones_service", "Notificacion", "REGISTRA", "1", "0..*"], ["notificaciones_service", "Notificacion", "ACTUALIZA", "1", "0..*"],
        ["notificaciones_service", "ProveedorBrevo", "ENVIA_POR", "1", "1"]] + fks(c26)}

c27 = ["ConsultaIa", "ReportesService", "DictadoService", "dinamico_router", "dinamico", "interprete_reglas", "InterpreteGemini",
       "verificador", "ConsumoCupo", "BitacoraMiddleware", "AsientoBitacora", "Venta"]
CUS["CU-27"] = {"actores": ["Administrador", "Encargado"], "clases": c27,
    "operaciones_en_cu": {"ReportesService": ["consultarIa(texto)", "exportarIa(especificacion, formato)", "traducirIa(error)", "nombreDe(disposicion, tipo, formato)"],
        "InterpreteGemini": ["interpretar_consulta(texto, vocabulario, hoy)", "_pedir_json(modelo, instruccion)"],
        "verificador": ["verificar_funcion(db, funcion)", "verificar_cupo(db, cupo)", "uso_del_mes(db, cupo)", "consumir_cupo(db, cupo)", "plan_vigente(db)"],
        "Venta": ["ejecutar(db, espec, *, sucursal_forzada)"]},
    "nota": "La medida elige el hecho: Venta+DetalleVenta, Devolucion+DetalleDevolucion, Existencia o Reserva+DetalleReserva, con joins a Producto, Categoria, Talla, Color, Temporada y Sucursal (omitidas por el tope; Venta queda como ejemplo). El cupo se descuenta solo con el reporte armado; el pedido no entendido no gasta. exportar() vuelve a validar y ejecutar la especificacion y la convierte con reportes/exportador.py (omitido). El encargado tiene la sucursal impuesta (_sucursal_forzada).",
    "relaciones": [["Administrador", "ConsultaIa", "USA", "1", "1"], ["Encargado", "ConsultaIa", "USA", "1", "1"],
        ["ConsultaIa", "DictadoService", "DICTA_CON", "1", "1"], ["ConsultaIa", "ReportesService", "SOLICITA", "1", "1"],
        ["ReportesService", "dinamico_router", "LLAMA_A", "1", "1"], ["dinamico_router", "verificador", "USA", "1", "1"],
        ["dinamico_router", "InterpreteGemini", "SOLICITA", "1", "1"], ["dinamico_router", "interprete_reglas", "SOLICITA", "1", "0..1"],
        ["dinamico_router", "dinamico", "USA", "1", "1"], ["dinamico", "Venta", "CONSULTA", "1", "0..*"],
        ["verificador", "ConsumoCupo", "ACTUALIZA", "1", "0..1"]] + bit(["dinamico_router"]) + fks(c27)}

c28 = ["Exportar", "ReportesService", "reportes_router", "reportes_service", "exportador", "BitacoraMiddleware", "AsientoBitacora",
       "Devolucion", "DetalleDevolucion", "DetalleVenta", "Venta", "Sucursal"]
CUS["CU-28"] = {"actores": ["Administrador", "Encargado"], "clases": c28,
    "operaciones_en_cu": {"ReportesService": ["catalogo()", "descargar(tipo, formato, filtros)", "hayVoz()", "interpretarVoz(texto)", "traducir(error)"],
        "reportes_router": ["catalogo_de_reportes(db, usuario)", "descargar(tipo, formato, db, usuario, desde, hasta, sucursal_id, ...)"],
        "reportes_service": ["generar(db, *, tipo, desde, hasta, sucursal_id, extras)", "opciones_de(db, filtro)", "_rango(desde, hasta)", "_totales(definicion, filas)"],
        "Venta": []},
    "nota": "El reporte 'devoluciones' de REPORTES: una fila por linea devuelta (fecha, sucursal, tipo, venta, cajero, prenda, talla, color, cantidad, valor devuelto) y suma cantidad y valor. El valor sale del precio congelado de detalle_venta (join por venta y variante), no de variante_producto.precio. La sucursal sale de la caja del turno o, en la devolucion web (CU-25), de la venta. Omitidas por el tope: TurnoCaja, Caja, Usuario, VarianteProducto, Producto, Talla, Color. El GET de la exportacion SI deja asiento (EXPORTACIONES del middleware). El pedido por voz (hablar) es el CU-35 del primer parcial y pasa por el verificador con 'reportes_ia'.",
    "relaciones": [["Administrador", "Exportar", "USA", "1", "1"], ["Encargado", "Exportar", "USA", "1", "1"],
        ["Exportar", "ReportesService", "SOLICITA", "1", "1"], ["ReportesService", "reportes_router", "LLAMA_A", "1", "1"],
        ["reportes_router", "reportes_service", "USA", "1", "1"], ["reportes_router", "exportador", "USA", "1", "1"],
        ["reportes_service", "Devolucion", "CONSULTA", "1", "0..*"], ["reportes_service", "DetalleDevolucion", "CONSULTA", "1", "0..*"],
        ["reportes_service", "DetalleVenta", "CONSULTA", "1", "0..*"], ["reportes_service", "Venta", "CONSULTA", "1", "0..*"],
        ["reportes_service", "Sucursal", "CONSULTA", "1", "0..*"]] + bit(["reportes_router"]) + fks(c28)}

c29 = ["Analitica", "AnaliticaService", "analitica_router", "analitica_service", "modelos", "sinteticos", "verificador",
       "BitacoraMiddleware", "AsientoBitacora", "ModeloAnalitica", "Producto", "Venta"]
CUS["CU-29"] = {"actores": ["Administrador"], "clases": c29,
    "operaciones_en_cu": {"Analitica": ["entrenar()"], "AnaliticaService": ["entrenar(semilla)"], "analitica_router": ["entrenar(db, usuario, datos)"],
        "analitica_service": ["entrenar(db, usuario_id, semilla)", "_productos(db)", "_matriz_real(db, productos, lunes)", "_rfm_real(db)",
            "_guardar(db, tipo, e, inicio, usuario_id)", "resumen(db)"],
        "modelos": ["entrenar_demanda(productos, sinteticas, reales, lunes, semilla)", "entrenar_segmentos(sinteticos, reales, semilla)",
            "_preprocesar(rfm)", "_nombrar(centros)"],
        "verificador": ["verificar_funcion(db, funcion)", "plan_vigente(db)"],
        "ModeloAnalitica": ["guardar(db, modelo)", "ultimo(db, tipo)"],
        "Venta": ["ventas_semanales(db, desde)", "rfm_de_clientes(db)"]},
    "nota": "Lo dispara el Administrador (POST /analitica/entrenamientos); ninguna tarea automatica lo llama. Datos: productos activos y unidades por producto y semana de las ventas PAGADA o ENTREGADA, mas RFM por cliente; se suman a 104 semanas y 240 clientes sinteticos con semilla 2026. repo.guardar borra los entrenamientos viejos del tipo (conserva 5). Omitidas por el tope: DetalleVenta y Cliente (joins de ventas_semanales y rfm_de_clientes), Categoria.",
    "relaciones": [["Administrador", "Analitica", "USA", "1", "1"], ["Analitica", "AnaliticaService", "SOLICITA", "1", "1"],
        ["AnaliticaService", "analitica_router", "LLAMA_A", "1", "1"], ["analitica_router", "verificador", "USA", "1", "1"],
        ["analitica_router", "analitica_service", "USA", "1", "1"], ["analitica_service", "sinteticos", "USA", "1", "1"],
        ["analitica_service", "modelos", "USA", "1", "1"], ["analitica_service", "Producto", "CONSULTA", "1", "0..*"],
        ["analitica_service", "Venta", "CONSULTA", "1", "0..*"], ["analitica_service", "ModeloAnalitica", "REGISTRA", "1", "0..*"]]
        + bit(["analitica_router"]) + fks(c29)}

c30 = ["Analitica", "AnaliticaService", "analitica_router", "analitica_service", "modelos", "verificador", "exportador",
       "ModeloAnalitica", "Venta", "Plan"]
CUS["CU-30"] = {"actores": ["Administrador"], "clases": c30,
    "operaciones_en_cu": {"Analitica": ["ngOnInit()", "cargar()", "descargar(formato)", "tendencia(t)", "fechaCorta(iso)", "fechaLarga(iso)"],
        "AnaliticaService": ["resumen()", "clientes()", "reporte(formato)", "traducir(error)"],
        "analitica_router": ["resumen(db)", "clientes(db)", "reporte_pdf(db)", "reporte_excel(db)"],
        "analitica_service": ["resumen(db)", "clientes_por_segmento(db)", "_rfm_real(db)", "reporte(db)"],
        "modelos": ["clasificar(modelo, rfm)"], "verificador": ["verificar_funcion(db, funcion)", "plan_vigente(db)"],
        "ModeloAnalitica": ["ultimo(db, tipo)"], "Venta": ["rfm_de_clientes(db)"]},
    "nota": "Solo lectura: GET /analitica/resumen, /clientes y /reporte.pdf|xlsx. Sin bitacora: el middleware no anota GET y /analitica/reporte.* no esta en sus EXPORTACIONES (que solo mira /reportes/{tipo}.pdf|xlsx). Los clientes de hoy se clasifican con el modelo guardado, sin reentrenar; la pantalla muestra los 20 de mayor monto. La web no llama al historial (GET /analitica/entrenamientos).",
    "relaciones": [["Administrador", "Analitica", "USA", "1", "1"], ["Analitica", "AnaliticaService", "CONSULTA", "1", "1"],
        ["AnaliticaService", "analitica_router", "LLAMA_A", "1", "1"], ["analitica_router", "verificador", "USA", "1", "1"],
        ["verificador", "Plan", "CONSULTA", "1", "1"], ["analitica_router", "analitica_service", "USA", "1", "1"],
        ["analitica_router", "exportador", "USA", "1", "0..1"], ["analitica_service", "ModeloAnalitica", "CONSULTA", "1", "0..*"],
        ["analitica_service", "modelos", "USA", "1", "1"], ["analitica_service", "Venta", "CONSULTA", "1", "0..*"]] + fks(c30)}

# ------------------------------------------------------------------ 2.6 ---
ESPEC = {
    'CU-26': dict(
        descripcion='Avisa por correo a empleados y clientes los hechos que les importan, solo si el plan de la empresa '
                    'incluye los avisos por correo. El aviso dentro de la aplicación sale siempre.',
        actores='Sistema',
        iniciador='Sistema (la tarea automática)',
        precondiciones='Las tareas automáticas están encendidas (TAREAS_AUTOMATICAS=on). Ocurrió un hecho que avisa: '
                       'una reserva, un pedido pagado, existencia baja, un traspaso, una devolución, una operación sin '
                       'conexión o una talla disponible.',
        flujo=[
            'Otro caso de uso registra el hecho y le pide al sistema el aviso, dentro de la misma transacción.',
            'El sistema resuelve a quién avisarle (los encargados de la sucursal, el cliente o el cajero) y deja el aviso en la campanita.',
            'El sistema verifica que el plan vigente incluya los avisos por correo (incluye CU-05) y deja el correo pendiente.',
            'Cada 15 minutos la tarea automática despierta y toma el bloqueo, para que un solo worker corra la vuelta.',
            'Por cada empresa activa, el sistema toma de a una las notificaciones con el correo pendiente, la más vieja primero, hasta 50 por vuelta.',
            'El sistema arma el correo con el título, el cuerpo y el botón «Ver en Violet Boutique».',
            'El sistema envía el correo por Brevo.',
            'El sistema marca el correo como enviado, con la hora, y confirma cada uno por separado.',
        ],
        alternativos=[
            '3a. Plan sin correo: el aviso nace con el correo omitido y el motivo; queda solo en la campanita y en el push si hay un dispositivo suscrito.',
            '3b. Sin dirección: si el destinatario no tiene correo, el correo queda omitido.',
            '4a. Vuelta repetida: si el otro worker empezó una vuelta hace menos de 15 minutos, esta se saltea.',
            '7a. Falla el envío: Brevo rechaza o no responde; el correo queda fallido con el motivo y el sistema sigue con el siguiente. '
            'El administrador puede devolver los fallidos a la cola.',
        ],
        postcondiciones='Cada aviso queda en la campanita y su correo enviado, omitido o fallido. Correr la vuelta otra vez no repite ningún correo.',
        rastreo='RF-49',
    ),
    'CU-27': dict(
        descripcion='Permite pedir un reporte en lenguaje natural, escrito o hablado. La IA traduce el pedido y el sistema '
                    'arma el reporte con datos reales de la empresa, sin que la IA escriba SQL.',
        actores='Administrador de la empresa, encargado de sucursal',
        iniciador='Administrador o encargado',
        precondiciones='El usuario inició sesión. El plan incluye los reportes con IA y le queda cupo en el mes.',
        flujo=[
            'El usuario abre «Reportes con IA».',
            'El usuario escribe el pedido o lo dicta con «Hablar», o toca uno de los ejemplos, y pulsa «Generar».',
            'El sistema verifica el rol, que el plan incluya los reportes con IA y que quede cupo en el mes (incluye CU-05).',
            'El sistema arma el vocabulario: medidas, dimensiones y los nombres de las sucursales, categorías, productos y temporadas activas. Al encargado solo le da su sucursal.',
            'Gemini traduce el pedido a una especificación: medida, agrupación, filtros, período, orden, límite y tipo de gráfico.',
            'El sistema valida la especificación contra la lista blanca y comprueba que cada id sea de la empresa.',
            'El sistema arma la consulta, la ejecuta dentro de la empresa y escribe una lectura de los datos.',
            'El sistema descuenta uno del cupo del mes y muestra qué entendió, la tabla con totales y el gráfico.',
        ],
        alternativos=[
            '3a. Plan o cupo: si el plan no incluye los reportes con IA o el cupo del mes se agotó, el sistema rechaza el pedido y muestra el motivo.',
            '5a. Sin IA: si Gemini no está configurado o no contesta, el sistema usa el intérprete por reglas y la pantalla lo marca «sin IA».',
            '6a. Pedido ambiguo o no soportado: el sistema explica qué faltó y sugiere ejemplos; no gasta cupo.',
            '8a. Exportar: el usuario pulsa «PDF» o «Excel»; el sistema vuelve a correr la especificación y descarga el archivo.',
        ],
        postcondiciones='El usuario ve el reporte armado con datos de su empresa. El cupo del mes bajó en uno y la bitácora registra el pedido.',
        rastreo='RF-25, RF-26, RF-27, RF-28, RF-29, RF-30 · RN-10, RN-11',
    ),
    'CU-28': dict(
        descripcion='Permite bajar los reportes de gestión en PDF o Excel, incluido el de devoluciones y cambios, con el valor de cada prenda devuelta.',
        actores='Administrador de la empresa, encargado de sucursal',
        iniciador='Administrador o encargado',
        precondiciones='El usuario inició sesión. El encargado tiene una sucursal asignada.',
        flujo=[
            'El usuario abre «Reportes de gestión».',
            'El sistema muestra el catálogo de reportes con sus columnas y sus filtros, con las opciones ya cargadas.',
            'El usuario elige el período y, en «Reporte de devoluciones y cambios», la sucursal y el tipo: devolución o cambio de prenda.',
            'El usuario pulsa «PDF» o «Excel».',
            'El sistema aplica solo los filtros que declara ese reporte; al encargado le impone su sucursal.',
            'El sistema arma una fila por prenda devuelta: fecha y hora, sucursal, tipo, venta, cajero, prenda, talla, color, cantidad y valor devuelto al precio pagado en la venta.',
            'El sistema suma las unidades y el valor, e imprime el período, la sucursal y los filtros aplicados.',
            'El sistema entrega el archivo y la bitácora registra la exportación.',
        ],
        alternativos=[
            '3a. Pedir hablando: el usuario pulsa el micrófono y dice el reporte; el sistema muestra lo que entendió antes de descargar (necesita la función reportes_ia del plan).',
            '3b. Otros cortes: las devoluciones por día, semana, mes, producto, categoría, talla o color se piden en «Reportes con IA» (CU-27).',
            '5a. Encargado sin sucursal: el sistema no genera el reporte y le pide que el administrador lo asigne.',
        ],
        postcondiciones='El usuario tiene el archivo con el alcance impreso. La bitácora registra quién exportó qué reporte.',
        rastreo='RF-28, RF-38',
    ),
    'CU-29': dict(
        descripcion='Entrena el modelo supervisado de la demanda semanal y el no supervisado de los segmentos de clientes, '
                    'con los datos reales de la empresa completados con datos sintéticos.',
        actores='Administrador de la empresa',
        iniciador='Administrador',
        precondiciones='El administrador inició sesión. El plan incluye la analítica con ML.',
        flujo=[
            'El administrador abre «Analítica inteligente» y pulsa «Entrenar los modelos» o «Volver a entrenar».',
            'El sistema verifica el rol y que el plan incluya la analítica con ML (incluye CU-05).',
            'El sistema junta los productos activos y las unidades vendidas por producto y semana de las ventas pagadas o entregadas.',
            'El sistema genera la demanda sintética de 104 semanas con una semilla fija y le suma la real.',
            'El sistema entrena el GradientBoosting, lo valida con las últimas 12 semanas que no vio (MAE, RMSE, R² y mejora sobre la línea base), lo reentrena con todo y predice la semana que viene.',
            'El sistema calcula la recencia, la frecuencia y el monto de cada cliente real, los completa con 240 clientes sintéticos y entrena el KMeans con k de 2 a 6.',
            'El sistema elige el k de mejor silueta y le pone nombre a cada segmento según su centro.',
            'El sistema guarda los dos entrenamientos con sus parámetros, métricas, filas reales y sintéticas, duración y el modelo, y conserva los últimos cinco de cada tipo.',
            'El sistema muestra el dashboard nuevo (CU-30).',
        ],
        alternativos=[
            '1a. Otro rol: si no es administrador, el sistema rechaza el pedido.',
            '2a. Plan sin analítica: el sistema rechaza el pedido y la pantalla muestra el candado con el enlace a «Mi plan».',
            '3a. Pocas ventas: si la empresa no tiene productos o ventas, el sistema entrena con productos de relleno y datos sintéticos, y el dashboard muestra cuántas filas son reales.',
        ],
        postcondiciones='Quedan guardados un entrenamiento de demanda y uno de segmentos. La bitácora registra quién entrenó.',
        rastreo='RF-31, RF-32',
    ),
    'CU-30': dict(
        descripcion='Muestra el dashboard analítico: las métricas de los modelos, la demanda prevista, los segmentos de clientes y los clientes de hoy en su segmento.',
        actores='Administrador de la empresa',
        iniciador='Administrador',
        precondiciones='El administrador inició sesión. El plan incluye la analítica con ML.',
        flujo=[
            'El administrador abre «Analítica inteligente».',
            'El sistema verifica el rol y que el plan incluya la analítica con ML (incluye CU-05).',
            'El sistema lee el último entrenamiento de demanda y el último de segmentos.',
            'El sistema muestra las métricas del modelo de demanda, el gráfico de lo previsto contra lo real y el peso de cada variable.',
            'El sistema muestra la demanda prevista para la semana que viene por producto, con su tendencia.',
            'El sistema muestra los segmentos con la silueta de cada k y la cantidad de clientes de cada uno.',
            'El sistema clasifica a los clientes reales de hoy con el modelo guardado, sin reentrenar, y muestra los 20 de mayor monto con su segmento.',
        ],
        alternativos=[
            '2a. Plan sin analítica: la pantalla muestra el candado con el enlace a «Mi plan».',
            '3a. Sin entrenar: la pantalla invita a pulsar «Entrenar los modelos» (CU-29).',
            '7a. Reporte inteligente: el administrador pulsa «PDF» o «Excel» y baja las predicciones con las métricas y los segmentos.',
        ],
        postcondiciones='El administrador conoce la demanda prevista y los segmentos de sus clientes. No se modifica ningún dato.',
        rastreo='RF-32, RF-33',
    ),
}


# ------------------------------------------------------------- validación ---
def validar():
    ids = {c[0] for c in CASOS}
    actores_validos = {'Administrador de la plataforma', 'Administrador de la empresa', 'Encargado de sucursal', 'Cajero',
                       'Cliente', 'Proveedor', 'Sistema', 'Usuario', 'Empresa interesada'}
    for c in CASOS:
        assert set(c[2]) <= actores_validos, c[0]
        for x in c[3] + (c[5] if len(c) > 5 else []):
            assert x in ids or int(x[3:]) <= 20, (c[0], x)
    for r in ROBUSTEZ:
        assert r['cu'] in ids, r['cu']
        tipos = {**{f'A:{x}': 'A' for x in r['a']}, **{x: 'F' for x in r['f']},
                 **{x: 'C' for x in r['c']}, **{x: 'E' for x in r['e']}}
        grupos = sorted({g for g, *_ in r['m']})
        assert grupos == list(range(1, len(r['grupos']) + 1)), (r['cu'], grupos)
        assert 1 <= len(r['grupos']) <= 5, r['cu']
        for g, de, a, op in r['m']:
            assert de in tipos and a in tipos, (r['cu'], de, a)
            par = {tipos[de], tipos[a]}
            # la regla de la ing: nunca entidad con entidad; tampoco frontera con frontera
            assert par in ({'A', 'F'}, {'F', 'C'}, {'C', 'E'}, {'C'}), (r['cu'], de, a, op)
        usados = {p for _, de, a, _ in r['m'] for p in (de, a)}
        assert usados == set(tipos), (r['cu'], set(tipos) - usados)
        # F3: si aparece la bitácora, con sus dos mensajes
        if 'BitacoraMiddleware' in r['c']:
            ops = {(de, a, op.split('(')[0]) for _, de, a, op in r['m']}
            assert any(a == 'BitacoraMiddleware' and o == 'registrar' for _, a, o in ops), r['cu']
            assert ('BitacoraMiddleware', 'AsientoBitacora', 'agregar') in ops, r['cu']
    nombres_nuevos = set(DESCRIPCION)
    todos = {x for r in ROBUSTEZ for x in r['f'] + r['c'] + r['e']}
    assert nombres_nuevos <= todos, nombres_nuevos - todos


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
            assert any(r[2] == "ES_ANOTADO_POR" for r in d["relaciones"]), cu


def validar_espec():
    claves = {'descripcion', 'actores', 'iniciador', 'precondiciones', 'flujo', 'alternativos', 'postcondiciones', 'rastreo'}
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
    assert {c[0] for c in CASOS} == {r['cu'] for r in ROBUSTEZ} == set(CUS) == set(ESPEC)
    for cu, d in CUS.items():
        print(cu, len(d["clases"]), 'clases,', len(d["relaciones"]), 'relaciones')
    print('ok:', len(CASOS), 'casos,', len(ROBUSTEZ), 'robusteces,', len(CLASES), 'clases')
